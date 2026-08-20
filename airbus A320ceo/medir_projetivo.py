"""1D projective (Moebius) mapping along the fuselage axis, both photos.

For a straight line in space imaged by a pinhole camera, axial position x [m]
maps to pixel u by u = (a*x + b) / (c*x + 1). Exact for any yaw; no ad-hoc
linear-scale approximation. Fit on ACAP-known anchors, report residuals, then
invert to read unknown features (door 2, registration, title, wedge).
"""
import numpy as np
from scipy.optimize import least_squares

L = 37.57


def fit(anchors):
    """anchors: list of (x_m, u_px). Returns params (a,b,c)."""
    xs = np.array([p[0] for p in anchors])
    us = np.array([p[1] for p in anchors])

    def resid(p):
        a, b, c = p
        return (a * xs + b) / (c * xs + 1.0) - us

    s0 = (us[-1] - us[0]) / (xs[-1] - xs[0])
    p0 = np.array([s0, us[0], 0.0])
    r = least_squares(resid, p0, method="lm")
    return r.x, resid(r.x)


def u_of(p, x):
    a, b, c = p
    return (a * x + b) / (c * x + 1.0)


def x_of(p, u):
    a, b, c = p
    return (b - u) / (u * c - a)


def scale(p, x):
    """px per metre at x"""
    a, b, c = p
    return (a - b * c) / (c * x + 1.0) ** 2  # d u / d x


def report(name, anchors, reads):
    p, res = fit(anchors)
    print(f"== {name}")
    print("   anchors (x_m, u_px) residuals px:",
          [f"{x}:{r:+.1f}" for (x, _), r in zip(anchors, res)])
    print(f"   scale nose {scale(p,0):.2f} px/m -> tail {scale(p,L):.2f} px/m")
    for lab, u in reads:
        print(f"   {lab:28s} u={u:6.0f} -> x = {x_of(p,u):7.3f} m")
    return p


# ---------------- STARBOARD photo (3965x1780) ----------------
# anchors: nose tip, door1 centre, overwing exit centres (ACAP 14.43 / 15.28), tail tip
anc_s = [(0.0, 487.0),
         (5.04, 916.5),
         (14.43, 1670.0),
         (15.28, 1740.5),
         (37.57, 3521.0)]
reads_s = [
    ("janela fwd (idx?) 1098.4", 1098.4),
    ("janela aft ultima 2690.2", 2690.2),
    ("porta2 contorno esq", 2787.0),
    ("porta2 contorno dir", 2867.0),
    ("matricula esq", 2905.0),
    ("matricula dir", 3010.0),
    ("titulo esq", 2557.0),
    ("titulo dir", 2693.0),
]
ps = report("STBD (Moebius)", anc_s, reads_s)

# implied window pitch at fwd run and aft run
for u0, u1, n, lab in [(1098.4, 1608.8, 12, "fwd run 12 pitches"),
                       (2324.2, 2690.2, 9, "aft run 9 pitches")]:
    d = x_of(ps, u1) - x_of(ps, u0)
    print(f"   {lab}: {d:.3f} m -> pitch {d/n:.4f} m (spec 0.515)")

# windows per lattice
x0w = x_of(ps, 1098.4)
xNw = x_of(ps, 2690.2)
print(f"   first detected window at {x0w:.2f} m; last at {xNw:.2f} m")
