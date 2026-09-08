"""Bake field plates with millimetre-scale Draco precision at airport scale.
14 bits over 6 km can displace points by 37 cm, swallowing raised pavements.
These production plates use 22 bits; the existing library exports stay intact.
Run with Blender -b --factory-startup -P this_file after exportar_ambientes.py.
"""
import json
import sys
from pathlib import Path
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'export'))
import cenarios_portateis as C
OUT = ROOT/'export/ambientes'
manifest = json.loads((OUT/'manifest.json').read_text())
C.DRACO['export_draco_position_quantization'] = 22
for field in ['sbgr','sdsc','scl']:
    if '--scl-only' in sys.argv and field != 'scl': continue
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/C.CAMPOS[field]['blend']))
    C._DUMMY = None
    C._ACHATADOS.clear()
    if field == 'sdsc':
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from conformar_grama import conformar_grama
        conformar_grama()
    slug = field+'_pavimentos_precisos'
    spec = dict(C.CATALOGO[field+'_placa_campo'])
    spec['rotulo'] = field.upper()+' · pistas e pátios de precisão'
    report = {}
    row = C.montar(slug,spec,C.CAMPOS[field],str(OUT),report)
    row['nota'] = 'Pavimentos nas coordenadas de campo, compressão de posição a 22 bits para preservar as separações de centímetros entre as superfícies.'
    manifest['assets'] = [a for a in manifest['assets'] if a['slug']!=slug]+[row]
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    (OUT/(slug+'-bake.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('PRECISE_PLATE_EXPORTED',slug,flush=True)
