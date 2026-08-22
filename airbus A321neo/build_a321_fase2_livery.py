"""A321neo PS-LBA — phase 2: livery texture, marks, materials.

Run: blender -b --factory-startup "airbus A321neo/A321neo_LATAM.blend" -P build_a321_fase2_livery.py

Everything measured on ref_PS-LBO_wikimedia_DSC00834.jpg (see medir_echarpe_v2.py):
  fwd wedge boundary   x >= 35.48 + 0.822*z
  lower wedge boundary theta <= max(129.0 - 23.7*(x-34.45), 105.3 - 3.78*(x-36.05))
  rear boundary        x <= 41.46 + 0.0538*z   (fin TE line, +6.94 from A320)
  title "AIRBUS A321neo": x 33.55..35.35, caps z 0.88..1.03 (cap 0.145 m)
  registration PS-LBA: white in the wedge, x 36.75.., cap 0.40 m, bottom z 0.70
The old A320 texture is remapped column-wise with the same piecewise map used
for the hull, then fixed: cargo/overwing outlines moved, PT-TMN marks erased,
wedge boundary re-solved, new marks rasterized.
"""
import bpy
import bmesh
import math
import numpy as np

D = bpy.data
W, H = 4096, 1024
L_OLD, L_NEW = 38.0, 45.0
CUT1, CUT2, D_FWD, D_TOT = 11.5, 26.4, 4.26, 6.94
BRANCO = np.array([0.969, 0.976, 0.980])
INDIGO = np.array([0.165, 0.000, 0.533])

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
rx = np.array(rx); rzc = np.array(rzc); rr = np.array(rr)
def zc_of(x): return np.interp(x, rx, rzc)
def r_of(x):  return np.interp(x, rx, rr)

# texel grids
ux = (np.arange(W) + 0.5) / W * L_NEW               # x per column
vv = (np.arange(H) + 0.5) / H                        # v per row
TH = vv * 2 * math.pi - math.pi                      # theta in [-pi, pi], 0 = crown
XG = np.broadcast_to(ux, (H, W))
THG = np.broadcast_to(TH[:, None], (H, W))
ZCG = np.broadcast_to(zc_of(ux), (H, W))
RG = np.broadcast_to(r_of(ux), (H, W))
ZG = ZCG + RG * np.cos(THG)                          # z of each texel
THDEG = np.degrees(np.abs(THG))                      # angle from crown, symmetric

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

# ------------------------------------------------ column remap (old -> new)
def src_x_of(xn):
    if xn <= CUT1: return xn
    if xn <= CUT1 + D_FWD: return 19.0 + (xn % 2.0)          # plug: clean barrel tile
    if xn <= CUT2 + D_FWD: return xn - D_FWD
    if xn <= CUT2 + D_TOT: return 19.0 + (xn % 2.0)          # aft plug tile
    return xn - D_TOT

src_cols = np.array([src_x_of(x) / L_OLD * W - 0.5 for x in ux])
c0 = np.clip(np.floor(src_cols).astype(int), 0, W - 1)
c1 = np.clip(c0 + 1, 0, W - 1)
t = np.clip(src_cols - c0, 0, 1)[None, :, None]
tex = tex[:, c0, :] * (1 - t) + tex[:, c1, :] * t
fac = fac[:, c0, :] * (1 - t) + fac[:, c1, :] * t
print("remap done")

# NoseMask: metre-identity remap (content lives in the nose only)
nm = load("NoseMask")
src_cols = ux / L_OLD * W - 0.5
c0 = np.clip(np.floor(src_cols).astype(int), 0, W - 1)
c1n = np.clip(c0 + 1, 0, W - 1)
t = np.clip(src_cols - c0, 0, 1)[None, :, None]
valid = (ux < L_OLD - 0.2)
nm2 = nm[:, c0, :] * (1 - t) + nm[:, c1n, :] * t
nm2[:, ~valid, :] = 0.0
store("NoseMask", nm2)
print("nosemask remapped")

# ------------------------------------------------ helpers
def box(x0, x1, z0, z1, lado="ambos"):
    """texel mask for x/z box on one or both sides."""
    m = (XG >= x0) & (XG <= x1) & (ZG >= z0) & (ZG <= z1)
    if lado == "E":   m &= THG < 0
    elif lado == "D": m &= THG > 0
    return m

def bluish(a):
    return (a[..., 2] - a[..., 0] > 0.05) & (a[..., 2] > 0.08)

def erase(mask):
    fac[mask, 0:3] = 0.0
    if fac.shape[2] > 3: fac[mask, 3] = 1.0

# capture/paste for outline moves: work on COLUMN bands within a v range
def cap_paste(x0s, x1s, dx, v0, v1, clear_ranges):
    """capture tex/fac in src cols [x0s,x1s] rows v0..v1, clear old zones, paste at +dx."""
    r0, r1 = int(v0 * H), int(v1 * H)
    j0, j1 = int(x0s / L_NEW * W), int(x1s / L_NEW * W)
    keep_t = tex[r0:r1, j0:j1].copy()
    keep_f = fac[r0:r1, j0:j1].copy()
    for (cx0, cx1) in clear_ranges:
        q0, q1 = int(cx0 / L_NEW * W), int(cx1 / L_NEW * W)
        fac[r0:r1, q0:q1, 0:3] = 0.0
    p0 = int((x0s + dx) / L_NEW * W)
    tex[r0:r1, p0:p0 + (j1 - j0)] = keep_t
    fac[r0:r1, p0:p0 + (j1 - j0)] = keep_f

# ------------------------------------------------ outline moves
# after the remap: fwd cargo ring sits at its OLD metres (7.24..9.08, x<=CUT1)
cap_paste(7.10, 9.25, +0.40, 0.77, 0.93, [(7.10, 9.25)])        # fwd cargo -> 8.56
cap_paste(26.00, 27.92, +3.07, 0.77, 0.93, [(26.00, 27.92)])    # aft cargo 26.95 -> 30.02
# bulk: torn across the cut; erase both fragments, rebuild by pasting from the
# aft fragment source... simplest: erase fragments and paste the ORIGINAL bulk
# columns from the +6.94 region (they landed intact at 32.74..33.72 already).
r0, r1 = int(0.77 * H), int(0.93 * H)
for (cx0, cx1) in [(29.95, 30.75)]:                              # +4.26 fragment
    q0, q1 = int(cx0 / L_NEW * W), int(cx1 / L_NEW * W)
    fac[r0:r1, q0:q1, 0:3] = 0.0
# overwing outline 2: landed at 19.61..20.23, want 19.23..19.85
for vb in [(0.23, 0.35), (0.65, 0.77)]:
    cap_paste(19.55, 20.30, -0.38, vb[0], vb[1], [(19.55, 20.30)])
# door 3: copy D1's painted ring/FAR band to +21.78 on both sides
for vb in [(0.15, 0.38), (0.62, 0.85)]:
    cap_paste(4.45, 5.65, +21.78, vb[0], vb[1], [])
print("outlines moved")

# ------------------------------------------------ erase PT-TMN-specific marks
m = box(3.15, 6.25, -0.85, -0.02) & bluish(tex)                  # nose titles/logo
erase(m)
m = box(36.9, 38.45, 0.95, 1.50) & bluish(tex)                   # old reg (remapped)
erase(m)
m = box(33.70, 37.05, 1.10, 1.55) & bluish(tex)                  # old type titles
erase(m)
print("old marks erased")

# ------------------------------------------------ wedge re-solve
def inside(xg, zg, thdeg, x_fwd0, k_fwd, th_lines, x_te0, k_te):
    ok = xg >= x_fwd0 + k_fwd * zg
    ok &= xg <= x_te0 + k_te * zg
    cap = np.full_like(xg, -1e9)
    for (t0, slope, xr) in th_lines:
        cap = np.maximum(cap, t0 + slope * (xg - xr))
    ok &= thdeg <= cap
    return ok

old_in = inside(XG, ZG, THDEG, 34.33, 0.8393,
                [(101.4, -7.58, 36.05)], 41.46, 0.0538)
new_in = inside(XG, ZG, THDEG, 35.48, 0.822,
                [(129.0, -23.7, 34.45), (105.3, -3.78, 36.05)], 41.46, 0.0538)
zone = (XG > 32.0) & (XG < 43.0)
flat_w = (np.abs(tex[..., 0:3] - BRANCO).max(axis=2) < 0.06) | (fac[..., 0] < 0.15)
flat_i = np.abs(tex[..., 0:3] - INDIGO).max(axis=2) < 0.08
to_white = zone & old_in & ~new_in & (flat_i | bluish(tex))
to_indigo = zone & new_in & ~old_in & flat_w
fac[to_white, 0:3] = 0.0
tex[to_indigo, 0:3] = INDIGO
fac[to_indigo, 0:3] = 1.0
print("wedge: -%d texels, +%d texels" % (to_white.sum(), to_indigo.sum()))

# ------------------------------------------------ new marks (rasterized)
def tris_of_object(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    out = []
    for tri in me.loop_triangles:
        out.append([tuple(ob.matrix_world @ me.vertices[i].co) for i in tri.vertices])
    ob.evaluated_get(dg).to_mesh_clear()
    return out

def raster_side(tris, cor, lado, fac_val=1.0, ss=2):
    """rasterize flat (x,z) triangles onto the hull side texture via z->theta."""
    Ws, Hs = W * ss, H * ss
    cov = np.zeros((Hs, Ws), dtype=bool)
    for pts in tris:
        pix = []
        for (x, _, z) in pts:
            r = max(r_of(x), 1e-6)
            ct = np.clip((z - zc_of(x)) / r, -1, 1)
            th = math.acos(ct)
            if lado == "E":
                th = -th
            u = x / L_NEW * Ws
            v = (th + math.pi) / (2 * math.pi) * Hs
            pix.append((u, v))
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
    # downsample coverage to fraction
    frac = cov.reshape(H, ss, W, ss).mean(axis=(1, 3))
    m = frac > 0.02
    a = frac[m][:, None]
    tex[m, 0:3] = tex[m, 0:3] * (1 - a) + np.asarray(cor)[None, :] * a
    fac[m, 0:3] = np.maximum(fac[m, 0:3], (a * fac_val))
    return int(m.sum())

def text_mesh(body, size, name):
    cu = D.curves.new(name, 'FONT')
    cu.body = body
    cu.font = D.fonts["Arial Bold"]
    cu.size = size
    ob = D.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    mo = D.objects.new(name + "_mesh", me)
    bpy.context.scene.collection.objects.link(mo)
    bpy.data.objects.remove(ob, do_unlink=True)
    return mo

# --- registration PS-LBA, white inside the wedge (factory style, press photo)
NAVY = np.array([0.110, 0.180, 0.388])
# NOTA (auditoria de espelhamento da frota): os dois lacos `for lado in
# ("E", "D")` abaixo rasterizam OS MESMOS triangulos nos dois bordos, e
# raster_side() so troca o SINAL DE THETA -- nunca o x. Vista de estibordo a
# pele corre para o outro lado, entao a matricula e o titulo saiam ao
# contrario. Isto NAO e corrigido aqui: quem corrige e
# build_a321_fase2b_espelho.py, que apaga as duas marcas do lado D e as repinta
# espelhadas, e e ele que tem de rodar depois deste arquivo. Deixado como esta
# para que o par de scripts continue descrevendo o que de facto aconteceu; se
# um dia este arquivo for a unica fonte, o espelho tem de vir para ca.
for lado in ("E", "D"):
    mo = text_mesh("PS-LBA", 1.0, "RegTmp")
    xs = [v.co.x for v in mo.data.vertices]; ys = [v.co.y for v in mo.data.vertices]
    x0b, x1b, y0b, y1b = min(xs), max(xs), min(ys), max(ys)
    cap = y1b - y0b
    s = 0.40 / cap
    for v in mo.data.vertices:
        vx = (v.co.x - x0b) * s + 36.78
        vz = (v.co.y - y0b) * s + 0.70
        v.co = (vx, 0.0, vz)
    n = raster_side(tris_of_object(mo), (1.0, 1.0, 1.0), lado)
    print("reg", lado, n, "texels; length", round((x1b - x0b) * s, 2))
    bpy.data.objects.remove(mo, do_unlink=True)

# --- title AIRBUS A321neo: reuse the AIRBUS part of the old mark + official SVG
mark = D.objects["MarkAirbusNeo_E"]
xs_loc = sorted(set(round(v.co.x, 4) for v in mark.data.vertices))
# find the word gap: largest x gap in vertex positions
gaps = [(b - a, a, b) for a, b in zip(xs_loc[:-1], xs_loc[1:])]
gap, ga, gb = max(gaps)
print("mark word gap: %.4f at %.3f..%.3f (local)" % (gap, ga, gb))
# AIRBUS = local x <= ga ; measure its bbox
airbus_v = [v.co for v in mark.data.vertices if v.co.x <= ga + 1e-5]
ax0 = min(v.x for v in airbus_v); ax1 = max(v.x for v in airbus_v)
ay0 = min(v.y for v in airbus_v); ay1 = max(v.y for v in airbus_v)
cap_old = ay1 - ay0
s = 0.145 / cap_old
print("AIRBUS local bbox %.3fx%.3f -> scaled len %.3f" % (ax1 - ax0, cap_old, (ax1 - ax0) * s))

# import the official A321neo wordmark
import os
svg = os.path.join(os.path.dirname(D.filepath), "..", "airbus_a321neo_logo.svg")
before = set(D.objects)
bpy.ops.import_curve.svg(filepath=os.path.abspath(svg))
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
ob321 = D.objects.new("a321neo_mark", me321)
bpy.context.scene.collection.objects.link(ob321)
xs = [v.co.x for v in me321.vertices]; ys = [v.co.y for v in me321.vertices]
n0, n1, m0, m1 = min(xs), max(xs), min(ys), max(ys)
# 'A321' caps define the cap height; the neo loop rises a bit above. Use full
# height ~1.12*cap (measured on the A320neo svg proportions) -> cap = h/1.12
cap321 = (m1 - m0) / 1.12
s321 = 0.145 / cap321
len321 = (n1 - n0) * s321
print("A321neo svg bbox %.3fx%.3f -> scaled len %.3f" % (n1 - n0, m1 - m0, len321))

for lado in ("E", "D"):
    X0 = 33.55
    # AIRBUS part, from the old mark's LOCAL (flat) coords
    me = mark.data
    me.calc_loop_triangles()
    tris = []
    for tri in me.loop_triangles:
        pts = [me.vertices[i].co for i in tri.vertices]
        if max(p.x for p in pts) <= ga + 1e-5:
            tris.append([((p.x - ax0) * s + X0, 0.0, (p.y - ay0) * s + 0.88) for p in pts])
    n = raster_side(tris, NAVY, lado)
    # A321neo part
    XA = X0 + (ax1 - ax0) * s + 0.10
    me321.calc_loop_triangles()
    tris = []
    for tri in me321.loop_triangles:
        pts = [me321.vertices[i].co for i in tri.vertices]
        tris.append([((p.x - n0) * s321 + XA, 0.0, (p.y - m0) * s321 + 0.88) for p in pts])
    n2 = raster_side(tris, NAVY, lado)
    print(f"title {lado}: AIRBUS {n} + A321neo {n2} texels, ends at x={round(XA+len321,2)}")
mark.hide_viewport = True
bpy.data.objects.remove(ob321, do_unlink=True)

store("LiveryTex", tex)
store("LiveryFac", fac)
print("livery stored")

# ------------------------------------------------ PanelBump regenerate
pb = np.full((H, W, 4), 1.0, dtype=np.float32)
joints = [0.96, 1.79, 2.65, 3.51, 4.4, 5.3, 6.96]
xj = 8.9
while xj < 31.2:
    joints.append(xj); xj += 1.99
joints += [33.69, 35.6, 37.4, 39.2, 41.0, 42.5]
for j in joints:
    cjj = int(j / L_NEW * W)
    pb[:, cjj:cjj + 2, 0:3] = 0.55
for vrow in (0.285, 0.375, 0.625, 0.715):   # lap joints
    rj = int(vrow * H)
    pb[rj:rj + 1, :, 0:3] = 0.75
img = D.images["PanelBump"]
img.pixels.foreach_set(pb.ravel())
img.pack()
print("panelbump regenerated")

# ------------------------------------------------ materials & objects
# stabilizer extrados: flight grey per PS-LBO photos (not indigo)
st = D.objects["EstabHorizontal"]
st.data.materials[0] = D.materials["CinzaAsa"]

# D4 leaf split at the wedge boundary (z -0.11): white below
for nome in ("Porta2_E", "Porta2_D"):
    o = D.objects[nome]
    me = o.data if o.data.users == 1 else o.data.copy()
    o.data = me
    if "LATAM_Branco" not in [m.name for m in me.materials]:
        me.materials.append(D.materials["LATAM_Branco"])
    wi = [m.name for m in me.materials].index("LATAM_Branco")
    for p in me.polygons:
        if p.material_index == 0:  # indigo leaf
            zc_face = sum(me.vertices[vi].co.z for vi in p.vertices) / len(p.vertices)
            if zc_face + o.location.z < -0.11:
                p.material_index = wi
print("porta2 split done")

# nose gear door registration
D.objects["RegPortaTrem"].data.body = "LBA"

# window count refined to the photo (last window centre ~34.9)
jp = D.objects["JanelasPax"]
arr = next(m2 for m2 in jp.modifiers if m2.type == 'ARRAY')
arr.count = 57
print("windows ->", arr.count)

bpy.ops.wm.save_mainfile()
print("SAVED")
