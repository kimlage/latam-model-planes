"""Fix: starboard (D) copies of the NEW marks must be x-mirrored in (x,theta)
texture space to read correctly on the aircraft. Erase the bad ones, repaint."""
import bpy
import math
import numpy as np

D = bpy.data
W, H = 4096, 1024
L_NEW = 45.0
INDIGO = np.array([0.165, 0.000, 0.533])
NAVY = np.array([0.110, 0.180, 0.388])

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

ux = (np.arange(W) + 0.5) / W * L_NEW
vv = (np.arange(H) + 0.5) / H
TH = vv * 2 * math.pi - math.pi
XG = np.broadcast_to(ux, (H, W))
THG = np.broadcast_to(TH[:, None], (H, W))
ZG = np.broadcast_to(zc_of(ux), (H, W)) + np.broadcast_to(r_of(ux), (H, W)) * np.cos(THG)

def load(name):
    img = D.images[name]
    a = np.empty(W * H * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(H, W, 4)
tex = load("LiveryTex")
fac = load("LiveryFac")

# --- erase bad starboard marks ------------------------------------------------
D_side = THG > 0
# reg on the wedge: restore indigo where whiteish glyphs sit
m = D_side & (XG > 36.6) & (XG < 38.9) & (ZG > 0.62) & (ZG < 1.18) \
    & (tex[..., 0] > 0.5) & (tex[..., 1] > 0.5)
tex[m, 0:3] = INDIGO
fac[m, 0:3] = 1.0
print("reg D erased:", int(m.sum()))
# title on white: fac off where navy
m = D_side & (XG > 33.35) & (XG < 35.62) & (ZG > 0.82) & (ZG < 1.12) \
    & (tex[..., 2] - tex[..., 0] > 0.05)
fac[m, 0:3] = 0.0
print("title D erased:", int(m.sum()))

# --- rasterizer (with mirroring for D) ---------------------------------------
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
            pix.append((x / L_NEW * Ws, (th + math.pi) / (2 * math.pi) * Hs))
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
        m = ~((((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0))))
        cov[ylo:yhi + 1, xlo:xhi + 1] |= m
    frac = cov.reshape(H, ss, W, ss).mean(axis=(1, 3))
    m = frac > 0.02
    a = frac[m][:, None]
    tex[m, 0:3] = tex[m, 0:3] * (1 - a) + np.asarray(cor)[None, :] * a
    fac[m, 0:3] = np.maximum(fac[m, 0:3], a)
    return int(m.sum())

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

# registration D (mirrored)
tris, span = text_tris("PS-LBA", 0.40, 36.78, 0.70)
n = raster_side(mirror(tris, 36.78, 36.78 + span), (1.0, 1.0, 1.0), "D")
print("reg D repainted:", n, "span", round(span, 2))

# title D (mirrored assembly)
mark = D.objects["MarkAirbusNeo_E"]
me = mark.data
me.calc_loop_triangles()
xs_loc = sorted(set(round(v.co.x, 4) for v in me.vertices))
ga = max((b - a, a) for a, b in zip(xs_loc[:-1], xs_loc[1:]))[1]
airbus_v = [v.co for v in me.vertices if v.co.x <= ga + 1e-5]
ax0 = min(v.x for v in airbus_v); ax1 = max(v.x for v in airbus_v)
ay0 = min(v.y for v in airbus_v); ay1 = max(v.y for v in airbus_v)
s = 0.145 / (ay1 - ay0)
X0 = 33.55
tris = []
for tri in me.loop_triangles:
    pts = [me.vertices[i].co for i in tri.vertices]
    if max(p.x for p in pts) <= ga + 1e-5:
        tris.append([((p.x - ax0) * s + X0, 0.0, (p.y - ay0) * s + 0.88) for p in pts])
me321 = D.meshes.get("a321neo_mark")
if me321 is None:
    import bmesh, os
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
    me321 = D.meshes.new("a321neo_mark")
    bmn.to_mesh(me321)
    bmn.free()
xs = [v.co.x for v in me321.vertices]; ys = [v.co.y for v in me321.vertices]
n0, m0, m1 = min(xs), min(ys), max(ys)
s321 = 0.145 / ((m1 - m0) / 1.12)
XA = X0 + (ax1 - ax0) * s + 0.10
me321.calc_loop_triangles()
tris321 = []
for tri in me321.loop_triangles:
    pts = [me321.vertices[i].co for i in tri.vertices]
    tris321.append([((p.x - n0) * s321 + XA, 0.0, (p.y - m0) * s321 + 0.88) for p in pts])
xend = XA + (max(xs) - n0) * s321
allt = mirror(tris + tris321, X0, xend)
n = raster_side(allt, NAVY, "D")
print("title D repainted:", n, "span", round(xend - X0, 2))

img = D.images["LiveryTex"]; img.pixels.foreach_set(tex.astype(np.float32).ravel()); img.pack()
img = D.images["LiveryFac"]; img.pixels.foreach_set(fac.astype(np.float32).ravel()); img.pack()
bpy.ops.wm.save_mainfile()
print("SAVED")
