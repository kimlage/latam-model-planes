"""Bounded local PNG-sequence to H.264 conversion. No shell or external service."""
import io
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

MAX_BYTES = 512 * 1024 * 1024
FPS = {5, 10, 12.5, 20, 25}


def converter(payload, fps, executable=None):
    if fps not in FPS:
        raise ValueError('Taxa de quadros inválida.')
    executable = executable or shutil.which('ffmpeg')
    if not executable:
        raise RuntimeError('ffmpeg não está disponível neste servidor. Use PNG seq.')
    if len(payload) > MAX_BYTES:
        raise ValueError('Sequência excede 512 MB. Reduza a resolução ou a duração.')
    with zipfile.ZipFile(io.BytesIO(payload)) as archive, tempfile.TemporaryDirectory(prefix='latam-video-') as folder:
        entries = archive.infolist()
        if len(entries) > 15002 or sum(e.file_size for e in entries) > MAX_BYTES:
            raise ValueError('Sequência muito grande.')
        frames = sorted((e.filename for e in entries if re.fullmatch(r'quadro_\d{4,5}\.png',e.filename)),
                        key=lambda name:int(name[7:-4]))
        allowed = set(frames) | {'ATRIBUICAO.txt','sequencia.json'}
        if len(entries) != len(set(e.filename for e in entries)) or any(e.filename not in allowed for e in entries):
            raise ValueError('Conteúdo inesperado no arquivo de quadros.')
        if not frames or len(frames) > 600*fps:
            raise ValueError('A sequência precisa ter entre um quadro e dez minutos.')
        dims = None
        for i, name in enumerate(frames):
            if name != f'quadro_{i:04d}.png':
                raise ValueError('Os quadros devem ser consecutivos, começando em zero.')
            data = archive.read(name)
            if data[:8] != b'\x89PNG\r\n\x1a\n' or len(data)<24 or data[12:16]!=b'IHDR':
                raise ValueError('Quadro PNG inválido.')
            size = struct.unpack('>II',data[16:24])
            if min(size)<2 or max(size)>4096 or size[0]*size[1]>8388608 or any(n%2 for n in size):
                raise ValueError('O MP4 exige dimensões pares, até 4096 px e 8 MP.')
            if dims and dims!=size:
                raise ValueError('Os quadros devem ter o mesmo tamanho.')
            dims=size
            (Path(folder)/f'quadro_{i:04d}.png').write_bytes(data)
        attribution = archive.read('ATRIBUICAO.txt').decode('utf-8')[:16000] if 'ATRIBUICAO.txt' in archive.namelist() else ''
        target=Path(folder)/'video.mp4'
        cmd=[executable,'-hide_banner','-loglevel','error','-nostdin',
             '-framerate',str(fps),'-i',str(Path(folder)/'quadro_%04d.png'),
             '-frames:v',str(len(frames)),'-an','-c:v','libx264','-preset','fast',
             '-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',
             '-metadata','comment='+attribution,str(target)]
        p=subprocess.run(cmd,capture_output=True,timeout=180,check=False)
        if p.returncode:
            raise RuntimeError('Falha ao codificar o vídeo: '+p.stderr.decode('utf-8',errors='replace')[-1500:])
        return target.read_bytes()
