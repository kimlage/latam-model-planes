#!/usr/bin/env python3
"""Clip 2 — the roll-out: a 777 backs out of its own hangar, fin first.

    blender -b --factory-startup -P scenario_sbgr/hangar_rollout.py -- \\
        --out scenario_sbgr/sbgr_rollout.blend

    python3 scenario_sbgr/hangar_rollout.py     # offline solve, no Blender

WHY IT IS TAIL-FIRST, AND WHY THAT IS THE SHOT
==============================================
Phase 2 parked the hangar 777 OUTSIDE, nose-in, 18 m clear of the door — so
"the 777 entering its hangar" would be São Carlos's clip with the labels
changed, which the owner explicitly does not want a base to be. What an MRO
actually does at the end of a check is the reverse: the aeroplane is towed
in nose-first and comes out TAIL-FIRST, backing into the daylight. On film
that inversion is the whole clip: the first thing to cross the door line is
the FIN — the LATAM sash sliding out of a dark bay into 17:30 raking light —
and the aeroplane the base exists to serve is revealed stern-first, the way
the people who work here actually see it leave.

THE MATHS IS SÃO CARLOS'S TRACTRIX, TIME-REVERSED
--------------------------------------------------
`scenario_sdsc/hangar_tow.py` solved the tow by making the AEROPLANE's
heading the control curve, integrating the main gear along it and deriving
the nose gear — square-to-the-door guaranteed, counter-steer for free. A
kinematic path is reversible: solve the same ENTRY (angled approach easing
square into the bay), then play it backwards. The tug never changes ends —
it holds the nose gear throughout, pulling on the way in, easing the
aeroplane back on the way out, exactly as a real crew does it.

Entry solved forward:  heading 318° at the far end of the path easing to
343.65° (square, = HDG_IN) over 55 m of main-gear travel; nose gear ends
25.9 m inside the door plane, tail 2 m inside — the aeroplane is IN.
Played reversed: frames 1..400 show the last frame first, so the clip opens
on the closed composition (aircraft inside, bay glowing) and ends with the
777 out on its apron, swung 25° toward the taxiway, tug at its nose.

CAMERA
------
Fixed-with-drift on the hangar apron, ~95 m SSE of the door, 35 mm, looking
NNW into the open bay — the SDSC tow grammar (a 16-second locked-off push
is the one thing that reads as CG, so it drifts a metre on two mutually
prime periods). Sun 251° sits ~62° left of the lens: the door face is
grazing-lit, the emerging fin catches it, the bay behind stays in its own
lamplight. The 901 row reads at frame right as the aeroplane clears.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import shot_common as S                                       # noqa: E402

FRAME_END = 400
FPS = 25.0

# --- the hangar and its bay (build_scenery constants, phase 2) --------------
HGR_C = (2281.2, 1361.7)          # footprint centre
HALF_L, HALF_D = 68.4, 46.1       # half length (along track), half depth
Z_APRON = -8.70 + 0.05            # hangar apron top
HDG_IN = 343.65                   # nose-in heading (into the bay)
# door face centre (SSE wall) and outward normal
FACE_C = (HGR_C[0] + HALF_D * S.RX, HGR_C[1] + HALF_D * S.RY)
OUT_N = (S.RX, S.RY)              # unit, SSE, out of the door
ALONG = (S.UX, S.UY)              # unit along the face (ENE)
# For the roll-out the doors OPEN: a 777 spans 64.8 m and the everyday 30 m
# bay cannot pass it - the first solve caught that before any render did.
# This clip dresses the 100 m door with the leaves stacked 12 m at each end,
# a 76 m opening centred on the face (5.6 m per wingtip, the same order as
# hangar 9's 8.9 for the 787). The SHARED field keeps its 30 m gap; the
# ray-cast proved nothing solid stands behind the door band, so only the two
# dressing objects are replaced, locally, in this blend.
OPEN_HALF = 38.0
DOOR_H = 20.5
BAY_C = FACE_C                    # the tow corridor runs through face centre

# --- the aeroplane (B77W master, place_777.py's cited geometry) -------------
NOSE_X, TAIL_X = 0.0, 73.95
NOSE_GEAR_X, MAIN_GEAR_X = 5.3, 36.5
WHEELBASE = MAIN_GEAR_X - NOSE_GEAR_X          # 31.2
FIN_TOP = 18.5
SPAN = 64.8

# --- the entry path (solved forward, PLAYED BACKWARD) -----------------------
# Heading is the control curve. The swing must be DONE before the wingtips
# reach the plane (each degree of heading moves a tip 0.57 m sideways and the
# margin is 5.6), so it lives entirely in the first ~25 m of entry path and
# the corridor is flown square from there on.
HEADING = [(1, 318.65), (60, 328.0), (100, 337.0), (130, 342.0),
           (155, 343.65), (400, 343.65)]
TRAVEL = 76.5
# entry speeds (m/s): 5.0 on the open apron easing to 1.0 at the deep end.
# The reversed clip therefore ACCELERATES away, ending at 18 km/h - a 16 s
# clip compresses a quarter-hour job, exactly as the Sao Carlos tow did.
SPEED = [(1, 5.0), (120, 4.4), (250, 2.6), (330, 1.5), (400, 1.0)]
# nose gear ends 70.65 m past the door plane: tail 2 m inside the leaves,
# nose 16 m clear of the back wall of the 92 m hall.
NG_END = (BAY_C[0] - 70.65 * OUT_N[0], BAY_C[1] - 70.65 * OUT_N[1])

TOWBAR_L = 6.0
TUG_L, TUG_W, TUG_H = 7.5, 3.0, 1.45

# --- the camera -------------------------------------------------------------
# The forecourt is NOT empty: stand R910 parks a 767 at 109 m straight out
# from the door (the first camera ended 7 m inside it and the proof frame
# was a wall of fuselage). The camera lives in the clear cell BETWEEN the
# door and the row: 58-64 m out, west of the corridor.
CAM0 = (BAY_C[0] + 64.0 * OUT_N[0] - 52.0 * ALONG[0],
        BAY_C[1] + 64.0 * OUT_N[1] - 52.0 * ALONG[1], Z_APRON + 8.5)
# ...and it RETREATS west as the aeroplane comes out: a 74 m fuselage at
# 50 m overfills a 35 mm frame (the second proof), so the close is shot
# from 110 m with the lens easing wide.
CAM1 = (BAY_C[0] + 78.0 * OUT_N[0] - 78.0 * ALONG[0],
        BAY_C[1] + 78.0 * OUT_N[1] - 78.0 * ALONG[1], Z_APRON + 7.0)
AIM0 = (BAY_C[0] - 10.0 * OUT_N[0], BAY_C[1] - 10.0 * OUT_N[1], Z_APRON + 10.0)
AIM1 = (2319.0, 1283.0, Z_APRON + 8.0)   # between final mg and tail
LENS = [(1, 35.0), (240, 34.0), (400, 29.5)]
DRIFT = ((0.9, 11.0, 0.4), (0.5, 8.0, 2.3))

# the static prop tug build_scenery parks beside the stand (checked in the
# report: it must stay outside the swept path of engines and gear)
PROP_TUG = (2339.1, 1302.4)


def arclengths():
    raw, acc = [0.0], 0.0
    for f in range(2, FRAME_END + 1):
        acc += S.piecewise(f - 0.5, SPEED) / FPS
        raw.append(acc)
    k = TRAVEL / raw[-1]
    return [x * k for x in raw]


def solve_entry():
    """Forward entry rows; the Blender bake reads them REVERSED."""
    s = arclengths()
    mg, x, y = [], 0.0, 0.0
    for f in range(FRAME_END):
        if f:
            h = math.radians(S.piecewise(f + 0.5, HEADING))
            ds = s[f] - s[f - 1]
            x += ds * math.sin(h)
            y += ds * math.cos(h)
        mg.append((x, y))
    ng = []
    for f in range(FRAME_END):
        h = math.radians(S.piecewise(f + 1, HEADING))
        ng.append((mg[f][0] + WHEELBASE * math.sin(h),
                   mg[f][1] + WHEELBASE * math.cos(h)))
    dx, dy = NG_END[0] - ng[-1][0], NG_END[1] - ng[-1][1]
    mg = [(p[0] + dx, p[1] + dy) for p in mg]
    ng = [(p[0] + dx, p[1] + dy) for p in ng]
    rows = []
    for f in range(FRAME_END):
        h = S.piecewise(f + 1, HEADING)
        rows.append(dict(f=f + 1, mg=mg[f], ng=ng[f], head=h))
    # nose-wheel steering = atan(W * dh/ds), reported not baked
    for a, b in zip(rows, rows[1:]):
        ds = math.dist(a["mg"], b["mg"]) or 1e-9
        a["steer"] = math.degrees(math.atan(math.radians(
            (b["head"] - a["head"])) * WHEELBASE / ds))
    rows[-1]["steer"] = 0.0
    return rows


def door_gap(p):
    """Signed distance of a point OUTSIDE the door plane (negative = inside)."""
    return ((p[0] - FACE_C[0]) * OUT_N[0] + (p[1] - FACE_C[1]) * OUT_N[1])


def along_face(p):
    return ((p[0] - FACE_C[0]) * ALONG[0] + (p[1] - FACE_C[1]) * ALONG[1])


def nose_tail(row):
    h = math.radians(row["head"])
    u = (math.sin(h), math.cos(h))
    nose = (row["ng"][0] + (NOSE_GEAR_X - NOSE_X) * u[0],
            row["ng"][1] + (NOSE_GEAR_X - NOSE_X) * u[1])
    tail = (row["mg"][0] - (TAIL_X - MAIN_GEAR_X) * u[0],
            row["mg"][1] - (TAIL_X - MAIN_GEAR_X) * u[1])
    return nose, tail


def wingtips(row):
    h = math.radians(row["head"])
    r = (math.cos(h), -math.sin(h))
    # wing centre ~ 2 m ahead of the main gear
    u = (math.sin(h), math.cos(h))
    c = (row["mg"][0] + 2.0 * u[0], row["mg"][1] + 2.0 * u[1])
    return ((c[0] + 0.5 * SPAN * r[0], c[1] + 0.5 * SPAN * r[1]),
            (c[0] - 0.5 * SPAN * r[0], c[1] - 0.5 * SPAN * r[1]))


def camera_rows(nframes=FRAME_END):
    rows = []
    for f in range(1, nframes + 1):
        t = (f - 1) / float(nframes - 1)
        tt = t * t * (3 - 2 * t)
        cam = tuple(a + (b - a) * tt for a, b in zip(CAM0, CAM1))
        aim = tuple(a + (b - a) * tt for a, b in zip(AIM0, AIM1))
        ts = f / FPS
        cam = (cam[0] + DRIFT[0][0] * math.sin(2 * math.pi * ts / DRIFT[0][1]
                                               + DRIFT[0][2]),
               cam[1] + DRIFT[1][0] * math.sin(2 * math.pi * ts / DRIFT[1][1]
                                               + DRIFT[1][2]),
               cam[2])
        dx, dy, dz = aim[0] - cam[0], aim[1] - cam[1], aim[2] - cam[2]
        rows.append(dict(f=f, cam=cam, az=math.atan2(dx, dy),
                         el=math.atan2(dz, math.hypot(dx, dy)),
                         lens=S.piecewise(f, LENS)))
    for key in ("az", "el"):
        for r, x in zip(rows, S.gaussian_smooth([r[key] for r in rows], 6.0)):
            r[key] = x
    return rows


def report(entry, cams):
    print("%-5s %10s %10s %8s %7s %8s %8s"
          % ("f_out", "mg", "head", "steer", "tail_gap", "fin_u", "clr_tug"))
    for i in (1, 60, 120, 180, 240, 300, 360, 400):
        row = entry[FRAME_END - i]          # reversed playback
        nose, tail = nose_tail(row)
        cr = cams[i - 1]
        u, v, _ = S.project(cr["cam"], cr["az"], cr["el"], cr["lens"],
                            (tail[0], tail[1], Z_APRON + FIN_TOP - 2.0))
        d_tug = min(math.dist(row["mg"], PROP_TUG),
                    math.dist(nose, PROP_TUG), math.dist(tail, PROP_TUG))
        print("%-5d %10s %10.2f %8.2f %8.1f %8.2f %8.1f"
              % (i, "(%.0f,%.0f)" % row["mg"], row["head"],
                 row.get("steer", 0.0), door_gap(tail), u, d_tug))
    # door clearances at the tightest frame (tail crossing the plane)
    worst_lat, worst_f = 99.0, 0
    for row in entry:
        nose, tail = nose_tail(row)
        if -3.0 < door_gap(tail) < 3.0:
            lat = OPEN_HALF - abs(along_face(tail))
            if lat < worst_lat:
                worst_lat, worst_f = lat, row["f"]
        for tip in wingtips(row):
            if -1.0 < door_gap(tip) < 1.0:
                lat = OPEN_HALF - abs(along_face(tip))
                print("   wingtip crosses the plane at entry f%d with "
                      "%.1f m to the leaf" % (row["f"], lat))
    print("tail crosses the door plane with %.2f m of lateral margin "
          "(entry f%d); fin top %.1f under the %.1f door"
          % (worst_lat, worst_f, FIN_TOP, DOOR_H))
    S.flow_report(cams, "SBGR roll-out (camera)")
    sun = S.SUN_AZIM_DEG
    offs = [abs((math.degrees(r["az"]) - sun + 540) % 360 - 180)
            for r in cams]
    print("sun stays %.0f..%.0f deg off the lens" % (min(offs), max(offs)))


def main():
    import bpy

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(HERE, "sbgr_rollout.blend")
    scn = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    FIELD = os.path.join(HERE, "sbgr_field.blend")
    TERRAIN = os.path.join(HERE, "sbgr_terrain.blend")
    MASTER = os.path.join(os.path.dirname(HERE), "boeing 777-300ER",
                          "B77W_LATAM.blend")

    def link(path, name):
        with bpy.data.libraries.load(path, link=True) as (src, dst):
            dst.collections = [name]
        c = dst.collections[0]
        ob = bpy.data.objects.new(name + "_Link", None)
        ob.instance_type = "COLLECTION"
        ob.instance_collection = c
        scn.collection.objects.link(ob)
        return c

    # The field is NOT linked wholesale: SBGR_LATAM_Base comes in as an
    # APPEND (local, editable) so this clip can open the hangar doors; every
    # sibling collection is linked read-only as usual. The ray-cast in the
    # docstring is what makes this safe: nothing solid stands behind the two
    # door-dressing objects, so replacing them opens the wall.
    SIBLINGS = ("SBGR_Runways", "SBGR_Taxiways", "SBGR_Aprons", "SBGR_Ground",
                "SBGR_Terminals", "SBGR_Buildings", "SBGR_BASP", "SBGR_Cargo",
                "SBGR_Furniture", "SBGR_Roads", "SBGR_Rail", "SBGR_Water",
                "SBGR_City", "SBGR_Vegetation", "SBGR_Operations")
    for name in SIBLINGS:
        link(FIELD, name)
    link(FIELD, "SBGR_Light")
    with bpy.data.libraries.load(FIELD, link=False) as (src, dst):
        dst.collections = ["SBGR_LATAM_Base"]
    base_coll = dst.collections[0]
    scn.collection.children.link(base_coll)
    if os.path.exists(TERRAIN):
        link(TERRAIN, "SBGR_Terrain")
    with bpy.data.libraries.load(FIELD, link=True) as (src, dst):
        dst.worlds = ["SBGR_World"]
    scn.world = dst.worlds[0]

    # ---- open the doors ----------------------------------------------------
    import bmesh
    clad_mat = None
    for nm in ("SBGR_LATAM_HangarDoors", "SBGR_LATAM_HangarOpenBay"):
        ob = bpy.data.objects.get(nm)
        if ob:
            if nm.endswith("Doors") and ob.data.materials:
                clad_mat = ob.data.materials[0]
            bpy.data.objects.remove(ob, do_unlink=True)
    # stacked leaves: three 4 m panels at each end of the 100 m door, and a
    # dark reveal strip behind each stack
    def leafbox(name, t0, t1, depth0, depth1, z0, z1, mat):
        bm = bmesh.new()
        cs = []
        for (t, dep) in ((t0, depth0), (t1, depth0), (t1, depth1), (t0, depth1)):
            cs.append((FACE_C[0] + t * ALONG[0] - dep * OUT_N[0],
                       FACE_C[1] + t * ALONG[1] - dep * OUT_N[1]))
        vs_b = [bm.verts.new((c[0], c[1], z0)) for c in cs]
        vs_t = [bm.verts.new((c[0], c[1], z1)) for c in cs]
        bm.faces.new(vs_b)
        bm.faces.new(list(reversed(vs_t)))
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((vs_b[i], vs_b[j], vs_t[j], vs_t[i]))
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        if mat:
            me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        base_coll.objects.link(ob)
        return ob
    for side in (-1, 1):
        for k in range(3):
            t_in = side * (38.0 + k * 4.0)
            t_out = side * (38.0 + (k + 1) * 4.0)
            leafbox("Roll_Leaf_%+d_%d" % (side, k), t_in, t_out,
                    0.30 + k * 0.55, 0.85 + k * 0.55,
                    Z_APRON - 0.05, Z_APRON - 0.05 + DOOR_H, clad_mat)
    # The body's SSE wall is solid behind the dressing (the ray-cast saw
    # only the FIRST hit - the proof frame showed the fin embedded in
    # cladding). Cut the 76 x 20.5 opening into the appended body: bisect
    # the SSE-facing faces at the two jambs and the lintel, delete the
    # middle-low pieces, keep the wall above the door and beyond the jambs.
    body = bpy.data.objects.get("SBGR_LATAM_Hangar")
    if body:
        bmb = bmesh.new()
        bmb.from_mesh(body.data)
        lintel_z = Z_APRON - 0.05 + DOOR_H

        def sse_faces():
            out = []
            for fce in bmb.faces:
                n = fce.normal
                # the OSM-footprint wall sits ~6 m INSIDE the analytic face
                # plane and its normals point inward - measured, not assumed
                if abs(n.x * OUT_N[0] + n.y * OUT_N[1]) > 0.5:
                    c = fce.calc_center_median()
                    if abs(door_gap((c.x, c.y))) < 8.0:
                        out.append(fce)
            return out

        for (pco, pno) in (
                ((FACE_C[0], FACE_C[1], lintel_z), (0.0, 0.0, 1.0)),
                ((FACE_C[0] - 38.0 * ALONG[0], FACE_C[1] - 38.0 * ALONG[1],
                  0.0), (ALONG[0], ALONG[1], 0.0)),
                ((FACE_C[0] + 38.0 * ALONG[0], FACE_C[1] + 38.0 * ALONG[1],
                  0.0), (ALONG[0], ALONG[1], 0.0))):
            faces = sse_faces()
            geom = list(faces)
            for fce in faces:
                geom.extend(fce.edges)
                geom.extend(fce.verts)
            bmesh.ops.bisect_plane(bmb, geom=list(set(geom)),
                                   plane_co=pco, plane_no=pno)
        doomed = []
        for fce in sse_faces():
            c = fce.calc_center_median()
            if abs(along_face((c.x, c.y))) < 38.0 and c.z < lintel_z:
                doomed.append(fce)
        bmesh.ops.delete(bmb, geom=doomed, context="FACES")
        bmb.to_mesh(body.data)
        bmb.free()
        print("body wall opened: %d faces removed" % len(doomed))

    dark = bpy.data.materials.new("Roll_Reveal_Dark")
    dark.use_nodes = True
    bsdf = dark.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.025, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    for side in (-1, 1):
        leafbox("Roll_Reveal_%+d" % side, side * 38.0, side * 50.0,
                2.4, 2.5, Z_APRON - 0.05, Z_APRON - 0.05 + DOOR_H, dark)

    import fleet_placement as F
    F.populate(scn, skip=("HGR",))       # the animated 777 replaces the prop

    # ---- the aeroplane on a pivot at the MAIN GEAR ------------------------
    piv = bpy.data.objects.new("B77W_Roll", None)
    scn.collection.objects.link(piv)
    for name in ("01_Estrutura", "02_Motores", "03_Trem", "04_Detalhes"):
        with bpy.data.libraries.load(MASTER, link=True) as (src, dst):
            dst.collections = [name]
        c = dst.collections[0]
        e = bpy.data.objects.new("Roll_" + name, None)
        e.instance_type = "COLLECTION"
        e.instance_collection = c
        e.parent = piv
        # master nose -X onto pivot-local +Y (same mapping place_777 proved)
        e.rotation_euler = (0.0, 0.0, -math.pi / 2.0)
        e.location = (0.0, MAIN_GEAR_X, 0.0)
        scn.collection.objects.link(e)

    entry = solve_entry()
    cams = camera_rows()
    report(entry, cams)

    # bake REVERSED: output frame i shows entry row FRAME_END - i
    for i in range(1, FRAME_END + 1):
        row = entry[FRAME_END - i]
        h = math.radians(row["head"])
        piv.location = (row["mg"][0], row["mg"][1], Z_APRON)
        piv.rotation_euler = (0.0, 0.0, math.atan2(-math.cos(h),
                                                   -math.sin(h))
                              + math.pi / 2.0)
        # pivot-local +Y must lie on compass "head": the master mapping puts
        # the nose on local +Y, so rotate local +Y onto the heading:
        piv.rotation_euler = (0.0, 0.0, -h)
        piv.keyframe_insert("location", frame=i)
        piv.keyframe_insert("rotation_euler", frame=i)

    # ---- the tug and towbar, on the nose-gear track ------------------------
    def prim_box(name, dims, rgb):
        me = bpy.data.meshes.new(name)
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=dims, verts=bm.verts)
        bm.to_mesh(me)
        bm.free()
        m = bpy.data.materials.new(name)
        m.diffuse_color = rgb + (1.0,)
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = rgb + (1.0,)
        me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        scn.collection.objects.link(ob)
        return ob

    tug = prim_box("Roll_Tug", (TUG_L, TUG_W, TUG_H), (0.85, 0.75, 0.12))
    bar = prim_box("Roll_Towbar", (TOWBAR_L, 0.25, 0.18), (0.35, 0.35, 0.38))
    for i in range(1, FRAME_END + 1):
        row = entry[FRAME_END - i]
        h = math.radians(row["head"])
        u = (math.sin(h), math.cos(h))
        ng = row["ng"]
        hitch = (ng[0] + TOWBAR_L * u[0], ng[1] + TOWBAR_L * u[1])
        tc = (ng[0] + (TOWBAR_L + TUG_L * 0.45) * u[0],
              ng[1] + (TOWBAR_L + TUG_L * 0.45) * u[1])
        tug.location = (tc[0], tc[1], Z_APRON + TUG_H * 0.5)
        tug.rotation_euler = (0.0, 0.0, math.atan2(u[1], u[0]))
        bc = (ng[0] + 0.5 * TOWBAR_L * u[0], ng[1] + 0.5 * TOWBAR_L * u[1])
        bar.location = (bc[0], bc[1], Z_APRON + 0.55)
        bar.rotation_euler = (0.0, 0.0, math.atan2(u[1], u[0]))
        for ob in (tug, bar):
            ob.keyframe_insert("location", frame=i)
            ob.keyframe_insert("rotation_euler", frame=i)

    # ---- bay interior, local to this clip (the SDSC tow rule: never in the
    # shared asset) - a pale floor pad and six warm lamps inside the bay
    floor = prim_box("Roll_BayFloor", (34.0, 80.0, 0.1), (0.62, 0.63, 0.66))
    fl_c = (BAY_C[0] - 44.0 * OUT_N[0], BAY_C[1] - 44.0 * OUT_N[1])
    floor.location = (fl_c[0], fl_c[1], Z_APRON + 0.03)
    floor.rotation_euler = (0.0, 0.0, math.atan2(OUT_N[1], OUT_N[0]))
    for k in range(6):
        lam = bpy.data.lights.new("Roll_Bay_L%d" % k, type="POINT")
        lam.energy = 30000.0
        lam.color = (1.0, 0.92, 0.80)
        lo = bpy.data.objects.new("Roll_Bay_L%d" % k, lam)
        off = (k % 3 - 1) * 12.0
        dep = 20.0 + (k // 3) * 35.0
        lo.location = (BAY_C[0] - dep * OUT_N[0] + off * ALONG[0],
                       BAY_C[1] - dep * OUT_N[1] + off * ALONG[1],
                       Z_APRON + 17.0)
        scn.collection.objects.link(lo)

    # ---- the camera --------------------------------------------------------
    cd = bpy.data.cameras.new("CamRollout")
    cam = bpy.data.objects.new("CamRollout", cd)
    scn.collection.objects.link(cam)
    cd.clip_start = 0.5
    cd.clip_end = 250000.0
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = S.SENSOR
    for r in cams:
        cam.location = r["cam"]
        cam.rotation_euler = (math.pi / 2.0 + r["el"], 0.0, -r["az"])
        cam.keyframe_insert("location", frame=r["f"])
        cam.keyframe_insert("rotation_euler", frame=r["f"])
        cd.lens = r["lens"]
        cd.keyframe_insert("lens", frame=r["f"])

    def fcurves(act):
        if len(getattr(act, "fcurves", [])):
            return list(act.fcurves)
        fs = []
        for lay in act.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    fs.extend(cb.fcurves)
        return fs

    for ob in (piv, tug, bar, cam, cd):
        for c in fcurves(ob.animation_data.action):
            for kp in c.keyframe_points:
                kp.interpolation = "LINEAR"
            c.update()

    scn.camera = cam
    scn.render.fps, scn.render.fps_base = 25, 1.0
    scn.frame_start, scn.frame_end = 1, FRAME_END
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 96
    scn.cycles.use_denoising = True
    scn.cycles.max_bounces = 4
    scn.render.resolution_x, scn.render.resolution_y = 960, 540
    scn.render.use_motion_blur = False
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"

    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    print("saved", out)


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ImportError:
        report(solve_entry(), camera_rows())
    else:
        main()
