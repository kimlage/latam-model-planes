"""A321ceo wedge measurement v2 on PT-XPB — window-row vertical map.

Fixes over v1: the crown/keel affine was only locally valid and its px-tilt term
extrapolated badly. Here the vertical reference is the WINDOW ROW (z centre
0.69 m, constant along the hull), detected automatically and fitted as a line;
the vertical scale is the local horizontal px/m (telephoto, isotropic).
Calibration adds the tailcone tip (x=44.51 -> px 74) to stop extrapolation
drift aft of D4.
"""
import numpy as np
from PIL import Image, ImageDraw

im = Image.open("ref_PT-XPB_sbgr.jpg").convert("RGB")
A = np.asarray(im).astype(np.int16)
R, G, B = A[..., 0], A[..., 1], A[..., 2]
indigo = (B - R > 35) & (B - G > 25) & (B > 60) & (B < 200)
white = (R > 150) & (G > 150) & (B > 150) & (abs(R - B) < 25)

# ---- horizontal calibration: 4 door centres + tailcone tip -----------------
AX = [5.02, 13.84, 24.79, 36.58, 44.51]
AP = [3307.0, 2578.5, 1679.5, 706.5, 74.0]
coef = np.polyfit(AX, AP, 2)
print("anchor residuals(px):", [round(np.polyval(coef, x) - p, 1) for x, p in zip(AX, AP)])
def x_of_px2(p):
    c2, c1, c0 = coef
    rts = np.roots([c2, c1, c0 - p])
    for r in rts:
        if abs(r.imag) < 1e-9 and -3 < r.real < 60:
            return r.real
    return np.nan
def pxm(p):  # local px per metre
    return -np.polyval(np.polyder(coef), x_of_px2(p))
print("px/m at x=5/25/36/42:", [round(-np.polyval(np.polyder(coef), x), 2) for x in (5, 25, 36, 42)])

# ---- window row detection --------------------------------------------------
# dark window ellipses on white: scan columns, find dark blobs in band y 1210-1290
dark = (R < 110) & (G < 110) & (B < 130)
wins = []
p = 750
while p < 3300:
    col = dark[1190:1300, p]
    ys = np.nonzero(col)[0]
    if 4 <= len(ys) <= 40:          # window-sized dark run
        # centroid over a small patch
        patch = dark[1190:1300, p - 6:p + 7]
        yy, xx = np.nonzero(patch)
        if 20 <= len(yy) <= 320:
            wins.append((p - 6 + xx.mean(), 1190 + yy.mean()))
            p += 18
            continue
    p += 4
W = np.array(wins)
print("window candidates:", len(W))
w1, w0 = np.polyfit(W[:, 0], W[:, 1], 1)
for _ in range(3):
    rsd = W[:, 1] - (w1 * W[:, 0] + w0)
    W = W[np.abs(rsd) < max(2.5 * rsd.std(), 3.0)]
    w1, w0 = np.polyfit(W[:, 0], W[:, 1], 1)
print(f"window row: py = {w0:.1f} + {w1:.5f}*px  (n={len(W)}, rms={np.abs(W[:,1]-(w1*W[:,0]+w0)).std():.2f} px)")
def z_of(p, py):
    return 0.69 + ((w1 * p + w0) - py) / pxm(p)

# window pitch check: mean spacing of consecutive detected windows
d = np.diff(sorted(W[:, 0]))
d = d[(d > 25) & (d < 60)]
print(f"window pitch: {d.mean():.1f} px -> {d.mean()/0.515:.1f} px/m (horiz cal ~82.4)")

# ---- validation against doors ----------------------------------------------
for px_d, name, ztop, zbot in ((3307, "D1", 1.18, -0.67), (706.5, "D4", 1.18, -0.67),
                               (2578.5, "D2", 1.06, -0.67), (1679.5, "D3", 1.06, -0.67)):
    yt = (w1 * px_d + w0) - (ztop - 0.69) * pxm(px_d)
    yb = (w1 * px_d + w0) - (zbot - 0.69) * pxm(px_d)
    print(f"VALID {name}: top py {yt:.0f}  bottom py {yb:.0f}")

# tail ring table (x, keel, crown) — A321 model hull
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

# silhouette witnesses: keel at x 31/34 (clean stretches)
for xq in (31.0, 33.5, 35.5):
    p = int(np.polyval(coef, xq))
    zk = keel(xq)
    yk = (w1 * p + w0) - (zk - 0.69) * pxm(p)
    print(f"VALID keel x={xq}: predicted py {yk:.0f} (check overlay)")

overlay = im.copy()
dr = ImageDraw.Draw(overlay)
for (pw, pyw) in wins:
    dr.ellipse([pw - 2, pyw - 2, pw + 2, pyw + 2], outline=(255, 0, 255), width=1)

# ---- lower boundary --------------------------------------------------------
res = []
for p in range(310, 1030, 5):
    x = x_of_px2(p)
    y_crn = int((w1 * p + w0) - (crown(x) - 0.69) * pxm(p))
    y_keel = int((w1 * p + w0) - (keel(x) - 0.69) * pxm(p))
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
X = np.array([t[0] for t in res if 35.4 <= t[0] <= 41.2])
T = np.array([t[1] for t in res if 35.4 <= t[0] <= 41.2])
for _ in range(3):
    m, b = np.polyfit(X, T, 1)
    rsd = T - (m * X + b)
    keep = np.abs(rsd) < max(2.5 * rsd.std(), 2.0)
    X, T = X[keep], T[keep]
m, b = np.polyfit(X, T, 1)
print(f"FIT lower main: theta <= {m*36.05+b:.1f} {m:+.2f}*(x-36.05)  (n={len(X)}, rms={rsd[keep].std():.1f} deg)")
print(f"   at x=36.58 (D4): theta {m*36.58+b:.1f} -> z {zc_r(36.58)[0] + zc_r(36.58)[1]*np.cos(np.radians(m*36.58+b)):.2f}")

# ---- forward boundary (rows outside reg/dorsal contamination) --------------
fwd = []
for yq in range(1080, 1500, 4):
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
    if not (-2.1 < z < 2.15):
        continue
    tag = "ok"
    if 36.7 <= x <= 39.6 and 0.35 <= z <= 1.35:
        tag = "reg"          # stopped at the white registration
    elif z > 1.7:
        tag = "dorsal"       # fin-root fairing, not hull
    fwd.append((x, z, tag))
    dr.ellipse([pb - 3, yq - 3, pb + 3, yq + 3],
               outline=(255, 160, 0) if tag == "ok" else (150, 150, 150), width=2)
print("\nforward boundary (x, z, tag):")
for t in fwd[::3]:
    print("  %6.2f %6.2f %s" % t)
ok = [(x, z) for x, z, tag in fwd if tag == "ok"]
Z = np.array([t[1] for t in ok]); Xf = np.array([t[0] for t in ok])
for _ in range(3):
    k, x0 = np.polyfit(Z, Xf, 1)
    rsd = Xf - (k * Z + x0)
    keep = np.abs(rsd) < max(2.5 * rsd.std(), 0.12)
    Z, Xf = Z[keep], Xf[keep]
k, x0 = np.polyfit(Z, Xf, 1)
print(f"FIT forward: x = {x0:.2f} + {k:.3f}*z  (n={len(Z)}, rms={rsd[keep].std():.2f} m)")

# ---- title bbox: dark navy on white, near crown forward of the wedge -------
tt = (B - R > 15) & (B < 160) & (R < 130)
band = tt[1185:1240, 830:1120]
ys, xs2 = np.nonzero(band)
if len(xs2):
    pxc = 830 + xs2.mean()
    print(f"\nTITLE bbox: x {x_of_px2(830 + xs2.max()):.2f}..{x_of_px2(830 + xs2.min()):.2f}"
          f"  z {z_of(pxc, 1185 + ys.max()):.2f}..{z_of(pxc, 1185 + ys.min()):.2f}"
          f"  raw px {830+xs2.min()}..{830+xs2.max()} y {1185+ys.min()}..{1185+ys.max()}")

# ---- registration: white glyph pixels bounded by indigo left+right ---------
regmask = np.zeros_like(white)
sub = white[1150:1240, 500:700] & True
regmask[1150:1240, 500:700] = sub
ys, xs3 = np.nonzero(regmask)
if len(xs3):
    # trim: keep only pixels whose row has indigo within 40 px both sides
    good = []
    for yy, xx in zip(ys, xs3):
        if indigo[yy, max(xx - 45, 0):xx].any() and indigo[yy, xx:xx + 45].any():
            good.append((yy, xx))
    if good:
        gy = np.array([g[0] for g in good]); gx = np.array([g[1] for g in good])
        print(f"REG bbox: x {x_of_px2(gx.max()):.2f}..{x_of_px2(gx.min()):.2f}"
              f"  z {z_of(gx.mean(), gy.max()):.2f}..{z_of(gx.mean(), gy.min()):.2f}"
              f"  raw px {gx.min()}..{gx.max()} y {gy.min()}..{gy.max()}")

# ---- rear boundary ---------------------------------------------------------
for row_z in (1.6, 1.3, 1.0):
    yq = int((w1 * 300 + w0) - (row_z - 0.69) * pxm(300))
    seg = indigo[yq, 150:560]
    idx = np.nonzero(seg)[0]
    if len(idx):
        print(f"REAR indigo end at z~{row_z}: x = {x_of_px2(150+idx.min()):.2f}  (fin TE line neo: {41.46 + 0.0538*row_z:.2f})")

overlay.crop((60, 1000, 1450, 1620)).save("insp_echarpe_medida_xpb.png")
print("\noverlay: insp_echarpe_medida_xpb.png")
