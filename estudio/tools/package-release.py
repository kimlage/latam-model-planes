"""Assemble the animation distribution from the validated catalog and renders."""
from pathlib import Path
import argparse,hashlib,html,json,shutil,zipfile
parser=argparse.ArgumentParser();parser.add_argument("--prepare",action="store_true");args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'dist';OUT.mkdir(exist_ok=True)
STAGE=OUT/'latam-animacoes-completo-2026-09-08';STAGE.mkdir(exist_ok=True)
rows=json.loads((ROOT/'output/release-scenes/scenes.json').read_text())
results=json.loads((ROOT/'output/release-videos/results.json').read_text())
if not args.prepare: assert len(rows)==len(results)==122 and {r['id'] for r in rows}=={r['id'] for r in results}

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def copy(source,relative):
 target=STAGE/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)

# Only executable web assets, code and distribution documentation; no workspace logs/backups.
for f in (ROOT/'estudio').rglob('*'):
 rel=f.relative_to(ROOT)
 if not f.is_file() or any(p in {'__pycache__','tests','tools'} for p in rel.parts):continue
 if f.name=='cockpit.js' or 'cockpit' in f.name:continue
 if f.name=='LICENSE' or f.suffix in {'.html','.js','.css','.json','.wasm','.svg','.mp4','.png','.txt','.md','.py'}:copy(f,rel)
for f in (ROOT/'export').rglob('*'):
 if f.is_file() and (f.suffix in {'.glb','.txt'} or f.name in {'manifest.json','README.md'}):copy(f,f.relative_to(ROOT))
for n in ['LICENSE','NOTICE.md']:copy(ROOT/n,n)
(STAGE/'README.md').write_text((ROOT/'docs/ANIMACOES.md').read_text().replace('(../estudio/', '(estudio/').replace('(../NOTICE.md)', '(NOTICE.md)'))
copy(ROOT/'docs/ANIMACOES.md','docs/ANIMACOES.md')
catalog=[]
for r in rows:
 c=r['config'];rel=Path(c['aeroporto'])/c['aeronave']/c['situacao'];video=Path('animacoes')/rel.with_suffix('.mp4');scene=Path('cenas')/rel.with_suffix('.json')
 source=ROOT/'output/release-videos'/(r['id']+'.mp4')
 if source.exists():copy(source,video)
 elif not args.prepare:raise FileNotFoundError(source)
 dest=STAGE/scene;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(r['document'],ensure_ascii=False,indent=2))
 catalog.append({'id':r['id'],**c,'video':video.as_posix(),'scene':scene.as_posix()})
(STAGE/'catalogo.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2))
links=''.join('<tr><td>'+html.escape(r['aeroporto'].upper())+'</td><td>'+html.escape(r['aeronave'])+'</td><td>'+html.escape(r['situacao'])+'</td><td><a href="'+r['video']+'">Ver MP4</a></td><td><a href="'+r['scene']+'" download>JSON</a></td></tr>' for r in catalog)
(STAGE/'index.html').write_text('''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>LATAM · 122 animações</title><style>body{font:16px system-ui;background:#10121b;color:#eee;max-width:1000px;margin:40px auto;padding:20px}a{color:#a9c7ff}td,th{text-align:left;padding:12px;border-bottom:1px solid #343744}table{width:100%;border-collapse:collapse}video{width:100%;background:#000;position:sticky;top:0;max-height:50vh}h1{font-size:28px}</style><h1>LATAM · Biblioteca de animações</h1><p>122 vídeos · 11 aeronaves · três bases. Selecione um MP4 na tabela para reproduzir.</p><video controls playsinline></video><p><label>Filtrar base, aeronave ou situação <input type="search" id="filter"></label></p><p>Para editar, consulte o README. <a href="NOTICE.md">Licenças e atribuições</a></p><table><thead><tr><th>Base</th><th>Aeronave</th><th>Situação</th><th>Vídeo</th><th>Cena</th></tr></thead><tbody>'''+links+'''</tbody></table><script>document.querySelectorAll('a[href$=".mp4"]').forEach(a=>a.onclick=e=>{e.preventDefault();const v=document.querySelector('video');v.src=a.getAttribute('href');v.play()});document.querySelector('#filter').oninput=e=>{const q=e.target.value.toLocaleLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLocaleLowerCase().includes(q))}</script></html>''')
if args.prepare:
 print('Prepared runnable package at',STAGE);raise SystemExit(0)
files={f.relative_to(STAGE).as_posix():{'bytes':f.stat().st_size,'sha256':digest(f)} for f in sorted(STAGE.rglob('*')) if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc' and f.name!='manifest-sha256.json'}
(STAGE/'manifest-sha256.json').write_text(json.dumps(files,indent=2))
archive=OUT/(STAGE.name+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(STAGE.rglob('*')):
  if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc':z.write(f,Path(STAGE.name)/f.relative_to(STAGE),compress_type=zipfile.ZIP_STORED if f.suffix in {'.mp4','.glb','.png','.wasm'} else zipfile.ZIP_DEFLATED)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
checksum=digest(archive);(OUT/(archive.name+'.sha256')).write_text(checksum+'  '+archive.name+'\n')
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files)+1,'sha256':checksum}))
