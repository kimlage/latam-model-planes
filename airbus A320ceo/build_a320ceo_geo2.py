"""A320ceo geometry patch — STAGE 1b.

- pax doors raised to the ACAP sill heights (2-3-0 table, ground z=-3.67):
  D1 sill 3.381 -> leaf bottom z=-0.29 (master had -0.85);
  D4 sill 3.615 -> leaf bottom z=-0.06 (master had -0.67).
  Confirmed independently on the CC-BFO photo (door1 leaf -0.35..1.55).
- fin root bottom stretched down (z<2.05 -> bottom 1.55->1.05) so the
  aft-moved fin still buries into the thinner tailcone (crown 1.64 at TE root).
"""
import bpy
import os

D = bpy.data
log = lambda *a: print("[A320ceo2]", *a)

for n, dz in (("Porta1_E", 0.55), ("Porta1_D", 0.55),
              ("Porta2_E", 0.57), ("Porta2_D", 0.57)):
    ob = D.objects[n]
    for v in ob.data.vertices:
        v.co.z += dz
    zs = [v.co.z + ob.location.z for v in ob.data.vertices]
    log(n, "z now %.2f..%.2f" % (min(zs), max(zs)))

der = D.objects["Deriva"]
Z_PIVOT = 2.05
K = 2.0
n_moved = 0
for v in der.data.vertices:
    if v.co.z < Z_PIVOT:
        v.co.z = Z_PIVOT - (Z_PIVOT - v.co.z) * K
        n_moved += 1
zs = [v.co.z for v in der.data.vertices]
log("fin bottom now %.2f (%d verts moved)" % (min(zs), n_moved))

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
