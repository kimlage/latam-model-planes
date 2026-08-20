"""A319 geometry derivation from the A320neo master — STAGE 1 (geometry).

Run headless:
  blender -b "airbus A319/A319_LATAM.blend" --python "airbus A319/build_a319_geo.py"

Derivation (spec_a319.json):
- fuselage: nose rings (x<=6.96) kept verbatim; barrel rebuilt 6.96..20.43 from the
  constant ring; tail rings (x>=26 in the master) shifted -3.73;
- wing group -1.60; empennage per the A319 ACAP (fin remapped in (h,c), stab -2.86);
- V2500 nacelles (radial x0.846, length x0.88, inlet at 9.52);
- sharklet cut at |y|=18.45 + classic wingtip fence;
- doors: door2->25.81, single overwing pair at 12.83, cargo aft 20.56, bulk 22.57.
"""
import bpy
import bmesh
import json
import math
import os
from mathutils import Vector

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))

SHIFT_WING = -1.60
SHIFT_TAIL = -3.73
L319 = 33.84
COMPRIMENTO_UV = 34.2

log = lambda *a: print("[A319]", *a)

# ------------------------------------------------------------------ fuselage
fus = D.objects["Fuselagem"]
me = fus.data
verts = [v.co.copy() for v in me.vertices]

# group rings by rounded x
rings = {}
tips = []
for co in verts:
    key = round(co.x, 2)
    rings.setdefault(key, []).append(co)
ring_items = []
for key, gl in sorted(rings.items()):
    if len(gl) == 1:
        tips.append((key, gl[0]))
    else:
        assert len(gl) == 32, f"ring at x={key} has {len(gl)} verts"
        ring_items.append((key, gl))
log("rings:", len(ring_items), "tips:", [round(t[0], 2) for t in tips])

front_tip = min(tips, key=lambda t: t[0])[1]
rear_tip = max(tips, key=lambda t: t[0])[1]


def ring_sorted(gl):
    zs = [c.z for c in gl]
    zc = 0.5 * (max(zs) + min(zs))
    return sorted(gl, key=lambda c: math.atan2(c.y, c.z - zc)), zc


nose = [(x, gl) for x, gl in ring_items if x <= 6.97]
barrel_src = [gl for x, gl in ring_items if 11.9 < x < 12.1][0]
tail = [(x, gl) for x, gl in ring_items if x >= 25.9]
log("nose rings:", len(nose), "tail rings:", len(tail))

new_rings = []          # list of (x, [Vector,...] sorted by theta)
for x, gl in nose:
    srt, zc = ring_sorted(gl)
    new_rings.append((x, srt))
# barrel: constant ring shape copied to new stations
srt_b, zc_b = ring_sorted(barrel_src)
for xb in (8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0):
    new_rings.append((xb, [Vector((xb, c.y, c.z)) for c in srt_b]))
# tail: shift -3.73
for x, gl in tail:
    srt, zc = ring_sorted(gl)
    new_rings.append((round(x + SHIFT_TAIL, 3),
                      [Vector((c.x + SHIFT_TAIL, c.y, c.z)) for c in srt]))
new_rings.sort(key=lambda r: r[0])
log("new ring count:", len(new_rings), "x:", [r[0] for r in new_rings])

bm = bmesh.new()
ringverts = []
for x, coords in new_rings:
    ringverts.append([bm.verts.new(c) for c in coords])
for a, b in zip(ringverts[:-1], ringverts[1:]):
    for s in range(32):
        bm.faces.new((a[s], a[(s + 1) % 32], b[(s + 1) % 32], b[s]))
v0 = bm.verts.new(front_tip)
for s in range(32):
    bm.faces.new((ringverts[0][s], v0, ringverts[0][(s + 1) % 32]))
vN = bm.verts.new(Vector((rear_tip.x + SHIFT_TAIL, rear_tip.y, rear_tip.z)))
for s in range(32):
    bm.faces.new((ringverts[-1][s], ringverts[-1][(s + 1) % 32], vN))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

new_me = D.meshes.new("Fuselagem319")
bm.to_mesh(new_me)
bm.free()
for p in new_me.polygons:
    p.use_smooth = True
for m in me.materials:
    new_me.materials.append(m)

# cylindrical UV (u = x/COMPRIMENTO_UV, v = theta about section centre)
aneis_xz = [(x, 0.5 * (max(c.z for c in coords) + min(c.z for c in coords)))
            for x, coords in new_rings]


def centro(x):
    xs = [a[0] for a in aneis_xz]
    zcs = [a[1] for a in aneis_xz]
    if x <= xs[0]:
        return zcs[0]
    if x >= xs[-1]:
        return zcs[-1]
    for (xa, za), (xb, zb) in zip(aneis_xz[:-1], aneis_xz[1:]):
        if xa <= x <= xb:
            f = (x - xa) / max(xb - xa, 1e-9)
            return za + f * (zb - za)
    return zcs[-1]


uv = new_me.uv_layers.new(name="UVMap")
for loop in new_me.loops:
    co = new_me.vertices[loop.vertex_index].co
    zc = centro(co.x)
    th = math.atan2(co.y, co.z - zc) if (abs(co.y) > 1e-9 or abs(co.z - zc) > 1e-9) else 0.0
    uv.data[loop.index].uv = (co.x / COMPRIMENTO_UV, (th + math.pi) / (2 * math.pi))
for p in new_me.polygons:
    vs = [uv.data[li].uv[1] for li in p.loop_indices]
    if max(vs) - min(vs) > 0.5:
        for li in p.loop_indices:
            if uv.data[li].uv[1] < 0.5:
                uv.data[li].uv = (uv.data[li].uv[0], uv.data[li].uv[1] + 1.0)

old = fus.data
fus.data = new_me
D.meshes.remove(old)
log("fuselage swapped:", len(new_me.vertices), "verts")

# save ring table for the livery stage
ringtab = []
for x, coords in new_rings:
    zs = [c.z for c in coords]
    ys = [c.y for c in coords]
    ringtab.append({"x": x, "zc": 0.5 * (max(zs) + min(zs)),
                    "rz": 0.5 * (max(zs) - min(zs)), "ry": max(ys)})
json.dump(ringtab, open(os.path.join(BASE, "a319_rings.json"), "w"), indent=1)

# ------------------------------------------------------------------ doors
def move_mesh(name, dx, dy=0.0, dz=0.0):
    ob = D.objects.get(name)
    if not ob:
        log("MISSING", name)
        return
    if abs(ob.location.x) > 1e-6 or abs(ob.location.y) > 1e-6 or abs(ob.location.z) > 1e-6:
        ob.location.x += dx
        ob.location.y += dy
        ob.location.z += dz
    else:
        for v in ob.data.vertices:
            v.co.x += dx
            v.co.y += dy
            v.co.z += dz
    log("moved", name, dx)


for n in ("Porta2_E", "Porta2_D"):
    move_mesh(n, -3.83)
for n in ("Overwing1_E", "Overwing1_D"):
    move_mesh(n, SHIFT_WING)
for n in ("Overwing2_E", "Overwing2_D"):
    ob = D.objects.get(n)
    if ob:
        D.objects.remove(ob, do_unlink=True)
        log("deleted", n)
move_mesh("PortaCargaAft", -2.13)
move_mesh("PortaCargaBulk", -3.72)

# windows: 40 -> 33
jan = D.objects["JanelasPax"]
for m in jan.modifiers:
    if m.type == 'ARRAY':
        m.count = 33
        log("windows count ->", m.count)

# ------------------------------------------------------------------ wing group
for n in ("Asas", "BellyFairing", "FlapFairing0", "FlapFairing1", "FlapFairing2",
          "FlapFairing3", "FlapFairing4",
          "TremPrincipal_StrutE", "TremPrincipal_StrutD", "TremPrincipal_BraceE",
          "TremPrincipal_BraceD", "TremPrincipal_EixoE", "TremPrincipal_EixoD",
          "TremPrincipal_RodaE1", "TremPrincipal_RodaE2", "TremPrincipal_RodaD1",
          "TremPrincipal_RodaD2"):
    move_mesh(n, SHIFT_WING)

# sharklet cut + cap
asas = D.objects["Asas"]
bm = bmesh.new()
bm.from_mesh(asas.data)
side = 1.0 if max(v.co.y for v in bm.verts) > 1.0 else -1.0
doomed = [v for v in bm.verts if abs(v.co.y) > 18.45]
log("sharklet verts removed:", len(doomed), "raw side:", side)
bmesh.ops.delete(bm, geom=doomed, context='VERTS')
edges = [e for e in bm.edges if e.is_boundary and abs(e.verts[0].co.y) > 18.2]
if edges:
    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    log("tip capped with", len(edges), "boundary edges")
bm.to_mesh(asas.data)
bm.free()

# wingtip fence
tipverts = [v.co for v in asas.data.vertices if abs(v.co.y) > 18.30]
tx0 = min(v.x for v in tipverts)
tx1 = max(v.x for v in tipverts)
tz = 0.5 * (min(v.z for v in tipverts) + max(v.z for v in tipverts))
ty = max(abs(v.y) for v in tipverts) * side
log(f"tip chord {tx0:.2f}..{tx1:.2f} z {tz:.2f} y {ty:.2f}")

mats = {m.name: i for i, m in enumerate(asas.data.materials)}


def fence_mesh():
    """Classic A320-family wingtip fence: lens above and below the tip chord."""
    bm = bmesh.new()
    cx = 0.5 * (tx0 + tx1)
    ch = (tx1 - tx0)
    prof = [  # (z offset, LE x offset, TE x offset) — swept-back lobes
        (-0.58, 0.42, 0.92),
        (-0.30, 0.18, 0.98),
        (0.0, 0.02, 1.02),
        (0.30, 0.18, 0.98),
        (0.62, 0.45, 0.95),
    ]
    thick = 0.045
    rows = []
    for dz, le, te in prof:
        x0 = tx0 + le * 0.35 * ch
        x1 = tx0 + te * 0.72 * ch + 0.30
        rows.append([(x0, dz), (0.5 * (x0 + x1), dz), (x1, dz)])
    grid = []
    for yo in (-thick, thick):
        layer = []
        for r in rows:
            layer.append([bm.verts.new(Vector((px, ty + yo, tz + pz))) for px, pz in r])
        grid.append(layer)
    faces = []
    for layer in grid:
        for ra, rb in zip(layer[:-1], layer[1:]):
            for a, b in zip(range(2), range(1, 3)):
                try:
                    faces.append(bm.faces.new((ra[a], ra[b], rb[b], rb[a])))
                except ValueError:
                    pass
    # stitch rim
    la, lb = grid
    edge_pairs = []
    n_r, n_c = len(rows), 3
    rim = [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (4, 1), (4, 0),
           (3, 0), (2, 0), (1, 0)]
    for (r1, c1), (r2, c2) in zip(rim, rim[1:] + rim[:1]):
        try:
            faces.append(bm.faces.new((la[r1][c1], la[r2][c2], lb[r2][c2], lb[r1][c1])))
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = D.meshes.new("WingFence")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


fme = fence_mesh()
fme.materials.append(D.materials["LATAM_Indigo"])
fme.materials.append(D.materials["LATAM_Branco"])
fme.materials.append(D.materials["LATAM_Coral"])
# outer faces indigo, inner faces white, mid band coral
for p in fme.polygons:
    outer = (p.center.y - ty * 1.0) * side > 0 if abs(p.normal.y) > 0.5 else None
    if outer is None:
        p.material_index = 0
    elif (p.center.y * side) > abs(ty):
        p.material_index = 0 if abs(p.center.z - tz) > 0.18 else 2
    else:
        p.material_index = 1
fob = D.objects.new("WingFence", fme)
col = D.collections["01_Estrutura"]
col.objects.link(fob)
mir = fob.modifiers.new("Mirror", 'MIRROR')
mir.use_axis = (False, True, False)
log("fence built at y=%.2f" % ty)

# nav lights to the new tip
for n, sgn in (("NavEsq", -1), ("NavDir", 1)):
    ob = D.objects[n]
    ob.location.x = tx0 + 0.35 * (tx1 - tx0)
    ob.location.y = sgn * (abs(ty) + 0.02)
    ob.location.z = tz
    log(n, "->", tuple(round(v, 2) for v in ob.location))

# ------------------------------------------------------------------ engines (V2500)
SR = 0.846   # radial
SL = 0.88    # length
X_REF_OLD = 11.14   # PW inlet world x
X_REF_NEW = 9.52    # V2500 inlet world x
Y0, Z0 = 5.75, -1.95
for n in ("Motor_Nacelle", "Motor_Fan", "Motor_Spinner", "Motor_Core", "Motor_Exaustao"):
    ob = D.objects[n]
    lx = ob.location.x
    for v in ob.data.vertices:
        xw = v.co.x + lx
        v.co.x = (X_REF_NEW + SL * (xw - X_REF_OLD)) - lx
        v.co.y = Y0 + SR * (v.co.y - Y0)
        v.co.z = Z0 + SR * (v.co.z - Z0)
    log("V2500-scaled", n)
# pylon: x like the engine, y narrowed, z kept (wing side)
ob = D.objects["Motor_Pylon"]
lx = ob.location.x
for v in ob.data.vertices:
    xw = v.co.x + lx
    v.co.x = (X_REF_NEW + SL * (xw - X_REF_OLD)) - lx
    v.co.y = Y0 + SR * (v.co.y - Y0)
log("pylon adjusted")

# ------------------------------------------------------------------ empennage
LE_O = lambda z: 0.8393 * z + 26.773
TE_O = lambda z: 34.60 + 0.0538 * (z - 1.55)
LE_N = lambda z: 0.851 * z + 23.866
TE_N = lambda z: 0.220 * z + 30.72
der = D.objects["Deriva"]
for v in der.data.vertices:
    z = v.co.z
    lo, to = LE_O(z), TE_O(z)
    c = (v.co.x - lo) / max(to - lo, 1e-6)
    ln, tn = LE_N(z), TE_N(z)
    v.co.x = ln + c * (tn - ln)
log("fin remapped: root LE %.2f TE %.2f" % (LE_N(1.55), TE_N(1.55)))

move_mesh("EstabHorizontal", -2.86)
move_mesh("APUTip", SHIFT_TAIL)
move_mesh("LuzCauda", SHIFT_TAIL)

# ------------------------------------------------------------------ antennas & details
for n, dx in (("Belly_RamAirD", SHIFT_WING), ("Belly_RamAirE", SHIFT_WING),
              ("Belly_PackOutD", SHIFT_WING), ("Belly_PackOutE", SHIFT_WING),
              ("Belly_DME2", SHIFT_WING),
              ("Belly_RA1", SHIFT_WING), ("Belly_RA2", SHIFT_WING),
              ("Belly_RA3", SHIFT_WING), ("Belly_RA4", SHIFT_WING),
              ("Belly_Beacon", -2.30), ("Belly_VHF2", -2.15),
              ("Belly_DrenoAft", SHIFT_TAIL), ("Belly_Outflow", SHIFT_TAIL),
              ("Belly_APUIntake", SHIFT_TAIL), ("Beacon", SHIFT_WING)):
    move_mesh(n, dx)

# top antennas embedded at loc 0: shift by zone
import numpy as np
for n in ("AntenaGPS", "AntenaVHF1", "AntenaVHF2", "AntenaVHF3"):
    ob = D.objects.get(n)
    if not ob:
        continue
    cx = sum(v.co.x for v in ob.data.vertices) / len(ob.data.vertices)
    dx = 0.0 if cx < 9 else (SHIFT_WING if cx < 21 else SHIFT_TAIL)
    if dx:
        for v in ob.data.vertices:
            v.co.x += dx
    log(n, "cx=%.1f dx=%.2f" % (cx, dx))

# gear-door registration text
reg = D.objects.get("RegPortaTrem")
if reg and reg.type == 'FONT':
    log("gear door text:", repr(reg.data.body))
    reg.data.body = "PT-TMT"

# drop A320-specific marks
for n in ("CapAmerica_E", "CapAmerica_D", "CapPrimeiro_E", "CapPrimeiro_D",
          "LogoA320neo_E", "LogoA320neo_D"):
    ob = D.objects.get(n)
    if ob:
        me_old = ob.data
        D.objects.remove(ob, do_unlink=True)
        if me_old.users == 0:
            D.meshes.remove(me_old)
        log("removed", n)

# ------------------------------------------------------------------ cameras
D.objects["CamAlvoCauda"].location.x = 27.8
D.objects["CamCauda"].location.x = 41.2
D.objects["CamPerfil"].location.x = 16.9
D.objects["CamAlvo"].location.x = 14.4
D.objects["CamAlvoBarriga"].location.x = 10.8
D.objects["CamHero"].location = (-15.0, -24.5, 0.5)
log("cameras retargeted")

col = D.collections.get("A320neo_LATAM")
if col:
    col.name = "A319_LATAM"

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
