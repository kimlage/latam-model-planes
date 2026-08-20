"""Perspective-corrected axial mapping for the CC-BFO starboard photo.

Model: local scale s(px) [px/m] varies linearly along the fuselage (small yaw,
long lens). b is fitted from the window-pitch gradient; a is set so the
nose->tail integral equals 37.57 m. Everything else is validated against the
mapping: x_m(px) = integral from PX_NOSE of dt / s(t).

Anchors (read by eye on gridded crops, insp_stbd_*.png):
  nose tip   (487, 1100)
  tail tip   (3521, 912)   +-5 px (tree clutter)
"""
import numpy as np

PX_NOSE = 487.0
PX_TAIL = 3521.0
LEN_M = 37.57
PITCH_M = 0.515

# window centroids (medir_janelas.py, stbd, h>=15 blobs only)
FWD = [1098.4, 1141.4, 1184.4, 1227.0, 1269.8, 1312.4, 1355.2, 1397.6,
       1439.8, 1482.2, 1524.7, 1566.8, 1608.8]
AFT = [2324.2, 2364.9, 2405.8, 2446.7, 2487.6, 2528.2, 2568.9, 2608.9,
       2649.7, 2690.2]

# pitch samples (midpoint px, px-per-pitch)
samples = []
for run in (FWD, AFT):
    for p, q in zip(run[:-1], run[1:]):
        samples.append((0.5 * (p + q), q - p))
samples = np.array(samples)

# local px/m from pitch
mx, mp = samples[:, 0], samples[:, 1] / PITCH_M
b, a0 = np.polyfit(mx, mp, 1)          # s(px) ~ a0 + b*px  (px/m)


def integral(a, x0, x1):
    """metres between px x0 and x1 for s(t)=a+b*t"""
    if abs(b) < 1e-12:
        return (x1 - x0) / a
    return (np.log(a + b * x1) - np.log(a + b * x0)) / b


# recalibrate a so nose->tail = 37.57 m, keeping the fitted gradient b
from scipy.optimize import brentq  # noqa
try:
    a = brentq(lambda av: integral(av, PX_NOSE, PX_TAIL) - LEN_M, 1e-3, 500.0)
except Exception:
    a = a0
print(f"pitch fit: s(px) = {a0:.3f} {b:+.6f}*px  (px/m); recalibrated a = {a:.3f}")
print(f"scale nose {a + b*PX_NOSE:.2f} px/m -> tail {a + b*PX_TAIL:.2f} px/m")
print(f"pitch-only length check: integral with a0 = {integral(a0, PX_NOSE, PX_TAIL):.2f} m vs 37.57")


def x_m(px):
    return integral(a, PX_NOSE, px)


def px_of(xm, lo=400.0, hi=3900.0):
    return brentq(lambda p: x_m(p) - xm, lo, hi)


print("\n-- window lattice check (first window spec x=6.08, pitch 0.515)")
for w in FWD[:3] + AFT[-3:]:
    xm = x_m(w)
    k = (xm - 6.08) / PITCH_M
    print(f"  window centroid px {w:7.1f} -> x = {xm:6.3f} m -> index {k:6.2f}")

print("\n-- feature predictions (spec_a320 master) vs photo")
feats = [("porta1 centro", 5.04), ("porta2 centro", 29.64),
         ("overwing1 centro", 14.43 + 0.615 / 2 if False else 14.74),
         ("janela 1", 6.08),
         ("fin TE raiz (master 34.60)", 34.60),
         ("asa raiz LE", 11.0)]
for name, xm in feats:
    print(f"  {name:28s} x={xm:6.2f} m -> px {px_of(xm):7.1f}")

print("\n-- measured px -> metres")
meas = [("porta1 sulco esq", 876), ("porta1 sulco dir", 957),
        ("porta2 contorno esq", 2757), ("porta2 contorno dir", 2812),
        ("matricula esq", 2830), ("matricula dir", 3010),
        ("titulo A320 esq", 2557), ("titulo A320 dir", 2693),
        ("overwing1 esq", 1652), ("overwing1 dir", 1688),
        ("overwing2 esq", 1724), ("overwing2 dir", 1757)]
for name, p in meas:
    print(f"  {name:22s} px {p:6.0f} -> x = {x_m(p):7.3f} m")

print("\n-- widths in metres")
for name, p0, p1 in [("porta1 (sulco-sulco)", 876, 957),
                     ("porta2 (contorno)", 2757, 2812),
                     ("matricula", 2830, 3010),
                     ("titulo", 2557, 2693)]:
    print(f"  {name:22s} {integral(a, p0, p1):6.3f} m")
