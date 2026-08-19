#!/usr/bin/env python3
"""Re-shoot the SCL take-off: a calm dolly that yields into an aerial reveal.

    blender -b "airbus A320neo/A320neo_scl.blend" \\
        -P scenario/takeoff_camera.py -- --out "airbus A320neo/A320neo_scl_v2.blend"

The module is importable without Blender (``import takeoff_camera``) so the
geometry can be tuned and printed without opening a 137 MB scene; ``bpy`` is
only touched inside :func:`main`.

Why the shot was rebuilt rather than tweaked
--------------------------------------------
The v1 SCL camera reused the azimuth curve of the no-scenery v2 clip - 123 deg
in 140 frames - and reframed it by sliding the camera out along its sight line
with the lens going 35 -> 140 mm. The curve was untouched, but the LENS is the
gain on it: what the eye reads is not deg/s, it is how much of the frame width
the world crosses per second, and that is (angular rate / horizontal FOV).
Same 31 deg/s through 14.7 deg of FOV instead of 54.9 deg is 3.7x faster on
screen. Measured: 2.0 frame-widths per second, sustained, where ~0.5 is calm.

Two more measured facts drove the rebuild:

* the v1 camera was itself a 114 m/s vehicle flying at 5-19 m through the west
  tree line (trees sit at e = -114..-201 m; the camera ran at e = -70..-182 m),
  so individual trees crossed the whole frame in 2-3 frames - the "objects that
  flash past" complaint. Nothing about the pan could fix that; the trajectory
  had to leave the tree line.
* an orbiting camera adds its own tangential speed to the aircraft's, so the
  apparent rate is the SUM. A dolly that runs down-runway WITH the aircraft
  subtracts instead: the useful invariant is

      screen flow  =  (aircraft size in frame) x (relative transverse speed) / L

  With v1's 80% subject and ~150 m/s of relative transverse speed that is
  ~3 widths/s. With a 40% subject and 23 m/s of relative speed it is 0.25.

Shape of the shot (v3 - the front-quarter crane)
------------------------------------------------
The v2 side-dolly-into-arc was calm and correct, and after five scenery
rounds it was also the reason every version looked the same. The owner's
brief for v3: show the FRONT of the aircraft, keep it the focus, and climb
the camera with it.

1-85    the approach. The camera starts 368 m AHEAD of the jet at nose
        height (7.5 m), e = -96 in the clean corridor, running down-track
        at ~30 m/s while the aircraft closes at 53-64. The nose grows
        head-on from 15.6% to 20% of frame width at 55 mm. The motion is
        almost purely radial, so the drama costs nearly nothing in screen
        flow (0.02-0.09 w/s).
85-128  rotation, and the hand-over. The jet pitches up 300 m from the
        lens; the rig blends from the runway-frame dolly into an ORBIT
        flown in the aircraft's own coordinates, entering it almost dead
        ahead (psi -21.5 deg, matched to the dolly position at frame 100).
128-240 the crane. Attached to the climbing aircraft, the camera rises
        with it by construction - plus its own gain, eye level to 21.5 deg
        above - while CLOSING 284 -> 225 m and swinging 22 deg around the
        starboard bow. Closing instead of receding keeps the jet growing
        as the world opens beneath it; the lens opens 55 -> 28 mm. The
        terminals slide past below-right, the LATAM base comes into frame
        over the aircraft's shoulder at frame ~195, and the aim swings
        11 -> 49 true, rotating the cordillera into the right half of the
        frame for the close.

The pan never reverses (0 direction changes, one smooth hump peaking at
7.0 deg/s) and no camera axis doubles back. The 5.7:1 body flow ratio is
the deliberately-still approach against the moving crane, not a hitch
inside a move - the rate ramps monotonically up and eases out.

Solved offline (this file, no Blender): flow median 0.103, max 0.121 w/s;
aircraft screen box u 0.32-0.60, v 0.21-0.56; Andes crest pinned at
v 0.70-0.82; camera 26-57 m/s. Scene-measured numbers live in the v8 GIF
commit via scenario/camera_metrics.py.

"""
import math

# --- survey (scl_aip_corrections.json), same numbers as place_aircraft.py ----
THR_17R = (-1582.57, 459.21)
TRACK_DEG = 177.424
Z_RUNWAY = 0.09

# --- the aircraft rig --------------------------------------------------------
PIVOT_X0 = 17.71          # AviaoPivo local x at frame 1 (main-gear contact)
ROLL_AT_FRAME_1 = 1670.3  # its roll distance down 17R at frame 1
AC_LENGTH = 37.57         # A320neo overall length, the size yardstick

# --- shot length -------------------------------------------------------------
FRAME_END = 240           # 9.6 s at 25 fps
SRC_END = 140             # the aircraft action stops here; we extend it

# --- landmarks in runway-local (s = roll distance, e = east of centreline) ----
LATAM_BASE = (1800.0, 880.0, 12.0)      # measured centre of the MRO buildings
ANDES_ELEV_DEG = 3.6                    # mean crest elevation, terrain/peaks.json


# ---------------------------------------------------------------------------
# small numeric helpers
# ---------------------------------------------------------------------------
def smoothstep(x):
    x = 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)
    return x * x * (3.0 - 2.0 * x)


def ramp(f, f0, f1, v0, v1):
    """Smoothstep from v0 to v1 between frames f0 and f1."""
    return v0 + (v1 - v0) * smoothstep((f - f0) / float(f1 - f0))


_PCHIP = {}


def _slopes(pts):
    """Fritsch-Carlson tangents: C1 everywhere, monotone, no overshoot.

    A smoothstep chain looks smooth on a graph and is wrong for a camera: its
    derivative is ZERO at every control point, so the crane stops climbing, and
    then starts again, once per control point. That pulsing showed up as a
    107 m/s2 acceleration spike before this replaced it.
    """
    n = len(pts)
    h = [pts[i + 1][0] - pts[i][0] for i in range(n - 1)]
    dl = [(pts[i + 1][1] - pts[i][1]) / h[i] for i in range(n - 1)]
    m = [0.0] * n                       # ease in and out at the two ends
    for i in range(1, n - 1):
        if dl[i - 1] * dl[i] <= 0.0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])
    return h, m


def piecewise(f, pts):
    """Monotone cubic (PCHIP) through (frame, value) control points."""
    key = id(pts)
    if key not in _PCHIP:
        _PCHIP[key] = _slopes(pts)
    h, m = _PCHIP[key]
    if f <= pts[0][0]:
        return pts[0][1]
    if f >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        if f <= pts[i + 1][0]:
            t = (f - pts[i][0]) / h[i]
            t2, t3 = t * t, t * t * t
            return ((2 * t3 - 3 * t2 + 1) * pts[i][1]
                    + (t3 - 2 * t2 + t) * h[i] * m[i]
                    + (-2 * t3 + 3 * t2) * pts[i + 1][1]
                    + (t3 - t2) * h[i] * m[i + 1])
    return pts[-1][1]


def gaussian_smooth(vals, sigma):
    if sigma <= 0:
        return list(vals)
    n = len(vals)
    half = int(math.ceil(3 * sigma))
    ker = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-half, half + 1)]
    out = []
    for i in range(n):
        acc = wsum = 0.0
        for k, w in zip(range(-half, half + 1), ker):
            j = min(n - 1, max(0, i + k))      # clamp at the ends
            acc += w * vals[j]
            wsum += w
        out.append(acc / wsum)
    return out


# ---------------------------------------------------------------------------
# the aircraft: the shipped 140 frames, plus a physical continuation
# ---------------------------------------------------------------------------
def extend_aircraft(loc, rot):
    """Continue the climb past frame 140.

    ``loc``/``rot`` are the per-frame AviaoPivo channels for frames 1..140.
    The aircraft leaves frame 140 at 64.71 m/s with 8.85 m/s of climb and
    13.60 deg of pitch. It keeps accelerating, but the acceleration tapers as
    the speed builds, the climb rate goes up with it (gradient stays ~14%) and
    the pitch eases back by a degree, which is what an A320 does once it is
    established on the initial climb.
    """
    x0, y0, z0 = loc[-1]
    vx = (loc[-1][0] - loc[-2][0]) * 25.0        # m/s, negative (nose is -x)
    vz = (loc[-1][2] - loc[-2][2]) * 25.0
    p0 = rot[-1][1]
    speed0, speed1 = abs(vx), 74.5
    vs0, vs1 = vz, 11.2
    n = FRAME_END - SRC_END
    x, z = x0, z0
    for i in range(1, n + 1):
        sp = ramp(i, 0, n, speed0, speed1)
        vs = ramp(i, 0, n, vs0, vs1)
        x -= sp / 25.0
        z += vs / 25.0
        loc.append((x, y0, z))
        rot.append((rot[-1][0], ramp(i, 0, n, p0, p0 - math.radians(1.0)),
                    rot[-1][2]))
    return loc, rot


# ---------------------------------------------------------------------------
# the camera path, in runway-local (s down the roll, e east, h above pavement)
# ---------------------------------------------------------------------------
# Along-runway dolly speed. The v3 camera starts AHEAD of the aircraft and
# runs slower than it, so the jet closes head-on through the whole ground
# run - the approach IS the drama, and it is radial, so it costs almost no
# screen flow. Past the hand-over the orbit below owns the position; these
# curves keep running only so the blend has something smooth to blend FROM.
DOLLY_SPEED = [(1, 26.0), (60, 30.0), (100, 34.0), (140, 40.0),
               (180, 46.0), (240, 50.0)]

# Lateral: hold the clean corridor between the runway edge and the tree line
# (the nearest tree is at e = -114.5 m). The camera only drifts west once the
# orbit is in charge and the height has already cleared the trees.
LATERAL = [(1, -96.0), (70, -96.0), (100, -104.0), (140, -120.0),
           (240, -150.0)]

# Height: nose-level for the approach - 7.5 m puts the lens just under the
# fin and above every tuft - then the crane rises with the rotation. The
# orbit's elevation takes over from ~frame 100.
HEIGHT = [(1, 7.5), (60, 8.5), (85, 12.0), (110, 22.0), (150, 45.0),
          (240, 90.0)]

# From frame ~100 the camera stops being a dolly and becomes an ORBIT, flown
# in coordinates attached to the aircraft: distance, relative bearing (0 =
# dead ahead, negative = off its right/starboard bow, which is where the
# camera sits) and elevation above it. The v3 move is a FRONT-QUARTER CRANE:
# it starts 284 m off the nose almost dead ahead (psi -21.5, matching the
# dolly's own position at frame 100 so the hand-over is invisible), then
# CLOSES to 225 m while swinging 22 deg around toward the right bow and
# climbing from eye level to 24 deg above the aircraft. Closing instead of
# receding is what keeps the jet growing in frame as the world opens under
# it; the climb is automatic - the orbit is attached to the aircraft, so the
# camera rises with the climb-out plus its own elevation gain.
# The last entry is past FRAME_END on purpose: PCHIP eases to a stop at its
# final knot, and a camera that slams to a halt on the last frame reads as a
# lurch. Overshooting the knot leaves the move still travelling when the
# clip ends, decelerating gently rather than braking.
# v4: the orbit owns the WHOLE shot - there is no dolly phase and no
# hand-over. The residual stiffness the owner still saw in v3 lived in the
# seam between the two coordinate frames; a camera that flies formation in
# the aircraft's own frame from frame 1 has no seam to read. During the
# ground roll psi stays shallow (-13.5 deg) because a wider angle at 400 m
# would put the camera INSIDE the west tree line (nearest tree e = -114.5;
# at psi -20 the camera sits at e = -128 ten metres up - the v1 disaster).
# The swing around the bow waits for the altitude that clears the trees.
ORBIT = [(1, 400.0, -13.5, 1.8), (60, 362.0, -14.0, 1.9),
         (100, 315.0, -16.0, 2.6), (140, 270.0, -22.0, 6.0),
         (180, 240.0, -30.0, 12.0), (210, 222.0, -38.0, 17.0),
         (240, 205.0, -45.0, 21.5), (275, 192.0, -52.0, 26.5)]
ORBIT_BLEND = (-10, -5)   # w = 1 from frame 1: the orbit is the shot

# Formation flight is not a rail: a real chase drone drifts. Two slow
# sinusoids on the camera position - amplitudes about a metre, periods 7.3
# and 5.1 s, well under one cycle per reveal - break the CG-perfect line
# without registering in the flow metrics.
SWAY_E = (1.2, 7.3, 0.9)     # amplitude m, period s, phase rad
SWAY_H = (0.5, 5.1, 2.1)
ORBIT_D = [(p[0], p[1]) for p in ORBIT]
ORBIT_PSI = [(p[0], p[2]) for p in ORBIT]
ORBIT_EPS = [(p[0], p[3]) for p in ORBIT]

# Focal length. Long through the approach - 55 mm compresses the nose-on jet
# against the field and costs nothing while the motion is radial - then it
# opens through the crane so the climb reads as the world widening, not as a
# zoom-out. The pan-rate gain of the long end lives only where the pan is
# near zero.
LENS = [(1, 55.0), (70, 56.0), (100, 54.0), (140, 45.0), (180, 36.0),
        (210, 31.0), (240, 28.0), (275, 26.0)]

# Where the aircraft sits in frame. Nearly centred for the head-on approach,
# then easing left of centre so the reveal - the terminals sliding past, the
# base behind, the cordillera - opens into the right half of the frame.
SCREEN_U = [(1, 0.52), (70, 0.50), (120, 0.46), (180, 0.43), (240, 0.41),
            (275, 0.40)]

# Tilt is NOT driven off the aircraft. The Andes crest line is pinned to the
# frame instead, and the aircraft is allowed to float against it. That is the
# eye's anchor: with the horizon holding still, a moving camera stays legible,
# and it also stops the cordillera being tipped out of the top of the frame
# when the crane climbs above the aircraft.
HORIZON_V = [(1, 0.70), (70, 0.75), (120, 0.78), (180, 0.80), (240, 0.82),
             (275, 0.83)]

AIM_SMOOTH = 9.0          # frames of Gaussian smoothing on the solved angles
FINAL_SMOOTH = 8.0        # kills the ripple the piecewise path leaves in the pan
SENSOR = 36.0
ASPECT = 16.0 / 9.0


def orbit_point(f, ac_s, ac_h):
    """Camera position from the aircraft-attached orbit, in runway-local."""
    d = piecewise(f, ORBIT_D)
    psi = math.radians(piecewise(f, ORBIT_PSI))
    eps = math.radians(piecewise(f, ORBIT_EPS))
    horiz = d * math.cos(eps)
    return (ac_s + horiz * math.cos(psi),
            0.0 + horiz * math.sin(psi),
            ac_h + d * math.sin(eps))


def camera_path(ac_s, ac_h, nframes=FRAME_END):
    """Integrate the dolly, then hand over to the orbit. Returns [(s, e, h)]."""
    dolly = []
    s = 0.0
    for f in range(1, nframes + 1):
        if f > 1:
            s += piecewise(f - 0.5, DOLLY_SPEED) / 25.0
        dolly.append((s, piecewise(f, LATERAL), piecewise(f, HEIGHT)))
    # anchor: at frame 70 the camera sits 300 m AHEAD of the abeam station,
    # looking back up the roll at the approaching nose. The LATAM base still
    # enters the frame behind the aircraft - now over its shoulder instead of
    # broadside - and the aim at frame 70 is roughly 340 true.
    s_abeam = 1816.1 + 300.0
    off = s_abeam - dolly[69][0]
    dolly = [(s + off, e, h) for (s, e, h) in dolly]

    out = []
    for f in range(1, nframes + 1):
        w = smoothstep((f - ORBIT_BLEND[0]) / float(ORBIT_BLEND[1] - ORBIT_BLEND[0]))
        a = dolly[f - 1]
        if w <= 0.0:
            out.append(a)
            continue
        b = orbit_point(f, ac_s[f - 1], ac_h[f - 1])
        out.append(tuple(x + (y - x) * w for x, y in zip(a, b)))
    # drone drift: slow positional sway, honest formation-flight texture
    t = [f / 25.0 for f in range(1, nframes + 1)]
    out = [(s,
            e + SWAY_E[0] * math.sin(2 * math.pi * tt / SWAY_E[1] + SWAY_E[2]),
            h + SWAY_H[0] * math.sin(2 * math.pi * tt / SWAY_H[1] + SWAY_H[2]))
           for (s, e, h), tt in zip(out, t)]
    return out


def solve_shot(ac_s, ac_h, nframes=FRAME_END):
    """Solve azimuth, elevation and focal length for every frame.

    Returns a list of dicts in runway-local terms; :func:`main` converts to
    Blender world space.
    """
    cam = camera_path(ac_s, ac_h, nframes)
    raw_az, raw_el, dist = [], [], []
    for f in range(nframes):
        cs, ce, ch = cam[f]
        # aim at the aircraft's visual centre: the pivot is the main-gear
        # contact, the body centre is ~2.9 m above it and ~1.5 m aft.
        ds = ac_s[f] + 1.5 - cs
        de = 0.0 - ce
        dh = ac_h[f] + 2.9 - ch
        raw_az.append(math.atan2(de, ds))      # 0 = down the roll, +ve = east
        raw_el.append(math.atan2(dh, math.hypot(ds, de)))
        dist.append(math.sqrt(ds * ds + de * de + dh * dh))

    # unwrap (the aim never crosses +-pi here, but be explicit) and smooth: a
    # human operator does not track a moving target with zero lag, and the
    # smoothing is what shaves the peak off the pan rate at closest approach.
    for i in range(1, len(raw_az)):
        while raw_az[i] - raw_az[i - 1] > math.pi:
            raw_az[i] -= 2 * math.pi
        while raw_az[i] - raw_az[i - 1] < -math.pi:
            raw_az[i] += 2 * math.pi
    sm_az = gaussian_smooth(raw_az, AIM_SMOOTH)
    sm_el = gaussian_smooth(raw_el, AIM_SMOOTH)

    rows = []
    for f in range(nframes):
        fr = f + 1
        cs, ce, ch = cam[f]
        lens = piecewise(fr, LENS)
        u = piecewise(fr, SCREEN_U)
        t = (SENSOR / 2.0) / lens              # tan(hfov/2)
        hfov = 2.0 * math.atan(t)
        # Screen x grows with TRUE azimuth, and true = TRACK - local, so a
        # subject to the right of centre sits at a HIGHER local azimuth than
        # the camera. Getting this sign wrong mirrors the whole composition.
        az = sm_az[f] + math.atan((u - 0.5) * 2.0 * t)
        hv = piecewise(fr, HORIZON_V)
        el = (math.radians(ANDES_ELEV_DEG)
              - math.atan((hv - 0.5) * 2.0 * t / ASPECT))
        v = 0.5 + math.tan(sm_el[f] - el) * ASPECT / (2.0 * t)
        size = 2.0 * math.atan(0.5 * AC_LENGTH / dist[f]) / hfov
        rows.append(dict(f=fr, s=cs, e=ce, h=ch, az=az, el=el, lens=lens,
                         dist=dist[f], size=size, u=u, v=v, horizon_v=hv,
                         ac_s=ac_s[f], ac_h=ac_h[f]))
    # one more light pass so the solved lens/angle pair cannot chatter, then
    # recover where the aircraft ACTUALLY lands - the u/v above were requests.
    for key in ("az", "el", "lens"):
        sm = gaussian_smooth([r[key] for r in rows], FINAL_SMOOTH)
        for r, x in zip(rows, sm):
            r[key] = x
    # The pan runs one way while the aircraft overtakes the camera and the
    # other way once the camera overtakes the aircraft - that sign change IS
    # the orbit, and it happens once, smoothly, at the apex. What is not
    # allowed is ripple: the piecewise path leaves ~0.1 deg wobbles that would
    # read as extra direction changes, so the RATE is smoothed and the angle
    # re-integrated from it rather than the angle being smoothed directly.
    az = [r["az"] for r in rows]
    d = gaussian_smooth([b - a for a, b in zip(az, az[1:])], 6.0)
    out = [az[0]]
    for step in d:
        out.append(out[-1] + step)
    for r, x in zip(rows, out):
        r["az"] = x

    for f, r in enumerate(rows):
        t = (SENSOR / 2.0) / r["lens"]
        r["u"] = 0.5 - math.tan(raw_az[f] - r["az"]) / (2.0 * t)
        r["v"] = 0.5 + math.tan(raw_el[f] - r["el"]) * ASPECT / (2.0 * t)
        r["size"] = 2.0 * math.atan(0.5 * AC_LENGTH / r["dist"]) \
            / (2.0 * math.atan(t))
        r["horizon_v"] = 0.5 + (math.tan(math.radians(ANDES_ELEV_DEG) - r["el"])
                                * ASPECT / (2.0 * t))
    return rows


def report(rows):
    """Print the numbers the shot is judged on."""
    fps = 25.0
    print("\n%-5s %8s %8s %7s %7s %6s %7s %7s %6s %6s %6s %6s"
          % ("frame", "roll_m", "cam_s", "cam_e", "cam_h", "lens",
             "az_true", "pan_d/s", "flow", "ac_u", "ac_v", "size%"))
    prev = None
    flows, pans, azt = [], [], []
    for r in rows:
        az_true = (TRACK_DEG - math.degrees(r["az"])) % 360.0
        azt.append(az_true)
        hfov = 2.0 * math.atan((SENSOR / 2.0) / r["lens"])
        pan = flow = float("nan")
        if prev:
            dpan = math.hypot(r["az"] - prev["az"], r["el"] - prev["el"]) * fps
            pan = math.degrees(dpan)
            flow = dpan / hfov
            flows.append(flow)
            pans.append(pan)
        if r["f"] % 10 == 0 or r["f"] in (1, 70):
            print("%-5d %8.1f %8.1f %7.1f %7.1f %6.1f %7.1f %7.2f %6.3f "
                  "%6.2f %6.2f %6.1f"
                  % (r["f"], r["ac_s"], r["s"], r["e"], r["h"], r["lens"],
                     az_true, pan, flow, r["u"], r["v"], r["size"] * 100))
        prev = r
    body = flows[8:-8]
    print("\nlens %.1f -> %.1f mm   azimuth sweep %.1f deg over %.2f s"
          % (rows[0]["lens"], rows[-1]["lens"], azt[-1] - azt[0],
             len(rows) / fps))
    print("pan rate  max %.1f deg/s   flow  median %.3f  max %.3f w/s"
          % (max(pans), sorted(flows)[len(flows) // 2], max(flows)))
    print("body (excl. 8-frame ease at each end): flow min %.3f max %.3f "
          "ratio %.2f" % (min(body), max(body), max(body) / max(min(body), 1e-9)))
    rev = [i + 1 for i in range(1, len(azt) - 1)
           if (azt[i] - azt[i - 1]) * (azt[i + 1] - azt[i]) < 0]
    print("pan direction reversals: %d %s"
          % (len(rev), rev[:12] if rev else ""))
    umin = min(r["u"] - r["size"] / 2 for r in rows)
    umax = max(r["u"] + r["size"] / 2 for r in rows)
    vs = [r["v"] for r in rows]
    print("aircraft screen box  u %.3f..%.3f   v %.3f..%.3f   "
          "(rough margin %.1f%%)"
          % (umin, umax, min(vs), max(vs), 100 * min(umin, 1 - umax)))
    hv = [r["horizon_v"] for r in rows]
    print("Andes crest line held at v %.3f..%.3f" % (min(hv), max(hv)))
    # camera speed, the thing that whips near objects
    sp = []
    for a, b in zip(rows, rows[1:]):
        sp.append(math.dist((a["s"], a["e"], a["h"]),
                            (b["s"], b["e"], b["h"])) * fps)
    acc = [abs(b - a) * 25.0 for a, b in zip(sp, sp[1:])]
    print("camera speed %.0f..%.0f m/s, peak acceleration %.1f m/s2"
          % (min(sp), max(sp), max(acc)))
    # the orbit must not double back on itself in any axis
    for i, name in enumerate(("s", "e", "h")):
        d = [b[name if False else i] - a[i] for a, b in
             zip([(r["s"], r["e"], r["h"]) for r in rows],
                 [(r["s"], r["e"], r["h"]) for r in rows[1:]])]
        flips = sum(1 for x, y in zip(d, d[1:]) if x * y < 0)
        print("  axis %s: %+.0f m total, %d direction changes" % (name, sum(d), flips))
    # where the LATAM base and the cordillera sit in frame
    print("\n%-5s %8s %8s %9s %9s   %s"
          % ("frame", "base_u", "base_v", "base_dist", "andes_v", "note"))
    for r in rows:
        if r["f"] % 20 and r["f"] not in (1, 70):
            continue
        u, v, d = landmark_uv(r, LATAM_BASE)
        t = (SENSOR / 2.0) / r["lens"]
        andes_v = 0.5 + (math.tan(math.radians(ANDES_ELEV_DEG) - r["el"])
                         * ASPECT / (2 * t))
        print("%-5d %8.3f %8.3f %9.0f %9.3f   %s"
              % (r["f"], u, v, d, andes_v,
                 "base in frame" if 0.02 <= u <= 0.98 and 0.02 <= v <= 0.98
                 else "base OUT"))


def landmark_uv(row, point):
    """Screen position of a fixed runway-local point in a solved frame."""
    ds = point[0] - row["s"]
    de = point[1] - row["e"]
    dh = point[2] - row["h"]
    az = math.atan2(de, ds)
    el = math.atan2(dh, math.hypot(ds, de))
    t = (SENSOR / 2.0) / row["lens"]
    u = 0.5 - math.tan(az - row["az"]) / (2 * t)
    v = 0.5 + math.tan(el - row["el"]) * ASPECT / (2 * t)
    return u, v, math.hypot(ds, de)


# ---------------------------------------------------------------------------
# Blender side
# ---------------------------------------------------------------------------
def main():
    import bpy
    import os
    import sys
    from mathutils import Vector

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    if out is None:
        raise SystemExit("need --out <file.blend>")

    scn = bpy.context.scene
    piv = bpy.data.objects["AviaoPivo"]
    cam = bpy.data.objects["CamDecolagem"]
    rig = bpy.data.objects["SCL_Placement"]
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

    # ---- 1. extend the aircraft ------------------------------------------
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

    ac_s = [ROLL_AT_FRAME_1 + (PIVOT_X0 - p[0]) for p in loc]
    ac_h = [p[2] + 3.670 + Z_RUNWAY for p in loc]   # pivot height over pavement

    # ---- 2. solve the camera ---------------------------------------------
    rows = solve_shot(ac_s, ac_h, FRAME_END)
    report(rows)

    ux = math.sin(math.radians(TRACK_DEG))
    uy = math.cos(math.radians(TRACK_DEG))
    nx, ny = -uy, ux                       # east = left of the roll
    psi = rig.rotation_euler.z
    rig_inv = rig.matrix_world.inverted()

    cam_act = cam.animation_data.action
    for i in range(3):
        for path in ("location", "rotation_euler"):
            c = channel(cam_act, path, i)
            for kp in reversed(list(c.keyframe_points)):
                c.keyframe_points.remove(kp)

    for r in rows:
        wx = THR_17R[0] + ux * r["s"] + nx * r["e"]
        wy = THR_17R[1] + uy * r["s"] + ny * r["e"]
        wz = Z_RUNWAY + r["h"]
        world_az = math.radians(TRACK_DEG) - r["az"]
        # Blender camera: rotation_euler = (pi/2 + elevation, 0, -azimuth)
        rx = math.pi / 2.0 + r["el"]
        rz = -world_az
        lx, ly, lz = rig_inv @ Vector((wx, wy, wz))
        for i, val in enumerate((lx, ly, lz)):
            channel(cam_act, "location", i).keyframe_points.insert(
                r["f"], val, options={'FAST'})
        for i, val in enumerate((rx, 0.0, rz - psi)):
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
    cam.data.clip_end = 300000.0
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = SENSOR

    # ---- 3. render settings ----------------------------------------------
    scn.render.fps = 25
    scn.render.fps_base = 1.0
    scn.frame_start, scn.frame_end = 1, FRAME_END
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 96
    scn.cycles.use_denoising = True
    scn.cycles.max_bounces = 4
    scn.render.resolution_x, scn.render.resolution_y = 960, 540
    scn.render.use_motion_blur = True
    # A 180 deg shutter, the film standard - and affordable only because the
    # pan slowed down. v1 had to cut its shutter to 0.15 because at 0.40 the
    # background smeared ~26 px at the abeam frame; it then had thin geometry
    # jumping ~65 px per frame with 10 px of blur, which is what makes light
    # masts strobe. Here the background crosses 0.28 frame-widths/s at worst,
    # so 0.50 smears it 4.5 px while covering the whole inter-frame step -
    # motion that joins up instead of stepping.
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
        # offline tuning: reconstruct the aircraft track from the exported curve
        import json
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        cache = os.environ.get("AC_CURVE", os.path.join(here, "ac_curve.json"))
        data = json.load(open(cache))
        loc, rot = extend_aircraft([tuple(p) for p in data["loc"]],
                                   [tuple(p) for p in data["rot"]])
        ac_s = [ROLL_AT_FRAME_1 + (PIVOT_X0 - p[0]) for p in loc]
        ac_h = [p[2] + 3.670 + Z_RUNWAY for p in loc]
        report(solve_shot(ac_s, ac_h, FRAME_END))
    else:
        main()
