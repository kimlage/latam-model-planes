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
import json
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


def mapa_do_render(ren):
    """px/m e a linha da crista do render de perfil, LIDOS DE cameras_gate.json.

    Nao se mede a escala na silhueta: o gate ja grava a provenienciada camera ao
    lado dos renders — distancia, lente e a largura do quadro no plano do alvo.
    Com isso o mapa e exato em vez de estimado, e continua valendo se alguem
    reenquadrar o gate.  A camera de perfil e perpendicular ao eixo, entao o
    quadro e simetrico em torno do alvo; a 165 m sobre um casco de 5 m de
    profundidade a diferenca de escala entre a pele proxima e o plano do eixo e
    de 1.5%, o que basta para uma comparacao de APARENCIA.
    """
    cam = json.load(open(os.path.join(BASE, "cameras_gate.json")))["cameras"]["CamPerfil"]
    ppm = ren.width / cam["W"]                       # px por metro no plano do eixo
    x_centro, z_centro = cam["alvo"][0], cam["alvo"][2]
    x0_px = ren.width / 2.0 - x_centro * ppm         # coluna de x = 0
    y_crista = ren.height / 2.0 - (2.705 - z_centro) * ppm
    return ppm, y_crista, x0_px


def do_render(ren, ppm, y_crista, x0_px, x0, x1, z0, z1, alt_px):
    a = int(round(x0_px + x0 * ppm))
    b = int(round(x0_px + x1 * ppm))
    t = int(round(y_crista + (2.705 - z1) * ppm))
    u = int(round(y_crista + (2.705 - z0) * ppm))
    a, b = max(0, min(a, b)), min(ren.width, max(a, b))
    t, u = max(0, min(t, u)), min(ren.height, max(t, u))
    if b - a < 4 or u - t < 4:
        return None
    c = ren.crop((a, t, b, u))
    return c.resize((int(c.width * alt_px / c.height), alt_px), Image.LANCZOS)


def main(saida):
    if not os.path.exists(RENDER):
        sys.exit("falta render_perfil.png — rode o gate primeiro")
    ren = Image.open(RENDER).convert("RGB")
    ppm, y_crista, x0_px = mapa_do_render(ren)
    print("render: %.2f px/m, crista na linha %d, nariz na coluna %d"
          % (ppm, y_crista, x0_px))
    tiras = []
    for rot, x0, x1, z0, z1 in REGIOES:
        f = da_foto(x0, x1, z0, z1, 300)
        r = do_render(ren, ppm, y_crista, x0_px, x0, x1, z0, z1, 300)
        if r is None:
            continue
        tiras.append((rot, f, r))
    if not tiras:
        sys.exit("nada recortado — confira o mapa do render")
    w = max(max(t[1].width, t[2].width) for t in tiras)
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
