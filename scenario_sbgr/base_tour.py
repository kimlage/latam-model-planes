#!/usr/bin/env python3
"""Clip 3 — the aerial tour of Guarulhos: one line, four beats, no seams.

    blender -b --factory-startup -P scenario_sbgr/base_tour.py -- \\
        --out scenario_sbgr/sbgr_base_tour.blend

    python3 scenario_sbgr/base_tour.py      # offline solve, no Blender

The Santiago/São Carlos survey grammar, applied to a field ten times the
area: ONE straight camera line at constant speed with a travelling aim —
the two-base lesson that a tour reads as one gesture or it reads as a
slideshow. The four beats are phase 2's own proven check framings
(`render_checks.py check_tour`), flown through instead of cut between:

    open    south-west and high: the terminal crescent and the tower in
            front of the camera, the Cantareira wall across the top.
    middle  crabbing north-east along the south side: both runways cross
            the frame, the mid-field, the cargo apron, the city ring
            beyond the fence — never an empty ring.
    close   the NE corner: the LATAM hangar with its 777, the 901 row,
            and the east city behind them.

The camera never drops below 300 m — phase 2's rule is >100 m near the NE
fence (the 30 m tint patchwork is the weakest close-up surface) and the
whole line clears that with margin. Sun 251° stays 65–100° off the lens,
behind-left, for all 240 frames.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import shot_common as S                                       # noqa: E402

FRAME_END = 240

# Camera line and travelling aim, ENU metres. PCHIP through the knots;
# the camera knots are ON one straight line so the speed is the only thing
# the interpolation shapes (a gentle ease at both ends).
CAM_A = (500.0, -1500.0, 430.0)     # over the BASP corner, south-west
CAM_B = (3150.0, 350.0, 300.0)      # past the NE corner
AIM = [(1, (150.0, 720.0, -9.0)),
       (240, (2300.0, 1355.0, 5.0)), (275, (2560.0, 1400.0, 7.0))]
LENS = [(1, 34.0), (120, 35.5), (240, 38.0), (275, 38.5)]

AIM_SMOOTH = 8.0
RATE_SMOOTH = 6.0


def _interp3(f, knots):
    pts = {i: [(k, v[i]) for k, v in knots] for i in range(3)}
    return tuple(S.piecewise(f, pts[i]) for i in range(3))


def solve_shot(nframes=FRAME_END):
    rows = []
    for f in range(1, nframes + 1):
        # the camera line is LITERALLY constant-rate: the two-base tour rule
        # is one gesture, and PCHIP knots on a line still modulate the speed
        # (the first solve peaked at 478 m/s with 722 m/s2 of acceleration).
        t = (f - 1) / float(nframes - 1)
        cam = tuple(a + (b - a) * t for a, b in zip(CAM_A, CAM_B))
        aim = _interp3(f, AIM)
        dx, dy, dz = (aim[0] - cam[0], aim[1] - cam[1], aim[2] - cam[2])
        az = math.atan2(dx, dy)
        el = math.atan2(dz, math.hypot(dx, dy))
        rows.append(dict(f=f, cam=cam, az=az, el=el,
                         lens=S.piecewise(f, LENS)))
    for key in ("az", "el"):
        vals = S.unwrap([r[key] for r in rows]) if key == "az" else \
            [r[key] for r in rows]
        for r, x in zip(rows, S.gaussian_smooth(vals, AIM_SMOOTH)):
            r[key] = x
    az = [r["az"] for r in rows]
    dstep = S.gaussian_smooth([b - a for a, b in zip(az, az[1:])],
                              RATE_SMOOTH)
    acc = [az[0]]
    for step in dstep:
        acc.append(acc[-1] + step)
    for r, x in zip(rows, acc):
        r["az"] = x
    return rows


LANDMARKS = {
    "tower": (390.0, 630.0, 45.0),
    "terminals": (100.0, 750.0, 5.0),
    "hangar": (2281.2, 1361.7, S.HANGAR_EAVE_Z),
    "row901": (2150.0, 1120.0, -5.0),
    "city_e": (3300.0, 1600.0, 20.0),
    "thr10L": (S.THR_X, S.THR_Y, S.Z_THR10L),
}


def report(rows):
    print("%-5s %26s %8s %8s %7s" % ("frame", "cam", "az_deg", "el_deg",
                                     "lens"))
    for r in rows:
        if r["f"] % 40 and r["f"] not in (1, FRAME_END):
            continue
        print("%-5d %26s %8.1f %8.2f %7.1f"
              % (r["f"], "(%.0f, %.0f, %.0f)" % r["cam"],
                 math.degrees(r["az"]) % 360.0, math.degrees(r["el"]),
                 r["lens"]))
    S.flow_report(rows, "SBGR aerial tour")
    sun = S.SUN_AZIM_DEG
    offs = [abs((math.degrees(r["az"]) - sun + 540) % 360 - 180)
            for r in rows]
    print("sun stays %.0f..%.0f deg off the lens axis" % (min(offs),
                                                          max(offs)))
    print("\n%-5s %s" % ("frame", " ".join("%13s" % k for k in LANDMARKS)))
    for r in rows:
        if r["f"] % 60 and r["f"] not in (1, FRAME_END):
            continue
        cells = []
        for k, p in LANDMARKS.items():
            u, v, _ = S.project(r["cam"], r["az"], r["el"], r["lens"], p)
            cells.append("%5.2f,%5.2f%s" % (u, v,
                                            " " if 0 <= u <= 1 and 0 <= v <= 1
                                            else "*"))
        print("%-5d %s" % (r["f"], " ".join("%13s" % c for c in cells)))


def main():
    import bpy

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(HERE, "sbgr_base_tour.blend")
    scn = bpy.context.scene

    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    FIELD = os.path.join(HERE, "sbgr_field.blend")
    TERRAIN = os.path.join(HERE, "sbgr_terrain.blend")

    def link(path, name):
        with bpy.data.libraries.load(path, link=True) as (src, dst):
            dst.collections = [name]
        c = dst.collections[0]
        ob = bpy.data.objects.new(name + "_Link", None)
        ob.instance_type = "COLLECTION"
        ob.instance_collection = c
        scn.collection.objects.link(ob)

    for name in ("SBGR_Field", "SBGR_Light"):
        link(FIELD, name)
    if os.path.exists(TERRAIN):
        link(TERRAIN, "SBGR_Terrain")
    with bpy.data.libraries.load(FIELD, link=True) as (src, dst):
        dst.worlds = ["SBGR_World"]
    scn.world = dst.worlds[0]

    import fleet_placement as F
    F.populate(scn)

    rows = solve_shot(FRAME_END)
    report(rows)

    cd = bpy.data.cameras.new("CamTour")
    cam = bpy.data.objects.new("CamTour", cd)
    scn.collection.objects.link(cam)
    cd.clip_start = 1.0
    cd.clip_end = 250000.0
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = S.SENSOR
    for r in rows:
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

    for act in (cam.animation_data.action, cd.animation_data.action):
        for c in fcurves(act):
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
    scn.render.use_motion_blur = False      # same GPU-memory reasoning as
    scn.view_settings.view_transform = "AgX"  # the departure clip
    scn.view_settings.look = "AgX - Medium High Contrast"

    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    print("saved", out)


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ImportError:
        report(solve_shot(FRAME_END))
    else:
        main()
