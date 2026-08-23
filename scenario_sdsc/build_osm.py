#!/usr/bin/env python3
"""Fetch the SDSC aerodrome + LATAM MRO geometry from OSM and write sdsc_osm.json.

Same shape as ../scenario/scl_osm.json: every feature carries its OSM id, tags
worth keeping, and its polygon/centroid in the scene's local ENU frame
(lib/frame.py). z is not set here - this is a PLAN, not terrain.

    python3 build_osm.py            # query Overpass and rebuild
    python3 build_osm.py --raw x.json   # rebuild from a saved Overpass dump

Licence: OpenStreetMap, ODbL 1.0. "(c) OpenStreetMap contributors".
"""
import argparse, json, math, os, sys, urllib.parse, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import frame as F

OVERPASS = "https://overpass-api.de/api/interpreter"
# Generous box around the field: the aerodrome is ~2.4 x 1.6 km, the MRO sits
# inside it, and the surround gives the roads/vegetation a departure sees.
BBOX = (-21.905, -47.940, -21.845, -47.870)      # S, W, N, E

QUERY = """[out:json][timeout:300];
(
  nwr["aeroway"](%s);
  nwr["building"](%s);
  nwr["landuse"](%s);
  nwr["man_made"](%s);
  nwr["highway"](%s);
  nwr["barrier"](%s);
  nwr["natural"](%s);
  nwr["waterway"](%s);
);
out geom;
"""

KEEP_TAGS = ("name", "name:en", "name:pt", "ref", "operator", "aeroway",
             "building", "building:levels", "building:part", "height",
             "man_made", "landuse", "surface", "width", "length", "icao",
             "iata", "wikidata", "wikipedia", "aerodrome:type", "old_name",
             "website", "addr:street", "addr:housenumber", "natural",
             "highway", "barrier", "waterway", "power", "tower:type")


# ----------------------------------------------------------------- geometry
def enu_xy(enu, pts):
    """[{lat,lon}] -> [[x,y]] in the scene frame, 2 dp."""
    if not pts:
        return []
    lat = np.array([p["lat"] for p in pts], dtype=float)
    lon = np.array([p["lon"] for p in pts], dtype=float)
    e, n, _ = enu.from_geodetic(lat, lon, np.zeros_like(lat))
    return [[round(float(a), 2), round(float(b), 2)] for a, b in zip(e, n)]


def centroid(poly):
    """Area centroid of a closed ring; falls back to the mean for open ways."""
    if len(poly) < 3:
        xs = [p[0] for p in poly] or [0.0]
        ys = [p[1] for p in poly] or [0.0]
        return [round(sum(xs) / len(xs), 2), round(sum(ys) / len(ys), 2)]
    a = cx = cy = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        cr = x0 * y1 - x1 * y0
        a += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
    if abs(a) < 1e-9:
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        return [round(sum(xs) / len(xs), 2), round(sum(ys) / len(ys), 2)]
    return [round(cx / (3 * a), 2), round(cy / (3 * a), 2)]


def ring_area(poly):
    if len(poly) < 3:
        return 0.0
    a = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def min_area_box(poly):
    """Rotating-calipers minimum-area rectangle: (length, width, azimuth_deg)."""
    pts = np.array(poly, dtype=float)
    if len(pts) < 3:
        return None
    # convex hull (monotone chain)
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
    return dict(long_m=round(best[1], 1), short_m=round(best[2], 1),
                long_axis_bearing_deg_true=round((90.0 - best[3]) % 180.0, 1))


def path_length(poly):
    return round(sum(math.dist(poly[i], poly[i + 1])
                     for i in range(len(poly) - 1)), 1)


# ----------------------------------------------------------------- overpass
def fetch(path):
    q = QUERY % tuple(",".join("%.6f" % v for v in BBOX) for _ in range(8))
    data = urllib.parse.urlencode({"data": q}).encode()
    req = urllib.request.Request(OVERPASS, data=data,
                                 headers={"User-Agent": "sdsc-scenery/1.0"})
    with urllib.request.urlopen(req, timeout=360) as r:
        raw = r.read()
    with open(path, "wb") as fh:
        fh.write(raw)
    return json.loads(raw)


def _key(p):
    return (round(p["lat"], 7), round(p["lon"], 7))


def stitch(segments):
    """Join open way segments end-to-end into closed rings.

    A multipolygon whose outer boundary is cut into 18 separate ways - which is
    exactly how the SDSC aerodrome relation is mapped - is only a polygon after
    this step. Taking the longest member instead gives a fragment, and the
    aerodrome then measures 1.0 x 0.85 km instead of the real 1.72 x 2.16 km.
    """
    segs = [list(s) for s in segments if len(s) >= 2]
    rings = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while changed and _key(cur[0]) != _key(cur[-1]):
            changed = False
            for i, s in enumerate(segs):
                if _key(s[0]) == _key(cur[-1]):
                    cur += s[1:]; segs.pop(i); changed = True; break
                if _key(s[-1]) == _key(cur[-1]):
                    cur += s[::-1][1:]; segs.pop(i); changed = True; break
                if _key(s[-1]) == _key(cur[0]):
                    cur = s[:-1] + cur; segs.pop(i); changed = True; break
                if _key(s[0]) == _key(cur[0]):
                    cur = s[::-1][:-1] + cur; segs.pop(i); changed = True; break
        rings.append(cur)
    rings.sort(key=len, reverse=True)
    return rings


def geom_of(el, ways):
    """Point list for a way, or the largest stitched outer ring of a relation."""
    if el["type"] == "way":
        return el.get("geometry", [])
    if el["type"] == "relation":
        outers = [m.get("geometry", []) for m in el.get("members", [])
                  if m.get("role") in ("outer", "") and m.get("geometry")]
        rings = stitch(outers)
        return rings[0] if rings else []
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(HERE, "sdsc_osm_raw.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "sdsc_osm.json"))
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()

    if a.offline and os.path.exists(a.raw):
        raw = json.load(open(a.raw))
    else:
        raw = fetch(a.raw)
    enu = F.enu()
    els = raw["elements"]
    ways = {e["id"]: e for e in els if e["type"] == "way"}
    # ways that are members of a kept relation should not also appear alone
    member_ids = set()
    for e in els:
        if e["type"] == "relation" and e.get("tags"):
            for m in e.get("members", []):
                if m["type"] == "way":
                    member_ids.add(m["ref"])

    out = {
        "_what": ("OpenStreetMap geometry for SDSC (Sao Carlos / Mario Pereira "
                  "Lopes) and the LATAM MRO, converted to the scene's local ENU "
                  "frame. Companion to sdsc_aip_survey.json, which carries the "
                  "official survey values and OVERRIDES anything here that "
                  "disagrees."),
        "_license": {
            "data_source": "OpenStreetMap, via the Overpass API "
                           "(https://overpass-api.de/api/interpreter).",
            "copyright": "(c) OpenStreetMap contributors",
            "license": "Open Database License (ODbL) v1.0 - "
                       "https://opendatacommons.org/licenses/odbl/1-0/",
            "attribution_required": True,
            "attribution_string": "Airport geometry (c) OpenStreetMap "
                                  "contributors, ODbL 1.0.",
            "share_alike_note": ("ODbL is share-alike: a derived database (this "
                                 "JSON, and any mesh generated straight from it) "
                                 "must be published under ODbL as well."),
            "osm_data_timestamp": raw.get("osm3s", {}).get("timestamp_osm_base"),
            "overpass_bbox_south_west_north_east": list(BBOX),
        },
        "airport": {
            "icao": "SDSC", "iata": "QSC",
            "name": "Aeroporto Estadual Mario Pereira Lopes de Sao Carlos",
            "operator_osm": "DAESP",
            "operator_current": ("Rede Voa / VOA-SP SPE - the ROTAER entry reads "
                                 "'REDE VOA SP SPE'. The OSM operator=DAESP tag "
                                 "predates the 2021 concession and is STALE."),
            "elevation_note": "Not tagged in OSM. Take 807 m / 2648 ft from "
                              "sdsc_aip_survey.json.",
        },
        "reference_frame": {
            "type": "local East-North-Up tangent plane (WGS84 -> ECEF -> ENU)",
            "origin_lat": F.LAT0, "origin_lon": F.LON0,
            "origin_is": ("published landing threshold of RWY 02 "
                          "(AISWEB/ROTAER declared-distance table, "
                          "S 21 52 54.63 / W 047 54 14.27)"),
            "axes": {"x": "east, metres", "y": "north, metres", "z": "up, metres"},
            "units": "metres",
            "z_convention": "All z are 0 in this file: this is a PLAN, not terrain.",
        },
        "runways": [], "aprons": [], "taxiways": [], "hangars": [],
        "terminals": [], "parking_positions": [], "helipads": [],
        "windsocks": [], "navaids": [], "holding_positions": [],
        "buildings": [], "landuse": [], "roads": [], "water": [],
        "aerodrome_boundary_xy_m": [], "latam_mro": {},
    }

    boundary_rel = None
    for el in els:
        t = el.get("tags") or {}
        if not t:
            continue
        if el["type"] == "way" and el["id"] in member_ids and \
                not (set(t) - {"source"}):
            continue
        g = geom_of(el, ways)
        poly = enu_xy(enu, g) if g else None
        extra_rings = []
        if el["type"] == "relation":
            outers = [m.get("geometry", []) for m in el.get("members", [])
                      if m.get("role") in ("outer", "") and m.get("geometry")]
            rings = stitch(outers)
            extra_rings = [enu_xy(enu, r) for r in rings[1:]]
            inners = [m.get("geometry", []) for m in el.get("members", [])
                      if m.get("role") == "inner" and m.get("geometry")]
            inner_rings = [enu_xy(enu, r) for r in stitch(inners)]
        if el["type"] == "node":
            poly = enu_xy(enu, [{"lat": el["lat"], "lon": el["lon"]}])
        rec = {"osm_id": "%s/%d" % (el["type"], el["id"])}
        for k in KEEP_TAGS:
            if k in t:
                rec[k] = t[k]
        aw = t.get("aeroway"); bld = t.get("building")

        if el["type"] == "node":
            rec["xy_m"] = poly[0] if poly else None
        elif poly:
            closed = len(poly) > 2 and (
                math.dist(poly[0], poly[-1]) < 0.5 or
                el["type"] == "relation")
            rec["polygon_xy_m"] = poly
            rec["centroid_xy_m"] = centroid(poly)
            if closed:
                rec["area_m2"] = round(ring_area(poly), 1)
                box = min_area_box(poly)
                if box:
                    rec["min_area_box"] = box
            else:
                rec["length_m"] = path_length(poly)
        if extra_rings:
            rec["extra_outer_rings_xy_m"] = extra_rings
        if el["type"] == "relation" and inner_rings:
            rec["inner_rings_xy_m"] = inner_rings

        if aw == "aerodrome":
            boundary_rel = rec
            out["aerodrome_boundary_xy_m"] = [rec.get("polygon_xy_m", [])]
            out["airport"]["osm_id"] = rec["osm_id"]
            continue
        if aw == "runway":
            out["runways"].append(rec); continue
        if aw == "apron":
            out["aprons"].append(rec); continue
        if aw == "taxiway":
            out["taxiways"].append(rec); continue
        if aw == "hangar" or bld == "hangar":
            out["hangars"].append(rec); continue
        if aw == "terminal" or bld == "transportation":
            out["terminals"].append(rec); continue
        if aw == "parking_position":
            out["parking_positions"].append(rec); continue
        if aw == "helipad":
            out["helipads"].append(rec); continue
        if aw == "windsock":
            out["windsocks"].append(rec); continue
        if aw == "navigationaid":
            out["navaids"].append(rec); continue
        if aw == "holding_position":
            out["holding_positions"].append(rec); continue
        if bld:
            out["buildings"].append(rec); continue
        if t.get("landuse"):
            out["landuse"].append(rec); continue
        if t.get("highway"):
            out["roads"].append(rec); continue
        if t.get("waterway") or t.get("natural") in ("water", "wetland"):
            out["water"].append(rec); continue
        out.setdefault("other", []).append(rec)

    # ---------------------------------------------------- the MRO block
    site = next((r for r in out["landuse"] if r.get("name") == "TAM MRO"), None)
    if site:
        xs = [p[0] for p in site["polygon_xy_m"]]
        ys = [p[1] for p in site["polygon_xy_m"]]
        bb = dict(min=[round(min(xs), 1), round(min(ys), 1)],
                  max=[round(max(xs), 1), round(max(ys), 1)])
        members, built = [], 0.0
        for k in ("hangars", "buildings", "terminals"):
            for r in out[k]:
                c = r.get("centroid_xy_m")
                if c and bb["min"][0] <= c[0] <= bb["max"][0] and \
                        bb["min"][1] <= c[1] <= bb["max"][1]:
                    built += r.get("area_m2") or 0.0
                    members.append(dict(osm_id=r["osm_id"], category=k,
                                        name=r.get("name"),
                                        centroid_xy_m=c,
                                        area_m2=r.get("area_m2"),
                                        min_area_box=r.get("min_area_box")))
        members.sort(key=lambda m: -(m["area_m2"] or 0))
        apr = [r for r in out["aprons"]
               if (r.get("centroid_xy_m") or [0, 0])[0] > 500]
        # projection onto the RWY 02 take-off track (true 1.026 deg)
        th = math.radians(1.026)
        ux, uy = math.sin(th), math.cos(th)          # along-track unit
        def proj(p):
            return (round(p[0] * ux + p[1] * uy, 1),      # along the roll
                    round(p[0] * uy - p[1] * ux, 1))      # right of the track
        cx = (bb["min"][0] + bb["max"][0]) / 2.0
        cy = (bb["min"][1] + bb["max"][1]) / 2.0
        along, lateral = proj((cx, cy))
        out["latam_mro"] = {
            "what_it_is": "LATAM MRO Sao Carlos - LATAM's heavy-maintenance base.",
            "how_identified": ("OSM multipolygon relation/7422930, landuse="
                               "industrial, name='TAM MRO', website "
                               "tammro.com.br. It is the only industrial site "
                               "inside the aerodrome."),
            "osm_name_warning": ("The SAME relation carries name:en='TAM Museum', "
                                 "wikidata=Q3868501 and wikipedia=pt:Museu TAM. "
                                 "Q3868501 is the MUSEU TAM, a separate aviation "
                                 "museum that shared this site and closed in "
                                 "2016. The polygon is the MRO; the museum tags "
                                 "on it are wrong. Do not follow them."),
            "site_polygon_area_m2": site["area_m2"],
            "site_bbox_xy_m": bb,
            "site_extent_m": {"east_west": round(bb["max"][0] - bb["min"][0], 1),
                              "north_south": round(bb["max"][1] - bb["min"][1], 1)},
            "site_centre_xy_m": [round(cx, 1), round(cy, 1)],
            "relation_to_runway_02": {
                "along_takeoff_roll_m": along,
                "lateral_offset_m": abs(lateral),
                "side_when_departing_02": "right" if lateral > 0 else "left",
                "note": ("Distances are of the site CENTRE, projected on the "
                         "RWY 02 track. The block spans %.0f-%.0f m along the "
                         "roll and %.0f-%.0f m off the centreline."
                         % (proj((bb['min'][0], bb['min'][1]))[0],
                            proj((bb['max'][0], bb['max'][1]))[0],
                            min(abs(proj((bb['min'][0], bb['min'][1]))[1]),
                                abs(proj((bb['max'][0], bb['max'][1]))[1])),
                            max(abs(proj((bb['min'][0], bb['min'][1]))[1]),
                                abs(proj((bb['max'][0], bb['max'][1]))[1])))),
            },
            "osm_mapped_building_footprint_m2": round(built, 0),
            "osm_mapped_apron_m2": round(sum(r.get("area_m2") or 0
                                             for r in apr), 0),
            "osm_survey_date": ("2017-07-27 - every MRO building and apron in "
                                "OSM is version 1 from one tracing session by "
                                "user 'naoliv' on that date, except way/"
                                "708700156 (2019-07-30) and way/510750642 "
                                "(2021-06-17). HANGAR 9, INAUGURATED "
                                "2025-09-26, IS THEREFORE NOT IN THIS DATA."),
            "members": members,
        }

    # -------------------------------------------- what goes past on a 02 roll
    th = math.radians(1.026)
    ux, uy = math.sin(th), math.cos(th)
    marks = []
    for key in ("hangars", "aprons", "terminals", "buildings", "landuse",
                "navaids", "windsocks", "runways", "taxiways"):
        for r in out[key]:
            c = r.get("centroid_xy_m") or r.get("xy_m")
            if not c:
                continue
            if key in ("buildings", "landuse") and not r.get("name") and \
                    (r.get("area_m2") or 0) < 1500:
                continue
            if key in ("taxiways",) and not r.get("name"):
                continue
            along = c[0] * ux + c[1] * uy
            lat_off = c[0] * uy - c[1] * ux
            marks.append(dict(
                name=r.get("name") or r.get("ref") or
                     ("%s %s" % (key[:-1], r["osm_id"])),
                kind=key[:-1], osm_id=r["osm_id"],
                distance_along_roll_m=round(along, 1),
                lateral_offset_m=round(abs(lat_off), 1),
                side="right" if lat_off > 0 else "left",
                xy_m=c))
    marks.sort(key=lambda m: m["distance_along_roll_m"])
    out["departure_02_landmarks"] = {
        "explanation": ("Every mapped feature projected onto the RWY 02 take-off "
                        "roll. distance_along_roll_m is metres from THR 02 (the "
                        "origin) along the runway; lateral_offset_m is the "
                        "perpendicular distance from the centreline; side is as "
                        "seen from an aircraft rolling on 02 (northbound, true "
                        "001 deg)."),
        "note": ("The whole LATAM MRO is on the RIGHT, 360-1400 m out, from "
                 "1155 m into the roll onwards - i.e. it comes abeam right "
                 "around rotation and stays in frame after lift-off. The "
                 "Aeroclube's GA apron and hangars are the only thing on the "
                 "LEFT, and they are in the first 500 m. Departing 20 instead "
                 "mirrors all of this AND puts the base behind the aircraft "
                 "from the very start of the roll."),
        "landmarks": marks,
    }

    out["counts"] = {k: len(v) for k, v in out.items()
                     if isinstance(v, list)}
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps(out["counts"], indent=1))


if __name__ == "__main__":
    main()
