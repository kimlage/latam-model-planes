#!/usr/bin/env python3
"""Build the SBGR terrain mesh in Blender from the heightfields in terrain/.

Sibling of ../scenario_sdsc/load_terrain.py; same API, same three-tier
structure, the tier-seam sink values re-measured for THIS terrain (see
TIER_SINK below - Sao Paulo hills are rougher than the Sao Carlos plate).

Coordinates are the scene's local metric frame (see lib/frame.py):
x East, y North, z Up, metres, origin at the published RWY 10L threshold,
z = 0 at 750 m AMSL. Blender units are metres, 1:1 - no scaling.

The three tiers each carry something SBGR-specific:
  Near  30 m, +-15 km : the field, the city ring, and the whole Cabucu spur -
                        the +3.2 deg north wall lives INSIDE this tier
  Mid   60 m, +-50 km : Greater Sao Paulo, the Cantareira crest, Serra do Mar
  Far  180 m, +-120 km: the Mantiqueira and the ATLANTIC - the first ocean in
                        this project; its only shape is the curvature drop
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__))
TERRAIN = os.path.join(HERE, "terrain")


def _meta():
    return json.load(open(os.path.join(TERRAIN, "terrain_meta.json")))


def build(name="terrain_sbgr_60m", stride=1, obj_name=None, mask_inner=None,
          sink=None):
    """Create a mesh from one heightfield.

    stride      decimates (2 = half resolution)
    mask_inner  (x0, x1, y0, y1) in metres: drop faces whose centre falls inside
                this box, so a coarse tier can ring a finer one
    sink        (x0, x1, y0, y1, depth, ramp): push this tier DOWN by `depth`
                metres inside the box, ramping back to zero over `ramp` metres
                outside it - the SDSC tier-de-confliction, numbers re-measured
                for this terrain."""
    import bpy, numpy as np

    m = _meta()["grids"][name]
    z = np.load(os.path.join(TERRAIN, m["file"]))[::stride, ::stride]
    ny, nx = z.shape
    step = m["step_m"] * stride
    x0, y0 = m["x_min_m"], m["y_min_m"]

    xs = x0 + np.arange(nx) * step
    ys = y0 + np.arange(ny) * step
    X, Y = np.meshgrid(xs, ys)
    verts = np.empty((ny * nx, 3), dtype=np.float32)
    verts[:, 0] = X.ravel(); verts[:, 1] = Y.ravel()
    verts[:, 2] = np.nan_to_num(z, nan=0.0).ravel()

    if sink is not None:
        sx0, sx1, sy0, sy1, depth, ramp = sink
        dx = np.maximum(np.maximum(sx0 - X, X - sx1), 0.0).ravel()
        dy = np.maximum(np.maximum(sy0 - Y, Y - sy1), 0.0).ravel()
        t = np.clip(np.hypot(dx, dy) / max(ramp, 1e-6), 0.0, 1.0)
        verts[:, 2] -= depth * (1.0 - t * t * (3.0 - 2.0 * t))

    idx = np.arange(ny * nx).reshape(ny, nx)
    a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel()
    c = idx[1:, 1:].ravel();   d = idx[1:, :-1].ravel()
    faces = np.stack([a, b, c, d], axis=1).astype(np.int32)

    if mask_inner is not None:
        mx0, mx1, my0, my1 = mask_inner
        cx = (verts[faces[:, 0], 0] + verts[faces[:, 2], 0]) * 0.5
        cy = (verts[faces[:, 0], 1] + verts[faces[:, 2], 1]) * 0.5
        keep = ~((cx > mx0) & (cx < mx1) & (cy > my0) & (cy < my1))
        faces = faces[keep]

    me = bpy.data.meshes.new(obj_name or name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(faces.size)
    me.loops.foreach_set("vertex_index", faces.ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set("loop_start", np.arange(len(faces), dtype=np.int32) * 4)
    me.polygons.foreach_set("loop_total", np.full(len(faces), 4, dtype=np.int32))
    me.update(); me.validate()

    ob = bpy.data.objects.new(obj_name or name, me)
    bpy.context.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    print("%s: %d verts, %d faces, step %.0f m, extent %.1f x %.1f km"
          % (ob.name, len(verts), len(faces), step,
             (nx - 1) * step / 1000, (ny - 1) * step / 1000))
    return ob


def fix_camera_clipping(far_m=250000.0, near_m=1.0):
    """The scene is 240 km wide. Blender's default 100 m clip end hides it."""
    import bpy
    for cam in bpy.data.cameras:
        cam.clip_end = max(cam.clip_end, far_m)
        cam.clip_start = min(cam.clip_start, near_m)
    for area in getattr(bpy.context.screen, "areas", []):
        if area.type == "VIEW_3D":
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.clip_end = max(sp.clip_end, far_m)


# Tier de-confliction, the SDSC fix with SBGR numbers. MEASURED on these grids
# (40 000 random probes in the seam bands, 2026-08-26):
#   60 m vs 30 m over a 200 m band inside the near boundary: +8.49 / -8.91 m
#  180 m vs 60 m over a 600 m band inside the mid boundary:  +35.08 / -51.84 m
# The sink beats the positive tail; the ramp keeps the residual step under
# ~0.03 deg from anywhere a camera stands in this project.
TIER_SHRINK = 2.0        # coarse cells the mask is pulled IN by, so it overlaps
TIER_SINK = {"mid": (9.5, 1500.0), "far": (38.0, 6000.0)}


def _dc(fine, coarse_step, tag):
    """(mask_inner, sink) for a coarse tier that has to underlie `fine`."""
    pad = TIER_SHRINK * coarse_step
    box = (fine["x_min_m"], fine["x_max_m"], fine["y_min_m"], fine["y_max_m"])
    depth, ramp = TIER_SINK[tag]
    return ((box[0] + pad, box[1] - pad, box[2] + pad, box[3] - pad),
            (box[0], box[1], box[2], box[3], depth, ramp))


def build_all(stride_mid=1, stride_far=1):
    m = _meta()["grids"]
    g60 = m["terrain_sbgr_60m"]; g30 = m["terrain_sbgr_near_30m"]
    mk, sk = _dc(g60, 180.0 * stride_far, "far")
    far = build("terrain_sbgr_far_180m", stride=stride_far,
                obj_name="SBGR_Terrain_Far", mask_inner=mk, sink=sk)
    mk, sk = _dc(g30, 60.0 * stride_mid, "mid")
    mid = build("terrain_sbgr_60m", stride=stride_mid,
                obj_name="SBGR_Terrain_Mid", mask_inner=mk, sink=sk)
    near = build("terrain_sbgr_near_30m", obj_name="SBGR_Terrain_Near")
    fix_camera_clipping()
    return far, mid, near


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
        build_all()
    except ImportError:
        m = _meta()
        print("Run this inside Blender. Available heightfields:")
        for k, g in m["grids"].items():
            print("  %-26s %s  step %.0f m  x %.1f..%.1f km  y %.1f..%.1f km"
                  % (k, g["shape"], g["step_m"], g["x_min_m"] / 1000,
                     g["x_max_m"] / 1000, g["y_min_m"] / 1000,
                     g["y_max_m"] / 1000))
