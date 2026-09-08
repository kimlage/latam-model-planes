"""Export complete, co-registered airport surroundings and the authored tow.

Run from the repository root with Blender -b --factory-startup -P this_file.
The .blend masters are read only. Pavement stays in the existing textured
field plates; context retains buildings, roads, foliage and ground relief.
Procedural context materials use representative PBR colours, not photos.
"""
import json
import bmesh
import math
import sys
import struct
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'export'))
import cenarios_portateis as C
C.DRACO['export_draco_position_quantization'] = 22

OUT = ROOT / 'export/ambientes'
OUT.mkdir(exist_ok=True)
old = json.loads((ROOT / 'export/cenarios/manifest.json').read_text())
assets, reports = [], {}


def export_meshes(slug, objects, transform, campo, label, source, categoria='ambiente'):
    deps = bpy.context.evaluated_depsgraph_get()
    copies, report = [], {}
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), depsgraph=deps)
        # The same non-planar crop/cane grid must use the same diagonal.
        # Explicit diagonals keep the two sampled surfaces parallel through
        # glTF tessellation. Grass uses its own conforming export below.
        if any(k in ob.name for k in ('Cropland_', 'CaneSurround')):
            bm = bmesh.new(); bm.from_mesh(mesh)
            for face in list(bm.faces):
                if len(face.verts) != 4: continue
                centre = face.calc_center_median()
                vs = sorted(face.verts, key=lambda v: math.atan2(v.co.y-centre.y,v.co.x-centre.x))
                index = face.material_index
                bm.faces.remove(face)
                for ids in ((0,1,2),(0,2,3)):
                    f = bm.faces.new([vs[i] for i in ids]); f.material_index=index; f.smooth=True
            bm.to_mesh(mesh); bm.free()
        mesh.transform(ob.matrix_world)
        cp = bpy.data.objects.new(ob.name + '_web', mesh)
        bpy.context.scene.collection.objects.link(cp)
        if ob.name in ('SDSC_Hangar9_Shell', 'SDSC_Hangar9_DoorLeaves',
                       'SDSC_Hangar9_Floor', 'SBGR_LATAMHangar', 'SBGR_TerminalBodies'):
            C.assar_materiais(cp, {'categoria':'estrutura'}, ob.name+'_web', report)
        else:
            for i, mat in enumerate(mesh.materials):
                flat = C._achatar(mat, report)
                # The native high-bay lamps use a standalone Emission shader.
                emission = next((n for n in mat.node_tree.nodes if n.type=='EMISSION'),None) if mat and mat.use_nodes else None
                if emission:
                    bsdf = next(n for n in flat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
                    bsdf.inputs['Emission Color'].default_value = emission.inputs['Color'].default_value
                    bsdf.inputs['Emission Strength'].default_value = emission.inputs['Strength'].default_value
                mesh.materials[i] = flat
        mesh.transform(transform)
        # Crown blobs are disconnected low-poly components; whole-mesh
        # decimation turned them into floating triangle fragments. Preserve them.
        copies.append(cp)
    bpy.ops.object.select_all(action='DESELECT')
    for cp in copies:
        cp.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    path = OUT / (slug + '.glb')
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB',
        use_selection=True, export_apply=True, export_yup=True,
        export_animations=False, export_cameras=False, export_lights=True,
        export_copyright=old['licencas']['odbl-1.0']['atribuicao'],
        **C.DRACO)
    raw = path.read_bytes()
    gltf = json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
    triangles = sum(gltf['accessors'][p['indices']]['count']//3
        for mesh in gltf.get('meshes',[]) for p in mesh['primitives'] if 'indices' in p)
    corners = [cp.matrix_world@Vector(c) for cp in copies if cp.type=='MESH' for c in cp.bound_box]
    coords = [(v.x,v.z,-v.y) for v in corners]
    lo = [min(v[i] for v in coords) for i in range(3)]
    hi = [max(v[i] for v in coords) for i in range(3)]
    assets.append(dict(slug=slug, rotulo=label, campo=campo,
        categoria=categoria, licenca='odbl-1.0', arquivo=path.name,
        bytes=path.stat().st_size, fonte={'blend':source,
        'pecas':[o.name for o in objects]},
        triangulos=triangles, materiais=len(gltf.get('materials',[])),
        caixa={'min':lo,'max':hi,'tamanho':[hi[i]-lo[i] for i in range(3)]},
        nota='Cenário completo nas coordenadas da placa de campo. Materiais PBR simplificados; geometria OSM e arquitetura interpretada dos masters.'))
    reports[slug] = report
    for cp in copies:
        bpy.data.objects.remove(cp, do_unlink=True)


for field, source, datum in [('sbgr', 'scenario_sbgr/sbgr_field.blend', -4.76),
                              ('sdsc', 'scenario_sdsc/sdsc_hangar_tow.blend', -2.33),
                              ('scl', 'scenario/scl_field.blend', 0.0)]:
    if '--scl-only' in sys.argv and field != 'scl': continue
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / source))
    C._DUMMY = None
    C._ACHATADOS.clear()
    scn = bpy.context.scene
    scn.frame_set(1)
    plate = next(a for a in old['assets'] if a['slug'] == field + '_placa_campo')
    ox, oy = plate['fonte']['origem_no_campo_m']
    shift = Matrix.Translation((-ox, -oy, -datum))
    excluded = set(plate['fonte']['superficies'])
    prefix = field.upper() + '_'
    objects = [o for o in scn.objects if o.type == 'MESH' and not o.hide_render
        and o.name.startswith(prefix) and o.name not in excluded
        and o.name not in ('SDSC_Hangar9_SpaceFrame','SDSC_Hangar9_HighBays')
        and not any(x in o.name for x in ('_AC_', '_ACFin_', '_GA_', '_Terrain', '_Tug_', '_Towbar_'))]
    export_meshes(field + '_contexto', objects, shift, field,
        {'sbgr':'GRU · terminais, cidade e entorno','sdsc':'São Carlos · MRO e entorno, hangar aberto','scl':'Santiago · terminais e base LATAM'}[field], source)
    if field != 'sdsc':
        continue

    # Geometry is in each rig's LOCAL frame; trajectory uses the same pivot.
    for rig_name, slug, label in [('SDSC_Tug', 'sdsc_tug_operacional', 'Trator de reboque'),
                                  ('SDSC_Towbar', 'sdsc_barra_reboque', 'Barra de reboque')]:
        rig = bpy.data.objects[rig_name]
        export_meshes(slug, [o for o in rig.children_recursive if o.type == 'MESH'],
            rig.matrix_world.inverted(), field, label, source, 'veiculo')

    def point(p):
        return [round(p[0]-ox, 5), round(p[2]-datum, 5), round(-(p[1]-oy), 5)]

    fleet = json.loads((ROOT / 'export/manifest.json').read_text())
    box = next(e for e in fleet['exportacoes'] if e['slug']=='B789' and e['lod']=='web')['caixa_blender']
    pivot = Vector(((box['min'][0]+box['max'][0])/2, 0, box['min'][2]))
    rows = []
    for f in range(scn.frame_start, scn.frame_end + 1):
        scn.frame_set(f)
        row = {'t': round((f-scn.frame_start)/scn.render.fps, 5)}
        for key, name in [('aircraft','B789_Tow'), ('tug','SDSC_Tug'), ('bar','SDSC_Towbar')]:
            rig = bpy.data.objects[name]
            pos = rig.matrix_world @ pivot if key=='aircraft' else rig.matrix_world.translation
            row[key] = dict(pos=point(pos), rot=[0, math.degrees(rig.rotation_euler.z), 0])
        cam = bpy.data.objects['CamTow']
        target = cam.matrix_world @ Vector((0, 0, -140))
        # Three.js uses vertical FOV; native sensor is horizontal, 16:9 output.
        row['camera'] = dict(pos=point(cam.matrix_world.translation), alvo=point(target),
            fov=math.degrees(2*math.atan(cam.data.sensor_width/(2*cam.data.lens)/(16/9))))
        row['steer'] = math.degrees(bpy.data.objects['B789_NoseGear'].rotation_euler.z)
        rows.append(row)
    (ROOT / 'estudio/producoes/reboque-trajetoria.json').write_text(json.dumps(dict(
        fonte=source, fps=scn.render.fps, origem=[ox,oy,datum], quadros=rows), separators=(',',':')))

prior = json.loads((OUT/'manifest.json').read_text()) if (OUT/'manifest.json').exists() else {}
generated = {a['slug'] for a in assets}
assets.extend(a for a in prior.get('assets',[]) if a['slug'] not in generated)
(OUT / 'manifest.json').write_text(json.dumps(dict(licencas={**old['licencas'],**prior.get('licencas',{})},
    categorias={**prior.get('categorias',{}),'ambiente':'ambientes completos'}, campos=old['campos'], assets=assets), ensure_ascii=False, indent=2))
(OUT / 'conversao.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2))
print('COMPLETE_ENVIRONMENTS_EXPORTED', [(a['slug'], a['bytes']) for a in assets])
