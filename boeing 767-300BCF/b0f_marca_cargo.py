"""Etapa 0 (cargueiro) — importa a arte OFICIAL do lockup LATAM CARGO.

    /Applications/Blender.app/Contents/MacOS/Blender -b \
        "boeing 767-300BCF/B763BCF_LATAM_CARGO.blend" \
        --python "boeing 767-300BCF/b0f_marca_cargo.py"

Fonte: latam_cargo_logo.svg — 'File:LATAM Cargo logo.svg' do Wikimedia Commons,
DOMINIO PUBLICO. E a marca oficial de duas linhas ('LATAM' com 'CARGO' embaixo)
mais o simbolo; a regra da skill livery-latam e categorica: marca vem do vetor
oficial, nunca de fonte parecida. O 'CARGO' em especial nao existe em nenhum
SVG que o projeto ja tivesse.

Gera tres objetos de malha planos, escondidos, que o b5f rasteriza:
    CargoLockup_Simbolo_Indigo
    CargoLockup_Simbolo_Coral
    CargoLockup_Texto            ('LATAM' + 'CARGO' como UMA peca)

O SVG vem em Y para BAIXO (convencao de tela); as malhas sao espelhadas em Y
para que Y cresca para CIMA, que e o que encaixa()/marca_th() assumem.
"""
import os

import bpy

BASE = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(BASE, "latam_cargo_logo.svg")

# ---------------------------------------------------------------- limpeza
for nome in ("CargoLockup_Simbolo_Indigo", "CargoLockup_Simbolo_Coral",
             "CargoLockup_Texto"):
    ob = bpy.data.objects.get(nome)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
for c in list(bpy.data.collections):
    if c.name.startswith("latam_cargo_logo"):
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)

antes = set(bpy.data.objects.keys())
bpy.ops.import_curve.svg(filepath=SVG)
novos = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in antes]
print("[cargo] %d caminhos importados" % len(novos))

# ------------------------------------------------- curva -> malha + bbox
#
# NAO usar meshes.new_from_object() no resultado do importador de SVG.  O
# preenchimento de curva do Blender PERDE contornos: no 'CARGO' deste lockup ele
# comeu a perna do R e a palavra virava 'CAPGO' — visivel na textura antes de
# qualquer render.  O caminho do R tem duas subcurvas (o olho e o contorno
# externo) e a perna sai no contorno externo; o preenchedor de curva
# simplesmente descartou parte dele.
#
# O caminho certo e tesselar os contornos a mao com
# mathutils.geometry.tessellate_polygon, que e a funcao feita para poligono com
# furo: o primeiro contorno e a borda, os seguintes sao buracos, e ela devolve
# triangulos que respeitam os dois.
from mathutils import Vector  # noqa: E402
from mathutils.geometry import tessellate_polygon  # noqa: E402

dg = bpy.context.evaluated_depsgraph_get()
info = []
for ob in novos:
    if ob.type != 'CURVE':
        continue
    cu = ob.data
    cu.resolution_u = 24
    ev = ob.evaluated_get(dg)
    contornos = []
    for sp in ev.data.splines:
        if sp.type == 'BEZIER':
            # amostrar a bezier de verdade, nao so os nos
            pts = []
            n = len(sp.bezier_points)
            for i in range(n):
                a = sp.bezier_points[i]
                b = sp.bezier_points[(i + 1) % n]
                for k in range(cu.resolution_u):
                    t = k / cu.resolution_u
                    it = 1.0 - t
                    p = (it ** 3 * a.co + 3 * it * it * t * a.handle_right +
                         3 * it * t * t * b.handle_left + t ** 3 * b.co)
                    pts.append(Vector((p.x, p.y, 0.0)))
        else:
            pts = [Vector((p.co.x, p.co.y, 0.0)) for p in sp.points]
        if len(pts) >= 3:
            contornos.append(pts)
    if not contornos:
        continue
    # tessellate_polygon trata o PRIMEIRO contorno como borda e todos os
    # seguintes como furo.  O caminho 'LATAM' tem CINCO contornos externos (uma
    # letra cada) mais os olhos do A: jogar os cinco de uma vez faz a palavra
    # virar um borrao solido.  Entao primeiro separa-se em ILHAS por
    # aninhamento — contorno dentro de um numero PAR de outros e borda, dentro
    # de um numero IMPAR e furo da menor borda que o contem — e tessela-se cada
    # ilha sozinha.
    def _area(c):
        s = 0.0
        for i in range(len(c)):
            x1, y1 = c[i].x, c[i].y
            x2, y2 = c[(i + 1) % len(c)].x, c[(i + 1) % len(c)].y
            s += x1 * y2 - x2 * y1
        return abs(s) * 0.5

    def _dentro(p, c):
        dentro = False
        n = len(c)
        for i in range(n):
            x1, y1 = c[i].x, c[i].y
            x2, y2 = c[(i + 1) % n].x, c[(i + 1) % n].y
            if (y1 > p.y) != (y2 > p.y):
                xi = x1 + (p.y - y1) * (x2 - x1) / (y2 - y1)
                if p.x < xi:
                    dentro = not dentro
        return dentro

    areas = [_area(c) for c in contornos]
    pais = []
    for i, c in enumerate(contornos):
        pais.append([j for j, d in enumerate(contornos)
                     if j != i and areas[j] > areas[i] and _dentro(c[0], d)])
    ilhas = {}
    for i, c in enumerate(contornos):
        if len(pais[i]) % 2 == 0:
            ilhas.setdefault(i, [])
        else:
            pai = min(pais[i], key=lambda j: areas[j])
            ilhas.setdefault(pai, []).append(i)
    plano = []
    faces = []
    for raiz, furos in ilhas.items():
        grupos = [contornos[raiz]] + [contornos[j] for j in furos]
        base = len(plano)
        tris = tessellate_polygon(grupos)
        for g in grupos:
            plano.extend(g)
        faces.extend([(base + t[0], base + t[1], base + t[2]) for t in tris])
    me = bpy.data.meshes.new(ob.name + "_M")
    me.from_pydata([(p.x, p.y, 0.0) for p in plano], [], faces)
    me.update()
    novo = bpy.data.objects.new(ob.name + "_M", me)
    bpy.context.scene.collection.objects.link(novo)
    # aplicar a matriz do objeto importado nos vertices
    mw = ob.matrix_world.copy()
    for v in me.vertices:
        p = mw @ v.co
        v.co = (p.x, p.y, 0.0)
    novo.matrix_world.identity()
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    cor = "?"
    if ob.data.materials:
        c = ob.data.materials[0].diffuse_color
        cor = "coral" if c[0] > c[2] else "indigo"
    info.append((novo, min(xs), max(xs), min(ys), max(ys), cor))
    print("  %-16s x %8.3f..%8.3f  y %8.3f..%8.3f  %s"
          % (ob.name, min(xs), max(xs), min(ys), max(ys), cor))

for ob in novos:
    bpy.data.objects.remove(ob, do_unlink=True)

# ---------------------------------------------- classificar por posicao
# o simbolo e o bloco mais a ESQUERDA; o texto e todo o resto.
x_corte = min(i[2] for i in info if i[5] == "coral") + 1e-6
simbolo = [i for i in info if i[1] < x_corte]
texto = [i for i in info if i[1] >= x_corte]
print("[cargo] simbolo: %d caminhos, texto: %d caminhos" % (len(simbolo), len(texto)))


def juntar(pecas, nome):
    bpy.ops.object.select_all(action='DESELECT')
    obs = [p[0] for p in pecas]
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    fin = bpy.context.view_layer.objects.active
    fin.name = nome
    fin.data.name = nome
    fin.hide_viewport = True
    fin.hide_render = True
    xs = [v.co.x for v in fin.data.vertices]
    ys = [v.co.y for v in fin.data.vertices]
    print("[cargo] %-30s x %.3f..%.3f  y %.3f..%.3f  razao %.3f"
          % (nome, min(xs), max(xs), min(ys), max(ys),
             (max(xs) - min(xs)) / max(max(ys) - min(ys), 1e-9)))
    return fin


juntar([p for p in simbolo if p[5] == "indigo"], "CargoLockup_Simbolo_Indigo")
juntar([p for p in simbolo if p[5] == "coral"], "CargoLockup_Simbolo_Coral")
juntar(texto, "CargoLockup_Texto")

bpy.ops.wm.save_mainfile()
print("SALVO", bpy.data.filepath)
