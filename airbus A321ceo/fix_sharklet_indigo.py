"""Sharklet blades -> solid indigo (both faces).

Photo evidence (all in refs_manifest.json): PT-MXD 2021 (inboard face solid
indigo), PT-MXP 2024 and PT-XPB (dark inboard blades), and even the neo's own
PS-LBO photo. The inherited master leaves the blade white/grey — latent family
defect, flagged separately for the A320neo/A321neo masters."""
import bpy

D = bpy.data
asas = D.objects["Asas"]
me = asas.data

names = [m.name for m in me.materials]
print("[A321ceo] wing materials:", names)
if "LATAM_Indigo" not in names:
    me.materials.append(D.materials["LATAM_Indigo"])
    names.append("LATAM_Indigo")
idx_ind = names.index("LATAM_Indigo")

# blade geometry survey
tipv = [v.co for v in me.vertices if abs(v.co.y) > 17.0]
print("[A321ceo] tip verts:", len(tipv),
      "y", round(min(abs(v.y) for v in tipv), 2), "..", round(max(abs(v.y) for v in tipv), 2),
      "z", round(min(v.z for v in tipv), 2), "..", round(max(v.z for v in tipv), 2))

n = 0
for p in me.polygons:
    c = p.center
    ay = abs(c.y)
    if ay > 17.25 and c.z > 0.55 + 1.2 * max(0.0, 17.9 - ay):
        p.material_index = idx_ind
        n += 1
print("[A321ceo] blade faces painted indigo:", n)

bpy.ops.wm.save_mainfile()
print("SAVED", D.filepath)
