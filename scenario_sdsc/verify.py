#!/usr/bin/env python3
"""Check the delivered heightfields against the DEM-derived horizon, and
against the published survey.

The heightfield is what actually becomes mesh in Blender. Resampling the DEM to
a 60/180 m grid could quietly change the profile, so this ray-casts the
*delivered grid* and compares it against the profile computed from the
full-resolution DEM.

Elevation angles here are purely geometric (no refraction), because the grid's
z already carries the true curvature drop - so they are compared against the
profile's elev_deg_no_refraction column.
"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import frame as F
from srtm import Mosaic
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
    z_obs = obs_amsl - F.DATUM_M

    s30, _ = grid_sampler("terrain_sdsc_near_30m")
    s60, m60 = grid_sampler("terrain_sdsc_60m")
    s180, _ = grid_sampler("terrain_sdsc_far_180m")
    r = np.arange(1500.0, 129000.0, 30.0)

    def combined(x, y):
        a = s30(x, y); b = s60(x, y); c = s180(x, y)
        return np.where(np.isnan(a), np.where(np.isnan(b), c, b), a)

    print("1. delivered grid vs full-resolution DEM horizon")
    for label, fn in (("60 m grid alone", s60),
                      ("30 + 60 + 180 m stack", combined)):
        diffs = []
        for row in prof["profile"]:
            az = np.radians(row["azimuth_deg"])
            x = np.sin(az) * r; y = np.cos(az) * r
            ang = np.degrees(np.arctan2(fn(x, y) - z_obs, r))
            diffs.append(float(np.nanmax(ang)) - row["elev_deg_no_refraction"])
        diffs = np.array(diffs)
        print("   %-24s mean %+.3f  rms %.3f  max|diff| %.3f deg"
              % (label, diffs.mean(), np.sqrt((diffs ** 2).mean()),
                 np.abs(diffs).max()))

    print("\n2. how wide is the horizon band at all?")
    a = np.array([row["elev_deg"] for row in prof["profile"]])
    nf = np.array([row["near_field_elev_deg"] for row in prof["profile"]])
    print("   terrain horizon      : %+.3f .. %+.3f deg  (band %.3f deg)"
          % (a.min(), a.max(), a.max() - a.min()))
    print("   with the near field  : %+.3f .. %+.3f deg  (band %.3f deg)"
          % (min(a.min(), nf.min()), max(a.max(), nf.max()),
             max(a.max(), nf.max()) - min(a.min(), nf.min())))
    print("   near field exceeds the terrain horizon at %d of %d azimuths"
          % (int((nf > a).sum()), len(a)))
    print("   -> for comparison, SCL/SCEL: 3.2-4.9 deg in the east sector,")
    print("      max 4.63 deg at az 75. SDSC has no skyline.")

    print("\n3. aerodrome elevation against both DEMs")
    cop = Mosaic(os.path.join(HERE, "dem_cop_hgt"))
    srt = Mosaic(os.path.join(HERE, "dem_srtm_clean"))
    for k, v in F.RUNWAYS.items():
        la = np.array([v["lat"]]); lo = np.array([v["lon"]])
        pub = v["elev_ft"] * F.FT
        print("   THR %-3s published %7.1f  Copernicus %7.1f  SRTM %7.1f  "
              "(spread %.1f m)"
              % (k, pub, cop.sample_bilinear(la, lo)[0],
                 srt.sample_bilinear(la, lo)[0],
                 max(cop.sample_bilinear(la, lo)[0], srt.sample_bilinear(la, lo)[0],
                     pub) -
                 min(cop.sample_bilinear(la, lo)[0], srt.sample_bilinear(la, lo)[0],
                     pub)))
    d02 = F.RUNWAYS["02"]["elev_ft"] * F.FT
    d20 = F.RUNWAYS["20"]["elev_ft"] * F.FT
    c02 = float(cop.sample_bilinear(np.array([F.RUNWAYS["02"]["lat"]]),
                                    np.array([F.RUNWAYS["02"]["lon"]]))[0])
    c20 = float(cop.sample_bilinear(np.array([F.RUNWAYS["20"]["lat"]]),
                                    np.array([F.RUNWAYS["20"]["lon"]]))[0])
    print("   runway slope: published %.1f m fall over 1620 m (%.2f%%); "
          "Copernicus %.1f m (%.2f%%)"
          % (d02 - d20, 100 * (d02 - d20) / 1620.0, c02 - c20,
             100 * (c02 - c20) / 1620.0))

    print("\n4. threshold geometry against the published declared distances")
    enu = F.enu()
    def xy(lat, lon):
        e, n, _ = enu.from_geodetic(np.array([lat]), np.array([lon]),
                                    np.array([0.0]))
        return float(e[0]), float(n[0])
    a2 = xy(F.RUNWAYS["02"]["lat"], F.RUNWAYS["02"]["lon"])
    a20 = xy(F.RUNWAYS["20"]["lat"], F.RUNWAYS["20"]["lon"])
    d = math.hypot(a20[0] - a2[0], a20[1] - a2[1])
    brg = math.degrees(math.atan2(a20[0] - a2[0], a20[1] - a2[1])) % 360
    print("   THR 02 -> THR 20 measures %.2f m; published 1720 - 52 - 48 = 1620 m"
          "  (delta %.2f m)" % (d, d - 1620.0))
    print("   true bearing %.3f deg; + VAR %.1f W = %.1f deg magnetic; "
          "published final course 023 deg MAG (delta %.1f deg)"
          % (brg, F.MAG_VAR_DEG_W, brg + F.MAG_VAR_DEG_W,
             brg + F.MAG_VAR_DEG_W - 23.0))
    p1 = xy(F.PAVEMENT_ENDS["south_02"]["lat"], F.PAVEMENT_ENDS["south_02"]["lon"])
    p2 = xy(F.PAVEMENT_ENDS["north_20"]["lat"], F.PAVEMENT_ENDS["north_20"]["lon"])
    print("   OSM centreline end-to-end %.1f m vs published pavement 1720 m "
          "(OSM is %.1f m short)"
          % (math.hypot(p2[0] - p1[0], p2[1] - p1[1]),
             1720.0 - math.hypot(p2[0] - p1[0], p2[1] - p1[1])))


if __name__ == "__main__":
    main()
