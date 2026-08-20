"""Photogrammetry of the rear indigo wedge on PS-LBO (DSC00834, port profile).

Calibration: quadratic px(x) fitted on ACAP door stations
  D1 5.04 -> px 702 ; D3 26.82 -> px 3034 ; D4 36.47 -> px 4032
  validated on the overwing exits (18.70 -> 2177 predicted / 2180 measured;
  19.54 -> 2267 / 2269). Local scale ~103-107 px/m, +-3 px.
Vertical: per-column linear z from the hull silhouette (top=crown, bottom=keel),
with crown/keel from the validated A320 rings shifted +6.94 m.
theta = acos(1 - 2u), u = (y - y_top)/(y_bot - y_top)  [exact in side view].
"""
import numpy as np
from PIL import Image, ImageDraw

im = Image.open("ref_PS-LBO_wikimedia_DSC00834.jpg").convert("RGB")
A = np.asarray(im).astype(np.int16)
H, W = A.shape[:2]

# --- calibration px(x) = a + b x + c x^2 (and inverse) -----------------------
import numpy.polynomial.polynomial as P
xs = np.array([5.04, 26.82, 36.47])
ps = np.array([702.0, 3034.0, 4032.0])
coef = np.polyfit(xs, ps, 2)          # [c2, c1, c0]
def px_of_x(x): return np.polyval(coef, x)
def x_of_px(p):
    r = np.roots([coef[0], coef[1], coef[2] - p])
    r = [v for v in r if 0 < v.real < 60 and abs(v.imag) < 1e-6]
    return float(r[0].real)

# --- hull crown/keel (A321 = A320 rings + 6.94) ------------------------------
tbl = [  # x_a321, z_keel(cage), z_crown(cage)
    (30.26, -2.083, 2.083), (33.69, -2.038, 2.098), (34.44, -1.973, 2.093),
    (35.19, -1.843, 2.083), (35.94, -1.712, 2.072), (36.69, -1.511, 2.051),
    (37.44, -1.311, 2.031), (38.19, -1.070, 1.990), (38.94, -0.829, 1.949),
    (39.69, -0.568, 1.888), (40.44, -0.307, 1.827), (41.19, -0.036, 1.756),
    (41.94,  0.225, 1.675), (42.54,  0.446, 1.594), (43.14,  0.657, 1.503),
]
tx = [t[0] for t in tbl]
def keel(x):  return np.interp(x, tx, [t[1] for t in tbl])
def crown(x): return np.interp(x, tx, [t[2] for t in tbl])

# --- colour tests ------------------------------------------------------------
R, G, B = A[..., 0], A[..., 1], A[..., 2]
indigo = (B - R > 35) & (B - G > 25) & (B > 60) & (B < 200)
greenbg = (G - B > 15) & (G > 60)          # grass / trees
white = (R > 150) & (G > 150) & (B > 150)

# --- column sweep ------------------------------------------------------------
res_lower = []   # (x, theta_deg)
overlay = im.copy()
dr = ImageDraw.Draw(overlay)
for p in range(3560, 4620, 6):
    x = x_of_px(p)
    col_ind = indigo[:, p]
    col_grn = greenbg[:, p]
    # hull bottom: first green run (>=6 px) scanning downward from y=1250
    ybot = None
    run = 0
    for y in range(1250, 1750):
        run = run + 1 if col_grn[y] else 0
        if run >= 6:
            ybot = y - 5
            break
    # hull top: scan upward band; hull pixel = white or indigo, background above
    ytop = None
    run = 0
    for y in range(1250, 950, -1):
        ok = white[y, p] or indigo[y, p]
        run = run + 1 if not ok else 0
        if run >= 8:
            ytop = y + 8
            break
    if ybot is None or ytop is None or ybot - ytop < 120:
        continue
    ys = np.nonzero(col_ind[ytop:ybot])[0]
    if len(ys) < 4:
        continue
    ylow = ytop + ys.max()
    u = (ylow - ytop) / (ybot - ytop)
    th = np.degrees(np.arccos(np.clip(1 - 2 * u, -1, 1)))
    res_lower.append((x, th, ytop, ybot, ylow))
    dr.line([(p, ytop), (p, ytop + 4)], fill=(255, 0, 0), width=3)
    dr.line([(p, ybot - 4), (p, ybot)], fill=(255, 0, 0), width=3)
    dr.ellipse([p - 3, ylow - 3, p + 3, ylow + 3], outline=(0, 255, 0), width=2)

print("lower-boundary samples:", len(res_lower))
for (x, th, *_ ) in res_lower[::6]:
    print(f"  x={x:6.2f}  theta={th:6.1f}")

# robust line fit theta(x) in the straight stretch (exclude fin-TE tailoff)
pts = [(x, th) for (x, th, *_ ) in res_lower if 35.2 <= x <= 41.0 and th > 15]
if len(pts) > 10:
    X = np.array([p[0] for p in pts]); T = np.array([p[1] for p in pts])
    for _ in range(3):                      # 2 reject passes
        m, b = np.polyfit(X, T, 1)
        rsd = T - (m * X + b)
        keep = np.abs(rsd) < max(3 * rsd.std(), 2.0)
        X, T = X[keep], T[keep]
    m, b = np.polyfit(X, T, 1)
    print(f"FIT lower boundary: theta = {b:.1f} {m:+.2f}*x   (n={len(X)}, rms={np.sqrt(((T-(m*X+b))**2).mean()):.1f} deg)")
    print(f"  as skill form: theta <= {m*36.05+b:.1f} + {m:.2f}*(x-36.05)")
    print(f"  A320 shifted +6.94:  theta <= 101.4 - 7.58*(x-36.05)")

# --- forward boundary: leftmost indigo per row in the upper band -------------
res_fwd = []
for yq in range(1120, 1330, 4):
    row = indigo[yq, 3500:4200]
    idx = np.nonzero(row)[0]
    if len(idx) == 0:
        continue
    # first run of >=5 indigo pixels
    for i in idx:
        if row[i:i + 5].all():
            pxx = 3500 + i
            x = x_of_px(pxx)
            # z from local silhouette: reuse nearest column's ytop/ybot
            near = min(res_lower, key=lambda r: abs(px_of_x(r[0]) - pxx)) if res_lower else None
            if near is None: break
            _, _, ytop, ybot, _ = near
            u = (yq - ytop) / (ybot - ytop)
            zk, zc = keel(x), crown(x)
            z = zc - u * (zc - zk)
            res_fwd.append((x, z))
            dr.ellipse([pxx - 3, yq - 3, pxx + 3, yq + 3], outline=(255, 160, 0), width=2)
            break
if len(res_fwd) > 6:
    Z = np.array([r[1] for r in res_fwd]); X = np.array([r[0] for r in res_fwd])
    k, x0 = np.polyfit(Z, X, 1)
    print(f"FIT forward boundary: x = {x0:.2f} + {k:.3f}*z   (n={len(res_fwd)})")
    print(f"  A320 shifted +6.94: x = 34.33 + 0.839*z")

overlay.crop((3450, 900, 4700, 1800)).save("insp_echarpe_medida.png")
print("overlay saved: insp_echarpe_medida.png")
