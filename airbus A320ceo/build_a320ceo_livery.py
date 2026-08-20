"""A320ceo livery — STAGE 2 (textures), CC-BFO.

Run headless:
  blender -b "airbus A320ceo/A320ceo_LATAM.blend" --python "airbus A320ceo/build_a320ceo_livery.py"

Regenerates LiveryTex/LiveryFac (4096x1024, supersampled 2x, comprimento_uv=38.0):
- white hull + indigo rear wedge measured on the CC-BFO photos (spec_a320ceo.json);
- LATAM lockup port/starboard/belly from the official flat meshes (master positions);
- registration CC-BFO white inside the wedge, BOTH sides (Arial Bold, the
  master's registration font), x 30.36..31.80 z 0.88..1.42;
- 'AIRBUS A320' title from the official logotype glyphs ('0' ring reconstructed);
- door outlines (porta 2 white ring inside the indigo), overwing pair, cargo;
- APU metal ring 36.7..37.15; light weathering.
NoseMask and PanelBump inherited from the master (same hull, same UV).
"""
import bpy
import json
import math
import os
import numpy as np

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))
log = lambda *a: print("[A320ceoL]", *a)

L_UV = 38.0
W, H = 4096, 1024
SS = 2
Ws, Hs = W * SS, H * SS

rings = json.load(open(os.path.join(BASE, "a320ceo_rings.json")))
rx = np.array([r["x"] for r in rings])
rzc = np.array([r["zc"] for r in rings])
rrz = np.array([r["rz"] for r in rings])
rry = np.array([r["ry"] for r in rings])

u = (np.arange(Ws) + 0.5) / Ws
v = (np.arange(Hs) + 0.5) / Hs
X = u * L_UV
TH = v * 2 * math.pi - math.pi
Xg = np.broadcast_to(X, (Hs, Ws))
THg = np.broadcast_to(TH[:, None], (Hs, Ws))
ZCg = np.interp(X, rx, rzc)[None, :]
RZg = np.interp(X, rx, rrz)[None, :]
RYg = np.interp(X, rx, rry)[None, :]
Zg = ZCg + RZg * np.cos(THg)
Yg = RYg * np.sin(THg)
THdeg = np.degrees(np.abs(THg))

code = np.zeros((Hs, Ws), np.uint8)
fac = np.zeros((Hs, Ws), np.float32)

COLORS = {
    1: (0.969, 0.976, 0.980),   # white
    2: (0.165, 0.000, 0.533),   # indigo #2A0088
    3: (0.929, 0.086, 0.318),   # coral #ED1651
    4: (0.624, 0.643, 0.663),   # FAR band grey
    5: (0.098, 0.106, 0.114),   # groove dark
    6: (0.541, 0.561, 0.580),   # metal ring
    7: (0.545, 0.494, 0.396),   # tan streak
    8: (0.165, 0.173, 0.180),   # dark grime
}

def paint(mask, c, f=1.0, keep=False):
    if keep:
        mask = mask & (code == 0)
    code[mask] = c
    fac[mask] = f

# ---------------------------------------------------------------- wedge CC-BFO
# spec_a320ceo.json livery_cc_bfo.echarpe (photo-measured):
wedge = (Xg >= 28.60 + 0.66 * Zg) & (Xg <= 30.35 + 1.83 * Zg) \
        & (Zg >= -1.25) & (THdeg <= 145.0)
paint(wedge, 2, 1.0)
log("wedge texels:", int(wedge.sum()))

# ---------------------------------------------------------------- decal machinery
def tri_mask_2d(tris, x0, x1, y0, y1, res=600):
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
    ob = D.objects[name]
    me = ob.data
    import mathutils
    mw = mathutils.Matrix.LocRotScale(ob.location, ob.rotation_euler, ob.scale)
    vs = [mw @ v.co for v in me.vertices]
    me.calc_loop_triangles()
    return [[vs[i] for i in t.vertices] for t in me.loop_triangles]

def paint_side_decal(names, c, side):
    tris3 = []
    for n in names:
        tris3 += mesh_tris_world(n)
    t2 = [[(p.x, p.z) for p in t] for t in tris3]
    xs = [p[0] for t in t2 for p in t]; zs = [p[1] for t in t2 for p in t]
    mi = tri_mask_2d(t2, min(xs) - 0.05, max(xs) + 0.05, min(zs) - 0.05, max(zs) + 0.05)
    sel = sample_mask(mi, Xg, Zg)
    sel &= (Yg < 0) if side < 0 else (Yg > 0)
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
    sel &= (np.cos(THg) < -0.35)
    paint(sel, c, 1.0)
    log("belly decal", names, "->", int(sel.sum()), "texels")

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

# ---------------------------------------------------------------- registration CC-BFO
# Arial Bold (the master's registration font, RegPortaTrem) typeset fresh.
cu = D.curves.new("RegCeoTmp", type='FONT')
cu.body = "CC-BFO"
cu.font = D.fonts["Arial Bold"]
cu.size = 1.0
ob = D.objects.new("RegCeoTmp", cu)
bpy.context.scene.collection.objects.link(ob)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
me = ob.evaluated_get(dg).to_mesh()
me.calc_loop_triangles()
tris2 = [[(me.vertices[i].co.x, me.vertices[i].co.y) for i in t.vertices]
         for t in me.loop_triangles]
xs = [p[0] for t in tris2 for p in t]; ys = [p[1] for t in tris2 for p in t]
lx0, lx1, ly0, ly1 = min(xs), max(xs), min(ys), max(ys)
TX0, TZ0, TZ1 = 30.29, 1.04, 1.335
s = (TZ1 - TZ0) / (ly1 - ly0)
tris2 = [[(TX0 + (px - lx0) * s, TZ0 + (py - ly0) * s) for px, py in t] for t in tris2]
TX1 = TX0 + (lx1 - lx0) * s
log("registration 'CC-BFO': x %.2f..%.2f (target right edge 31.80), z %.2f..%.2f"
    % (TX0, TX1, TZ0, TZ1))
mi = tri_mask_2d(tris2, TX0 - 0.05, TX1 + 0.05, TZ0 - 0.05, TZ1 + 0.05, res=900)
selp = sample_mask(mi, Xg, Zg) & (Yg < 0) & (np.abs(np.sin(THg)) > 0.30)
XMIR = TX0 + TX1
sels = sample_mask(mi, XMIR - Xg, Zg) & (Yg > 0) & (np.abs(np.sin(THg)) > 0.30)
paint(selp | sels, 1, 1.0)
log("registration texels:", int((selp | sels).sum()))
ob.evaluated_get(dg).to_mesh_clear()
D.objects.remove(ob, do_unlink=True)
D.curves.remove(cu)

# ---------------------------------------------------------------- title AIRBUS A320
mk = D.objects["MarkAirbusNeo_E"]
mm = mk.data
mm.calc_loop_triangles()
import collections
adj = collections.defaultdict(set)
for e in mm.edges:
    a, b = e.vertices
    adj[a].add(b); adj[b].add(a)
seen = set(); isl = []
for v0 in range(len(mm.vertices)):
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
    isl.append(comp)

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
# islands (texture-level verified): [A,I,R,B,U,S, A,3,2,0, neo] — there is no
# swirl in this mesh and the last island is 'neo' alone. Drop it, keep the rest.
keep = list(range(0, n - 1))
tris2 = []
for k in keep:
    tris2 += mtris[k]
xs = [p[0] for t in tris2 for p in t]; ys = [p[1] for t in tris2 for p in t]
lx0, lx1, ly0, ly1 = min(xs), max(xs), min(ys), max(ys)
TX0, TX1, TZ0, TZ1 = 26.21, 27.94, 1.040, 1.240
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
    ix0, ix1, iz0, iz1 = x0 + r, x1 - r, z0 + r, z1 - r
    dx = np.maximum(np.maximum(ix0 - px, px - ix1), 0)
    dz = np.maximum(np.maximum(iz0 - pz, pz - iz1), 0)
    return np.hypot(dx, dz) <= r

def door_ring(name, band_c, band_w, groove_c, groove_w, side, far_band=False):
    ob = D.objects.get(name)
    if not ob:
        return
    vs = np.array([v.co[:] for v in ob.data.vertices])
    x0, x1 = vs[:, 0].min() + ob.location.x, vs[:, 0].max() + ob.location.x
    z0, z1 = vs[:, 2].min() + ob.location.z, vs[:, 2].max() + ob.location.z
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
for on in ("Overwing1_E", "Overwing2_E"):
    door_ring(on, 4, 0.03, 5, 0.008, side=-1, far_band=False)
for on in ("Overwing1_D", "Overwing2_D"):
    door_ring(on, 4, 0.03, 5, 0.008, side=+1, far_band=False)
for cn in ("PortaCargaFwd", "PortaCargaAft", "PortaCargaBulk"):
    door_ring(cn, 4, 0.03, 5, 0.009, side=+1, far_band=False)

# ---------------------------------------------------------------- APU ring & weathering
sel = (Xg > 36.70) & (Xg < 37.15)
paint(sel, 6, 0.55, keep=True)
sel = (Xg > 6.0) & (Xg < 14.0) & (np.cos(THg) < -0.75)
fade = np.clip((14.0 - Xg) / 8.0, 0, 1) * 0.12
m = sel & (code == 0)
code[m] = 8
fac[m] = fade[m]
for dx0 in (8.55, 27.60):
    sel = (np.abs(Xg - dx0) < 0.10) & (np.cos(THg) < -0.35) & (THdeg > 115) & (THdeg < 165)
    m = sel & (code == 0)
    code[m] = 7
    fac[m] = 0.18
sel = (Xg > 16.8) & (Xg < 18.8) & (np.cos(THg) < -0.80)
m = sel & (code == 0)
code[m] = 8
fac[m] = 0.10
log("weathering painted")

# ---------------------------------------------------------------- downsample & write
rgb = np.ones((Hs, Ws, 3), np.float32)
for c, col in COLORS.items():
    m = code == c
    rgb[m] = col
rgb4 = rgb.reshape(H, SS, W, SS, 3).mean(axis=(1, 3))
fac4 = fac.reshape(H, SS, W, SS).mean(axis=(1, 3))

def write_image(name, arr_rgb, arr_a=None, colorspace="sRGB"):
    img = D.images.get(name)
    if img is None:
        img = D.images.new(name, W, H, alpha=False)
    img.colorspace_settings.name = colorspace
    out = np.ones((H, W, 4), np.float32)
    if arr_rgb is not None:
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

for ob in D.objects:
    if ob.name.startswith(("LogoLATAM", "LogoBarriga", "Reg_", "MarkAirbus")):
        ob.hide_viewport = True
        ob.hide_render = True

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
