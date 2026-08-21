#!/usr/bin/env python3
"""Re-importa um arquivo exportado e mede o que voltou. Roda DENTRO do Blender.

    blender -b --factory-startup --python export/reimportar.py -- <arquivo>

`verificar_glb.py` le o container no nivel do byte, mas so sabe ler GLB - e o
GLB e o unico dos quatro formatos cujo interior e legivel sem uma biblioteca.
Para USDZ, FBX e OBJ a unica prova honesta e a viagem de ida e volta: abrir o
arquivo num Blender vazio e medir o que apareceu.

E a viagem de volta e que pega o erro de eixo. Blender e +Z para cima; glTF, USD
e FBX sao +Y. Um arquivo com o eixo errado abre sem reclamar e so fica DEITADO,
o que nenhum contador de triangulos percebe. Aqui a aeronave volta para o frame
do Blender e as tres medidas tem de cair onde o repositorio as deixou:

    X = comprimento   Y = envergadura   Z = altura   e min(Z) = 0 (rodas no chao)

Uma linha `ROUNDTRIP` por arquivo, lida por `export_frota.py --reimportar`.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

IMPORTADORES = {
    ".glb": lambda c: bpy.ops.import_scene.gltf(filepath=c),
    ".gltf": lambda c: bpy.ops.import_scene.gltf(filepath=c),
    ".fbx": lambda c: bpy.ops.import_scene.fbx(filepath=c),
    # o exportador escreveu com up_axis=Y; o importador precisa saber disso,
    # porque o .obj nao carrega o eixo dentro do arquivo
    ".obj": lambda c: bpy.ops.wm.obj_import(filepath=c, up_axis="Y",
                                            forward_axis="NEGATIVE_Z"),
    ".usdz": lambda c: bpy.ops.wm.usd_import(filepath=c),
    ".usdc": lambda c: bpy.ops.wm.usd_import(filepath=c),
    ".usda": lambda c: bpy.ops.wm.usd_import(filepath=c),
}


def medir(caminho):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ext = os.path.splitext(caminho)[1].lower()
    if ext not in IMPORTADORES:
        return "ROUNDTRIP %s SEM_IMPORTADOR" % os.path.basename(caminho)
    try:
        IMPORTADORES[ext](caminho)
    except Exception as exc:                       # noqa: BLE001 - queremos o texto
        return "ROUNDTRIP %s IMPORT_FALHOU %s" % (os.path.basename(caminho), exc)

    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    n = tris = 0
    mats, imgs = set(), set()
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        n += 1
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        if me:
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
            ev.to_mesh_clear()
        for ms in ob.material_slots:
            if not ms.material:
                continue
            mats.add(ms.material.name)
            if ms.material.node_tree:
                for nd in ms.material.node_tree.nodes:
                    if nd.type == "TEX_IMAGE" and nd.image is not None:
                        imgs.add(nd.image.name)
    if not n:
        return "ROUNDTRIP %s VAZIO" % os.path.basename(caminho)
    d = [hi[i] - lo[i] for i in range(3)]
    return ("ROUNDTRIP %s objs=%d tris=%d mats=%d texs=%d X=%.3f Y=%.3f Z=%.3f minZ=%.4f"
            % (os.path.basename(caminho), n, tris, len(mats), len(imgs),
               d[0], d[1], d[2], lo[2]))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for caminho in argv:
        print(medir(caminho))


if __name__ == "__main__":
    main()
