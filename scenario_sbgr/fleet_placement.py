#!/usr/bin/env python3
"""The real aeroplanes on the Guarulhos ramp - one module, every clip.

    import fleet_placement as F
    F.populate(bpy.context.scene)                   # the whole ramp
    F.populate(bpy.context.scene, skip=("DEP",))    # nothing named DEP here
                                                    # yet; phase 3's departure
                                                    # aircraft will use it

This is the SBGR instance of the pattern ``../scenario_sdsc/fleet_placement.py``
established, kept as a SEPARATE module rather than a shared one - declared
decision: the two tables (stands, states, types) are entirely base-specific,
the machinery below is ~200 lines, and coupling SDSC's clip files to an SBGR
refactor would put a working base at risk for no render-time gain. The
load-bearing discovery carries over verbatim:

    LINK the masters' four sub-collections and put an
    ``instance_type='COLLECTION'`` empty at each stand. Every master mesh
    carries SUBSURF/MIRROR/BEVEL modifiers, and Cycles keys geometry on the
    OBJECT whenever the object is modified - so append+copy exports one
    geometry PER STAND, while collection-instance empties share ONE evaluated
    geometry per TYPE. Sixteen aircraft on this ramp cost eleven types of
    geometry, not sixteen. Linking the masters' TOP collections would
    disassemble them (parent empties live outside); the four sub-collections
    are all world-coordinate roots. Verified on all eleven masters at SDSC.

WHAT IS DIFFERENT AT GRU
========================
This is a HUB, not an MRO: every aircraft is intact and in service - parked at
a gate, on the remote row, at the cargo frontage, or by its hangar. No jacked
airframes, no open cowls, no docks; the states machinery from SDSC is
deliberately absent. The GSE around each stand is build_scenery's.

STAND ALLOCATION IS NOT PUBLISHED and every entry in FLEET is a declared
reading (sbgr_references.md section 6.4):
  * the 901-row widebodies re-read refs/ne_apron_tam_widebodies_dome_2013.jpg
    forward thirteen years - one old photograph, not data;
  * LATAM narrowbodies on the T2/T3 frontage and widebodies at T3 follow the
    airline's published terminal split, not any stand chart;
  * the LATAM Cargo 767s stand on the TECA III frontage;
  * the 777-300ER at the hangar stand is the point of the base: GRU is where
    LATAM's 777 fleet is maintained (CNN Brasil, recorded in the SDSC survey),
    and the 777 is the one type with no scenery presence before this file.

TYPES: all eleven masters in the repository appear - GRU is the only base
where that is honest, because GRU is the hub that operates all of them. The
777-300ER, banned from the SDSC table with evidence, is the PROTAGONIST here
with evidence. Non-LATAM traffic is neutral white proxies at distant gates
(build_scenery.PROXY_STANDS) - we have no non-LATAM models and say so.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: the four sub-collections every master in this repository is built with
PARTS = ("01_Estrutura", "02_Motores", "03_Trem", "04_Detalhes")

#: type key -> master file, relative to the repository root
TYPES = {
    "A319":    os.path.join("airbus A319", "A319_LATAM.blend"),
    "A320ceo": os.path.join("airbus A320ceo", "A320ceo_LATAM.blend"),
    "A320neo": os.path.join("airbus A320neo", "A320neo_LATAM.blend"),
    "A321ceo": os.path.join("airbus A321ceo", "A321ceo_LATAM.blend"),
    "A321neo": os.path.join("airbus A321neo", "A321neo_LATAM.blend"),
    "B763":    os.path.join("boeing 767-300ER", "B763_LATAM.blend"),
    "B763F":   os.path.join("boeing 767-300F", "B763F_LATAM_CARGO.blend"),
    "B763BCF": os.path.join("boeing 767-300BCF", "B763BCF_LATAM_CARGO.blend"),
    "B77W":    os.path.join("boeing 777-300ER", "B77W_LATAM.blend"),
    "B788":    os.path.join("boeing 787-8", "B788_LATAM.blend"),
    "B789":    os.path.join("boeing 787-9", "B789_LATAM.blend"),
}

#: stand tag -> type key, or None to leave the stand to build_scenery's proxy.
#: Positions/headings/zone-z stay in build_scenery.SBGR_STANDS.
FLEET = {
    # T2/T3 frontage - the domestic narrowbody wave
    "G303": "A320neo",
    "G304": "A321neo",
    "G310": "A319",
    "G402": "A321ceo",
    "G403": "A320ceo",
    "G410": "A320neo",      # shares G303's linked geometry
    "G409": "A319",         # shares G310's
    # T3 widebodies - the international wave
    "G502": "B788",
    "G510": "B789",
    # TECA III cargo frontage
    "C104": "B763BCF",
    "C106": "B763F",
    # the 901-912 remote row (the 2013-photograph reading)
    "R901": "B77W",
    "R904": "B789",
    "R907": "B788",
    "R910": "B763",
    # the hangar stand - the 777 at its own base
    "HGR":  "B77W",
}


def master_path(type_key):
    return os.path.join(ROOT, TYPES[type_key])


def type_of(tag):
    return FLEET.get(tag)


def is_real(tag):
    return FLEET.get(tag) is not None


def missing():
    return [k for k, p in TYPES.items()
            if not os.path.exists(os.path.join(ROOT, p))]


# ---------------------------------------------------------------------------
# Blender side. Nothing above this line imports bpy.
# ---------------------------------------------------------------------------
_LINKED = {}          # (realpath, collection name) -> linked collection


def _heading_rot(deg):
    """rotation_euler.z that puts the master's nose on a compass heading.
    Every master's nose is along local -X (the fleet convention)."""
    h = math.radians(deg)
    return math.atan2(-math.cos(h), -math.sin(h))


def _link_part(path, name):
    import bpy
    key = (os.path.realpath(path), name)
    c = _LINKED.get(key)
    if c is not None:
        return c
    with bpy.data.libraries.load(path, link=True) as (src, dst):
        if name not in src.collections:
            raise RuntimeError("%s has no collection %s" % (path, name))
        dst.collections = [name]
    c = dst.collections[0]
    _LINKED[key] = c
    return c


def _world_bbox(owned):
    """Evaluated world envelope of everything hanging off `owned`."""
    import bpy
    import mathutils
    dg = bpy.context.evaluated_depsgraph_get()
    lo = mathutils.Vector((1e9, 1e9, 1e9))
    hi = mathutils.Vector((-1e9, -1e9, -1e9))
    n = 0
    for inst in dg.object_instances:
        src = inst.parent.original if inst.is_instance else inst.object.original
        if src not in owned:
            continue
        ob = inst.object
        if ob.type != "MESH" or ob.original.hide_render:
            continue
        mw = inst.matrix_world
        for c in ob.bound_box:
            w = mw @ mathutils.Vector(c[:])
            lo = mathutils.Vector(map(min, lo, w))
            hi = mathutils.Vector(map(max, hi, w))
        n += 1
    return lo, hi, n


def _place_one(scn, coll, tag, type_key, x, y, hdg, apron_z):
    """Link, instance, aim and seat one aeroplane - self-verifying: the
    evaluated envelope is measured through the depsgraph, the centre moved to
    the stand and the tyres to the apron, then measured again and reported."""
    import bpy
    path = master_path(type_key)
    if not os.path.exists(path):
        print("!! master missing: %s" % path)
        return None

    root = bpy.data.objects.new("SBGR_Fleet_%s" % tag, None)
    root.empty_display_type = "ARROWS"
    root.empty_display_size = 6.0
    coll.objects.link(root)
    root.rotation_euler = (0.0, 0.0, _heading_rot(hdg))

    owned = set()
    for name in PARTS:
        c = _link_part(path, name)
        e = bpy.data.objects.new("SBGR_Fleet_%s_%s" % (tag, name), None)
        e.instance_type = "COLLECTION"
        e.instance_collection = c
        e.empty_display_size = 0.5
        coll.objects.link(e)
        e.parent = root
        owned.add(e)

    bpy.context.view_layer.update()
    lo, hi, n = _world_bbox(owned)
    if n == 0:
        print("!! %s: nothing evaluated" % tag)
        return None
    root.location.x += x - 0.5 * (lo.x + hi.x)
    root.location.y += y - 0.5 * (lo.y + hi.y)
    root.location.z += apron_z - lo.z
    bpy.context.view_layer.update()

    lo, hi, n = _world_bbox(owned)
    return dict(tag=tag, type=type_key, meshes=n,
                x0=lo.x, x1=hi.x, y0=lo.y, y1=hi.y, z0=lo.z, z1=hi.z,
                span=hi.x - lo.x, depth=hi.y - lo.y, height=hi.z - lo.z,
                apron=apron_z)


def _on_concrete(rows):
    """Ray-cast under each aeroplane's centre and extrema and read what was
    actually BUILT there - the check that caught SDSC's jacked freighter on
    the dirt. A wingtip over the apron edge reports; a CENTRE off it shouts."""
    import bpy
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    scn = bpy.context.scene

    GROUND = ("Concrete", "Apron", "Ground", "Terrain", "Taxi", "Runway",
              "City", "Infield", "Pavement", "Edges")

    def under(px, py, top):
        z = top + 60.0
        for _ in range(12):
            hit, loc, _, _, ob, _ = scn.ray_cast(
                dg, Vector((px, py, z)), Vector((0.0, 0.0, -1.0)))
            if not hit:
                return "NOTHING"
            if any(k in ob.name for k in GROUND):
                return ob.name
            z = loc.z - 0.01
        return ob.name

    bad = 0
    for r in rows:
        cx, cy = 0.5 * (r["x0"] + r["x1"]), 0.5 * (r["y0"] + r["y1"])
        top = r["z1"]
        centre = under(cx, cy, top)
        tips = [under(px, py, top) for (px, py) in
                ((cx, r["y0"]), (cx, r["y1"]),
                 (r["x0"], cy), (r["x1"], cy))]
        n_ok = sum(1 for c in tips if "Concrete" in c or "Apron" in c
                   or "Edges" in c)
        if "Concrete" not in centre and "Apron" not in centre \
                and "Edges" not in centre:
            bad += 1
            print("!! %s CENTRE is standing on %s, not concrete"
                  % (r["tag"], centre))
        elif n_ok < 4:
            print("  %-5s nose/tail/wingtips: %d of 4 over concrete (%s)"
                  % (r["tag"], n_ok,
                     ", ".join(sorted({c for c in tips
                                       if "Concrete" not in c
                                       and "Apron" not in c
                                       and "Edges" not in c}))))
    print("fleet: %d aircraft not standing on concrete" % bad)


def populate(scn=None, skip=(), collection="SBGR_Fleet", quiet=False):
    """Put the real masters on every stand this module owns."""
    import bpy
    sys.path.insert(0, HERE)
    import build_scenery as B                                  # needs bpy

    scn = scn or bpy.context.scene
    coll = bpy.data.collections.get(collection)
    if coll is None:
        coll = bpy.data.collections.new(collection)
        scn.collection.children.link(coll)

    out = []
    for (tag, key, x, y, hdg, zz) in B.SBGR_STANDS:
        if tag in skip:
            continue
        type_key = FLEET.get(tag)
        if type_key is None:
            continue
        r = _place_one(scn, coll, tag, type_key, x, y, hdg, zz + B.Z_APRON)
        if r is not None:
            out.append(r)
    if not quiet:
        report(out)
    return out


def report(rows):
    if not rows:
        print("fleet: nothing placed")
        return
    print("\n%-5s %-8s %6s %7s %7s %8s %8s"
          % ("stand", "type", "meshes", "x_m", "y_m", "wheels_z", "fin_z"))
    for r in rows:
        print("%-5s %-8s %6d %7.1f %7.1f %8.2f %8.2f   %.1f x %.1f x %.1f m"
              % (r["tag"], r["type"], r["meshes"],
                 0.5 * (r["x0"] + r["x1"]), 0.5 * (r["y0"] + r["y1"]),
                 r["z0"], r["z1"], r["span"], r["depth"], r["height"]))
    worst = max(abs(r["z0"] - r["apron"]) for r in rows)
    print("fleet: %d aircraft, %d types, wheels seated to %.3f m"
          % (len(rows), len({r["type"] for r in rows}), worst))
    bad = 0
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            ox = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
            oy = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
            if ox > 0 and oy > 0:
                bad += 1
                print("!! %s and %s overlap by %.1f x %.1f m"
                      % (a["tag"], b["tag"], ox, oy))
    print("fleet: %d envelope overlaps" % bad)
    try:
        _on_concrete(rows)
    except Exception as exc:
        print("fleet: concrete check skipped (%s)" % exc)


if __name__ == "__main__":
    print(__doc__)
    print("masters on disk:")
    for k in sorted(TYPES):
        p = os.path.join(ROOT, TYPES[k])
        print("  %-8s %-50s %s" % (k, TYPES[k],
                                   "ok" if os.path.exists(p) else "MISSING"))
    print("stands: %s" % ", ".join("%s=%s" % (k, v or "proxy")
                                   for k, v in FLEET.items()))
