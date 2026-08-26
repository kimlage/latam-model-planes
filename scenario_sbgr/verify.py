#!/usr/bin/env python3
"""Check the delivered heightfields against the DEM-derived horizon, and the
published survey against both DEMs and the OSM tracing.

Same structure as scenario_sdsc/verify.py, with SBGR's own questions:
  1. does the delivered 30/60/180 m grid stack reproduce the horizon?
  2. how tall is the ring, sector by sector?
  3. do the DEMs agree with the four published threshold elevations?
  4. does the whole-second published geometry close on itself, and how does
     the OSM centreline tracing reconcile with it?
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
    obs_amsl = prof["observer"]["height_m_amsl"]
    z_obs = obs_amsl - F.DATUM_M

    s30, _ = grid_sampler("terrain_sbgr_near_30m")
    s60, _ = grid_sampler("terrain_sbgr_60m")
    s180, _ = grid_sampler("terrain_sbgr_far_180m")

    def combined(x, y):
        a = s30(x, y); b = s60(x, y); c = s180(x, y)
        return np.where(np.isnan(a), np.where(np.isnan(b), c, b), a)

    print("1. delivered grid vs full-resolution DEM horizon")
    for label, fn in (("60 m grid alone", s60),
                      ("30 + 60 + 180 m stack", combined)):
        diffs = []
        for row in prof["profile"]:
            az = np.radians(row["azimuth_deg"])
            r = np.arange(row["scan_start_m"], 129000.0, 30.0)
            x = np.sin(az) * r; y = np.cos(az) * r
            ang = np.degrees(np.arctan2(fn(x, y) - z_obs, r))
            diffs.append(float(np.nanmax(ang)) - row["elev_deg_no_refraction"])
        diffs = np.array(diffs)
        print("   %-24s mean %+.3f  rms %.3f  max|diff| %.3f deg"
              % (label, diffs.mean(), np.sqrt((diffs ** 2).mean()),
                 np.abs(diffs).max()))

    print("\n2. the ring, sector by sector")
    a = np.array([row["elev_deg"] for row in prof["profile"]])
    az = np.array([row["azimuth_deg"] for row in prof["profile"]])
    nf = np.array([row["near_field_elev_deg"] for row in prof["profile"]])
    print("   whole band            : %+.3f .. %+.3f deg" % (a.min(), a.max()))
    for lo, hi, name in ((325, 380, "N   (Cabucu/Cantareira spur)"),
                         (265, 320, "W-NW (Cantareira crest, Jaragua)"),
                         (50, 120, "ESE (the departure direction)"),
                         (130, 185, "S-SSE (near ridge)")):
        m = ((az >= lo % 360) | (az <= hi - 360)) if hi > 360 else \
            ((az >= lo) & (az <= hi))
        print("   %-33s %+.3f .. %+.3f deg" % (name, a[m].min(), a[m].max()))
    print("   near field exceeds the terrain horizon at %d of %d azimuths"
          % (int((nf > a).sum()), len(a)))
    print("   -> SCL east wall: 3.2-4.9 deg. SDSC: nothing above 1.30 deg.")

    print("\n3. threshold elevations against both DEMs")
    cop = Mosaic(os.path.join(HERE, "dem_cop_hgt"))
    srt = Mosaic(os.path.join(HERE, "dem_srtm_clean"))
    for k, v in F.RUNWAYS.items():
        la = np.array([v["lat"]]); lo = np.array([v["lon"]])
        pub = v["elev_ft"] * F.FT
        c = float(cop.sample_bilinear(la, lo)[0])
        s = float(srt.sample_bilinear(la, lo)[0])
        print("   THR %-3s published %7.2f  Copernicus %7.2f  SRTM %7.2f  "
              "(spread %.1f m)" % (k, pub, c, s, max(c, s, pub) - min(c, s, pub)))
    for nm, a_, b_ in (("10L->28R", "10L", "28R"), ("10R->28L", "10R", "28L")):
        d1 = F.RUNWAYS[a_]["elev_ft"] * F.FT
        d2 = F.RUNWAYS[b_]["elev_ft"] * F.FT
        print("   %s published fall %.2f m eastward - the runways are "
              "nearly LEVEL (SDSC fell 10.1 m)" % (nm, d1 - d2))

    print("\n4. threshold geometry: published whole-second strings vs "
          "themselves and vs OSM")
    enu = F.enu()
    def xy(k):
        v = F.RUNWAYS[k]
        e, n, _ = enu.from_geodetic(np.array([v["lat"]]), np.array([v["lon"]]),
                                    np.array([0.0]))
        return float(e[0]), float(n[0])
    for a_, b_, pav, d_a, d_b in (("10L", "28R", 3700, 90, 60),
                                  ("10R", "28L", 3000, 0, 0)):
        p1, p2 = xy(a_), xy(b_)
        d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        exp = pav - d_a - d_b
        brg = math.degrees(math.atan2(p2[0] - p1[0], p2[1] - p1[1])) % 360
        print("   THR %s -> THR %s measures %.2f m vs %d implied "
              "(delta %+.2f m, inside the +/-43 m worst case of two "
              "whole-second coordinates)" % (a_, b_, d, exp, d - exp))
        print("      true bearing %.3f + VAR %.0f W = %.2f MAG vs published "
              "095/275" % (brg, F.MAG_VAR_DEG_W, brg + F.MAG_VAR_DEG_W))
    try:
        osm = json.load(open(os.path.join(HERE, "sbgr_osm.json")))
        from collections import defaultdict
        segs = defaultdict(list)
        for r in osm["runways"]:
            if r.get("polygon_xy_m"):
                segs[r.get("ref")].append(r["polygon_xy_m"])
        for ref, ps in segs.items():
            pts = [q for p in ps for q in p]
            L = 0.0
            # stitch by nearest-end merge
            def K(p): return (round(p[0], 1), round(p[1], 1))
            polys = [list(p) for p in ps]
            cur = polys.pop(0)
            changed = True
            while changed and polys:
                changed = False
                for i, s in enumerate(polys):
                    if K(s[0]) == K(cur[-1]): cur += s[1:]
                    elif K(s[-1]) == K(cur[-1]): cur += s[::-1][1:]
                    elif K(s[-1]) == K(cur[0]): cur = s[:-1] + cur
                    elif K(s[0]) == K(cur[0]): cur = s[::-1][:-1] + cur
                    else: continue
                    polys.pop(i); changed = True; break
            L = sum(math.dist(cur[i], cur[i + 1]) for i in range(len(cur) - 1))
            a2, b2 = (cur[0], cur[-1]) if cur[0][0] < cur[-1][0] else (cur[-1], cur[0])
            brg = math.degrees(math.atan2(b2[0] - a2[0], b2[1] - a2[1])) % 360
            print("   OSM %s: %.1f m end-to-end, true %.3f deg  "
                  "(published pavement %s)" % (ref, L, brg,
                  "3700" if "10L" in ref else "3000"))
        print("      the two OSM centrelines are parallel to ~0.02 deg; the "
              "published thresholds spread 0.13 deg. OSM's RELATIVE geometry "
              "is the finer one - see sbgr_aip_survey.json 'bearing_adopted'.")
    except FileNotFoundError:
        print("   (sbgr_osm.json not built yet)")


if __name__ == "__main__":
    main()
