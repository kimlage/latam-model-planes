#!/usr/bin/env python3
"""Clip 2 — a 787-9 towed into hangar 9. Nothing in this repository has done this before.

    blender -b --factory-startup scenario_sdsc/sdsc_field.blend \\
        -P scenario_sdsc/hangar_tow.py -- --out scenario_sdsc/sdsc_hangar_tow.blend

    python3 scenario_sdsc/hangar_tow.py     # the tow solved offline, ~1 s

WHY A 787-9, AND WHY THIS BUILDING
==================================
Hangar 9 was inaugurated on 26 September 2025 **for Boeing 787 heavy
maintenance** — that is the whole reason it exists, and it is why phase 2 sized
its door at 78 × 20.5 m: a 787-9 needs 60.1 m of span and 17 m of fin through
it. So the aeroplane is not a choice, it is the building's specification made
visible. Measured on the model actually used here (`boeing 787-9/B789_LATAM.blend`):

    span      60.12 m   in a 78.0 m door   ->  8.94 m of tip clearance each side
    fin top   17.02 m   in a 20.5 m door   ->  3.48 m under the lintel
                        (the geometry-truth round of 2026-08-27 lengthened the
                        legs: WHEEL_Z -4.88 -> -5.42, and the fin now rides at
                        the published 17.02 m height)
    length    62.85 m   in a 95 m hangar
    wheelbase 25.83 m   nose gear 5.41 m aft of the nose

**The clip runs on the MRO platform, 35 m BELOW the runway.** Every height in
this file is measured off Z_MRO_PLATFORM = −37.10, never off z = 0. Phase 2's
warning is exact: a camera at "runway eye height" over here is 35 m in the air.

FOUR THINGS THE SHARED SCENERY DOES NOT HAVE, BUILT LOCALLY IN THIS FILE
========================================================================
The field file is background scenery seen from 0.8–1.9 km, and at that range
hangar 9's door is correctly a dark rectangle *painted on a solid wall* — the
build makes it as a 1.6 m thick box of `SDSC_HangarInterior` across the opening.
An aeroplane cannot be towed through that. So this script, **in its own output
file and never in `sdsc_field.blend`**, replaces four things:

1. **A real opening.** The gable shell is rebuilt as walls with a 78 × 20.5 m
   hole in the north face, plus a header beam and the parked door leaves
   stacked in the jamb pockets either side. Single-sided quads: Blender renders
   both faces, so the same geometry is the inside of the hangar.
2. **A floor and a lit interior.** The existing `SDSC_Hangar9_Floor` is only as
   wide as the door; it is rebuilt to the full 128 × 93 m bay. The red space
   frame phase 2 built is kept exactly as it is — it is the one interior fact
   the photographs give unambiguously — and six high-bay light lines are hung
   under it. **They are needed, not decorative:** the door faces NORTH and the
   shipped sun is at azimuth 274.46°, so no direct sunlight enters this door at
   any hour of the shipped rig. Without lamps the interior is a black slot and
   nothing phase 2 built behind the door is visible at all.
3. **A fascia band that is not hanging in mid-air.** `build_scenery` draws the
   indigo band as one plane across the whole 130 m north face, which is right
   for a solid wall and wrong the moment the door is a hole: 3.1 m of the 4 m
   band spans the opening with nothing behind it. Here it becomes two panels
   flanking the door — the same treatment `build_mro_frontage` already gives the
   hangar line, "one run on each face that really exists" — and the LATAM lockup
   moves onto the eastern panel, which is the one inside this camera's frame for
   all 400 frames.
4. **The stand is cleared.** Hangar 9's stand is where the towed aeroplane has
   to be, so nothing is parked on it: `fleet_placement.populate(skip=("H9",))`
   is how this clip says so, and it is one argument rather than a special case.
   Everything else on that ramp — the nine other stands, eight real masters,
   the heavy-check states — comes from the same call. Phase 4's `SDSC_AC_H9`
   proxy is not built any more and its deletion below is left in as a no-op for
   an older field file. This is also why the script opens `sdsc_field.blend`
   directly instead of linking it: re-running the script IS the propagation,
   and the shared asset is left untouched.

   **The towed 787-9 is still APPENDED here, not instanced**, and that is the
   one place this file departs from the module: the tow needs `TremNariz*`
   re-parented to a steering empty so the nose gear tracks the towbar, and you
   cannot re-parent inside a collection instance. One aircraft's worth of
   unique geometry, for the one aircraft the clip is about.

   While a camera was finally close enough to read that lockup it turned out to
   be **mirrored** — `place_wordmark` lays it out along world +X × `facing` and
   a north-facing wall needs −1, not +1. That one IS a defect in the shared
   build and was fixed there; `sdsc_field.blend` was rebuilt.

HOW THE TOW IS SOLVED — a tractrix, not a slide
================================================
The thing that separates a tow from an aeroplane sliding along a spline is that
**the aeroplane does not follow the nose gear's path.** The nose gear is dragged
along a curve; the main gear follows on a taut 25.83 m link and cuts the corner;
the fuselage lies along the line between them and the tail swings OUTSIDE the
turn. That is a tractrix, and it is two lines of integration:

    N' = the nose-gear path point at this frame
    M' = N' − W·(N' − M)/|N' − M|          (M = main-gear midpoint, W = wheelbase)
    heading = bearing from M' to N'

**AND IT IS SOLVED BACKWARDS.** Driving that tractrix forward from a
"turn then straight" nose-gear path was the first attempt and it is wrong, for a
reason worth keeping: a trailer needs three or four wheelbases to settle, and
after the 19 m of straight this hangar allows, the fuselage was still **9.3° off
square** with one wingtip at 4.0 m of clearance against the other's 14.7. So the
AEROPLANE's heading is the control curve here, its main gear integrates along
it, and the nose gear is *derived* at N = M + W·(sin h, cos h). The tug follows
N. That guarantees square-to-the-door at the last frame — 8.94 m of tip
clearance on both sides, not one — and it produces the nose-wheel steering for
free, because the steering angle is just atan(W·dh/ds): the wheels swing out to
start the turn and come back to centre to stop it.

Measured on the shipped path: the main gear tracks **3.65 m** inside the
nose-gear line and the tail swings **5.01 m** outside it. That lateral
difference IS the tow, and it is exactly what is missing when an aeroplane is
keyframed as a rigid body sliding along a curve.

The eight `TremNariz_*` parts are re-parented to an empty on the strut axis so
the nose wheels can actually turn through their **18.84°**. It is a two-degree
detail that costs ten lines.

THE PATH
--------
Heading 197° → **180.0°**, eased to a stop by frame 304; **180.0 and not the
runway's 181.026** because hangar 9 is built axis-aligned to the scene, not to
the runway track, so square to this door is due south. Speed 3.4 m/s (12 km/h)
on the apron easing to 1.0 m/s (3.6 km/h) over the threshold, 42 m in 16 s. That
is a real tow speed and it is the reason this clip is 400 frames where the other
two are 240: **a 787 does not enter a hangar in 9.6 seconds, and speeding it up
would be the one lie the shot cannot afford.**

What that buys, in order: the tug and towbar plainly outside for the opening
fifth; the tug into the dark at frame 85 (21%); the nose across the door plane
at frame 115 (29%); and at frame 400 the wingtips sitting in the 78 m opening at
x 719.9 and 780.1, 8.94 m of clearance on each side. What it does not buy is the
fin passing under the lintel — the fin is 55 m behind the nose, which is 22 more
seconds of tow, and no framing recovers it. Stated rather than shown: 17.02 m of
fin in a 20.5 m door is 3.48 m.

THE CAMERA
----------
One continuous push, 58 m in 16 s (3.6 m/s), from 30 m above the platform down
to 17 m, with a travelling aim that walks from the aeroplane on the apron to
the door mouth. Fixed 35 mm — the closing distance does the widening, so there
is no lens gain riding on the pan. It sits **north-west** of the door, inside
the perimeter wall, which is the one quadrant that satisfies all three
constraints at once: north of the door plane (or you cannot see in), west of
the aeroplane (or you see its shaded side), and with the 274° sun behind the
right shoulder rather than in the lens.

**Slow shots fail differently.** The risk is not disorientation, it is stepping
— a move this gentle shows every quantisation in the curves. So the path is
PCHIP, not a smoothstep chain (zero derivative at every knot would read as the
camera stopping six times), every f-curve is baked per frame and set LINEAR, and
the offline report below prints the *minimum* screen flow as well as the maximum.

Measured in the scene by `../scenario/camera_metrics.py --pivot B789_Tow`:
central-band screen flow **median 0.011, max 0.017 w/s**, worst single probe
0.036, body ratio 2.0, 0 aim reversals, aeroplane edge margin 12.5%. The nearest
scenery in frame is a **floodlight mast at 59 m** on hangar 9's own apron — the
one piece of thin geometry close enough to matter — and at 3 m/s it steps 1.9 px
per frame against a 12.1 px shaft, so the coupling that made Santiago's masts
strobe (thin geometry stepping 68 px behind a 10 px shutter) cannot arise here.
It sits at u 0.93, outside the doorway, and is foreground depth rather than an
obstruction.

REJECTED
--------
* **A camera inside the hangar looking out.** The most dramatic version and the
  best for scale — the door frames the aeroplane — but it throws away the tug,
  the curve and the base beyond, and it makes a silhouette of a white aeroplane
  against a blown-out apron.
* **Towing tail-first.** It would put the fin under the lintel, which is the one
  scale moment this shot cannot otherwise reach. Rejected because phase 2 parks
  its hangar-9 proxy nose-in and because a towbar tug pulling forward is what a
  driver can see out of; the fin is given as a number instead.
* **Changing the hour so sunlight falls into the door.** A north-facing door at
  latitude −21.88 is only lit either side of noon (14:00 on the same date is
  55°/301.5°, and light would reach 14 m in). Rejected: it would put this clip
  on a different light rig from the other two for a detail the hangar's own
  lamps do better.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import shot_common as S                                       # noqa: E402
import fleet_placement as F                                   # noqa: E402

B789 = os.path.join(ROOT, "boeing 787-9", "B789_LATAM.blend")
TERRAIN = os.path.join(HERE, "sdsc_terrain.blend")

FRAME_END = 400                      # 16.0 s at 25 fps
BASE = S.Z_MRO_PLATFORM              # -37.10, and everything here hangs off it
APRON_Z = BASE + S.Z_APRON           # -37.05, wheels and tug tyres

# --- hangar 9, as build_scenery.py has it -----------------------------------
H9 = dict(x0=685.0, x1=815.0, y0=1590.0, y1=1685.0,
          eave=22.0, ridge=26.0, door_w=78.0, door_h=20.5)
DOOR_X = 0.5 * (H9["x0"] + H9["x1"])          # 750.0
DOOR_Y = H9["y1"]                             # 1685.0, the north face
DOOR_HALF = H9["door_w"] * 0.5                # 39.0

# --- the aeroplane, measured off B789_LATAM.blend ---------------------------
AC_NOSE_X = 0.0             # model local: nose at x=0, tail at x=+62.85
AC_TAIL_X = 62.85
NOSE_GEAR_X = 5.41
MAIN_GEAR_X = 31.24
WHEEL_Z = -5.42        # re-measured 2026-08-27 after trem_787.py's leg fix
FIN_TOP_Z = 11.60
SPAN = 60.12
WHEELBASE = MAIN_GEAR_X - NOSE_GEAR_X         # 25.83

# --- the tow path -----------------------------------------------------------
# SOLVED FROM THE AEROPLANE, NOT FROM THE NOSE GEAR, and that inversion is the
# whole correctness of the clip. Driving a tractrix off a "turn then straight"
# nose-gear path was the first attempt and it is WRONG: a trailer needs three or
# four wheelbases to settle, so after the 19 m of straight this hangar allows,
# the fuselage was still 9.3 deg off square and one wingtip had 4.0 m of
# clearance against the other's 14.7. Measured, not guessed - it is in the git
# history of this file.
#
# So the AEROPLANE's heading is the control curve, its main gear integrates
# along it, and the nose gear is derived at N = M + W*(sin h, cos h). The tug
# then follows N. That guarantees square-to-the-door at the last frame, and it
# produces the counter-steer for free: the nose wheels swing one way to start
# the turn and back the other way to stop it, exactly as a tug driver does it,
# because the steering angle IS atan(W * dh/ds).
NG_END = (750.0, 1664.0)      # where the nose gear stops, 21 m inside the door
HEADING = [(1, 197.0), (60, 194.0), (130, 187.5), (200, 182.0),
           (260, 180.3), (330, 180.0), (400, 180.0)]
TRAVEL = 42.0                 # metres of main-gear path in the clip

# Ground speed, m/s. 3.4 = 12 km/h on the apron; 1.0 = 3.6 km/h over the
# threshold. Normalised below so the integral is exactly TRAVEL.
SPEED = [(1, 3.40), (120, 3.15), (250, 2.35), (330, 1.45), (400, 1.00)]

# --- the tug ----------------------------------------------------------------
TOWBAR_L = 6.0               # hitch to nose gear
TUG_L, TUG_W, TUG_H = 7.5, 3.0, 1.45

# --- the camera -------------------------------------------------------------
CAM0 = (630.0, 1812.0, BASE + 30.0)
CAM1 = (676.0, 1778.0, BASE + 17.0)
AIM0 = (742.0, 1712.0, BASE + 7.0)
AIM1 = (751.0, 1681.0, BASE + 8.0)
LENS = 35.0
TILT_UP = math.radians(2.6)   # puts the aim point at v ~ 0.43
# One metre of drift, because a 16-second locked-off push is the one thing that
# looks like CG. Periods chosen so neither completes a cycle in the clip.
DRIFT = ((0.9, 11.0, 0.4), (0.5, 8.0, 2.3))    # amplitude m, period s, phase


# ---------------------------------------------------------------------------
# the path
# ---------------------------------------------------------------------------
def arclengths():
    """Cumulative main-gear arc length per frame, normalised to TRAVEL."""
    raw, acc = [0.0], 0.0
    for f in range(2, FRAME_END + 1):
        acc += S.piecewise(f - 0.5, SPEED) / S.FPS
        raw.append(acc)
    k = TRAVEL / raw[-1]
    return [x * k for x in raw], [S.piecewise(f, SPEED) * k
                                  for f in range(1, FRAME_END + 1)]


class Polyline:
    """Arc-length sampler over a polyline, extrapolating past both ends.

    The tug is 6 m AHEAD of the nose gear, which at the last frame is already
    inside the hangar, so the sampler has to keep going past the end of the
    solved track rather than clamping - a clamp would park the tug for the last
    two seconds while the aeroplane kept moving, which is a towbar under
    compression.
    """

    def __init__(self, pts):
        self.p = list(pts)
        self.s = [0.0]
        for a, b in zip(self.p, self.p[1:]):
            self.s.append(self.s[-1] + math.dist(a, b))

    def at(self, s):
        if s <= self.s[0]:
            return self._extrap(self.p[0], self.p[1], s - self.s[0])
        if s >= self.s[-1]:
            return self._extrap(self.p[-2], self.p[-1], s - self.s[-1])
        for i in range(len(self.s) - 1):
            if s <= self.s[i + 1]:
                t = (s - self.s[i]) / (self.s[i + 1] - self.s[i])
                a, b = self.p[i], self.p[i + 1]
                return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        return self.p[-1]

    @staticmethod
    def _extrap(a, b, d):
        """a -> b is the FORWARD direction; d is signed along it from the end
        that owns it (b for the far end, a for the near end)."""
        L = math.dist(a, b) or 1.0
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        o = a if d < 0 else b
        return (o[0] + ux * d, o[1] + uy * d)

    def offset(self, q):
        """Signed-magnitude lateral distance from q to the nearest point on the
        polyline: how far a following wheel tracks off the leader's line."""
        best = 1e9
        for a, b in zip(self.p, self.p[1:]):
            vx, vy = b[0] - a[0], b[1] - a[1]
            L2 = vx * vx + vy * vy or 1.0
            t = max(0.0, min(1.0, ((q[0] - a[0]) * vx
                                   + (q[1] - a[1]) * vy) / L2))
            d = math.dist(q, (a[0] + vx * t, a[1] + vy * t))
            best = min(best, d)
        return best

    def heading(self, s):
        a = self.at(s - 0.25)
        b = self.at(s + 0.25)
        return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))


def solve_tow():
    """Per-frame main gear, nose gear, heading and nose-wheel steering."""
    s, speed = arclengths()
    mg, x, y = [], 0.0, 0.0
    for f in range(FRAME_END):
        if f:
            h = math.radians(S.piecewise(f + 0.5, HEADING))
            ds = s[f] - s[f - 1]
            x += ds * math.sin(h)
            y += ds * math.cos(h)
        mg.append((x, y))
    ng = []
    for f in range(FRAME_END):
        h = math.radians(S.piecewise(f + 1, HEADING))
        ng.append((mg[f][0] + WHEELBASE * math.sin(h),
                   mg[f][1] + WHEELBASE * math.cos(h)))
    dx, dy = NG_END[0] - ng[-1][0], NG_END[1] - ng[-1][1]
    mg = [(p[0] + dx, p[1] + dy) for p in mg]
    ng = [(p[0] + dx, p[1] + dy) for p in ng]

    track = Polyline(ng)
    # the same track extended 120 m backwards, only for the off-tracking
    # measurement: at frame 1 the tail is 57 m behind the nose gear, i.e. off
    # the end of the solved polyline, and measuring against a clamped end
    # returns the wheelbase instead of the lateral error.
    meas = Polyline([track.at(-120.0), track.at(-60.0)] + ng)
    rows = []
    for f in range(FRAME_END):
        head = S.piecewise(f + 1, HEADING)
        ph = track.heading(track.s[f])
        rows.append(dict(f=f + 1, s=s[f], v=speed[f], ng=ng[f], mg=mg[f],
                         head=head, path_head=ph,
                         steer=(ph - head + 540) % 360 - 180,
                         track=track, meas=meas))
    return rows


def tug_pose(row):
    """Hitch, centre and heading of the towbar tug, ahead on the nose-gear track."""
    t = row["track"]
    s = t.s[row["f"] - 1]
    hitch = t.at(s + TOWBAR_L)
    centre = t.at(s + TOWBAR_L + TUG_L * 0.5)
    return hitch, centre, t.heading(s + TOWBAR_L + TUG_L * 0.5)


def nose_xy(row):
    h = math.radians(row["head"])
    return (row["ng"][0] + (NOSE_GEAR_X - AC_NOSE_X) * math.sin(h),
            row["ng"][1] + (NOSE_GEAR_X - AC_NOSE_X) * math.cos(h))


def tail_xy(row):
    h = math.radians(row["head"])
    return (row["mg"][0] - (AC_TAIL_X - MAIN_GEAR_X) * math.sin(h),
            row["mg"][1] - (AC_TAIL_X - MAIN_GEAR_X) * math.cos(h))


# ---------------------------------------------------------------------------
# the camera
# ---------------------------------------------------------------------------
def camera_rows(tow):
    rows = []
    for f in range(1, FRAME_END + 1):
        t = (f - 1) / float(FRAME_END - 1)
        u = S._smoothstep(t) * 0.20 + t * 0.80       # gentle ease, mostly linear
        cam = [a + (b - a) * u for a, b in zip(CAM0, CAM1)]
        aim = [a + (b - a) * u for a, b in zip(AIM0, AIM1)]
        tt = f / S.FPS
        cam[0] += DRIFT[0][0] * math.sin(2 * math.pi * tt / DRIFT[0][1]
                                         + DRIFT[0][2])
        cam[2] += DRIFT[1][0] * math.sin(2 * math.pi * tt / DRIFT[1][1]
                                         + DRIFT[1][2])
        dx, dy = aim[0] - cam[0], aim[1] - cam[1]
        horiz = math.hypot(dx, dy)
        rows.append(dict(f=f, cam=tuple(cam), aim=tuple(aim),
                         az=math.atan2(dx, dy),
                         el=math.atan2(aim[2] - cam[2], horiz) + TILT_UP,
                         lens=LENS, dist=horiz))
    for key in ("az", "el"):
        for r, x in zip(rows, S.gaussian_smooth([r[key] for r in rows], 4.0)):
            r[key] = x
    return rows


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------
def door_corners():
    return dict(
        door_wjamb=(DOOR_X - DOOR_HALF, DOOR_Y, BASE + H9["door_h"]),
        door_ejamb=(DOOR_X + DOOR_HALF, DOOR_Y, BASE + H9["door_h"]),
        door_sill_w=(DOOR_X - DOOR_HALF, DOOR_Y, BASE),
        h9_ridge=(DOOR_X, 1637.5, BASE + H9["ridge"]),
        mro_bay=(931.0, 1810.0, BASE + 17.5),
    )


def report(tow, cams):
    print("\n%-5s %6s %7s %9s %9s %8s %7s %7s %8s %8s"
          % ("frame", "m/s", "path_m", "nose_y", "tail_y", "head", "steer",
             "cam_z", "cam_d", "note"))
    for t, c in zip(tow, cams):
        if t["f"] % 40 and t["f"] not in (1, FRAME_END):
            continue
        ny = nose_xy(t)[1]
        note = ("nose INSIDE" if ny < DOOR_Y else
                "tug inside" if tug_pose(t)[1][1] < DOOR_Y else "")
        print("%-5d %6.2f %7.1f %9.1f %9.1f %8.2f %7.2f %8.1f %8.0f  %s"
              % (t["f"], t["v"], t["s"], ny, tail_xy(t)[1], t["head"] % 360.0,
                 t["steer"], c["cam"][2], math.dist(c["cam"], (t["ng"][0],
                                                               t["ng"][1],
                                                               APRON_Z)), note))

    # what makes a tow a tow: the three tracks do not coincide
    meas = tow[0]["meas"]
    off_m = max(meas.offset(t["mg"]) for t in tow)
    off_t = max(meas.offset(tail_xy(t)) for t in tow)
    print("\noff-tracking against the nose-gear line: main gear up to %.2f m, "
          "tail up to %.2f m" % (off_m, off_t))
    print("nose-wheel steering %.2f .. %.2f deg - out to start the turn, back "
          "to centre to stop it (steer = atan(W*dh/ds))"
          % (min(t["steer"] for t in tow), max(t["steer"] for t in tow)))
    print("heading %.2f -> %.2f deg; square to the door (180.00) from frame %d"
          % (tow[0]["head"], tow[-1]["head"],
             next(t["f"] for t in tow if abs(t["head"] - 180.0) < 0.05)))

    ev = [t for t in tow if tug_pose(t)[1][1] < DOOR_Y]  # tug centre
    en = [t for t in tow if nose_xy(t)[1] < DOOR_Y]
    print("tug crosses the door plane at frame %s (%.0f%%), "
          "the nose at frame %s (%.0f%%)"
          % (ev[0]["f"] if ev else "-", 100 * ev[0]["f"] / FRAME_END if ev else 0,
             en[0]["f"] if en else "-",
             100 * en[0]["f"] / FRAME_END if en else 0))

    last = tow[-1]
    h = math.radians(last["head"])
    # wingtips: mid-chord is ~28 m aft of the nose on this model
    wc = (nose_xy(last)[0] + 28.0 * math.sin(h),
          nose_xy(last)[1] + 28.0 * math.cos(h))
    px, py = math.cos(h), -math.sin(h)
    tips = [(wc[0] + sgn * 0.5 * SPAN * px, wc[1] + sgn * 0.5 * SPAN * py)
            for sgn in (-1, 1)]
    xw, xe = min(t[0] for t in tips), max(t[0] for t in tips)
    print("at frame %d the wingtips are at x %.1f and %.1f in an opening "
          "x %.1f..%.1f  -> %.2f m west and %.2f m east of clearance"
          % (FRAME_END, xw, xe, DOOR_X - DOOR_HALF, DOOR_X + DOOR_HALF,
             xw - (DOOR_X - DOOR_HALF), (DOOR_X + DOOR_HALF) - xe))
    print("fin top %.2f m over the floor in a %.1f m door -> %.2f m under "
          "the lintel (NOT reached in this clip: the fin ends %.0f m short)"
          % (FIN_TOP_Z - WHEEL_Z, H9["door_h"],
             H9["door_h"] - (FIN_TOP_Z - WHEEL_Z),
             (nose_xy(last)[1] + 55.0) - DOOR_Y))

    S.flow_report(cams, "SDSC hangar-9 tow")
    flows = []
    for a, b in zip(cams, cams[1:]):
        d = math.hypot(b["az"] - a["az"], b["el"] - a["el"]) * S.FPS
        flows.append(d / S.hfov(LENS))
    print("slow-shot check: flow MIN %.4f w/s (a slow move fails by stepping, "
          "not by speed)" % min(flows))

    print("\n%-5s %s" % ("frame", " ".join("%13s" % k for k in door_corners())))
    for c in cams:
        if c["f"] % 80 and c["f"] not in (1, FRAME_END):
            continue
        cells = []
        for k, p in door_corners().items():
            u, v, _ = S.project(c["cam"], c["az"], c["el"], c["lens"], p)
            cells.append("%5.2f,%5.2f%s" % (u, v, " " if 0 <= u <= 1
                                            and 0 <= v <= 1 else "*"))
        print("%-5d %s" % (c["f"], " ".join("%13s" % x for x in cells)))
    print("       (u, v; * = outside the frame)")


def lateral_in_door(row):
    """How far the fuselage centreline is off the door centreline, at the door."""
    return abs(row["ng"][0] - DOOR_X)


# ---------------------------------------------------------------------------
# Blender side
# ---------------------------------------------------------------------------
def main():
    import bpy
    import bmesh
    from mathutils import Matrix

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(HERE, "sdsc_hangar_tow.blend")
    scn = bpy.context.scene
    M = {m.name: m for m in bpy.data.materials}

    def mat(n):
        if n not in M:
            raise SystemExit("material %s missing - is this sdsc_field.blend?" % n)
        return M[n]

    def coll(name):
        c = bpy.data.collections.get(name)
        if c is None:
            c = bpy.data.collections.new(name)
            scn.collection.children.link(c)
        return c

    tow_coll = coll("SDSC_Tow")

    def put(bm, name, material, collection=None, roof=None):
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(material)
        if roof is not None:
            me.materials.append(roof)
            for p in me.polygons:
                if p.normal.z > 0.55:
                    p.material_index = 1
        ob = bpy.data.objects.new(name, me)
        (collection or tow_coll).objects.link(ob)
        return ob

    def quad(bm, a, b, z0, z1):
        v = [bm.verts.new(p) for p in ((a[0], a[1], z0), (b[0], b[1], z0),
                                       (b[0], b[1], z1), (a[0], a[1], z1))]
        try:
            bm.faces.new(v)
        except ValueError:
            pass

    def box(bm, x0, x1, y0, y1, z0, z1):
        v = [bm.verts.new(p) for p in
             ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
              (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        for f in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
                  (4, 5, 6, 7), (0, 3, 2, 1)):
            try:
                bm.faces.new([v[i] for i in f])
            except ValueError:
                pass

    # ---- 1. the ramp, the stand and the painted-on door --------------------
    # Every stand but hangar 9's, which is where the towed aeroplane goes.
    F.populate(scn, skip=("H9",))
    for nm in ("SDSC_AC_H9", "SDSC_ACFin_H9", "SDSC_Hangar9",
               "SDSC_Hangar9_Door", "SDSC_Hangar9_Floor",
               "SDSC_Hangar9_Band"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
            print("removed", nm)

    # ---- 2. hangar 9 with a real opening -----------------------------------
    x0, x1, y0, y1 = H9["x0"], H9["x1"], H9["y0"], H9["y1"]
    ev, rd, dh = BASE + H9["eave"], BASE + H9["ridge"], BASE + H9["door_h"]
    jw, je = DOOR_X - DOOR_HALF, DOOR_X + DOOR_HALF        # 711, 789
    ym = 0.5 * (y0 + y1)
    bm = bmesh.new()
    quad(bm, (x0, y0), (x1, y0), BASE, ev)                 # south wall
    quad(bm, (x0, y0), (x0, y1), BASE, ev)                 # west wall
    quad(bm, (x1, y0), (x1, y1), BASE, ev)                 # east wall
    quad(bm, (x0, y1), (jw, y1), BASE, ev)                 # north, west of door
    quad(bm, (je, y1), (x1, y1), BASE, ev)                 # north, east of door
    quad(bm, (jw, y1), (je, y1), dh, ev)                   # the header over it
    for (ya, yb) in ((y0, ym), (ym, y1)):                  # the two roof planes
        za = rd if ya == ym else ev
        zb = rd if yb == ym else ev
        v = [bm.verts.new(p) for p in ((x0, ya, za), (x1, ya, za),
                                       (x1, yb, zb), (x0, yb, zb))]
        bm.faces.new(v)
    for x in (x0, x1):                                     # the gable ends
        v = [bm.verts.new(p) for p in ((x, y0, ev), (x, ym, rd), (x, y1, ev))]
        bm.faces.new(v)
    ob = put(bm, "SDSC_Hangar9_Shell", mat("SDSC_Cladding"),
             roof=mat("SDSC_RoofPale"))
    ob["inference"] = ("hangar 9 is declared inference (build_scenery.py); the "
                       "opening, the door pockets and the lamps are this "
                       "clip's, not the shared asset's")

    bm = bmesh.new()                                       # the floor slab
    v = [bm.verts.new(p) for p in ((x0 + 1, y0 + 1, APRON_Z),
                                   (x1 - 1, y0 + 1, APRON_Z),
                                   (x1 - 1, y1 - 1, APRON_Z),
                                   (x0 + 1, y1 - 1, APRON_Z))]
    bm.faces.new(v)
    put(bm, "SDSC_Hangar9_Floor", mat("SDSC_HangarFloor"))

    # The fascia band, CLIPPED TO THE WALL. build_scenery draws it as one plane
    # across the whole 130 m north face, which is right for a solid wall seen
    # from 1 km and wrong the moment the door is a real hole: 3.1 m of the 4 m
    # band hangs across the opening with nothing behind it, and from any angle
    # off the normal it reads as a banner strung in mid-air. Here it becomes two
    # panels flanking the door - the same treatment `build_mro_frontage` already
    # gives the hangar line, "one run on each face that really exists".
    band_z0, band_z1 = BASE + H9["eave"] - 4.6, BASE + H9["eave"] - 0.6
    bm = bmesh.new()
    for (a, b) in ((x0, jw), (je, x1)):
        quad(bm, (a, y1 + 0.5), (b, y1 + 0.5), band_z0, band_z1)
    put(bm, "SDSC_Hangar9_Band", mat("SDSC_FasciaBand"))
    # and the lockup moves with it, onto the EASTERN panel: 16.4 m of lockup on
    # a 26 m panel. It was centred on the door, which is now air. East and not
    # west because this camera swings toward the door as it pushes in, and the
    # western panel leaves the frame by the last second while the eastern one
    # is inside it from frame 1 to frame 400.
    for nm in ("SDSC_Hangar9_Wordmark", "SDSC_Hangar9_Brandmark"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            ob.location.x = 0.5 * (je + x1) - DOOR_X

    bm = bmesh.new()                                       # door leaves, parked
    for (a, b) in ((x0, jw), (je, x1)):
        n = 5
        for k in range(n):
            xa = a + (b - a) * k / n
            xb = a + (b - a) * (k + 1) / n
            box(bm, xa + 0.15, xb - 0.15, y1 + 0.10 + 0.34 * k,
                y1 + 0.42 + 0.34 * k, BASE + 0.05, dh)
    box(bm, jw - 0.6, je + 0.6, y1 - 0.35, y1 + 2.0, dh, dh + 1.15)  # the track
    put(bm, "SDSC_Hangar9_DoorLeaves", mat("SDSC_Cladding"))

    # ---- 3. the lamps. A north-facing door gets no sun from a 274 deg sun --
    lamp_z = BASE + 17.6
    bm = bmesh.new()
    for k in range(6):
        yl = y0 + 8.0 + k * 14.5
        box(bm, DOOR_X - 30.0, DOOR_X + 30.0, yl - 0.9, yl + 0.9,
            lamp_z, lamp_z + 0.35)
    put(bm, "SDSC_Hangar9_HighBays", _emissive(bpy, "SDSC_HighBay", 4.0))
    for k in range(3):
        ld = bpy.data.lights.new("SDSC_H9_Fill%d" % k, "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = 58.0, 22.0
        # ~2 W/m2 on the floor - an interior, and clearly dimmer than the
        # sunlit apron outside it. Tuned by render: the first pass ran three
        # 26 kW lights plus emissive strips at 24, about 8 W/m2, and blew the
        # whole bay to white.
        ld.energy = 6000.0
        lo = bpy.data.objects.new("SDSC_H9_Fill%d" % k, ld)
        lo.location = (DOOR_X, y0 + 18.0 + k * 28.0, lamp_z - 0.6)
        tow_coll.objects.link(lo)       # an AREA light already emits along -Z

    # ---- 4. the aeroplane --------------------------------------------------
    with bpy.data.libraries.load(B789, link=False) as (src, dst):
        dst.collections = [c for c in src.collections
                           if c in ("01_Estrutura", "02_Motores", "03_Trem",
                                    "04_Detalhes")]
    ac_objs = []
    for c in dst.collections:
        if c is None:
            continue
        scn.collection.children.link(c)
        ac_objs.extend(c.all_objects)
    rig = bpy.data.objects.new("B789_Tow", None)
    rig.empty_display_type = "ARROWS"
    rig.empty_display_size = 8.0
    tow_coll.objects.link(rig)
    ng_rig = bpy.data.objects.new("B789_NoseGear", None)
    ng_rig.empty_display_size = 3.0
    tow_coll.objects.link(ng_rig)
    ng_rig.parent = rig
    ng_rig.location = (NOSE_GEAR_X, 0.0, 0.0)
    for ob in ac_objs:
        if ob.parent is not None:
            continue
        if ob.name.startswith("TremNariz"):
            # keep the world pose: world = parent.matrix @ mpi @ basis, and the
            # parent is a pure translation of NOSE_GEAR_X down local +X
            ob.parent = ng_rig
            ob.matrix_parent_inverse = Matrix.Translation(
                (-NOSE_GEAR_X, 0.0, 0.0))
        else:
            ob.parent = rig
            ob.matrix_parent_inverse.identity()
    print("787-9 parts parented:", len(ac_objs))

    # ---- 5. the tug and the towbar -----------------------------------------
    tug = bpy.data.objects.new("SDSC_Tug", None)
    tug.empty_display_size = 3.0
    tow_coll.objects.link(tug)
    bm = bmesh.new()
    box(bm, -TUG_L * 0.5, TUG_L * 0.5, -TUG_W * 0.5, TUG_W * 0.5, 0.42,
        0.42 + TUG_H)
    put(bm, "SDSC_Tug_Body", _flat(bpy, "SDSC_TugYellow",
                                   (0.480, 0.330, 0.030))).parent = tug
    bm = bmesh.new()
    box(bm, -TUG_L * 0.5 + 0.4, -TUG_L * 0.5 + 2.9, -TUG_W * 0.5 + 0.2,
        TUG_W * 0.5 - 0.2, 0.42 + TUG_H, 0.42 + TUG_H + 1.30)
    put(bm, "SDSC_Tug_Cab", _flat(bpy, "SDSC_TugWhite",
                                  (0.560, 0.562, 0.560))).parent = tug
    bm = bmesh.new()
    box(bm, -TUG_L * 0.5 + 0.55, -TUG_L * 0.5 + 2.75, -TUG_W * 0.5 + 0.34,
        TUG_W * 0.5 - 0.34, 0.42 + TUG_H + 0.30, 0.42 + TUG_H + 1.20)
    put(bm, "SDSC_Tug_Glass", mat("SDSC_Glass")).parent = tug
    bm = bmesh.new()
    for sx in (-2.4, 2.4):
        for sy in (-1, 1):
            box(bm, sx - 0.62, sx + 0.62, sy * (TUG_W * 0.5 - 0.16) - 0.22,
                sy * (TUG_W * 0.5 - 0.16) + 0.22, 0.0, 1.24)
    put(bm, "SDSC_Tug_Wheels", mat("SDSC_MeshFence")).parent = tug
    bm = bmesh.new()
    box(bm, -TUG_L * 0.5 + 1.4, -TUG_L * 0.5 + 2.0, -0.28, 0.28,
        0.42 + TUG_H + 1.30, 0.42 + TUG_H + 1.72)
    put(bm, "SDSC_Tug_Beacon", _emissive(bpy, "SDSC_Beacon", 12.0,
                                         (1.0, 0.32, 0.02))).parent = tug

    bar = bpy.data.objects.new("SDSC_Towbar", None)
    bar.empty_display_size = 2.0
    tow_coll.objects.link(bar)
    bm = bmesh.new()
    box(bm, 0.0, TOWBAR_L, -0.16, 0.16, 0.38, 0.70)
    box(bm, TOWBAR_L - 0.9, TOWBAR_L + 0.25, -0.55, 0.55, 0.30, 0.86)
    put(bm, "SDSC_Towbar_Mesh", _flat(bpy, "SDSC_TowbarGrey",
                                      (0.150, 0.152, 0.150))).parent = bar

    # ---- 6. animate --------------------------------------------------------
    tow = solve_tow()
    cams = camera_rows(tow)
    report(tow, cams)

    for t in tow:
        f = t["f"]
        h = math.radians(t["head"])
        theta = math.atan2(-math.cos(h), -math.sin(h))     # nose is local -X
        c = (MAIN_GEAR_X, 0.0, WHEEL_Z)
        cx = c[0] * math.cos(theta) - c[1] * math.sin(theta)
        cy = c[0] * math.sin(theta) + c[1] * math.cos(theta)
        rig.location = (t["mg"][0] - cx, t["mg"][1] - cy, APRON_Z - c[2])
        rig.rotation_euler = (0.0, 0.0, theta)
        rig.keyframe_insert("location", frame=f)
        rig.keyframe_insert("rotation_euler", frame=f)
        ng_rig.rotation_euler = (0.0, 0.0, -math.radians(t["steer"]))
        ng_rig.keyframe_insert("rotation_euler", frame=f)

        hitch, tc, th = tug_pose(t)
        tug.location = (tc[0], tc[1], APRON_Z)
        tug.rotation_euler = (0.0, 0.0,
                              math.atan2(-math.cos(math.radians(th)),
                                         -math.sin(math.radians(th))))
        tug.keyframe_insert("location", frame=f)
        tug.keyframe_insert("rotation_euler", frame=f)
        # the towbar spans hitch -> nose gear; its local +X runs along it
        dx, dy = t["ng"][0] - hitch[0], t["ng"][1] - hitch[1]
        bar.location = (hitch[0], hitch[1], APRON_Z)
        bar.rotation_euler = (0.0, 0.0, math.atan2(dy, dx))
        bar.keyframe_insert("location", frame=f)
        bar.keyframe_insert("rotation_euler", frame=f)

    cd = bpy.data.cameras.new("CamTow")
    cd.lens = LENS
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = S.SENSOR
    cd.clip_start = 0.5
    cd.clip_end = 250000.0
    cam = bpy.data.objects.new("CamTow", cd)
    tow_coll.objects.link(cam)
    for c in cams:
        cam.location = c["cam"]
        cam.rotation_euler = (math.pi / 2.0 + c["el"], 0.0, -c["az"])
        cam.keyframe_insert("location", frame=c["f"])
        cam.keyframe_insert("rotation_euler", frame=c["f"])

    _linearise(bpy, (rig, ng_rig, tug, bar, cam))

    # ---- 7. terrain, render settings, save ---------------------------------
    if os.path.exists(TERRAIN) and "SDSC_Terrain" not in bpy.data.collections:
        with bpy.data.libraries.load(TERRAIN, link=True) as (src, dst2):
            dst2.collections = [c for c in src.collections
                                if c == "SDSC_Terrain"]
        for c in dst2.collections:
            if c is None:
                continue
            ob = bpy.data.objects.new("SDSC_Terrain_Link", None)
            ob.instance_type = "COLLECTION"
            ob.instance_collection = c
            scn.collection.objects.link(ob)

    scn.camera = cam
    scn.render.fps = 25
    scn.render.fps_base = 1.0
    scn.frame_start, scn.frame_end = 1, FRAME_END
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 128            # an interior; more light paths to find
    scn.cycles.use_denoising = True
    scn.cycles.max_bounces = 6
    scn.render.resolution_x, scn.render.resolution_y = 960, 540
    scn.render.use_motion_blur = True
    # 180 deg shutter. At 2.5 m/s and 120 m the subject steps 0.5 px per frame,
    # so the shutter is doing nothing here except keeping the pipeline honest
    # with the other two clips.
    scn.render.motion_blur_shutter = 0.50
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"

    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    print("saved", out)


def _flat(bpy, name, rgb, rough=0.55):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs["Roughness"].default_value = rough
    return m


def _emissive(bpy, name, strength, rgb=(1.0, 0.94, 0.86)):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def _linearise(bpy, objs):
    """Bake every channel to LINEAR. A slow move is where Bezier handles show:
    the default auto-clamped handles overshoot between sparse keys, and here the
    keys are per frame anyway, so LINEAR is exactly the solved curve."""
    for ob in objs:
        ad = getattr(ob, "animation_data", None)
        if not ad or not ad.action:
            continue
        fcs = list(getattr(ad.action, "fcurves", []) or [])
        if not fcs:
            for lay in ad.action.layers:
                for st in lay.strips:
                    for cb in st.channelbags:
                        fcs.extend(cb.fcurves)
        for fc in fcs:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
            fc.update()


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ImportError:
        t = solve_tow()
        report(t, camera_rows(t))
    else:
        main()
