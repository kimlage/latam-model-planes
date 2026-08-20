"""Fix: the SVG interval clustering merged kerned glyphs ('A3','2','1','neo'),
so 'neo' was kept and the painted title reads A321neo. Erase and repaint,
dropping clusters whose max height is below cap (lowercase 'neo')."""
import bpy
import bmesh
import math
import os
import numpy as np

D = bpy.data
W, H = 4096, 1024
L_UV = 45.0
NAVY = np.array([0.110, 0.180, 0.388])
log = lambda *a: print("[A321ceo]", *a)

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

img = D.images["LiveryTex"]
tex = np.empty(W * H * 4, dtype=np.float32); img.pixels.foreach_get(tex)
tex = tex.reshape(H, W, 4)
imgf = D.images["LiveryFac"]
fac = np.empty(W * H * 4, dtype=np.float32); imgf.pixels.foreach_get(fac)
fac = fac.reshape(H, W, 4)

# erase the badly painted title (both sides)
m = (XG > 32.80) & (XG < 34.95) & (ZG > 0.78) & (ZG < 1.18) & SIDE
fac[m, 0:3] = 0.0
log("bad title erased (unconditional box):", int(m.sum()))

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
me321 = D.meshes.new("a321_mark_tmp2")
bmn.to_mesh(me321)
bmn.free()
me321.calc_loop_triangles()

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
# the SVG holds 4 outlines: [A+3], [2], [1], [neo] — 'neo' is one path
# spanning 0.314..0.505 of the width (checked in the SVG source). Keep <=0.31.
span = clusters[-1][1]
keep = [c for c in clusters if c[1] <= 0.62 * span]
for c in clusters:
    log(f"cluster {c[0]:.3f}..{c[1]:.3f} {'KEEP' if c in keep else 'drop'}")
tris321_raw = [t for c in keep for t in c[2]]
k0 = min(c[0] for c in keep); k1 = max(c[1] for c in keep)
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

img.pixels.foreach_set(tex.astype(np.float32).ravel()); img.pack()
imgf.pixels.foreach_set(fac.astype(np.float32).ravel()); imgf.pack()
bpy.ops.wm.save_mainfile()
print("SAVED", D.filepath)
