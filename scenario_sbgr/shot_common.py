#!/usr/bin/env python3
"""Shared math for the SBGR clips - the Guarulhos sibling of
`scenario_sdsc/shot_common.py`, lean because this field is lean: the runway is
level to 0.034%, there is no crest, no graded bowl, and therefore no Ground
class and no sight_line() - nothing here is ever hidden behind terrain. What
Guarulhos has instead is a RIDGE: the Cabucu/Cantareira wall crosses the whole
northern sector at +1.8..+3.2 deg (terrain/horizon_fine_0p1deg.csv), so a shot
looking north pins a crest line the way Santiago pins the Andes, not a flat
level the way Sao Carlos pins its empty band.

Frame conventions (documented once, used everywhere):
  station s   metres along the 10L roll, s = 0 AT THE THR 10L centreline
              point the build placed at ENU (-2.7, 12.3) - phase 2's "abeam at
              2 575 m" quotes this same origin (the hangar solves to s 2571).
  lateral l   metres RIGHT of the roll, i.e. l > 0 is SOUTH-EAST of the
              centreline (the starboard side of a departing aircraft), l < 0
              is the hangar side. This is the OPPOSITE sign family from the
              SDSC module (which had positive = west/port); each module owns
              its file and says so, and neither imports the other.
  rwy_z(s)    linear between the two published threshold elevations:
              -4.76 m at s = 0 to -5.98 m at s = 3548.7 (THR 28R). The fall
              is 0.034% - built, because it is published, but invisible.
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TRACK_DEG = 73.65                      # true bearing of the 10L roll (adopted)
UX = math.sin(math.radians(TRACK_DEG))
UY = math.cos(math.radians(TRACK_DEG))
RX, RY = UY, -UX                       # unit vector 90 deg RIGHT of the track

THR_X, THR_Y = -2.42, 11.21            # the SBGR_10L_Threshold anchor itself
#   (the anchor in sbgr_field.blend is the authority: it sits 1.1 m from the
#    survey table's THR point, and an aircraft placed off IT is on the painted
#    centreline, which is what a viewer checks the wheels against)
Z_THR10L = -4.76                       # published 2445 ft against the datum
Z_THR28R = -5.98                       # published 2441 ft
THR28R_S = 3548.7                      # station of THR 28R
RWY_SLOPE = (Z_THR28R - Z_THR10L) / THR28R_S
PAVE_END_S = 3610.4                    # pavement ends 3700 - 89.6 past THR 10L

# The LATAM hangar, in this frame (solved from the anchor at ENU 2281.2,1361.7)
HANGAR_S, HANGAR_L = 2571.4, -652.2
Z_HGR_PLATFORM = -8.70                 # Patio 9 / hangar platform (phase 2)
HANGAR_EAVE_Z = Z_HGR_PLATFORM + 26.0
HANGAR_RIDGE_Z = Z_HGR_PLATFORM + 30.0

SUN_ELEV_DEG = 16.46                   # 21 Dec, 17:30 local (phase 2, S9)
SUN_AZIM_DEG = 251.1

# Crest of the Cantareira wall across the sector this shot's lens sweeps
# (azimuths 340..020): mean elevation from the fine horizon table.
RIDGE_ELEV_DEG = 2.39

FPS = 25.0                             # a GIF delay is an integer centiseconds
SENSOR = 36.0
ASPECT = 16.0 / 9.0


def rwy_z(s):
    return Z_THR10L + RWY_SLOPE * s


def sl_xy(s, l):
    """(station, lateral) -> scene ENU xy."""
    return (THR_X + UX * s + RX * l, THR_Y + UY * s + RY * l)


def to_sl(x, y):
    dx, dy = x - THR_X, y - THR_Y
    return (dx * UX + dy * UY, dx * RX + dy * RY)


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# --------------------------------------------------------------- interpolation
_PCHIP = {}


def _slopes(pts):
    """Fritsch-Carlson tangents: C1, monotone, no overshoot. A chain of
    smoothsteps has ZERO derivative at every knot - the SDSC module records the
    107 m/s2 acceleration spike that lesson cost."""
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


# -------------------------------------------------------------------- framing
def half_tan(lens):
    return (SENSOR / 2.0) / lens


def hfov(lens):
    return 2.0 * math.atan(half_tan(lens))


def project(cam_xyz, az, el, lens, point):
    """Screen (u, v) and range of a world ENU point; az/el are the lens axis
    as a compass bearing / elevation, exactly as in the SDSC module."""
    dx = point[0] - cam_xyz[0]
    dy = point[1] - cam_xyz[1]
    dz = point[2] - cam_xyz[2]
    horiz = math.hypot(dx, dy)
    b = math.atan2(dx, dy)
    e = math.atan2(dz, horiz)
    t = half_tan(lens)
    du = math.atan2(math.sin(b - az), math.cos(b - az))
    u = 0.5 + math.tan(du) / (2.0 * t)
    v = 0.5 + math.tan(e - el) * ASPECT / (2.0 * t)
    return u, v, math.sqrt(horiz * horiz + dz * dz)


def flow_report(rows, label="shot", key_az="az", key_el="el", key_lens="lens",
                key_cam="cam"):
    """Frame-widths per second - the number a camera is judged on. Offline
    estimate; `../scenario/camera_metrics.py` ray-casts the real thing."""
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
    hs, hl = to_sl(2281.2, 1361.7)
    print("frame self-check: hangar anchor -> s %.1f l %.1f "
          "(phase 2 quotes 2 575 / -654)" % (hs, hl))
    print("rwy_z: %.2f at THR 10L, %.2f at THR 28R, slope %.4f%%"
          % (rwy_z(0), rwy_z(THR28R_S), 100 * RWY_SLOPE))
