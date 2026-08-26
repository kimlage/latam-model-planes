#!/usr/bin/env python3
"""Draw sbgr_osm.json as a plan, in the scene frame. -> sbgr_osm_plan.png

The plan is the check: render the built field orthographically top-down with
the same framing and put the two side by side. Same role as
../scenario_sdsc/sdsc_osm_plan.png.

    python3 plot_osm_plan.py            # whole field
    python3 plot_osm_plan.py --latam    # the LATAM maintenance corner only
"""
import argparse, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

HERE = os.path.dirname(os.path.abspath(__file__))

STYLE = {          # key            face          edge      z
    "aerodrome_boundary_xy_m": (None, "#7a7a7a", 1),
    "landuse":            ("#eef0e6", "#d8dcc8", 2),
    "water":              ("#bcd8ea", "#7fb0cc", 3),
    "roads":              (None, "#c9b79a", 4),
    "railways":           (None, "#8a6f9e", 4),
    "aprons":             ("#cfcfcf", "#9a9a9a", 5),
    "taxiways":           (None, "#d8c25a", 6),
    "runways":            (None, "#3a3a3a", 7),
    "buildings":          ("#c8b6a6", "#8a7565", 8),
    "terminals":          ("#b7a0d0", "#6e5a90", 9),
    "hangars":            ("#e07a4a", "#8c3f1c", 10),
}


def draw(ax, data, keys):
    for key in keys:
        face, edge, z = STYLE[key]
        items = data[key] if key != "aerodrome_boundary_xy_m" else \
            [{"polygon_xy_m": p} for p in data[key]]
        for r in items:
            polys = []
            if r.get("polygon_xy_m"):
                polys.append(r["polygon_xy_m"])
            polys += r.get("extra_outer_rings_xy_m", [])
            for p in polys:
                if len(p) < 2:
                    continue
                closed = len(p) > 2 and (abs(p[0][0] - p[-1][0]) < 0.5 and
                                         abs(p[0][1] - p[-1][1]) < 0.5)
                if closed and face:
                    ax.add_patch(Polygon(p, closed=True, facecolor=face,
                                         edgecolor=edge, lw=0.5, zorder=z))
                else:
                    xs = [q[0] for q in p]; ys = [q[1] for q in p]
                    lw = 3.0 if key == "runways" else \
                         1.2 if key == "taxiways" else \
                         1.2 if key == "railways" else 0.6
                    ax.plot(xs, ys, color=edge, lw=lw, zorder=z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--latam", action="store_true")
    a = ap.parse_args()
    data = json.load(open(os.path.join(HERE, "sbgr_osm.json")))

    fig, ax = plt.subplots(figsize=(14, 10), dpi=130)
    draw(ax, data, [k for k in STYLE if k in data])

    # the survey thresholds, from sbgr_aip_survey.json, over the OSM tracing
    try:
        s = json.load(open(os.path.join(HERE, "sbgr_aip_survey.json")))
        for r in s["runways"]:
            for name, th in r["thresholds"].items():
                x, y = th["xy_m"]
                ax.plot([x], [y], "o", color="#d81b60", ms=6, zorder=20)
                ax.annotate("THR " + name, (x, y), textcoords="offset points",
                            xytext=(8, 4), color="#d81b60", fontsize=8,
                            zorder=21)
    except Exception:
        pass

    for r in data["hangars"] + data["terminals"]:
        if r.get("name"):
            c = r.get("centroid_xy_m")
            if c:
                ax.annotate(r["name"], c, fontsize=7, color="#333",
                            ha="center", zorder=22)

    if a.latam:
        ax.set_xlim(1600, 3000); ax.set_ylim(700, 1900)
        out = "sbgr_osm_plan_latam.png"
        for r in data["gates"] + data["parking_positions"]:
            c = r.get("xy_m")
            if c and 1600 < c[0] < 3000 and 700 < c[1] < 1900:
                ax.plot([c[0]], [c[1]], ".", color="#2a6f2a", ms=3, zorder=15)
    else:
        ax.set_xlim(-1300, 4700); ax.set_ylim(-2700, 1900)
        out = "sbgr_osm_plan.png"
    ax.set_aspect("equal")
    ax.grid(True, color="#dddddd", lw=0.4, zorder=0)
    ax.set_xlabel("x  east (m)"); ax.set_ylabel("y  north (m)")
    ax.set_title("SBGR / Guarulhos - OSM plan in the scene frame\n"
                 "origin = THR 10L;  (c) OpenStreetMap contributors, ODbL 1.0",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, out))
    print("wrote", out)


if __name__ == "__main__":
    main()
