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
# PT-TMT (photo-measured, render-matched): the boundary is a curved swoosh —
# forward at the crown, sweeping AFT going down (opposite lean to the A320's),
# then running low toward the tailcone. Quadratic fit through the rectified
# photo points; door 4 leaf follows the boundary (white ring outlines it).
_bpts = np.array([(2.10, 24.25), (1.00, 24.85), (0.00, 25.45),
                  (-0.70, 26.10), (-1.00, 26.90)])
_A = np.stack([np.ones(len(_bpts)), _bpts[:, 0], _bpts[:, 0] ** 2], 1)
_c = np.linalg.lstsq(_A, _bpts[:, 1], rcond=None)[0]
def X_BOUND(z):
    zz = np.clip(z, -1.05, 2.4)
    return _c[0] + _c[1] * zz + _c[2] * zz * zz
Z_LOWLINE = lambda x: -1.05 + 0.26 * (x - 26.9)      # aft low edge rising to tail
REAR = lambda z: 31.30 + 0.10 * z                     # fin TE-root fairing edge
wedge = (Xg >= X_BOUND(Zg)) & (Xg <= REAR(Zg)) & (Zg >= Z_LOWLINE(Xg)) \
        & (THdeg <= 150.0)
paint(wedge, 2, 1.0)
log("wedge texels:", int(wedge.sum()), "boundary coefs", _c.round(3))

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

# reveal hidden decals and refresh matrices (stale-matrix trap)
for ob in D.objects:
    if ob.name.startswith(("LogoLATAM", "LogoBarriga", "Reg_", "MarkAirbus")):
        ob.hide_viewport = False
bpy.context.view_layer.update()

paint_side_decal(["LogoLATAM_E_Coral"], 3, side=-1)
paint_side_decal(["LogoLATAM_E"], 2, side=-1)
paint_side_decal(["LogoLATAM_D_Coral"], 3, side=+1)
paint_side_decal(["LogoLATAM_D"], 2, side=+1)
paint_belly_decal(["LogoBarriga_Coral"], 3)
paint_belly_decal(["LogoBarriga"], 2)

# ---------------------------------------------------------------- registration PT-TMT
# glyphs from the master's official Reg_E mesh ("PT-TMN"): P T - T M N
reg = D.objects["Reg_E"]
me = reg.data
me.calc_loop_triangles()
isl = mesh_islands(me)
# order islands by min x
def isl_bbox(comp):
    xs = [me.vertices[i].co.x for i in comp]
    zs = [me.vertices[i].co.z for i in comp]
    return min(xs), max(xs), min(zs), max(zs)
isl.sort(key=lambda c: isl_bbox(c)[0])
log("Reg_E islands:", len(isl), [f"{isl_bbox(c)[0]:.2f}-{isl_bbox(c)[1]:.2f}" for c in isl])
# build triangles per island in local (x, z)
vert_isl = {}
for k, comp in enumerate(isl):
    for i in comp:
        vert_isl[i] = k
tris_by_isl = {k: [] for k in range(len(isl))}
for t in me.loop_triangles:
    k = vert_isl[t.vertices[0]]
    tris_by_isl[k].append([(me.vertices[i].co.x, me.vertices[i].co.z) for i in t.vertices])
# sequence P T - T M N -> P T - T M T : replace last island with a copy of island 1 (T)
seq = [0, 1, 2, 3, 4, 1]
bb = [isl_bbox(c) for c in isl]
tris2 = []
for pos, k in enumerate(seq):
    src = tris_by_isl[k]
    tgt_slot = bb[pos] if pos < len(bb) else bb[-1]
    # place glyph k at slot pos: align glyph centre x to slot centre x
    dx = (0.5 * (tgt_slot[0] + tgt_slot[1])) - (0.5 * (bb[k][0] + bb[k][1]))
    tris2 += [[(px + dx, pz) for px, pz in t] for t in src]
# local extent -> target: x 26.30..28.10, z 0.34..0.74 (spec_a319 livery_pt_tmt)
xs = [p[0] for t in tris2 for p in t]; zs = [p[1] for t in tris2 for p in t]
lx0, lx1, lz0, lz1 = min(xs), max(xs), min(zs), max(zs)
TX0, TX1, TZ0, TZ1 = 26.45, 28.45, 0.22, 0.66
s = min((TX1 - TX0) / (lx1 - lx0), (TZ1 - TZ0) / (lz1 - lz0))
tris2 = [[(TX0 + (px - lx0) * s, TZ0 + (pz - lz0) * s) for px, pz in t] for t in tris2]
mi = tri_mask_2d(tris2, TX0 - 0.05, TX1 + 0.05, TZ0 - 0.05, TZ1 + 0.05, res=800)
selp = sample_mask(mi, Xg, Zg) & (Yg < 0) & (np.abs(np.sin(THg)) > 0.30)
XMIR = TX0 + TX1
sels = sample_mask(mi, XMIR - Xg, Zg) & (Yg > 0) & (np.abs(np.sin(THg)) > 0.30)
paint(selp | sels, 1, 1.0)
log("registration texels:", int((selp | sels).sum()))

# ---------------------------------------------------------------- title AIRBUS A319
mk = D.objects["MarkAirbusNeo_E"]
mm = mk.data
mm.calc_loop_triangles()
isl = mesh_islands(mm)
def mbox(comp):
    xs = [mm.vertices[i].co.x for i in comp]
    ys = [mm.vertices[i].co.y for i in comp]
    return min(xs), max(xs), min(ys), max(ys)
isl.sort(key=lambda c: mbox(c)[0])
log("Mark islands:", len(isl), [f"{mbox(c)[0]:.3f}" for c in isl])
vert_isl = {}
for k, comp in enumerate(isl):
    for i in comp:
        vert_isl[i] = k
mtris = {k: [] for k in range(len(isl))}
for t in mm.loop_triangles:
    k = vert_isl[t.vertices[0]]
    mtris[k].append([(mm.vertices[i].co.x, mm.vertices[i].co.y) for i in t.vertices])
n = len(isl)
# layout (11 islands): [swirl, A, I, R, B, U, S, A, 3, 2, 0+neo-merged]
# keep swirl..3 (drop the last 2: '2' and the merged '0neo'); append 1 and 9.
keep = list(range(0, n - 2))
tris2 = []
for k in keep:
    tris2 += mtris[k]
b3 = mbox(isl[keep[-1]])              # bbox of '3'
gw = b3[1] - b3[0]                    # glyph width
gap = 0.15 * gw
capz0, capz1 = b3[2], b3[3]
# find 'I' island: narrowest among kept letters
widths = [(mbox(isl[k])[1] - mbox(isl[k])[0], k) for k in keep[1:]]
wI, kI = sorted(widths)[0]
# digit 1 = copy of I stem
dx = (b3[1] + gap) - mbox(isl[kI])[0]
one_tris = [[(px + dx, py) for px, py in t] for t in mtris[kI]]
tris2 += one_tris
one_x1 = mbox(isl[kI])[1] + dx
# digit 9 = bowl (scaled '0'-like: reuse '3'? use bowl from letter 'B'? use scaled 'U'?)
# reconstruct: ring bowl from circle approximation + stem
import mathutils
bx0 = one_x1 + gap
bw = gw * 0.92
bh = (capz1 - capz0)
cx = bx0 + 0.5 * bw * 0.92
cyb = capz0 + bh * 0.62               # bowl centre (upper part)
r_out_x = 0.46 * bw; r_out_y = 0.40 * bh
r_in_x = 0.24 * bw; r_in_y = 0.20 * bh
ring = []
NSEG = 24
for i in range(NSEG):
    a0 = 2 * math.pi * i / NSEG; a1 = 2 * math.pi * (i + 1) / NSEG
    o0 = (cx + r_out_x * math.cos(a0), cyb + r_out_y * math.sin(a0))
    o1 = (cx + r_out_x * math.cos(a1), cyb + r_out_y * math.sin(a1))
    i0 = (cx + r_in_x * math.cos(a0), cyb + r_in_y * math.sin(a0))
    i1 = (cx + r_in_x * math.cos(a1), cyb + r_in_y * math.sin(a1))
    ring.append([o0, o1, i1]); ring.append([o0, i1, i0])
tris2 += ring
# stem of the 9: right side, from bowl mid down to baseline
sw = wI
sx0 = cx + r_out_x - sw
tris2.append([(sx0, capz0), (sx0 + sw, capz0), (sx0 + sw, cyb + 0.1 * bh)])
tris2.append([(sx0, capz0), (sx0 + sw, cyb + 0.1 * bh), (sx0, cyb + 0.1 * bh)])
# target: x 24.30..26.05, z 1.22..1.39, both sides, indigo
xs = [p[0] for t in tris2 for p in t]; ys = [p[1] for t in tris2 for p in t]
lx0, lx1, ly0, ly1 = min(xs), max(xs), min(ys), max(ys)
TX0, TX1, TZ0, TZ1 = 23.45, 25.20, 1.040, 1.210
s = min((TX1 - TX0) / (lx1 - lx0), (TZ1 - TZ0) / (ly1 - ly0))
tris2 = [[(TX0 + (px - lx0) * s, TZ0 + (py - ly0) * s) for px, py in t] for t in tris2]
mi = tri_mask_2d(tris2, TX0 - 0.03, TX1 + 0.03, TZ0 - 0.03, TZ1 + 0.03, res=1500)
selp = sample_mask(mi, Xg, Zg) & (Yg < 0) & (np.abs(np.sin(THg)) > 0.25)
XMIR = TX0 + TX1
sels = sample_mask(mi, XMIR - Xg, Zg) & (Yg > 0) & (np.abs(np.sin(THg)) > 0.25)
paint(selp | sels, 2, 1.0)
log("title texels:", int((selp | sels).sum()))

# ---------------------------------------------------------------- door outlines
def rounded_rect(px, pz, x0, x1, z0, z1, r):
    """signed inside-test for a rounded rect"""
    qx = np.maximum(np.maximum(x0 - px, px - x1), 0)
    qz = np.maximum(np.maximum(z0 - pz, pz - z1), 0)
    # distance outside the plain rect of the *inset* rect
    ix0, ix1, iz0, iz1 = x0 + r, x1 - r, z0 + r, z1 - r
    dx = np.maximum(np.maximum(ix0 - px, px - ix1), 0)
    dz = np.maximum(np.maximum(iz0 - pz, pz - iz1), 0)
    return np.hypot(dx, dz) <= r

def door_ring(name, band_c, band_w, groove_c, groove_w, side, far_band=False):
    ob = D.objects.get(name)
    if not ob:
        return
    vs = np.array([v.co[:] for v in ob.data.vertices])
    x0, x1 = vs[:, 0].min(), vs[:, 0].max()
    z0, z1 = vs[:, 2].min(), vs[:, 2].max()
    r = 0.15
    inner = rounded_rect(Xg, Zg, x0, x1, z0, z1, r)
    oband = rounded_rect(Xg, Zg, x0 - band_w, x1 + band_w, z0 - band_w, z1 + band_w, r)
    ogro = rounded_rect(Xg, Zg, x0 + groove_w, x1 - groove_w, z0 + groove_w, z1 - groove_w, r)
    sideok = ((Yg < 0) if side < 0 else (Yg > 0)) & (np.abs(np.sin(THg)) > 0.25)
    if far_band:
        paint((oband & ~inner) & sideok, band_c, 1.0)
    paint((inner & ~ogro) & sideok, groove_c, 1.0)
    log("door ring", name, f"x {x0:.2f}..{x1:.2f} z {z0:.2f}..{z1:.2f}")

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

# ---------------------------------------------------------------- NoseMask resample
nm = D.images["NoseMask"]
wn, hn = nm.size
buf = np.empty(wn * hn * 4, np.float32)
nm.pixels.foreach_get(buf)
buf = buf.reshape(hn, wn, 4)
xs_new = (np.arange(wn) + 0.5) / wn * L_UV
cols = xs_new / 38.0 * wn                 # master used comprimento_uv = 38.0
c0 = np.clip(cols.astype(int), 0, wn - 1)
newbuf = buf[:, c0, :]
nm.pixels.foreach_set(newbuf.ravel())
nm.pack()
log("NoseMask resampled")

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
