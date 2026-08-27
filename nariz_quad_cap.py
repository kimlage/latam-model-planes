#!/usr/bin/env python3
"""Tampa quadrangular no nariz — mata o polo de valencia 32 (frota inteira).

    /Applications/Blender.app/Contents/MacOS/Blender -b "<pasta>/<MASTER>.blend" \
        --python nariz_quad_cap.py -- [medir|construir]

QA-BACKLOG "Fleet-wide: the nose tip is a valence-32 pole": a gaiola do casco
termina num UNICO vertice com 32 arestas. Catmull-Clark mantem continuidade de
plano tangente num vertice extraordinario dessa valencia mas deixa a CURVATURA
explodir, e o clear coat da pintura transforma isso numa cunha radial escura
com olho especular no apice — a "vinco vertical no radome" da reclamacao de
cabeca (aa2d27d). Medido em 2026-08-27: os ONZE cascos tem o mesmo polo
(nariz e cauda; o leque do nariz vai da ponta ate o anel FR1 a ~1 m — grande
e visivel; o da cauda cobre ~3 cm de cone e nao resolve em render nenhum:
fica como esta, registrado).

A CIRURGIA (a unica mudanca de malha):
1. remove o vertice-polo do nariz -> buraco de 32 lados;
2. tampa com uma GRADE 8x8 de quads (Coons sobre o anel, cantos em 0/8/16/24):
   os 4 cantos viram valencia 3 (suave para CC), o resto fica regular 4;
3. cada vertice novo e PROJETADO na superficie avaliada ANTIGA (raycast a
   partir do centro do anel) — a forma do radome que os gates aprovaram nao
   muda, so a curvatura para de concentrar num ponto; os CANTOS da grade
   (valencia 3) ficam a 45 graus do plano de simetria, fora da silhueta e
   da linha que o CamHeadOn olha (a 1a tentativa pos um canto na quilha e o
   vinco apareceu exatamente ali);
4. resolve-se o encolhimento CC por PONTO FIXO POR VERTICE: a cada iteracao,
   o erro entre a superficie avaliada nova e o ALVO ao longo do raio de cada
   vertice interno e reaplicado ao vertice da gaiola (amortecido 0.8), ate o
   pior residuo na zona da tampa ficar <=2 mm — um ajuste radial uniforme
   (1a tentativa) deixava 1.2 cm de depressao no apice, que o clear coat lia
   como vinco;
4b. o ALVO nao e a superficie antiga pura: perto do apice ela E o defeito —
   o limite CC de um leque de 32 arestas e quase um CONE, e reproduzi-la
   fielmente (2a tentativa, residuo <=2 mm) manteve o vinco identico no
   render. O alvo e a superficie antiga MISTURADA com um domo eliptico por
   direcao (apice antigo preservado, rho<=0.72 -> domo, rho>=0.72 -> casca
   antiga, peso smoothstep) — arredonda o apice sem tocar o flanco nem a
   emenda com o anel;
5. UV novo por (x -> u ajustado nos aneis vizinhos, theta -> v na convencao
   do anel; face que cruza a costura ganha v>1, repeat da textura resolve) —
   o radome e pintura chapada, nenhuma marca mora ali.

Idempotente por construcao: sem polo de valencia >=16 no nariz, nada e feito.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODO = argv[0] if argv else "construir"
D = bpy.data
log = lambda *a: print("[cap]", *a)

hull = D.objects.get("Fuselagem")
if hull is None:
    raise SystemExit("[cap] sem objeto Fuselagem")
mw = hull.matrix_world
inv = mw.inverted()

# -------------------------------------------------- superficie avaliada ANTIGA
def bvh_avaliada():
    dg = bpy.context.evaluated_depsgraph_get()
    oe = hull.evaluated_get(dg)
    me = oe.to_mesh()
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    tree = BVHTree.FromPolygons(verts, polys)
    oe.to_mesh_clear()
    return tree


def perfil(tree, xs):
    """(x, meia-largura, crista, quilha) por raycast lateral/vertical."""
    out = []
    for x in xs:
        hw = cr = ke = None
        h = tree.ray_cast(Vector((x, 5.0, -0.7)), Vector((0, -1, 0)), 10)
        if h[0] is not None:
            hw = abs(h[0].y)
        h = tree.ray_cast(Vector((x, 0.0, 5.0)), Vector((0, 0, -1)), 12)
        if h[0] is not None:
            cr = h[0].z
        h = tree.ray_cast(Vector((x, 0.0, -6.0)), Vector((0, 0, 1)), 12)
        if h[0] is not None:
            ke = h[0].z
        out.append((x, hw, cr, ke))
    return out


bvh_antiga = bvh_avaliada()
XS = [0.05, 0.10, 0.20, 0.35, 0.55, 0.80, 1.20, 2.00]
antes = perfil(bvh_antiga, XS)

# ------------------------------------------------------------------- topologia
bm = bmesh.new()
bm.from_mesh(hull.data)
bm.verts.ensure_lookup_table()

polos = [v for v in bm.verts if len(v.link_edges) >= 16]
polos.sort(key=lambda v: (mw @ v.co).x)
if not polos or (mw @ polos[0].co).x > 2.0:
    log("sem polo de nariz (ja capado?) — nada a fazer")
    bm.free()
    raise SystemExit(0)
polo = polos[0]
w_polo = mw @ polo.co
log("polo: idx %d valencia %d em x %.3f z %.3f" % (polo.index, len(polo.link_edges), w_polo.x, w_polo.z))

anel = [e.other_vert(polo) for e in polo.link_edges]
centro = sum((mw @ v.co for v in anel), Vector()) / len(anel)
log("anel: %d verts, centro x %.3f z %.3f, raio medio %.3f"
    % (len(anel), centro.x, centro.z,
       sum(((mw @ v.co) - centro).length for v in anel) / len(anel)))

if MODO == "medir":
    bm.free()
    raise SystemExit(0)

N = len(anel)
if N % 4 != 0:
    raise SystemExit("[cap] anel de %d lados (nao multiplo de 4)" % N)
Q = N // 4

# orientacao do anel por theta no plano (y, z-centro), e a convencao v(theta)
uv_layer = bm.loops.layers.uv.active


def theta_de(v):
    w = mw @ v.co
    return math.atan2(w.y, -(w.z - centro.z)) % (2 * math.pi)   # 0 na quilha


anel.sort(key=theta_de)
# girar a lista para que os CANTOS (indices 0, Q, 2Q, 3Q) caiam a ~45 graus do
# plano de simetria — nunca na quilha nem na crista (valencia 3 visivel).
Ntmp = len(anel)
alvo45 = math.pi / 4
melhor = min(range(Ntmp), key=lambda i: abs(theta_de(anel[i]) - alvo45))
anel = anel[melhor:] + anel[:melhor]
# snapshot do anel em coordenadas de mundo (os BMVerts morrem no to_mesh)
anel_snap = [(theta_de(v), (mw @ v.co).copy()) for v in anel]

# amostrar a convencao (theta -> v) e (x -> u) nos loops do anel ANTES da cirurgia
amostras_v, amostras_u = [], []
for v in anel:
    th = theta_de(v)
    for lo in v.link_loops:
        uv = lo[uv_layer].uv
        amostras_v.append((th, uv.y))
        amostras_u.append(((mw @ v.co).x, uv.x))
# v(theta): linear com costura — estimar em dois pontos afastados
amostras_v.sort()
th_a, v_a = amostras_v[len(amostras_v) // 4]
th_b, v_b = amostras_v[3 * len(amostras_v) // 4]
dv = (v_b - v_a) / (th_b - th_a) if th_b != th_a else 1.0 / (2 * math.pi)
u_x = sorted(amostras_u)
(x_u0, u0), (x_u1, u1) = u_x[0], u_x[-1]
u_polo = u0 + (u1 - u0) * ((w_polo.x - x_u0) / (x_u1 - x_u0) if x_u1 != x_u0 else 0.0)


def v_de_theta(th):
    return v_a + dv * (th - th_a)


def u_de_x(x):
    if x_u1 == x_u0:
        return u0
    return u0 + (u1 - u0) * (x - x_u0) / (x_u1 - x_u0)


mat_idx = None
suave = True
for f in polo.link_faces:
    mat_idx = f.material_index
    suave = f.smooth
    break

# ------------------------------------------------------- remover polo e tampar
bmesh.ops.delete(bm, geom=[polo], context='VERTS')
bm.verts.ensure_lookup_table()

b = anel                                   # 32 verts ordenados por theta
G = {}
for j in range(Q + 1):
    G[(0, j)] = b[j]
for i in range(1, Q + 1):
    G[(i, Q)] = b[Q + i]
for j in range(Q + 1):
    G[(Q, j)] = b[3 * Q - j]
for i in range(1, Q):
    G[(i, 0)] = b[(4 * Q - i) % N]

# projecao: do centro-interno C atraves da posicao Coons ate a superficie antiga
C = Vector((centro.x + 0.35, 0.0, centro.z))


def projeta(p):
    d = (p - C)
    L = d.length
    if L < 1e-6:
        d = Vector((-1, 0, 0)); L = 1.0
    d = d / L
    hit = bvh_antiga.ray_cast(C, d, 8.0)
    return hit[0] if hit[0] is not None else p


novos = {}
for i in range(1, Q):
    for j in range(1, Q):
        s, t = i / Q, j / Q
        P = ((1 - s) * (mw @ G[(0, j)].co) + s * (mw @ G[(Q, j)].co)
             + (1 - t) * (mw @ G[(i, 0)].co) + t * (mw @ G[(i, Q)].co)
             - (1 - s) * (1 - t) * (mw @ G[(0, 0)].co) - (1 - s) * t * (mw @ G[(0, Q)].co)
             - s * (1 - t) * (mw @ G[(Q, 0)].co) - s * t * (mw @ G[(Q, Q)].co))
        W = projeta(P)
        nv = bm.verts.new(inv @ W)
        G[(i, j)] = nv
        novos[(i, j)] = nv

faces_novas = []
for i in range(Q):
    for j in range(Q):
        try:
            f = bm.faces.new((G[(i, j)], G[(i, j + 1)], G[(i + 1, j + 1)], G[(i + 1, j)]))
        except ValueError:
            continue
        f.material_index = mat_idx or 0
        f.smooth = suave
        faces_novas.append(f)
log("tampa: %d verts novos, %d faces" % (len(novos), len(faces_novas)))

bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

# UV das faces novas
for f in faces_novas:
    vs = []
    for lo in f.loops:
        w = mw @ lo.vert.co
        r = math.hypot(w.y, w.z - centro.z)
        th = theta_de(lo.vert) if r > 0.02 else None
        vs.append((lo, w, th))
    ths = [t for _, _, t in vs if t is not None]
    ref = ths[0] if ths else 0.0
    for lo, w, th in vs:
        if th is None:
            th = ref
        # face nao pode cruzar a costura com salto: aproximar do ref
        while th - ref > math.pi:
            th -= 2 * math.pi
        while ref - th > math.pi:
            th += 2 * math.pi
        lo[uv_layer].uv = (u_de_x(w.x), v_de_theta(th))

bm.to_mesh(hull.data)
bm.free()
hull.data.update()

# ------------------------- resolver o encolhimento CC: ponto fixo por vertice
# apice antigo (preservado) e eixo do domo
h_apex = bvh_antiga.ray_cast(Vector((centro.x - 4.0, 0.0, centro.z)), Vector((1, 0, 0)), 10.0)
APEX = h_apex[0] if h_apex[0] is not None else Vector((0.0, 0.0, centro.z))
AXIS = (APEX - centro).normalized()
log("apice antigo: x %.4f z %.4f" % (APEX.x, APEX.z))

# fronteira por theta (para rho e para o domo) — do snapshot pre-cirurgia
anel_pos = sorted(anel_snap, key=lambda t: t[0])


def fronteira(th):
    ths = [t for t, _ in anel_pos]
    for k in range(len(ths)):
        t0, t1 = ths[k], ths[(k + 1) % len(ths)]
        span = (t1 - t0) % (2 * math.pi)
        dt = (th - t0) % (2 * math.pi)
        if dt <= span + 1e-9 and span > 1e-9:
            f = dt / span
            return anel_pos[k][1] * (1 - f) + anel_pos[(k + 1) % len(ths)][1] * f
    return anel_pos[0][1]


# perfil OGIVA: r^2 = a*d + b*d^2 (d = recuo axial atras do apice), ajustado no
# ANEL DE CONFIANCA rho 0.55..0.95 da casca antiga, com raio de apice minimo
# imposto (a >= 2*R_APEX) — o limite CC do leque e um quase-cone (a ~ 0) e o
# cone e exatamente o defeito; um radome real leva tampa arredondada de alguns
# cm. R_APEX = 0.05 m e ESTIMATIVA declarada (3 px no desenho de 600 dpi, nao
# resolve; foto de perto nao ha). O ajuste casa o perfil no anel de confianca,
# entao nao ha "botao": a curva e uma so, C1, do apice ao flanco.
R_APEX = float(argv[1]) if len(argv) > 1 else 0.05
EIXO_TRAS = (centro - APEX).normalized()      # aponta do apice para dentro


def _amostra_perfil():
    ds, rs = [], []
    for k in range(128):
        th = 2 * math.pi * k / 128
        B = fronteira(th)
        relB = B - APEX
        axB = relB.dot(EIXO_TRAS)
        radB = (relB - axB * EIXO_TRAS).length
        for rho in (0.55, 0.65, 0.75, 0.85, 0.95):
            # ponto-guia no leque antigo: interp apice->fronteira, projetado
            P = APEX + (B - APEX) * rho
            dirv = (P - C)
            if dirv.length < 1e-6:
                continue
            dirv.normalize()
            h = bvh_antiga.ray_cast(C, dirv, 8.0)[0]
            if h is None:
                continue
            rel = h - APEX
            d = rel.dot(EIXO_TRAS)
            r = (rel - d * EIXO_TRAS).length
            if d > 1e-4:
                # normalizar a anisotropia da secao pela fronteira desta direcao
                ds.append(d)
                rs.append(r / max(1e-6, radB))
    import numpy as _np
    A_ = _np.array([[d, d * d] for d in ds])
    y = _np.array(rs) ** 2
    (a_fit, b_fit), *_ = _np.linalg.lstsq(A_, y, rcond=None)
    return float(a_fit), float(b_fit)


A_FIT, B_FIT = _amostra_perfil()
log("ogiva ajustada (r/rB)^2 = %.4f d + %.4f d^2" % (A_FIT, B_FIT))
# impor raio de apice: em unidades normalizadas, r_norm = r/radB — o raio de
# apice fisico ~ (a_norm/2)*radB^2/... na pratica: a_min tal que r(d) do perfil
# FISICO tenha raio >= R_APEX na direcao media
_radB_med = sum(((fronteira(2 * math.pi * k / 32) - APEX)
                 - ((fronteira(2 * math.pi * k / 32) - APEX).dot(EIXO_TRAS)) * EIXO_TRAS).length
                for k in range(32)) / 32
a_min = 2.0 * R_APEX / max(1e-6, _radB_med ** 2)
if A_FIT < a_min:
    # re-ancorar b para manter o perfil no anel de confianca (d ~ recuo da fronteira)
    _axB_med = sum(((fronteira(2 * math.pi * k / 32) - APEX).dot(EIXO_TRAS)) for k in range(32)) / 32
    B_FIT = (1.0 - a_min * _axB_med) / max(1e-9, _axB_med ** 2)
    A_FIT = a_min
    log("apice forcado a R>=%.3f: a=%.4f b=%.4f (radB %.3f, axB %.3f)"
        % (R_APEX, A_FIT, B_FIT, _radB_med, _axB_med))


def alvo_no_raio(P_old):
    """substitui o raio radial pelo perfil ogiva, com fade para a casca antiga."""
    rel = P_old - APEX
    d = rel.dot(EIXO_TRAS)
    rad = rel - d * EIXO_TRAS
    if d <= 1e-5 or rad.length < 1e-6:
        return APEX
    th = math.atan2(rad.y, -(rad.z)) % (2 * math.pi)
    B = fronteira(th)
    relB = B - APEX
    axB = relB.dot(EIXO_TRAS)
    radB = (relB - axB * EIXO_TRAS).length
    rho = min(1.0, rad.length / max(1e-6, radB))
    r_fit = math.sqrt(max(0.0, A_FIT * d + B_FIT * d * d)) * radB
    if rho >= 0.90:
        w = 0.0
    elif rho <= 0.55:
        w = 1.0
    else:
        t = (0.90 - rho) / 0.35
        w = t * t * (3 - 2 * t)
    r_alvo = rad.length * (1 - w) + r_fit * w
    return APEX + d * EIXO_TRAS + rad.normalized() * r_alvo


n_novos = len(novos)
for rodada in range(14):
    bvh_nova = bvh_avaliada()
    bm = bmesh.new(); bm.from_mesh(hull.data); bm.verts.ensure_lookup_table()
    idxs = sorted(v.index for v in bm.verts)[-n_novos:]
    pior = 0.0
    for ix in idxs:
        v = bm.verts[ix]
        w = mw @ v.co
        d = (w - C)
        if d.length < 1e-6:
            continue
        d.normalize()
        h_old = bvh_antiga.ray_cast(C, d, 8.0)[0]
        h_new = bvh_nova.ray_cast(C, d, 8.0)[0]
        if h_old is None or h_new is None:
            continue
        erro = alvo_no_raio(h_old) - h_new       # onde a superficie deveria estar
        pior = max(pior, erro.length)
        v.co = inv @ (w + erro * 0.8)
    bm.to_mesh(hull.data); bm.free(); hull.data.update()
    log("ponto-fixo rodada %d: pior residuo %.4f m" % (rodada, pior))
    if pior <= 0.002:
        break

depois = perfil(bvh_avaliada(), XS)
log("perfil novo-antigo final:",
    [(x, None if None in (hw0, hw1) else round(hw1 - hw0, 4),
      None if None in (cr0, cr1) else round(cr1 - cr0, 4),
      None if None in (ke0, ke1) else round(ke1 - ke0, 4))
     for (x, hw0, cr0, ke0), (_, hw1, cr1, ke1) in zip(antes, depois)])

bpy.ops.wm.save_mainfile()
log("SALVO", bpy.data.filepath)
