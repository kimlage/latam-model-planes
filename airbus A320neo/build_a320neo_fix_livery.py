"""A320neo master (PT-TMN) — ACAP corrections 2026-08-20, STAGE 2 (livery).

Run headless AFTER build_a320neo_fix_geo.py:
  blender -b "airbus A320neo/A320neo_LATAM.blend" --python "airbus A320neo/build_a320neo_fix_livery.py"

Surgical repaint of LiveryTex/LiveryFac (everything else in the texture —
lockups, belly logo, nose marks, title, weathering — is left untouched):
- ERASE everything painted in the tail zone (x >= 26): the old wedge (painted
  for the mis-placed fin and the pre-2026 boundary) and the old porta-2 ring.
  The 'AIRBUS A320neo' title is erased along with it and REPAINTED from the
  official glyph mesh (MarkAirbusNeo_E) at the spec position — protecting the
  old raster proved fragile. Also erases the old door-1 ring (0.55 m too low)
  and the old overwing-2 rings (0.38 m too far aft).
- REPAINT the wedge as resolved on ref_PT-TMN_wikimedia.jpg (door-4-anchored
  frame, 2026-08-20):
    front  x >= 28.51 + 0.63*z   (linear fit z 0.4..1.6, residuals < 0.02 m;
                                  refutes BOTH previous candidates: the planar
                                  27.39+0.8393z rode the old wrong fin, and the
                                  spec table's crown 31.3 was crown-wrap bias)
    rear   x <= interp z:[-1.2,1.6,1.8,2.05] -> x:[27.75,32.80,33.36,33.85]
                                 (measured z>=1.6; the 1.80 diagonal through the
                                  tip matches the family pattern, CC-BFO 1.83)
    below  z >= -1.2, |theta| <= 145 (white keel, tip at 27.75)
  Cross-checks: reg 27.00-28.80 clears the front line by 0.04 m at its aft-
  bottom corner and the title by 0.09 m — the fleet's almost-touching style.
- Door/overwing/cargo rings re-read from the (already corrected) meshes.
- (registration and type title: DISABLED on merge, see PINTAR_MATRICULA /
  PINTAR_TITULO below - both marks are painted by refazer_marcas.py instead).
- APU metal ring x 36.70..37.15 (= A319 33.05-33.45 + 3.73), was absent.
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


# ---------------------------------------------------------------------------
# MERGE 2026-08-21: this stage originally also painted the registration
# "PT-TMN" in INDIGO ON WHITE at x 27.00..28.80, taking the arrangement from
# the spec's `cauda_livery.matricula_atual` (an owner photo that is not in the
# repository). The (x, theta) marks round that runs AFTER this one
# (refazer_marcas.py) re-measured it on the only VERSIONED photo,
# ref_PT-TMN_wikimedia.jpg, and puts it WHITE INSIDE THE WEDGE at
# x 30.14..31.76 - which is also what the rest of the family does
# (A319 PT-TMT 26.45..28.45, A320ceo CC-BFO 30.29..31.81, A321ceo PT-MXP,
# A321neo PS-LBA: all "branca dentro do indigo"). Painting it here as well
# would leave a second, contradictory registration that the later round's
# erase boxes do not cover, so the block is switched off and the mark is left
# to refazer_marcas.py. The wedge front line below does NOT depend on it: it
# comes from the door-anchored fit (residuals < 0.02 m over z 0.4..1.6).
PINTAR_MATRICULA = False

# MERGE 2026-08-21, second finding: the title repaint below is switched off for
# the same reason plus one of its own. It re-rasterized "AIRBUS A320neo" in
# C["indigo"] (#2A0088), but the title ink on this hull is NAVY (#1C2E63,
# material AirbusNavy) - sampling the pre-merge LiveryTex over the title box
# gives 3053 texels of #1C2E63 against 2425 of #2A0088, and the #2A0088 there is
# the wedge behind it, not the letters. Painting the title indigo also blinds
# the marks round that follows: its erase reads the wedge's forward boundary
# back FROM THE PAINT by finding the first indigo column in each row, and an
# indigo title 2 m ahead of the wedge turns that read into two clusters (the fit
# came out at 92 px rms instead of 0.3). refazer_marcas.py erases this title and
# re-rasterizes it in navy at x 26.42..28.72 with an ARC height of 0.230 m, so
# it is left to do that.
PINTAR_TITULO = False
log = lambda *a: print("[A320neoL]", *a)

L_UV = 38.0
imT = D.images["LiveryTex"]
imF = D.images["LiveryFac"]
W, H = imT.size
rgb = np.array(imT.pixels[:], dtype=np.float32).reshape(H, W, 4)
facA = np.array(imF.pixels[:], dtype=np.float32).reshape(H, W, 4)

rings = json.load(open(os.path.join(BASE, "a320neo_rings.json")))
rx = np.array([r["x"] for r in rings])
rzc = np.array([r["zc"] for r in rings])
rrz = np.array([r["rz"] for r in rings])
rry = np.array([r["ry"] for r in rings])

u = (np.arange(W) + 0.5) / W
v = (np.arange(H) + 0.5) / H
X = u * L_UV
TH = v * 2 * math.pi - math.pi
Xg = np.broadcast_to(X, (H, W))
THg = np.broadcast_to(TH[:, None], (H, W))
ZCg = np.interp(X, rx, rzc)[None, :]
RZg = np.interp(X, rx, rrz)[None, :]
RYg = np.interp(X, rx, rry)[None, :]
Zg = ZCg + RZg * np.cos(THg)
Yg = RYg * np.sin(THg)
THdeg = np.degrees(np.abs(THg))

C = {
    "branco": (0.969, 0.976, 0.980),
    "indigo": (0.165, 0.000, 0.533),
    "far":    (0.624, 0.643, 0.663),
    "sulco":  (0.098, 0.106, 0.114),
    "metal":  (0.541, 0.561, 0.580),
}

R_, G_, B_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
is_indigo = (B_ > 0.30) & (R_ < 0.40)
is_coral = (R_ > 0.60) & (B_ < 0.55) & (G_ < 0.40)
is_ring = (facA[..., 0] > 0.05) & (R_ > 0.55)   # painted whites/greys/grooves

def set_px(mask, cor, f):
    for k in range(3):
        rgb[..., k][mask] = cor[k]
    facA[..., 0][mask] = f
    facA[..., 1][mask] = f
    facA[..., 2][mask] = f

# ---------------------------------------------------------------- erase
painted = is_indigo | is_coral | is_ring
tail = painted & (Xg >= 26.0)
log("erasing tail texels:", int(tail.sum()))
set_px(tail, C["branco"], 0.0)

def erase_rect(x0, x1, z0, z1):
    m = painted & (Xg >= x0) & (Xg <= x1) & (Zg >= z0) & (Zg <= z1)
    set_px(m, C["branco"], 0.0)
    log("erased rect x %.2f..%.2f z %.2f..%.2f: %d texels" % (x0, x1, z0, z1, int(m.sum())))

erase_rect(4.40, 5.68, -1.00, 1.40)     # old porta-1 ring + FAR band (door was low)
erase_rect(15.20, 16.10, -0.15, 1.15)   # old overwing-2 ring

# ---------------------------------------------------------------- wedge
front = 28.51 + 0.63 * Zg
rear = np.interp(Zg, [-1.2, 1.6, 1.8, 2.05], [27.75, 32.80, 33.36, 33.85])
wedge = (Xg >= front) & (Xg <= rear) & (Zg >= -1.2) & (THdeg <= 145.0)
set_px(wedge, C["indigo"], 1.0)
log("wedge texels:", int(wedge.sum()))

# ---------------------------------------------------------------- rings
# ------------------------------------------------------------ door rings
# UMA implementacao para as cinco Airbus: `latam_livery_kit.anel_porta`.
# Este bloco era uma copia de `door_ring()` que pintava o contorno no
# RETANGULO (x, z) — a projecao lateral — enquanto a folha vive na superficie.
# Acima do ombro os dois divergiam 0.5-0.7 m: era a "porta 1 fantasma".
# O contorno agora e descrito em (x, w), com w = arco da secao. Ver
# `airbus A320neo/portas_familia.py` para a medicao e para o assentamento das
# folhas, que tinham o mesmo erro NA MALHA.
_WG = kit.grade_arco(rx, rrz, rry, X, TH)

def door_ring(name, band_cor, band_w, groove_cor, groove_w, side, far_band=False):
    ob = D.objects.get(name)
    if ob is None:
        return
    caixa = kit.caixa_porta_xw(ob, rx, rzc, rrz, rry)
    banda, sulco = kit.anel_porta(Xg, _WG, caixa, band_w, groove_w, 0.15)
    sideok = ((Yg < 0) if side < 0 else (Yg > 0)) & (np.abs(np.sin(THg)) > 0.25)
    if far_band:
        set_px(banda & sideok, band_cor, 1.0)
    set_px(sulco & sideok, groove_cor, 1.0)
    log("door ring", name, "x %.2f..%.2f w %.3f..%.3f" % caixa)

door_ring("Porta1_E", C["far"], 0.05, C["sulco"], 0.010, side=-1, far_band=True)
door_ring("Porta1_D", C["far"], 0.05, C["sulco"], 0.010, side=+1, far_band=True)
door_ring("Porta2_E", C["branco"], 0.058, C["branco"], 0.010, side=-1, far_band=True)
door_ring("Porta2_D", C["branco"], 0.058, C["branco"], 0.010, side=+1, far_band=True)
for on, sd in (("Overwing1_E", -1), ("Overwing2_E", -1), ("Overwing1_D", +1), ("Overwing2_D", +1)):
    door_ring(on, C["far"], 0.03, C["sulco"], 0.008, side=sd, far_band=False)
for cn in ("PortaCargaFwd", "PortaCargaAft", "PortaCargaBulk"):
    door_ring(cn, C["far"], 0.03, C["sulco"], 0.009, side=+1, far_band=False)

# --------------------------------------------- flat-art rasterizer helpers
def tri_mask_2d(tris, x0, x1, y0, y1, res=900):
    nx = max(int((x1 - x0) * res), 4)
    ny = max(int((y1 - y0) * res), 4)
    m = np.zeros((ny, nx), bool)
    gx, gy = np.meshgrid(np.arange(nx) + 0.5, np.arange(ny) + 0.5)
    gx = x0 + gx * (x1 - x0) / nx
    gy = y0 + gy * (y1 - y0) / ny
    for (ax, ay), (bx, by), (cx, cy) in tris:
        d1 = (gx - bx) * (ay - by) - (ax - bx) * (gy - by)
        d2 = (gx - cx) * (by - cy) - (bx - cx) * (gy - cy)
        d3 = (gx - ax) * (cy - ay) - (cx - ax) * (gy - ay)
        m |= ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
    return m, (x0, x1, y0, y1)

def sample_mask(mi, px, py):
    m, (x0, x1, y0, y1) = mi
    ny, nx = m.shape
    ii = ((px - x0) / (x1 - x0) * nx).astype(int)
    jj = ((py - y0) / (y1 - y0) * ny).astype(int)
    ok = (ii >= 0) & (ii < nx) & (jj >= 0) & (jj < ny)
    out = np.zeros(px.shape, bool)
    out[ok] = m[jj[ok], ii[ok]]
    return out


# ---------------------------------------------------------------- registration
if PINTAR_MATRICULA:
    cu = D.curves.new("RegTmp", type='FONT')
    cu.body = "PT-TMN"
    cu.font = D.fonts["Arial Bold"]
    cu.size = 1.0
    ob = D.objects.new("RegTmp", cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    tris2 = [[(me.vertices[i].co.x, me.vertices[i].co.y) for i in t.vertices]
             for t in me.loop_triangles]
    xs = [p[0] for t in tris2 for p in t]
    ys = [p[1] for t in tris2 for p in t]
    lx0, lx1, ly0, ly1 = min(xs), max(xs), min(ys), max(ys)
    TZ0, TZ1, TX1 = 0.52, 0.89, 28.80
    s = (TZ1 - TZ0) / (ly1 - ly0)
    TX0 = TX1 - (lx1 - lx0) * s
    tris2 = [[(TX0 + (px - lx0) * s, TZ0 + (py - ly0) * s) for px, py in t] for t in tris2]
    log("registration 'PT-TMN': x %.2f..%.2f z %.2f..%.2f" % (TX0, TX1, TZ0, TZ1))

    mi = tri_mask_2d(tris2, TX0 - 0.05, TX1 + 0.05, TZ0 - 0.05, TZ1 + 0.05)
    selp = sample_mask(mi, Xg, Zg) & (Yg < 0) & (np.abs(np.sin(THg)) > 0.30)
    sels = sample_mask(mi, (TX0 + TX1) - Xg, Zg) & (Yg > 0) & (np.abs(np.sin(THg)) > 0.30)
    set_px(selp | sels, C["indigo"], 1.0)
    log("registration texels:", int((selp | sels).sum()))
    ob.evaluated_get(dg).to_mesh_clear()
    D.objects.remove(ob, do_unlink=True)
    D.curves.remove(cu)

# ---------------------------------------------------------------- title
if PINTAR_TITULO:
    # 'AIRBUS A320neo' from the official glyph mesh, spec position x 27.0..29.3
    # z 1.22..1.39 (owner-photo current arrangement; clears the new front line
    # by 0.09 m at its top-aft corner).
    mk = D.objects["MarkAirbusNeo_E"]
    mm = mk.data
    mm.calc_loop_triangles()
    ttris = [[(mm.vertices[i].co.x, mm.vertices[i].co.y) for i in t.vertices]
             for t in mm.loop_triangles]
    xs = [p[0] for t in ttris for p in t]
    ys = [p[1] for t in ttris for p in t]
    lx0, lx1, ly0, ly1 = min(xs), max(xs), min(ys), max(ys)
    TX0, TX1, TZ0, TZ1 = 27.00, 29.30, 1.22, 1.39
    s = (TX1 - TX0) / (lx1 - lx0)   # width-driven: spec z band is CAPS height;
    # the mesh box includes the 'neo' swirl descender (cf. A321 titulo note)
    ttris = [[(TX0 + (px - lx0) * s, TZ0 + (py - ly0) * s) for px, py in t] for t in ttris]
    txs = [p[0] for t in ttris for p in t]
    log("title: x %.2f..%.2f z %.2f..%.2f" % (min(txs), max(txs), TZ0, TZ0 + (ly1 - ly0) * s))
    TXe = max(txs)
    mi = tri_mask_2d(ttris, TX0 - 0.03, TXe + 0.03, TZ0 - 0.03, TZ1 + 0.03, res=1500)
    selp = sample_mask(mi, Xg, Zg) & (Yg < 0) & (np.abs(np.sin(THg)) > 0.25)
    sels = sample_mask(mi, (TX0 + TXe) - Xg, Zg) & (Yg > 0) & (np.abs(np.sin(THg)) > 0.25)
    set_px(selp | sels, C["indigo"], 1.0)
    log("title texels:", int((selp | sels).sum()))

# ---------------------------------------------------------------- APU ring
sel = (Xg > 36.70) & (Xg < 37.15) & (facA[..., 0] < 0.05)
set_px(sel, C["metal"], 0.55)
log("APU ring texels:", int(sel.sum()))

# ---------------------------------------------------------------- write back
imT.pixels.foreach_set(rgb.ravel())
imT.pack()
imF.pixels.foreach_set(facA.ravel())
imF.pack()
bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
