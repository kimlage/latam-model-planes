#!/usr/bin/env python3
"""Clip 1 — the RWY 02 departure: a formation chase that cranes into the reveal.

    blender -b scenario_sdsc/sdsc_takeoff.blend \\
        -P scenario_sdsc/takeoff_camera.py -- --out scenario_sdsc/sdsc_takeoff_v1.blend

    python3 scenario_sdsc/takeoff_camera.py        # the same shot, solved
                                                   # offline in ~1 s, no Blender

WHAT THIS FIELD GIVES A CAMERA THAT SANTIAGO DOES NOT
=====================================================
Santiago's shot is held together by the cordillera: a crest line pinned at a
constant fraction of frame height is the eye's anchor, and everything else is
allowed to move against it. **There is nothing to pin here.** The whole 360°
terrain horizon spans −0.35° to +1.33° (`terrain/horizon_fine_0p1deg.csv`), and
across the NNE→ENE sector this shot looks through it averages **−0.10°** and
never leaves ±0.31°. It is a field on a plate.

So the anchor is not a shape, it is a *level*: the horizon here is a ruler-
straight line, and pinning it is a stronger constraint than pinning a mountain,
because any tilt or roll error shows against a straight edge immediately. The
tilt is driven off that line at all 240 frames and the aeroplane is allowed to
float against it, exactly as Santiago drives tilt off the Andes.

And the field offers a second thing Santiago has no version of — **a reveal
that is a fact about the terrain, not a camera move.** The MRO platform is
35 m below the runway and the runway is a crest, so from a camera 15 m over the
roll the sight line to the MRO apron clears the ground by **−5.5 m**: it does
not clear it. The base is *behind the hill* and none of its apron, none of its
nose-in row and none of hangar 9's doorway can be seen — only the tops of the
tallest roofs. The clearance goes positive at **frame 78**, nine frames after
the wheels leave, and reaches **+10.9 m** by the last frame. Measured per frame
with `shot_common.sight_line()` against the same graded surface the scenery was
built on, and printed below as `mro_clr`. Phase 2's negative check
`checks/ground_sp318_from_west.png` is the same geometry seen from outside, and
this is the one thing in the clip that no camera decision produced.

**The base cannot be separated from the aeroplane at any usable focal length.**
It is ~1 040 m east of the centreline; a camera far enough west to have the sun
behind it sees the climbing jet and the hangar line at converging bearings, and
pushing the camera further west converges them faster. At the close the hangar
line spans u 0.32…0.76 — 44% of the frame — and the aeroplane sits at u 0.37
over its southern third. So the composition does not try to separate them side
by side: the aeroplane flies in FRONT of its own base, 24% of the frame wide and
bright against a 471 m dark line, and the two are separated in HEIGHT instead
(aeroplane v 0.46, hangar line v 0.54, flat horizon v 0.76) because the
aeroplane is near and below the camera while the base is far and shallow.

THE SHAPE OF THE MOVE
=====================
One orbit flown in the aeroplane's own coordinates from frame 1 to frame 240 —
no dolly, no hand-over. Santiago rebuilt its take-off five times and what
finally worked was exactly this: the residual stiffness lived in the *seam*
between two coordinate frames, and a camera that flies formation from the first
frame has no seam to read.

    1–70    the roll. Camera on the PORT quarter at psi 122°, 112 m out,
            15.2 m above the wheels, 95 m west of the centreline, 50 mm — the
            aeroplane is 40% of the frame wide, in three-quarter rear view.
            Sun 274.46°, 154° off the lens axis, so the whole port side is lit
            and so is the base when it comes. The mid-field cluster (1 146 m
            along, 314 m right, with the chequerboard tower and the 30 m
            antenna mast) tracks across behind the aeroplane; the MRO is
            behind the crest, and that is correct.
    69      the main wheels leave, 1 150 m into a 1 672 m TORA — 522 m, 31% of
            the declared distance, still ahead of it.
    70–240  the crane. psi walks 122° → 111° (aft quarter toward the beam),
            d opens 112 → 176 m, eps 7.8° → 9.1° so the camera ends 28 m above
            the jet on top of the jet's own climb, and the lens shortens
            50 → 42 mm. The aeroplane RISES through the frame, v 0.35 → 0.46,
            because the camera gains height more slowly than the climb-out
            does; the base clears the crest at frame 78 and fills the middle
            of the frame for the close.

WHY THE CAMERA IS 97 m WEST AND NOT 40
--------------------------------------
Two independent reasons, both measured:

* **The RWY 20 PAPI stands at lateral +20…+68 m west, along ~1 320 m**, which
  is exactly where a tight chase would fly at exactly the frame it would be at
  eye height. `SDSC_PAPI` in the field file; the camera stays outside it by
  >45 m at its closest.
* **Screen flow scales as V/h.** A camera abeam a 47 m/s roll at 7 m needs the
  bottom of its frame to look 32 m away, which is 2.3 frame-widths per second —
  the "objects flash past" defect, and no pan change touches it because it is
  parallax. The fix is height and view angle, not the pan: at 15 m up looking
  58° off the velocity vector the same band measures 0.5 w/s. Santiago solved
  the same problem the opposite way (nearly head-on, so the flow is radial),
  which is not available here because the payoff is 78° off the nose.

REJECTED, and why
-----------------
* **A low broadside at 7 m.** The classic profile-of-the-rotation shot. 1.36
  w/s in the central band at 50 mm — disorienting, and it is parallax so it
  cannot be panned away.
* **A camera east of the centreline**, on the same side as the base. The sun is
  at azimuth 274.46°; a camera looking west has it 3° off the lens axis. This
  is the one framing the light forbids outright.
* **A head-on approach** like Santiago's v5. Cheap in flow, and it points the
  camera at the empty south half of the field with the base squarely behind the
  lens for the whole clip.
* **Ending high enough to look down INTO the base.** From 1.2 km the depression
  to the apron and to the hangar roofs differ by 1°, at any altitude a 240-frame
  climb can reach. Opening the apron out needs to be close, and that is the
  aerial tour's job (`base_flyover.py`), not this one's.

Solved offline (this file, no Blender): pan max 2.57°/s, 0 aim reversals;
aeroplane 40.4% → 24.4% of frame width, edge margin 24.5%; horizon held at
v 0.620 → 0.758; camera 95 → 162 m west, never closer than 130 m to the RWY 20
PAPI; MRO crest clearance −5.5 m → +10.9 m, breaking at frame 78.

Measured IN THE SCENE by `../scenario/camera_metrics.py`, which is the number
that counts because it ray-casts instead of inferring: **central-band screen
flow median 0.050, p90 0.069, max 0.073 w/s — 0 of 239 frames above 0.5, 0
above 1.0.** Whole frame 0.076 median. Nearest scenery in frame 67 m and it is
`SDSC_AerodromeGround`, i.e. grass — no tree, no mast, nothing with an edge.
Worst foreground parallax 47°/s against the 582°/s that was Santiago's tree-line
disaster. The body max/min ratio is 8.7, which looks like a violation of the
"under 5:1" rule and is not one: the range is 0.008 → 0.073 w/s, a monotonic
ramp from a camera locked to the aeroplane during the roll to one craning at the
close. A ratio between two numbers that are both an order of magnitude below the
comfort threshold is not a hitch.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import shot_common as S                                       # noqa: E402
import fleet_placement as F                                   # noqa: E402

FRAME_END = 240             # 9.6 s at 25 fps
SRC_END = 140               # where the shipped A320neo action stops
AC_LENGTH = 37.57           # A320neo overall length, the size yardstick
AC_SPAN = 35.80

# The horizon this shot pins. Mean of terrain/horizon_fine_0p1deg.csv over
# azimuths 15-110 deg, which is the sector the lens looks through.
HORIZON_ELEV_DEG = -0.10

# --- the orbit, in the aeroplane's own frame --------------------------------
# psi: relative bearing of the CAMERA from the aeroplane, 0 = dead ahead,
#      measured POSITIVE TO PORT (west/left), so 90 = port beam, 180 = astern.
# d:   slant range.    eps: elevation of the camera above the aeroplane.
# The last knot is past FRAME_END on purpose: PCHIP eases to a stop at its
# final knot and a camera that halts on the last frame reads as a lurch.
ORBIT = [(1, 112.0, 122.0, 7.8), (50, 116.0, 121.0, 7.9),
         (85, 124.0, 119.5, 8.1), (120, 136.0, 117.5, 8.4),
         (160, 150.0, 115.5, 8.7), (200, 163.0, 113.5, 8.9),
         (240, 176.0, 111.5, 9.1), (275, 186.0, 110.0, 9.2)]
ORBIT_D = [(p[0], p[1]) for p in ORBIT]
ORBIT_PSI = [(p[0], p[2]) for p in ORBIT]
ORBIT_EPS = [(p[0], p[3]) for p in ORBIT]

# Formation flight is not a rail. Two slow sinusoids on the camera position,
# amplitude about a metre, periods well over a second and mutually prime, so
# they never beat into a visible cycle inside 9.6 s.
SWAY_LAT = (1.15, 7.3, 0.9)     # amplitude m, period s, phase rad
SWAY_H = (0.55, 5.1, 2.1)

# Long through the roll, shortening into the crane. 50 mm holds the aeroplane
# at 42% of frame width at 124 m; the pan is near zero there, so the long end's
# gain costs nothing.
LENS = [(1, 50.0), (70, 50.0), (110, 48.0), (160, 45.5), (200, 43.5),
        (240, 42.0), (275, 41.0)]

# Where the aeroplane sits in frame. It drifts left through the crane so the
# hangar line opens into the right half for the close.
SCREEN_U = [(1, 0.50), (70, 0.49), (120, 0.45), (180, 0.40), (240, 0.36),
            (275, 0.34)]

# The anchor. Tilt is NOT driven off the aeroplane - the horizon is held and
# the aeroplane floats against it.
HORIZON_V = [(1, 0.62), (70, 0.63), (120, 0.67), (180, 0.72), (240, 0.76),
             (275, 0.78)]

AIM_SMOOTH = 9.0            # frames of Gaussian smoothing on the solved angles
FINAL_SMOOTH = 8.0
RATE_SMOOTH = 6.0


# ---------------------------------------------------------------------------
# the aeroplane
# ---------------------------------------------------------------------------
def extend_aircraft(loc, rot):
    """Continue the climb past frame 140, as a FERRY departure.

    Santiago's A320 leaves frame 140 at 64.7 m/s with 8.85 m/s of climb and
    ramps to 74.5 / 11.2 - a normal revenue initial climb, ~15% gradient. This
    one is empty: no payload, minimum fuel, out of a 1 672 m runway because the
    aeroplane has just come out of heavy maintenance. It gets 16.0 m/s of climb
    against 76 m/s, a 21% gradient, and holds 15.5 deg of pitch. That is what
    makes it read as light, and it is the whole reason the type choice matters
    on this runway.
    """
    x0, y0, z0 = loc[-1]
    vx = (loc[-1][0] - loc[-2][0]) * S.FPS
    vz = (loc[-1][2] - loc[-2][2]) * S.FPS
    p0 = rot[-1][1]
    speed0, speed1 = abs(vx), 76.0
    vs0, vs1 = vz, 16.0
    p1 = math.radians(15.5)
    n = FRAME_END - SRC_END
    x, z = x0, z0
    for i in range(1, n + 1):
        t = S._smoothstep(i / float(n))
        sp = speed0 + (speed1 - speed0) * t
        vs = vs0 + (vs1 - vs0) * t
        x -= sp / S.FPS
        z += vs / S.FPS
        loc.append((x, y0, z))
        rot.append((rot[-1][0], p0 + (p1 - p0) * t, rot[-1][2]))
    return loc, rot


def aircraft_track():
    """(along, z) of the main-gear contact per frame, in scene coordinates."""
    d = json.load(open(os.path.join(HERE, "ac_curve_sdsc.json")))
    loc, rot = extend_aircraft([tuple(p) for p in d["loc"]],
                               [tuple(p) for p in d["rot"]])
    a = [d["roll_at_frame_1"] + (d["pivot_x0"] - p[0]) for p in loc]
    z = [d["rig_z"] + p[2] for p in loc]
    pitch = [r[1] for r in rot]
    return a, z, pitch


# ---------------------------------------------------------------------------
# the camera
# ---------------------------------------------------------------------------
def camera_path(ac_a, ac_z, nframes=FRAME_END):
    """(along, lateral, z) per frame. lateral > 0 is WEST."""
    out = []
    for f in range(1, nframes + 1):
        d = S.piecewise(f, ORBIT_D)
        psi = math.radians(S.piecewise(f, ORBIT_PSI))
        eps = math.radians(S.piecewise(f, ORBIT_EPS))
        horiz = d * math.cos(eps)
        t = f / S.FPS
        out.append((ac_a[f - 1] + horiz * math.cos(psi),
                    horiz * math.sin(psi)
                    + SWAY_LAT[0] * math.sin(2 * math.pi * t / SWAY_LAT[1]
                                             + SWAY_LAT[2]),
                    ac_z[f - 1] + d * math.sin(eps)
                    + SWAY_H[0] * math.sin(2 * math.pi * t / SWAY_H[1]
                                           + SWAY_H[2])))
    return out


def solve_shot(nframes=FRAME_END):
    ac_a, ac_z, pitch = aircraft_track()
    cam = camera_path(ac_a, ac_z, nframes)

    raw_b, raw_e, dist = [], [], []
    for f in range(nframes):
        ca, cl, cz = cam[f]
        # aim at the visual centre: the pivot is the main-gear contact, the
        # body centre is ~2.9 m above it and ~1.5 m forward along the track
        da, dl = ac_a[f] + 1.5 - ca, 0.0 - cl
        dz = ac_z[f] + 2.9 - cz
        # bearing measured in the roll frame, positive to the RIGHT (east)
        raw_b.append(math.atan2(-dl, da))
        raw_e.append(math.atan2(dz, math.hypot(da, dl)))
        dist.append(math.sqrt(da * da + dl * dl + dz * dz))

    raw_b = S.unwrap(raw_b)
    sm_b = S.gaussian_smooth(raw_b, AIM_SMOOTH)

    rows = []
    for f in range(nframes):
        fr = f + 1
        lens = S.piecewise(fr, LENS)
        t = S.half_tan(lens)
        u = S.piecewise(fr, SCREEN_U)
        hv = S.piecewise(fr, HORIZON_V)
        az = sm_b[f] - math.atan((u - 0.5) * 2.0 * t)
        el = (math.radians(HORIZON_ELEV_DEG)
              - math.atan((hv - 0.5) * 2.0 * t / S.ASPECT))
        rows.append(dict(f=fr, a=cam[f][0], lat=cam[f][1], z=cam[f][2],
                         az=az, el=el, lens=lens, dist=dist[f],
                         ac_a=ac_a[f], ac_z=ac_z[f], pitch=pitch[f]))

    # one light pass so the solved angle/lens triple cannot chatter, then the
    # RATE is smoothed and the azimuth re-integrated from it: smoothing the
    # angle directly leaves ~0.1 deg ripples that read as extra direction
    # changes in the pan.
    for key in ("az", "el", "lens"):
        for r, x in zip(rows, S.gaussian_smooth([r[key] for r in rows],
                                                FINAL_SMOOTH)):
            r[key] = x
    az = [r["az"] for r in rows]
    dz = S.gaussian_smooth([b - a for a, b in zip(az, az[1:])], RATE_SMOOTH)
    acc = [az[0]]
    for step in dz:
        acc.append(acc[-1] + step)
    for r, x in zip(rows, acc):
        r["az"] = x

    # recover where things ACTUALLY land - u/v above were requests
    for f, r in enumerate(rows):
        t = S.half_tan(r["lens"])
        r["u"] = 0.5 + math.tan(raw_b[f] - r["az"]) / (2 * t)
        r["v"] = 0.5 + math.tan(raw_e[f] - r["el"]) * S.ASPECT / (2 * t)
        r["horizon_v"] = (0.5 + math.tan(math.radians(HORIZON_ELEV_DEG)
                                         - r["el"]) * S.ASPECT / (2 * t))
        # apparent width: span dominates from astern, length from the beam
        r["cam"] = S.rwy_pt(r["a"], r["lat"], 0.0)[:2] + (r["z"],)
        r["size"] = (2 * math.atan(0.5 * _apparent_width(r, f) / r["dist"])
                     / S.hfov(r["lens"]))
    return rows


def _apparent_width(row, f):
    """Silhouette width of the aeroplane from this bearing, metres.

    Seen from astern the wingspan is what fills the frame; from the beam it is
    the fuselage length. The blend is the honest middle of the two, and it is
    what the "% of frame width" column is computed from.
    """
    psi = math.radians(S.piecewise(row["f"], ORBIT_PSI))
    return max(AC_LENGTH * abs(math.sin(psi)), AC_SPAN * abs(math.cos(psi)),
               0.55 * (AC_LENGTH * abs(math.sin(psi))
                       + AC_SPAN * abs(math.cos(psi))))


def roll_frame(p_scene):
    """Scene xyz -> (along, east, z): the frame this module's azimuths live in.

    `S.project` wants a compass-like pair (x right, y forward). Here "forward"
    is the 02 roll and "right" is EAST, which is minus the lateral convention
    `shot_common` uses everywhere else. Doing the flip in one named place is
    the whole defence against building the base on the wrong side.
    """
    a, l = S.to_al(p_scene[0], p_scene[1])
    return (-l, a, p_scene[2])


# ---------------------------------------------------------------------------
# the numbers the shot is judged on
# ---------------------------------------------------------------------------
LANDMARKS = {
    "mro_spine_s": (938.0, 1580.0, S.Z_MRO_PLATFORM + 12.9),
    "mro_spine_n": (1027.0, 2039.0, S.Z_MRO_PLATFORM + 12.9),
    "mro_bay": (931.0, 1810.0, S.Z_MRO_PLATFORM + 17.5),
    "hangar9": (750.0, 1685.0, S.Z_MRO_PLATFORM + 22.0),
    "mro_apron": (900.0, 1800.0, S.Z_MRO_PLATFORM),
    "midfield": (300.0, 1150.0, S.Z_MIDFIELD_APRON + 10.0),
    "chequer": (300.0, 1255.0, S.Z_MIDFIELD_APRON + 29.0),
}


def report(rows):
    print("\n%-5s %8s %8s %8s %7s %8s %7s %6s %6s %6s %7s %8s"
          % ("frame", "ac_roll", "cam_a", "cam_lat", "cam_z", "az_true",
             "lens", "ac_u", "ac_v", "size%", "horiz_v", "mro_clr"))
    for r in rows:
        clr, _ = S.sight_line(r["cam"], LANDMARKS["mro_apron"], n=200)
        r["mro_clr"] = clr
        if r["f"] % 20 and r["f"] not in (1, 69, FRAME_END):
            continue
        print("%-5d %8.0f %8.0f %8.1f %7.1f %8.1f %7.1f %6.2f %6.2f %6.1f "
              "%7.2f %8.2f"
              % (r["f"], r["ac_a"], r["a"], r["lat"], r["z"],
                 (S.TRACK_02_DEG + math.degrees(r["az"])) % 360.0, r["lens"],
                 r["u"], r["v"], 100 * r["size"], r["horizon_v"], clr))

    S.flow_report(rows, "SDSC departure, RWY 02")

    umin = min(r["u"] - r["size"] / 2 for r in rows)
    umax = max(r["u"] + r["size"] / 2 for r in rows)
    vs = [r["v"] for r in rows]
    print("aeroplane in frame: width %.1f%% -> %.1f%%, u %.3f..%.3f, "
          "v %.3f..%.3f, edge margin %.1f%%"
          % (100 * rows[0]["size"], 100 * rows[-1]["size"], umin, umax,
             min(vs), max(vs), 100 * min(umin, 1 - umax)))
    hv = [r["horizon_v"] for r in rows]
    print("horizon held at v %.3f..%.3f (elev %.2f deg, band -0.35..+1.33)"
          % (min(hv), max(hv), HORIZON_ELEV_DEG))
    lat = [r["lat"] for r in rows]
    print("camera stays %.0f..%.0f m WEST of the centreline "
          "(RWY 20 PAPI is at +20..+68, along ~1320)" % (min(lat), max(lat)))
    papi = [r for r in rows if 1280 < r["a"] < 1360]
    if papi:
        print("  closest approach to the PAPI station: lateral %.0f m at "
              "frame %d" % (min(p["lat"] for p in papi),
                            min(papi, key=lambda p: p["lat"])["f"]))

    brk = next((r["f"] for r in rows if r["mro_clr"] > 0), None)
    print("MRO apron clears the runway crest at frame %s "
          "(clearance %.1f m -> %.1f m)"
          % (brk, rows[0]["mro_clr"], rows[-1]["mro_clr"]))

    print("\n%-5s %s" % ("frame", " ".join("%13s" % k for k in LANDMARKS)))
    for r in rows:
        if r["f"] % 40 and r["f"] not in (1, FRAME_END):
            continue
        cells = []
        for k, p in LANDMARKS.items():
            u, v, _ = S.project(roll_frame(r["cam"]), r["az"], r["el"],
                                r["lens"], roll_frame(p))
            cells.append("%5.2f,%5.2f%s" % (u, v,
                                            " " if 0 <= u <= 1 and 0 <= v <= 1
                                            else "*"))
        print("%-5d %s" % (r["f"], " ".join("%13s" % c for c in cells)))
    print("       (u, v of each landmark; * = outside the frame)")


# ---------------------------------------------------------------------------
# Blender side
# ---------------------------------------------------------------------------
def main():
    import bpy
    from mathutils import Vector

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    if out is None:
        raise SystemExit("need --out <file.blend>")

    scn = bpy.context.scene
    piv = bpy.data.objects["AviaoPivo"]
    cam = bpy.data.objects["CamDecolagem"]
    rig = bpy.data.objects["SDSC_Placement"]
    if scn.frame_end != SRC_END:
        raise SystemExit("run this on the %d-frame placed file, not on its own "
                         "output - the aircraft action would be extended twice"
                         % SRC_END)

    def fcurves(action):
        if len(getattr(action, "fcurves", [])):
            return list(action.fcurves)
        fs = []
        for lay in action.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    fs.extend(cb.fcurves)
        return fs

    def channel(action, path, index):
        for c in fcurves(action):
            if c.data_path == path and c.array_index == index:
                return c
        raise KeyError((path, index))

    # ---- 1. extend the aeroplane -----------------------------------------
    act = piv.animation_data.action
    loc = [[channel(act, "location", i).evaluate(f) for i in range(3)]
           for f in range(1, SRC_END + 1)]
    rot = [[channel(act, "rotation_euler", i).evaluate(f) for i in range(3)]
           for f in range(1, SRC_END + 1)]
    loc, rot = extend_aircraft(loc, rot)
    for i in range(3):
        for path, data in (("location", loc), ("rotation_euler", rot)):
            c = channel(act, path, i)
            for f in range(SRC_END + 1, FRAME_END + 1):
                c.keyframe_points.insert(f, data[f - 1][i], options={'FAST'})
            for kp in c.keyframe_points:
                kp.interpolation = "LINEAR"
            c.update()

    # ---- 2. solve --------------------------------------------------------
    rows = solve_shot(FRAME_END)
    report(rows)

    psi_rig = rig.rotation_euler.z
    rig_inv = rig.matrix_world.inverted()
    cam_act = cam.animation_data.action
    for i in range(3):
        for path in ("location", "rotation_euler"):
            c = channel(cam_act, path, i)
            for kp in reversed(list(c.keyframe_points)):
                c.keyframe_points.remove(kp)

    for r in rows:
        wx, wy = S.al_xy(r["a"], r["lat"])
        wz = r["z"]
        # r["az"] is measured in the roll frame, positive to the RIGHT/east;
        # a compass bearing is TRACK + that.
        world_az = math.radians(S.TRACK_02_DEG) + r["az"]
        rx = math.pi / 2.0 + r["el"]
        rz = -world_az
        lx, ly, lz = rig_inv @ Vector((wx, wy, wz))
        for i, val in enumerate((lx, ly, lz)):
            channel(cam_act, "location", i).keyframe_points.insert(
                r["f"], val, options={'FAST'})
        for i, val in enumerate((rx, 0.0, rz - psi_rig)):
            channel(cam_act, "rotation_euler", i).keyframe_points.insert(
                r["f"], val, options={'FAST'})
        cam.data.lens = r["lens"]
        cam.data.keyframe_insert("lens", frame=r["f"])

    for i in range(3):
        for path in ("location", "rotation_euler"):
            c = channel(cam_act, path, i)
            for kp in c.keyframe_points:
                kp.interpolation = "LINEAR"
            c.update()
    for c in fcurves(cam.data.animation_data.action):
        for kp in c.keyframe_points:
            kp.interpolation = "LINEAR"
        c.update()

    cam.data.clip_start = 1.0
    cam.data.clip_end = 250000.0
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = S.SENSOR

    # ---- 3. the ramp -------------------------------------------------------
    # The MRO goes past on the RIGHT between 1 600 and 1 940 m of the roll, so
    # the nose-in line is in this frame from rotation to the close - at 800 to
    # 1 900 m, where an A320 is 15-37 px wide. Detailed models are not free at
    # that size, but a fin shape and an engine count are exactly what those
    # pixels carry, and this clip shares the fleet module with the other two:
    # the field it links no longer has proxies on those stands, so the
    # aeroplanes are instanced here, locally, from the same table.
    F.populate(scn)

    # ---- 4. render settings ----------------------------------------------
    scn.render.fps = 25
    scn.render.fps_base = 1.0
    scn.frame_start, scn.frame_end = 1, FRAME_END
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 96
    scn.cycles.use_denoising = True
    scn.cycles.max_bounces = 4
    scn.render.resolution_x, scn.render.resolution_y = 960, 540
    scn.render.use_motion_blur = True
    # A 180 deg shutter, the film standard, and affordable only because the
    # background never crosses faster than ~0.2 frame-widths/s here. Santiago's
    # v1 had to cut to 0.15 and then had thin geometry stepping 68 px per frame
    # with 10 px of blur behind it, which is what makes light masts strobe.
    scn.render.motion_blur_shutter = 0.50
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
    scn.camera = cam

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
