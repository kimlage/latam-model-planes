#!/usr/bin/env python3
"""Contact sheet for the final visual verification of an aircraft model.

Usage: python3 verificacao_visual.py "airbus A320neo"

Joins the canonical renders (front, nose, side profile, hero, tail, low front,
head-on) into a single labelled image, for side-by-side checking against the
reference photos before calling the model finished. Part of the project's
standard flow (see README.md / aircraft pipeline).

The renders come from `render_gate.py`, which builds the seven cameras with the
fleet standard in `cameras_canonicas.py` and drops a `cameras_gate.json` next to
them. When that file is present each panel is labelled with the lens and the
distance that produced it, so the sheet carries its own camera provenance.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

VISTAS = [
    ("render_frontal.png", "CamFrontal", "FRONT 3/4 (nose proportion, windshield, engines)"),
    ("render_nariz.png", "CamNariz", "NOSE CLOSE-UP (glass, radome, door 1 outline)"),
    ("render_perfil.png", "CamPerfil", "SIDE PROFILE (compare with the reference photo)"),
    ("render_hero.png", "CamHero", "HERO 3/4"),
    ("render_cauda.png", "CamCauda", "TAIL (fin sash / hull wedge / registration)"),
    ("render_frente_baixa.png", "CamBarriga", "LOW FRONT (belly / fairing / gear / nacelles)"),
    ("render_headon.png", "CamHeadOn", "HEAD-ON (windshield V, frontal section)"),
]


def main(pasta):
    cams = {}
    p = os.path.join(pasta, "cameras_gate.json")
    if os.path.exists(p):
        try:
            cams = json.load(open(p)).get("cameras", {})
        except Exception:
            cams = {}

    thumbs = []
    tw = 800
    for fn, cam, label in VISTAS:
        p = os.path.join(pasta, fn)
        if not os.path.exists(p):
            print("faltando:", fn)
            continue
        c = cams.get(cam)
        if c:
            label = "%s  -  %.0f mm @ %.0f m" % (label, c["lens"], c["d"])
        im = Image.open(p).convert("RGB")
        th = int(im.height / im.width * tw)
        im = im.resize((tw, th))
        cab = Image.new("RGB", (tw, th + 34), (18, 18, 22))
        cab.paste(im, (0, 34))
        d = ImageDraw.Draw(cab)
        d.text((10, 9), label, fill=(255, 255, 255))
        thumbs.append(cab)
    if not thumbs:
        print("nenhum render em", pasta)
        return
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
