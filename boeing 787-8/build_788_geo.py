"""787-8 geometry derivation from the 787-9 master — STAGE 1 (geometry).

Run headless:
  blender -b "boeing 787-8/B788_LATAM.blend" --python "boeing 787-8/build_788_geo.py"

Derivation (spec_788.json; Boeing APR D6-58333 Rev P p.20/p.23/p.31):
- the 787-9 = 787-8 + two 3.05 m plugs, one ahead of the wing (between the fwd
  cargo door and door 2) and one behind it (between door 3 and the aft cargo
  door). Removing them: nose rings (x<=10) verbatim; barrel rebuilt 10..38.41
  from the constant ring; tail rings (x>=44.5 in the master) shifted -6.09;
- wing group (wing, belly fairing, flap fairings, main gear) -3.04
  (doors 2/3 and inlet check out exactly: 15.32/32.39/17.76);
- engines -3.04 in x and 0.18 INBOARD: APR prints cl_y 9.73 m for the -8
  against 9.91 for the -9;
- empennage, tail lights -6.09 (door 4 / aft cargo / bulk: 43.56/37.21/41.66);
- windows: zone-shift, deleting the two plug bands (5 windows each; the plug
  is 3.05 m = 5 x 0.61 pitch, so the row stays in phase);
- decal meshes repositioned for stage 2 (lockup x0.88 per CC-BBF photo,
  belly symbol to x centre 11.45, regs/DREAMLINER -6.09).
"""
import bpy
import bmesh
import json
import math
import os
from mathutils import Vector

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))

S_WING = -3.04
S_TAIL = -6.09
L788 = 56.72
COMPRIMENTO_UV = 57.5
# master-coordinate cut bands (must match build_788_livery.py)
CUT1 = (13.40, 16.44)   # fwd plug removed band (between fwd cargo door and door 2)
CUT2 = (37.54, 40.59)   # aft plug removed band (between door 3 and aft cargo door)

log = lambda *a: print("[B788]", *a)

# ------------------------------------------------------------------ fuselage
fus = D.objects["Fuselagem"]
me = fus.data
verts = [v.co.copy() for v in me.vertices]

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


nose = [(x, gl) for x, gl in ring_items if x <= 10.01]
barrel_src = [gl for x, gl in ring_items if 12.9 < x < 13.1][0]
tail = [(x, gl) for x, gl in ring_items if x >= 44.49]
log("nose rings:", len(nose), "tail rings:", len(tail))

new_rings = []
for x, gl in nose:
    srt, zc = ring_sorted(gl)
    new_rings.append((x, srt))
srt_b, zc_b = ring_sorted(barrel_src)
# NOTE: no explicit ring at 38.41 — the master's 44.5 ring arrives there via S_TAIL
for xb in (13.0, 16.0, 19.0, 22.0, 25.0, 28.0, 31.0, 34.0, 36.5):
    new_rings.append((xb, [Vector((xb, c.y, c.z)) for c in srt_b]))
for x, gl in tail:
    srt, zc = ring_sorted(gl)
    new_rings.append((round(x + S_TAIL, 3),
                      [Vector((c.x + S_TAIL, c.y, c.z)) for c in srt]))
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
vN = bm.verts.new(Vector((rear_tip.x + S_TAIL, rear_tip.y, rear_tip.z)))
for s in range(32):
    bm.faces.new((ringverts[-1][s], ringverts[-1][(s + 1) % 32], vN))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

new_me = D.meshes.new("Fuselagem788")
bm.to_mesh(new_me)
bm.free()
for p in new_me.polygons:
    p.use_smooth = True
for m in me.materials:
    new_me.materials.append(m)

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

ringtab = []
for x, coords in new_rings:
    zs = [c.z for c in coords]
    ys = [c.y for c in coords]
    ringtab.append({"x": x, "zc": 0.5 * (max(zs) + min(zs)),
                    "rz": 0.5 * (max(zs) - min(zs)), "ry": max(ys)})
json.dump(ringtab, open(os.path.join(BASE, "b788_rings.json"), "w"), indent=1)

# ------------------------------------------------------------------ helpers
def shift_zone(x):
    """master x -> delta for the -8 (None = falls inside a removed plug)"""
    if x < CUT1[0]:
        return 0.0
    if x < CUT1[1]:
        return None
    if x < CUT2[0]:
        return S_WING
    if x < CUT2[1]:
        return None
    return S_TAIL


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
    log("moved", name, dx, dy, dz)


# ------------------------------------------------------------------ windows
jan = D.objects["JanelasPax"]
jm = jan.data
# connected components
import collections
adj = collections.defaultdict(set)
for e in jm.edges:
    a, b = e.vertices
    adj[a].add(b)
    adj[b].add(a)
seen = set()
comps = []
for v0 in range(len(jm.vertices)):
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
    comps.append(comp)
log("window units:", len(comps))
doomed = set()
n_kept = n_shift = 0
for comp in comps:
    cx = sum(jm.vertices[i].co.x for i in comp) / len(comp)
    dx = shift_zone(cx)
    if dx is None:
        doomed |= comp
    else:
        if dx:
            for i in comp:
                jm.vertices[i].co.x += dx
            n_shift += 1
        else:
            n_kept += 1
bmj = bmesh.new()
bmj.from_mesh(jm)
bmj.verts.ensure_lookup_table()
bmesh.ops.delete(bmj, geom=[bmj.verts[i] for i in doomed], context='VERTS')
bmj.to_mesh(jm)
bmj.free()
log(f"windows: kept {n_kept}, shifted {n_shift}, deleted {len(doomed)} verts in plug bands")

# ------------------------------------------------------------------ wing group
for n in ("Asas", "BellyFairing",
          "FlapFairingE0", "FlapFairingE1", "FlapFairingE2",
          "FlapFairingD0", "FlapFairingD1", "FlapFairingD2",
          "TremPrincipal_BogieD", "TremPrincipal_BogieE",
          "TremPrincipal_BraceD", "TremPrincipal_BraceE",
          "TremPrincipal_EixoD-76", "TremPrincipal_EixoD76",
          "TremPrincipal_EixoE-76", "TremPrincipal_EixoE76",
          "TremP_CilindroD", "TremP_CilindroE", "TremP_PistaoD", "TremP_PistaoE",
          "TremP_TesouraDA", "TremP_TesouraDB", "TremP_TesouraEA", "TremP_TesouraEB",
          "TremP_RodaD-76-75", "TremP_RodaD-7675", "TremP_RodaD76-75", "TremP_RodaD7675",
          "TremP_RodaE-76-75", "TremP_RodaE-7675", "TremP_RodaE76-75", "TremP_RodaE7675",
          "NavEsq", "NavDir", "EstroboEsq", "EstroboDir"):
    move_mesh(n, S_WING)

# ------------------------------------------------------------------ engines
# x: -3.04 with the wing; y: 0.18 INBOARD (APR -8 cl_y 9.73 vs -9 9.91)
DY_ENG = 0.18
for n in ("Motor_Nacelle_E", "Motor_Nacelle_D", "Motor_Lip_E", "Motor_Lip_D",
          "Motor_Fan_E", "Motor_Fan_D", "Motor_Pas_E", "Motor_Pas_D",
          "Motor_Spinner_E", "Motor_Spinner_D", "Motor_Duto_E", "Motor_Duto_D",
          "Motor_Core_E", "Motor_Core_D", "Motor_Bocal_E", "Motor_Bocal_D",
          "Motor_Plug_E", "Motor_Plug_D", "Motor_Chevrons_E", "Motor_Chevrons_D",
          "Motor_Pylon_E", "Motor_Pylon_D"):
    ob = D.objects.get(n)
    if not ob:
        log("MISSING", n)
        continue
    side = -1.0 if n.endswith("_E") else 1.0
    if ob.location.length > 1e-6:
        ob.location.x += S_WING
        ob.location.y -= side * DY_ENG
    else:
        for v in ob.data.vertices:
            v.co.x += S_WING
            v.co.y -= side * DY_ENG
    log("engine part", n, "x%+.2f y%+.2f" % (S_WING, -side * DY_ENG))

# ------------------------------------------------------------------ empennage
for n in ("Deriva", "EstabHorizontal", "LuzCauda"):
    move_mesh(n, S_TAIL)

# dorsal antennas / beacon by zone
for n in ("AntenaSAT", "AntenaVHF_Dorso1", "AntenaVHF_Dorso2", "BeaconDorso"):
    ob = D.objects.get(n)
    if not ob:
        continue
    cx = sum(v.co.x for v in ob.data.vertices) / len(ob.data.vertices) + ob.location.x
    dx = shift_zone(cx)
    if dx is None:      # sits inside a plug band: snap to the nearest kept zone
        dx = S_WING
    if dx:
        move_mesh(n, dx)
    log(n, "cx=%.1f dx=%.2f" % (cx, dx))

# ------------------------------------------------------------------ decal meshes (stage 2 uses them)
# regs and DREAMLINER ride with the tail
for n in ("Reg787_E", "Reg787_D", "MarkDreamliner"):
    ob = D.objects.get(n)
    if ob:
        ob.location.x += S_TAIL
        log("decal", n, "-> x", round(ob.location.x, 3))

# lockup: photo CC-BBF (MIA 2023): symbol fwd edge 7.62, letters end 15.54
# master lockup spans 7.5..16.6 -> scale 0.88 about x=7.5, z about mid 1.55
SLK = 0.88
for n in ("B789_LogoLATAM_E", "B789_LogoLATAM_E_Coral",
          "B789_LogoLATAM_D", "B789_LogoLATAM_D_Coral"):
    ob = D.objects.get(n)
    if not ob:
        log("MISSING", n)
        continue
    ob.scale = tuple(s * SLK for s in ob.scale)
    ob.location.x = 7.5 + (ob.location.x - 7.5) * SLK + 0.10   # symbol fwd edge ~7.6
    ob.location.z = 1.55 + (ob.location.z - 1.55) * SLK
    log("lockup", n, "loc", tuple(round(v, 3) for v in ob.location),
        "scale", tuple(round(s, 3) for s in ob.scale))

# belly symbol: photo CC-BBF (MIA/MCO): centre x ~11.45 (was painted at 17-22 on the -9)
for n in ("LogoBarriga", "LogoBarriga_Coral"):
    ob = D.objects.get(n)
    if not ob:
        continue
    # master mesh spans 6.2*scale from loc.x; centre target 11.45
    w = 6.2 * ob.scale.x
    ob.location.x = 11.45 - 0.5 * w
    log("belly logo", n, "loc.x ->", round(ob.location.x, 3), "width", round(w, 2))

# ------------------------------------------------------------------ cameras & set
def set_loc(name, x=None, y=None, z=None):
    ob = D.objects.get(name)
    if not ob:
        log("MISSING cam", name)
        return
    if x is not None:
        ob.location.x = x
    if y is not None:
        ob.location.y = y
    if z is not None:
        ob.location.z = z
    log(name, "->", tuple(round(v, 2) for v in ob.location))


set_loc("CamAlvoCauda", x=49.4)
set_loc("CamCauda", x=81.6)
set_loc("CamPerfil", x=28.4)
set_loc("CamAlvo", x=24.1)
set_loc("CamAlvoBarriga", x=18.2)
set_loc("CamHero", x=-24.5, y=-40.0)
set_loc("Pista", x=28.2)
set_loc("CamBomb", x=25.4)
set_loc("CamEstib", x=25.4)

col = D.collections.get("B789_LATAM")
if col:
    col.name = "B788_LATAM"

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
