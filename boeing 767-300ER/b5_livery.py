"""Etapa 5 — livery LATAM do CC-CWY, medida na foto (refs/ref_CC-CWY_perfil_mia.jpg).

/Applications/Blender.app/Contents/MacOS/Blender -b "boeing 767-300ER/B763_LATAM.blend" --python "boeing 767-300ER/b5_livery.py"

Tudo o que e tinta vira textura: (x,theta) no casco (LiveryTex/LiveryFac) e
planar (x,z) na deriva (FinSashE/FinSashD). Nada de decalque 3D.

Fonte das cotas: fotogrametria 2026-08-20 sobre a foto de perfil de CC-CWY
(Miami 19/02/2026, 5398 px, CC BY 4.0, refs/manifest.json). Mapa foto->modelo
por afim de tres retas (crista do casco = z 2.705; BA reto da deriva;
BF da deriva), 94.38 px/m, validado na ponta do nariz (x=0), na porta 1
(x=5.70) e na porta 3 (x=42.55).
"""
import bpy
import bmesh
import json
import math
import os
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
spec = json.load(open(os.path.join(BASE, "spec_763.json")))

LUV = 55.5                 # dominio u do casco: u = x/LUV
W, H = 4096, 1024          # LiveryTex / LiveryFac
FW = FH = 2048             # FinSashE / FinSashD

INDIGO = (0x2A, 0x00, 0x88)
CORAL = (0xED, 0x16, 0x51)
BRANCO = (0xE6, 0xE7, 0xEA)
CINZA_VOO = (0xC8, 0xCA, 0xCC)
CINZA_FAR = (0xB6, 0xB8, 0xBA)
SULCO = (0x2E, 0x30, 0x33)
TITULO = (0x1C, 0x2E, 0x63)
VIDRO = (0x14, 0x17, 0x1A)

# ------------------------------------------------------- rasterizador numpy
def fill_tris(tris, x0, x1, z0, z1, nx, nz):
    """Rasteriza triangulos (lista de 3 pares (x,z)) numa grade nx x nz.

    Grade: coluna i -> x = x0 + (i+0.5)*(x1-x0)/nx ; linha j -> z crescente.
    Devolve mascara booleana (nz, nx).
    """
    out = np.zeros((nz, nx), bool)
    if not tris:
        return out
    sx = (x1 - x0) / nx
    sz = (z1 - z0) / nz
    T = np.asarray(tris, np.float64)                    # (n,3,2)
    # para pixel-centro: i = (x-x0)/sx - 0.5
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
    """triangula um poligono convexo por leque a partir do vertice 0."""
    return [[poly[0], poly[i], poly[i + 1]] for i in range(1, len(poly) - 1)]


# ----------------------------------------------------------------- geometria
nose = spec["nariz_estacoes"]
tail = spec["cauda_estacoes"]
_nx = np.array([s[0] for s in nose])
_nc = np.array([s[1] for s in nose])
_nk = np.array([s[2] for s in nose])
_tx = np.array([s[0] for s in tail])
_tzc = np.array([s[1] for s in tail])
_trz = np.array([s[2] for s in tail])


def zc_rz(x):
    x = np.asarray(x, float)
    zc = np.zeros_like(x)
    rz = np.full_like(x, 2.705)
    m = x <= 7.5
    if m.any():
        c = np.interp(x[m], _nx, _nc)
        k = np.interp(x[m], _nx, _nk)
        zc[m] = (c + k) / 2.0
        rz[m] = (c - k) / 2.0
    m = x >= 41.0
    if m.any():
        zc[m] = np.interp(x[m], _tx, _tzc)
        rz[m] = np.interp(x[m], _tx, _trz)
    return zc, rz


uu = (np.arange(W) + 0.5) / W
vv = (np.arange(H) + 0.5) / H
UX = uu * LUV                                    # x de cada coluna
VT = vv * 2 * math.pi - math.pi                  # theta assinado de cada linha
GX = np.repeat(UX[None, :], H, axis=0)
GT = np.repeat(VT[:, None], W, axis=1)
_zc, _rz = zc_rz(UX)
GZ = _zc[None, :] + _rz[None, :] * np.cos(GT)
GABS = np.abs(GT)                                # angulo desde a crista
LADO = np.where(GT < 0, -1, 1)                   # -1 bombordo (y<0)

tex = np.zeros((H, W, 3), np.uint8)
tex[:] = BRANCO

# ============================================================ 1. cunha indigo
# medido em CC-CWY 2026-08-20:
#   fronteira dianteira  x = 42.11 + 1.008 z   (paralela ao BA reto da deriva,
#                                               0.72 m atras dele; rms 0.21 m)
#   fronteira inferior   theta <= 134.4 - 8.061 (x-41.5)  graus  (rms 1.4 graus)
#   limite traseiro      x <= 50.55 + 0.398 z  (a propria linha do BF da deriva)
CUNHA_X0, CUNHA_K = 42.11, 1.008
CUNHA_T0, CUNHA_R = 134.4, 8.061
theta_max = np.radians(np.clip(CUNHA_T0 - CUNHA_R * (GX - 41.5), 0.0, 180.0))
cunha = ((GX >= CUNHA_X0 + CUNHA_K * GZ) & (GABS <= theta_max) &
         (GX <= 50.55 + 0.398 * GZ))
tex[cunha] = INDIGO
base_cor = np.where(cunha[..., None], np.array(INDIGO, np.uint8),
                    np.array(BRANCO, np.uint8))

# ==================================================== 2. colocar marcas em (x,z)
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
    if cor is None:                      # None = devolve a cor de base
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
            Xc = X + cis * (Y - ay)                      # cisalhamento (italico)
            xm = (x1 - (Xc - ax) * sx) if espelha else (x0 + (Xc - ax) * sx)
            p.append((xm, z0 + (Y - ay) * sz))
        out.append(p)
    return out


def marca_th(tris, bb, x0, x1, th_topo, th_base, cor, lado, espelha=False,
             ppm=460):
    """Coloca uma marca em (x, theta): preserva a proporcao da arte sobre a
    superficie desenvolvida, em vez de a achatar na projecao lateral (z).
    th_topo/th_base em GRAUS desde a crista; Y max da arte -> th_topo."""
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
    nt = max(8, int(round(math.radians(th_base - th_topo) * 2.50 * ppm)))
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
    jt = np.clip(((GD[sel] - th_topo) / (th_base - th_topo) * nt).astype(int),
                 0, nt - 1)
    hit = arr[jt, ix]
    r, c = np.where(sel)
    tex[r[hit], c[hit]] = cor
    return int(hit.sum())


# ============================================== 3. portas, saidas e contornos
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
    """banda cinza FAR + sulco escuro + folha na cor de base."""
    x0, x1 = cx - larg / 2, cx + larg / 2
    X0, X1, Z0, Z1 = x0 - 0.25, x1 + 0.25, zl - 0.25, zh + 0.25
    marca(leque(rrect(x0, x1, zl, zh, 0.070, r)), X0, X1, Z0, Z1, CINZA_FAR, lado)
    marca(leque(rrect(x0, x1, zl, zh, 0.030, r)), X0, X1, Z0, Z1, SULCO, lado)
    marca(leque(rrect(x0, x1, zl, zh, 0.008, r)), X0, X1, Z0, Z1, None, lado)


pd = spec["portas_pax"]
for k in ("porta1", "porta3"):
    p = pd[k]
    porta(p["centro_x"], p["abertura"][0], p["z"][0], p["z"][1], lado=-1)
    porta(p["centro_x"], 1.07, p["z"][0] + 0.02, p["z"][1] - 0.03, lado=1)
ow = pd["overwing"]
for cx in ow["centros_x"]:
    for lado in (-1, 1):
        porta(cx, ow["folha"][0], ow["z"][0], ow["z"][1], r=0.16, lado=lado)
pc = spec["portas_carga"]
for k in ("fwd_grande", "aft", "bulk"):
    c = pc[k]
    larg = (c.get("clear") or c.get("dim"))[0]
    porta(c["centro_x"], larg, c["z"][0], c["z"][1], r=0.14, lado=1)

# ==================================================== 4. faixa de janelas
# medido: vidro z 0.81..1.09 (0.28 m), passo 0.567 m, faixa x 7.10..43.10
JZ0, JZ1, JPASSO = 0.81, 1.09, 0.5669
JX0, JX1 = 7.10, 43.10
njan = int((JX1 - JX0) / JPASSO)
for lado in (-1, 1):
    tris = []
    for i in range(njan + 1):
        cx = JX0 + i * JPASSO
        if 5.0 < cx < 6.45 or 41.85 < cx < 43.30:
            continue
        tris += leque(rrect(cx - 0.115, cx + 0.115, JZ0, JZ1, 0.0, 0.055))
    marca(tris, JX0 - 0.4, JX1 + 0.4, JZ0 - 0.1, JZ1 + 0.1, VIDRO, lado, ppm=620)

# ============================================================ 5. marca LATAM
# A arte oficial e importada do 787 (bpy.data.libraries.load na sessao anterior):
# mesma marca, mesma geometria, sem risco de deriva.  Simbolo e wordmark sao
# colocados SEPARADAMENTE, cada um na sua propria razao oficial, porque o CC-CWY
# usa o simbolo ~30% maior em relacao ao wordmark do que o lockup padrao
# (medido: simbolo 1.70 m de largura por 2.73 m de arco; wordmark 6.65 x 0.99).
tri_all, bb_all = tris_do_objeto("B789_LogoLATAM_E")
tri_c, bb_c = tris_do_objeto("B789_LogoLATAM_E_Coral")
if tri_all and tri_c:
    tri_sim = [t for t in tri_all if max(p[0] for p in t) < 1.10]
    tri_wm = [t for t in tri_all if min(p[0] for p in t) >= 1.10]
    a = np.asarray(tri_sim + tri_c)
    bb_s = (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())
    a = np.asarray(tri_wm)
    bb_w = (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())
    rs = (bb_s[1] - bb_s[0]) / (bb_s[3] - bb_s[2])
    rw = (bb_w[1] - bb_w[0]) / (bb_w[3] - bb_w[2])
    # medido em CC-CWY (bombordo, 2026-08-20):
    SX0, SX1, S_TH = 6.98, 8.68, 34.26      # simbolo: x e theta do topo
    WX0, WX1, W_TH = 9.15, 15.80, 37.21     # wordmark: x e theta do topo (cap)
    S_TB = S_TH + math.degrees((SX1 - SX0) / rs / 2.50)
    W_TB = W_TH + math.degrees((WX1 - WX0) / rw / 2.50)
    print(f"[logo] simbolo razao {rs:.3f} -> theta {S_TH:.1f}..{S_TB:.1f} "
          f"(medido 34.3..94.4) | wordmark razao {rw:.3f} -> theta "
          f"{W_TH:.1f}..{W_TB:.1f} (medido 37.2..59.4)")
    for lado, esp in ((-1, False), (1, True)):
        marca_th(tri_sim, bb_s, SX0, SX1, S_TH, S_TB, INDIGO, lado, esp)
        marca_th(tri_c, bb_s, SX0, SX1, S_TH, S_TB, CORAL, lado, esp)
        marca_th(tri_wm, bb_w, WX0, WX1, W_TH, W_TB, INDIGO, lado, esp)
else:
    print("[logo] AVISO: malhas do lockup nao encontradas")

# ============================================ 6. matricula e titulo de tipo
# matricula BRANCA dentro do indigo: x 44.12..45.92, z 1.044..1.343 (medido)
tr, bbr = texto_tris("CC-CWY")
for lado in (-1, 1):
    marca(encaixa(tr, bbr, 44.12, 45.92, 1.044, 1.343), 44.12, 45.92,
          1.044, 1.343, (0xF2, 0xF3, 0xF5), lado, ppm=760)
# titulo de tipo, escuro sobre branco, obliquo: x 37.41..40.68, z 1.083..1.269
tt, bbt = texto_tris("BOEING 767-300ER")
for lado in (-1, 1):
    marca(encaixa(tt, bbt, 37.41, 40.68, 1.083, 1.269, cis=0.20), 37.41, 40.68,
          1.083, 1.269, TITULO, lado, ppm=760)

# =================================================== 7. barriga e desgaste
if tri_all and tri_c:
    # arco lateral a partir da quilha, com sinal do lado -> espaco desenvolvido
    lat = (np.pi - GABS) * 2.466 * LADO
    BX0, BX1 = 24.0, 31.0                      # wordmark no ventre
    BH = (BX1 - BX0) / rw
    nx, nz = int((BX1 - BX0) * 300), max(8, int(BH * 300))
    arr = fill_tris(encaixa(tri_wm, bb_w, BX0, BX1, -BH / 2, BH / 2),
                    BX0, BX1, -BH / 2, BH / 2, nx, nz)
    SBX1 = BX0 - 0.45
    SBX0 = SBX1 - (BH * rs) * (bb_s[1] - bb_s[0]) / (bb_s[1] - bb_s[0])
    SBH = BH * 2.0                             # simbolo 2x a altura do cap
    SBX0 = SBX1 - SBH * rs
    nsx, nsz = max(8, int((SBX1 - SBX0) * 300)), max(8, int(SBH * 300))
    arrS = fill_tris(encaixa(tri_sim, bb_s, SBX0, SBX1, -SBH / 2, SBH / 2),
                     SBX0, SBX1, -SBH / 2, SBH / 2, nsx, nsz)
    arrC = fill_tris(encaixa(tri_c, bb_s, SBX0, SBX1, -SBH / 2, SBH / 2),
                     SBX0, SBX1, -SBH / 2, SBH / 2, nsx, nsz)
    for (a0, X0b, X1b, Hb, nX, nZ, cor) in (
            (arr, BX0, BX1, BH, nx, nz, INDIGO),
            (arrS, SBX0, SBX1, SBH, nsx, nsz, INDIGO),
            (arrC, SBX0, SBX1, SBH, nsx, nsz, CORAL)):
        sel = (GX >= X0b) & (GX <= X1b) & (np.abs(lat) <= Hb / 2)
        if not sel.any():
            continue
        ix = np.clip(((GX[sel] - X0b) / (X1b - X0b) * nX).astype(int), 0, nX - 1)
        jz = np.clip(((lat[sel] + Hb / 2) / Hb * nZ).astype(int), 0, nZ - 1)
        r, c = np.where(sel)
        h = a0[jz, ix]
        tex[r[h], c[h]] = cor


def suja(x0, x1, t0, t1, cor, inten):
    m = ((GX >= x0) & (GX <= x1) & (GABS >= math.radians(t0)) &
         (GABS <= math.radians(t1)))
    if m.any():
        tex[m] = (tex[m] * (1 - inten) + np.array(cor) * inten).astype(np.uint8)


suja(5.2, 12.5, 156, 180, (0x9A, 0x93, 0x88), 0.09)
suja(12.5, 17.5, 150, 172, (0xA8, 0xA2, 0x99), 0.05)
suja(27.5, 34.0, 150, 180, (0x9E, 0x98, 0x8E), 0.07)

# ============================================================ 8. grava casco
D = bpy.data


def grava(nome, dados, cinza=False, colorspace="sRGB"):
    img = D.images.get(nome)
    if img is None or tuple(img.size) != (W, H):
        if img:
            D.images.remove(img)
        img = D.images.new(nome, W, H, alpha=False, float_buffer=False)
    px = np.ones((H, W, 4), np.float32)
    if cinza:
        px[..., 0] = px[..., 1] = px[..., 2] = dados
    else:
        px[..., :3] = dados.astype(np.float32) / 255.0
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(px.ravel())
    img.pack()


grava("LiveryTex", tex, False, "sRGB")
grava("LiveryFac", np.ones((H, W), np.float32), True, "Non-Color")
print(f"[casco] cunha indigo = {int(cunha.sum())} texels ({100*cunha.mean():.1f}%)")

# =============================================================== 9. deriva
# UV medida no modelo: u = (x-40.0)/15.5 ; v = (z-1.4)/10.0
FX0, FXL, FZ0, FZL = 40.0, 15.5, 1.4, 10.0
fu = (np.arange(FW) + 0.5) / FW
fv = (np.arange(FH) + 0.5) / FH
FX = np.repeat((FX0 + fu * FXL)[None, :], FH, axis=0)
FZ = np.repeat((FZ0 + fv * FZL)[:, None], FW, axis=1)

mLE, cLEf, mTE, cTEf = 1.0014, 41.39, 0.398, 50.55
U = FZ - 0.370 * FX          # atravessa as bandas (sobem 20.3 graus)
E = FZ + 0.21 * FX           # ao longo das bandas (cortes descem 11.9 graus)

# medido em CC-CWY 2026-08-20 (foto retificada no plano (x,z) da deriva)
LB_U0, LB_U1 = -14.32, -13.27     # banda inferior (1.05 em z = 0.985 perpend.)
UB_U0, UB_U1 = -10.56, -9.60      # banda superior (0.96 em z = 0.900 perpend.)
LB_E0, LB_E1 = 14.37, 16.26       # coral da banda inferior
UB_E0, UB_E1 = 19.13, 21.05       # coral da banda superior
FILETE = 0.24                     # filete cinza-voo do BA, perpendicular

fin = np.zeros((FH, FW, 3), np.uint8)
fin[:] = INDIGO
fin[U >= UB_U0] = CINZA_VOO                                   # banda sup + cap
fin[(U >= LB_U0) & (U <= LB_U1)] = CINZA_VOO                  # banda inferior
fin[(U >= LB_U0) & (U <= LB_U1) & (E >= LB_E0) & (E <= LB_E1)] = CORAL
fin[(U >= UB_U0) & (U <= UB_U1) & (E >= UB_E0) & (E <= UB_E1)] = CORAL
dLE = (FX - (cLEf + mLE * FZ)) / math.sqrt(1 + mLE * mLE)
fin[(dLE >= 0) & (dLE <= FILETE)] = CINZA_VOO
fin[(FX < cLEf + mLE * FZ) | (FX > cTEf + mTE * FZ)] = INDIGO   # fora da planform


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
grava_fin("FinSashD", fin)        # mesma arte em (x,z) nos dois lados (CC-CXH)

der = D.objects["Deriva"]
nomes = [s.name for s in der.material_slots]
iE, iD = nomes.index("Deriva_Sash_E"), nomes.index("Deriva_Sash_D")
for p in der.data.polygons:
    p.material_index = iE if p.center.y < 0 else iD
# valores da frota (A320neo/787-9 aprovados): a deriva NAO leva verniz.
# Com Coat 1.0 e Coat Roughness 0.05 o cartao de nuvem reflete na deriva
# inteira e lava a tinta — o coral saia (219,96,110) contra (182,34,57) no
# A320 aprovado, com o mesmo #ED1651 na textura.
for mn in ("Deriva_Sash_E", "Deriva_Sash_D"):
    b = next(n for n in D.materials[mn].node_tree.nodes
             if n.type == "BSDF_PRINCIPLED")
    b.inputs["Roughness"].default_value = 0.45
    b.inputs["Specular IOR Level"].default_value = 0.20
    b.inputs["Coat Weight"].default_value = 0.0
    b.inputs["Coat Roughness"].default_value = 0.03

# ================================================= 10. janelas: geometria
# medido: vidro z 0.81..1.09, ultima janela em x~43.1 (a cunha come o resto)
jp = D.objects.get("JanelasPax")
if jp:
    me = jp.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    z0, z1 = co[:, 2].min(), co[:, 2].max()
    alvo0, alvo1 = 0.79, 1.11
    print(f"[janelas] z {z0:.3f}..{z1:.3f} -> {alvo0}..{alvo1}; "
          f"x {co[:,0].min():.2f}..{co[:,0].max():.2f}")
    esc = (alvo1 - alvo0) / (z1 - z0)
    co[:, 2] = alvo0 + (co[:, 2] - z0) * esc
    me.vertices.foreach_set("co", co.ravel())
    bm = bmesh.new()
    bm.from_mesh(me)
    fora = [f for f in bm.faces if f.calc_center_median().x > 43.35]
    bmesh.ops.delete(bm, geom=fora, context="FACES")
    solto = [v for v in bm.verts if not v.link_faces]
    if solto:
        bmesh.ops.delete(bm, geom=solto, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()
    print(f"[janelas] {len(fora)} faces apagadas atras de x=43.35")

# ================================================ 10b. parabrisa (NoseMask)
# R = moldura fosca, G = vidro.  Contorno medido na foto de CC-CWY no
# enquadramento ortografico (x 1.60..3.25, z 0.60..1.33): o parabrisa do 767 e
# GRANDE e vai quase ate o radome.  A mascara herdada dava uma fresta de
# x 1.63..2.50 por z 0.75..1.25, com um terco da area — o nariz lia como um
# bulbo branco sem cabine.
CONTORNO = [(1.60, 0.62), (1.62, 0.95), (1.90, 1.22), (2.40, 1.33),
            (2.95, 1.31), (3.25, 1.18), (3.22, 0.82), (2.60, 0.66),
            (2.00, 0.60)]


def _offset(poly, d):
    cx = sum(p[0] for p in poly) / len(poly)
    cz = sum(p[1] for p in poly) / len(poly)
    out = []
    for (x, z) in poly:
        dx, dz = x - cx, (z - cz) * 3.0        # z pesa mais: a banda e baixa
        n = math.hypot(dx, dz) or 1.0
        out.append((x + d * dx / n, z + d * dz / n / 3.0))
    return out


NX_M, NZ_M = 3.60, 1.60
nx_m = int(NX_M * 900)
nz_m = int(NZ_M * 900)
X0M, X1M, Z0M, Z1M = 1.20, 1.20 + NX_M, 0.20, 0.20 + NZ_M
vidro = fill_tris(leque(CONTORNO), X0M, X1M, Z0M, Z1M, nx_m, nz_m)
moldura = fill_tris(leque(_offset(CONTORNO, 0.115)), X0M, X1M, Z0M, Z1M, nx_m, nz_m)
# montantes entre os 3 paineis por lado (o 767 tem para-brisa + no.2 + no.3)
for xp in (2.16, 2.78):
    post = fill_tris([[(xp - 0.045, 0.4), (xp + 0.045, 0.4), (xp + 0.045, 1.5)],
                      [(xp - 0.045, 0.4), (xp + 0.045, 1.5), (xp - 0.045, 1.5)]],
                     X0M, X1M, Z0M, Z1M, nx_m, nz_m)
    vidro &= ~post
nose_r = np.zeros((H, W), np.float32)
nose_g = np.zeros((H, W), np.float32)
sel = (GX >= X0M) & (GX <= X1M) & (GZ >= Z0M) & (GZ <= Z1M)
ixm = np.clip(((GX[sel] - X0M) / NX_M * nx_m).astype(int), 0, nx_m - 1)
jzm = np.clip(((GZ[sel] - Z0M) / NZ_M * nz_m).astype(int), 0, nz_m - 1)
r, c = np.where(sel)
hm = moldura[jzm, ixm]
nose_r[r[hm], c[hm]] = 1.0
hv = vidro[jzm, ixm]
nose_g[r[hv], c[hv]] = 1.0
nose_r[nose_g > 0.5] = 0.0
img = D.images.get("NoseMask")
if img is None or tuple(img.size) != (W, H):
    if img:
        D.images.remove(img)
    img = D.images.new("NoseMask", W, H, alpha=False, float_buffer=False)
px = np.ones((H, W, 4), np.float32)
px[..., 0] = nose_r
px[..., 1] = nose_g
px[..., 2] = 0.0
img.colorspace_settings.name = "Non-Color"
img.pixels.foreach_set(px.ravel())
img.pack()
print(f"[parabrisa] vidro={int((nose_g>0.5).sum())} texels, "
      f"moldura={int((nose_r>0.5).sum())}")

# ============================================ 11. materiais e exposicao
# O branco do casco saia a 161/255 contra 236/255 na foto de CC-CWY medida no
# mesmo enquadramento ortografico — o aviao inteiro lia cinza.  E os pneus
# saiam como discos pretos chapados, sem forma nenhuma.
def bsdf(nome):
    m = D.materials.get(nome)
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
                None) if m else None

b = bsdf("Pneu")
if b:
    b.inputs["Base Color"].default_value = (0.030, 0.031, 0.034, 1.0)
    b.inputs["Roughness"].default_value = 0.82
    b.inputs["Specular IOR Level"].default_value = 0.32
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 0.0
b = bsdf("StrutMetal")
if b:
    b.inputs["Base Color"].default_value = (0.62, 0.63, 0.65, 1.0)
    b.inputs["Metallic"].default_value = 0.85
    b.inputs["Roughness"].default_value = 0.33
b = bsdf("MetalMotor")
if b:
    b.inputs["Base Color"].default_value = (0.34, 0.34, 0.35, 1.0)
    b.inputs["Metallic"].default_value = 0.80
    b.inputs["Roughness"].default_value = 0.30

sol = D.objects.get("Sol")
if sol:
    sol.data.energy = 4.5
    sol.data.angle = math.radians(0.53)
cc = D.objects.get("CloudCard")
if cc:
    cc.data.energy = 8000.0
for sc in D.scenes:
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"
    sc.view_settings.exposure = 0.20

bpy.ops.wm.save_mainfile()
print("SALVO", bpy.data.filepath)
