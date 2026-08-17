#!/usr/bin/env python3
"""Folha de contato para verificação visual final de um modelo de aeronave.

Uso: python3 verificacao_visual.py "airbus A320neo"

Junta os renders canônicos (frontal, nariz, perfil, hero, cauda, frente baixa)
numa única imagem rotulada, para conferência lado a lado com as fotos de
referência antes de dar o modelo por pronto. Parte do fluxo padrão do projeto
(ver README.md / pipeline de aeronaves).
"""
import sys
import os
from PIL import Image, ImageDraw

VISTAS = [
    ("render_frontal.png", "FRONTAL 3/4 (ref: foto Airbus F-WNEO)"),
    ("render_nariz.png", "NARIZ CLOSE"),
    ("render_perfil.png", "PERFIL (ref: foto PT-TMN)"),
    ("render_hero.png", "HERO 3/4"),
    ("render_cauda.png", "CAUDA (sash/wrap)"),
    ("render_frente_baixa.png", "FRENTE BAIXA (barriga/motores)"),
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
