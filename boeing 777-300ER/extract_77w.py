#!/usr/bin/env python3
"""Extraction of the 777-300ER hull curves from APR D6-58329-2 Rev G p.18 (600 dpi).

The drawing uses BLUE strokes for the airframe and gray for dimension lines,
so the mask is chromatic (B-R) instead of the generic dark-pixel mask.
Datum: x=0 at nose tip, z=0 at mid-height of the constant section.
Calibration: overall length 73.86 m across the top view x-extent; validated
against fuselage width 6.20 (top), height 6.20 (side), wheelbase 31.22.
"""
import json
import numpy as np
from PIL import Image

PAGE = "apr600_p18-018.png"

im = Image.open(PAGE).convert("RGB")
a = np.asarray(im).astype(np.int16)
blue = (a[:, :, 2] - a[:, :, 0] > 60) & (a[:, :, 2] > 120)
print("blue px:", blue.sum())

# ---------------------------------------------------------------- top view
# band that contains only the top view (thumb said y 1950-2700 covers it,
# but wing tips extend well above/below; the FUSELAGE band is narrower)
TOP_Y0, TOP_Y1 = 1950, 2700          # fuselage band of the top view
top = blue[TOP_Y0:TOP_Y1, :]
cols = np.where(top.any(axis=0))[0]
x_nose_top, x_tail_top = cols.min(), cols.max()
print(f"top view x extent: {x_nose_top}..{x_tail_top} px")

# full drawing extent for the length calibration: use a WIDE band around the
# top view (the printed 73.86 spans the whole top view drawing)
TOPWIDE_Y0, TOPWIDE_Y1 = 1300, 3450
topwide = blue[TOPWIDE_Y0:TOPWIDE_Y1, :]
colsw = np.where(topwide.any(axis=0))[0]
print(f"top view WIDE x extent: {colsw.min()}..{colsw.max()} px")

# ---------------------------------------------------------------- side view
SIDE_Y0, SIDE_Y1 = 3550, 4300
side = blue[SIDE_Y0:SIDE_Y1, :]
cols_s = np.where(side.any(axis=0))[0]
print(f"side view x extent: {cols_s.min()}..{cols_s.max()} px")

# per-column top/bottom in each view
def band(mask, y0):
    xs, top_, bot_ = [], [], []
    for c in range(mask.shape[1]):
        col = np.where(mask[:, c])[0]
        if len(col) == 0:
            continue
        xs.append(c)
        top_.append(col[0] + y0)
        bot_.append(col[-1] + y0)
    return np.array(xs), np.array(top_, float), np.array(bot_, float)

xs_t, esq, dire = band(top, TOP_Y0)
xs_s, crown, keel = band(side, SIDE_Y0)

np.save("_xs_t.npy", xs_t); np.save("_esq.npy", esq); np.save("_dir.npy", dire)
np.save("_xs_s.npy", xs_s); np.save("_crown.npy", crown); np.save("_keel.npy", keel)
print("saved raw bands")
