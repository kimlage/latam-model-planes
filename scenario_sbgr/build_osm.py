#!/usr/bin/env python3
"""Fetch the SBGR aerodrome + LATAM maintenance-base geometry from OSM and
write sbgr_osm.json.

Same shape as ../scenario_sdsc/sdsc_osm.json: every feature carries its OSM id,
tags worth keeping, and its polygon/centroid in the scene's local ENU frame
(lib/frame.py). z is not set here - this is a PLAN, not terrain.

    python3 build_osm.py            # query Overpass and rebuild
    python3 build_osm.py --offline  # rebuild from the saved Overpass dump

THE EXTRACT IS SCOPED, AND THE CUTS ARE DECISIONS. Guarulhos is a city of
1.3 M people wrapped around the airport; "everything in the bbox", which was
the right answer for Sao Carlos's cane fields, would drag in ~2 900 urban
buildings and ~9 400 residential street ways that no camera in this project
will ever resolve. What is kept, and why:

  KEPT  every aeroway feature in the bbox        the aerodrome is the subject
  KEPT  every building INSIDE the aerodrome      terminals, hangars, cargo, TWR
  KEPT  service/internal roads INSIDE the fence  apron circulation, phase 2
  KEPT  motorway/trunk/primary/secondary (+links) in the bbox
                                                 Helio Smidt, Ayrton Senna,
                                                 Dutra: the roads an aerial
                                                 actually reads
  KEPT  railway in the bbox                      CPTM Line 13 Jade + the
                                                 Aeroporto-Guarulhos station,
                                                 the one rail line INTO a
                                                 Brazilian airport
  KEPT  landuse, waterway, natural water/wetland in the bbox
                                                 the Rio Baquirivu-Guacu
                                                 valley the field sits in,
                                                 and the urban/industrial
                                                 tint for the surround
  CUT   buildings outside the aerodrome (~2 756 of 2 888)
                                                 the city is a landuse tint +
                                                 terrain problem, not 2 756
                                                 footprints; revisit in phase
                                                 2 only if a ground-level
                                                 camera looks over the fence
  CUT   residential/unclassified/tertiary etc. outside the fence
                                                 (~8 550 of 9 391 highway ways)
  CUT   power, barrier, man_made outside the fence
                                                 nothing published hangs on
                                                 them here, unlike the SDSC
                                                 power poles which were a
                                                 photographed feature

Licence: OpenStreetMap, ODbL 1.0. "(c) OpenStreetMap contributors".
"""
import argparse, json, math, os, sys, time, urllib.parse, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import frame as F

# overpass-api.de was refusing with "server too busy" for most of the survey
# session; the mail.ru mirror answered. Rotate instead of hammering one.
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
# The aerodrome is ~5.2 x 2.5 km; this box gives it a 2-3 km fringe.
BBOX = (-23.47, -46.52, -23.40, -46.42)      # S, W, N, E
AERODROME_REL = 5141542                       # OSM relation for SBGR

QUERY = """[out:json][timeout:300];
rel(%d); map_to_area ->.gru;
(
  nwr["aeroway"](%s);
  nwr["building"](area.gru);
  way["highway"](area.gru);
  way["highway"~"^(motorway|trunk|primary|secondary)(_link)?$"](%s);
  way["railway"](%s);
  nwr["man_made"](area.gru);
  nwr["landuse"](%s);
  way["waterway"](%s);
  nwr["natural"~"^(water|wetland)$"](%s);
);
out geom;
"""

KEEP_TAGS = ("name", "name:en", "name:pt", "ref", "operator", "aeroway",
             "building", "building:levels", "building:part", "height",
             "man_made", "landuse", "surface", "width", "length", "icao",
             "iata", "wikidata", "wikipedia", "aerodrome:type", "old_name",
             "website", "addr:street", "addr:housenumber", "natural",
             "highway", "barrier", "waterway", "power", "tower:type",
             "railway", "public_transport", "train", "station", "bridge",
             "tunnel", "layer", "parking_position", "holding_position")


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
    q = QUERY % ((AERODROME_REL,) +
                 tuple(",".join("%.6f" % v for v in BBOX) for _ in range(6)))
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for attempt in range(6):
        ep = OVERPASS[attempt % len(OVERPASS)]
        req = urllib.request.Request(ep, data=data,
                                     headers={"User-Agent": "sbgr-scenery/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=360) as r:
                raw = r.read()
            if raw[:1] == b"{":
                with open(path, "wb") as fh:
                    fh.write(raw)
                print("fetched from", ep)
                return json.loads(raw)
            last = raw[:200]
        except Exception as ex:                      # noqa: BLE001
            last = ex
        print("  overpass attempt %d failed (%s); waiting" % (attempt + 1, ep))
        time.sleep(20)
    raise SystemExit("Overpass kept refusing: %r" % (last,))


def _key(p):
    return (round(p["lat"], 7), round(p["lon"], 7))


def stitch(segments):
    """Join open way segments end-to-end into closed rings. Same lesson as
    SDSC: a multipolygon boundary cut into member ways is only a polygon
    after this step."""
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


def geom_of(el):
    """Point list for a way, or the largest stitched outer ring of a relation."""
    if el["type"] == "way":
        return el.get("geometry", [])
    if el["type"] == "relation":
        outers = [m.get("geometry", []) for m in el.get("members", [])
                  if m.get("role") in ("outer", "") and m.get("geometry")]
        rings = stitch(outers)
        return rings[0] if rings else []
    return []


# The 10L departure track: along-roll unit vector from the measured true
# bearing of the NORTH runway (073.411 deg in this frame). The origin is
# THR 10L; note the physical take-off roll starts 90 m BEFORE it (the
# threshold is displaced, TORA = full pavement).
TRACK_TRUE_DEG = 73.411


def proj_10l(p):
    th = math.radians(TRACK_TRUE_DEG)
    ux, uy = math.sin(th), math.cos(th)
    return (p[0] * ux + p[1] * uy,          # along the roll from THR 10L
            p[0] * uy - p[1] * ux)          # +right / -left of the track


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(HERE, "sbgr_osm_raw.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "sbgr_osm.json"))
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()

    if a.offline and os.path.exists(a.raw):
        raw = json.load(open(a.raw))
    else:
        raw = fetch(a.raw)
    enu = F.enu()
    els = raw["elements"]
    member_ids = set()
    for e in els:
        if e["type"] == "relation" and e.get("tags"):
            for m in e.get("members", []):
                if m["type"] == "way":
                    member_ids.add(m["ref"])

    out = {
        "_what": ("OpenStreetMap geometry for SBGR (Sao Paulo/Guarulhos - "
                  "Gov. Andre Franco Montoro) and the LATAM maintenance "
                  "base, converted to the scene's local ENU frame. Companion "
                  "to sbgr_aip_survey.json, which carries the official "
                  "survey values and OVERRIDES anything here that disagrees "
                  "- EXCEPT the runway centreline positions, where OSM's "
                  "imagery tracing is finer than DECEA's whole-second "
                  "threshold strings; sbgr_aip_survey.json records how the "
                  "two reconcile."),
        "_scoping": ("This extract is deliberately scoped; the docstring of "
                     "build_osm.py lists what was kept and what was cut, "
                     "and the cut counts. Buildings and minor streets of "
                     "Guarulhos city (outside the aerodrome fence) are the "
                     "big cut: ~2 756 footprints and ~8 550 street ways."),
        "_license": {
            "data_source": "OpenStreetMap, via the Overpass API.",
            "copyright": "(c) OpenStreetMap contributors",
            "license": "Open Database License (ODbL) v1.0 - "
                       "https://opendatacommons.org/licenses/odbl/1-0/",
            "attribution_required": True,
            "attribution_string": "Airport geometry (c) OpenStreetMap "
                                  "contributors, ODbL 1.0.",
            "share_alike_note": ("ODbL is share-alike: a derived database "
                                 "(this JSON, and any mesh generated straight "
                                 "from it) must be published under ODbL as "
                                 "well."),
            "osm_data_timestamp": raw.get("osm3s", {}).get("timestamp_osm_base"),
            "overpass_bbox_south_west_north_east": list(BBOX),
        },
        "airport": {
            "icao": "SBGR", "iata": "GRU",
            "name": "Aeroporto Internacional de Sao Paulo/Guarulhos - "
                    "Governador Andre Franco Montoro",
            "operator": "GRU Airport (concession); ROTAER operator string "
                        "'GRU Airport'",
            "elevation_note": "Take 750 m / 2461 ft from sbgr_aip_survey.json.",
        },
        "reference_frame": {
            "type": "local East-North-Up tangent plane (WGS84 -> ECEF -> ENU)",
            "origin_lat": F.LAT0, "origin_lon": F.LON0,
            "origin_is": ("published landing threshold of RWY 10L "
                          "(AISWEB/ROTAER declared-distance table and the "
                          "SBGR ADC, S 23 26 03 / W 046 28 57 - WHOLE "
                          "SECONDS, +/- ~30 m; see sbgr_aip_survey.json)"),
            "axes": {"x": "east, metres", "y": "north, metres", "z": "up, metres"},
            "units": "metres",
            "z_convention": "All z are 0 in this file: this is a PLAN, not terrain.",
        },
        "runways": [], "aprons": [], "taxiways": [], "hangars": [],
        "terminals": [], "gates": [], "parking_positions": [], "helipads": [],
        "windsocks": [], "navaids": [], "holding_positions": [],
        "buildings": [], "landuse": [], "roads": [], "railways": [],
        "water": [], "aerodrome_boundary_xy_m": [], "latam_maintenance": {},
    }

    for el in els:
        t = el.get("tags") or {}
        if not t:
            continue
        if el["type"] == "way" and el["id"] in member_ids and \
                not (set(t) - {"source"}):
            continue
        g = geom_of(el)
        poly = enu_xy(enu, g) if g else None
        extra_rings, inner_rings = [], []
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
            out["aerodrome_boundary_xy_m"] = [rec.get("polygon_xy_m", [])]
            out["airport"]["osm_id"] = rec["osm_id"]
            out["airport"]["osm_boundary_extra_rings"] = len(extra_rings)
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
        if aw == "gate":
            out["gates"].append(rec); continue
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
        if t.get("railway") or t.get("public_transport") == "station":
            out["railways"].append(rec); continue
        if t.get("landuse"):
            out["landuse"].append(rec); continue
        if t.get("highway"):
            out["roads"].append(rec); continue
        if t.get("waterway") or t.get("natural") in ("water", "wetland"):
            out["water"].append(rec); continue
        out.setdefault("other", []).append(rec)

    # ------------------------------------------- the LATAM maintenance block
    latam = [r for k in ("hangars", "buildings", "terminals")
             for r in out[k] if "latam" in (r.get("name") or "").lower()]
    neighbours = [r for r in out["hangars"]
                  if "latam" not in (r.get("name") or "").lower()]
    if latam:
        h = max(latam, key=lambda r: r.get("area_m2") or 0)
        c = h["centroid_xy_m"]
        along, lat_off = proj_10l(c)
        # nearest apron to the hangar (the maintenance ramp)
        best = None
        for r in out["aprons"]:
            cc = r.get("centroid_xy_m")
            if not cc:
                continue
            d = math.dist(c, cc)
            if best is None or d < best[0]:
                best = (d, r)
        out["latam_maintenance"] = {
            "what_it_is": ("LATAM's maintenance hangar at Guarulhos - the "
                           "hangar where the 777-300ER fleet is maintained "
                           "(CNN Brasil, recorded in ../scenario_sdsc/"
                           "sdsc_aip_survey.json during the Sao Carlos "
                           "round: 777 maintenance is done at Guarulhos, "
                           "not Sao Carlos)."),
            "how_identified": ("OSM %s, building=hangar, name='%s' - AND the "
                               "SBGR ADC itself prints 'HANGAR LATAM' at "
                               "this position on the chart face (georef of "
                               "the label text: lat -23.4203, lon -46.4580, "
                               "label sits just NE of the footprint). Two "
                               "independent sources; the ADC is primary."
                               % (h["osm_id"], h.get("name"))),
            "hangar": h,
            "relation_to_runway_10L": {
                "along_takeoff_roll_m": round(along, 1),
                "lateral_offset_m": round(abs(lat_off), 1),
                "side_when_departing_10L": "right" if lat_off > 0 else "left",
                "note": ("Projected on the RWY 10L departure track (073.411 "
                         "true). The physical roll starts 90 m before the "
                         "origin (displaced threshold, TORA = full "
                         "pavement)."),
            },
            "nearest_apron": None if not best else dict(
                osm_id=best[1]["osm_id"], name=best[1].get("name"),
                distance_m=round(best[0], 1),
                area_m2=best[1].get("area_m2")),
            "neighbour_hangars": [
                dict(osm_id=r["osm_id"], name=r.get("name"),
                     centroid_xy_m=r.get("centroid_xy_m"),
                     area_m2=r.get("area_m2"),
                     min_area_box=r.get("min_area_box"))
                for r in neighbours],
        }

    # -------------------------------------- what goes past on a 10L roll
    marks = []
    for key in ("hangars", "aprons", "terminals", "buildings", "landuse",
                "navaids", "windsocks", "runways", "taxiways", "railways"):
        for r in out[key]:
            c = r.get("centroid_xy_m") or r.get("xy_m")
            if not c:
                continue
            if key in ("buildings", "landuse") and not r.get("name") and \
                    (r.get("area_m2") or 0) < 3000:
                continue
            if key in ("taxiways", "railways") and not r.get("name") and \
                    not r.get("ref"):
                continue
            along, lat_off = proj_10l(c)
            if along < -2000 or along > 8000:
                continue
            marks.append(dict(
                name=r.get("name") or r.get("ref") or
                     ("%s %s" % (key[:-1], r["osm_id"])),
                kind=key[:-1], osm_id=r["osm_id"],
                distance_along_roll_m=round(along, 1),
                lateral_offset_m=round(abs(lat_off), 1),
                side="right" if lat_off > 0 else "left",
                xy_m=[round(c[0], 1), round(c[1], 1)]))
    marks.sort(key=lambda m: m["distance_along_roll_m"])
    out["departure_10L_landmarks"] = {
        "explanation": ("Every mapped feature projected onto the RWY 10L "
                        "take-off roll. distance_along_roll_m is metres from "
                        "THR 10L (the origin) along the runway (073.411 "
                        "true); the physical roll starts at -90 m (displaced "
                        "threshold). lateral_offset_m is the perpendicular "
                        "distance from the centreline; side is as seen from "
                        "an aircraft rolling on 10L (ESE-bound)."),
        "landmarks": marks,
    }

    out["counts"] = {k: len(v) for k, v in out.items()
                     if isinstance(v, list)}
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps(out["counts"], indent=1))


if __name__ == "__main__":
    main()
