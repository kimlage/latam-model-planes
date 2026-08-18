#!/usr/bin/env python3
"""Build the SCL terrain mesh in Blender from the heightfields.

Run inside Blender (Scripting tab, or via the blender-mcp addon):

    import sys; sys.path.append("<...>/cenario")
    import carregar_terreno as t
    t.build_all()

Coordinates are the scene's local metric frame (see lib/frame.py):
x East, y North, z Up, metres, origin at the RWY 17L threshold, z = 0 at
474 m AMSL. Blender units are metres, 1:1 - no scaling.
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__))
TERRENO = os.path.join(HERE, "terreno")


def _meta():
    return json.load(open(os.path.join(TERRENO, "terreno_meta.json")))


def build(name="terreno_scl_60m", stride=1, obj_name=None, mask_inner=None):
    """Create a mesh from one heightfield.

    stride      decimates (2 = half resolution)
    mask_inner  (x0, x1, y0, y1) in metres: drop faces whose centre falls inside
                this box, so a coarse tier can ring a finer one without z-fighting
    """
    import bpy, numpy as np

    m = _meta()["grids"][name]
    z = np.load(os.path.join(TERRENO, m["file"]))[::stride, ::stride]
    ny, nx = z.shape
    step = m["step_m"] * stride
    x0, y0 = m["x_min_m"], m["y_min_m"]

    xs = x0 + np.arange(nx) * step
    ys = y0 + np.arange(ny) * step
    X, Y = np.meshgrid(xs, ys)
    verts = np.empty((ny * nx, 3), dtype=np.float32)
    verts[:, 0] = X.ravel(); verts[:, 1] = Y.ravel()
    verts[:, 2] = np.nan_to_num(z, nan=0.0).ravel()

    # quad faces over the regular grid
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
    """The scene is 130 km wide. Blender's default 100 m clip end hides all of it."""
    import bpy
    for cam in bpy.data.cameras:
        cam.clip_end = max(cam.clip_end, far_m)
        cam.clip_start = min(cam.clip_start, near_m)
    for area in getattr(bpy.context.screen, "areas", []):
        if area.type == "VIEW_3D":
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.clip_end = max(sp.clip_end, far_m)


def build_all(stride_mid=1):
    """Three tiers, coarse to fine, each ringing the next.

      Andes_terreno_longe  180 m, +-150 km : closes the horizon in every
                                             direction (the southern skyline
                                             sits 70-150 km out)
      Andes_terreno        60 m            : the required box, the Andes wall
      SCL_terreno_proximo  30 m, +-15 km   : the aerodrome surroundings
    """
    m = _meta()["grids"]
    g60 = m["terreno_scl_60m"]; g30 = m["terreno_scl_perto_30m"]
    far = build("terreno_scl_longe_180m", obj_name="Andes_terreno_longe",
                mask_inner=(g60["x_min_m"], g60["x_max_m"],
                            g60["y_min_m"], g60["y_max_m"]))
    mid = build("terreno_scl_60m", stride=stride_mid, obj_name="Andes_terreno",
                mask_inner=(g30["x_min_m"], g30["x_max_m"],
                            g30["y_min_m"], g30["y_max_m"]))
    near = build("terreno_scl_perto_30m", obj_name="SCL_terreno_proximo")
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
            print("  %-24s %s  step %.0f m  x %.1f..%.1f km  y %.1f..%.1f km"
                  % (k, g["shape"], g["step_m"], g["x_min_m"] / 1000,
                     g["x_max_m"] / 1000, g["y_min_m"] / 1000, g["y_max_m"] / 1000))
