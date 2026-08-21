"""Renderiza os SETE angulos canonicos do gate visual do 767-300BCF.

  /Applications/Blender.app/Contents/MacOS/Blender -b "boeing 767-300BCF/B763BCF_LATAM_CARGO.blend" \
      --python "boeing 767-300BCF/b6_render.py" -- [largura] [amostras] [alvos...]

Este arquivo e um atalho: as cameras vem do PADRAO DE FROTA na raiz
(cameras_canonicas.py), montadas na hora e nao gravadas no .blend. Antes cada
aeronave carregava a sua propria lista de cameras e o gate julgava cada uma com
uma lente diferente - foi assim que teleobjetiva virou grande-angular a 18 m.
Equivalente a rodar `render_gate.py` na raiz.
"""
import os
import sys

import bpy

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import cameras_canonicas  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
larg = int(argv[0]) if argv else 1600
amostras = int(argv[1]) if len(argv) > 1 else 96
alvos = argv[2:] or None

cameras_canonicas.renderizar(os.path.dirname(os.path.abspath(__file__)),
                             larg=larg, amostras=amostras, alvos=alvos)
print("[gate] FIM")
