"""A321ceo PT-MXP — phase 1: geometry deltas from the A321neo master copy.

Run: blender -b "airbus A321ceo/A321ceo_LATAM.blend" --python "airbus A321ceo/build_a321ceo_fase1_geo.py"

Same 44.51 m hull as the neo-ACF — the fuselage, wing, empennage, gear and UV
are untouched. Deltas (sources in spec_a321ceo.json):
- doors ceo (ACAP Fig 2-7-0-991-004 sheet 2): D1 5.02(model keeps 5.04, delta
  documented), D2 13.84, D3 24.79, D4 36.58, cargo 8.16/29.62/33.22.
  Overwing exits DELETED; D2/D3 are 0.76 x 1.52 exits on the D1 sill line
  (photo PT-XPB + Fig -034); D4 = old Porta2, renamed, position already exact.
- engines: IAE V2533-A5 — PW1100G nacelle scaled with the A319-validated
  factors (radial 0.846, length 0.88), inlet at 15.39 (ACAP V2500).
"""
import bpy
import numpy as np

D = bpy.data
log = lambda *a: print("[A321ceo]", *a)

# ------------------------------------------------------------ overwing exits out
for n in ("Overwing1_E", "Overwing1_D", "Overwing2_E", "Overwing2_D"):
    ob = D.objects.get(n)
    if ob:
        me = ob.data
        D.objects.remove(ob, do_unlink=True)
        if me.users == 0:
            D.meshes.remove(me)
        log("deleted", n)

# ------------------------------------------------------------ D4 rename (was Porta2)
for side in ("E", "D"):
    ob = D.objects.get("Porta2_" + side)
    if ob:
        ob.name = "Porta4_" + side
        log("renamed Porta2_%s -> Porta4_%s" % (side, side))

# ------------------------------------------------------------ D2/D3 exits
SX = 0.76 / 0.81          # width factor
SZ = 1.52 / 1.85          # height factor, anchored at the sill


def make_exit(src_name, new_name, loc_x):
    """own-mesh copy of Porta1 scaled to ceo exit size, placed via location."""
    src = D.objects[src_name]
    ob = D.objects.get(new_name)
    if ob is None:
        ob = src.copy()
        ob.name = new_name
        for col in src.users_collection:
            col.objects.link(ob)
    ob.data = src.data.copy()
    ob.data.name = new_name
    vs = ob.data.vertices
    xs = [v.co.x for v in vs]
    zs = [v.co.z for v in vs]
    cx = 0.5 * (min(xs) + max(xs))
    z0 = min(zs)
    for v in vs:
        v.co.x = cx + SX * (v.co.x - cx)
        v.co.z = z0 + SZ * (v.co.z - z0)
    ob.location = (loc_x, src.location.y, src.location.z)
    b = [(min(v.co.x for v in vs) + loc_x), (max(v.co.x for v in vs) + loc_x)]
    log(f"{new_name}: x {b[0]:.2f}..{b[1]:.2f} (centre {(b[0]+b[1])/2:.2f}) "
        f"z {z0 + src.location.z:.2f}..{z0 + SZ*(max(zs)-z0) + src.location.z:.2f}")


for side in ("E", "D"):
    # D3: replace the shared-mesh dup with a scaled own-mesh at 24.79
    old3 = D.objects.get("Porta3_" + side)
    if old3:
        me = old3.data
        D.objects.remove(old3, do_unlink=True)
        if me.users == 0:
            D.meshes.remove(me)
    make_exit("Porta1_" + side, "Porta3_" + side, 24.79 - 5.04)
    # D2: new forward exit at 13.84
    make_exit("Porta1_" + side, "Porta2_" + side, 13.84 - 5.04)

# ------------------------------------------------------------ cargo doors
for n, dx in (("PortaCargaFwd", -0.40), ("PortaCargaAft", -0.40)):
    ob = D.objects[n]
    ob.location.x += dx
    log(n, "moved", dx)

# ------------------------------------------------------------ engines V2500
SR, SL = 0.846, 0.88
X_OLD, X_NEW = 15.40, 15.39
Y0, Z0 = 5.75, -1.95
for n in ("Motor_Nacelle", "Motor_Fan", "Motor_Spinner", "Motor_Core", "Motor_Exaustao"):
    ob = D.objects[n]
    lx = ob.location.x
    ys = [v.co.y for v in ob.data.vertices]
    log(n, "y range %.2f..%.2f mods=%s" % (min(ys), max(ys),
        [m.type for m in ob.modifiers]))
    for v in ob.data.vertices:
        xw = v.co.x + lx
        v.co.x = (X_NEW + SL * (xw - X_OLD)) - lx
        v.co.y = Y0 + SR * (v.co.y - Y0)
        v.co.z = Z0 + SR * (v.co.z - Z0)
    log("V2500-scaled", n)
ob = D.objects["Motor_Pylon"]
lx = ob.location.x
for v in ob.data.vertices:
    xw = v.co.x + lx
    v.co.x = (X_NEW + SL * (xw - X_OLD)) - lx
    v.co.y = Y0 + SR * (v.co.y - Y0)
log("pylon adjusted")

# ------------------------------------------------------------ checks
bpy.context.view_layer.update()


def bbox(o):
    return [round(f, 3) for f in
            (min((o.matrix_world @ v.co).x for v in o.data.vertices),
             max((o.matrix_world @ v.co).x for v in o.data.vertices))]


for n, want in [("Porta1_E", 5.04), ("Porta2_E", 13.84), ("Porta3_E", 24.79),
                ("Porta4_E", 36.58), ("PortaCargaFwd", 8.16),
                ("PortaCargaAft", 29.62), ("PortaCargaBulk", 33.23)]:
    b = bbox(D.objects[n])
    print(f"CHECK {n}: centre {round((b[0]+b[1])/2, 3)} (want {want})")
print("CHECK V2500 inlet x (want 15.39):", bbox(D.objects["Motor_Nacelle"])[0])
naz = min((D.objects["Motor_Nacelle"].matrix_world @ v.co).z
          for v in D.objects["Motor_Nacelle"].data.vertices)
print("CHECK nacelle low z: %.2f (ground -3.67 -> clearance %.2f, ACAP 0.78)" %
      (naz, naz + 3.67))

# raycast sanity on the hull (unchanged, but confirm nothing broke)
dg = bpy.context.evaluated_depsgraph_get()
fus = D.objects["Fuselagem"].evaluated_get(dg)
import mathutils
hit, locv, *_ = fus.ray_cast(mathutils.Vector((20.0, -5.0, 0.0)),
                             mathutils.Vector((0, 1, 0)), distance=10)
print("CHECK barrel half-width at x=20:", round(-locv.y, 3) if hit else "MISS")

bpy.ops.wm.save_mainfile()
print("SAVED", D.filepath)
