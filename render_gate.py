#!/usr/bin/env python3
"""Renderiza os SETE angulos canonicos do gate visual, em qualquer aeronave.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<aeronave>/<X>.blend" \
        --python render_gate.py -- [largura] [amostras] [alvos...]

As cameras sao montadas na hora pelo padrao de frota (cameras_canonicas.py) e
NAO sao gravadas no .blend - o master fica intocado, o que permite rodar o gate
enquanto outra sessao edita a aeronave.

A pasta de saida e a do proprio .blend. Depois rode, fora do Blender:

    python3 verificacao_visual.py "<aeronave>"
"""
import os
import sys

import bpy

RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import cameras_canonicas  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
larg = int(argv[0]) if argv else 1600
amostras = int(argv[1]) if len(argv) > 1 else 96
alvos = argv[2:] or None

pasta = os.path.dirname(os.path.abspath(bpy.data.filepath))
print("[gate] %s -> %s  %dpx  %d amostras" % (os.path.basename(bpy.data.filepath),
                                              pasta, larg, amostras))
cameras_canonicas.renderizar(pasta, larg=larg, amostras=amostras, alvos=alvos)
print("[gate] FIM")
