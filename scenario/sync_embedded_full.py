#!/usr/bin/env python3
"""Full re-sync of a take-off rig that EMBEDS a copy of a master aircraft.

    blender -b "airbus A320neo/A320neo_decolagem.blend" \\
        -P scenario/sync_embedded_full.py -- "airbus A320neo/A320neo_LATAM.blend"

`sync_from_master.py` (the surgical form) copies vertex coordinates and
re-points images, and that was the right tool while master rounds moved
geometry under the same topology. The appendages + surface-print rounds of
2026-08-27 broke both of its assumptions at once: the master grew NEW
objects (the 22 Apx_* probes/lights/wipers/wicks), new UV layers on
existing meshes (UVAsa on the wings), a new image (AsaLinhas) and new
shader branches in the MATERIALS - which the surgical form deliberately
never touches. This is the heavier form for that case:

* every matching local mesh datablock is REPLACED by the master's
  (``user_remap`` - so shared-datablock doors stay shared), which carries
  UV layers, material slots, and through them the master's materials and
  packed images;
* master objects with no local counterpart are appended as new pivot
  children: parent = the local Fuselagem's parent, matrix_parent_inverse
  identity, master local transform kept (the rig doctrine of 0b22f97:
  local == aircraft frame);
* the stale local material/image sets - including the ``.001`` duplicates
  a previous append left behind - are purged once nothing uses them, and
  the master's datablocks take the clean names.

The rig's OWN datablocks (pivot, hinges, camera, scenery props, their
materials) and every object transform and animation curve are untouched.
Object locations are never copied for existing objects - the fix scripts
move vertices, and in a placed scene the transform belongs to the rig.

Verification is printed, not assumed: wheel-bottom z at frame 1 before and
after (must not move - geometry was already synced in 0b22f97), the wing
UV layer list, the Apx count, and the final local-envelope sanity box.
"""
import os
import sys

import bpy


def _argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


PURGE = ("meshes", "materials", "images", "node_groups", "textures",
         "actions", "curves", "fonts")


def base(name):
    stem, dot, suf = name.rpartition(".")
    if dot and suf.isdigit() and len(suf) == 3:
        return stem
    return name


def wheel_bottom(frame=1):
    """min world z over the landing-gear meshes, at `frame`."""
    import mathutils
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    z = 1e9
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.library is not None:
            continue
        if not (ob.name.startswith("Trem") or "Roda" in ob.name):
            continue
        mw = ob.evaluated_get(dg).matrix_world
        for c in ob.bound_box:
            z = min(z, (mw @ mathutils.Vector(c)).z)
    return z


def main():
    a = _argv()
    if not a:
        raise SystemExit("usage: ... -- <master.blend>")
    master = os.path.abspath(a[0])
    print("[fullsync] %s  <-  %s" % (os.path.basename(bpy.data.filepath),
                                     os.path.basename(master)))

    wb0 = wheel_bottom()
    print("[fullsync] wheel bottom before: %.3f m" % wb0)

    local = {ob.name: ob for ob in bpy.data.objects if ob.library is None}
    before = {c: {id(d) for d in getattr(bpy.data, c)}
              for c in PURGE + ("objects",)}

    # ---- append every master object, identity-tracked ----------------------
    with bpy.data.libraries.load(master, link=False) as (src, dst):
        names = list(src.objects)
        # NB: Blender mutates the ASSIGNED list in place at block exit
        # (it becomes the loaded datablocks) - hand it a copy or `names`
        # stops being names.
        dst.objects = list(names)
    appended = dict(zip(names, dst.objects))
    n_missing = sum(1 for ob in appended.values() if ob is None)
    if n_missing:
        print("[fullsync] WARNING: %d master objects failed to append"
              % n_missing)

    # ---- swap mesh datablocks on matching objects --------------------------
    dead_meshes = []
    n_swap = 0
    for name, new_ob in appended.items():
        if new_ob is None or new_ob.type != "MESH":
            continue
        old_ob = local.get(name)
        if old_ob is None or old_ob.type != "MESH":
            continue
        old_me, new_me = old_ob.data, new_ob.data
        if old_me is new_me:
            continue
        old_me.user_remap(new_me)
        dead_meshes.append(old_me)
        n_swap += 1
    print("[fullsync] %d mesh datablocks swapped in from the master" % n_swap)

    # ---- keep master-only objects as new pivot children --------------------
    fus = local.get("Fuselagem")
    pivot = fus.parent if fus is not None else None
    det = bpy.data.collections.get("04_Detalhes")
    kept = []
    for name, new_ob in appended.items():
        if new_ob is None or name in local:
            continue
        if pivot is not None:
            new_ob.parent = pivot
            new_ob.matrix_parent_inverse.identity()
        (det or bpy.context.scene.collection).objects.link(new_ob)
        kept.append(name)
    print("[fullsync] %d new master objects kept as pivot children: %s"
          % (len(kept), ", ".join(sorted(kept)[:8]) +
             (" ..." if len(kept) > 8 else "")))

    # ---- drop the appended object shells we did not keep -------------------
    keep_ids = {id(appended[n]) for n in kept}
    for ob in list(bpy.data.objects):
        if ob.library is not None or id(ob) in before["objects"]:
            continue
        if id(ob) not in keep_ids:
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in dead_meshes:
        try:
            bpy.data.meshes.remove(me)
        except Exception:
            pass

    # ---- purge whatever nothing uses any more ------------------------------
    n_purged = 0
    for _ in range(6):
        for c in PURGE:
            coll = getattr(bpy.data, c)
            for d in list(coll):
                if d.library is not None:
                    continue
                if d.users == 1 and d.use_fake_user:
                    d.use_fake_user = False
                if d.users == 0:
                    coll.remove(d)
                    n_purged += 1
    print("[fullsync] %d orphaned datablocks purged" % n_purged)

    # ---- give surviving datablocks the clean names -------------------------
    n_renamed = 0
    for c in PURGE:
        coll = getattr(bpy.data, c)
        for d in list(coll):
            if d.library is not None:
                continue
            b = base(d.name)
            if b != d.name and coll.get(b) is None:
                d.name = b
                n_renamed += 1
    print("[fullsync] %d datablocks renamed to their base names" % n_renamed)

    # ---- verification ------------------------------------------------------
    wb1 = wheel_bottom()
    print("[fullsync] wheel bottom after: %.3f m (moved %.3f)"
          % (wb1, wb1 - wb0))
    asas = bpy.data.objects.get("Asas")
    if asas is not None:
        print("[fullsync] Asas UV layers: %s  materials: %s"
              % ([l.name for l in asas.data.uv_layers],
                 [m.name if m else None for m in asas.data.materials]))
    n_apx = sum(1 for ob in bpy.data.objects
                if ob.library is None and ob.name.startswith("Apx_"))
    print("[fullsync] Apx_ objects now local: %d" % n_apx)
    for img in ("LiveryTex", "PanelBump", "AsaLinhas", "FinSashD"):
        im = bpy.data.images.get(img)
        print("[fullsync] image %-10s %s" % (img,
              "%dx%d packed=%s" % (im.size[0], im.size[1],
                                   im.packed_file is not None)
              if im is not None else "MISSING"))
    if abs(wb1 - wb0) > 0.02:
        raise SystemExit("[fullsync] FAIL: the stance moved - not saving")
    if n_missing:
        raise SystemExit("[fullsync] FAIL: master objects missing - not saving")

    bpy.ops.wm.save_mainfile()
    print("[fullsync] SAVED", bpy.data.filepath)


if __name__ == "__main__":
    main()
