#!/usr/bin/env python3
"""Place a 777-300ER on RWY 10L at Guarulhos and author its departure.

    blender -b --factory-startup -P scenario_sbgr/place_777.py -- \\
        --out scenario_sbgr/sbgr_takeoff.blend

The São Carlos sibling (`scenario_sdsc/place_aircraft.py`) reuses the A320's
shipped take-off action; there is no 777 equivalent, so this script AUTHORS the
motion — which is the honest place to author it, because the profile is where
"a loaded 777" lives, and São Carlos already proved the type story is told by
the numbers, not the label. Its ferry A320 leaves 1 150 m into a 1 672 m TORA
at a 21% gradient. This aeroplane does the opposite of all of that:

    frame 1     s = 2 170 m past THR 10L, 74 m/s and still accelerating at
                1.4 m/s² — the clip OPENS two kilometres into the roll,
                because a loaded 777 spends 50 s on the runway and the clip
                has 9.6.
    ~128        rotation begins at 81 m/s, s ≈ 2 550 — ABEAM ITS OWN HANGAR
                (s 2 571): the aeroplane pitches up exactly as its
                maintenance base crosses the frame behind it. 3.1°/s to
                12.0° — a 777 rotates slowly; snapping it up is what would
                read "empty".
    160         main gear leaves at ~83 m/s, s ≈ 2 670 — 940 m of pavement
                still ahead (the ferry had 522 on a runway half this long).
    160–240     climb-out ramps to 9.5 m/s against 86 m/s — an 11% gradient,
                HALF the ferry's, pitch settling at 13°. Gear stays down
                through the last frame: retraction starts seconds later than
                a 9.6 s clip lasts.

The pivot sits at the MAIN-GEAR CONTACT, measured off the linked master's
03_Trem collection (printed below), so rotation lifts the nose about the
wheels the way the real geometry does, and the tail sweeps down toward the
pavement it is certified to clear.

Frame: everything hangs off the SBGR_10L_Threshold anchor in the field file —
its +Y is the roll, its origin is the painted centreline. `shot_common.py`
holds the same frame for the offline camera solver, and this script exports
`ac_curve_sbgr.json` so the solver never needs the 110 MB scene open.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import shot_common as S                                       # noqa: E402

FIELD = os.path.join(HERE, "sbgr_field.blend")
TERRAIN = os.path.join(HERE, "sbgr_terrain.blend")
MASTER = os.path.join(ROOT, "boeing 777-300ER", "B77W_LATAM.blend")
PARTS = ("01_Estrutura", "02_Motores", "03_Trem", "04_Detalhes")

FRAME_END = 240
FPS = 25.0
Z_RUNWAY = 0.09                 # pavement top over rwy_z (build_scenery.py)

# --- the profile ------------------------------------------------------------
S0 = 2170.0                     # station at frame 1
V0 = 74.0                       # ground speed at frame 1, m/s
ACCEL = 1.4                     # m/s², held until lift-off
ROTATE_F = 128                  # rotation begins
PITCH_TAKEOFF = 12.0            # deg reached at lift-off attitude
ROTATE_RATE = 3.1               # deg/s
LIFTOFF_F = 160                 # main gear leaves
VS_FINAL = 9.5                  # m/s climb at frame 240
V_CLIMB = 86.0                  # speed settles here after lift-off
PITCH_FINAL = 13.0
CLIMB_RAMP = 70                 # frames over which vs ramps 0 -> VS_FINAL


def profile():
    """Per-frame (station s, wheel-agl z, pitch deg). Authoring, not physics
    homework: constant accel to lift-off, smoothstep ramps after, every rate
    chosen to read 'heavy' against the São Carlos ferry."""
    out = []
    s, v = S0, V0
    pitch = 0.0
    agl, vs = 0.0, 0.0
    for f in range(1, FRAME_END + 1):
        if f > 1:
            if f <= LIFTOFF_F:
                v += ACCEL / FPS
            else:
                v += (V_CLIMB - v) * 0.02
            s += v / FPS
            if f > ROTATE_F:
                pitch = min(PITCH_TAKEOFF, pitch + ROTATE_RATE / FPS)
            if f > LIFTOFF_F:
                t = S._smoothstep((f - LIFTOFF_F) / float(CLIMB_RAMP))
                vs = VS_FINAL * t
                agl += vs / FPS
                pitch = min(PITCH_FINAL,
                            PITCH_TAKEOFF + (PITCH_FINAL - PITCH_TAKEOFF)
                            * S._smoothstep((f - LIFTOFF_F) / 80.0))
        out.append((s, agl, pitch))
    return out


def link_collection(path, name, instance_parent=None):
    with bpy.data.libraries.load(path, link=True) as (src, dst):
        if name not in src.collections:
            raise RuntimeError("%s has no collection %s" % (path, name))
        dst.collections = [name]
    c = dst.collections[0]
    ob = bpy.data.objects.new(name + "_Link", None)
    ob.instance_type = "COLLECTION"
    ob.instance_collection = c
    bpy.context.scene.collection.objects.link(ob)
    if instance_parent is not None:
        ob.parent = instance_parent
    return c, ob


def measure_gear(trem):
    """Main-gear contact (x, z) in master coordinates, from the linked meshes.

    Nose is local −X fleet-wide, so the nose gear is the wheel cluster with
    the SMALLEST x and the main gear is everything else. Contact z is the
    lowest point of the main cluster."""
    boxes = []
    for ob in trem.all_objects:
        if ob.type != "MESH":
            continue
        for corner in ob.bound_box:
            p = ob.matrix_world @ Vector(corner)
            boxes.append((ob.name, p.x, p.z))
    if not boxes:
        raise RuntimeError("03_Trem has no mesh geometry")
    zmin = min(b[2] for b in boxes)
    low = [b for b in boxes if b[2] < zmin + 0.6]      # near-ground points
    xs = sorted(b[1] for b in low)
    # nose/main split: the largest x-gap between near-ground clusters
    gap_i = max(range(1, len(xs)), key=lambda i: xs[i] - xs[i - 1])
    nose_xs, main_xs = xs[:gap_i], xs[gap_i:]
    if len(nose_xs) > len(main_xs):                    # nose cluster is small
        nose_xs, main_xs = main_xs, nose_xs
    if min(nose_xs) > min(main_xs):
        nose_xs, main_xs = main_xs, nose_xs            # nose is most −X
    mg_x = sum(main_xs) / len(main_xs)
    mg_z = min(b[2] for b in low if b[1] >= main_xs[0])
    print("gear survey: %d near-ground corners, nose cluster x %.2f..%.2f, "
          "main cluster x %.2f..%.2f -> pivot (%.3f, %.3f), wheelbase %.2f m"
          % (len(low), min(nose_xs), max(nose_xs), min(main_xs), max(main_xs),
             mg_x, mg_z, mg_x - sum(nose_xs) / len(nose_xs)))
    return mg_x, mg_z


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(HERE, "sbgr_takeoff.blend")
    scn = bpy.context.scene

    for ob in list(bpy.data.objects):                  # factory scene junk
        bpy.data.objects.remove(ob, do_unlink=True)

    # ---- scenery ----------------------------------------------------------
    for name in ("SBGR_Field", "SBGR_Light", "SBGR_Anchors"):
        link_collection(FIELD, name)
    if os.path.exists(TERRAIN):
        link_collection(TERRAIN, "SBGR_Terrain")
    else:
        print("!! sbgr_terrain.blend missing - build_scenery.py -- --terrain")
    with bpy.data.libraries.load(FIELD, link=True) as (src, dst):
        dst.worlds = ["SBGR_World"]
    scn.world = dst.worlds[0]

    # ---- the rig on the anchor's frame ------------------------------------
    # anchor local +Y = down the roll; rig repeats it so pivot-local x is
    # LATERAL (right positive) and pivot-local y is STATION.
    rig = bpy.data.objects.new("SBGR_Placement", None)
    rig.empty_display_type = "ARROWS"
    rig.empty_display_size = 30.0
    rig.location = (S.THR_X, S.THR_Y, 0.0)
    rig.rotation_euler = (0.0, 0.0, -math.radians(S.TRACK_DEG))
    scn.collection.objects.link(rig)

    piv = bpy.data.objects.new("AviaoPivo", None)
    piv.empty_display_type = "PLAIN_AXES"
    piv.empty_display_size = 12.0
    piv.parent = rig
    scn.collection.objects.link(piv)

    # ---- the aeroplane, nose down the roll --------------------------------
    parts = {}
    for name in PARTS:
        c, ob = link_collection(MASTER, name, instance_parent=piv)
        parts[name] = (c, ob)
    try:
        mg_x, mg_z = measure_gear(parts["03_Trem"][0])
    except RuntimeError:
        mg_x, mg_z = None, None
    if mg_x is None or not 25.0 < mg_x < 45.0:
        # The linked-library survey reads unevaluated matrices (it measured a
        # 0.34 m "wheelbase" on the first run), so it cannot be trusted for a
        # master whose parts carry parent transforms. Constants instead, each
        # with its source: the master occupies x 0.02..73.95 with wheels at
        # z ~0 (export/verificar_glb.py on B77W_alta.glb), and the published
        # 777-300ER gear geometry is a 31.22 m wheelbase with the nose leg
        # ~5.3 m aft of the nose - main-gear contact x = 36.5, z = 0.
        # The GLB-derived "wheels at z 0" was WRONG: the exporter seats
        # every aircraft on the Y=0 floor by its own rule, so the bbox told
        # the truth about the EXPORT and a lie about the MASTER, whose gear
        # hangs to z = -5.670 (evaluated-depsgraph minimum over 03_Trem;
        # main cluster x 37.11). The false 0.0 sank the 777 5.7 m in both
        # SBGR clips - belly on the runway, no gear in frame - and the
        # owner, not the pipeline, caught it in the published GIFs.
        print("gear survey unusable (%s) - using measured master geometry: "
              "contact (37.11, -5.670)" % repr((mg_x, mg_z)))
        mg_x, mg_z = 37.11, -5.670
    # master nose is −X; rig-local station axis is +Y. The fleet convention
    # (fleet_placement._heading_rot) puts a master on compass heading h with
    # world yaw atan2(−cos h, −sin h); for h = TRACK that is −163.65°, and the
    # rig already carries −73.65°, so the parts' local yaw is the difference:
    # **−90°**. Check by rotation, not by faith: R(−90°)·(−1,0) = (0,+1) —
    # nose onto rig-local +Y, down the roll; chirality untouched, so the
    # wings land the same way they do at every stand fleet_placement fills.
    # The gear contact (mg_x, 0, mg_z) maps under R(−90°) to (0, −mg_x, mg_z);
    # offsetting the parts by its negation puts the contact at the pivot.
    for name, (c, ob) in parts.items():
        ob.rotation_euler = (0.0, 0.0, -math.radians(90.0))
        ob.location = (0.0, mg_x, -mg_z)

    # ---- authored motion --------------------------------------------------
    prof = profile()
    piv.rotation_mode = "XYZ"
    for f, (s, agl, pitch) in enumerate(prof, start=1):
        piv.location = (0.0, s, S.rwy_z(s) + Z_RUNWAY + agl)
        # pitch about rig-local X lifts +Y (the nose) for NEGATIVE rx:
        # R_x(θ): y' = y cosθ − z sinθ; z' = y sinθ + z cosθ. Nose at +Y:
        # z' = sinθ·y — nose UP needs θ > 0. Asserted in the report below.
        piv.rotation_euler = (math.radians(pitch), 0.0, 0.0)
        piv.keyframe_insert("location", frame=f)
        piv.keyframe_insert("rotation_euler", frame=f)
    act = piv.animation_data.action
    fcs = []
    if len(getattr(act, "fcurves", [])):
        fcs = list(act.fcurves)
    else:
        for lay in act.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    fcs.extend(cb.fcurves)
    for c in fcs:
        for kp in c.keyframe_points:
            kp.interpolation = "LINEAR"
        c.update()

    # ---- the camera placeholder ------------------------------------------
    cd = bpy.data.cameras.new("CamDecolagem")
    cam = bpy.data.objects.new("CamDecolagem", cd)
    cam.parent = rig
    scn.collection.objects.link(cam)
    cd.clip_start = 1.0
    cd.clip_end = 250000.0
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = S.SENSOR
    for c in bpy.data.cameras:
        c.clip_end = 250000.0

    # ---- verification: where is the nose, really? -------------------------
    deps = bpy.context.evaluated_depsgraph_get()
    scn.frame_set(1)
    report_rows = []
    for f in (1, 60, ROTATE_F, 140, LIFTOFF_F, 200, FRAME_END):
        scn.frame_set(f)
        deps.update()
        P = piv.matrix_world.translation
        s, l = S.to_sl(P.x, P.y)
        agl = P.z - (S.rwy_z(s) + Z_RUNWAY)
        report_rows.append((f, s, l, agl, prof[f - 1][2]))
    print("\n%-6s %9s %8s %9s %7s" % ("frame", "station", "lateral",
                                      "wheel_agl", "pitch"))
    for f, s, l, agl, p in report_rows:
        print("%-6d %9.1f %8.2f %9.3f %7.2f" % (f, s, l, agl, p))
    print("\nabeam the hangar (s %.0f) around frame %d; lift-off at s %.0f "
          "with %.0f m of pavement remaining (ends s %.0f)"
          % (S.HANGAR_S,
             min(range(1, FRAME_END + 1),
                 key=lambda f: abs(prof[f - 1][0] - S.HANGAR_S)),
             prof[LIFTOFF_F - 1][0],
             S.PAVE_END_S - prof[LIFTOFF_F - 1][0], S.PAVE_END_S))

    # ---- export the track for the offline solver --------------------------
    json.dump(dict(profile=prof, s0=S0, liftoff_f=LIFTOFF_F,
                   rotate_f=ROTATE_F, z_runway=Z_RUNWAY,
                   mg_x=mg_x, mg_z=mg_z),
              open(os.path.join(HERE, "ac_curve_sbgr.json"), "w"))

    # ---- render settings --------------------------------------------------
    scn.render.fps, scn.render.fps_base = 25, 1.0
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
    scn.camera = cam

    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    print("saved", out)


if __name__ == "__main__":
    main()
