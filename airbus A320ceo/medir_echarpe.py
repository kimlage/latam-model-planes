"""Wedge (echarpe) boundary photogrammetry, CC-BFO starboard photo.

Forward boundary: for each row (z), leftmost run of indigo. Rear boundary:
rightmost indigo before the white TE-root fairing (rows near the crown only;
the stab occludes below). Axial mapping: 6-anchor Moebius (door2@29.53).
Vertical: window-row reference z=0.69 at y=975.5, s_local px/m from the fit.
"""
import numpy as np
from PIL import Image
from scipy.optimize import least_squares

im = np.asarray(Image.open("refs/ref_CC-BFO_sjo_stbd.jpg").convert("RGB"), dtype=np.int16)

anchors = [(0.0, 487.0), (5.04, 916.5), (14.43, 1670.0), (15.28, 1740.5),
           (29.53, 2827.0), (37.57, 3521.0)]
xs = np.array([p[0] for p in anchors]); us = np.array([p[1] for p in anchors])
r = least_squares(lambda p: (p[0] * xs + p[1]) / (p[2] * xs + 1) - us,
                  [80, 487, 0.001], method="lm")
a, b, c = r.x
x_of = lambda u: (b - u) / (u * c - a)
scale_at = lambda x: (a - b * c) / (c * x + 1.0) ** 2

R, G, B = im[..., 0], im[..., 1], im[..., 2]
V = im.max(axis=2)
indigo = (B - R > 25) & (B > G) & (V < 190) & (B > 60)

Y_REF, Z_REF = 975.5, 0.69
S_V = 78.0  # px/m vertical near tail
z_of = lambda y: Z_REF - (y - Y_REF) / S_V

print("-- forward boundary x_front(z): leftmost indigo run per row")
pts = []
for y in range(880, 1120, 8):
    row = indigo[y, 2350:2980]
    # first index with 6 consecutive indigo
    idx = None
    run = 0
    for i, v in enumerate(row):
        run = run + 1 if v else 0
        if run >= 6:
            idx = i - 5
            break
    if idx is not None:
        u = 2350 + idx
        pts.append((z_of(y), x_of(u), u, y))
for z, xm, u, y in pts:
    print(f"  z={z:6.2f}  x_front={xm:6.2f}  (u={u}, y={y})")

print("-- rear boundary (rows near crown): last indigo before white fairing")
for y in range(880, 1000, 8):
    row = indigo[y, 3000:3400]
    js = np.nonzero(row)[0]
    if len(js):
        u = 3000 + js.max()
        print(f"  z={z_of(y):6.2f}  x_rear={x_of(u):6.2f}  (u={u}, y={y})")
