#!/usr/bin/env python3
"""Build the SBGR scene heightfields in the local metric frame.

Primary DEM  : Copernicus DEM GLO-30 (WorldDEM-30), 1 arcsec.
Control DEM  : SRTM v3 1 arcsec (NASA/USGS).

Output: regular grids in the ENU frame defined by lib/frame.py, z in metres
above the 750 m datum, sampled where the local vertical through each grid node
meets the terrain - so Earth curvature is baked into z, exactly as at SCL and
SDSC. Here the plate is neither Santiago's wall of Andes nor Sao Carlos's
empty cane plateau: Guarulhos sits in the Rio Baquirivu-Guacu valley with the
Serra da Cantareira rising 10 km to the north-west, the Serra do Mar falling
to the Atlantic 55-60 km south-east (the far tier crosses the coastline - the
first scene in this project whose plate contains ocean), and the Serra da
Mantiqueira standing 80-110 km to the north-east. Both the relief AND the
curvature drop matter.
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
from srtm import Mosaic
import frame as F

OUT = os.path.join(HERE, "terrain")
os.makedirs(OUT, exist_ok=True)


def sample_terrain(dem, enu, e, n, iters=3):
    """ENU (e,n) -> z, following the local vertical down to the terrain."""
    shp = np.shape(e)
    u = np.zeros(shp, dtype=np.float64)
    lat = lon = None
    for _ in range(iters):
        lat, lon, h = enu.to_geodetic(e, n, u)
        hd = dem.sample_bilinear(lat, lon)
        u = u + (hd - h)
    return u, lat, lon


def build(dem, enu, x0, x1, y0, y1, step, label, chunk_rows=64):
    xs = np.arange(x0, x1 + 0.5 * step, step, dtype=np.float64)
    ys = np.arange(y0, y1 + 0.5 * step, step, dtype=np.float64)
    nx, ny = len(xs), len(ys)
    z = np.empty((ny, nx), dtype=np.float32)
    latmin = lonmin = 1e9; latmax = lonmax = -1e9
    for r0 in range(0, ny, chunk_rows):
        r1 = min(r0 + chunk_rows, ny)
        E, N = np.meshgrid(xs, ys[r0:r1])
        u, lat, lon = sample_terrain(dem, enu, E, N)
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

    grids = {}
    # Near field around the aerodrome, 30 m. Reaches the Cantareira crest.
    grids["terrain_sbgr_near_30m"] = build(dem, enu, -15000, 15000,
                                           -15000, 15000, 30.0, "30m")
    # Mid field, 60 m: all of Greater Sao Paulo, the Serra do Mar crest.
    grids["terrain_sbgr_60m"] = build(dem, enu, -50000, 50000,
                                      -50000, 50000, 60.0, "60m")
    # Far field, 180 m, out to 120 km: the Mantiqueira skyline NE, and the
    # Atlantic SE - the ocean is the one surface where the curvature drop is
    # the whole story, and it is in this tier.
    grids["terrain_sbgr_far_180m"] = build(dem, enu, -120000, 120000,
                                           -120000, 120000, 180.0, "180m")

    meta = dict(
        frame=dict(
            origin_lat=F.LAT0, origin_lon=F.LON0,
            origin_desc="published threshold of RWY 10L, SBGR "
                        "(whole-second precision, +/- ~30 m; see "
                        "sbgr_aip_survey.json)",
            datum_m_amsl=F.DATUM_M,
            datum_desc="z = 0 at 750.0 m AMSL (published SBGR aerodrome "
                       "elevation, 2461 ft)",
            axes="x=East, y=North, z=Up; metres; WGS84 local ENU tangent frame",
            note=("z already contains the Earth-curvature drop: a point 60 km "
                  "away sits ~282 m lower than a flat-plane approximation "
                  "would put it. Over the Atlantic corner of the far tier "
                  "that drop is the only thing in z."),
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
            z_units="metres above the 750 m datum",
            lat_range=g["lat_range"], lon_range=g["lon_range"], nan_nodes=g["nan"],
        )
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

    rw = {}
    for k, v in F.RUNWAYS.items():
        e, n, _ = enu.from_geodetic(np.array([v["lat"]]), np.array([v["lon"]]),
                                    np.array([v["elev_ft"] * F.FT]))
        rw["THR" + k] = dict(x_m=round(float(e[0]), 2), y_m=round(float(n[0]), 2),
                             z_m=round(v["elev_ft"] * F.FT - F.DATUM_M, 2),
                             lat=v["lat"], lon=v["lon"], hdg_true=v["hdg_true"],
                             source="AISWEB/ROTAER declared distances + SBGR "
                                    "ADC (coords, whole seconds) + IAC (THR "
                                    "elevations)")
    e, n, _ = enu.from_geodetic(np.array([F.ARP["lat"]]), np.array([F.ARP["lon"]]),
                                np.array([F.ARP["elev_ft"] * F.FT]))
    rw["ARP"] = dict(x_m=round(float(e[0]), 2), y_m=round(float(n[0]), 2),
                     z_m=round(F.ARP["elev_ft"] * F.FT - F.DATUM_M, 2),
                     lat=F.ARP["lat"], lon=F.ARP["lon"],
                     source="ROTAER 23 26 08S/046 28 23W (whole-second precision)")
    meta["reference_points_enu"] = rw

    with open(os.path.join(OUT, "terrain_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta["grids"], indent=2)[:1400])
    print("\nreference points (ENU m):")
    for k, v in rw.items():
        print("  %-7s x=%9.1f y=%9.1f z=%6.1f" % (k, v["x_m"], v["y_m"], v["z_m"]))


if __name__ == "__main__":
    main()
