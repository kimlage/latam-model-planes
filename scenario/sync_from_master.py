#!/usr/bin/env python3
"""Carry a master's corrections into a derived scene that embeds a COPY of it.

    blender -b "airbus A320neo/A320neo_scl.blend" \\
        -P scenario/sync_from_master.py -- "airbus A320neo/A320neo_LATAM.blend"

`A320neo_scl.blend` (and the `_v*` files derived from it) LINK the airport but
carry the aeroplane locally: 100 local objects with their own meshes and their
own packed textures. Every QA round on the master therefore has to be pushed
into them by hand, or the clips keep flying the old aircraft.

Two halves, and both are needed:

**Textures.** Force-remap, never compare. A sampled-hash "has it changed?" test
was tried once and missed a repaint that happened outside the first thousand
pixels; worse, in `blender -b` a packed image reports ``has_data`` False until
something touches its pixels, so the candidate list came out empty and the sync
silently did nothing. Here every image is loaded from the master, ``user_remap``
takes every reference to the stale copy, and the stale copy is removed - no
test, no candidates, no way to skip one.

**Meshes.** The round of 2026-08-20 moved geometry, not only paint: the fin and
the stabilizer went aft, the pax doors up, the second overwing exit forward, and
the sharklet blades changed material. A texture-only sync would have left a
derived scene whose aeroplane is a different shape from the master's, which is
exactly the failure this script exists to prevent. The copy is surgical - vertex
coordinates and per-face material indices are written into the meshes that are
already there, so object transforms, parenting, animation curves and the local
material datablocks are untouched. Topology must match; anything that does not
match is reported and skipped rather than guessed at.

Object LOCATIONS are deliberately not copied: the fix scripts move vertices, and
in a placed scene the object transform belongs to the rig.
"""
import os
import sys

import bpy
import numpy as np


COLLECTIONS = ("objects", "meshes", "materials", "images", "node_groups",
               "actions", "curves", "fonts", "textures", "collections")


def _argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _snapshot():
    """Identity of every local datablock, so an append can be undone exactly."""
    return {c: {id(d) for d in getattr(bpy.data, c) if d.library is None}
            for c in COLLECTIONS}


def _drop_new(before, keep=()):
    """Remove everything an append brought in except the ids in `keep`.

    Appending an object drags its materials, images and node groups along, and
    the master marks several materials with a FAKE USER - so they survive the
    save as ``LATAM_Indigo.001`` clutter unless the flag is cleared first. This
    is what keeps a synced scene from growing a duplicate material set every
    time the sync is run.
    """
    keep = {id(d) for d in keep}
    for c in COLLECTIONS:
        coll = getattr(bpy.data, c)
        for d in list(coll):
            if d.library is not None or id(d) in before[c] or id(d) in keep:
                continue
            if hasattr(d, "use_fake_user"):
                d.use_fake_user = False
    for _ in range(4):                      # users_ drop as owners disappear
        for c in COLLECTIONS:
            coll = getattr(bpy.data, c)
            for d in list(coll):
                if d.library is not None or id(d) in before[c] or id(d) in keep:
                    continue
                if d.users == 0:
                    coll.remove(d)
    left = [d.name for c in COLLECTIONS for d in getattr(bpy.data, c)
            if d.library is None and id(d) not in before[c] and id(d) not in keep]
    if left:
        print("[sync] %d appended datablocks could not be dropped: %s"
              % (len(left), left[:8]))


def sync_images(master):
    """Replace every local image with the master's copy, unconditionally."""
    # "Render Result" and "Viewer Node" are render buffers, not paint
    stale = {im.name: im for im in bpy.data.images
             if im.library is None and im.size[0] > 0
             and im.name not in ("Render Result", "Viewer Node")}
    if not stale:
        print("[sync] no local images")
        return
    before = _snapshot()
    with bpy.data.libraries.load(master, link=False) as (src, dst):
        dst.images = [n for n in src.images if n in stale]
    fresh = {}
    for im in bpy.data.images:
        if im.library is not None or id(im) in before["images"]:
            continue
        fresh.setdefault(im.name.rsplit(".", 1)[0], im)   # appended as "X.001"
    n = 0
    kept = []
    for name, old in sorted(stale.items()):
        new = fresh.get(name)
        if new is None:
            print("[sync] image %-12s NOT IN MASTER - left alone" % name)
            continue
        # touch the pixels: a packed image in -b reports has_data False until
        # read, which once emptied a sync's candidate list without a word
        try:
            _ = new.pixels[0]
        except (IndexError, RuntimeError):
            print("[sync] image %-12s HAS NO DATA in the master - skipped" % name)
            continue
        old.user_remap(new)
        bpy.data.images.remove(old)
        new.name = name
        if new.packed_file is None:
            new.pack()
        print("[sync] image %-12s remapped from master (%dx%d)"
              % (name, new.size[0], new.size[1]))
        kept.append(new)
        n += 1
    _drop_new(before, keep=kept)
    print("[sync] %d images synced" % n)


def sync_meshes(master):
    """Copy vertex coordinates and material indices for every matching mesh."""
    local = {o.name: o for o in bpy.data.objects
             if o.library is None and o.type == "MESH"}
    before = _snapshot()
    with bpy.data.libraries.load(master, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in local]
    got = [o for o in bpy.data.objects
           if o.library is None and o.type == "MESH" and id(o) not in before["objects"]]
    ref = {}
    for o in got:
        base = o.name.rsplit(".", 1)[0]
        ref[base] = o
    ok = skipped = 0
    for name in sorted(local):
        src_ob = ref.get(name)
        dst_ob = local[name]
        if src_ob is None:
            continue
        a, b = src_ob.data, dst_ob.data
        if len(a.vertices) != len(b.vertices) or len(a.polygons) != len(b.polygons):
            print("[sync] mesh  %-18s TOPOLOGY DIFFERS (%d/%d verts, %d/%d faces) - SKIPPED"
                  % (name, len(a.vertices), len(b.vertices),
                     len(a.polygons), len(b.polygons)))
            skipped += 1
            continue
        co = np.empty(len(a.vertices) * 3, np.float32)
        a.vertices.foreach_get("co", co)
        was = np.empty_like(co)
        b.vertices.foreach_get("co", was)
        b.vertices.foreach_set("co", co)
        mi_src = np.empty(len(a.polygons), np.int32)
        a.polygons.foreach_get("material_index", mi_src)
        mi_dst = np.empty(len(b.polygons), np.int32)
        b.polygons.foreach_get("material_index", mi_dst)
        na = [m.name.rsplit(".", 1)[0] if m else None for m in a.materials]
        nb = [m.name.rsplit(".", 1)[0] if m else None for m in b.materials]
        mapped = mi_src
        if na != nb:
            table = {}
            for i, mn in enumerate(na):
                table[i] = nb.index(mn) if mn in nb else 0
                if mn not in nb:
                    print("[sync] mesh  %-18s material '%s' absent locally -> slot 0"
                          % (name, mn))
            mapped = np.array([table[int(i)] for i in mi_src], np.int32)
        b.polygons.foreach_set("material_index", mapped)
        b.update()
        dv = float(np.abs(co - was).max())
        dm = int((mapped != mi_dst).sum())
        if dv > 1e-6 or dm:
            print("[sync] mesh  %-18s verts moved up to %.3f m, %d faces re-assigned"
                  % (name, dv, dm))
        ok += 1
    _drop_new(before)
    print("[sync] %d meshes synced, %d skipped" % (ok, skipped))


def main():
    a = _argv()
    if not a:
        raise SystemExit("usage: ... -- <master.blend>")
    master = os.path.abspath(a[0])
    print("[sync] %s  <-  %s" % (os.path.basename(bpy.data.filepath),
                                 os.path.basename(master)))
    sync_meshes(master)
    sync_images(master)
    bpy.ops.wm.save_mainfile()
    print("[sync] SAVED", bpy.data.filepath)


if __name__ == "__main__":
    main()
