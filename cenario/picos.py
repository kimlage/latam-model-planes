#!/usr/bin/env python3
"""Name the peaks that form the SCL skyline, and test which famous summits
are actually visible from the takeoff point (line-of-sight over the DEM).

Gazetteers: GeoNames (CC BY 4.0) + OpenStreetMap (ODbL). A peak is reported
only when both the DEM and the gazetteer agree on its height.
"""
import os, sys, json, math
import numpy as np
from scipy.signal import find_peaks

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
from srtm import Mosaic
import frame as F
import horizonte as H

OUT = os.path.join(HERE, "terreno")


def geodesic(lat, lon):
    """Distance (m) and true azimuth (deg) from the observer to lat/lon."""
    p1 = math.radians(F.LAT0); l1 = math.radians(F.LON0)
    p2 = np.radians(lat); l2 = np.radians(lon)
    dl = l2 - l1
    dp = p2 - p1
    a = np.sin(dp / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    d = 2 * H.R_GEO * np.arcsin(np.sqrt(a))
    az = np.degrees(np.arctan2(np.sin(dl) * np.cos(p2),
                               math.cos(p1) * np.sin(p2) -
                               math.sin(p1) * np.cos(p2) * np.cos(dl))) % 360.0
    return d, az


def snap_to_summit(dem, lat, lon, radius_m=1200.0):
    """Move a gazetteer coordinate onto the local DEM maximum, so line-of-sight
    is tested against the real summit rather than a mislocated label."""
    dl = radius_m / 110900.0
    dlo = radius_m / (110900.0 * math.cos(math.radians(lat)))
    la = np.linspace(lat - dl, lat + dl, 41)
    lo = np.linspace(lon - dlo, lon + dlo, 41)
    LA, LO = np.meshgrid(la, lo, indexing="ij")
    h = dem.sample_bilinear(LA.ravel(), LO.ravel())
    if np.all(np.isnan(h)):
        return lat, lon, float("nan")
    j = int(np.nanargmax(h))
    return float(LA.ravel()[j]), float(LO.ravel()[j]), float(h[j])


def line_of_sight(dem, lat, lon, h_obs, ele=None, k=None):
    """Is the summit at lat/lon visible? Returns (visible, summit_angle,
    blocking_angle, dist_m, az_deg, dem_height)."""
    d, az = geodesic(np.array([lat]), np.array([lon]))
    d = float(d[0]); az = float(az[0])
    h_sum = float(dem.sample_bilinear(np.array([lat]), np.array([lon]))[0])
    if ele is not None and not math.isnan(h_sum):
        h_sum = max(h_sum, 0.0)
    a_sum = float(H.elev_angle(np.array([h_sum]), np.array([d]), h_obs, k=k)[0])
    # terrain between the observer and the summit
    rr = np.arange(H.D_MIN, max(H.D_MIN + 1, d - 250.0), H.D_STEP)
    if len(rr) < 2:
        return True, a_sum, -90.0, d, az, h_sum
    la, lo = H.ray_latlon(np.array([az]), rr)
    hh = dem.sample_bilinear(la.ravel(), lo.ravel())
    aa = H.elev_angle(hh, rr, h_obs, k=k)
    blk = float(np.nanmax(aa))
    return (a_sum > blk + 0.005), a_sum, blk, d, az, h_sum


def main():
    dem = Mosaic(os.path.join(HERE, "dem_cop_hgt"))
    h_obs = H.field_height(dem) + H.EYE_M
    gaz = json.load(open(os.path.join(HERE, "refs", "gazetteer.json")))
    gaz = [g for g in gaz if g["ele"]]
    glat = np.array([g["lat"] for g in gaz]); glon = np.array([g["lon"] for g in gaz])
    gele = np.array([g["ele"] for g in gaz])
    gd, gaz_az = geodesic(glat, glon)

    prof = np.load(os.path.join(OUT, "_fine_profile.npy"))
    azf, ang, dist, hgt, plat, plon = prof

    # ---- 1. which named summit sits at each skyline maximum ----------
    pk, props = find_peaks(ang, prominence=0.05, distance=8)
    print("skyline local maxima: %d" % len(pk))
    named = []
    for i in pk:
        # nearest gazetteer entry to this horizon point
        dy = (glat - plat[i]) * 110900.0
        dx = (glon - plon[i]) * 93000.0
        r = np.hypot(dx, dy)
        j = int(np.argmin(r))
        if r[j] > 2500:
            continue
        # keep the best-matching entry within 2.5 km: prefer closest in height
        cand = np.where(r < 2500)[0]
        cand = cand[np.argsort(np.abs(gele[cand] - hgt[i]))]
        j = int(cand[0])
        dh = abs(float(gele[j]) - float(hgt[i])); off = float(r[j])
        if dh <= 60 and off <= 800:
            conf = "confirmed"
        elif dh <= 150 and off <= 1500:
            conf = "probable"
        else:
            conf = "uncertain"
        named.append(dict(
            confidence=conf,
            azimuth_deg=round(float(azf[i]), 1),
            elev_deg=round(float(ang[i]), 3),
            name=gaz[j]["name"], source=gaz[j]["src"],
            gazetteer_ele_m=float(gele[j]),
            dem_height_m=round(float(hgt[i]), 1),
            dist_km=round(float(dist[i]) / 1000.0, 2),
            lat=round(float(plat[i]), 5), lon=round(float(plon[i]), 5),
            match_offset_m=round(float(r[j]), 0),
        ))

    # merge duplicates (same name over adjacent azimuths) - keep the highest
    best = {}
    for n in named:
        k = n["name"]
        if k not in best or n["elev_deg"] > best[k]["elev_deg"]:
            best[k] = n
    skyline = sorted(best.values(), key=lambda n: n["azimuth_deg"])

    # ---- 2. explicit visibility test on the notable summits -----------
    watch = ["Cerro El Plomo", "Nevado El Plomo", "Cerro Tupungato", "Tupungato",
             "Volcán Tupungatito", "Cerro Marmolejo", "Cerro San Ramón",
             "Cerro Provincia", "Cerro Manquehue", "Cerro San Cristóbal",
             "Cerro Renca", "Nevado Juncal", "Cerro La Paloma", "Cerro Altar",
             "Aconcagua", "Cerro Aconcagua", "Cerro El Roble", "Cerro La Campana",
             "Cerro Punta Negra", "Cerro Bismarck", "Cerro Leonera",
             "Volcán San José", "Cerro Alto de los Leones", "Cerro Polleras"]
    seen = {}
    for g in gaz:
        if g["name"] in watch and g["ele"] and g["ele"] > 400:
            k = g["name"]
            if k not in seen or g["ele"] > seen[k]["ele"]:
                seen[k] = g
    vis = []
    for k, g in sorted(seen.items(), key=lambda kv: -kv[1]["ele"]):
        slat, slon, shgt = snap_to_summit(dem, g["lat"], g["lon"])
        v, a_sum, blk, d, az, hdem = line_of_sight(dem, slat, slon, h_obs)
        sens = {}
        for kk in (0.0, 0.13, 0.25):
            vv, aa2, bb2, _, _, _ = line_of_sight(dem, slat, slon, h_obs, k=kk)
            sens["k=%.2f" % kk] = dict(visible=bool(vv),
                                       margin_deg=round(aa2 - bb2, 3))
        margin = a_sum - blk
        vis.append(dict(name=k, gazetteer_ele_m=g["ele"], dem_height_m=round(hdem, 1),
                        source=g["src"], lat=round(slat, 5), lon=round(slon, 5),
                        gazetteer_lat=g["lat"], gazetteer_lon=g["lon"],
                        snap_offset_m=round(float(np.hypot(
                            (slat - g["lat"]) * 110900.0,
                            (slon - g["lon"]) * 110900.0 *
                            math.cos(math.radians(g["lat"])))), 0),
                        azimuth_deg=round(az, 1), dist_km=round(d / 1000.0, 1),
                        summit_elev_deg=round(a_sum, 3),
                        blocking_elev_deg=round(blk, 3),
                        margin_deg=round(margin, 3),
                        marginal=bool(abs(margin) < 0.25),
                        refraction_sensitivity=sens,
                        visible=bool(v)))

    res = dict(
        observer=dict(lat=F.LAT0, lon=F.LON0, height_m_amsl=round(h_obs, 1),
                      desc="RWY 17L threshold, SCEL"),
        gazetteers=["GeoNames (CC BY 4.0)", "OpenStreetMap (ODbL)"],
        skyline_peaks=skyline,
        notable_summits=vis,
    )
    json.dump(res, open(os.path.join(OUT, "picos.json"), "w"),
              ensure_ascii=False, indent=2)

    print("\n=== NAMED SUMMITS ON THE SKYLINE (by azimuth) ===")
    print("%6s %8s %9s %8s  %-34s %s"
          % ("az", "elev", "dist km", "DEM m", "name", "gaz m"))
    for n in skyline:
        print("%6.1f %8.3f %9.2f %8.0f  %-34s %.0f"
              % (n["azimuth_deg"], n["elev_deg"], n["dist_km"], n["dem_height_m"],
                 n["name"], n["gazetteer_ele_m"]))

    print("\n=== NOTABLE SUMMITS: visible from the runway? ===")
    print("%-26s %7s %7s %8s %8s %8s  %-8s %s"
          % ("name", "gaz m", "az", "dist km", "margin", "k=0.25", "visible", "note"))
    for v in vis:
        print("%-26s %7.0f %7.1f %8.1f %8.3f %8.3f  %-8s %s"
              % (v["name"], v["gazetteer_ele_m"], v["azimuth_deg"], v["dist_km"],
                 v["margin_deg"], v["refraction_sensitivity"]["k=0.25"]["margin_deg"],
                 "YES" if v["visible"] else "no",
                 "MARGINAL" if v["marginal"] else ""))
    nconf = sum(1 for n in skyline if n["confidence"] == "confirmed")
    print("\nskyline matches: %d confirmed, %d probable, %d uncertain"
          % (nconf,
             sum(1 for n in skyline if n["confidence"] == "probable"),
             sum(1 for n in skyline if n["confidence"] == "uncertain")))


if __name__ == "__main__":
    main()
