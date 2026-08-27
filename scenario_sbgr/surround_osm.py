#!/usr/bin/env python3
"""The surround re-query: minor streets + building footprints for the ring.

Phase 1's extract CUT ~8 550 minor-street ways and ~2 756 building footprints
on purpose (build_osm.py header: "no camera in this project will ever resolve
them"). The owner's verdict on the phase-3 aerial tour - "o entorno esta todo
muito vazio" - reversed that decision: the fabric IS what those cameras read.
This script documents the re-query and converts it to the compact form
build_scenery.py seeds the procedural surround from.

    python3 surround_osm.py             # query Overpass and rebuild
    python3 surround_osm.py --offline   # rebuild from the saved raw dump

THE QUERY (run 2026-08-26, overpass-api.de, 33 s, 16.7 MB, 21 544 elements)

    [out:json][timeout:240];
    (
      way["highway"~"^(residential|unclassified|tertiary|tertiary_link|
                       living_street)$"](-23.48,-46.54,-23.38,-46.40);
      way["building"](-23.48,-46.54,-23.38,-46.40);
    );
    out geom;

The bbox is WIDER than build_osm.py's (-23.47,-46.52,-23.40,-46.42) on
purpose: the tour and departure lenses read the Bonsucesso / Agua Chata /
Itaim Paulista flank north of the Baquirivu valley and the wall-to-wall
fabric south-west of the field well past the old 2-3 km fringe. Mapped
LANDUSE in that north sector is under 1 km2 - Brazilian OSM maps streets and
buildings far more completely than landuse - so the street network, not the
landuse polygons, is the honest urbanization mask there.

Output  sbgr_osm_surround.json
    streets    polylines in scene ENU metres, 1 dp, simplified to ~10 m -
               the urbanization mask AND drawable minor-road geometry
    buildings  real footprints as min-area boxes (cx, cy, long_m, short_m,
               bearing) - massing seeds where OSM actually mapped a roof

Nothing in the output is invented; the raw dump is git-ignored like
sbgr_osm_raw.json and this script re-downloads it. (c) OpenStreetMap
contributors, ODbL 1.0.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import frame as F                                             # noqa: E402

RAW = os.path.join(HERE, "sbgr_osm_streets_raw.json")
OUT = os.path.join(HERE, "sbgr_osm_surround.json")

BBOX = (-23.48, -46.54, -23.38, -46.40)      # S, W, N, E - the WIDER box
QUERY = """[out:json][timeout:240];
(
  way["highway"~"^(residential|unclassified|tertiary|tertiary_link|living_street)$"](%s);
  way["building"](%s);
);
out geom;
""" % (",".join(map(str, BBOX)), ",".join(map(str, BBOX)))

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def fetch():
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    for url in MIRRORS:
        try:
            t0 = time.time()
            req = urllib.request.Request(
                url, data=data,
                headers={"User-Agent": "latam-model-planes-scenery/1.0"})
            with urllib.request.urlopen(req, timeout=280) as r:
                raw = r.read()
            print("%s ok, %d bytes in %.0f s" % (url, len(raw),
                                                 time.time() - t0))
            open(RAW, "wb").write(raw)
            return
        except Exception as e:                                # noqa: BLE001
            print(url, "FAIL", e)
    raise SystemExit("every Overpass mirror refused")


def simplify(pts, tol=10.0):
    """Keep endpoints and any point further than tol from the running chord -
    a cheap one-pass thinning (the fabric mask needs ~10 m, not 1 m)."""
    if len(pts) <= 2:
        return pts
    out = [pts[0]]
    for p in pts[1:-1]:
        a = out[-1]
        if math.hypot(p[0] - a[0], p[1] - a[1]) >= tol:
            out.append(p)
    out.append(pts[-1])
    return out


def min_area_box(poly):
    """Rotating calipers, same convention as build_osm.py."""
    pts = np.array(poly, dtype=float)
    if len(pts) < 3:
        return None
    p = sorted(map(tuple, pts))

    def half(seq):
        h = []
        for q in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (q[1] - h[-2][1]) - \
                                  (h[-1][1] - h[-2][1]) * (q[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(q)
        return h[:-1]

    hull = np.array(half(p) + half(p[::-1]), dtype=float)
    if len(hull) < 3:
        return None
    best = None
    for i in range(len(hull)):
        d = hull[(i + 1) % len(hull)] - hull[i]
        th = math.atan2(d[1], d[0])
        c, s = math.cos(-th), math.sin(-th)
        R = np.array([[c, -s], [s, c]])
        q = hull @ R.T
        w = q[:, 0].max() - q[:, 0].min()
        h = q[:, 1].max() - q[:, 1].min()
        if best is None or w * h < best[0]:
            best = (w * h, max(w, h), min(w, h), math.degrees(th) % 180.0)
    long_brg = (90.0 - best[3]) % 180.0
    return best[1], best[2], long_brg


def main():
    if "--offline" not in sys.argv or not os.path.exists(RAW):
        if "--offline" in sys.argv:
            print("no raw dump on disk; querying anyway")
        fetch()
    raw = json.load(open(RAW))
    enu = F.enu()

    streets, buildings = [], []
    n_pts_in = n_pts_out = 0
    inside = 0
    for e in raw["elements"]:
        if e.get("type") != "way" or "geometry" not in e:
            continue
        g = e["geometry"]
        lat = np.array([p["lat"] for p in g], dtype=float)
        lon = np.array([p["lon"] for p in g], dtype=float)
        x, y, _ = enu.from_geodetic(lat, lon, np.zeros_like(lat))
        pts = [[round(float(a), 1), round(float(b), 1)] for a, b in zip(x, y)]
        t = e.get("tags", {})
        if t.get("highway"):
            n_pts_in += len(pts)
            pts = simplify(pts)
            n_pts_out += len(pts)
            streets.append(dict(cls=t["highway"], pts=pts))
        elif t.get("building"):
            box = min_area_box(pts)
            if box is None:
                continue
            L, W, brg = box
            cx = sum(p[0] for p in pts[:-1]) / max(1, len(pts) - 1)
            cy = sum(p[1] for p in pts[:-1]) / max(1, len(pts) - 1)
            lv = t.get("building:levels")
            try:
                lv = float(lv) if lv else None
            except ValueError:
                lv = None
            buildings.append(dict(
                cx=round(cx, 1), cy=round(cy, 1),
                long_m=round(L, 1), short_m=round(W, 1),
                bearing_deg=round(brg, 1),
                kind=t.get("building"), levels=lv))
            inside += 1

    out = dict(
        what_this_is=(
            "The SBGR surround re-query: minor streets and building "
            "footprints the phase-1 extract deliberately cut, fetched "
            "2026-08-26 for the surround round (the owner's verdict on the "
            "aerial tour: 'o entorno esta todo muito vazio'). Streets are "
            "the urbanization mask - Brazilian OSM maps streets/buildings "
            "far more completely than landuse. See surround_osm.py for the "
            "exact query and the wider bbox rationale."),
        source="(c) OpenStreetMap contributors, ODbL 1.0 - via Overpass API",
        bbox_s_w_n_e=list(BBOX),
        frame="scene ENU, lib/frame.py (origin THR 10L, z=0 at 750 m AMSL)",
        street_classes=sorted({s["cls"] for s in streets}),
        counts=dict(streets=len(streets), buildings=len(buildings)),
        streets=streets,
        buildings=buildings,
    )
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    km = sum(sum(math.dist(a, b) for a, b in zip(s["pts"], s["pts"][1:]))
             for s in streets) / 1000.0
    print("streets: %d ways, %.0f km (points %d -> %d after ~10 m thinning)"
          % (len(streets), km, n_pts_in, n_pts_out))
    print("buildings: %d footprints" % len(buildings))
    print("wrote %s (%d kB)" % (OUT, os.path.getsize(OUT) // 1024))


if __name__ == "__main__":
    main()
