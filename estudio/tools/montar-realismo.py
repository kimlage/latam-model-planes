"""Assemble the complete render-realismo.js batch without another lossy encode.
Run from the repository root, after all seven partial exports have completed.
"""
from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FFMPEG = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
FFPROBE = shutil.which('ffprobe') or '/opt/homebrew/bin/ffprobe'
PARTS = ROOT / 'output/realismo-parts'
DEST = ROOT / 'estudio/loading/media/cinema'
EXPECTED = {'gru-decolagem':159, 'gru-a320-patio':300, 'sdsc-reboque':400,
            'sdsc-b789-interior':350, 'gru-b77w-aproximacao':600,
            'scl-b789-aproximacao':600, 'sdsc-a320-sobrevoo':600}

def probe(path):
    return json.loads(subprocess.check_output([FFPROBE, '-v','error',
        '-show_streams','-show_format','-of','json',str(path)]))

results = []
for name, count in EXPECTED.items():
    files = sorted(PARTS.glob(name + '-*.mp4'))
    assert files and sum(int(probe(p)['streams'][0]['nb_frames']) for p in files) == count, name
    manifest = PARTS / (name + '.txt')
    manifest.write_text(''.join("file '"+str(p).replace("'", "'\\''")+"'\n" for p in files))
    staged = PARTS / (name + '-complete.mp4')
    subprocess.run([FFMPEG,'-v','error','-y','-f','concat','-safe','0','-i',str(manifest),
        '-c','copy','-movflags','+faststart',str(staged)], check=True)
    info = probe(staged); stream = info['streams'][0]
    assert int(stream['nb_frames']) == count and stream['width'] == 1280 and stream['height'] == 720
    subprocess.run([FFMPEG,'-v','error','-i',str(staged),'-f','null','-'],check=True)
    backup = ROOT / 'output/renderfix-before' / (name + '.mp4')
    backup.parent.mkdir(parents=True,exist_ok=True)
    out = DEST / (name + '.mp4')
    if out.exists() and not backup.exists(): shutil.copy2(out,backup)
    staged.replace(out)
    subprocess.run([FFMPEG,'-v','error','-y','-ss','4','-i',str(out),'-frames:v','1',str(DEST/(name+'-poster.png'))],check=True)
    subprocess.run([FFMPEG,'-v','error','-y','-i',str(out),'-vf','fps=1/3,scale=480:270,tile=4x2',
        '-frames:v','1',str(ROOT/'output/playwright'/('renderfix-'+name+'.png'))],check=True)
    results.append(dict(name=name,frames=count,fps=stream['r_frame_rate'],duration=info['format']['duration'],bytes=out.stat().st_size))
(ROOT/'output/playwright/renderfix-videos.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
