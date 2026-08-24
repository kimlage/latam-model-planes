#!/usr/bin/env python3
"""Clip 3 — the aerial tour of the São Carlos base. Santiago's `scl_base_v7.gif` here.

    blender -b --factory-startup scenario_sdsc/sdsc_field.blend \\
        -P scenario_sdsc/base_flyover.py -- --out scenario_sdsc/sdsc_base_flyover.blend

    python3 scenario_sdsc/base_flyover.py        # solved offline, ~1 s

WHAT SANTIAGO'S FLYOVER GOT RIGHT, AND IS COPIED HERE
=====================================================
`../scenario/base_flyover.py` works for three reasons and all three transfer:

* **one continuous move at constant rate.** A straight line, linear in every
  control value, no eases, no segments. The fluidity of that clip is the
  absence of decisions inside it.
* **a travelling aim.** The camera line and the aim line are different lines,
  so the shot surveys rather than tracks — it opens on one thing and settles on
  another without the camera ever changing its mind.
* **the sun never gets in front of the lens.** Here that is azimuth 274.46°,
  which puts the camera west of everything it looks at, for the whole run.

WHAT IS DIFFERENT, AND IT IS THE HAZE
=====================================
Phase 2 calibrated V = 18 km against GROUND-level sight lines and warned that
an aerial is a different matter: from 400–700 m the slant range across this
field is 3–8 km and `checks/tour_field_south.png` is soft for exactly that
reason. It offered `HAZE_VIS_KM` as the knob.

**This clip does not touch the knob. It flies lower and closer instead.**
230 → 292 m above the plateau at 209 m/s, 930 → 1 038 m from the aim, so the
slant range never leaves ~1 km and the haze term stays at 15–16% — about what
the 2013 reference photograph shows at 1.3 km. The cost is that the whole field
is not in one frame at any instant, which is what the travelling aim is for; the
gain is that the hangar line, hangar 9 and the nose-in row are all *legible*,
which is the entire point of a tour of a maintenance base.

THE LINE, AND WHY IT IS NOT PARALLEL TO THE AIM
-----------------------------------------------
The aim runs Aeroclube → mid-field cluster → hangar 9 → hangar line. Those three
are very nearly collinear on this field — the straight line from the Aeroclube
(−212, 456) to the MRO (900, 1800) passes within 30 m of the mid-field apron —
so a single lerp gives the whole tour for free.

The camera line CONVERGES on it by about 6°. A parallel line was tried first and
is the trap: it holds the bearing exactly constant, which sounds ideal and in
fact makes the entire world slide sideways at 0.34 frame-widths per second with
nothing growing and nothing arriving. Converging costs 20° of pan across 9.6 s
— 2.3°/s, 0.04 w/s of pan — and buys a shot in which the base gets closer.

What that puts in frame, and for how long, of 240 frames:

    Aeroclube             1..32      hangar 9                90..240
    runway, mid-point     1..93      MRO hangar bay         127..240
    mid-field apron       1..156     hangar line, north end 181..240
    chequerboard tower   10..167     Museu TAM block         46..240

The lens is 38 mm and fixed. 32 mm was tried and covers more of the field, and
that is exactly its problem: at 32 mm the 471 m hangar line is 42% of the frame
width at the close instead of 50%, and a tour whose subject is a row of hangars
cannot afford to give away a fifth of them to sky and cane.

The three levels of this field are what an aerial actually shows, and they are
all in the frame: the runway on its crest at −2.3 to −12.4 m, the mid-field
apron 9 m below that, and the MRO platform 35 m below the threshold, with the
ground falling ~40 m/km eastward into the córrego between them. That fall is
real terrain, not DEM error (TERRAIN.md §2), and it is the reason the base
cannot be seen from the runway at all.

THE HORIZON PROBLEM AN AERIAL HAS HERE
--------------------------------------
The camera-animation skill's rule is to keep a stable anchor in frame or the
eye loses orientation. On a field whose horizon band is 1.6° wide there is
nothing to pin *except* the horizon — and a steep aerial throws even that away:
at 250 m and 500 m range the depression is 27° and the horizon is off the top
of the frame. This shot is deliberately shallow enough to keep it: 16–20° of
depression, less 5.0–7.4° of TILT_UP, holds the flat edge at **v 0.813–0.842**
for all 240 frames. It is a thin strip of sky and it is the only orientation cue
the shot has. The sun stays 177° off the lens axis at frame 1 and 163° at frame
240 — behind the camera throughout, which is the third of Santiago's three
reasons.

WHAT THIS SHOT FOUND IN THE SHARED SCENERY
------------------------------------------
It is the first camera on this field to look OUT at 4–7 km at a shallow angle —
every check frame before it is either ground-level, where haze closes at 2 km,
or steeply down — and it caught a defect that had been in the ground since phase
2. `SDSC_CaneSurround_*` and the terrain tiers are two samplings of the same
Copernicus grid, the cane sheet linear between its 120 m nodes and the terrain
at 30 m. Wherever the coarse chord dipped under the fine surface the TERRAIN
material won, so the far field rendered as a mottle of two farmland shaders in
hard-edged patches up to a kilometre across. Measured over 30 000 points inside
the ring: **the terrain won 39.3% of them, worst case 13.80 m.** Fixed in
`build_scenery.py` at 60 m and +0.45 (2.6%, and the sheet sits 1.25 m clear);
the reasoning and the whole ladder are in README §4b. The terrain tiers still
interleave with each other past 12 km and that one is left standing.

The lesson is the general one: **a new camera angle is a test the scenery has
never taken.** Nothing about this was visible from any station phase 2 checked.

THE POPULATED RAMP
------------------
Phase 3 shipped this clip with three of the nose-in proxies hand-swapped for
real masters, right here in this file, and the owner caught what that left
behind: everything else on the ramp was still a low-poly proxy. Phase 5 took
the whole business out of this script. `fleet_placement.py` owns it now — ten
stands, eight of the eleven masters, the heavy-check states worked out one by
one, and the same self-verifying envelope on every one of them. This clip calls
`F.populate(scn)` and says nothing else about aeroplanes.

**No 777-300ER anywhere on this field**: CNN Brasil puts 777 maintenance at
Guarulhos, and it is the one type with evidence against.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import shot_common as S                                       # noqa: E402
import fleet_placement as F                                   # noqa: E402

TERRAIN = os.path.join(HERE, "sdsc_terrain.blend")
FRAME_END = 240                     # 9.6 s at 25 fps
LENS = 38.0

# The camera line and the aim line. Both straight, both linear in the frame
# number: every control value in this shot is a lerp, which is what "constant
# rate" means in practice.
CAM0 = (-1080.0, 620.0, 230.0)
CAM1 = (60.0, 2260.0, 292.0)
AIM0 = (-180.0, 600.0, S.Z_AEROCLUBE_APRON - 2.0)     # off the Aeroclube
AIM1 = (980.0, 1900.0, S.Z_MRO_PLATFORM + 12.0)       # the MRO hangar line
TILT0, TILT1 = math.radians(5.0), math.radians(7.4)

LANDMARKS = {
    "aeroclube": (-250.0, 450.0, S.Z_AEROCLUBE_APRON + 6.0),
    "rwy_mid": (15.0, 800.0, S.rwy_z(800.0)),
    "midfield": (300.0, 1150.0, S.Z_MIDFIELD_APRON + 8.0),
    "chequer": (300.0, 1255.0, S.Z_MIDFIELD_APRON + 29.0),
    "hangar9": (750.0, 1637.5, S.Z_MRO_PLATFORM + 22.0),
    "mro_bay": (931.0, 1810.0, S.Z_MRO_PLATFORM + 17.5),
    "spine_n": (1027.0, 2039.0, S.Z_MRO_PLATFORM + 12.9),
    "museu": (1320.0, 1725.0, S.Z_MRO_PLATFORM + 11.0),
    "thr02": (0.0, 0.0, S.Z_THR02),
    "thr20": (29.0, 1619.7, S.Z_THR20),
}


def pose(f):
    t = (f - 1) / float(FRAME_END - 1)
    cam = tuple(a + (b - a) * t for a, b in zip(CAM0, CAM1))
    aim = tuple(a + (b - a) * t for a, b in zip(AIM0, AIM1))
    dx, dy = aim[0] - cam[0], aim[1] - cam[1]
    horiz = math.hypot(dx, dy)
    tilt = TILT0 + (TILT1 - TILT0) * t
    return (cam, aim, math.atan2(dx, dy),
            math.atan2(aim[2] - cam[2], horiz) + tilt, horiz)


def rows():
    out = []
    for f in range(1, FRAME_END + 1):
        cam, aim, az, el, horiz = pose(f)
        out.append(dict(f=f, cam=cam, aim=aim, az=az, el=el, lens=LENS,
                        dist=horiz))
    return out


def report(rs):
    print("\n%-5s %9s %9s %7s %8s %8s %8s %8s %8s"
          % ("frame", "cam_x", "cam_y", "cam_z", "aim_m", "az_true", "el_deg",
             "horiz_v", "haze%"))
    for r in rs:
        if r["f"] % 20 and r["f"] not in (1, FRAME_END):
            continue
        t = S.half_tan(r["lens"])
        hv = 0.5 + math.tan(math.radians(-0.10) - r["el"]) * S.ASPECT / (2 * t)
        # the shipped haze model, quoted at the aim's slant range
        d = math.dist(r["cam"], r["aim"])
        z = max(r["cam"][2] + 60.0, 1.0)
        tau = (3.912 / 18000.0) * d * (1100.0 / z) * (1 - math.exp(-z / 1100.0))
        print("%-5d %9.0f %9.0f %7.0f %8.0f %8.1f %8.2f %8.3f %8.1f"
              % (r["f"], r["cam"][0], r["cam"][1], r["cam"][2], r["dist"],
                 math.degrees(r["az"]) % 360.0, math.degrees(r["el"]), hv,
                 100 * (1 - math.exp(-tau))))
    S.flow_report(rs, "SDSC aerial tour")
    hv = []
    for r in rs:
        t = S.half_tan(r["lens"])
        hv.append(0.5 + math.tan(math.radians(-0.10) - r["el"])
                  * S.ASPECT / (2 * t))
    print("flat horizon held at v %.3f..%.3f  (the only anchor this field has)"
          % (min(hv), max(hv)))
    sp = [math.dist(a["cam"], b["cam"]) * S.FPS for a, b in zip(rs, rs[1:])]
    print("camera %.0f m/s over %.0f m of line, %.0f -> %.0f m above the plateau"
          % (sum(sp) / len(sp), math.dist(CAM0, CAM1), CAM0[2], CAM1[2]))
    sun = (S.SUN_AZIM_DEG - math.degrees(rs[0]["az"])) % 360.0
    sun2 = (S.SUN_AZIM_DEG - math.degrees(rs[-1]["az"])) % 360.0
    print("sun %.1f deg off the lens axis at frame 1, %.1f at frame %d "
          "(>90 = behind the camera)"
          % (min(sun, 360 - sun), min(sun2, 360 - sun2), FRAME_END))

    print("\n%-5s %s" % ("frame", " ".join("%13s" % k for k in LANDMARKS)))
    seen = {k: [] for k in LANDMARKS}
    for r in rs:
        cells = []
        for k, p in LANDMARKS.items():
            u, v, _ = S.project(r["cam"], r["az"], r["el"], r["lens"], p)
            if 0 <= u <= 1 and 0 <= v <= 1:
                seen[k].append(r["f"])
            cells.append("%5.2f,%5.2f%s"
                         % (u, v, " " if 0 <= u <= 1 and 0 <= v <= 1 else "*"))
        if r["f"] % 40 == 0 or r["f"] in (1, FRAME_END):
            print("%-5d %s" % (r["f"], " ".join("%13s" % c for c in cells)))
    print("       (u, v; * = outside the frame)")
    print("\nframes in shot, of %d:" % FRAME_END)
    for k, fs in seen.items():
        print("  %-12s %4d frames %s" % (k, len(fs),
                                         ("%d..%d" % (fs[0], fs[-1])) if fs
                                         else "NEVER IN FRAME"))


# ---------------------------------------------------------------------------
# Blender side
# ---------------------------------------------------------------------------
def main():
    import bpy

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(HERE, "sdsc_base_flyover.blend")
    scn = bpy.context.scene

    if os.path.exists(TERRAIN) and "SDSC_Terrain" not in bpy.data.collections:
        with bpy.data.libraries.load(TERRAIN, link=True) as (src, dst):
            dst.collections = [c for c in src.collections
                               if c == "SDSC_Terrain"]
        for c in dst.collections:
            if c is None:
                continue
            ob = bpy.data.objects.new("SDSC_Terrain_Link", None)
            ob.instance_type = "COLLECTION"
            ob.instance_collection = c
            scn.collection.objects.link(ob)
        print("linked terrain")
    else:
        print("!! sdsc_terrain.blend missing - build_scenery.py -- --terrain")

    # ---- the aeroplanes, from the shared module ---------------------------
    # Ten stands, eight types, every heavy-check state reproduced or declared:
    # fleet_placement.py's docstring is the reasoning and this is the whole of
    # the call site. It was a three-entry tuple in this file until phase 5.
    F.populate(scn)

    # ---- the camera --------------------------------------------------------
    cd = bpy.data.cameras.new("CamTour")
    cd.lens = LENS
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = S.SENSOR
    cd.clip_start = 1.0
    cd.clip_end = 250000.0
    cam = bpy.data.objects.new("CamTour", cd)
    scn.collection.objects.link(cam)
    rs = rows()
    report(rs)
    for r in rs:
        cam.location = r["cam"]
        cam.rotation_euler = (math.pi / 2.0 + r["el"], 0.0, -r["az"])
        cam.keyframe_insert("location", frame=r["f"])
        cam.keyframe_insert("rotation_euler", frame=r["f"])
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
    try:
        import bpy  # noqa: F401
    except ImportError:
        report(rows())
    else:
        main()
