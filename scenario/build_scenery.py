#!/usr/bin/env python3
"""Build the SCL / SCEL scenery in Blender from the surveyed data in this folder.

The scenery is a SHARED ASSET: it is built into its own .blend files under
``scenario/`` and LINKED into each aircraft file, so fixing the airport fixes it
for every aircraft at once.

    blender -b --factory-startup -P scenario/build_scenery.py -- --field
    blender -b --factory-startup -P scenario/build_scenery.py -- --terrain

Outputs
    scenario/scl_field.blend    the aerodrome: runways, markings, taxiways,
                                aprons, buildings, LATAM base, tower, terminals,
                                parked aircraft, lighting masts, sun + sky
    scenario/scl_terrain.blend  the Andes / Coastal Range heightfield mesh

Reference frame (identical in both files, and documented in scenario/README.md)
    local ENU tangent plane, WGS84
    origin  = RWY 17L threshold, lat -33.3760915  lon -70.7867106
    x = East, y = North, z = Up, metres
    z = 0 at 474.0 m AMSL (published SCEL aerodrome elevation)

Data sources
    scl_osm.json            (c) OpenStreetMap contributors, ODbL 1.0
    scl_aip_corrections.json AIP-Chile / DGAC survey values (override OSM)
    scl_operations.md        AIP marking geometry, sun geometry
    terrain/*.npy            Copernicus DEM GLO-30 + SRTM control
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
# Survey constants. Every number here comes from scl_aip_corrections.json or
# scl_operations.md; nothing on this page is estimated.
# ---------------------------------------------------------------------------
THR_17R = (-1582.57, 459.21)      # AIP threshold, local frame
THR_35L = (-1411.15, -3337.32)
THR_17L = (0.21, 1.21)
THR_35R = (144.40, -3193.96)
END_35R_PAVE = (169.14, -3742.20)  # south pavement end of 17L/35R
W_17R = 45.0                        # DGAC IFIS
W_17L = 55.0                        # DGAC IFIS
TRACK_17R_DEG = 177.424

# Sun: mid-February, ~19:13 local. scl_operations.md section 5 tabulates
# 19:30 -> 11.5 deg / 264.7 deg and 19:45 -> 8.4 deg / 262.7 deg, i.e. 0.207 deg
# of elevation and 0.133 deg of azimuth per minute; 17 minutes earlier than
# 19:30 gives the values below. Still squarely in the recommended band - sun in
# the west, behind a camera looking east, lighting the aircraft's starboard side
# - but 15 deg puts sin(elev) = 0.26 on the ground instead of 0.15, which is the
# difference between a readable airfield and a black one.
SUN_ELEV_DEG = 15.0
SUN_AZIM_DEG = 267.0

# Haze. Koschmieder with an exponential boundary layer; see README.md.
HAZE_VIS_KM = 14.0        # surface meteorological visibility
HAZE_SCALE_H = 900.0      # aerosol scale height, metres

# ---------------------------------------------------------------------------
# Building heights.
#
# Of 748 OSM footprints, FOUR carry a height tag and 42 carry building:levels.
# Everything else below is an ESTIMATE BY TYPE, declared as such. It is not
# measured and must not be quoted as data.
# ---------------------------------------------------------------------------
HEIGHT_BY_TYPE = {
    "hangar": 16.0,      # generic GA / airline hangar, door ~12 m
    "warehouse": 12.0,   # cargo sheds, single tall bay
    "industrial": 10.0,
    "office": 14.0,      # ~4 floors
    "commercial": 9.0,
    "apartments": 15.0,  # ~5 floors
    "hotel": 18.0,
    "house": 4.0,
    "service": 5.0,      # plant rooms, small sheds
    "roof": 6.0,         # canopies
    "carport": 3.0,
    "parking": 10.0,
    "public": 6.0,
    "hut": 3.0,
    "kindergarten": 5.0,
    "manufacture": 10.0,
    "construction": 6.0,
    "ruins": 3.0,
    "yes": 7.0,          # untyped; most are single-storey airport service blocks
}
LEVEL_HEIGHT = 3.2       # metres per building:levels

# Named overrides. Each carries its justification in README.md.
HEIGHT_BY_NAME = {
    "Torre de Control SCL": 60.0,          # OSM height tag (DGAC publishes 65)
    "Torre de Control FACh": 15.0,         # OSM height tag
    "Base de Operaciones y Mantenimiento LATAM Airlines": 20.0,
    "LATAM": 23.0,                          # hangar: 18-25 m door range, mid+roof
    "Base de Mantenimiento Sky Airline": 21.0,
    "Terminal 2 Internacional": 28.0,
    "Terminal 1 Nacional": 16.0,
    "Dirección General de Aeronáutica Civil": 11.0,
    "Terminal de Carga Nacional": 12.0,
    "Terminal de Exportación Internacional (TEISA)": 12.0,
    "Centro de Importación": 12.0,
    "Holiday Inn Aeropuerto Santiago": 20.0,
    "Estacionamiento Expreso 1": 11.0,
    "Estacionamiento Expreso 2": 11.0,
}
PIER_HEIGHT = 18.0       # T2/T1 concourses
HANGAR_FACH = 14.0       # Hangar A..G, FACh/ENAER, gable

Z_GROUND = 0.00
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


def data():
    with open(os.path.join(HERE, "scl_osm.json")) as fh:
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


def add_mesh(name, verts, faces, mat, collection):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def dedupe_ring(poly):
    """OSM rings repeat the first node last; drop it and any coincident pair."""
    ring = [tuple(p) for p in poly]
    if len(ring) > 1 and math.dist(ring[0], ring[-1]) < 1e-6:
        ring = ring[:-1]
    out = []
    for p in ring:
        if not out or math.dist(out[-1], p) > 1e-6:
            out.append(p)
    return out


def prism(bm, ring, z0, z1):
    """Extruded footprint: walls + a filled top cap (and bottom left open)."""
    ring = dedupe_ring(ring)
    if len(ring) < 3:
        return
    top = [bm.verts.new((x, y, z1)) for x, y in ring]
    bot = [bm.verts.new((x, y, z0)) for x, y in ring]
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


def flat_poly(bm, ring, z):
    ring = dedupe_ring(ring)
    if len(ring) < 3:
        return
    vs = [bm.verts.new((x, y, z)) for x, y in ring]
    try:
        f = bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=[f])
    except ValueError:
        pass


def ribbon(bm, pts, width, z):
    """Turn a polyline into a flat strip of the given width."""
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
            if m < 1e-9:
                dx, dy = ax, ay
            else:
                dx, dy = dx / m, dy / m
        nx, ny = -dy, dx
        left.append(bm.verts.new((x + nx * h, y + ny * h, z)))
        right.append(bm.verts.new((x - nx * h, y - ny * h, z)))
    for i in range(len(pts) - 1):
        try:
            bm.faces.new((right[i], right[i + 1], left[i + 1], left[i]))
        except ValueError:
            pass


def bm_to_object(bm, name, mat, collection, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if mat:
        me.materials.append(mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------
# materials, with the atmospheric-haze term baked in
# ---------------------------------------------------------------------------
def haze_group():
    """Node group: mixes any shader toward airlight as a function of distance.

    Optical depth along the sight line, with an exponential aerosol layer:

        tau(d, z) = beta0 * d * (H/z) * (1 - exp(-z/H))

    which is the exact integral of exp(-z/H) along a straight ray that starts at
    the ground and ends at height z, distance d away. beta0 = 3.912 / V with V
    the surface meteorological visibility (Koschmieder). The airlight colour is
    the sky itself, sampled horizontally in the viewing azimuth.
    """
    g = bpy.data.node_groups.get("SCL_Haze")
    if g:
        return g
    g = bpy.data.node_groups.new("SCL_Haze", "ShaderNodeTree")
    g.interface.new_socket("Shader", in_out="INPUT", socket_type="NodeSocketShader")
    g.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
    nin = g.nodes.new("NodeGroupInput"); nin.location = (-1400, 200)
    nout = g.nodes.new("NodeGroupOutput"); nout.location = (600, 0)

    geo = g.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1400, -200)
    sep = g.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-1200, -260)
    g.links.new(geo.outputs["Position"], sep.inputs[0])

    zmax = g.nodes.new("ShaderNodeMath"); zmax.operation = "MAXIMUM"
    zmax.inputs[1].default_value = 1.0; zmax.location = (-1020, -260)
    g.links.new(sep.outputs["Z"], zmax.inputs[0])

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

    # Airlight colour. The Sky Texture node cannot be sampled in an arbitrary
    # direction, so the horizon colour is modelled directly: strong warm forward
    # scatter toward the low sun in the west, pale blue-grey away from it. That
    # is the split the photographs show - golden over the Coastal Range, pale
    # desaturated blue over the Andes.
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
    el[0].color = (0.300, 0.325, 0.400, 1.0)      # away from the sun: cool pale
    el[1].position = 0.62
    el[1].color = (0.440, 0.415, 0.395, 1.0)
    e2 = ramp.color_ramp.elements.new(0.88)
    e2.color = (0.860, 0.620, 0.370, 1.0)
    e3 = ramp.color_ramp.elements.new(1.0)
    e3.color = (1.000, 0.720, 0.420, 1.0)         # into the sun: golden
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
    sky.sun_disc = False        # the explicit Sun lamp provides the disc
    sky.sun_intensity = 1.0
    sky.sun_size = math.radians(0.545)
    sky.altitude = 474
    sky.air_density = 2.2      # Santiago valley: dusty, thick
    sky.aerosol_density = 4.5
    sky.ozone_density = 1.0


_MATS = {}


def mat(name, color, rough=0.85, metal=0.0, hazy=True, emit=None):
    key = name
    if key in _MATS:
        return _MATS[key]
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
    m.diffuse_color = (*color, 1.0)          # viewport / Workbench colour
    m.roughness = rough
    m.metallic = metal
    _MATS[key] = m
    return m


def soil_material(name, base, dark, scrub, scale=0.0016):
    """Bare ochre infield. scl_operations.md section 7: dry ochre-to-reddish soil
    with darker ploughed-looking patches, no turf anywhere inside the fence. A
    green European infield is the fastest way to make this scene read as wrong."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (800, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (400, 0)
    bsdf.inputs["Roughness"].default_value = 0.95
    tex = nt.nodes.new("ShaderNodeTexCoord"); tex.location = (-900, 0)
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.location = (-700, 0)
    n1.inputs["Scale"].default_value = scale * 1000.0
    n1.inputs["Detail"].default_value = 6.0
    n1.inputs["Roughness"].default_value = 0.55
    map1 = nt.nodes.new("ShaderNodeMapping"); map1.location = (-820, 0)
    map1.inputs["Scale"].default_value = (0.001, 0.001, 0.001)
    nt.links.new(tex.outputs["Object"], map1.inputs["Vector"])
    nt.links.new(map1.outputs["Vector"], n1.inputs["Vector"])
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.location = (-700, -260)
    n2.inputs["Scale"].default_value = scale * 9000.0
    n2.inputs["Detail"].default_value = 4.0
    nt.links.new(map1.outputs["Vector"], n2.inputs["Vector"])
    mix1 = nt.nodes.new("ShaderNodeMixRGB"); mix1.location = (-380, 0)
    mix1.inputs["Color1"].default_value = (*base, 1.0)
    mix1.inputs["Color2"].default_value = (*dark, 1.0)
    nt.links.new(n1.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMixRGB"); mix2.location = (-140, 0)
    mix2.inputs["Color2"].default_value = (*scrub, 1.0)
    nt.links.new(mix1.outputs[0], mix2.inputs["Color1"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-380, -300)
    ramp.color_ramp.elements[0].position = 0.52
    ramp.color_ramp.elements[1].position = 0.72
    nt.links.new(n2.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix2.inputs["Factor"])
    nt.links.new(mix2.outputs[0], bsdf.inputs["Base Color"])
    grp = nt.nodes.new("ShaderNodeGroup"); grp.node_tree = haze_group()
    grp.location = (620, 0)
    nt.links.new(bsdf.outputs[0], grp.inputs[0])
    nt.links.new(grp.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*base, 1.0)
    return m


def palette():
    """Colours are linear-Rec709. Sources are the photographs listed in
    scl_references.md section 7 / scl_operations.md section 7, read
    qualitatively — they are not spectrophotometric measurements."""
    return dict(
        asphalt=mat("SCL_Asphalt", (0.058, 0.062, 0.058), 0.78),
        shoulder=mat("SCL_AsphaltShoulder", (0.095, 0.093, 0.085), 0.88),
        concrete=mat("SCL_Concrete", (0.235, 0.230, 0.215), 0.84),
        taxi=mat("SCL_TaxiwayAsphalt", (0.070, 0.073, 0.070), 0.84),
        white=mat("SCL_MarkingWhite", (0.520, 0.520, 0.500), 0.65),
        yellow=mat("SCL_MarkingYellow", (0.400, 0.260, 0.020), 0.70),
        red=mat("SCL_MarkingRed", (0.320, 0.030, 0.020), 0.70),
        soil=soil_material("SCL_Soil", (0.205, 0.138, 0.078),
                           (0.128, 0.082, 0.045), (0.098, 0.098, 0.052)),
        soil_dark=soil_material("SCL_SoilOutfield", (0.175, 0.122, 0.070),
                                (0.105, 0.072, 0.042), (0.082, 0.092, 0.045),
                                scale=0.0009),
        scrub=mat("SCL_Scrub", (0.062, 0.062, 0.030), 0.95),
        farm=mat("SCL_Farmland", (0.070, 0.085, 0.035), 0.94),
        roof_light=mat("SCL_RoofLight", (0.330, 0.335, 0.330), 0.72),
        roof_grey=mat("SCL_RoofGrey", (0.140, 0.143, 0.145), 0.78),
        roof_navy=mat("SCL_RoofNavy", (0.020, 0.030, 0.075), 0.65),
        roof_maroon=mat("SCL_RoofMaroon", (0.130, 0.010, 0.055), 0.70),
        wall=mat("SCL_WallLight", (0.300, 0.298, 0.288), 0.80),
        wall_grey=mat("SCL_WallGrey", (0.170, 0.172, 0.175), 0.82),
        wall_tan=mat("SCL_WallTan", (0.245, 0.205, 0.150), 0.82),
        wall_pale=mat("SCL_WallPale", (0.390, 0.388, 0.375), 0.78),
        foliage=mat("SCL_Foliage", (0.052, 0.070, 0.028), 0.90),
        trunk=mat("SCL_TreeTrunk", (0.048, 0.038, 0.026), 0.90),
        glass=mat("SCL_Glass", (0.030, 0.045, 0.050), 0.16, metal=0.35),
        tower_concrete=mat("SCL_TowerConcrete", (0.185, 0.182, 0.176), 0.80),
        steel=mat("SCL_SteelLight", (0.330, 0.340, 0.350), 0.42, metal=0.85),
        mast=mat("SCL_MastWhite", (0.520, 0.525, 0.530), 0.50),
        t2_roof=mat("SCL_T2Roof", (0.088, 0.092, 0.094), 0.58, metal=0.45),
        t2_green=mat("SCL_T2PanelGreen", (0.185, 0.290, 0.150), 0.72),
        t2_brise=mat("SCL_T2Brise", (0.360, 0.115, 0.030), 0.62),
        latam_indigo=mat("SCL_LATAM_Indigo", (0.023, 0.000, 0.246), 0.55),
        latam_coral=mat("SCL_LATAM_Coral", (0.847, 0.008, 0.082), 0.45),
        latam_white=mat("SCL_LATAM_White", (0.700, 0.705, 0.720), 0.40),
        ac_white=mat("SCL_AircraftWhite", (0.640, 0.645, 0.660), 0.30),
        ac_grey=mat("SCL_AircraftGrey", (0.180, 0.190, 0.200), 0.35),
        sky_purple=mat("SCL_SkyAirlinePurple", (0.180, 0.020, 0.300), 0.45),
        jetsmart=mat("SCL_JetSmartOrange", (0.780, 0.130, 0.010), 0.45),
        bridge_blue=mat("SCL_JetBridgeBlue", (0.020, 0.060, 0.300), 0.45),
        terrain=None,
    )


# ---------------------------------------------------------------------------
# runways and ICAO markings
# ---------------------------------------------------------------------------
# ICAO Annex 14 Fig. 5-3 style stroke glyphs, in a 9 m tall box, stroke 1.5 m.
# Each glyph is a list of (x0, y0, x1, y1) rectangles; y up-field.
S = 1.5
GLYPHS = {
    "1": [(1.5, 0, 3.0, 9.0), (0.0, 7.5, 1.5, 9.0), (0.0, 0.0, 4.5, 1.5)],
    "3": [(0.0, 7.5, 4.5, 9.0), (3.0, 4.5, 4.5, 9.0), (1.0, 3.9, 4.5, 5.1),
          (3.0, 0.0, 4.5, 4.5), (0.0, 0.0, 4.5, 1.5)],
    "5": [(0.0, 7.5, 4.5, 9.0), (0.0, 4.5, 1.5, 9.0), (0.0, 3.9, 4.5, 5.1),
          (3.0, 0.0, 4.5, 4.5), (0.0, 0.0, 4.5, 1.5)],
    "7": [(0.0, 7.5, 4.5, 9.0), (3.0, 0.0, 4.5, 7.5)],
    "L": [(0.0, 0.0, 1.5, 9.0), (0.0, 0.0, 4.5, 1.5)],
    "R": [(0.0, 0.0, 1.5, 9.0), (0.0, 7.5, 4.5, 9.0), (3.0, 4.5, 4.5, 9.0),
          (0.0, 3.9, 4.5, 5.1), (3.0, 0.0, 4.5, 3.9)],
}
GLYPH_W = 4.5
GLYPH_GAP = 1.5


def paint_glyphs(bm, text, along0, lateral_centre, ux, uy, ox, oy, z, flip=False):
    """Paint characters lying on the pavement, read from the threshold."""
    nx, ny = -uy, ux                      # left-hand normal of the roll direction
    total = len(text) * GLYPH_W + (len(text) - 1) * GLYPH_GAP
    x0 = -total * 0.5
    for ch in text:
        for (gx0, gy0, gx1, gy1) in GLYPHS[ch]:
            for (a, b) in (((x0 + gx0, gy0), (x0 + gx1, gy1)),):
                corners = [(a[0], a[1]), (b[0], a[1]), (b[0], b[1]), (a[0], b[1])]
                vs = []
                for (cx, cy) in corners:
                    lat = lateral_centre + (-cx if flip else cx)
                    dist = along0 + (cy if not flip else -cy)
                    px = ox + ux * dist + nx * lat
                    py = oy + uy * dist + ny * lat
                    vs.append(bm.verts.new((px, py, z)))
                try:
                    bm.faces.new(vs)
                except ValueError:
                    pass
        x0 += GLYPH_W + GLYPH_GAP


def runway_strip(bm, ox, oy, ux, uy, a0, a1, l0, l1, z):
    nx, ny = -uy, ux
    pts = [(a0, l0), (a1, l0), (a1, l1), (a0, l1)]
    vs = [bm.verts.new((ox + ux * a + nx * l, oy + uy * a + ny * l, z))
          for a, l in pts]
    try:
        bm.faces.new(vs)
    except ValueError:
        pass


def build_runway(bm_pave, bm_shoulder, bm_mark, thr_a, thr_b, width,
                 name_a, name_b, disp_b=0.0, pave_end_b=None):
    """One runway: pavement, shoulders and the full ICAO marking set at both ends.

    Marking geometry is the set measured on RWY 17R and tabulated in
    scl_operations.md section 3, with the documented +2 m along-track imagery bias
    removed. The same pattern is mirrored onto the other end and scaled onto the
    55 m runway, where it was not independently measured.
    """
    ox, oy = thr_a
    ux, uy, L = unit(thr_a[0], thr_a[1], thr_b[0], thr_b[1])
    nx, ny = -uy, ux
    half = width * 0.5
    k = width / 45.0          # lateral scale from the measured 45 m runway

    a_start = 0.0
    a_end = L + disp_b
    if pave_end_b is not None:
        _, _, a_end = unit(thr_a[0], thr_a[1], pave_end_b[0], pave_end_b[1])

    runway_strip(bm_pave, ox, oy, ux, uy, a_start - 60.0, a_end + 60.0,
                 -half, half, Z_RUNWAY)
    for s in (1, -1):
        runway_strip(bm_shoulder, ox, oy, ux, uy, a_start - 90.0, a_end + 90.0,
                     s * half, s * (half + 10.5), Z_SHOULDER)

    for (base, direction, label) in ((0.0, +1, name_a), (a_end, -1, name_b)):
        d = direction

        def A(v):
            return base + d * v

        # threshold stripes: 12, outer edge at +-22.25 m (scaled)
        w, g, inner = 1.75 * k, 1.95 * k, 2.0 * k
        for s in (1, -1):
            for i in range(6):
                l0 = inner + i * (w + g)
                runway_strip(bm_mark, ox, oy, ux, uy, A(6.0), A(36.2),
                             s * l0, s * (l0 + w), Z_MARK)
        # designator: letter first from the threshold, number beyond it
        letter, number = label[-1], label[:-1]
        paint_glyphs(bm_mark, letter, A(45.8) if d > 0 else A(55.0), 0.0,
                     ux * d, uy * d, ox, oy, Z_MARK)
        paint_glyphs(bm_mark, number, A(62.0) if d > 0 else A(71.0), 0.0,
                     ux * d, uy * d, ox, oy, Z_MARK)
        # aiming point
        runway_strip(bm_mark, ox, oy, ux, uy, A(385.0), A(430.3),
                     9.25 * k, 15.25 * k, Z_MARK)
        runway_strip(bm_mark, ox, oy, ux, uy, A(385.0), A(430.3),
                     -15.25 * k, -9.25 * k, Z_MARK)
        # touchdown zone, pattern B; the 450 m pair is deleted by rule
        for dist in (150, 300, 600, 750, 900):
            for s in (1, -1):
                for i in range(3):
                    l0 = (9.25 + i * 3.3) * k
                    runway_strip(bm_mark, ox, oy, ux, uy, A(dist), A(dist + 23.8),
                                 s * l0, s * (l0 + 1.8 * k), Z_MARK)
    # centre line: 30 m stripe, 30 m gap, 0.9 m wide
    a = 12.0
    while a + 30.0 < a_end - 12.0:
        runway_strip(bm_mark, ox, oy, ux, uy, a, a + 30.0, -0.45, 0.45, Z_MARK)
        a += 60.0
    # side stripes
    for s in (1, -1):
        runway_strip(bm_mark, ox, oy, ux, uy, a_start, a_end,
                     s * (half - 1.0), s * half, Z_MARK)


# ---------------------------------------------------------------------------
# the field
# ---------------------------------------------------------------------------
def build_field():
    wipe()
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    P = palette()
    d = data()

    c_root = coll("SCL_Field")
    c_run = coll("SCL_Runways", c_root)
    c_taxi = coll("SCL_Taxiways", c_root)
    c_apron = coll("SCL_Aprons", c_root)
    c_ground = coll("SCL_Ground", c_root)
    c_bldg = coll("SCL_Buildings", c_root)
    c_latam = coll("SCL_LATAMBase", c_root)
    c_term = coll("SCL_Terminals", c_root)
    c_tower = coll("SCL_Tower", c_root)
    c_furn = coll("SCL_Furniture", c_root)
    c_park = coll("SCL_ParkedAircraft", c_root)
    c_anchor = coll("SCL_Anchors")
    c_light = coll("SCL_Light")

    # ---- ground -----------------------------------------------------------
    bm = bmesh.new()
    boundary = d["aerodrome_boundary_xy_m"][0]
    flat_poly(bm, boundary, Z_GROUND)
    bm_to_object(bm, "SCL_AerodromeGround", P["soil"], c_ground)

    # a wider apron of bare ground so the field does not end abruptly
    bm = bmesh.new()
    xs = [p[0] for p in boundary]; ys = [p[1] for p in boundary]
    pad = 1800.0
    flat_poly(bm, [(min(xs) - pad, min(ys) - pad), (max(xs) + pad, min(ys) - pad),
                   (max(xs) + pad, max(ys) + pad), (min(xs) - pad, max(ys) + pad)],
              Z_GROUND - 0.40)
    bm_to_object(bm, "SCL_FieldSurround", P["soil_dark"], c_ground)

    # ---- runways ----------------------------------------------------------
    bmp, bms, bmm = bmesh.new(), bmesh.new(), bmesh.new()
    build_runway(bmp, bms, bmm, THR_17R, THR_35L, W_17R, "17R", "35L")
    build_runway(bmp, bms, bmm, THR_17L, THR_35R, W_17L, "17L", "35R",
                 disp_b=548.8, pave_end_b=END_35R_PAVE)
    bm_to_object(bmp, "SCL_RunwayPavement", P["asphalt"], c_run)
    bm_to_object(bms, "SCL_RunwayShoulders", P["shoulder"], c_run)
    bm_to_object(bmm, "SCL_RunwayMarkings", P["white"], c_run)

    # ---- taxiways ---------------------------------------------------------
    bm, bmc = bmesh.new(), bmesh.new()
    for t in d["taxiways"]:
        pts = t["polygon_xy_m"]
        w = 36.0 if t.get("ref") == "A" else 23.0
        if t.get("is_closed"):
            flat_poly(bm, pts, Z_TAXI)
        else:
            ribbon(bm, pts, w, Z_TAXI)
            ribbon(bmc, pts, 0.30, Z_TAXI + 0.03)
    bm_to_object(bm, "SCL_TaxiwayPavement", P["taxi"], c_taxi)
    bm_to_object(bmc, "SCL_TaxiwayCentrelines", P["yellow"], c_taxi)

    # ---- aprons -----------------------------------------------------------
    bm = bmesh.new()
    for a in d["aprons"]:
        flat_poly(bm, a["polygon_xy_m"], Z_APRON)
    bm_to_object(bm, "SCL_ApronConcrete", P["concrete"], c_apron)

    # ---- buildings --------------------------------------------------------
    build_buildings(d, P, c_bldg, c_latam, c_term, c_tower)
    build_control_tower(P, c_tower)
    build_latam_signage(P, c_latam)
    build_masts(d, P, c_furn)
    build_trees(d, P, c_furn)
    build_windsocks(d, P, c_furn)
    build_papi(P, c_furn)
    build_parked_aircraft(d, P, c_park)

    # ---- anchors ----------------------------------------------------------
    for name, xy, brg in (("SCL_17R_Threshold", THR_17R, TRACK_17R_DEG),
                          ("SCL_17L_Threshold", THR_17L, 177.416),
                          ("SCL_35L_Threshold", THR_35L, 357.424),
                          ("SCL_LATAM_Base", (-620.0, -1290.0), TRACK_17R_DEG)):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 60.0
        e.location = (xy[0], xy[1], 0.0)
        # +Y of the empty points down the take-off track
        e.rotation_euler = (0.0, 0.0, math.radians(-brg))
        c_anchor.objects.link(e)

    # ---- light ------------------------------------------------------------
    build_light(P, c_light)

    scn.render.engine = "CYCLES"
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Base Contrast"
    scn.view_settings.exposure = 0.0
    for cam in bpy.data.cameras:
        cam.clip_end = 250000.0
    print("field objects:", len(bpy.data.objects),
          "polys:", sum(len(o.data.polygons) for o in bpy.data.objects
                        if o.type == "MESH"))


def estimate_height(b):
    """Return (height, source-tag). 'osm' means measured/tagged; 'est' is ours."""
    if b.get("height_m"):
        return float(b["height_m"]), "osm"
    nm = b.get("name")
    if nm and nm in HEIGHT_BY_NAME:
        return HEIGHT_BY_NAME[nm], "est"
    lv = b.get("building_levels")
    if lv:
        try:
            return float(str(lv).split(";")[0]) * LEVEL_HEIGHT, "osm-levels"
        except ValueError:
            pass
    return HEIGHT_BY_TYPE.get(b.get("building"), 7.0), "est"


def gable(bm, ring, eave, ridge, bearing_deg):
    """Hangar-style volume: prism to the eave, then a shallow gable on top."""
    ring = dedupe_ring(ring)
    if len(ring) < 3:
        return
    prism(bm, ring, 0.0, eave)
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    br = math.radians(bearing_deg)
    ux, uy = math.sin(br), math.cos(br)          # along the ridge
    nx, ny = uy, -ux
    proj = [((p[0] - cx) * ux + (p[1] - cy) * uy,
             (p[0] - cx) * nx + (p[1] - cy) * ny) for p in ring]
    a0 = min(p[0] for p in proj); a1 = max(p[0] for p in proj)
    l0 = min(p[1] for p in proj); l1 = max(p[1] for p in proj)

    def w(a, l, z):
        return bm.verts.new((cx + ux * a + nx * l, cy + uy * a + ny * l, z))

    lm = (l0 + l1) * 0.5
    v = [w(a0, l0, eave), w(a1, l0, eave), w(a1, lm, ridge), w(a0, lm, ridge),
         w(a1, l1, eave), w(a0, l1, eave)]
    for f in ((v[0], v[1], v[2], v[3]), (v[3], v[2], v[4], v[5])):
        try:
            bm.faces.new(f)
        except ValueError:
            pass


def build_buildings(d, P, c_bldg, c_latam, c_term, c_tower):
    fach_names = {"Hangar A", "Hangar B", "Hangar C", "Hangar D",
                  "Hangar E", "Hangar F", "Hangar G"}
    latam_names = {"Base de Operaciones y Mantenimiento LATAM Airlines", "LATAM"}
    towers = {"Torre de Control SCL", "Torre de Control FACh"}
    term_names = {t["name"] for t in d["terminals"]}

    bm_generic = [bmesh.new() for _ in range(4)]
    bm_roof = bmesh.new()
    bm_fach = bmesh.new()
    bm_latam = bmesh.new()
    bm_sky = bmesh.new()
    bm_hangar = bmesh.new()
    bm_pier = bmesh.new()

    def emit(target, b, h, kind="prism"):
        ring = b["polygon_xy_m"]
        if kind == "gable":
            gable(target, ring, h * 0.82, h, b["footprint"]["long_axis_bearing_deg"])
        else:
            prism(target, ring, 0.0, h)

    for b in d["buildings"]:
        nm = b.get("name")
        if nm in towers:
            continue                                  # modelled explicitly
        if nm in term_names:
            continue                                  # handled with terminals
        h, _ = estimate_height(b)
        if nm == "LATAM" and b.get("building") != "hangar":
            emit(bm_generic[0], b, HEIGHT_BY_TYPE["yes"])
        elif nm in latam_names:
            emit(bm_latam, b, h, "gable" if nm == "LATAM" else "prism")
        elif nm == "Base de Mantenimiento Sky Airline":
            emit(bm_sky, b, h, "gable")
        elif nm in fach_names or (b.get("building") == "hangar"
                                  and b["centroid_xy_m"][1] > -400):
            emit(bm_fach, b, HANGAR_FACH, "gable")
        elif b.get("building") == "hangar":
            emit(bm_hangar, b, h, "gable")
        elif b.get("building") == "roof":
            emit(bm_roof, b, h)
        else:
            emit(bm_generic[hash(b["osm_id"]) % 4], b, h)

    # A single dark window band on buildings 10 m and taller. INFERENCE, not
    # survey: it stops the airport reading as a field of blank white boxes, and
    # every office/cargo block in the reference photographs has one.
    bm_win = bmesh.new()
    for b in d["buildings"]:
        nm = b.get("name")
        if nm in towers or nm in term_names:
            continue
        hh, _ = estimate_height(b)
        if hh < 10.0 or b.get("building") in ("hangar", "roof", "carport"):
            continue
        ring = dedupe_ring(b["polygon_xy_m"])
        for i in range(len(ring)):
            ax, ay = ring[i]
            bx, by = ring[(i + 1) % len(ring)]
            dx, dy, ln = unit(ax, ay, bx, by)
            if ln < 8.0:
                continue
            ox2, oy2 = -dy * 0.25, dx * 0.25
            for (z0, z1) in ((hh * 0.42, hh * 0.60), (hh * 0.68, hh * 0.86)):
                v = [bm_win.verts.new((ax + dx * 2 + ox2, ay + dy * 2 + oy2, z0)),
                     bm_win.verts.new((bx - dx * 2 + ox2, by - dy * 2 + oy2, z0)),
                     bm_win.verts.new((bx - dx * 2 + ox2, by - dy * 2 + oy2, z1)),
                     bm_win.verts.new((ax + dx * 2 + ox2, ay + dy * 2 + oy2, z1))]
                try:
                    bm_win.faces.new(v)
                except ValueError:
                    pass
    bm_to_object(bm_win, "SCL_Buildings_Windows", P["glass"], c_bldg)

    for h in d["hangars"]:
        nm = h.get("name")
        if nm in latam_names:
            continue
        hh = HANGAR_FACH if (nm in fach_names or h["centroid_xy_m"][1] > -400) \
            else HEIGHT_BY_TYPE["hangar"]
        target = bm_fach if (nm in fach_names or h["centroid_xy_m"][1] > -400) \
            else bm_hangar
        gable(target, h["polygon_xy_m"], hh * 0.82, hh,
              h["footprint"]["long_axis_bearing_deg"])

    for i, (bmg, key) in enumerate(zip(bm_generic,
                                       ("wall", "wall_grey", "wall_tan",
                                        "wall_pale"))):
        bm_to_object(bmg, "SCL_Buildings_Generic_%d" % i, P[key], c_bldg)
    bm_to_object(bm_roof, "SCL_Buildings_Canopies", P["roof_light"], c_bldg)
    bm_to_object(bm_fach, "SCL_Hangars_FACh", P["roof_navy"], c_bldg)
    bm_to_object(bm_hangar, "SCL_Hangars_Other", P["roof_light"], c_bldg)
    bm_to_object(bm_sky, "SCL_Hangar_SkyAirline", P["roof_maroon"], c_bldg)
    bm_to_object(bm_latam, "SCL_LATAM_Buildings", P["roof_light"], c_latam)

    # terminals: T2 gets its undulating roof, everything else a flat slab
    bm_t = bmesh.new()
    bm_roofline = bmesh.new()
    for t in d["terminals"]:
        nm = t["name"]
        h = HEIGHT_BY_NAME.get(nm, PIER_HEIGHT)
        prism(bm_t, t["polygon_xy_m"], 0.0, h)
        if nm == "Terminal 2 Internacional":
            undulating_roof(bm_roofline, t["polygon_xy_m"], h, h + 7.0)
        elif nm.startswith("Espig") and nm[8] in "CDEF":
            undulating_roof(bm_roofline, t["polygon_xy_m"], h, h + 3.5)
    bm_to_object(bm_t, "SCL_Terminal_Volumes", P["wall_grey"], c_term)
    ob = bm_to_object(bm_roofline, "SCL_Terminal_Roofs", P["t2_roof"], c_term,
                      smooth=True)
    ob.data.materials.append(P["t2_green"])
    build_terminal_facades(d, P, c_term)


def point_in_ring(px, py, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % n]
        if (ay > py) != (by > py):
            t = (py - ay) / (by - ay)
            if px < ax + t * (bx - ax):
                inside = not inside
    return inside


def undulating_roof(bm, ring, z_low, z_high):
    """The T2 signature: a corrugated shell, clipped to the real footprint.

    Grid cells whose centre falls outside the OSM polygon are dropped, so the
    roof follows the building rather than its bounding box - which for the
    367 x 309 m central processor is a very different shape."""
    ring = dedupe_ring(ring)
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    nx, ny = 40, 26
    amp = (z_high - z_low)
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            y = y0 + (y1 - y0) * j / ny
            u = i / nx * math.pi * 7.0
            z = z_low + amp * (0.5 + 0.5 * math.sin(u))
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            cx = x0 + (x1 - x0) * (i + 0.5) / nx
            cy = y0 + (y1 - y0) * (j + 0.5) / ny
            if not point_in_ring(cx, cy, ring):
                continue
            try:
                bm.faces.new((grid[j][i], grid[j][i + 1],
                              grid[j + 1][i + 1], grid[j + 1][i]))
            except ValueError:
                pass
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces],
                     context="VERTS")


def build_terminal_facades(d, P, c_term):
    """Mint-green panels and copper brise-soleil bands on the T2 volumes, and a
    glass band on T1. Read from t2_panorama_anfiteatro.jpg / apron_2022_sky_latam.jpg."""
    bm_green, bm_brise, bm_glass = bmesh.new(), bmesh.new(), bmesh.new()
    for t in d["terminals"]:
        nm = t["name"]
        h = HEIGHT_BY_NAME.get(nm, PIER_HEIGHT)
        ring = dedupe_ring(t["polygon_xy_m"])
        t2 = nm == "Terminal 2 Internacional" or (nm.startswith("Espig")
                                                  and nm[8] in "CDEF")
        n = len(ring)
        for i in range(n):
            ax, ay = ring[i]
            bx, by = ring[(i + 1) % n]
            dx, dy, ln = unit(ax, ay, bx, by)
            if ln < 4.0:
                continue
            ox, oy = -dy * 0.35, dx * 0.35          # push the band off the wall
            if t2:
                bands = ((0.35 * h, 0.60 * h, bm_green),
                         (0.62 * h, 0.80 * h, bm_brise),
                         (0.05 * h, 0.32 * h, bm_glass))
            else:
                bands = ((0.30 * h, 0.85 * h, bm_glass),)
            for (z0, z1, target) in bands:
                v = [target.verts.new((ax + ox, ay + oy, z0)),
                     target.verts.new((bx + ox, by + oy, z0)),
                     target.verts.new((bx + ox, by + oy, z1)),
                     target.verts.new((ax + ox, ay + oy, z1))]
                try:
                    target.faces.new(v)
                except ValueError:
                    pass
    bm_to_object(bm_green, "SCL_T2_GreenPanels", P["t2_green"], c_term)
    bm_to_object(bm_brise, "SCL_T2_Brise", P["t2_brise"], c_term)
    bm_to_object(bm_glass, "SCL_Terminal_Glazing", P["glass"], c_term)


def build_control_tower(P, c_tower):
    """DGAC tower at (-676.4, -1778.8). 60 m per the OSM height tag; DGAC's own
    history page says 65 m — divergence recorded in README.md. Shape from
    apron_panoramio_2011.jpg: tapering chamfered shaft, open gallery, flared
    glazed cab, roof slab with a horizontal-bar radar, external lattice frame."""
    cx, cy = -676.41, -1778.83
    H = HEIGHT_BY_NAME["Torre de Control SCL"]

    def oct_ring(bm, r, z, chamfer=0.30):
        pts = []
        for i in range(8):
            a = math.radians(22.5 + i * 45.0)
            k = 1.0 if i % 2 == 0 else chamfer + 0.7
            pts.append(bm.verts.new((cx + r * math.cos(a) * k,
                                     cy + r * math.sin(a) * k, z)))
        return pts

    bm = bmesh.new()
    levels = [(0.0, 8.6), (H * 0.52, 7.6), (H - 12.0, 6.9)]
    rings = [oct_ring(bm, r, z) for (z, r) in levels]
    for a, b in zip(rings, rings[1:]):
        for i in range(8):
            j = (i + 1) % 8
            try:
                bm.faces.new((a[i], a[j], b[j], b[i]))
            except ValueError:
                pass
    bm_to_object(bm, "SCL_Tower_Shaft", P["tower_concrete"], c_tower)

    # gallery + cab + roof slab
    bm = bmesh.new()
    for (z, r, t) in ((H - 12.0, 11.5, 0.9), (H - 3.2, 12.6, 1.0)):
        lo = oct_ring(bm, r, z, 0.9)
        hi = oct_ring(bm, r, z + t, 0.9)
        for i in range(8):
            j = (i + 1) % 8
            try:
                bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
            except ValueError:
                pass
        cap = oct_ring(bm, r, z + t, 0.9)
        try:
            f = bm.faces.new(cap)
            bmesh.ops.triangulate(bm, faces=[f])
        except ValueError:
            pass
    bm_to_object(bm, "SCL_Tower_Decks", P["tower_concrete"], c_tower)

    bm = bmesh.new()          # cab glazing, raked outward
    lo = oct_ring(bm, 9.4, H - 11.1, 0.9)
    hi = oct_ring(bm, 12.5, H - 3.2, 0.9)
    for i in range(8):
        j = (i + 1) % 8
        try:
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
        except ValueError:
            pass
    bm_to_object(bm, "SCL_Tower_Cab", P["glass"], c_tower)

    bm = bmesh.new()          # radar bar + whip antenna on the roof deck
    zt = H - 2.2
    for (a, b, w, hgt) in ((-5.5, 5.5, 0.5, 0.9),):
        v = [bm.verts.new((cx + a, cy - w, zt + 2.0)),
             bm.verts.new((cx + b, cy - w, zt + 2.0)),
             bm.verts.new((cx + b, cy + w, zt + 2.0)),
             bm.verts.new((cx + a, cy + w, zt + 2.0)),
             bm.verts.new((cx + a, cy - w, zt + 2.0 + hgt)),
             bm.verts.new((cx + b, cy - w, zt + 2.0 + hgt)),
             bm.verts.new((cx + b, cy + w, zt + 2.0 + hgt)),
             bm.verts.new((cx + a, cy + w, zt + 2.0 + hgt))]
        for f in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
                  (4, 5, 6, 7)):
            try:
                bm.faces.new([v[i] for i in f])
            except ValueError:
                pass
    for (px, py, r, h0, h1) in ((cx, cy, 0.25, zt, zt + 8.0),
                                (cx + 8.4, cy, 0.45, 4.0, H - 4.0),
                                (cx - 8.4, cy, 0.45, 4.0, H - 4.0)):
        prism(bm, [(px - r, py - r), (px + r, py - r),
                   (px + r, py + r), (px - r, py + r)], h0, h1)
    # external lattice frame leaning on one face
    for i in range(9):
        z0 = 4.0 + i * (H - 12.0) / 9.0
        z1 = z0 + (H - 12.0) / 9.0
        for (sx, sz0, sz1) in ((-1, z0, z1), (1, z0, z1)):
            prism(bm, [(cx + 8.0, cy + sx * 0.9 - 0.2),
                       (cx + 8.8, cy + sx * 0.9 - 0.2),
                       (cx + 8.8, cy + sx * 0.9 + 0.2),
                       (cx + 8.0, cy + sx * 0.9 + 0.2)], sz0, sz1)
    bm_to_object(bm, "SCL_Tower_Equipment", P["steel"], c_tower)

    # DGAC block directly beneath the tower (60 x 22 m footprint in OSM)
    bm = bmesh.new()
    prism(bm, [(-706.0, -1810.0), (-646.0, -1810.0),
               (-646.0, -1788.0), (-706.0, -1788.0)], 0.0, 11.0)
    bm_to_object(bm, "SCL_DGAC_Building", P["wall"], c_tower)


def build_latam_signage(P, c_latam):
    """The illuminated LATAM sign and the lit office band on the ops building.

    Geometry that IS data: the OSM footprint puts the ops building at
    x -721..-596, y -1397..-1233, and its west facade (x = -721, y -1397..-1320)
    is the one that faces RWY 17R - which is the face a departing crew sees.
    Geometry that is INFERRED: that the sign is on that face, and its size.
    The only photographic evidence is a small distant night crop
    (refs/_detalhe_letreiro_latam_noite.jpg) showing a white LATAM wordmark with
    the coral brandmark to its left, high on a facade above 2-3 lit office
    floors. Facade colour and cladding remain unconfirmed - scl_references.md 7.2.
    """
    x_face = -721.5                 # west facade, looking at the runway
    y0, y1 = -1397.0, -1320.0
    z_top = HEIGHT_BY_NAME["Base de Operaciones y Mantenimiento LATAM Airlines"]

    bm = bmesh.new()                # three lit office floors
    for i in range(3):
        z = 5.0 + i * 4.2
        v = [bm.verts.new((x_face - 0.4, y0 + 5, z)),
             bm.verts.new((x_face - 0.4, y1 - 5, z)),
             bm.verts.new((x_face - 0.4, y1 - 5, z + 2.6)),
             bm.verts.new((x_face - 0.4, y0 + 5, z + 2.6))]
        try:
            bm.faces.new(v)
        except ValueError:
            pass
    bm_to_object(bm, "SCL_LATAM_WindowBand",
                 mat("SCL_LATAM_LitWindows", (0.33, 0.31, 0.26), 0.3,
                     emit=(0.42, 0.33, 0.18)), c_latam)

    # A dark upper-facade band for the sign to read against. INFERENCE: the only
    # evidence is the night crop, where the white wordmark reads bright against a
    # dark surround. White-on-white would be invisible and is certainly wrong.
    bm = bmesh.new()
    v = [bm.verts.new((x_face - 0.5, y0 + 2.0, z_top - 8.6)),
         bm.verts.new((x_face - 0.5, y1 - 2.0, z_top - 8.6)),
         bm.verts.new((x_face - 0.5, y1 - 2.0, z_top - 0.8)),
         bm.verts.new((x_face - 0.5, y0 + 2.0, z_top - 0.8))]
    try:
        bm.faces.new(v)
    except ValueError:
        pass
    bm_to_object(bm, "SCL_LATAM_SignBand",
                 mat("SCL_LATAM_SignBand", (0.021, 0.020, 0.048), 0.45), c_latam)

    # wordmark, 5.5 m cap height, sitting just under the parapet
    letters = {
        "L": [(0.00, 0.00, 1.00, 5.50), (0.00, 0.00, 3.30, 1.00)],
        "A": [(0.00, 0.00, 1.00, 5.50), (2.66, 0.00, 3.66, 5.50),
              (0.00, 2.38, 3.66, 3.38)],
        "T": [(0.00, 4.50, 4.03, 5.50), (1.51, 0.00, 2.52, 5.50)],
        "M": [(0.00, 0.00, 1.00, 5.50), (3.58, 0.00, 4.58, 5.50),
              (1.00, 3.12, 2.19, 5.50), (2.39, 3.12, 3.58, 5.50)],
    }
    widths = {"L": 3.30, "A": 3.66, "T": 4.03, "M": 4.58}
    zs = z_top - 7.2
    total = sum(widths[c] for c in "LATAM") + 4 * 1.2
    y = (y0 + y1) * 0.5 + total * 0.5 - 4.0
    bm = bmesh.new()
    for ch in "LATAM":
        for (a, b, c_, dd) in letters[ch]:
            v = [bm.verts.new((x_face - 0.6, y - a, zs + b)),
                 bm.verts.new((x_face - 0.6, y - c_, zs + b)),
                 bm.verts.new((x_face - 0.6, y - c_, zs + dd)),
                 bm.verts.new((x_face - 0.6, y - a, zs + dd))]
            try:
                bm.faces.new(v)
            except ValueError:
                pass
        y -= widths[ch] + 1.2
    bm_to_object(bm, "SCL_LATAM_Wordmark", P["latam_white"], c_latam)

    bm = bmesh.new()                # coral brandmark, four raking strokes
    yb = (y0 + y1) * 0.5 + total * 0.5 + 2.5
    for i in range(4):
        ya = yb + i * 2.3
        v = [bm.verts.new((x_face - 0.6, ya, zs + 0.4 + i * 0.9)),
             bm.verts.new((x_face - 0.6, ya + 1.28, zs + 0.4 + i * 0.9)),
             bm.verts.new((x_face - 0.6, ya + 1.28, zs + 5.2 - i * 0.6)),
             bm.verts.new((x_face - 0.6, ya, zs + 5.2 - i * 0.6))]
        try:
            bm.faces.new(v)
        except ValueError:
            pass
    bm_to_object(bm, "SCL_LATAM_Brandmark", P["latam_coral"], c_latam)

    # hangar doors on the south face of the LATAM hangar (y = -1291), which is
    # the face onto Plataforma LATAM. Two bays: the satellite image shows a
    # central roof joint, so the hangar reads as two ~45 m bays.
    bm = bmesh.new()
    for (xa, xb2) in ((-670.0, -627.0), (-624.0, -583.0)):
        v = [bm.verts.new((xa, -1291.6, 0.6)),
             bm.verts.new((xb2, -1291.6, 0.6)),
             bm.verts.new((xb2, -1291.6, 18.8)),
             bm.verts.new((xa, -1291.6, 18.8))]
        try:
            bm.faces.new(v)
        except ValueError:
            pass
    bm_to_object(bm, "SCL_LATAM_HangarDoors", P["wall_grey"], c_latam)


def build_trees(d, P, c_furn):
    """The poplar/eucalyptus line along the airfield boundary. scl_operations.md
    section 7 records it in nearly every ground-level view, sitting between the
    pavement and the hills. Species and exact rows are not surveyed; this is a
    plausible hedge on the mapped aerodrome boundary and along the access roads."""
    import random
    rnd = random.Random(17)
    ring = dedupe_ring(d["aerodrome_boundary_xy_m"][0])
    bm_f, bm_t = bmesh.new(), bmesh.new()
    n = 0
    for i in range(len(ring)):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % len(ring)]
        ux, uy, ln = unit(ax, ay, bx, by)
        nx, ny = -uy, ux
        t = rnd.random() * 40.0
        while t < ln:
            if rnd.random() < 0.30:      # real hedgerows have gaps
                t += 22.0 + rnd.random() * 55.0
                continue
            off = 24.0 + rnd.random() * 16.0
            px = ax + ux * t + nx * off * (1 if (i % 2 == 0) else -1)
            py = ay + uy * t + ny * off * (1 if (i % 2 == 0) else -1)
            h = 8.5 + rnd.random() * 10.0
            r = h * (0.15 + rnd.random() * 0.12)
            # trunk
            prism(bm_t, [(px - 0.35, py - 0.35), (px + 0.35, py - 0.35),
                         (px + 0.35, py + 0.35), (px - 0.35, py + 0.35)],
                  0.0, h * 0.42)
            # crown: a tall lozenge, poplar-like
            zs = [h * 0.28, h * 0.55, h * 0.80, h]
            rs = [r * 0.55, r, r * 0.82, 0.001]
            prev = None
            for (z, rr) in zip(zs, rs):
                vs = [bm_f.verts.new((px + rr * math.cos(math.radians(a)),
                                      py + rr * math.sin(math.radians(a)), z))
                      for a in range(0, 360, 60)]
                if prev:
                    for k in range(6):
                        j = (k + 1) % 6
                        try:
                            bm_f.faces.new((prev[k], prev[j], vs[j], vs[k]))
                        except ValueError:
                            pass
                prev = vs
            n += 1
            t += 14.0 + rnd.random() * 13.0
    bm_to_object(bm_f, "SCL_TreeLine_Foliage", P["foliage"], c_furn, smooth=True)
    bm_to_object(bm_t, "SCL_TreeLine_Trunks", P["trunk"], c_furn)
    print("trees:", n)


def build_masts(d, P, c_furn):
    """Apron floodlight masts. Height is an ESTIMATE: 30 m is the usual range for
    apron high-mast lighting and matches the photographs, where the masts read as
    clearly taller than the terminal. No published figure was found."""
    H = 30.0
    bm = bmesh.new()
    placed = []
    for a in d["aprons"]:
        ring = dedupe_ring(a["polygon_xy_m"])
        if len(ring) < 3:
            continue
        n = len(ring)
        acc = 0.0
        for i in range(n):
            ax, ay = ring[i]
            bx, by = ring[(i + 1) % n]
            dx, dy, ln = unit(ax, ay, bx, by)
            t = 0.0
            while t < ln:
                px, py = ax + dx * t, ay + dy * t
                if all(math.dist((px, py), q) > 110.0 for q in placed):
                    placed.append((px, py))
                t += 40.0
            acc += ln
    for (px, py) in placed:
        r = 0.75
        prism(bm, [(px - r, py - r), (px + r, py - r),
                   (px + r, py + r), (px - r, py + r)], 0.0, H)
        r2 = 2.4
        prism(bm, [(px - r2, py - 1.2), (px + r2, py - 1.2),
                   (px + r2, py + 1.2), (px - r2, py + 1.2)], H, H + 2.6)
    bm_to_object(bm, "SCL_LightMasts", P["mast"], c_furn)
    print("light masts:", len(placed))


def build_windsocks(d, P, c_furn):
    bm = bmesh.new()
    for w in d["windsocks"]:
        px, py = w["xy_m"]
        prism(bm, [(px - 0.2, py - 0.2), (px + 0.2, py - 0.2),
                   (px + 0.2, py + 0.2), (px - 0.2, py + 0.2)], 0.0, 6.5)
    bm_to_object(bm, "SCL_Windsocks", P["mast"], c_furn)


def build_papi(P, c_furn):
    """PAPI boxes. AD 2.14: all four are on the LEFT of the runway, i.e. east
    when rolling on 17R."""
    bm = bmesh.new()
    for (thr, other) in ((THR_17R, THR_35L), (THR_35L, THR_17R),
                         (THR_17L, THR_35R), (THR_35R, THR_17L)):
        ux, uy, _ = unit(thr[0], thr[1], other[0], other[1])
        nx, ny = -uy, ux
        for i in range(4):
            lat = 60.0 + i * 9.0
            px = thr[0] + ux * 320.0 + nx * lat
            py = thr[1] + uy * 320.0 + ny * lat
            prism(bm, [(px - 1.2, py - 0.7), (px + 1.2, py - 0.7),
                       (px + 1.2, py + 0.7), (px - 1.2, py + 0.7)], 0.0, 1.1)
    bm_to_object(bm, "SCL_PAPI", P["mast"], c_furn)


# ---------------------------------------------------------------------------
# parked aircraft
# ---------------------------------------------------------------------------
def airliner_proxy(name, length, span, fin_h, fus_r, mats, collection):
    """Low-poly airliner. Nose along +X. Enough shape at 700-2000 m, which is
    where every one of these sits relative to the take-off camera."""
    bm = bmesh.new()
    ns = 14
    prof = [(-0.02, 0.10), (0.03, 0.55), (0.09, 0.86), (0.18, 1.00),
            (0.62, 1.00), (0.78, 0.92), (0.90, 0.66), (1.00, 0.22)]
    rings = []
    for (t, r) in prof:
        ring = []
        for i in range(ns):
            a = 2 * math.pi * i / ns
            ring.append(bm.verts.new((length * (0.5 - t),
                                      fus_r * r * math.sin(a),
                                      fus_r * r * math.cos(a) + fus_r * 1.05)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(ns):
            j = (i + 1) % ns
            try:
                bm.faces.new((a[i], a[j], b[j], b[i]))
            except ValueError:
                pass
    # wings
    hs = span * 0.5
    for s in (1, -1):
        v = [bm.verts.new((length * 0.06, s * fus_r * 0.8, fus_r * 0.45)),
             bm.verts.new((-length * 0.16, s * fus_r * 0.8, fus_r * 0.45)),
             bm.verts.new((-length * 0.20, s * hs, fus_r * 1.35)),
             bm.verts.new((-length * 0.09, s * hs, fus_r * 1.35))]
        try:
            bm.faces.new(v)
        except ValueError:
            pass
        # engine
        ex, ey = length * 0.02, s * hs * 0.36
        er = fus_r * 0.42
        ring0 = [bm.verts.new((ex + 1.8, ey + er * math.sin(2 * math.pi * i / 10),
                               fus_r * 0.15 + er * math.cos(2 * math.pi * i / 10)))
                 for i in range(10)]
        ring1 = [bm.verts.new((ex - 2.6, ey + er * math.sin(2 * math.pi * i / 10),
                               fus_r * 0.15 + er * math.cos(2 * math.pi * i / 10)))
                 for i in range(10)]
        for i in range(10):
            j = (i + 1) % 10
            try:
                bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
            except ValueError:
                pass
    # horizontal tail
    for s in (1, -1):
        v = [bm.verts.new((-length * 0.40, s * fus_r * 0.5, fus_r * 1.15)),
             bm.verts.new((-length * 0.50, s * fus_r * 0.5, fus_r * 1.15)),
             bm.verts.new((-length * 0.50, s * span * 0.17, fus_r * 1.45)),
             bm.verts.new((-length * 0.44, s * span * 0.17, fus_r * 1.45))]
        try:
            bm.faces.new(v)
        except ValueError:
            pass
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(mats[0])
    for p in me.polygons:
        p.use_smooth = True

    # fin as a second mesh so it can take the airline colour
    bmf = bmesh.new()
    v = [bmf.verts.new((-length * 0.34, 0.0, fus_r * 1.7)),
         bmf.verts.new((-length * 0.50, 0.0, fus_r * 1.7)),
         bmf.verts.new((-length * 0.50, 0.0, fus_r * 1.05 + fin_h)),
         bmf.verts.new((-length * 0.41, 0.0, fus_r * 1.05 + fin_h))]
    try:
        bmf.faces.new(v)
    except ValueError:
        pass
    mef = bpy.data.meshes.new(name + "_Fin")
    bmf.to_mesh(mef); bmf.free()
    mef.materials.append(mats[1])
    return me, mef


def build_parked_aircraft(d, P, c_park):
    """Fill the stands. RECOGNITION.md ranks this above every building: an
    employee recognises the ramp with their own tails on it, and an empty SCL
    reads as a construction site. Fleet mix and stand allocation are inferred
    from the AIP stand groups plus operator presence, not published per airline."""
    fleets = {
        "LATAM": (P["ac_white"], P["latam_indigo"]),
        "LATAM_wide": (P["ac_white"], P["latam_indigo"]),
        "Sky": (P["ac_white"], P["sky_purple"]),
        "JetSmart": (P["ac_white"], P["jetsmart"]),
        "Other": (P["ac_white"], P["ac_grey"]),
    }
    protos = {}
    for key, mats in fleets.items():
        wide = key.endswith("_wide")
        me, mef = airliner_proxy(
            "SCL_Proxy_" + key,
            63.0 if wide else 37.6, 60.1 if wide else 35.8,
            17.0 if wide else 11.8, 2.95 if wide else 1.98,
            mats, c_park)
        protos[key] = (me, mef)

    def place(key, x, y, heading_deg, tag):
        me, mef = protos[key]
        ob = bpy.data.objects.new("SCL_AC_%s" % tag, me)
        ob.location = (x, y, Z_APRON)
        ob.rotation_euler = (0.0, 0.0, math.radians(90.0 - heading_deg))
        c_park.objects.link(ob)
        fin = bpy.data.objects.new("SCL_ACFin_%s" % tag, mef)
        fin.parent = ob
        c_park.objects.link(fin)

    # ---- LATAM base. Stand coordinates are constrained by the mapped apron
    # polygons: Plataforma LATAM spans x -713..-408, y -1510..-1035 and
    # Plataforma Papa x -906..-740, y -1483..-1207. Aircraft are parked with the
    # fuselage north-south, which is what the satellite image shows and what puts
    # the fins broadside to a camera west of RWY 17R.
    n = 0
    for i, y in enumerate((-1462.0, -1396.0, -1330.0)):
        place("LATAM_wide", -487.0, y, 357.4, "MROW%d" % i)
        n += 1
    for i, y in enumerate((-1258.0, -1196.0, -1134.0, -1072.0)):
        place("LATAM", -483.0, y, 357.4, "MRON%d" % i)
        n += 1
    for i, y in enumerate((-1470.0, -1240.0)):
        place("LATAM", -828.0, y, 357.4, "PAPA%d" % i)
        n += 1
    for i, y in enumerate((-1470.0, -1440.0)):
        place("LATAM", -660.0, -1470.0 + i * 0.0, 357.4, "MROS%d" % i) \
            if False else None
    place("LATAM", -662.0, -1466.0, 357.4, "MROS0")
    n += 1

    # ---- terminal stands, taken from the mapped parking positions. The 108
    # way-type entries are the painted stand guidance lines, so they carry the
    # real nose-in direction; the 100 node-type entries carry only a point.
    order = ["LATAM", "LATAM", "LATAM", "Sky", "LATAM", "JetSmart",
             "LATAM", "Other", "LATAM", "Sky"]
    used = []
    stands = []
    for pp in d["parking_positions"]:
        if "polygon_xy_m" in pp and len(pp["polygon_xy_m"]) >= 2:
            a = pp["polygon_xy_m"][0]
            b = pp["polygon_xy_m"][-1]
            ux, uy, ln = unit(a[0], a[1], b[0], b[1])
            if ln < 25.0:
                continue
            stands.append((b[0], b[1], math.degrees(math.atan2(ux, uy)),
                           pp.get("ref")))
        elif "xy_m" in pp:
            x, y = pp["xy_m"]
            stands.append((x, y, 357.4 if y < -2700 else 177.4, pp.get("ref")))
    k = 0
    for (sx, sy, hdg, ref) in stands:
        if sy > -2080 or sy < -3450:
            continue
        L = 37.6
        cx2 = sx - math.sin(math.radians(hdg)) * L * 0.5
        cy2 = sy - math.cos(math.radians(hdg)) * L * 0.5
        if any(math.dist((cx2, cy2), q) < 46.0 for q in used):
            continue
        used.append((cx2, cy2))
        place(order[k % len(order)], cx2, cy2, hdg, "T%s" % (ref or k))
        k += 1
        n += 1

    # ---- Sky maintenance base and the cargo apron
    for i in range(3):
        place("Sky", -900.0 + i * 44.0, -1620.0, 177.4, "SKY%d" % i)
        n += 1
    for i in range(3):
        place("Other", -980.0 + i * 70.0, -3390.0, 87.4, "CGO%d" % i)
        n += 1
    print("parked aircraft:", n)


# ---------------------------------------------------------------------------
# lighting
# ---------------------------------------------------------------------------
def build_light(P, c_light):
    scn = bpy.context.scene
    world = bpy.data.worlds.new("SCL_World")
    scn.world = world
    world.use_nodes = True
    nt = world.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputWorld"); out.location = (400, 0)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.location = (200, 0)
    bg.inputs["Strength"].default_value = 0.16
    sky = nt.nodes.new("ShaderNodeTexSky"); sky.location = (-100, 0)
    configure_sky(sky)
    nt.links.new(sky.outputs[0], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])

    lamp = bpy.data.lights.new("SCL_Sun", "SUN")
    lamp.energy = 13.0
    lamp.angle = math.radians(0.545)
    lamp.color = (1.0, 0.845, 0.680)        # 15 deg elevation, thick air mass
    ob = bpy.data.objects.new("SCL_Sun", lamp)
    # A sun lamp shines along its local -Z. For euler (rx, 0, rz) that is
    # (-sin rx sin rz, sin rx cos rz, -cos rx); setting it to minus the unit
    # vector toward a sun at (elevation, compass azimuth) gives
    #   rx = 90 - elevation,  rz = 180 - azimuth.
    ob.rotation_euler = (math.radians(90.0 - SUN_ELEV_DEG), 0.0,
                         math.radians(180.0 - SUN_AZIM_DEG))
    c_light.objects.link(ob)


# ---------------------------------------------------------------------------
# terrain
# ---------------------------------------------------------------------------
def build_terrain(stride_mid=1, stride_far=3, stride_near=1):
    wipe()
    sys.path.insert(0, HERE)
    import load_terrain as lt
    c = coll("SCL_Terrain")
    layer = bpy.context.view_layer.active_layer_collection
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children[c.name]

    m = lt._meta()["grids"]
    g60, g30 = m["terrain_scl_60m"], m["terrain_scl_near_30m"]
    lt.build("terrain_scl_far_180m", stride=stride_far, obj_name="SCL_Terrain_Far",
             mask_inner=(g60["x_min_m"], g60["x_max_m"],
                         g60["y_min_m"], g60["y_max_m"]))
    lt.build("terrain_scl_60m", stride=stride_mid, obj_name="SCL_Terrain_Mid",
             mask_inner=(g30["x_min_m"], g30["x_max_m"],
                         g30["y_min_m"], g30["y_max_m"]))
    lt.build("terrain_scl_near_30m", stride=stride_near,
             obj_name="SCL_Terrain_Near")
    bpy.context.view_layer.active_layer_collection = layer

    flatten_aerodrome()
    m_t = terrain_material()
    for ob in c.objects:
        ob.data.materials.append(m_t)
    print("terrain polys:", sum(len(o.data.polygons) for o in c.objects))


def flatten_aerodrome():
    """The aerodrome is graded flat; a 30 m DEM there carries buildings and radar
    noise rather than ground. Blend the near tier to z = 0 over the field."""
    ob = bpy.data.objects.get("SCL_Terrain_Near")
    if ob is None:
        return
    d = data()
    ring = dedupe_ring(d["aerodrome_boundary_xy_m"][0])
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    inner, outer = 400.0, 2600.0
    target = -0.8          # keep the DEM clear of the built ground planes
    me = ob.data
    for v in me.vertices:
        dx = max(x0 - v.co.x, 0.0, v.co.x - x1)
        dy = max(y0 - v.co.y, 0.0, v.co.y - y1)
        dist = math.hypot(dx, dy)
        if dist >= outer:
            continue
        t = 0.0 if dist <= inner else (dist - inner) / (outer - inner)
        t = t * t * (3 - 2 * t)
        v.co.z = v.co.z * t + target * (1.0 - t)


def terrain_material():
    """Dry valley floor -> grey rock -> permanent snow above ~4300 m AMSL.
    Mid-February is summer: scl_references.md 3.5 records no snow on the near
    ranges then, but the 5000 m summits keep their glaciers."""
    m = bpy.data.materials.new("SCL_TerrainRock")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (700, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (300, 0)
    bsdf.inputs["Roughness"].default_value = 0.92
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-800, -200)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-620, -200)
    nt.links.new(geo.outputs["Position"], sep.inputs[0])

    r1 = nt.nodes.new("ShaderNodeMapRange"); r1.location = (-440, -100)
    r1.inputs[1].default_value = 0.0
    r1.inputs[2].default_value = 1600.0
    nt.links.new(sep.outputs["Z"], r1.inputs["Value"])
    mix1 = nt.nodes.new("ShaderNodeMixRGB"); mix1.location = (-220, 0)
    mix1.inputs["Color1"].default_value = (0.105, 0.082, 0.048, 1)   # valley
    mix1.inputs["Color2"].default_value = (0.088, 0.078, 0.070, 1)   # rock
    nt.links.new(r1.outputs["Result"], mix1.inputs["Factor"])

    r2 = nt.nodes.new("ShaderNodeMapRange"); r2.location = (-440, -320)
    r2.inputs[1].default_value = 3826.0     # 4300 m AMSL
    r2.inputs[2].default_value = 4300.0
    nt.links.new(sep.outputs["Z"], r2.inputs["Value"])
    mix2 = nt.nodes.new("ShaderNodeMixRGB"); mix2.location = (20, 0)
    mix2.inputs["Color2"].default_value = (0.70, 0.72, 0.78, 1)      # snow
    nt.links.new(mix1.outputs[0], mix2.inputs["Color1"])
    nt.links.new(r2.outputs["Result"], mix2.inputs["Factor"])
    nt.links.new(mix2.outputs[0], bsdf.inputs["Base Color"])

    grp = nt.nodes.new("ShaderNodeGroup"); grp.node_tree = haze_group()
    grp.location = (500, 0)
    nt.links.new(bsdf.outputs[0], grp.inputs[0])
    nt.links.new(grp.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------------------
ASSET_CATALOGS = {
    "b1f0a5c2-9d3e-4a71-8c55-5c1a7e2d0011": "SCL Scenery",
    "b1f0a5c2-9d3e-4a71-8c55-5c1a7e2d0012": "SCL Scenery/Collections",
    "b1f0a5c2-9d3e-4a71-8c55-5c1a7e2d0013": "SCL Scenery/Furniture",
    "b1f0a5c2-9d3e-4a71-8c55-5c1a7e2d0014": "SCL Scenery/Markings",
    "b1f0a5c2-9d3e-4a71-8c55-5c1a7e2d0015": "SCL Scenery/Aircraft",
    "b1f0a5c2-9d3e-4a71-8c55-5c1a7e2d0016": "SCL Scenery/Materials",
}


def write_catalogs():
    """Asset Browser catalogue definitions live next to the .blend files."""
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
        pass                                        # no preview in background mode


def mark_assets():
    """Expose the reusable pieces in the Asset Browser, the same convention the
    project already uses for the engines, the pax window and the plug door.
    The collections are marked too, so a new aircraft file can drag the whole
    airport in as a link instead of running a script."""
    write_catalogs()
    cats = list(ASSET_CATALOGS)
    for name, note in (
            ("SCL_Field", "Whole SCEL aerodrome: runways, taxiways, aprons, "
                          "buildings, LATAM base, tower, terminals, parked "
                          "aircraft. Link, do not append."),
            ("SCL_Light", "Sun + Nishita sky for mid-February 19:13 local."),
            ("SCL_Anchors", "SCL_17R_Threshold and friends: +Y points down the "
                            "take-off track."),
            ("SCL_LATAMBase", "LATAM MRO buildings, sign and hangar doors."),
            ("SCL_Tower", "DGAC control tower and the DGAC block beneath it."),
            ("SCL_Runways", "17R/35L and 17L/35R with ICAO Annex 14 markings.")):
        c = bpy.data.collections.get(name)
        if c:
            _mark(c, cats[1], note)
    for name, cat, note in (
            ("SCL_LightMasts", cats[2], "30 m apron floodlight masts (height "
                                        "estimated, see README)"),
            ("SCL_TreeLine_Foliage", cats[2], "perimeter poplar hedge"),
            ("SCL_Tower_Shaft", cats[2], "control tower shaft"),
            ("SCL_Tower_Cab", cats[2], "control tower cab glazing"),
            ("SCL_RunwayMarkings", cats[3], "ICAO Annex 14 runway markings, "
                                            "both runways"),
            ("SCL_AC_MROW0", cats[4], "low-poly widebody proxy, LATAM"),
            ("SCL_AC_MRON0", cats[4], "low-poly narrowbody proxy, LATAM")):
        ob = bpy.data.objects.get(name)
        if ob:
            _mark(ob, cat, note)
    for m in bpy.data.materials:
        if m.name.startswith("SCL_"):
            _mark(m, cats[5], "SCL scenery material (haze term included)")


def main():
    args = argv_after_dashdash()
    if "--terrain" in args:
        build_terrain()
        path = os.path.join(HERE, "scl_terrain.blend")
    else:
        build_field()
        mark_assets()
        path = os.path.join(HERE, "scl_field.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("saved", path, os.path.getsize(path) // 1024, "kB")


if __name__ == "__main__":
    main()
