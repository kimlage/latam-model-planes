#!/usr/bin/env python3
"""The second clip: a drone orbit of the LATAM maintenance base.

    blender -b "airbus A320neo/A320neo_scl.blend" \\
        -P scenario/base_flyover.py -- --out scenario/scl_base_flyover.blend

It runs on the PLACED take-off file, not on the bare field: that file
already carries the fully assembled PT-TMN (rig, gear hinges, livery) with
the scenery linked. The aircraft is frozen at frame 1 - on its wheels, gear
down - and its placement empty is swung 180 deg about the pivot and moved
to a stand on Plataforma LATAM, 40 m south of the hangar doors, nose north
like the proxy rows. Linking the model's sub-collections was tried first
and failed structurally: the parts hang from parent empties that live
outside those collections, so an instance disassembles into a fin sticking
out of the apron.

Why this shot is built the way it is
------------------------------------
v4, after three orbit versions: the owner pointed out the clip only ever
showed the LATAM base - the REST of the airport was missing. The orbit
became a northbound aerial SURVEY of the whole east-side infrastructure:

- the camera travels a straight line 2.0 km long, west of both runways
  (x -1750), from SSW of the terminals to north of the base, climbing
  280 -> 330 m at 208 m/s - at that altitude nothing is near enough to
  rush, and every control value is linear, so the move keeps the
  constant-rate fluidity of the orbits
- the AIM travels too: it opens on the T1/T2 terminal core - piers, jet
  bridges, the parked fleet - crosses the control tower mid-clip, and
  settles on the LATAM base with the assembled PT-TMN at its stand
- both runways cross the lower frame the whole way; the Andes hold the
  top; the sun (267 deg) stays behind the camera end to end
- lens 38 mm fixed; the aim point rides at v ~ 0.38 (TILT_UP), which
  keeps the crest inside the frame until the closing seconds
- pan is 79 -> 109 deg true, 3.1 deg/s through a 50 deg hfov: 0.06
  frame-widths/s of pan, with translation parallax bounded by altitude

"""
import bpy
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TERRAIN = os.path.join(HERE, "scl_terrain.blend")

AIM0 = (-230.0, -2600.0, 12.0)   # T1/T2 terminal core
AIM1 = (-590.0, -1290.0, 10.0)   # the LATAM base
CAM0 = (-1750.0, -2900.0, 280.0)  # west of both runways, SSW of the terminals
CAM1 = (-1750.0, -900.0, 330.0)   # same line, north of the base
FRAME_END = 240
LENS = 38.0
TILT_UP = math.radians(3.7)       # puts the aim point at v ~ 0.38


def pose(f):
    t = (f - 1) / float(FRAME_END - 1)
    cam = tuple(a + (b - a) * t for a, b in zip(CAM0, CAM1))
    aim = tuple(a + (b - a) * t for a, b in zip(AIM0, AIM1))
    dx, dy = aim[0] - cam[0], aim[1] - cam[1]
    look = math.atan2(dx, dy)                      # compass, radians
    horiz = math.hypot(dx, dy)
    el = math.atan2(aim[2] - cam[2], horiz) + TILT_UP
    return cam, look, el


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(HERE, "scl_base_flyover.blend")

    # terrain, only when running on the bare field file
    if os.path.exists(TERRAIN) and "SCL_Terrain" not in bpy.data.collections:
        with bpy.data.libraries.load(TERRAIN, link=True) as (src, dst):
            dst.collections = [c for c in src.collections if c == "SCL_Terrain"]
        for c in dst.collections:
            if c is None:
                continue
            ob = bpy.data.objects.new("SCL_Terrain_Link", None)
            ob.instance_type = "COLLECTION"
            ob.instance_collection = c
            bpy.context.scene.collection.objects.link(ob)

    # The hero: freeze the assembled PT-TMN at frame 1 and park it at the
    # base. Rotation is 180.000 deg exactly (357.424 - 177.424), applied
    # about the PIVOT's world position, not the empty's origin.
    piv = bpy.data.objects.get("AviaoPivo")
    rig = bpy.data.objects.get("SCL_Placement")
    if piv is not None and rig is not None:
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        for ob in bpy.data.objects:
            if ob.animation_data and ob.animation_data.action \
                    and ob.name != "CamBase":
                loc, rot = ob.location[:], ob.rotation_euler[:]
                ob.animation_data_clear()
                ob.location, ob.rotation_euler = loc, rot
        # By the hangar doors, nose north - broadside to the west camera.
        # Plataforma Papa was tried as a foreground stand and taught the
        # vertical-FOV lesson: ground closer than ~240 m of track passes
        # BELOW the frame (depression > el + vfov/2). A white fuselage
        # 400 m away in haze will never pop off pale concrete; the hero is
        # an honest detail for the viewer who looks, not the subject.
        stand = (-560.0, -1330.0)
        rig.rotation_euler.z += math.pi        # 357.424 - 177.424, exactly
        bpy.context.view_layer.update()

        # Self-verifying placement: evaluate the real world envelope of the
        # aircraft meshes and put the WHEELS on the apron and the CENTRE on
        # the stand, instead of trusting any convention about the rig.
        import mathutils

        def hero_meshes():
            # only render-visible meshes riding the rig NEAR the pivot: the
            # hierarchy also carries livery-raster support meshes parked
            # hundreds of metres away, which poison a naive envelope
            pw = piv.matrix_world.translation
            out = []
            for ob in bpy.data.objects:
                if ob.type != "MESH" or ob.hide_render:
                    continue
                p = ob
                while p is not None:
                    if p is rig:
                        c = ob.matrix_world.translation
                        if (c - pw).length < 80.0:
                            out.append(ob)
                        break
                    p = p.parent
            return out

        def envelope():
            dg = bpy.context.evaluated_depsgraph_get()
            lo = mathutils.Vector((1e9, 1e9, 1e9))
            hi = mathutils.Vector((-1e9, -1e9, -1e9))
            for ob in hero_meshes():
                mw = ob.evaluated_get(dg).matrix_world
                for c in ob.bound_box:
                    w = mw @ mathutils.Vector(c)
                    lo = mathutils.Vector(map(min, lo, w))
                    hi = mathutils.Vector(map(max, hi, w))
            return lo, hi

        lo, hi = envelope()
        rig.location.x += stand[0] - (lo.x + hi.x) * 0.5
        rig.location.y += stand[1] - (lo.y + hi.y) * 0.5
        rig.location.z += 0.06 - lo.z          # wheels onto the apron
        bpy.context.view_layer.update()
        lo, hi = envelope()
        print("hero PT-TMN parked: x %.1f..%.1f y %.1f..%.1f z %.2f..%.2f"
              % (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))

        old_cam = bpy.data.objects.get("CamDecolagem")
        if old_cam is not None:
            bpy.data.objects.remove(old_cam, do_unlink=True)

        # Two more DETAILED A320s on free stands - pure translations of the
        # hero (same heading), duplicated hierarchies sharing mesh data. The
        # owner's brief: the base must be populated with the models we built,
        # not the low-poly proxies. Stand clearances checked against the
        # proxy rows (46 m rule from build_parked_aircraft).
        def copy_subtree(root, dx, dy, tag):
            mapping = {}

            def rec(ob, parent_copy):
                nc = ob.copy()
                mapping[ob] = nc
                bpy.context.scene.collection.objects.link(nc)
                if parent_copy is not None:
                    nc.parent = parent_copy
                    nc.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
                for ch in ob.children:
                    rec(ch, nc)
            rec(root, None)
            r = mapping[root]
            r.location.x += dx
            r.location.y += dy
            r.name = "SCL_Hero_%s" % tag
            return r

        for i, (sx, sy) in enumerate(((-560.0, -1455.0), (-435.0, -1490.0))):
            copy_subtree(rig, sx - stand[0], sy - stand[1], "A320_%d" % i)
        print("2 detailed A320 copies placed")

        # And the other DETAILED masters, appended. Their parts are
        # world-coordinate roots (no rig, zero parented objects - verified
        # per file), so each set is parented to a fresh empty, rotated
        # nose-north (nose is local -X: Rz(-90) points it +Y) and placed by
        # the same self-verifying envelope. One aircraft of each type we
        # have built now stands on the maintenance aprons.
        ROOT = os.path.dirname(HERE)
        MASTERS = (
            ("B789", os.path.join(ROOT, "boeing 787-9", "B789_LATAM.blend"),
             (-545.0, -1100.0)),
            ("A319", os.path.join(ROOT, "airbus A319", "A319_LATAM.blend"),
             (-828.0, -1355.0)),   # Plataforma Papa, between the two proxies
            ("A321", os.path.join(ROOT, "airbus A321neo",
                                  "A321neo_LATAM.blend"),
             (-450.0, -1420.0)),   # east edge of Plataforma LATAM
            ("A320ceo", os.path.join(ROOT, "airbus A320ceo",
                                     "A320ceo_LATAM.blend"),
             (-828.0, -1300.0)),   # Plataforma Papa, north of the A319
            ("A321ceo", os.path.join(ROOT, "airbus A321ceo",
                                     "A321ceo_LATAM.blend"),
             (-435.0, -1345.0)),   # between the hero row and the neo
            # the wide-bodies take the north end of Plataforma LATAM, where
            # the apron is deepest: the 777 needs 65 m of span and 74 m of
            # length, which no narrow-body stand can hold
            ("B77W", os.path.join(ROOT, "boeing 777-300ER",
                                  "B77W_LATAM.blend"),
             (-660.0, -1090.0)),
            ("B788", os.path.join(ROOT, "boeing 787-8",
                                  "B788_LATAM.blend"),
             (-455.0, -1130.0)),
            ("B763", os.path.join(ROOT, "boeing 767-300ER",
                                  "B763_LATAM.blend"),
             (-655.0, -1235.0)),
        )
        for tag, path, stand_i in MASTERS:
            if not os.path.exists(path):
                print("!! master missing:", path)
                continue
            with bpy.data.libraries.load(path, link=False) as (src, dst):
                dst.collections = [c for c in src.collections
                                   if c in ("01_Estrutura", "02_Motores",
                                            "03_Trem", "04_Detalhes")]
            root_i = bpy.data.objects.new("SCL_Hero_" + tag, None)
            bpy.context.scene.collection.objects.link(root_i)
            b_obs = []
            for c in dst.collections:
                if c is None:
                    continue
                bpy.context.scene.collection.children.link(c)
                for ob in c.all_objects:
                    b_obs.append(ob)
                    if ob.parent is None:
                        ob.parent = root_i
            root_i.rotation_euler = (0.0, 0.0, -math.pi / 2.0)
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            lo = mathutils.Vector((1e9, 1e9, 1e9))
            hi = mathutils.Vector((-1e9, -1e9, -1e9))
            for ob in b_obs:
                if ob.type != "MESH" or ob.hide_render:
                    continue
                mw = ob.evaluated_get(dg).matrix_world
                for cn in ob.bound_box:
                    w = mw @ mathutils.Vector(cn)
                    lo = mathutils.Vector(map(min, lo, w))
                    hi = mathutils.Vector(map(max, hi, w))
            root_i.location.x += stand_i[0] - (lo.x + hi.x) * 0.5
            root_i.location.y += stand_i[1] - (lo.y + hi.y) * 0.5
            root_i.location.z += 0.06 - lo.z
            bpy.context.view_layer.update()
            print("detailed %s parked at %s (span %.1f x %.1f m)"
                  % (tag, stand_i, hi.x - lo.x, hi.y - lo.y))

    cd = bpy.data.cameras.new("CamBase")
    cd.lens = LENS
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36.0
    cd.clip_start = 1.0
    cd.clip_end = 300000.0
    cam = bpy.data.objects.new("CamBase", cd)
    bpy.context.scene.collection.objects.link(cam)

    for f in range(1, FRAME_END + 1):
        (x, y, z), look, el = pose(f)
        cam.location = (x, y, z)
        cam.rotation_euler = (math.pi / 2.0 + el, 0.0, -look)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    act = cam.animation_data.action
    fcs = list(getattr(act, "fcurves", []) or [])
    if not fcs:
        for lay in act.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    fcs.extend(cb.fcurves)
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.update()

    scn = bpy.context.scene
    scn.camera = cam
    scn.render.fps = 25
    scn.render.fps_base = 1.0
    scn.frame_start, scn.frame_end = 1, FRAME_END
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 96
    scn.cycles.use_denoising = True
    scn.cycles.max_bounces = 4
    scn.render.resolution_x, scn.render.resolution_y = 960, 540
    scn.render.use_motion_blur = True
    scn.render.motion_blur_shutter = 0.50
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"

    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    print("saved", out)


if __name__ == "__main__":
    main()
