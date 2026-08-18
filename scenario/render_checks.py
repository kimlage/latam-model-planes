#!/usr/bin/env python3
"""Visual checks on the SCL scenery. Run each with

    blender -b --factory-startup scenario/scl_field.blend \\
        -P scenario/render_checks.py -- <check> [more checks]

Checks
    plan        orthographic top-down of the whole aerodrome, framed to match
                scl_osm_plan.png so the two can be compared side by side
    ground      eye-level views west of RWY 17R looking east, at the roll
                stations where the take-off camera will be
    andes       wide view east from the 17R threshold: the cordillera silhouette
"""
import bpy
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "checks")
TERRAIN = os.path.join(HERE, "scl_terrain.blend")

THR_17R = (-1582.57, 459.21)
TRACK = 177.424


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def link_terrain():
    if not os.path.exists(TERRAIN):
        print("!! no terrain blend; run build_scenery.py -- --terrain")
        return
    with bpy.data.libraries.load(TERRAIN, link=True) as (src, dst):
        dst.collections = [c for c in src.collections if c == "SCL_Terrain"]
    for c in dst.collections:
        if c is None:
            continue
        ob = bpy.data.objects.new("SCL_Terrain_Link", None)
        ob.instance_type = "COLLECTION"
        ob.instance_collection = c
        bpy.context.scene.collection.objects.link(ob)
        print("linked terrain:", c.name)


def cam(name, loc, rot, lens=50.0, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.clip_start = 0.5
    cd.clip_end = 300000.0
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    ob.rotation_euler = rot
    bpy.context.scene.collection.objects.link(ob)
    return ob


def render(path, res=(1280, 720), engine="CYCLES", samples=64):
    scn = bpy.context.scene
    scn.render.engine = engine
    if engine == "CYCLES":
        scn.cycles.samples = samples
        scn.cycles.use_denoising = True
        scn.cycles.max_bounces = 4
        scn.cycles.transparent_max_bounces = 4
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.resolution_percentage = 100
    scn.render.film_transparent = False
    scn.render.filepath = path
    scn.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("wrote", path)


def check_plan():
    """Match the framing of scl_osm_plan.png: x -2700..900, y -4500..500."""
    x0, x1, y0, y1 = -2700.0, 900.0, -4500.0, 500.0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    c = cam("ChkPlan", (cx, cy, 4000.0), (0, 0, 0), ortho=(y1 - y0))
    bpy.context.scene.camera = c
    bpy.context.scene.render.pixel_aspect_x = 1.0
    w = 1100
    h = int(round(w * (y1 - y0) / (x1 - x0)))
    # ortho_scale applies to the larger dimension
    c.data.ortho_scale = max(x1 - x0, y1 - y0)
    scn = bpy.context.scene
    scn.render.engine = "BLENDER_WORKBENCH"
    scn.display.shading.light = "FLAT"
    scn.display.shading.color_type = "MATERIAL"
    scn.display.shading.show_xray = False
    scn.world.color = (0.02, 0.02, 0.025)
    render(os.path.join(OUT, "plan_built.png"), res=(w, h),
           engine="BLENDER_WORKBENCH")


def _roll_point(dist, lateral, z):
    ux, uy = math.sin(math.radians(TRACK)), math.cos(math.radians(TRACK))
    nx, ny = -uy, ux                     # left of the roll = east
    return (THR_17R[0] + ux * dist + nx * lateral,
            THR_17R[1] + uy * dist + ny * lateral, z)


def check_ground():
    link_terrain()
    scn = bpy.context.scene
    for (tag, dist, lat, look_brg, lens, z) in (
            ("abeam_latam", 1786.0, -140.0, 90.0, 90.0, 12.0),
            ("abeam_latam_wide", 1786.0, -140.0, 90.0, 35.0, 12.0),
            ("threshold_look_south", 60.0, -120.0, 160.0, 50.0, 12.0),
            ("terminals", 3100.0, -160.0, 100.0, 60.0, 14.0)):
        loc = _roll_point(dist, lat, z)
        c = cam("Chk_" + tag, loc,
                (math.radians(89.0), 0.0, math.radians(-look_brg)), lens=lens)
        scn.camera = c
        render(os.path.join(OUT, "ground_%s.png" % tag), res=(1280, 720))


def check_andes():
    link_terrain()
    scn = bpy.context.scene
    for (tag, brg, lens) in (("andes_east", 90.0, 35.0),
                             ("andes_ne", 60.0, 50.0),
                             ("coast_west", 262.0, 35.0)):
        loc = _roll_point(1800.0, -200.0, 15.0)
        c = cam("Chk_" + tag, loc,
                (math.radians(88.0), 0.0, math.radians(-brg)), lens=lens)
        scn.camera = c
        render(os.path.join(OUT, "%s.png" % tag), res=(1280, 720), samples=48)


def main():
    os.makedirs(OUT, exist_ok=True)
    todo = args() or ["plan"]
    for t in todo:
        {"plan": check_plan, "ground": check_ground, "andes": check_andes}[t]()


if __name__ == "__main__":
    main()
