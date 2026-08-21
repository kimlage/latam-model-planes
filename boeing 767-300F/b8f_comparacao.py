#!/usr/bin/env python3
"""Reprojeta a foto de referencia no MESMO mapa do render ortografico e empilha
os dois, para comparar a pintura medida contra a pintura pintada.

    python3 "boeing 767-300F/b8f_comparacao.py"

Consome:
    render_orto_perfil.png   (b7f_orto.py: x 0..56 m, 40 px/m, z 12..-5)
    refs/ref_N568LA_mia26.jpg

O mapa foto->modelo e o mesmo que produziu todos os numeros de
spec_763f.json -> livery_n536la, e esta escrito la:
    x_px = 66.0 + 91.4 * x_m
    y_px = ycrown(x_px) + (2.705 - z) * 94.1
    ycrown(xp) = 1520.0 + 0.006 * (xp - 700.0)
A escala em z sai da ponta da deriva (z=11.15) contra a crista (z=2.705); a de x
sai da inclinacao medida do BA reto da deriva contra a do modelo (2.9% de
encurtamento por guinada).  A ponta da deriva prevista em x=52.7 cai em 4883 px
contra 4880 medidos.

Sai comparacao_perfil.png (foto reprojetada em cima, render embaixo) e
comparacao_porta_conves.png (recorte da porta de conves principal, render x a
foto de controle da UPS, a unica em que a aresta da porta fechada resolve).
"""
import os

import numpy as np
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
PPM = 40.0
X0M, X1M = 0.0, 56.0
Z1M, Z0M = 12.0, -5.0
Wc = int((X1M - X0M) * PPM)
Hc = int((Z1M - Z0M) * PPM)

SX, SZ, X0PX = 91.4, 94.1, 66.0


def ycrown(xp):
    return 1520.0 + 0.006 * (xp - 700.0)


def reprojeta(foto):
    im = Image.open(foto).convert("RGB")
    a = np.asarray(im)
    j, i = np.mgrid[0:Hc, 0:Wc]
    xm = X0M + i / PPM
    zm = Z1M - j / PPM
    xp = X0PX + SX * xm
    yp = ycrown(xp) + (2.705 - zm) * SZ
    xi = np.clip(np.round(xp).astype(int), 0, a.shape[1] - 1)
    yi = np.clip(np.round(yp).astype(int), 0, a.shape[0] - 1)
    out = a[yi, xi]
    fora = (xp < 0) | (xp >= a.shape[1]) | (yp < 0) | (yp >= a.shape[0])
    out[fora] = (20, 20, 24)
    return Image.fromarray(out)


def sobre_fundo(p, fundo=(20, 20, 24)):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, fundo + (255,))
    return Image.alpha_composite(bg, im).convert("RGB")


def main():
    foto = reprojeta(os.path.join(BASE, "refs", "ref_N568LA_mia26.jpg"))
    rp = os.path.join(BASE, "render_orto_perfil.png")
    if not os.path.exists(rp):
        print("falta render_orto_perfil.png — rode b7f_orto.py")
        return
    ren = sobre_fundo(rp)
    ren = ren.resize((Wc, int(Wc * ren.height / ren.width)))
    # o render cobre z 12..-5 em 17 m; a foto tambem.  Se as alturas nao baterem,
    # e porque a resolucao do render mudou; realinha por altura.
    if ren.height != Hc:
        ren = ren.resize((Wc, Hc))
    sheet = Image.new("RGB", (Wc, foto.height + ren.height + 36), (10, 10, 12))
    sheet.paste(foto, (0, 12))
    sheet.paste(ren, (0, foto.height + 24))
    d = ImageDraw.Draw(sheet)
    d.text((8, 2), "FOTO N568LA (Duncan Kirk, CC BY 4.0) reprojetada — 40 px/m",
           fill=(255, 255, 255))
    d.text((8, foto.height + 14), "RENDER ortografico N536LA — mesma escala",
           fill=(255, 255, 255))
    # reguas de estacao a cada 5 m
    for x in range(0, 56, 5):
        for y0 in (12, foto.height + 24):
            d.line([(x * PPM, y0), (x * PPM, y0 + 10)], fill=(255, 0, 255))
    out = os.path.join(BASE, "comparacao_perfil.png")
    sheet.save(out)
    print("gravado", out, sheet.size)


if __name__ == "__main__":
    main()
