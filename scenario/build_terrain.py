#!/usr/bin/env python3
"""Build the SCL scene heightfields in the local metric frame.

Primary DEM  : Copernicus DEM GLO-30 (WorldDEM-30), 1 arcsec.
Control DEM  : SRTM v3 1 arcsec (NASA/USGS), despiked.

Output: regular grids in the ENU frame defined by lib/frame.py, z in metres
above the 474 m datum, sampled where the local vertical through each grid
node meets the terrain (so Earth curvature is baked into z, as it must be
for a 130 km-wide scene).
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
from srtm import Mosaic
import frame as F

OUT = os.path.join(HERE, "terrain")
os.makedirs(OUT, exist_ok=True)


def sample_terrain(dem, enu, e, n, iters=3, fill_sea=False):
    """ENU (e,n) -> z, following the local vertical down to the terrain.

    fill_sea: outside the DEM tiles (the Pacific) treat the surface as 0 m
    orthometric instead of NaN, so the far grid closes cleanly at sea level.
    """
    shp = np.shape(e)
    u = np.zeros(shp, dtype=np.float64)
    lat = lon = None
    for _ in range(iters):
        lat, lon, h = enu.to_geodetic(e, n, u)
        hd = dem.sample_bilinear(lat, lon)
        if fill_sea:
            hd = np.where(np.isnan(hd), 0.0, hd)
        u = u + (hd - h)
    return u, lat, lon


def build(dem, enu, x0, x1, y0, y1, step, label, chunk_rows=64, fill_sea=False):
    xs = np.arange(x0, x1 + 0.5 * step, step, dtype=np.float64)
    ys = np.arange(y0, y1 + 0.5 * step, step, dtype=np.float64)
    nx, ny = len(xs), len(ys)
    z = np.empty((ny, nx), dtype=np.float32)
    latmin = lonmin = 1e9; latmax = lonmax = -1e9
    for r0 in range(0, ny, chunk_rows):
        r1 = min(r0 + chunk_rows, ny)
        E, N = np.meshgrid(xs, ys[r0:r1])
        u, lat, lon = sample_terrain(dem, enu, E, N, fill_sea=fill_sea)
        z[r0:r1] = u.astype(np.float32)
        latmin = min(latmin, np.nanmin(lat)); latmax = max(latmax, np.nanmax(lat))
        lonmin = min(lonmin, np.nanmin(lon)); lonmax = max(lonmax, np.nanmax(lon))
        print("  %s  row %d/%d" % (label, r1, ny), end="\r", flush=True)
    print()
    nan = int(np.isnan(z).sum())
    if nan:
        print("  WARNING: %d NaN nodes" % nan)
    return dict(z=z, xs=xs, ys=ys, nx=nx, ny=ny, step=step,
                lat_range=[latmin, latmax], lon_range=[lonmin, lonmax], nan=nan)


def main():
    dem = Mosaic(os.path.join(HERE, "dem_cop_hgt"))
    enu = F.enu()

    # --- ENU bounds of the required geographic box -----------------------
    req = dict(lat=(-33.8, -32.9), lon=(-71.2, -69.8))
    cl, cn = [], []
    for la in req["lat"]:
        for lo in req["lon"]:
            e, n, _ = enu.from_geodetic(np.array([la]), np.array([lo]), np.array([0.0]))
            cl.append(float(e[0])); cn.append(float(n[0]))
    print("required box in ENU: x %.0f..%.0f  y %.0f..%.0f m"
          % (min(cl), max(cl), min(cn), max(cn)))

    grids = {}
    # Full scene, 60 m. Rounded outward from the required box.
    S = 60.0
    x0 = np.floor(min(cl) / S) * S; x1 = np.ceil(max(cl) / S) * S
    y0 = np.floor(min(cn) / S) * S; y1 = np.ceil(max(cn) / S) * S
    grids["terrain_scl_60m"] = build(dem, enu, x0, x1, y0, y1, S, "60m")

    # Near field around the aerodrome, 30 m.
    grids["terrain_scl_near_30m"] = build(dem, enu, -15000, 15000, -15000, 15000,
                                           30.0, "30m")

    # Far field, 180 m. The southern skyline sits 70-150 km out, well beyond the
    # required box, so without this tier the horizon south of the field is simply
    # missing. West is capped at 110 km by the DEM tiles - beyond that is Pacific,
    # filled at sea level.
    grids["terrain_scl_far_180m"] = build(dem, enu, -110000, 150000,
                                            -150000, 150000, 180.0, "180m",
                                            fill_sea=True)

    meta = dict(
        frame=dict(
            origin_lat=F.LAT0, origin_lon=F.LON0,
            origin_desc="threshold of RWY 17L, SCEL - start of the takeoff roll (south flow)",
            datum_m_amsl=F.DATUM_M,
            datum_desc="z = 0 at 474.0 m AMSL (published SCEL aerodrome elevation, 1555 ft)",
            axes="x=East, y=North, z=Up; metres; WGS84 local ENU tangent frame",
            note=("z already contains the Earth-curvature drop: a point 90 km away "
                  "sits ~600 m lower than a flat-plane approximation would put it. "
                  "This is correct and required for the Andes silhouette."),
        ),
        dem=dict(
            primary="Copernicus DEM GLO-30 (WorldDEM-30), 1 arcsec, EGM2008 orthometric",
            control="SRTM v3 1 arcsec (NASA/USGS), EGM96 orthometric",
        ),
        grids={},
    )
    for name, g in grids.items():
        np.save(os.path.join(OUT, name + ".npy"), g["z"])
        meta["grids"][name] = dict(
            file=name + ".npy", dtype="float32", shape=[g["ny"], g["nx"]],
            step_m=g["step"],
            x_min_m=float(g["xs"][0]), x_max_m=float(g["xs"][-1]),
            y_min_m=float(g["ys"][0]), y_max_m=float(g["ys"][-1]),
            row_order="row 0 = y_min (south); column 0 = x_min (west)",
            z_min_m=float(np.nanmin(g["z"])), z_max_m=float(np.nanmax(g["z"])),
            z_units="metres above the 474 m datum",
            lat_range=g["lat_range"], lon_range=g["lon_range"], nan_nodes=g["nan"],
        )
        # 16-bit PNG twin, for displacement workflows
        z = np.nan_to_num(g["z"], nan=float(np.nanmin(g["z"])))
        zmin, zmax = float(z.min()), float(z.max())
        png = np.rint((z - zmin) / (zmax - zmin) * 65535.0).astype(np.uint16)
        try:
            from PIL import Image
            Image.fromarray(png[::-1], mode="I;16").save(os.path.join(OUT, name + ".png"))
            meta["grids"][name]["png"] = dict(
                file=name + ".png", bitdepth=16,
                decode="z_m = png/65535 * (z_max_png - z_min_png) + z_min_png",
                z_min_png=zmin, z_max_png=zmax,
                row_order="PNG row 0 = y_max (north), i.e. flipped vs the .npy",
            )
        except Exception as ex:
            print("  PNG skipped:", ex)

    # runway ends in the frame, so siblings can re-base trivially
    rw = {}
    for k, v in F.RUNWAYS.items():
        e, n, _ = enu.from_geodetic(np.array([v["lat"]]), np.array([v["lon"]]),
                                    np.array([v["elev_ft"] * F.FT]))
        rw[k] = dict(x_m=round(float(e[0]), 2), y_m=round(float(n[0]), 2),
                     z_m=round(v["elev_ft"] * F.FT - F.DATUM_M, 2),
                     lat=v["lat"], lon=v["lon"], hdg_true=v["hdg_true"])
    e, n, _ = enu.from_geodetic(np.array([F.ARP["lat"]]), np.array([F.ARP["lon"]]),
                                np.array([F.ARP["elev_ft"] * F.FT]))
    rw["ARP"] = dict(x_m=round(float(e[0]), 2), y_m=round(float(n[0]), 2),
                     z_m=round(F.ARP["elev_ft"] * F.FT - F.DATUM_M, 2),
                     lat=F.ARP["lat"], lon=F.ARP["lon"])
    meta["reference_points_enu"] = rw

    with open(os.path.join(OUT, "terrain_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta["grids"], indent=2)[:2000])
    print("\nreference points (ENU m):")
    for k, v in rw.items():
        print("  %-4s x=%9.1f y=%9.1f z=%6.1f" % (k, v["x_m"], v["y_m"], v["z_m"]))


if __name__ == "__main__":
    main()
