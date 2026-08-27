#!/usr/bin/env python3
"""Build the SBGR / Guarulhos scenery in Blender from the surveyed data here.

The scenery is a SHARED ASSET: built into its own .blend files under
``scenario_sbgr/`` and LINKED into each aircraft file, the way ``../scenario/``
works for Santiago and ``../scenario_sdsc/`` for Sao Carlos.

    blender -b --factory-startup -P scenario_sbgr/build_scenery.py -- --field
    blender -b --factory-startup -P scenario_sbgr/build_scenery.py -- --terrain

Outputs
    scenario_sbgr/sbgr_field.blend    the aerodrome: two runways + ICAO
                                      markings, 302 taxiways, the apron sheet,
                                      three terminals + jetbridges, the TWR,
                                      the LATAM + American hangars, cargo,
                                      BASP, the city ring, roads/rail/water,
                                      furniture, GSE, sun + sky
    scenario_sbgr/sbgr_terrain.blend  the three-tier heightfield (git-ignored)

Reference frame (identical in both files, and in README.md)
    local ENU tangent plane, WGS84 - lib/frame.py is the single source of truth
    origin  = published RWY 10L threshold, lat -23.4341667  lon -46.4825000
    x = East, y = North, z = Up, metres
    z = 0 at 750.0 m AMSL (published SBGR aerodrome elevation, 2461 ft)

FIVE THINGS ABOUT THIS FIELD THAT ARE NOT TRUE AT SDSC OR SCL
    1. TWO parallel runways, centrelines ~373 m apart, both on ~073.65 TRUE
       (designators 10/28 are magnetic; VAR 22 W). Aircraft hold between them.
    2. The field is LEVEL: 6 ft of published relief across 5 km. There is no
       graded-platform machinery here - but z = 0 is the AD elevation and every
       pavement sits 3-6 m BELOW it. Do not build anything at z = 0.
    3. The relative geometry is the OSM TRACING, not the published thresholds:
       DECEA publishes SBGR thresholds to whole seconds (+/- 30 m) while the
       tracing closes the published lengths to 1.5 m and holds the centrelines
       parallel to 0.015 deg (sbgr_aip_survey.json -> divergences). The scene
       runways are built ON the OSM centrelines so the 302 taxiways meet them;
       the published origin string remains the frame origin. OSM's THR 10L
       lands at (-2.7, 12.3) - 12.6 m from the origin, inside the rounding.
    4. The surround is a METROPOLIS of 1.3 M people, not cane. Phase 1 cut
       ~2 756 city footprints and ~8 550 minor streets on purpose; the
       surround round brought the streets and footprints BACK via the wider
       re-query (surround_osm.py -> sbgr_osm_surround.json) after the owner
       called the ring empty - landuse-tinted cells + street-mask fabric +
       real-footprint and procedural massing (build_city), and the serra
       forest over it all (build_serra_forest). See the CITY block below.
    5. The horizon is a RING (+0.12..+3.23 deg, never negative) and it is real
       terrain: the Cabucu/Cantareira wall carries the north, and a terrain
       mesh draws most of the skyline correctly (TERRAIN.md section 3). The
       tree line owed at SDSC is owed here only along the Baquirivu belt and
       inside the city fabric.

Data sources
    sbgr_osm.json            (c) OpenStreetMap contributors, ODbL 1.0
    sbgr_aip_survey.json     AISWEB/ROTAER + ADC + the four IAC charts
    sbgr_operations_sun.json solar geometry, computed in this repository
    sbgr_operations_wind.json ERA5 2021-2025 flow climatology
    terrain/*.npy            Copernicus DEM GLO-30 (+ SRTM control)
    refs/*.jpg               Wikimedia Commons, cited in sbgr_references.md,
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
# Survey constants. Everything in this block is sbgr_aip_survey.json or the
# OSM tracing in sbgr_osm.json. Nothing here is estimated.
# ---------------------------------------------------------------------------
TRACK_DEG = 73.65               # TRUE, adopted (survey bearing_adopted)
UX = math.sin(math.radians(TRACK_DEG))
UY = math.cos(math.radians(TRACK_DEG))
NX, NY = -UY, UX                # LEFT of a 10L roll = NNW (the terminal side)

RWY_WIDTH = 45.0                # ROTAER, both runways

# The two pavements, exactly as the OSM tracing puts them in this frame
# (endpoints of the merged runway ways; lengths close 3698.5 / 3000.0 m
# against the published 3700 / 3000). z at each threshold is the PUBLISHED
# IAC elevation converted to the 750 m datum; the fall is linear.
RWY_N = dict(                   # 10L/28R - the departure runway, 3700 x 45
    p0=(-88.4, -14.0),          # pavement SW end (OSM way/510285454)
    p1=(3460.7, 1026.5),        # pavement NE end (OSM way/510285450)
    thr_a=(89.6, 3638.3),       # THR 10L / THR 28R, along the pavement
    thr_z=(-4.76, -5.98),       # published 2445 / 2441 ft against 750 m
    disp=(90.0, 60.0),          # ROTAER displaced thresholds
    designators=("10L", "28R"),
    stopway=(60.0, 60.0),       # ADC, both ends
)
RWY_S = dict(                   # 10R/28L - CAT III, the landing runway, 3000 x 45
    p0=(-462.6, -513.0),        # pavement SW end (OSM way/1388686342)
    p1=(2415.9, 331.7),         # pavement NE end (OSM way/5367899)
    thr_a=(0.0, 2999.9),        # no displacement on the south runway
    thr_z=(-2.94, -4.46),       # published 2451 / 2446 ft
    disp=(0.0, 0.0),
    designators=("10R", "28L"),
    stopway=(60.0, 60.0),       # ADC; plus a 300 x 150 clearway at the 28L end
)

ARP_XY = (965.24, -153.87)

# ---------------------------------------------------------------------------
# THE Z-STACK - flat, for once (README section 4). No graded-function
# machinery: graded() below is the DEM shifted onto the published datum, with
# the runway strips forced to the published threshold line and each apron
# plateau held flat at its measured level.
#
# DEM_TO_PUB is MEASURED, not chosen: Copernicus reads the four thresholds at
# -6.00 / -8.82 / -4.19 / -6.47 against the published -4.76 / -5.98 / -2.94 /
# -4.46 - a consistent -1.2..-2.8 m offset (EGM2008 vs the -2.33 m geoid
# undulation is most of it). +1.84 is the mean; verify_levels() prints the
# residuals every build.
# ---------------------------------------------------------------------------
DEM_TO_PUB = 1.84

# Apron-zone plateaus: median of the Copernicus 30 m grid inside the mapped
# apron polygons of each zone, + DEM_TO_PUB. Measured 2026-08-26 (this build's
# own probe; sample counts in parentheses). The terminal platform genuinely
# sits ~4 m below the north runway - the field falls north, as the ADC's
# "high point = RWY 10R TDZ" says.
Z_TERM = -9.20        # terminal frontage + TECA west aprons  (DEM -11.04, 800+)
Z_NE_RAMP = -8.70     # Patio 9 + the 901-912 remote row      (DEM -10.52, 106)
Z_HGR = -8.70         # the LATAM hangar apron + both hangars. The DEM reads
                      # -6.93 here - but that is PRE-CONSTRUCTION ground
                      # (2011-14 epoch; the hangar and its apron are 2014-2020
                      # work), and a 3.6 m step against the touching Patio 9
                      # would make the hangar untowable. Built LEVEL with the
                      # remote ramp - the towpath is the constraint. DECLARED
                      # INFERENCE; the first build used the raw DEM figure and
                      # its own concrete check caught the cliff.
Z_CARGO_E = -8.50     # east cargo patios                     (DEM -10.11/-10.59)
Z_SIDERAL = -7.00     # Patio Sideral                         (DEM -8.90, 32)
Z_VIP = -0.20         # PATIO 12 (VIP), south side            (DEM -2.03, 68)
Z_BASP = -2.00        # BASP apron - CLAMPED: the DSM reads +1.3 here but that
                      # is hangar roofs in a 2011-14 surface model, and nothing
                      # published on this field stands above the 10R TDZ (z=0).
                      # Declared estimate.

ZONES = (
    # (x0, x1, y0, y1, z, fade_m)
    (-850.0, 1080.0, 300.0, 1160.0, Z_TERM, 120.0),
    (1900.0, 2600.0, 990.0, 1460.0, Z_NE_RAMP, 100.0),   # remote row + hangars
    (1250.0, 1700.0, 890.0, 1160.0, Z_CARGO_E, 100.0),
    (3040.0, 3330.0, 1270.0, 1480.0, Z_SIDERAL, 80.0),
    (-30.0, 250.0, -730.0, -490.0, Z_VIP, 80.0),
    (940.0, 1210.0, -490.0, -270.0, Z_BASP, 80.0),
)

Z_GROUND = 0.00        # offsets ABOVE the graded surface, the SCL/SDSC stack
Z_APRON = 0.05
Z_TAXI = 0.06
Z_SHOULDER = 0.07
Z_RUNWAY = 0.09
Z_MARK = 0.12

# ---------------------------------------------------------------------------
# Sun: 21 December, 17:30 local (UTC-3, no DST in Brazil since 2019).
# sbgr_operations_sun.json, sample "December 17:30 - the raking light":
# 16.46 deg up at 251.1 true - behind a south-west camera looking north-east
# at the LATAM hangar with the Cantareira behind, the composition phase 1
# found photographed in refs/latam_cargo_767_north_rwy_cantareira_2023.jpg.
# FLOW HONESTY (RECOGNITION.md section 3 trap 7): 12-15 local is when west
# flow is most likely (39-46% east); by 17:00 east flow is back to 62%
# (ERA5 2021-2025), so a 17:30 10L departure is the honest hour with the
# raking light. Recorded as the render-hour decision.
# ---------------------------------------------------------------------------
SUN_ELEV_DEG = 16.46
SUN_AZIM_DEG = 251.10

# Haze. Same Koschmieder node group as SCL/SDSC. Sao Paulo summer air is
# humid metropolitan haze - between SCL's smog basin (14 km) and SDSC's
# dry-season smoke (18 km). The 2023 photographs show the Cantareira wall at
# 4-5 km still green but flattened. V is INFERRED.
HAZE_VIS_KM = 22.0
HAZE_SCALE_H = 1200.0

# ---------------------------------------------------------------------------
# APPEARANCE INFERENCES - the constants a photograph would move.
#
# 1. THE LATAM HANGAR (OSM way/778050745, 136.8 x 92.2 m, long axis parallel
#    to the runways, doors facing SSE onto its own 32 892 m2 apron). NO
#    photograph of it exists and NO height is measured - the 2011-14 DSM
#    predates it (TERRAIN.md section 6). Everything vertical below is sized
#    from what it has to hold, not from a source:
#      a 777-300ER is 18.5 m tall -> door clear >= 20.5 m -> eave 26 m
#      one 777 bay + working margin  -> door 100 m of the 133 m SSE face
#    Branding: the ADC/AGMC print HANGAR LATAM and OSM names it Latam
#    Airlines; the facade carries the official-SVG lockup on an indigo band
#    because the charts say whose hangar it is - the same declared inference
#    SDSC's hangar 9 carries. Flip LATAM_HANGAR values when a photograph
#    surfaces; nothing else depends on them.
# 2. THE AMERICAN AIRLINES HANGAR (way/777394328, 178.6 x 95.0 m,
#    perpendicular). DSM floor +7.2 m - a FLOOR from a 30 m surface model
#    over a widebody hangar; built at 24 m eave (a 777/787 hangar door band),
#    UNBRANDED grey. Estimate.
# 3. THE TWR: ADC label georef (301, 1322) +/- 100 m, no OSM object, no
#    published height. Height from photograph proportion: in
#    refs/t2_tower_t3_construction_2013.jpg the shaft stands ~3.5-4x the T2
#    roofline (DSM floor 14.1 m -> ~20 m with plant), and
#    refs/tower_closeup_2024.jpg gives the shape - bare concrete shaft,
#    two-ring gallery, glazed cab, white radome ball. Cab roof ~55 m, ball
#    top ~61 m. ESTIMATE +/- 10 m, declared.
# 4. TERMINAL 3 opened 2014 - absent from the DSM. Built to Terminal 2's
#    measured band (T2 floor +14.1 -> built 20 m); the two are one complex
#    and every aerial shows them at the same scale. Estimate.
# ---------------------------------------------------------------------------
LATAM_HANGAR = dict(eave=26.0, ridge=30.0, door_w=100.0, door_h=20.5,
                    open_bay=30.0)      # one door leaf stands open
AA_HANGAR = dict(eave=24.0, ridge=27.5)
TOWER = dict(x=301.0, y=1322.0, shaft_w=7.5, gallery=(42.0, 47.0),
             cab=(48.0, 55.0), ball_z=58.5, ball_r=3.2)
H_T2 = 20.0           # DSM floor +14.1 (roofs smeared) + roof plant
H_T1 = 14.0           # DSM floor +10.8
H_T3 = 20.0           # NO DSM (opened 2014); built as T2's sibling. ESTIMATE
H_TECA = 11.0         # DSM floor +8..10

# Building heights by OSM type where nothing is measured (10 of ~140 carry
# any OSM tag). SCL-style defaults, ESTIMATES:
HEIGHT_BY_TYPE = {
    "hangar": 12.0, "warehouse": 11.0, "industrial": 9.0, "office": 13.0,
    "commercial": 8.0, "hotel": 22.0, "apartments": 16.0, "roof": 5.0,
    "storage_tank": 9.0, "public": 7.0, "chapel": 6.0, "train_station": 8.0,
    "yes": 6.0,
}
LEVEL_HEIGHT = 3.2

# Apron floodlight masts: GRU's "mast forest". Two designs photographed side
# by side in refs/remote_stands_masts_city_2026.jpg - a plain high-mast with a
# lamp ring, and a lattice tower with a rectangular lamp rack. HEIGHT is the
# international-apron high-mast band (30 m, as at SCL); no published figure.
MAST_H = 30.0

# ---------------------------------------------------------------------------
# THE CITY - the answer to phase 1's deliberate cut, and this build's one
# structural addition over SDSC. ~2 756 Guarulhos footprints and ~8 550 minor
# streets were cut from the extract; RECOGNITION.md trap 10 says the ring must
# be city anyway. Three layers at first; the SURROUND ROUND (the owner's
# verdict on the aerial tour was "o entorno esta todo muito vazio") widened
# every one of them and added the street-mask fabric and the serra forest:
#   1. LANDUSE TINT: every mapped landuse polygon rendered as 30 m cells
#      snapped to the near terrain tier's OWN lattice (same nodes, same DEM
#      sample), 0.5 m proud - so the two surfaces are parallel by construction
#      and cannot interleave (the SDSC cane-sheet lesson, applied one tier up).
#      PLUS, since the surround round: fabric tint on every 30 m cell the
#      MINOR-STREET MASK (below) calls urban and no landuse polygon covers -
#      Brazilian OSM maps streets far more completely than landuse, and the
#      Bonsucesso/Agua Chata flank north of the Baquirivu has ~50 km of
#      mapped streets under <1 km2 of mapped landuse.
#   2. MASSING, three sources in order of honesty: the 13 154 re-queried REAL
#      footprints (surround_osm.py) as min-area boxes; block-hashed boxes
#      inside the residential/commercial/industrial polygons within
#      CITY_REACH; and fabric boxes on urban street-mask cells nothing else
#      covered, out to FABRIC_REACH. Big mapped industrial polygons south of
#      the field build as the Cumbica LOGISTICS BELT - warehouse massing,
#      60-120 m sheds, not houses.
#   3. The mapped roads - now including the minor streets themselves - the
#      CPTM Line 13 rail and the Rio Baquirivu-Guacu, which are data.
# The DSM under all of it is roofs-and-canopy (TERRAIN.md section 8); the
# massing sits ON that surface, which double-counts a storey or two and is
# declared: at 1.5+ km under haze it reads as fabric, not as survey.
# ---------------------------------------------------------------------------
CITY_REACH = 4200.0       # polygon massing beyond this: tint + terrain + haze
FABRIC_REACH = 6500.0     # street-mask massing + real footprints reach
TINT_REACH = 9000.0       # tint cells; beyond this the terrain shading is it
CITY_BOX_BUDGET = 22000   # hard cap on massing structures (was 4200 before
                          # the surround round)
CITY_SEED = 20260826

ROAD_WIDTH = {            # metres, ESTIMATED - no width/lanes tags used
    "motorway": 11.0,         # Helio Smidt / Ayrton Senna / Dutra carriageways
    "motorway_link": 7.0,
    "trunk": 9.0,
    "primary": 9.0,
    "primary_link": 6.5,
    "secondary": 8.0,
    "secondary_link": 6.0,
    "tertiary": 6.5,
    "unclassified": 5.5,
    "residential": 5.5,
    "service": 4.5,
}
ROAD_SKIP = {"footway", "path", "steps", "cycleway", "pedestrian", "corridor"}
UNPAVED = {"unpaved", "dirt", "gravel", "ground", "compacted", "sand",
           "earth", "grass", "fine_gravel"}

# ---------------------------------------------------------------------------
# THE OPERATION. GRU is a working hub, not an MRO: the ramp population is
# turnarounds at gates, widebodies on the remote row, freighters at the cargo
# frontage and the 777 at its own hangar - aircraft INTACT, kit AROUND them.
#
# STAND ALLOCATION IS NOT PUBLISHED (sbgr_references.md section 6.4) and every
# assignment below is a declared reading:
#   * the 901 row widebodies: refs/ne_apron_tam_widebodies_dome_2013.jpg shows
#     exactly that - five TAM/American widebodies on the numbered remote
#     stands. A 2013 photograph read forward, not data.
#   * LATAM narrowbodies on the T2/T3 frontage: LATAM operates its domestic
#     wave from T2 and international from T3. Common knowledge, unpublished.
#   * LATAM Cargo 767s at stands 104/106 in front of TECA III.
#   * the 777-300ER at the hangar stand: the whole reason this base is third.
# Stand tags below are the PUBLISHED stand numbers from the OSM
# parking_position nodes (which mirror the PDC charts); positions are the
# mapped node coordinates.
#
# NON-LATAM TRAFFIC EXISTS AT GRU AND WE HAVE NO NON-LATAM MODELS. The honest
# rendering is neutral white proxies at a few gates the cameras never
# approach - declared here, built by build_parked_proxies().
# ---------------------------------------------------------------------------
HDG_IN = 343.65           # nose-in toward the terminals / the hangar line
                          # (perpendicular to the frontage; the mapped stand
                          # guidance at GRU is nose-in on the piers)

# tag, class, x, y, heading, zone-z   (positions = OSM parking_position nodes)
SBGR_STANDS = (
    # T2/T3 frontage - the LATAM narrowbody wave, tails to the runways
    ("G303", "narrow", 5.0, 613.0, HDG_IN, Z_TERM),
    ("G304", "narrow", -5.0, 670.0, HDG_IN, Z_TERM),
    ("G310", "narrow", 203.0, 639.0, HDG_IN, Z_TERM),
    ("G402", "narrow", 305.0, 585.0, HDG_IN, Z_TERM),
    ("G403", "narrow", 300.0, 640.0, HDG_IN, Z_TERM),
    ("G410", "narrow", 529.0, 684.0, HDG_IN, Z_TERM),
    ("G409", "narrow", 500.0, 761.0, HDG_IN, Z_TERM),
    # T3 widebodies (the first pick put two 60 m spans on 29 m centres and
    # the placement's own overlap check said so; re-picked at widebody pitch)
    ("G502", "wide", 600.0, 670.0, HDG_IN, Z_TERM),
    ("G510", "wide", 846.0, 727.0, HDG_IN, Z_TERM),
    # TECA III cargo frontage
    ("C104", "wide", -624.0, 523.0, HDG_IN, Z_TERM),
    ("C106", "wide", -616.0, 663.0, HDG_IN, Z_TERM),
    # the 901-912 remote row by the hangars (the 2013-photograph reading).
    # The mapped stands sit on ~33 m centres - narrowbody pitch - so the
    # widebodies take EVERY THIRD stand, which is what a mixed row does.
    ("R901", "heavy", 2206.0, 1088.0, HDG_IN, Z_NE_RAMP),
    ("R904", "wide", 2303.0, 1124.0, HDG_IN, Z_NE_RAMP),
    ("R907", "wide", 2405.0, 1142.0, HDG_IN, Z_NE_RAMP),
    ("R910", "wide", 2315.0, 1210.0, HDG_IN, Z_NE_RAMP),
    # the hangar stand - the 777 at its own base, centred on the OPEN bay
    # and held 18 m clear of the door line (the first pick put the nose
    # 23 m INSIDE the closed leaves; the hangar close-up check showed it)
    ("HGR", "heavy", 2343.0, 1275.0, HDG_IN, Z_HGR),
)

# Neutral white proxies - the honest non-LATAM presence. Stand numbers real,
# aircraft anonymous. All are 600+ m from every planned camera.
PROXY_STANDS = (
    ("P205", "wide", -315.0, 715.0, HDG_IN, Z_TERM),
    ("P208", "narrow", -96.0, 715.0, HDG_IN, Z_TERM),
    ("P601", "wide", 985.0, 726.0, HDG_IN, Z_TERM),
    ("P612", "narrow", 1241.0, 786.0, HDG_IN, Z_TERM),
)

# nominal envelopes for spacing/proxies: length, span, fin, fus radius, gear
AC_TYPES = {"narrow": (37.6, 35.8, 11.8, 2.0, 2.4),
            "wide": (54.9, 47.6, 15.9, 2.5, 3.0),
            "heavy": (73.9, 64.8, 18.5, 3.1, 3.4)}   # 777-300ER


# ---------------------------------------------------------------------------
# small helpers (shared shape with scenario_sdsc/build_scenery.py)
# ---------------------------------------------------------------------------
def argv_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


_DATA = None


def data():
    global _DATA
    if _DATA is None:
        with open(os.path.join(HERE, "sbgr_osm.json")) as fh:
            _DATA = json.load(fh)
    return _DATA


_SURROUND = None


def surround():
    """The surround re-query (surround_osm.py): 8 390 minor-street ways and
    13 154 real footprints the phase-1 extract cut. Regenerate with
    `python3 surround_osm.py`."""
    global _SURROUND
    if _SURROUND is None:
        with open(os.path.join(HERE, "sbgr_osm_surround.json")) as fh:
            _SURROUND = json.load(fh)
    return _SURROUND


class StreetMask:
    """A 50 m occupancy grid of the minor-street network: a cell is URBAN
    when a mapped street passes within ~50-100 m (one 4-neighbour dilation
    over the rasterized polylines - a 100 m Brazilian block's interior stays
    covered). This is the urbanization mask for the sectors where OSM
    landuse is thin: streets and buildings are mapped far more completely
    than landuse in Brazil, so where the streets are IS where the city is.
    Its complement above the forest line is where the serra is."""

    STEP = 50.0

    def __init__(self, streets):
        cells = set()
        for s in streets:
            pts = s["pts"]
            for a, b in zip(pts, pts[1:]):
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                n = max(1, int(L / 25.0))
                for k in range(n + 1):
                    t = k / n
                    cells.add((int(math.floor((a[0] + (b[0] - a[0]) * t)
                                              / self.STEP)),
                               int(math.floor((a[1] + (b[1] - a[1]) * t)
                                              / self.STEP))))
        grown = set(cells)
        for (i, j) in cells:
            grown.update(((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)))
        self.cells = grown

    def key(self, x, y):
        return (int(math.floor(x / self.STEP)),
                int(math.floor(y / self.STEP)))

    def urban(self, x, y):
        return self.key(x, y) in self.cells


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
    ring = [tuple(p[:2]) for p in poly]
    if len(ring) > 1 and math.dist(ring[0], ring[-1]) < 1e-6:
        ring = ring[:-1]
    out = []
    for p in ring:
        if not out or math.dist(out[-1], p) > 1e-6:
            out.append(p)
    return out


def bm_to_object(bm, name, mat, collection, smooth=False, roof_mat=None):
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


def _smoothstep(t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# runway parametrisation - two runways, one shape of code
# ---------------------------------------------------------------------------
class Runway:
    def __init__(self, spec):
        self.spec = spec
        self.p0 = spec["p0"]
        ux, uy, L = unit(*spec["p0"], *spec["p1"])
        self.u = (ux, uy)
        self.n = (-uy, ux)              # +lateral = LEFT of the 10-end roll
        self.len = L
        self.thr_a = spec["thr_a"]
        self.thr_z = spec["thr_z"]
        a0, a1 = spec["thr_a"]
        z0, z1 = spec["thr_z"]
        self.slope = (z1 - z0) / (a1 - a0)

    def z(self, a):
        return self.thr_z[0] + self.slope * (a - self.thr_a[0])

    def pt(self, a, l, dz=0.0):
        return (self.p0[0] + self.u[0] * a + self.n[0] * l,
                self.p0[1] + self.u[1] * a + self.n[1] * l,
                self.z(a) + dz)

    def to_al(self, x, y):
        dx, dy = x - self.p0[0], y - self.p0[1]
        return dx * self.u[0] + dy * self.u[1], dx * self.n[0] + dy * self.n[1]


RN = Runway(RWY_N)
RS = Runway(RWY_S)


# ---------------------------------------------------------------------------
# THE GROUND SURFACE - flat-field edition. graded() = DEM + DEM_TO_PUB, with
# the two runway strips forced to the published threshold lines and each apron
# zone held flat. Total relief inside the fence: ~9 m. No SDSC platform drops.
# ---------------------------------------------------------------------------
class Ground:
    def __init__(self):
        import numpy as np
        meta = json.load(open(os.path.join(HERE, "terrain",
                                           "terrain_meta.json")))
        self.m = meta["grids"]["terrain_sbgr_near_30m"]
        self.Z = np.load(os.path.join(HERE, "terrain", self.m["file"]))
        self.ny, self.nx = self.Z.shape

    def dem(self, x, y):
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
        z = self.dem(x, y) + DEM_TO_PUB
        # runway strips: full weight to 90 m either side, gone by 240 m, and
        # tapered off the pavement ends over 200 m
        for R in (RN, RS):
            a, l = R.to_al(x, y)
            w = 1.0 - _smoothstep((abs(l) - 90.0) / 150.0)
            if a < 0.0:
                w *= 1.0 - _smoothstep(-a / 200.0)
            elif a > R.len:
                w *= 1.0 - _smoothstep((a - R.len) / 200.0)
            if w > 0.0:
                z = z * (1.0 - w) + R.z(a) * w
        # apron-zone plateaus. INSIDE a box the plateau is exact - the first
        # build let a neighbouring zone's fade lift the pad 2.6 m above the
        # Patio 9 fill and the fleet's own ray-cast caught an aeroplane on
        # grass. Outside, fades blend as before.
        for (x0, x1, y0, y1, zz, fade) in ZONES:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return zz
        for (x0, x1, y0, y1, zz, fade) in ZONES:
            dx = max(x0 - x, 0.0, x - x1)
            dy = max(y0 - y, 0.0, y - y1)
            w = 1.0 - _smoothstep(math.hypot(dx, dy) / fade)
            if w > 0.0:
                z = z * (1.0 - w) + zz * w
        return z


G = None


def gz(x, y, dz=0.0):
    return G.graded(x, y) + dz


def zone_z(x, y):
    """The flat plateau constant for a point, or None outside every zone."""
    for (x0, x1, y0, y1, zz, fade) in ZONES:
        if x0 - 1.0 < x < x1 + 1.0 and y0 - 1.0 < y < y1 + 1.0:
            return zz
    return None


class RingField:
    """Signed distance to the aerodrome boundary RING (positive inside),
    sampled from a 30 m numpy grid built once. The first plan check showed
    why this exists: the pad was laid over the boundary's BOUNDING BOX, a
    5.8 x 4.4 km rectangle that buried the entire city ring under infield
    grass - the exact empty-ring failure RECOGNITION.md trap 10 names. The
    pad, the city sheets and surface_z all clip to the RING through this."""

    def __init__(self, ring):
        import numpy as np
        self.step = 30.0
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        self.x0 = min(xs) - 900.0
        self.y0 = min(ys) - 900.0
        nx = int((max(xs) - min(xs) + 1800.0) / self.step) + 2
        ny = int((max(ys) - min(ys) + 1800.0) / self.step) + 2
        gx = self.x0 + np.arange(nx) * self.step
        gy = self.y0 + np.arange(ny) * self.step
        X, Y = np.meshgrid(gx, gy)
        P = np.stack([X.ravel(), Y.ravel()], axis=1)
        dmin = np.full(len(P), 1e18)
        inside = np.zeros(len(P), dtype=bool)
        n = len(ring)
        for i in range(n):
            ax, ay = ring[i]
            bx, by = ring[(i + 1) % n]
            ex, ey = bx - ax, by - ay
            L2 = ex * ex + ey * ey
            if L2 < 1e-12:
                continue
            t = np.clip(((P[:, 0] - ax) * ex + (P[:, 1] - ay) * ey) / L2,
                        0.0, 1.0)
            dx = P[:, 0] - (ax + t * ex)
            dy = P[:, 1] - (ay + t * ey)
            dmin = np.minimum(dmin, dx * dx + dy * dy)
            cond = (ay > P[:, 1]) != (by > P[:, 1])
            xx = ax + (P[:, 1] - ay) * ex / (ey if abs(ey) > 1e-12 else 1e-12)
            inside ^= cond & (P[:, 0] < xx)
        d = np.sqrt(dmin)
        d[~inside] *= -1.0
        self.D = d.reshape(ny, nx).astype(np.float32)
        self.ny, self.nx = ny, nx

    def dist(self, x, y):
        """Signed distance, positive INSIDE the fence. Clamped bilinear."""
        fi = (x - self.x0) / self.step
        fj = (y - self.y0) / self.step
        i = min(max(int(fi), 0), self.nx - 2)
        j = min(max(int(fj), 0), self.ny - 2)
        a = min(max(fi - i, 0.0), 1.0)
        b = min(max(fj - j, 0.0), 1.0)
        D = self.D
        v = (D[j, i] * (1 - a) * (1 - b) + D[j, i + 1] * a * (1 - b) +
             D[j + 1, i] * (1 - a) * b + D[j + 1, i + 1] * a * b)
        # beyond the sampled grid everything is far outside
        if fi < 0 or fj < 0 or fi > self.nx - 1 or fj > self.ny - 1:
            return -9999.0
        return float(v)


RING_F = None      # the single RingField, made with Ground


def ring_dist(x, y):
    return RING_F.dist(x, y)


_PAD = None


def pad_box():
    global _PAD
    if _PAD is None:
        ring = dedupe_ring(data()["aerodrome_boundary_xy_m"][0])
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        _PAD = (min(xs) - 400.0, max(xs) + 400.0,
                min(ys) - 400.0, max(ys) + 400.0)
    return _PAD


def surface_z(x, y, dz=0.0):
    """Height of the ground a camera SEES, anywhere. Inside the fence RING it
    is the graded surface; outside it is the raw DEM + 0.45, where the
    terrain tier and the city sheets sit; the two blend over the pad's own
    150 m skirt outside the ring. The SDSC surface_z, re-cut to the ring."""
    d = ring_dist(x, y)
    if d >= 0.0:
        return G.graded(x, y) + dz
    if d > -150.0:
        t = _smoothstep(-d / 150.0)
        return (G.graded(x, y) - 0.8 * t) * (1.0 - t) + \
               (G.dem(x, y) + 0.45) * t + dz
    return G.dem(x, y) + 0.45 + dz


def resample(pts, step):
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


def prism(bm, ring, z0_rel, z1_rel, base=None):
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
            store.append(bm.verts.new(
                (px, py, (flat_z + dz) if flat_z is not None
                 else gz(px, py, dz))))
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


def obox(bm, cx, cy, z0, z1, length, width, hdg_deg):
    a = math.radians(hdg_deg)
    ux, uy = math.sin(a), math.cos(a)
    px, py = uy, -ux
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


def post(bm, x, y, r, z0, z1):
    box(bm, x - r, x + r, y - r, y + r, z0, z1)


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


def _cells(ring, step, ox, oy):
    """Lattice cell centres inside `ring`, on the lattice (ox+i*step,
    oy+j*step). Snapping to a shared lattice is what stops two samplings of
    one DEM from interleaving - the SDSC cane lesson."""
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
          ((cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h),
           (cx - h, cy + h))]
    try:
        bm.faces.new(vs)
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# materials, with the atmospheric-haze term baked in (SCL/SDSC recipe)
# ---------------------------------------------------------------------------
def haze_group():
    """tau(d, z) = beta0 * d * (H/z) * (1 - exp(-z/H)), beta0 = 3.912 / V.
    Identical maths to the SCL/SDSC groups, including the camera-height fix
    (the exponential integral uses the HIGHER end of the ray). V = 16 km:
    humid metropolitan summer haze, between SCL's 14 and SDSC's 18. Airlight
    is warm toward the low WSW sun and pale blue-grey away from it - the 2023
    photographs show the Cantareira flattened but still green at 4-5 km."""
    g = bpy.data.node_groups.get("SBGR_Haze")
    if g:
        return g
    g = bpy.data.node_groups.new("SBGR_Haze", "ShaderNodeTree")
    g.interface.new_socket("Shader", in_out="INPUT",
                           socket_type="NodeSocketShader")
    g.interface.new_socket("Shader", in_out="OUTPUT",
                           socket_type="NodeSocketShader")
    nin = g.nodes.new("NodeGroupInput"); nin.location = (-1400, 200)
    nout = g.nodes.new("NodeGroupOutput"); nout.location = (600, 0)

    geo = g.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1400, -200)
    sep = g.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-1200, -260)
    g.links.new(geo.outputs["Position"], sep.inputs[0])
    cam0 = g.nodes.new("ShaderNodeCameraData"); cam0.location = (-1400, -700)
    inc = g.nodes.new("ShaderNodeSeparateXYZ"); inc.location = (-1200, -700)
    g.links.new(geo.outputs["Incoming"], inc.inputs[0])

    zc = g.nodes.new("ShaderNodeMath"); zc.operation = "MULTIPLY_ADD"
    zc.location = (-1100, -700)
    g.links.new(inc.outputs["Z"], zc.inputs[0])
    g.links.new(cam0.outputs["View Distance"], zc.inputs[1])
    g.links.new(sep.outputs["Z"], zc.inputs[2])
    zhi = g.nodes.new("ShaderNodeMath"); zhi.operation = "MAXIMUM"
    zhi.location = (-1180, -400)
    g.links.new(sep.outputs["Z"], zhi.inputs[0])
    g.links.new(zc.outputs[0], zhi.inputs[1])

    # z is measured from the AD datum and the pavements sit below it; lift
    # into "height above the lowest scenery" before the exponential.
    lift = g.nodes.new("ShaderNodeMath"); lift.operation = "ADD"
    lift.inputs[1].default_value = 40.0; lift.location = (-1100, -260)
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

    inc2 = g.nodes.new("ShaderNodeNewGeometry"); inc2.location = (-1400, 520)
    flat = g.nodes.new("ShaderNodeVectorMath"); flat.operation = "MULTIPLY"
    flat.inputs[1].default_value = (-1.0, -1.0, 0.0); flat.location = (-1180, 520)
    g.links.new(inc2.outputs["Incoming"], flat.inputs[0])
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
    el[0].color = (0.360, 0.390, 0.450, 1.0)      # away from the sun
    el[1].position = 0.60
    el[1].color = (0.480, 0.465, 0.445, 1.0)
    e2 = ramp.color_ramp.elements.new(0.88)
    e2.color = (0.860, 0.660, 0.430, 1.0)
    e3 = ramp.color_ramp.elements.new(1.0)
    e3.color = (0.990, 0.760, 0.470, 1.0)         # into the low WSW sun
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
    sky.sun_disc = False
    sky.sun_intensity = 1.0
    sky.sun_size = math.radians(0.545)
    sky.altitude = 750
    # December in Sao Paulo is the WET season: more air, less smoke than the
    # SDSC dry-season rig - a milky-blue summer sky, not a smoky one. The
    # aerosol is still metropolitan. Values are inference on the same scale
    # SDSC's were (air 1.05 / aerosol 4.6 there).
    sky.air_density = 1.30
    sky.aerosol_density = 3.00
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
    if metal < 0.1:
        try:
            bsdf.inputs["Specular IOR Level"].default_value = 0.18
        except KeyError:
            pass
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
    # matte ground: the first horizon renders mirrored the bright summer sky
    # at grazing incidence and the W/E pavements rendered as snow - the SCL
    # lesson, fixed at the material this time
    try:
        bsdf.inputs["Specular IOR Level"].default_value = 0.18
    except KeyError:
        pass
    return m, nt, out, bsdf


def aged_pavement_material(name, base, aged, stain, patch_scale, rough=0.86):
    """Weathered concrete / asphalt patchwork - the SDSC recipe with the red
    dust film left OFF: GRU's shoulders are grass and city, not latosol
    tracks, and the 2023 photographs show grey pavement, not red-dusted."""
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
    nt.links.new(mix2.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    m.diffuse_color = (*base, 1.0)
    return m


def runway_material(name, R, heavy=True):
    """Weathered runway asphalt with rubber about the centreline, in THIS
    runway's own along/lateral frame. GRU is the busiest international runway
    pair in South America and refs/rwy28l_rollout_terminals_tower_2023.jpg
    shows heavy rubber and grooving - the TDZ bands are deeper than SDSC's.
    Amplitudes read qualitatively off the photographs."""
    m, nt, out, bsdf = _blank(name, 0.80)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1200, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    X, Y = sep.outputs["X"], sep.outputs["Y"]
    xr = _nm(nt, "SUBTRACT", X, R.p0[0])
    yr = _nm(nt, "SUBTRACT", Y, R.p0[1])
    a = _nm(nt, "ADD", _nm(nt, "MULTIPLY", xr, R.u[0]),
            _nm(nt, "MULTIPLY", yr, R.u[1]))
    l = _nm(nt, "ADD", _nm(nt, "MULTIPLY", xr, R.n[0]),
            _nm(nt, "MULTIPLY", yr, R.n[1]))

    lg = _nm(nt, "MULTIPLY", l, 0.2)
    gauss = _nm(nt, "EXPONENT",
                _nm(nt, "MULTIPLY", _nm(nt, "MULTIPLY", lg, lg), -1.0))
    amp0 = 0.30 if heavy else 0.22
    thr0, thr1 = R.thr_a
    aa = _nm(nt, "SUBTRACT", a, thr0)
    tdz_a = _nm(nt, "MULTIPLY", _sm(nt, aa, 60.0, 240.0),
                _sm(nt, aa, 700.0, 1400.0, 1.0, 0.0))
    ar = _nm(nt, "SUBTRACT", thr1, a)
    tdz_b = _nm(nt, "MULTIPLY", _sm(nt, ar, 60.0, 240.0),
                _sm(nt, ar, 700.0, 1400.0, 1.0, 0.0))
    amp = _nm(nt, "ADD", amp0,
              _nm(nt, "MULTIPLY", _nm(nt, "ADD", tdz_a, tdz_b), 0.85))
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
    mix_b.inputs["Color1"].default_value = (0.058, 0.058, 0.056, 1.0)
    mix_b.inputs["Color2"].default_value = (0.105, 0.102, 0.095, 1.0)
    nt.links.new(_sm(nt, n_big.outputs["Fac"], 0.35, 0.65), mix_b.inputs["Fac"])
    mix_r = nt.nodes.new("ShaderNodeMixRGB")
    mix_r.inputs["Color2"].default_value = (0.016, 0.016, 0.017, 1.0)
    nt.links.new(mix_b.outputs[0], mix_r.inputs["Color1"])
    nt.links.new(rub, mix_r.inputs["Fac"])
    nt.links.new(mix_r.outputs[0], bsdf.inputs["Base Color"])
    nt.links.new(_nm(nt, "SUBTRACT", 0.84, _nm(nt, "MULTIPLY", rub, 0.25)),
                 bsdf.inputs["Roughness"])
    _finish(nt, bsdf, out, 840)
    m.diffuse_color = (0.075, 0.074, 0.070, 1.0)
    return m


def worn_marking_material(name, base):
    m, nt, out, bsdf = _blank(name, 0.70)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-900, 0)
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 0.010
    n1.inputs["Detail"].default_value = 2.0
    nt.links.new(geo.outputs["Position"], n1.inputs["Vector"])
    w1 = _sm(nt, n1.outputs["Fac"], 0.30, 0.70, 0.62, 1.0)
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 0.35
    n2.inputs["Detail"].default_value = 2.0
    nt.links.new(geo.outputs["Position"], n2.inputs["Vector"])
    w2 = _sm(nt, n2.outputs["Fac"], 0.25, 0.75, 0.82, 1.02)
    w = _nm(nt, "MULTIPLY", w1, w2)
    lc = nt.nodes.new("ShaderNodeCombineColor")
    for i, ch in enumerate(base):
        nt.links.new(_nm(nt, "MULTIPLY", w, ch), lc.inputs[i])
    nt.links.new(lc.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    m.diffuse_color = (*base, 1.0)
    return m


def infield_material(name, scale=1.0):
    """The infield: GREEN December grass over red-brown Sao Paulo soil.

    The anti-SDSC palette: this render hour is the WET season (21 December),
    and every 2023 photograph shows saturated green grass between the
    pavements with the red soil showing only on worn patches and the graded
    strips. Values read qualitatively off
    refs/latam_cargo_767_north_rwy_cantareira_2023.jpg and
    refs/city_fence_taxiway_2023.jpg."""
    m, nt, out, bsdf = _blank(name, 0.95)
    tex = nt.nodes.new("ShaderNodeTexCoord"); tex.location = (-1000, 0)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.location = (-860, 0)
    mp.inputs["Scale"].default_value = (0.001, 0.001, 0.001)
    nt.links.new(tex.outputs["Object"], mp.inputs["Vector"])

    grass = (0.062, 0.098, 0.026)
    grass_dry = (0.105, 0.118, 0.040)
    soil = (0.200, 0.096, 0.048)
    soil_dark = (0.120, 0.052, 0.026)

    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 2.8 * scale
    n1.inputs["Detail"].default_value = 5.0
    n1.inputs["Roughness"].default_value = 0.55
    nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    g_mix = nt.nodes.new("ShaderNodeMixRGB")
    g_mix.inputs["Color1"].default_value = (*grass, 1.0)
    g_mix.inputs["Color2"].default_value = (*grass_dry, 1.0)
    nt.links.new(_sm(nt, n1.outputs["Fac"], 0.35, 0.68), g_mix.inputs["Fac"])

    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 16.0 * scale
    n2.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], n2.inputs["Vector"])
    s_mix = nt.nodes.new("ShaderNodeMixRGB")
    s_mix.inputs["Color1"].default_value = (*soil, 1.0)
    s_mix.inputs["Color2"].default_value = (*soil_dark, 1.0)
    nt.links.new(_sm(nt, n2.outputs["Fac"], 0.30, 0.70), s_mix.inputs["Fac"])

    n3 = nt.nodes.new("ShaderNodeTexNoise")
    n3.inputs["Scale"].default_value = 7.0 * scale
    n3.inputs["Detail"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], n3.inputs["Vector"])
    soil_fac = _sm(nt, n3.outputs["Fac"], 0.55, 0.82, 0.02, 0.75)
    top = nt.nodes.new("ShaderNodeMixRGB")
    nt.links.new(g_mix.outputs[0], top.inputs["Color1"])
    nt.links.new(s_mix.outputs[0], top.inputs["Color2"])
    nt.links.new(soil_fac, top.inputs["Fac"])

    n4 = nt.nodes.new("ShaderNodeTexNoise")
    n4.inputs["Scale"].default_value = 48.0 * scale
    n4.inputs["Detail"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], n4.inputs["Vector"])
    lum = nt.nodes.new("ShaderNodeMapRange")
    lum.inputs["To Min"].default_value = 0.72
    lum.inputs["To Max"].default_value = 1.14
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
    m.diffuse_color = (*grass, 1.0)
    return m


def ribbed_material(name, colour, pitch=1.0, rough=0.62):
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


def city_material(name, base, vary=0.35, cell=42.0, rough=0.90):
    """City-fabric tint: a per-block value hash so the cells read as blocks of
    different buildings, not as a painted sheet."""
    m, nt, out, bsdf = _blank(name, rough)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1100, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    cx = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", sep.outputs["X"], cell))
    cy = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", sep.outputs["Y"], cell * 0.83))
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(cx, cmb.inputs[0])
    nt.links.new(cy, cmb.inputs[1])
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"
    nt.links.new(cmb.outputs[0], wn.inputs["Vector"])
    lum = nt.nodes.new("ShaderNodeMapRange")
    lum.inputs["To Min"].default_value = 1.0 - vary
    lum.inputs["To Max"].default_value = 1.0 + vary
    nt.links.new(wn.outputs["Value"], lum.inputs["Value"])
    lc = nt.nodes.new("ShaderNodeCombineColor")
    for i in range(3):
        nt.links.new(lum.outputs["Result"], lc.inputs[i])
    base_c = nt.nodes.new("ShaderNodeMixRGB"); base_c.blend_type = "MULTIPLY"
    base_c.inputs["Fac"].default_value = 1.0
    base_c.inputs["Color1"].default_value = (*base, 1.0)
    nt.links.new(lc.outputs[0], base_c.inputs["Color2"])
    nt.links.new(base_c.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    m.diffuse_color = (*base, 1.0)
    return m


def palette():
    """Colours are linear-Rec709, read QUALITATIVELY off the photographs in
    sbgr_references.md section 2. They are not spectrophotometric."""
    return dict(
        shoulder=mat("SBGR_Shoulder", (0.100, 0.096, 0.085), 0.90),
        concrete=aged_pavement_material("SBGR_ApronConcrete",
                                        (0.200, 0.196, 0.184),
                                        (0.245, 0.238, 0.222),
                                        (0.132, 0.128, 0.120), 0.020, 0.86),
        taxi=aged_pavement_material("SBGR_TaxiwayAsphalt",
                                    (0.085, 0.084, 0.078),
                                    (0.130, 0.126, 0.115),
                                    (0.055, 0.054, 0.050), 0.017, 0.85),
        white=worn_marking_material("SBGR_MarkingWhite", (0.520, 0.518, 0.498)),
        yellow=worn_marking_material("SBGR_MarkingYellow", (0.420, 0.268, 0.022)),
        red=mat("SBGR_MarkingRed", (0.320, 0.030, 0.020), 0.70),
        # the apron lane edges at GRU are PINK-EDGED in
        # refs/t3_apron_747_a330_masts_2023.jpg
        pink=mat("SBGR_MarkingPink", (0.480, 0.130, 0.160), 0.70),
        infield=infield_material("SBGR_Infield"),
        clad=ribbed_material("SBGR_Cladding", (0.250, 0.252, 0.248), 1.1),
        clad_pale=ribbed_material("SBGR_CladdingPale", (0.300, 0.300, 0.295), 1.1),
        clad_warm=ribbed_material("SBGR_CladdingWarm", (0.225, 0.218, 0.200), 1.1),
        roof_grey=mat("SBGR_RoofGrey", (0.160, 0.163, 0.161), 0.66),
        roof_pale=mat("SBGR_RoofPale", (0.210, 0.211, 0.205), 0.60),
        roof_dark=mat("SBGR_RoofDark", (0.085, 0.086, 0.088), 0.72),
        band_indigo=mat("SBGR_LATAM_Band", (0.0085, 0.0035, 0.0740), 0.55),
        band_grey=mat("SBGR_AABand", (0.070, 0.072, 0.078), 0.60),
        latam_indigo=mat("SBGR_LATAM_Indigo", (0.0085, 0.0035, 0.0740), 0.55),
        latam_coral=mat("SBGR_LATAM_Coral", (0.847, 0.008, 0.082), 0.45),
        latam_white=mat("SBGR_LATAM_White", (0.700, 0.702, 0.715), 0.42),
        hangar_dark=mat("SBGR_HangarInterior", (0.022, 0.020, 0.019), 0.90),
        floor_pale=mat("SBGR_HangarFloor", (0.300, 0.298, 0.290), 0.35),
        frame_steel=mat("SBGR_SpaceFrameSteel", (0.240, 0.246, 0.252), 0.55),
        wall_white=mat("SBGR_WallRender", (0.390, 0.386, 0.372), 0.80),
        wall_cream=mat("SBGR_WallCream", (0.330, 0.310, 0.268), 0.82),
        glass=mat("SBGR_Glass", (0.028, 0.042, 0.048), 0.16, metal=0.35),
        glass_band=mat("SBGR_TerminalGlass", (0.022, 0.032, 0.040), 0.18,
                       metal=0.40),
        steel=mat("SBGR_Steel", (0.320, 0.330, 0.340), 0.42, metal=0.85),
        mast=mat("SBGR_Mast", (0.470, 0.472, 0.478), 0.52),
        concrete_bare=mat("SBGR_BareConcrete", (0.175, 0.170, 0.158), 0.88),
        radome=mat("SBGR_Radome", (0.640, 0.642, 0.650), 0.42),
        foliage=mat("SBGR_Foliage", (0.042, 0.072, 0.022), 0.92),
        foliage2=mat("SBGR_FoliageDeep", (0.030, 0.055, 0.018), 0.92),
        trunk=mat("SBGR_TreeTrunk", (0.042, 0.033, 0.024), 0.92),
        # the surround round's ONE new vegetation material: closed-canopy
        # mata atlantica for the Cantareira/Cabucu wall - near-black green,
        # darker than either foliage tint (the 2023 refs show a green WALL)
        serra=mat("SBGR_SerraCanopy", (0.016, 0.034, 0.011), 0.95),
        fence=mat("SBGR_FenceMesh", (0.060, 0.062, 0.064), 0.60),
        jet_body=mat("SBGR_Jetbridge", (0.360, 0.362, 0.368), 0.55),
        jet_dark=mat("SBGR_JetbridgeDark", (0.060, 0.062, 0.066), 0.60),

        # --- the surround --------------------------------------------
        road_paved=mat("SBGR_RoadAsphalt", (0.046, 0.046, 0.045), 0.78),
        road_dirt=mat("SBGR_RoadDirt", (0.260, 0.120, 0.058), 0.92),
        rail_bed=mat("SBGR_RailBed", (0.090, 0.082, 0.072), 0.90),
        rail_deck=mat("SBGR_RailViaduct", (0.190, 0.188, 0.182), 0.85),
        water=mat("SBGR_Water", (0.030, 0.042, 0.036), 0.16, metal=0.10),
        # the Baquirivu runs murky brown-green through the city
        # city fabric tints (build_city) - per-block value hash
        city_res=city_material("SBGR_CityResidential", (0.165, 0.128, 0.100)),
        city_fav=city_material("SBGR_CityHillside", (0.170, 0.096, 0.062),
                               vary=0.45, cell=26.0),
        city_ind=city_material("SBGR_CityIndustrial", (0.150, 0.150, 0.146),
                               vary=0.30, cell=70.0),
        city_com=city_material("SBGR_CityCommercial", (0.140, 0.135, 0.128),
                               vary=0.30, cell=55.0),
        city_green=mat("SBGR_CityGreen", (0.055, 0.082, 0.028), 0.94),
        city_bare=mat("SBGR_CityBareLot", (0.215, 0.104, 0.052), 0.94),
        house_a=mat("SBGR_HouseRenderA", (0.330, 0.318, 0.285), 0.86),
        house_b=mat("SBGR_HouseRenderB", (0.290, 0.245, 0.195), 0.86),
        house_brick=mat("SBGR_HouseBrick", (0.240, 0.115, 0.062), 0.90),
        tile_red=mat("SBGR_RoofTile", (0.160, 0.062, 0.038), 0.90),
        roof_fiber=mat("SBGR_RoofFiberCement", (0.185, 0.180, 0.170), 0.80),
        midrise=mat("SBGR_MidriseConcrete", (0.260, 0.252, 0.238), 0.80),
        # the surround round's ONE new built material: the Cumbica logistics
        # belt's big white sheds (every airport-adjacent aerial shows them)
        warehouse=mat("SBGR_WarehouseShed", (0.300, 0.306, 0.302), 0.62),

        # --- the operation -------------------------------------------
        gse_white=mat("SBGR_GSEWhite", (0.480, 0.482, 0.478), 0.55),
        gse_yellow=mat("SBGR_GSEYellow", (0.410, 0.250, 0.020), 0.58),
        gse_dark=mat("SBGR_GSEDark", (0.045, 0.046, 0.050), 0.60),
        gse_red=mat("SBGR_GSERed", (0.300, 0.028, 0.024), 0.60),
        container=mat("SBGR_Container", (0.300, 0.300, 0.292), 0.72),
        dolly=mat("SBGR_CargoDolly", (0.110, 0.112, 0.118), 0.65),
        uld=mat("SBGR_ULD", (0.360, 0.362, 0.370), 0.50),
        bus=mat("SBGR_ApronBus", (0.420, 0.424, 0.430), 0.45),
        ac_white=mat("SBGR_AircraftWhite", (0.640, 0.643, 0.655), 0.30),
        ac_grey=mat("SBGR_AircraftGrey", (0.175, 0.185, 0.195), 0.35),
    )


# ---------------------------------------------------------------------------
# the runways, and ICAO Annex 14 markings.
#
# UNLIKE SDSC, most of this is PUBLISHED: the ADC gives strips, stopways, the
# clearway and the approach lighting; ROTAER gives the displacements; the IAC
# charts give the threshold elevations. What is still applied by me is the
# Annex 14 PATTERN detail (stripe counts, TDZ pairs, glyph shapes) - the
# standard for a 45 m runway with LDA 3000-3640, plus the 2019-renumbered
# designators 10/28 (RECOGNITION.md trap 2: old photographs say 09/27).
# ---------------------------------------------------------------------------
GLYPHS = {
    "0": [(0.0, 0.0, 4.5, 1.5), (0.0, 7.5, 4.5, 9.0), (0.0, 0.0, 1.5, 9.0),
          (3.0, 0.0, 4.5, 9.0)],
    "1": [(1.5, 0.0, 3.0, 9.0), (0.2, 6.6, 1.5, 9.0)],
    "2": [(0.0, 7.5, 4.5, 9.0), (3.0, 4.5, 4.5, 7.5), (0.0, 3.9, 4.5, 5.1),
          (0.0, 0.0, 1.5, 4.5), (0.0, 0.0, 4.5, 1.5)],
    "8": [(0.0, 0.0, 4.5, 1.5), (0.0, 7.5, 4.5, 9.0), (0.0, 0.0, 1.5, 9.0),
          (3.0, 0.0, 4.5, 9.0), (0.0, 3.9, 4.5, 5.1)],
    "L": [(0.0, 0.0, 1.5, 9.0), (0.0, 0.0, 4.5, 1.5)],
    "R": [(0.0, 0.0, 1.5, 9.0), (0.0, 7.5, 4.5, 9.0), (3.0, 4.7, 4.5, 7.5),
          (0.0, 3.9, 4.5, 5.1), (3.0, 0.0, 4.5, 3.9)],
}
GLYPH_W = 4.5
GLYPH_GAP = 1.5


def paint_glyphs(bm, R, text, along0, lateral_centre, direction, z_off):
    """Characters on the pavement, read from the approaching threshold.
    direction = +1 at the 10 end, -1 at the 28 end. The glyph's local +x runs
    to the PILOT'S RIGHT = -lateral on the roll - the SDSC mirror lesson."""
    total = len(text) * GLYPH_W + (len(text) - 1) * GLYPH_GAP
    x0 = -total * 0.5
    for ch in text:
        for (gx0, gy0, gx1, gy1) in GLYPHS[ch]:
            corners = [(gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1)]
            vs = []
            for (cx, cy) in corners:
                lat = lateral_centre - direction * (x0 + cx)
                a = along0 + direction * cy
                vs.append(bm.verts.new(R.pt(a, lat, z_off)))
            try:
                bm.faces.new(vs)
            except ValueError:
                pass
        x0 += GLYPH_W + GLYPH_GAP


def strip(bm, R, a0, a1, l0, l1, dz, steps=1):
    for k in range(steps):
        b0 = a0 + (a1 - a0) * k / steps
        b1 = a0 + (a1 - a0) * (k + 1) / steps
        vs = [bm.verts.new(R.pt(a, l, dz))
              for (a, l) in ((b0, l0), (b1, l0), (b1, l1), (b0, l1))]
        try:
            bm.faces.new(vs)
        except ValueError:
            pass


def build_runway(R, bm_pave, bm_sh, bm_mark):
    """One runway: pavement, shoulders, stopways, full Annex 14 marking set."""
    half = RWY_WIDTH * 0.5
    spec = R.spec

    strip(bm_pave, R, 0.0, R.len, -half, half, Z_RUNWAY, steps=36)
    for s in (1, -1):
        strip(bm_sh, R, -30.0, R.len + 30.0,
              s * half, s * (half + 7.5), Z_SHOULDER, steps=36)
    # stopways: published 60 x 45 at each end (ADC)
    for (a0, a1) in ((-spec["stopway"][0], 0.0),
                     (R.len, R.len + spec["stopway"][1])):
        strip(bm_pave, R, a0, a1, -half, half, Z_RUNWAY - 0.01, steps=2)

    for end in (0, 1):
        thr_a = R.thr_a[end]
        d = +1 if end == 0 else -1
        label = spec["designators"][end]
        disp = spec["disp"][end]

        def A(v):
            return thr_a + d * v

        # threshold stripes: 12 for a 45 m runway (6 per side), 1.8 m wide
        w, gpx, inner = 1.80, 1.80, 1.80
        for s in (1, -1):
            for i in range(6):
                l0 = inner + i * (w + gpx)
                strip(bm_mark, R, A(6.0), A(36.0), s * l0, s * (l0 + w),
                      Z_MARK, 2)
        # designator: letter nearer the threshold, digits beyond (Annex 14)
        paint_glyphs(bm_mark, R, label[2], A(44.0), 0.0, d, Z_MARK)
        paint_glyphs(bm_mark, R, label[:2], A(58.0), 0.0, d, Z_MARK)
        # aiming point: 400 m for LDA >= 2400, 45 m long, inner edges 9.25 m
        for s in (1, -1):
            strip(bm_mark, R, A(400.0), A(445.0), s * 9.25, s * 15.25,
                  Z_MARK, 2)
        # touchdown zone: LDA > 2400 m -> six pairs at 150 m, the 400 m pair
        # deleted where the aiming point stands
        for dist in (150.0, 300.0, 550.0, 700.0, 850.0):
            for s in (1, -1):
                for i in range(3):
                    l0 = 9.25 + i * 3.0
                    strip(bm_mark, R, A(dist), A(dist + 22.5),
                          s * l0, s * (l0 + 1.8), Z_MARK, 1)
        # displaced-threshold arrows (10L: 90 m -> 3; 28R: 60 m -> 2)
        n_arrows = int(disp // 30)
        for i in range(n_arrows):
            a_tip = A(-8.0 - i * 30.0)
            for lat in (0.0, -9.0, 9.0):
                strip(bm_mark, R, a_tip - d * 22.0, a_tip - d * 4.0,
                      lat - 0.45, lat + 0.45, Z_MARK, 2)
                vs = [bm_mark.verts.new(R.pt(a_tip, lat, Z_MARK)),
                      bm_mark.verts.new(R.pt(a_tip - d * 4.0, lat - 1.6,
                                             Z_MARK)),
                      bm_mark.verts.new(R.pt(a_tip - d * 4.0, lat + 1.6,
                                             Z_MARK))]
                try:
                    bm_mark.faces.new(vs)
                except ValueError:
                    pass

    # centre line: 30 m stripe / 30 m gap between the thresholds
    a = R.thr_a[0] + 12.0
    while a + 30.0 < R.thr_a[1] - 12.0:
        strip(bm_mark, R, a, a + 30.0, -0.45, 0.45, Z_MARK, 1)
        a += 60.0
    # side stripes over the full pavement
    for s in (1, -1):
        strip(bm_mark, R, 0.0, R.len, s * (half - 0.9), s * half, Z_MARK, 18)


# ---------------------------------------------------------------------------
# the field
# ---------------------------------------------------------------------------
def build_field():
    global G, RING_F
    wipe()
    G = Ground()
    RING_F = RingField(dedupe_ring(data()["aerodrome_boundary_xy_m"][0]))
    verify_levels()
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    P = palette()
    d = data()

    c_root = coll("SBGR_Field")
    c_run = coll("SBGR_Runways", c_root)
    c_taxi = coll("SBGR_Taxiways", c_root)
    c_apron = coll("SBGR_Aprons", c_root)
    c_ground = coll("SBGR_Ground", c_root)
    c_term = coll("SBGR_Terminals", c_root)
    c_bldg = coll("SBGR_Buildings", c_root)
    c_latam = coll("SBGR_LATAM_Base", c_root)
    c_basp = coll("SBGR_BASP", c_root)
    c_cargo = coll("SBGR_Cargo", c_root)
    c_furn = coll("SBGR_Furniture", c_root)
    c_road = coll("SBGR_Roads", c_root)
    c_rail = coll("SBGR_Rail", c_root)
    c_water = coll("SBGR_Water", c_root)
    c_city = coll("SBGR_City", c_root)
    c_veg = coll("SBGR_Vegetation", c_root)
    c_ops = coll("SBGR_Operations", c_root)
    c_anchor = coll("SBGR_Anchors")
    c_light = coll("SBGR_Light")

    build_ground(d, P, c_ground)

    bmp, bms, bmm = bmesh.new(), bmesh.new(), bmesh.new()
    build_runway(RN, bmp, bms, bmm)
    bm_to_object(bmp, "SBGR_RwyN_Pavement",
                 runway_material("SBGR_Runway_10L28R", RN), c_run)
    bmp2 = bmesh.new()
    build_runway(RS, bmp2, bms, bmm)
    bm_to_object(bmp2, "SBGR_RwyS_Pavement",
                 runway_material("SBGR_Runway_10R28L", RS), c_run)
    bm_to_object(bms, "SBGR_RunwayShoulders", P["shoulder"], c_run)
    bm_to_object(bmm, "SBGR_RunwayMarkings", P["white"], c_run)

    build_taxiways(d, P, c_taxi)
    build_aprons(d, P, c_apron)
    build_terminals(d, P, c_term)
    build_jetbridges(d, P, c_term)
    build_tower(P, c_term)
    build_latam_base(d, P, c_latam)
    build_buildings(d, P, c_bldg, c_basp, c_cargo)
    build_fence(d, P, c_furn)
    build_masts(d, P, c_furn)
    build_runway_furniture(d, P, c_furn)
    # ---- the surround: the city ring, and everything mapped through it
    mask = StreetMask(surround()["streets"])
    print("street mask: %d urban 50 m cells" % len(mask.cells))
    build_city(d, P, c_city, mask)
    build_roads(d, P, c_road)
    build_rail(d, P, c_rail)
    build_water(d, P, c_water)
    build_trees(d, P, c_veg)
    build_serra_forest(P, c_veg, mask)
    # ---- the operation
    build_gse(d, P, c_ops)
    build_parked_proxies(P, c_ops)
    build_light(P, c_light)

    # ---- anchors: +Y points down the take-off track. Positions are the
    # BUILT centrelines (the OSM tracing), so an aircraft parented here rolls
    # down the middle of the pavement; the published strings differ by up to
    # 13 m - the whole-second rounding, recorded in the survey.
    for name, xyz, brg in (
            ("SBGR_10L_Threshold", RN.pt(RN.thr_a[0], 0.0), TRACK_DEG),
            ("SBGR_28R_Threshold", RN.pt(RN.thr_a[1], 0.0), TRACK_DEG + 180.0),
            ("SBGR_10R_Threshold", RS.pt(RS.thr_a[0], 0.0), TRACK_DEG),
            ("SBGR_28L_Threshold", RS.pt(RS.thr_a[1], 0.0), TRACK_DEG + 180.0),
            ("SBGR_LATAM_Hangar", (2281.2, 1361.7, Z_HGR), TRACK_DEG),
            ("SBGR_TWR", (TOWER["x"], TOWER["y"], Z_TERM), TRACK_DEG)):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 60.0
        e.location = xyz
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
    """Print the datum reconciliation back against the grid, every build."""
    print("-- flat-field z check (m, against the 750 m datum) --")
    worst = 0.0
    for lbl, (x, y), pub in (("THR 10L", (-2.7, 12.3), -4.76),
                             ("THR 28R", (3402.8, 1009.9), -5.98),
                             ("THR 10R", (-462.6, -513.0), -2.94),
                             ("THR 28L", (2415.9, 331.7), -4.46)):
        g = G.graded(x, y)
        dem = G.dem(x, y)
        worst = max(worst, abs(g - pub))
        print("   %-8s graded %7.2f   raw DEM %7.2f   published %7.2f"
              % (lbl, g, dem, pub))
    print("   graded-vs-published worst %.2f m "
          "(DEM_TO_PUB = %+.2f, mean of the four offsets)" % (worst, DEM_TO_PUB))
    for lbl, (x, y), want in (("terminal apron", (0.0, 610.0), Z_TERM),
                              ("901 row", (2338.0, 1123.0), Z_NE_RAMP),
                              ("hangar apron", (2252.0, 1281.0), Z_HGR),
                              ("VIP patio", (107.0, -608.0), Z_VIP)):
        print("   %-14s graded %7.2f   zone %7.2f" % (lbl, G.graded(x, y),
                                                      want))


def build_ground(d, P, c_ground):
    """The aerodrome ground pad: a 25 m grid clipped to the fence RING plus a
    150 m skirt that tapers onto the city sheet. The first build laid this
    over the boundary's BBOX and the plan check showed a metropolis buried
    under 25 km2 of infield grass - the empty-ring failure, caught by the
    check that exists to catch it."""
    ring = dedupe_ring(d["aerodrome_boundary_xy_m"][0])
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    x0, x1 = min(xs) - 200.0, max(xs) + 200.0
    y0, y1 = min(ys) - 200.0, max(ys) + 200.0
    step = 25.0
    nx = int((x1 - x0) / step) + 1
    ny = int((y1 - y0) / step) + 1
    bm = bmesh.new()
    grid = []
    keep = []
    for j in range(ny):
        row = []
        krow = []
        y = y0 + j * step
        for i in range(nx):
            x = x0 + i * step
            dd = ring_dist(x, y)
            krow.append(dd > -160.0)
            if dd >= 0.0:
                z = G.graded(x, y)
            else:
                t = _smoothstep(-dd / 150.0)
                z = (G.graded(x, y) - 0.8 * t) * (1.0 - t) + \
                    (G.dem(x, y) + 0.45 - 0.15) * t
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
        keep.append(krow)
    for j in range(ny - 1):
        for i in range(nx - 1):
            if not (keep[j][i] or keep[j][i + 1] or keep[j + 1][i] or
                    keep[j + 1][i + 1]):
                continue
            try:
                bm.faces.new((grid[j][i], grid[j][i + 1],
                              grid[j + 1][i + 1], grid[j + 1][i]))
            except ValueError:
                pass
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces],
                     context="VERTS")
    bm_to_object(bm, "SBGR_AerodromeGround", P["infield"], c_ground,
                 smooth=True)


def _twy_width(t):
    """Taxiway width by role. GRU's parallels are code-F; OSM has no width
    tag on them, so: long ways parallel to the runways get 25 m, everything
    else 16 m. ESTIMATE (the ADC prints the layout, not the widths)."""
    pts = t.get("polygon_xy_m")
    if not pts or len(pts) < 2:
        return None
    ux, uy, L = unit(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1])
    para = abs(ux * UX + uy * UY)
    if t.get("length_m", 0.0) > 450.0 and para > 0.97:
        return 25.0
    return 16.0


def build_taxiways(d, P, c_taxi):
    """302 mapped ways, 34.1 km. Closed rings (turn pads, link fans) are
    filled; open ways are ribbons with yellow centrelines."""
    bm, bmc = bmesh.new(), bmesh.new()
    n = 0
    for t in d["taxiways"]:
        pts = t.get("polygon_xy_m")
        if not pts or len(pts) < 2:
            continue
        closed = len(pts) > 3 and math.dist(pts[0], pts[-1]) < 1.0
        if closed:
            flat_poly(bm, pts, Z_TAXI)
            n += 1
            continue
        w = _twy_width(t)
        if w is None:
            continue
        pts = resample(pts, 40.0)
        ribbon(bm, pts, w, Z_TAXI)
        ribbon(bmc, pts, 0.30, Z_TAXI + 0.03)
        n += 1
    bm_to_object(bm, "SBGR_TaxiwayPavement", P["taxi"], c_taxi)
    bm_to_object(bmc, "SBGR_TaxiwayCentrelines", P["yellow"], c_taxi)
    print("taxiways:", n)


def build_aprons(d, P, c_apron):
    """25 named aprons, 677 272 m2, each FLAT at its zone plateau. OSM maps
    several aprons twice (way + multipolygon relation, and the duplicated
    'Patio 7' the survey records); duplicates are dropped by centroid+area."""
    bm = bmesh.new()
    bm_edge = bmesh.new()
    seen = set()
    n = 0
    for a in d["aprons"]:
        key = (round(a["centroid_xy_m"][0]), round(a["centroid_xy_m"][1]),
               round(a.get("area_m2", 0.0)))
        if key in seen:
            continue
        seen.add(key)
        cx, cy = a["centroid_xy_m"]
        z = zone_z(cx, cy)
        if z is None:
            z = G.graded(cx, cy)
        flat_poly(bm, a["polygon_xy_m"], Z_APRON, flat_z=z)
        # the pink-edged apron lanes of the 2023 photographs: a thin edge
        # course inside the apron boundary
        ring = dedupe_ring(a["polygon_xy_m"])
        if a.get("area_m2", 0) > 20000:
            ribbon(bm_edge, ring + [ring[0]], 0.5, Z_APRON + 0.02, flat_z=z)
        n += 1
    bm_to_object(bm, "SBGR_ApronConcrete", P["concrete"], c_apron)
    bm_to_object(bm_edge, "SBGR_ApronLaneEdges", P["pink"], c_apron)
    print("aprons: %d unique of %d mapped" % (n, len(d["aprons"])))


# ---------------------------------------------------------------------------
# terminals, jetbridges, tower
# ---------------------------------------------------------------------------
def build_terminals(d, P, c_term):
    """T1, T2, T3, the cargo terminals and the people-mover stations.

    HEIGHTS: T2 is the one measured thing (DSM floor +14.1 -> built 20 m with
    roof plant); T1 +10.8 -> 14 m; TECA +8..10 -> 11 m. T3 has NO measured
    height (opened 2014, after the DSM): built at T2's 20 m because the two
    are one complex - DECLARED INFERENCE. Facades: white steel with a dark
    glass band on the airside - refs/t2_tower_t3_construction_2013.jpg and
    refs/rwy28l_rollout_terminals_tower_2023.jpg."""
    bm_body, bm_roof, bm_glass, bm_pm = (bmesh.new(), bmesh.new(),
                                         bmesh.new(), bmesh.new())
    for t in d["terminals"]:
        name = t.get("name") or ""
        ring = t["polygon_xy_m"]
        cx, cy = t["centroid_xy_m"]
        base = zone_z(cx, cy)
        if base is None:
            base = G.graded(cx, cy)
        if name.startswith("Esta"):                     # people-mover stations
            prism(bm_pm, ring, 6.0, 12.0, base=base)    # elevated boxes
            for (px, py) in dedupe_ring(ring)[::2]:
                post(bm_pm, px, py, 0.5, base, base + 6.0)
            continue
        if name == "Terminal 2":
            h = H_T2
        elif name == "Terminal 1":
            h = H_T1
        elif name == "Terminal 3":
            h = H_T3
        elif "TECA" in name or "Cargas" in name:
            h = H_TECA
        elif "GATGRU" in name:
            h = 6.0
        else:
            h = 12.0                                    # unnamed piers
        prism(bm_body, ring, 0.0, h, base=base)
        # glass band: an inset ring 60% up the facade
        ring2 = dedupe_ring(ring)
        for i in range(len(ring2)):
            ax, ay = ring2[i]
            bx, by = ring2[(i + 1) % len(ring2)]
            ux, uy, L = unit(ax, ay, bx, by)
            if L < 8.0:
                continue
            ox, oy = -uy * 0.4, ux * 0.4
            z0, z1 = base + h * 0.30, base + h * 0.80
            vs = [bm_glass.verts.new(p) for p in
                  ((ax + ox, ay + oy, z0), (bx + ox, by + oy, z0),
                   (bx + ox, by + oy, z1), (ax + ox, ay + oy, z1))]
            try:
                bm_glass.faces.new(vs)
            except ValueError:
                pass
    bm_to_object(bm_body, "SBGR_TerminalBodies", P["wall_white"], c_term,
                 roof_mat=P["roof_pale"])
    bm_to_object(bm_glass, "SBGR_TerminalGlassBand", P["glass_band"], c_term)
    bm_to_object(bm_pm, "SBGR_PeopleMover", P["clad_pale"], c_term,
                 roof_mat=P["roof_grey"])


def build_jetbridges(d, P, c_term):
    """One simple jetbridge per gate node within reach of a terminal: a
    rotunda post at the building line and a tunnel sloping down toward the
    stand. 171 gates are mapped; the LOD rule (README section 5) is
    pier-and-jetbridge MASSING, not detail - the closest camera is 650+ m."""
    rings = []
    for t in d["terminals"]:
        nm = t.get("name") or ""
        if nm.startswith("Esta"):
            continue
        rings.append(dedupe_ring(t["polygon_xy_m"]))
    bm_t, bm_d = bmesh.new(), bmesh.new()
    n = 0
    for g in d["gates"]:
        if "xy_m" not in g:
            continue
        gx, gy = g["xy_m"]
        best, bd = None, 1e9
        for ring in rings:
            for i in range(len(ring)):
                ax, ay = ring[i]
                bx, by = ring[(i + 1) % len(ring)]
                ux, uy, L = unit(ax, ay, bx, by)
                t_ = max(0.0, min(L, (gx - ax) * ux + (gy - ay) * uy))
                px, py = ax + ux * t_, ay + uy * t_
                dd = math.hypot(gx - px, gy - py)
                if dd < bd:
                    bd, best = dd, (px, py)
        if best is None or bd > 90.0 or bd < 2.0:
            continue
        px, py = best
        base = zone_z(gx, gy)
        if base is None:
            base = G.graded(gx, gy)
        ux, uy, L = unit(px, py, gx, gy)
        # rotunda at the building line, tunnel toward the stand
        post(bm_t, px, py, 1.7, base, base + 7.0)
        steps = 4
        reach = min(bd, 42.0)
        for k in range(steps):
            t0, t1 = k / steps * reach, (k + 1) / steps * reach
            z0 = base + 6.2 - 1.8 * (k / steps)
            z1 = base + 6.2 - 1.8 * ((k + 1) / steps)
            vs = [bm_t.verts.new(p) for p in
                  ((px + ux * t0 - uy * 1.7, py + uy * t0 + ux * 1.7, z0),
                   (px + ux * t1 - uy * 1.7, py + uy * t1 + ux * 1.7, z1),
                   (px + ux * t1 + uy * 1.7, py + uy * t1 - ux * 1.7, z1),
                   (px + ux * t0 + uy * 1.7, py + uy * t0 - ux * 1.7, z0))]
            try:
                bm_t.faces.new(vs)
            except ValueError:
                pass
            for (sx, sy) in ((-uy * 1.7, ux * 1.7), (uy * 1.7, -ux * 1.7)):
                vs = [bm_d.verts.new(p) for p in
                      ((px + ux * t0 + sx, py + uy * t0 + sy, z0 - 2.4),
                       (px + ux * t1 + sx, py + uy * t1 + sy, z1 - 2.4),
                       (px + ux * t1 + sx, py + uy * t1 + sy, z1),
                       (px + ux * t0 + sx, py + uy * t0 + sy, z0))]
                try:
                    bm_d.faces.new(vs)
                except ValueError:
                    pass
        # cab end + support leg
        ex, ey = px + ux * reach, py + uy * reach
        box(bm_t, ex - 2.2, ex + 2.2, ey - 2.2, ey + 2.2,
            base + 3.4, base + 6.6)
        post(bm_d, ex, ey, 0.35, base, base + 3.6)
        n += 1
    bm_to_object(bm_t, "SBGR_Jetbridges", P["jet_body"], c_term)
    bm_to_object(bm_d, "SBGR_JetbridgeDark", P["jet_dark"], c_term)
    print("jetbridges:", n)


def build_tower(P, c_term):
    """The TWR: bare concrete shaft, two-ring gallery, glazed cab, white
    radome ball - refs/tower_closeup_2024.jpg for shape, ADC label georef
    (+/- 100 m) for position, photograph PROPORTION for height (~55 m cab
    roof, ~61 m ball top). ESTIMATE, declared in the module header."""
    T = TOWER
    base = Z_TERM
    bm = bmesh.new()
    w = T["shaft_w"] * 0.5
    box(bm, T["x"] - w, T["x"] + w, T["y"] - w, T["y"] + w,
        base, base + T["cab"][0])
    bm_to_object(bm, "SBGR_TWR_Shaft", P["concrete_bare"], c_term)
    bm = bmesh.new()
    for gz_ in T["gallery"]:
        box(bm, T["x"] - w - 2.2, T["x"] + w + 2.2,
            T["y"] - w - 2.2, T["y"] + w + 2.2,
            base + gz_, base + gz_ + 1.1)
    bm_to_object(bm, "SBGR_TWR_Galleries", P["wall_white"], c_term)
    bm = bmesh.new()
    box(bm, T["x"] - w - 1.4, T["x"] + w + 1.4,
        T["y"] - w - 1.4, T["y"] + w + 1.4,
        base + T["cab"][0], base + T["cab"][1])
    bm_to_object(bm, "SBGR_TWR_Cab", P["glass"], c_term)
    # the white radome ball: an octahedron-sphere of rings
    bm = bmesh.new()
    rings = []
    nseg = 12
    for k in range(7):
        th = math.pi * k / 6.0
        zz = base + T["ball_z"] + T["ball_r"] * math.cos(th)
        rr = T["ball_r"] * math.sin(th) + 1e-3
        rings.append([bm.verts.new((T["x"] + rr * math.cos(2 * math.pi * i / nseg),
                                    T["y"] + rr * math.sin(2 * math.pi * i / nseg),
                                    zz)) for i in range(nseg)])
    for a, b in zip(rings, rings[1:]):
        for i in range(nseg):
            j = (i + 1) % nseg
            try:
                bm.faces.new((a[i], a[j], b[j], b[i]))
            except ValueError:
                pass
    post(bm, T["x"], T["y"], 0.5, base + T["cab"][1],
         base + T["ball_z"] - T["ball_r"] + 0.4)
    ob = bm_to_object(bm, "SBGR_TWR_Radome", P["radome"], c_term, smooth=True)
    ob["inference"] = ("height estimated from photograph proportions; "
                       "position is the ADC label georef +/- 100 m")


# ---------------------------------------------------------------------------
# the LATAM maintenance corner
# ---------------------------------------------------------------------------
def gable(bm, ring, eave, ridge, bearing_deg, base):
    """Prism to the eave, then a shallow gable along `bearing_deg`."""
    ring = dedupe_ring(ring)
    if len(ring) < 3:
        return
    prism(bm, ring, 0.0, eave, base=base)
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    br = math.radians(bearing_deg)
    ux, uy = math.sin(br), math.cos(br)
    nx_, ny_ = uy, -ux
    proj = [((p[0] - cx) * ux + (p[1] - cy) * uy,
             (p[0] - cx) * nx_ + (p[1] - cy) * ny_) for p in ring]
    a0 = min(p[0] for p in proj); a1 = max(p[0] for p in proj)
    l0 = min(p[1] for p in proj); l1 = max(p[1] for p in proj)

    def w(a, l, z):
        return bm.verts.new((cx + ux * a + nx_ * l, cy + uy * a + ny_ * l, z))

    lm = (l0 + l1) * 0.5
    v = [w(a0, l0, base + eave), w(a1, l0, base + eave),
         w(a1, lm, base + ridge), w(a0, lm, base + ridge),
         w(a1, l1, base + eave), w(a0, l1, base + eave)]
    for f in ((v[0], v[1], v[2], v[3]), (v[3], v[2], v[4], v[5])):
        try:
            bm.faces.new(f)
        except ValueError:
            pass


def wordmark_on_wall(P, collection, tag, centre_xy, right_uv, z_base, cap_m):
    """The LATAM lockup from the OFFICIAL SVG, on an arbitrarily-oriented
    vertical wall. `right_uv` is the direction an observer LOOKING AT the wall
    reads left-to-right - get it from the wall's outward normal n as
    right = (-n.y, n.x) (the SDSC facing lesson, generalised: an observer at
    +n sees world axes mirrored)."""
    sys.path.insert(0, ROOT)
    import latam_livery_kit as kit
    me_word, me_brand = kit.importar_svg_2_camadas(
        os.path.join(ROOT, "latam_logo_indigo.svg"))
    wy = [v.co.y for v in me_word.vertices]
    s = cap_m / (max(wy) - min(wy))
    all_x = [v.co.x for me in (me_word, me_brand) for v in me.vertices]
    lockup_w = (max(all_x) - min(all_x)) * s
    rx, ry = right_uv
    x_start = centre_xy[0] - rx * lockup_w * 0.5
    y_start = centre_xy[1] - ry * lockup_w * 0.5
    zs = z_base - min(wy) * s
    for me, mt, nm in ((me_word, P["latam_white"], tag + "_Wordmark"),
                       (me_brand, P["latam_coral"], tag + "_Brandmark")):
        bm = bmesh.new()
        bm.from_mesh(me)
        for v in bm.verts:
            v.co = Vector((x_start + rx * v.co.x * s,
                           y_start + ry * v.co.x * s,
                           zs + v.co.y * s))
        bm_to_object(bm, nm, mt, collection)
        bpy.data.meshes.remove(me)


def build_latam_base(d, P, c_latam):
    """The NE maintenance corner: the LATAM hangar and the American Airlines
    hangar - the L-shaped pair of big roofs that says 'Guarulhos' from the
    air (RECOGNITION.md section 2.5).

    EVERY VERTICAL DIMENSION HERE IS DECLARED INFERENCE - see the module
    header. The footprints, orientations and the apron are OSM data."""
    lat = d["latam_maintenance"]
    hangars = {h["osm_id"]: h for h in d["hangars"]}
    lh = hangars["way/778050745"]          # LATAM
    ah = hangars["way/777394328"]          # American Airlines
    H = LATAM_HANGAR
    base = Z_HGR

    # --- the LATAM hangar body -----------------------------------------
    bm = bmesh.new()
    gable(bm, lh["polygon_xy_m"], H["eave"], H["ridge"],
          lh["min_area_box"]["long_axis_bearing_deg_true"], base)
    ob = bm_to_object(bm, "SBGR_LATAM_Hangar", P["clad_pale"], c_latam,
                      roof_mat=P["roof_pale"])
    ob["inference"] = ("declared inference: no photograph and no measured "
                       "height exist (DSM predates the building). Sized so a "
                       "777-300ER (18.5 m tail) clears the door.")

    # The SSE door face: the long wall that looks at the hangar's own apron.
    # Wall midline from the footprint's min-area box, pushed to the SSE side.
    brg = math.radians(lh["min_area_box"]["long_axis_bearing_deg_true"])
    ux, uy = math.sin(brg), math.cos(brg)          # along the long axis
    # SSE normal: rotate the long axis -90 deg (73.7 -> 163.7)
    nx_, ny_ = uy, -ux
    ccx, ccy = lh["centroid_xy_m"]
    half_short = lh["min_area_box"]["short_m"] * 0.5
    fx, fy = ccx + nx_ * half_short, ccy + ny_ * half_short   # door-face mid
    dw = H["door_w"] * 0.5

    # the door band (closed leaves) and one OPEN bay showing the interior
    bm_door, bm_open, bm_floor, bm_frame = (bmesh.new(), bmesh.new(),
                                            bmesh.new(), bmesh.new())
    for (t0, t1, bmx, depth) in ((-dw, dw - H["open_bay"], bm_door, 0.4),
                                 (dw - H["open_bay"], dw, bm_open, 2.0)):
        c0 = (fx + ux * t0 - nx_ * depth, fy + uy * t0 - ny_ * depth)
        c1 = (fx + ux * t1 - nx_ * depth, fy + uy * t1 - ny_ * depth)
        for (z0, z1) in ((base, base + H["door_h"]),):
            vs = [bmx.verts.new(p) for p in
                  ((c0[0], c0[1], z0), (c1[0], c1[1], z0),
                   (c1[0], c1[1], z1), (c0[0], c0[1], z1))]
            try:
                bmx.faces.new(vs)
            except ValueError:
                pass
    # floor + a steel truss line visible through the open bay
    o0 = (fx + ux * (dw - H["open_bay"]), fy + uy * (dw - H["open_bay"]))
    vs = [bm_floor.verts.new(p) for p in
          ((o0[0], o0[1], base + 0.02),
           (o0[0] + ux * H["open_bay"], o0[1] + uy * H["open_bay"], base + 0.02),
           (o0[0] + ux * H["open_bay"] - nx_ * 40.0,
            o0[1] + uy * H["open_bay"] - ny_ * 40.0, base + 0.02),
           (o0[0] - nx_ * 40.0, o0[1] - ny_ * 40.0, base + 0.02))]
    bm_floor.faces.new(vs)
    for k in range(4):
        px = o0[0] + ux * H["open_bay"] * 0.5 - nx_ * (6.0 + k * 9.0)
        py = o0[1] + uy * H["open_bay"] * 0.5 - ny_ * (6.0 + k * 9.0)
        obox(bm_frame, px, py, base + H["door_h"] - 3.0, base + H["door_h"] - 1.6,
             H["open_bay"], 0.8, math.degrees(brg))
    bm_to_object(bm_door, "SBGR_LATAM_HangarDoors", P["clad"], c_latam)
    bm_to_object(bm_open, "SBGR_LATAM_HangarOpenBay", P["hangar_dark"], c_latam)
    bm_to_object(bm_floor, "SBGR_LATAM_HangarFloor", P["floor_pale"], c_latam)
    bm_to_object(bm_frame, "SBGR_LATAM_HangarTruss", P["frame_steel"], c_latam)

    # fascia band over the door + the official lockup. The wall's outward
    # normal is (nx_, ny_); an observer out on the apron reads left-to-right
    # along right = (-ny_, nx_)... which for a 163.7 normal is the runway
    # direction: the lockup reads correctly from the ramp AND from a 10L roll.
    bm = bmesh.new()
    z0, z1 = base + H["eave"] - 4.6, base + H["eave"] - 0.6
    off = 0.25
    vs = [bm.verts.new(p) for p in
          ((fx - ux * 66.0 + nx_ * off, fy - uy * 66.0 + ny_ * off, z0),
           (fx + ux * 66.0 + nx_ * off, fy + uy * 66.0 + ny_ * off, z0),
           (fx + ux * 66.0 + nx_ * off, fy + uy * 66.0 + ny_ * off, z1),
           (fx - ux * 66.0 + nx_ * off, fy - uy * 66.0 + ny_ * off, z1))]
    bm.faces.new(vs)
    bm_to_object(bm, "SBGR_LATAM_HangarBand", P["band_indigo"], c_latam)
    right = (-ny_, nx_)
    wordmark_on_wall(P, c_latam, "SBGR_LATAM_Hangar",
                     (fx + nx_ * (off + 0.15), fy + ny_ * (off + 0.15)),
                     right, z0 + 0.9, 2.4)

    # --- the American Airlines hangar ----------------------------------
    bm = bmesh.new()
    gable(bm, ah["polygon_xy_m"], AA_HANGAR["eave"], AA_HANGAR["ridge"],
          ah["min_area_box"]["long_axis_bearing_deg_true"], base)
    ob = bm_to_object(bm, "SBGR_AA_Hangar", P["clad"], c_latam,
                      roof_mat=P["roof_grey"])
    ob["inference"] = ("DSM floor +7.2 m (smeared); built at a widebody-door "
                       "24 m eave, unbranded - no photograph of the facade")
    # its door band faces the shared apron (ESE end of its long axis)
    brg_a = math.radians(ah["min_area_box"]["long_axis_bearing_deg_true"])
    aux, auy = math.sin(brg_a), math.cos(brg_a)
    acx, acy = ah["centroid_xy_m"]
    half_l = ah["min_area_box"]["long_m"] * 0.5
    # the end nearer the LATAM apron (positive along toward ESE/SSE)
    e1 = (acx + aux * half_l, acy + auy * half_l)
    e2 = (acx - aux * half_l, acy - auy * half_l)
    door_end = e1 if math.hypot(e1[0] - 2252, e1[1] - 1281) < \
        math.hypot(e2[0] - 2252, e2[1] - 1281) else e2
    sgn = 1.0 if door_end is e1 else -1.0
    bm = bmesh.new()
    hw = ah["min_area_box"]["short_m"] * 0.5 - 4.0
    px, py = door_end[0] - aux * sgn * 0.4, door_end[1] - auy * sgn * 0.4
    vs = [bm.verts.new(p) for p in
          ((px - auy * hw, py + aux * hw, base),
           (px + auy * hw, py - aux * hw, base),
           (px + auy * hw, py - aux * hw, base + 20.0),
           (px - auy * hw, py + aux * hw, base + 20.0))]
    bm.faces.new(vs)
    bm_to_object(bm, "SBGR_AA_HangarDoors", P["band_grey"], c_latam)


# ---------------------------------------------------------------------------
# buildings, fence, furniture
# ---------------------------------------------------------------------------
def estimate_height(b):
    lv = b.get("building_levels")
    if lv:
        try:
            return float(str(lv).split(";")[0]) * LEVEL_HEIGHT
        except ValueError:
            pass
    return HEIGHT_BY_TYPE.get(b.get("building"), 6.0)


def build_buildings(d, P, c_bldg, c_basp, c_cargo):
    """The 122 in-fence footprints (119 with polygons), split by where they
    are: BASP + GA on the south side, cargo on the west/east frontages,
    service everywhere else. Heights are HEIGHT_BY_TYPE estimates - 10 of
    ~140 SBGR objects carry any OSM height tag (survey section 6.6)."""
    done_ids = {"way/778050745", "way/777394328"}     # the two big hangars
    bm_basp, bm_cargo, bm_srv, bm_tank = (bmesh.new(), bmesh.new(),
                                          bmesh.new(), bmesh.new())
    for h in d["hangars"]:
        if h["osm_id"] in done_ids:
            continue
        cx, cy = h["centroid_xy_m"]
        base = zone_z(cx, cy) or G.graded(cx, cy)
        gable(bm_basp, h["polygon_xy_m"], 10.0, 12.0,
              h["min_area_box"]["long_axis_bearing_deg_true"], base)
    n = 0
    for b in d["buildings"]:
        ring = b.get("polygon_xy_m")
        if not ring:
            continue
        pts = dedupe_ring(ring)
        if len(pts) < 3:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        base = zone_z(cx, cy) or G.graded(cx, cy)
        h = estimate_height(b)
        if b.get("building") == "storage_tank" or \
                b.get("man_made") == "storage_tank":
            prism(bm_tank, ring, 0.0, h, base=base)
        elif cy < -150.0:
            prism(bm_basp, ring, 0.0, h, base=base)
        elif cx < -350.0 or b.get("building") in ("warehouse", "industrial"):
            prism(bm_cargo, ring, 0.0, h, base=base)
        else:
            prism(bm_srv, ring, 0.0, h, base=base)
        n += 1
    bm_to_object(bm_basp, "SBGR_BASP_Buildings", P["clad_warm"], c_basp,
                 roof_mat=P["roof_grey"])
    bm_to_object(bm_cargo, "SBGR_CargoSheds", P["clad"], c_cargo,
                 roof_mat=P["roof_pale"])
    bm_to_object(bm_srv, "SBGR_ServiceBuildings", P["wall_cream"], c_bldg,
                 roof_mat=P["roof_grey"])
    bm_to_object(bm_tank, "SBGR_Tanks", P["wall_white"], c_bldg)
    print("buildings:", n)


def build_fence(d, P, c_furn):
    """The aerodrome fence on the mapped boundary ring - at GRU the city is
    PRESSED against it (refs/city_fence_taxiway_2023.jpg), so the fence line
    is part of what makes the place read. A thin mesh ribbon + posts."""
    ring = dedupe_ring(d["aerodrome_boundary_xy_m"][0])
    bm_m, bm_p = bmesh.new(), bmesh.new()
    npost = 0
    for i in range(len(ring)):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % len(ring)]
        za = surface_z(ax, ay)
        zb = surface_z(bx, by)
        vs = [bm_m.verts.new(p) for p in
              ((ax, ay, za + 0.1), (bx, by, zb + 0.1),
               (bx, by, zb + 2.6), (ax, ay, za + 2.6))]
        try:
            bm_m.faces.new(vs)
        except ValueError:
            pass
        ux, uy, L = unit(ax, ay, bx, by)
        t = 0.0
        while t < L:
            px, py = ax + ux * t, ay + uy * t
            post(bm_p, px, py, 0.07, surface_z(px, py), surface_z(px, py) + 2.7)
            npost += 1
            t += 40.0
    bm_to_object(bm_m, "SBGR_Fence", P["fence"], c_furn)
    bm_to_object(bm_p, "SBGR_FencePosts", P["fence"], c_furn)
    print("fence posts:", npost)


def build_masts(d, P, c_furn):
    """The MAST FOREST - RECOGNITION.md section 2.6. TWO designs, photographed
    side by side in refs/remote_stands_masts_city_2026.jpg: a plain high-mast
    with a lamp ring, and a lattice tower with a rectangular lamp rack. 30 m
    is the international-apron high-mast band (as at SCL); no published
    height. Positions: apron edges at ~140 m - INFERRED."""
    bm_a, bm_b = bmesh.new(), bmesh.new()
    placed = []
    seen = set()
    for a in d["aprons"]:
        key = (round(a["centroid_xy_m"][0]), round(a["centroid_xy_m"][1]))
        if key in seen or a.get("area_m2", 0) < 9000:
            continue
        seen.add(key)
        ring = dedupe_ring(a["polygon_xy_m"])
        n = len(ring)
        for i in range(n):
            ax, ay = ring[i]
            bx, by = ring[(i + 1) % n]
            ux, uy, L = unit(ax, ay, bx, by)
            t = 0.0
            while t < L:
                px, py = ax + ux * t, ay + uy * t
                if all(math.dist((px, py), q) > 140.0 for q in placed):
                    placed.append((px, py))
                t += 35.0
    blocks = [dedupe_ring(h["polygon_xy_m"]) for h in d["hangars"]] + \
             [dedupe_ring(t["polygon_xy_m"]) for t in d["terminals"]
              if not (t.get("name") or "").startswith("Esta")]
    placed = [p for p in placed
              if not any(_ring_hit(r, p[0], p[1]) for r in blocks)]
    for k, (px, py) in enumerate(placed):
        zb = gz(px, py)
        if k % 2 == 0:
            post(bm_a, px, py, 0.45, zb, zb + MAST_H)
            # the lamp ring
            for i in range(6):
                th = math.pi * 2 * i / 6
                obox(bm_a, px + 1.6 * math.cos(th), py + 1.6 * math.sin(th),
                     zb + MAST_H - 1.2, zb + MAST_H - 0.4, 1.4, 0.7,
                     math.degrees(th))
        else:
            for (dx, dy) in ((-0.8, -0.8), (0.8, -0.8), (0.8, 0.8),
                             (-0.8, 0.8)):
                post(bm_b, px + dx, py + dy, 0.10, zb, zb + MAST_H - 2.0)
            box(bm_b, px - 2.6, px + 2.6, py - 1.0, py + 1.0,
                zb + MAST_H - 2.0, zb + MAST_H)
    bm_to_object(bm_a, "SBGR_MastsRing", P["mast"], c_furn)
    bm_to_object(bm_b, "SBGR_MastsLattice", P["mast"], c_furn)
    print("floodlight masts:", len(placed))


def build_runway_furniture(d, P, c_furn):
    """Edge lights, PAPI, approach-light rows, holding boards, windsocks,
    localizer arrays and glideslope masts. The approach LIGHTING SYSTEMS are
    published (ADC: ALSF-2 on 10L and 10R, ALSF-1 on 28R and 28L; PAPI x4,
    MEHT 57/61.5/63/71 ft); the layout detail is the standard pattern."""
    bm_l, bm_p, bm_al, bm_s, bm_q = (bmesh.new(), bmesh.new(), bmesh.new(),
                                     bmesh.new(), bmesh.new())
    half = RWY_WIDTH * 0.5
    for R in (RN, RS):
        a = 30.0
        while a < R.len - 10.0:
            for s in (1, -1):
                x, y, z = R.pt(a, s * (half + 2.5), 0.02)
                post(bm_l, x, y, 0.13, z, z + 0.36)
            a += 60.0
        for end in (0, 1):
            thr_a = R.thr_a[end]
            dsgn = +1 if end == 0 else -1
            # PAPI: 4 boxes, 300 m in, LEFT of the approach
            for i in range(4):
                lat = dsgn * (45.0 + i * 9.0)
                x, y, z = R.pt(thr_a + dsgn * 300.0, lat, 0.0)
                box(bm_p, x - 1.2, x + 1.2, y - 0.7, y + 0.7, z, z + 1.1)
            # approach lights: centreline bars every 30 m to 720 m before the
            # threshold, a crossbar at 300 m - the ALSF skeleton. They stand
            # on the ground OUTSIDE the pavement, on frangible posts.
            for k in range(1, 25):
                aa = thr_a - dsgn * (30.0 * k)
                if 0.0 < aa < R.len and k * 30.0 <= R.spec["disp"][end]:
                    continue          # inside the displaced area: painted, lit low
                x, y, _ = R.pt(aa, 0.0)
                zb = surface_z(x, y)
                zt = max(zb + 1.0, R.z(thr_a) + 0.5)
                post(bm_al, x, y, 0.10, zb, zt)
                bx0, by0, _ = R.pt(aa, -2.1)
                bx1, by1, _ = R.pt(aa, 2.1)
                vs = [bm_al.verts.new(p) for p in
                      ((bx0, by0, zt), (bx1, by1, zt),
                       (bx1, by1, zt + 0.25), (bx0, by0, zt + 0.25))]
                try:
                    bm_al.faces.new(vs)
                except ValueError:
                    pass
                if k == 10:           # the 300 m crossbar
                    cx0, cy0, _ = R.pt(aa, -9.0)
                    cx1, cy1, _ = R.pt(aa, 9.0)
                    vs = [bm_al.verts.new(p) for p in
                          ((cx0, cy0, zt), (cx1, cy1, zt),
                           (cx1, cy1, zt + 0.3), (cx0, cy0, zt + 0.3))]
                    try:
                        bm_al.faces.new(vs)
                    except ValueError:
                        pass
            # localizer array ~350 m past the OTHER end of the pavement
            la = R.len + 350.0 if end == 0 else -350.0
            for i in range(-7, 8):
                x, y, _ = R.pt(la, i * 1.8)
                zb = surface_z(x, y)
                post(bm_al, x, y, 0.09, zb, zb + 2.6)
    # holding-position boards at the mapped nodes
    for hp in d["holding_positions"]:
        if "xy_m" not in hp:
            continue
        px, py = hp["xy_m"]
        zb = gz(px, py)
        vs = [bm_s.verts.new(p) for p in
              ((px - 1.4, py, zb + 0.6), (px + 1.4, py, zb + 0.6),
               (px + 1.4, py, zb + 1.6), (px - 1.4, py, zb + 1.6))]
        try:
            bm_s.faces.new(vs)
        except ValueError:
            pass
        for dx in (-1.1, 1.1):
            post(bm_q, px + dx, py, 0.07, zb, zb + 0.6)
    for w in d["windsocks"]:
        if "xy_m" not in w:
            continue
        px, py = w["xy_m"]
        zb = gz(px, py)
        post(bm_q, px, py, 0.18, zb, zb + 6.5)
    bm_to_object(bm_l, "SBGR_RunwayEdgeLights",
                 mat("SBGR_EdgeLightFitting", (0.420, 0.400, 0.330), 0.45),
                 c_furn)
    bm_to_object(bm_p, "SBGR_PAPI", P["mast"], c_furn)
    bm_to_object(bm_al, "SBGR_ApproachLights", P["mast"], c_furn)
    bm_to_object(bm_s, "SBGR_HoldingBoards",
                 mat("SBGR_SignRed", (0.360, 0.020, 0.016), 0.55), c_furn)
    bm_to_object(bm_q, "SBGR_HoldingPosts", P["mast"], c_furn)


# ---------------------------------------------------------------------------
# THE CITY RING - the answer to phase 1's deliberate cut (module header).
# ---------------------------------------------------------------------------
CITY_MAT_BY_LANDUSE = {
    "residential": "city_res",
    "industrial": "city_ind",
    "commercial": "city_com",
    "retail": "city_com",
    "garages": "city_ind",
    "depot": "city_ind",
    "military": "city_ind",
    "construction": "city_bare",
    "brownfield": "city_bare",
    "greenfield": "city_bare",
    "farmland": "city_green",
    "meadow": "city_green",
    "forest": "city_green",
    "village_green": "city_green",
    "recreation_ground": "city_green",
    "cemetery": "city_green",
    "religious": "city_res",
    "education": "city_com",
    "yes": "city_res",
}


def build_city(d, P, c_city, mask):
    """The surround: tint, massing, and the north-hill favela texture.

    LAYER 1, TINT: every mapped landuse polygon as 30 m cells snapped to the
    NEAR TERRAIN TIER'S OWN LATTICE (nodes at -15000 + 30i) and sampled with
    the same dem() - so tint and terrain are the same piecewise surface 0.5 m
    apart and cannot interleave at any distance. The SDSC cane-sheet lesson,
    applied before the fact. Residential polygons on the north hills (y >
    1500, ground > +25 m) use the tighter, redder hillside tint the
    photographs show climbing the Cabucu flank. Since the surround round:
      * green/bare cells above the +30 m forest line are NOT tinted - the
        serra owns that ground (terrain shading + build_serra_forest), which
        also buries the hard-edged tint sawtooth phase 2's checks recorded
        stepping down the flank;
      * every urban STREET-MASK cell no landuse polygon covers gets the
        residential (or hillside) tint - Bonsucesso and Agua Chata across
        the Baquirivu valley exist in the render because their streets are
        mapped, even though their landuse mostly is not.

    LAYER 2, MASSING, three sources in order of honesty, one shared budget:
      A. the re-queried REAL footprints (min-area boxes, height from
         building:levels where tagged, else from the building kind);
      B. procedural boxes inside the mapped residential / commercial /
         industrial polygons within CITY_REACH - houses 4-9 m, sheds,
         occasional mid-rises; big industrial polygons build as the Cumbica
         LOGISTICS BELT (40-110 m warehouses);
      C. fabric boxes on urban street-mask cells nothing above covered,
         nearest-first out to FABRIC_REACH.
    Deterministic (CITY_SEED); capped at CITY_BOX_BUDGET. The DSM under all
    of it is roofs-and-canopy already, which double-counts a storey and is
    declared in the module header.

    The tint polygons, the streets and the footprints are DATA. The
    procedural boxes of B and C are not."""
    import random
    rnd = random.Random(CITY_SEED)
    lat30 = -15000.0                      # the near tier's lattice origin
    px0, px1, py0, py1 = pad_box()

    def outside_fence(x, y, margin):
        if not (px0 < x < px1 and py0 < y < py1):
            return True                   # far outside the pad box entirely
        return ring_dist(x, y) <= margin

    def cell30(x, y):
        return (int(math.floor((x - lat30) / 30.0)),
                int(math.floor((y - lat30) / 30.0)))

    bms = {k: bmesh.new() for k in ("city_res", "city_fav", "city_ind",
                                    "city_com", "city_green", "city_bare")}
    tinted = set()
    ncell = nskip_serra = 0
    for l in d["landuse"]:
        ring = l.get("polygon_xy_m") or []
        if len(ring) < 3:
            continue
        kind = l.get("landuse")
        if kind == "grass":
            continue                      # the infield pad already is grass
        mk = CITY_MAT_BY_LANDUSE.get(kind)
        if mk is None:
            continue
        for (x, y) in _cells(dedupe_ring(ring), 30.0, lat30, lat30):
            if not outside_fence(x, y, -30.0):
                continue                  # the fence ring owns the inside
            if abs(x) > TINT_REACH or abs(y) > TINT_REACH:
                continue                  # beyond this the terrain shading is it
            key = mk
            z = G.dem(x, y)
            if mk in ("city_green", "city_bare") and z > 30.0 \
                    and not mask.urban(x, y):
                nskip_serra += 1
                continue                  # the serra owns the high flank
            if mk == "city_res" and y > 1500.0 and z > 25.0:
                key = "city_fav"          # the hillside fabric
            _quad(bms[key], x, y, 30.0, lambda a, b: G.dem(a, b) + 0.5)
            tinted.add(cell30(x, y))
            ncell += 1

    # ---- fabric tint: urban street-mask cells with no landuse polygon ----
    nfab = 0
    i0 = int((-TINT_REACH - lat30) / 30.0)
    i1 = int((TINT_REACH - lat30) / 30.0)
    for j in range(i0, i1 + 1):
        cy = lat30 + (j + 0.5) * 30.0
        for i in range(i0, i1 + 1):
            if (i, j) in tinted:
                continue
            cx = lat30 + (i + 0.5) * 30.0
            if not mask.urban(cx, cy):
                continue
            if not outside_fence(cx, cy, -30.0):
                continue
            key = "city_fav" if (cy > 1500.0 and G.dem(cx, cy) > 25.0) \
                else "city_res"
            _quad(bms[key], cx, cy, 30.0, lambda a, b: G.dem(a, b) + 0.5)
            tinted.add((i, j))
            nfab += 1
    for k, bm in bms.items():
        bm_to_object(bm, "SBGR_CityTint_%s" % k.split("_")[1], P[k], c_city,
                     smooth=True)

    # ---- massing ------------------------------------------------------
    bm_a, bm_b, bm_br = bmesh.new(), bmesh.new(), bmesh.new()
    bm_rt, bm_rf = bmesh.new(), bmesh.new()
    bm_mid, bm_shed, bm_ware = bmesh.new(), bmesh.new(), bmesh.new()
    nbox = nmid = nshed = nware = nfoot = 0
    occupied = set()

    def house(jx, jy, zb, hdg, hill, w=None, dp=None, h=None):
        w = w or (6.0 if hill else 8.0) + rnd.random() * 5.0
        dp = dp or (7.0 if hill else 9.0) + rnd.random() * 6.0
        h = h or (3.2 if hill else 3.6) + rnd.random() * (4.0 if hill else 4.5)
        wall = bm_br if hill or rnd.random() < 0.25 else \
            (bm_a if rnd.random() < 0.6 else bm_b)
        obox(wall, jx, jy, zb, zb + h, dp, w, hdg)
        roof = bm_rt if rnd.random() < (0.35 if hill else 0.55) else bm_rf
        obox(roof, jx, jy, zb + h, zb + h + 0.7, dp + 0.8, w + 0.8, hdg)

    # -- A. the real footprints -----------------------------------------
    for b in surround()["buildings"]:
        if nbox >= CITY_BOX_BUDGET:
            break
        cx, cy = b["cx"], b["cy"]
        if abs(cx) > FABRIC_REACH or abs(cy) > FABRIC_REACH:
            continue
        if not outside_fence(cx, cy, -35.0):
            continue
        L, W = min(b["long_m"], 260.0), min(b["short_m"], 120.0)
        if L < 4.0 or W < 2.6:
            continue
        hdg = b["bearing_deg"]            # both are compass bearings of the
        #                                   long axis (obox: 0 = north)
        kind = b.get("kind") or "yes"
        lv = b.get("levels")
        zb = G.dem(cx, cy) + 0.3
        big = L > 40.0 and W > 14.0
        if kind in ("industrial", "warehouse", "hangar", "depot", "garage",
                    "garages", "commercial", "retail", "office",
                    "supermarket", "service") or (big and kind in
                                                  ("yes", "roof")):
            h = (8.0 + rnd.random() * 5.0) if big else \
                (6.0 + rnd.random() * 3.0)
            if lv:
                h = max(h, 3.4 * lv)
            obox(bm_ware if big else bm_shed, cx, cy, zb, zb + h, L, W, hdg)
            nware += 1 if big else 0
            nshed += 0 if big else 1
        elif kind == "apartments" or (lv or 0) >= 4:
            h = (3.0 * lv + 1.5) if lv else (16.0 + rnd.random() * 14.0)
            obox(bm_mid, cx, cy, zb, zb + h, L, W, hdg)
            nmid += 1
        else:
            hill = cy > 1500.0 and G.dem(cx, cy) > 25.0
            h = 3.4 * lv if lv else None
            house(cx, cy, zb, hdg, hill, w=W, dp=L, h=h)
        nfoot += 1
        nbox += 1
        occupied.add(mask.key(cx, cy))

    # -- B. procedural massing inside the mapped landuse polygons --------
    polys = []
    for l in d["landuse"]:
        ring = l.get("polygon_xy_m") or []
        if len(ring) < 3:
            continue
        kind = l.get("landuse")
        if kind not in ("residential", "commercial", "retail", "industrial",
                        "depot", "garages"):
            continue
        ring = dedupe_ring(ring)
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        if abs(cx) > CITY_REACH + 1200 or abs(cy) > CITY_REACH + 1200:
            continue
        area = 0.0
        for i in range(len(ring) - 1):
            area += ring[i][0] * ring[i + 1][1] - \
                ring[i + 1][0] * ring[i][1]
        polys.append((kind, ring, cx, cy, abs(area) / 2.0))
    rnd.shuffle(polys)
    for (kind, ring, cx, cy, area) in polys:
        if nbox >= CITY_BOX_BUDGET:
            break
        res = kind == "residential"
        hill = res and cy > 1500.0
        # the logistics belt: big mapped industrial ground gets WAREHOUSE
        # massing (Cumbica's aerials read as sheds, not houses)
        belt = kind in ("industrial", "depot") and area > 60000.0
        step = 26.0 if hill else (32.0 if res else (95.0 if belt else 60.0))
        for (x, y) in _cells(ring, step, lat30 + 7.0, lat30 + 7.0):
            if nbox >= CITY_BOX_BUDGET:
                break
            if not outside_fence(x, y, -35.0):
                continue
            if abs(x) > CITY_REACH or abs(y) > CITY_REACH:
                continue
            if mask.key(x, y) in occupied:
                continue                  # a real footprint stands here
            if rnd.random() < (0.25 if hill else 0.30):
                continue                          # streets and yards
            zb = G.dem(x, y) + 0.3
            jx = x + (rnd.random() - 0.5) * step * 0.4
            jy = y + (rnd.random() - 0.5) * step * 0.4
            hdg = rnd.random() * 180.0
            if belt:
                obox(bm_ware, jx, jy, zb, zb + 9.0 + rnd.random() * 5.0,
                     45.0 + rnd.random() * 65.0, 24.0 + rnd.random() * 30.0,
                     hdg)
                nware += 1
                nbox += 1
                occupied.add(mask.key(jx, jy))
                continue
            if not res and rnd.random() < 0.75:
                # industrial shed
                obox(bm_shed, jx, jy, zb, zb + 7.0 + rnd.random() * 6.0,
                     30.0 + rnd.random() * 28.0, 16.0 + rnd.random() * 12.0,
                     hdg)
                nshed += 1
                nbox += 1
                occupied.add(mask.key(jx, jy))
                continue
            if res and not hill and rnd.random() < 0.035:
                # a mid-rise block - Guarulhos has scattered towers
                h = 18.0 + rnd.random() * 18.0
                obox(bm_mid, jx, jy, zb, zb + h, 14.0, 12.0, hdg)
                nmid += 1
                nbox += 1
                occupied.add(mask.key(jx, jy))
                continue
            house(jx, jy, zb, hdg, hill)
            nbox += 1
            occupied.add(mask.key(jx, jy))

    # -- C. fabric massing on the street mask, nearest-first -------------
    ncfab = 0
    fab = sorted((k for k in mask.cells
                  if abs((k[0] + 0.5) * mask.STEP) < FABRIC_REACH
                  and abs((k[1] + 0.5) * mask.STEP) < FABRIC_REACH),
                 key=lambda k: math.hypot((k[0] + 0.5) * mask.STEP - 2000.0,
                                          (k[1] + 0.5) * mask.STEP - 300.0))
    for k in fab:
        if nbox >= CITY_BOX_BUDGET:
            break
        if k in occupied:
            continue
        bx = (k[0] + 0.5) * mask.STEP
        by = (k[1] + 0.5) * mask.STEP
        if not outside_fence(bx, by, -35.0):
            continue
        hill = by > 1500.0 and G.dem(bx, by) > 25.0
        for _ in range(3 if hill else 2):
            if rnd.random() < 0.28:
                continue
            jx = bx + (rnd.random() - 0.5) * mask.STEP * 0.8
            jy = by + (rnd.random() - 0.5) * mask.STEP * 0.8
            house(jx, jy, G.dem(jx, jy) + 0.3, rnd.random() * 180.0, hill)
            nbox += 1
            ncfab += 1
        occupied.add(k)

    bm_to_object(bm_a, "SBGR_City_HousesA", P["house_a"], c_city)
    bm_to_object(bm_b, "SBGR_City_HousesB", P["house_b"], c_city)
    bm_to_object(bm_br, "SBGR_City_HousesBrick", P["house_brick"], c_city)
    bm_to_object(bm_rt, "SBGR_City_RoofsTile", P["tile_red"], c_city)
    bm_to_object(bm_rf, "SBGR_City_RoofsFiber", P["roof_fiber"], c_city)
    bm_to_object(bm_mid, "SBGR_City_Midrises", P["midrise"], c_city,
                 roof_mat=P["roof_dark"])
    bm_to_object(bm_shed, "SBGR_City_Sheds", P["city_ind"], c_city,
                 roof_mat=P["roof_pale"])
    bm_to_object(bm_ware, "SBGR_City_Warehouses", P["warehouse"], c_city,
                 roof_mat=P["roof_pale"])
    print("city: %d landuse + %d fabric tint cells (%d ceded to the serra), "
          "%d structures (%d footprints, %d mid-rises, %d sheds, "
          "%d warehouses, %d fabric houses)"
          % (ncell, nfab, nskip_serra, nbox, nfoot, nmid, nshed, nware,
             ncfab))


def build_roads(d, P, c_road):
    """1 415 mapped ways, 269 km: the Helio Smidt into the terminals, the
    Ayrton Senna and Dutra corridors, and every kept street. Widths are
    ESTIMATES (no width/lanes tags used); surfaces default paved - this is a
    metropolis, and only tagged ways go red-dirt."""
    bm_p, bm_d = bmesh.new(), bmesh.new()
    km_p = km_d = 0.0
    n = 0
    for r in d["roads"]:
        pts = r.get("polygon_xy_m")
        if not pts or len(pts) < 2:
            continue
        hw = r.get("highway")
        if hw in ROAD_SKIP:
            continue
        w = ROAD_WIDTH.get(hw)
        if w is None:
            continue
        unpaved = (r.get("surface") or "").lower() in UNPAVED
        pts = resample(pts, 40.0)
        drape(bm_d if unpaved else bm_p, pts, w, 0.07)
        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        if unpaved:
            km_d += L / 1000.0
        else:
            km_p += L / 1000.0
        n += 1
    bm_to_object(bm_p, "SBGR_RoadsPaved", P["road_paved"], c_road, smooth=True)
    bm_to_object(bm_d, "SBGR_RoadsUnpaved", P["road_dirt"], c_road,
                 smooth=True)
    # the minor streets themselves (surround_osm.py re-query) - the grid the
    # fabric houses stand between; same asphalt material, a centimetre under
    # the mapped roads so junction overlaps resolve
    bm_m = bmesh.new()
    km_m = 0.0
    for s in surround()["streets"]:
        pts = s.get("pts") or []
        if len(pts) < 2:
            continue
        if all(max(abs(p[0]), abs(p[1])) > 6800.0 for p in pts):
            continue
        w = 6.5 if s["cls"].startswith("tertiary") else 5.5
        pts = resample(pts, 45.0)
        drape(bm_m, pts, w, 0.06)
        km_m += sum(math.dist(pts[i], pts[i + 1])
                    for i in range(len(pts) - 1)) / 1000.0
    bm_to_object(bm_m, "SBGR_StreetsMinor", P["road_paved"], c_road,
                 smooth=True)
    print("roads: %d ways  %.1f km paved  %.1f km unpaved  +%.0f km minor "
          "streets" % (n, km_p, km_d, km_m))


def build_rail(d, P, c_rail):
    """The CPTM Line 13 into the airport - 39 mapped ways, 32 km, much of it
    on VIADUCT (the OSM ways carry bridge=yes). Elevated spans are built as a
    deck 8 m up on piers; ground spans as a ballast ribbon. The line and its
    bridge flags are data; the deck section is inference."""
    bm_bed, bm_deck, bm_pier = bmesh.new(), bmesh.new(), bmesh.new()
    km = 0.0
    for r in d["railways"]:
        if r.get("railway") not in ("rail", "light_rail"):
            continue
        pts = r.get("polygon_xy_m")
        if not pts or len(pts) < 2:
            continue
        pts = resample(pts, 40.0)
        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        km += L / 1000.0
        if r.get("bridge"):
            drape(bm_deck, pts, 9.0, 8.0)
            # piers every ~35 m
            acc = 0.0
            for i in range(len(pts) - 1):
                ax, ay = pts[i]
                bx, by = pts[i + 1]
                ux, uy, seg = unit(ax, ay, bx, by)
                t = 35.0 - acc
                while t < seg:
                    px, py = ax + ux * t, ay + uy * t
                    zb = surface_z(px, py)
                    post(bm_pier, px, py, 1.0, zb - 1.0, zb + 7.6)
                    t += 35.0
                acc = (acc + seg) % 35.0
            # parapets
            drape(bm_deck, pts, 0.4, 9.3)
        else:
            drape(bm_bed, pts, 9.0, 0.12)
    bm_to_object(bm_bed, "SBGR_RailBed", P["rail_bed"], c_rail, smooth=True)
    bm_to_object(bm_deck, "SBGR_RailViaduct", P["rail_deck"], c_rail)
    bm_to_object(bm_pier, "SBGR_RailPiers", P["rail_deck"], c_rail)
    print("rail: %.1f km" % km)


def build_water(d, P, c_water):
    """251 mapped features: the Rio Baquirivu-Guacu along the north fence -
    the one green gap in the city ring - its tributaries, and the ponds.
    Widths per class are ESTIMATES; levels of bodies are the 40th percentile
    of the ground under their own shoreline (the SDSC recipe)."""
    bm_s, bm_b = bmesh.new(), bmesh.new()
    km = 0.0
    nb = 0
    for w in d["water"]:
        pts = w.get("polygon_xy_m")
        if not pts or len(pts) < 2:
            continue
        ww = w.get("waterway")
        if ww:
            width = {"river": 14.0, "canal": 7.0, "stream": 4.0,
                     "drain": 2.5, "ditch": 2.0}.get(ww, 4.0)
            pts2 = resample(pts, 40.0)
            drape(bm_s, pts2, width, 0.10)
            km += sum(math.dist(pts2[i], pts2[i + 1])
                      for i in range(len(pts2) - 1)) / 1000.0
        elif "area_m2" in w:
            ring = dedupe_ring(pts)
            if len(ring) < 3:
                continue
            zs = sorted(surface_z(x, y) for x, y in ring)
            level = zs[int(len(zs) * 0.40)] + 0.10
            vs = [bm_b.verts.new((x, y, level)) for x, y in ring]
            try:
                f = bm_b.faces.new(vs)
                bmesh.ops.triangulate(bm_b, faces=[f])
                nb += 1
            except ValueError:
                pass
    bm_to_object(bm_s, "SBGR_Watercourses", P["water"], c_water, smooth=True)
    bm_to_object(bm_b, "SBGR_WaterBodies", P["water"], c_water)
    print("water: %.1f km of watercourse, %d bodies" % (km, nb))


def build_trees(d, P, c_veg):
    """The Baquirivu green belt, the mapped forest patches - the ONE green
    gap in the city ring (RECOGNITION.md 2.3) - gallery rows on the
    watercourses, and (since the surround round) verge rows along the mapped
    major roads and scattered crowns on the green landuse. Unlike SDSC the
    horizon does NOT depend on these (the ring is real terrain); they are
    the middle-ground texture a subtropical metropolis edge actually
    carries. Species/spacing not surveyed. The serra's closed canopy is
    build_serra_forest, not this."""
    import random
    rnd = random.Random(CITY_SEED + 1)
    bm_f, bm_f2, bm_t = bmesh.new(), bmesh.new(), bmesh.new()
    n = 0

    def plant(px, py, h, r, deep=False):
        nonlocal n
        bmc = bm_f2 if deep else bm_f
        zb = surface_z(px, py)
        post(bm_t, px, py, 0.30, zb, zb + h * 0.38)
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

    # gallery rows on the watercourses
    for w in d["water"]:
        if not w.get("waterway"):
            continue
        pts = w.get("polygon_xy_m") or []
        for i in range(len(pts) - 1):
            ax, ay = pts[i][:2]
            bx, by = pts[i + 1][:2]
            if max(abs(ax), abs(ay)) > 6500:
                continue
            ux, uy, L = unit(ax, ay, bx, by)
            if L < 1.0:
                continue
            t = rnd.random() * 40.0
            while t < L:
                if rnd.random() < 0.30:
                    t += 30.0 + rnd.random() * 60.0
                    continue
                off = (rnd.random() - 0.5) * 36.0
                px = ax + ux * t - uy * off
                py = ay + uy * t + ux * off
                if ring_dist(px, py) > -10.0:
                    # inside the fence: only along the north Baquirivu belt,
                    # never on the movement area
                    if py < 1350.0:
                        t += 30.0
                        continue
                h = 9.0 + rnd.random() * 9.0
                plant(px, py, h, h * (0.34 + rnd.random() * 0.20),
                      deep=rnd.random() < 0.4)
                t += 18.0 + rnd.random() * 22.0
        if n > 2400:
            break
    # mapped forest patches: clustered crowns
    for l in d["landuse"]:
        if l.get("landuse") != "forest":
            continue
        ring = dedupe_ring(l.get("polygon_xy_m") or [])
        if len(ring) < 3:
            continue
        for (x, y) in _cells(ring, 38.0, -15000.0, -15000.0):
            if abs(x) > 6500 or abs(y) > 6500 or n > 3400:
                continue
            h = 10.0 + rnd.random() * 8.0
            plant(x + (rnd.random() - 0.5) * 18, y + (rnd.random() - 0.5) * 18,
                  h, h * 0.45, deep=True)
    # verge rows along the mapped major roads - the city's aerials show the
    # Dutra and the avenidas lined green; irregular, one side at a time
    n_verge0 = n
    for r in d["roads"]:
        if n - n_verge0 > 1800:
            break
        hw = r.get("highway")
        if hw not in ("motorway", "trunk", "primary", "secondary",
                      "tertiary"):
            continue
        pts = r.get("polygon_xy_m") or []
        half = ROAD_WIDTH.get(hw, 8.0) * 0.5
        # t accumulates ALONG THE WAY, not per segment - OSM nodes come
        # every 10-100 m and a per-segment reset plants almost nothing
        t = rnd.random() * 60.0
        for i in range(len(pts) - 1):
            ax, ay = pts[i][:2]
            bx, by = pts[i + 1][:2]
            ux, uy, L = unit(ax, ay, bx, by) if (ax, ay) != (bx, by) \
                else (0.0, 0.0, 0.0)
            if L < 0.1:
                continue
            if max(abs(ax), abs(ay)) > 5500:
                t = max(0.0, t - L)
                continue
            while t < L:
                if rnd.random() < 0.45:
                    t += 45.0 + rnd.random() * 70.0
                    continue
                side = 1.0 if rnd.random() < 0.5 else -1.0
                off = side * (half + 4.0 + rnd.random() * 6.0)
                px = ax + ux * t - uy * off
                py = ay + uy * t + ux * off
                if ring_dist(px, py) > -12.0:
                    t += 50.0
                    continue
                h = 7.0 + rnd.random() * 6.0
                plant(px, py, h, h * (0.36 + rnd.random() * 0.18),
                      deep=rnd.random() < 0.3)
                t += 45.0 + rnd.random() * 55.0
            t -= L
    # scattered crowns on the mapped green landuse (parks, cemeteries,
    # recreation grounds - the tint alone read as felt)
    n_park0 = n
    for l in d["landuse"]:
        if n - n_park0 > 900:
            break
        if l.get("landuse") not in ("recreation_ground", "village_green",
                                    "cemetery", "meadow", "farmland"):
            continue
        ring = dedupe_ring(l.get("polygon_xy_m") or [])
        if len(ring) < 3:
            continue
        for (x, y) in _cells(ring, 70.0, -15000.0, -15000.0):
            if abs(x) > 6000 or abs(y) > 6000 or n - n_park0 > 900:
                continue
            if rnd.random() < 0.45 or ring_dist(x, y) > -12.0:
                continue
            h = 8.0 + rnd.random() * 8.0
            plant(x + (rnd.random() - 0.5) * 30, y + (rnd.random() - 0.5) * 30,
                  h, h * 0.42, deep=rnd.random() < 0.4)
    bm_to_object(bm_f, "SBGR_Trees", P["foliage"], c_veg, smooth=True)
    bm_to_object(bm_f2, "SBGR_TreesDeep", P["foliage2"], c_veg, smooth=True)
    bm_to_object(bm_t, "SBGR_TreeTrunks", P["trunk"], c_veg)
    print("trees:", n)


def build_serra_forest(P, c_veg, mask):
    """The single highest-impact change of the surround round: the
    Cantareira/Cabucu wall is CLOSED-CANOPY Atlantic forest, not bare hill.
    Squat crown blobs (14 verts each, one material) on a jittered 55 m
    lattice over every cell that is high (+32 m over the datum, easing to
    full density by +54), UNBUILT (no minor street within ~100 m - the
    street mask carves Bonsucesso and the hillside favelas out), and outside
    the fence. The terrain shading underneath (terrain_material) goes the
    same near-black green, so the crowns read as canopy texture on a canopy-
    coloured ground - and the 30 m tint sawtooth phase 2 recorded stepping
    down this flank is buried under them. The DSM already contains the real
    canopy height; these crowns re-texture that surface, declared."""
    import random
    rnd = random.Random(CITY_SEED + 5)
    bm = bmesh.new()
    n = 0
    px0, px1, py0, py1 = pad_box()
    STEP = 55.0
    NC = int(18600.0 / STEP)
    NJ = int((9300.0 + 6500.0) / STEP)    # y -6500..+9300: south of that is
    #                                       beyond the tint reach, haze +
    #                                       terrain shading own it
    for j in reversed(range(NJ)):         # NORTH FIRST - the Cantareira wall
        #                                   is the backdrop of every clip and
        #                                   must never lose out to the cap
        cy = -6500.0 + (j + 0.5) * STEP
        for i in range(NC):
            cx = -9300.0 + (i + 0.5) * STEP
            z = G.dem(cx, cy)
            if z < 32.0:
                continue
            if mask.urban(cx, cy):
                continue
            if px0 < cx < px1 and py0 < cy < py1 \
                    and ring_dist(cx, cy) > -60.0:
                continue
            if rnd.random() > 0.40 + 0.58 * _smoothstep((z - 32.0) / 22.0):
                continue
            if max(abs(cx - 2000.0), abs(cy)) > 7200.0 and (i + j) % 2:
                continue                  # thin the far flank; haze owns it
            if n >= 24000:
                break
            px = cx + (rnd.random() - 0.5) * 40.0
            py = cy + (rnd.random() - 0.5) * 40.0
            h = 10.0 + rnd.random() * 7.0
            r = h * (0.62 + rnd.random() * 0.25)
            zb = G.dem(px, py) - 1.0
            a0 = rnd.random() * 60.0
            ring1 = [bm.verts.new((px + r * math.cos(math.radians(a0 + k * 60)),
                                   py + r * math.sin(math.radians(a0 + k * 60)),
                                   zb + 0.30 * h)) for k in range(6)]
            r2 = r * 0.72
            ring2 = [bm.verts.new((px + r2 * math.cos(math.radians(a0 + 30 + k * 60)),
                                   py + r2 * math.sin(math.radians(a0 + 30 + k * 60)),
                                   zb + 0.78 * h)) for k in range(6)]
            top = bm.verts.new((px, py, zb + h))
            bot = bm.verts.new((px, py, zb))
            for k in range(6):
                kk = (k + 1) % 6
                try:
                    bm.faces.new((ring1[k], ring1[kk], ring2[k]))
                    bm.faces.new((ring2[k], ring1[kk], ring2[kk]))
                    bm.faces.new((ring2[k], ring2[kk], top))
                    bm.faces.new((ring1[kk], ring1[k], bot))
                except ValueError:
                    pass
            n += 1
    bm_to_object(bm, "SBGR_SerraCanopy", P["serra"], c_veg, smooth=True)
    print("serra canopy crowns:", n)


# ---------------------------------------------------------------------------
# THE OPERATION - GSE at the occupied stands, and the neutral proxies
# ---------------------------------------------------------------------------
GSE_KINDS = (
    ("tug", 4.8, 2.4, 1.7, "gse_white"),
    ("gpu", 3.2, 1.6, 1.8, "gse_yellow"),
    ("beltloader", 6.4, 2.2, 1.6, "gse_white"),
    ("stairs", 5.0, 1.8, 3.4, "gse_white"),
    ("catering", 7.0, 2.5, 3.6, "gse_white"),
    ("bus", 12.0, 2.5, 3.0, "bus"),
    ("cargoloader", 7.0, 3.2, 3.0, "gse_yellow"),
    ("van", 5.2, 2.0, 2.1, "gse_white"),
    ("bowser", 9.0, 2.6, 2.9, "gse_white"),
)


def build_gse(d, P, c_ops):
    """Ground kit at every OCCUPIED stand - the turnaround, not the heavy
    check: tug + towbar at the nose, GPU and loader at the wing, catering on
    the starboard side, stairs and a bus at the remote row, dolly trains and
    ULDs at the cargo frontage. ALL positions are inference; that a hub ramp
    HAS this kit is not (refs/t3_apron_747_a330_masts_2023.jpg shows the
    marshaller, lanes and kit at work)."""
    import random
    rnd = random.Random(CITY_SEED + 2)
    bms = {k: bmesh.new() for k in ("gse_white", "gse_yellow", "gse_dark",
                                    "gse_red", "bus", "dolly", "uld")}

    def put(kind, x, y, hdg, zb):
        for (nm, L, W, Hh, mk) in GSE_KINDS:
            if nm != kind:
                continue
            obox(bms[mk], x, y, zb + 0.28, zb + Hh, L, W, hdg)
            obox(bms["gse_dark"], x, y, zb, zb + 0.34, L * 0.92, W * 1.02, hdg)
            if kind == "tug":
                a = math.radians(hdg)
                ux, uy = math.sin(a), math.cos(a)
                obox(bms["gse_yellow"], x + ux * (L * 0.5 + 2.6),
                     y + uy * (L * 0.5 + 2.6), zb + 0.35, zb + 0.55,
                     5.2, 0.35, hdg)

    n = 0
    for (tag, key, x, y, hdg, zz) in SBGR_STANDS:
        L, S, F, R, GH = AC_TYPES[key]
        a = math.radians(hdg)
        fx, fy = math.sin(a), math.cos(a)
        rx, ry = fy, -fx
        zb = zz + Z_APRON

        def at(along, lat):
            return (x + fx * along + rx * lat, y + fy * along + ry * lat)

        if tag == "HGR":
            # the hangar 777: kit to one side, the door line kept clear for
            # the phase-3 tow - the SDSC hangar-9 lesson
            put("tug", *at(L * 0.75, R * 4.0), hdg + 160.0, zb)
            put("van", *at(L * 0.1, R * 5.0), hdg + 90.0, zb)
            n += 2
            continue
        put("tug", *at(L * 0.62, 0.0), hdg + 180.0, zb)
        put("gpu", *at(L * 0.16, R * 3.4), hdg + 90.0, zb)
        n += 2
        if tag.startswith("C"):
            # cargo: loader at the forward door, a dolly train alongside
            put("cargoloader", *at(L * 0.2, -R * 3.0), hdg, zb)
            for k in range(4):
                px, py = at(-L * 0.15 - k * 5.0, R * 4.4)
                obox(bms["dolly"], px, py, zb + 0.3, zb + 0.9, 4.0, 2.4, hdg + 90)
                if rnd.random() < 0.7:
                    obox(bms["uld"], px, py, zb + 0.9, zb + 2.3, 3.1, 2.2,
                         hdg + 90)
            n += 5
        elif tag.startswith("R"):
            # remote row: stairs fore and aft, a bus
            put("stairs", *at(L * 0.25, R * 2.6), hdg + 90.0, zb)
            put("stairs", *at(-L * 0.28, R * 2.6), hdg + 90.0, zb)
            put("bus", *at(L * 0.05, R * 5.2), hdg + 85.0, zb)
            n += 3
        else:
            # gate stand: loader + catering
            put("beltloader", *at(-L * 0.10, -R * 3.2), hdg + 70.0, zb)
            put("catering", *at(L * 0.05, -R * 3.8), hdg, zb)
            if rnd.random() < 0.5:
                put("van", *at(-L * 0.30, R * 3.4), hdg, zb)
            n += 3
    # a bowser row by the fuel farm tanks (the mapped storage tanks)
    for k in range(3):
        put("bowser", 2100.0 + k * 12.0, 1395.0, 73.0, Z_HGR + Z_APRON)
        n += 1
    key2mat = dict(gse_white="gse_white", gse_yellow="gse_yellow",
                   gse_dark="gse_dark", gse_red="gse_red", bus="bus",
                   dolly="dolly", uld="uld")
    for k, bm in bms.items():
        bm_to_object(bm, "SBGR_GSE_%s" % k.split("_")[-1].title(),
                     P[key2mat[k]], c_ops)
    print("GSE: %d clusters" % n)


def airliner_proxy(name, length, span, fin_h, fus_r, gear_h, mats):
    """Low-poly NEUTRAL airliner, nose along +X, wheels on z = 0 - the SDSC
    proxy, engines always on, no livery: the honest stand-in for the
    non-LATAM traffic this repository has no models for."""
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
        v = [bm.verts.new((-length * 0.40, s * fus_r * 0.5, hc + fus_r * 0.15)),
             bm.verts.new((-length * 0.50, s * fus_r * 0.5, hc + fus_r * 0.15)),
             bm.verts.new((-length * 0.50, s * span * 0.17, hc + fus_r * 0.45)),
             bm.verts.new((-length * 0.44, s * span * 0.17, hc + fus_r * 0.45))]
        try:
            bm.faces.new(v)
        except ValueError:
            pass
        post(bm, -length * 0.06, s * fus_r * 1.5, 0.30, 0.0, hc - fus_r * 0.8)
    post(bm, length * 0.33, 0.0, 0.24, 0.0, hc - fus_r * 0.85)
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


def build_parked_proxies(P, c_ops):
    """The NON-LATAM presence: neutral white proxies at PROXY_STANDS. GRU's
    ramp is half other airlines' metal and this repository has no non-LATAM
    model; an anonymous white airliner at a distant gate is the honest
    rendering, declared here and in the README."""
    protos = {}
    n = 0
    for (tag, key, x, y, hdg, zz) in PROXY_STANDS:
        if key not in protos:
            L, S, F, R, GH = AC_TYPES[key]
            protos[key] = airliner_proxy("SBGR_Proxy_%s" % key, L, S, F, R,
                                         GH, (P["ac_white"], P["ac_grey"]))
        me, mef = protos[key]
        ob = bpy.data.objects.new("SBGR_AC_%s" % tag, me)
        ob.location = (x, y, zz + Z_APRON)
        ob.rotation_euler = (0.0, 0.0, math.radians(90.0 - hdg))
        c_ops.objects.link(ob)
        fin = bpy.data.objects.new("SBGR_ACFin_%s" % tag, mef)
        fin.parent = ob
        c_ops.objects.link(fin)
        n += 1
    print("neutral proxies: %d" % n)


# ---------------------------------------------------------------------------
# lighting
# ---------------------------------------------------------------------------
def build_light(P, c_light):
    scn = bpy.context.scene
    world = bpy.data.worlds.new("SBGR_World")
    scn.world = world
    world.use_nodes = True
    nt = world.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputWorld"); out.location = (400, 0)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.location = (200, 0)
    # Sun/sky balance MEASURED, not carried: a white lambertian card rendered
    # under this rig (Raw view transform, 2026-08-26) reads sun-only 0.32
    # against sky-only 0.14 - a 2.3:1 direct:diffuse split, inside the ~2:1
    # band a 16 deg sun through humid air actually gives (the SCL method).
    bg.inputs["Strength"].default_value = 0.14
    sky = nt.nodes.new("ShaderNodeTexSky"); sky.location = (-100, 0)
    configure_sky(sky)
    nt.links.new(sky.outputs[0], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])

    lamp = bpy.data.lights.new("SBGR_Sun", "SUN")
    lamp.energy = 16.5
    lamp.angle = math.radians(0.545)
    lamp.color = (1.0, 0.850, 0.690)       # 16.5 deg, humid summer air mass
    ob = bpy.data.objects.new("SBGR_Sun", lamp)
    ob.rotation_euler = (math.radians(90.0 - SUN_ELEV_DEG), 0.0,
                         math.radians(180.0 - SUN_AZIM_DEG))
    c_light.objects.link(ob)


# ---------------------------------------------------------------------------
# terrain
# ---------------------------------------------------------------------------
def build_terrain(stride_mid=1, stride_far=3, stride_near=1):
    global G, RING_F
    wipe()
    G = Ground()
    RING_F = RingField(dedupe_ring(data()["aerodrome_boundary_xy_m"][0]))
    sys.path.insert(0, HERE)
    import load_terrain as lt
    c = coll("SBGR_Terrain")
    layer = bpy.context.view_layer.active_layer_collection
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children[c.name]
    m = lt._meta()["grids"]
    g60, g30 = m["terrain_sbgr_60m"], m["terrain_sbgr_near_30m"]
    mk, sk = lt._dc(g60, 180.0 * stride_far, "far")
    lt.build("terrain_sbgr_far_180m", stride=stride_far,
             obj_name="SBGR_Terrain_Far", mask_inner=mk, sink=sk)
    mk, sk = lt._dc(g30, 60.0 * stride_mid, "mid")
    lt.build("terrain_sbgr_60m", stride=stride_mid,
             obj_name="SBGR_Terrain_Mid", mask_inner=mk, sink=sk)
    lt.build("terrain_sbgr_near_30m", stride=stride_near,
             obj_name="SBGR_Terrain_Near")
    bpy.context.view_layer.active_layer_collection = layer

    grade_aerodrome()
    m_t = terrain_material()
    for ob in c.objects:
        ob.data.materials.append(m_t)
    print("terrain polys:", sum(len(o.data.polygons) for o in c.objects))


def grade_aerodrome():
    """Push the near tier onto the graded surface inside the field and blend
    back to the raw DEM outside - flat-field edition, small numbers, same
    machinery. The DSM outside the fence is roofs and canopy (TERRAIN.md
    section 8); the blend starts AT the boundary so the city keeps its own
    lumpy surface, which under the tint reads as fabric."""
    ob = bpy.data.objects.get("SBGR_Terrain_Near")
    if ob is None:
        return
    me = ob.data
    moved = 0
    # Inside the fence the terrain must sit under the graded pad; outside it
    # must stay the raw DSM the city sheets are snapped to. Blend over the
    # pad's own 150 m skirt - NOT a kilometre ramp, which would drag the city
    # surface away from the tint cells lying on it.
    for v in me.vertices:
        d = ring_dist(v.co.x, v.co.y)
        if d <= -160.0:
            continue
        t = _smoothstep(-d / 150.0) if d < 0.0 else 0.0
        target = G.graded(v.co.x, v.co.y) - 0.8
        v.co.z = v.co.z * t + target * (1.0 - t)
        moved += 1
    print("graded terrain vertices:", moved)


def terrain_material():
    """Metropolis-and-serra ground: city-grey fabric on the flats, CLOSED-
    CANOPY dark green on the ranges, by HEIGHT above the datum - the
    Cantareira and the Serra do Mar are forest, the basin is city. A crude
    but honest split: the mapped landuse tint covers the near ring; this
    shades everything beyond it. The surround round re-cut the split: the
    old 25->90 m band left the whole visible flank a half-mixed tan (the
    owner's 'bare hills'; phase 2's first render already read as dunes), so
    the band is now 18->52 m - forest from low on the flank, the way the
    2023 photographs show a green WALL behind the field - the greens are
    darker (matching SBGR_SerraCanopy, so the instanced crowns read as
    texture on the same mass), and a 45 m canopy noise replaces the 420 m
    city block hash on the forest side."""
    m, nt, out, bsdf = _blank("SBGR_TerrainGround", 0.94)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1000, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-820, -200)
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    # block-hash mottle
    cx = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", sep.outputs["X"], 420.0))
    cy = _nm(nt, "FLOOR", _nm(nt, "DIVIDE", sep.outputs["Y"], 360.0))
    cell = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(cx, cell.inputs[0])
    nt.links.new(cy, cell.inputs[1])
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"
    nt.links.new(cell.outputs[0], wn.inputs["Vector"])
    city = nt.nodes.new("ShaderNodeValToRGB"); city.location = (-380, 100)
    cr = city.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.140, 0.112, 0.088, 1.0)   # warm roofscape
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.158, 0.148, 0.136, 1.0)   # concrete-grey blocks
    nt.links.new(wn.outputs["Value"], city.inputs["Fac"])
    # canopy mottle: ~45 m crowns-and-shadow features, not city blocks
    cnoise = nt.nodes.new("ShaderNodeTexNoise"); cnoise.location = (-600, -320)
    cnoise.noise_dimensions = "3D"
    cnoise.inputs["Scale"].default_value = 0.022
    cnoise.inputs["Detail"].default_value = 3.0
    cnoise.inputs["Roughness"].default_value = 0.55
    nt.links.new(geo.outputs["Position"], cnoise.inputs["Vector"])
    green = nt.nodes.new("ShaderNodeValToRGB"); green.location = (-380, -160)
    gr = green.color_ramp
    gr.elements[0].position = 0.30
    gr.elements[0].color = (0.013, 0.028, 0.009, 1.0)   # canopy shadow
    gr.elements[1].position = 0.85
    gr.elements[1].color = (0.034, 0.062, 0.020, 1.0)   # lit crown
    nt.links.new(cnoise.outputs["Fac"], green.inputs["Fac"])
    hfac = _sm(nt, sep.outputs["Z"], 18.0, 52.0)        # basin -> serra: the
    # Cabucu face is a green wall from low on its flank; the half-mixed tan
    # of the old 25->90 band is what the owner called empty bare hills
    mix = nt.nodes.new("ShaderNodeMixRGB")
    nt.links.new(city.outputs["Color"], mix.inputs["Color1"])
    nt.links.new(green.outputs["Color"], mix.inputs["Color2"])
    nt.links.new(hfac, mix.inputs["Fac"])
    # the ocean corner of the far tier: below -800 m the surface IS the
    # curvature drop over the Atlantic
    sea = _sm(nt, sep.outputs["Z"], -900.0, -700.0, 1.0, 0.0)
    mix2 = nt.nodes.new("ShaderNodeMixRGB")
    mix2.inputs["Color2"].default_value = (0.012, 0.030, 0.042, 1.0)
    nt.links.new(mix.outputs[0], mix2.inputs["Color1"])
    nt.links.new(sea, mix2.inputs["Fac"])
    nt.links.new(mix2.outputs[0], bsdf.inputs["Base Color"])
    _finish(nt, bsdf, out)
    return m


def main():
    args = argv_after_dashdash()
    if "--terrain" in args:
        build_terrain()
        path = os.path.join(HERE, "sbgr_terrain.blend")
    else:
        build_field()
        path = os.path.join(HERE, "sbgr_field.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("saved", path, os.path.getsize(path) // 1024, "kB")


if __name__ == "__main__":
    main()
