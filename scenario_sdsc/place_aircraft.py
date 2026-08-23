#!/usr/bin/env python3
"""Put an aircraft take-off rig on RWY 02 at SDSC and link the São Carlos scenery.

    blender -b "airbus A320neo/A320neo_decolagem.blend" \\
        -P scenario_sdsc/place_aircraft.py -- --out scenario_sdsc/sdsc_takeoff.blend

The Santiago sibling is `../scenario/place_aircraft.py` and the placement half
is the same idea: link the shared scenery, drop an Empty on the threshold
carrying the true track, parent the aircraft pivot to it, touch none of the
aircraft's own animation curves. Everything below is what this field changes.

THREE SDSC CHANGES, and the second one has no Santiago analogue at all
----------------------------------------------------------------------
1.  **The threshold is at z = −2.33 m, not 0.** z = 0 here is the published
    *aerodrome* elevation (807.0 m AMSL); the RWY 02 threshold is 2 640 ft =
    804.67 m, so it sits 2.33 m below the datum. A rig placed at z = 0 puts the
    wheels 2.3 m in the air.

2.  **The runway is not level, so the placement cannot be one transform.**
    It falls 0.62% — 10.06 m over the 1 620 m between the published thresholds
    — downhill toward 20, which is the direction a 02 departure rolls. The
    wheels have to ride that grade. A single parent Empty cannot express it, so
    the grade is baked into the pivot's own z channel:

        dz(f) = rwy_z(min(roll(f), roll_liftoff)) − rwy_z(roll(1))

    frozen at lift-off — after that the aeroplane climbs and the runway is no
    longer under it. The freeze is smoothstepped over `GRADE_FREEZE` frames
    rather than cut, because at 58 m/s the grade is worth −0.36 m/s of sink and
    a hard stop puts a velocity step into the vertical exactly at rotation,
    which is the one moment the eye is locked on. Measured residual after the
    taper: under 4 cm.

3.  **TORA is 1 672 m and this is a ferry flight.** ROLL_AT_FRAME_1 is chosen
    so the main wheels leave at 1 150 m — 522 m of TORA still ahead, 31% —
    which is what an empty A320neo with minimum fuel looks like out of a short,
    hot-and-high field (2 648 ft, and a 30 °C afternoon is ISA+20). The
    everyday choice, and the one type this repository already has a take-off
    rig for; the 787-9 is the striking one and it gets the hangar-9 clip, where
    the aeroplane is the reason the building exists.

What it deliberately does NOT do
--------------------------------
No camera reframe. Santiago's `place_aircraft.py` still carries the
slide-out-along-the-sight-line reframe that produced its uncomfortable v1;
`takeoff_camera.py` replaces the camera action outright and that is the step
that makes the clip. Here the placeholder camera is left where it is and
overwritten downstream.

It also exports `ac_curve_sdsc.json` — the graded aircraft track — so
`takeoff_camera.py` can be tuned in a second without opening a 108 MB scene.
"""
import bpy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import shot_common as S                                       # noqa: E402

FIELD = os.path.join(HERE, "sdsc_field.blend")
TERRAIN = os.path.join(HERE, "sdsc_terrain.blend")

# --- the shot's one free number ---------------------------------------------
# Main-gear lift-off station on the 02 roll. The shipped A320neo action lifts
# off 145.75 m after its frame 1, so ROLL_AT_FRAME_1 follows from this.
LIFTOFF_A = 1150.0
LIFTOFF_FRAME = 69          # first frame with the pivot off the pavement
GRADE_FREEZE = 14           # frames over which the grade offset stops tracking

PIVOT_X0 = 17.71            # AviaoPivo local x at frame 1 (main-gear contact)
PIVOT_Z0 = -3.670           # ... and its local z
LIFTOFF_DX = 145.75         # PIVOT_X0 − local x at LIFTOFF_FRAME
ROLL_AT_FRAME_1 = LIFTOFF_A - LIFTOFF_DX          # 1004.25 m

SRC_END = 140

DROP = ("Pista", "PistaMarcas", "Grama", "Sol", "CloudCard",
        "CamHero", "CamPerfil", "CamCauda", "CamBarriga", "CamNariz",
        "CamFrontal", "CamOrtoFrente", "CamAlvo", "CamAlvoCauda",
        "CamAlvoBarriga", "CamAlvoNariz", "CamAlvoFrontal")


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def fcurves(action):
    if len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    out = []
    for lay in action.layers:
        for st in lay.strips:
            for cb in st.channelbags:
                out.extend(cb.fcurves)
    return out


def fc(action, path, index):
    for c in fcurves(action):
        if c.data_path == path and c.array_index == index:
            return c
    raise KeyError((path, index))


def link_collection(path, name, instance=True):
    with bpy.data.libraries.load(path, link=True) as (src, dst):
        if name not in src.collections:
            raise RuntimeError("%s has no collection %s" % (path, name))
        dst.collections = [name]
    c = dst.collections[0]
    if instance:
        ob = bpy.data.objects.new(name + "_Link", None)
        ob.instance_type = "COLLECTION"
        ob.instance_collection = c
        bpy.context.scene.collection.objects.link(ob)
    return c


def main():
    a = args()
    out = a[a.index("--out") + 1] if "--out" in a else \
        os.path.join(HERE, "sdsc_takeoff.blend")
    scn = bpy.context.scene

    # ---- 1. strip the placeholder scenery ----------------------------------
    for nm in DROP:
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)

    # ---- 2. link the shared scenery ----------------------------------------
    link_collection(FIELD, "SDSC_Field")
    link_collection(FIELD, "SDSC_Light")
    link_collection(FIELD, "SDSC_Anchors")
    if os.path.exists(TERRAIN):
        link_collection(TERRAIN, "SDSC_Terrain")
    else:
        print("!! sdsc_terrain.blend missing - rebuild it with "
              "build_scenery.py -- --terrain")
    with bpy.data.libraries.load(FIELD, link=True) as (src, dst):
        dst.worlds = ["SDSC_World"]
    scn.world = dst.worlds[0]
    for cam in bpy.data.cameras:
        cam.clip_end = 250000.0            # the scene is 240 km wide

    # ---- 3. the placement Empty --------------------------------------------
    # the aircraft's nose is local −X; solve (−cos psi, −sin psi) = track unit
    psi = math.atan2(-S.UY, -S.UX)
    piv = bpy.data.objects["AviaoPivo"]
    scn.frame_set(1)
    lx, ly, lz = piv.location
    tx, ty = S.al_xy(ROLL_AT_FRAME_1, 0.0)
    ox = tx - (lx * math.cos(psi) - ly * math.sin(psi))
    oy = ty - (lx * math.sin(psi) + ly * math.cos(psi))
    oz = S.rwy_z(ROLL_AT_FRAME_1) + S.Z_RUNWAY - lz

    rig = bpy.data.objects.new("SDSC_Placement", None)
    rig.empty_display_type = "ARROWS"
    rig.empty_display_size = 30.0
    rig.location = (ox, oy, oz)
    rig.rotation_euler = (0.0, 0.0, psi)
    scn.collection.objects.link(rig)

    cam = bpy.data.objects["CamDecolagem"]
    for ob in (piv, cam):
        ob.parent = rig
        ob.matrix_parent_inverse.identity()

    # ---- 4. ride the grade -------------------------------------------------
    act = piv.animation_data.action
    cz = fc(act, "location", 2)
    cx = fc(act, "location", 0)
    base = [cz.evaluate(f) for f in range(1, SRC_END + 1)]
    rolls = [ROLL_AT_FRAME_1 + (PIVOT_X0 - cx.evaluate(f))
             for f in range(1, SRC_END + 1)]
    z0 = S.rwy_z(rolls[0])
    grade = []
    for f in range(1, SRC_END + 1):
        w = 1.0 - S._smoothstep((f - LIFTOFF_FRAME + GRADE_FREEZE * 0.5)
                                / float(GRADE_FREEZE))
        # w = 1 while the wheels are down, easing to 0 across lift-off; the
        # offset then HOLDS at whatever it had reached (it is integrated, not
        # re-evaluated), so the climb-out is untouched by the runway grade.
        grade.append(w)
    off, prev_roll = 0.0, rolls[0]
    offs = []
    for f in range(SRC_END):
        off += grade[f] * S.RWY_SLOPE * (rolls[f] - prev_roll)
        prev_roll = rolls[f]
        offs.append(off)
    for f in range(SRC_END):
        cz.keyframe_points.insert(f + 1, base[f] + offs[f], options={'FAST'})
    for kp in cz.keyframe_points:
        kp.interpolation = "LINEAR"
    cz.update()
    exact = S.rwy_z(min(rolls[-1], LIFTOFF_A)) - z0
    print("grade baked: %.3f m of fall over the roll (exact %.3f, delta %+.3f)"
          % (offs[-1], exact, offs[-1] - exact))

    # ---- 5. export the graded track for offline camera tuning --------------
    loc = [[fc(act, "location", i).evaluate(f) for i in range(3)]
           for f in range(1, SRC_END + 1)]
    rot = [[fc(act, "rotation_euler", i).evaluate(f) for i in range(3)]
           for f in range(1, SRC_END + 1)]
    json.dump(dict(loc=loc, rot=rot, roll_at_frame_1=ROLL_AT_FRAME_1,
                   pivot_x0=PIVOT_X0, rig_z=oz),
              open(os.path.join(HERE, "ac_curve_sdsc.json"), "w"))

    # ---- 6. render settings ------------------------------------------------
    scn.render.fps = 25                  # exact 4 cs GIF delays; 24 is not
    scn.render.fps_base = 1.0
    scn.frame_start, scn.frame_end = 1, SRC_END
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

    report(scn, piv, rig)
    # Library paths must end up relative or the file only opens on this
    # machine. save_as_mainfile(relative_remap=True) only re-bases paths that
    # were ALREADY relative, so save once, convert, save again.
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    print("saved", out)


def report(scn, piv, rig):
    print("\n%-6s %9s %9s %9s %9s %9s   %s"
          % ("frame", "roll_m", "lateral", "pivot_z", "rwy_z", "wheel_agl",
             "note"))
    for f in (1, 20, 40, 60, LIFTOFF_FRAME, 80, 100, 120, 140):
        scn.frame_set(f)
        P = piv.matrix_world.translation
        a, l = S.to_al(P.x, P.y)
        agl = P.z - (S.rwy_z(a) + S.Z_RUNWAY)
        print("%-6d %9.1f %9.2f %9.3f %9.3f %9.3f   %s"
              % (f, a, l, P.z, S.rwy_z(a), agl,
                 "on the pavement" if abs(agl) < 0.03 else "airborne"))
    scn.frame_set(140)
    a, _ = S.to_al(*piv.matrix_world.translation[:2])
    print("\nlift-off at %.0f m of a %.0f m TORA - %.0f m (%.0f%%) remaining"
          % (LIFTOFF_A, S.TORA_02, S.TORA_02 - LIFTOFF_A,
             100 * (S.TORA_02 - LIFTOFF_A) / S.TORA_02))
    print("frame 140 station %.0f m, %.0f m past the north pavement end at 240"
          % (a, 0.0))
    print("MRO abeam window %.0f-%.0f m on the RIGHT, %.0f-%.0f m out"
          % (S.MRO_BUILDINGS_A[0], S.MRO_BUILDINGS_A[1],
             -S.MRO_BUILDINGS_L[0], -S.MRO_BUILDINGS_L[1]))


if __name__ == "__main__":
    main()
