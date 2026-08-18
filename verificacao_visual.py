#!/usr/bin/env python3
"""Contact sheet for the final visual verification of an aircraft model.

Usage: python3 verificacao_visual.py "airbus A320neo"

Joins the canonical renders (front, nose, side profile, hero, tail, low front)
into a single labelled image, for side-by-side checking against the reference
photos before calling the model finished. Part of the project's standard flow
(see README.md / aircraft pipeline).
"""
import sys
import os
from PIL import Image, ImageDraw

VISTAS = [
    ("render_frontal.png", "FRONT 3/4 (ref: photo Airbus F-WNEO)"),
    ("render_nariz.png", "NOSE CLOSE-UP"),
    ("render_perfil.png", "SIDE PROFILE (ref: photo PT-TMN)"),
    ("render_hero.png", "HERO 3/4"),
    ("render_cauda.png", "TAIL (fin sash / hull wedge)"),
    ("render_frente_baixa.png", "LOW FRONT (belly / engines)"),
]

def main(pasta):
    thumbs = []
    tw = 800
    for fn, label in VISTAS:
        p = os.path.join(pasta, fn)
        if not os.path.exists(p):
            print("faltando:", fn)
            continue
        im = Image.open(p).convert("RGB")
        th = int(im.height / im.width * tw)
        im = im.resize((tw, th))
        cab = Image.new("RGB", (tw, th + 34), (18, 18, 22))
        cab.paste(im, (0, 34))
        d = ImageDraw.Draw(cab)
        d.text((10, 9), label, fill=(255, 255, 255))
        thumbs.append(cab)
    cols = 2
    rows = (len(thumbs) + cols - 1) // cols
    cw = max(t.width for t in thumbs)
    chs = [max(t.height for t in thumbs[r*cols:(r+1)*cols]) for r in range(rows)]
    sheet = Image.new("RGB", (cw*cols + 12, sum(chs) + 12*(rows+1)), (10, 10, 12))
    y = 12
    for r in range(rows):
        for c in range(cols):
            i = r*cols + c
            if i < len(thumbs):
                sheet.paste(thumbs[i], (c*cw + 6, y))
        y += chs[r] + 12
    out = os.path.join(pasta, "verificacao_visual.png")
    sheet.save(out)
    print("folha de contato:", out)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "airbus A320neo")
