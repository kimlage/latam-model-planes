"""A320ceo (CC-BFO) geometry derivation from the A320neo master — STAGE 1.

Run headless:
  blender -b "airbus A320ceo/A320ceo_LATAM.blend" --python "airbus A320ceo/build_a320ceo_geo.py"

Derivation (spec_a320ceo.json):
- fuselage/doors/gear/wing identical to the master (ACAP 2-2-0 + 2-7-0:
  same dims, same door stations "ON A/C A320-200 A320neo");
- engines: PW1100G -> CFM56-5B4/3: radial x0.835 about (y5.75, z-1.95) then
  z-0.055 (nacelle low point 0.577 m above ground, ACAP 2-3-0 N1 CFM 5B),
  length x0.94 anchored at inlet 11.19 (ACAP top view "CFM56 11.19 m");
- empennage per ACAP (double-read p040 600dpi + p074 300dpi):
  fin remapped (h,c) to LE x=28.02+0.863z / TE x=34.91+0.221z,
  stab shifted +0.87 (tip TE 36.62 = A319 ACAP 32.89 + 3.73);
- windows: first 6.18, pitch 0.5334 (21-in frames), 41 per side (ACAP drawing;
  master had 40 @ 0.515 from 6.08 — row ended 1.3 m early);
- neo-only marks removed; gear-door reg -> BFO.
"""
import bpy
import json
import math
import os

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))
log = lambda *a: print("[A320ceo]", *a)

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
    ln, tn = LE_N(z), TE_N(z)
    v.co.x = ln + c * (tn - ln)
log("fin remapped: root LE %.2f TE %.2f ; top LE %.2f TE %.2f"
    % (LE_N(1.55), TE_N(1.55), LE_N(8.05), TE_N(8.05)))

# ------------------------------------------------------------------ stab
SHIFT_STAB = 0.87
eh = D.objects["EstabHorizontal"]
for v in eh.data.vertices:
    v.co.x += SHIFT_STAB
log("stab shifted +%.2f -> tip TE %.2f" % (SHIFT_STAB,
    max(v.co.x for v in eh.data.vertices)))
# CC-BFO: light-grey upper surface (photo 2022), not the indigo of today's PT-TMN
mats = eh.data.materials
grey = D.materials.get("CinzaAsa") or D.materials.get("CinzaBarriga")
if grey.name not in [m.name for m in mats]:
    mats.append(grey)
gi = [m.name for m in mats].index(grey.name)
n_sw = 0
for p in eh.data.polygons:
    if p.material_index == 0:          # 0 = LATAM_Indigo (upper faces)
        p.material_index = gi
        n_sw += 1
log("stab top faces -> %s (%d faces)" % (grey.name, n_sw))

# ------------------------------------------------------------------ engines CFM56-5B
SR = 0.835          # radial about (Y0, Z0)
DZ = -0.055         # then translate down (low point -3.09)
SL = 0.94           # length about inlet
X_REF_OLD = 11.14   # PW inlet world x
X_REF_NEW = 11.19   # CFM inlet world x (ACAP top view)
Y0, Z0 = 5.75, -1.95
for n in ("Motor_Nacelle", "Motor_Fan", "Motor_Spinner", "Motor_Core", "Motor_Exaustao"):
    ob = D.objects[n]
    lx = ob.location.x
    for v in ob.data.vertices:
        xw = v.co.x + lx
        v.co.x = (X_REF_NEW + SL * (xw - X_REF_OLD)) - lx
        v.co.y = Y0 + SR * (v.co.y - Y0)
        v.co.z = Z0 + SR * (v.co.z - Z0) + DZ
    log("CFM56-scaled", n)
ob = D.objects["Motor_Pylon"]
lx = ob.location.x
for v in ob.data.vertices:
    xw = v.co.x + lx
    v.co.x = (X_REF_NEW + SL * (xw - X_REF_OLD)) - lx
    v.co.y = Y0 + SR * (v.co.y - Y0)
log("pylon adjusted")
nb = D.objects["Motor_Nacelle"]
xs = [v.co.x + nb.location.x for v in nb.data.vertices]
zs = [v.co.z for v in nb.data.vertices]
log("nacelle now x %.2f..%.2f z %.2f..%.2f" % (min(xs), max(xs), min(zs), max(zs)))

# ------------------------------------------------------------------ windows
jp = D.objects["JanelasPax"]
jp.location.x = 6.18
for m in jp.modifiers:
    if m.type == 'ARRAY':
        m.count = 41
        m.constant_offset_displace[0] = 0.5334
        log("windows: first 6.18, pitch 0.5334, count", m.count)

# ------------------------------------------------------------------ marks & text
reg = D.objects.get("RegPortaTrem")
if reg and reg.type == 'FONT':
    reg.data.body = "BFO"
    log("gear door text -> BFO")
for n in ("CapAmerica_E", "CapAmerica_D", "CapPrimeiro_E", "CapPrimeiro_D",
          "LogoA320neo_E", "LogoA320neo_D"):
    ob = D.objects.get(n)
    if ob:
        me_old = ob.data
        D.objects.remove(ob, do_unlink=True)
        if me_old.users == 0:
            D.meshes.remove(me_old)
        log("removed", n)

# ------------------------------------------------------------------ ring table for livery
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
json.dump(ringtab, open(os.path.join(BASE, "a320ceo_rings.json"), "w"), indent=1)
log("rings saved:", len(ringtab))

# ------------------------------------------------------------------ cameras
D.objects["CamAlvoCauda"].location.x = 32.2   # fin moved aft
D.objects["CamCauda"].location.x = 46.0
col = D.collections.get("A320neo_LATAM")
if col:
    col.name = "A320ceo_LATAM"

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
