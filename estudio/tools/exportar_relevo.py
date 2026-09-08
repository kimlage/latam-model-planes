"""Export the missing GRU relief from the existing Copernicus near heightfield.
Read-only masters. Keep terrain separate from OSM airport geometry and aircraft.
Run after exportar_ambientes.py with Blender -b --factory-startup -P this_file.
"""
import bpy,importlib.util,json,sys,struct
from pathlib import Path
from mathutils import Matrix,Vector
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'export'))
import cenarios_portateis as C

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
S=module('sbgr_scenery',root/'scenario_sbgr/build_scenery.py')
T=module('sbgr_terrain',root/'scenario_sbgr/load_terrain.py')
S.G=S.Ground();S.RING_F=S.RingField(S.dedupe_ring(S.data()['aerodrome_boundary_xy_m'][0]))
ob=T.build('terrain_sbgr_near_30m',stride=2,obj_name='SBGR_Terrain_Near')
S.grade_aerodrome()
# Height-dependent colours retain the solid mountain underneath the crowns.
mat=bpy.data.materials.new('GRU_Relief');mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.95
attr=mat.node_tree.nodes.new('ShaderNodeVertexColor');attr.layer_name='ReliefColor'
mat.node_tree.links.new(attr.outputs['Color'],bsdf.inputs['Base Color']);ob.data.materials.append(mat)
colour=ob.data.color_attributes.new(name='ReliefColor',type='FLOAT_COLOR',domain='CORNER')
for loop in ob.data.loops:
 z=ob.data.vertices[loop.vertex_index].co.z;t=max(0,min(1,(z-18)/34));a=(.14,.135,.12);b=(.016,.034,.011)
 colour.data[loop.index].color=tuple(a[i]*(1-t)+b[i]*t for i in range(3))+(1,)
manifest_path=root/'export/ambientes/manifest.json';manifest=json.loads(manifest_path.read_text())
plate=json.loads((root/'export/cenarios/manifest.json').read_text())
plate=next(a for a in plate['assets'] if a['slug']=='sbgr_placa_campo');ox,oy=plate['fonte']['origem_no_campo_m']
ob.data.transform(Matrix.Translation((-ox,-oy,4.76)))
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
notice=('produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved\nThe organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30')
path=root/'export/ambientes/sbgr_relevo.glb';C.DRACO['export_draco_position_quantization']=22
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False,export_animations=False,export_copyright=notice,**C.DRACO)
raw=path.read_bytes();gltf=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
tris=sum(gltf['accessors'][p['indices']]['count']//3 for mesh in gltf['meshes'] for p in mesh['primitives'])
coords=[(v.co.x,v.co.z,-v.co.y) for v in ob.data.vertices];lo=[min(v[i] for v in coords) for i in range(3)];hi=[max(v[i] for v in coords) for i in range(3)]
manifest['licencas']['copernicus-dem']={'nome':'Copernicus DEM — dados modificados','url':'https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model','atribuicao':notice,'share_alike':False,'nota':'Heightfield local modificado: amostragem 60 m e ajuste sob o aeródromo; fonte e avisos no NOTICE.md.'}
row={'slug':'sbgr_relevo','rotulo':'GRU · relevo contínuo da serra','campo':'sbgr','categoria':'ambiente','licenca':'copernicus-dem','arquivo':path.name,'bytes':path.stat().st_size,'triangulos':tris,'materiais':1,'caixa':{'min':lo,'max':hi,'tamanho':[hi[i]-lo[i] for i in range(3)]},'fonte':{'heightfield':'scenario_sbgr/terrain/terrain_sbgr_near_30m.npy','amostragem_m':60},'nota':'Relevo contínuo sob a vegetação. Sem reinterpretação da altura das aeronaves ou dos pavimentos.'}
manifest['assets']=[a for a in manifest['assets'] if a['slug']!=row['slug']]+[row];manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(root/'export/ambientes/COPERNICUS.txt').write_text(notice+'\n')
print('RELIEF_EXPORTED',path.stat().st_size,tris)
