"""Fase 2 — livery LATAM de PT-MUG, medida nas fotos (refs/manifest.md).

blender -b "boeing 777-300ER/B77W_LATAM.blend" --python "boeing 777-300ER/build_77w_fase2_livery.py"

Tudo o que e tinta vira textura: (x,theta) no casco (LiveryTex/LiveryFac/NoseMask)
e planar (x,z) na deriva (FinSashE/FinSashD). Nada de decalque 3D.

Cotas: fotogrametria 2026-08-20 sobre as duas fotos Wikimedia de PT-MUG
(FRA 2022-10-25 em voo, EGLL 2025-06-17 no solo). Deriva por retificacao afim
de tres retas (BA reto, BF, corda da ponta); casco por quadro local
(crista+quilha = eixo, 6.20 m = escala z; x pinado na porta 5 = 59.66 do APR,
que a medida devolveu em 59.67). Detalhes em spec_77w.json.
"""
import bpy
import bmesh
import json
import math
import os
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(BASE, "spec_77w.json")))

# CONSOLIDACAO DO PINTOR UNICO (2026-08-27): este arquivo pinta so LIVERY
# PLANA. As marcas (lockup, matricula PT-MUG, titulo, simbolo do ventre)
# moram em refazer_marcas.py (tag b77w), constantes movidas textualmente.
# Sequencia de reconstrucao (REBUILD.md):
#     build_77w_fase2_livery.py -> refazer_marcas.py -- b77w
#                               -> reparar_echarpe.py -- b77w
# A cunha vem da regra unica reparar_echarpe.FROTA["b77w"] — que ja carrega a
# fronteira dianteira re-medida de 2026-08-22 (x >= 58.25 + 1.0104 z; a
# constante 59.11 deste arquivo era a que a rodada da cauda corrigiu) — sobre
# a ponte da malha (kit.secoes_do_casco), com o mesmo supersampling ss=3 que
# este builder inventou e o kit herdou.
import sys as _sys
if os.path.dirname(BASE) not in _sys.path:
    _sys.path.insert(0, os.path.dirname(BASE))
import latam_livery_kit as kit  # noqa: E402
import reparar_echarpe as _re   # noqa: E402

LUV = 74.5                 # dominio u do casco: u = x/LUV (igual ao uv_cilindrica)
W, H = 4096, 1024
FW = FH = 2048

INDIGO = (0x2A, 0x00, 0x88)
CORAL = (0xED, 0x16, 0x51)
BRANCO = (0xE6, 0xE7, 0xEA)
CINZA_VOO = (0xC8, 0xCA, 0xCC)
CINZA_FAR = (0xB6, 0xB8, 0xBA)
SULCO = (0x2E, 0x30, 0x33)
VIDRO = (0x14, 0x17, 0x1A)


# ------------------------------------------------------- rasterizador numpy
def fill_tris(tris, x0, x1, z0, z1, nx, nz):
    out = np.zeros((nz, nx), bool)
    if not tris:
        return out
    sx = (x1 - x0) / nx
    sz = (z1 - z0) / nz
    T = np.asarray(tris, np.float64)
    P = np.empty_like(T)
    P[..., 0] = (T[..., 0] - x0) / sx - 0.5
    P[..., 1] = (T[..., 1] - z0) / sz - 0.5
    for k in range(P.shape[0]):
        a, b, c = P[k]
        i0 = max(0, int(math.floor(min(a[0], b[0], c[0]))))
        i1 = min(nx - 1, int(math.ceil(max(a[0], b[0], c[0]))))
        j0 = max(0, int(math.floor(min(a[1], b[1], c[1]))))
        j1 = min(nz - 1, int(math.ceil(max(a[1], b[1], c[1]))))
        if i1 < i0 or j1 < j0:
            continue
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        ii = np.arange(i0, i1 + 1)[None, :]
        jj = np.arange(j0, j1 + 1)[:, None]
        l1 = ((b[1] - c[1]) * (ii - c[0]) + (c[0] - b[0]) * (jj - c[1])) / d
        l2 = ((c[1] - a[1]) * (ii - c[0]) + (a[0] - c[0]) * (jj - c[1])) / d
        l3 = 1.0 - l1 - l2
        m = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        out[j0:j1 + 1, i0:i1 + 1] |= m
    return out


def leque(poly):
    return [[poly[0], poly[i], poly[i + 1]] for i in range(1, len(poly) - 1)]


# ----------------------------------------------------------------- geometria
nose = S["nariz_estacoes"]
tail = S["cauda"]
_nx = np.array([s[0] for s in nose])
_nc = np.array([s[1] for s in nose])
_nk = np.array([s[2] for s in nose])
_nw = np.array([s[3] for s in nose])
_tx = np.array([s[0] for s in tail])
_tzc = np.array([s[1] for s in tail])
_trz = np.array([s[2] for s in tail])
XCONST0, XCONST1 = S["secao_constante_x"]


def w_ratio_cone(x):
    x = np.asarray(x, float)
    return np.where(x <= 68.0, 0.96,
                    0.96 + (0.35 - 0.96) * (x - 68.0) / (73.86 - 68.0))


def zc_rz_ry(x):
    """centro z, semi-eixo vertical e semi-eixo lateral da secao em x."""
    x = np.asarray(x, float)
    zc = np.zeros_like(x)
    rz = np.full_like(x, 3.10)
    ry = np.full_like(x, 3.10)
    m = x <= XCONST0
    if m.any():
        c = np.interp(x[m], _nx, _nc)
        k = np.interp(x[m], _nx, _nk)
        zc[m] = (c + k) / 2.0
        rz[m] = (c - k) / 2.0
        ry[m] = np.interp(x[m], _nx, _nw)
    m = x >= XCONST1
    if m.any():
        zc[m] = np.interp(x[m], _tx, _tzc)
        rz[m] = np.interp(x[m], _tx, _trz)
        ry[m] = w_ratio_cone(x[m]) * rz[m]
    return zc, rz, ry


uu = (np.arange(W) + 0.5) / W
vv = (np.arange(H) + 0.5) / H
UX = uu * LUV
VT = vv * 2 * math.pi - math.pi
GX = np.repeat(UX[None, :], H, axis=0)
GT = np.repeat(VT[:, None], W, axis=1)
_zc, _rz, _ry = zc_rz_ry(UX)
GZ = _zc[None, :] + _rz[None, :] * np.cos(GT)
GABS = np.abs(GT)
LADO = np.where(GT < 0, -1, 1)          # -1 = bombordo (y<0)

tex = np.zeros((H, W, 3), np.uint8)
tex[:] = BRANCO

# ============================================================ 1. cunha indigo
LV = S["livery_pt_mug"]["cunha_indigo"]
# Cobertura pela regra unica (reparar_echarpe._r_77w) sobre a ponte da MALHA,
# ss=3 — o mecanismo que este builder inventou, agora compartilhado no kit.
for _o in bpy.data.objects:
    _o.hide_viewport = False
bpy.context.view_layer.update()
_casco_ob = bpy.data.objects.get("Fuselagem") or bpy.data.objects["Casco"]
_crx, _crzc, _crrz, _crry = kit.secoes_do_casco(_casco_ob)
cob = kit.cobertura_echarpe(_re.FROTA["b77w"]["regra"], _crx, _crzc, _crrz,
                            0.0, LUV, W, H, ss=3)
cunha = cob >= 0.5
tex[...] = (np.array(BRANCO, np.float32) * (1 - cob[..., None]) +
            np.array(INDIGO, np.float32) * cob[..., None]).astype(np.uint8)
base_cor = tex.copy()
print(f"[casco] cunha indigo = {int(cunha.sum())} texels ({100*cunha.mean():.2f}%), "
      f"{int(((cob > 0.02) & (cob < 0.98)).sum())} texels de borda suavizados")


# ==================================================== 2. marcas em (x,z)
def marca(tris, x0, x1, z0, z1, cor, lado, ppm=460):
    nx = max(8, int(round((x1 - x0) * ppm)))
    nz = max(8, int(round((z1 - z0) * ppm)))
    arr = fill_tris(tris, x0, x1, z0, z1, nx, nz)
    if not arr.any():
        return 0
    sel = (GX >= x0) & (GX <= x1) & (GZ >= z0) & (GZ <= z1)
    if lado:
        sel &= (LADO == lado)
    if not sel.any():
        return 0
    ix = np.clip(((GX[sel] - x0) / (x1 - x0) * nx).astype(int), 0, nx - 1)
    jz = np.clip(((GZ[sel] - z0) / (z1 - z0) * nz).astype(int), 0, nz - 1)
    hit = arr[jz, ix]
    r, c = np.where(sel)
    r, c = r[hit], c[hit]
    if cor is None:
        tex[r, c] = base_cor[r, c]
    else:
        tex[r, c] = cor
    return int(hit.sum())


def tris_do_objeto(nome):
    ob = bpy.data.objects.get(nome)
    if ob is None:
        return [], None
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tris = [[(v.co.x, v.co.y) for v in f.verts] for f in bm.faces]
    bm.free()
    if not tris:
        return [], None
    a = np.asarray(tris)
    return tris, (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())


def texto_tris(txt):
    cu = bpy.data.curves.new(type="FONT", name="_tmp_txt")
    cu.body = txt
    ob = bpy.data.objects.new("_tmp_txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tris = [[(v.co.x, v.co.y) for v in f.verts] for f in bm.faces]
    bm.free()
    bpy.data.meshes.remove(me)
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    a = np.asarray(tris)
    return tris, (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())


def encaixa(tris, bb, x0, x1, z0, z1, espelha=False, cis=0.0):
    ax, bx, ay, by = bb
    sx = (x1 - x0) / max(bx - ax, 1e-9)
    sz = (z1 - z0) / max(by - ay, 1e-9)
    out = []
    for t in tris:
        p = []
        for X, Y in t:
            Xc = X + cis * (Y - ay)
            xm = (x1 - (Xc - ax) * sx) if espelha else (x0 + (Xc - ax) * sx)
            p.append((xm, z0 + (Y - ay) * sz))
        out.append(p)
    return out


def marca_th(tris, bb, x0, x1, th_topo, th_base, cor, lado, espelha=False, ppm=460):
    """Marca colocada em (x, theta): preserva a proporcao sobre a superficie
    desenvolvida em vez de a achatar na projecao lateral."""
    ax, bx, ay, by = bb
    sx = (x1 - x0) / max(bx - ax, 1e-9)
    st = (th_base - th_topo) / max(by - ay, 1e-9)
    polys = []
    for t in tris:
        p = []
        for X, Y in t:
            xm = (x1 - (X - ax) * sx) if espelha else (x0 + (X - ax) * sx)
            p.append((xm, th_base - (Y - ay) * st))
        polys.append(p)
    nx = max(8, int(round((x1 - x0) * ppm)))
    nt = max(8, int(round(math.radians(th_base - th_topo) * 3.10 * ppm)))
    arr = fill_tris(polys, x0, x1, th_topo, th_base, nx, nt)
    if not arr.any():
        return 0
    GD = np.degrees(GABS)
    sel = (GX >= x0) & (GX <= x1) & (GD >= th_topo) & (GD <= th_base)
    if lado:
        sel &= (LADO == lado)
    if not sel.any():
        return 0
    ix = np.clip(((GX[sel] - x0) / (x1 - x0) * nx).astype(int), 0, nx - 1)
    jt = np.clip(((GD[sel] - th_topo) / (th_base - th_topo) * nt).astype(int), 0, nt - 1)
    hit = arr[jt, ix]
    r, c = np.where(sel)
    tex[r[hit], c[hit]] = cor
    return int(hit.sum())


# ============================================== 3. portas e contornos
def rrect(x0, x1, zl, zh, d, r):
    a, b, c, e = x0 - d, x1 + d, zl - d, zh + d
    rr = min(r + d, (b - a) / 2 - 1e-4, (e - c) / 2 - 1e-4)
    pts = []
    for (cx, cz, a0) in ((b - rr, e - rr, 0), (a + rr, e - rr, 90),
                         (a + rr, c + rr, 180), (b - rr, c + rr, 270)):
        for k in range(9):
            th = math.radians(a0 + k * 90 / 8)
            pts.append((cx + rr * math.cos(th), cz + rr * math.sin(th)))
    return pts


def porta(cx, larg, zl, zh, r=0.28, lado=0):
    x0, x1 = cx - larg / 2, cx + larg / 2
    X0, X1, Z0, Z1 = x0 - 0.30, x1 + 0.30, zl - 0.30, zh + 0.30
    marca(leque(rrect(x0, x1, zl, zh, 0.075, r)), X0, X1, Z0, Z1, CINZA_FAR, lado)
    marca(leque(rrect(x0, x1, zl, zh, 0.032, r)), X0, X1, Z0, Z1, SULCO, lado)
    marca(leque(rrect(x0, x1, zl, zh, 0.008, r)), X0, X1, Z0, Z1, None, lado)


P = S["portas_pax"]
DZ0, DZ1 = -0.55, 1.33          # soleira/topo do recorte (medido na porta 5)
for cx in P["centros_x"]:
    for lado in (-1, 1):
        porta(cx, P["recorte"][0], DZ0, DZ1, r=0.26, lado=lado)
PC = S["portas_carga"]
porta(PC["fwd_x"], PC["abertura_fwd"][0], -2.35, -0.65, r=0.16, lado=1)
porta(PC["aft_x"], PC["abertura_aft"][0], -2.35, -0.65, r=0.16, lado=1)
porta(PC["bulk"]["x"], PC["bulk"]["dim"][0], -2.05, -0.91, r=0.12, lado=1)

# ==================================================== 4. faixa de janelas
J = S["janelas_pax"]
JW, JH = J["abertura"]
JZ0, JZ1 = J["centro_z"] - JH / 2, J["centro_z"] + JH / 2
JPASSO = J["pitch"]
JX0, JX1 = J["faixa_x"]
njan = int((JX1 - JX0) / JPASSO)
portas_x = list(P["centros_x"])
for lado in (-1, 1):
    tris = []
    for i in range(njan + 1):
        cx = JX0 + i * JPASSO
        if any(abs(cx - px) < 1.05 for px in portas_x):
            continue
        tris += leque(rrect(cx - JW / 2, cx + JW / 2, JZ0, JZ1, 0.0, 0.06))
    n = marca(tris, JX0 - 0.5, JX1 + 0.5, JZ0 - 0.12, JZ1 + 0.12, VIDRO, lado, ppm=620)
print(f"[casco] janelas pintadas: {n} texels por lado")

# =================================== 5-7. MARCAS: movidas para refazer_marcas
# Lockup LATAM (simbolo+wordmark), matricula PT-MUG, titulo 'BOEING 777-300'
# e o simbolo do ventre moram em refazer_marcas.py (tag b77w, secao "legado
# 767/777"), com estas mesmas constantes e o mesmo rasterizador (raio de arco
# 3.10), citados la. Rodar refazer_marcas e o proximo passo obrigatorio
# (REBUILD.md). O desgaste (suja) fica aqui por ser livery plana;
# refazer_marcas reaplica as mesmas caixas sobre a tinta do ventre.


def suja(x0, x1, t0, t1, cor, inten):
    m = ((GX >= x0) & (GX <= x1) & (GABS >= math.radians(t0)) &
         (GABS <= math.radians(t1)))
    if m.any():
        tex[m] = (tex[m] * (1 - inten) + np.array(cor) * inten).astype(np.uint8)


suja(6.5, 14.0, 156, 180, (0x9A, 0x93, 0x88), 0.08)          # spray do trem de nariz
suja(38.0, 46.0, 150, 180, (0x9E, 0x98, 0x8E), 0.06)         # atras do trem principal
suja(69.0, 74.0, 120, 180, (0x8E, 0x88, 0x82), 0.10)         # fuligem da APU

# ========================================================= 8. NoseMask
# Parabrisa do 777: SEIS vidros, tres por lado, que envolvem a FRENTE do nariz.
#
# O que estava errado ate 2026-08-21: a banda era construida em (x,z) com o
# topo colado na crista (z = crista(x)-0.16, limitado em 0.97) e cortada por
# dois montantes VERTICAIS em x. Isso produz tres retangulos enfileirados numa
# faixa que so existe entre theta 28 e 73 graus — ou seja, nunca chega ao
# plano de simetria. Os dois vidros No.1 nao se encontravam no montante
# central, e o "V" que identifica o 777 de frente simplesmente nao existia.
# A causa e a que a skill extrair-cotas ja tinha escrito: a projecao LATERAL
# nao ve o vidro contornar o nariz, e medir nela achata o que sobe o ombro.
#
# Metodo correto (o mesmo do 787-9): os poligonos sao medidos na VISTA FRONTAL
# em (|y|, z) — projecao ao longo de x, portanto y e z sao exatos — e a
# estacao x de cada vertice sai de POR O PONTO NA SUPERFICIE: para (|y|,z)
# dado existe um unico x cuja secao passa por ele, porque as secoes do nariz
# crescem monotonicamente. O acoplamento com o casco produz sozinho o V e o
# contorno em 3D; nada e decalque.
#
# Fontes: APR D6-58329-2 p.18 vista frontal rasterizada a 4800 dpi, calibrada
# pelo proprio circulo da fuselagem (ajuste por raios, R=889.5 px = 3.10 m,
# rms 0.55 px). Conferido na foto head-on de S2-AFO (refs/manifest.json):
# meia-largura maxima do envidracado 1.63 m contra 1.62 medido no desenho, e
# razao altura/meia-largura 0.382 na foto contra 0.392 no desenho.
PB = S["parabrisa_6_vidros"]
PANES_YZ = [PB["no1_frontal_yz"], PB["no2_deslizante_yz"], PB["no3_kick_yz"]]
SELO_M = PB["selo_m"]                     # espessura do selo preto na superficie
FOLGA_M = PB["folga_desenho_m"]           # o APR desenha o vidro menor que a foto


def x_de_yz(y, z):
    """Estacao x cuja secao eliptica passa por (|y|, z).

    g(x) = (y/ry)^2 + ((z-zc)/rz)^2 - 1 e monotona decrescente em x no nariz
    (as secoes crescem), entao a bissecao acha a raiz sem ambiguidade.
    """
    def g(x):
        zc, rz, ry = zc_rz_ry(np.array([x]))
        return (y / float(ry[0])) ** 2 + ((z - float(zc[0])) / float(rz[0])) ** 2 - 1.0
    lo, hi = 0.02, 9.5
    if g(hi) > 0.0:
        raise ValueError(f"(y={y}, z={z}) nao pousa no casco ate x=9.5")
    for _ in range(70):
        m = 0.5 * (lo + hi)
        if g(m) > 0.0:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def theta_de_yz(x, y, z):
    zc, rz, ry = zc_rz_ry(np.array([x]))
    return math.degrees(math.atan2(max(y, 0.0) / float(ry[0]),
                                   (z - float(zc[0])) / float(rz[0])))


def para_xtheta(poly_yz, n=24):
    """(|y|,z) -> (x, theta em graus), densificando cada aresta."""
    out = []
    m = len(poly_yz)
    for i in range(m):
        y0, z0 = poly_yz[i]
        y1, z1 = poly_yz[(i + 1) % m]
        for k in range(n):
            t = k / n
            y, z = y0 + t * (y1 - y0), z0 + t * (z1 - z0)
            x = x_de_yz(y, z)
            out.append((x, theta_de_yz(x, y, z)))
    return out


def desloca(poly, d):
    """Offset do poligono por d em (|y|, z): cada aresta anda d para fora e as
    retas vizinhas se reencontram. O alvo desta correcao E a vista head-on, e
    e nela que a medida existe, entao o offset e feito NO PLANO frontal e nao
    sobre a superficie."""
    m = len(poly)
    P = [np.array(p, float) for p in poly]
    c = sum(P) / m
    ret = []
    for i in range(m):
        a, b = P[i], P[(i + 1) % m]
        e = b - a
        n = np.array([e[1], -e[0]])
        n /= max(np.linalg.norm(n), 1e-9)
        if n @ (a - c) < 0:
            n = -n
        ret.append((n, float(n @ a) + d))
    out = []
    for i in range(m):
        n1, o1 = ret[i - 1]
        n2, o2 = ret[i]
        M = np.array([n1, n2])
        if abs(np.linalg.det(M)) < 1e-9:
            out.append(tuple(P[i]))
        else:
            q = np.linalg.solve(M, [o1, o2])
            out.append((float(q[0]), float(q[1])))
    return out


def arredonda(poly, r=0.055, n=7):
    """Filete de raio r em cada canto do poligono, feito em (|y|, z) antes do
    mapeamento — mais barato e mais previsivel que uma abertura morfologica na
    grade, e o vidro do 777 tem canto arredondado bem visivel na foto."""
    out = []
    m = len(poly)
    for i in range(m):
        p = np.array(poly[i], float)
        a = np.array(poly[i - 1], float)
        b = np.array(poly[(i + 1) % m], float)
        ua = (a - p) / max(np.linalg.norm(a - p), 1e-9)
        ub = (b - p) / max(np.linalg.norm(b - p), 1e-9)
        cosang = float(np.clip(ua @ ub, -1.0, 1.0))
        t = r / max(math.tan(math.acos(cosang) / 2.0), 1e-6)
        t = min(t, 0.45 * np.linalg.norm(a - p), 0.45 * np.linalg.norm(b - p))
        pa, pb = p + ua * t, p + ub * t
        for k in range(n + 1):
            s = k / n
            # Bezier quadratica: aproxima o arco do filete
            q = (1 - s) ** 2 * pa + 2 * (1 - s) * s * p + s ** 2 * pb
            out.append((float(q[0]), float(q[1])))
    return out


def leque_centro(poly):
    """Fan a partir do centroide: os poligonos mapeados em (x,theta) tem
    arestas curvas e o fan a partir do vertice 0 deixaria buraco."""
    cx = sum(p[0] for p in poly) / len(poly)
    ct = sum(p[1] for p in poly) / len(poly)
    return [[(cx, ct), poly[i], poly[(i + 1) % len(poly)]]
            for i in range(len(poly))]


# NoseMask tem resolucao PROPRIA (2x a do casco) e cobertura por supersample
# 4x4: o parabrisa ocupa ~2% do dominio u, entao mascara binaria vira serrilha
# grossa no close-up do nariz — o defeito apareceu no primeiro render.
NW, NH = W * 2, H * 2
nose_mask = np.zeros((NH, NW, 3), np.float32)

PANES_XT = [para_xtheta(arredonda(desloca(p, FOLGA_M)), n=6)
             for p in PANES_YZ]
_allx = [p[0] for pn in PANES_XT for p in pn]
_allt = [p[1] for pn in PANES_XT for p in pn]
for nome, pn in zip(("No.1 frontal", "No.2 deslizante", "No.3 kick"), PANES_XT):
    xs = [p[0] for p in pn]; ts = [p[1] for p in pn]
    print(f"[parabrisa] {nome:16s} x {min(xs):.3f}..{max(xs):.3f}  "
          f"theta {min(ts):.1f}..{max(ts):.1f} graus")
print(f"[parabrisa] envidracado inteiro: x {min(_allx):.3f}..{max(_allx):.3f}  "
      f"theta {min(_allt):.1f}..{max(_allt):.1f} graus")

PX0, PX1 = min(_allx) - 0.30, max(_allx) + 0.30
PT0, PT1 = 0.0, max(_allt) + 8.0
npx, npt = 2600, 1800
_nuu = (np.arange(NW) + 0.5) / NW * LUV
_nvv = (np.arange(NH) + 0.5) / NH * 2 * math.pi - math.pi
NGX = np.repeat(_nuu[None, :], NH, axis=0)
NGD = np.degrees(np.abs(np.repeat(_nvv[:, None], NW, axis=1)))
dx_tex = LUV / NW
dt_tex = 360.0 / NH

# raio medio da secao na zona do parabrisa: converte metros em graus de theta
_zcw, _rzw, _ryw = zc_rz_ry(np.array([0.5 * (min(_allx) + max(_allx))]))
R_WS = 0.5 * (float(_rzw[0]) + float(_ryw[0]))
print(f"[parabrisa] raio medio na zona do vidro {R_WS:.3f} m -> "
      f"{math.degrees(1.0 / R_WS):.2f} graus/m (so diagnostico: a morfologia "
      f"usa o raio LOCAL, faixa a faixa)")


def _dil_eixo(m, r, eixo):
    """Dilatacao de caixa por raio r ao longo de um eixo, por duplicacao
    binaria: 1,2,4,... — O(log r) passadas em vez de O(r)."""
    if r <= 0:
        return m
    out = m.copy()
    d = 1
    while d <= r:
        sh = np.zeros_like(out)
        if eixo == 0:
            sh[d:, :] = out[:-d, :]
            out = out | sh
            sh = np.zeros_like(out)
            sh[:-d, :] = out[d:, :]
        else:
            sh[:, d:] = out[:, :-d]
            out = out | sh
            sh = np.zeros_like(out)
            sh[:, :-d] = out[:, d:]
        out = out | sh
        d *= 2
    return out


def _dil_octo(m, rx, rt):
    """Octogono ~ uniao de dois retangulos (rx, rt/2) e (rx/2, rt): evita o
    canto quadrado que um retangulo puro deixaria na borda externa do selo."""
    a = _dil_eixo(_dil_eixo(m, rx, 1), max(1, rt // 2), 0)
    b = _dil_eixo(_dil_eixo(m, max(1, rx // 2), 1), rt, 0)
    return a | b


sx_m = (PX1 - PX0) / npx                    # metros por celula em x
st_g = (PT1 - PT0) / npt                    # graus por celula em theta


def _dil_metrico(m, metros, nb=10):
    """Dilata por `metros` de ARCO REAL.

    Um disco fixo em (x, theta) nao e um disco em metros: o raio da secao vai
    de ~1.1 m em x=1.1 a ~2.1 m em x=3.0, entao o mesmo numero de graus vale o
    dobro de arco atras. Um raio unico em graus deixava o selo 25% fino perto
    da crista — que e exatamente onde fica o montante central, o detalhe que
    o dono olha primeiro. Resolvido por faixas de x.
    """
    out = np.zeros_like(m)
    bordas = np.linspace(PX0, PX1, nb + 1)
    rx = max(1, int(round(metros / sx_m)))
    for k in range(nb):
        xa, xb = bordas[k], bordas[k + 1]
        zc_, rz_, ry_ = zc_rz_ry(np.array([0.5 * (xa + xb)]))
        r = 0.5 * (float(rz_[0]) + float(ry_[0]))
        rt = max(1, int(round(metros * math.degrees(1.0 / r) / st_g)))
        ia = max(0, int((xa - PX0) / sx_m) - rx - 1)
        ib = min(npx, int((xb - PX0) / sx_m) + rx + 2)
        d = _dil_octo(m[:, ia:ib], rx, rt)
        ja = max(0, int((xa - PX0) / sx_m))
        jb = min(npx, int((xb - PX0) / sx_m) + 1)
        out[:, ja:jb] |= d[:, ja - ia:jb - ia]
    return out


# vidro rasterizado na grade fina (cantos ja filetados nos poligonos)
vidro_f = np.zeros((npt, npx), bool)
for pn in PANES_XT:
    vidro_f |= fill_tris(leque_centro(pn), PX0, PX1, PT0, PT1, npx, npt)

# Selo escuro em volta de cada vidro. O APR desenha o CONTORNO DO VIDRO; na
# aeronave real ha uma vedacao preta de ~6 cm entre o vidro e a pintura, e e
# ela que a foto head-on conta como parte da mancha escura. Medido em
# S2-AFO: a mancha escura vai a |y| 1.70 contra 1.617 do contorno do desenho,
# e o vao branco no montante central mede 0.128 m contra 0.216 de abertura a
# abertura — as duas coisas fecham com um selo de 0.06 m por lado.
selo_f = _dil_metrico(vidro_f, SELO_M) & ~vidro_f


def pinta_grade(arr, canal, sub=4):
    sel = (NGX >= PX0) & (NGX <= PX1) & (NGD >= PT0) & (NGD <= PT1)
    r, c = np.where(sel)
    acc = np.zeros(r.shape, np.float32)
    for a_ in range(sub):
        for b_ in range(sub):
            ox = (a_ + 0.5) / sub - 0.5
            ot = (b_ + 0.5) / sub - 0.5
            gx = NGX[sel] + ox * dx_tex
            gd = NGD[sel] + ot * dt_tex
            ix = np.clip(((gx - PX0) / (PX1 - PX0) * npx).astype(int), 0, npx - 1)
            jt = np.clip(((gd - PT0) / (PT1 - PT0) * npt).astype(int), 0, npt - 1)
            acc += arr[jt, ix]
    acc /= sub * sub
    nose_mask[r, c, canal] = np.maximum(nose_mask[r, c, canal], acc)


pinta_grade(selo_f, 0)                                          # R = selo
pinta_grade(vidro_f, 1)                                         # G = vidro
nose_mask[..., 0] *= (1.0 - nose_mask[..., 1])

# Cinta da moldura: na foto os seis vidros vivem dentro de UMA estrutura
# rebitada, levemente mais fosca que a pintura do casco, e e ela que faz o
# conjunto ler como um envidracado so em vez de seis adesivos separados.
# Vai na LiveryTex (cor base), nao na NoseMask: e tinta/estrutura, nao vidro.
CINTA_M = PB.get("cinta_moldura_m", 0.085)
CINTA_COR = (0xD8, 0xD9, 0xDC)
cinta_f = _dil_metrico(vidro_f | selo_f, CINTA_M) & ~(vidro_f | selo_f)
_selc = (GX >= PX0) & (GX <= PX1) & (np.degrees(GABS) >= PT0) & (np.degrees(GABS) <= PT1)
if _selc.any():
    _r, _c = np.where(_selc)
    _ix = np.clip(((GX[_selc] - PX0) / (PX1 - PX0) * npx).astype(int), 0, npx - 1)
    _jt = np.clip(((np.degrees(GABS[_selc]) - PT0) / (PT1 - PT0) * npt).astype(int),
                  0, npt - 1)
    _h = cinta_f[_jt, _ix]
    tex[_r[_h], _c[_h]] = CINTA_COR
    print(f"[parabrisa] cinta da moldura {int(_h.sum())} texels na LiveryTex")

# area real do envidracado sobre a superficie (dA = ry*rz*... ; aproximacao por
# celula da grade fina usando o raio local) — serve de numero antes/depois.
_area = 0.0
_jj, _ii = np.where(vidro_f)
if len(_ii):
    _xc = PX0 + (_ii + 0.5) * sx_m
    _zcc, _rzc, _ryc = zc_rz_ry(_xc)
    _rloc = 0.5 * (_rzc + _ryc)
    _area = float(np.sum(sx_m * math.radians(st_g) * _rloc)) * 2.0   # dois lados
print(f"[parabrisa] area de vidro na superficie: {_area:.3f} m2 (os 6 vidros)")
print(f"[parabrisa] selo {float(nose_mask[...,0].sum()):.0f} / vidro "
      f"{float(nose_mask[...,1].sum()):.0f} texels (cobertura, {NW}x{NH})")

# ========================================================= 9. PanelBump
pb = np.full((H, W), 0.5, np.float32)
for xj in (2.05, 10.0, 22.6, 33.5, 44.9, 51.5, 56.0, 62.0, 68.0):
    c = int(xj / LUV * W)
    pb[:, max(0, c - 2):c + 3] += 0.16
for vf in (0.285, 0.345, 0.655, 0.715):
    r = int(vf * H)
    pb[max(0, r - 1):r + 2, :] += 0.08
for vf in (0.47, 0.53):
    r = int(vf * H)
    pb[max(0, r - 1):r + 2, :] += 0.05
pb = np.clip(pb, 0.0, 1.0)

# ============================================================ 10. gravacao
D = bpy.data


def grava(nome, dados, w, h, cinza=False, colorspace="sRGB"):
    # NUNCA remover e recriar o datablock: os nos de material referenciam a
    # imagem, e recriar deixa o no com image=None (que o Cycles renderiza
    # magenta -> o casco inteiro virou escuro numa das voltas). Redimensionar
    # preserva o link.
    img = D.images.get(nome)
    if img is None:
        img = D.images.new(nome, w, h, alpha=False, float_buffer=False)
    elif tuple(img.size) != (w, h):
        img.scale(w, h)
    px = np.ones((h, w, 4), np.float32)
    if cinza:
        px[..., 0] = px[..., 1] = px[..., 2] = dados
    elif dados.dtype == np.uint8:
        px[..., :3] = dados.astype(np.float32) / 255.0
    else:
        px[..., :3] = dados
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


img_tex = grava("LiveryTex", tex, W, H, False, "sRGB")
img_fac = grava("LiveryFac", np.ones((H, W), np.float32), W, H, True, "Non-Color")
img_nose = grava("NoseMask", nose_mask, NW, NH, False, "Non-Color")
img_pb = grava("PanelBump", pb, W, H, True, "Non-Color")

# religar os nos do shader do casco (uma volta anterior deixou o no do NoseMask
# com image=None e o Cycles pintou o casco inteiro de magenta/escuro)
nt = D.materials["FuselagemPaint"].node_tree
alvo = {"Separate Color": img_nose}
for link in nt.links:
    if link.from_node.type == 'TEX_IMAGE' and link.to_node.name in alvo:
        if link.from_node.image is None:
            link.from_node.image = alvo[link.to_node.name]
            print("[shader] reconectado", link.to_node.name, "->", alvo[link.to_node.name].name)
for n in nt.nodes:
    if n.type == 'TEX_IMAGE' and n.image is None:
        n.image = img_nose
        n.image.colorspace_settings.name = "Non-Color"
        print("[shader] no de imagem orfao religado ao NoseMask")
for n in nt.nodes:
    if n.type == 'TEX_IMAGE':
        print("   [shader]", n.name, "->", n.image.name, n.image.size[:])

# =============================================================== 11. deriva
FX0, FXL, FZ0, FZL = 57.5, 16.5, 1.4, 12.0
fu = (np.arange(FW) + 0.5) / FW
fv = (np.arange(FH) + 0.5) / FH
FX = np.repeat((FX0 + fu * FXL)[None, :], FH, axis=0)
FZ = np.repeat((FZ0 + fv * FZL)[:, None], FW, axis=1)

FB = S["fin_bandas_2026-08-20"]
M_LOW, M_UP = 0.364, 0.403
LB_BOT, LB_TOP = -18.70, -17.73          # z - 0.364x
UB_BOT = -18.05                          # z - 0.403x
FILETE = 0.30
mLE, cLE = 1.0104, 57.996
mTE, cTE = 0.396, 68.254

U_low = FZ - M_LOW * FX
U_up = FZ - M_UP * FX
fin = np.zeros((FH, FW, 3), np.uint8)
fin[:] = INDIGO
fin[U_up >= UB_BOT] = CINZA_VOO                                # banda sup + cap
banda_inf = (U_low >= LB_BOT) & (U_low <= LB_TOP)
fin[banda_inf] = CINZA_VOO


def corte(p, q):
    """>=0 do lado de tras (aft) da reta p->q."""
    (px, pz), (qx, qz) = p, q
    return -((qx - px) * (FZ - pz) - (qz - pz) * (FX - px))


ci = FB["coral_inferior_cantos"]        # [fwd_bot, fwd_top, aft_bot, aft_top]
cs = FB["coral_superior_cantos"]
coral_inf = banda_inf & (corte(ci[0], ci[1]) >= 0) & (corte(ci[2], ci[3]) < 0)
fin[coral_inf] = CORAL
dLE = (FX - (cLE + mLE * FZ)) / math.sqrt(1 + mLE * mLE)
coral_sup = ((U_up >= UB_BOT) & (corte(cs[0], cs[1]) >= 0) &
             (corte(cs[2], cs[3]) < 0) & (dLE >= FILETE))
fin[coral_sup] = CORAL
fin[(dLE >= 0) & (dLE <= FILETE)] = CINZA_VOO                  # filete do BA
fora = (FX < cLE + mLE * FZ) | (FX > cTE + mTE * FZ)
fin[fora] = INDIGO                                             # fora da planform
print(f"[deriva] banda inf {int(banda_inf.sum())} px, coral inf {int(coral_inf.sum())}, "
      f"coral sup {int(coral_sup.sum())}, cinza total {int((fin==np.array(CINZA_VOO)).all(-1).sum())}")


def grava_fin(nome, rgb):
    img = D.images.get(nome)
    if img is None or tuple(img.size) != (FW, FH):
        if img:
            D.images.remove(img)
        img = D.images.new(nome, FW, FH, alpha=False, float_buffer=False)
    px = np.ones((FH, FW, 4), np.float32)
    px[..., :3] = rgb.astype(np.float32) / 255.0
    img.colorspace_settings.name = "sRGB"
    img.pixels.foreach_set(px.ravel())
    img.pack()


grava_fin("FinSashE", fin)
grava_fin("FinSashD", fin)         # mesma arte em (x,z) nos dois lados (PT-MUB)

der = D.objects["Deriva"]
me = der.data
me.materials.clear()
me.materials.append(D.materials["Deriva_Sash_E"])
me.materials.append(D.materials["Deriva_Sash_D"])
uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
for loop in me.loops:
    co = me.vertices[loop.vertex_index].co
    uvl.data[loop.index].uv = ((co.x - FX0) / FXL, (co.z - FZ0) / FZL)
for p in me.polygons:
    p.material_index = 0 if p.center.y < 0 else 1
for mn in ("Deriva_Sash_E", "Deriva_Sash_D"):
    b = next(n for n in D.materials[mn].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Roughness"].default_value = 0.36
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 1.0
        b.inputs["Coat Roughness"].default_value = 0.05
# carenagem dorsal: branca (a cunha so comeca atras dela)
dd = D.objects.get("DerivaDorsal")
if dd:
    dd.data.materials.clear()
    dd.data.materials.append(D.materials["LATAM_Branco"])

bpy.ops.wm.save_mainfile()
print("SALVO", bpy.data.filepath)
