"""A321neo PS-LBA — phase 1: geometry, derived from the A320neo master.

Run:  blender -b --factory-startup "airbus A321neo/A321neo_LATAM.blend" -P build_a321_fase1_geometria.py

Derivation (sources in spec_a321.json):
- A321 ACAP Rev 35 Jul/26, Fig 2-2-0 (ACF sheet): length 44.51, wheelbase 16.90,
  nose gear 5.07, engine inlet 15.40, span 35.80, track 7.59.
- Stretch vs A320: fwd plug +4.26 m ahead of the wing box, aft plug +2.68 m
  behind it (total +6.94; the fwd value is pinned by the gear: 17.71+4.26=21.97
  = 5.07+16.90, and by the engine: 11.14+4.26=15.40).
- ACAP Fig 2-7-0 (ACF): D1 5.04, fwd overwing 18.70, aft overwing 19.54,
  D3 26.82, D4 36.47, cargo fwd/aft/bulk 8.56/30.02/33.22.
The hull cage keeps the A320 rings (identical cross-section) with a piecewise
x map; the barrel gets duplicate identical rings so ring spacing stays 2-3 m.
"""
import bpy
import bmesh
import math

D = bpy.data
CUT1, CUT2 = 11.5, 26.4       # cut stations inside the constant section
D_FWD, D_TOT = 4.26, 6.94     # plug shifts
L_UV_NEW = 45.0               # new UV length (u = x / L_UV_NEW)

def mapx(x):
    if x <= CUT1: return x
    if x <= CUT2: return x + D_FWD
    return x + D_TOT

# ------------------------------------------------------------------ fuselage
fus = D.objects["Fuselagem"]
me = fus.data

# group verts into rings by x
rings = {}
tips = []
for v in me.vertices:
    k = round(v.co.x, 4)
    rings.setdefault(k, []).append(v.co.copy())
ring_items = []
for k in sorted(rings):
    vs = rings[k]
    if len(vs) == 1:
        tips.append((k, vs[0]))
        continue
    zc = (max(p.z for p in vs) + min(p.z for p in vs)) / 2
    vs.sort(key=lambda p: math.atan2(p.y, p.z - zc))
    ring_items.append((k, zc, vs))
assert len(tips) == 2, tips
tip_front = min(tips)[1]
tip_back = max(tips)[1]
print("rings:", len(ring_items), "tips:", tuple(round(c,3) for c in tip_front), tuple(round(c,3) for c in tip_back))

# reference identical barrel ring (x=20)
barrel = next(vs for (k, zc, vs) in ring_items if abs(k - 20.0) < 0.01)

# new ring list: mapped rings + duplicated barrel rings in the plug gaps
new_rings = []
for (k, zc, vs) in ring_items:
    new_rings.append((mapx(k), [(mapx(k), p.y, p.z) for p in vs]))
for xd in (12.1, 14.2,          # forward plug (gap 10 -> 16.26)
           32.94):              # aft plug (gap 30.26 -> 33.69, mirrors A320's 26.0->26.75 step)
    new_rings.append((xd, [(xd, p.y, p.z) for p in barrel]))
new_rings.sort(key=lambda r: r[0])
xs_seq = [r[0] for r in new_rings]
print("new ring xs:", [round(x, 2) for x in xs_seq])

SEG = len(barrel)
bm = bmesh.new()
ringverts = []
for (x, pts) in new_rings:
    ringverts.append([bm.verts.new(p) for p in pts])
for a, b in zip(ringverts[:-1], ringverts[1:]):
    for s in range(SEG):
        bm.faces.new((a[s], a[(s + 1) % SEG], b[(s + 1) % SEG], b[s]))
v0 = bm.verts.new((tip_front.x, tip_front.y, tip_front.z))
vN = bm.verts.new((tip_back.x + D_TOT, tip_back.y, tip_back.z))
# cap winding must match the ring loft (see casco.py)
for s in range(SEG):
    bm.faces.new((ringverts[0][s], v0, ringverts[0][(s + 1) % SEG]))
for s in range(SEG):
    bm.faces.new((ringverts[-1][s], ringverts[-1][(s + 1) % SEG], vN))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me_new = D.meshes.new("Fuselagem")
bm.to_mesh(me_new)
bm.free()
for p in me_new.polygons:
    p.use_smooth = True
for mslot in me.materials:
    me_new.materials.append(mslot)
old = fus.data
fus.data = me_new
D.meshes.remove(old)

# cylindrical UV (u = x/L, v about the ring centre) + wrap stitch
ring_centers = [(x, (max(p[2] for p in pts) + min(p[2] for p in pts)) / 2)
                for (x, pts) in new_rings]
def centro(x):
    if x <= ring_centers[0][0]: return ring_centers[0][1]
    for (xa, za), (xb, zb) in zip(ring_centers[:-1], ring_centers[1:]):
        if xa <= x <= xb:
            f = (x - xa) / max(xb - xa, 1e-9)
            return za + f * (zb - za)
    return ring_centers[-1][1]
uv = me_new.uv_layers.new(name="UVMap")
for loop in me_new.loops:
    co = me_new.vertices[loop.vertex_index].co
    zc = centro(co.x)
    th = math.atan2(co.y, co.z - zc) if (abs(co.y) > 1e-9 or abs(co.z - zc) > 1e-9) else 0.0
    uv.data[loop.index].uv = (co.x / L_UV_NEW, (th + math.pi) / (2 * math.pi))
for p in me_new.polygons:
    vs = [uv.data[li].uv[1] for li in p.loop_indices]
    if max(vs) - min(vs) > 0.5:
        for li in p.loop_indices:
            if uv.data[li].uv[1] < 0.5:
                uv.data[li].uv = (uv.data[li].uv[0], uv.data[li].uv[1] + 1.0)

# ------------------------------------------------------------------ moves
MOVE = {
    D_FWD: ["Asas", "BellyFairing", "Motor_Nacelle", "Motor_Core", "Motor_Fan",
            "Motor_Spinner", "Motor_Exaustao", "Motor_Pylon",
            "TremPrincipal_StrutE", "TremPrincipal_EixoE", "TremPrincipal_RodaE1",
            "TremPrincipal_RodaE2", "TremPrincipal_BraceE", "TremPrincipal_StrutD",
            "TremPrincipal_EixoD", "TremPrincipal_RodaD1", "TremPrincipal_RodaD2",
            "TremPrincipal_BraceD", "FlapFairing0", "FlapFairing1", "FlapFairing2",
            "FlapFairing3", "FlapFairing4", "NavEsq", "NavDir", "Beacon",
            "AntenaVHF2", "Belly_DME2", "Belly_RamAirE", "Belly_RamAirD",
            "Belly_PackOutE", "Belly_PackOutD", "Belly_RA1", "Belly_RA2",
            "Belly_RA3", "Belly_RA4", "Belly_Beacon", "Belly_VHF2"],
    D_TOT: ["Deriva", "EstabHorizontal", "APUTip", "LuzCauda", "WrapIndigo",
            "Reg_E", "Reg_D", "MarkAirbusNeo_E", "MarkAirbusNeo_D",
            "Belly_DrenoAft", "Belly_Outflow", "Belly_APUIntake",
            "Porta2_E", "Porta2_D", "PortaCargaBulk"],
    0.40: ["PortaCargaFwd"],
    4.27: ["Overwing1_E", "Overwing1_D"],
    3.88: ["Overwing2_E", "Overwing2_D"],
}
for delta, names in MOVE.items():
    for n in names:
        o = D.objects.get(n)
        if o is None:
            print("MISSING", n)
            continue
        o.location.x += delta

# door 3 (new full door pair aft of the wing, ACAP 26.82)
for side in ("E", "D"):
    src = D.objects["Porta1_" + side]
    dup = src.copy()
    dup.data = src.data  # same sheet; identical constant section -> same surface fit
    dup.name = "Porta3_" + side
    dup.location.x += 26.82 - 5.04
    for col in src.users_collection:
        col.objects.link(dup)

# ------------------------------------------------------------------ windows
jp = D.objects["JanelasPax"]
arr = next(m for m in jp.modifiers if m.type == 'ARRAY')
pitch = arr.constant_offset_displace[0]
w = 0.255
n = int((34.65 - 6.08 - w) / pitch) + 1
print("window pitch", round(pitch, 4), "count", arr.count, "->", n,
      "last window end", round(6.08 + (n - 1) * pitch + w, 2))
arr.count = n

# ------------------------------------------------------------------ cameras & set
def setloc(name, x=None, y=None, z=None):
    o = D.objects[name]
    lx, ly, lz = o.location
    o.location = (x if x is not None else lx, y if y is not None else ly,
                  z if z is not None else lz)
setloc("CamPerfil", x=22.3, y=-112.5)
setloc("CamHero", x=-18.9, y=-30.8)
setloc("CamAlvo", x=19.0)
setloc("CamCauda", x=51.94)
setloc("CamAlvoCauda", x=38.44)
setloc("CamBarriga", x=-1.74)
setloc("CamAlvoBarriga", x=16.26)
setloc("Pista", x=21.5)
setloc("CloudCard", x=18.0)

# ------------------------------------------------------------------ checks
def bbox(o):
    return [round(f, 3) for f in
            (min((o.matrix_world @ v.co).x for v in o.data.vertices),
             max((o.matrix_world @ v.co).x for v in o.data.vertices))]
bpy.context.view_layer.update()
print("CHECK fuselage x:", bbox(D.objects["Fuselagem"]))
print("CHECK engine inlet x (want 15.40):", bbox(D.objects["Motor_Nacelle"])[0])
print("CHECK main gear x (want 21.97):", round(D.objects["TremPrincipal_StrutE"].location.x, 3))
for n, want in [("Porta1_E", 5.04), ("Overwing1_E", 18.70), ("Overwing2_E", 19.54),
                ("Porta3_E", 26.82), ("Porta2_E", 36.58),
                ("PortaCargaFwd", 8.56), ("PortaCargaAft", 30.02), ("PortaCargaBulk", 33.23)]:
    o = D.objects[n]
    b = bbox(o)
    print(f"CHECK {n}: centre {round((b[0]+b[1])/2, 3)} (want {want})")
print("CHECK fin x:", bbox(D.objects["Deriva"]), "stab x:", bbox(D.objects["EstabHorizontal"]))

bpy.ops.wm.save_mainfile()
print("SAVED", bpy.data.filepath)
