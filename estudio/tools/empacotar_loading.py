#!/usr/bin/env python3
"""Build loading media from the Studio's trusted, locally exported PNG sequence."""
import argparse
import pathlib
import shutil
import subprocess
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sequencia', type=pathlib.Path)
    args = parser.parse_args()
    dest = pathlib.Path(__file__).resolve().parents[1] / 'loading' / 'media'
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='latam-loading-') as folder:
        folder = pathlib.Path(folder)
        with zipfile.ZipFile(args.sequencia) as archive:
            names = [f'quadro_{i:04d}.png' for i in range(100)]
            if sorted(n for n in archive.namelist() if n.endswith('.png')) != names:
                raise ValueError('Expected exactly 100 frames exported at 25 fps / 4 s')
            for name in names + ['ATRIBUICAO.txt']:
                (folder / name).write_bytes(archive.read(name))
        subprocess.run([
            shutil.which('ffmpeg') or 'ffmpeg', '-v', 'error',
            '-f', 'lavfi', '-i', 'color=c=0x10002b:s=800x450:r=25:d=4',
            '-framerate', '25', '-i', str(folder / 'quadro_%04d.png'),
            '-filter_complex', '[0:v][1:v]overlay=shortest=1:format=auto,scale=out_color_matrix=bt709,format=yuv420p[v]',
            '-map', '[v]', '-frames:v', '100', '-an', '-c:v', 'libx264',
            '-preset', 'slow', '-crf', '17', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart',
            '-metadata', 'comment=LATAM fleet 3D replicas — Kim Lage — CC BY 4.0. LATAM/Airbus/Boeing trademarks belong to their holders. See NOTICE.md.',
            '-y', str(dest / 'flight.mp4'),
        ], check=True)
        shutil.copyfile(folder / names[0], dest / 'poster.png')
        shutil.copyfile(folder / 'ATRIBUICAO.txt', dest / 'ATRIBUICAO.txt')
    print(dest)


if __name__ == '__main__':
    main()
