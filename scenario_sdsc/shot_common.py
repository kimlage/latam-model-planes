#!/usr/bin/env python3
"""Geometry and curve helpers shared by the three SDSC clips. **No bpy.**

`takeoff_camera.py`, `hangar_tow.py` and `base_flyover.py` all import this so
that each of them can be tuned OFFLINE - `python3 takeoff_camera.py` prints the
whole shot's numbers in under a second, against `blender -b` on a 108 MB terrain
file. That is the loop Santiago's `../scenario/takeoff_camera.py` established
and it is worth more here than there, because this field has three levels
(runway, mid-field apron, MRO platform) and every camera height has to be taken
off the right one.

What lives here
    * the RWY 02 frame: `to_al` / `rwy_pt` / `rwy_z`, identical to
      `build_scenery.py`'s, so a station quoted in one file means the same
      thing in the other;
    * `Ground`, a numpy-only re-implementation of `build_scenery.Ground` -
      same 30 m Copernicus grid, same runway/platform grading - because
      `build_scenery` imports bpy at module scope and cannot be used offline;
    * PCHIP interpolation and Gaussian smoothing, lifted from Santiago's
      take-off module for the reason its docstring gives: a smoothstep chain
      has ZERO derivative at every control point, so a crane built on one stops
      climbing and starts again once per knot;
    * `sight_line`, which answers the SDSC-specific question "can this camera
      see the MRO yet, or is the runway crest still in the way".

THE SIGN CONVENTION, and it is the one that gets a base built mirrored.
`lateral > 0 is LEFT of a RWY 02 roll, i.e. WEST` - the same as
`build_scenery.rwy_pt` and `render_checks._roll_point`. So:

    Aeroclube        lateral +180..+280, along 190..520      LEFT / west
    mid-field cluster lateral -314,      along 1146          RIGHT / east
    LATAM MRO        lateral -797..-1287, along 1602..1937   RIGHT / east
    the sun          azimuth 274.46 deg true                 WEST

A camera with the sun behind it therefore stands WEST of the aeroplane and
looks EAST - which is also the side the base is on. Both constraints point the
same way, which is the single luckiest fact about this field.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --- the RWY 02 frame (sdsc_aip_survey.json; identical to build_scenery.py) --
TRACK_02_DEG = 1.026                 # TRUE. The designator says 02; VAR is 22 W.
UX = math.sin(math.radians(TRACK_02_DEG))
UY = math.cos(math.radians(TRACK_02_DEG))
NX, NY = -UY, UX                     # +lateral = LEFT of the roll = WEST

Z_THR02 = 804.67 - 807.0             # -2.33  published 2640 ft
Z_THR20 = 794.61 - 807.0             # -12.39 published 2607 ft
THR20_A = 1619.98                    # measured THR-to-THR, published 1620
RWY_SLOPE = (Z_THR20 - Z_THR02) / THR20_A        # -0.006210, downhill to 20
TORA_02 = 1672.0                     # ROTAER declared distance
PAVE_N_A = 1667.71                   # north pavement end

Z_MRO_PLATFORM = 769.9 - 807.0       # -37.10
Z_MIDFIELD_APRON = 795.9 - 807.0     # -11.10
Z_AEROCLUBE_APRON = 804.9 - 807.0    # -2.10
Z_RUNWAY = 0.09                      # pavement top above graded()
Z_APRON = 0.05

SUN_ELEV_DEG = 15.14                 # 26 Sep, 17:00 local (UTC-3)
SUN_AZIM_DEG = 274.46

# Landmarks, in (along, lateral) on the 02 roll. lateral<0 = east = RIGHT.
MRO_BUILDINGS_A = (1602.0, 1937.0)
MRO_BUILDINGS_L = (-797.0, -1287.0)
MRO_CENTRE = (1770.0, -1040.0, Z_MRO_PLATFORM + 22.0)   # hangar-line eave
HANGAR9_CENTRE = (750.0, 1637.5, Z_MRO_PLATFORM)        # scene xy, not roll
MIDFIELD = (1146.0, -314.0, Z_MIDFIELD_APRON + 10.0)
AEROCLUBE = (355.0, 230.0, Z_AEROCLUBE_APRON + 6.0)

FPS = 25.0                           # a GIF delay is an integer of centiseconds
SENSOR = 36.0
ASPECT = 16.0 / 9.0


# ---------------------------------------------------------------------------
# the frame
# ---------------------------------------------------------------------------
def rwy_z(a):
    """Runway surface z at `a` metres along the 02 track from THR 02."""
    return Z_THR02 + RWY_SLOPE * a


def rwy_pt(a, l, dz=0.0):
    """(along, lateral, height above the runway surface) -> scene xyz."""
    return (UX * a + NX * l, UY * a + NY * l, rwy_z(a) + dz)


def al_xy(a, l):
    """(along, lateral) -> scene (x, y), no z."""
    return (UX * a + NX * l, UY * a + NY * l)


def to_al(x, y):
    return x * UX + y * UY, x * NX + y * NY


# ---------------------------------------------------------------------------
# the graded ground, without Blender
# ---------------------------------------------------------------------------
def _smoothstep(t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


class Ground:
    """`build_scenery.Ground`, re-expressed with numpy only.

    Kept byte-for-byte equivalent in behaviour to the class the scenery was
    BUILT with - if these two ever disagree, cameras stand off the ground they
    were placed against. The numbers below are the ones `build_scenery.py`
    prints back on every build.
    """

    def __init__(self):
        import numpy as np
        meta = json.load(open(os.path.join(HERE, "terrain",
                                           "terrain_meta.json")))
        self.m = meta["grids"]["terrain_sdsc_near_30m"]
        self.Z = np.load(os.path.join(HERE, "terrain", self.m["file"]))
        self.ny, self.nx = self.Z.shape

    def dem(self, x, y):
        fi = (x - self.m["x_min_m"]) / self.m["step_m"]
        fj = (y - self.m["y_min_m"]) / self.m["step_m"]
        i = min(max(int(fi), 0), self.nx - 2)
        j = min(max(int(fj), 0), self.ny - 2)
        a, b = fi - i, fj - j
        a = 0.0 if a < 0 else (1.0 if a > 1 else a)
        b = 0.0 if b < 0 else (1.0 if b > 1 else b)
        Z = self.Z
        return float(Z[j, i] * (1 - a) * (1 - b) + Z[j, i + 1] * a * (1 - b) +
                     Z[j + 1, i] * (1 - a) * b + Z[j + 1, i + 1] * a * b)

    def graded(self, x, y):
        z = self.dem(x, y)
        a, l = to_al(x, y)
        w = 1.0 - _smoothstep((abs(l) - 90.0) / 170.0)
        if a < -51.99:
            w *= 1.0 - _smoothstep((-51.99 - a) / 200.0)
        elif a > PAVE_N_A:
            w *= 1.0 - _smoothstep((a - PAVE_N_A) / 200.0)
        if w > 0.0:
            z = z * (1.0 - w) + rwy_z(a) * w
        for (x0, x1, y0, y1, fade, lvl) in (
                (620.0, 1100.0, 1530.0, 2060.0, 160.0, Z_MRO_PLATFORM),
                (225.0, 400.0, 1040.0, 1240.0, 70.0, Z_MIDFIELD_APRON),
                (-300.0, -150.0, 190.0, 520.0, 60.0, Z_AEROCLUBE_APRON)):
            dx = max(x0 - x, 0.0, x - x1)
            dy = max(y0 - y, 0.0, y - y1)
            w = 1.0 - _smoothstep(math.hypot(dx, dy) / fade)
            if w > 0.0:
                z = z * (1.0 - w) + lvl * w
        return z


_G = [None]


def ground():
    if _G[0] is None:
        _G[0] = Ground()
    return _G[0]


def sight_line(p0, p1, n=240, t_max=0.92):
    """Terrain clearance along the segment p0->p1, both scene xyz.

    Returns (min_clearance_m, fraction_at_min). Negative means the graded
    ground is IN THE WAY. This is the function that decides when the MRO
    breaks the runway crest, which is the whole reveal of the departure clip:
    the base is 35 m below the runway and cannot be seen from it.

    `t_max` stops the scan short of the target. Without it the minimum always
    lands on the last sample - a point ON the apron is 5 cm above the apron -
    and the number saturates near zero the moment the crest is cleared, hiding
    how much clearance the shot actually gained.
    """
    g = ground()
    best, at = 1e9, 0.0
    for k in range(1, int(n * t_max)):
        t = k / float(n)
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        z = p0[2] + (p1[2] - p0[2]) * t
        c = z - g.graded(x, y)
        if c < best:
            best, at = c, t
    return best, at


# ---------------------------------------------------------------------------
# curves - PCHIP, and why not a smoothstep chain
# ---------------------------------------------------------------------------
_PCHIP = {}


def _slopes(pts):
    """Fritsch-Carlson tangents: C1 everywhere, monotone, no overshoot.

    Santiago's lesson, and it cost a shipped clip: a chain of smoothsteps looks
    smooth on a graph and is wrong for a camera, because its derivative is ZERO
    at every control point. The crane stops climbing and starts again once per
    knot - measured there as a 107 m/s2 acceleration spike.
    """
    n = len(pts)
    h = [pts[i + 1][0] - pts[i][0] for i in range(n - 1)]
    dl = [(pts[i + 1][1] - pts[i][1]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
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
            j = min(n - 1, max(0, i + k))
            acc += w * vals[j]
            wsum += w
        out.append(acc / wsum)
    return out


def unwrap(vals):
    out = list(vals)
    for i in range(1, len(out)):
        while out[i] - out[i - 1] > math.pi:
            out[i] -= 2 * math.pi
        while out[i] - out[i - 1] < -math.pi:
            out[i] += 2 * math.pi
    return out


# ---------------------------------------------------------------------------
# framing
# ---------------------------------------------------------------------------
def half_tan(lens):
    return (SENSOR / 2.0) / lens


def hfov(lens):
    return 2.0 * math.atan(half_tan(lens))


def project(cam_xyz, az, el, lens, point):
    """Screen (u, v) and range of a world point, u right, v up, 0..1 in frame."""
    dx = point[0] - cam_xyz[0]
    dy = point[1] - cam_xyz[1]
    dz = point[2] - cam_xyz[2]
    horiz = math.hypot(dx, dy)
    b = math.atan2(dx, dy)                      # compass bearing, radians
    e = math.atan2(dz, horiz)
    t = half_tan(lens)
    du = math.atan2(math.sin(b - az), math.cos(b - az))
    u = 0.5 + math.tan(du) / (2.0 * t)
    v = 0.5 + math.tan(e - el) * ASPECT / (2.0 * t)
    return u, v, math.sqrt(horiz * horiz + dz * dz)


def flow_report(rows, label="shot", key_az="az", key_el="el", key_lens="lens",
                key_cam="cam"):
    """The one number a camera is judged on: frame-widths per second.

    Degrees per second is not what the eye reads - the lens is the gain on the
    pan. Below ~0.5 w/s is calm, above ~1.0 disorients. This is the OFFLINE
    estimate (aim rate / hfov); `../scenario/camera_metrics.py` measures the
    real thing by ray-casting the scene, and is what the numbers in the README
    are quoted from. Run both: this one to tune, that one to believe.
    """
    pans, flows, azt = [], [], []
    for a, b in zip(rows, rows[1:]):
        d = math.hypot(b[key_az] - a[key_az], b[key_el] - a[key_el]) * FPS
        pans.append(math.degrees(d))
        flows.append(d / hfov(b[key_lens]))
    for r in rows:
        azt.append(math.degrees(r[key_az]) % 360.0)
    sp = [math.dist(a[key_cam], b[key_cam]) * FPS
          for a, b in zip(rows, rows[1:])]
    acc = [abs(b - a) * FPS for a, b in zip(sp, sp[1:])]
    body = flows[8:-8] if len(flows) > 20 else flows
    rev = [i + 1 for i in range(1, len(azt) - 1)
           if ((azt[i] - azt[i - 1] + 540) % 360 - 180) *
           ((azt[i + 1] - azt[i] + 540) % 360 - 180) < 0]
    print("\n--- %s: %d frames = %.2f s @ %.0f fps ---"
          % (label, len(rows), len(rows) / FPS, FPS))
    print("lens %.1f -> %.1f mm" % (rows[0][key_lens], rows[-1][key_lens]))
    print("pan rate  max %.2f deg/s     aim reversals %d %s"
          % (max(pans), len(rev), rev[:8] if rev else ""))
    print("screen flow (offline)  median %.3f  p90 %.3f  max %.3f w/s"
          % (sorted(flows)[len(flows) // 2],
             sorted(flows)[int(len(flows) * 0.9)], max(flows)))
    print("body flow (excl. 8-frame ease each end) %.3f..%.3f  ratio %.2f"
          % (min(body), max(body), max(body) / max(min(body), 1e-9)))
    print("camera speed %.1f..%.1f m/s   peak acceleration %.2f m/s2"
          % (min(sp), max(sp), max(acc) if acc else 0.0))
    return dict(flow_med=sorted(flows)[len(flows) // 2], flow_max=max(flows),
                pan_max=max(pans), reversals=len(rev),
                speed=(min(sp), max(sp)), accel=max(acc) if acc else 0.0)


if __name__ == "__main__":
    g = ground()
    print("graded() spot checks against build_scenery.py's printed levels")
    for (nm, x, y, want) in (("THR 02", 0.0, 0.0, Z_THR02),
                             ("THR 20", 29.0, 1619.72, Z_THR20),
                             ("MRO apron", 912.5, 1608.9, Z_MRO_PLATFORM),
                             ("hangar 9", 750.0, 1637.5, Z_MRO_PLATFORM),
                             ("mid-field", 300.0, 1140.0, Z_MIDFIELD_APRON),
                             ("Aeroclube", -212.0, 456.0, Z_AEROCLUBE_APRON)):
        got = g.graded(x, y)
        print("  %-10s graded %8.2f   expected %8.2f   delta %+.3f"
              % (nm, got, want, got - want))
