#!/usr/bin/env python3
"""Arte do nariz do 787 — para-brisa e junta do radome — para o -9 E para o -8.

O nariz do 787-8 e o do 787-9 sao IDENTICOS em metros (spec_788.json ->
herdado_do_787_9_sem_alteracao/nariz), entao este arquivo constroi os dois: so
muda o comprimento de referencia do UV (L_UV) e o .blend de destino.

------------------------------------------------------------------------------
COMO RODAR (os tres passos, para cada aeronave)
------------------------------------------------------------------------------
    B=/Applications/Blender.app/Contents/MacOS/Blender
    $B -b "boeing 787-9/B789_LATAM.blend" --python "boeing 787-9/nose_art.py" -- export /tmp/na9
    python3 "boeing 787-9/nose_art.py" build /tmp/na9 63.5
    $B -b "boeing 787-9/B789_LATAM.blend" --python "boeing 787-9/nose_art.py" -- apply /tmp/na9

O passo do meio roda FORA do Blender porque precisa de scipy (KD-tree), que o
Python do Blender 5.2 nao traz. Os tres passos sao idempotentes.

------------------------------------------------------------------------------
O DEFEITO QUE ISTO CORRIGE (medido, 2026-08-21)
------------------------------------------------------------------------------
1. O MONTANTE ERA PINTADO INTEIRO DE ESCURO. No 787 o montante e pintado na
   COR DO CASCO, com um selo escuro de cada lado; head-on ve-se uma MANCHA
   ESCURA por vidro e uma FRESTA CLARA entre elas. A mascara antiga nao tinha
   fresta nenhuma: pintava 0.230 m (central) e 0.181 m (do meio) de preto
   corrido. Era isso que lia como "barras pretas largas" — nao um vidro fora
   de lugar, uma fresta que nao existia.

   Medido em duas fotos head-on de licenca livre, com a FRESTA normalizada
   pela meia-largura da MANCHA (a unica normalizacao imune a escala, lente e
   distancia):

       fresta central  0.0733 (A7-BCC)  0.0747 (N805AN)  -> 0.0740 x Ymancha
       fresta do meio  0.0477 (A7-BCC)  0.0517 (N805AN)  -> 0.0497 x Ymancha
       centro do meio  0.564  (A7-BCC)  0.582  (N805AN)  -> 0.573  x Ymancha

   As duas fotos tem lente, distancia e elevacao diferentes e concordam em 2%
   e 8% — e o que da confianca na normalizacao.

2. MONTANTES RASGADOS. As barras tinham pontas em zigue-zague porque o vao
   entre dois poligonos era preenchido por dilatacao do selo, e onde as arestas
   nao sao paralelas a dilatacao deixa farpas. Aqui os vidros sao o envelope do
   envidracado MENOS duas faixas de |y|, e o selo e uma distancia 3D constante
   ao redor de cada vidro: as duas larguras sao exatas por construcao e nao ha
   como sobrar farpa.

3. MONTANTE CENTRAL FORA DO PLANO DE SIMETRIA. A mascara antiga era simetrica
   em torno de v = 0.5 da textura. Mas a CRISTA do casco nao esta em v = 0.5:
   o vertice da crista da gaiola carrega v = 0.50712 e o da quilha 0.99288
   (todos os outros estao exatamente em i/32). Na superficie avaliada a crista
   cai em v = 0.5044. Resultado: o montante central saia 0.045 m deslocado para
   bombordo, partido ao meio por uma fresta de casco BRANCO de 0.018 m — os
   "dois montantes com um vao branco" que o head-on mostrava.
   Aqui nada e desenhado em (x, v): cada texel e testado pela sua PROPRIA
   posicao 3D na malha avaliada, entao o defeito de UV nao pode se propagar.

4. SELO DE UM TEXEL E MASCARA BINARIA. A NoseMask tinha a resolucao do casco
   (4096x1024) e valores 0/1: o contorno do vidro virava uma linha de um texel
   que o shader lia a meio termo (cinza claro) e a borda serrilhava. Agora a
   NoseMask tem 8192x2048 e cobertura por supersample 4x4.

5. JUNTA DO RADOME — o backlog dizia "circulo desenhado na face frontal". NAO
   E. A linha ja estava numa ESTACAO de fuselagem: medida na textura antiga ela
   vai de x=1.109 na crista a x=1.389 na quilha, e a vista lateral do APR
   D6-58333 p.2-6 (600 dpi, calibrada pela altura de fuselagem 5.94 m ->
   49.16 px/m, ponta do nariz em col 865) da 1.078 e 1.403. Head-on, uma anilha
   nessa estacao PROJETA um oval fechado dentro da silhueta — e a vista frontal
   do proprio APR desenha esse oval, e as tres fotos head-on tambem. O que
   estava ruim era o traco: 0.039 m de cinza chapado, com degrau, sem relevo.
   Aqui a anilha e re-derivada como o corte do plano x + 0.1118 z = 1.1309,
   desenhada com 0.026 m e supersample, e ganha um sulco no PanelBump.

------------------------------------------------------------------------------
FONTES
------------------------------------------------------------------------------
- Boeing 787 APR D6-58333 Rev P, p.2-6 (2.2.2 General Dimensions: Model 787-9),
  imagem embutida 1208x1708 (201 dpi nativos), rasterizada a 600 dpi.
  Vista lateral: estacao da junta do radome. Vista superior: meia-largura do
  nariz (confere o casco em 1.3%). Vista frontal: envidracado e oval do radome.
- Fotos head-on CC BY / CC BY-SA, creditadas em refs/manifest.json:
  A7-BCC (Bene Riobo, CC BY-SA 4.0) e N805AN (Eric Salard, CC BY-SA 2.0).

------------------------------------------------------------------------------
O QUE FICOU EM ABERTO
------------------------------------------------------------------------------
A razao meia-largura-do-oval-do-radome / meia-largura-do-envidracado vale 0.770
no modelo, 0.697 na vista frontal do APR, 0.673 na A7-BCC e 0.835 na N805AN. As
duas fotos discordam em 22% (a N805AN e tirada de CIMA do para-brisa, o que
encurta o vidro externo justo onde ele sobe o ombro), entao YMAX nao foi mexido.
Se aparecer uma head-on na altura do olho com nariz claro, remedir: o APR e a
melhor foto apontam para um envidracado ~10% mais largo. O casco NAO e suspeito
(a vista superior do APR confere a meia-largura do nariz em 1.3%).
"""
import math
import os
import sys

import numpy as np

# ---------------------------------------------------------------- constantes

# Envidracado — poligonos herdados de spec_b789.json/parabrisa_4_vidros, que
# vieram da VISTA FRONTAL do APR. So os MONTANTES foram remedidos.
YMAX = 1.500                 # meia-largura do envidracado, |y| maximo
PANE_IN = [(0.215, 0.355), (0.576, 0.355), (0.837, 0.44), (0.837, 0.80),
           (0.777, 0.885), (0.416, 0.885), (0.115, 0.80), (0.115, 0.44)]
PANE_OUT = [(1.219, 0.355), (1.480, 0.355), (1.500, 0.44), (1.500, 0.52),
            (1.159, 0.84), (1.118, 0.885), (1.038, 0.885), (1.018, 0.56),
            (1.078, 0.44)]

# O QUE A FOTO MEDE. Head-on, vidro e selo sao ambos ESCUROS e nao se separam:
# o que se ve e uma MANCHA ESCURA por vidro e uma FRESTA CLARA entre elas — o
# montante, que no 787 e pintado na cor do casco. Entao o que se mede na foto e
#   * a meia-largura da mancha escura   (vidro + selo)  -> YDARK
#   * a largura da fresta CLARA         (montante - 2 selos)
# e e assim que as constantes abaixo estao normalizadas. Pintar o montante
# INTEIRO de escuro, como a mascara antiga fazia, e o que produzia as "barras
# pretas largas": a fresta clara simplesmente nao existia.
SEAL = 0.030                 # selo escuro em volta de cada vidro, em METROS DE
                             # SUPERFICIE (distancia 3D, nao offset em (|y|,z))
YDARK = YMAX + SEAL          # meia-largura da mancha escura = 1.530

F_CENTRE = 0.0740            # x YDARK -> fresta clara no montante central
F_MID = 0.0497               # x YDARK -> fresta clara no montante do meio
F_MID_C = 0.573              # x YDARK -> centro do montante do meio

W_CENTRE = F_CENTRE * YDARK + 2 * SEAL   # 0.1732 m: montante ESTRUTURAL
W_MID = F_MID * YDARK + 2 * SEAL         # 0.1360 m
C_MID = F_MID_C * YDARK                  # 0.8767 m
R_ROUND = 0.055              # filete dos cantos convexos
R_FILL = 0.030               # filete dos cantos concavos (< W_MID/2 = 0.0373,
                             # senao o fechamento engoliria o montante do meio)

# Junta do radome: plano  x + K_RADOME * z = X0_RADOME
K_RADOME = 0.1118
X0_RADOME = 1.1309
W_RADOME = 0.026             # largura do traco na pele, em metros
X_RADOME_MAX = 3.0           # so o nariz

SS = 4                       # supersample por eixo


# ------------------------------------------------------------------- comuns

def _log(*a):
    print("[nose_art]", *a)


# =========================================================== 1. EXPORT (Blender)

def export(outdir):
    import bpy
    os.makedirs(outdir, exist_ok=True)
    fus = bpy.data.objects["Fuselagem"]
    dg = bpy.context.evaluated_depsgraph_get()
    ev = fus.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    uvl = me.uv_layers.active.data
    M = ev.matrix_world
    tu, tx = [], []
    for t in me.loop_triangles:
        tu.append([tuple(uvl[li].uv) for li in t.loops])
        tx.append([tuple(M @ me.vertices[vi].co) for vi in t.vertices])
    ev.to_mesh_clear()
    np.save(os.path.join(outdir, "tris_uv.npy"), np.array(tu, np.float64))
    np.save(os.path.join(outdir, "tris_xyz.npy"), np.array(tx, np.float64))

    for nome in ("LiveryTex", "PanelBump", "NoseMask"):
        img = bpy.data.images[nome]
        w, h = img.size
        buf = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(buf)
        np.save(os.path.join(outdir, "%s.npy" % nome), buf.reshape(h, w, 4))
        _log("exportado", nome, (w, h))
    _log("triangulos avaliados:", len(tu))


# ============================================================ 2. BUILD (python3)

def _raster_poly(poly, Y0, Y1, Z0, Z1, ny, nz):
    """Rasteriza um poligono (|y|,z) numa grade booleana."""
    ys = (np.arange(ny) + 0.5) / ny * (Y1 - Y0) + Y0
    zs = (np.arange(nz) + 0.5) / nz * (Z1 - Z0) + Z0
    Y, Z = np.meshgrid(ys, zs)
    inside = np.zeros(Y.shape, bool)
    n = len(poly)
    for i in range(n):
        y0, z0 = poly[i]
        y1, z1 = poly[(i + 1) % n]
        cond = ((z0 > Z) != (z1 > Z))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (y1 - y0) * (Z - z0) / (z1 - z0) + y0
        inside ^= cond & (Y < xint)
    return inside


def _morph(mask, r_px, mode):
    """Erosao/dilatacao binaria por DISCO EXATO via transformada de distancia.

    Com raio de 110 celulas, um elemento estruturante 221x221 custaria 3e11
    operacoes e trava. A EDT da o mesmo resultado em O(N): dilatar por r e
    "distancia ao objeto <= r"; erodir por r e "distancia ao fundo >= r".
    """
    from scipy.ndimage import distance_transform_edt
    if mode == "d":
        return distance_transform_edt(~mask) <= r_px
    return distance_transform_edt(mask) > r_px


def _band_from_panes():
    """Contorno superior/inferior do ENVIDRACADO inteiro em funcao de |y|.

    A uniao dos dois vidros medidos, com os vaos (montantes originais) ligados
    por reta e o extremo interno estendido ate a linha de centro. E dele que
    saem os vidros novos, recortados pelos montantes MEDIDOS NA FOTO.
    """
    def extent(poly, ys):
        """z minimo e maximo do poligono em cada |y| (varredura de arestas).

        Nao tenta adivinhar qual metade do contorno e "de cima": os dois vidros
        do 787 tem cantos que quebram qualquer heuristica de ordenacao. Aqui a
        linha vertical em |y| corta o poligono e as raizes dao o intervalo.
        """
        zlo = np.full_like(ys, np.nan)
        zhi = np.full_like(ys, np.nan)
        n = len(poly)
        for i in range(n):
            y0, z0 = poly[i]
            y1, z1 = poly[(i + 1) % n]
            if y0 == y1:
                m = np.isclose(ys, y0)
                cand = np.where(m, min(z0, z1), np.nan)
                cand2 = np.where(m, max(z0, z1), np.nan)
            else:
                t = (ys - y0) / (y1 - y0)
                m = (t >= 0.0) & (t <= 1.0)
                cand = np.where(m, z0 + t * (z1 - z0), np.nan)
                cand2 = cand
            zlo = np.fmin(zlo, cand)
            zhi = np.fmax(zhi, cand2)
        return zlo, zhi

    ys = np.linspace(0.0, YMAX, 3001)
    zb = np.full_like(ys, np.nan)
    zt = np.full_like(ys, np.nan)
    for poly in (PANE_IN, PANE_OUT):
        lo, hi = extent(poly, ys)
        zb = np.fmin(zb, lo)
        zt = np.fmax(zt, hi)
    # O vao entre os dois vidros medidos tem de ser PONTE explicita: ali os
    # poligonos nao se tocam e, pior, o vidro externo comeca num VERTICE unico
    # em |y|=1.018, onde a varredura devolve altura ~0. Um limiar de altura
    # sozinho nao resolve (o mesmo limiar que descarta o vertice descartaria a
    # ponta legitima do vidro externo, que tambem afina).
    ok = np.isfinite(zb) & np.isfinite(zt) & ((zt - zb) > 0.02)
    ok &= ~((ys > 0.84) & (ys < 1.055))
    idx = np.where(ok)[0]
    zb = np.interp(ys, ys[idx], zb[idx])
    zt = np.interp(ys, ys[idx], zt[idx])
    # extremidade interna: prolongar a inclinacao dos primeiros 30 mm ate |y|=0
    i0 = idx[0]
    if i0 > 0:
        j = i0 + 60
        for arr in (zb, zt):
            slope = (arr[j] - arr[i0]) / (ys[j] - ys[i0])
            arr[:i0] = arr[i0] + slope * (ys[:i0] - ys[i0])
    # alisar os joelhos que a ponte deixa (media movel de ~20 mm)
    k = np.ones(41) / 41.0
    for arr in (zb, zt):
        arr[:] = np.convolve(np.pad(arr, 20, mode="edge"), k, mode="valid")
    return ys, zb, zt


def build(outdir, L_UV):
    from scipy.spatial import cKDTree
    tu = np.load(os.path.join(outdir, "tris_uv.npy"))
    tx = np.load(os.path.join(outdir, "tris_xyz.npy"))
    nose = np.load(os.path.join(outdir, "NoseMask.npy"))
    lt = np.load(os.path.join(outdir, "LiveryTex.npy"))
    H0, W0 = nose.shape[:2]
    NW, NH = W0 * 2, H0 * 2                   # NoseMask com o dobro da resolucao
    _log("NoseMask %dx%d -> %dx%d ; L_UV=%.2f" % (W0, H0, NW, NH, L_UV))

    # ------------------------------------------------------------ (y,z) raster
    # A grade e SIMETRICA em y (nao |y|): o montante central e uma faixa
    # INTERNA e as operacoes morfologicas precisam de vidro dos dois lados
    # dela. Numa grade em |y| a faixa encostaria na borda do array e o
    # fechamento a comeria.
    Y0, Y1, Z0, Z1 = -1.70, 1.70, 0.20, 1.05
    ny, nz = 6800, 1700                        # 0.5 mm por celula
    dy = (Y1 - Y0) / ny
    ys, zb, zt = _band_from_panes()

    yy = (np.arange(ny) + 0.5) / ny * (Y1 - Y0) + Y0
    zz = (np.arange(nz) + 0.5) / nz * (Z1 - Z0) + Z0
    ay = np.abs(yy)
    ZB = np.interp(ay, ys, zb, left=np.nan, right=np.nan)
    ZT = np.interp(ay, ys, zt, left=np.nan, right=np.nan)
    ZB[ay > YMAX] = np.nan
    band = ((zz[:, None] >= ZB[None, :]) & (zz[:, None] <= ZT[None, :])
            & np.isfinite(ZB)[None, :])

    strip_c = ay <= W_CENTRE / 2.0
    strip_m = np.abs(ay - C_MID) <= W_MID / 2.0
    r1 = R_ROUND / dy
    r2 = R_FILL / dy
    band = _morph(_morph(band, r1, "e"), r1, "d")          # borda externa lisa
    panes = band & ~strip_c[None, :] & ~strip_m[None, :]
    panes = _morph(_morph(panes, r1, "e"), r1, "d")        # cantos convexos
    panes = _morph(_morph(panes, r2, "d"), r2, "e")        # cantos concavos
    posts = band & ~panes
    _log("(y,z): vidro %d celulas, montantes %d celulas"
         % (int(panes.sum()), int(posts.sum())))

    def lookup(mask, y, z):
        iy = np.clip(((y - Y0) / (Y1 - Y0) * ny).astype(np.int32), 0, ny - 1)
        iz = np.clip(((z - Z0) / (Z1 - Z0) * nz).astype(np.int32), 0, nz - 1)
        okk = (y >= Y0) & (y < Y1) & (z >= Z0) & (z < Z1)
        out = np.zeros(y.shape, bool)
        out[okk] = mask[iz[okk], iy[okk]]
        return out

    # ------------------------------------------------- janela de texels do vidro
    xa, xb = 1.00, 3.20                        # gate longitudinal do envidracado
    c0 = max(0, int(xa / L_UV * NW) - 40)
    c1 = min(NW, int(xb / L_UV * NW) + 40)
    r0, r1_ = int(0.28 * NH), int(0.72 * NH)
    _log("janela do para-brisa: cols %d..%d  rows %d..%d" % (c0, c1, r0, r1_))
    P = _sample(tu, tx, c0, c1, r0, r1_, NW, NH, SS)      # (nr*SS, nc*SS, 3)
    PX, PY, PZ = P[..., 0], P[..., 1], P[..., 2]
    ok = np.isfinite(PX) & (PX >= 0.5) & (PX <= 4.5)
    YS = np.where(ok, PY, -9.0)
    ZZ = np.where(ok, PZ, -9.0)
    g_ss = lookup(panes, YS, ZZ) & ok

    # Selo: distancia 3D REAL ate o contorno do vidro, na superficie. NAO um
    # offset no plano (|y|,z) — no nariz um mesmo offset em z vale muito mais
    # arco do que o mesmo offset em y, e foi misturar os dois que distorceu os
    # montantes do 767 em 20-30%.
    bnd = g_ss & ~_shrink(g_ss)
    pts = np.stack([PX[bnd], PY[bnd], PZ[bnd]], 1)
    _log("pontos de contorno do vidro: %d" % len(pts))
    tree = cKDTree(pts)
    cand = ok & ~g_ss
    q = np.stack([PX[cand], PY[cand], PZ[cand]], 1)
    d, _ = tree.query(q, workers=-1)
    seal_ss = np.zeros(g_ss.shape, bool)
    seal_ss[cand] = d <= SEAL

    # O MONTANTE NAO E PINTADO: fica na cor do casco, com o selo escuro de cada
    # lado. Por isso o canal R leva SO o selo; a fresta clara entre dois vidros
    # sai sozinha, com largura = montante estrutural - 2 selos.
    frame_ss = seal_ss
    nc = c1 - c0
    nr = r1_ - r0
    glass = g_ss.reshape(nr, SS, nc, SS).mean((1, 3))
    frame = frame_ss.reshape(nr, SS, nc, SS).mean((1, 3))
    frame = np.minimum(frame, 1.0 - glass)

    nm = np.zeros((NH, NW, 3), np.float32)
    nm[r0:r1_, c0:c1, 0] = frame
    nm[r0:r1_, c0:c1, 1] = glass
    np.save(os.path.join(outdir, "NoseMask_new.npy"), nm)

    # ---------------------------------------------------------- medidas do vidro
    rep = _medir(PX, PY, PZ, g_ss, frame_ss, ok)
    rep["NoseMask"] = [NW, NH]

    # ------------------------------------------------------ junta do radome
    lw, lh = lt.shape[1], lt.shape[0]
    lc1 = int(1.9 / L_UV * lw) + 6
    Pr = _sample(tu, tx, 0, lc1, 0, lh, lw, lh, SS)
    RX, RZ = Pr[..., 0], Pr[..., 2]
    okr = np.isfinite(RX)
    f = np.where(okr, RX + K_RADOME * RZ - X0_RADOME, 99.0)
    dist = np.abs(f) / math.sqrt(1.0 + K_RADOME * K_RADOME)
    line_ss = (dist <= W_RADOME / 2.0) & okr & (RX <= X_RADOME_MAX)
    fwd_ss = (f < 0.0) & okr
    cov = line_ss.reshape(lh, SS, lc1, SS).mean((1, 3))
    fwd = fwd_ss.reshape(lh, SS, lc1, SS).mean((1, 3))

    # duas tintas ja existentes: radome (a vante) e casco (a re)
    col_rad = np.array([0.969, 0.976, 0.980], np.float32)
    col_hull = lt[lh // 2, int(2.6 / L_UV * lw), :3].astype(np.float32)
    col_line = col_rad * 0.62
    base = col_rad[None, None, :] * fwd[..., None] + col_hull[None, None, :] * (1 - fwd[..., None])
    patch = base * (1 - cov[..., None]) + col_line[None, None, :] * cov[..., None]
    np.save(os.path.join(outdir, "LiveryTex_patch.npy"), patch.astype(np.float32))
    np.save(os.path.join(outdir, "LiveryTex_patch_cols.npy"), np.array([0, lc1]))

    # sulco no PanelBump: a junta e uma peca removivel, tem folga de verdade
    groove = 0.5 - 0.16 * cov
    np.save(os.path.join(outdir, "PanelBump_patch.npy"), groove.astype(np.float32))

    rep["radome"] = {
        "plano": "x + %.4f*z = %.4f" % (K_RADOME, X0_RADOME),
        "largura_m": W_RADOME,
        "cor": [float(v) for v in col_line],
        "casco": [float(v) for v in col_hull],
    }
    import json
    with open(os.path.join(outdir, "relatorio.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    for k, v in rep.items():
        _log(k, "=", v)


def _shrink(m):
    out = m.copy()
    out[1:, :] &= m[:-1, :]
    out[:-1, :] &= m[1:, :]
    out[:, 1:] &= m[:, :-1]
    out[:, :-1] &= m[:, 1:]
    return out


def _sample(tu, tx, c0, c1, r0, r1, NW, NH, ss):
    """Posicao 3D de cada sub-texel da janela [c0,c1) x [r0,r1) da textura."""
    nc, nr = c1 - c0, r1 - r0
    u = ((np.arange(nc * ss) + 0.5) / ss + c0) / NW
    v = ((np.arange(nr * ss) + 0.5) / ss + r0) / NH
    grid = np.full((len(v), len(u), 3), np.nan)
    u0, u1 = u[0], u[-1]
    v0, v1 = v[0], v[-1]
    du = (u1 - u0) / max(len(u) - 1, 1)
    dv = (v1 - v0) / max(len(v) - 1, 1)
    for k in range(len(tu)):
        a, b, c = tu[k]
        if max(a[0], b[0], c[0]) < u0 or min(a[0], b[0], c[0]) > u1:
            continue
        if max(a[1], b[1], c[1]) < v0 or min(a[1], b[1], c[1]) > v1:
            continue
        i0 = max(0, int((min(a[0], b[0], c[0]) - u0) / du) - 1)
        i1 = min(len(u), int((max(a[0], b[0], c[0]) - u0) / du) + 2)
        j0 = max(0, int((min(a[1], b[1], c[1]) - v0) / dv) - 1)
        j1 = min(len(v), int((max(a[1], b[1], c[1]) - v0) / dv) + 2)
        if i1 <= i0 or j1 <= j0:
            continue
        d = np.array([b[0] - a[0], b[1] - a[1]])
        e = np.array([c[0] - a[0], c[1] - a[1]])
        det = d[0] * e[1] - d[1] * e[0]
        if abs(det) < 1e-15:
            continue
        U, V = np.meshgrid(u[i0:i1], v[j0:j1])
        px = U - a[0]; py = V - a[1]
        s = (px * e[1] - py * e[0]) / det
        t = (d[0] * py - d[1] * px) / det
        m = (s >= -1e-9) & (t >= -1e-9) & (s + t <= 1 + 1e-9)
        if not m.any():
            continue
        A, B, C = tx[k]
        val = (A[None, None, :] + s[..., None] * (B - A)[None, None, :]
               + t[..., None] * (C - A)[None, None, :])
        tgt = grid[j0:j1, i0:i1]
        tgt[m] = val[m]
    return grid


def _medir(PX, PY, PZ, glass, frame, ok):
    """Numeros do para-brisa novo, LIDOS COMO A FOTO LE.

    Head-on nao se ve "vidro" e "selo": ve-se uma MANCHA ESCURA por vidro e uma
    FRESTA CLARA entre elas. Entao mede-se a mancha (vidro | selo) e as frestas,
    que e o que as duas fotos deram normalizado pela meia-largura da mancha.
    """
    dark = (glass | frame) & ok
    g = glass & ok
    ydark = float(np.nanmax(np.abs(PY[dark])))
    out = {
        "vidro_x": [float(np.nanmin(PX[g])), float(np.nanmax(PX[g]))],
        "vidro_z": [float(np.nanmin(PZ[g])), float(np.nanmax(PZ[g]))],
        "meia_largura_vidro": float(np.nanmax(np.abs(PY[g]))),
        "meia_largura_mancha": ydark,
        "altura_mancha_sobre_meia_largura":
            float((np.nanmax(PZ[dark]) - np.nanmin(PZ[dark])) / ydark),
    }
    zc = 0.5 * (np.nanmin(PZ[g]) + np.nanmax(PZ[g]))
    sel = ok & (np.abs(PZ - zc) < 0.004)
    yv = PY[sel]
    dv = dark[sel]
    order = np.argsort(yv)
    yv, dv = yv[order], dv[order]
    runs = []
    i = 0
    while i < len(dv):
        if dv[i]:
            j = i
            while j < len(dv) and dv[j]:
                j += 1
            runs.append((yv[i], yv[j - 1]))
            i = j
        else:
            i += 1
    runs = [r for r in runs if r[1] - r[0] > 0.02]
    out["manchas_em_z_medio"] = [[round(float(a), 4), round(float(b), 4)]
                                 for a, b in runs]
    if len(runs) == 4:
        fc = float(runs[2][0] - runs[1][1])
        fm = float(0.5 * ((runs[1][0] - runs[0][1]) + (runs[3][0] - runs[2][1])))
        cm = float(0.5 * (abs(runs[0][1] + runs[1][0]) / 2
                          + abs(runs[2][1] + runs[3][0]) / 2))
        out["fresta_central"] = fc
        out["fresta_meio"] = fm
        out["fresta_meio_centro"] = cm
        out["fresta_central_x_mancha"] = fc / ydark
        out["fresta_meio_x_mancha"] = fm / ydark
        out["fresta_meio_centro_x_mancha"] = cm / ydark
        out["alvo_da_foto"] = {"fresta_central": F_CENTRE, "fresta_meio": F_MID,
                               "fresta_meio_centro": F_MID_C}
    else:
        out["aviso"] = "corte em z medio deu %d manchas, nao 4" % len(runs)
    return out


# ============================================================ 3. APPLY (Blender)

def apply(outdir):
    import bpy
    D = bpy.data
    nm = np.load(os.path.join(outdir, "NoseMask_new.npy"))
    lt_patch = np.load(os.path.join(outdir, "LiveryTex_patch.npy"))
    lt_cols = np.load(os.path.join(outdir, "LiveryTex_patch_cols.npy"))
    pb_patch = np.load(os.path.join(outdir, "PanelBump_patch.npy"))

    def grava(nome, dados, colorspace):
        """NUNCA remover/recriar o datablock: os nos do material o referenciam
        pelo ponteiro e recriar deixa image=None (casco magenta).

        E o colorspace tem de ser ajustado ANTES do scale: atribuir
        `colorspace_settings.name` invalida o buffer e uma imagem PACKED se
        recarrega do arquivo empacotado — desfazendo o redimensionamento em
        silencio. O sintoma e um `foreach_set` que pede o tamanho ANTIGO
        mesmo depois de `img.size` ter mostrado o novo.
        """
        h, w = dados.shape[:2]
        img = D.images.get(nome)
        if img is None:
            img = D.images.new(nome, w, h, alpha=False, float_buffer=False)
        if img.colorspace_settings.name != colorspace:
            img.colorspace_settings.name = colorspace
        if tuple(img.size) != (w, h):
            img.scale(w, h)
        px = np.ones((h, w, 4), np.float32)
        px[..., :3] = dados
        img.pixels.foreach_set(px.ravel())
        img.pack()
        _log("gravado", nome, tuple(img.size), colorspace)
        return img

    grava("NoseMask", nm, "Non-Color")

    lt = D.images["LiveryTex"]
    w, h = lt.size
    buf = np.empty(w * h * 4, np.float32); lt.pixels.foreach_get(buf)
    A = buf.reshape(h, w, 4)
    A[:, int(lt_cols[0]):int(lt_cols[1]), :3] = lt_patch
    grava("LiveryTex", A[..., :3], "sRGB")

    pbimg = D.images["PanelBump"]
    w, h = pbimg.size
    buf = np.empty(w * h * 4, np.float32); pbimg.pixels.foreach_get(buf)
    B = buf.reshape(h, w, 4)
    B[:, :pb_patch.shape[1], 0] = pb_patch
    B[:, :pb_patch.shape[1], 1] = pb_patch
    B[:, :pb_patch.shape[1], 2] = pb_patch
    grava("PanelBump", B[..., :3], "Non-Color")

    # Conferencia do shader. `link.from_node is node` NUNCA casa na RNA do
    # Blender (cada acesso devolve um wrapper novo) — comparar por NOME.
    nt = D.materials["FuselagemPaint"].node_tree
    for n in nt.nodes:
        if n.type == "TEX_IMAGE":
            _log("shader:", n.name, "->", None if n.image is None else
                 (n.image.name, tuple(n.image.size)))
            if n.image is None:
                raise RuntimeError("no de imagem orfao em FuselagemPaint")
    alvo = {}
    for link in nt.links:
        if link.from_node.type == "TEX_IMAGE":
            alvo.setdefault(link.to_node.name, []).append(link.from_node.image.name)
    _log("ligacoes por nome:", alvo)
    bpy.ops.wm.save_mainfile()
    _log("blend salvo:", bpy.data.filepath)


# ------------------------------------------------------------------- driver

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    modo = argv[0]
    if modo == "export":
        export(argv[1])
    elif modo == "build":
        build(argv[1], float(argv[2]))
    elif modo == "apply":
        apply(argv[1])
    else:
        raise SystemExit(__doc__)
