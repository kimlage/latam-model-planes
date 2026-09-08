import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[2]
r={}
for name,path in [('sbgr','scenario_sbgr/sbgr_field.blend'),('sdsc','scenario_sdsc/sdsc_hangar_tow.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(root/path));r[name]=[]
 for o in bpy.context.scene.objects:
  if o.type=='MESH' and any(k in o.name for k in ['Terrain','Serra','Cropland','Ground','Cane','Floor','TerminalBodies']):
   pts=[o.matrix_world@Vector(p) for p in o.bound_box]
   r[name].append(dict(name=o.name,vertices=len(o.data.vertices),polys=len(o.data.polygons),hidden=o.hide_render,z=[min(v.z for v in pts),max(v.z for v in pts)],materials=[m.name for m in o.data.materials if m]))
(root/'output/playwright/qa-cinema/native-geometry.json').write_text(json.dumps(r,indent=2))
