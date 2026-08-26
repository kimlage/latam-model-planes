#!/usr/bin/env python3
"""Normalise both DEMs onto one 3601x3601 1-arcsec tile format, for SBGR.

Copernicus COG (3600x3600, float32) -> dem_cop_hgt/  (edges filled from the
neighbouring tile so the mosaic has no seams)
SRTM v3 .hgt                        -> dem_srtm_clean/ (voids filled, spikes
removed)

Difference from ../scenario/prepare_dem.py: the Copernicus COGs are read with
**tifffile**, not rasterio. rasterio is not installed here and pulling it in
forces a numpy major-version upgrade across the whole project - the Santiago
README already warns about that. A Copernicus GLO-30 tile is a plain tiled,
deflate-compressed float32 GeoTIFF; tifffile reads it directly, and the georef
is read off ModelTiepointTag / ModelPixelScaleTag instead of being trusted from
the file name.
"""
import os, glob, itertools
import numpy as np
from scipy.ndimage import median_filter

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKE_THRESHOLD_M = 200.0

# tiles covering ~120 km around SBGR
LATS = [-25, -24, -23]        # SW corner latitudes
LONS = [-48, -47, -46]        # SW corner longitudes


def _read_cop(path):
    """(array, sw_lat, sw_lon) for one Copernicus COG, georef read from tags."""
    import tifffile
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        a = page.asarray().astype(np.float32)
        tie = page.tags["ModelTiepointTag"].value      # (i,j,k, x,y,z)
        scale = page.tags["ModelPixelScaleTag"].value  # (sx, sy, sz)
    west = float(tie[3]); north = float(tie[4])
    sy = float(scale[1]); rows = a.shape[0]
    south = north - sy * rows
    return a, int(round(south)), int(round(west))


def prepare_copernicus():
    try:
        import tifffile                                 # noqa: F401
    except ImportError:
        print("! tifffile not installed - skipping Copernicus normalisation.\n"
              "  python3 -m pip install tifffile")
        return
    src = os.path.join(HERE, "dem_cop"); dst = os.path.join(HERE, "dem_cop_hgt")
    os.makedirs(dst, exist_ok=True)
    cache = {}

    def get(la, lo):
        if (la, lo) not in cache:
            p = os.path.join(src, "Copernicus_DSM_COG_10_S%02d_00_W%03d_00_DEM.tif"
                             % (abs(la), abs(lo)))
            if not os.path.exists(p):
                cache[(la, lo)] = None
            else:
                a, s, w = _read_cop(p)
                if (s, w) != (la, lo):
                    raise SystemExit("%s: georef says S%d W%d, name says S%d W%d"
                                     % (os.path.basename(p), -s, -w, -la, -lo))
                cache[(la, lo)] = a
        return cache[(la, lo)]

    for la, lo in itertools.product(LATS, LONS):
        a = get(la, lo)
        if a is None:
            continue
        out = np.zeros((3601, 3601), dtype=np.float32)
        out[:3600, :3600] = a
        e = get(la, lo + 1);  out[:3600, 3600] = e[:, 0] if e is not None else a[:, -1]
        s = get(la - 1, lo);  out[3600, :3600] = s[0, :] if s is not None else a[-1, :]
        se = get(la - 1, lo + 1)
        out[3600, 3600] = se[0, 0] if se is not None else out[3599, 3600]
        n = "S%02dW%03d.hgt" % (abs(la), abs(lo))
        np.rint(out).astype(">i2").tofile(os.path.join(dst, n))
        print("  copernicus %s  min %d  max %d m"
              % (n[:7], int(out.min()), int(out.max())))


def prepare_srtm():
    dst = os.path.join(HERE, "dem_srtm_clean"); os.makedirs(dst, exist_ok=True)
    total = 0
    for p in sorted(glob.glob(os.path.join(HERE, "dem", "*.hgt"))):
        a = np.fromfile(p, dtype=">i2").reshape(3601, 3601).astype(np.float32)
        a[a == -32768] = np.nan
        med = median_filter(np.nan_to_num(a, nan=0.0), size=3, mode="nearest")
        a = np.where(np.isnan(a), med, a)
        med = median_filter(a, size=3, mode="nearest")
        spike = np.abs(a - med) > SPIKE_THRESHOLD_M
        total += int(spike.sum())
        a = np.where(spike, med, a)
        np.rint(a).astype(">i2").tofile(os.path.join(dst, os.path.basename(p)))
        print("  srtm %s despiked %d px" % (os.path.basename(p)[:7], int(spike.sum())))
    print("  total spikes removed:", total)


if __name__ == "__main__":
    prepare_copernicus()
    prepare_srtm()
