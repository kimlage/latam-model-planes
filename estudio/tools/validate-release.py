"""Validate all delivered videos and produce temporal contact sheets for review."""
from pathlib import Path
from PIL import Image, ImageDraw
import argparse,json,subprocess,shutil
parser=argparse.ArgumentParser();parser.add_argument("--group");args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'output/release-review';out.mkdir(exist_ok=True)
rows=json.loads((ROOT/'output/release-scenes/scenes.json').read_text());groups={}
if args.group: rows=[r for r in rows if r['config']['aeroporto']+'-'+r['config']['situacao']==args.group]
for r in rows:
 p=ROOT/'output/release-videos'/(r['id']+'.mp4');assert p.is_file(),p
 check=subprocess.run([shutil.which('ffmpeg') or 'ffmpeg','-v','error','-i',str(p),'-f','null','-'],capture_output=True,text=True)
 assert check.returncode==0 and not check.stderr,(r['id'],check.stderr)
 strip=Image.new('RGB',(960,204),'#12151c');draw=ImageDraw.Draw(strip);draw.text((8,4),r['id'],fill='white')
 for i,u in enumerate([.15,.5,.85]):
  png=out/(r['id']+f'-{i}.png');t=r['document']['linha']['duracao']*u
  subprocess.run([shutil.which('ffmpeg') or 'ffmpeg','-v','error','-y','-ss',str(t),'-i',str(p),'-frames:v','1','-vf','scale=320:180',str(png)],check=True)
  strip.paste(Image.open(png),(i*320,24))
 c=r['config'];groups.setdefault(c['aeroporto']+'-'+c['situacao'],[]).append(strip)
for group,strips in groups.items():
 sheet=Image.new('RGB',(960,204*len(strips)),'#12151c')
 for i,strip in enumerate(strips):sheet.paste(strip,(0,i*204))
 sheet.save(out/(group+'.jpg'),quality=90)
(out/('results-'+args.group+'.json' if args.group else 'results.json')).write_text(json.dumps({'decoded':len(rows),'framesReviewedPerVideo':3,'contactSheets':list(groups)},indent=2))
print('Decoded',len(rows),'videos; contact sheets:',list(groups))
