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
CUNHA_X0, CUNHA_K = 59.11, 1.058              # dianteira, reta em (x,z)
CUNHA_T0, CUNHA_R = 108.1, 1.03               # inferior, reta em (x,theta) graus
CUNHA_TX0 = 60.0
theta_max = np.radians(np.clip(CUNHA_T0 + CUNHA_R * (GX - CUNHA_TX0), 0.0, 180.0))
cunha = ((GX >= CUNHA_X0 + CUNHA_K * GZ) & (GABS <= theta_max) &
         (GX <= 68.254 + 0.396 * GZ))
tex[cunha] = INDIGO
base_cor = np.where(cunha[..., None], np.array(INDIGO, np.uint8),
                    np.array(BRANCO, np.uint8))
print(f"[casco] cunha indigo = {int(cunha.sum())} texels ({100*cunha.mean():.2f}%)")


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

# ============================================================ 5. marca LATAM
tri_all, bb_all = tris_do_objeto("B77W_LogoLATAM_E")
tri_c, bb_c = tris_do_objeto("B77W_LogoLATAM_E_Coral")
if tri_all and tri_c:
    corte = bb_all[0] + 0.18 * (bb_all[1] - bb_all[0])
    tri_sim = [t for t in tri_all if max(p[0] for p in t) < corte]
    tri_wm = [t for t in tri_all if min(p[0] for p in t) >= corte]
    a = np.asarray(tri_sim + tri_c)
    bb_s = (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())
    a = np.asarray(tri_wm)
    bb_w = (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())
    rs = (bb_s[1] - bb_s[0]) / (bb_s[3] - bb_s[2])
    rw = (bb_w[1] - bb_w[0]) / (bb_w[3] - bb_w[2])
    # medido em PT-MUG (bombordo, foto FRA 2022):
    SX0, SX1, S_TH = 7.91, 9.64, 46.8       # simbolo
    WX0, WX1, W_TH = 10.34, 17.26, 51.6     # wordmark (caixa alta)
    S_TB = S_TH + math.degrees((SX1 - SX0) / rs / 3.10)
    W_TB = W_TH + math.degrees((WX1 - WX0) / rw / 3.10)
    print(f"[logo] simbolo razao {rs:.3f} -> theta {S_TH:.1f}..{S_TB:.1f} (medido 46.8..95.0) | "
          f"wordmark razao {rw:.3f} -> theta {W_TH:.1f}..{W_TB:.1f} (medido 51.6..68.4)")
    for lado, esp in ((-1, False), (1, True)):
        marca_th(tri_sim, bb_s, SX0, SX1, S_TH, S_TB, INDIGO, lado, esp)
        marca_th(tri_c, bb_s, SX0, SX1, S_TH, S_TB, CORAL, lado, esp)
        marca_th(tri_wm, bb_w, WX0, WX1, W_TH, W_TB, INDIGO, lado, esp)
else:
    print("[logo] AVISO: malhas do lockup nao encontradas")

# ============================================ 6. matricula e titulo de tipo
tr, bbr = texto_tris("PT-MUG")
for lado in (-1, 1):
    marca(encaixa(tr, bbr, 60.64, 62.37, 0.80, 1.35), 60.64, 62.37, 0.80, 1.35,
          (0xF2, 0xF3, 0xF5), lado, ppm=760)
tt, bbt = texto_tris("BOEING 777-300")
for lado in (-1, 1):
    marca(encaixa(tt, bbt, 55.84, 58.55, 0.78, 1.12, cis=0.18), 55.84, 58.55,
          0.78, 1.12, INDIGO, lado, ppm=760)

# =================================================== 7. barriga e desgaste
if tri_all and tri_c:
    # No ventre do PT-MUG so vai o SIMBOLO (a foto FRA mostra a bandeirinha
    # sozinha, sem wordmark), x 11.1..14.1 medido na foto.
    lat = (np.pi - GABS) * 3.10 * LADO
    SBX0, SBX1 = 11.1, 14.1
    SBH = (SBX1 - SBX0) / rs
    nsx, nsz = max(8, int((SBX1 - SBX0) * 300)), max(8, int(SBH * 300))
    arrS = fill_tris(encaixa(tri_sim, bb_s, SBX0, SBX1, -SBH / 2, SBH / 2),
                     SBX0, SBX1, -SBH / 2, SBH / 2, nsx, nsz)
    arrC = fill_tris(encaixa(tri_c, bb_s, SBX0, SBX1, -SBH / 2, SBH / 2),
                     SBX0, SBX1, -SBH / 2, SBH / 2, nsx, nsz)
    npix = 0
    for (a0, cor) in ((arrS, INDIGO), (arrC, CORAL)):
        sel = (GX >= SBX0) & (GX <= SBX1) & (np.abs(lat) <= SBH / 2)
        if not sel.any():
            continue
        ix = np.clip(((GX[sel] - SBX0) / (SBX1 - SBX0) * nsx).astype(int), 0, nsx - 1)
        jz = np.clip(((lat[sel] + SBH / 2) / SBH * nsz).astype(int), 0, nsz - 1)
        r, c = np.where(sel)
        h = a0[jz, ix]
        tex[r[h], c[h]] = cor
        npix += int(h.sum())
    print(f"[barriga] simbolo x {SBX0}..{SBX1}, arco {SBH:.2f} m, {npix} texels")


def suja(x0, x1, t0, t1, cor, inten):
    m = ((GX >= x0) & (GX <= x1) & (GABS >= math.radians(t0)) &
         (GABS <= math.radians(t1)))
    if m.any():
        tex[m] = (tex[m] * (1 - inten) + np.array(cor) * inten).astype(np.uint8)


suja(6.5, 14.0, 156, 180, (0x9A, 0x93, 0x88), 0.08)          # spray do trem de nariz
suja(38.0, 46.0, 150, 180, (0x9E, 0x98, 0x8E), 0.06)         # atras do trem principal
suja(69.0, 74.0, 120, 180, (0x8E, 0x88, 0x82), 0.10)         # fuligem da APU

# ========================================================= 8. NoseMask
# Parabrisa do 777: banda de 3 vidros por lado que envolve o nariz.
# Construida em (x, z) — topo colado na crista la na frente e descendo em
# relacao a ela para tras — e convertida para (x, theta) pelo angulo
# parametrico da secao. Fontes: vista lateral do APR p.18 @600 dpi (a arte dos
# vidros esta desenhada: x 1.37..3.00, z 0.36..0.99) e a vista frontal
# (y ate 1.99); conferido na foto de nariz de PT-MUC (refs 083).
PB = S["parabrisa_6_vidros"]
WSX0, WSX1 = 1.45, 3.05
POSTES = [(1.90, 1.96), (2.46, 2.52)]        # montantes entre os vidros


def ws_z_topo(x):
    zc, rz, ry = zc_rz_ry(np.array([x]))
    crista = float(zc[0] + rz[0])
    return min(crista - 0.16, 0.97)


def ws_z_base(x):
    return ws_z_topo(x) - (0.50 + 0.085 * (x - WSX0))


def theta_de(x, z):
    zc, rz, ry = zc_rz_ry(np.array([x]))
    zc, rz, ry = float(zc[0]), float(rz[0]), float(ry[0])
    t = max(-1.0, min(1.0, (z - zc) / rz))
    s = math.sqrt(max(0.0, 1.0 - t * t))
    return math.degrees(math.atan2(s, t))


def pane_poly(xa, xb, folga_t=0.0, folga_x=0.0):
    """poligono do vidro em (x, theta), amostrado ao longo de x."""
    xa, xb = xa - folga_x, xb + folga_x
    xs = np.linspace(xa, xb, 12)
    topo = [(x, theta_de(x, ws_z_topo(x)) - folga_t) for x in xs]
    base = [(x, theta_de(x, ws_z_base(x)) + folga_t) for x in xs]
    return topo + base[::-1]


# NoseMask tem resolucao PROPRIA (2x a do casco) e cobertura por supersample
# 4x4: o parabrisa ocupa ~2% do dominio u, entao mascara binaria vira serrilha
# grossa no close-up do nariz — o defeito apareceu no primeiro render.
NW, NH = W * 2, H * 2
nose_mask = np.zeros((NH, NW, 3), np.float32)
lim = [WSX0] + [p for pr in POSTES for p in pr] + [WSX1]
panes = [(lim[0], lim[1]), (lim[2], lim[3]), (lim[4], lim[5])]
for (a, b) in panes:
    print(f"[parabrisa] vidro x {a:.2f}..{b:.2f}  theta "
          f"{theta_de(a, ws_z_topo(a)):.0f}..{theta_de(a, ws_z_base(a)):.0f} -> "
          f"{theta_de(b, ws_z_topo(b)):.0f}..{theta_de(b, ws_z_base(b)):.0f}")
PX0, PX1 = WSX0 - 0.35, WSX1 + 0.35
PT0, PT1 = 0.0, 95.0
npx, npt = 2400, 1500
_nuu = (np.arange(NW) + 0.5) / NW * LUV
_nvv = (np.arange(NH) + 0.5) / NH * 2 * math.pi - math.pi
NGX = np.repeat(_nuu[None, :], NH, axis=0)
NGD = np.degrees(np.abs(np.repeat(_nvv[:, None], NW, axis=1)))
dx_tex = LUV / NW
dt_tex = 360.0 / NH


def pinta(poly, canal, sub=4):
    arr = fill_tris(leque(poly), PX0, PX1, PT0, PT1, npx, npt)
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
    return float(acc.sum())


pinta(pane_poly(WSX0, WSX1, folga_t=-2.4, folga_x=0.085), 0)   # R = moldura
for (a, b) in panes:
    pinta(pane_poly(a, b), 1)                                   # G = vidro
nose_mask[..., 0] *= (1.0 - nose_mask[..., 1])
print(f"[parabrisa] moldura {float(nose_mask[...,0].sum()):.0f} / vidro "
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
