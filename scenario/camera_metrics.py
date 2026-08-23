#!/usr/bin/env python3
"""Measure whether a camera move is comfortable to watch, in numbers.

    blender -b "airbus A320neo/A320neo_scl.blend" -P scenario/camera_metrics.py
    blender -b <file>.blend -P scenario/camera_metrics.py -- --json out.json
    blender -b <file>.blend -P scenario/camera_metrics.py -- --pivot B789_Tow

``--pivot`` names the Empty the subject hangs from; it defaults to ``AviaoPivo``,
which is what every Santiago file calls it. A scene with no moving subject at all
- the SDSC aerial tour, say - passes ``--pivot none`` and gets everything except
the silhouette and the edge-margin columns.

Degrees per second is the wrong unit. What the eye reads is how much of the
FRAME WIDTH the world crosses per second, and that is (angular rate / HFOV) -
so the same pan through a 140 mm lens is four times faster on screen than
through a 35 mm one. Below ~0.5 frame-widths/s reads as calm; above ~1.0
disorients. This script measures that directly rather than inferring it:

* SCREEN FLOW. At each frame a grid of screen points is ray-cast into the
  scene; the world points that come back are re-projected at the next frame and
  the displacement is converted to frame-widths per second. Rays that miss
  everything are pinned at 80 km so the sky and the cordillera still count.
  Reported twice: over the whole frame, and over the central band only. A low,
  fast tracking shot always streaks at the very bottom edge - that reads as
  speed, not disorientation - and the central band is what the eye uses to stay
  oriented.
* NEAR OBJECTS. For every frame, the closest scenery hit inside the frustum,
  which object it belongs to, and the angular rate that proximity produces at
  the current camera speed. This is what catches a camera flying through a tree
  line: a 30 m tree crossing at 114 m/s sweeps 15 frame-widths per second.
* THIN GEOMETRY. Projected pixel width of the light masts, the usual suspect
  when something "flickers" - anything approaching one pixel wide appears and
  disappears between frames.
* EDGE MARGIN. The aircraft's silhouette cloud projected into the frame, and
  its smallest distance to any frame edge.
"""
import bpy
import json
import math
import sys

from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

FAR = 80000.0
GRID_X, GRID_Y = 13, 9
MID_BAND = (0.22, 0.92)      # rows of the grid counted as "central"
MAST_SHAFT_M = 1.50          # SCL_LightMasts shaft section, build_scenery.py


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def descendants(ob):
    out = []
    for c in ob.children:
        out.append(c)
        out.extend(descendants(c))
    return out


def silhouette_cloud(piv, dg, budget=6000):
    """Aircraft vertices in pivot-local space, thinned to `budget` points."""
    pts = []
    inv = piv.matrix_world.inverted()
    for o in descendants(piv):
        if o.type != "MESH" or not o.visible_get():
            continue
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        m = inv @ o.matrix_world
        pts.extend(m @ v.co for v in me.vertices)
        oe.to_mesh_clear()
    step = max(1, len(pts) // budget)
    return pts, pts[::step]


def main():
    a = args()
    out_json = a[a.index("--json") + 1] if "--json" in a else None

    scn = bpy.context.scene
    cam = scn.camera
    pivot_name = a[a.index("--pivot") + 1] if "--pivot" in a else "AviaoPivo"
    piv = bpy.data.objects.get(pivot_name)
    if piv is None and pivot_name != "none":
        print("!! no object %r; measuring without a subject" % pivot_name)
    fps = scn.render.fps / scn.render.fps_base
    res_x, res_y = scn.render.resolution_x, scn.render.resolution_y
    aspect = res_x / res_y
    f0, f1 = scn.frame_start, scn.frame_end

    dg = bpy.context.evaluated_depsgraph_get()
    if piv is None:
        cloud, aircraft = [], set()
        print("no subject: skipping the silhouette and edge-margin columns")
    else:
        full, cloud = silhouette_cloud(piv, dg)
        aircraft = set(o.name for o in descendants(piv)) | {piv.name}
        print("silhouette cloud: %d points (thinned from %d)"
              % (len(cloud), len(full)))

    probes = [((i + 0.5) / GRID_X, (j + 0.5) / GRID_Y)
              for j in range(GRID_Y) for i in range(GRID_X)]

    masts = bpy.data.objects.get("SCL_LightMasts")

    def ray(u, v, lens):
        half_x = (cam.data.sensor_width / 2.0) / lens
        half_y = half_x / aspect
        d = Vector(((u - 0.5) * 2 * half_x, (v - 0.5) * 2 * half_y, -1.0))
        return (cam.matrix_world.to_quaternion() @ d).normalized()

    rows, prev = [], None
    for f in range(f0, f1 + 1):
        scn.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        c = cam.matrix_world.translation.copy()
        q = cam.matrix_world.to_quaternion()
        fwd = (q @ Vector((0, 0, -1))).normalized()
        lens = cam.data.lens
        hfov = 2.0 * math.atan((cam.data.sensor_width / 2.0) / lens)

        pts, near = [], (1e18, "", 0.0, 0.0)
        for (u, v) in probes:
            d = ray(u, v, lens)
            hit, loc, _n, _i, ob, _m = scn.ray_cast(dg, c, d, distance=FAR)
            if hit and ob is not None and ob.name in aircraft:
                hit = False
            p = loc.copy() if hit else (c + d * FAR)
            pts.append(p)
            if hit:
                dist = (p - c).length
                if dist < near[0]:
                    near = (dist, ob.name, u, v)

        m = piv.matrix_world if piv is not None else None
        xs, ys, ok = [], [], bool(cloud)
        for p in cloud:
            co = world_to_camera_view(scn, cam, m @ p)
            if co.z <= 0:
                ok = False
                break
            xs.append(co.x)
            ys.append(co.y)
        margin = min(min(xs), 1 - max(xs), min(ys), 1 - max(ys)) if ok and xs \
            else float("nan")

        row = dict(f=f, lens=lens, cam=[c.x, c.y, c.z], margin=margin,
                   az=math.degrees(math.atan2(fwd.x, fwd.y)) % 360.0,
                   el=math.degrees(math.asin(max(-1, min(1, fwd.z)))),
                   near_dist=near[0] if near[0] < 1e17 else float("nan"),
                   near_obj=near[1])

        if masts is not None:
            # projected shaft width of every mast inside the frame, in output
            # pixels: the aliasing test for "thin geometry that flickers".
            widths = []
            oe = masts.evaluated_get(dg)
            me = oe.to_mesh()
            mm = masts.matrix_world
            for k in range(0, len(me.vertices), 16):
                p = mm @ me.vertices[k].co
                co = world_to_camera_view(scn, cam, p)
                if co.z <= 0 or not (0 <= co.x <= 1 and 0 <= co.y <= 1):
                    continue
                widths.append(MAST_SHAFT_M / co.z / (2 * math.tan(hfov / 2))
                              * res_x)
            oe.to_mesh_clear()
            if widths:
                row["mast_px_min"] = min(widths)
                row["mast_px_max"] = max(widths)
        if prev is not None:
            flows, flows_mid = [], []
            for p, a0, (u, v) in zip(prev["pts"], prev["ndc"], probes):
                if a0 is None:
                    continue
                b = world_to_camera_view(scn, cam, p)
                if b.z <= 0:
                    continue
                fl = math.hypot(b.x - a0.x, (b.y - a0.y) / aspect) * fps
                flows.append(fl)
                if MID_BAND[0] <= v <= MID_BAND[1]:
                    flows_mid.append(fl)
            for key, vals in (("flow", flows), ("flow_mid", flows_mid)):
                if vals:
                    vals.sort()
                    row[key] = vals[len(vals) // 2]
                    row[key + "_p90"] = vals[int(len(vals) * 0.9)]
                    row[key + "_max"] = vals[-1]
            dcam = (Vector(prev["cam"]) - c).length * fps
            row["cam_speed"] = dcam
            dz = (row["az"] - prev["az"] + 540) % 360 - 180
            row["pan"] = abs(dz) * fps
            row["tilt"] = abs(row["el"] - prev["el"]) * fps
        rows.append(row)
        prev = dict(pts=pts, cam=[c.x, c.y, c.z], az=row["az"],
                    el=row["el"],
                    ndc=[(lambda co: co if co.z > 0 else None)(
                        world_to_camera_view(scn, cam, p)) for p in pts])

    # ---------------------------------------------------------------- report
    print("\n%-5s %7s %7s %7s %8s %8s %8s %9s %10s %8s"
          % ("frame", "lens", "az", "pan_d/s", "flow", "flow_mid", "flow_max",
             "cam_m/s", "near_m", "margin"))
    for r in rows:
        if r["f"] % 10 and r["f"] not in (f0, f1, 70):
            continue
        print("%-5d %7.1f %7.1f %7.2f %8.3f %8.3f %8.3f %9.1f %10.0f %8.4f"
              % (r["f"], r["lens"], r["az"], r.get("pan", float("nan")),
                 r.get("flow", float("nan")), r.get("flow_mid", float("nan")),
                 r.get("flow_max", float("nan")),
                 r.get("cam_speed", float("nan")), r["near_dist"], r["margin"]))

    def stat(key):
        v = sorted(r[key] for r in rows if key in r and r[key] == r[key])
        return (v[len(v) // 2], v[int(len(v) * .9)], v[-1]) if v else (0, 0, 0)

    print("\n--- SUMMARY  %d..%d @ %.0f fps = %.2f s, %dx%d ---"
          % (f0, f1, fps, (f1 - f0 + 1) / fps, res_x, res_y))
    print("lens %.1f -> %.1f mm" % (rows[0]["lens"], rows[-1]["lens"]))
    for key, label in (("flow", "screen flow, whole frame"),
                       ("flow_mid", "screen flow, central band"),
                       ("flow_max", "worst probe in frame")):
        med, p90, mx = stat(key)
        print("%-26s median %.3f  p90 %.3f  max %.3f  frame-widths/s"
              % (label, med, p90, mx))
    fl = [r["flow_mid"] for r in rows if "flow_mid" in r]
    for thr in (0.5, 1.0):
        print("  central-band frames above %.1f w/s: %d of %d"
              % (thr, sum(1 for x in fl if x > thr), len(fl)))
    body = fl[8:-8]
    print("  body ratio (excl. 8-frame ease each end) max/min = %.1f"
          % (max(body) / max(min(body), 1e-9)))
    nd = [r["near_dist"] for r in rows if r["near_dist"] == r["near_dist"]]
    worst = min(rows, key=lambda r: r["near_dist"] if r["near_dist"] == r["near_dist"] else 1e18)
    print("nearest scenery in frame: min %.0f m (frame %d, %s), median %.0f m"
          % (min(nd), worst["f"], worst["near_obj"], sorted(nd)[len(nd) // 2]))
    par = [(r["cam_speed"] / r["near_dist"], r["f"]) for r in rows
           if "cam_speed" in r and r["near_dist"] == r["near_dist"]
           and r["near_dist"] > 0]
    p, pf = max(par)
    print("worst foreground parallax: %.1f deg/s at frame %d"
          % (math.degrees(p), pf))
    mp = [r["mast_px_min"] for r in rows if "mast_px_min" in r]
    if mp:
        print("light-mast shaft width in frame: thinnest %.2f px, "
              "thickest %.2f px (of %d)"
              % (min(mp), max(r["mast_px_max"] for r in rows
                              if "mast_px_max" in r), res_x))
    mg = [r["margin"] for r in rows if r["margin"] == r["margin"]]
    if mg:
        mf = min(rows, key=lambda r: r["margin"]
                 if r["margin"] == r["margin"] else 9)
        print("aircraft edge margin: min %.4f (%.2f%%) at frame %d"
              % (min(mg), 100 * min(mg), mf["f"]))
    cs = [r["cam_speed"] for r in rows if "cam_speed" in r]
    print("camera speed %.0f..%.0f m/s" % (min(cs), max(cs)))

    if out_json:
        for r in rows:
            r.pop("pts", None)
        json.dump(rows, open(out_json, "w"), indent=1, default=float)
        print("wrote", out_json)


if __name__ == "__main__":
    main()
