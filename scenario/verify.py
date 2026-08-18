#!/usr/bin/env python3
"""Check the delivered heightfield against the DEM-derived horizon.

The heightfield is what actually becomes mesh in Blender. Resampling the DEM
to a 60 m grid could shave the ridge crests and quietly flatten the skyline,
so this ray-casts the *delivered grid* and compares it against the profile
computed from the full-resolution DEM.

Elevation angles here are purely geometric (no refraction), because the grid's
z already carries the true curvature drop - so they are compared against the
profile's elev_deg_no_refraction column.
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
OUT = os.path.join(HERE, "terrain")


def grid_sampler(name):
    m = json.load(open(os.path.join(OUT, "terrain_meta.json")))["grids"][name]
    z = np.load(os.path.join(OUT, m["file"])).astype(np.float64)
    x0, y0, s = m["x_min_m"], m["y_min_m"], m["step_m"]
    ny, nx = z.shape

    def sample(x, y):
        fx = (x - x0) / s; fy = (y - y0) / s
        i0 = np.floor(fy).astype(int); j0 = np.floor(fx).astype(int)
        ok = (i0 >= 0) & (i0 < ny - 1) & (j0 >= 0) & (j0 < nx - 1)
        i0 = np.clip(i0, 0, ny - 2); j0 = np.clip(j0, 0, nx - 2)
        ty = fy - i0; tx = fx - j0
        v = (z[i0, j0] * (1 - tx) * (1 - ty) + z[i0, j0 + 1] * tx * (1 - ty) +
             z[i0 + 1, j0] * (1 - tx) * ty + z[i0 + 1, j0 + 1] * tx * ty)
        return np.where(ok, v, np.nan)
    return sample, m


def main():
    prof = json.load(open(os.path.join(OUT, "horizon_5deg.json")))
    obs_amsl = prof["observer"]["height_m_amsl_copernicus"]
    z_obs = obs_amsl - 474.0                       # observer in frame units

    s60, m = grid_sampler("terrain_scl_60m")
    s180, _ = grid_sampler("terrain_scl_far_180m")
    r = np.arange(3000.0, 150000.0, 30.0)

    def combined(x, y):
        """finest grid available at each sample"""
        a = s60(x, y); b = s180(x, y)
        return np.where(np.isnan(a), b, a)

    for label, fn in (("60 m grid alone", s60), ("60 m + 180 m far field", combined)):
        diffs = []
        for row in prof["profile"]:
            az = np.radians(row["azimuth_deg"])
            x = np.sin(az) * r; y = np.cos(az) * r
            ang = np.degrees(np.arctan2(fn(x, y) - z_obs, r))
            diffs.append(float(np.nanmax(ang)) - row["elev_deg_no_refraction"])
        diffs = np.array(diffs)
        print("%-26s mean %+.3f  rms %.3f  max|diff| %.3f deg"
              % (label, diffs.mean(), np.sqrt((diffs ** 2).mean()),
                 np.abs(diffs).max()))
        if "far" in label:
            print("   per-azimuth residual, south sector:")
            for row, d in zip(prof["profile"], diffs):
                if 145 <= row["azimuth_deg"] <= 200:
                    print("     az %3.0f  %+.3f deg" % (row["azimuth_deg"], d))
            east = np.array([d for row, d in zip(prof["profile"], diffs)
                             if 45 <= row["azimuth_deg"] <= 125])
            print("   east sector (45-125, the Andes wall): rms %.3f  max|diff| %.3f deg"
                  % (np.sqrt((east ** 2).mean()), np.abs(east).max()))

    # how much of the required geographic box does the grid cover?
    g = m
    print("\ngrid covers lat %.4f..%.4f, lon %.4f..%.4f (required -33.8..-32.9, -71.2..-69.8)"
          % (g["lat_range"][0], g["lat_range"][1], g["lon_range"][0], g["lon_range"][1]))
    ok = (g["lat_range"][0] <= -33.8 and g["lat_range"][1] >= -32.9 and
          g["lon_range"][0] <= -71.2 and g["lon_range"][1] >= -69.8)
    print("  required box fully covered:", ok)


if __name__ == "__main__":
    main()
