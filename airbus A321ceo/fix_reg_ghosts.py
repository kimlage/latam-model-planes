"""SUPERADO 2026-08-27 (pintor unico): absorvido por refazer_marcas.py (tag a321ceo).
Fica como registro historico do que pintou o estado embarcado. NAO rodar.

Fix: PS-LBA anti-alias fringes survived the whiteish-only erase and read as
ghost strokes (one made the final P look like an R). Unconditionally refill the
registration box with indigo, then repaint the D4 white ring and PT-MXP."""
import bpy
import math
import numpy as np

D = bpy.data
W, H = 4096, 1024
L_UV = 45.0
INDIGO = np.array([0.165, 0.000, 0.533])
WHITE = np.array([1.0, 1.0, 1.0])
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

# hard indigo refill of the registration zone (both sides). The box lies fully
# inside the wedge (forward boundary at z1.25 is x 36.51 < 36.55).
m = (XG > 36.55) & (XG < 39.30) & (ZG > 0.52) & (ZG < 1.28) & SIDE
tex[m, 0:3] = INDIGO
fac[m, 0:3] = 1.0
log("reg zone refilled:", int(m.sum()))

def rounded_rect(px, pz, x0, x1, z0, z1, r):
    ix0, ix1, iz0, iz1 = x0 + r, x1 - r, z0 + r, z1 - r
    dx = np.maximum(np.maximum(ix0 - px, px - ix1), 0)
    dz = np.maximum(np.maximum(iz0 - pz, pz - iz1), 0)
    return np.hypot(dx, dz) <= r

for side in ("E", "D"):
    ob = D.objects["Porta4_" + side]
    vs = np.array([v.co[:] for v in ob.data.vertices])
    x0 = vs[:, 0].min() + ob.location.x; x1 = vs[:, 0].max() + ob.location.x
    z0 = vs[:, 2].min() + ob.location.z; z1 = vs[:, 2].max() + ob.location.z
    r = 0.13
    inner = rounded_rect(XG, ZG, x0, x1, z0, z1, r)
    oband = rounded_rect(XG, ZG, x0 - 0.058, x1 + 0.058, z0 - 0.058, z1 + 0.058, r)
    ogro = rounded_rect(XG, ZG, x0 + 0.010, x1 - 0.010, z0 + 0.010, z1 - 0.010, r)
    sideok = ((THG < 0) if side == "E" else (THG > 0)) & SIDE
    mm = ((oband & ~inner) | (inner & ~ogro)) & sideok
    tex[mm, 0:3] = WHITE
    fac[mm, 0:3] = 1.0
    log("D4 ring repainted", side, int(mm.sum()))

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

tris, span = text_tris("PT-MXP", 0.40, 37.15, 0.70)
n = raster_side(tris, (1.0, 1.0, 1.0), "E")
log("reg E:", n, "span", round(span, 2))
n = raster_side(mirror(tris, 37.15, 37.15 + span), (1.0, 1.0, 1.0), "D")
log("reg D:", n)

img.pixels.foreach_set(tex.astype(np.float32).ravel()); img.pack()
imgf.pixels.foreach_set(fac.astype(np.float32).ravel()); imgf.pack()
bpy.ops.wm.save_mainfile()
print("SAVED", D.filepath)
