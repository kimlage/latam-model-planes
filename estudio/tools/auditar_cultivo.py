import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(root/'scenario_sdsc/sdsc_hangar_tow.blend'))
def key(o,p):return tuple(sorted((round((o.matrix_world@o.data.vertices[i].co).x,2),round((o.matrix_world@o.data.vertices[i].co).y,2)) for i in p.vertices))
base={key(o,p):p for o in bpy.context.scene.objects if 'CaneSurround' in o.name for p in o.data.polygons}
seen=set();n=duplicates=matched=0
for o in bpy.context.scene.objects:
 if 'Cropland_' not in o.name:continue
 for p in o.data.polygons:
  k=key(o,p);n+=1;duplicates+=k in seen;matched+=k in base;seen.add(k)
print('CROP_AUDIT',json.dumps(dict(polys=n,duplicate_cells=duplicates,matching_surround_cells=matched)))
