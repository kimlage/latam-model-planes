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
if HERE not in sys.path:
    sys.path.insert(0, HERE)

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

# ---------------------------------------------------------------------------
# THE SURROUND. Phase 2 left roads, water and landuse "in the plan and not the
# build, as at Santiago". At Santiago that was defensible - the city is 15 km
# away and the farmland grid carried the middle distance. Here the field is
# 1.7 x 2.2 km and the surroundings fill the frame of every aerial, so the same
# omission renders an aerodrome floating on coloured ground.
#
# Everything below is built from sdsc_osm.json. What is DATA: the centreline of
# every road, the course of every stream, the outline of every water body, the
# 35 landuse polygons and their crop/residential classification, and OSM's own
# `surface` tag (paved vs unpaved), which in this landscape is the difference
# between a black line and a bright red one. What is INFERENCE: every WIDTH
# (OSM carries no width or lanes tag on any of these ways), the depth of the
# streams, and everything in POWERLINE / VILLAGE below.
# ---------------------------------------------------------------------------
ROAD_WIDTH = {          # metres, ESTIMATED - no width or lanes tag anywhere
    "motorway": 8.5,          # the SP-318; OSM maps its two carriageways apart
    "motorway_link": 6.0,
    "trunk": 8.0,
    "primary": 7.5,
    "secondary": 7.0,         # Avenida Bela Cintra, the village spine
    "secondary_link": 5.5,
    "tertiary": 6.5,          # the SCA municipal roads
    "tertiary_link": 5.0,
    "unclassified": 5.5,      # 78 km of it, half unpaved - the farm grid
    "residential": 5.5,
    "service": 4.0,
    "track": 3.5,
}
ROAD_SKIP = {"footway", "path", "steps", "cycleway", "pedestrian"}

# Powerlines. DECLARED INFERENCE as to line, spacing and height; their
# PRESENCE is photographed - refs/sdsc_field_from_sp318_2013.jpg has a
# conductor strung right across the top of the frame, shot from the SP-318
# verge, and refs/agua_vermelha_avenida.jpg shows the standard Brazilian rural
# distribution pole: a square concrete section about 9 m out of the ground, a
# single crossarm, three phases and a neutral, with a street-light bracket in
# the village. OSM maps no power line in this extract, so the ROUTE is taken
# from the road verges, which is where these actually run in the region.
POLE_H = 9.2
POLE_SPACING = 52.0
POWERLINE_ROADS = ("motorway", "secondary", "tertiary")   # the ones with poles
POWERLINE_REACH = 3000.0      # the band a camera can still resolve them in

# Agua Vermelha. The district the base sits in, and a VILLAGE, not empty land.
# OSM gives 15 building footprints, two residential landuse polygons totalling
# 75 201 m2, and the street grid. Fifteen houses in 7.5 ha is an under-mapping,
# not a hamlet: refs/agua_vermelha_avenida.jpg shows a continuous street
# frontage of single-storey rendered houses under red pantile, with a heavy
# street canopy. The mapped buildings and the mapped streets are DATA; the
# INFILL houses along those streets are INFERENCE, and this is the constant.
VILLAGE_INFILL = True
VILLAGE_LOT_PITCH = 17.0      # metres of frontage per house - ESTIMATE
VILLAGE_SETBACK = 6.5
VILLAGE_MAX_HOUSES = 300      # ~300 m2 a lot over 75 201 m2 of mapped
                              # residential land - ESTIMATE, and a ceiling

# ---------------------------------------------------------------------------
# THE OPERATION. This is a working MRO - ~2 000 people, 22 workshops, ~270
# aircraft a year, 16 in work at once (phase 1) - and phase 2 built none of it.
# Whole aeroplanes parked nose-in on an empty slab is what a MODEL of a base
# looks like; a heavy-check base has aircraft that are visibly APART, yellow
# steel standing round them, and somewhere for two thousand people to park.
#
# What is DATA here, and it is more than expected:
#   * The CAR PARKS' geometry. OSM maps the MRO's landside circulation as
#     `service` and short `unclassified` ways - and among them are four
#     unmistakable AISLE GRIDS: parallel 60-120 m runs on a ~30 m pitch inside
#     closed loops. That layout is a car park and nothing else. The slabs below
#     are laid on those mapped aisles. The CARS in them are inference.
#   * The MAINTENANCE KIT IS YELLOW. refs/mro_centro_manutencao_2006.jpg and
#     refs/mro_centro_tecnologico_2010.jpg are both taken inside a TAM hangar
#     on this site and both are full of yellow tubular access towers, yellow
#     wing docks, yellow rolling stairs and RED tool trolleys. That palette is
#     photographed, not chosen.
#   * AIRCRAFT APART. refs/mro_centro_tecnologico_2010.jpg is an A320 with the
#     fan cowls open and the engine core exposed, stands under the wing and a
#     ladder at the nose door. refs/mro_centro_tecnologico_2009.jpg shows, on
#     the APRON, a stripped fuselage with a tall tan/yellow dock built round it.
#   * CONTAINERS on the apron: white ISO boxes in the 2009 frame, a dark-red
#     skip in the 2010 one.
# What is INFERENCE: every position of every vehicle, the count and mix of the
# GSE, the car count, the gate and guard house, and the tug's colours. No
# photograph of LATAM's Sao Carlos ground fleet was found.
# ---------------------------------------------------------------------------
CARPARK_AISLE_MIN_M = 25.0    # shorter than this is a kerb stub, not an aisle
CARPARK_AISLE_MAX_M = 400.0   # a mapped service way longer than this is a road
CARPARK_HALF_W = 11.0         # aisle + a 5 m bay each side - ESTIMATE
CARPARK_BAY_PITCH = 2.65      # ESTIMATE, the Brazilian standard bay is 2.4-2.5
CARPARK_OCCUPANCY = 0.72      # ESTIMATE: a day shift on a full ramp

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


_PAD = None


def pad_box():
    """The aerodrome ground pad's own extent, exactly as build_ground lays it:
    the OSM boundary bbox grown by 400 m. Outside it the visible ground is the
    cane sheet, not the graded pad."""
    global _PAD
    if _PAD is None:
        ring = dedupe_ring(data()["aerodrome_boundary_xy_m"][0])
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        _PAD = (min(xs) - 400.0, max(xs) + 400.0,
                min(ys) - 400.0, max(ys) + 400.0)
    return _PAD


def surface_z(x, y, dz=0.0):
    """Height of the ground a camera actually SEES, anywhere in the scene.

    Two surfaces meet here and they are not the same function. Inside the pad
    the ground is `graded(x, y)` with the 0.8 m rim taper build_ground applies;
    outside it the ground is the cane sheet at `dem + 0.45` (build_ground, and
    the +0.45 is the measured clearance from the cane/terrain fix). Everything
    in the SURROUND - roads, watercourses, field margins, poles, village -
    has to sit on whichever one is under it, and cross between them without a
    step. Weighting the two by the pad's own taper `t` does that: at the rim
    t = 1 and this returns the cane sheet exactly, 200 m in t = 0 and it
    returns the graded pad exactly.

    Using gz() instead would bury every surround object 1.25 m at the pad rim
    and leave the roads floating where the pad tapers - which is the same class
    of mistake as the cane sheet fighting the terrain."""
    x0, x1, y0, y1 = pad_box()
    if x0 <= x <= x1 and y0 <= y <= y1:
        e = min(x - x0, x1 - x, y - y0, y1 - y)
        t = _smoothstep(1.0 - e / 200.0)
        return (G.graded(x, y) - 0.8 * t) * (1.0 - t) + \
               (G.dem(x, y) + 0.45) * t + dz
    return G.dem(x, y) + 0.45 + dz


def resample(pts, step):
    """Split a polyline so no segment is longer than `step`. A 500 m chord
    across this plateau sinks 3-6 m into the ground it is supposed to lie on;
    every surround ribbon is resampled before it is draped."""
    out = []
    for i in range(len(pts) - 1):
        ax, ay = pts[i][0], pts[i][1]
        bx, by = pts[i + 1][0], pts[i + 1][1]
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L / step))
        for k in range(n):
            t = k / n
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    if pts:
        out.append((pts[-1][0], pts[-1][1]))
    return out


def drape(bm, pts, width, dz, zfun=None):
    """A polyline as a flat strip lying on `zfun` (surface_z by default)."""
    zf = zfun or surface_z
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
        nx_, ny_ = -dy, dx
        for side, store in ((1, left), (-1, right)):
            px, py = x + side * nx_ * h, y + side * ny_ * h
            store.append(bm.verts.new((px, py, zf(px, py, dz))))
    for i in range(len(pts) - 1):
        try:
            bm.faces.new((right[i], right[i + 1], left[i + 1], left[i]))
        except ValueError:
            pass


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

        # --- the surround ----------------------------------------------
        # OSM's `surface` tag decides which of these two a road gets, and in
        # this landscape that is the difference between a black line and a
        # bright red one. Half the 78 km of unclassified road here is unpaved.
        road_paved=mat("SDSC_RoadAsphalt", (0.048, 0.048, 0.046), 0.78),
        road_dirt=mat("SDSC_RoadDirt", (0.290, 0.132, 0.062), 0.92),
        water=mat("SDSC_Water", (0.020, 0.036, 0.042), 0.14, metal=0.10),
        wetland=mat("SDSC_Wetland", (0.070, 0.086, 0.048), 0.88),
        crop_a=mat("SDSC_CropCane", (0.086, 0.112, 0.036), 0.92),
        crop_b=mat("SDSC_CropCaneDry", (0.150, 0.146, 0.062), 0.92),
        crop_c=mat("SDSC_CropTilled", (0.196, 0.092, 0.046), 0.94),
        crop_d=mat("SDSC_CropPasture", (0.128, 0.130, 0.058), 0.92),
        # yard-and-garden ground: dusty tan with the latosol showing
        margin=mat("SDSC_VillageYard", (0.152, 0.116, 0.062), 0.94),
        pole=mat("SDSC_PoleConcrete", (0.118, 0.116, 0.112), 0.90),
        wire=mat("SDSC_Conductor", (0.020, 0.020, 0.021), 0.65),
        house_a=mat("SDSC_HouseRenderA", (0.360, 0.348, 0.310), 0.86),
        house_b=mat("SDSC_HouseRenderB", (0.320, 0.286, 0.226), 0.86),

        # --- the operation ---------------------------------------------
        # refs/mro_centro_manutencao_2006.jpg and _tecnologico_2010.jpg: the
        # access towers, wing docks and rolling stairs on this site are YELLOW
        # and the tool trolleys are RED. Photographed, not chosen.
        dock_yellow=mat("SDSC_DockYellow", (0.320, 0.196, 0.020), 0.64),
        cart_red=mat("SDSC_ToolCartRed", (0.300, 0.028, 0.024), 0.60),
        gse_white=mat("SDSC_GSEWhite", (0.480, 0.482, 0.478), 0.55),
        gse_yellow=mat("SDSC_GSEYellow", (0.410, 0.250, 0.020), 0.58),
        gse_dark=mat("SDSC_GSEDark", (0.045, 0.046, 0.050), 0.60),
        container=mat("SDSC_Container", (0.300, 0.300, 0.292), 0.72),
        container_b=mat("SDSC_ContainerRust", (0.150, 0.062, 0.040), 0.86),
        carpark=aged_pavement_material("SDSC_CarparkAsphalt",
                                       (0.062, 0.061, 0.058),
                                       (0.098, 0.094, 0.086),
                                       (0.042, 0.041, 0.040), 0.030, 0.84),
        car_white=mat("SDSC_CarWhite", (0.470, 0.472, 0.470), 0.34),
        car_silver=mat("SDSC_CarSilver", (0.210, 0.214, 0.220), 0.32),
        car_dark=mat("SDSC_CarDark", (0.026, 0.027, 0.030), 0.34),
        car_red=mat("SDSC_CarRed", (0.230, 0.026, 0.022), 0.34),
        glass_car=mat("SDSC_CarGlass", (0.030, 0.034, 0.040), 0.18,
                      metal=0.30),
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
    c_road = coll("SDSC_Roads", c_root)
    c_water = coll("SDSC_Water", c_root)
    c_ops = coll("SDSC_Operations", c_root)
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
    # ---- the surround: 330 roads, 80 water features, 35 landuse polygons,
    #      the village and the poles. All of it was already in sdsc_osm.json.
    build_landuse(d, P, c_ground)
    build_roads(d, P, c_road)
    build_water(d, P, c_water)
    build_village(d, P, c_bldg, c_veg, c_ground)
    build_powerlines(d, P, c_furn)
    build_cane_yards(P, c_bldg)
    build_trees(d, P, c_veg)
    # ---- the operation: what makes it a working MRO and not a diagram
    build_parked_aircraft(P, c_park)
    build_maintenance(P, c_ops)
    build_gse(d, P, c_ops)
    build_containers(d, P, c_ops)
    build_carparks(d, P, c_ops)
    build_gate(P, c_mro)
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
    # STEP AND HEIGHT ARE BOTH MEASURED, and they were both wrong. This sheet
    # and the terrain mesh are two samplings of the SAME DEM - this one linear
    # between its own nodes, the terrain one at 30 m - so wherever the coarse
    # chord dips under the fine surface the TERRAIN material shows through and
    # the far field renders as a mottle of two different farmland shaders. At
    # the shipped 120 m / -0.55 that happened over 39% of the ring, in patches
    # up to a kilometre across, and it is plainly visible in the aerial tour:
    # a hard-edged rectangle of the wrong green at 4-7 km. Sampled over 30 000
    # random points inside the inner ring:
    #
    #     step  offset   terrain wins   worst
    #      120   -0.55       39.3%     -13.80 m
    #       60   -0.55       21.0%      -5.99 m
    #       40   -0.55       10.6%      -3.67 m
    #       60   +0.45        2.6%      -4.99 m     <- shipped
    #       40   +0.25        0.9%      -2.87 m
    #
    # 60 m and +0.45 leaves the cane 1.25 m clear of the terrain, which at the
    # 1-9 km this ring is seen from is 0.02 deg, and costs the field 38 000
    # faces it can easily afford. The alternative - keeping 120 m and raising
    # the sheet until it always wins - needs +14 m, which is a cliff at the
    # aerodrome-pad boundary.
    for tag, reach, step2, mat_ in (("Inner", 4200.0, 60.0, P["cane"]),
                                    ("Outer", 9000.0, 200.0, P["cane"])):
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
                row.append(bm.verts.new((x, y, G.dem(x, y) + 0.45)))
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
    # facing = -1, and it is not cosmetic. The lockup is laid out along world
    # +X * facing; this wall's outward normal is NORTH, and an observer standing
    # north of it sees world +X on their LEFT. Built with facing=+1 the wordmark
    # renders MIRRORED - which is what it did until the hangar-9 tow clip put a
    # camera close enough to read it. The west-facing run below has the opposite
    # handedness and was right all along, which is why the two disagreed.
    place_wordmark(P, c_mro, "SDSC_Hangar9", face_y=h["y1"] + 0.7,
                   x_centre=cx, z_base=band_z0 + 0.8, cap_m=3.2, facing=-1)


def place_wordmark(P, collection, tag, face_y, x_centre, z_base, cap_m,
                   facing=+1):
    """The LATAM lockup on a north- or south-facing fascia, from the OFFICIAL
    SVG via latam_livery_kit - never a lookalike font, the same rule the fleet
    livery follows.

    `facing` is the handedness, NOT the wall's normal: the lockup runs along
    world +X * facing. A wall whose outward normal is NORTH needs facing = -1
    (an observer north of it sees +X on their left); a SOUTH-facing wall needs
    +1. Getting it wrong renders the wordmark mirrored and nothing else changes,
    which is why it survived until a camera got close enough to read it.

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
            # THE GATE. Four mapped service ways - way/510750444, /445, /446
            # and /510750640 - cross this run at x = 914-930, which is where
            # the landside road really enters the airside, so the wall opens
            # there rather than wherever looked convenient. build_gate stands
            # the leaves, the guard house and the boom in the hole.
            if abs(y0 - 1545.0) < 1.0 and 906.0 < x0 < 938.0:
                continue
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
        # surface_z, not graded: the riparian rows below run out to 4.2 km,
        # where the ground a camera sees is the cane sheet and not the pad.
        zb = surface_z(px, py)
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

    # Riparian rows on the mapped watercourses inside 4 km - these are the ones
    # that put vegetation on the horizon in the sectors the terrain cannot.
    #
    # THIS LOOP NEVER RAN. It read `w["xy_m"]`, and a way-type water feature in
    # sdsc_osm.json carries its polyline under `polygon_xy_m`; `xy_m` exists on
    # exactly one of the 80 entries, the Agua Vermelha waterfall NODE, which is
    # then correctly skipped for having no second point. So every tree in this
    # scene came from the aerodrome boundary ring and there was no gallery
    # forest on any watercourse at all - which is a real part of why the
    # surroundings read as empty. Fixed with the rest of the water.
    for w in d["water"]:
        pts = w.get("polygon_xy_m") or w.get("xy_m") or []
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
                if rnd.random() < 0.44:
                    t += 30.0 + rnd.random() * 60.0
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
                t += 19.0 + rnd.random() * 22.0
    bm_to_object(bm_f, "SDSC_TreeLine_Foliage", P["foliage"], c_veg, smooth=True)
    bm_to_object(bm_d, "SDSC_TreeLine_FoliageDry", P["foliage2"], c_veg,
                 smooth=True)
    bm_to_object(bm_t, "SDSC_TreeLine_Trunks", P["trunk"], c_veg)
    print("trees:", n)


# ---------------------------------------------------------------------------
# THE SURROUND - roads, water, landuse, the village, the poles
#
# Phase 2's own report: "roads, water and landuse tint are in the plan and not
# the build, as at Santiago". The plan check (checks/plan_built.png against
# sdsc_osm_plan.png) has been carrying that line as a known gap since. It is
# closed here, and the reason it had to be is scale: Santiago's city is 15 km
# out and its farmland grid carries the middle distance, but SDSC is a 1.7 km
# field whose surroundings are IN the frame of every aerial. 330 roads, 80
# water features and 35 landuse polygons were already sitting in sdsc_osm.json.
# ---------------------------------------------------------------------------
def obox(bm, cx, cy, z0, z1, length, width, hdg_deg):
    """A box of given plan size, rotated to `hdg_deg` (0 = +Y = north)."""
    a = math.radians(hdg_deg)
    ux, uy = math.sin(a), math.cos(a)          # along the length
    px, py = uy, -ux                           # across it
    hl, hw = length * 0.5, width * 0.5
    c = [(cx + ux * sl * hl + px * sw * hw, cy + uy * sl * hl + py * sw * hw)
         for (sl, sw) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    v = [bm.verts.new((x, y, z0)) for x, y in c] + \
        [bm.verts.new((x, y, z1)) for x, y in c]
    for f in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
              (4, 5, 6, 7)):
        try:
            bm.faces.new([v[i] for i in f])
        except ValueError:
            pass


UNPAVED = {"unpaved", "dirt", "gravel", "ground", "compacted", "sand",
           "earth", "grass", "fine_gravel"}


def build_roads(d, P, c_road):
    """330 mapped ways, 162 km of them, every one from OpenStreetMap.

    The SP-318 (Rodovia Engenheiro Thales de Lorena Peixoto Junior) is the
    important one: it runs NNW-SSE about 620-700 m west of the runway and it is
    where refs/sdsc_field_from_sp318_2013.jpg - the best photograph in this
    survey - was taken from. Its two carriageways are mapped separately, which
    is why 15.35 km of `motorway` covers only ~7 km of road.

    DATA: the centreline of every way, its highway class, and OSM's `surface`
    tag. That last one is not cosmetic here - 35 of the 101 unclassified ways
    are tagged unpaved, and an unpaved road in this soil is a BRIGHT RED-ORANGE
    line across a green landscape, not a black one. It is the single most
    characteristic thing about the road network of the region seen from the air.
    INFERENCE: every width (no way here carries a width or lanes tag), and the
    reading of an untagged surface as paved."""
    bm_p, bm_d = bmesh.new(), bmesh.new()
    km_p = km_d = 0.0
    n = 0
    for r in d["roads"]:
        pts = r.get("polygon_xy_m")
        if not pts or len(pts) < 2:
            continue                       # node features: crossings, stops
        hw = r.get("highway")
        if hw in ROAD_SKIP:
            continue
        w = ROAD_WIDTH.get(hw)
        if w is None:
            continue
        unpaved = (r.get("surface") or "").lower() in UNPAVED
        pts = resample(pts, 30.0)
        drape(bm_d if unpaved else bm_p, pts, w, 0.07)
        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        if unpaved:
            km_d += L / 1000.0
        else:
            km_p += L / 1000.0
        n += 1
    bm_to_object(bm_p, "SDSC_RoadsPaved", P["road_paved"], c_road, smooth=True)
    bm_to_object(bm_d, "SDSC_RoadsUnpaved", P["road_dirt"], c_road, smooth=True)
    print("roads: %d ways  %.1f km paved  %.1f km unpaved" % (n, km_p, km_d))


def build_water(d, P, c_water):
    """80 mapped water features: 71 stream centrelines totalling 62 km, seven
    `natural=water` bodies and one wetland.

    Two of them matter to the shots. The RIBEIRAO DAS ARARAS runs north-south
    down the east side of the field, 300-900 m outside the fence, and it is the
    corrego the ground falls 40 m/km into - the fall RECOGNITION.md and the tour
    both point at. And way/154922934 is a 71 772 m2 reservoir at (1097, 1137),
    a kilometre south-west of the MRO and in frame for most of the aerial tour;
    it was simply not built.

    DATA: every centreline, every shoreline, the `waterway`/`natural` class.
    INFERENCE: the WIDTH of each stream (no width tag anywhere) and the water
    LEVEL of each body, which is taken as the 40th percentile of the ground
    under its own shoreline. The Copernicus DEM is a 30 m surface model and
    does not resolve a channel, so the streams are laid ON the ground rather
    than cut into it: at the 0.3-8 km these are seen from, a dark meandering
    line is what a watercourse looks like either way."""
    bm_s, bm_b, bm_w = bmesh.new(), bmesh.new(), bmesh.new()
    km = 0.0
    nb = 0
    for w in d["water"]:
        pts = w.get("polygon_xy_m")
        if not pts or len(pts) < 2:
            continue
        if w.get("waterway") == "stream":
            name = w.get("name") or ""
            width = 7.0 if name.startswith("Ribeir") else \
                (5.0 if name else 3.5)             # ESTIMATE, see docstring
            pts = resample(pts, 30.0)
            drape(bm_s, pts, width, 0.10)
            km += sum(math.dist(pts[i], pts[i + 1])
                      for i in range(len(pts) - 1)) / 1000.0
        elif "area_m2" in w:
            ring = dedupe_ring(pts)
            if len(ring) < 3:
                continue
            zs = sorted(surface_z(x, y) for x, y in ring)
            level = zs[int(len(zs) * 0.40)] + 0.10
            bm = bm_w if w.get("natural") == "wetland" else bm_b
            vs = [bm.verts.new((x, y, level)) for x, y in ring]
            try:
                f = bm.faces.new(vs)
                bmesh.ops.triangulate(bm, faces=[f])
                nb += 1
            except ValueError:
                pass
    bm_to_object(bm_s, "SDSC_Streams", P["water"], c_water, smooth=True)
    bm_to_object(bm_b, "SDSC_WaterBodies", P["water"], c_water)
    bm_to_object(bm_w, "SDSC_Wetland", P["wetland"], c_water)
    print("water: %.1f km of stream, %d bodies" % (km, nb))


def _ring_hit(ring, px, py):
    inside = False
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        if (y0 > py) != (y1 > py):
            xx = x0 + (py - y0) * (x1 - x0) / (y1 - y0)
            if px < xx:
                inside = not inside
    return inside


def build_landuse(d, P, c_ground):
    """35 mapped landuse polygons - and the reason they are worth building is
    that they replace GUESSED field boundaries with SURVEYED ones.

    build_ground's cane surround gets its parcels from a procedural cell
    pattern, because when it was written nothing better was in the build. But
    sdsc_osm.json carries the real thing: 19 km2 of named fazendas - Sao
    Roberto, Chile, Palmeiras, Santo Antonio, do Saltinho, Bela Vista - with
    their actual boundaries. From 230-700 m up, mapped parcel edges are what
    separates a landscape from a texture.

    HOW THEY ARE LAID, and it is the one thing that could have gone wrong.
    The cane sheet and the terrain mesh are two samplings of the same DEM and
    they fought until baba4e6 measured the fight and biased the sheet 1.25 m
    clear. Dropping a triangulated 5.7 km2 polygon on top would restart it -
    a long chord across a rolling parcel sinks metres below the 60 m sheet. So
    every crop cell here is snapped to the CANE SHEET'S OWN 60 m LATTICE and
    sampled with the same `dem()` at the same nodes: the two surfaces are then
    parallel by construction, 0.30 m apart, and cannot interleave at any
    distance. Same rule, one tier down.

    DATA: every polygon, its landuse class and its name. INFERENCE: which crop
    each parcel is carrying (the palette is cane green, cut cane, tilled soil
    and pasture, dealt by a hash of the OSM id - nothing in OSM says which),
    and the 8 m field margin round each one."""
    ring0 = dedupe_ring(d["aerodrome_boundary_xy_m"][0])
    xs = [p[0] for p in ring0]
    ys = [p[1] for p in ring0]
    gx0, gy0 = min(xs) - 4200.0, min(ys) - 4200.0      # the cane lattice origin
    reach = (min(xs) - 4200.0, max(xs) + 4200.0,
             min(ys) - 4200.0, max(ys) + 4200.0)
    px0, px1, py0, py1 = pad_box()
    step = 60.0

    crops = [P["crop_a"], P["crop_b"], P["crop_c"], P["crop_d"]]
    bms = [bmesh.new() for _ in crops]
    bm_g = bmesh.new()
    cells = 0
    for l in d["landuse"]:
        kind = l.get("landuse")
        ring = dedupe_ring(l["polygon_xy_m"])
        if len(ring) < 3:
            continue
        if kind == "grass":
            # mown grass INSIDE the aerodrome. Snapped to the aerodrome pad's
            # own 25 m lattice for exactly the same reason as above.
            for (x, y) in _cells(ring, 25.0, 0.0, 0.0):
                if not (px0 < x < px1 and py0 < y < py1):
                    continue
                _quad(bm_g, x, y, 25.0, lambda a, b: surface_z(a, b, 0.05))
                cells += 1
            continue
        if kind != "farmland":
            continue                       # industrial = the MRO; residential
                                           # is build_village's
        bm = bms[abs(hash(l["osm_id"])) % len(crops)]
        for (x, y) in _cells(ring, step, gx0, gy0):
            if not (reach[0] < x < reach[1] and reach[2] < y < reach[3]):
                continue
            if px0 < x < px1 and py0 < y < py1:
                continue                   # the aerodrome pad has no cane sheet
            _quad(bm, x, y, step, lambda a, b: G.dem(a, b) + 0.75)
            cells += 1
        # NO HEADLAND RIBBON. An 8 m margin round each parcel was built and
        # then removed: a ribbon cannot be snapped to the cane lattice the way
        # a cell can, so it re-created exactly the fight baba4e6 measured out
        # of the cane sheet - poking through in places and vanishing in others,
        # and rendering as a bright red outline round an empty rectangle. The
        # crop colours already draw the boundaries, and they draw them without
        # a second surface to fight.
    for k, (bm, m) in enumerate(zip(bms, crops)):
        bm_to_object(bm, "SDSC_Cropland_%d" % k, m, c_ground, smooth=True)
    bm_to_object(bm_g, "SDSC_MownGrass", P["crop_d"], c_ground, smooth=True)
    print("landuse: %d cells over %d polygons" % (cells, len(d["landuse"])))


def _cells(ring, step, ox, oy):
    """Lattice cell centres whose centre falls inside `ring`, on the lattice
    (ox + i*step, oy + j*step). Snapping to a shared lattice is what stops two
    samplings of one DEM from interleaving."""
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    i0 = int(math.floor((min(xs) - ox) / step))
    i1 = int(math.ceil((max(xs) - ox) / step))
    j0 = int(math.floor((min(ys) - oy) / step))
    j1 = int(math.ceil((max(ys) - oy) / step))
    out = []
    for j in range(j0, j1 + 1):
        cy = oy + (j + 0.5) * step
        for i in range(i0, i1 + 1):
            cx = ox + (i + 0.5) * step
            if _ring_hit(ring, cx, cy):
                out.append((cx, cy))
    return out


def _quad(bm, cx, cy, step, zf):
    h = step * 0.5
    vs = [bm.verts.new((x, y, zf(x, y))) for (x, y) in
          ((cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h))]
    try:
        bm.faces.new(vs)
    except ValueError:
        pass


# ---------------------------------------------------------------------------
VILLAGE_BOX = (-1100.0, 1800.0, -2900.0, -1150.0)


def build_village(d, P, c_bldg, c_veg, c_ground):
    """AGUA VERMELHA - the district the base is in, and a village, not empty
    land. 1.5 km south of THR 02 and directly under the tour's south leg.

    What OSM gives, and it is built: two residential landuse polygons totalling
    75 201 m2, the street grid (Avenida Bela Cintra, Rua Doutor Ernesto Pereira
    Lopes Filho, Rua Julieta Machado Palma and 30 more), and 15 building
    footprints - among them the Capela de Sao Roque, the Unidade de Saude da
    Familia, the Assembleia de Deus, the Igreja do Evangelho Quadrangular, the
    Salao do Reino and the Armazem Cultura Lola Puccinelli Biazon. Those are
    already built by build_buildings, at 5 m, as SDSC_AguaVermelha.

    Fifteen buildings in 7.5 ha of mapped residential land is an under-mapping,
    not a hamlet. refs/agua_vermelha_avenida.jpg is the photograph: a
    continuous street frontage of single-storey rendered houses under red
    pantile, garden walls to the pavement, a heavy street canopy of large
    trees, and concrete distribution poles with street-light brackets down the
    verge. So the frontage is INFILLED along the mapped streets, one house per
    17 m of frontage, set back 6.5 m, skipped wherever a mapped footprint or
    another house is already there.

    THE HOUSES ARE INFERENCE. Their STREETS are data. `VILLAGE_INFILL = False`
    rebuilds the village with only the 15 surveyed footprints in it."""
    import random
    rnd = random.Random(20260824)
    x0, x1, y0, y1 = VILLAGE_BOX

    # the residential ground: dusty red lot-and-yard, not cane
    bm_g = bmesh.new()
    for l in d["landuse"]:
        if l.get("landuse") != "residential":
            continue
        ring = dedupe_ring(l["polygon_xy_m"])
        for (x, y) in _cells(ring, 30.0, 0.0, 0.0):
            _quad(bm_g, x, y, 30.0, lambda a, b: G.dem(a, b) + 0.62)
    bm_to_object(bm_g, "SDSC_VillageGround", P["margin"], c_ground,
                 smooth=True)
    if not VILLAGE_INFILL:
        return

    taken = [tuple(b["centroid_xy_m"]) for b in d["buildings"]
             if x0 < b["centroid_xy_m"][0] < x1 and
             y0 < b["centroid_xy_m"][1] < y1]
    n_mapped = len(taken)
    # The infill is anchored, not scattered: a house only goes where the
    # frontage is inside a mapped residential polygon or within 180 m of a
    # mapped village footprint. Anything further out is farm road, and the
    # village would grow into a town if the rule were just "in the box".
    res = [dedupe_ring(l["polygon_xy_m"]) for l in d["landuse"]
           if l.get("landuse") == "residential"]

    def in_village(px, py):
        if any(_ring_hit(r, px, py) for r in res):
            return True
        return any(math.dist((px, py), q) < 180.0 for q in taken[:n_mapped])
    bm_a, bm_b, bm_r = bmesh.new(), bmesh.new(), bmesh.new()
    bm_tf, bm_tt = bmesh.new(), bmesh.new()
    n = ntree = 0
    # Shuffled, because the cap is a budget and the first attempt spent all of
    # it on one street: 240 houses in a single 400 m terrace, which is what
    # the ops_village check showed. Shuffling spreads the same budget over the
    # whole mapped grid, including the Residencial Bosque dos Jatobas
    # subdivision east of the centre.
    streets = [r for r in d["roads"]
               if r.get("polygon_xy_m") and len(r["polygon_xy_m"]) >= 2 and
               r.get("highway") in ("residential", "unclassified", "secondary",
                                    "tertiary")]
    rnd.shuffle(streets)
    for r in streets:
        pts = r.get("polygon_xy_m")
        pts = [p for p in pts if x0 < p[0] < x1 and y0 < p[1] < y1]
        if len(pts) < 2:
            continue
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            ux, uy, L = unit(ax, ay, bx, by)
            if L < 6.0:
                continue
            nx_, ny_ = -uy, ux
            t = rnd.random() * VILLAGE_LOT_PITCH
            while t < L:
                for side in (1.0, -1.0):
                    # A village is not a terrace. The first pass put every
                    # house at the same setback on the same street and the
                    # ops_village check rendered a 400 m row of identical
                    # sheds; the frontage is broken up here - two lot depths,
                    # a jittered setback, a plot skipped now and then, and a
                    # few degrees of yaw off the street line.
                    if rnd.random() < 0.22:
                        continue                       # an empty lot
                    depth_row = 0 if rnd.random() < 0.78 else 1
                    off = (VILLAGE_SETBACK + 4.5 + rnd.random() * 3.5 +
                           depth_row * (15.0 + rnd.random() * 6.0))
                    jit = (rnd.random() - 0.5) * 5.0
                    px = ax + ux * (t + jit) + nx_ * off * side
                    py = ay + uy * (t + jit) + ny_ * off * side
                    if not in_village(px, py):
                        continue
                    if any(math.dist((px, py), q) < 12.0 for q in taken):
                        continue
                    taken.append((px, py))
                    hdg = math.degrees(math.atan2(ux, uy)) + \
                        (rnd.random() - 0.5) * 7.0
                    w_ = 6.5 + rnd.random() * 4.5
                    dp = 7.5 + rnd.random() * 6.5
                    zb = G.dem(px, py) + 0.62
                    h = 3.0 + rnd.random() * 1.4
                    obox(bm_a if rnd.random() < 0.6 else bm_b,
                         px, py, zb, zb + h, dp, w_, hdg)
                    # a shallow hipped pantile roof, which is what the
                    # photograph shows on every house in the frame
                    obox(bm_r, px, py, zb + h, zb + h + 1.05 +
                         rnd.random() * 0.5, dp + 1.0, w_ + 1.0, hdg)
                    n += 1
                # the street canopy - the avenue photograph is half tree
                if rnd.random() < 0.55 and in_village(ax + ux * t,
                                                      ay + uy * t):
                    side = 1.0 if rnd.random() < 0.5 else -1.0
                    px = ax + ux * t + nx_ * 4.2 * side
                    py = ay + uy * t + ny_ * 4.2 * side
                    _plant_simple(bm_tf, bm_tt, px, py,
                                  8.0 + rnd.random() * 6.0, rnd)
                    ntree += 1
                t += VILLAGE_LOT_PITCH * (0.85 + rnd.random() * 0.4)
                if n >= VILLAGE_MAX_HOUSES:
                    break
            if n >= VILLAGE_MAX_HOUSES:
                break
        if n >= VILLAGE_MAX_HOUSES:
            break
    bm_to_object(bm_a, "SDSC_Village_HousesA", P["house_a"], c_bldg)
    bm_to_object(bm_b, "SDSC_Village_HousesB", P["house_b"], c_bldg)
    bm_to_object(bm_r, "SDSC_Village_Roofs", P["tile_red"], c_bldg)
    bm_to_object(bm_tf, "SDSC_Village_Foliage", P["foliage"], c_veg, smooth=True)
    bm_to_object(bm_tt, "SDSC_Village_Trunks", P["trunk"], c_veg)
    print("village: %d mapped footprints, %d inferred houses, %d trees"
          % (n_mapped, n, ntree))


def _plant_simple(bm_f, bm_t, px, py, h, rnd):
    r = h * (0.36 + rnd.random() * 0.18)
    zb = surface_z(px, py)
    post(bm_t, px, py, 0.26, zb, zb + h * 0.40)
    zs = [h * 0.32, h * 0.56, h * 0.80, h]
    rs = [r * 0.60, r, r * 0.80, 0.001]
    prev = None
    for (z, rr) in zip(zs, rs):
        vs = [bm_f.verts.new((px + rr * math.cos(math.radians(k * 60)),
                              py + rr * math.sin(math.radians(k * 60)),
                              zb + z)) for k in range(6)]
        if prev:
            for k in range(6):
                j = (k + 1) % 6
                try:
                    bm_f.faces.new((prev[k], prev[j], vs[j], vs[k]))
                except ValueError:
                    pass
        prev = vs


def build_powerlines(d, P, c_furn):
    """Rural distribution on the road verges.

    THE PRESENCE IS PHOTOGRAPHED AND THE ROUTE IS NOT. A conductor is strung
    right across the top of refs/sdsc_field_from_sp318_2013.jpg - that frame is
    taken standing on the SP-318 verge and the wire is the nearest object in it
    - and refs/agua_vermelha_avenida.jpg shows the poles themselves: square
    concrete sections, one crossarm, three phases and a neutral, a street-light
    bracket on the village ones. OSM's extract carries no `power` way at all,
    so the LINE is taken from the verges of the motorway, secondary and
    tertiary roads, which is where these run in the region, and the 45 m
    spacing and 9.2 m height are the standard rural ones. ALL INFERENCE except
    that there are poles and wires along these roads.

    The conductors are built as VERTICAL ribbons 0.16 m deep. That is not
    laziness, it is the Santiago light-mast lesson applied before the fact:
    thin geometry that steps several pixels a frame strobes in a 25 fps GIF.
    Edge-on to an aerial looking down they nearly vanish, which is exactly
    where the risk is; broadside to a ground camera - the 2013 framing, and the
    departure clip's eye height - they read."""
    bm_p, bm_a, bm_w = bmesh.new(), bmesh.new(), bmesh.new()
    npole = 0
    for r in d["roads"]:
        pts = r.get("polygon_xy_m")
        if not pts or len(pts) < 2:
            continue
        if r.get("highway") not in POWERLINE_ROADS:
            continue
        pts = [p for p in pts if abs(p[0]) < POWERLINE_REACH and
               abs(p[1]) < POWERLINE_REACH]
        if len(pts) < 2:
            continue
        half = ROAD_WIDTH.get(r["highway"], 6.0) * 0.5 + 3.2
        run = []
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            ux, uy, L = unit(ax, ay, bx, by)
            nx_, ny_ = -uy, ux
            t = 0.0
            while t < L:
                run.append((ax + ux * t + nx_ * half,
                            ay + uy * t + ny_ * half))
                t += POLE_SPACING
        for (px, py) in run:
            zb = surface_z(px, py)
            post(bm_p, px, py, 0.13, zb, zb + POLE_H)
            box(bm_a, px - 1.1, px + 1.1, py - 0.09, py + 0.09,
                zb + POLE_H - 0.9, zb + POLE_H - 0.72)
            npole += 1
        for i in range(len(run) - 1):
            ax, ay = run[i]
            bx, by = run[i + 1]
            L = math.hypot(bx - ax, by - ay)
            if L > POLE_SPACING * 1.5:
                continue                    # a corner, not a span
            za = surface_z(ax, ay) + POLE_H - 0.82
            zbb = surface_z(bx, by) + POLE_H - 0.82
            for lat in (-0.95, 0.0, 0.95):
                ux, uy, _ = unit(ax, ay, bx, by)
                nx_, ny_ = -uy, ux
                prev = None
                for k in range(3):
                    t = k / 2.0
                    x = ax + (bx - ax) * t + nx_ * lat
                    y = ay + (by - ay) * t + ny_ * lat
                    sag = 0.9 * 4.0 * t * (1.0 - t)
                    z = za + (zbb - za) * t - sag
                    cur = (bm_w.verts.new((x, y, z)),
                           bm_w.verts.new((x, y, z - 0.16)))
                    if prev:
                        try:
                            bm_w.faces.new((prev[0], cur[0], cur[1], prev[1]))
                        except ValueError:
                            pass
                    prev = cur
    bm_to_object(bm_p, "SDSC_PowerPoles", P["pole"], c_furn)
    bm_to_object(bm_a, "SDSC_PowerCrossarms", P["pole"], c_furn)
    bm_to_object(bm_w, "SDSC_PowerConductors", P["wire"], c_furn)
    print("powerlines: %d poles" % npole)


def build_cane_yards(P, c_bldg):
    """Cane-loading yards. DECLARED INFERENCE, all of it - nothing in OSM says
    these are here. But this is the cane belt in the burning season, the field
    is ringed by mapped fazendas, and a cane block that is being cut has a
    loading yard at the head of its track: a scraped red pad, a stack or two of
    cut cane, and a couple of high-sided trailers waiting. Three of them, at
    the ends of mapped tracks. They are here because the alternative - 19 km2
    of surveyed farmland with no sign that anyone works it - is the less true
    of the two."""
    bm_c, bm_t, bm_p = bmesh.new(), bmesh.new(), bmesh.new()
    for (cx, cy, hdg) in ((-1980.0, 1520.0, 20.0),
                          (2320.0, 480.0, 100.0),
                          (-1240.0, 3180.0, 70.0)):
        zb = G.dem(cx, cy) + 0.55
        obox(bm_p, cx, cy, zb, zb + 0.04, 46.0, 28.0, hdg)
        a = math.radians(hdg)
        ux, uy = math.sin(a), math.cos(a)
        for k in (-1, 1):
            sx, sy = cx + ux * 9.0 * k, cy + uy * 9.0 * k
            obox(bm_c, sx, sy, zb, zb + 2.6, 22.0, 5.0, hdg + 90.0)
        for k in (-1, 1):
            tx = cx - uy * 11.0 + ux * 6.0 * k
            ty = cy + ux * 11.0 + uy * 6.0 * k
            obox(bm_t, tx, ty, zb + 0.9, zb + 3.4, 9.0, 2.6, hdg)
    bm_to_object(bm_p, "SDSC_CaneYardPads", P["margin"], c_bldg)
    bm_to_object(bm_c, "SDSC_CaneStacks", P["crop_b"], c_bldg)
    bm_to_object(bm_t, "SDSC_CaneTrailers", P["gse_white"], c_bldg)


# ---------------------------------------------------------------------------
# THE OPERATION
#
# ~2 000 people, 22 workshops, ~270 aircraft a year, 16 in work at once. Phase
# 2 put six whole aeroplanes nose-in on an empty slab and built nothing else,
# and that is why the base reads as a model of a base: a heavy-check line has
# aircraft that are visibly APART, yellow steel standing round them, kit
# between them, and somewhere for two thousand people to leave a car.
#
# Everything in this section is at 200-700 m in the tour and 800-1 900 m in the
# departure. Simple proxies that read correctly at those distances beat
# detailed models nobody sees - the same rule the rest of this field follows.
# ---------------------------------------------------------------------------

# The nose-in line, and what state each aeroplane is in.
#
# POSITIONS are inference constrained by data: not one MRO stand is surveyed
# (sdsc_references.md 6.10 - OSM's three parking positions are all at the
# Aeroclube), but the apron polygon and relation/7422966's west face at x = 931
# fix the row. STATES are inference of a different kind: no photograph shows
# which aeroplane is in what check on a given day, but a base that has 16
# aircraft in work at once does not have a ramp full of ready-to-go airliners,
# and refs/mro_centro_tecnologico_2009.jpg has a stripped fuselage inside a
# dock ON THE APRON, not in a hangar.
#
# THE AEROPLANES THEMSELVES ARE NO LONGER BUILT HERE. Phase 5 gave every stand
# in this table one of the eleven real masters, through `fleet_placement.py`;
# what stays in this file is the STAND - its position, heading and state - plus
# all the kit that state implies, because the docks, jacks, cradles and GSE are
# scenery and the aeroplane is not. `fleet_placement.FLEET` says which type
# stands where and its docstring says what each state could honestly become on
# a real model. `airliner_proxy()` below is kept and still wired up: a stand
# whose FLEET entry is None gets its proxy back, which is the escape hatch if
# the render cost of a detailed aeroplane at some far stand ever stops being
# worth it. Nothing uses it at present.
MRO_STANDS = (
    # tag     type      x       y      hdg    state
    ("ROW0", "wide",   902.0, 1786.0,  91.0, "parked"),
    ("ROW1", "narrow", 900.0, 1838.0,  91.0, "parked"),
    ("H9",   "dream",  750.0, 1725.0, 181.0, "parked"),
    ("N0",   "wide",   877.0, 1950.0, 181.0, "jacked"),
    ("N1",   "narrow", 881.0, 1888.0, 181.0, "docked"),
    ("N2",   "narrow", 980.0, 1958.0, 181.0, "engine_off"),
    ("N3",   "narrow", 993.0, 2004.0, 181.0, "cowls"),
    ("N4",   "narrow", 997.0, 1911.0, 181.0, "cowls"),
    ("N5",   "narrow", 848.5, 1835.0, 181.0, "docked"),
)
# THE POSITIONS ABOVE ARE PHASE 5'S, AND THEY ARE SOLVED, NOT PICKED.
#
# Phase 4 checked a 21 m circle round each stand - a narrowbody half-span -
# against the mapped apron polygon relation/7422967, and its first attempt had
# put two stands on the grass west of the ramp. That test stopped being enough
# the moment real models went on the stands: the aeroplanes are 34 to 63 m
# across, and this apron is not one slab. Ray-cast at 2 m over x 690..1042,
# y 1640..2072, the built `SDSC_ApronConcrete` is **10 632 cells of 38 409** -
# a deep frontage block from y 1770 to 1920, and above that only three
# fingers, 10 to 50 m wide, at x ~880, x ~920-930 and x ~970-1020.
#
# Measured against that map, phase 4's N0 was standing on `SDSC_AerodromeGround`
# - the jacked LATAM Cargo 767 was on dirt, 5 cm below the concrete and the
# same pale grey in a render, which is why nobody saw it - and five more
# aeroplanes had a wingtip over the edge.
#
# So the nine stands were re-solved against the concrete itself, with the
# criterion a ramp actually has: **the fuselage strip on pavement** - the belly
# and the main-gear track, 13 m wide, which covers every type here (A320 7.6 m,
# 767 9.3 m, 787 10.8 m) - full envelopes 8 m clear of each other, and clear of
# every mapped building. A WINGTIP MAY OVERHANG: real ramps end somewhere, and
# a bounding box is mostly empty air. Each stand then took the nearest solution
# to where phase 4 had put it, so the composition is phase 4's and only the
# error is gone: H9, N2 and N4 did not move at all, ROW0/ROW1/N1/N5 moved 1 to
# 3 m, N0 moved 7 m onto the concrete and N3 moved 13 m onto its finger.
#
# `fleet_placement._on_concrete()` re-runs the test after every placement, by
# ray-cast, on whatever the clip file actually contains.
AC_TYPES = {"narrow": (37.6, 35.8, 11.76, 1.98, 2.40),   # A320 family
            "wide": (54.9, 47.6, 15.85, 2.52, 3.00),     # 767-300ER
            "dream": (62.8, 60.1, 17.02, 2.85, 3.20)}    # 787-9
JACK_LIFT = 0.55

# Stands that are NOT on the MRO platform, in the same shape as MRO_STANDS with
# the apron's own z on the end. The mid-field apron sits 26 m below the runway
# crest and the 2013 reference photograph has a TAM widebody parked on it; that
# is the whole list.
OUTFIELD_STANDS = (
    # tag    type     x      y       hdg    state     apron z
    ("MID", "wide", 300.0, 1140.0, 181.0, "parked", Z_MIDFIELD_APRON),
)


def ac_axes(hdg):
    """(nose unit, starboard unit) for a stand heading, in the same convention
    build_parked_aircraft uses: rotation_euler.z = radians(90 - heading)."""
    a = math.radians(90.0 - hdg)
    fx, fy = math.cos(a), math.sin(a)
    return (fx, fy), (fy, -fx)


# --- the kit vocabulary ----------------------------------------------------
def _deck(bm, cx, cy, zb, L, W, H, hdg, rail=True):
    """A yellow access platform: four legs, a deck, and a rail on the long
    sides. refs/mro_centro_manutencao_2006.jpg is full of these."""
    a = math.radians(hdg)
    ux, uy = math.sin(a), math.cos(a)
    px, py = uy, -ux
    for (sl, sw) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        lx = cx + ux * sl * (L * 0.5 - 0.4) + px * sw * (W * 0.5 - 0.35)
        ly = cy + uy * sl * (L * 0.5 - 0.4) + py * sw * (W * 0.5 - 0.35)
        post(bm, lx, ly, 0.10, zb, zb + H)
    obox(bm, cx, cy, zb + H, zb + H + 0.14, L, W, hdg)
    if rail:
        for sw in (-1, 1):
            obox(bm, cx + px * sw * W * 0.5, cy + py * sw * W * 0.5,
                 zb + H + 0.14, zb + H + 1.05, L, 0.10, hdg)


def _tower(bm, cx, cy, zb, H, hdg, w=2.4):
    """A stepped tubular access tower with a stair face - the thing standing at
    every door and every engine in the 2006 and 2010 hangar photographs."""
    n = max(2, int(H / 2.4))
    for k in range(n):
        z0 = zb + k * H / n
        obox(bm, cx, cy, z0, z0 + 0.12, w, w, hdg)
        for (sl, sw) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            a = math.radians(hdg)
            ux, uy = math.sin(a), math.cos(a)
            px, py = uy, -ux
            lx = cx + ux * sl * (w * 0.5 - 0.15) + px * sw * (w * 0.5 - 0.15)
            ly = cy + uy * sl * (w * 0.5 - 0.15) + py * sw * (w * 0.5 - 0.15)
            post(bm, lx, ly, 0.07, z0, z0 + H / n)
    obox(bm, cx, cy, zb + H, zb + H + 1.0, w, 0.09, hdg)


def _stairs(bm, cx, cy, zb, H, hdg, w=1.6):
    """Rolling passenger / access stairs: a wedge, in steps."""
    a = math.radians(hdg)
    ux, uy = math.sin(a), math.cos(a)
    n = 6
    for k in range(n):
        t = (k + 0.5) / n
        obox(bm, cx + ux * (t - 0.5) * H * 1.25,
             cy + uy * (t - 0.5) * H * 1.25,
             zb, zb + H * t, H * 1.25 / n, w, hdg)


def _jack(bm, x, y, zb, h):
    post(bm, x, y, 0.55, zb, zb + 0.25)
    post(bm, x, y, 0.16, zb + 0.25, zb + h)


def _engine_stand(bm_y, bm_g, x, y, zb, r, hdg):
    """An engine off the wing and on its cradle - the single clearest sign that
    an aeroplane is in a check and not on a turnaround."""
    _deck(bm_y, x, y, zb, r * 3.4, r * 2.6, 0.85, hdg, rail=False)
    a = math.radians(hdg)
    ux, uy = math.sin(a), math.cos(a)
    ns = 8
    prev = None
    for t in (-1.4, -0.9, 0.9, 1.4):
        rr = r * (0.55 if abs(t) > 1.2 else 1.0)
        vs = [bm_g.verts.new((x + ux * t * r + 0.0,
                              y + uy * t * r + rr * math.sin(2 * math.pi * i / ns),
                              zb + 1.0 + r + rr * math.cos(2 * math.pi * i / ns)))
              for i in range(ns)]
        if prev:
            for i in range(ns):
                j = (i + 1) % ns
                try:
                    bm_g.faces.new((prev[i], prev[j], vs[j], vs[i]))
                except ValueError:
                    pass
        prev = vs


def build_maintenance(P, c_ops):
    """The docks, stands, jacks and loose engines that make this an MRO and not
    a terminal apron.

    THE COLOUR IS PHOTOGRAPHED. refs/mro_centro_manutencao_2006.jpg (a Fokker
    100 in a bay on this site) and refs/mro_centro_tecnologico_2010.jpg (an
    A320 with the fan cowls open) are both full of yellow tubular access
    towers, yellow wing docks and yellow rolling stairs, with RED tool
    trolleys on the floor between them. refs/mro_centro_tecnologico_2009.jpg
    puts the same tan-yellow dock structure round a stripped fuselage OUT ON
    THE APRON. What is inference is where each piece stands and how many there
    are - nothing surveys a ramp's kit."""
    bm_y, bm_g, bm_r = bmesh.new(), bmesh.new(), bmesh.new()
    zb = Z_MRO_PLATFORM + Z_APRON
    n = 0
    for (tag, key, x, y, hdg, state) in MRO_STANDS:
        if state == "parked":
            continue
        L, S, F, R, GH = AC_TYPES[key]
        (fx, fy), (rx, ry) = ac_axes(hdg)
        lift = JACK_LIFT if state == "jacked" else 0.0

        def at(along, lat):
            return (x + fx * along + rx * lat, y + fy * along + ry * lat)

        # A wing dock under each wing, at the trailing edge. The first pass
        # made these S * 0.30 long and 3.0 m wide and stood them at S * 0.30
        # out - which is a platform the size of a wing chord sitting OUTBOARD
        # of the wing, and the ramp check rendered a row of yellow ironing
        # boards. 8 m x 2.4 m at S * 0.24 puts them under the wing where a
        # dock goes, and they stop competing with the aeroplane.
        for s in (1, -1):
            px, py = at(-L * 0.15, s * S * 0.24)
            _deck(bm_y, px, py, zb, S * 0.22, 2.4, GH + R * 0.55 + lift,
                  hdg + 90.0)
            n += 1
        # engine access towers
        for s in (1, -1):
            px, py = at(L * 0.05, s * S * 0.17)
            _tower(bm_y, px, py, zb, GH + R * 0.2 + lift, hdg)
            n += 1
        # stairs at the forward door
        px, py = at(L * 0.22, R * 1.9)
        _stairs(bm_y, px, py, zb, GH + R * 1.1 + lift, hdg + 90.0)
        n += 1
        if state in ("docked", "jacked"):
            # nose dock and tail dock - the deep-check silhouette
            px, py = at(L * 0.44, 0.0)
            _tower(bm_y, px, py, zb, GH + R * 1.6 + lift, hdg, w=3.2)
            px, py = at(-L * 0.44, 0.0)
            _tower(bm_y, px, py, zb, F * 0.62 + lift, hdg, w=4.0)
            n += 2
        if state == "jacked":
            for (a_, l_) in ((L * 0.33, 0.0), (-L * 0.02, S * 0.24),
                             (-L * 0.02, -S * 0.24)):
                px, py = at(a_, l_)
                _jack(bm_y, px, py, zb, GH - 0.4 + lift)
                n += 1
        if state == "engine_off":
            px, py = at(L * 0.02, -S * 0.30)
            _engine_stand(bm_y, bm_g, px, py, zb, R * 0.44, hdg)
            px, py = at(-L * 0.10, -S * 0.42)
            obox(bm_y, px, py, zb, zb + 1.1, 4.0, 2.2, hdg)   # engine dolly
            n += 2
        # tool trolleys, red, in the working area under the wing
        for k in range(5):
            a_ = (-0.20 + 0.10 * k) * L
            l_ = (R * 2.4) if k % 2 else -(R * 2.4)
            px, py = at(a_, l_)
            obox(bm_r, px, py, zb, zb + 1.0, 1.6, 0.9, hdg + 25.0 * k)
            n += 1
    bm_to_object(bm_y, "SDSC_MRO_Docks", P["dock_yellow"], c_ops)
    bm_to_object(bm_g, "SDSC_MRO_LooseEngines", P["ac_grey"], c_ops,
                 smooth=True)
    bm_to_object(bm_r, "SDSC_MRO_ToolCarts", P["cart_red"], c_ops)
    print("maintenance kit: %d pieces" % n)


GSE_KINDS = (
    # name, length, width, height, material key
    ("tug", 4.8, 2.4, 1.7, "gse_white"),
    ("gpu", 3.2, 1.6, 1.8, "gse_yellow"),
    ("airstart", 3.6, 1.8, 1.9, "gse_yellow"),
    ("beltloader", 6.4, 2.2, 1.6, "gse_white"),
    ("van", 5.2, 2.0, 2.1, "gse_white"),
    ("pickup", 5.4, 2.0, 1.9, "gse_white"),
    ("bowser", 9.0, 2.6, 2.9, "gse_white"),
    ("cherrypicker", 5.6, 2.3, 2.4, "gse_yellow"),
)


def _on_concrete(d, x, y):
    """True if (x, y) is inside the mapped MRO apron or hangar 9's own stand.
    Kit standing on the grass beside a ramp is the detail that says nobody
    checked, and the first pass had a GSE row and a container row doing it."""
    for a in d["aprons"]:
        if a["osm_id"] == "relation/7422967" and \
                _ring_hit(dedupe_ring(a["polygon_xy_m"]), x, y):
            return True
    h = HANGAR9
    return (h["x0"] - 25 < x < h["x1"] + 25) and (h["y1"] < y < 1762.0)


def build_gse(d, P, c_ops):
    """Ground support equipment on the MRO apron.

    ALL OF IT IS INFERENCE and it has to be said plainly: no photograph of
    LATAM's Sao Carlos ground fleet was found, and OSM maps no vehicle. What is
    not inference is that an apron working 270 aircraft a year has tugs,
    towbars, ground power, air start, steps, loaders, tool carts and service
    vehicles on it, and that an apron with NONE of those on it is the thing the
    owner noticed. refs/mro_centro_tecnologico_2009.jpg shows small dark
    vehicles clustered at the nose of every aeroplane in the line; that is the
    level of detail this reproduces.

    A towbar is modelled with its tug because a tug WITHOUT one, parked at a
    nose gear, is the detail that reads wrong to anybody who has stood on a
    ramp."""
    bm_w, bm_y, bm_d = bmesh.new(), bmesh.new(), bmesh.new()
    bmk = {"gse_white": bm_w, "gse_yellow": bm_y, "gse_dark": bm_d}
    zb = Z_MRO_PLATFORM + Z_APRON
    n = 0

    def put(kind, x, y, hdg):
        nonlocal n
        for (nm, L, W, H, mk) in GSE_KINDS:
            if nm != kind:
                continue
            bm = bmk[mk]
            obox(bm, x, y, zb + 0.28, zb + H, L, W, hdg)
            obox(bm_d, x, y, zb, zb + 0.34, L * 0.92, W * 1.02, hdg)  # wheels
            if kind == "tug":       # and its towbar
                a = math.radians(hdg)
                ux, uy = math.sin(a), math.cos(a)
                obox(bm_y, x + ux * (L * 0.5 + 2.6), y + uy * (L * 0.5 + 2.6),
                     zb + 0.35, zb + 0.55, 5.2, 0.35, hdg)
            n += 1

    for (tag, key, x, y, hdg, state) in MRO_STANDS:
        if tag == "H9":
            # NOTHING on hangar 9's stand and nothing in its door line. That
            # stand is where hangar_tow.py drives a 787 through, from a nose
            # gear at (762, 1706) to (750, 1664) with 60 m of span either side
            # of x = 750, and a tug parked at the tow point would be inside the
            # aeroplane for the whole clip. The kit for that apron goes in the
            # row at x 660-700 below, west of the door jamb at x = 711.
            continue
        L, S, F, R, GH = AC_TYPES[key]
        (fx, fy), (rx, ry) = ac_axes(hdg)

        def at(along, lat):
            return (x + fx * along + rx * lat, y + fy * along + ry * lat)

        px, py = at(L * 0.62, 0.0)
        put("tug", px, py, hdg + 180.0)                 # nose-on to the tow point
        px, py = at(L * 0.16, R * 3.4)
        put("gpu", px, py, hdg + 90.0)
        px, py = at(-L * 0.06, R * 3.6)
        put("van", px, py, hdg)
        if state in ("cowls", "engine_off", "docked"):
            px, py = at(L * 0.02, R * 4.6)
            put("cherrypicker", px, py, hdg + 20.0)
            px, py = at(-L * 0.26, -R * 3.6)
            put("airstart", px, py, hdg)
        if state == "parked":
            px, py = at(L * 0.26, -R * 3.2)
            put("beltloader", px, py, hdg + 90.0)

    # the GSE park: everything not out at an aeroplane, lined up on the apron
    # edge where the mapped concrete meets the perimeter road.
    import random
    rnd = random.Random(20260824)
    kinds = [k[0] for k in GSE_KINDS]
    # Row starts found by walking the mapped apron polygon for ten consecutive
    # 7.4 m slots that are on the concrete, clear of every mapped MRO footprint
    # and 34 m from every stand. Guessed rows kept landing on the grass.
    for row, (bx, by, hdg) in enumerate(((950.0, 1875.0, 0.0),
                                         (820.0, 1760.0, 0.0),
                                         (800.0, 1800.0, 0.0),
                                         (662.0, 1700.0, 0.0))):
        for k in range(12):
            a = math.radians(hdg)
            ux, uy = math.sin(a), math.cos(a)
            px, py = bx + uy * k * 7.4, by - ux * k * 7.4
            if 702.0 < px < 845.0 and 1680.0 < py < 1772.0:
                continue          # clear of hangar 9's door and the tow path
            if not _on_concrete(d, px, py):
                continue
            put(kinds[(k + row) % len(kinds)], px, py, hdg)
    for k in range(3):
        px, py = 1012.0, 1900.0 + k * 14.0
        if _on_concrete(d, px, py):
            put("bowser", px, py, 0.0)
    bm_to_object(bm_w, "SDSC_GSE_White", P["gse_white"], c_ops)
    bm_to_object(bm_y, "SDSC_GSE_Yellow", P["gse_yellow"], c_ops)
    bm_to_object(bm_d, "SDSC_GSE_Chassis", P["gse_dark"], c_ops)
    print("GSE: %d units" % n)


def build_containers(d, P, c_ops):
    """ISO containers and tool cribs against the hangar line.

    PHOTOGRAPHED: refs/mro_centro_tecnologico_2009.jpg has a line of white
    boxes standing along the apron behind the parked aeroplanes, and
    refs/mro_centro_tecnologico_2010.jpg has a dark red-brown skip in the
    foreground of the hangar floor. Where each one stands is inference."""
    bm_a, bm_b = bmesh.new(), bmesh.new()
    zb = Z_MRO_PLATFORM + Z_APRON
    n = 0
    # Along the APRON'S OWN EDGE, 9 m in, rather than at hand-picked spots: the
    # mapped polygon decides where there is room, so nothing ends up on the
    # grass and nothing lands under a wing. Four hand-picked rows were tried
    # first and three of them were off the concrete - the same mistake the ops
    # check caught on the GSE park.
    ring = dedupe_ring([a["polygon_xy_m"] for a in d["aprons"]
                        if a["osm_id"] == "relation/7422967"][0])
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    for i in range(len(ring)):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % len(ring)]
        ux, uy, L = unit(ax, ay, bx, by)
        if L < 26.0:
            continue
        nx_, ny_ = -uy, ux
        if (cx - ax) * nx_ + (cy - ay) * ny_ < 0:      # point inward
            nx_, ny_ = -nx_, -ny_
        hdg = math.degrees(math.atan2(ux, uy))
        # In BLOCKS - two rows deep, four long, then a gap. A single file of
        # 34 boxes end-on to the ramp was tried first and read as a train:
        # containers on a working apron are stacked in blocks against a wall,
        # long axis parallel to it, not laid out in a 100 m line.
        t = 14.0
        while t < L - 20.0 and n < 26:
            for k in range(4):
                for row in range(2):
                    px = (ax + ux * (t + k * 12.8) + nx_ * (8.0 + row * 2.9))
                    py = (ay + uy * (t + k * 12.8) + ny_ * (8.0 + row * 2.9))
                    if not _on_concrete(d, px, py):
                        continue
                    if any(math.hypot(px - sx, py - sy) < 32.0
                           for (_, _, sx, sy, _, _) in MRO_STANDS):
                        continue
                    bm = bm_a if n % 3 else bm_b
                    obox(bm, px, py, zb, zb + 2.6, 12.2, 2.44, hdg)
                    if (k + row) % 3 == 1:            # stacked two high
                        obox(bm, px, py, zb + 2.6, zb + 5.2, 12.2, 2.44, hdg)
                    n += 1
            t += 108.0
    bm_to_object(bm_a, "SDSC_Containers", P["container"], c_ops)
    bm_to_object(bm_b, "SDSC_ContainersRust", P["container_b"], c_ops)
    print("containers: %d" % n)


def _aisles(d):
    """OSM `service` and short `unclassified` ways inside the MRO site.

    This is the landside circulation, and it is mapped. Among it are the aisle
    grids: parallel runs 18-45 m apart inside closed loops, which is a car park
    and nothing else. `grid` marks the segments that have such a neighbour."""
    bb = d["latam_mro"]["site_bbox_xy_m"]
    x0, y0 = bb["min"]
    x1, y1 = bb["max"]
    segs = []
    for r in d["roads"]:
        pts = r.get("polygon_xy_m")
        if not pts or len(pts) < 2:
            continue
        if r.get("highway") not in ("service", "unclassified"):
            continue
        if (r.get("length_m") or 0.0) > CARPARK_AISLE_MAX_M:
            continue
        if not all(x0 - 40 < p[0] < x1 + 40 and y0 - 40 < p[1] < y1 + 40
                   for p in pts):
            continue
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            ux, uy, L = unit(ax, ay, bx, by)
            if L < 8.0:
                continue
            segs.append([ax, ay, bx, by, ux, uy, L, r["osm_id"], False])
    # An aisle is 25 m or more, and so is its parallel neighbour. Without that
    # floor the test fires on pairs of 7 m gate stubs at x = 470-583 and lays
    # 22 m of car park over them, 200 m west of anything - which the ops check
    # showed as black rectangles standing on the grass.
    for s in segs:
        if s[6] < CARPARK_AISLE_MIN_M:
            continue
        for t in segs:
            if t[7] == s[7] or t[6] < CARPARK_AISLE_MIN_M:
                continue
            if abs(s[4] * t[4] + s[5] * t[5]) < 0.97:      # not parallel
                continue
            mx, my = (t[0] + t[2]) * 0.5, (t[1] + t[3]) * 0.5
            dx, dy = mx - s[0], my - s[1]
            along = dx * s[4] + dy * s[5]
            if not (-6.0 < along < s[6] + 6.0):
                continue
            lat = abs(-dx * s[5] + dy * s[4])
            if 17.0 < lat < 46.0:
                s[8] = True
                break
    return segs


def build_carparks(d, P, c_ops):
    """STAFF PARKING. Two thousand people arrive somehow, and a car park at
    that scale is a large, instantly readable feature - its absence is a real
    part of why this base reads as a model.

    THE GEOMETRY IS DATA, and that was a surprise. OSM has no `amenity=parking`
    on this site, but it maps the landside circulation as `service` ways, and
    four of those clusters are unmistakable AISLE GRIDS - parallel 60-120 m
    runs 18-45 m apart inside closed loops - along the south face of the
    workshop spine, on the east side by the ring road, on the west by the
    hangar line, and at the north end. `_aisles()` finds them by that geometric
    test rather than by a hand-written list, so a future OSM refresh moves them
    by itself.

    WHAT IS INFERENCE: that these aisles are STAFF car parks rather than
    service yards; the 22 m slab width (aisle + one 5 m bay each side); the
    2.65 m bay pitch; and every car. The occupancy is set to 56%, which is a
    day shift and not a full house. Nothing published says how many of LATAM's
    2 000 Sao Carlos staff drive."""
    segs = _aisles(d)
    zb = Z_MRO_PLATFORM + Z_APRON
    bm_s = bmesh.new()
    aisle_m = 0.0
    for s in segs:
        if not s[8]:
            continue          # an ordinary service road; build_roads has it
        pts = resample([(s[0], s[1]), (s[2], s[3])], 20.0)
        drape(bm_s, pts, CARPARK_HALF_W * 2.0, 0.02,
              zfun=lambda a, b, dz: Z_MRO_PLATFORM + dz)
        aisle_m += s[6]
    bm_to_object(bm_s, "SDSC_LandsideHardstanding", P["carpark"], c_ops)

    import random
    rnd = random.Random(20260824)
    keys = ("car_white", "car_white", "car_silver", "car_silver", "car_dark",
            "car_red")
    bms = {k: bmesh.new() for k in set(keys)}
    bm_glass = bmesh.new()
    mro_ids = set(m["osm_id"] for m in d["latam_mro"]["members"])
    blocks = [(b["polygon_xy_m"], b["centroid_xy_m"]) for b in d["buildings"]
              if b["osm_id"] in mro_ids] + \
             [(h["polygon_xy_m"], h["centroid_xy_m"]) for h in d["hangars"]
              if h["osm_id"] in mro_ids]
    ncar = nbay = 0
    for s in segs:
        if not s[8]:
            continue
        ax, ay, bx, by, ux, uy, L = s[:7]
        nx_, ny_ = -uy, ux
        hdg = math.degrees(math.atan2(nx_, ny_))
        t = 1.6
        while t < L - 1.6:
            for side in (1.0, -1.0):
                nbay += 1
                if rnd.random() > CARPARK_OCCUPANCY:
                    continue
                px = ax + ux * t + nx_ * 5.6 * side
                py = ay + uy * t + ny_ * 5.6 * side
                if any(_ring_hit(ring, px, py) or
                       math.dist((px, py), c) < 8.0 for ring, c in blocks):
                    continue
                bm = bms[keys[rnd.randrange(len(keys))]]
                obox(bm, px, py, zb + 0.28, zb + 0.95, 4.4, 1.82,
                     hdg + (0.0 if side > 0 else 180.0))
                obox(bm_glass, px, py, zb + 0.95, zb + 1.42, 2.3, 1.70, hdg)
                ncar += 1
            t += CARPARK_BAY_PITCH
    for k, bm in bms.items():
        bm_to_object(bm, "SDSC_Cars_" + k.split("_")[1].title(), P[k], c_ops)
    bm_to_object(bm_glass, "SDSC_CarGlazing", P["glass_car"], c_ops)
    print("car parks: %.0f m of mapped aisle, %d bays, %d cars"
          % (aisle_m, nbay, ncar))


def build_gate(P, c_mro):
    """The gate and the guard house on the perimeter wall.

    The WALL is photographed (refs/mro_airbus_esquadrilha_2010.jpg: white
    render about 0.8 m, black welded mesh above it) and phase 2 drew its line.
    The GATE'S POSITION is not free invention either: four mapped service ways
    - way/510750444, /445, /446 and /510750640 - cross the wall's south run at
    x = 914-930, which is where the landside road actually enters the airside.
    The guard house, the canopy and the boom are inference; a controlled
    aerodrome gate has them."""
    base = Z_MRO_PLATFORM
    bm_w, bm_d, bm_y = bmesh.new(), bmesh.new(), bmesh.new()
    gx, gy = 922.0, 1545.0
    # the two sliding leaves, stacked back off a 14 m opening
    for s in (-1, 1):
        obox(bm_d, gx + s * 10.5, gy, base + 0.2, base + 2.6, 7.0, 0.16, 90.0)
        post(bm_d, gx + s * 7.0, gy, 0.18, base, base + 3.2)
    # guard house, on the landside, with a flat canopy over the lane
    obox(bm_w, gx - 12.0, gy - 6.5, base, base + 3.1, 6.0, 4.0, 0.0)
    obox(bm_w, gx - 12.0, gy - 6.5, base + 3.1, base + 3.35, 7.0, 5.0, 0.0)
    obox(bm_w, gx, gy - 6.0, base + 4.4, base + 4.7, 16.0, 6.0, 0.0)
    for sx in (-7.0, 7.0):
        post(bm_w, gx + sx, gy - 8.6, 0.16, base, base + 4.4)
    # the boom
    obox(bm_y, gx + 2.6, gy - 6.0, base + 1.0, base + 1.14, 0.24, 5.2, 0.0)
    post(bm_y, gx - 0.2, gy - 6.0, 0.18, base, base + 1.2)
    bm_to_object(bm_w, "SDSC_MRO_GuardHouse", P["wall_white"], c_mro)
    bm_to_object(bm_d, "SDSC_MRO_Gate", P["mesh_black"], c_mro)
    bm_to_object(bm_y, "SDSC_MRO_Boom", P["dock_yellow"], c_mro)


# ---------------------------------------------------------------------------
# parked aircraft
# ---------------------------------------------------------------------------
def airliner_proxy(name, length, span, fin_h, fus_r, gear_h, mats,
                   engines="on", lift=0.0):
    """Low-poly airliner, nose along +X, WHEELS ON z = 0.

    Santiago's proxies sit on their bellies, which is invisible at the 0.7-2 km
    those sit at. Here the nose-in line is 800 m from a departing aircraft and
    the mid-field aeroplane is closer still, so this one stands on its gear:
    fuselage axis at gear_h + fus_r, a low-wing at belly height with dihedral,
    underslung engines and three struts.

    `engines` is what makes this an MRO ramp rather than a terminal one:

        "on"      both nacelles closed - an aeroplane ready to go
        "open"    both nacelles with the fan cowls hinged UP, which is the
                  state refs/mro_centro_tecnologico_2010.jpg photographs on
                  this very site: an A320 with the cowls open and the core
                  exposed, stands under the wing, a ladder at the nose door
        "off"     the PORT nacelle absent, pylon bare. build_maintenance puts
                  the engine itself on a cradle beside the wing.

    `lift` raises the whole aeroplane off its wheels for a jacked airframe;
    the gear struts stretch with it, which is what a jacked aeroplane looks
    like from 300 m - the wheels hanging clear of the concrete."""
    hc = gear_h + fus_r + lift
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
        pylon = [bm.verts.new((ex + 0.4, ey, ez + er)),
                 bm.verts.new((ex - 2.2, ey, ez + er)),
                 bm.verts.new((ex - 2.2, ey, hc - fus_r * 0.72)),
                 bm.verts.new((ex + 0.4, ey, hc - fus_r * 0.72))]
        try:
            bm.faces.new(pylon)
        except ValueError:
            pass
        if not (engines == "off" and s == 1):
            r0 = [bm.verts.new((ex + 1.9,
                                ey + er * math.sin(2 * math.pi * i / 10),
                                ez + er * math.cos(2 * math.pi * i / 10)))
                  for i in range(10)]
            r1 = [bm.verts.new((ex - 3.0,
                                ey + er * math.sin(2 * math.pi * i / 10),
                                ez + er * math.cos(2 * math.pi * i / 10)))
                  for i in range(10)]
            for i in range(10):
                j = (i + 1) % 10
                try:
                    bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
                except ValueError:
                    pass
            if engines == "open":
                # the fan cowls, hinged up off the top centreline. Two panels
                # standing at about 55 deg is the shape that reads as "open"
                # from 300 m - it breaks the nacelle's silhouette, which a
                # closed one never does.
                for c in (1, -1):
                    ang = math.radians(55.0)
                    w = er * 1.35
                    v = [bm.verts.new((ex + 1.5, ey, ez + er)),
                         bm.verts.new((ex - 2.6, ey, ez + er)),
                         bm.verts.new((ex - 2.6,
                                       ey + c * w * math.sin(ang),
                                       ez + er + w * math.cos(ang))),
                         bm.verts.new((ex + 1.5,
                                       ey + c * w * math.sin(ang),
                                       ez + er + w * math.cos(ang)))]
                    try:
                        bm.faces.new(v)
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
    777-300ER - CNN Brasil states 777 maintenance is done at Guarulhos.

    WHAT THIS FUNCTION STILL BUILDS, AFTER PHASE 5
    ----------------------------------------------
    The five Aeroclube light aircraft, and a proxy for any airliner stand
    `fleet_placement.FLEET` maps to None. Every other stand gets one of the
    eleven real masters, instanced into each clip file by
    `fleet_placement.populate()` - so the ramp aeroplanes are no longer part of
    the shared field asset and `render_checks.py` populates the field before it
    looks at it. The stand table, the maintenance kit and the GSE are untouched
    and stay here: a dock is scenery, an aeroplane is not.

    There is no light-aircraft master in this repository, so the Aeroclube
    apron is the one place proxies survive on this field - and it is 180-280 m
    off a RWY 02 roll, which is close enough that it is worth saying out loud
    rather than leaving to be noticed."""
    # One proxy mesh per (type, engine state, jacked) actually used. The state
    # table is MRO_STANDS at the top of the operation section: this is a
    # heavy-check base with 16 aircraft in work at once, so most of the line is
    # APART - cowls open, an engine off, an airframe on jacks. Those states are
    # what fleet_placement.py had to reproduce on real models, and its docstring
    # records which of them survived the switch and which one had to be built.
    protos = {}

    def proto(key, engines, lift):
        k = (key, engines, lift > 0.0)
        if k not in protos:
            L, S_, F, R, GH = AC_TYPES[key]
            protos[k] = airliner_proxy(
                "SDSC_Proxy_%s_%s%s" % (key, engines, "_jk" if lift else ""),
                L, S_, F, R, GH, (P["ac_white"], P["latam_indigo"]),
                engines=engines, lift=lift)
        return protos[k]

    ga = ga_proxy("SDSC_Proxy_GA", (P["ga_white"], P["ga_trim"]))

    n = 0

    def place(key, x, y, heading_deg, tag, z=Z_MRO_PLATFORM,
              engines="on", lift=0.0):
        nonlocal n
        me, mef = proto(key, engines, lift)
        ob = bpy.data.objects.new("SDSC_AC_%s" % tag, me)
        ob.location = (x, y, z + Z_APRON)
        ob.rotation_euler = (0.0, 0.0, math.radians(90.0 - heading_deg))
        c_park.objects.link(ob)
        fin = bpy.data.objects.new("SDSC_ACFin_%s" % tag, mef)
        fin.parent = ob
        c_park.objects.link(fin)
        n += 1

    # THE ROW. Two aeroplanes nose-in on the hangar face at x = 931 - tails to
    # the runway, which is the side a RWY 02 departure sees - and the rest on
    # the apron's northern lobes, which run north-south and are what the mapped
    # polygon actually offers. All of them clear of way/708700156, the 44 x 42 m
    # hangar that stands in the middle of that apron.
    ENGINE_STATE = {"parked": "on", "jacked": "on", "docked": "on",
                    "cowls": "open", "engine_off": "off"}
    import fleet_placement as fleet
    kept = fleet.proxy_stands(MRO_STANDS + tuple(s[:6] for s
                                                 in OUTFIELD_STANDS))
    for (tag, key, x, y, hdg, state) in MRO_STANDS:
        if fleet.is_real(tag):
            continue
        place(key, x, y, hdg, tag, engines=ENGINE_STATE[state],
              lift=JACK_LIFT if state == "jacked" else 0.0)

    # the Aeroclube: light aircraft on the little apron, 180-280 m off the roll
    for i, (x, y) in enumerate(((-212.0, 456.0), (-212.0, 474.0),
                                (-212.0, 492.0), (-206.0, 318.0),
                                (-206.0, 288.0))):
        ob = bpy.data.objects.new("SDSC_GA_%d" % i, ga)
        ob.location = (x, y, Z_AEROCLUBE_APRON + Z_APRON)
        ob.rotation_euler = (0.0, 0.0, math.radians(90.0 - 271.0))
        c_park.objects.link(ob)
        n += 1
    # and the outfield stands - the mid-field widebody the 2013 photograph
    # shows - for whatever fleet_placement does not own
    for (tag, key, x, y, hdg, state, z) in OUTFIELD_STANDS:
        if fleet.is_real(tag):
            continue
        place(key, x, y, hdg, tag, z=z, engines=ENGINE_STATE[state],
              lift=JACK_LIFT if state == "jacked" else 0.0)
    print("parked proxies: %d (%d GA + %d airliner stands: %s)"
          % (n, 5, len(kept), ", ".join(kept) or "none - all real masters"))


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

    # THE TIERS ARE DE-CONFLICTED, and this is the second half of the fix that
    # baba4e6 started on the cane sheet. Same bug, one level up: two samplings
    # of one DEM covering the same ground, with nothing deciding which wins.
    #
    # `mask_inner` dropped coarse faces whose CENTRE fell inside the fine
    # tier's box. That does not tile, because the lattices are not aligned -
    # the near grid's nodes are at -15000 + 30i, the mid grid's at -50000 + 60k,
    # and no node is shared. It left a 20 m GAP on the low side and a 20 m
    # OVERLAP on the high side, and over a 200 m band there the two surfaces
    # differ by up to +6.35 / -6.67 m. That is exactly the "shallow ray past
    # 12 km alternates between Near and Mid" left open after phase 3; the same
    # arithmetic at the 60/180 m seam is worth +30.8 / -35.0 m.
    #
    # The fix is the cane fix's shape: make the overlap DELIBERATE (shrink the
    # mask by two coarse cells, so the coarse tier always underlaps and never
    # gaps) and then BIAS the coarse tier down by more than the measured worst
    # case, ramped back to zero outside so there is no cliff. 7 m over 1 500 m
    # at the 30/60 seam, 32 m over 6 000 m at the 60/180 seam. Like the cane,
    # the tiers share one material, so this always cost shading and never
    # colour - which is why it survived three phases.
    m = lt._meta()["grids"]
    g60, g30 = m["terrain_sdsc_60m"], m["terrain_sdsc_near_30m"]
    mk, sk = lt._dc(g60, 180.0 * stride_far, "far")
    lt.build("terrain_sdsc_far_180m", stride=stride_far,
             obj_name="SDSC_Terrain_Far", mask_inner=mk, sink=sk)
    mk, sk = lt._dc(g30, 60.0 * stride_mid, "mid")
    lt.build("terrain_sdsc_60m", stride=stride_mid, obj_name="SDSC_Terrain_Mid",
             mask_inner=mk, sink=sk)
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
            # The airliner proxies are gone (fleet_placement.py owns those
            # stands now); the Aeroclube light aircraft are what is left.
            ("SDSC_GA_0", cats[4], "low-poly high-wing single, Aeroclube - "
                                   "the one aircraft type with no master in "
                                   "this repository")):
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
