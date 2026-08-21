#!/usr/bin/env python3
"""Para-brisa da familia A320 — a mascara do nariz medida na VISTA FRONTAL.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<pasta>/<X>.blend" \
        --python "airbus A320neo/parabrisa_familia.py" -- [medir|construir]

Este arquivo e o BUILDER DA FAMILIA: A320neo (mestre), A319, A320ceo, A321neo
e A321ceo usam este mesmo codigo e as mesmas cotas.  As cinco aeronaves
compartilham a fuselagem dianteira e o envidracado e IDENTICO nos tres ACAP —
medidos vertice a vertice, A319/A320/A321 concordam dentro de 1,5 mm.

------------------------------------------------------------------------------
O DEFEITO QUE ISTO CORRIGE
------------------------------------------------------------------------------
Ate 2026-08-21 o spec guardava o para-brisa como poligonos em (x, z) —
`parabrisa_lado_esq.no1_frontal` etc. — e o builder os convertia numa FAIXA
que fechava na crista.  Uma faixa em z vira uma faixa em THETA que nunca chega
a theta = 0: medido na propria NoseMask antiga do PT-TMN, o vidro vivia em
|theta| 5,5..69,3 graus e o seu |y| minimo era 0,112 m, enquanto o selo
(canal R) chegava a |theta| 0,06 e |y| 0,001 e FECHAVA ATRAVES do plano de
simetria sobre x 1,40..2,00.  Essa banda preta arqueada e a "cunha preta larga
no topo do para-brisa" do backlog — no lugar dela mora um montante central
estreito, e na familia A320 ele e BRANCO.

A causa e a regra que o 767 escreveu em f2f96cd e que o 777 (22500e6) e o
proprio 767 (d401766) reaprenderam: feature em casco curvo se mede na
superficie desenvolvida, nunca na projecao lateral (x, z), que achata quem
sobe o ombro.

------------------------------------------------------------------------------
O METODO
------------------------------------------------------------------------------
1. As cotas vem da VISTA FRONTAL do ACAP, lida no VETOR (pdftocairo -svg), nao
   no raster: o desenho e CAD e os vertices sao exatos.  A vista frontal e uma
   projecao AO LONGO DE x, entao (|y|, z) sao exatos e so x se perde.
2. Auto-calibracao pela propria secao desenhada: (|y|, z) normalizados pela
   secao do desenho e remultiplicados pela secao verdadeira (3,95 x 4,14 m).
   Isso absorve a anisotropia de 1,05% da prancha (a envergadura de 35,80 m da
   490,09 unidades/m na horizontal e o estabilizador de 12,45 m da 495,26 na
   vertical; a secao desenhada da 489,6 e 494,9 — ou seja, a secao desenhada E
   a secao real, o desenho e que nao e isotropico).
3. A estacao x de cada vertice sai de por o ponto NA SUPERFICIE por raycast ao
   longo de +x contra o casco AVALIADO.  Isso e a propria definicao da
   projecao frontal, e pega de graca a pinca do cockpit, o lobo superior e o
   encolhimento do subsurf.
4. (u, v) do vertice sai da UV do casco por baricentricas na face atingida —
   nao de uma formula reconstruida.  A mascara fica registrada com a pintura
   por construcao.
5. Recuo do desenho (a prancha desenha a ABERTURA, a foto mostra o VIDRO) e
   selo escuro sao AMBOS em METROS DE ARCO na superficie, com o raio LOCAL da
   secao.  Misturar um recuo no plano (|y|,z) com um selo em arco distorceu os
   montantes do 767 em 20-30%; um raio unico em graus deixa o selo ~25% fino
   na crista, que e exatamente onde fica o montante central.
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
MESTRE = os.path.join(BASE, "spec_a320.json")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODO = argv[0] if argv else "construir"

D = bpy.data
PASTA = os.path.dirname(os.path.abspath(bpy.data.filepath))


# --------------------------------------------------------------- spec
def carrega_spec():
    """Cotas do MESTRE, com os desvios do spec local por cima.

    As cotas do envidracado sao unicas na familia (os tres ACAP desenham o
    mesmo desenho dentro de 1,5 mm), entao elas vivem so em spec_a320.json.
    O que PODE variar por matricula e a pintura em volta do vidro: as fotos
    mostram moldura BRANCA em PT-TMN, CC-BFO, PR-TYR e PT-MXP e uma MASCARA
    PRETA no A321neo.  Isso entra como desvio no spec da propria aeronave.
    """
    base = dict(json.load(open(MESTRE))["parabrisa"])
    fonte = os.path.basename(MESTRE)
    for f in sorted(os.listdir(PASTA)):
        if not (f.startswith("spec_") and f.endswith(".json")):
            continue
        if os.path.abspath(os.path.join(PASTA, f)) == os.path.abspath(MESTRE):
            break                       # o proprio mestre: nada a sobrepor
        loc = json.load(open(os.path.join(PASTA, f))).get("parabrisa")
        if not loc:
            continue
        desvios = {k: v for k, v in loc.items()
                   if k not in ("herda_de", "nota") and k in base
                   or k.startswith("mascara") or k.startswith("desvio")}
        if desvios:
            base.update(desvios)
            fonte += " + desvios de " + f
        break
    if "no1_frontal_yz" not in base:
        raise RuntimeError("nenhum spec com as cotas do bloco 'parabrisa'")
    return base, fonte


# ------------------------------------------------------- casco avaliado
FUS = D.objects["Fuselagem"]
_niveis = []
for _m in FUS.modifiers:
    if _m.type == "SUBSURF":
        _niveis.append((_m, _m.levels))
        _m.levels = _m.render_levels          # a mascara e para o RENDER
bpy.context.view_layer.update()
DG = bpy.context.evaluated_depsgraph_get()
FEV = FUS.evaluated_get(DG)
MEV = FEV.to_mesh()
UVL = MEV.uv_layers.active.data
VCO = np.array([v.co[:] for v in MEV.vertices], np.float64)

# escala u do casco: u = x / LUV (medida, nao suposta — 38,0 nas A320, 34,2 na
# A319, 45,0 nas A321)
_xs, _us = [], []
for _p in FUS.data.polygons:
    for _li in _p.loop_indices:
        _xs.append(FUS.data.vertices[FUS.data.loops[_li].vertex_index].co.x)
        _us.append(FUS.data.uv_layers.active.data[_li].uv[0])
_k = np.polyfit(np.array(_xs), np.array(_us), 1)
LUV = 1.0 / _k[0]
print("[parabrisa] LUV = %.4f m (u = x/LUV, residuo %.1e)"
      % (LUV, np.abs(np.polyval(_k, np.array(_xs)) - np.array(_us)).max()))


def uv_na_face(idx, P):
    """(u, v) no ponto P da face idx, por baricentricas (fan de triangulos)."""
    poly = MEV.polygons[idx]
    lis = list(poly.loop_indices)
    vs = [VCO[MEV.loops[l].vertex_index] for l in lis]
    uvs = [np.array(UVL[l].uv[:], np.float64) for l in lis]
    melhor, dmin = None, 1e9
    for k in range(1, len(vs) - 1):
        a, b, c = vs[0], vs[k], vs[k + 1]
        n = np.cross(b - a, c - a)
        nn = float(n @ n)
        if nn < 1e-18:
            continue
        w0 = float(np.cross(c - b, P - b) @ n) / nn
        w1 = float(np.cross(a - c, P - c) @ n) / nn
        w2 = float(np.cross(b - a, P - a) @ n) / nn
        pior = -min(w0, w1, w2)
        if pior < dmin:
            dmin, melhor = pior, w0 * uvs[0] + w1 * uvs[k] + w2 * uvs[k + 1]
        if pior <= 1e-7:
            return melhor
    return melhor


def xt_de_yz(y, z):
    """(|y|, z) -> (x, theta em graus) POR CIMA DA SUPERFICIE.

    Raycast de frente ao longo de +x: o primeiro impacto e exatamente o que a
    vista frontal desenha.  theta sai da UV gravada no casco, nao de uma
    formula: e a UV que a textura usa, entao a mascara registra por
    construcao."""
    r = FEV.ray_cast(Vector((-8.0, float(y), float(z))), Vector((1.0, 0.0, 0.0)))
    if not r[0]:
        raise ValueError("parabrisa: (|y|=%.3f, z=%.3f) nao pousa no casco"
                         % (y, z))
    uv = uv_na_face(r[3], np.array(r[1][:], np.float64))
    return float(r[1].x), (float(uv[1]) - 0.5) * 360.0


# ---- metrica local da superficie: metros de arco por radiano de theta -------
# Um disco fixo em (x, theta) NAO e um disco em metros.  Ao longo do proprio
# para-brisa o raio da secao vai de ~0,9 m a ~1,8 m, entao o mesmo numero de
# graus vale o dobro de arco atras — e um raio unico em graus deixa o selo
# ~25% fino perto da crista, que e onde fica o montante central.
#
# Medido EXATAMENTE, sem supor secao: para cada triangulo da malha avaliada,
# resolve-se dP = du*T + dv*B a partir da propria UV.  |B| e o comprimento
# correspondente a uma volta inteira de theta, logo |B|/(2*pi) = raio local.
def _tabela_raio(x0, x1, nb=24):
    xs, rs = [], []
    amostras = [[] for _ in range(nb)]
    larg = (x1 - x0) / nb
    for poly in MEV.polygons:
        lis = list(poly.loop_indices)
        if len(lis) < 3:
            continue
        v0 = VCO[MEV.loops[lis[0]].vertex_index]
        uv0 = np.array(UVL[lis[0]].uv[:], np.float64)
        xm = v0[0]
        k = int((xm - x0) / larg)
        if k < 0 or k >= nb:
            continue
        if abs((uv0[1] - 0.5) * 360.0) > 110.0:
            continue
        v1 = VCO[MEV.loops[lis[1]].vertex_index]
        v2 = VCO[MEV.loops[lis[2]].vertex_index]
        uv1 = np.array(UVL[lis[1]].uv[:], np.float64)
        uv2 = np.array(UVL[lis[2]].uv[:], np.float64)
        A = np.array([[uv1[0] - uv0[0], uv1[1] - uv0[1]],
                      [uv2[0] - uv0[0], uv2[1] - uv0[1]]])
        det = A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0]
        if abs(det) < 1e-14:
            continue
        E = np.array([v1 - v0, v2 - v0])
        B = (-A[1, 0] * E[0] + A[0, 0] * E[1]) / det     # dP/dv
        amostras[k].append(float(np.linalg.norm(B)) / (2.0 * math.pi))
    for k in range(nb):
        if len(amostras[k]) >= 4:
            xs.append(x0 + (k + 0.5) * larg)
            rs.append(float(np.median(amostras[k])))
    return np.array(xs), np.array(rs)


# ------------------------------------------------------ rasterizador
def fill_tris(tris, x0, x1, t0, t1, nx, nt):
    out = np.zeros((nt, nx), bool)
    if not tris:
        return out
    sx = (x1 - x0) / nx
    st = (t1 - t0) / nt
    T = np.asarray(tris, np.float64)
    P = np.empty_like(T)
    P[..., 0] = (T[..., 0] - x0) / sx - 0.5
    P[..., 1] = (T[..., 1] - t0) / st - 0.5
    for k in range(P.shape[0]):
        a, b, c = P[k]
        i0 = max(0, int(math.floor(min(a[0], b[0], c[0]))))
        i1 = min(nx - 1, int(math.ceil(max(a[0], b[0], c[0]))))
        j0 = max(0, int(math.floor(min(a[1], b[1], c[1]))))
        j1 = min(nt - 1, int(math.ceil(max(a[1], b[1], c[1]))))
        if i1 < i0 or j1 < j0:
            continue
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
        d = ((b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1]))
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (ii - c[0]) + (c[0] - b[0]) * (jj - c[1])) / d
        l2 = ((c[1] - a[1]) * (ii - c[0]) + (a[0] - c[0]) * (jj - c[1])) / d
        l3 = 1.0 - l1 - l2
        out[j0:j1 + 1, i0:i1 + 1] |= (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
    return out


def arredonda(poly, r, n=7):
    """Filete de raio r em cada canto, em (|y|, z), antes do mapeamento."""
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
            q = (1 - s) ** 2 * pa + 2 * (1 - s) * s * p + s ** 2 * pb
            out.append((float(q[0]), float(q[1])))
    return out


def para_xtheta(poly_yz, n=6):
    """(|y|, z) -> (x, theta), densificando: reta em (|y|,z) e curva la."""
    out = []
    m = len(poly_yz)
    for i in range(m):
        y0, z0 = poly_yz[i]
        y1, z1 = poly_yz[(i + 1) % m]
        for k in range(n):
            t = k / n
            out.append(xt_de_yz(y0 + t * (y1 - y0), z0 + t * (z1 - z0)))
    return out


def leque_centro(poly):
    cx = sum(p[0] for p in poly) / len(poly)
    ct = sum(p[1] for p in poly) / len(poly)
    return [[(cx, ct), poly[i], poly[(i + 1) % len(poly)]]
            for i in range(len(poly))]


# ============================================================ MEDIR
def medir_antigo():
    """O que a NoseMask atual do .blend faz, em theta / |y| / x / area."""
    img = D.images.get("NoseMask")
    W, H = img.size
    a = np.array(img.pixels[:], np.float32).reshape(H, W, 4)
    ux = np.array([UVL[l].uv[0] for l in range(len(MEV.loops))])
    uy = np.array([UVL[l].uv[1] for l in range(len(MEV.loops))])
    vi = np.array([MEV.loops[l].vertex_index for l in range(len(MEV.loops))])
    P = VCO[vi]
    ix = np.clip((ux * W).astype(int), 0, W - 1)
    iy = np.clip((uy * H).astype(int), 0, H - 1)
    for canal, nome in ((0, "moldura/selo (R)"), (1, "vidro (G)")):
        m = a[iy, ix, canal] > 0.5
        if not m.any():
            print("[antigo] %s: vazio" % nome)
            continue
        th = (uy[m] - 0.5) * 360.0
        print("[antigo] %-17s x %.3f..%.3f  |theta| %.1f..%.1f  |y| %.3f..%.3f"
              % (nome, (ux[m] * LUV).min(), (ux[m] * LUV).max(),
                 np.abs(th).min(), np.abs(th).max(),
                 np.abs(P[m][:, 1]).min(), np.abs(P[m][:, 1]).max()))
    # a moldura fecha sobre a crista?
    m = a[iy, ix, 0] > 0.5
    xr = ux[m] * LUV
    tr = np.abs((uy[m] - 0.5) * 360.0)
    for lo in np.arange(1.2, 3.6, 0.2):
        s = (xr >= lo) & (xr < lo + 0.2)
        if s.any():
            print("      x %.1f..%.1f: |theta| minimo do selo = %.2f graus"
                  % (lo, lo + 0.2, tr[s].min()))
    # area de vidro
    g = a[iy, ix, 1] > 0.5
    if g.any():
        print("[antigo] vidro toca %d loops de %d" % (g.sum(), len(g)))


# ============================================================ CONSTRUIR
def construir():
    PB, arq = carrega_spec()
    print("[parabrisa] cotas de %s" % arq)
    PANES = [[list(p) for p in PB["no1_frontal_yz"]],
             [list(p) for p in PB["no2_deslizante_yz"]],
             [list(p) for p in PB["no3_kick_yz"]]]
    SELO = PB.get("mascara_preta_m") or PB["selo_m"]
    if PB.get("mascara_preta_m"):
        print("[parabrisa] MASCARA PRETA de %.3f m (desvio desta matricula)" % SELO)
    FOLGA = PB["folga_desenho_m"]
    FIL = PB["filete_canto_m"]
    MC_Y = PB["montante_central_meia_largura"]
    DZ = PB.get("desloca_z_m", 0.0)
    EZ = PB.get("estica_z", 1.0)
    EZC = PB.get("estica_z_centro", 0.0)

    # A vista frontal e a vista lateral da mesma prancha discordam em z (ver
    # spec).  A correcao e uma afim em z SO — |y| continua vindo da frontal,
    # que e a unica que ve y.
    for p in PANES:
        for v in p:
            v[1] = EZC + (v[1] - EZC) * EZ + DZ

    # A borda interna do No.1 vai para MC_Y - FOLGA para que o recuo em arco a
    # deixe exatamente em MC_Y: perto do plano de simetria o arco corre
    # praticamente ao longo de y, entao a conta fecha em metros.
    _int = PB["indices_borda_interna_no1"]
    for _v in _int:
        PANES[0][_v][0] = MC_Y - FOLGA

    PXT = [para_xtheta(arredonda(p, FIL), n=6) for p in PANES]
    allx = [q[0] for pn in PXT for q in pn]
    allt = [q[1] for pn in PXT for q in pn]
    for nome, pn in zip(("No.1 frontal", "No.2 deslizante", "No.3 kick"), PXT):
        xs = [q[0] for q in pn]
        ts = [q[1] for q in pn]
        print("[parabrisa] %-16s x %.3f..%.3f  theta %.1f..%.1f graus"
              % (nome, min(xs), max(xs), min(ts), max(ts)))
    print("[parabrisa] envidracado inteiro: x %.3f..%.3f  theta %.1f..%.1f"
          % (min(allx), max(allx), min(allt), max(allt)))

    # Nao ha zona morta no montante central, e isto e deliberado: na A320 o
    # poste entre os dois No.1 e PRETO (faz parte da moldura), ao contrario do
    # 767, cuja moldura e branca e exigia furar o selo no plano de simetria.
    # Aqui o selo dos dois lados se encontra e forma o poste sozinho, com a
    # largura 2*montante_central_meia_largura que o desenho da.  O que NAO
    # pode acontecer — e nao acontece, porque o selo e uma dilatacao LIMITADA
    # do vidro — e a faixa preta continuar sobre a crista onde nao ha vidro
    # nenhum: era isso a "cunha preta" do backlog.

    # --- grades -----------------------------------------------------------
    # O trabalho pesado acontece num espaco METRICO (x, w), onde
    #     w = theta_radianos * raio_local(x)
    # e o comprimento de ARCO ao longo da secao.  Nesse espaco a distancia e
    # euclidiana e o recuo e o selo viram OFFSETS DE POLIGONO analiticos, sem
    # morfologia nenhuma.
    #
    # POR QUE NAO MORFOLOGIA.  A primeira versao desta correcao dilatava a
    # mascara na grade (x, theta) por faixas de x, cada faixa com o seu raio —
    # a receita do 767.  La o selo tem 0,018 m e passa; aqui ele tem 0,085 m
    # (a moldura da A320 e uma faixa PRETA larga, nao um fio prateado), e a
    # 0,085 m os degraus entre faixas e as faces planas do octogono viram
    # serrilha grossa: no primeiro render as bordas dos seis vidros sairam
    # rasgadas.  Offset de poligono nao tem faixa, nao tem octogono e nao tem
    # degrau.
    NW, NH = 8192, 2048          # a NoseMask tem resolucao PROPRIA
    nose = np.zeros((NH, NW, 3), np.float32)
    PX0, PX1 = min(allx) - 0.35, max(allx) + 0.35
    PT0, PT1 = 0.0, max(allt) + 9.0
    RX, RR = _tabela_raio(PX0, PX1)
    print("[parabrisa] raio local da secao: %.3f m em x=%.2f -> %.3f m em x=%.2f"
          % (RR[0], RX[0], RR[-1], RX[-1]))

    def raio(x):
        return np.interp(np.asarray(x, float), RX, RR)

    def para_w(pn):
        return [(x, math.radians(t) * float(raio(x))) for x, t in pn]

    PXW = [para_w(pn) for pn in PXT]

    # Largura REAL dos montantes, medida na superficie desenvolvida (x, w).
    # Nao da para le-la na vista frontal: No.2 e No.3 estao lado a lado ao
    # longo de x, e a vista frontal projeta x fora.  O "vao" que ela mostra
    # mistura a largura do montante com a curvatura da secao.
    for _a, _b, _nome in ((0, 1, "No.1/No.2"), (1, 2, "No.2/No.3")):
        A = np.array(PXW[_a]); B = np.array(PXW[_b])
        dmin = float(np.min(np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2)))
        print("[parabrisa] montante %s: %.4f m de abertura a abertura na "
              "superficie (vidro a vidro %.4f)" % (_nome, dmin, dmin + 2 * FOLGA))
    CEL = 0.0012                                  # metros por celula
    WMAX = math.radians(PT1) * float(RR.max())
    W0, W1 = -0.22, WMAX
    npx = int(round((PX1 - PX0) / CEL))
    npw = int(round((W1 - W0) / CEL))
    sx_m = (PX1 - PX0) / npx
    sw_m = (W1 - W0) / npw

    def banda(poly, d):
        """Pontos a menos de `d` da FRONTEIRA do poligono, em metros.

        Uniao de retangulos de largura 2d sobre cada aresta com discos de raio
        d em cada vertice — exato, isotropico e sem passo de grade.  Com ela:
            vidro = interior MENOS banda(d=recuo)   (erosao)
            selo  = interior UNIAO banda(d=selo)    (dilatacao)
        """
        tris = []
        m = len(poly)
        for i in range(m):
            a = np.array(poly[i], float)
            b = np.array(poly[(i + 1) % m], float)
            e = b - a
            L = float(np.hypot(*e))
            if L < 1e-12:
                continue
            n = np.array([-e[1], e[0]]) / L * d
            p1, p2, p3, p4 = a + n, b + n, b - n, a - n
            tris.append([tuple(p1), tuple(p2), tuple(p3)])
            tris.append([tuple(p1), tuple(p3), tuple(p4)])
            NA = 14
            for k in range(NA):
                t0 = 2 * math.pi * k / NA
                t1 = 2 * math.pi * (k + 1) / NA
                tris.append([tuple(a),
                             (a[0] + d * math.cos(t0), a[1] + d * math.sin(t0)),
                             (a[0] + d * math.cos(t1), a[1] + d * math.sin(t1))])
        return fill_tris(tris, PX0, PX1, W0, W1, npx, npw)

    vidro = np.zeros((npw, npx), bool)
    selo = np.zeros((npw, npx), bool)
    for pw in PXW:
        dentro = fill_tris(leque_centro(pw), PX0, PX1, W0, W1, npx, npw)
        vidro |= dentro & ~banda(pw, FOLGA)
        # O selo MANTEM o vidro dentro dele.  Como anel puro, o texel de borda
        # ficaria com R=0,5 e G=0,5 e o shader — Mix(tinta, selo, R) e depois
        # Mix(., vidro, G) — deixaria ~25% de TINTA passar entre vidro e selo:
        # um fio branco contornando cada painel (bug documentado no 767).
        selo |= dentro | banda(pw, SELO)

    # A mascara e lida em |theta|, entao o outro bordo e o espelho deste.  Perto
    # do plano de simetria o selo de um lado passa para w < 0: dobra-se de volta
    # para que o poste central saia com a largura certa e sem costura.
    j0 = int(round((0.0 - W0) / sw_m))
    for M in (vidro, selo):
        n = min(j0, npw - j0)
        M[j0:j0 + n] |= M[j0 - n:j0][::-1]

    nuu = (np.arange(NW) + 0.5) / NW * LUV
    nvv = (np.arange(NH) + 0.5) / NH
    NGX = np.repeat(nuu[None, :], NH, axis=0)
    NGD = np.abs(np.repeat(((nvv - 0.5) * 360.0)[:, None], NW, axis=1))
    NGW = np.radians(NGD) * raio(NGX)
    dx_tex = LUV / NW
    dw_tex = np.radians(360.0 / NH) * raio(NGX)

    def pinta(arr, canal):
        """Cobertura EXATA do texel por imagem integral (sem supersample).

        O supersample 4x4 que a receita antiga usava media 16 amostras de uma
        celula que cobre dezenas da grade fina: o ruido de cobertura desenhava
        um dente de serra na borda quase horizontal do selo.
        """
        I = np.zeros((npw + 1, npx + 1), np.float64)
        I[1:, 1:] = np.cumsum(np.cumsum(arr.astype(np.float64), 0), 1)
        sel = ((NGX >= PX0 + sx_m) & (NGX <= PX1 - sx_m)
               & (NGW >= W0 + sw_m) & (NGW <= W1 - sw_m))
        r, c = np.where(sel)
        i0 = np.clip(np.round((NGX[sel] - 0.5 * dx_tex - PX0) / sx_m).astype(int), 0, npx)
        i1 = np.clip(np.round((NGX[sel] + 0.5 * dx_tex - PX0) / sx_m).astype(int), 0, npx)
        j0 = np.clip(np.round((NGW[sel] - 0.5 * dw_tex[sel] - W0) / sw_m).astype(int), 0, npw)
        j1 = np.clip(np.round((NGW[sel] + 0.5 * dw_tex[sel] - W0) / sw_m).astype(int), 0, npw)
        i1 = np.maximum(i1, i0 + 1)
        j1 = np.maximum(j1, j0 + 1)
        s = I[j1, i1] - I[j0, i1] - I[j1, i0] + I[j0, i0]
        nose[r, c, canal] = np.maximum(nose[r, c, canal],
                                       (s / ((i1 - i0) * (j1 - j0))).astype(np.float32))

    pinta(selo, 0)
    pinta(vidro, 1)

    jj, ii = np.where(vidro)
    area = float(len(ii)) * sx_m * sw_m * 2.0        # os dois bordos
    print("[parabrisa] area de vidro na superficie: %.3f m2 (os 6 vidros)" % area)

    def _theta_min(M):
        j, i = np.where(M)
        w = W0 + (j + 0.5) * sw_m
        x = PX0 + (i + 0.5) * sx_m
        return float(np.degrees(np.min(np.abs(w) / raio(x))))

    print("[parabrisa] |theta| minimo do VIDRO: %.2f graus  (|y| minimo %.3f m)"
          % (_theta_min(vidro),
             float(np.min(np.abs(W0 + (jj + 0.5) * sw_m)))))
    print("[parabrisa] |theta| minimo do SELO : %.2f graus" % _theta_min(selo))

    img = D.images.get("NoseMask")
    if img is None or tuple(img.size) != (NW, NH):
        if img:
            D.images.remove(img)
        img = D.images.new("NoseMask", NW, NH, alpha=False, float_buffer=False)
    px = np.ones((NH, NW, 4), np.float32)
    px[..., :3] = nose
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(px.ravel())
    img.pack()
    print("[parabrisa] NoseMask %dx%d: selo %.0f / vidro %.0f texels"
          % (NW, NH, float(nose[..., 0].sum()), float(nose[..., 1].sum())))

    # Religar o no de imagem.  ATENCAO: identidade de no NAO funciona no RNA do
    # Blender — `l.from_node is no` e SEMPRE falso, cada acesso devolve um
    # wrapper novo.  Comparar por NOME.  Com o no orfao o Separate Color
    # devolve zero e o nariz INTEIRO renderiza no material do selo.
    nt = D.materials["FuselagemPaint"].node_tree
    sep = next((n for n in nt.nodes if n.type == "SEPARATE_COLOR"), None)
    alvo = None
    if sep is not None:
        for l in nt.links:
            if l.to_node.name == sep.name and l.from_node.type == "TEX_IMAGE":
                alvo = nt.nodes[l.from_node.name]
                break
    if alvo is None:
        raise RuntimeError("parabrisa: no de imagem da NoseMask nao encontrado")
    alvo.image = img
    alvo.image.colorspace_settings.name = "Non-Color"
    alvo.interpolation = "Cubic"
    print("[parabrisa] no '%s' religado a NoseMask %dx%d" % (alvo.name, NW, NH))

    # Vidro: o mesmo lobo especular que fez um painel do 767 renderizar CLARO
    # existe aqui em escala menor.  Parametros do 767 pos-d401766.
    vm = PB.get("vidro_bsdf")
    if vm:
        b = nt.nodes.get("Principled BSDF.002")
        if b is not None:
            b.inputs["Roughness"].default_value = vm["roughness"]
            b.inputs["Coat Weight"].default_value = vm["coat"]
            b.inputs["Coat Roughness"].default_value = vm["coat_roughness"]
            print("[parabrisa] vidro: rough %.2f coat %.2f coat_rough %.2f"
                  % (vm["roughness"], vm["coat"], vm["coat_roughness"]))


if MODO == "medir":
    medir_antigo()
else:
    construir()

FEV.to_mesh_clear()
for _m, _lv in _niveis:
    _m.levels = _lv
if MODO != "medir":
    bpy.ops.wm.save_mainfile()
    print("[parabrisa] blend salvo: %s" % bpy.data.filepath)
print("[parabrisa] FIM")
