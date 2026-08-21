"""A321ceo PT-MXP — phase 2: livery texture deltas.

Run: blender -b "airbus A321ceo/A321ceo_LATAM.blend" --python "airbus A321ceo/build_a321ceo_fase2_livery.py"

The wedge, fin sash, LATAM lockups and belly stay EXACTLY as inherited from the
A321neo (measured identical on PT-XPB: forward boundary 35.52+0.816z vs neo
35.48+0.822z, rms 0.06 — see medir_echarpe_xpb2.py). Deltas:
- overwing hatch outlines erased (ceo has none);
- D3 ring 26.82 -> repainted at 24.79 in ceo exit size; new D2 ring at 13.84;
- cargo fwd/aft rings -0.40 (8.56->8.16, 30.02->29.62);
- PS-LBA -> PT-MXP (white in the wedge, x 37.15, both sides, D mirrored);
- title AIRBUS A321neo -> AIRBUS A321, aft end at 34.75 (measured on two ceo
  photos: XPB 34.65, PT-MXP-2024 ~34.77 by window count);
- moderate weathering (2014 airframe): gear spray fan, drain streaks;
- nose-gear door text LBA -> MXP.
"""
import bpy
import bmesh
import math
import os
import numpy as np

D = bpy.data
W, H = 4096, 1024
L_UV = 45.0
INDIGO = np.array([0.165, 0.000, 0.533])
NAVY = np.array([0.110, 0.180, 0.388])
FAR_GREY = np.array([0.624, 0.643, 0.663])
GROOVE = np.array([0.098, 0.106, 0.114])
log = lambda *a: print("[A321ceo]", *a)

# ------------------------------------------------ hull section geometry
fus = D.objects["Fuselagem"]
rings = {}
for v in fus.data.vertices:
    rings.setdefault(round(v.co.x, 3), []).append(v.co)
rx, rzc, rr = [], [], []
for k in sorted(rings):
    vs = rings[k]
    if len(vs) < 8:
        continue
    zmax = max(p.z for p in vs); zmin = min(p.z for p in vs)
    rx.append(k); rzc.append((zmax + zmin) / 2); rr.append((zmax - zmin) / 2)
def zc_of(x): return np.interp(x, rx, rzc)
def r_of(x):  return np.interp(x, rx, rr)

ux = (np.arange(W) + 0.5) / W * L_UV
vv = (np.arange(H) + 0.5) / H
TH = vv * 2 * math.pi - math.pi
XG = np.broadcast_to(ux, (H, W))
THG = np.broadcast_to(TH[:, None], (H, W))
ZG = np.broadcast_to(zc_of(ux), (H, W)) + np.broadcast_to(r_of(ux), (H, W)) * np.cos(THG)
SIDE = np.abs(np.sin(THG)) > 0.25

def load(name):
    img = D.images[name]
    a = np.empty(W * H * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(H, W, 4)

def store(name, arr):
    img = D.images[name]
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.pack()

tex = load("LiveryTex")
fac = load("LiveryFac")

# ------------------------------------------------ erase overwing outlines
m = (XG > 18.20) & (XG < 20.15) & (ZG > -0.6) & (ZG < 1.7) & SIDE
n0 = int((fac[..., 0][m] > 0.05).sum())
fac[m, 0:3] = 0.0
log("overwing outlines erased:", n0, "painted texels in zone")

# ------------------------------------------------ erase old D3 ring (26.82)
m = (XG > 26.15) & (XG < 27.50) & (ZG > -1.15) & (ZG < 1.55) & SIDE
n0 = int((fac[..., 0][m] > 0.05).sum())
fac[m, 0:3] = 0.0
log("old D3 ring erased:", n0)

# ------------------------------------------------ move cargo rings -0.40
def cap_paste(x0s, x1s, dx, v0, v1):
    r0, r1 = int(v0 * H), int(v1 * H)
    j0, j1 = int(x0s / L_UV * W), int(x1s / L_UV * W)
    keep_t = tex[r0:r1, j0:j1].copy()
    keep_f = fac[r0:r1, j0:j1].copy()
    fac[r0:r1, j0:j1, 0:3] = 0.0
    p0 = int((x0s + dx) / L_UV * W)
    tex[r0:r1, p0:p0 + (j1 - j0)] = keep_t
    fac[r0:r1, p0:p0 + (j1 - j0)] = keep_f

cap_paste(7.45, 9.70, -0.40, 0.77, 0.93)     # fwd cargo 8.56 -> 8.16
cap_paste(28.90, 31.15, -0.40, 0.77, 0.93)   # aft cargo 30.02 -> 29.62
log("cargo rings moved -0.40")

# ------------------------------------------------ door rings (paint helpers)
# SUPERADO 2026-08-21. Este `door_ring` pinta o contorno no RETANGULO (x, z) —
# a projecao lateral — e por isso desloca o anel 0.5-0.7 m acima do ombro (a
# "porta 1 fantasma"). A implementacao correta, em (x, w) com w = arco da secao,
# e `latam_livery_kit.anel_porta`, e quem repinta os quatro aneis desta aeronave
# e `build_a321ceo_fase3_acap.py`, que roda DEPOIS desta fase e ja usa o kit.
# Nao da para trocar aqui sem mais: esta fase monta a tabela de aneis com apenas
# (x, zc, r) — secao circular — e o arco precisa dos dois semi-eixos.
def rounded_rect(px, pz, x0, x1, z0, z1, r):
    ix0, ix1, iz0, iz1 = x0 + r, x1 - r, z0 + r, z1 - r
    dx = np.maximum(np.maximum(ix0 - px, px - ix1), 0)
    dz = np.maximum(np.maximum(iz0 - pz, pz - iz1), 0)
    return np.hypot(dx, dz) <= r

def door_ring(name, band_cor, band_w, groove_cor, groove_w, far_band=True):
    ob = D.objects[name]
    vs = np.array([v.co[:] for v in ob.data.vertices])
    x0 = vs[:, 0].min() + ob.location.x; x1 = vs[:, 0].max() + ob.location.x
    z0 = vs[:, 2].min() + ob.location.z; z1 = vs[:, 2].max() + ob.location.z
    r = 0.13
    inner = rounded_rect(XG, ZG, x0, x1, z0, z1, r)
    oband = rounded_rect(XG, ZG, x0 - band_w, x1 + band_w, z0 - band_w, z1 + band_w, r)
    ogro = rounded_rect(XG, ZG, x0 + groove_w, x1 - groove_w, z0 + groove_w, z1 - groove_w, r)
    sideok = ((THG < 0) if name.endswith("E") else (THG > 0)) & SIDE
    if far_band:
        mm = (oband & ~inner) & sideok
        tex[mm, 0:3] = band_cor; fac[mm, 0:3] = 1.0
    mm = (inner & ~ogro) & sideok
    tex[mm, 0:3] = groove_cor; fac[mm, 0:3] = 1.0
    log("ring", name, f"x {x0:.2f}..{x1:.2f} z {z0:.2f}..{z1:.2f}")

for side in ("E", "D"):
    door_ring("Porta2_" + side, FAR_GREY, 0.05, GROOVE, 0.010)
    door_ring("Porta3_" + side, FAR_GREY, 0.05, GROOVE, 0.010)

# ------------------------------------------------ registration PS-LBA -> PT-MXP
# erase: whiteish inside the wedge box (catches old reg AND the D4 ring bits;
# the ring is repainted deterministically right after)
for side_mask, lbl in ((THG < 0, "E"), (THG > 0, "D")):
    m = side_mask & (XG > 36.55) & (XG < 39.00) & (ZG > 0.55) & (ZG < 1.25) \
        & (tex[..., 0] > 0.5) & (tex[..., 1] > 0.5)
    tex[m, 0:3] = INDIGO
    fac[m, 0:3] = 1.0
    log("reg erased", lbl, int(m.sum()))
# repaint the D4 white ring (was clipped by the erase box)
WHITE = np.array([1.0, 1.0, 1.0])
for side in ("E", "D"):
    door_ring("Porta4_" + side, WHITE, 0.058, WHITE, 0.010)

def raster_side(tris, cor, lado, ss=2):
    Ws, Hs = W * ss, H * ss
    cov = np.zeros((Hs, Ws), dtype=bool)
    for pts in tris:
        pix = []
        for (x, _, z) in pts:
            r = max(r_of(x), 1e-6)
            ct = float(np.clip((z - zc_of(x)) / r, -1, 1))
            th = math.acos(ct)
            if lado == "E":
                th = -th
            pix.append((x / L_UV * Ws, (th + math.pi) / (2 * math.pi) * Hs))
        xs = [p[0] for p in pix]; ys = [p[1] for p in pix]
        xlo, xhi = max(int(min(xs)), 0), min(int(max(xs)) + 1, Ws - 1)
        ylo, yhi = max(int(min(ys)), 0), min(int(max(ys)) + 1, Hs - 1)
        if xhi <= xlo or yhi <= ylo:
            continue
        gx, gy = np.meshgrid(np.arange(xlo, xhi + 1), np.arange(ylo, yhi + 1))
        (ax, ay), (bx, by), (cx, cy) = pix
        d1 = (gx - bx) * (ay - by) - (ax - bx) * (gy - by)
        d2 = (gx - cx) * (by - cy) - (bx - cx) * (gy - cy)
        d3 = (gx - ax) * (cy - ay) - (cx - ax) * (gy - ay)
        mm = ~((((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0))))
        cov[ylo:yhi + 1, xlo:xhi + 1] |= mm
    frac = cov.reshape(H, ss, W, ss).mean(axis=(1, 3))
    mm = frac > 0.02
    a = frac[mm][:, None]
    tex[mm, 0:3] = tex[mm, 0:3] * (1 - a) + np.asarray(cor)[None, :] * a
    fac[mm, 0:3] = np.maximum(fac[mm, 0:3], a)
    return int(mm.sum())

def mirror(tris, x0, x1):
    return [[(x0 + x1 - x, y, z) for (x, y, z) in pts] for pts in tris]

def text_tris(body, cap, x_at, z_at):
    cu = D.curves.new("t", 'FONT')
    cu.body = body
    cu.font = D.fonts["Arial Bold"]
    cu.size = 1.0
    ob = D.objects.new("t", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    s = cap / (max(ys) - min(ys))
    x0b, y0b = min(xs), min(ys)
    me.calc_loop_triangles()
    tris = []
    for tri in me.loop_triangles:
        pts = [me.vertices[i].co for i in tri.vertices]
        tris.append([((p.x - x0b) * s + x_at, 0.0, (p.y - y0b) * s + z_at) for p in pts])
    span = (max(xs) - min(xs)) * s
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    return tris, span

REG_X, REG_Z = 37.15, 0.70
tris, span = text_tris("PT-MXP", 0.40, REG_X, REG_Z)
n = raster_side(tris, (1.0, 1.0, 1.0), "E")
log("reg E painted:", n, "span", round(span, 2), "-> x", REG_X, "..", round(REG_X + span, 2))
n = raster_side(mirror(tris, REG_X, REG_X + span), (1.0, 1.0, 1.0), "D")
log("reg D painted:", n)

# ------------------------------------------------ title AIRBUS A321neo -> AIRBUS A321
# erase old title, both sides (navy on white -> fac off)
m = (XG > 33.30) & (XG < 35.75) & (ZG > 0.80) & (ZG < 1.16) & SIDE \
    & (tex[..., 2] - tex[..., 0] > 0.04)
fac[m, 0:3] = 0.0
log("old title erased:", int(m.sum()))

# swirl+AIRBUS from the master mark (local coords, x <= word gap)
mark = D.objects["MarkAirbusNeo_E"]
me = mark.data
me.calc_loop_triangles()
xs_loc = sorted(set(round(v.co.x, 4) for v in me.vertices))
ga = max((b - a, a) for a, b in zip(xs_loc[:-1], xs_loc[1:]))[1]
airbus_v = [v.co for v in me.vertices if v.co.x <= ga + 1e-5]
ax0 = min(v.x for v in airbus_v); ax1 = max(v.x for v in airbus_v)
ay0 = min(v.y for v in airbus_v); ay1 = max(v.y for v in airbus_v)
s_air = 0.145 / (ay1 - ay0)
L_air = (ax1 - ax0) * s_air

# 'A321' = first 4 glyph clusters of the official A321neo SVG
svg = os.path.abspath(os.path.join(os.path.dirname(D.filepath), "..", "airbus_a321neo_logo.svg"))
before = set(D.objects)
bpy.ops.import_curve.svg(filepath=svg)
imported = [o for o in D.objects if o not in before]
bmn = bmesh.new()
dg = bpy.context.evaluated_depsgraph_get()
for o in imported:
    mev = o.evaluated_get(dg).to_mesh()
    vmap = {}
    for p in mev.polygons:
        nv = []
        for vi in p.vertices:
            if vi not in vmap:
                vmap[vi] = bmn.verts.new(o.matrix_world @ mev.vertices[vi].co)
            nv.append(vmap[vi])
        try:
            bmn.faces.new(nv)
        except ValueError:
            pass
    o.evaluated_get(dg).to_mesh_clear()
for o in imported:
    bpy.data.objects.remove(o, do_unlink=True)
bmesh.ops.triangulate(bmn, faces=bmn.faces[:])
me321 = D.meshes.new("a321_mark_tmp")
bmn.to_mesh(me321)
bmn.free()
me321.calc_loop_triangles()

# glyph clustering on triangle x-intervals
ivs = []
for tri in me321.loop_triangles:
    pts = [me321.vertices[i].co for i in tri.vertices]
    ivs.append((min(p.x for p in pts), max(p.x for p in pts), tri))
ivs.sort(key=lambda t: t[0])
clusters = []
for lo, hi, tri in ivs:
    if clusters and lo <= clusters[-1][1] + 1e-6:
        clusters[-1][1] = max(clusters[-1][1], hi)
        clusters[-1][2].append(tri)
    else:
        clusters.append([lo, hi, [tri]])
log("svg glyph clusters:", len(clusters),
    [f"{c[0]:.3f}..{c[1]:.3f}" for c in clusters])
keep = clusters[:4]                      # A, 3, 2, 1
tris321_raw = [t for c in keep for t in c[2]]
k0 = keep[0][0]; k1 = keep[3][1]
kys = [me321.vertices[i].co.y for c in keep for t in c[2] for i in t.vertices]
cap321 = max(kys) - min(kys)
s321 = 0.145 / cap321
L_321 = (k1 - k0) * s321
ky0 = min(kys)

GAP = 0.10
X_END = 34.75
X0 = X_END - (L_air + GAP + L_321)
log(f"title: L_air {L_air:.2f} + gap {GAP} + L_321 {L_321:.2f} -> X0 {X0:.2f}, end {X_END}")

tris_air = []
for tri in me.loop_triangles:
    pts = [me.vertices[i].co for i in tri.vertices]
    if max(p.x for p in pts) <= ga + 1e-5:
        tris_air.append([((p.x - ax0) * s_air + X0, 0.0, (p.y - ay0) * s_air + 0.88) for p in pts])
XA = X0 + L_air + GAP
tris_321 = []
for tri in tris321_raw:
    pts = [me321.vertices[i].co for i in tri.vertices]
    tris_321.append([((p.x - k0) * s321 + XA, 0.0, (p.y - ky0) * s321 + 0.88) for p in pts])
allt = tris_air + tris_321
n = raster_side(allt, NAVY, "E")
log("title E painted:", n)
n = raster_side(mirror(allt, X0, X_END), NAVY, "D")
log("title D painted:", n)
D.meshes.remove(me321)

# ------------------------------------------------ weathering (2014 airframe)
clean = fac[..., 0] < 0.05
# nose-gear spray fan on the belly
sel = (XG > 6.0) & (XG < 14.0) & (np.cos(THG) < -0.75) & clean
fade = np.clip((14.0 - XG) / 8.0, 0, 1) * 0.12
tex[sel, 0:3] = np.array([0.28, 0.29, 0.30])
fac[sel, 0:3] = fade[sel][:, None]
log("spray fan texels:", int(sel.sum()))
# drain streaks
THDEG = np.degrees(np.abs(THG))
for dx0 in (8.55, 34.54):
    sel = (np.abs(XG - dx0) < 0.10) & (THDEG > 115) & (THDEG < 165) & clean
    tex[sel, 0:3] = np.array([0.55, 0.47, 0.35])
    fac[sel, 0:3] = 0.20
    log(f"drain streak at {dx0}: {int(sel.sum())} texels")

store("LiveryTex", tex)
store("LiveryFac", fac)
log("livery stored")

# ------------------------------------------------ nose gear door text
D.objects["RegPortaTrem"].data.body = "MXP"

bpy.ops.wm.save_mainfile()
print("SAVED", D.filepath)
