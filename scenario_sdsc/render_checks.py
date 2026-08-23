#!/usr/bin/env python3
"""Visual checks on the SDSC scenery. Run each with

    blender -b --factory-startup scenario_sdsc/sdsc_field.blend \\
        -P scenario_sdsc/render_checks.py -- <check> [more checks]

Checks
    plan      orthographic top-down of the whole aerodrome, framed to match
              sdsc_osm_plan.png EXACTLY (x -500..1700, y -400..2300) so the two
              can be laid side by side. THIS is the check that catches a build
              that is silently wrong - a mirrored base, a runway on the
              designator instead of the true track, a footprint in the wrong
              place. Look at it before you look at anything pretty.
    mro       orthographic top-down of the MRO block only, framed to match
              sdsc_osm_plan_mro.png (x 200..1600, y 1000..2200)
    ground    eye level from the roll stations the departure clip will use,
              looking right at the mid-field cluster and then at the MRO
    horizon   the thing TERRAIN.md says to check: a 360 deg sweep at eye level
              from THR 02. The horizon band is 1.6 deg wide and MUST look
              empty - and must NOT look too clean, because a third of it is
              vegetation, not terrain.
    tour      three frames of the aerial tour phase 3 will fly

Output lands in scenario_sdsc/checks/.
"""
import bpy
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "checks")
TERRAIN = os.path.join(HERE, "sdsc_terrain.blend")

TRACK = 1.026                      # TRUE, not the 020 the designator implies
UX = math.sin(math.radians(TRACK))
UY = math.cos(math.radians(TRACK))
NX, NY = -UY, UX                   # +lateral is LEFT of a RWY 02 roll = west
Z_THR02 = 804.67 - 807.0
RWY_SLOPE = ((794.61 - 807.0) - Z_THR02) / 1619.98


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def link_terrain():
    if not os.path.exists(TERRAIN):
        print("!! no terrain blend; run build_scenery.py -- --terrain")
        return
    with bpy.data.libraries.load(TERRAIN, link=True) as (src, dst):
        dst.collections = [c for c in src.collections if c == "SDSC_Terrain"]
    for c in dst.collections:
        if c is None:
            continue
        ob = bpy.data.objects.new("SDSC_Terrain_Link", None)
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


def _ortho(tag, x0, x1, y0, y1, width=1100):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    c = cam("Chk" + tag, (cx, cy, 4000.0), (0, 0, 0),
            ortho=max(x1 - x0, y1 - y0))
    bpy.context.scene.camera = c
    bpy.context.scene.render.pixel_aspect_x = 1.0
    h = int(round(width * (y1 - y0) / (x1 - x0)))
    scn = bpy.context.scene
    scn.render.engine = "BLENDER_WORKBENCH"
    scn.display.shading.light = "FLAT"
    scn.display.shading.color_type = "MATERIAL"
    scn.display.shading.show_xray = False
    if scn.world:
        scn.world.color = (0.02, 0.02, 0.025)
    render(os.path.join(OUT, "plan_%s.png" % tag), res=(width, h),
           engine="BLENDER_WORKBENCH")


def check_plan():
    """Framed to match sdsc_osm_plan.png: x -500..1700, y -400..2300."""
    _ortho("built", -500.0, 1700.0, -400.0, 2300.0)


def check_mro():
    """Framed to match sdsc_osm_plan_mro.png: x 200..1600, y 1000..2200."""
    _ortho("mro", 200.0, 1600.0, 1000.0, 2200.0, width=1100)


_G = None


def _ground():
    """The same graded surface build_scenery.py built the field on, so a
    ground-level check camera stands on the ground and not on the runway plane
    extended sideways - which at 480 m west of the centreline is 14 m of error
    and hands you a view over a crest that is really in the way."""
    global _G
    if _G is None:
        sys.path.insert(0, HERE)
        import build_scenery as bs
        _G = bs.Ground()
    return _G


def _roll_point(dist, lateral, agl, on_ground=False):
    """A point in runway coordinates. `agl` is above the SLOPING runway surface,
    or above the real ground when on_ground is set."""
    x = UX * dist + NX * lateral
    y = UY * dist + NY * lateral
    z = (_ground().graded(x, y) if on_ground
         else Z_THR02 + RWY_SLOPE * dist) + agl
    return (x, y, z)


def check_ground():
    """Eye-level frames from where the departure clip's camera will be.

    All of them look RIGHT of a RWY 02 roll, because that is where the base is
    (RECOGNITION.md section 1) - the only thing on the LEFT is the Aeroclube in
    the first 500 m. The two 'abeam' frames are at the stations
    sdsc_osm.json/departure_02_landmarks gives for the mid-field cluster
    (1 146 m) and the MRO (1 602-1 940 m)."""
    link_terrain()
    scn = bpy.context.scene
    for (tag, dist, lat, agl, look_brg, lens, ong) in (
            ("thr02_down_runway", -140.0, 0.0, 6.0, 1.0, 50.0, False),
            ("aeroclube_left", 300.0, 60.0, 8.0, 300.0, 40.0, False),
            ("abeam_midfield", 1146.0, 40.0, 10.0, 91.0, 50.0, False),
            ("abeam_mro_rotate", 1670.0, 0.0, 35.0, 70.0, 50.0, False),
            ("abeam_mro_tele", 1670.0, 0.0, 35.0, 70.0, 135.0, False),
            # the SP-318 frame: standing on the real ground 480 m west of the
            # centreline. THE MRO SHOULD NOT BE VISIBLE FROM HERE - the runway
            # is a crest and the base is 35 m down behind it. If it is, the
            # platform level is wrong.
            ("sp318_from_west", 1150.0, 620.0, 1.7, 72.0, 105.0, True),
            ("sp318_midfield", 1150.0, 620.0, 1.7, 91.0, 160.0, True),
            ("climbout_north", 2400.0, -120.0, 220.0, 200.0, 35.0, False)):
        loc = _roll_point(dist, lat, agl, on_ground=ong)
        c = cam("Chk_" + tag, loc,
                (math.radians(89.0), 0.0, math.radians(-look_brg)), lens=lens)
        scn.camera = c
        render(os.path.join(OUT, "ground_%s.png" % tag), res=(1280, 720))


def check_horizon():
    """The SDSC-specific check. TERRAIN.md section 3: the whole 360 deg horizon
    band spans -0.32 to +1.30 deg, and the near field beats the terrain at 24 of
    72 azimuths. Two failures to look for, and they pull opposite ways:
      * too LOW and too CLEAN  -> the tree line is missing or too short
      * a skyline               -> something is standing where nothing does"""
    link_terrain()
    scn = bpy.context.scene
    for (tag, brg) in (("n_000", 0.0), ("e_090", 90.0),
                       ("s_180", 180.0), ("w_270", 270.0)):
        loc = _roll_point(0.0, 0.0, 5.0)     # the observer horizon.py used
        c = cam("Chk_h_" + tag, loc,
                (math.radians(90.0), 0.0, math.radians(-brg)), lens=24.0)
        scn.camera = c
        render(os.path.join(OUT, "horizon_%s.png" % tag), res=(1280, 400),
               samples=48)


def check_tour():
    """Three frames of the aerial tour phase 3 has to fly."""
    link_terrain()
    scn = bpy.context.scene
    for (tag, loc, rot, lens) in (
            ("tour_mro_high", (300.0, 1100.0, 420.0),
             (math.radians(62.0), 0.0, math.radians(-62.0)), 35.0),
            ("tour_hangar9", (500.0, 1400.0, 90.0),
             (math.radians(80.0), 0.0, math.radians(-55.0)), 50.0),
            ("tour_field_south", (-900.0, -1500.0, 700.0),
             (math.radians(66.0), 0.0, math.radians(-25.0)), 28.0)):
        c = cam("Chk_" + tag, loc, rot, lens=lens)
        scn.camera = c
        render(os.path.join(OUT, "%s.png" % tag), res=(1280, 720), samples=64)


def main():
    os.makedirs(OUT, exist_ok=True)
    todo = args() or ["plan"]
    table = {"plan": check_plan, "mro": check_mro, "ground": check_ground,
             "horizon": check_horizon, "tour": check_tour}
    for t in todo:
        table[t]()


if __name__ == "__main__":
    main()
