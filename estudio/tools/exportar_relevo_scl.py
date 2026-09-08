"""SCL terrain from the existing Copernicus grids. Original masters stay intact."""
import bpy,importlib.util,json,sys,struct
from pathlib import Path
from mathutils import Matrix
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'export'))
import cenarios_portateis as C
sys.path.insert(0,str(root/'scenario'))
import load_terrain as T
spec=importlib.util.spec_from_file_location('scl_scenery',root/'scenario/build_scenery.py');S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)
meta=T._meta()['grids'];mid=meta['terrain_scl_60m'];near=meta['terrain_scl_near_30m']
objects=[T.build('terrain_scl_far_180m',stride=12,obj_name='SCL_Terrain_Far',mask_inner=(mid['x_min_m'],mid['x_max_m'],mid['y_min_m'],mid['y_max_m'])),T.build('terrain_scl_60m',stride=6,obj_name='SCL_Terrain_Mid',mask_inner=(near['x_min_m'],near['x_max_m'],near['y_min_m'],near['y_max_m'])),T.build('terrain_scl_near_30m',stride=4,obj_name='SCL_Terrain_Near')]
S.flatten_aerodrome()
mat=bpy.data.materials.new('SCL_Relief');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.95
attr=mat.node_tree.nodes.new('ShaderNodeVertexColor');attr.layer_name='ReliefColor';mat.node_tree.links.new(attr.outputs['Color'],bs.inputs['Base Color'])
for ob in objects:
 ob.data.materials.append(mat);color=ob.data.color_attributes.new(name='ReliefColor',type='FLOAT_COLOR',domain='CORNER')
 for loop in ob.data.loops:
  z=ob.data.vertices[loop.vertex_index].co.z;t=max(0,min(1,z/2200));snow=max(0,min(1,(z-3500)/750));a=(.21,.17,.115);b=(.12,.125,.14)
  color.data[loop.index].color=tuple((a[i]*(1-t)+b[i]*t)*(1-snow)+.75*snow for i in range(3))+(1,)
 ob.data.transform(Matrix.Translation((662.26,1461.45,0)))
bpy.ops.object.select_all(action='DESELECT')
for ob in objects:ob.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
mp=root/'export/ambientes/manifest.json';m=json.loads(mp.read_text());notice=m['licencas']['copernicus-dem']['atribuicao'];path=root/'export/ambientes/scl_relevo.glb';C.DRACO['export_draco_position_quantization']=22
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False,export_animations=False,export_copyright=notice,**C.DRACO)
raw=path.read_bytes();g=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]]);tris=sum(g['accessors'][p['indices']]['count']//3 for mesh in g['meshes'] for p in mesh['primitives']);coords=[(v.co.x,v.co.z,-v.co.y) for o in objects for v in o.data.vertices];lo=[min(v[i] for v in coords) for i in range(3)];hi=[max(v[i] for v in coords) for i in range(3)]
row={'slug':'scl_relevo','rotulo':'Santiago · vale e cordilheira','campo':'scl','categoria':'ambiente','licenca':'copernicus-dem','arquivo':path.name,'bytes':path.stat().st_size,'triangulos':tris,'materiais':1,'caixa':{'min':lo,'max':hi,'tamanho':[hi[i]-lo[i] for i in range(3)]},'fonte':{'heightfield':'scenario/terrain/terrain_scl_*.npy','amostragem_m':[120,360,2160]},'nota':'Dados locais Copernicus modificados: três malhas com máscaras internas e ajuste sob o aeródromo. Cor por altitude interpretada.'}
m['assets']=[a for a in m['assets'] if a['slug']!=row['slug']]+[row];mp.write_text(json.dumps(m,ensure_ascii=False,indent=2));print('SCL_RELIEF_EXPORTED',path.stat().st_size,tris)
