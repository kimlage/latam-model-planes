"""A319 (PT-TMT) — pax doors raised to the ACAP sills, 2026-08-20.

Run headless, then re-run build_a319_livery.py (door rings are read from the
meshes, so the painted outlines follow):
  blender -b "airbus A319/A319_LATAM.blend" --python "airbus A319/build_a319_fix_portas.py"

The A319 inherited the master A320neo's door z, which sat ~0.55 m low vs the
ACAP 2-3-0 sill table (found in the A320ceo derivation, confirmed on the
CC-BFO and PT-TMN photos). The A319's doors sit at the same hull stations
(D4 25.81 = A320's 29.54 - 3.73), so the same raise applies:
D1 +0.55 (leaf -0.30..1.76), D4 +0.57 (leaf -0.10..1.90).
Empennage and windows stay: both were built from the A319's own ACAP + photo.
"""
import bpy

D = bpy.data
log = lambda *a: print("[A319fix]", *a)

for n, dz in (("Porta1_E", 0.55), ("Porta1_D", 0.55),
              ("Porta2_E", 0.57), ("Porta2_D", 0.57)):
    ob = D.objects[n]
    for v in ob.data.vertices:
        v.co.z += dz
    zs = [v.co.z + ob.location.z for v in ob.data.vertices]
    log(n, "z now %.2f..%.2f" % (min(zs), max(zs)))

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
