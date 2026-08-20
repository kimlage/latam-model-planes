"""A320neo master (PT-TMN) — ACAP corrections 2026-08-20, STAGE 1 (geometry).

Run headless:
  blender -b "airbus A320neo/A320neo_LATAM.blend" --python "airbus A320neo/build_a320neo_fix_geo.py"

Applies the pendencias recorded in spec_a320ceo.json (double ACAP read, p040
600dpi + p074-77 300dpi, three independent dimension cross-checks each):
- empennage moved aft to where the ACAP draws it: fin remapped (h,c) to
  LE x=28.02+0.863z / TE x=34.91+0.221z (was LE 26.773+0.8393z /
  TE 34.60+0.0538(z-1.55)); per-loop UV kept, so the sash art and its
  edge-crossing anchoring travel with the mesh (same recipe as the A320ceo);
- fin root bottom stretched down (z<2.05, 1.55->1.05) so the aft-moved root
  stays buried in the thinner tailcone (hull crown 1.64 at the new TE root);
- horizontal stab +0.87 -> tip TE 36.62 (= A319 ACAP 32.89 + 3.73);
- pax doors raised to the ACAP 2-3-0 sill table (ground z=-3.67):
  D1 +0.55 (leaf -0.30..1.76), D4 +0.57 (leaf -0.10..1.90). Independently
  confirmed on the PT-TMN photo (door 4 center measures z 0.81+-0.15 in the
  corrected frame; the old 0.33 is excluded);
- second overwing exit 15.66 -> 15.28 (ACAP pair 14.43/15.28, pitch 0.85);
- window row: KEPT at 40 @ 0.515 from 6.08. The ACAP full frame row
  (6.18/0.5334/41, last 27.58) is what CC-BFO flies, but the PT-TMN photo shows
  the row ending at ~26.1 with pitch 0.50-0.52 - this registration blanks the
  aft frames. Registration photo > generic drawing (rule zero).
Also dumps the ring table for the livery rebuild and moves the tail camera
target aft with the fin.
"""
import bpy
import json
import os

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))
log = lambda *a: print("[A320neoFix]", *a)

# ------------------------------------------------------------------ fin remap
LE_O = lambda z: 0.8393 * z + 26.773
TE_O = lambda z: 34.60 + 0.0538 * (z - 1.55)
LE_N = lambda z: 0.863 * z + 28.02
TE_N = lambda z: 0.221 * z + 34.91
der = D.objects["Deriva"]
for v in der.data.vertices:
    z = v.co.z
    lo, to = LE_O(z), TE_O(z)
    c = (v.co.x - lo) / max(to - lo, 1e-6)
    v.co.x = LE_N(z) + c * (TE_N(z) - LE_N(z))
log("fin remapped: root LE %.2f TE %.2f ; top LE %.2f TE %.2f"
    % (LE_N(1.55), TE_N(1.55), LE_N(8.05), TE_N(8.05)))

Z_PIVOT, K = 2.05, 2.0
n_moved = 0
for v in der.data.vertices:
    if v.co.z < Z_PIVOT:
        v.co.z = Z_PIVOT - (Z_PIVOT - v.co.z) * K
        n_moved += 1
log("fin root bottom now %.2f (%d verts)" % (min(v.co.z for v in der.data.vertices), n_moved))

# ------------------------------------------------------------------ stab
SHIFT_STAB = 0.87
eh = D.objects["EstabHorizontal"]
for v in eh.data.vertices:
    v.co.x += SHIFT_STAB
log("stab shifted +%.2f -> tip TE %.2f" % (SHIFT_STAB,
    max(v.co.x for v in eh.data.vertices)))

# ------------------------------------------------------------------ doors up
for n, dz in (("Porta1_E", 0.55), ("Porta1_D", 0.55),
              ("Porta2_E", 0.57), ("Porta2_D", 0.57)):
    ob = D.objects[n]
    for v in ob.data.vertices:
        v.co.z += dz
    zs = [v.co.z + ob.location.z for v in ob.data.vertices]
    log(n, "z now %.2f..%.2f" % (min(zs), max(zs)))

# ------------------------------------------------------------------ overwing 2
for n in ("Overwing2_E", "Overwing2_D"):
    ob = D.objects[n]
    for v in ob.data.vertices:
        v.co.x -= 0.38
    xs = [v.co.x + ob.location.x for v in ob.data.vertices]
    log(n, "x now %.2f..%.2f (center %.2f)" % (min(xs), max(xs), 0.5 * (min(xs) + max(xs))))

# ------------------------------------------------------------------ ring table
fus = D.objects["Fuselagem"]
rings = {}
for v in fus.data.vertices:
    rings.setdefault(round(v.co.x, 2), []).append(v.co)
ringtab = []
for x, gl in sorted(rings.items()):
    if len(gl) < 8:
        continue
    zs = [c.z for c in gl]
    ys = [c.y for c in gl]
    ringtab.append({"x": x, "zc": 0.5 * (max(zs) + min(zs)),
                    "rz": 0.5 * (max(zs) - min(zs)), "ry": max(ys)})
json.dump(ringtab, open(os.path.join(BASE, "a320neo_rings.json"), "w"), indent=1)
log("rings saved:", len(ringtab))

# ------------------------------------------------------------------ cameras
D.objects["CamAlvoCauda"].location.x = 32.2   # fin moved aft
bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
