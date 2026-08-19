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
The owner asked to see the base CLOSER, and for a camera that does not lose
fluidity. The take-off clip's residual artificiality lives in its hand-over
(dolly frame -> aircraft frame); this shot has no hand-over and no solver.
It is one continuous orbit at CONSTANT angular rate - every control value is
linear in the frame number, so the pan rate ratio is 1.0 by construction and
the loop restarts mid-motion the way every version of the take-off GIF
already does.

Geometry (world frame, metres):
- subject centre (-590, -1290, 10): between the ops building / hangar block
  and the apron rows where the LATAM tails park
- camera bearing FROM the centre sweeps 215 deg -> 288 deg: the camera stays
  in the west half the whole time, so the 15 deg sun stays behind it, the
  SIGN faces it (west facade), and the cordillera is the permanent backdrop
- radius 420 -> 375 m, height 112 -> 137 m: a gentle push-in and rise;
  depression to the centre grows 14.9 -> 20.1 deg. A 340 m orbit was tried
  and rejected: it crops the sign and fills the frame with hangar roof
- lens 30 mm, fixed: a drone does not zoom
- aim: azimuth dead on the centre (the base holds u = 0.5); elevation runs
  -8 -> -10 deg, which keeps the base at v ~ 0.3 and the Andes crest inside
  the top of the frame (v ~ 0.80 -> 0.86) - the pinned-horizon rule from the
  take-off shot, done here with a constant instead of a solver

At 30 mm from ~400 m the base block plus apron spans roughly three quarters
of the frame width: the hangar doors, the sign lockup, the window band and
the parked tails all read. Pan rate 73 deg / 9.6 s = 7.6 deg/s through a
62 deg hfov = 0.12 frame-widths/s - inside the calm band by a factor of 4.
"""
import bpy
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TERRAIN = os.path.join(HERE, "scl_terrain.blend")

CENTER = (-590.0, -1290.0, 10.0)
FRAME_END = 240
A0, A1 = 215.0, 288.0          # camera bearing from the centre, compass deg
R0, R1 = 420.0, 375.0          # orbit radius, m
H0, H1 = 112.0, 137.0          # camera height, m
EL0, EL1 = -8.0, -10.0         # aim elevation, deg (negative = down)
LENS = 30.0


def pose(f):
    t = (f - 1) / float(FRAME_END - 1)
    a = math.radians(A0 + (A1 - A0) * t)
    r = R0 + (R1 - R0) * t
    h = H0 + (H1 - H0) * t
    x = CENTER[0] + r * math.sin(a)
    y = CENTER[1] + r * math.cos(a)
    look = a - math.pi                      # dead at the centre
    el = math.radians(EL0 + (EL1 - EL0) * t)
    return (x, y, h), look, el


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
