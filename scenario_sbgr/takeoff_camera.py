#!/usr/bin/env python3
"""Clip 1 — the 777 off RWY 10L: a starboard-quarter chase under the ridge.

    blender -b scenario_sbgr/sbgr_takeoff.blend \\
        -P scenario_sbgr/takeoff_camera.py -- --out scenario_sbgr/sbgr_takeoff_v1.blend

    python3 scenario_sbgr/takeoff_camera.py     # offline solve, ~1 s, no Blender

WHAT THIS FIELD GIVES THE SHOT
==============================
São Carlos's departure is anchored to a ruler-flat horizon and its reveal is
the terrain uncovering the base. Guarulhos gives back what São Carlos lacked
and Santiago had: a CREST. The Cabuçu/Cantareira wall crosses the whole sector
this lens sweeps at +1.8..+3.2° (mean +2.39°), so the tilt is pinned to the
ridge exactly as Santiago pins the Andes — and the reveal is not terrain but
GEOMETRY IN TIME: rotation begins abeam the LATAM hangar (s 2 571), so the
nose lifts precisely as the aeroplane's own maintenance base crosses the
frame behind it, ridge above, both grazing-lit by the 17:30 sun.

THE SIDE IS DECIDED BY THREE THINGS AT ONCE
-------------------------------------------
The hangar is NORTH of the runway; the sun at 251° is almost dead astern of a
073° departure (2° off the tail); phase 2's proven still
(`checks/ground_south_side_hangar_ridge.png`) already held hangar + heavy +
ridge from the SOUTH. A camera south of the roll looking north gets all
three: the hangar face beyond the aeroplane, the ridge above it, and the low
sun raking both from behind-left of the lens. The starboard quarter is also
the side the SDSC clips never used, which the fleet's starboard round exists
to support.

THE SHAPE OF THE MOVE
---------------------
One orbit in the aeroplane's own frame, frame 1 to 240, no dolly, no
hand-over — the two-base lesson, kept. ψ is the camera's relative bearing
from the aeroplane, 0 = dead ahead, POSITIVE TO STARBOARD (south). The orbit
opens on the aft-starboard quarter and walks toward the beam as the range
opens and the lens eases wide, so the 74 m aeroplane never crowds the frame
and the hangar holds the left third through rotation:

    1–128   the roll, ψ 127°, d 225→245 m, ε ~5°: the jet 36% of frame
            width, three-quarter rear, hangar sliding in from frame-left.
    128–160 rotation abeam the hangar: ψ eases 127→120°, the nose comes up
            3.1°/s against the ridge.
    160–240 lift-off and climb-out: d opens to 375 m, ε 5.0→6.2° — the
            camera climbs SLOWER than the jet, so the aeroplane rises
            through the frame (v 0.42→0.52) while the ridge line holds.

A metre of two-sinusoid sway (periods 7.3 / 5.1 s, mutually prime) keeps the
formation flight from reading as a rail.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import shot_common as S                                       # noqa: E402

FRAME_END = 240
AC_LENGTH = 73.86
AC_SPAN = 64.80
Z_RUNWAY = 0.09
MG_X = 36.5                  # main-gear contact aft of the nose (place_777)

# --- the orbit, aircraft frame ----------------------------------------------
ORBIT = [(1, 225.0, 127.0, 5.0), (60, 232.0, 126.0, 5.0),
         (110, 242.0, 124.0, 5.1), (150, 262.0, 121.0, 5.2),
         (190, 300.0, 117.5, 5.0), (240, 355.0, 113.0, 4.6),
         (275, 395.0, 110.5, 4.4)]
ORBIT_D = [(p[0], p[1]) for p in ORBIT]
ORBIT_PSI = [(p[0], p[2]) for p in ORBIT]
ORBIT_EPS = [(p[0], p[3]) for p in ORBIT]

SWAY_LAT = (1.1, 7.3, 0.9)
SWAY_H = (0.5, 5.1, 2.1)

LENS = [(1, 48.0), (110, 44.5), (160, 41.5), (200, 40.0), (240, 39.0),
        (275, 38.5)]

# The aeroplane drifts right through the clip so the hangar and the ridge own
# the left half at the close.
SCREEN_U = [(1, 0.58), (110, 0.63), (160, 0.66), (200, 0.67), (240, 0.67),
            (275, 0.67)]

# The anchor: the Cantareira crest, held like Santiago holds the Andes.
HORIZON_V = [(1, 0.70), (110, 0.71), (160, 0.72), (200, 0.735), (240, 0.75),
             (275, 0.76)]

AIM_SMOOTH = 9.0
FINAL_SMOOTH = 8.0
RATE_SMOOTH = 6.0


def aircraft_track():
    d = json.load(open(os.path.join(HERE, "ac_curve_sbgr.json")))
    prof = d["profile"]
    s = [p[0] for p in prof]
    z = [S.rwy_z(p[0]) + Z_RUNWAY + p[1] for p in prof]
    pitch = [p[2] for p in prof]
    return s, z, pitch


def camera_path(ac_s, ac_z, nframes=FRAME_END):
    out = []
    for f in range(1, nframes + 1):
        d = S.piecewise(f, ORBIT_D)
        psi = math.radians(S.piecewise(f, ORBIT_PSI))
        eps = math.radians(S.piecewise(f, ORBIT_EPS))
        horiz = d * math.cos(eps)
        t = f / S.FPS
        out.append((ac_s[f - 1] + horiz * math.cos(psi),
                    horiz * math.sin(psi)
                    + SWAY_LAT[0] * math.sin(2 * math.pi * t / SWAY_LAT[1]
                                             + SWAY_LAT[2]),
                    ac_z[f - 1] + d * math.sin(eps)
                    + SWAY_H[0] * math.sin(2 * math.pi * t / SWAY_H[1]
                                           + SWAY_H[2])))
    return out


def bearing_sl(ds, dl):
    """Compass bearing of an (s, l) displacement."""
    return math.radians(S.TRACK_DEG) + math.atan2(dl, ds)


def solve_shot(nframes=FRAME_END):
    ac_s, ac_z, pitch = aircraft_track()
    cam = camera_path(ac_s, ac_z, nframes)

    raw_b, raw_e, dist = [], [], []
    for f in range(nframes):
        cs, cl, cz = cam[f]
        # visual centre: the pivot rides the main gear and the 777's centre
        # is almost exactly at the pivot station (nose +36.5, tail -37.4);
        # aim 2 m ahead of it and 7 m up (fuselage centreline + a little fin)
        ds, dl = ac_s[f] + 2.0 - cs, 0.0 - cl
        dz = ac_z[f] + 7.0 - cz
        raw_b.append(bearing_sl(ds, dl))
        raw_e.append(math.atan2(dz, math.hypot(ds, dl)))
        dist.append(math.sqrt(ds * ds + dl * dl + dz * dz))

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
        el = (math.radians(S.RIDGE_ELEV_DEG)
              - math.atan((hv - 0.5) * 2.0 * t / S.ASPECT))
        x, y = S.sl_xy(cam[f][0], cam[f][1])
        rows.append(dict(f=fr, s=cam[f][0], l=cam[f][1], z=cam[f][2],
                         az=az, el=el, lens=lens, dist=dist[f],
                         ac_s=ac_s[f], ac_z=ac_z[f], pitch=pitch[f],
                         cam=(x, y, cam[f][2])))

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

    for f, r in enumerate(rows):
        t = S.half_tan(r["lens"])
        r["u"] = 0.5 + math.tan(raw_b[f] - r["az"]) / (2 * t)
        r["v"] = 0.5 + math.tan(raw_e[f] - r["el"]) * S.ASPECT / (2 * t)
        r["ridge_v"] = (0.5 + math.tan(math.radians(S.RIDGE_ELEV_DEG)
                                       - r["el"]) * S.ASPECT / (2 * t))
        psi = math.radians(S.piecewise(r["f"], ORBIT_PSI))
        width = max(AC_LENGTH * abs(math.sin(psi)),
                    AC_SPAN * abs(math.cos(psi)),
                    0.55 * (AC_LENGTH * abs(math.sin(psi))
                            + AC_SPAN * abs(math.cos(psi))))
        r["size"] = (2 * math.atan(0.5 * width / r["dist"])
                     / S.hfov(r["lens"]))
    return rows


LANDMARKS = {
    "hangar_sw": (S.sl_xy(S.HANGAR_S - 68, S.HANGAR_L)
                  + (S.HANGAR_EAVE_Z,)),
    "hangar_ne": (S.sl_xy(S.HANGAR_S + 68, S.HANGAR_L)
                  + (S.HANGAR_EAVE_Z,)),
    "hangar_door": (S.sl_xy(S.HANGAR_S, S.HANGAR_L + 46)
                    + (S.Z_HGR_PLATFORM + 10.0,)),
    "thr_28R": S.sl_xy(S.THR28R_S, 0.0) + (S.rwy_z(S.THR28R_S),),
}


def report(rows):
    print("\n%-5s %8s %8s %8s %7s %8s %7s %6s %6s %6s %8s"
          % ("frame", "ac_s", "cam_s", "cam_l", "cam_z", "az_deg",
             "lens", "ac_u", "ac_v", "size%", "ridge_v"))
    for r in rows:
        if r["f"] % 20 and r["f"] not in (1, 128, 160, FRAME_END):
            continue
        print("%-5d %8.0f %8.0f %8.1f %7.1f %8.1f %7.1f %6.2f %6.2f %6.1f "
              "%8.2f"
              % (r["f"], r["ac_s"], r["s"], r["l"], r["z"],
                 math.degrees(r["az"]) % 360.0, r["lens"],
                 r["u"], r["v"], 100 * r["size"], r["ridge_v"]))

    S.flow_report(rows, "SBGR departure, RWY 10L")

    umin = min(r["u"] - r["size"] / 2 for r in rows)
    umax = max(r["u"] + r["size"] / 2 for r in rows)
    vs = [r["v"] for r in rows]
    print("aeroplane in frame: width %.1f%% -> %.1f%%, u %.3f..%.3f, "
          "v %.3f..%.3f, edge margin %.1f%%"
          % (100 * rows[0]["size"], 100 * rows[-1]["size"], umin, umax,
             min(vs), max(vs), 100 * min(umin, 1 - umax)))
    rv = [r["ridge_v"] for r in rows]
    print("ridge held at v %.3f..%.3f (crest %.2f deg)"
          % (min(rv), max(rv), S.RIDGE_ELEV_DEG))
    print("camera lateral %.0f..%.0f m SOUTH of the 10L centreline "
          "(RWY 10R is at l +373)"
          % (min(r["l"] for r in rows), max(r["l"] for r in rows)))

    print("\n%-5s %s" % ("frame", " ".join("%13s" % k for k in LANDMARKS)))
    for r in rows:
        if r["f"] % 40 and r["f"] not in (1, 128, 160, FRAME_END):
            continue
        cells = []
        for k, p in LANDMARKS.items():
            u, v, _ = S.project(r["cam"], r["az"], r["el"], r["lens"], p)
            cells.append("%5.2f,%5.2f%s" % (u, v,
                                            " " if 0 <= u <= 1 and 0 <= v <= 1
                                            else "*"))
        print("%-5d %s" % (r["f"], " ".join("%13s" % c for c in cells)))
    print("       (u, v of each landmark; * = outside the frame)")


# ---------------------------------------------------------------------------
def main():
    import bpy

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    if out is None:
        raise SystemExit("need --out <file.blend>")

    scn = bpy.context.scene
    cam = bpy.data.objects["CamDecolagem"]
    cam.parent = None
    for c in cam.constraints:
        cam.constraints.remove(c)
    dbg = bpy.data.objects.get("DbgAim")
    if dbg:
        bpy.data.objects.remove(dbg, do_unlink=True)

    rows = solve_shot(FRAME_END)
    report(rows)

    if cam.animation_data:
        cam.animation_data_clear()
    if cam.data.animation_data:
        cam.data.animation_data_clear()
    for r in rows:
        x, y, z = r["cam"]
        cam.location = (x, y, z)
        cam.rotation_euler = (math.pi / 2.0 + r["el"], 0.0, -r["az"])
        cam.keyframe_insert("location", frame=r["f"])
        cam.keyframe_insert("rotation_euler", frame=r["f"])
        cam.data.lens = r["lens"]
        cam.data.keyframe_insert("lens", frame=r["f"])

    def fcurves(act):
        if len(getattr(act, "fcurves", [])):
            return list(act.fcurves)
        fs = []
        for lay in act.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    fs.extend(cb.fcurves)
        return fs

    for act in (cam.animation_data.action, cam.data.animation_data.action):
        for c in fcurves(act):
            for kp in c.keyframe_points:
                kp.interpolation = "LINEAR"
            c.update()

    cam.data.clip_start = 1.0
    cam.data.clip_end = 250000.0
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = S.SENSOR
    scn.camera = cam
    scn.frame_start, scn.frame_end = 1, FRAME_END

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
