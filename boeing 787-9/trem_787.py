#!/usr/bin/env python3
"""Estancia dos 787 — a altura publicada, as pernas, o motor e a carenagem.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<pasta>/<MASTER>.blend" \
        --python "boeing 787-9/trem_787.py" -- [medir|construir]

QA-BACKLOG "787-8 height 16.48 vs 16.92 published". Medido em 2026-08-27
contra o APR do repo (D6-58333 REV P):

- A DERIVA ESTA CERTA. Na side view do -9 (p21, 600 dpi, calibrada pela
  PROPRIA cota de altura 55'10" = 17.02 m entre setas: 49.35 px/m; a cota
  19'6" = 5.94 m da 49.35 tambem), quilha->topo-da-deriva mede 14.47 m; o
  modelo tem 14.57 (topo 11.60, quilha -2.97). A suspeita do backlog
  ("identical fin top") apontava para a deriva; a medida a exonera.
- AS PERNAS E QUE SAO CURTAS: roda em -4.88 -> folga da quilha 1.91 m; o
  desenho da 2.55 +-0.05 (linha de solo na seta da cota de altura, linha da
  quilha na seta da cota 5.94). Alvo por tipo, ancorado na ALTURA PUBLICADA
  com o modelo nivelado: solo(-9) = topo 11.60 - 17.02 = -5.42;
  solo(-8) = 11.60 - 16.92 = -5.32 (a diferenca real entre os tipos e de
  atitude estatica, nao de estrutura — os dois usam a mesma perna).
- O MOTOR PENDURADO ALTO: fundo da nacele -4.20 = 1.23 abaixo da quilha; as
  cotas publicadas F (motor GEnx 0.69..0.76 no -9) + folga da quilha dao
  1.70..1.86. Alvo 1.75 -> fundo -4.72, descida de 0.52 com o pylon
  ESTICADO (so os vertices que descem ao nacelle). Sem isso, esticar a
  perna deixaria o motor flutuando a 1.2 m da pista — regressao visivel.
  Residuo declarado: no -8 nivelado o F resultante (0.60) fica 0.14 abaixo
  do minimo publicado do -8 (0.74–1.07, envelope de atitude maior).
- A CARENAGEM VENTRAL 0.33 FUNDA DEMAIS: fundo -3.994 = 1.02 abaixo da
  quilha; a cota D (ponto mais baixo da fuselagem central na figura 2.3,
  1.75..1.85 no -9) + folga da quilha dao 0.65..0.75. Alvo -3.67 (remap so
  dos vertices abaixo de z -3.0, mesmo metodo do trem_familia dos A320).

Nada de casco, marcas ou textura muda aqui — as pontes das marcas leem
secoes que este script nao toca. Idempotente (alvos absolutos re-medidos).
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODO = argv[0] if argv else "construir"
D = bpy.data
PASTA = os.path.dirname(os.path.abspath(bpy.data.filepath))
TAG = {"boeing 787-8": "b788", "boeing 787-9": "b789"}.get(os.path.basename(PASTA))
if TAG is None:
    raise SystemExit("pasta nao reconhecida: %s" % PASTA)
log = lambda *a: print("[trem787]", *a)

SOLO = {"b788": -5.32, "b789": -5.42}[TAG]
FUNDO_NACELE = -4.72          # quilha -2.97 - 1.75 (F publicado + folga da quilha)
FUNDO_CARENAGEM = -3.67       # quilha - 0.70 (cota D + folga da quilha)
Z0_CARENAGEM = -3.00


def caixa(ob):
    ws = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return (min(w.x for w in ws), max(w.x for w in ws),
            min(w.z for w in ws), max(w.z for w in ws))


def mover_verts(ob, cond, dz):
    mw = ob.matrix_world
    inv = mw.inverted()
    n = 0
    for v in ob.data.vertices:
        w = mw @ v.co
        if cond(w):
            v.co = inv @ Vector((w.x, w.y, w.z + dz))
            n += 1
    ob.data.update()
    return n


def escala_z(ob, z_fixo, fator):
    mw = ob.matrix_world
    inv = mw.inverted()
    for v in ob.data.vertices:
        w = mw @ v.co
        v.co = inv @ Vector((w.x, w.y, z_fixo + (w.z - z_fixo) * fator))
    ob.data.update()


rodas = [o for o in D.objects if o.type == 'MESH' and 'Roda' in o.name]
fundo_roda = min(caixa(o)[2] for o in rodas)
nacelle = D.objects['Motor_Nacelle_D']
fundo_nac = caixa(nacelle)[2]
caren = D.objects['BellyFairing']
fundo_car = caixa(caren)[2]
deriva_top = max((D.objects['Deriva'].matrix_world @ v.co).z for v in D.objects['Deriva'].data.vertices)
log("ANTES: roda %.3f nacele %.3f carenagem %.3f deriva %.3f altura %.3f"
    % (fundo_roda, fundo_nac, fundo_car, deriva_top, deriva_top - fundo_roda))
if MODO == "medir":
    raise SystemExit(0)

dg = SOLO - fundo_roda            # extensao da perna (negativo = desce)
de = FUNDO_NACELE - fundo_nac     # descida do motor

# ------------------------------------------------------------------ 1) PERNAS
TRANSLADA = ("TremNariz_RodaD", "TremNariz_RodaE", "TremNariz_Eixo",
             "TremNariz_TesouraB",
             "TremP_RodaD-76-75", "TremP_RodaD-7675", "TremP_RodaD76-75", "TremP_RodaD7675",
             "TremP_RodaE-76-75", "TremP_RodaE-7675", "TremP_RodaE76-75", "TremP_RodaE7675",
             "TremPrincipal_EixoD-76", "TremPrincipal_EixoD76",
             "TremPrincipal_EixoE-76", "TremPrincipal_EixoE76",
             "TremPrincipal_BogieD", "TremPrincipal_BogieE",
             "TremPrincipal_BraceD", "TremPrincipal_BraceE",
             "TremP_TesouraDB", "TremP_TesouraEB")
if abs(dg) > 1e-4:
    for nm in TRANSLADA:
        ob = D.objects.get(nm)
        if ob is not None:
            ob.location.z += dg
    # pistoes ESTICAM (o topo fica dentro do cilindro)
    for nm, corte in (("TremNariz_Pistao", -4.00), ("TremP_PistaoD", -3.00), ("TremP_PistaoE", -3.00)):
        ob = D.objects.get(nm)
        if ob is not None:
            n = mover_verts(ob, lambda w: w.z < corte, dg)
            log("pistao %s: %d verts abaixo de %.1f descem %.3f" % (nm, n, corte, dg))
    # tesouras A esticam ate encontrar as B transladadas
    for nm in ("TremNariz_TesouraA", "TremP_TesouraDA", "TremP_TesouraEA"):
        ob = D.objects.get(nm)
        if ob is None:
            continue
        _, _, zb, zt = caixa(ob)
        alt = zt - zb
        fator = (alt - dg) / alt          # dg<0 -> fator>1
        escala_z(ob, zt, fator)
        log("tesoura %s: escala z x%.2f (topo fixo %.2f)" % (nm, fator, zt))
    log("pernas: %.3f" % dg)

# ------------------------------------------------------------------ 2) MOTORES
if abs(de) > 1e-4:
    for ob in D.objects:
        if ob.type != 'MESH' or not ob.name.startswith("Motor_"):
            continue
        if "Pylon" in ob.name:
            n = mover_verts(ob, lambda w: w.z < -0.50, de)
            log("pylon %s: %d verts esticados %.3f" % (ob.name, n, de))
        else:
            ob.location.z += de
    log("motores: %.3f" % de)

# ---------------------------------------------------------------- 3) CARENAGEM
s = (FUNDO_CARENAGEM - Z0_CARENAGEM) / (fundo_car - Z0_CARENAGEM)
if abs(s - 1.0) > 1e-4:
    n = 0
    mw = caren.matrix_world
    inv = mw.inverted()
    for v in caren.data.vertices:
        w = mw @ v.co
        if w.z < Z0_CARENAGEM:
            v.co = inv @ Vector((w.x, w.y, Z0_CARENAGEM + (w.z - Z0_CARENAGEM) * s))
            n += 1
    caren.data.update()
    log("carenagem: s=%.3f, %d verts" % (s, n))

# -------------------------------------------------------------------- 4) PISTA
pista = D.objects.get("Pista")
if pista is not None:
    topo = max((pista.matrix_world @ v.co).z for v in pista.data.vertices)
    pista.location.z += SOLO - topo
    log("pista: %.3f -> %.3f" % (topo, SOLO))

bpy.context.view_layer.update()

fundo_roda2 = min(caixa(o)[2] for o in rodas)
log("DEPOIS: roda %.3f nacele %.3f carenagem %.3f altura %.3f"
    % (fundo_roda2, caixa(nacelle)[2], caixa(caren)[2], deriva_top - fundo_roda2))
log("folgas: quilha %.2f  motor %.2f  carenagem %.2f"
    % (-2.97 - fundo_roda2 - 0.0, caixa(nacelle)[2] - fundo_roda2, caixa(caren)[2] - fundo_roda2))

# tailstrike informativo (fuselagem, contato do trem principal)
mg_x = 31.24
melhor = None
dgs = bpy.context.evaluated_depsgraph_get()
fus = D.objects['Fuselagem'].evaluated_get(dgs)
me = fus.to_mesh()
mw = fus.matrix_world
for v in me.vertices:
    w = mw @ v.co
    dx, dz = w.x - mg_x, w.z - fundo_roda2
    if dx > 0.5 and dz > 0:
        t = math.atan2(dz, dx)
        if melhor is None or t < melhor:
            melhor = t
fus.to_mesh_clear()
log("tailstrike fuselagem: %.2f deg" % math.degrees(melhor))

bpy.ops.wm.save_mainfile()
log("SALVO", bpy.data.filepath)
