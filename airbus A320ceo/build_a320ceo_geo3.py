"""A320ceo geometry patch — STAGE 1c, 2026-08-20.

Run headless, then re-run build_a320ceo_livery.py (rings are read from meshes):
  blender -b "airbus A320ceo/A320ceo_LATAM.blend" --python "airbus A320ceo/build_a320ceo_geo3.py"

Second overwing exit moved 15.66 -> 15.28 (ACAP pair 14.43/15.28, pitch 0.85).
The ceo build had measured this on its own ACAP and photo (passo 0.86 na foto
CC-BFO) but left the master's mesh untouched, logging it as a master pendencia;
with the master now fixed, the ceo mesh follows.
"""
import bpy

D = bpy.data
log = lambda *a: print("[A320ceo3]", *a)

for n in ("Overwing2_E", "Overwing2_D"):
    ob = D.objects[n]
    for v in ob.data.vertices:
        v.co.x -= 0.38
    xs = [v.co.x + ob.location.x for v in ob.data.vertices]
    log(n, "x now %.2f..%.2f (center %.2f)" % (min(xs), max(xs), 0.5 * (min(xs) + max(xs))))

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
