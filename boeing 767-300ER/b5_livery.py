"""Etapa 5 — livery PLANA do CC-CWY (consolidacao do pintor unico, 2026-08-27).

/Applications/Blender.app/Contents/MacOS/Blender -b "boeing 767-300ER/B763_LATAM.blend" --python "boeing 767-300ER/b5_livery.py"

ESTE ARQUIVO SO PINTA LIVERY PLANA: base branca, cunha indigo, portas,
janelas, deriva, parabrisa, desgaste. AS MARCAS — lockup LATAM, matricula,
titulo de tipo, marca do ventre — moram em `refazer_marcas.py` (tag b763er),
com as constantes deste arquivo movidas para la textualmente. A sequencia de
reconstrucao e SEMPRE:

    b5_livery.py  ->  refazer_marcas.py -- b763er lockup marcas
                  ->  reparar_echarpe.py -- b763er        (fecha a borda)

Ver REBUILD.md na raiz. Motivo (QA-BACKLOG "The wedge rasterizer is shared
now"): rodar um builder que pinta marcas re-insere as marcas por cima do que
as rodadas posteriores corrigiram.

A CUNHA vem da regra unica em `reparar_echarpe.FROTA["b763er"]` sobre a ponte
z(x,theta) lida da MALHA (`latam_livery_kit.secoes_do_casco`) — o `zc_rz()`
local, emendado em x = 41.0 (dzc +0.117 / drz -0.117 numa estacao), fica
apenas para posicionar portas/janelas/parabrisa, que foram autoradas nele;
usa-lo na cunha era o degrau de 3.0 graus que a rodada da cauda mediu.
Pintada BINARIA de proposito: e o que a textura embarcada tem, e o
anti-alias da borda e o passo final do `reparar_echarpe` (so no -300ER; nos
cargueiros a auditoria diz que a borda dura embarcada fica — QA-BACKLOG).

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

# regra da cunha e ponte de secoes: as UNICAS implementacoes, na raiz
import sys as _sys
if os.path.dirname(BASE) not in _sys.path:
    _sys.path.insert(0, os.path.dirname(BASE))
import latam_livery_kit as kit  # noqa: E402
import reparar_echarpe as _re   # noqa: E402

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
# medido em CC-CWY 2026-08-20 (a regra vive em reparar_echarpe._r_763er):
#   fronteira dianteira  x = 42.11 + 1.008 z   (paralela ao BA reto da deriva,
#                                               0.72 m atras dele; rms 0.21 m)
#   fronteira inferior   theta <= 134.4 - 8.061 (x-41.5)  graus  (rms 1.4 graus)
#   limite traseiro      x <= 50.55 + 0.398 z  (a propria linha do BF da deriva)
# Rasterizada pela ponte da MALHA (secoes_do_casco), nao pelo zc_rz() emendado:
# a emenda em x = 41.0 dava o degrau de 3.0 graus na fronteira inferior.
# Binaria (ss=1) porque e o estado embarcado; reparar_echarpe fecha a borda.
for _o in bpy.data.objects:
    _o.hide_viewport = False
bpy.context.view_layer.update()
_casco_ob = bpy.data.objects.get("Fuselagem") or bpy.data.objects["Casco"]
_crx, _crzc, _crrz, _crry = kit.secoes_do_casco(_casco_ob)
_cov = kit.cobertura_echarpe(_re.FROTA["b763er"]["regra"], _crx, _crzc, _crrz,
                             0.0, LUV, W, H, ss=1)
cunha = _cov >= 0.5
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

# =================================== 5-7. MARCAS: movidas para refazer_marcas
# Lockup LATAM (simbolo+wordmark), matricula CC-CWY, titulo de tipo e a marca
# do ventre moram em `refazer_marcas.py` (tag b763er, secao "legado 767/777"),
# com estas mesmas constantes e o mesmo rasterizador, citados la. Este arquivo
# nao pinta marca nenhuma — rodar refazer_marcas e o proximo passo obrigatorio
# da sequencia de reconstrucao (REBUILD.md).
#
# O desgaste (suja) fica AQUI porque e livery plana; refazer_marcas reaplica as
# mesmas caixas sobre a tinta do ventre que ele proprio pinta, preservando a
# ordem original (marca antes, sujeira por cima).


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
# SEIS vidros, tres por lado, que envolvem a FRENTE do nariz e se encontram
# num montante central no plano de simetria.  R = selo escuro, G = vidro.
#
# O que estava errado ate 2026-08-21: a mascara era UM poligono unico em
# (x, z) — CONTORNO = [(1.60,0.62) ... (3.25,1.18) ...] — rasterizado contra
# GZ = zc + rz*cos(theta), mais uma "moldura" que era o mesmo poligono
# dilatado 0.115 m.  Uma faixa em z vira uma faixa em THETA que nunca chega a
# theta = 0: medido na propria mascara antiga, o vidro vivia em theta
# 21.2..66.6 e o seu |y| minimo era 0.472 — 0.945 m de pintura branca entre
# os dois lados, onde mora o montante central. Os dois lados nunca se tocavam,
# nao havia montante central e nao havia V.  Pior, onde a moldura dilatada
# passava da crista do casco a faixa fechava POR CIMA do plano de simetria —
# a banda preta de borda serrilhada arqueada sobre o nariz que o gate
# head-on de aa2d27d expos.  E os "montantes" eram dois retangulos verticais
# em x, nao os montantes reais, o que dava 4 vidros em vez de 6.
#
# A causa e a regra que este proprio 767 escreveu em f2f96cd e que o 777
# reaprendeu em 22500e6: feature em casco curvo se mede na superficie
# desenvolvida, nunca na projecao (x, z), que achata o que sobe o ombro.
#
# Metodo correto: os poligonos vem da VISTA FRONTAL do ACAP em (|y|, z) —
# projecao ao longo de x, logo y e z sao exatos — e a estacao x de cada
# vertice sai de por o ponto NA SUPERFICIE por raycast ao longo de +x, que e
# a propria definicao da projecao frontal.  O acoplamento com o casco produz
# sozinho o V e o contorno 3D; nada e decalque.  Ver spec_763.json
# ("parabrisa"), inclusive a anisotropia do desenho, que custava 10% em |y|.
PB = spec["parabrisa"]
PANES_YZ = [[list(p) for p in PB["no1_frontal_yz"]],
            [list(p) for p in PB["no2_deslizante_yz"]],
            [list(p) for p in PB["no3_kick_yz"]]]
SELO_M = PB["selo_m"]                     # selo escuro na superficie
FOLGA_M = PB["folga_desenho_m"]           # recuo EM ARCO: o ACAP desenha a
                                          # ABERTURA, a foto mostra o VIDRO
FIL_M = PB["filete_canto_m"]
MC_Y = PB["montante_central_meia_largura"]
CINTA_M = PB["cinta_moldura_m"]

_fus = D.objects["Fuselagem"]
_fev = _fus.evaluated_get(bpy.context.evaluated_depsgraph_get())
from mathutils import Vector  # noqa: E402


def x_de_yz(y, z):
    """Estacao x de (|y|, z) NA SUPERFICIE, por raycast de frente ao longo
    de +x.  Primeiro impacto = exatamente o que a vista frontal desenha.
    Usar o casco avaliado pega de graca a pinca do cockpit, o duplo lobo e o
    encolhimento do subsurf — nada disso precisa ser replicado aqui."""
    hit, loc, _n, _i = _fev.ray_cast(Vector((-6.0, float(y), float(z))),
                                     Vector((1.0, 0.0, 0.0)))[:4]
    if not hit:
        raise ValueError(f"parabrisa: (|y|={y:.3f}, z={z:.3f}) nao pousa no casco")
    return float(loc.x)


def theta_de_yz(x, y, z):
    """Mesma formula da UV gravada em b1_casco.py: atan2(y, z - zc(x))."""
    zc, _rz = zc_rz(np.array([float(x)]))
    return math.degrees(math.atan2(abs(float(y)), float(z) - float(zc[0])))


def arredonda(poly, r, n=7):
    """Filete de raio r em cada canto, feito em (|y|, z) antes do mapeamento
    — mais barato e mais previsivel que uma abertura morfologica na grade."""
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
    """(|y|, z) -> (x, theta em graus), densificando cada aresta: o
    mapeamento e nao linear, uma aresta reta em (|y|,z) e curva em (x,theta)."""
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


def leque_centro(poly):
    """Fan a partir do centroide: os poligonos mapeados tem arestas curvas e
    o fan a partir do vertice 0 deixaria buraco."""
    cx = sum(p[0] for p in poly) / len(poly)
    ct = sum(p[1] for p in poly) / len(poly)
    return [[(cx, ct), poly[i], poly[(i + 1) % len(poly)]]
            for i in range(len(poly))]


# O ACAP separa os dois No.1 por apenas 4 cm — a 1:200 e a separacao minima
# que o traco permite, nao a aeronave.  A foto head-on manda (ver spec).  A
# aresta interna da ABERTURA vai para MC_Y - FOLGA para que o recuo em arco
# a deixe em MC_Y; perto do plano de simetria o arco corre praticamente ao
# longo de y, entao a conta fecha em metros.
for _v in (0, 3):
    PANES_YZ[0][_v][0] = MC_Y - FOLGA_M

# O montante No.2/No.3 do ACAP fica para FORA do que a foto mostra, e o erro
# cai todo no painel mais estreito: o desenho da No.2 19% largo e No.3 11%
# estreito, com a borda EXTERNA do No.3 batendo.  Nao e o painel, e a
# fronteira.  Um numero so, para dentro, nos dois lados do mesmo montante —
# o vao entre eles nao muda.
_A23 = PB["ajuste_montante_23_m"]
for _v in (1, 2):                    # No.2: externo-topo, externo-base
    PANES_YZ[1][_v][0] -= _A23
for _v in (0, 3):                    # No.3: interno-topo, interno-base
    PANES_YZ[2][_v][0] -= _A23

# A vista frontal achata o envidracado ~9% na vertical: a vista LATERAL da
# mesma prancha da 0.666 m de altura contra 0.610, e as tres fotos head-on
# (h/meia-largura 0.403, 0.419, 0.435) caem em cima da LATERAL, nao da
# frontal (0.390).  Escala so em z, em torno do centro do envidracado, de
# modo que |y| continue vindo da frontal — a lateral nao ve y nenhum.
EZ = PB["estica_z"]
EZC = PB["estica_z_centro"]
for _p in PANES_YZ:
    for _v in _p:
        _v[1] = EZC + (_v[1] - EZC) * EZ

PANES_XT = [para_xtheta(arredonda(p, FIL_M), n=6) for p in PANES_YZ]
_allx = [p[0] for pn in PANES_XT for p in pn]
_allt = [p[1] for pn in PANES_XT for p in pn]
for _nome, _pn in zip(("No.1 frontal", "No.2 deslizante", "No.3 kick"), PANES_XT):
    _xs = [p[0] for p in _pn]
    _ts = [p[1] for p in _pn]
    print(f"[parabrisa] {_nome:16s} x {min(_xs):.3f}..{max(_xs):.3f}  "
          f"theta {min(_ts):.1f}..{max(_ts):.1f} graus")
print(f"[parabrisa] envidracado inteiro: x {min(_allx):.3f}..{max(_allx):.3f}  "
      f"theta {min(_allt):.1f}..{max(_allt):.1f} graus")

# Zona morta do montante central: |y| <= MC_Y - SELO_M sobre toda a altura do
# No.1.  Sem ela a dilatacao do selo (e mais ainda a da cinta) atravessaria o
# plano de simetria e fecharia por cima da crista — que e literalmente o
# defeito que estamos consertando, so que em cinza.
_z1 = [p[1] for p in PANES_YZ[0]]
_POSTE_YZ = [(0.0, max(_z1) + 0.10), (max(0.0, MC_Y - SELO_M), max(_z1) + 0.10),
             (max(0.0, MC_Y - SELO_M), min(_z1) - 0.10), (0.0, min(_z1) - 0.10)]
POSTE_XT = para_xtheta(_POSTE_YZ, n=10)

# NoseMask tem resolucao PROPRIA (2x a do casco): o parabrisa ocupa ~2% do
# dominio u e uma mascara binaria vira serrilha grossa no close-up do nariz.
NW, NH = W * 2, H * 2
nose_mask = np.zeros((NH, NW, 3), np.float32)

PX0, PX1 = min(_allx) - 0.30, max(_allx) + 0.30
PT0, PT1 = 0.0, max(_allt) + 8.0
npx, npt = 2600, 1800
_nuu = (np.arange(NW) + 0.5) / NW * LUV
_nvv = (np.arange(NH) + 0.5) / NH * 2 * math.pi - math.pi
NGX = np.repeat(_nuu[None, :], NH, axis=0)
NGD = np.degrees(np.abs(np.repeat(_nvv[:, None], NW, axis=1)))
dx_tex = LUV / NW
dt_tex = 360.0 / NH
sx_m = (PX1 - PX0) / npx                    # metros por celula em x
st_g = (PT1 - PT0) / npt                    # graus por celula em theta


def _raio_local(x):
    """Raio medio da secao em x: media do semi-eixo vertical (rz) com a
    meia-largura (w2 do spec).  E ele que converte metros de arco em graus de
    theta; no nariz vai de ~0.9 m a ~1.9 m ao longo do proprio parabrisa."""
    x = np.asarray(x, float)
    _zc, _rz = zc_rz(x)
    _ry = np.interp(x, _nx, np.array([s[3] for s in nose]))
    return 0.5 * (_rz + np.maximum(_ry, 0.05))


def _dil_eixo(m, r, eixo):
    """Dilatacao de caixa por raio r ao longo de um eixo, por duplicacao
    binaria: 1, 2, 4, ... — O(log r) passadas em vez de O(r)."""
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
    """Octogono ~ uniao de dois retangulos: evita o canto quadrado."""
    a = _dil_eixo(_dil_eixo(m, rx, 1), max(1, rt // 2), 0)
    b = _dil_eixo(_dil_eixo(m, max(1, rx // 2), 1), rt, 0)
    return a | b


def _dil_metrico(m, metros, nb=10):
    """Dilata por `metros` de ARCO REAL.

    Um disco fixo em (x, theta) nao e um disco em metros: o raio da secao vai
    de ~0.9 m em x=1.3 a ~1.9 m em x=3.2, entao o mesmo numero de graus vale
    o dobro de arco atras.  Um raio unico em graus deixa o selo ~25% fino
    perto da crista — que e exatamente onde fica o montante central, o
    detalhe que o dono olha primeiro.  Resolvido por faixas de x.
    """
    out = np.zeros_like(m)
    bordas = np.linspace(PX0, PX1, nb + 1)
    rx = max(1, int(round(metros / sx_m)))
    for k in range(nb):
        xa, xb = bordas[k], bordas[k + 1]
        r = float(_raio_local(np.array([0.5 * (xa + xb)]))[0])
        rt = max(1, int(round(metros * math.degrees(1.0 / r) / st_g)))
        ia = max(0, int((xa - PX0) / sx_m) - rx - 1)
        ib = min(npx, int((xb - PX0) / sx_m) + rx + 2)
        d = _dil_octo(m[:, ia:ib], rx, rt)
        ja = max(0, int((xa - PX0) / sx_m))
        jb = min(npx, int((xb - PX0) / sx_m) + 1)
        out[:, ja:jb] |= d[:, ja - ia:jb - ia]
    return out


def _ero_metrico(m, metros, nb=10):
    """Erosao por `metros` de ARCO REAL: dilatar o complemento."""
    return ~_dil_metrico(~m, metros, nb)


# A abertura desenhada no ACAP recua para virar VIDRO VISIVEL — a moldura
# cavalga a borda — e depois o selo escuro cresce de volta.  As DUAS coisas
# tem de acontecer NA SUPERFICIE, em metros de arco.
#
# Foi aqui que a primeira tentativa errou: o recuo estava no plano (|y|,z) e
# so o selo na superficie.  Head-on, um selo de arco s aparece com largura
# s*cos(theta), enquanto um recuo no plano aparece inteiro — entao nos vidros
# que ja subiram o ombro os dois nao se cancelam.  No montante No.2/No.3
# (theta ~50-58 graus, cos ~0.6) o vao saia 29% largo e o No.3, que e o
# painel estreito, saia 19% fino.  Com recuo e selo ambos em arco o erro cai
# para poucos por cento nos dois.  Mesma familia de erro que o 25% do selo
# na crista: metros de arco != graus de theta.
abertura_f = np.zeros((npt, npx), bool)
for _pn in PANES_XT:
    abertura_f |= fill_tris(leque_centro(_pn), PX0, PX1, PT0, PT1, npx, npt)
vidro_f = _ero_metrico(abertura_f, FOLGA_M)
poste_f = fill_tris(leque_centro(POSTE_XT), PX0, PX1, PT0, PT1, npx, npt)
# O selo MANTEM o vidro dentro dele. Se ele fosse so o anel (& ~vidro_f), no
# texel de borda ficariam R=0.5 e G=0.5, e o shader — Mix(tinta, selo, R) e
# depois Mix(., vidro, G) — deixaria 25% de TINTA aparecer entre o vidro e o
# selo: um fio branco contornando cada painel, bem visivel no close do nariz.
# Com o selo cheio, R=1 em todo o conjunto e o G so decide quanto e vidro.
selo_f = _dil_metrico(vidro_f, SELO_M) & ~poste_f


def pinta_grade(arr, canal):
    """Cobertura EXATA do texel por imagem integral.

    As duas grades sao uniformes em (x, theta), entao a media de area sai de
    uma soma cumulativa 2D — sem amostragem. O supersample 4x4 que estava
    aqui media 16 amostras de uma celula que cobre ~27 celulas da grade fina:
    o ruido de cobertura que sobrava desenhava um dente de serra na borda
    quase horizontal do selo, exatamente o defeito de "borda serrilhada" que
    esta correcao existe para eliminar.
    """
    I = np.zeros((npt + 1, npx + 1), np.float64)
    I[1:, 1:] = np.cumsum(np.cumsum(arr.astype(np.float64), 0), 1)
    sel = (NGX >= PX0) & (NGX <= PX1) & (NGD >= PT0) & (NGD <= PT1)
    r, c = np.where(sel)
    i0 = np.clip(np.round((NGX[sel] - 0.5 * dx_tex - PX0) / sx_m).astype(int), 0, npx)
    i1 = np.clip(np.round((NGX[sel] + 0.5 * dx_tex - PX0) / sx_m).astype(int), 0, npx)
    j0 = np.clip(np.round((NGD[sel] - 0.5 * dt_tex - PT0) / st_g).astype(int), 0, npt)
    j1 = np.clip(np.round((NGD[sel] + 0.5 * dt_tex - PT0) / st_g).astype(int), 0, npt)
    i1 = np.maximum(i1, i0 + 1)
    j1 = np.maximum(j1, j0 + 1)
    soma = I[j1, i1] - I[j0, i1] - I[j1, i0] + I[j0, i0]
    nose_mask[r, c, canal] = np.maximum(nose_mask[r, c, canal],
                                        (soma / ((i1 - i0) * (j1 - j0))).astype(np.float32))


pinta_grade(selo_f, 0)                                          # R = selo
pinta_grade(vidro_f, 1)                                         # G = vidro

# Cinta clara da moldura.  Nas fotos head-on de 767 a moldura do parabrisa e
# BRANCA/prateada (nao preta como no 777), levemente mais fosca que a pintura
# do casco, e e ela que faz os seis vidros lerem como UM conjunto em vez de
# seis adesivos.  Vai na LiveryTex (cor base), nao na NoseMask: e tinta.
CINTA_COR = (0xD8, 0xD9, 0xDC)
cinta_f = _dil_metrico(vidro_f | selo_f, CINTA_M) & ~(vidro_f | selo_f) & ~poste_f
_selc = (GX >= PX0) & (GX <= PX1) & (np.degrees(GABS) >= PT0) & (np.degrees(GABS) <= PT1)
if _selc.any():
    _r, _c = np.where(_selc)
    _ix = np.clip(((GX[_selc] - PX0) / (PX1 - PX0) * npx).astype(int), 0, npx - 1)
    _jt = np.clip(((np.degrees(GABS[_selc]) - PT0) / (PT1 - PT0) * npt).astype(int),
                  0, npt - 1)
    _h = cinta_f[_jt, _ix]
    tex[_r[_h], _c[_h]] = CINTA_COR
    print(f"[parabrisa] cinta da moldura {int(_h.sum())} texels na LiveryTex")
    grava("LiveryTex", tex, False, "sRGB")      # a cinta entra depois do item 8

# area real do envidracado sobre a superficie, celula a celula com o raio
# local — o numero antes/depois que o commit cita.
_area = 0.0
_jj, _ii = np.where(vidro_f)
if len(_ii):
    _xc = PX0 + (_ii + 0.5) * sx_m
    _area = float(np.sum(sx_m * math.radians(st_g) * _raio_local(_xc))) * 2.0
print(f"[parabrisa] area de vidro na superficie: {_area:.3f} m2 (os 6 vidros)")

img = D.images.get("NoseMask")
if img is None or tuple(img.size) != (NW, NH):
    if img:
        D.images.remove(img)
    img = D.images.new("NoseMask", NW, NH, alpha=False, float_buffer=False)
px = np.ones((NH, NW, 4), np.float32)
px[..., :3] = nose_mask
img.colorspace_settings.name = "Non-Color"
img.pixels.foreach_set(px.ravel())
img.pack()
print(f"[parabrisa] selo {float(nose_mask[...,0].sum()):.0f} / vidro "
      f"{float(nose_mask[...,1].sum()):.0f} texels (cobertura, {NW}x{NH})")

# Religar o no de imagem do parabrisa: trocar a resolucao da NoseMask obriga a
# apagar e recriar a imagem, e apagar deixa o no ORFAO.  Um no de imagem vazio
# nao pinta nada de errado — pinta TUDO de errado: o Separate Color devolve
# zero, o Mix Shader some com a tinta e o nariz inteiro renderiza no material
# do selo.  Foi o que aconteceu na primeira passada desta correcao.
#
# ATENCAO: identidade de no NAO funciona no RNA do Blender — `l.from_node is
# no` e sempre falso, porque cada acesso devolve um wrapper novo.  Comparar
# por NOME.  Era exatamente esse o bug, e ele falhava em silencio.
_nt = D.materials["FuselagemPaint"].node_tree
_sep = next((n for n in _nt.nodes if n.type == "SEPARATE_COLOR"), None)
_alvo = None
if _sep is not None:
    for _l in _nt.links:
        if _l.to_node.name == _sep.name and _l.from_node.type == "TEX_IMAGE":
            _alvo = _nt.nodes[_l.from_node.name]
            break
if _alvo is None:
    raise RuntimeError("parabrisa: no de imagem da NoseMask nao encontrado")
_alvo.image = img
_alvo.image.colorspace_settings.name = "Non-Color"
print(f"[parabrisa] no '{_alvo.name}' religado a NoseMask {NW}x{NH}")

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

# ---- vidro do parabrisa: o painel que renderizava CLARO --------------------
# Diagnostico, porque a hipotese obvia estava errada: nao ha atribuicao de
# material por painel.  Os seis vidros sao UMA regiao do canal G da NoseMask
# alimentando UM BSDF, e os parametros do 767 eram identicos aos do 777
# aprovado (Roughness 0.05, Coat 0.85, Coat Roughness 0.03).  O painel claro e
# o reflexo ESPECULAR do CloudCard — uma area light de 60x20 m com 8000 W em
# (15, -25, 30) — num vidro quase espelho.  O mesmo reflexo aparece no
# render_headon do 777, la como uma lasca fina; no 767 o nariz e muito mais
# rombudo e os paineis maiores, entao o lobo cobre um painel inteiro e le como
# vidro faltando.  Reflexo em parabrisa e real; borda dura e artefato.  Basta
# afastar o lobo do espelho puro: a mancha vira brilho com gradiente.
_ntv = D.materials["FuselagemPaint"].node_tree
_glass = _ntv.nodes.get("Principled BSDF.002")
if _glass:
    _glass.inputs["Roughness"].default_value = 0.14
    _glass.inputs["Coat Weight"].default_value = 0.55
    _glass.inputs["Coat Roughness"].default_value = 0.11
    print("[parabrisa] vidro: rough 0.05->0.14, coat 0.85->0.55, "
          "coat rough 0.03->0.11 (lobo do CloudCard)")
_selo = _ntv.nodes.get("Principled BSDF.001")
if _selo:
    # selo de borracha, nao pintura preta brilhante
    _selo.inputs["Base Color"].default_value = (0.020, 0.021, 0.023, 1.0)
    _selo.inputs["Roughness"].default_value = 0.68

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
