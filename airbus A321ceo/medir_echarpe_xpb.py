"""A321ceo wedge measurement on PT-XPB (ref_PT-XPB_sbgr.jpg, CC BY-SA 2.0).

Method = airbus A321neo/medir_echarpe_v2.py (PS-LBO), re-anchored:
  px(x): quadratic through the four ceo door centres read off gridded crops
         D1 5.02->3307, D2 13.84->2578.5, D3 24.79->1679.5, D4 36.58->706.5
         (gradient 82.1-82.6 px/m -> nearly orthographic)
  py(px,z): affine, anchored on keel + crown silhouettes of the rear fuselage.
Tail ring table (x, keel, crown) copied from the A321 model (same hull).
"""
import numpy as np
from PIL import Image, ImageDraw

im = Image.open("ref_PT-XPB_sbgr.jpg").convert("RGB")
A = np.asarray(im).astype(np.int16)
R, G, B = A[..., 0], A[..., 1], A[..., 2]
indigo = (B - R > 35) & (B - G > 25) & (B > 60) & (B < 200)
white = (R > 150) & (G > 150) & (B > 150) & (abs(R - B) < 25)
# background behind/below the rear fuselage: trees + grass (greenish) or tarmac (tan)
greenish = (G - B > 12) & (G > 50)
tan = (R - B > 18) & (R > 120) & (G > 100)
bg = greenish | tan

coef = np.polyfit([5.02, 13.84, 24.79, 36.58], [3307.0, 2578.5, 1679.5, 706.5], 2)
def x_of_px2(p):
    c2, c1, c0 = coef
    rts = np.roots([c2, c1, c0 - p])
    for r in rts:
        if abs(r.imag) < 1e-9 and -2 < r.real < 60:
            return r.real
    return np.nan
def px_of_x(x): return np.polyval(coef, x)
print("px/m at x=10/25/40:", [round(-np.polyval(np.polyder(coef), x), 2) for x in (10, 25, 40)])

# tail rings (x, keel, crown) — A321 model geometry (identical ceo/neo hull)
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
# keel silhouette: on clean stretches x 30..36.3 (px ~1250..730): first bg run downward
for p in range(740, 1260, 6):
    run = 0
    for y in range(1330, 1620):
        run = run + 1 if bg[y, p] else 0
        if run >= 6:
            samples.append((p, y - 6, keel(x_of_px2(p))))
            break
# crown silhouette forward of the wedge (white hull against trees) x 30..35.6 (px ~790..1250)
for p in range(790, 1260, 6):
    run = 0
    for y in range(1240, 1000, -1):
        run = run + 1 if not white[y, p] else 0
        if run >= 10:
            samples.append((p, y + 10, crown(x_of_px2(p))))
            break
S = np.array(samples)
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
print("VALID px/m vertical (=-c3):", round(-c3, 1), " horizontal ~82.4")
# witnesses: D4 leaf top ~z 1.18 bottom ~z -0.67 (model door 1.85 tall, sill at z -0.67)
for z, lbl in ((-0.67, "D4 bottom (obs ~1322)"), (1.18, "D4 top (obs ~1160)")):
    print(f"VALID {lbl}: py @D4px = {c1 + c2*706.5 + c3*z:.0f}")

overlay = im.copy()
dr = ImageDraw.Draw(overlay)

# ---- lower boundary: lowest indigo per column ------------------------------
res = []
for p in range(310, 1030, 5):
    x = x_of_px2(p)
    y_crn = int(c1 + c2 * p + c3 * crown(x))
    y_keel = int(c1 + c2 * p + c3 * keel(x))
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
for t in res[::4]:
    print("  %6.2f %6.1f %6.2f" % t)
X = np.array([t[0] for t in res if 35.2 <= t[0] <= 41.0])
T = np.array([t[1] for t in res if 35.2 <= t[0] <= 41.0])
for _ in range(3):
    m, b = np.polyfit(X, T, 1)
    rsd = T - (m * X + b)
    keep = np.abs(rsd) < max(2.5 * rsd.std(), 2.0)
    X, T = X[keep], T[keep]
m, b = np.polyfit(X, T, 1)
print(f"FIT lower main: theta = {b:.1f} {m:+.2f}*x  -> theta <= {m*36.05+b:.1f} {m:+.2f}*(x-36.05)  (n={len(X)}, rms={rsd[keep].std():.1f})")
# steep nose segment of the wedge tip (x < 35.2)
Xs = np.array([t[0] for t in res if 33.5 <= t[0] < 35.4])
Ts = np.array([t[1] for t in res if 33.5 <= t[0] < 35.4])
if len(Xs) > 3:
    ms, bs = np.polyfit(Xs, Ts, 1)
    print(f"FIT lower tip:  theta = {bs:.1f} {ms:+.2f}*x  (n={len(Xs)})")

# ---- forward boundary: walk right (forward) per row from inside the wedge --
fwd = []
for yq in range(1080, 1470, 4):
    seg = indigo[yq, 380:700]
    nz = np.nonzero(seg)[0]
    if len(nz) < 20:
        continue
    p = 380 + int(nz[len(nz) // 2])
    gap = 0
    while p < 1150 and gap < 15:
        p += 1
        gap = gap + 1 if not indigo[yq, p] else 0
    pb = p - gap
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

# ---- title bbox (dark navy text on white) ----------------------------------
tt = (B - R > 15) & (B < 160) & (R < 130)
band = tt[1150:1220, 1050:1420]
ys, xs2 = np.nonzero(band)
if len(xs2):
    print(f"\nTITLE bbox: x {x_of_px2(1420 - 0 - (xs2.max()+0)):.2f}..{x_of_px2(1050 + xs2.min()):.2f} (aft..fwd)"
          f"  z {z_of(1050+xs2.mean(), 1150+ys.max()):.2f}..{z_of(1050+xs2.mean(), 1150+ys.min()):.2f}")
    print(f"  raw px x {1050+xs2.min()}..{1050+xs2.max()}  y {1150+ys.min()}..{1150+ys.max()}")

# ---- white registration inside the wedge -----------------------------------
wp = white[1150:1230, 480:680]
ys, xs3 = np.nonzero(wp)
if len(xs3):
    print(f"REG patch: x {x_of_px2(480+xs3.max()):.2f}..{x_of_px2(480+xs3.min()):.2f}"
          f"  z {z_of(580, 1150+ys.max()):.2f}..{z_of(580, 1150+ys.min()):.2f}")
    print(f"  raw px x {480+xs3.min()}..{480+xs3.max()}  y {1150+ys.min()}..{1150+ys.max()}")

# ---- rear boundary at crown ------------------------------------------------
for row_z in (1.7, 1.4):
    yq = int(c1 + c2 * 300 + c3 * row_z)
    seg = indigo[yq, 150:560]
    idx = np.nonzero(seg)[0]
    if len(idx):
        print(f"REAR indigo end at z~{row_z}: x = {x_of_px2(150+idx.min()):.2f}  (neo fin TE line: {41.46 + 0.0538*row_z:.2f})")

overlay.crop((150, 1000, 1450, 1620)).save("insp_echarpe_medida_xpb.png")
print("\noverlay: insp_echarpe_medida_xpb.png")
