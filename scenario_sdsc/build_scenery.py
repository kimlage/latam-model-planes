#!/usr/bin/env python3
"""Build the SDSC / Sao Carlos scenery in Blender from the surveyed data here.

The scenery is a SHARED ASSET: it is built into its own .blend files under
``scenario_sdsc/`` and LINKED into each aircraft file, exactly the way
``../scenario/`` works for Santiago, so fixing the aerodrome fixes it for every
aircraft at once.

    blender -b --factory-startup -P scenario_sdsc/build_scenery.py -- --field
    blender -b --factory-startup -P scenario_sdsc/build_scenery.py -- --terrain

Outputs
    scenario_sdsc/sdsc_field.blend    the aerodrome: runway + ICAO markings,
                                      taxiways, aprons, the LATAM MRO, hangar 9,
                                      the mid-field cluster, the Aeroclube, the
                                      tree line, parked aircraft, sun + sky
    scenario_sdsc/sdsc_terrain.blend  the plateau heightfield (git-ignored)

Reference frame (identical in both files, and in ../scenario_sdsc/README.md)
    local ENU tangent plane, WGS84 - lib/frame.py is the single source of truth
    origin  = published RWY 02 threshold, lat -21.8818417  lon -47.9039639
    x = East, y = North, z = Up, metres
    z = 0 at 807.0 m AMSL (published SDSC aerodrome elevation, 2648 ft)

FOUR THINGS ABOUT THIS FIELD THAT ARE NOT TRUE AT SANTIAGO
    1. The runway is designated 02/20 but its TRUE track is 001.026 deg.
       Magnetic variation here is 22 W. Everything below is built on the true
       track; building on the designator rotates the whole field 19 deg against
       the terrain, the footprints and the sun.
    2. The runway is NOT LEVEL. It falls 10.06 m over the 1 620 m between the
       published thresholds - 0.62%, downhill toward 20. Every pavement, marking
       and light below takes its z from rwy_z(along), never from a constant.
    3. The MRO platform is ~35 m BELOW the runway. Confirmed here against the
       Copernicus grid: 769.9 m median over 348 samples inside the apron polygon
       against a published 804.67 m at THR 02. It is not a DEM artefact.
    4. There is no skyline (TERRAIN.md section 3: the whole 360 deg horizon band
       spans -0.32 to +1.30 deg). A terrain mesh alone renders a horizon that is
       too low and too clean, so the tree line here is scenery, not detail.

Data sources
    sdsc_osm.json          (c) OpenStreetMap contributors, ODbL 1.0
    sdsc_aip_survey.json   AISWEB/ROTAER + the two SDSC IAC charts
    sdsc_operations_sun.json  solar geometry, computed in this repository
    terrain/*.npy          Copernicus DEM GLO-30 (+ SRTM control)
    refs/*.jpg             Wikimedia Commons, cited in sdsc_references.md,
                           never committed - the appearance comes from these
"""

import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------------------
# Survey constants. Everything on this page comes from sdsc_aip_survey.json or
# sdsc_operations_sun.json. Nothing here is estimated.
# ---------------------------------------------------------------------------
TRACK_02_DEG = 1.026            # TRUE. The designator says 02; VAR is 22 W.
UX = math.sin(math.radians(TRACK_02_DEG))
UY = math.cos(math.radians(TRACK_02_DEG))
NX, NY = -UY, UX                # left of a RWY 02 roll = WEST

RWY_WIDTH = 45.0                # ROTAER
THR02_A = 0.0                   # scene origin
THR20_A = 1619.98               # measured in this frame; published 1620
PAVE_S_A = -51.99               # THR 02 walked back by the published 52 m
PAVE_N_A = 1667.71              # THR 20 walked on by the published 48 m
Z_THR02 = 804.67 - 807.0        # -2.33   (IAC RNP Z RWY 02, THR ELEV 2640 ft)
Z_THR20 = 794.61 - 807.0        # -12.39  (IAC RNP Y RWY 20, THR ELEV 2607 ft)
RWY_SLOPE = (Z_THR20 - Z_THR02) / THR20_A          # -0.006210 (0.62% down to 20)
DISP_02, DISP_20 = 52.0, 48.0   # ROTAER displaced thresholds
LDA_02 = 1668.0                 # ROTAER declared distances; TORA 02 is 1672
ARP_XY = (65.20, 603.77)

# Platform levels, medians of the Copernicus 30 m grid inside each polygon.
# These are measurements, printed again by verify_levels() at build time.
Z_MRO_PLATFORM = 769.9 - 807.0        # -37.1   348 samples, p10..p90 769.3..771.3
Z_MIDFIELD_APRON = 795.9 - 807.0      # -11.1   121 samples
Z_AEROCLUBE_APRON = 804.9 - 807.0     # -2.1     25 samples

# Sun: 26 September, 17:00 local (UTC-3, Brazil has had no DST since 2019).
# sdsc_operations_sun.json, sample "hangar 9 inauguration": 15.14 deg / 274.46.
# Why that instant: RECOGNITION.md section 4 asks for the sun in the WEST so a
# northbound RWY 02 departure is lit on its starboard side and a camera west of
# the runway looking east at the MRO has the sun behind it. 15 deg is also the
# elevation Santiago had to be argued up to - below ~10 deg the whole field
# renders as silhouette - and this field's own equinox 17:00 lands on it.
SUN_ELEV_DEG = 15.14
SUN_AZIM_DEG = 274.46

# Haze. Koschmieder with an exponential aerosol layer; same node group as SCL.
# 26 September is the end of the dry season in the cane belt, when the plateau
# air is milky with smoke and dust; the photographs (all dry or wet season, all
# hazy at 1 km) support a soft, not a crystalline, air. V is INFERRED.
HAZE_VIS_KM = 18.0
HAZE_SCALE_H = 1100.0

# ---------------------------------------------------------------------------
# APPEARANCE: the single biggest unconfirmed thing in this build.
#
# Every free-licence photograph of this base is 2006-2014, i.e. TAM: light-grey
# ribbed cladding under a broad DARK RED-MAROON fascia band carrying the TAM
# wordmark. The base has been LATAM since 2016, hangar 9 opened under LATAM in
# September 2025, and NO free-licence photograph of the base in LATAM colours
# was found (sdsc_references.md section 3).
#
# The build paints the ARCHITECTURE from the photographs - vault, shallow gable,
# ribbed cladding, the fascia band and its proportions, the nose-in line, the
# white wall + black mesh perimeter, the red space frame - because those are
# photographed, and repaints only the BAND COLOUR and the MARK, because the date
# says so. Flip this one constant to rebuild the base as it is photographed.
# ---------------------------------------------------------------------------
LIVERY = os.environ.get("SDSC_LIVERY", "latam")    # "latam" | "tam"

# ---------------------------------------------------------------------------
# Building heights.
#
# ZERO of the 95 OSM footprints carries a height tag and none carries
# building:levels. Santiago had 4 heights and 42 level counts out of 748; here
# there is nothing. ONE height is measured - see MEASURED_HEIGHT below - and
# everything else on this page is an ESTIMATE BY ME. Do not quote it as data.
# The reasoning for each is in README.md section 3.
# ---------------------------------------------------------------------------
HEIGHT_BY_TYPE = {
    "hangar": 12.0,      # GA hangar: the Aeroclube's are single-bay light-aircraft sheds
    "yes": 5.0,          # 89 of 95 footprints; village houses and field sheds
    "house": 4.0,
    "church": 7.0,       # nave + a small bell gable
    "roof": 4.0,         # canopies
    "storage_tank": 8.0,
    "industrial": 9.0,
    "warehouse": 9.0,
    "service": 4.0,
}

# Measured, not estimated. The Copernicus DSM reads the roof of relation/7422966
# at 784.8 m against a 770.8 m platform around it: +14.0 m. Phase 1 measured
# relation/7422965 at +12.9 m over 54 grid cells and called it a FLOOR, because a
# 30 m DSM smears roof edges inward. Photogrammetry on the 2013 photograph gives
# 12.7 m for the mid-field hangar by the horizon-ratio method (README section 3).
# Three methods, three buildings, 12.7-14.0 m: the hangars on this field are LOW.
MEASURED_HEIGHT = {
    "relation/7422966": 14.0,      # DSM, 784.8 - 770.8
    "relation/7422965": 12.9,      # DSM, phase 1, a floor not a ridge
}

# Named / id overrides. Every one carries its justification in README.md.
HEIGHT_BY_ID = {
    # --- LATAM MRO ---------------------------------------------------------
    "relation/7422965": 13.0,   # 471 x 137 m hangar line + workshop spine, eave
    "relation/7422966": 17.5,   # the widebody bay - see build_mro_frontage
    "relation/7422968": 12.0,   # 50 x 46 m hangar
    "way/708700156":    12.0,   # 44 x 42 m hangar (2019 in OSM)
    "way/510750642":     8.0,   # 50 x 38 m workshop
    "way/510750671":    11.0,   # 80 x 76 m - the museum hall (silver space frame)
    "way/510750697":    11.0,   # 80 x 90 m - the museum hall / entrance block
    "way/510750672":     8.0,
    "way/510750674":     7.0,   # 105 x 25 m workshop strip
    "way/510750687":     7.0,   # 105 x 26 m workshop strip
    "relation/7422964":  6.0,   # 57 x 9 m canopy strip
    "way/510750464":     5.0,
    "way/510750463":     5.0,
    # --- mid-field cluster (see build_midfield) ----------------------------
    "relation/7422970": 12.7,   # the barrel-vault hangar in the 2013 photograph
}
LEVEL_HEIGHT = 3.2

# Hangar 9 - DECLARED INFERENCE, not data. Inaugurated 2025-09-26, R$40 M, ten
# months, for 787 heavy maintenance, painting of large aircraft, and three A320s
# at once. It has NO published dimension, NO published position, and it is not in
# OpenStreetMap (every MRO footprint there is version 1 from 2017-07-27).
#
# Size, from what it has to hold, not from a source:
#   787-9   62.8 m long, 60.1 m span, 17.0 m tail  -> door >= 68 m, clear >= 20 m
#   3 x A320 nose-in, 35.8 m span each             -> >= 115 m of usable width
#   a paint bay must enclose the whole aeroplane   -> >= 70 m deep
# Position, from the apron geometry: the ONLY clear, level, platform-height,
# taxiway-served ground on the MRO site big enough for it - a search over the
# site polygon for a free 140 x 105 m rectangle clear of every mapped footprint,
# the apron and the taxiway returns this block as the one nearest the apron
# (56 m). It is not from imagery. If a 2025 image later puts it elsewhere, move
# it: nothing else in the build depends on its position.
HANGAR9 = dict(
    x0=685.0, x1=815.0, y0=1590.0, y1=1685.0,     # 130 x 95 m, door face north
    eave=22.0, ridge=26.0, door_w=78.0, door_h=20.5,
)

# Apron floodlight masts. The 2013 photograph puts their lamp clusters within
# ~1 m of the 12.7 m hangar apex beside them, so these are NOT Santiago's 30 m
# high-masts - they are short. 16 m is that reading plus a margin. ESTIMATE.
MAST_H = 16.0

# The chequerboard tower. Unidentified (sdsc_references.md section 6.8): it has
# the Brazilian obstruction chequer, a glazed cab with a railed gallery and whip
# antennas, and it is at neither OSM node phase 1 offered. Height by the
# horizon-ratio method on the 2013 photograph: ~22 m to the cab roof, ~30 m to
# the antenna tip. Position triangulated against the mid-field apron in the same
# photograph, +-80 m. ESTIMATE, both.
CHEQUER = dict(x=300.0, y=1255.0, cab=21.0, tip=29.0, w=6.0)

Z_GROUND = 0.00        # aerodrome ground, RELATIVE to the graded surface
Z_APRON = 0.05
Z_TAXI = 0.06
Z_SHOULDER = 0.07
Z_RUNWAY = 0.09
Z_MARK = 0.12


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def argv_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


_DATA = None


def data():
    global _DATA
    if _DATA is None:
        with open(os.path.join(HERE, "sdsc_osm.json")) as fh:
            _DATA = json.load(fh)
    return _DATA


def survey():
    with open(os.path.join(HERE, "sdsc_aip_survey.json")) as fh:
        return json.load(fh)


def wipe():
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.curves,
                bpy.data.lights, bpy.data.cameras, bpy.data.node_groups):
        for it in list(blk):
            blk.remove(it)


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def unit(ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    return dx / n, dy / n, n


def dedupe_ring(poly):
    """OSM rings repeat the first node last; drop it and any coincident pair."""
    ring = [tuple(p[:2]) for p in poly]
    if len(ring) > 1 and math.dist(ring[0], ring[-1]) < 1e-6:
        ring = ring[:-1]
    out = []
    for p in ring:
        if not out or math.dist(out[-1], p) > 1e-6:
            out.append(p)
    return out


def bm_to_object(bm, name, mat, collection, smooth=False, roof_mat=None):
    """roof_mat: optional slot-1 material on up-facing polygons (normal.z > 0.55
    - flat caps and shallow roof planes, never walls). Same split Santiago uses."""
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if mat:
        me.materials.append(mat)
    if roof_mat is not None:
        me.materials.append(roof_mat)
        for p in me.polygons:
            if p.normal.z > 0.55:
                p.material_index = 1
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------
# THE GROUND SURFACE. This is the piece that has no analogue at Santiago.
#
# Santiago grades the whole aerodrome to one z and drops a flat pad on it. Here
# the runway falls 10 m end to end, the MRO platform is 35 m lower again, and
# the land falls ~40 m/km eastward into the corrego. So every built surface
# takes its height from graded(x, y), and the terrain mesh is pushed down to the
# SAME function before it is blended back to the raw DEM.
# ---------------------------------------------------------------------------
def rwy_z(a):
    """Runway surface z at `a` metres along the track from THR 02.

    Linear between the two PUBLISHED threshold elevations, extrapolated to the
    pavement ends. Copernicus independently reads a 12.0 m fall against this
    10.06 m; the published pair is primary."""
    return Z_THR02 + RWY_SLOPE * a


def rwy_pt(a, l, dz=0.0):
    """(along, lateral, height above the runway surface) -> scene xyz.
    l > 0 is LEFT of a RWY 02 roll, i.e. west."""
    return (UX * a + NX * l, UY * a + NY * l, rwy_z(a) + dz)


def to_al(x, y):
    return x * UX + y * UY, x * NX + y * NY


def _smoothstep(t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


class Ground:
    """The graded aerodrome surface, and the raw DEM under everything else."""

    def __init__(self):
        import numpy as np
        meta = json.load(open(os.path.join(HERE, "terrain",
                                           "terrain_meta.json")))
        self.m = meta["grids"]["terrain_sdsc_near_30m"]
        self.Z = np.load(os.path.join(HERE, "terrain", self.m["file"]))
        self.ny, self.nx = self.Z.shape

    def dem(self, x, y):
        """Bilinear sample of the 30 m Copernicus grid, in scene z."""
        fi = (x - self.m["x_min_m"]) / self.m["step_m"]
        fj = (y - self.m["y_min_m"]) / self.m["step_m"]
        i = min(max(int(fi), 0), self.nx - 2)
        j = min(max(int(fj), 0), self.ny - 2)
        a, b = fi - i, fj - j
        a = 0.0 if a < 0 else (1.0 if a > 1 else a)
        b = 0.0 if b < 0 else (1.0 if b > 1 else b)
        Z = self.Z
        return float(Z[j, i] * (1 - a) * (1 - b) + Z[j, i + 1] * a * (1 - b) +
                     Z[j + 1, i] * (1 - a) * b + Z[j + 1, i + 1] * a * b)

    def graded(self, x, y):
        """Aerodrome ground level: the DEM, forced to the published runway
        surface over the strip and to the measured platform levels over the
        three aprons, with smooth blends between."""
        z = self.dem(x, y)
        a, l = to_al(x, y)

        # runway strip: full weight to 90 m either side, gone by 260 m, and
        # tapering off the ends over 200 m beyond the pavement.
        w = 1.0 - _smoothstep((abs(l) - 90.0) / 170.0)
        if a < PAVE_S_A:
            w *= 1.0 - _smoothstep((PAVE_S_A - a) / 200.0)
        elif a > PAVE_N_A:
            w *= 1.0 - _smoothstep((a - PAVE_N_A) / 200.0)
        if w > 0.0:
            z = z * (1.0 - w) + rwy_z(a) * w

        # MRO platform: flat, 35 m below THR 02, over the apron + hangar line
        # + hangar 9. Measured, and NOT flattened to runway level.
        w = self._box(x, y, 620.0, 1100.0, 1530.0, 2060.0, 160.0)
        if w > 0.0:
            z = z * (1.0 - w) + Z_MRO_PLATFORM * w

        # mid-field apron (the cluster in the 2013 photograph)
        w = self._box(x, y, 225.0, 400.0, 1040.0, 1240.0, 70.0)
        if w > 0.0:
            z = z * (1.0 - w) + Z_MIDFIELD_APRON * w

        # Aeroclube
        w = self._box(x, y, -300.0, -150.0, 190.0, 520.0, 60.0)
        if w > 0.0:
            z = z * (1.0 - w) + Z_AEROCLUBE_APRON * w
        return z

    @staticmethod
    def _box(x, y, x0, x1, y0, y1, fade):
        dx = max(x0 - x, 0.0, x - x1)
        dy = max(y0 - y, 0.0, y - y1)
        d = math.hypot(dx, dy)
        return 1.0 - _smoothstep(d / fade)


G = None          # the single Ground instance, made in build_field/build_terrain


def gz(x, y, dz=0.0):
    return G.graded(x, y) + dz


# --- mesh primitives, all of them ground-following ------------------------
def prism(bm, ring, z0_rel, z1_rel, base=None):
    """Extruded footprint. Heights are RELATIVE to the ground under the ring's
    centroid, so a building on the MRO platform sits on the platform."""
    ring = dedupe_ring(ring)
    if len(ring) < 3:
        return
    if base is None:
        base = gz(sum(p[0] for p in ring) / len(ring),
                  sum(p[1] for p in ring) / len(ring))
    top = [bm.verts.new((x, y, base + z1_rel)) for x, y in ring]
    bot = [bm.verts.new((x, y, base + z0_rel - 1.5)) for x, y in ring]
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        try:
            bm.faces.new((bot[i], bot[j], top[j], top[i]))
        except ValueError:
            pass
    try:
        f = bm.faces.new(top)
        bmesh.ops.triangulate(bm, faces=[f])
    except ValueError:
        pass


def flat_poly(bm, ring, dz, flat_z=None):
    """Fill a ring. flat_z forces one level (aprons are graded planes); else the
    polygon is draped on the graded ground."""
    ring = dedupe_ring(ring)
    if len(ring) < 3:
        return
    vs = [bm.verts.new((x, y, (flat_z + dz) if flat_z is not None
                        else gz(x, y, dz))) for x, y in ring]
    try:
        f = bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=[f])
    except ValueError:
        pass


def ribbon(bm, pts, width, dz, flat_z=None):
    """A polyline as a flat strip, draped on the graded ground."""
    pts = dedupe_ring(pts)
    if len(pts) < 2:
        return
    h = width * 0.5
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        if i == 0:
            dx, dy, _ = unit(x, y, *pts[1])
        elif i == len(pts) - 1:
            dx, dy, _ = unit(*pts[i - 1], x, y)
        else:
            ax, ay, _ = unit(*pts[i - 1], x, y)
            bx, by, _ = unit(x, y, *pts[i + 1])
            dx, dy = ax + bx, ay + by
            m = math.hypot(dx, dy)
            dx, dy = (ax, ay) if m < 1e-9 else (dx / m, dy / m)
        nx, ny = -dy, dx
        for side, store in ((1, left), (-1, right)):
            px, py = x + side * nx * h, y + side * ny * h
            store.append(bm.verts.new(
                (px, py, (flat_z + dz) if flat_z is not None else gz(px, py, dz))))
    for i in range(len(pts) - 1):
        try:
            bm.faces.new((right[i], right[i + 1], left[i + 1], left[i]))
        except ValueError:
            pass


def box(bm, x0, x1, y0, y1, z0, z1):
    v = [bm.verts.new(p) for p in
         ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
          (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
              (4, 5, 6, 7)):
        try:
            bm.faces.new([v[i] for i in f])
        except ValueError:
            pass


def post(bm, x, y, r, z0, z1):
    box(bm, x - r, x + r, y - r, y + r, z0, z1)


# ---------------------------------------------------------------------------
# materials, with the atmospheric-haze term baked in
# ---------------------------------------------------------------------------
def haze_group():
    """Node group: mixes any shader toward airlight as a function of distance.

        tau(d, z) = beta0 * d * (H/z) * (1 - exp(-z/H))

    the exact integral of an exp(-z/H) aerosol layer along a straight ray from
    the ground to a point at height z, distance d away; beta0 = 3.912 / V
    (Koschmieder). Identical maths to ../scenario/build_scenery.py, re-tuned:
    V = 18 km here against Santiago's 14, because the plateau air is thinner
    than the Santiago basin's, and the airlight ramp is warmer because a
    dry-season Brazilian afternoon is smoky rather than blue.
    """
    g = bpy.data.node_groups.get("SDSC_Haze")
    if g:
        return g
    g = bpy.data.node_groups.new("SDSC_Haze", "ShaderNodeTree")
    g.interface.new_socket("Shader", in_out="INPUT", socket_type="NodeSocketShader")
    g.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
    nin = g.nodes.new("NodeGroupInput"); nin.location = (-1400, 200)
    nout = g.nodes.new("NodeGroupOutput"); nout.location = (600, 0)

    geo = g.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1400, -200)
    sep = g.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-1200, -260)
    g.links.new(geo.outputs["Position"], sep.inputs[0])
    cam0 = g.nodes.new("ShaderNodeCameraData"); cam0.location = (-1400, -700)
    inc = g.nodes.new("ShaderNodeSeparateXYZ"); inc.location = (-1200, -700)
    g.links.new(geo.outputs["Incoming"], inc.inputs[0])

    # tau's shape term is the integral of exp(-z/H) along a ray between the
    # ground and height z. The height that belongs in it is the HIGHER end of
    # the ray, not the shaded point: with the camera at 700 m on the aerial tour
    # the ray spends most of its length in thin air, and using the ground point
    # over-hazes an aerial by about a third. Incoming points from the surface
    # toward the camera, so z_cam = z + Incoming.z * View Distance.
    zc = g.nodes.new("ShaderNodeMath"); zc.operation = "MULTIPLY_ADD"
    zc.location = (-1100, -700)
    g.links.new(inc.outputs["Z"], zc.inputs[0])
    g.links.new(cam0.outputs["View Distance"], zc.inputs[1])
    g.links.new(sep.outputs["Z"], zc.inputs[2])
    zhi = g.nodes.new("ShaderNodeMath"); zhi.operation = "MAXIMUM"
    zhi.location = (-1180, -400)
    g.links.new(sep.outputs["Z"], zhi.inputs[0])
    g.links.new(zc.outputs[0], zhi.inputs[1])

    # z is measured from the aerodrome datum, and much of this field sits BELOW
    # it (the MRO platform is at z = -37). Shift into "height above the lowest
    # scenery" before the exponential, or the layer integral goes negative.
    lift = g.nodes.new("ShaderNodeMath"); lift.operation = "ADD"
    lift.inputs[1].default_value = 60.0; lift.location = (-1100, -260)
    g.links.new(zhi.outputs[0], lift.inputs[0])
    zmax = g.nodes.new("ShaderNodeMath"); zmax.operation = "MAXIMUM"
    zmax.inputs[1].default_value = 1.0; zmax.location = (-1020, -260)
    g.links.new(lift.outputs[0], zmax.inputs[0])

    a = g.nodes.new("ShaderNodeMath"); a.operation = "DIVIDE"
    a.inputs[1].default_value = HAZE_SCALE_H; a.location = (-860, -260)
    g.links.new(zmax.outputs[0], a.inputs[0])

    neg = g.nodes.new("ShaderNodeMath"); neg.operation = "MULTIPLY"
    neg.inputs[1].default_value = -1.0; neg.location = (-700, -340)
    g.links.new(a.outputs[0], neg.inputs[0])
    ex = g.nodes.new("ShaderNodeMath"); ex.operation = "EXPONENT"
    ex.location = (-540, -340)
    g.links.new(neg.outputs[0], ex.inputs[0])
    one = g.nodes.new("ShaderNodeMath"); one.operation = "SUBTRACT"
    one.inputs[0].default_value = 1.0; one.location = (-380, -340)
    g.links.new(ex.outputs[0], one.inputs[1])
    shape = g.nodes.new("ShaderNodeMath"); shape.operation = "DIVIDE"
    shape.location = (-220, -300)
    g.links.new(one.outputs[0], shape.inputs[0])
    g.links.new(a.outputs[0], shape.inputs[1])

    cam = g.nodes.new("ShaderNodeCameraData"); cam.location = (-1400, -520)
    beta = g.nodes.new("ShaderNodeMath"); beta.operation = "MULTIPLY"
    beta.inputs[1].default_value = 3.912 / (HAZE_VIS_KM * 1000.0)
    beta.location = (-1000, -520)
    g.links.new(cam.outputs["View Distance"], beta.inputs[0])

    tau = g.nodes.new("ShaderNodeMath"); tau.operation = "MULTIPLY"
    tau.location = (-60, -420)
    g.links.new(beta.outputs[0], tau.inputs[0])
    g.links.new(shape.outputs[0], tau.inputs[1])

    ntau = g.nodes.new("ShaderNodeMath"); ntau.operation = "MULTIPLY"
    ntau.inputs[1].default_value = -1.0; ntau.location = (100, -420)
    g.links.new(tau.outputs[0], ntau.inputs[0])
    et = g.nodes.new("ShaderNodeMath"); et.operation = "EXPONENT"
    et.location = (240, -420)
    g.links.new(ntau.outputs[0], et.inputs[0])
    fac = g.nodes.new("ShaderNodeMath"); fac.operation = "SUBTRACT"
    fac.inputs[0].default_value = 1.0; fac.location = (380, -420)
    g.links.new(et.outputs[0], fac.inputs[1])

    # Airlight colour: warm smoky gold looking west into the low sun, pale
    # grey-blue away from it. Read off refs/sdsc_field_from_sp318_2013.jpg and
    # refs/mro_airbus_esquadrilha_2010.jpg, qualitatively.
    inc = g.nodes.new("ShaderNodeNewGeometry"); inc.location = (-1400, 520)
    flat = g.nodes.new("ShaderNodeVectorMath"); flat.operation = "MULTIPLY"
    flat.inputs[1].default_value = (-1.0, -1.0, 0.0); flat.location = (-1180, 520)
    g.links.new(inc.outputs["Incoming"], flat.inputs[0])
    nrm = g.nodes.new("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"
    nrm.location = (-1000, 520)
    g.links.new(flat.outputs[0], nrm.inputs[0])
    dot = g.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = (math.sin(math.radians(SUN_AZIM_DEG)),
                                   math.cos(math.radians(SUN_AZIM_DEG)), 0.0)
    dot.location = (-820, 520)
    g.links.new(nrm.outputs[0], dot.inputs[0])
    rng = g.nodes.new("ShaderNodeMapRange"); rng.location = (-640, 520)
    rng.inputs[1].default_value = -1.0
    rng.inputs[2].default_value = 1.0
    g.links.new(dot.outputs["Value"], rng.inputs[0])
    ramp = g.nodes.new("ShaderNodeValToRGB"); ramp.location = (-460, 520)
    el = ramp.color_ramp.elements
    el[0].position = 0.0
    el[0].color = (0.330, 0.360, 0.430, 1.0)      # away from the sun
    el[1].position = 0.60
    el[1].color = (0.470, 0.450, 0.430, 1.0)
    e2 = ramp.color_ramp.elements.new(0.88)
    e2.color = (0.880, 0.680, 0.430, 1.0)
    e3 = ramp.color_ramp.elements.new(1.0)
    e3.color = (1.000, 0.780, 0.480, 1.0)         # into the low western sun
    g.links.new(rng.outputs["Result"], ramp.inputs["Fac"])
    em = g.nodes.new("ShaderNodeEmission"); em.location = (-260, 520)
    em.inputs["Strength"].default_value = 1.0
    g.links.new(ramp.outputs["Color"], em.inputs["Color"])

    mix = g.nodes.new("ShaderNodeMixShader"); mix.location = (420, 0)
    g.links.new(fac.outputs[0], mix.inputs["Fac"])
    g.links.new(nin.outputs[0], mix.inputs[1])
    g.links.new(em.outputs[0], mix.inputs[2])
    g.links.new(mix.outputs[0], nout.inputs[0])
    return g


def configure_sky(sky):
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(SUN_ELEV_DEG)
    sky.sun_rotation = math.radians(90.0 - SUN_AZIM_DEG)
    sky.sun_disc = False           # the explicit Sun lamp provides the disc
    sky.sun_intensity = 1.0
    sky.sun_size = math.radians(0.545)
    sky.altitude = 807
    # Rayleigh DOWN and Mie UP against Santiago, on purpose. A measured white
    # card under the first rig split the light 1.53:1 direct:diffuse with a sky
    # whose blue channel was 2.2x its red - and that blue diffuse is exactly
    # what turns red latosol grey-green. The end of the dry season in the cane
    # belt is smoky, not blue; more aerosol and less air gives a milky sky whose
    # bounce does not fight the ground colour.
    sky.air_density = 1.05
    sky.aerosol_density = 4.6
    sky.ozone_density = 1.0


_MATS = {}


def mat(name, color, rough=0.85, metal=0.0, hazy=True, emit=None):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.0
    if hazy:
        grp = nt.nodes.new("ShaderNodeGroup")
        grp.node_tree = haze_group(); grp.location = (320, 0)
        nt.links.new(bsdf.outputs[0], grp.inputs[0])
        nt.links.new(grp.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*color, 1.0)
    m.roughness = rough
    m.metallic = metal
    _MATS[name] = m
    return m


def _nm(nt, op, a=None, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _sm(nt, x, lo, hi, out_lo=0.0, out_hi=1.0):
    n = nt.nodes.new("ShaderNodeMapRange")
    n.interpolation_type = "SMOOTHERSTEP"
    n.inputs["From Min"].default_value = lo
    n.inputs["From Max"].default_value = hi
    n.inputs["To Min"].default_value = out_lo
    n.inputs["To Max"].default_value = out_hi
    nt.links.new(x, n.inputs["Value"])
    return n.outputs["Result"]


def _finish(nt, bsdf, out, x=640):
    grp = nt.nodes.new("ShaderNodeGroup"); grp.node_tree = haze_group()
    grp.location = (x, 0)
    nt.links.new(bsdf.outputs[0], grp.inputs[0])
    nt.links.new(grp.outputs[0], out.inputs["Surface"])


def _blank(name, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (800, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (480, 0)
    bsdf.inputs["Roughness"].default_value = rough
    return m, nt, out, bsdf


def aged_pavement_material(name, base, aged, stain, patch_scale, rough=0.86):
    """Weathered concrete / asphalt. refs/mro_airbus_esquadrilha_2010.jpg and
    refs/ga_cessna150_2007.jpg show the paved surfaces as patchworks of repair
    shades with darker stains on the used lanes, and - specific to this field -
    a fine RED dust film blown off the latosol beside them. Amplitudes read
    qualitatively; they are not measurements."""
    m, nt, out, bsdf = _blank(name, rough)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-900, 0)
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = patch_scale
    n1.inputs["Detail"].default_value = 3.0
    nt.links.new(geo.outputs["Position"], n1.inputs["Vector"])
    mix1 = nt.nodes.new("ShaderNodeMixRGB")
    mix1.inputs["Color1"].default_value = (*base, 1.0)
    mix1.inputs["Color2"].default_value = (*aged, 1.0)
    nt.links.new(_sm(nt, n1.outputs["Fac"], 0.34, 0.66), mix1.inputs["Fac"])
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 0.10
    n2.inputs["Detail"].default_value = 2.0
    nt.links.new(geo.outputs["Position"], n2.inputs["Vector"])
    mix2 = nt.nodes.new("ShaderNodeMixRGB")
    mix2.inputs["Color2"].default_value = (*stain, 1.0)
    nt.links.new(mix1.outputs[0], mix2.inputs["Color1"])
    nt.links.new(_sm(nt, n2.outputs["Fac"], 0.58, 0.80, 0.0, 0.45),
                 mix2.inputs["Fac"])
    # red dust film, ~25 m blotches, only ever adding warmth
    n3 = nt.nodes.new("ShaderNodeTexNoise")
    n3.inputs["Scale"].default_value = 0.04
    n3.inputs["Detail"].default_value = 2.0
    nt.links.new(geo.outputs["Position"], n3.inputs["Vector"])
    mix3 = nt.nodes.new("ShaderNodeMixRGB")
    mix3.inputs["Color2"].default_value = (base[0] * 1.30, base[1] * 0.92,
                                           base[2] * 0.78, 1.0)
    nt.links.new(mix2.outputs[0], mix3.inputs["Color1"])
    nt.links.new(_sm(nt, n3.outputs["Fac"], 0.45, 0.85, 0.0, 0.55),
                 mix3.inputs["Fac"])
    nt.links.new(mix3.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    m.diffuse_color = (*base, 1.0)
    return m


def runway_material(name):
    """Weathered runway asphalt with rubber about the centreline.

    The along/lateral frame is baked in from the TRUE track, and the touchdown
    zones are placed at the DISPLACED thresholds - 52 m in from the south end
    and 48 m in from the north - not at the pavement ends, because that is where
    aeroplanes actually touch down. Amplitudes read off the photographs."""
    m, nt, out, bsdf = _blank(name, 0.82)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1200, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    X, Y = sep.outputs["X"], sep.outputs["Y"]
    a = _nm(nt, "ADD", _nm(nt, "MULTIPLY", X, UX), _nm(nt, "MULTIPLY", Y, UY))
    l = _nm(nt, "ADD", _nm(nt, "MULTIPLY", X, NX), _nm(nt, "MULTIPLY", Y, NY))

    lg = _nm(nt, "MULTIPLY", l, 0.2)                 # sigma ~5 m
    gauss = _nm(nt, "EXPONENT",
                _nm(nt, "MULTIPLY", _nm(nt, "MULTIPLY", lg, lg), -1.0))
    tdz_a = _nm(nt, "MULTIPLY", _sm(nt, a, 60.0, 240.0),
                _sm(nt, a, 600.0, 1200.0, 1.0, 0.0))
    ar = _nm(nt, "SUBTRACT", THR20_A, a)
    tdz_b = _nm(nt, "MULTIPLY", _sm(nt, ar, 60.0, 240.0),
                _sm(nt, ar, 600.0, 1200.0, 1.0, 0.0))
    amp = _nm(nt, "ADD", 0.20,
              _nm(nt, "MULTIPLY", _nm(nt, "ADD", tdz_a, tdz_b), 0.80))
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(_nm(nt, "MULTIPLY", a, 0.006), cmb.inputs[0])
    nt.links.new(_nm(nt, "MULTIPLY", l, 0.45), cmb.inputs[1])
    n_st = nt.nodes.new("ShaderNodeTexNoise")
    n_st.inputs["Scale"].default_value = 1.0
    n_st.inputs["Detail"].default_value = 4.0
    nt.links.new(cmb.outputs[0], n_st.inputs["Vector"])
    streak = _sm(nt, n_st.outputs["Fac"], 0.32, 0.68, 0.25, 1.0)
    rub = _nm(nt, "MINIMUM", 1.0,
              _nm(nt, "MULTIPLY", _nm(nt, "MULTIPLY", gauss, amp),
                  _nm(nt, "MULTIPLY", streak, 1.15)))

    n_big = nt.nodes.new("ShaderNodeTexNoise")
    n_big.inputs["Scale"].default_value = 0.005
    n_big.inputs["Detail"].default_value = 3.0
    nt.links.new(geo.outputs["Position"], n_big.inputs["Vector"])
    mix_b = nt.nodes.new("ShaderNodeMixRGB")
    mix_b.inputs["Color1"].default_value = (0.062, 0.062, 0.058, 1.0)
    mix_b.inputs["Color2"].default_value = (0.112, 0.106, 0.096, 1.0)
    nt.links.new(_sm(nt, n_big.outputs["Fac"], 0.35, 0.65), mix_b.inputs["Fac"])
    # red dust drifted onto the edges from the latosol shoulders
    edge = _sm(nt, _nm(nt, "ABSOLUTE", l), 14.0, 22.5, 0.0, 0.55)
    mix_d = nt.nodes.new("ShaderNodeMixRGB")
    mix_d.inputs["Color2"].default_value = (0.150, 0.088, 0.052, 1.0)
    nt.links.new(mix_b.outputs[0], mix_d.inputs["Color1"])
    nt.links.new(edge, mix_d.inputs["Fac"])
    mix_r = nt.nodes.new("ShaderNodeMixRGB")
    mix_r.inputs["Color2"].default_value = (0.017, 0.017, 0.018, 1.0)
    nt.links.new(mix_d.outputs[0], mix_r.inputs["Color1"])
    nt.links.new(rub, mix_r.inputs["Fac"])
    nt.links.new(mix_r.outputs[0], bsdf.inputs["Base Color"])
    nt.links.new(_nm(nt, "SUBTRACT", 0.84, _nm(nt, "MULTIPLY", rub, 0.25)),
                 bsdf.inputs["Roughness"])
    _finish(nt, bsdf, out, 840)
    m.diffuse_color = (0.078, 0.076, 0.070, 1.0)
    return m


def worn_marking_material(name, base):
    """Runway/taxiway paint, worn. Same recipe as Santiago; the wear here is
    heavier because SDSC's markings are older than its traffic."""
    m, nt, out, bsdf = _blank(name, 0.70)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-900, 0)
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 0.010
    n1.inputs["Detail"].default_value = 2.0
    nt.links.new(geo.outputs["Position"], n1.inputs["Vector"])
    w1 = _sm(nt, n1.outputs["Fac"], 0.30, 0.70, 0.58, 1.0)
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 0.35
    n2.inputs["Detail"].default_value = 2.0
    nt.links.new(geo.outputs["Position"], n2.inputs["Vector"])
    w2 = _sm(nt, n2.outputs["Fac"], 0.25, 0.75, 0.80, 1.02)
    w = _nm(nt, "MULTIPLY", w1, w2)
    lc = nt.nodes.new("ShaderNodeCombineColor")
    for i, ch in enumerate(base):
        nt.links.new(_nm(nt, "MULTIPLY", w, ch), lc.inputs[i])
    nt.links.new(lc.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    m.diffuse_color = (*base, 1.0)
    return m


def latosol_material(name, soil, soil_dark, grass, grass_dry, scale=1.0,
                     runway_band=False):
    """The infield: RED-BROWN LATOSOL under dry-season grass.

    This is the material Santiago's ochre soil cannot be recoloured into. The
    photographs give a soil whose channels run roughly 1 : 0.48 : 0.26 - a
    strongly red earth - against Santiago's 1 : 0.78 : 0.43 pale ochre. The
    reference is refs/ga_cessna150_2007.jpg (wet season, bare red earth beside
    green grass) and refs/mro_airbus_esquadrilha_2010.jpg (July, the same earth
    dry and dusty with olive stubble over it). Values are read qualitatively off
    those two frames, not sampled photometrically.

    Structure: grass over soil, with the soil showing through on the worn and
    graded bands, plus a fine tuft mottle at ~20 m for the low camera."""
    m, nt, out, bsdf = _blank(name, 0.95)
    tex = nt.nodes.new("ShaderNodeTexCoord"); tex.location = (-1000, 0)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.location = (-860, 0)
    mp.inputs["Scale"].default_value = (0.001, 0.001, 0.001)
    nt.links.new(tex.outputs["Object"], mp.inputs["Vector"])

    n1 = nt.nodes.new("ShaderNodeTexNoise")          # ~350 m: field patches
    n1.inputs["Scale"].default_value = 2.8 * scale
    n1.inputs["Detail"].default_value = 5.0
    n1.inputs["Roughness"].default_value = 0.55
    nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    g_mix = nt.nodes.new("ShaderNodeMixRGB")
    g_mix.inputs["Color1"].default_value = (*grass, 1.0)
    g_mix.inputs["Color2"].default_value = (*grass_dry, 1.0)
    nt.links.new(_sm(nt, n1.outputs["Fac"], 0.35, 0.68), g_mix.inputs["Fac"])

    n2 = nt.nodes.new("ShaderNodeTexNoise")          # ~60 m: bare-earth scars
    n2.inputs["Scale"].default_value = 16.0 * scale
    n2.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], n2.inputs["Vector"])
    s_mix = nt.nodes.new("ShaderNodeMixRGB")
    s_mix.inputs["Color1"].default_value = (*soil, 1.0)
    s_mix.inputs["Color2"].default_value = (*soil_dark, 1.0)
    nt.links.new(_sm(nt, n2.outputs["Fac"], 0.30, 0.70), s_mix.inputs["Fac"])

    n3 = nt.nodes.new("ShaderNodeTexNoise")          # where soil wins
    n3.inputs["Scale"].default_value = 7.0 * scale
    n3.inputs["Detail"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], n3.inputs["Vector"])
    soil_fac = _sm(nt, n3.outputs["Fac"], 0.48, 0.76, 0.04, 1.00)
    if runway_band:
        # The graded strip either side of the pavement is scraped bare: in
        # refs/mro_airbus_esquadrilha_2010.jpg and refs/ga_cessna150_2007.jpg
        # the earth beside the paving is raw red latosol, and only further out
        # does the grass close over. |lateral| < 130 m of the TRUE track.
        geo2 = nt.nodes.new("ShaderNodeNewGeometry")
        sp = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo2.outputs["Position"], sp.inputs[0])
        lat = _nm(nt, "ABSOLUTE",
                  _nm(nt, "ADD", _nm(nt, "MULTIPLY", sp.outputs["X"], NX),
                      _nm(nt, "MULTIPLY", sp.outputs["Y"], NY)))
        soil_fac = _nm(nt, "MAXIMUM", soil_fac,
                       _sm(nt, lat, 30.0, 95.0, 0.90, 0.0))
    top = nt.nodes.new("ShaderNodeMixRGB")
    nt.links.new(g_mix.outputs[0], top.inputs["Color1"])
    nt.links.new(s_mix.outputs[0], top.inputs["Color2"])
    nt.links.new(soil_fac, top.inputs["Fac"])

    n4 = nt.nodes.new("ShaderNodeTexNoise")          # ~20 m tuft mottle
    n4.inputs["Scale"].default_value = 48.0 * scale
    n4.inputs["Detail"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], n4.inputs["Vector"])
    lum = nt.nodes.new("ShaderNodeMapRange")
    lum.inputs["To Min"].default_value = 0.70
    lum.inputs["To Max"].default_value = 1.16
    nt.links.new(n4.outputs["Fac"], lum.inputs["Value"])
    lc = nt.nodes.new("ShaderNodeCombineColor")
    for i in range(3):
        nt.links.new(lum.outputs["Result"], lc.inputs[i])
    mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 1.0
    nt.links.new(top.outputs[0], mul.inputs["Color1"])
    nt.links.new(lc.outputs[0], mul.inputs["Color2"])
    nt.links.new(mul.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    m.diffuse_color = (*soil, 1.0)
    return m


def cane_material(name):
    """The surround: SUGAR CANE and pasture on red soil.

    refs/mro_centro_tecnologico_2009.jpg is taken through a cane field with the
    hangars on the skyline; RECOGNITION.md section 2 makes the cane one of the
    five things that say "Sao Carlos". Cane is grown in long parallel rows in
    blocks of a few hundred metres, cut on a five-stage rotation, so the surround
    is a patchwork of standing green cane, pale cut stubble, burnt-off dark
    ground and bare red earth - never Santiago's neat tan grid.

    Blocks and palette are read off the photographs and off the satellite
    impression of the region; the field boundaries are procedural, not the
    mapped parcels."""
    m, nt, out, bsdf = _blank(name, 0.95)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1200, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    cx = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", sep.outputs["X"], 430.0))
    cy = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", sep.outputs["Y"], 350.0))
    cell = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(cx, cell.inputs[0])
    nt.links.new(cy, cell.inputs[1])
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"
    nt.links.new(cell.outputs[0], wn.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-380, 0)
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    stops = [(0.00, (0.070, 0.098, 0.030)),   # standing cane, deep green
             (0.26, (0.132, 0.140, 0.058)),   # ratoon / older cane, olive
             (0.46, (0.175, 0.152, 0.078)),   # cut stubble, pale straw
             (0.64, (0.190, 0.092, 0.048)),   # ploughed red latosol
             (0.82, (0.098, 0.098, 0.044))]   # pasture
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[1][0], (*stops[1][1], 1)
    for pos, col in stops[2:]:
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    nt.links.new(wn.outputs["Value"], ramp.inputs["Fac"])
    wn2 = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn2.noise_dimensions = "4D"
    wn2.inputs["W"].default_value = 3.17
    nt.links.new(cell.outputs[0], wn2.inputs["Vector"])
    lum = nt.nodes.new("ShaderNodeMapRange")
    lum.inputs["To Min"].default_value = 0.80
    lum.inputs["To Max"].default_value = 1.18
    nt.links.new(wn2.outputs["Value"], lum.inputs["Value"])
    lc = nt.nodes.new("ShaderNodeCombineColor")
    for i in range(3):
        nt.links.new(lum.outputs["Result"], lc.inputs[i])
    mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], mul.inputs["Color1"])
    nt.links.new(lc.outputs[0], mul.inputs["Color2"])
    # cane rows: noise squashed 22:1, so the blocks read as planted, not painted
    rm = nt.nodes.new("ShaderNodeMapping")
    rm.inputs["Scale"].default_value = (0.22, 0.010, 0.010)
    nt.links.new(geo.outputs["Position"], rm.inputs["Vector"])
    rows = nt.nodes.new("ShaderNodeTexNoise")
    rows.inputs["Scale"].default_value = 1.0
    rows.inputs["Detail"].default_value = 2.0
    nt.links.new(rm.outputs["Vector"], rows.inputs["Vector"])
    rl = nt.nodes.new("ShaderNodeMapRange")
    rl.inputs["To Min"].default_value = 0.88
    rl.inputs["To Max"].default_value = 1.10
    nt.links.new(rows.outputs["Fac"], rl.inputs["Value"])
    rc = nt.nodes.new("ShaderNodeCombineColor")
    for i in range(3):
        nt.links.new(rl.outputs["Result"], rc.inputs[i])
    mul2 = nt.nodes.new("ShaderNodeMixRGB"); mul2.blend_type = "MULTIPLY"
    mul2.inputs["Fac"].default_value = 1.0
    nt.links.new(mul.outputs[0], mul2.inputs["Color1"])
    nt.links.new(rc.outputs[0], mul2.inputs["Color2"])
    nt.links.new(mul2.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    m.diffuse_color = (0.12, 0.12, 0.05, 1.0)
    return m


def ribbed_material(name, colour, pitch=1.0, rough=0.62):
    """Ribbed/trapezoidal metal sheet: a soft vertical corrugation. The MRO
    cladding is ribbed sheet in every photograph, and a flat wall at 1 km reads
    as a slab. The rib is shading only, no geometry."""
    m, nt, out, bsdf = _blank(name, rough)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-900, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    s = _nm(nt, "ADD", _nm(nt, "MULTIPLY", sep.outputs["X"], 0.9),
            _nm(nt, "MULTIPLY", sep.outputs["Y"], 0.44))
    ph = _nm(nt, "MULTIPLY", _nm(nt, "DIVIDE", s, pitch), 6.28318)
    w = _nm(nt, "ADD", 0.90, _nm(nt, "MULTIPLY", _nm(nt, "SINE", ph), 0.10))
    lc = nt.nodes.new("ShaderNodeCombineColor")
    for i, ch in enumerate(colour):
        nt.links.new(_nm(nt, "MULTIPLY", w, ch), lc.inputs[i])
    nt.links.new(lc.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    m.diffuse_color = (*colour, 1.0)
    return m


def chequer_material(name, a, b, cell=1.6):
    """The Brazilian obstruction chequer: orange and white squares."""
    m, nt, out, bsdf = _blank(name, 0.70)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-900, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    u = _nm(nt, "ADD", sep.outputs["X"], sep.outputs["Y"])
    fu = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", u, cell))
    fv = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", sep.outputs["Z"], cell))
    par = _nm(nt, "MODULO", _nm(nt, "ADD", fu, fv), 2.0)
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.inputs["Color1"].default_value = (*a, 1.0)
    mix.inputs["Color2"].default_value = (*b, 1.0)
    nt.links.new(par, mix.inputs["Fac"])
    nt.links.new(mix.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    m.diffuse_color = (*a, 1.0)
    return m


def palette():
    """Colours are linear-Rec709, read QUALITATIVELY off the photographs listed
    in sdsc_references.md section 3. They are not spectrophotometric."""
    # LATAM indigo is a very DARK blue-violet (the official #150E4C family), not
    # the lavender a naive linear 0.19 renders as under AgX with a bright sky.
    band = ((0.0085, 0.0035, 0.0740) if LIVERY == "latam"
            else (0.0900, 0.0080, 0.0180))                  # TAM maroon
    return dict(
        asphalt=mat("SDSC_Asphalt", (0.060, 0.060, 0.056), 0.80),
        shoulder=mat("SDSC_Shoulder", (0.105, 0.086, 0.062), 0.90),
        # refs/mro_airbus_esquadrilha_2010.jpg: the MRO apron is pale concrete
        # with a warm dust film, much lighter than the runway.
        concrete=aged_pavement_material("SDSC_Concrete",
                                        (0.215, 0.208, 0.192),
                                        (0.258, 0.248, 0.228),
                                        (0.145, 0.138, 0.126), 0.020, 0.86),
        taxi=aged_pavement_material("SDSC_TaxiwayAsphalt",
                                    (0.090, 0.088, 0.080),
                                    (0.140, 0.134, 0.120),
                                    (0.058, 0.056, 0.052), 0.017, 0.85),
        white=worn_marking_material("SDSC_MarkingWhite", (0.500, 0.498, 0.478)),
        yellow=worn_marking_material("SDSC_MarkingYellow", (0.400, 0.255, 0.020)),
        red=mat("SDSC_MarkingRed", (0.320, 0.030, 0.020), 0.70),
        # the infield: dry-season olive grass over red latosol
        soil=latosol_material("SDSC_Infield",
                              (0.245, 0.108, 0.052), (0.138, 0.056, 0.026),
                              (0.106, 0.108, 0.034), (0.168, 0.140, 0.056),
                              runway_band=True),
        # kept for a future outfield split; the pad currently uses one material
        soil_out=latosol_material("SDSC_InfieldOuter",
                                  (0.222, 0.098, 0.048), (0.124, 0.050, 0.024),
                                  (0.098, 0.102, 0.032), (0.156, 0.132, 0.052),
                                  scale=0.55),
        cane=cane_material("SDSC_Cane"),
        # cladding: light grey ribbed sheet in every MRO photograph
        clad=ribbed_material("SDSC_Cladding", (0.255, 0.258, 0.252), 1.1),
        clad_warm=ribbed_material("SDSC_CladdingWarm", (0.230, 0.222, 0.204), 1.1),
        roof_grey=mat("SDSC_RoofGrey", (0.165, 0.168, 0.166), 0.66),
        roof_pale=mat("SDSC_RoofPale", (0.215, 0.216, 0.210), 0.60),
        roof_rust=mat("SDSC_RoofRust", (0.115, 0.072, 0.050), 0.80),
        band=mat("SDSC_FasciaBand", band, 0.55),
        oxide=mat("SDSC_OxideRed", (0.115, 0.024, 0.020), 0.72),
        latam_indigo=mat("SDSC_LATAM_Indigo", (0.0085, 0.0035, 0.0740), 0.55),
        latam_coral=mat("SDSC_LATAM_Coral", (0.847, 0.008, 0.082), 0.45),
        latam_white=mat("SDSC_LATAM_White", (0.700, 0.702, 0.715), 0.42),
        tam_red=mat("SDSC_TAM_Red", (0.520, 0.012, 0.030), 0.45),
        # refs/mro_centro_tecnologico_2010.jpg / _2006: the space frame really
        # is that red, and it is the one interior colour that matters.
        frame_red=mat("SDSC_SpaceFrameRed", (0.420, 0.045, 0.028), 0.60),
        hangar_dark=mat("SDSC_HangarInterior", (0.022, 0.020, 0.019), 0.90),
        floor_pale=mat("SDSC_HangarFloor", (0.300, 0.298, 0.290), 0.35),
        wall_white=mat("SDSC_WallRender", (0.400, 0.396, 0.380), 0.80),
        wall_cream=mat("SDSC_WallCream", (0.330, 0.310, 0.268), 0.82),
        mesh_black=mat("SDSC_MeshFence", (0.020, 0.021, 0.022), 0.60),
        glass=mat("SDSC_Glass", (0.028, 0.042, 0.048), 0.16, metal=0.35),
        steel=mat("SDSC_Steel", (0.320, 0.330, 0.340), 0.42, metal=0.85),
        mast=mat("SDSC_Mast", (0.480, 0.482, 0.488), 0.52),
        chequer=chequer_material("SDSC_Chequer", (0.640, 0.180, 0.030),
                                 (0.640, 0.640, 0.630)),
        concrete_bare=mat("SDSC_BareConcrete", (0.175, 0.170, 0.158), 0.88),
        foliage=mat("SDSC_Foliage", (0.048, 0.076, 0.024), 0.92),
        foliage2=mat("SDSC_FoliageDry", (0.075, 0.082, 0.032), 0.92),
        trunk=mat("SDSC_TreeTrunk", (0.042, 0.033, 0.024), 0.92),
        ac_white=mat("SDSC_AircraftWhite", (0.640, 0.643, 0.655), 0.30),
        ac_grey=mat("SDSC_AircraftGrey", (0.175, 0.185, 0.195), 0.35),
        ga_white=mat("SDSC_GAWhite", (0.560, 0.562, 0.570), 0.35),
        ga_trim=mat("SDSC_GATrim", (0.030, 0.050, 0.220), 0.40),
        tile_red=mat("SDSC_RoofTile", (0.160, 0.062, 0.038), 0.90),
    )


# ---------------------------------------------------------------------------
# the runway, and ICAO Annex 14 markings
#
# SDSC HAS NO AERODROME CHART. DECEA publishes an ADC only for IFR aerodromes
# and SDSC is VFR, so the marking layout, the taxiway designators, the stand
# positions and the lighting layout are ALL unpublished (sdsc_references.md
# section 6.1). What follows is the Annex 14 pattern for a 45 m code-C runway
# with LDA 1668/1672 m and the published 52 m / 48 m displacements, applied by
# me. It is an ESTIMATE, not a survey.
# ---------------------------------------------------------------------------
S = 1.5
GLYPHS = {
    "0": [(0.0, 0.0, 4.5, 1.5), (0.0, 7.5, 4.5, 9.0), (0.0, 0.0, 1.5, 9.0),
          (3.0, 0.0, 4.5, 9.0)],
    "2": [(0.0, 7.5, 4.5, 9.0), (3.0, 4.5, 4.5, 7.5), (0.0, 3.9, 4.5, 5.1),
          (0.0, 0.0, 1.5, 4.5), (0.0, 0.0, 4.5, 1.5)],
}
GLYPH_W = 4.5
GLYPH_GAP = 1.5


def paint_glyphs(bm, text, along0, lateral_centre, direction, z_off):
    """Characters lying on the pavement, read from the approaching threshold.
    direction = +1 for the 02 end, -1 for the 20 end.

    The glyph's local +x must run to the PILOT'S RIGHT, which is -lateral on a
    northbound roll and +lateral on a southbound one - hence the minus below.
    Get that sign wrong and RWY 02 is painted "20": the string reverses and every
    digit mirrors, and both faults come from the same term."""
    total = len(text) * GLYPH_W + (len(text) - 1) * GLYPH_GAP
    x0 = -total * 0.5
    for ch in text:
        for (gx0, gy0, gx1, gy1) in GLYPHS[ch]:
            corners = [(gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1)]
            vs = []
            for (cx, cy) in corners:
                lat = lateral_centre - direction * (x0 + cx)
                a = along0 + direction * cy
                vs.append(bm.verts.new(rwy_pt(a, lat, z_off)))
            try:
                bm.faces.new(vs)
            except ValueError:
                pass
        x0 += GLYPH_W + GLYPH_GAP


def strip(bm, a0, a1, l0, l1, dz, steps=1):
    """A pavement rectangle in runway coordinates. `steps` subdivides along the
    track so the surface follows the 0.62% slope instead of chording it."""
    for k in range(steps):
        b0 = a0 + (a1 - a0) * k / steps
        b1 = a0 + (a1 - a0) * (k + 1) / steps
        vs = [bm.verts.new(rwy_pt(a, l, dz))
              for (a, l) in ((b0, l0), (b1, l0), (b1, l1), (b0, l1))]
        try:
            bm.faces.new(vs)
        except ValueError:
            pass


def build_runway(bm_pave, bm_sh, bm_mark):
    """RWY 02/20: 1 720 x 45 m of pavement, thresholds displaced 52 m and 48 m,
    on a 0.62% down-to-the-north grade. All of it from the published survey; the
    MARKINGS are the Annex 14 pattern applied by me (see the block comment)."""
    half = RWY_WIDTH * 0.5

    # pavement and shoulders, subdivided so the grade is a ramp, not a chord
    strip(bm_pave, PAVE_S_A, PAVE_N_A, -half, half, Z_RUNWAY, steps=48)
    for s in (1, -1):
        strip(bm_sh, PAVE_S_A - 30.0, PAVE_N_A + 30.0,
              s * half, s * (half + 8.0), Z_SHOULDER, steps=48)

    for (thr_a, d, label, disp) in ((THR02_A, +1, "02", DISP_02),
                                    (THR20_A, -1, "20", DISP_20)):
        def A(v):
            return thr_a + d * v

        # threshold stripes: 12 for a 45 m runway, 1.80 m wide, 1.80 m apart,
        # outer edges 1.80 m in from the runway edge, 30 m long from 6 m in
        w, g, inner = 1.80, 1.80, 1.80
        for s in (1, -1):
            for i in range(6):
                l0 = inner + i * (w + g)
                strip(bm_mark, A(6.0), A(36.0), s * l0, s * (l0 + w), Z_MARK, 2)
        # designator, letter-free here: "02" and "20"
        paint_glyphs(bm_mark, label, A(52.0), 0.0, d, Z_MARK)
        # aiming point: LDA 1668/1672 m -> 300 m, 45 m long, inner edges 9.25 m
        for s in (1, -1):
            strip(bm_mark, A(300.0), A(345.0), s * 9.25, s * 15.25, Z_MARK, 2)
        # touchdown zone: pairs at 150 m spacing, the pair at the aiming point
        # deleted by rule. LDA 1500-2400 m -> four pairs.
        for dist in (150.0, 450.0, 600.0, 750.0):
            for s in (1, -1):
                for i in range(3):
                    l0 = 9.25 + i * 3.0
                    strip(bm_mark, A(dist), A(dist + 22.5),
                          s * l0, s * (l0 + 1.8), Z_MARK, 1)
        # pre-threshold: the displaced area carries arrows on and beside the
        # centreline, and an arrowhead row across the threshold
        n_arrows = max(1, int(disp // 30))
        for i in range(n_arrows):
            a_tip = A(-8.0 - i * 30.0)
            for lat in (0.0, -9.0, 9.0):
                strip(bm_mark, a_tip - d * 22.0, a_tip - d * 4.0,
                      lat - 0.45, lat + 0.45, Z_MARK, 2)
                vs = [bm_mark.verts.new(rwy_pt(a_tip, lat, Z_MARK)),
                      bm_mark.verts.new(rwy_pt(a_tip - d * 4.0, lat - 1.6, Z_MARK)),
                      bm_mark.verts.new(rwy_pt(a_tip - d * 4.0, lat + 1.6, Z_MARK))]
                try:
                    bm_mark.faces.new(vs)
                except ValueError:
                    pass

    # centre line: 30 m stripe, 30 m gap, 0.9 m wide, between the thresholds
    a = THR02_A + 12.0
    while a + 30.0 < THR20_A - 12.0:
        strip(bm_mark, a, a + 30.0, -0.45, 0.45, Z_MARK, 1)
        a += 60.0
    # side stripes, over the full pavement
    for s in (1, -1):
        strip(bm_mark, PAVE_S_A, PAVE_N_A, s * (half - 0.9), s * half, Z_MARK, 24)


# ---------------------------------------------------------------------------
# the field
# ---------------------------------------------------------------------------
def build_field():
    global G
    wipe()
    G = Ground()
    verify_levels()
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    P = palette()
    d = data()

    c_root = coll("SDSC_Field")
    c_run = coll("SDSC_Runway", c_root)
    c_taxi = coll("SDSC_Taxiways", c_root)
    c_apron = coll("SDSC_Aprons", c_root)
    c_ground = coll("SDSC_Ground", c_root)
    c_bldg = coll("SDSC_Buildings", c_root)
    c_mro = coll("SDSC_LATAM_MRO", c_root)
    c_club = coll("SDSC_Aeroclube", c_root)
    c_mid = coll("SDSC_Midfield", c_root)
    c_veg = coll("SDSC_Vegetation", c_root)
    c_furn = coll("SDSC_Furniture", c_root)
    c_park = coll("SDSC_ParkedAircraft", c_root)
    c_anchor = coll("SDSC_Anchors")
    c_light = coll("SDSC_Light")

    build_ground(d, P, c_ground)

    bmp, bms, bmm = bmesh.new(), bmesh.new(), bmesh.new()
    build_runway(bmp, bms, bmm)
    bm_to_object(bmp, "SDSC_RunwayPavement", runway_material("SDSC_Runway_0220"),
                 c_run)
    bm_to_object(bms, "SDSC_RunwayShoulders", P["shoulder"], c_run)
    bm_to_object(bmm, "SDSC_RunwayMarkings", P["white"], c_run)

    build_taxiways(d, P, c_taxi)
    build_aprons(d, P, c_apron)
    build_buildings(d, P, c_bldg, c_mro, c_club, c_mid)
    build_hangar9(P, c_mro)
    build_mro_frontage(d, P, c_mro)
    build_mro_perimeter(P, c_mro)
    build_midfield(P, c_mid)
    build_masts(P, c_furn)
    build_windsock(d, P, c_furn)
    build_runway_furniture(d, P, c_furn)
    build_trees(d, P, c_veg)
    build_parked_aircraft(P, c_park)
    build_light(P, c_light)

    # ---- anchors: +Y points down the take-off track --------------------
    for name, xy, z, brg in (
            ("SDSC_02_Threshold", (0.0, 0.0), Z_THR02, TRACK_02_DEG),
            ("SDSC_20_Threshold", (29.0, 1619.72), Z_THR20, TRACK_02_DEG + 180.0),
            ("SDSC_LATAM_MRO", (912.5, 1608.9), Z_MRO_PLATFORM, TRACK_02_DEG),
            ("SDSC_Hangar9", ((HANGAR9["x0"] + HANGAR9["x1"]) * 0.5,
                              (HANGAR9["y0"] + HANGAR9["y1"]) * 0.5),
             Z_MRO_PLATFORM, TRACK_02_DEG)):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 60.0
        e.location = (xy[0], xy[1], z)
        e.rotation_euler = (0.0, 0.0, math.radians(-brg))
        c_anchor.objects.link(e)

    scn.render.engine = "CYCLES"
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Base Contrast"
    scn.view_settings.exposure = 0.0
    for cam in bpy.data.cameras:
        cam.clip_end = 250000.0
    print("field objects:", len(bpy.data.objects),
          "polys:", sum(len(o.data.polygons) for o in bpy.data.objects
                        if o.type == "MESH"))


def verify_levels():
    """Print the three platform constants back against the grid they came from,
    every build. If a future DEM refresh moves them, this is where it shows."""
    print("-- graded surface check (m AMSL) --")
    for lbl, x, y, want in (("THR 02", 0.0, 0.0, 807.0 + Z_THR02),
                            ("THR 20", 29.0, 1619.72, 807.0 + Z_THR20),
                            ("MRO apron", 916.0, 1882.0, 807.0 + Z_MRO_PLATFORM),
                            ("mid-field apron", 280.0, 1138.0,
                             807.0 + Z_MIDFIELD_APRON),
                            ("Aeroclube apron", -216.0, 473.0,
                             807.0 + Z_AEROCLUBE_APRON)):
        print("   %-16s graded %8.2f   DEM %8.2f   published/median %8.2f"
              % (lbl, 807.0 + G.graded(x, y), 807.0 + G.dem(x, y), want))
    print("   runway fall THR02->THR20: %.2f m  (%.3f%%)"
          % (Z_THR02 - Z_THR20, -RWY_SLOPE * 100.0))


def build_ground(d, P, c_ground):
    """The aerodrome ground, graded; and the cane surround beyond it.

    Santiago drops one flat pad. Here the pad is a 25 m grid whose z is
    graded(x, y): the runway slope, the MRO platform and the real eastward fall
    are all in it. The outer 250 m of the pad tapers down onto the terrain so
    its rim closes rather than standing as a step."""
    ring = dedupe_ring(d["aerodrome_boundary_xy_m"][0])
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    x0, x1 = min(xs) - 400.0, max(xs) + 400.0
    y0, y1 = min(ys) - 400.0, max(ys) + 400.0
    step = 25.0
    nx = int((x1 - x0) / step) + 1
    ny = int((y1 - y0) / step) + 1
    bm = bmesh.new()
    grid = []
    for j in range(ny):
        row = []
        y = y0 + j * step
        for i in range(nx):
            x = x0 + i * step
            # taper the last 250 m down onto the terrain (which sits 0.8 lower)
            e = min(x - x0, x1 - x, y - y0, y1 - y)
            t = _smoothstep(1.0 - e / 200.0)
            row.append(bm.verts.new((x, y, G.graded(x, y) - 0.8 * t)))
        grid.append(row)
    for j in range(ny - 1):
        for i in range(nx - 1):
            try:
                bm.faces.new((grid[j][i], grid[j][i + 1],
                              grid[j + 1][i + 1], grid[j + 1][i]))
            except ValueError:
                pass
    bm_to_object(bm, "SDSC_AerodromeGround", P["soil"], c_ground, smooth=True)

    # The cane and pasture surround, in two tiers. RECOGNITION.md section 2
    # makes the cane one of the five things that say "Sao Carlos", and the
    # aerodrome pad now stops 400 m outside the fence, so the cane starts where
    # a camera on the field can still resolve it - hence a 120 m inner grid out
    # to 4 km, and a 400 m outer one beyond that where haze has taken over.
    for tag, reach, step2, mat_ in (("Inner", 4200.0, 120.0, P["cane"]),
                                    ("Outer", 9000.0, 400.0, P["cane"])):
        gx0, gx1 = min(xs) - reach, max(xs) + reach
        gy0, gy1 = min(ys) - reach, max(ys) + reach
        hole = (x0, x1, y0, y1) if tag == "Inner" else \
               (min(xs) - 4200.0, max(xs) + 4200.0,
                min(ys) - 4200.0, max(ys) + 4200.0)
        nx = int((gx1 - gx0) / step2) + 1
        ny = int((gy1 - gy0) / step2) + 1
        bm = bmesh.new()
        grid = []
        for j in range(ny):
            row = []
            y = gy0 + j * step2
            for i in range(nx):
                x = gx0 + i * step2
                row.append(bm.verts.new((x, y, G.dem(x, y) - 0.55)))
            grid.append(row)
        for j in range(ny - 1):
            for i in range(nx - 1):
                cx = gx0 + (i + 0.5) * step2
                cy = gy0 + (j + 0.5) * step2
                if hole[0] < cx < hole[1] and hole[2] < cy < hole[3]:
                    continue                # leave the inner tier its hole
                try:
                    bm.faces.new((grid[j][i], grid[j][i + 1],
                                  grid[j + 1][i + 1], grid[j + 1][i]))
                except ValueError:
                    pass
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces],
                         context="VERTS")
        bm_to_object(bm, "SDSC_CaneSurround_" + tag, mat_, c_ground,
                     smooth=True)


def build_taxiways(d, P, c_taxi):
    """Eight mapped taxiways. Widths are ESTIMATES - SDSC has no ADC and OSM
    carries no width tag. The MRO link (way/152827558, 1 163 m) is the one a
    widebody uses, so it is built at 23 m; the Aeroclube links at 12 m; the
    turn pads at each runway end are closed ways and are filled."""
    bm, bmc = bmesh.new(), bmesh.new()
    for t in d["taxiways"]:
        pts = t["polygon_xy_m"]
        oid = t["osm_id"]
        closed = len(pts) > 3 and math.dist(pts[0], pts[-1]) < 1.0
        if closed:
            flat_poly(bm, pts, Z_TAXI)
            continue
        w = 23.0 if oid in ("way/152827558", "way/152827557", "way/510750689",
                            "way/958781969") else 12.0
        ribbon(bm, pts, w, Z_TAXI)
        ribbon(bmc, pts, 0.30, Z_TAXI + 0.03)
    bm_to_object(bm, "SDSC_TaxiwayPavement", P["taxi"], c_taxi)
    bm_to_object(bmc, "SDSC_TaxiwayCentrelines", P["yellow"], c_taxi)


def build_aprons(d, P, c_apron):
    """Six mapped aprons: four tiny ones at the Aeroclube, the 13 386 m2
    mid-field apron, and the MRO's 35 729 m2 concrete. Each is FLAT at its own
    measured platform level - the MRO's is 35 m below the runway."""
    levels = {"relation/7422967": Z_MRO_PLATFORM,
              "relation/7422969": Z_MIDFIELD_APRON}
    bm = bmesh.new()
    for a in d["aprons"]:
        z = levels.get(a["osm_id"], Z_AEROCLUBE_APRON)
        flat_poly(bm, a["polygon_xy_m"], Z_APRON, flat_z=z)
    # hangar 9's apron. DECLARED INFERENCE: a new hangar needs a new stand in
    # front of it, and nothing in OSM (traced 2017) can show it.
    h = HANGAR9
    flat_poly(bm, [(h["x0"] - 25, h["y1"]), (h["x1"] + 25, h["y1"]),
                   (h["x1"] + 25, 1762.0), (h["x0"] - 25, 1762.0)],
              Z_APRON, flat_z=Z_MRO_PLATFORM)
    bm_to_object(bm, "SDSC_ApronConcrete", P["concrete"], c_apron)


def estimate_height(b):
    """(height, source-tag). 'dsm' is measured off the Copernicus surface model;
    everything else is mine."""
    oid = b.get("osm_id")
    if oid in MEASURED_HEIGHT:
        return MEASURED_HEIGHT[oid], "dsm"
    if oid in HEIGHT_BY_ID:
        return HEIGHT_BY_ID[oid], "est"
    lv = b.get("building_levels")
    if lv:
        try:
            return float(str(lv).split(";")[0]) * LEVEL_HEIGHT, "osm-levels"
        except ValueError:
            pass
    return HEIGHT_BY_TYPE.get(b.get("building"), 5.0), "est"


def gable(bm, ring, eave, ridge, bearing_deg, base=None):
    """Prism to the eave, then a shallow gable. The MRO roofs in
    refs/mro_centro_tecnologico_2009.jpg are gables of a very low pitch - the
    ridge rises about 2 m over a 70 m half-span - so `ridge` is deliberately
    close to `eave` everywhere in this build."""
    ring = dedupe_ring(ring)
    if len(ring) < 3:
        return
    if base is None:
        base = gz(sum(p[0] for p in ring) / len(ring),
                  sum(p[1] for p in ring) / len(ring))
    prism(bm, ring, 0.0, eave, base=base)
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    br = math.radians(bearing_deg)
    ux, uy = math.sin(br), math.cos(br)
    nx, ny = uy, -ux
    proj = [((p[0] - cx) * ux + (p[1] - cy) * uy,
             (p[0] - cx) * nx + (p[1] - cy) * ny) for p in ring]
    a0 = min(p[0] for p in proj); a1 = max(p[0] for p in proj)
    l0 = min(p[1] for p in proj); l1 = max(p[1] for p in proj)

    def w(a, l, z):
        return bm.verts.new((cx + ux * a + nx * l, cy + uy * a + ny * l, z))

    lm = (l0 + l1) * 0.5
    v = [w(a0, l0, base + eave), w(a1, l0, base + eave),
         w(a1, lm, base + ridge), w(a0, lm, base + ridge),
         w(a1, l1, base + eave), w(a0, l1, base + eave)]
    for f in ((v[0], v[1], v[2], v[3]), (v[3], v[2], v[4], v[5])):
        try:
            bm.faces.new(f)
        except ValueError:
            pass


def vault(bm, x0, x1, y0, y1, springing, apex, base, segs=14, along="y"):
    """A barrel vault: a circular-ish arch extruded along one axis.

    refs/sdsc_field_from_sp318_2013.jpg shows the mid-field hangar as a
    continuous shallow arch springing off a low vertical wall - not a gable, and
    not a half-cylinder. Springing height and apex are set by the caller."""
    ax0, ax1 = (x0, x1) if along == "y" else (y0, y1)
    span = ax1 - ax0
    r = span * 0.5
    rows = []
    for k in range(segs + 1):
        t = k / segs
        u = ax0 + span * t
        h = springing + (apex - springing) * math.sin(math.pi * t) ** 0.72
        rows.append((u, base + h))
    ends = (y0, y1) if along == "y" else (x0, x1)
    verts = []
    for e in ends:
        col = []
        for (u, z) in rows:
            col.append(bm.verts.new((u, e, z) if along == "y" else (e, u, z)))
        verts.append(col)
    for k in range(segs):
        try:
            bm.faces.new((verts[0][k], verts[0][k + 1],
                          verts[1][k + 1], verts[1][k]))
        except ValueError:
            pass
    # the two arched gable ends, and the low side walls
    for col in verts:
        try:
            f = bm.faces.new(col + [bm.verts.new(
                (rows[-1][0], col[0].co.y, base) if along == "y"
                else (col[0].co.x, rows[-1][0], base)),
                bm.verts.new((rows[0][0], col[0].co.y, base) if along == "y"
                             else (col[0].co.x, rows[0][0], base))])
            bmesh.ops.triangulate(bm, faces=[f])
        except ValueError:
            pass
    for k in (0, segs):
        u = rows[k][0]
        if along == "y":
            box(bm, u - 0.35, u + 0.35, y0, y1, base, base + springing)
        else:
            box(bm, x0, x1, u - 0.35, u + 0.35, base, base + springing)


def build_buildings(d, P, c_bldg, c_mro, c_club, c_mid):
    """The 95 mapped footprints, split by where they are and what they are.

    Two traps handled here, both from RECOGNITION.md section 5:
      - Only FOUR of the nine `hangar` polygons are on the LATAM site. The other
        five are the AEROCLUBE's, on the opposite side of the field, and they
        are little GA sheds, not airline hangars.
      - relation/7422930 is tagged `TAM MRO` AND `TAM Museum` with the museum's
        wikidata. The two 80 x 80 m halls at x ~1280-1360 are the museum, which
        closed in 2016; they are built as a disused block, not as MRO."""
    mro_ids = set(m["osm_id"] for m in d["latam_mro"]["members"])
    museum_ids = {"way/510750671", "way/510750697", "way/510750672",
                  "way/510750673", "way/510750664", "way/510750665",
                  "way/510750666", "way/510750667", "way/510750668",
                  "way/510750669", "way/510750670"}

    bm_mro = bmesh.new()          # MRO workshops and the hangar-line spine
    bm_mro_h = bmesh.new()        # MRO hangars proper
    bm_mus = bmesh.new()
    bm_club = bmesh.new()
    bm_village = bmesh.new()
    bm_shed = bmesh.new()

    def emit(bm, b, kind="prism"):
        h, _ = estimate_height(b)
        ring = b["polygon_xy_m"]
        if kind == "gable":
            brg = b.get("min_area_box", {}).get("long_axis_bearing_deg_true", 0.0)
            gable(bm, ring, h, h + 2.2, brg, base=Z_MRO_PLATFORM
                  if b["osm_id"] in mro_ids else None)
        else:
            base = Z_MRO_PLATFORM if b["osm_id"] in mro_ids else None
            prism(bm, ring, 0.0, h, base=base)

    for h in d["hangars"]:
        oid = h["osm_id"]
        if oid in ("relation/7422970",     # the mid-field vault
                   "relation/7422966"):    # the widebody bay, build_mro_frontage
            continue                       # both are built by hand
        if oid in mro_ids:
            emit(bm_mro_h, h, "gable")
        else:
            emit(bm_club, h, "gable")      # the five Aeroclube sheds

    for b in d["buildings"]:
        oid = b["osm_id"]
        if oid in museum_ids:
            emit(bm_mus, b)
        elif oid in mro_ids:
            emit(bm_mro, b)
        elif b.get("centroid_xy_m", [0, 0])[1] < -900:
            emit(bm_village, b)            # Agua Vermelha, 1.6 km south
        else:
            emit(bm_shed, b)
    for t in d["terminals"]:
        prism(bm_club, t["polygon_xy_m"], 0.0, 6.0)

    bm_to_object(bm_mro, "SDSC_MRO_Workshops", P["clad"], c_mro,
                 roof_mat=P["roof_grey"])
    bm_to_object(bm_mro_h, "SDSC_MRO_Hangars", P["clad"], c_mro,
                 roof_mat=P["roof_pale"])
    bm_to_object(bm_mus, "SDSC_Museu_TAM", P["wall_white"], c_mro,
                 roof_mat=P["roof_grey"])
    bm_to_object(bm_club, "SDSC_Aeroclube_Buildings", P["clad_warm"], c_club,
                 roof_mat=P["roof_rust"])
    bm_to_object(bm_village, "SDSC_AguaVermelha", P["wall_cream"], c_bldg,
                 roof_mat=P["tile_red"])
    bm_to_object(bm_shed, "SDSC_FieldSheds", P["wall_cream"], c_bldg,
                 roof_mat=P["roof_rust"])


def build_hangar9(P, c_mro):
    """HANGAR 9 - the 2025 building, and the only volume in this scene with no
    footprint behind it. Everything about it is declared inference; see the
    HANGAR9 block at the top of this file for the reasoning and README.md
    section 3 for the same in prose.

    Built as a single-bay portal shed: a 130 x 95 m box with a very shallow
    gable, a 78 x 20.5 m door on the north face, and the fascia band and mark
    the rest of the base carries."""
    h = HANGAR9
    base = Z_MRO_PLATFORM
    ring = [(h["x0"], h["y0"]), (h["x1"], h["y0"]),
            (h["x1"], h["y1"]), (h["x0"], h["y1"])]
    bm = bmesh.new()
    gable(bm, ring, h["eave"], h["ridge"], 91.0, base=base)
    ob = bm_to_object(bm, "SDSC_Hangar9", P["clad"], c_mro,
                      roof_mat=P["roof_pale"])
    ob["inference"] = ("declared inference: no published dimension, no OSM "
                       "footprint, position from apron geometry")

    cx = (h["x0"] + h["x1"]) * 0.5
    # the door: dark opening, with the red space frame and the pale floor
    # visible inside. refs/mro_centro_tecnologico_2010.jpg is the interior.
    bm = bmesh.new()
    dw, dh = h["door_w"] * 0.5, h["door_h"]
    box(bm, cx - dw, cx + dw, h["y1"] - 1.2, h["y1"] + 0.4, base, base + dh)
    bm_to_object(bm, "SDSC_Hangar9_Door", P["hangar_dark"], c_mro)
    bm = bmesh.new()                       # floor slab seen through the door
    vs = [bm.verts.new(p) for p in
          ((cx - dw, h["y1"] - 1.2, base + 0.02),
           (cx + dw, h["y1"] - 1.2, base + 0.02),
           (cx + dw, h["y0"] + 6.0, base + 0.02),
           (cx - dw, h["y0"] + 6.0, base + 0.02))]
    bm.faces.new(vs)
    bm_to_object(bm, "SDSC_Hangar9_Floor", P["floor_pale"], c_mro)
    bm = bmesh.new()                       # the red space frame, four bays deep
    for k in range(6):
        y = h["y1"] - 6.0 - k * 12.0
        box(bm, cx - dw, cx + dw, y - 0.5, y + 0.5,
            base + h["eave"] - 3.4, base + h["eave"] - 1.0)
    for k in range(9):
        x = cx - dw + k * (2 * dw / 8)
        box(bm, x - 0.35, x + 0.35, h["y0"] + 6.0, h["y1"] - 6.0,
            base + h["eave"] - 2.6, base + h["eave"] - 1.6)
    bm_to_object(bm, "SDSC_Hangar9_SpaceFrame", P["frame_red"], c_mro)

    # fascia band + wordmark on the door face
    band_z0, band_z1 = base + h["eave"] - 4.6, base + h["eave"] - 0.6
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in
          ((h["x0"], h["y1"] + 0.5, band_z0), (h["x1"], h["y1"] + 0.5, band_z0),
           (h["x1"], h["y1"] + 0.5, band_z1), (h["x0"], h["y1"] + 0.5, band_z1))]
    bm.faces.new(vs)
    bm_to_object(bm, "SDSC_Hangar9_Band", P["band"], c_mro)
    place_wordmark(P, c_mro, "SDSC_Hangar9", face_y=h["y1"] + 0.7,
                   x_centre=cx, z_base=band_z0 + 0.8, cap_m=3.2, facing=+1)


def place_wordmark(P, collection, tag, face_y, x_centre, z_base, cap_m,
                   facing=+1):
    """The LATAM lockup on a north- or south-facing fascia, from the OFFICIAL
    SVG via latam_livery_kit - never a lookalike font, the same rule the fleet
    livery follows.

    THE CHOICE OF MARK IS INFERENCE. Every photograph of this base carries the
    TAM wordmark on a maroon band, because every photograph is 2006-2014. The
    base has been LATAM since 2016 and hangar 9 opened under LATAM in 2025, so
    the current mark is what goes on; set SDSC_LIVERY=tam to rebuild it as
    photographed. Only the band colour and the mark change - the band's height,
    its position under the eave and its proportion are measured off
    refs/mro_centro_tecnologico_2009.jpg."""
    if LIVERY != "latam":
        # TAM-era: a plain white wordmark block, no official SVG exists here
        bm = bmesh.new()
        w = cap_m * 4.2
        vs = [bm.verts.new(p) for p in
              ((x_centre - w, face_y, z_base), (x_centre + w, face_y, z_base),
               (x_centre + w, face_y, z_base + cap_m),
               (x_centre - w, face_y, z_base + cap_m))]
        bm.faces.new(vs)
        bm_to_object(bm, tag + "_Wordmark", P["latam_white"], collection)
        return
    sys.path.insert(0, ROOT)
    import latam_livery_kit as kit
    me_word, me_brand = kit.importar_svg_2_camadas(
        os.path.join(ROOT, "latam_logo_indigo.svg"))
    word_y = [v.co.y for v in me_word.vertices]
    s = cap_m / (max(word_y) - min(word_y))
    all_x = [v.co.x for me in (me_word, me_brand) for v in me.vertices]
    lockup_w = (max(all_x) - min(all_x)) * s
    x_start = x_centre - facing * lockup_w * 0.5
    zs = z_base - min(word_y) * s
    for me, mt, nm in ((me_word, P["latam_white"], tag + "_Wordmark"),
                       (me_brand, P["latam_coral"], tag + "_Brandmark")):
        bm = bmesh.new()
        bm.from_mesh(me)
        for v in bm.verts:
            v.co = Vector((x_start + facing * v.co.x * s, face_y,
                           zs + v.co.y * s))
        bm_to_object(bm, nm, mt, collection)
        bpy.data.meshes.remove(me)


def build_mro_frontage(d, P, c_mro):
    """The face the apron and the parked line look at: the open hangar door, the
    red space frame behind it, the fascia band and the mark.

    GEOMETRY THAT IS DATA, and it is not the obvious face. relation/7422965 has
    a bbox of x 938..1080, but its ring is C-shaped: the west edge sits at
    x = 938 only for y 1569..1758, steps back to x = 988 for y 1758..1853 and to
    x = 1027 for y 1852..2039. Painting a band along "x = 938" for the whole
    length hangs it in mid-air for 280 m of it - which is exactly what the first
    build did, and what the tele check caught.

    The face that actually stands on the apron is **relation/7422966's west
    wall, x = 931, y 1759..1859** - the polygon OSM tags `aeroway=hangar`, 101 x
    57 m, sitting in the step in front of the spine. The apron polygon's own east
    edge runs along it, node for node. So the hangar is the block in front and
    the 471 m spine behind it is the workshop line, which is also the reading
    `sdsc_references.md` section 6.5 left open.

    GEOMETRY THAT IS INFERRED: the door on that face, its size, the band's
    height, and the hangar's height - see below.
    """
    base = Z_MRO_PLATFORM
    spine_eave = HEIGHT_BY_ID["relation/7422965"]

    # relation/7422966 as the WIDEBODY BAY. The DSM reads +14.0 m over it, but
    # the building is 57 m across - two 30 m cells - and a DSM smears roof edges
    # inward, so 14.0 is a floor here for the same reason phase 1 called +12.9 a
    # floor over the spine. A 767-300ER's fin is 15.85 m and an A330-200's
    # 17.4 m, and both types are documented at this base; neither clears 14 m.
    # 17.5 m eave is the smallest height that works. ESTIMATE, and it is why
    # HEIGHT_BY_ID overrides the measurement for this one polygon.
    xf, ya, yb = 931.0, 1759.0, 1859.0
    BAY_EAVE, BAY_RIDGE, DOOR_H, DOOR_W = 17.5, 20.0, 16.4, 84.0
    bm = bmesh.new()
    gable(bm, [(xf, ya), (990.0, ya), (990.0, yb), (xf, yb)],
          BAY_EAVE, BAY_RIDGE, 0.9, base=base)
    bm_to_object(bm, "SDSC_MRO_HangarBay", P["clad"], c_mro,
                 roof_mat=P["roof_pale"])

    # the fascia band. Three runs, one on each face that really exists and really
    # looks at the apron. Its 3.1 m height and its 0.5 m drop below the eave are
    # measured off refs/mro_centro_tecnologico_2009.jpg; the COLOUR is the livery
    # decision in README section 3.
    bm = bmesh.new()
    for (x_face, y0, y1, ev) in ((xf - 0.5, ya + 2.0, yb - 2.0, BAY_EAVE),
                                 (937.5, 1580.0, 1752.0, spine_eave),
                                 (1026.5, 1866.0, 2030.0, spine_eave)):
        z0, z1 = base + ev - 3.6, base + ev - 0.5
        vs = [bm.verts.new(p) for p in
              ((x_face, y0, z0), (x_face, y1, z0),
               (x_face, y1, z1), (x_face, y0, z1))]
        bm.faces.new(vs)
    bm_to_object(bm, "SDSC_MRO_FasciaBand", P["band"], c_mro)

    # the open door, and the bright red space frame behind it. The frame is the
    # one interior fact the photographs give unambiguously
    # (refs/mro_centro_tecnologico_2010.jpg, _2006, mro_centro_manutencao_2007):
    # a deep steel truss painted bright red under a white profiled deck.
    yc = (ya + yb) * 0.5
    d0, d1 = yc - DOOR_W * 0.5, yc + DOOR_W * 0.5
    bm, bmf, bmfl = bmesh.new(), bmesh.new(), bmesh.new()
    box(bm, xf - 0.9, xf + 0.4, d0, d1, base, base + DOOR_H)
    bm_to_object(bm, "SDSC_MRO_HangarDoors", P["hangar_dark"], c_mro)
    vs = [bmfl.verts.new(p) for p in
          ((xf + 0.4, d0, base + 0.02), (988.0, d0, base + 0.02),
           (988.0, d1, base + 0.02), (xf + 0.4, d1, base + 0.02))]
    bmfl.faces.new(vs)
    bm_to_object(bmfl, "SDSC_MRO_HangarFloor", P["floor_pale"], c_mro)
    for k in range(5):
        x = xf + 6.0 + k * 12.0
        box(bmf, x - 0.5, x + 0.5, d0, d1,
            base + BAY_EAVE - 4.0, base + BAY_EAVE - 1.6)
    for k in range(8):
        y = d0 + k * DOOR_W / 7.0
        box(bmf, xf + 1.0, 987.0, y - 0.35, y + 0.35,
            base + BAY_EAVE - 3.2, base + BAY_EAVE - 2.2)
    bm_to_object(bmf, "SDSC_MRO_SpaceFrame", P["frame_red"], c_mro)

    # the mark, on the 172 m of spine wall at x = 938 that faces the runway -
    # the face a departing aircraft actually sees, and the only long unbroken
    # one on the site.
    _wordmark_on_west_face(P, c_mro, 937.3, y_centre=1665.0,
                           z_base=base + spine_eave - 3.1, cap_m=2.9)


def _wordmark_on_west_face(P, collection, x_face, y_centre, z_base, cap_m):
    if LIVERY != "latam":
        bm = bmesh.new()
        w = cap_m * 4.2
        vs = [bm.verts.new(p) for p in
              ((x_face, y_centre - w, z_base), (x_face, y_centre + w, z_base),
               (x_face, y_centre + w, z_base + cap_m),
               (x_face, y_centre - w, z_base + cap_m))]
        bm.faces.new(vs)
        bm_to_object(bm, "SDSC_MRO_Wordmark", P["latam_white"], collection)
        return
    sys.path.insert(0, ROOT)
    import latam_livery_kit as kit
    me_word, me_brand = kit.importar_svg_2_camadas(
        os.path.join(ROOT, "latam_logo_indigo.svg"))
    wy = [v.co.y for v in me_word.vertices]
    s = cap_m / (max(wy) - min(wy))
    all_x = [v.co.x for me in (me_word, me_brand) for v in me.vertices]
    lockup_w = (max(all_x) - min(all_x)) * s
    y_north = y_centre + lockup_w * 0.5
    zs = z_base - min(wy) * s
    for me, mt, nm in ((me_word, P["latam_white"], "SDSC_MRO_Wordmark"),
                       (me_brand, P["latam_coral"], "SDSC_MRO_Brandmark")):
        bm = bmesh.new()
        bm.from_mesh(me)
        for v in bm.verts:
            v.co = Vector((x_face, y_north - v.co.x * s, zs + v.co.y * s))
        bm_to_object(bm, nm, mt, collection)
        bpy.data.meshes.remove(me)


def build_mro_perimeter(P, c_mro):
    """WHITE RENDERED WALL + BLACK WELDED-MESH FENCE.

    refs/mro_airbus_esquadrilha_2010.jpg: a white-rendered wall about 0.8 m
    high carrying a black welded-mesh panel fence on black posts, with red-brown
    latosol in front of it. It is the most recognisable boundary on the site and
    it is 20 lines of geometry. Its LINE is inferred - it is drawn along the
    south and east edges of the MRO block, which is where the landside is."""
    base = Z_MRO_PLATFORM
    bmw, bmm, bmp = bmesh.new(), bmesh.new(), bmesh.new()
    runs = [((620.0, 1545.0), (1105.0, 1545.0)),
            ((1105.0, 1545.0), (1105.0, 2050.0)),
            ((620.0, 1545.0), (620.0, 2050.0))]
    for (a, b) in runs:
        ux, uy, L = unit(a[0], a[1], b[0], b[1])
        nx, ny = -uy, ux
        n = int(L // 3.0)
        for i in range(n):
            t0, t1 = i * 3.0, (i + 1) * 3.0
            x0, y0 = a[0] + ux * t0, a[1] + uy * t0
            x1, y1 = a[0] + ux * t1, a[1] + uy * t1
            for (bmx, z0, z1, off) in ((bmw, 0.0, 0.85, 0.16),
                                       (bmm, 0.85, 2.85, 0.04)):
                vs = [bmx.verts.new(p) for p in
                      ((x0 - nx * off, y0 - ny * off, base + z0),
                       (x1 - nx * off, y1 - ny * off, base + z0),
                       (x1 - nx * off, y1 - ny * off, base + z1),
                       (x0 - nx * off, y0 - ny * off, base + z1))]
                try:
                    bmx.faces.new(vs)
                except ValueError:
                    pass
                if bmx is bmw:
                    vs = [bmx.verts.new(p) for p in
                          ((x0 + nx * off, y0 + ny * off, base + z0),
                           (x1 + nx * off, y1 + ny * off, base + z0),
                           (x1 + nx * off, y1 + ny * off, base + z1),
                           (x0 + nx * off, y0 + ny * off, base + z1))]
                    try:
                        bmx.faces.new(vs)
                    except ValueError:
                        pass
            post(bmp, x0, y0, 0.09, base + 0.85, base + 3.0)
    bm_to_object(bmw, "SDSC_MRO_PerimeterWall", P["wall_white"], c_mro)
    bm_to_object(bmm, "SDSC_MRO_PerimeterMesh", P["mesh_black"], c_mro)
    bm_to_object(bmp, "SDSC_MRO_PerimeterPosts", P["mesh_black"], c_mro)


def build_midfield(P, c_mid):
    """The MID-FIELD CLUSTER, and a correction to phase 1's reading of the best
    photograph in the survey.

    sdsc_references.md reads refs/sdsc_field_from_sp318_2013.jpg as the LATAM
    MRO at 1.3 km. Re-measured here, it cannot be:
      * The sight line from the SP-318 to the MRO is BLOCKED. The runway is a
        local crest - 796 m where the line crosses it - and the camera position
        the file records is at 792.6 m on the Copernicus grid, so everything
        beyond needs to be above ~800 m to clear it. The MRO platform is 770 m
        and its roofs reach 784 m.
      * The parked widebody's FIN TOP STANDS ABOVE THE HORIZON in the frame.
        That is distance-free: it puts the camera less than the aeroplane's own
        height (17.4 m) above the plane it stands on. The MRO apron is 35 m
        below the SP-318. The mid-field apron is 1.7 m below the runway.
      * Reading the height ratio the same way gives an arch 12.7 m to the apex
        and ~32 m across at the distance that implies. relation/7422970, the
        isolated mid-field hangar, is 35.4 x 35.4 m.
    Everything in that photograph - the arch, the second vault behind it, the
    cylindrical tank, the chequerboard tower, the lattice antenna, the derelict
    concrete block and four floodlight masts - therefore sits HERE, at 314 m
    right of the roll and 1 146 m along it, which is where a RWY 02 departure
    passes closest to anything on the right.

    Every height below is from that photograph by the horizon-ratio method and
    is an ESTIMATE. Positions other than the two OSM footprints are triangulated
    from the same frame and are good to about +-80 m."""
    base = Z_MIDFIELD_APRON
    P_ = P            # short alias; this function is dense
    bm = bmesh.new()
    # the barrel-vault hangar, relation/7422970: 35.4 x 35.4 m, apex 12.7 m
    vault(bm, 317.0, 353.0, 1123.0, 1159.0, springing=6.4, apex=12.7,
          base=base, along="x")
    # the second, lower vault behind it
    vault(bm, 317.0, 349.0, 1160.0, 1192.0, springing=5.8, apex=11.4,
          base=base, along="x")
    bm_to_object(bm, "SDSC_Midfield_Hangar", P_["clad"], c_mid, smooth=True,
                 roof_mat=P_["roof_pale"])
    # The narrow maroon/oxide-red returns at the corners of the frontage. In
    # refs/sdsc_field_from_sp318_2013.jpg these are slim vertical strips at each
    # end of the arch, not a painted end wall - and they are TAM-era red, which
    # is left alone here because this building is not identified as LATAM's.
    bm = bmesh.new()
    for x0, x1 in ((316.4, 319.5), (350.5, 353.6)):
        for y in (1122.6, 1159.4):
            vs = [bm.verts.new(p) for p in
                  ((x0, y, base), (x1, y, base),
                   (x1, y, base + 6.4), (x0, y, base + 6.4))]
            bm.faces.new(vs)
    bm_to_object(bm, "SDSC_Midfield_EndPanels", P_["oxide"], c_mid)
    bm = bmesh.new()          # the hangar door, west face
    box(bm, 320.0, 350.0, 1122.4, 1123.4, base, base + 7.6)
    bm_to_object(bm, "SDSC_Midfield_Door", P_["hangar_dark"], c_mid)

    # the cylindrical tank: cream body, maroon top band, ~13 m
    bm = bmesh.new()
    cx, cy, r = 392.0, 1128.0, 11.0
    rings = []
    for z in (base, base + 10.6, base + 12.2, base + 13.4):
        rings.append([bm.verts.new((cx + r * (0.86 if z > base + 12 else 1.0)
                                    * math.cos(math.radians(k * 15)),
                                    cy + r * (0.86 if z > base + 12 else 1.0)
                                    * math.sin(math.radians(k * 15)), z))
                      for k in range(24)])
    for a, b in zip(rings, rings[1:]):
        for i in range(24):
            j = (i + 1) % 24
            try:
                bm.faces.new((a[i], a[j], b[j], b[i]))
            except ValueError:
                pass
    try:
        f = bm.faces.new(rings[-1])
        bmesh.ops.triangulate(bm, faces=[f])
    except ValueError:
        pass
    bm_to_object(bm, "SDSC_Midfield_Tank", P_["wall_cream"], c_mid, smooth=True)

    # the chequerboard tower: square shaft, glazed cab, whip antennas
    C = CHEQUER
    bm = bmesh.new()
    box(bm, C["x"] - C["w"] / 2, C["x"] + C["w"] / 2,
        C["y"] - C["w"] / 2, C["y"] + C["w"] / 2, base, base + C["cab"] - 3.0)
    bm_to_object(bm, "SDSC_Chequer_Shaft", P_["chequer"], c_mid)
    bm = bmesh.new()
    box(bm, C["x"] - 4.4, C["x"] + 4.4, C["y"] - 4.4, C["y"] + 4.4,
        base + C["cab"] - 3.2, base + C["cab"])
    bm_to_object(bm, "SDSC_Chequer_Cab", P_["glass"], c_mid)
    bm = bmesh.new()
    box(bm, C["x"] - 4.8, C["x"] + 4.8, C["y"] - 4.8, C["y"] + 4.8,
        base + C["cab"], base + C["cab"] + 0.5)
    for dx in (-1.4, 0.0, 1.4):
        post(bm, C["x"] + dx, C["y"], 0.10, base + C["cab"] + 0.5,
             base + C["tip"])
    bm_to_object(bm, "SDSC_Chequer_Roof", P_["steel"], c_mid)

    # the guyed lattice antenna mast: the tallest thing in the 2013 frame
    bm = bmesh.new()
    for dx, dy in ((-0.8, -0.8), (0.8, -0.8), (0.8, 0.8), (-0.8, 0.8)):
        post(bm, 300.0 + dx, 1180.0 + dy, 0.12, base, base + 30.0)
    for k in range(9):
        z = base + 2.0 + k * 3.2
        box(bm, 299.0, 301.0, 1179.0, 1181.0, z, z + 0.16)
    for k in range(4):                    # the dipole array at the top
        z = base + 25.0 + k * 1.4
        box(bm, 296.0, 304.0, 1179.9, 1180.1, z, z + 0.14)
    bm_to_object(bm, "SDSC_Midfield_AntennaMast", P_["steel"], c_mid)

    # the derelict multi-storey concrete block (sdsc_references.md 6.9)
    bm = bmesh.new()
    box(bm, 245.0, 289.0, 1248.0, 1262.0, base, base + 9.5)
    bm_to_object(bm, "SDSC_Midfield_Derelict", P_["concrete_bare"], c_mid)
    bm = bmesh.new()                       # its blown-out window band
    for z in (base + 3.0, base + 6.2):
        for yy in (1247.8, 1262.2):
            vs = [bm.verts.new(p) for p in
                  ((245.0, yy, z), (289.0, yy, z),
                   (289.0, yy, z + 1.8), (245.0, yy, z + 1.8))]
            bm.faces.new(vs)
    bm_to_object(bm, "SDSC_Midfield_DerelictWindows", P_["hangar_dark"], c_mid)

    # the small elevated water tank at the left of the same frame, and the
    # OSM man_made=water_tower nodes elsewhere on the field
    bm = bmesh.new()
    for (wx, wy, hgt) in [(262.0, 1210.0, 14.0)] + \
            [(o["xy_m"][0], o["xy_m"][1], 16.0) for o in data()["other"]
             if o.get("man_made") == "water_tower"]:
        zb = G.graded(wx, wy)
        for dx, dy in ((-1.6, -1.6), (1.6, -1.6), (1.6, 1.6), (-1.6, 1.6)):
            post(bm, wx + dx, wy + dy, 0.16, zb, zb + hgt - 3.0)
        box(bm, wx - 3.2, wx + 3.2, wy - 3.2, wy + 3.2,
            zb + hgt - 3.0, zb + hgt)
    bm_to_object(bm, "SDSC_WaterTowers", P_["wall_cream"], c_mid)


def build_masts(P, c_furn):
    """Apron floodlight masts.

    HEIGHT IS AN ESTIMATE AND IT IS NOT SANTIAGO'S. In
    refs/sdsc_field_from_sp318_2013.jpg the lamp clusters sit within about a
    metre of the 12.7 m hangar apex beside them, which makes these short masts,
    not the 30 m high-masts an international apron carries. 16 m is that reading
    with a margin. They are still the tallest things over the ramps, which is
    what RECOGNITION.md section 2 asks of them.

    POSITIONS are inferred: evenly around each apron's edge at ~120 m."""
    bm = bmesh.new()
    placed = []
    d = data()
    for a in d["aprons"]:
        if a["area_m2"] < 5000:
            continue
        ring = dedupe_ring(a["polygon_xy_m"])
        n = len(ring)
        for i in range(n):
            ax, ay = ring[i]
            bx, by = ring[(i + 1) % n]
            dx, dy, L = unit(ax, ay, bx, by)
            t = 0.0
            while t < L:
                px, py = ax + dx * t, ay + dy * t
                if all(math.dist((px, py), q) > 120.0 for q in placed):
                    placed.append((px, py))
                t += 30.0
    h = HANGAR9
    for px, py in ((h["x0"] - 18, 1740.0), (h["x1"] + 18, 1740.0)):
        if all(math.dist((px, py), q) > 90.0 for q in placed):
            placed.append((px, py))
    for (px, py) in placed:
        zb = G.graded(px, py)
        post(bm, px, py, 0.42, zb, zb + MAST_H)
        box(bm, px - 2.2, px + 2.2, py - 0.7, py + 0.7,
            zb + MAST_H, zb + MAST_H + 1.4)
    bm_to_object(bm, "SDSC_FloodlightMasts", P["mast"], c_furn)
    print("floodlight masts:", len(placed))


def build_windsock(d, P, c_furn):
    bm = bmesh.new()
    for w in d["windsocks"]:
        px, py = w["xy_m"]
        zb = G.graded(px, py)
        post(bm, px, py, 0.20, zb, zb + 6.5)
        box(bm, px - 3.2, px + 3.2, py - 3.2, py + 3.2, zb + 0.02, zb + 0.06)
    bm_to_object(bm, "SDSC_Windsock", P["mast"], c_furn)


def build_runway_furniture(d, P, c_furn):
    """Edge lights, threshold marker boards and a four-box PAPI at each end.

    SDSC HAS NO ADC, so none of this is published. ROTAER's runway line carries
    a lighting code at each threshold and two more along the runway; the layout
    below is the standard Annex 14 one - elevated edge lights at 60 m within 3 m
    of the pavement edge, and a four-box PAPI 300 m in on the LEFT - applied by
    me. Placement detail is INFERENCE."""
    bm_l = bmesh.new()
    half = RWY_WIDTH * 0.5
    a = PAVE_S_A + 30.0
    while a < PAVE_N_A - 10.0:
        for s in (1, -1):
            x, y, z = rwy_pt(a, s * (half + 2.5), 0.02)
            post(bm_l, x, y, 0.13, z, z + 0.36)
        a += 60.0
    bm_to_object(bm_l, "SDSC_RunwayEdgeLights",
                 mat("SDSC_EdgeLightFitting", (0.420, 0.400, 0.330), 0.45),
                 c_furn)

    bm_p = bmesh.new()
    for (thr_a, d_) in ((THR02_A, +1), (THR20_A, -1)):
        for i in range(4):
            lat = 45.0 + i * 9.0
            x, y, z = rwy_pt(thr_a + d_ * 300.0, lat, 0.0)
            box(bm_p, x - 1.2, x + 1.2, y - 0.7, y + 0.7, z, z + 1.1)
    bm_to_object(bm_p, "SDSC_PAPI", P["mast"], c_furn)

    # holding-position boards, at the two mapped holding nodes
    bm_s, bm_q = bmesh.new(), bmesh.new()
    for hp in d["holding_positions"]:
        px, py = hp["xy_m"]
        zb = G.graded(px, py)
        vs = [bm_s.verts.new(p) for p in
              ((px - 1.6, py, zb + 0.6), (px + 1.6, py, zb + 0.6),
               (px + 1.6, py, zb + 1.7), (px - 1.6, py, zb + 1.7))]
        bm_s.faces.new(vs)
        for dx in (-1.2, 1.2):
            post(bm_q, px + dx, py, 0.07, zb, zb + 0.6)
    bm_to_object(bm_s, "SDSC_HoldingBoards",
                 mat("SDSC_SignRed", (0.360, 0.020, 0.016), 0.55), c_furn)
    bm_to_object(bm_q, "SDSC_HoldingPosts", P["mast"], c_furn)


def build_trees(d, P, c_veg):
    """THE TREE LINE - and at SDSC it is not a detail, it is the horizon.

    TERRAIN.md section 3: the whole 360 deg terrain horizon band spans -0.32 to
    +1.30 deg, and the near field already exceeds it at 24 of 72 azimuths. A
    terrain mesh alone renders a horizon that is too low and too clean; the
    thing that actually cuts the sky from a camera on this field is a broken
    line of large-crowned tropical trees and cane along the boundary and the
    watercourses. refs/agua_vermelha_avenida.jpg is the species reference,
    refs/mro_centro_tecnologico_2009.jpg the cane.

    Species, spacing and rows are NOT surveyed. What is data is the aerodrome
    boundary ring and the 80 mapped watercourses the rows follow."""
    import random
    rnd = random.Random(20260823)
    bm_f, bm_d, bm_t = bmesh.new(), bmesh.new(), bmesh.new()
    n = 0

    def _keep_clear(px, py):
        """No trees on a working ramp. The aerodrome boundary ring runs right
        round the MRO site, and planting it blind stands a hedge between the
        camera and the hangar line - which is the one thing on this field that
        has to read."""
        for (a, b, c, e) in ((600.0, 1130.0, 1490.0, 2075.0),      # MRO ramps
                             (215.0, 400.0, 1040.0, 1270.0),       # mid-field
                             (-300.0, -140.0, 190.0, 520.0)):      # Aeroclube
            if a < px < b and c < py < e:
                return True
        return False

    def plant(px, py, h, r, dry=False):
        nonlocal n
        bmc = bm_d if dry else bm_f
        zb = G.graded(px, py)
        post(bm_t, px, py, 0.30, zb, zb + h * 0.38)
        # a broad, slightly flattened crown - these are mango, sibipiruna and
        # eucalypt, not Santiago's poplars, and the crown is what closes the sky
        zs = [h * 0.30, h * 0.52, h * 0.74, h * 0.92, h]
        rs = [r * 0.55, r * 0.98, r, r * 0.72, 0.001]
        prev = None
        for (z, rr) in zip(zs, rs):
            vs = [bmc.verts.new((px + rr * math.cos(math.radians(k * 45)),
                                 py + rr * math.sin(math.radians(k * 45)),
                                 zb + z)) for k in range(8)]
            if prev:
                for k in range(8):
                    j = (k + 1) % 8
                    try:
                        bmc.faces.new((prev[k], prev[j], vs[j], vs[k]))
                    except ValueError:
                        pass
            prev = vs
        n += 1

    ring = dedupe_ring(d["aerodrome_boundary_xy_m"][0])
    for rep, (off_lo, off_hi, h_lo, h_hi, gap, pitch) in enumerate(
            ((16.0, 32.0, 9.0, 17.0, 0.16, 8.0),      # the main line
             (36.0, 72.0, 6.0, 13.0, 0.38, 10.0))):   # a broken second row
        for i in range(len(ring)):
            ax, ay = ring[i]
            bx, by = ring[(i + 1) % len(ring)]
            ux, uy, L = unit(ax, ay, bx, by)
            nx, ny = -uy, ux
            t = rnd.random() * 30.0
            while t < L:
                if rnd.random() < gap:       # real hedgerows have gaps
                    t += 20.0 + rnd.random() * 55.0
                    continue
                off = off_lo + rnd.random() * (off_hi - off_lo)
                side = 1.0 if rnd.random() < 0.78 else -1.0
                px = ax + ux * t + nx * off * side
                py = ay + uy * t + ny * off * side
                if abs(to_al(px, py)[1]) < 150.0 or _keep_clear(px, py):
                    t += pitch                # never in the strip or on a ramp
                    continue
                h = h_lo + rnd.random() * (h_hi - h_lo)
                plant(px, py, h, h * (0.34 + rnd.random() * 0.20),
                      dry=rnd.random() < 0.28)
                t += pitch + rnd.random() * pitch

    # riparian rows on the mapped watercourses inside 4 km - these are the ones
    # that put vegetation on the horizon in the sectors the terrain cannot.
    for w in d["water"]:
        pts = w.get("xy_m") or []
        # node-type entries carry a bare [x, y]; way-type entries a polyline
        if len(pts) < 2 or not isinstance(pts[0], (list, tuple)):
            continue
        for i in range(len(pts) - 1):
            ax, ay = pts[i][:2]
            bx, by = pts[i + 1][:2]
            if max(abs(ax), abs(ay)) > 4200:
                continue
            ux, uy, L = unit(ax, ay, bx, by)
            if L < 1.0:
                continue
            t = rnd.random() * 40.0
            while t < L:
                if rnd.random() < 0.30:
                    t += 25.0 + rnd.random() * 45.0
                    continue
                off = (rnd.random() - 0.5) * 40.0
                px = ax + ux * t - uy * off
                py = ay + uy * t + ux * off
                if (abs(to_al(px, py)[1]) < 150.0 and
                        -300 < to_al(px, py)[0] < 1900) or _keep_clear(px, py):
                    t += 20.0
                    continue
                h = 11.0 + rnd.random() * 9.0     # riparian gallery forest
                plant(px, py, h, h * (0.34 + rnd.random() * 0.20),
                      dry=rnd.random() < 0.15)
                t += 12.0 + rnd.random() * 16.0
    bm_to_object(bm_f, "SDSC_TreeLine_Foliage", P["foliage"], c_veg, smooth=True)
    bm_to_object(bm_d, "SDSC_TreeLine_FoliageDry", P["foliage2"], c_veg,
                 smooth=True)
    bm_to_object(bm_t, "SDSC_TreeLine_Trunks", P["trunk"], c_veg)
    print("trees:", n)


# ---------------------------------------------------------------------------
# parked aircraft
# ---------------------------------------------------------------------------
def airliner_proxy(name, length, span, fin_h, fus_r, gear_h, mats):
    """Low-poly airliner, nose along +X, WHEELS ON z = 0.

    Santiago's proxies sit on their bellies, which is invisible at the 0.7-2 km
    those sit at. Here the nose-in line is 800 m from a departing aircraft and
    the mid-field aeroplane is closer still, so this one stands on its gear:
    fuselage axis at gear_h + fus_r, a low-wing at belly height with dihedral,
    underslung engines and three struts."""
    hc = gear_h + fus_r
    bm = bmesh.new()
    ns = 14
    prof = [(-0.02, 0.10), (0.03, 0.55), (0.09, 0.86), (0.18, 1.00),
            (0.62, 1.00), (0.78, 0.92), (0.90, 0.66), (1.00, 0.22)]
    rings = []
    for (t, r) in prof:
        rings.append([bm.verts.new((length * (0.5 - t),
                                    fus_r * r * math.sin(2 * math.pi * i / ns),
                                    fus_r * r * math.cos(2 * math.pi * i / ns)
                                    + hc)) for i in range(ns)])
    for a, b in zip(rings, rings[1:]):
        for i in range(ns):
            j = (i + 1) % ns
            try:
                bm.faces.new((a[i], a[j], b[j], b[i]))
            except ValueError:
                pass
    hs = span * 0.5
    for s in (1, -1):
        # wing: root at the belly, tip lifted by the dihedral, swept back
        z_root, z_tip = hc - fus_r * 0.76, hc - fus_r * 0.34
        v = [bm.verts.new((length * 0.10, s * fus_r * 0.85, z_root)),
             bm.verts.new((-length * 0.18, s * fus_r * 0.85, z_root)),
             bm.verts.new((-length * 0.22, s * hs, z_tip)),
             bm.verts.new((-length * 0.10, s * hs, z_tip))]
        try:
            bm.faces.new(v)
        except ValueError:
            pass
        ex, ey = length * 0.06, s * hs * 0.34
        er = fus_r * 0.44
        ez = hc - fus_r * 1.05
        r0 = [bm.verts.new((ex + 1.9, ey + er * math.sin(2 * math.pi * i / 10),
                            ez + er * math.cos(2 * math.pi * i / 10)))
              for i in range(10)]
        r1 = [bm.verts.new((ex - 3.0, ey + er * math.sin(2 * math.pi * i / 10),
                            ez + er * math.cos(2 * math.pi * i / 10)))
              for i in range(10)]
        for i in range(10):
            j = (i + 1) % 10
            try:
                bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            except ValueError:
                pass
        # tailplane
        v = [bm.verts.new((-length * 0.40, s * fus_r * 0.5, hc + fus_r * 0.15)),
             bm.verts.new((-length * 0.50, s * fus_r * 0.5, hc + fus_r * 0.15)),
             bm.verts.new((-length * 0.50, s * span * 0.17, hc + fus_r * 0.45)),
             bm.verts.new((-length * 0.44, s * span * 0.17, hc + fus_r * 0.45))]
        try:
            bm.faces.new(v)
        except ValueError:
            pass
        # main gear
        post(bm, -length * 0.06, s * fus_r * 1.5, 0.30, 0.0, hc - fus_r * 0.8)
    post(bm, length * 0.33, 0.0, 0.24, 0.0, hc - fus_r * 0.85)   # nose gear
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(mats[0])
    for p in me.polygons:
        p.use_smooth = True
    bmf = bmesh.new()
    v = [bmf.verts.new((-length * 0.34, 0.0, hc + fus_r * 0.62)),
         bmf.verts.new((-length * 0.50, 0.0, hc + fus_r * 0.62)),
         bmf.verts.new((-length * 0.50, 0.0, fin_h)),
         bmf.verts.new((-length * 0.41, 0.0, fin_h))]
    try:
        bmf.faces.new(v)
    except ValueError:
        pass
    mef = bpy.data.meshes.new(name + "_Fin")
    bmf.to_mesh(mef); bmf.free()
    mef.materials.append(mats[1])
    return me, mef


def ga_proxy(name, mats):
    """A high-wing single, ~7.3 m long / 10.2 m span. The Aeroclube apron is
    180-280 m off a RWY 02 roll on the LEFT and is the first thing a departure
    passes; an empty one reads as a closed aerodrome."""
    bm = bmesh.new()
    L, R = 7.3, 0.55
    rings = []
    for (t, r) in ((0.0, 0.35), (0.12, 0.95), (0.55, 0.85), (1.0, 0.22)):
        rings.append([bm.verts.new((L * (0.5 - t),
                                    R * r * math.sin(2 * math.pi * i / 8),
                                    R * r * math.cos(2 * math.pi * i / 8) + 1.35))
                      for i in range(8)])
    for a, b in zip(rings, rings[1:]):
        for i in range(8):
            j = (i + 1) % 8
            try:
                bm.faces.new((a[i], a[j], b[j], b[i]))
            except ValueError:
                pass
    v = [bm.verts.new(p) for p in ((0.9, -5.1, 2.0), (0.9, 5.1, 2.0),
                                   (-0.6, 5.1, 2.0), (-0.6, -5.1, 2.0))]
    bm.faces.new(v)
    v = [bm.verts.new(p) for p in ((-2.6, -1.7, 1.35), (-2.6, 1.7, 1.35),
                                   (-3.3, 1.7, 1.35), (-3.3, -1.7, 1.35))]
    bm.faces.new(v)
    v = [bm.verts.new(p) for p in ((-2.4, 0.0, 1.5), (-3.4, 0.0, 1.5),
                                   (-3.4, 0.0, 2.9), (-2.7, 0.0, 2.9))]
    bm.faces.new(v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(mats[0])
    return me


def build_parked_aircraft(P, c_park):
    """THE NOSE-IN LINE. RECOGNITION.md section 2 ranks it with the hangars:
    "five or six airliners parked nose-in in a line along the frontage - that
    row IS the base". refs/mro_centro_tecnologico_2009.jpg is the photograph.

    Stand positions are INFERRED. OSM maps three parking positions and all three
    are at the AEROCLUBE; not one stand on the MRO ramp is surveyed
    (sdsc_references.md 6.10). What is data is the apron polygon and the hangar
    line's west face at x = 938, which together fix the row: aircraft nose east,
    tails toward the runway, on the apron between x 800 and 935.

    Types are chosen from the evidence table in sdsc_aip_survey.json: A320
    family and 767 routinely, 787 since hangar 9, A330 historically. NOT a
    777-300ER - CNN Brasil states 777 maintenance is done at Guarulhos."""
    protos = {}
    for key, (L, S_, F, R, GH) in {
            "narrow": (37.6, 35.8, 11.76, 1.98, 2.40),   # A320-family
            "wide": (54.9, 47.6, 15.85, 2.52, 3.00),     # 767-300ER
            "dream": (62.8, 60.1, 17.02, 2.85, 3.20),    # 787-9
    }.items():
        protos[key] = airliner_proxy("SDSC_Proxy_" + key, L, S_, F, R, GH,
                                     (P["ac_white"], P["latam_indigo"]))
    ga = ga_proxy("SDSC_Proxy_GA", (P["ga_white"], P["ga_trim"]))

    n = 0

    def place(key, x, y, heading_deg, tag, z=Z_MRO_PLATFORM):
        nonlocal n
        me, mef = protos[key]
        ob = bpy.data.objects.new("SDSC_AC_%s" % tag, me)
        ob.location = (x, y, z + Z_APRON)
        ob.rotation_euler = (0.0, 0.0, math.radians(90.0 - heading_deg))
        c_park.objects.link(ob)
        fin = bpy.data.objects.new("SDSC_ACFin_%s" % tag, mef)
        fin.parent = ob
        c_park.objects.link(fin)
        n += 1

    # THE ROW. Two aeroplanes nose-in on the hangar face at x = 931 - tails to
    # the runway, which is the side a RWY 02 departure sees - and four more on
    # the apron's four northern lobes, which run north-south and are what the
    # mapped polygon actually offers. All six are clear of way/708700156, the
    # 44 x 42 m hangar that stands in the middle of that apron.
    for i, (x, y) in enumerate(((904.0, 1790.0), (900.0, 1832.0))):
        place("narrow" if i else "wide", x, y, 91.0, "ROW%d" % i)
    for i, (x, y, k) in enumerate(((870.0, 1950.0, "wide"),
                                   (878.0, 1888.0, "narrow"),
                                   (980.0, 1958.0, "narrow"),
                                   (980.0, 2004.0, "narrow"))):
        place(k, x, y, 181.0, "N%d" % i)
    # a 787 on hangar 9's stand - the reason hangar 9 exists
    h = HANGAR9
    place("dream", (h["x0"] + h["x1"]) * 0.5, 1725.0, 181.0, "H9")

    # the Aeroclube: light aircraft on the little apron, 180-280 m off the roll
    for i, (x, y) in enumerate(((-212.0, 456.0), (-212.0, 474.0),
                                (-212.0, 492.0), (-206.0, 318.0),
                                (-206.0, 288.0))):
        ob = bpy.data.objects.new("SDSC_GA_%d" % i, ga)
        ob.location = (x, y, Z_AEROCLUBE_APRON + Z_APRON)
        ob.rotation_euler = (0.0, 0.0, math.radians(90.0 - 271.0))
        c_park.objects.link(ob)
        n += 1
    # and one widebody on the mid-field apron, which is what the 2013
    # photograph shows parked there
    place("wide", 300.0, 1140.0, 181.0, "MID", z=Z_MIDFIELD_APRON)
    print("parked aircraft:", n)


# ---------------------------------------------------------------------------
# lighting
# ---------------------------------------------------------------------------
def build_light(P, c_light):
    scn = bpy.context.scene
    world = bpy.data.worlds.new("SDSC_World")
    scn.world = world
    world.use_nodes = True
    nt = world.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputWorld"); out.location = (400, 0)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.location = (200, 0)
    # Sun and sky are balanced against each other NUMERICALLY, the way Santiago
    # does it: a white lambertian card is rendered under the rig and the
    # horizontal irradiance split measured. The first rig here (sun 13.0, world
    # 0.18) gave 1.53:1 direct:diffuse; these values give about 2:1, which is
    # what a 15 deg sun through smoky air actually does.
    bg.inputs["Strength"].default_value = 0.15
    sky = nt.nodes.new("ShaderNodeTexSky"); sky.location = (-100, 0)
    configure_sky(sky)
    nt.links.new(sky.outputs[0], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])

    lamp = bpy.data.lights.new("SDSC_Sun", "SUN")
    lamp.energy = 15.0
    lamp.angle = math.radians(0.545)
    lamp.color = (1.0, 0.840, 0.672)       # 15 deg elevation, thick air mass
    ob = bpy.data.objects.new("SDSC_Sun", lamp)
    # A sun lamp shines along its local -Z; for euler (rx, 0, rz) that is
    # (-sin rx sin rz, sin rx cos rz, -cos rx), so rx = 90 - elevation and
    # rz = 180 - azimuth put it at (elevation, compass azimuth).
    ob.rotation_euler = (math.radians(90.0 - SUN_ELEV_DEG), 0.0,
                         math.radians(180.0 - SUN_AZIM_DEG))
    c_light.objects.link(ob)


# ---------------------------------------------------------------------------
# terrain
# ---------------------------------------------------------------------------
def build_terrain(stride_mid=1, stride_far=3, stride_near=1):
    global G
    wipe()
    G = Ground()
    sys.path.insert(0, HERE)
    import load_terrain as lt
    c = coll("SDSC_Terrain")
    layer = bpy.context.view_layer.active_layer_collection
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children[c.name]

    m = lt._meta()["grids"]
    g60, g30 = m["terrain_sdsc_60m"], m["terrain_sdsc_near_30m"]
    lt.build("terrain_sdsc_far_180m", stride=stride_far,
             obj_name="SDSC_Terrain_Far",
             mask_inner=(g60["x_min_m"], g60["x_max_m"],
                         g60["y_min_m"], g60["y_max_m"]))
    lt.build("terrain_sdsc_60m", stride=stride_mid, obj_name="SDSC_Terrain_Mid",
             mask_inner=(g30["x_min_m"], g30["x_max_m"],
                         g30["y_min_m"], g30["y_max_m"]))
    lt.build("terrain_sdsc_near_30m", stride=stride_near,
             obj_name="SDSC_Terrain_Near")
    bpy.context.view_layer.active_layer_collection = layer

    grade_aerodrome()
    m_t = terrain_material()
    for ob in c.objects:
        ob.data.materials.append(m_t)
    print("terrain polys:", sum(len(o.data.polygons) for o in c.objects))


def grade_aerodrome():
    """Push the near tier onto the SAME graded surface the field is built on,
    then blend back to the raw DEM outside.

    Santiago flattens the aerodrome to one z, because Santiago's aerodrome IS
    flat. Here the target is graded(x, y) - 0.8: the published runway grade, the
    measured MRO platform, and the real fall between them. Flattening this field
    to a constant would put the MRO 35 m in the air or the runway 35 m under."""
    ob = bpy.data.objects.get("SDSC_Terrain_Near")
    if ob is None:
        return
    ring = dedupe_ring(data()["aerodrome_boundary_xy_m"][0])
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    inner, outer = 500.0, 2600.0
    me = ob.data
    moved = 0
    for v in me.vertices:
        dx = max(x0 - v.co.x, 0.0, v.co.x - x1)
        dy = max(y0 - v.co.y, 0.0, v.co.y - y1)
        dist = math.hypot(dx, dy)
        if dist >= outer:
            continue
        t = 0.0 if dist <= inner else (dist - inner) / (outer - inner)
        t = t * t * (3 - 2 * t)
        target = G.graded(v.co.x, v.co.y) - 0.8
        v.co.z = v.co.z * t + target * (1.0 - t)
        moved += 1
    print("graded terrain vertices:", moved)


def terrain_material():
    """The plateau: red latosol under cane and pasture, going hazier and cooler
    with distance. There is no rock and no snow at SDSC - the whole 240 km plate
    is farmland - so the elevation ramp Santiago needs is replaced by a distance
    ramp that keeps the far ground from reading as a green wall."""
    m, nt, out, bsdf = _blank("SDSC_TerrainGround", 0.94)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1000, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-820, -200)
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    cx = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", sep.outputs["X"], 620.0))
    cy = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", sep.outputs["Y"], 520.0))
    cell = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(cx, cell.inputs[0])
    nt.links.new(cy, cell.inputs[1])
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"
    nt.links.new(cell.outputs[0], wn.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-380, 0)
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    stops = [(0.00, (0.072, 0.096, 0.032)),
             (0.28, (0.124, 0.130, 0.056)),
             (0.50, (0.162, 0.142, 0.074)),
             (0.70, (0.172, 0.086, 0.046)),
             (0.86, (0.096, 0.096, 0.042))]
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[1][0], (*stops[1][1], 1)
    for pos, col in stops[2:]:
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    nt.links.new(wn.outputs["Value"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    return m


# ---------------------------------------------------------------------------
ASSET_CATALOGS = {
    "c4a71e30-2b5d-4f8a-9d11-7e3a5c2d0021": "SDSC Scenery",
    "c4a71e30-2b5d-4f8a-9d11-7e3a5c2d0022": "SDSC Scenery/Collections",
    "c4a71e30-2b5d-4f8a-9d11-7e3a5c2d0023": "SDSC Scenery/Furniture",
    "c4a71e30-2b5d-4f8a-9d11-7e3a5c2d0024": "SDSC Scenery/Markings",
    "c4a71e30-2b5d-4f8a-9d11-7e3a5c2d0025": "SDSC Scenery/Aircraft",
    "c4a71e30-2b5d-4f8a-9d11-7e3a5c2d0026": "SDSC Scenery/Materials",
}


def write_catalogs():
    path = os.path.join(HERE, "blender_assets.cats.txt")
    with open(path, "w") as fh:
        fh.write("# This is an Asset Catalog Definition file for Blender.\n")
        fh.write("VERSION 1\n\n")
        for uid, tree in ASSET_CATALOGS.items():
            fh.write("%s:%s:%s\n" % (uid, tree, tree.split("/")[-1]))
    print("wrote", path)


def _mark(datablock, catalog_uuid, description):
    try:
        datablock.asset_mark()
    except Exception as exc:                       # pragma: no cover
        print("asset_mark failed for", datablock.name, exc)
        return
    datablock.asset_data.catalog_id = catalog_uuid
    datablock.asset_data.description = description
    try:
        with bpy.context.temp_override(id=datablock):
            bpy.ops.ed.lib_id_generate_preview()
    except Exception:
        pass


def mark_assets():
    write_catalogs()
    cats = list(ASSET_CATALOGS)
    for name, note in (
            ("SDSC_Field", "Whole SDSC aerodrome: sloping runway, taxiways, "
                           "aprons, LATAM MRO, hangar 9, mid-field cluster, "
                           "Aeroclube, tree line. Link, do not append."),
            ("SDSC_Light", "Sun + sky for 26 September 17:00 local, "
                           "15.1 deg / 274.5 deg."),
            ("SDSC_Anchors", "SDSC_02_Threshold and friends: +Y points down "
                             "the take-off track. z is the runway surface."),
            ("SDSC_LATAM_MRO", "The MRO: hangar line, hangar 9 (declared "
                               "inference), fascia band, mark, perimeter."),
            ("SDSC_Midfield", "The mid-field cluster from the 2013 photograph."),
            ("SDSC_Runway", "RWY 02/20, 1720 x 45 m, 0.62% down to the north, "
                            "thresholds displaced 52 / 48 m.")):
        c = bpy.data.collections.get(name)
        if c:
            _mark(c, cats[1], note)
    for name, cat, note in (
            ("SDSC_FloodlightMasts", cats[2],
             "16 m apron floodlight masts - height estimated off the 2013 "
             "photograph, NOT Santiago's 30 m"),
            ("SDSC_TreeLine_Foliage", cats[2],
             "perimeter and riparian tree line - at SDSC this IS the horizon"),
            ("SDSC_Chequer_Shaft", cats[2],
             "the orange/white chequerboard tower, unidentified"),
            ("SDSC_RunwayMarkings", cats[3],
             "ICAO Annex 14 pattern applied to a 45 m runway with 52/48 m "
             "displaced thresholds. SDSC has no ADC - this is an estimate."),
            ("SDSC_Hangar9", cats[1],
             "HANGAR 9 - declared inference. No published dimension, no OSM "
             "footprint. Sized from the 787-9 it holds."),
            ("SDSC_AC_ROW0", cats[4], "low-poly 767-300ER proxy, LATAM"),
            ("SDSC_AC_H9", cats[4], "low-poly 787-9 proxy, LATAM")):
        ob = bpy.data.objects.get(name)
        if ob:
            _mark(ob, cat, note)
    for m in bpy.data.materials:
        if m.name.startswith("SDSC_"):
            _mark(m, cats[5], "SDSC scenery material (haze term included)")


def main():
    args = argv_after_dashdash()
    if "--terrain" in args:
        build_terrain()
        path = os.path.join(HERE, "sdsc_terrain.blend")
    else:
        build_field()
        mark_assets()
        path = os.path.join(HERE, "sdsc_field.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("saved", path, os.path.getsize(path) // 1024, "kB")


if __name__ == "__main__":
    main()
