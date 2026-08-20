"""Wedge measurement v2 — global affine py(px, z) instead of per-column tops.

Anchors for the vertical map:
  keel silhouette (z = keel(x)) on clean stretches px 3560-4150
  crown silhouette (z = crown(x)) FORWARD of the wedge px 3260-3930 (white hull)
Validation: window row (z centre 0.69) and D4 door bottom (z -0.67).
"""
import numpy as np
from PIL import Image, ImageDraw

im = Image.open("ref_PS-LBO_wikimedia_DSC00834.jpg").convert("RGB")
A = np.asarray(im).astype(np.int16)
R, G, B = A[..., 0], A[..., 1], A[..., 2]
indigo = (B - R > 35) & (B - G > 25) & (B > 60) & (B < 200)
greenbg = (G - B > 15) & (G > 60)
white = (R > 150) & (G > 150) & (B > 150)

coef = np.polyfit([5.04, 26.82, 36.47], [702.0, 3034.0, 4032.0], 2)
def px_of_x(x): return np.polyval(coef, x)
def x_of_px(p):
    c2, c1, c0 = coef
    disc = c1 * c1 - 4 * c2 * (c0 - p)
    return (-c1 + np.sqrt(disc)) / (2 * c2) if c2 < 0 else (-c1 - np.sqrt(disc)) / (2 * c2)
# pick the root in range by testing both
def x_of_px2(p):
    c2, c1, c0 = coef
    rts = np.roots([c2, c1, c0 - p])
    for r in rts:
        if abs(r.imag) < 1e-9 and 0 < r.real < 60:
            return r.real
    return np.nan

tbl = [(30.26, -2.083, 2.083), (33.69, -2.038, 2.098), (34.44, -1.973, 2.093),
       (35.19, -1.843, 2.083), (35.94, -1.712, 2.072), (36.69, -1.511, 2.051),
       (37.44, -1.311, 2.031), (38.19, -1.070, 1.990), (38.94, -0.829, 1.949),
       (39.69, -0.568, 1.888), (40.44, -0.307, 1.827), (41.19, -0.036, 1.756),
       (41.94, 0.225, 1.675), (42.54, 0.446, 1.594), (43.14, 0.657, 1.503)]
tx = [t[0] for t in tbl]
def keel(x):  return np.interp(x, tx, [t[1] for t in tbl])
def crown(x): return np.interp(x, tx, [t[2] for t in tbl])
def zc_r(x):
    k, c = keel(x), crown(x)
    return (k + c) / 2, (c - k) / 2

samples = []   # (px, py, z_model)
# keel silhouette: first green run downward from y=1300
for p in range(3560, 4150, 8):
    run = 0
    for y in range(1300, 1750):
        run = run + 1 if greenbg[y, p] else 0
        if run >= 6:
            samples.append((p, y - 6, keel(x_of_px2(p))))
            break
# crown silhouette forward of the wedge (white hull against background)
for p in range(3260, 3930, 8):
    run = 0
    for y in range(1250, 950, -1):
        ok = white[y, p]
        run = run + 1 if not ok else 0
        if run >= 10:
            samples.append((p, y + 10, crown(x_of_px2(p))))
            break
S = np.array(samples)
# affine py = c1 + c2*px + c3*z  -> robust fit
Mx = np.c_[np.ones(len(S)), S[:, 0], S[:, 2]]
cv, *_ = np.linalg.lstsq(Mx, S[:, 1], rcond=None)
for _ in range(3):
    rsd = Mx @ cv - S[:, 1]
    keep = np.abs(rsd) < max(3 * rsd.std(), 4.0)
    Mx, S = Mx[keep], S[keep]
    cv, *_ = np.linalg.lstsq(Mx, S[:, 1], rcond=None)
c1, c2, c3 = cv
print(f"py = {c1:.1f} + {c2:.4f}*px + {c3:.2f}*z   (n={len(S)}, rms={np.abs(Mx@cv-S[:,1]).std():.2f} px)")
def z_of(px, py): return (py - c1 - c2 * px) / c3
# validation: window row centre z=0.69 -> predicted py at px 3400:
print("VALID window row py @px3400 (expect ~1305-1330):", round(c1 + c2*3400 + c3*0.69, 1))
print("VALID px/m vertical scale:", round(-c3, 1), "(horizontal ~103-107)")

overlay = im.copy()
dr = ImageDraw.Draw(overlay)

# ---- lower boundary: lowest indigo per column, z direct from affine ---------
res = []
for p in range(3560, 4280, 6):
    x = x_of_px2(p)
    zk = keel(x)
    y_keel = int(c1 + c2 * p + c3 * zk)
    y_crn = int(c1 + c2 * p + c3 * crown(x))
    col = indigo[y_crn:y_keel, p]
    ys = np.nonzero(col)[0]
    if len(ys) < 4:
        continue
    ylow = y_crn + ys.max()
    z = z_of(p, ylow)
    zc, r = zc_r(x)
    ct = np.clip((z - zc) / r, -1, 1)
    th = np.degrees(np.arccos(ct))
    res.append((x, th, z))
    dr.ellipse([p - 3, ylow - 3, p + 3, ylow + 3], outline=(0, 255, 0), width=2)
print("\nlower boundary (x, theta, z):")
for t in res[::5]:
    print("  %6.2f %6.1f %6.2f" % t)
X = np.array([t[0] for t in res if 33.2 <= t[0] <= 41.0])
T = np.array([t[1] for t in res if 33.2 <= t[0] <= 41.0])
for _ in range(3):
    m, b = np.polyfit(X, T, 1)
    rsd = T - (m * X + b)
    keep = np.abs(rsd) < max(2.5 * rsd.std(), 2.0)
    X, T = X[keep], T[keep]
m, b = np.polyfit(X, T, 1)
print(f"FIT lower: theta = {b:.1f} {m:+.2f}*x  -> theta <= {m*36.05+b:.1f} {m:+.2f}*(x-36.05)  (n={len(X)}, rms={rsd[keep].std():.1f})")

# ---- forward boundary: walk left per row from inside the wedge --------------
fwd = []
for yq in range(1100, 1500, 5):
    # seed: is there indigo at this row between px 3950 and 4250?
    seg = indigo[yq, 3950:4250]
    if seg.sum() < 20:
        continue
    seed = 3950 + int(np.nonzero(seg)[0][len(np.nonzero(seg)[0]) // 2])
    p = seed
    gap = 0
    while p > 3400 and gap < 18:
        p -= 1
        gap = gap + 1 if not indigo[yq, p] else 0
    pb = p + gap
    x = x_of_px2(pb)
    z = z_of(pb, yq)
    if -2.1 < z < 2.15:
        fwd.append((x, z))
        dr.ellipse([pb - 3, yq - 3, pb + 3, yq + 3], outline=(255, 160, 0), width=2)
print("\nforward boundary (x, z):")
for t in fwd[::4]:
    print("  %6.2f %6.2f" % t)
Z = np.array([t[1] for t in fwd]); Xf = np.array([t[0] for t in fwd])
for _ in range(3):
    k, x0 = np.polyfit(Z, Xf, 1)
    rsd = Xf - (k * Z + x0)
    keep = np.abs(rsd) < max(2.5 * rsd.std(), 0.15)
    Z, Xf = Z[keep], Xf[keep]
k, x0 = np.polyfit(Z, Xf, 1)
print(f"FIT forward: x = {x0:.2f} + {k:.3f}*z  (n={len(Z)}, rms={rsd[keep].std():.2f} m)")

# ---- title and registration patch in (x, z) --------------------------------
# title: dark navy text on white, band px 3650-3960
tt = (B - R > 20) & (B < 150) & (R < 120)
ys, xs2 = np.nonzero(tt[1240:1340, 3650:3960])
if len(xs2):
    x_a = x_of_px2(3650 + xs2.min()); x_b = x_of_px2(3650 + xs2.max())
    z_a = z_of(3650 + xs2.mean(), 1240 + ys.max()); z_b = z_of(3650 + xs2.mean(), 1240 + ys.min())
    print(f"\nTITLE bbox: x {x_a:.2f}..{x_b:.2f}  z {z_a:.2f}..{z_b:.2f}")
# white registration patch inside the wedge: white run surrounded by indigo
wp = white[1240:1310, 4060:4260]
ys, xs3 = np.nonzero(wp)
if len(xs3):
    print(f"REG patch: x {x_of_px2(4060+xs3.min()):.2f}..{x_of_px2(4060+xs3.max()):.2f}  z {z_of(4160, 1240+ys.max()):.2f}..{z_of(4160, 1240+ys.min()):.2f}")

# ---- rear boundary at crown: last indigo at z~1.9 --------------------------
row_z = 1.9
yq = int(c1 + c2 * 4300 + c3 * row_z)
seg = indigo[yq, 4200:4600]
idx = np.nonzero(seg)[0]
if len(idx):
    print(f"REAR indigo end at z~1.9: x = {x_of_px2(4200+idx.max()):.2f}  (fin TE line shifted: {41.46 + 0.0538*row_z:.2f})")

overlay.crop((3400, 950, 4700, 1750)).save("insp_echarpe_medida2.png")
print("\noverlay: insp_echarpe_medida2.png")
