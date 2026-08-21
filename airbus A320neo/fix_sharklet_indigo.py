"""Sharklet blades -> solid indigo (both faces), as on the A321ceo.

Photo evidence (A321ceo refs_manifest.json: PT-MXD 2021, PT-MXP 2024, PT-XPB;
and the A321neo's own ref PS-LBO DSC00834 — port sharklet indigo above the
fuselage): LATAM blades are solid indigo, inboard face included. The master
left the inboard face white/grey — latent family defect fixed on the A321ceo
by its fix_sharklet_indigo.py.

The A321ceo carries the SAME ~7% oversize master wing (identical 448-vert
mesh, tips at |y| 19.142), so its constants apply here UNCHANGED — verified
by per-face-index diff against the ceo blend: this selection reproduces the
ceo tip-zone assignment with 0 differences. Do NOT rescale the constants by
the oversize factor; a scaled version under-selects the blade-root band
(31 faces, y 18.40-18.71, z 0.55-1.12) and renders a white notch at the
blade-root trailing edge.

Run headless:
  blender -b "airbus A320neo/A320neo_LATAM.blend" --python "airbus A320neo/fix_sharklet_indigo.py"
"""
import bpy

D = bpy.data
TAG = "A320neo"
asas = D.objects["Asas"]
me = asas.data

names = [m.name for m in me.materials]
print(f"[{TAG}] wing materials:", names)
if "LATAM_Indigo" not in names:
    me.materials.append(D.materials["LATAM_Indigo"])
    names.append("LATAM_Indigo")
idx_ind = names.index("LATAM_Indigo")

# blade geometry survey
tipv = [v.co for v in me.vertices if abs(v.co.y) > 17.0]
print(f"[{TAG}] tip verts:", len(tipv),
      "y", round(min(abs(v.y) for v in tipv), 2), "..", round(max(abs(v.y) for v in tipv), 2),
      "z", round(min(v.z for v in tipv), 2), "..", round(max(v.z for v in tipv), 2))

# A321ceo selection, verbatim (same oversize wing coordinates)
n = 0
for p in me.polygons:
    c = p.center
    ay = abs(c.y)
    if ay > 17.25 and c.z > 0.55 + 1.2 * max(0.0, 17.9 - ay):
        p.material_index = idx_ind
        n += 1
print(f"[{TAG}] blade faces painted indigo:", n)

bpy.ops.wm.save_mainfile()
print("SAVED", D.filepath)
