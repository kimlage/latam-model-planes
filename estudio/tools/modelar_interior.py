"""Build an interpreted MRO interior, using the existing hangar shell datum.
Reference: scenario_sdsc/refs/mro_centro_tecnologico_2010.jpg (red trusses,
individual high bays and mobile work equipment). Layout is authored, not surveyed.
Run with Blender -b --factory-startup --python-exit-code 1 -P this_file.
"""
import bpy, math, json, sys, struct
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'export'));import cenarios_portateis as C
C.DRACO['export_draco_position_quantization']=22
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
parts=[];floor=-37.05

def mat(name,color,metal=0,rough=.6,emission=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
 if emission:b.inputs['Emission Color'].default_value=(*color,1);b.inputs['Emission Strength'].default_value=emission
 return m
red=mat('H9_RedSteel',(.28,.035,.023),.3,.45);steel=mat('H9_Galvanized',(.38,.42,.44),.45,.4)
yellow=mat('H9_SafetyYellow',(.76,.45,.025),.25,.5);dark=mat('H9_Rubber',(.015,.02,.025),0,.8)
blue=mat('H9_ToolCabinet',(.025,.075,.14),.4,.4);white=mat('H9_WallPanel',(.52,.54,.51),.2,.6)
black=mat('H9_Joint',(.065,.07,.075),0,.85);lamp=mat('H9_Lamp',(.93,.95,1),0,.25,3)
green=mat('H9_Exit',(.025,.3,.085),0,.6,1)

def finish(o,name,m):
 o.name=name;o.data.materials.append(m);parts.append(o);return o

def box(name,p,size,m):
 bpy.ops.mesh.primitive_cube_add(size=1,location=(p[0],p[1],floor+p[2]));o=bpy.context.object;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,name,m)

def rod(name,a,b,r,m):
 a=Vector((a[0],a[1],floor+a[2]));b=Vector((b[0],b[1],floor+b[2]));v=b-a
 bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=r,depth=v.length,location=(a+b)/2);o=bpy.context.object;o.rotation_euler=v.to_track_quat('Z','Y').to_euler();return finish(o,name,m)

def text(name,label,p,size,m,wall=False):
 bpy.ops.object.text_add(location=(p[0],p[1],floor+p[2]));o=bpy.context.object;o.data.body=label;o.data.size=size;o.data.align_x='CENTER';o.data.extrude=.003
 if wall:o.rotation_euler=(math.pi/2,0,math.pi)
 bpy.ops.object.convert(target='MESH');return finish(o,name,m)

# Portal columns and true open trusses, above the tail envelope (> 20.8 m).
for y in range(1595,1684,14):
 top=21.95+4*(1-abs(y-1637.5)/47.5)-.6;bottom=top-2
 for x in (687,813):
  box('H9_Column',(x,y,top/2),(.5,.7,top),red)
  box('H9_BasePlate',(x,y,.10),(1.1,1.1,.2),steel)
 for z in (bottom,top):rod('H9_TrussChord',(687,y,z),(813,y,z),.17,red)
 for i in range(18):
  x=687+i*7
  rod('H9_TrussWeb',(x,y,bottom),(x+7,y,top),.085,red);rod('H9_TrussWeb',(x,y,top),(x+7,y,bottom),.085,red)
for x in range(690,814,8):
 rod('H9_Purlin',(x,1592,21.8),(x,1637.5,25.5),.10,steel)
 rod('H9_Purlin',(x,1637.5,25.5),(x,1683,21.8),.10,steel)
# Wall girts, low wall protection, enclosed utility corridor along the back.
for x in (686.2,813.8):
 for z in (3,7,11,15,19):rod('H9_WallGirt',(x,1592,z),(x,1683,z),.1,steel)
 box('H9_WallBase',(x,1637.5,1),(0.15,90,2),white)
box('H9_WorkshopFacade',(750,1592,2.4),(124,.3,4.8),white)
for x in (699,723,778,802):
 box('H9_WorkshopDoor',(x,1592.2,1.1),(1.4,.09,2.2),blue)
 text('H9_ExitSign','SAIDA',(x,1592.28,2.75),.3,green,True)
text('H9_BaySign','HANGAR 09  /  MRO',(750,1592.3,4),.85,blue,True)
# Floor joints and yellow equipment bays. All raised a few mm, never a second slab.
for x in range(690,813,10):box('H9_FloorJoint',(x,1637,.005),(.018,90,.006),black)
for y in range(1595,1683,10):box('H9_FloorJoint',(750,y,.005),(126,.018,.006),black)
for x in (704,796):
 box('H9_FloorMarking',(x,1638,.018),(.12,84,.009),yellow)
 for y in range(1600,1681,12):box('H9_FloorMarking',(x+(-6 if x<750 else 6),y,.018),(12,.12,.009),yellow)
for y in range(1600,1680,4):box('H9_FloorCenterline',(750,y,.018),(.12,2,.009),yellow)
text('H9_FloorText','09',(750,1679,.035),2.3,yellow)
# Individual suspended high bays. Geometry emits; the GLB carries a sparse light grid.
for ix,x in enumerate((704,727,750,773,796)):
 for iy,y in enumerate((1605,1626,1647,1668)):
  rod('H9_LampDrop',(x,y,22),(x,y,20.4),.028,steel)
  box('H9_LampHousing',(x,y,20.35),(1.35,.7,.18),dark)
  box('H9_LampDiffuser',(x,y,20.23),(1.2,.6,.035),lamp)
  if ix%2==0:
   ld=bpy.data.lights.new('H9_InteriorLight','SPOT');ld.energy=6.6;ld.spot_size=math.radians(120);ld.spot_blend=.6;ld.color=(1,.96,.9);ld.shadow_soft_size=3
   o=bpy.data.objects.new(ld.name,ld);bpy.context.collection.objects.link(o);o.location=(x,y,floor+19.8);parts.append(o)

# Low, broad fill approximates light reflected by the floor and open door.
for x in (720,780):
 for y in (1610,1660):
  ld=bpy.data.lights.new('H9_BounceFill','POINT');ld.energy=.7;ld.color=(1,.96,.91)
  o=bpy.data.objects.new(ld.name,ld);bpy.context.collection.objects.link(o);o.location=(x,y,floor+7);parts.append(o)

def cart(x,y):
 box('H9_ToolChest',(x,y,.65),(1.4,.75,1),red);box('H9_Worktop',(x,y,1.2),(1.5,.85,.09),dark)
 for h in (.35,.55,.75,.95):box('H9_DrawerPull',(x,y+.39,h),(.9,.035,.025),steel)
 for dx in (-.52,.52):
  for dy in (-.25,.25):rod('H9_Caster',(x+dx,y+dy-.035,.13),(x+dx,y+dy+.035,.13),.12,dark)

def platform(x,y):
 # Parked mobile access tower, outside the wing/tow corridor.
 for dx in (-1,1):
  for dy in (-1.7,1.7):
   rod('H9_PlatformUpright',(x+dx,y+dy,.2),(x+dx,y+dy,4.1),.055,yellow)
   rod('H9_PlatformWheel',(x+dx,y+dy-.06,.17),(x+dx,y+dy+.06,.17),.16,dark)
 box('H9_PlatformDeck',(x,y,3),(2.2,3.7,.10),steel)
 for dx in (-1,1):
  rod('H9_Handrail',(x+dx,y-1.7,4.1),(x+dx,y+1.7,4.1),.045,yellow)
  rod('H9_Brace',(x+dx,y-1.7,.3),(x+dx,y+1.7,3),.035,yellow)
 for h in range(11):box('H9_StairTread',(x,y-4.4+h*.27,.3+h*.27),(1.1,.3,.055),steel)
 for dx in (-.5,.5):rod('H9_StairStringer',(x+dx,y-4.4,.2),(x+dx,y-1.7,2.9),.07,steel)
 rod('H9_PlatformEndRail',(x-1,y+1.7,4.1),(x+1,y+1.7,4.1),.045,yellow)
 for dx in (-.65,.65):rod('H9_StairRail',(x+dx,y-4.4,1.3),(x+dx,y-1.7,4),.045,yellow)

for x in (692,807):
 for y in (1608,1640,1668):
  box('H9_WorkBench',(x,y,1),(2.4,1,.10),steel)
  for dx in (-1,1):box('H9_BenchLeg',(x+dx,y,.5),(.08,.8,1),steel)
  cart(x+3 if x<750 else x-3,y+2)
  box('H9_PartsCabinet',(x,y+5,1.2),(2,1,2.4),blue)
  for h in (.5,1.1,1.7,2.3):box('H9_Shelf',(x,y+5,h),(1.9,1.02,.07),steel)
  rod('H9_FireExtinguisher',(x,y-3,.25),(x,y-3,1.05),.14,red)
for x,y in ((700,1612),(703,1626),(800,1630),(700,1650),(801,1668)):platform(x,y)
cart(712,1618)
cart(795,1649)
# Hose/cable trays run along walls, not through the aircraft path.
for x in (689,811):
 rod('H9_ServicePipe',(x,1596,3.3),(x,1680,3.3),.06,blue)
 for y in (1610,1640,1670):
  rod('H9_ServiceDrop',(x,y,3.3),(x,y,1),.035,blue)
  for i in range(24):
   a=2*math.pi*i/24;b=2*math.pi*(i+1)/24
   rod('H9_HoseReel',(x+.2,y+.38*math.cos(a),1.4+.38*math.sin(a)),(x+.2,y+.38*math.cos(b),1.4+.38*math.sin(b)),.022,dark)
# Merge by material so detail does not create thousands of draw calls.
meshes=[o for o in parts if o.type=='MESH'];grouped=[]
lights=[o for o in parts if o.type=='LIGHT']
groups=[(material,is_floor,[o for o in meshes if o.data.materials[0]==material and o.name.startswith('H9_Floor')==is_floor]) for material in list(bpy.data.materials) for is_floor in (False,True)]
for material,is_floor,group in groups:
 if not group:continue
 bpy.ops.object.select_all(action='DESELECT')
 for o in group:o.select_set(True)
 bpy.context.view_layer.objects.active=group[0];bpy.ops.object.join();o=group[0]
 o.name=('H9_Floor_' if is_floor else 'H9_Interior_')+material.name;grouped.append(o)
shift=Matrix.Translation((-570.18,-979.62,2.33))
for o in grouped+lights:o.matrix_world=shift@o.matrix_world
bpy.ops.object.select_all(action='DESELECT')
for o in grouped+lights:o.select_set(True)
out=ROOT/'export/ambientes';path=out/'sdsc_hangar9_interior.glb'
credit='LATAM fleet 3D replicas - Kim Lage - CC BY 4.0'
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_lights=True,export_animations=False,export_copyright=credit,**C.DRACO)
raw=path.read_bytes();g=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
tris=sum(g['accessors'][p['indices']]['count']//3 for m in g['meshes'] for p in m['primitives'])
mf=out/'manifest.json';manifest=json.loads(mf.read_text())
row=dict(slug='sdsc_hangar9_interior',rotulo='Hangar 9 · interior MRO',campo='sdsc',categoria='interior',licenca='cc-by-4.0',arquivo=path.name,bytes=path.stat().st_size,triangulos=tris,materiais=len(g.get('materials',[])),caixa={'tamanho':[128,26,94]},nota='Interior interpretado a partir da referência local do MRO. Equipamentos estacionados fora do corredor central; não é levantamento do Hangar 9.',fonte={'script':'estudio/tools/modelar_interior.py','referencia':'scenario_sdsc/refs/mro_centro_tecnologico_2010.jpg'})
manifest['assets']=[a for a in manifest['assets'] if a['slug']!=row['slug']]+[row];manifest['categorias']['interior']='interiores de hangar';mf.write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print('INTERIOR_EXPORTED',row['bytes'],tris,flush=True)
