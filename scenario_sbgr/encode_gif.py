#!/usr/bin/env python3
"""Encode a rendered frame directory into a verified GIF.

    python3 scenario_sbgr/encode_gif.py --dir scenario_sbgr/frames_tour \\
        --out scenario_sbgr/sbgr_base_v2.gif --width 640 --colors 64

The knobs are the project's proven ones: 25 fps, lanczos scale, a single
palettegen palette, paletteuse with dither=none (dithering crawls between
frames of an aerial and costs bytes), and the verification the memory notes
mandate: PIL frame-by-frame - every frame must carry a 40 ms delay and the
count must match the directory. NEVER the byte scan (phantom 0x21F904
matches inside LZW data). Hard gate: <= 15 MB.
"""
import argparse
import os
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--colors", type=int, required=True)
    ap.add_argument("--fps", type=int, default=25)
    a = ap.parse_args()

    frames = sorted(f for f in os.listdir(a.dir) if f.endswith(".png"))
    if not frames:
        raise SystemExit("no frames in " + a.dir)
    seq = os.path.join(a.dir, "%04d.png")
    pal = a.out + ".pal.png"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
         "-i", seq, "-vf",
         "scale=%d:-1:flags=lanczos,palettegen=max_colors=%d"
         % (a.width, a.colors), pal], check=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
         "-i", seq, "-i", pal, "-lavfi",
         "scale=%d:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=none"
         % a.width, a.out], check=True)
    os.remove(pal)

    from PIL import Image, ImageSequence
    im = Image.open(a.out)
    durs = [fr.info.get("duration") for fr in ImageSequence.Iterator(im)]
    want = round(1000.0 / a.fps)
    bad = [i for i, d in enumerate(durs) if d != want]
    size = os.path.getsize(a.out)
    print("%s: %d frames, %.1f s, %dx%d, %.2f MB"
          % (os.path.basename(a.out), len(durs), len(durs) / a.fps,
             im.size[0], im.size[1], size / 1e6))
    ok = True
    if len(durs) != len(frames):
        print("!! frame count %d != %d rendered" % (len(durs), len(frames)))
        ok = False
    if bad:
        print("!! %d frames without a %d ms delay (first at %d)"
              % (len(bad), want, bad[0]))
        ok = False
    else:
        print("every frame %d ms by PIL" % want)
    if size > 15 * 1024 * 1024:
        print("!! over the 15 MB gate")
        ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
