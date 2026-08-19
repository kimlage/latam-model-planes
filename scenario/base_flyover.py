#!/usr/bin/env python3
"""The second clip: a drone orbit of the LATAM maintenance base.

    blender -b --factory-startup scenario/scl_field.blend \\
        -P scenario/base_flyover.py -- --out scenario/scl_base_flyover.blend

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
  depression to the centre grows 14.9 -> 20.1 deg
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

    # terrain, linked exactly as render_checks does
    if os.path.exists(TERRAIN):
        with bpy.data.libraries.load(TERRAIN, link=True) as (src, dst):
            dst.collections = [c for c in src.collections if c == "SCL_Terrain"]
        for c in dst.collections:
            if c is None:
                continue
            ob = bpy.data.objects.new("SCL_Terrain_Link", None)
            ob.instance_type = "COLLECTION"
            ob.instance_collection = c
            bpy.context.scene.collection.objects.link(ob)

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
