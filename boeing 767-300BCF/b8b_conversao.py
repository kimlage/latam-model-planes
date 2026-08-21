#!/usr/bin/env python3
"""Folha de conferencia do que faz desta aeronave uma CONVERSAO, e nao um
cargueiro de fabrica: a fileira de janelas tamponada, a porta 3 desativada e as
saidas overwing com placa.

    python3 "boeing 767-300BCF/b8b_conversao.py" [pasta_de_saida]

Empilha, para cada uma das tres regioes, o mesmo trecho recortado do render de
perfil e da fotografia de referencia, na mesma escala em x.

A SAIDA NAO VAI PARA O REPOSITORIO.  Dois tercos dela sao pixels de fotografia
de terceiros (CC BY-SA), e o NOTICE.md deste repositorio diz que essas fotos sao
citadas, nao distribuidas.  Por isso o padrao e o diretorio temporario do
sistema e nao a pasta da aeronave — quem quiser a folha roda o script, que e
versionado, contra as fotos que refs_fetch.py traz de volta.

O mapa foto->modelo de ref_N568LA_mia26.jpg e o publicado pela construcao do
-300F (spec_763f.json e b8f_comparacao.py):

    x_px = 66.0 + 91.4 * x_m
    y_px = ycrown(x_px) + (2.705 - z) * 94.1 ,  ycrown = 1520 + 0.006*(xp-700)

Ele tem um vies local conhecido de ~0.8 m perto do nariz e da cauda (a camera
esta mais perto do nariz que do leme), entao os recortes sao gerados com uma
folga generosa e a comparacao e de APARENCIA — o tampao le como contorno claro e
nao como vidro? a placa aparece? — e nao de estacao.  As estacoes vem da ACAP.
"""
import os
import sys
import tempfile

from PIL import Image, ImageDraw, ImageOps

BASE = os.path.dirname(os.path.abspath(__file__))
FOTO = os.path.join(BASE, "refs", "ref_N568LA_mia26.jpg")
RENDER = os.path.join(BASE, "render_perfil.png")

SX, SZ, X0PX = 91.4, 94.1, 66.0
VIES = 0.80          # deslocamento local do mapa, em metros, ver docstring


def ycrown(xp):
    return 1520.0 + 0.006 * (xp - 700.0)


REGIOES = [
    ("fileira de janelas TAMPONADA (x 26..34)", 26.0, 34.0, -0.2, 2.0),
    ("saidas overwing + placa EXIT INOPERATIVE (x 22.5..27)", 22.5, 27.0, -0.6, 2.0),
    ("porta 3 desativada, cortada pela cunha (x 41..46)", 41.0, 46.0, -1.0, 2.2),
]


def da_foto(x0, x1, z0, z1, alt_px):
    im = Image.open(FOTO).convert("RGB")
    a = int(X0PX + SX * (x0 + VIES))
    b = int(X0PX + SX * (x1 + VIES))
    t = int(ycrown(a) + (2.705 - z1) * SZ)
    u = int(ycrown(b) + (2.705 - z0) * SZ)
    c = ImageOps.autocontrast(im.crop((a, t, b, u)), cutoff=0.3)
    return c.resize((int(c.width * alt_px / c.height), alt_px), Image.LANCZOS)


def main(saida):
    if not os.path.exists(RENDER):
        sys.exit("falta render_perfil.png — rode o gate primeiro")
    ren = Image.open(RENDER).convert("RGB")
    tiras = []
    for rot, x0, x1, z0, z1 in REGIOES:
        f = da_foto(x0, x1, z0, z1, 320)
        # o render de perfil e ortografico o bastante no meio do casco para um
        # recorte proporcional servir de comparacao de aparencia
        rw = int(ren.width * (x1 - x0) / 55.5)
        rx = int(ren.width * x0 / 55.5)
        r = ren.crop((max(0, rx), 0, min(ren.width, rx + rw), ren.height))
        r = r.resize((f.width, int(r.height * f.width / max(r.width, 1))),
                     Image.LANCZOS)
        tiras.append((rot, f, r))
    w = max(t[1].width for t in tiras)
    h = sum(t[1].height + t[2].height + 44 for t in tiras) + 12
    sheet = Image.new("RGB", (w + 12, h), (12, 12, 15))
    d = ImageDraw.Draw(sheet)
    y = 8
    for rot, f, r in tiras:
        d.text((8, y), rot + "  —  FOTO N568LA (Duncan Kirk, CC BY 4.0)",
               fill=(255, 220, 90))
        y += 16
        sheet.paste(f, (6, y))
        y += f.height + 6
        d.text((8, y), "RENDER CC-CXE", fill=(150, 220, 255))
        y += 16
        sheet.paste(r, (6, y))
        y += r.height + 6
    out = os.path.join(saida, "conferencia_conversao.png")
    sheet.save(out)
    print("gravado", out, sheet.size)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else tempfile.gettempdir())
