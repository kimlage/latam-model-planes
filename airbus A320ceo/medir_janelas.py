"""Window-pitch photogrammetry on the CC-BFO photos.

Detects the dark cabin-window ovals along the window row, reports centroid x of
each, consecutive pitches, and local px/m scale (pitch = 0.515 m), forward vs
aft, to expose any yaw-induced scale gradient before measuring anything else.
"""
import os
import numpy as np
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(BASE, "refs")

PITCH_M = 0.515


def detect(img_path, x0, x1, y0, y1, dark_thresh=120, min_area=60, max_area=2500):
    im = np.asarray(Image.open(img_path).convert("L"), dtype=np.uint8)
    band = im[y0:y1, x0:x1]
    mask = band < dark_thresh
    # connected components by simple flood via scipy-free labeling
    lbl = np.zeros(band.shape, dtype=np.int32)
    cur = 0
    stack = []
    H, W = mask.shape
    for j in range(H):
        for i in range(W):
            if mask[j, i] and lbl[j, i] == 0:
                cur += 1
                stack.append((j, i))
                lbl[j, i] = cur
                while stack:
                    a, b = stack.pop()
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        na, nb = a + da, b + db
                        if 0 <= na < H and 0 <= nb < W and mask[na, nb] and lbl[na, nb] == 0:
                            lbl[na, nb] = cur
                            stack.append((na, nb))
    cents = []
    for k in range(1, cur + 1):
        ys, xs = np.nonzero(lbl == k)
        area = len(xs)
        if not (min_area <= area <= max_area):
            continue
        w = xs.max() - xs.min() + 1
        h = ys.max() - ys.min() + 1
        if h == 0 or w == 0 or w > 2.2 * h or h > 3.0 * w:
            continue
        cents.append((xs.mean() + x0, ys.mean() + y0, area, w, h))
    cents.sort()
    return cents


def report(name, cents):
    print(f"== {name}: {len(cents)} blobs")
    xs = np.array([c[0] for c in cents])
    for c in cents:
        print(f"  x={c[0]:7.1f} y={c[1]:7.1f} area={c[2]:4d} w={c[3]} h={c[4]}")
    if len(xs) > 2:
        d = np.diff(xs)
        # keep plausible single-pitch gaps only
        med = np.median(d[(d > 0.6 * np.median(d)) & (d < 1.6 * np.median(d))])
        print(f"  raw diffs: {[round(v,1) for v in d]}")
        print(f"  median single pitch: {med:.2f} px -> {med/PITCH_M:.2f} px/m")
    return xs


if __name__ == "__main__":
    p = os.path.join(REFS, "ref_CC-BFO_sjo_stbd.jpg")
    # forward run (behind door1, before overwing): x 1050..1640
    report("stbd FWD x1050-1640", detect(p, 1050, 1640, 940, 1015))
    # aft run (behind wing, before wedge): x 2300..2700
    report("stbd AFT x2300-2700", detect(p, 2300, 2720, 940, 1015))

    q = os.path.join(REFS, "ref_CC-BFO_sjo_wide_port.jpg")
    # port photo rows: need band; aircraft near x 1600..3600, window row ~y?
    # explore two bands wide, filter by shape
    report("port MID (wide scan)", detect(q, 1900, 2900, 1640, 1730))
