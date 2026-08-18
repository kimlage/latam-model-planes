#!/usr/bin/env python3
"""Horizon (skyline) profile seen from the SCL takeoff point.

For each azimuth, scan radially over the DEM and take the maximum apparent
elevation angle, on a spherical Earth with standard atmospheric refraction
(k = 0.13, i.e. effective radius 7/6 R). Computed independently from the
Copernicus GLO-30 and the despiked SRTM v3 DEMs so the two can be compared.
"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
from srtm import Mosaic
import frame as F

OUT = os.path.join(HERE, "terrain")
os.makedirs(OUT, exist_ok=True)

# Gaussian mean radius of curvature at the origin latitude (WGS84)
A = 6378137.0; E2 = 0.00669437999014
_s = math.sin(math.radians(F.LAT0))
_M = A * (1 - E2) / (1 - E2 * _s * _s) ** 1.5
_N = A / math.sqrt(1 - E2 * _s * _s)
R_GEO = math.sqrt(_M * _N)
K_REFR = 0.13
R_EFF = R_GEO / (1 - K_REFR)

EYE_M = 5.0                # eye/cockpit height above the runway surface
D_MAX = 160000.0           # scan range, m
D_STEP = 20.0              # radial step, m
# The aerodrome and its immediate surroundings are graded flat: terrain stays
# within ~20 m of field level out to 3 km, and a *surface* DEM there carries
# buildings and radar noise rather than terrain. Nothing inside 3 km forms the
# mountain skyline, so the scan starts there. The excluded near field is
# reported in the output as near_field_max_elev_deg so the cut is auditable.
D_MIN = 3000.0


def ray_latlon(az_deg, d):
    """Great-circle destination(s) from the origin."""
    lat1 = math.radians(F.LAT0); lon1 = math.radians(F.LON0)
    A_ = np.radians(az_deg)[:, None]
    dl = (d / R_GEO)[None, :]
    sla = math.sin(lat1); cla = math.cos(lat1)
    lat2 = np.arcsin(sla * np.cos(dl) + cla * np.sin(dl) * np.cos(A_))
    lon2 = lon1 + np.arctan2(np.sin(A_) * np.sin(dl) * cla,
                             np.cos(dl) - sla * np.sin(lat2))
    return np.degrees(lat2), np.degrees(lon2)


def field_height(dem, radius=1500.0):
    """Median DEM height over the graded aerodrome -> the surface the observer
    actually stands on, in that DEM's own vertical reference."""
    az = np.arange(0, 360, 2.0)
    d = np.arange(0.0, radius, 20.0)
    lat, lon = ray_latlon(az, d)
    h = dem.sample_bilinear(lat.ravel(), lon.ravel())
    return float(np.nanmedian(h))


def elev_angle(h_t, d, h_obs, refraction=True, k=None):
    """Apparent elevation angle (deg) of terrain height h_t at distance d."""
    if k is not None:
        R = R_GEO / (1 - k)
    else:
        R = R_EFF if refraction else R_GEO
    th = d / R
    rt = R + h_t
    ro = R + h_obs
    return np.degrees(np.arctan2(rt * np.cos(th) - ro, rt * np.sin(th)))


def profile(dem, az_deg, chunk=40, refraction=True, h_obs=None, d_min=None,
            d_max=None):
    """-> (angle_deg, dist_m, height_m, lat, lon) arrays, one entry per azimuth."""
    if h_obs is None:
        h_obs = field_height(dem) + EYE_M
    d = np.arange(D_MIN if d_min is None else d_min,
                  (D_MAX if d_max is None else d_max) + D_STEP, D_STEP)
    na = len(az_deg)
    out_a = np.full(na, -90.0); out_d = np.zeros(na)
    out_h = np.zeros(na); out_lat = np.zeros(na); out_lon = np.zeros(na)
    for i0 in range(0, na, chunk):
        i1 = min(i0 + chunk, na)
        lat, lon = ray_latlon(az_deg[i0:i1], d)
        h = dem.sample_bilinear(lat.ravel(), lon.ravel()).reshape(lat.shape)
        ang = elev_angle(h, d[None, :], h_obs, refraction)
        ang = np.where(np.isnan(ang), -90.0, ang)
        j = np.argmax(ang, axis=1)
        r = np.arange(i1 - i0)
        out_a[i0:i1] = ang[r, j]
        out_d[i0:i1] = d[j]
        out_h[i0:i1] = h[r, j]
        out_lat[i0:i1] = lat[r, j]
        out_lon[i0:i1] = lon[r, j]
        print("  az %.1f/%.0f" % (az_deg[i1 - 1], az_deg[-1]), end="\r", flush=True)
    print()
    return out_a, out_d, out_h, out_lat, out_lon


def main():
    cop = Mosaic(os.path.join(HERE, "dem_cop_hgt"))
    srtm = Mosaic(os.path.join(HERE, "dem_srtm_clean"))

    az5 = np.arange(0.0, 360.0, 5.0)
    azf = np.arange(0.0, 360.0, 0.1)

    hf_c = field_height(cop); hf_s = field_height(srtm)
    ho_c = hf_c + EYE_M; ho_s = hf_s + EYE_M
    print("aerodrome surface: Copernicus %.1f m, SRTM %.1f m AMSL "
          "(published 474.0) -> observer at %.1f / %.1f"
          % (hf_c, hf_s, ho_c, ho_s))

    print("5-degree profile (Copernicus):")
    c5 = profile(cop, az5, h_obs=ho_c)
    print("5-degree profile (SRTM control):")
    s5 = profile(srtm, az5, h_obs=ho_s)
    print("fine 0.1-degree profile (Copernicus):")
    cf = profile(cop, azf, h_obs=ho_c)

    # no-refraction variant, to show the sensitivity
    print("5-degree profile, no refraction:")
    n5 = profile(cop, az5, refraction=False, h_obs=ho_c)

    # audit: what was excluded by starting the scan at D_MIN
    print("near-field audit (60 m .. D_MIN) - what the exclusion removes:")
    nf = profile(cop, az5, h_obs=ho_c, d_min=60.0, d_max=D_MIN - D_STEP)
    nf_in = nf[0]
    dominates = int((nf_in > c5[0]).sum())          # per-azimuth, the real test
    print("  excluded near field peaks at %.3f deg (max object %+.1f m above the "
          "observer); it exceeds the mountain horizon at %d of %d azimuths"
          % (nf_in.max(), np.nanmax(nf[2]) - ho_c, dominates, len(az5)))

    diff = c5[0] - s5[0]
    print("\nCopernicus vs SRTM horizon angle: max |diff| %.3f deg, rms %.3f deg"
          % (np.abs(diff).max(), np.sqrt((diff ** 2).mean())))

    rows = []
    for i, a in enumerate(az5):
        rows.append(dict(
            azimuth_deg=round(float(a), 1),
            elev_deg=round(float(c5[0][i]), 4),
            elev_deg_no_refraction=round(float(n5[0][i]), 4),
            elev_deg_srtm_control=round(float(s5[0][i]), 4),
            dist_km=round(float(c5[1][i]) / 1000.0, 2),
            height_m_amsl=round(float(c5[2][i]), 1),
            lat=round(float(c5[3][i]), 5),
            lon=round(float(c5[4][i]), 5),
        ))
    meta = dict(
        observer=dict(lat=F.LAT0, lon=F.LON0,
                      enu=[0.0, 0.0, EYE_M],
                      eye_height_m=EYE_M,
                      height_m_amsl_copernicus=round(ho_c, 1),
                      height_m_amsl_srtm=round(ho_s, 1),
                      aerodrome_surface_m_amsl=dict(
                          copernicus=round(hf_c, 1), srtm=round(hf_s, 1),
                          published=F.DATUM_M),
                      desc="RWY 17L threshold, SCEL - the scene origin"),
        method=dict(
            radial_step_m=D_STEP, max_range_km=D_MAX / 1000.0,
            earth_radius_m=round(R_GEO, 1),
            refraction_coefficient=K_REFR,
            effective_radius_m=round(R_EFF, 1),
            angle=("apparent elevation angle on a spherical Earth of effective "
                   "radius R/(1-k); positive = above the astronomical horizon"),
            azimuth="degrees true, 0 = North, 90 = East, clockwise",
            min_range_m=D_MIN,
            min_range_rationale=(
                "the aerodrome is graded flat and a surface DEM there carries "
                "buildings, not terrain; near_field_max_elev_deg records what "
                "this exclusion removes"),
        ),
        near_field=dict(
            max_elev_deg=round(float(nf_in.max()), 4),
            max_object_m_above_observer=round(float(np.nanmax(nf[2]) - ho_c), 1),
            azimuths_where_it_exceeds_the_horizon=int((nf_in > c5[0]).sum()),
            note=("compared per azimuth, not max-vs-min: the excluded near field "
                  "never forms the skyline at any azimuth, so cutting it removes "
                  "nothing from the silhouette. The ~18 m objects it contains are "
                  "terminal buildings in the surface model, not terrain."),
        ),
        dem=dict(primary="Copernicus DEM GLO-30",
                 control="SRTM v3 1 arcsec, despiked"),
        agreement=dict(max_abs_diff_deg=round(float(np.abs(diff).max()), 4),
                       rms_diff_deg=round(float(np.sqrt((diff ** 2).mean())), 4)),
        profile=rows,
    )
    with open(os.path.join(OUT, "horizon_5deg.json"), "w") as f:
        json.dump(meta, f, indent=2)

    with open(os.path.join(OUT, "horizon_fine_0p1deg.csv"), "w") as f:
        f.write("azimuth_deg,elev_deg,dist_km,height_m_amsl,lat,lon\n")
        for i, a in enumerate(azf):
            f.write("%.1f,%.4f,%.3f,%.1f,%.5f,%.5f\n"
                    % (a, cf[0][i], cf[1][i] / 1000.0, cf[2][i], cf[3][i], cf[4][i]))

    np.save(os.path.join(OUT, "_fine_profile.npy"),
            np.stack([azf, cf[0], cf[1], cf[2], cf[3], cf[4]]))

    print("\n%6s %9s %9s %9s %10s" % ("az", "elev", "dist km", "AMSL m", "srtm-diff"))
    for r in rows:
        if r["azimuth_deg"] % 15 == 0:
            print("%6.0f %9.3f %9.2f %9.1f %10.3f"
                  % (r["azimuth_deg"], r["elev_deg"], r["dist_km"],
                     r["height_m_amsl"], r["elev_deg"] - r["elev_deg_srtm_control"]))


if __name__ == "__main__":
    main()
