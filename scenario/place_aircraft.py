#!/usr/bin/env python3
"""Put an aircraft take-off rig onto RWY 17R at SCL and link the scenery.

    blender -b "airbus A320neo/A320neo_decolagem.blend" \\
        -P scenario/place_aircraft.py -- --out "airbus A320neo/A320neo_scl.blend"

What it does, and what it deliberately does not do
--------------------------------------------------
* LINKS ``scenario/scl_field.blend`` and ``scenario/scl_terrain.blend``. Nothing
  is appended, so a later fix to the airport fixes every aircraft at once.
* Creates ``SCL_Placement``, an Empty on the RWY 17R centreline carrying the
  177.424 deg true track, and parents the aircraft pivot and the take-off camera
  to it. The animation curves of the aircraft are NOT touched: the placement is
  entirely in the parent transform.
* Reframes the camera by sliding it OUTWARD ALONG ITS OWN SIGHT LINE. For each
  frame the aim point Q is recovered as the point on the camera ray closest to
  the aircraft pivot, and the camera is moved to Q + k*(C - Q) horizontally,
  keeping its height. Because Q stays on the ray, the azimuth curve
  (rotation_euler[2]) is left EXACTLY as it was - same sweep, same 2:1 pan-rate
  ratio, still no 360 deg wrap, which is what caused the motion-blur ghosting
  the first time round. Only the elevation curve is re-derived, as a monotonic
  remap atan(tan(phi)/k) of the old one, so it stays as smooth as it was.
  The lens is multiplied by the same k, so the aircraft keeps its size in frame
  while the LATAM base and the cordillera behind it grow by ~3.5x.
"""
import bpy
import math
import os
import sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIELD = os.path.join(HERE, "scl_field.blend")
TERRAIN = os.path.join(HERE, "scl_terrain.blend")

# --- survey (scl_aip_corrections.json) ---------------------------------------
THR_17R = (-1582.57, 459.21)
TRACK_DEG = 177.424
Z_RUNWAY = 0.09              # top of the runway pavement in the scenery

# --- shot design -------------------------------------------------------------
# Roll distance of the aircraft at frame 1. Chosen so that the frame at which
# the camera points due east (frame 57.2, from the untouched azimuth curve) is
# the moment the LATAM base is abeam - it sits 1776-1791 m down the 17R roll -
# and so rotation, at frame ~70, happens at 1816 m, which is where
# RECOGNITION.md puts it.
ROLL_AT_FRAME_1 = 1670.3
CAM_PULLBACK = 4.0           # k: horizontal standoff and focal length multiplier
BASE_LENS_MM = 35.0

DROP = ("Pista", "PistaMarcas", "Grama", "Sol", "CloudCard",
        "CamHero", "CamPerfil", "CamCauda", "CamBarriga", "CamNariz",
        "CamFrontal", "CamOrtoFrente", "CamAlvo", "CamAlvoCauda",
        "CamAlvoBarriga", "CamAlvoNariz", "CamAlvoFrontal")


def args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def fcurves(action):
    if len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    out = []
    for lay in action.layers:
        for st in lay.strips:
            for cb in st.channelbags:
                out.extend(cb.fcurves)
    return out


def fc(action, path, index):
    for c in fcurves(action):
        if c.data_path == path and c.array_index == index:
            return c
    raise KeyError((path, index))


def link_collection(path, name, instance=True):
    with bpy.data.libraries.load(path, link=True) as (src, dst):
        if name not in src.collections:
            raise RuntimeError("%s has no collection %s" % (path, name))
        dst.collections = [name]
    c = dst.collections[0]
    if instance:
        ob = bpy.data.objects.new(name + "_Link", None)
        ob.instance_type = "COLLECTION"
        ob.instance_collection = c
        bpy.context.scene.collection.objects.link(ob)
    return c


def main():
    a = args()
    out = a[a.index("--out") + 1] if "--out" in a else \
        os.path.join(ROOT, "airbus A320neo", "A320neo_scl.blend")
    scn = bpy.context.scene

    # ---- 1. strip the placeholder scenery ----------------------------------
    for nm in DROP:
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)

    # ---- 2. link the shared scenery ----------------------------------------
    link_collection(FIELD, "SCL_Field")
    link_collection(FIELD, "SCL_Light")
    link_collection(FIELD, "SCL_Anchors")
    if os.path.exists(TERRAIN):
        link_collection(TERRAIN, "SCL_Terrain")
    else:
        print("!! scl_terrain.blend missing - rebuild it with "
              "build_scenery.py -- --terrain")
    with bpy.data.libraries.load(FIELD, link=True) as (src, dst):
        dst.worlds = ["SCL_World"]
    scn.world = dst.worlds[0]

    # ---- 3. the placement Empty --------------------------------------------
    psi = math.atan2(math.cos(math.radians(TRACK_DEG)) * -1.0,
                     math.sin(math.radians(TRACK_DEG)) * -1.0)
    # local -X must land on the runway track; the line above solves
    # (-cos psi, -sin psi) = (sin track, cos track)
    ux = math.sin(math.radians(TRACK_DEG))
    uy = math.cos(math.radians(TRACK_DEG))
    piv = bpy.data.objects["AviaoPivo"]
    scn.frame_set(1)
    lx, ly, lz = piv.location            # local pose at frame 1
    tx = THR_17R[0] + ux * ROLL_AT_FRAME_1
    ty = THR_17R[1] + uy * ROLL_AT_FRAME_1
    ox = tx - (lx * math.cos(psi) - ly * math.sin(psi))
    oy = ty - (lx * math.sin(psi) + ly * math.cos(psi))
    oz = Z_RUNWAY - lz

    rig = bpy.data.objects.new("SCL_Placement", None)
    rig.empty_display_type = "ARROWS"
    rig.empty_display_size = 30.0
    rig.location = (ox, oy, oz)
    rig.rotation_euler = (0.0, 0.0, psi)
    scn.collection.objects.link(rig)

    cam = bpy.data.objects["CamDecolagem"]

    # ---- 4. reframe the camera BEFORE parenting (all maths in rig-local) ----
    reframe(scn, piv, cam, CAM_PULLBACK)
    cam.data.lens = BASE_LENS_MM * CAM_PULLBACK
    cam.data.clip_start = 1.0
    cam.data.clip_end = 300000.0

    for ob in (piv, cam):
        ob.parent = rig
        ob.matrix_parent_inverse.identity()

    # ---- 5. render settings -------------------------------------------------
    scn.render.fps = 25                  # 25 fps gives the GIF exact 40 ms delays
    scn.render.fps_base = 1.0
    scn.frame_start, scn.frame_end = 1, 140
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 96
    scn.cycles.use_denoising = True
    scn.cycles.max_bounces = 4
    scn.render.resolution_x, scn.render.resolution_y = 960, 540
    scn.render.use_motion_blur = True
    scn.render.motion_blur_shutter = 0.15
    # 0.15 at 25 fps is ~1/167 s. The original 0.4 (a 144 deg shutter) smeared
    # the panned background by ~33 px right at the moment the LATAM base is
    # abeam, which is the one frame that has to be readable.
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Base Contrast"
    scn.view_settings.exposure = 0.0
    scn.camera = cam

    report(scn, piv, cam, rig)
    # Library paths must end up relative (//../scenario/...) or the file only
    # opens on this machine. save_as_mainfile(relative_remap=True) only re-bases
    # paths that were ALREADY relative, so save once, convert, save again.
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    print("saved", out)


def reframe(scn, piv, cam, k):
    """Slide the camera out along its own sight line by k, horizontally."""
    act = cam.animation_data.action
    fx, fy, fz = (fc(act, "location", i) for i in range(3))
    rx = fc(act, "rotation_euler", 0)
    frames = sorted({round(kp.co[0]) for kp in fx.keyframe_points})
    newloc, newrx = {}, {}
    for f in frames:
        scn.frame_set(f)
        C = cam.matrix_world.translation.copy()
        v = (cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
        A = piv.matrix_world.translation.copy()
        t = (A - C).dot(v)
        Q = C + v * t                      # aim point: on the ray, nearest the pivot
        dx, dy = C.x - Q.x, C.y - Q.y
        nx, ny = Q.x + dx * k, Q.y + dy * k
        dh = math.hypot(nx - Q.x, ny - Q.y)
        dz = Q.z - C.z
        phi = math.atan2(dz, dh)           # new elevation to the same aim point
        newloc[f] = (nx, ny, C.z)
        newrx[f] = math.pi / 2.0 + phi
    for f in frames:
        for curve, val in ((fx, newloc[f][0]), (fy, newloc[f][1]),
                           (fz, newloc[f][2]), (rx, newrx[f])):
            for kp in curve.keyframe_points:
                if round(kp.co[0]) == f:
                    kp.co[1] = val
                    kp.handle_left[1] = val
                    kp.handle_right[1] = val
    for curve in (fx, fy, fz, rx):
        curve.update()


def report(scn, piv, cam, rig):
    ux = math.sin(math.radians(TRACK_DEG))
    uy = math.cos(math.radians(TRACK_DEG))
    nx, ny = -uy, ux                       # left of the roll = east
    print("\n%-6s %-28s %-26s %8s %8s %8s %8s"
          % ("frame", "aircraft world", "camera world",
             "roll_m", "lat_m", "cam_lat", "az_deg"))
    for f in (1, 20, 40, 57, 70, 90, 110, 140):
        scn.frame_set(f)
        A = piv.matrix_world.translation
        C = cam.matrix_world.translation
        dax, day = A.x - THR_17R[0], A.y - THR_17R[1]
        roll = dax * ux + day * uy
        lat = dax * nx + day * ny
        dcx, dcy = C.x - THR_17R[0], C.y - THR_17R[1]
        clat = dcx * nx + dcy * ny
        vd = (cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
        az = (math.degrees(math.atan2(vd.x, vd.y))) % 360.0
        print("%-6d (%8.1f,%8.1f,%6.2f) (%8.1f,%8.1f,%6.2f) %8.1f %8.1f %8.1f %8.1f"
              % (f, A.x, A.y, A.z, C.x, C.y, C.z, roll, lat, clat, az))
    # pan-rate sanity, the thing that broke last time
    act = cam.animation_data.action
    rz = fc(act, "rotation_euler", 2)
    vals = [rz.evaluate(f) for f in range(1, 141)]
    d = [abs(vals[i + 1] - vals[i]) for i in range(len(vals) - 1)]
    d = [x for x in d if x > 1e-6]
    print("\nazimuth sweep %.1f deg, pan rate min %.4f max %.4f ratio %.2f, "
          "monotonic=%s, wrap=%s"
          % (math.degrees(vals[-1] - vals[0]), min(d), max(d), max(d) / min(d),
             all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)),
             any(abs(vals[i + 1] - vals[i]) > 1.0 for i in range(len(vals) - 1))))


if __name__ == "__main__":
    main()
