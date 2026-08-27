"""A319 livery — STAGE 2 (textures).

Run headless:
  blender -b "airbus A319/A319_LATAM.blend" --python "airbus A319/build_a319_livery.py"

Regenerates LiveryTex/LiveryFac (4096x1024, supersampled 2x) for PT-TMT:
- white hull + indigo rear wedge measured on the PT-TMT photo (spec_a319.json);
- LATAM lockup port/starboard/belly from the official flat meshes (positions kept);
- registration PT-TMT white inside the wedge (glyphs recombined from the master's
  official Reg mesh: P,T,-,T,M,T);
- 'AIRBUS A319' title from the official logotype glyphs + reconstructed 1/9;
- door outlines (FAR band + groove; door 4 white ring inside the indigo),
  single overwing hatch, cargo doors, belly items, weathering;
- NoseMask resampled to the new u scale; PanelBump regenerated and packed.
"""
import bpy
import json
import math
import os
import numpy as np

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))

# a implementacao unica dos aneis de porta mora na raiz do repositorio
import sys as _sys
_sys.path.insert(0, os.path.dirname(BASE))
import latam_livery_kit as kit  # noqa: E402
import reparar_echarpe as _re   # noqa: E402

# CONSOLIDACAO DO PINTOR UNICO (2026-08-27): este arquivo pinta so LIVERY
# PLANA (base, cunha, aneis de porta, desgaste, PanelBump). As marcas —
# lockup (ja em refazer_marcas ha rodadas), matricula PT-TMT, titulo,
# marca do ventre — moram em refazer_marcas.py (tag a319, secao "legado
# A320-familia"). Sequencia de reconstrucao (REBUILD.md):
#     build_a319_livery.py -> portas_familia.py (aneis AA na superficie)
#                          -> refazer_marcas.py -- a319 lockup marcas
#                          -> reparar_echarpe.py -- a319 --forcar
# A cunha vem da regra unica reparar_echarpe.FROTA["a319"] — a re-medida de
# 2026-08-26 com a paralaxe de flanco corrigida; a quadratica local deste
# arquivo era a regra VELHA (inclinada ao contrario) e morreu com a rodada.

log = lambda *a: print("[A319L]", *a)

L_UV = 34.2
W, H = 4096, 1024
SS = 2
Ws, Hs = W * SS, H * SS

rings = json.load(open(os.path.join(BASE, "a319_rings.json")))
rx = np.array([r["x"] for r in rings])
rzc = np.array([r["zc"] for r in rings])
rrz = np.array([r["rz"] for r in rings])
rry = np.array([r["ry"] for r in rings])

def zc_of(x):  return np.interp(x, rx, rzc)
def rz_of(x):  return np.interp(x, rx, rrz)
def ry_of(x):  return np.interp(x, rx, rry)

# ---------------------------------------------------------------- texel grids
u = (np.arange(Ws) + 0.5) / Ws
v = (np.arange(Hs) + 0.5) / Hs
X = u * L_UV                              # (Ws,)
TH = v * 2 * math.pi - math.pi            # (Hs,) theta in [-pi, pi]; 0 = crown
Xg = np.broadcast_to(X, (Hs, Ws))
THg = np.broadcast_to(TH[:, None], (Hs, Ws))
ZCg = np.interp(X, rx, rzc)[None, :]
RZg = np.interp(X, rx, rrz)[None, :]
RYg = np.interp(X, rx, rry)[None, :]
Zg = ZCg + RZg * np.cos(THg)              # z of each texel
Yg = RYg * np.sin(THg)                    # y of each texel (port negative)
THdeg = np.degrees(np.abs(THg))

code = np.zeros((Hs, Ws), np.uint8)       # colour code per texel
fac = np.zeros((Hs, Ws), np.float32)

COLORS = {
    1: (0.969, 0.976, 0.980),   # white
    2: (0.165, 0.000, 0.533),   # indigo #2A0088
    3: (0.929, 0.086, 0.318),   # coral #ED1651
    4: (0.624, 0.643, 0.663),   # FAR band grey #9FA4A9
    5: (0.098, 0.106, 0.114),   # groove dark #191B1D
    6: (0.541, 0.561, 0.580),   # metal ring #8A8F94
    7: (0.545, 0.494, 0.396),   # tan streak
    8: (0.165, 0.173, 0.180),   # dark grime
}

def paint(mask, c, f=1.0, keep=False):
    if keep:
        mask = mask & (code == 0)
    code[mask] = c
    fac[mask] = f

# ---------------------------------------------------------------- écharpe (wedge)
# Regra unica (reparar_echarpe._r_a319, re-medida 2026-08-26), avaliada na
# grade SS2 do proprio builder sobre a tabela de aneis — que e a tabela da
# malha serializada (conferido: zc/rz/ry identicos, x a 4 mm).
wedge = _re.FROTA["a319"]["regra"](Xg, Zg, THdeg)
paint(wedge, 2, 1.0)
log("wedge texels:", int(wedge.sum()), "(regra unica _r_a319)")

# ---------------------------------------------------------------- flat-mesh masks
def mesh_islands(me):
    """connected components of a mesh -> list of vertex-index sets"""
    import collections
    adj = collections.defaultdict(set)
    for e in me.edges:
        a, b = e.vertices
        adj[a].add(b); adj[b].add(a)
    seen = set(); islands = []
    for v0 in range(len(me.vertices)):
        if v0 in seen:
            continue
        stack = [v0]; comp = set()
        while stack:
            v1 = stack.pop()
            if v1 in comp:
                continue
            comp.add(v1)
            stack.extend(adj[v1] - comp)
        seen |= comp
        islands.append(comp)
    return islands

def tri_mask_2d(tris, x0, x1, y0, y1, res=600):
    """rasterize triangles (in arbitrary 2D coords) into a lookup grid"""
    nx = max(int((x1 - x0) * res), 4); ny = max(int((y1 - y0) * res), 4)
    m = np.zeros((ny, nx), bool)
    gx, gy = np.meshgrid(np.arange(nx) + 0.5, np.arange(ny) + 0.5)
    gx = x0 + gx * (x1 - x0) / nx
    gy = y0 + gy * (y1 - y0) / ny
    for (ax, ay), (bx, by), (cx, cy) in tris:
        lo_x = min(ax, bx, cx); hi_x = max(ax, bx, cx)
        lo_y = min(ay, by, cy); hi_y = max(ay, by, cy)
        i0 = max(int((lo_x - x0) / (x1 - x0) * nx) - 1, 0)
        i1 = min(int((hi_x - x0) / (x1 - x0) * nx) + 2, nx)
        j0 = max(int((lo_y - y0) / (y1 - y0) * ny) - 1, 0)
        j1 = min(int((hi_y - y0) / (y1 - y0) * ny) + 2, ny)
        if i1 <= i0 or j1 <= j0:
            continue
        sx = gx[j0:j1, i0:i1]; sy = gy[j0:j1, i0:i1]
        d1 = (sx - bx) * (ay - by) - (ax - bx) * (sy - by)
        d2 = (sx - cx) * (by - cy) - (bx - cx) * (sy - cy)
        d3 = (sx - ax) * (cy - ay) - (cx - ax) * (sy - ay)
        inside = ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
        m[j0:j1, i0:i1] |= inside
    return m, (x0, x1, y0, y1)

def sample_mask(mask_info, px, py):
    m, (x0, x1, y0, y1) = mask_info
    ny, nx = m.shape
    ii = ((px - x0) / (x1 - x0) * nx).astype(int)
    jj = ((py - y0) / (y1 - y0) * ny).astype(int)
    ok = (ii >= 0) & (ii < nx) & (jj >= 0) & (jj < ny)
    out = np.zeros(px.shape, bool)
    out[ok] = m[jj[ok], ii[ok]]
    return out

def mesh_tris_world(name):
    """flat decal mesh -> world-space triangles in its 2 significant dims"""
    ob = D.objects[name]
    me = ob.data
    loc, rot, sca = ob.location, ob.rotation_euler, ob.scale
    import mathutils
    mw = mathutils.Matrix.LocRotScale(loc, rot, sca)
    vs = [mw @ v.co for v in me.vertices]
    tris = []
    me.calc_loop_triangles()
    for t in me.loop_triangles:
        tris.append([vs[i] for i in t.vertices])
    return tris

def paint_side_decal(names, c, side, keep_marks=True):
    """project flat meshes horizontally onto the hull side: mask in (x, z)"""
    tris3 = []
    for n in names:
        tris3 += mesh_tris_world(n)
    t2 = [[(p.x, p.z) for p in t] for t in tris3]
    xs = [p[0] for t in t2 for p in t]; zs = [p[1] for t in t2 for p in t]
    mi = tri_mask_2d(t2, min(xs) - 0.05, max(xs) + 0.05, min(zs) - 0.05, max(zs) + 0.05)
    sel = sample_mask(mi, Xg, Zg)
    sel &= (Yg < 0) if side < 0 else (Yg > 0)
    # only where the hull actually faces sideways (avoid crown/keel bleed-through)
    sel &= (np.abs(np.sin(THg)) > 0.30)
    paint(sel, c, 1.0)
    log("side decal", names, "->", int(sel.sum()), "texels")

def paint_belly_decal(names, c):
    tris3 = []
    for n in names:
        tris3 += mesh_tris_world(n)
    t2 = [[(p.x, p.y) for p in t] for t in tris3]
    xs = [p[0] for t in t2 for p in t]; ys = [p[1] for t in t2 for p in t]
    mi = tri_mask_2d(t2, min(xs) - 0.05, max(xs) + 0.05, min(ys) - 0.05, max(ys) + 0.05)
    sel = sample_mask(mi, Xg, Yg)
    sel &= (np.cos(THg) < -0.35)          # belly only
    paint(sel, c, 1.0)
    log("belly decal", names, "->", int(sel.sum()), "texels")

# MARCAS: lockup, ventre, matricula e titulo movidos para refazer_marcas.py
# (tag a319) — este builder nao pinta marca nenhuma. Ver REBUILD.md.

# (matricula PT-TMT e titulo AIRBUS A319: em refazer_marcas.py, tag a319 —
#  a matricula na caixa FINAL da rodada 2026-08-22, medida por
#  fix_matricula_a319.py na propria foto; os glifos recombinados do mesmo
#  Reg_E: P,T,-,T,M,T.)

# ---------------------------------------------------------------- door outlines
# ------------------------------------------------------------ door rings
# UMA implementacao para as cinco Airbus: `latam_livery_kit.anel_porta`.
# Este bloco era uma copia de `door_ring()` que pintava o contorno no
# RETANGULO (x, z) — a projecao lateral — enquanto a folha vive na superficie.
# Acima do ombro os dois divergiam 0.5-0.7 m: era a "porta 1 fantasma".
# O contorno agora e descrito em (x, w), com w = arco da secao. Ver
# `airbus A320neo/portas_familia.py` para a medicao e para o assentamento das
# folhas, que tinham o mesmo erro NA MALHA.
_WG = kit.grade_arco(rx, rrz, rry, X, TH)

def door_ring(name, band_c, band_w, groove_c, groove_w, side, far_band=False):
    ob = D.objects.get(name)
    if ob is None:
        return
    caixa = kit.caixa_porta_xw(ob, rx, rzc, rrz, rry)
    banda, sulco = kit.anel_porta(Xg, _WG, caixa, band_w, groove_w, 0.15)
    sideok = ((Yg < 0) if side < 0 else (Yg > 0)) & (np.abs(np.sin(THg)) > 0.25)
    if far_band:
        paint(banda & sideok, band_c, 1.0)
    paint(sulco & sideok, groove_c, 1.0)
    log("door ring", name, "x %.2f..%.2f w %.3f..%.3f" % caixa)

door_ring("Porta1_E", 4, 0.05, 5, 0.010, side=-1, far_band=True)
door_ring("Porta1_D", 4, 0.05, 5, 0.010, side=+1, far_band=True)
door_ring("Porta2_E", 1, 0.058, 1, 0.010, side=-1, far_band=True)   # white ring in indigo
door_ring("Porta2_D", 1, 0.058, 1, 0.010, side=+1, far_band=True)
door_ring("Overwing1_E", 4, 0.03, 5, 0.008, side=-1, far_band=False)
door_ring("Overwing1_D", 4, 0.03, 5, 0.008, side=+1, far_band=False)
for cn in ("PortaCargaFwd", "PortaCargaAft", "PortaCargaBulk"):
    door_ring(cn, 4, 0.03, 5, 0.009, side=+1, far_band=False)

# ---------------------------------------------------------------- belly & weathering
# APU ring (bare-ish metal) just ahead of the tailcone tip
sel = (Xg > 33.05) & (Xg < 33.45)
paint(sel, 6, 0.55, keep=True)
# nose-gear spray fan on the belly
sel = (Xg > 6.0) & (Xg < 14.0) & (np.cos(THg) < -0.75)
fade = np.clip((14.0 - Xg) / 8.0, 0, 1) * 0.14
m = sel & (code == 0)
code[m] = 8
fac[m] = fade[m]
# drain streaks (tan): fwd 8.55, aft 23.87
for dx0 in (8.55, 23.87):
    sel = (np.abs(Xg - dx0) < 0.10) & (np.cos(THg) < -0.35) & (THdeg > 115) & (THdeg < 165)
    m = sel & (code == 0)
    code[m] = 7
    fac[m] = 0.22
# gear door grime
sel = (Xg > 15.2) & (Xg < 17.2) & (np.cos(THg) < -0.80)
m = sel & (code == 0)
code[m] = 8
fac[m] = 0.10
log("weathering painted")

# ---------------------------------------------------------------- downsample & write
rgb = np.zeros((Hs, Ws, 3), np.float32)
rgb[..., 0] = 1.0
rgb[..., 1] = 1.0
rgb[..., 2] = 1.0
for c, col in COLORS.items():
    m = code == c
    rgb[m] = col
rgb4 = rgb.reshape(H, SS, W, SS, 3).mean(axis=(1, 3))
fac4 = fac.reshape(H, SS, W, SS).mean(axis=(1, 3))

def write_image(name, arr_rgb, arr_a=None, colorspace="sRGB"):
    img = D.images.get(name)
    if img is None:
        img = D.images.new(name, W, H, alpha=False)
    if img.size[0] != W or img.size[1] != H:
        img.scale(W, H)
    img.colorspace_settings.name = colorspace
    out = np.ones((H, W, 4), np.float32)
    out[..., :3] = arr_rgb
    if arr_a is not None:
        out[..., 0] = arr_a
        out[..., 1] = arr_a
        out[..., 2] = arr_a
    img.pixels.foreach_set(out.ravel())
    img.pack()
    return img

write_image("LiveryTex", rgb4, colorspace="sRGB")
write_image("LiveryFac", None, arr_a=fac4, colorspace="Non-Color")
log("LiveryTex/Fac written; painted fraction %.3f" % float((fac4 > 0).mean()))

# NoseMask: NAO tocar. O bloco que reamostrava as colunas do master (38.0 ->
# 34.2) era passo unico da DERIVACAO; a mascara embarcada e a da rodada do
# parabrisa e reamostra-la de novo a deslocaria. Dona da NoseMask e a rodada
# do parabrisa, nao este builder.

# ---------------------------------------------------------------- PanelBump
pb = D.images["PanelBump"]
wp, hp = pb.size
arr = np.full((hp, wp), 0.5, np.float32)
xs_pb = (np.arange(wp) + 0.5) / wp * L_UV
joints = [1.55, 2.65, 4.4, 5.96, 6.96, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0,
          22.27, 25.27, 28.27, 31.27, 33.0]
for j in joints:
    col = np.argmin(np.abs(xs_pb - j))
    arr[:, max(col - 1, 0):col + 1] = 0.42
# lap joints (longitudinal)
for vv in (0.36, 0.30, 0.64, 0.70, 0.14, 0.86):
    row = int(vv * hp)
    arr[row:row + 1, :] = 0.46
out = np.empty((hp, wp, 4), np.float32)
out[..., 0] = arr; out[..., 1] = arr; out[..., 2] = arr; out[..., 3] = 1.0
pb.pixels.foreach_set(out.ravel())
pb.pack()
log("PanelBump regenerated")

# hide decal helpers again
for ob in D.objects:
    if ob.name.startswith(("LogoLATAM", "LogoBarriga", "Reg_", "MarkAirbus")):
        ob.hide_viewport = True
        ob.hide_render = True

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
