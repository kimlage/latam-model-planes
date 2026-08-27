#!/usr/bin/env python3
"""UV da coroa/quilha dos 787 — os dois vertices errados de cada anel.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<pasta>/<MASTER>.blend" \
        --python "boeing 787-9/uv_coroa_787.py" -- [medir|construir]

QA-BACKLOG "787 family: the hull's crown and keel carry the wrong UV": em
ambos os 787 cada anel da gaiola tem v = i/32 exato, EXCETO o vertice da
coroa (0.50712 em vez de 0.5) e o da quilha (0.99288 em vez de 1.0). Na
superficie avaliada o plano de simetria cai em v=0.5044 — 4.5 linhas de
textura fora do centro; foi isso que pos o montante central do para-brisa
0.045 m a bombordo, partido por uma fresta de 0.018 m de casco branco, e
distorce ~0.7% de circunferencia em +-11 graus da coroa e da quilha (a
echarpe traseira cruza a coroa).

A correcao e so nos LOOPS UV do casco: v em (0.50712 +-0.001) -> 0.5 e
v em (0.99288 +-0.001) -> 1.0. Nenhum vertice 3D muda. Depois desta
correcao, `refazer_marcas.py` + `reparar_echarpe.py` (sequencia do
REBUILD.md) repintam as marcas — o diff de textura esperado concentra-se
nas bandas da coroa/quilha (as marcas que cruzam v 0.5, sobretudo a
echarpe), ate ~5 linhas de texel.

Idempotente: na segunda rodada nada esta na janela de captura.
"""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODO = argv[0] if argv else "construir"
D = bpy.data
log = lambda *a: print("[uv787]", *a)

hull = D.objects["Fuselagem"]
me = hull.data
uv = me.uv_layers.active.data

n_c = n_k = 0
vals = {}
for lo in uv:
    v = lo.uv[1]
    vals[round(v, 5)] = vals.get(round(v, 5), 0) + 1
    if abs(v - 0.50712) < 1e-3:
        n_c += 1
        if MODO == "construir":
            lo.uv[1] = 0.5
    elif abs(v - 0.99288) < 1e-3:
        n_k += 1
        if MODO == "construir":
            lo.uv[1] = 1.0

log("loops v~0.50712:", n_c, " v~0.99288:", n_k)
sus = {k: n for k, n in vals.items() if 0.5 < k < 0.508 or 0.99 < k < 0.9999}
log("valores na vizinhanca:", dict(sorted(sus.items()))
    if len(sus) < 12 else ("%d distintos" % len(sus)))

if MODO == "construir" and (n_c or n_k):
    me.update()
    bpy.ops.wm.save_mainfile()
    log("SALVO", bpy.data.filepath)
else:
    log("nada a fazer" if not (n_c or n_k) else "modo medir")
