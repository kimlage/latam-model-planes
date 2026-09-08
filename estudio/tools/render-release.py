"""Render the supported catalog through the same browser exporter as the Studio.
Requires the headless latam-cinema-headless session and capture-release.js catalog.
Progress is recoverable: completed videos are probed before skipping them.
"""
from pathlib import Path
import argparse, json, subprocess, shutil
parser=argparse.ArgumentParser();parser.add_argument("--base");parser.add_argument("--situation");parser.add_argument("--session",default="latam-cinema-headless");parser.add_argument("--port",type=int,default=8137);args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[2]
executable=shutil.which('playwright-cli')
CLI=([executable] if executable else ['npx','--yes','--package','@playwright/cli','playwright-cli'])+['-s='+args.session]
FFMPEG=shutil.which('ffmpeg') or 'ffmpeg'
FFPROBE=shutil.which('ffprobe') or 'ffprobe'

OUT=ROOT/'output/release-videos';OUT.mkdir(exist_ok=True,parents=True)
rows=json.loads((ROOT/'output/release-scenes/scenes.json').read_text())
if args.base: rows=[r for r in rows if r['config']['aeroporto']==args.base]
if args.situation: rows=[r for r in rows if r['config']['situacao']==args.situation]
results=[]
for number,row in enumerate(rows,1):
    name=row['id'];dest=OUT/(name+'.mp4');d=row['document'];expected=round(d['linha']['duracao']*d['linha']['fps'])
    if row['video'] and not dest.exists():shutil.copy2(ROOT/'estudio/loading/media/cinema'/(row['video']+'.mp4'),dest)
    if not dest.exists():
        c=row['config'];url=f'http://127.0.0.1:{args.port}/estudio/loading/runtime.html?airport='+c['aeroporto']+'&aircraft='+c['aeronave']+'&situation='+c['situacao']
        chunks=[]
        for start in range(0,expected,150):
            end=min(expected,start+150);part=OUT/(name+f'.part-{start:04d}.mp4');chunks.append(part)
            if part.exists():continue
            code='''async(page)=>{const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720},acceptDownloads:true}),p=await ctx.newPage();try{
 await p.goto(URL);await p.waitForFunction(()=>window.__cinema,{timeout:60000});
 await p.evaluate(async()=>{__cinema.t=0;const {exportarMp4}=await import('../js/exportar.js');const r=await exportarMp4(__cinema.mundo,__cinema.doc,{larg:1280,alt:720,ss:2,intervaloQuadros:[START,END]});const a=document.createElement('a');a.id='download';a.href=globalThis.URL.createObjectURL(r.blob);a.download='clip.mp4';a.textContent='Download';document.body.append(a)});
 const wait=p.waitForEvent('download');await p.locator('#download').click();await(await wait).saveAs(FILE);
 }finally{await ctx.close()}}'''.replace('p.goto(URL)','p.goto('+json.dumps(url)+')').replace('START',str(start)).replace('END',str(end)).replace('saveAs(FILE)','saveAs('+json.dumps(str(part))+')')
            r=subprocess.run(CLI+['run-code',code],capture_output=True,text=True)
            (OUT/(name+'.log')).write_text(r.stdout+r.stderr)
            if r.returncode or '### Error' in r.stdout or not part.exists():raise RuntimeError(name+' export failed; inspect log')
        manifest=OUT/(name+'.txt');manifest.write_text(''.join("file '"+str(p)+"'\n" for p in chunks))
        subprocess.run([FFMPEG,'-v','error','-y','-f','concat','-safe','0','-i',str(manifest),'-c','copy','-movflags','+faststart',str(dest)],check=True)
    info=json.loads(subprocess.check_output([FFPROBE,'-v','error','-show_streams','-of','json',str(dest)]))['streams'][0]
    assert int(info['nb_frames'])==expected and info['width']==1280 and info['height']==720,name
    results.append({'id':name,'frames':expected,'fps':info['r_frame_rate'],'bytes':dest.stat().st_size})
    (OUT/('results-'+args.base+'.json' if args.base else 'results.json')).write_text(json.dumps(results,indent=2))
    print(f'{number}/{len(rows)} {name} OK',flush=True)
