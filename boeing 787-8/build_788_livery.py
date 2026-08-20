"""787-8 livery — STAGE 2 (textures), derived from the approved 787-9 paint.

Run headless:
  blender -b "boeing 787-8/B788_LATAM.blend" --python "boeing 787-8/build_788_livery.py"

Strategy (CC-BBF, photos in refs/manifest.json):
- LiveryTex/LiveryFac/PanelBump are COLUMN-RESAMPLED from the master with the
  two plug bands removed (3-zone mapping). The tail art — indigo wedge with its
  feathered boundary, DREAMLINER, door outlines, windows — lands at the -8
  positions automatically (validated by photogrammetry: DREAMLINER measured at
  x 38.8..42.2 vs 44.85..48.21-6.09 predicted; aft cargo door 0.06 m off).
- The LATAM lockup CANNOT ride the resample (on the -9 it spans 9.7..16.6 and
  the fwd plug cuts straight through it; on CC-BBF it is scaled ~0.88 ending
  clear of the -8's door 2). Erased at the source, repainted from the official
  meshes at the measured -8 position.
- Belly symbol: erased and repainted at measured x centre 11.45 (photo shows it
  under the lockup, not at the -9's painted 17-22).
- Registration: CC-BBF is WHITE INSIDE THE INDIGO ON BOTH SIDES (stbd photo of
  CC-BBF + port photo of CC-BBB) — unlike CC-BGK's asymmetry. Both -9 regs are
  erased; CC-BBF is painted from the master's official glyphs (C,C,-,B,B) plus
  an F constructed from the font's own metrics (stem/bar/cap from B and hyphen).
- NoseMask: pure u rescale (nose identical in metres).
"""
import bpy
import json
import math
import os
import numpy as np
import mathutils

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))
log = lambda *a: print("[B788L]", *a)

L_UV_8 = 57.5
L_UV_9 = 63.5
S_WING = 3.04
S_TAIL = 6.09
S1 = 13.40           # -8 coords: seam nose/wing zone  (master cut 13.40..16.44)
S2 = 34.50           # -8 coords: seam wing/tail zone  (master cut 37.54..40.59)
W, H = 4096, 1024

WHITE = np.array([0.969, 0.976, 0.980], np.float32)
INDIGO = np.array([0.165, 0.000, 0.533], np.float32)
CORAL = np.array([0.929, 0.086, 0.318], np.float32)

rings = json.load(open(os.path.join(BASE, "b788_rings.json")))
rx = np.array([r["x"] for r in rings])
rzc = np.array([r["zc"] for r in rings])
rrz = np.array([r["rz"] for r in rings])
rry = np.array([r["ry"] for r in rings])


def read_img(name):
    img = D.images[name]
    w, h = img.size
    buf = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(buf)
    return img, buf.reshape(h, w, 4)


def write_img(img, arr):
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.pack()


# ---------------------------------------------------------------- 1. source-space erase
img_tex, tex = read_img("LiveryTex")
img_fac, fac = read_img("LiveryFac")
img_pb, pb = read_img("PanelBump")

x9_cols = (np.arange(W) + 0.5) / W * L_UV_9
v_rows = (np.arange(H) + 0.5) / H            # 0 = keel(-pi) .. 0.5 crown .. 1 keel(+pi)
chroma = tex[..., :3].max(axis=2) - tex[..., :3].min(axis=2)

# lockup (both sides): chromatic texels in the column band
m = (chroma > 0.10) & (x9_cols[None, :] >= 7.2) & (x9_cols[None, :] <= 16.85)
tex[m] = list(WHITE) + [1.0]
fac[m, 0] = fac[m, 1] = fac[m, 2] = 0.0
log("lockup erased:", int(m.sum()), "texels")

# belly symbol (keel rows near the v seam)
keel = (v_rows < 0.16) | (v_rows > 0.84)
m = (chroma > 0.10) & keel[:, None] & (x9_cols[None, :] >= 16.6) & (x9_cols[None, :] <= 23.0)
tex[m] = list(WHITE) + [1.0]
fac[m, 0] = fac[m, 1] = fac[m, 2] = 0.0
log("belly symbol erased:", int(m.sum()), "texels")

# ---------------------------------------------------------------- 2. column resample
def x8_to_x9(x8):
    x9 = np.where(x8 <= S1, x8, np.where(x8 < S2, x8 + S_WING, x8 + S_TAIL))
    return x9


x8_cols = (np.arange(W) + 0.5) / W * L_UV_8
src = x8_to_x9(x8_cols) / L_UV_9 * W - 0.5
c0 = np.clip(np.floor(src).astype(int), 0, W - 1)
c1 = np.clip(c0 + 1, 0, W - 1)
f = np.clip(src - c0, 0.0, 1.0).astype(np.float32)
oob = src > W - 0.5

tex = tex[:, c0, :] * (1 - f)[None, :, None] + tex[:, c1, :] * f[None, :, None]
fac = fac[:, c0, :] * (1 - f)[None, :, None] + fac[:, c1, :] * f[None, :, None]
pb = pb[:, c0, :] * (1 - f)[None, :, None] + pb[:, c1, :] * f[None, :, None]
tex[:, oob, :3] = WHITE
fac[:, oob, :3] = 0.0
pb[:, oob, :3] = 0.5
log("column resample done; oob cols:", int(oob.sum()))

# ---------------------------------------------------------------- texel grids (-8 coords)
X = x8_cols
TH = (np.arange(H) + 0.5) / H * 2 * math.pi - math.pi     # -pi..pi, 0 = crown
Xg = np.broadcast_to(X, (H, W))
THg = np.broadcast_to(TH[:, None], (H, W))
ZCg = np.interp(X, rx, rzc)[None, :]
RZg = np.interp(X, rx, rrz)[None, :]
RYg = np.interp(X, rx, rry)[None, :]
Zg = ZCg + RZg * np.cos(THg)
Yg = RYg * np.sin(THg)
THdeg = np.degrees(np.abs(THg))

# -8 wedge rule (the -9's, shifted -6.09; validated on the CC-BBF photo)
def wedge_mask(margin=0.0):
    return ((Xg >= 42.68 + 0.992 * Zg - margin) &
            (THdeg <= 117.0 - 5.2 * (Xg - 42.61) + margin * 5) &
            (Xg <= 51.05 + 0.3858 * Zg + margin))


# ---------------------------------------------------------------- 3. erase both regs
# The -9's PAINTED regs do not match its decal objects (objects are stale);
# find the glyphs by content. Post-resample coords: white-in-indigo reg at
# x ~47.9..51.9 (was 54..58), indigo-on-white at ~48.5..50.3 (was 54.6..56.4).
lum = tex[..., :3].mean(axis=2)
inw = wedge_mask(-0.10)
xband = (Xg >= 45.5) & (Xg <= 52.6)
m1 = xband & inw & (lum > 0.55) & (np.abs(np.sin(THg)) > 0.10)
tex[m1, :3] = INDIGO
fac[m1, 0] = fac[m1, 1] = fac[m1, 2] = 1.0
chroma8 = tex[..., :3].max(axis=2) - tex[..., :3].min(axis=2)
m2 = (Xg >= 44.3) & (Xg <= 52.6) & ~wedge_mask(0.15) & (chroma8 > 0.10)
tex[m2, :3] = WHITE
fac[m2, 0] = fac[m2, 1] = fac[m2, 2] = 0.0
if m1.sum():
    jj, ii = np.nonzero(m1)
    log("reg erase white-in-wedge:", int(m1.sum()), "x %.2f..%.2f" % (Xg[0, ii.min()], Xg[0, ii.max()]))
if m2.sum():
    jj, ii = np.nonzero(m2)
    log("reg erase chroma-out:", int(m2.sum()), "x %.2f..%.2f" % (Xg[0, ii.min()], Xg[0, ii.max()]))

# ---------------------------------------------------------------- decal rasterizer
def mesh_islands(me):
    import collections
    adj = collections.defaultdict(set)
    for e in me.edges:
        a, b = e.vertices
        adj[a].add(b)
        adj[b].add(a)
    seen = set()
    islands = []
    for v0 in range(len(me.vertices)):
        if v0 in seen:
            continue
        stack = [v0]
        comp = set()
        while stack:
            v1 = stack.pop()
            if v1 in comp:
                continue
            comp.add(v1)
            stack.extend(adj[v1] - comp)
        seen |= comp
        islands.append(comp)
    return islands


def tris_of(ob, world=True, islands=None):
    me = ob.data
    me.calc_loop_triangles()
    if world:
        mw = mathutils.Matrix.LocRotScale(ob.location, ob.rotation_euler, ob.scale)
        vs = [mw @ v.co for v in me.vertices]
    else:
        vs = [v.co.copy() for v in me.vertices]
    keep = None
    if islands is not None:
        keep = set()
        for comp in islands:
            keep |= comp
    tris = []
    for t in me.loop_triangles:
        if keep is not None and t.vertices[0] not in keep:
            continue
        tris.append([vs[i] for i in t.vertices])
    return tris


def coverage(tris2, PA, PB, gate, ss=3):
    """anti-aliased coverage of 2D triangles sampled at texel coords (PA,PB),
    restricted to texels passing `gate`. Supersample ss x ss per texel."""
    xs = [p[0] for t in tris2 for p in t]
    ys = [p[1] for t in tris2 for p in t]
    x0, x1 = min(xs) - 0.05, max(xs) + 0.05
    y0, y1 = min(ys) - 0.05, max(ys) + 0.05
    res = max(int(3000 / max(x1 - x0, y1 - y0)), 400)
    nx = max(int((x1 - x0) * res), 8)
    ny = max(int((y1 - y0) * res), 8)
    grid = np.zeros((ny, nx), bool)
    gx, gy = np.meshgrid((np.arange(nx) + 0.5) / nx * (x1 - x0) + x0,
                         (np.arange(ny) + 0.5) / ny * (y1 - y0) + y0)
    for (ax, ay), (bx, by), (cx, cy) in tris2:
        i0 = max(int((min(ax, bx, cx) - x0) / (x1 - x0) * nx) - 1, 0)
        i1 = min(int((max(ax, bx, cx) - x0) / (x1 - x0) * nx) + 2, nx)
        j0 = max(int((min(ay, by, cy) - y0) / (y1 - y0) * ny) - 1, 0)
        j1 = min(int((max(ay, by, cy) - y0) / (y1 - y0) * ny) + 2, ny)
        if i1 <= i0 or j1 <= j0:
            continue
        sx = gx[j0:j1, i0:i1]
        sy = gy[j0:j1, i0:i1]
        d1 = (sx - bx) * (ay - by) - (ax - bx) * (sy - by)
        d2 = (sx - cx) * (by - cy) - (bx - cx) * (sy - cy)
        d3 = (sx - ax) * (cy - ay) - (cx - ax) * (sy - ay)
        inside = ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
        grid[j0:j1, i0:i1] |= inside
    cov = np.zeros((H, W), np.float32)
    jj, ii = np.nonzero(gate)
    if len(ii) == 0:
        return cov
    pa = PA[jj, ii]
    pb = PB[jj, ii]
    acc = np.zeros(len(ii), np.float32)
    for oa in range(ss):
        for ob_ in range(ss):
            # texel footprint: ~14 mm in x (u), ~18 mm along the hull arc (v)
            da = (oa + 0.5) / ss - 0.5
            db = (ob_ + 0.5) / ss - 0.5
            sa = pa + da * (L_UV_8 / W)
            sb = pb + db * 0.018
            ci = ((sa - x0) / (x1 - x0) * nx).astype(int)
            cj = ((sb - y0) / (y1 - y0) * ny).astype(int)
            ok = (ci >= 0) & (ci < nx) & (cj >= 0) & (cj < ny)
            hit = np.zeros(len(ii), bool)
            hit[ok] = grid[cj[ok], ci[ok]]
            acc += hit
    cov[jj, ii] = acc / (ss * ss)
    return cov


def composite(cov, color, fmax=1.0):
    m = cov > 0.003
    a = cov[m][:, None]
    tex[m, :3] = tex[m, :3] * (1 - a) + np.asarray(color)[None, :] * a
    for ch in range(3):
        fac[m, ch] = np.maximum(fac[m, ch], cov[m] * fmax)
    return int(m.sum())


def paint_side(obs, color, side, islands_of=None):
    tris3 = []
    for nm in obs:
        ob = D.objects[nm]
        isl = islands_of(ob) if islands_of else None
        tris3 += tris_of(ob, world=True, islands=isl)
    tris2 = [[(p.x, p.z) for p in t] for t in tris3]
    gate = ((Yg < 0) if side < 0 else (Yg > 0)) & (np.abs(np.sin(THg)) > 0.30)
    cov = coverage(tris2, Xg, Zg, gate)
    n = composite(cov, color)
    log("side decal", obs, "side", side, "->", n, "texels")


# ---------------------------------------------------------------- 4. lockup repaint
for nm in ("B789_LogoLATAM_E", "B789_LogoLATAM_E_Coral",
           "B789_LogoLATAM_D", "B789_LogoLATAM_D_Coral",
           "LogoBarriga", "LogoBarriga_Coral", "MarkDreamliner"):
    ob = D.objects.get(nm)
    if ob:
        ob.hide_viewport = False
bpy.context.view_layer.update()

paint_side(["B789_LogoLATAM_E_Coral"], CORAL, side=-1)
paint_side(["B789_LogoLATAM_E"], INDIGO, side=-1)
paint_side(["B789_LogoLATAM_D_Coral"], CORAL, side=+1)
paint_side(["B789_LogoLATAM_D"], INDIGO, side=+1)

# ---------------------------------------------------------------- 5. belly symbol
# symbol-only: islands of the indigo lockup mesh in the symbol zone (local x<1.35)
ob = D.objects["LogoBarriga"]
me = ob.data
isl = mesh_islands(me)
sym_isl = []
for comp in isl:
    xs = [me.vertices[i].co.x for i in comp]
    if max(xs) < 1.35:
        sym_isl.append(comp)
log("belly symbol islands:", len(sym_isl), "of", len(isl))
tris_sym = tris_of(ob, world=False, islands=sym_isl)
obc = D.objects["LogoBarriga_Coral"]
tris_cor = tris_of(obc, world=False)

# local bbox of the symbol (indigo+coral share the frame)
allpts = [(p.x, p.y) for t in tris_sym + tris_cor for p in t]
lx0 = min(p[0] for p in allpts); lx1 = max(p[0] for p in allpts)
ly0 = min(p[1] for p in allpts); ly1 = max(p[1] for p in allpts)
# target: width 3.12 m centred at x 11.45, centred on y=0, coral tip to the nose
sW = 3.12 / (lx1 - lx0)
TX0 = 11.45 - 0.5 * 3.12
TY0 = -0.5 * (ly1 - ly0) * sW


def to_belly(tris):
    return [[(TX0 + (p.x - lx0) * sW, TY0 + (p.y - ly0) * sW) for p in t] for t in tris]


gate_belly = (np.cos(THg) < -0.35)
cov = coverage(to_belly(tris_cor), Xg, Yg, gate_belly)
n1 = composite(cov, CORAL)
cov = coverage(to_belly(tris_sym), Xg, Yg, gate_belly)
n2 = composite(cov, INDIGO)
log("belly symbol painted:", n1, "+", n2, "texels at x %.2f..%.2f" % (TX0, TX0 + 3.12))

# ---------------------------------------------------------------- 6. registration CC-BBF
reg = D.objects["Reg787_E"]
me = reg.data
isl = mesh_islands(me)


def ibox(comp):
    xs = [me.vertices[i].co.x for i in comp]
    zs = [me.vertices[i].co.y for i in comp]
    return min(xs), max(xs), min(zs), max(zs)


isl.sort(key=lambda c: ibox(c)[0])
log("Reg787_E glyph islands:", len(isl), [f"{ibox(c)[0]:.3f}-{ibox(c)[1]:.3f}" for c in isl])
vert_isl = {}
for k, comp in enumerate(isl):
    for i in comp:
        vert_isl[i] = k
me.calc_loop_triangles()
tris_by = {k: [] for k in range(len(isl))}
for t in me.loop_triangles:
    k = vert_isl[t.vertices[0]]
    tris_by[k].append([(me.vertices[i].co.x, me.vertices[i].co.y) for i in t.vertices])
bb = [ibox(c) for c in isl]
capH = max(b[3] for b in bb)
hyph = min(range(len(isl)), key=lambda k: (bb[k][3] - bb[k][2]))       # thinnest = '-'
tbar = bb[hyph][3] - bb[hyph][2]
log("cap height %.3f, bar thickness %.3f (island %d)" % (capH, tbar, hyph))
# sequence C C - B G K -> C C - B B F
seq = [0, 1, 2, 3, 3]
tris2 = []
for pos, k in enumerate(seq):
    slot = bb[pos]
    dxg = 0.5 * (slot[0] + slot[1]) - 0.5 * (bb[k][0] + bb[k][1])
    tris2 += [[(px + dxg, py) for px, py in t] for t in tris_by[k]]
# constructed F in slot 5 (K's slot)
s5 = bb[5]
wF = (s5[1] - s5[0]) * 0.92
fx0 = s5[0]
sw = tbar * 1.10                       # stem width ~ bar thickness
z0, z1 = 0.0, capH


def rect(x0, x1, y0, y1):
    return [[(x0, y0), (x1, y0), (x1, y1)], [(x0, y0), (x1, y1), (x0, y1)]]


tris2 += rect(fx0, fx0 + sw, z0, z1)                                   # stem
tris2 += rect(fx0, fx0 + wF, z1 - tbar, z1)                            # top arm
zm = 0.54 * capH
tris2 += rect(fx0, fx0 + 0.82 * wF, zm - 0.5 * tbar, zm + 0.5 * tbar)  # mid arm

# world placement, measured on the CC-BBF photo (stbd): the F's forward edge at
# x 44.26, cap height ~0.50, letters z ~0.78..1.3. Both sides identical (CC-BBB
# port photo shows the same white-in-indigo treatment on the -8s).
xs_l = [p[0] for t in tris2 for p in t]
ys_l = [p[1] for t in tris2 for p in t]
lx0, lx1 = min(xs_l), max(xs_l)
ly0, ly1 = min(ys_l), max(ys_l)
s = 0.50 / (ly1 - ly0)                     # cap height 0.50 m
TX1, TZ0 = 46.90, 0.78                     # aft end so that fwd (F) edge lands at 44.26
TX0 = TX1 - (lx1 - lx0) * s
tris2w = [[(TX0 + (px - lx0) * s, TZ0 + (py - ly0) * s) for px, py in t] for t in tris2]
xs = [p[0] for t in tris2w for p in t]
zs = [p[1] for t in tris2w for p in t]
log("reg CC-BBF world bbox x %.2f..%.2f z %.2f..%.2f" % (min(xs), max(xs), min(zs), max(zs)))

gate = (Yg < 0) & (np.abs(np.sin(THg)) > 0.25)
cov = coverage(tris2w, Xg, Zg, gate)
n1 = composite(cov, WHITE)
XMIR = min(xs) + max(xs)
tris2m = [[(XMIR - px, pz) for px, pz in t] for t in tris2w]
gate = (Yg > 0) & (np.abs(np.sin(THg)) > 0.25)
cov = coverage(tris2m, Xg, Zg, gate)
n2 = composite(cov, WHITE)
log("registration painted: port", n1, "stbd", n2)

# ---------------------------------------------------------------- 7. write textures
write_img(img_tex, np.concatenate([tex[..., :3], np.ones((H, W, 1), np.float32)], axis=2))
write_img(img_fac, np.concatenate([fac[..., :1].repeat(3, axis=2), np.ones((H, W, 1), np.float32)], axis=2))
write_img(img_pb, np.concatenate([pb[..., :3], np.ones((H, W, 1), np.float32)], axis=2))
log("LiveryTex/Fac/PanelBump written")

# ---------------------------------------------------------------- 8. NoseMask rescale
img_nm, nmb = read_img("NoseMask")
src = x8_cols / L_UV_9 * W - 0.5
c0 = np.clip(np.floor(src).astype(int), 0, W - 1)
c1 = np.clip(c0 + 1, 0, W - 1)
f = np.clip(src - c0, 0, 1).astype(np.float32)
nmb = nmb[:, c0, :] * (1 - f)[None, :, None] + nmb[:, c1, :] * f[None, :, None]
write_img(img_nm, nmb)
log("NoseMask resampled")

# debug crops of the final texture for eye verification
try:
    from PIL import Image as PILImage
    arr8 = (np.clip(tex[..., :3], 0, 1) * 255).astype(np.uint8)
    arr8 = arr8[::-1, :, :]        # Blender row 0 = bottom
    full = PILImage.fromarray(arr8)
    full.crop((int(5 / L_UV_8 * W), 0, int(19 / L_UV_8 * W), H)).resize((1400, 1024)).save(
        os.path.join(BASE, "refs", "dbg_tex_fwd.png"))
    full.crop((int(38 / L_UV_8 * W), 0, int(57.4 / L_UV_8 * W), H)).resize((1382, 1024)).save(
        os.path.join(BASE, "refs", "dbg_tex_tail.png"))
    full.crop((int(8 / L_UV_8 * W), 0, int(24 / L_UV_8 * W), H)).resize((1140, 1024)).save(
        os.path.join(BASE, "refs", "dbg_tex_belly.png"))
    log("debug crops written to refs/")
except Exception as e:
    log("debug crop failed:", e)

# hide decal helpers again
for ob in D.objects:
    if ob.name.startswith(("B789_Logo", "LogoBarriga", "Reg787", "MarkDreamliner")):
        ob.hide_viewport = True
        ob.hide_render = True

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
