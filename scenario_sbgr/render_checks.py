#!/usr/bin/env python3
"""Visual checks on the SBGR scenery. Run each with

    blender -b --factory-startup scenario_sbgr/sbgr_field.blend \\
        -P scenario_sbgr/render_checks.py -- <check> [more checks]

Checks
    plan      orthographic top-down of the whole aerodrome, framed to match
              sbgr_osm_plan.png EXACTLY (x -1300..4700, y -2700..1900) so the
              two can be laid side by side. THIS is the check that catches a
              build that is silently wrong - a mirrored field, runways on the
              magnetic designator, the LATAM corner in the wrong place.
    latam     orthographic top-down of the NE maintenance corner, framed to
              match sbgr_osm_plan_latam.png (x 1600..3000, y 700..1900)
    ground    eye level from the 10L roll stations the departure clip will
              use - including the frame the whole base exists for: the
              south-side camera that holds the rotating heavy, the LATAM
              hangar and the Cantareira wall in one composition
              (refs/latam_cargo_767_north_rwy_cantareira_2023.jpg)
    horizon   the ring: N/E/S/W sweeps at eye level from THR 10L, checked
              against terrain/horizon_5deg.json (N sector +1.8..+3.2 deg,
              departure sector ESE +0.22..+0.72, never negative)
    tour      frames of the aerial tour phase 3 will fly
    fleet     the populated ramp, close enough to argue about - the 901 row,
              the hangar 777, the T2/T3 frontage, the cargo pair

Output lands in scenario_sbgr/checks/ (git-ignored).
"""
import bpy
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "checks")
TERRAIN = os.path.join(HERE, "sbgr_terrain.blend")

TRACK = 73.65
UX = math.sin(math.radians(TRACK))
UY = math.cos(math.radians(TRACK))
NX, NY = -UY, UX                   # +lateral = LEFT of a 10L roll = NNW
THR10L = (-2.7, 12.3)              # the BUILT (OSM-traced) threshold
Z_THR10L = -4.76
SLOPE_N = (-5.98 + 4.76) / 3548.7


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def roll_point(along, lat, agl):
    """A camera position relative to the 10L roll (along from THR 10L)."""
    x = THR10L[0] + UX * along + NX * lat
    y = THR10L[1] + UY * along + NY * lat
    return (x, y, Z_THR10L + SLOPE_N * along + agl)


def link_terrain():
    if not os.path.exists(TERRAIN):
        print("!! no terrain blend; run build_scenery.py -- --terrain")
        return
    with bpy.data.libraries.load(TERRAIN, link=True) as (src, dst):
        dst.collections = [c for c in src.collections if c == "SBGR_Terrain"]
    for c in dst.collections:
        if c is None:
            continue
        ob = bpy.data.objects.new("SBGR_Terrain_Link", None)
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
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = (d.type == "METAL")
            scn.cycles.device = "GPU"
        except Exception as exc:
            print("METAL unavailable, CPU render:", exc)
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.resolution_percentage = 100
    scn.render.film_transparent = False
    scn.render.filepath = path
    scn.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("wrote", path)


def _ortho(tag, x0, x1, y0, y1, width=1400):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    c = cam("Chk" + tag, (cx, cy, 4000.0), (0, 0, 0),
            ortho=max(x1 - x0, y1 - y0))
    bpy.context.scene.camera = c
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
    """Framed to match sbgr_osm_plan.png: x -1300..4700, y -2700..1900."""
    _ortho("built", -1300.0, 4700.0, -2700.0, 1900.0)


def check_latam():
    """Framed to match sbgr_osm_plan_latam.png: x 1600..3000, y 700..1900."""
    _ortho("latam", 1600.0, 3000.0, 700.0, 1900.0, width=1100)


def _look_at(tag, eye, aim, lens):
    dx, dy = aim[0] - eye[0], aim[1] - eye[1]
    horiz = math.hypot(dx, dy)
    az = math.atan2(dx, dy)
    el = math.atan2(aim[2] - eye[2], horiz)
    c = cam("Chk_" + tag, eye, (math.pi / 2.0 + el, 0.0, -az), lens=lens)
    bpy.context.scene.camera = c
    return c


def check_ground():
    """The 10L roll, seen the way the phase-3 clips will see it."""
    link_terrain()
    scn = bpy.context.scene
    shots = (
        # lined up on 10L at the displaced threshold, cockpit height
        ("thr10L_down_runway", roll_point(-60.0, 0.0, 6.0),
         roll_point(1200.0, 0.0, 4.0), 50.0),
        # mid-roll, terminals + tower going past on the LEFT
        ("roll_terminals_left", roll_point(700.0, 0.0, 10.0),
         (301.0, 1322.0, 30.0), 45.0),
        # THE frame: from the south runway, the north runway abeam the
        # hangars with the Cabucu/Cantareira wall behind - the 2023 LATAM
        # Cargo composition. EYE INSIDE THE FENCE: the first pass stood at
        # (2000, -220), which the boundary ring's SCI notch puts OUTSIDE the
        # field, and rendered the 2.6 m fence as a wall across the frame.
        ("south_side_hangar_ridge", (1950.0, 60.0, -2.0),
         (2400.0, 1300.0, 25.0), 70.0),
        # abeam the LATAM hangar at rotation (2575 m along, hangar 654 m out
        # on the left)
        ("abeam_hangar_rotate", roll_point(2575.0, 0.0, 15.0),
         (2281.0, 1362.0, 10.0), 60.0),
        ("abeam_hangar_tele", roll_point(2300.0, -60.0, 8.0),
         (2281.0, 1362.0, 18.0), 135.0),
        # the climb-out: ESE into the LOWEST horizon sector
        ("climbout_ese", roll_point(3400.0, 0.0, 120.0),
         roll_point(6000.0, 0.0, 40.0), 35.0),
        # the city at the fence, NE corner - eye ON the ramp inside the
        # fence (the first pass stood outside at a z below the DSM surface
        # and rendered the underside of the city sheet)
        ("city_fence_ne", (2550.0, 1350.0, -5.5),
         (3300.0, 2350.0, 60.0), 40.0),
    )
    for (tag, eye, aim, lens) in shots:
        _look_at(tag, eye, aim, lens)
        render(os.path.join(OUT, "ground_%s.png" % tag), res=(1280, 720))


def check_horizon():
    """The ring. TERRAIN.md: N +1.8..+3.2 deg (the Cabucu wall at 4-5 km),
    E (departure) +0.22..+0.72, S +1.5..+2.1 (near city ridge), W +0.8..+2.2
    (Cantareira crest / Jaraguá). NEVER negative, and never clean - the near
    sectors carry city fabric."""
    link_terrain()
    scn = bpy.context.scene
    for (tag, brg) in (("n_000", 0.0), ("e_090", 90.0),
                       ("s_180", 180.0), ("w_270", 270.0)):
        loc = roll_point(0.0, 0.0, 5.0)
        c = cam("Chk_h_" + tag, loc,
                (math.radians(90.0), 0.0, math.radians(-brg)), lens=24.0)
        scn.camera = c
        render(os.path.join(OUT, "horizon_%s.png" % tag), res=(1280, 400),
               samples=48)


def check_tour():
    """Frames of the aerial tour phase 3 will fly: the maintenance corner
    high, the terminal crescent, the whole field from the south with the
    Cantareira behind, and the city ring that must NOT be empty."""
    link_terrain()
    # aim points, not hand-set eulers: the first pass typed a yaw sign wrong
    # and the south frame rendered 180 deg away from the airport
    for (tag, eye, aim, lens) in (
            ("tour_ne_corner", (2700.0, 700.0, 380.0),
             (2200.0, 1330.0, -8.0), 40.0),
            ("tour_terminals", (900.0, -200.0, 420.0),
             (100.0, 750.0, -9.0), 40.0),
            ("tour_field_south", (1200.0, -2200.0, 750.0),
             (1400.0, 600.0, -5.0), 30.0),
            ("tour_city_east", (3600.0, 900.0, 300.0),
             (2600.0, 1250.0, -8.0), 35.0)):
        _look_at(tag, eye, aim, lens)
        render(os.path.join(OUT, "%s.png" % tag), res=(1280, 720))


def check_fleet():
    """The populated ramp, close enough to argue about."""
    link_terrain()
    for (tag, eye, aim, lens) in (
            ("fleet_901row", (2100.0, 900.0, 60.0),
             (2330.0, 1140.0, -2.0), 50.0),
            ("fleet_hangar_777", (2150.0, 1120.0, 30.0),
             (2270.0, 1330.0, 12.0), 60.0),
            ("fleet_t3_frontage", (450.0, 350.0, 70.0),
             (300.0, 640.0, -4.0), 55.0),
            ("fleet_cargo", (-500.0, 350.0, 55.0),
             (-620.0, 600.0, -4.0), 55.0)):
        _look_at(tag, eye, aim, lens)
        render(os.path.join(OUT, "%s.png" % tag), res=(1280, 720))


def populate_fleet():
    """Every check sees what the clips will see: the ramp populated by
    fleet_placement (linked masters, instanced), exactly as the clip files
    will populate it."""
    sys.path.insert(0, HERE)
    import fleet_placement as F
    if bpy.data.collections.get("SBGR_Fleet") is None:
        F.populate(bpy.context.scene)


def main():
    os.makedirs(OUT, exist_ok=True)
    todo = args() or ["plan"]
    table = {"plan": check_plan, "latam": check_latam, "ground": check_ground,
             "horizon": check_horizon, "tour": check_tour,
             "fleet": check_fleet}
    populate_fleet()
    for t in todo:
        table[t]()


if __name__ == "__main__":
    main()
