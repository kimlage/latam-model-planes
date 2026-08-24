#!/usr/bin/env python3
"""The real aeroplanes on the São Carlos ramp — one module, three clips.

    import fleet_placement as F
    F.populate(bpy.context.scene)                  # the whole ramp
    F.populate(bpy.context.scene, skip=("H9",))    # ... minus the towed one

WHY THIS EXISTS
===============
Phase 4 parked fifteen low-poly `airliner_proxy()` aeroplanes on this field and
`base_flyover.py` then hand-swapped **three** of them for the real masters this
repository has built. The owner spotted the seam in the hangar-tow clip: the
towed 787-9 is the real model and there is an undetailed aeroplane standing
behind it. This module is the general form of those three entries — every stand
on the ramp, in every clip, from one table.

THE THREE THINGS IT HAD TO SOLVE, IN ORDER OF DIFFICULTY
========================================================

1. INSTANCE, DO NOT DUPLICATE
-----------------------------
A master at render subsurf is 307 000–356 000 triangles (measured, all eleven).
Fifteen unique copies is ~5 M triangles and the tow clip is 400 frames.

Santiago's `../scenario/base_flyover.py` APPENDS each master — a full copy of
every mesh datablock into the shot file — and duplicates hierarchies with
`ob.copy()` for its two extra A320s. That shares mesh *data*, but it does not
give Cycles an instance: every master mesh here carries SUBSURF / MIRROR /
BEVEL modifiers, and Cycles keys geometry on the OBJECT whenever the object is
modified, so two objects sharing one modified mesh still export as two
geometries. Appending also copies the meshes into the .blend, and the three
clip .blends are committed files.

So this module **links** the four sub-collections and puts a
`instance_type='COLLECTION'` empty at each stand. That is a real instance on
both counts: the .blend gains a library reference and an empty instead of
~40 MB of mesh, and the depsgraph hands Cycles the SAME evaluated object with N
matrices, so the geometry is synced once no matter how many stands use it.
Unique geometry is therefore (number of distinct TYPES), not (number of
aircraft) — eight types on ten stands here.

Linking the master's TOP collection is what does not work, and Santiago's
docstring says why: the parts hang from parent empties that live outside the
sub-collections, so an instance disassembles. Linking the four sub-collections
is fine — verified on all eleven masters, every object in them is a
world-coordinate root with no parent.

2. THIS IS A HEAVY-CHECK BASE, NOT A TERMINAL
---------------------------------------------
`build_scenery.MRO_STANDS` deliberately shows aircraft APART — that is what
distinguishes an MRO from a gate row, and the proxies were built with the
states. The masters have no states. What each one can honestly become:

    parked      all four collections. Nothing to do.
    docked      all four collections. `docked` was never an airframe state:
                the nose dock, tail dock, wing docks and towers that make it
                read are `build_maintenance`'s kit and they are already
                standing round the stand. Survives unchanged.
    jacked      all four collections, lifted `JACK_LIFT` (0.55 m) so the wheels
                hang clear of the concrete over the jacks that are already
                there. The gear stays DOWN — weight off wheels, which is what
                a jacking for a weighing or a strut change looks like. (A gear
                swing, gear retracted on jacks, would be the other reading and
                is not what the kit under it shows.)
    engine_off  02_Motores is a SEPARATE collection, and that is the opening.
                This stand does not instance it; it appends a local copy,
                bakes it, and deletes every face on the PORT side except the
                pylon's. Result: one engine, one bare pylon — exactly the
                proxy's semantics — and `build_maintenance` already has the
                missing engine on its cradle and the dolly beside the wing.
                Costs one aircraft's worth of unique engine geometry, once.
    cowls       THE ONE STATE THE MASTERS CANNOT HOLD BY THEMSELVES. There is
                no fan-cowl door in the geometry to hinge: `Motor_Nacelle`
                (Airbus) and `Nacelle_E`/`Nacelle_D` (Boeing) are single
                lofted, subsurfed skins. Hiding the skin gives "engine
                stripped to the core", a real state but a different one, and
                from 300 m it reads as a *thinner* engine rather than an
                opened one.

                So the doors are AUTHORED HERE and it has to be said plainly:
                two panels per engine, hinged on the nacelle crown at 55°,
                are new geometry this module builds — they are not part of any
                master. What is not invented is their size and position: the
                nacelle's crown line, centre, radius and length are MEASURED
                off the evaluated master (`_cowl_mesh`), so the doors sit on
                the real nacelle and scale with the type. It is the same
                construction `airliner_proxy(engines="open")` uses, moved onto
                a real aeroplane, and the state it reproduces is photographed
                on this site — refs/mro_centro_tecnologico_2010.jpg, an A320
                with the fan cowls open and the core exposed.

    No state is silently dropped. If a stand's state cannot be expressed the
    entry's type is set to None and `build_scenery` keeps its proxy — the
    escape hatch is real and `proxy_stands()` reports it. Nothing uses it at
    present.

3. THE PLACEMENT VERIFIES ITSELF
--------------------------------
Same rule as Santiago's, generalised: nothing here trusts a convention about
where a master's origin is or how big it is. Each aircraft is rotated
nose-to-heading, then its EVALUATED envelope is measured through the depsgraph
(instances included) and the root is moved so the CENTRE lands on the stand and
the LOWEST point — the tyres — lands on the apron. Then it is measured again
and printed. On top of that `populate` runs a pairwise 2-D overlap check across
every aircraft it placed and shouts about any wingtip inside another aeroplane,
which the proxy table could not do because the proxies were nominal boxes and
the real spans are not.

TYPES, AND WHY EACH ONE
=======================
`sdsc_aip_survey.json` is the evidence and `README.md` §7 is the table:

    A319 / A320 / A321, ceo and neo   routine — the base's core workload;
                                      hangar 9 alone takes three at once
    767-300ER / 767-300F              routine — listed by LATAM among the types
                                      maintained here, and a TAM widebody is on
                                      the mid-field apron in the 2013 photo
    787-8 / 787-9                     hangar 9 exists for 787 heavy maintenance
    A330-200                          historic, largest type before 2020
    777-300ER                         **NO** — CNN Brasil puts 777 maintenance
                                      at Guarulhos. The one type with evidence
                                      AGAINST. It is not in this table and must
                                      not be added to it.

Two gaps are declared rather than papered over:
  * **no A330 model exists**, so the historic A330 is not represented; the
    "wide" stands are 767s, which is the type with current evidence.
  * **no light-aircraft model exists**, so the five Aeroclube GA aeroplanes
    stay `ga_proxy()` — 180–280 m off a RWY 02 roll, and the only proxies
    left on this field.
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
    "B788":    os.path.join("boeing 787-8", "B788_LATAM.blend"),
    "B789":    os.path.join("boeing 787-9", "B789_LATAM.blend"),
    # B763BCF and B77W exist as masters and are deliberately NOT used on this
    # ramp: the BCF adds nothing the -300F does not already say, and the 777
    # has positive evidence against it operating at SDSC at all.
}

#: stand tag -> type key, or None to leave the stand a proxy.
#: The stand's POSITION, HEADING and STATE stay in `build_scenery.MRO_STANDS`
#: and `build_scenery.OUTFIELD_STANDS`, which is also what the maintenance kit
#: and the GSE are laid out from. This table only says which aeroplane.
FLEET = {
    # the hangar frontage — the row a RWY 02 departure sees, tails to the runway
    "ROW0": "B763",       # 767-300ER, the widebody LATAM lists for this base
    "ROW1": "A320neo",    # the everyday type, and the one the departure flies
    "H9":   "B789",       # hangar 9's own stand: the type the building is for
    # the northern lobes — the heavy-check line, all nose 181°
    "N0":   "B763F",      # jacked. LATAM Cargo 767-300F: the freighter is an
                          #   evidenced variant and it puts the cargo livery on
                          #   a ramp that would otherwise be all passenger white
    "N1":   "A321neo",    # docked, nose and tail docks round it
    "N2":   "A320ceo",    # engine_off — the port engine is on its cradle
    "N3":   "A320neo",    # cowls open (shares ROW1's linked geometry)
    "N4":   "A319",       # cowls open — the smallest of the family
    "N5":   "A321ceo",    # docked
    # off the MRO platform
    "MID":  "B763",       # the mid-field apron, 26 m below the runway crest:
                          #   the 2013 reference photograph has a TAM widebody
                          #   parked exactly here (shares ROW0's geometry)
}


def master_path(type_key):
    return os.path.join(ROOT, TYPES[type_key])


def type_of(tag):
    """The master type for a stand tag, or None if the stand stays a proxy."""
    return FLEET.get(tag)


def is_real(tag):
    """True when this module owns the stand, so `build_scenery` must not build
    a proxy on it."""
    return FLEET.get(tag) is not None


def proxy_stands(stands):
    """The subset of `stands` this module does NOT cover — the honest escape
    hatch. Empty at present; if a stand ever has to go back to a proxy because
    of render cost or because its state cannot be expressed, its FLEET entry
    becomes None and it turns up here."""
    return [s[0] for s in stands if not is_real(s[0])]


def missing():
    """Master files this table names that are not on disk."""
    return [k for k, p in TYPES.items()
            if not os.path.exists(os.path.join(ROOT, p))]


# ---------------------------------------------------------------------------
# Blender side. Nothing above this line imports bpy, so `build_scenery` can
# read the tables and the clip scripts can be tuned offline.
# ---------------------------------------------------------------------------
_LINKED = {}          # (realpath, collection name) -> linked collection
_COWLS = {}           # type key -> cowl-door mesh, in master-local coordinates


def _heading_rot(deg):
    """rotation_euler.z that puts the master's nose on a compass heading.

    Every master in this repository has its nose along local -X. Rz(t) maps
    (-1, 0) to (-cos t, -sin t); a heading h wants (sin h, cos h)."""
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


def _append_part(path, name):
    import bpy
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c == name]
    return dst.collections[0]


def _world_bbox(owned, want=None):
    """Evaluated world envelope of everything hanging off `owned`.

    `owned` holds the instancer empties AND any local objects, so one walk of
    the depsgraph covers both the linked instances and the appended engines.
    `want` filters on the ORIGINAL object name, for the nacelle measurement."""
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
        if want is not None and want not in ob.original.name:
            continue
        mw = inst.matrix_world
        for c in ob.bound_box:
            w = mw @ mathutils.Vector(c[:])
            lo = mathutils.Vector(map(min, lo, w))
            hi = mathutils.Vector(map(max, hi, w))
        n += 1
    return lo, hi, n


def _strip_port_side(coll):
    """Bake `coll`'s meshes at RENDER subdivision and delete every face on the
    port side, except the pylons'. Port is local -Y: the nose is local -X and
    up is +Z, so left = up x forward = (0, -1, 0)."""
    import bpy
    import bmesh
    scn = bpy.context.scene
    scn.collection.children.link(coll)
    for ob in coll.all_objects:
        for m in ob.modifiers:
            if m.type == "SUBSURF":
                m.levels = m.render_levels
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    kept = 0
    for ob in list(coll.all_objects):
        if ob.type != "MESH":
            continue
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        ob.data = me
        if "Pylon" in ob.name:
            kept += 1
            continue
        bm = bmesh.new()
        bm.from_mesh(me)
        gone = [f for f in bm.faces if f.calc_center_median().y < 0.0]
        bmesh.ops.delete(bm, geom=gone, context="FACES")
        bm.to_mesh(me)
        bm.free()
    scn.collection.children.unlink(coll)
    return kept


def _cowl_mesh(type_key, owned):
    """Two open fan-cowl doors per engine, MEASURED off this type's nacelle.

    Returns a mesh in the master's own local frame, so both cowls stands of a
    type share one datablock. See the module docstring: this geometry is
    authored here, it is not part of any master, and it is the one thing on
    this ramp that is."""
    import bpy
    import bmesh
    import mathutils
    me = _COWLS.get(type_key)
    if me is not None:
        return me
    dg = bpy.context.evaluated_depsgraph_get()
    root = None
    verts = []
    mat = None
    for inst in dg.object_instances:
        src = inst.parent.original if inst.is_instance else inst.object.original
        if src not in owned:
            continue
        ob = inst.object
        if ob.type != "MESH" or "Nacelle" not in ob.original.name:
            continue
        if root is None:
            root = src.parent          # the stand's root empty
        if mat is None and ob.original.data.materials:
            mat = ob.original.data.materials[0]
        inv = root.matrix_world.inverted()
        m = inv @ inst.matrix_world
        ev = ob.to_mesh()
        verts.extend(m @ v.co for v in ev.vertices)
        ob.to_mesh_clear()
    if not verts:
        print("!! no nacelle found for %s - no cowl doors" % type_key)
        return None
    bm = bmesh.new()
    for s in (1.0, -1.0):
        side = [v for v in verts if v.y * s > 0.0]
        if not side:
            continue
        x0 = min(v.x for v in side)
        x1 = max(v.x for v in side)
        y0 = min(v.y for v in side)
        y1 = max(v.y for v in side)
        z1 = max(v.z for v in side)
        ey = 0.5 * (y0 + y1)
        er = 0.5 * (y1 - y0)
        # the fan cowl is the FORWARD part of the nacelle, and forward is -X
        L = x1 - x0
        xa, xb = x0 + 0.06 * L, x0 + 0.58 * L
        ang = math.radians(55.0)       # the angle that reads as "open" at 300 m
        w = er * 1.35
        for c in (1.0, -1.0):
            p = [(xa, ey, z1), (xb, ey, z1),
                 (xb, ey + c * w * math.sin(ang), z1 + w * math.cos(ang)),
                 (xa, ey + c * w * math.sin(ang), z1 + w * math.cos(ang))]
            vs = [bm.verts.new(mathutils.Vector(q)) for q in p]
            try:
                bm.faces.new(vs)
            except ValueError:
                pass
    me = bpy.data.meshes.new("SDSC_Cowls_%s" % type_key)
    bm.to_mesh(me)
    bm.free()
    if mat is not None:
        me.materials.append(mat)
    _COWLS[type_key] = me
    return me


def _place_one(scn, coll, tag, type_key, x, y, hdg, state, apron_z, lift):
    """Link, instance, aim and seat one aeroplane. Returns a report dict."""
    import bpy
    path = master_path(type_key)
    if not os.path.exists(path):
        print("!! master missing: %s" % path)
        return None

    root = bpy.data.objects.new("SDSC_Fleet_%s" % tag, None)
    root.empty_display_type = "ARROWS"
    root.empty_display_size = 6.0
    coll.objects.link(root)
    root.rotation_euler = (0.0, 0.0, _heading_rot(hdg))

    owned = set()
    parts = [p for p in PARTS if not (p == "02_Motores"
                                      and state == "engine_off")]
    for name in parts:
        c = _link_part(path, name)
        e = bpy.data.objects.new("SDSC_Fleet_%s_%s" % (tag, name), None)
        e.instance_type = "COLLECTION"
        e.instance_collection = c
        e.empty_display_size = 0.5
        coll.objects.link(e)
        e.parent = root
        owned.add(e)
    local = []
    if state == "engine_off":
        # a local, baked, half-deleted 02_Motores: one engine and a bare pylon
        eng = _append_part(path, "02_Motores")
        _strip_port_side(eng)
        for ob in list(eng.all_objects):
            eng.objects.unlink(ob)
            coll.objects.link(ob)
            ob.name = "SDSC_Fleet_%s_%s" % (tag, ob.name)
            ob.parent = root
            ob.matrix_parent_inverse.identity()
            owned.add(ob)
            local.append(ob)
        bpy.data.collections.remove(eng)

    bpy.context.view_layer.update()
    lo, hi, n = _world_bbox(owned)
    if n == 0:
        print("!! %s: nothing evaluated" % tag)
        return None
    root.location.x += x - 0.5 * (lo.x + hi.x)
    root.location.y += y - 0.5 * (lo.y + hi.y)
    root.location.z += apron_z - lo.z + lift
    bpy.context.view_layer.update()

    if state == "cowls":
        me = _cowl_mesh(type_key, owned)
        if me is not None:
            ob = bpy.data.objects.new("SDSC_Fleet_%s_Cowls" % tag, me)
            coll.objects.link(ob)
            ob.parent = root
            ob.matrix_parent_inverse.identity()
            owned.add(ob)
            bpy.context.view_layer.update()

    lo, hi, n = _world_bbox(owned)
    return dict(tag=tag, type=type_key, state=state, meshes=n,
                x0=lo.x, x1=hi.x, y0=lo.y, y1=hi.y, z0=lo.z, z1=hi.z,
                span=hi.x - lo.x, depth=hi.y - lo.y, height=hi.z - lo.z,
                apron=apron_z, lift=lift, local=len(local))


def populate(scn=None, skip=(), collection="SDSC_Fleet", quiet=False):
    """Put the real masters on every stand this module owns.

    `skip` is a tuple of stand tags to leave empty — `hangar_tow.py` passes
    ("H9",) because its own 787-9 is being towed onto that stand."""
    import bpy
    sys.path.insert(0, HERE)
    import build_scenery as B                                  # needs bpy

    scn = scn or bpy.context.scene
    coll = bpy.data.collections.get(collection)
    if coll is None:
        coll = bpy.data.collections.new(collection)
        scn.collection.children.link(coll)

    stands = [(t, k, x, y, h, s, B.Z_MRO_PLATFORM + B.Z_APRON)
              for (t, k, x, y, h, s) in B.MRO_STANDS]
    stands += [(t, k, x, y, h, s, z + B.Z_APRON)
               for (t, k, x, y, h, s, z) in B.OUTFIELD_STANDS]

    out = []
    for (tag, key, x, y, hdg, state, apron_z) in stands:
        if tag in skip:
            continue
        type_key = FLEET.get(tag)
        if type_key is None:
            continue
        # The proxy this replaces, if an older field file still carries one.
        # LINKED proxies are left alone on purpose: the departure clip links
        # SDSC_Field as a collection instance and an object inside a library
        # cannot be removed from the file that instances it. `build_scenery`
        # is what must stop building them, and it does.
        for nm in ("SDSC_AC_%s" % tag, "SDSC_ACFin_%s" % tag):
            ob = bpy.data.objects.get(nm)
            if ob is not None and ob.library is None:
                bpy.data.objects.remove(ob, do_unlink=True)
        lift = B.JACK_LIFT if state == "jacked" else 0.0
        r = _place_one(scn, coll, tag, type_key, x, y, hdg, state,
                       apron_z, lift)
        if r is not None:
            out.append(r)
    if not quiet:
        report(out)
    return out


def report(rows):
    """What was placed, how big it turned out, and whether any two of them are
    standing in each other."""
    if not rows:
        print("fleet: nothing placed")
        return
    print("\n%-5s %-8s %-11s %6s %7s %7s %8s %8s"
          % ("stand", "type", "state", "meshes", "x_m", "y_m", "wheels_z",
             "fin_z"))
    for r in rows:
        print("%-5s %-8s %-11s %6d %7.1f %7.1f %8.2f %8.2f   "
              "%.1f x %.1f x %.1f m%s"
              % (r["tag"], r["type"], r["state"], r["meshes"],
                 0.5 * (r["x0"] + r["x1"]), 0.5 * (r["y0"] + r["y1"]),
                 r["z0"], r["z1"], r["span"], r["depth"], r["height"],
                 "  (+%.2f on jacks)" % r["lift"] if r["lift"] else ""))
    # wheels on the apron, to the centimetre
    worst = max(abs(r["z0"] - r["apron"] - r["lift"]) for r in rows)
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


if __name__ == "__main__":
    print(__doc__)
    print("masters on disk:")
    for k in sorted(TYPES):
        p = os.path.join(ROOT, TYPES[k])
        print("  %-8s %-46s %s" % (k, TYPES[k],
                                   "ok" if os.path.exists(p) else "MISSING"))
    print("stands: %s" % ", ".join("%s=%s" % (k, v or "proxy")
                                   for k, v in FLEET.items()))
