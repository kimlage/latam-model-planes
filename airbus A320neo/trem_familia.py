#!/usr/bin/env python3
"""Estancia estatica e quilha traseira da familia A320 — as cotas do ACAP.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<pasta>/<X>.blend" \
        --python "airbus A320neo/trem_familia.py" -- [medir|construir]

Este arquivo e o BUILDER DA FAMILIA para a estancia no solo, no mesmo papel que
`asa_familia.py` e `portas_familia.py`. Vale para A319, A320ceo, A320neo,
A321ceo e A321neo — a aeronave e detectada pela pasta do .blend.

------------------------------------------------------------------------------
OS TRES DEFEITOS QUE ISTO CORRIGE (QA-BACKLOG "tailstrike angles")
------------------------------------------------------------------------------
Medidos em 2026-08-27, nos cinco masters (todos identicos nos tres numeros):

1. TREM CURTO. Roda no chao em z = -3.675 -> folga da quilha da secao
   constante 1.605 m. O ACAP de cada tipo (Ground Clearances: A320 fig
   -004/-032, A319 fig -002, A321 fig -005/-034) da, para F1/F2 "BOTTOM
   FWD/AFT": MRW 1.72-1.88, vazio-manutencao 1.82-1.99. Alvo adotado: a
   estancia VAZIA nivelada (media F1/F2 na coluna de peso de manutencao):
   A319/A320 1.885 m, A321 1.915 m -> roda em z -3.955 / -3.985.
   A linha de solo DESENHADA na side view do ACAP A320 (p40) mede 1.87+-0.03
   pela mesma extracao — a tabela e o desenho concordam.

2. CARENAGEM VENTRAL 0.20 m FUNDA DEMAIS. Fundo do modelo em z -2.443; o
   ACAP (coluna A/C JACKED, FDL=4.60 m, igual nos tres tipos) da BF1 2.26 m
   contra F 2.43 m: a carenagem desce 0.17 m abaixo da quilha, nao 0.37.
   Alvo: fundo em z -2.24. Remapeio: so vertices abaixo de z0=-1.60,
   z' = z0 + (z-z0)*s, s=(alvo-z0)/(fundo_atual-z0). Os apendices que moram
   NELA (placas RA, saidas de pack, ram-air, DME2) seguem o mesmo mapa.

3. QUILHA TRASEIRA BAIXA (o upsweep comeca tarde e sobe pouco). Extraida a
   quilha da side view de cada ACAP (600 dpi, mascara amarela, ancorada na
   crista/quilha da secao constante — vies de traco cancela) e comparada com
   a malha avaliada: o modelo esta ate 0.29 m baixo no meio do upsweep
   (A320: x 28.5-30) e o upsweep parte de x 26.3 quando o desenho parte de
   x ~24.2 (A319 ~21.6, A321 ~30.7). Correcao POR ANEL da gaiola, afim em z
   com a CRISTA FIXA: z' = crista - (crista - z)*f, f = (crista-quilha_nova)
   / (crista-quilha_velha), e y' = y*f — mantendo a lei w = 0.954*r das
   secoes de cauda (medida nos aneis: ry/rz = 0.954). SO SE ERGUE, nunca se
   abaixa: alem do cruzamento (~x 34 no A320) o modelo fica ~0.1-0.2 ACIMA
   do desenho, mas ali a silhueta desenhada e fina (cone + bocal da APU),
   a leitura e ambigua (a cota AP fecha com o modelo a 1 cm numa estacao e
   diverge 0.2 na outra), e engordar o cone 68% por causa de um traco de
   3 px nao se defende. Fica registrado em aberto no spec.

   A validacao que fecha o metodo: com o trem do ACAP e a quilha do ACAP, o
   tailstrike geometrico estatico (rotacao em torno do contato do trem
   principal, primeiro toque da FUSELAGEM) da:

       A320  12.5-12.6 graus   (publicado: 11.7 comprimido / 13.5 estendido)
       A319  ~14.7             (publicado: 13.9 / 15.5)
       A321  ~10.3             (publicado:  9.7 / 11.2)

   — cada tipo entre o comprimido e o estendido, como deve ser uma estancia
   estatica. Antes da correcao o A320 dava 9.9 na fuselagem e 7.75 no dreno.

E OS MASTROS DE DRENO: Belly_DrenoFwd/Aft afundavam 0.27-0.32 m alem do
casco (o aft LIMITAVA o tailstrike em 7.75 graus). Nao ha cota de mastro no
ACAP; protrusao alvo 0.15 m e ESTIMATIVA declarada (mastros reais ~0.1-0.2 m;
nas fotos de perfil de ~50 px/m eles mal resolvem, o que limita <=0.3 m).
Registrada como estimativa no spec. Os demais apendices de ventre (VHF,
beacon, outflow, portas de carga da A321) apenas ACOMPANHAM o casco pelo
mesmo mapa afim, para continuarem assentados.

O que NAO muda: nariz, barril, cavernas, asas, empenagem, motores, portas
pax fora da janela de cauda (as de dentro sao re-assentadas por
`portas_familia -- construir` na sequencia do REBUILD.md), UVs (vertices
movem, UV por-loop fica — e a repintura do REBUILD realinha a tinta a regra).

Idempotente: rodar duas vezes nao move nada (alvos absolutos, medidos do
proprio blend a cada rodada).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODO = argv[0] if argv else "construir"

D = bpy.data
PASTA = os.path.dirname(os.path.abspath(bpy.data.filepath))
TAG = {
    "airbus A319": "a319", "airbus A320ceo": "a320ceo", "airbus A320neo": "a320neo",
    "airbus A321ceo": "a321ceo", "airbus A321neo": "a321neo",
}.get(os.path.basename(PASTA))
if TAG is None:
    raise SystemExit("pasta nao reconhecida: %s" % PASTA)
log = lambda *a: print("[trem]", *a)

# ---------------------------------------------------------------- alvos (ACAP)
# solo: -(2.07 + folga F1/F2 media na coluna vazio-manutencao)
SOLO = {"a319": -3.955, "a320ceo": -3.955, "a320neo": -3.955,
        "a321ceo": -3.985, "a321neo": -3.985}[TAG]
FUNDO_CARENAGEM = -2.24          # BF1 jacked 2.26 vs F 2.43 (FDL 4.60), 3 tipos
Z0_CARENAGEM = -1.60             # acima disso a carenagem nao se mexe
PROTRUSAO_DRENO = 0.15           # ESTIMATIVA declarada (sem cota ACAP)

# quilha da side view de cada ACAP (x, z no referencial do modelo; extracao
# 600 dpi ancorada na secao constante, 2026-08-27)
QUILHA_A320 = [(24.0, -2.060), (24.5, -2.045), (25.0, -2.014), (25.5, -1.984),
               (26.0, -1.938), (26.5, -1.892), (27.0, -1.816), (27.5, -1.740),
               (28.0, -1.649), (28.5, -1.542), (29.0, -1.435), (29.5, -1.328),
               (30.0, -1.207), (30.5, -1.100), (31.0, -0.978), (31.5, -0.871),
               (32.0, -0.765), (32.5, -0.627), (33.0, -0.490), (33.5, -0.353),
               (34.0, -0.201), (34.5, -0.064), (35.0, 0.074)]
QUILHA_A319 = [(21.5, -2.025), (22.0, -1.964), (22.5, -1.889), (23.0, -1.813),
               (23.5, -1.753), (24.0, -1.677), (24.5, -1.602), (25.0, -1.481),
               (25.5, -1.345), (26.0, -1.239), (26.5, -1.103), (27.0, -0.997),
               (27.5, -0.861), (28.0, -0.740), (28.5, -0.619), (29.0, -0.499),
               (29.5, -0.378), (30.0, -0.257), (30.5, -0.136), (31.0, -0.015),
               (31.5, 0.106)]
QUILHA_A321 = [(31.0, -2.055), (31.5, -2.040), (32.0, -2.009), (32.5, -1.979),
               (33.0, -1.933), (33.5, -1.872), (34.0, -1.796), (34.5, -1.720),
               (35.0, -1.629), (35.5, -1.522), (36.0, -1.400), (36.5, -1.294),
               (37.0, -1.187), (37.5, -1.081), (38.0, -0.974), (38.5, -0.852),
               (39.0, -0.746), (39.5, -0.609), (40.0, -0.472), (40.5, -0.335),
               (41.0, -0.198), (41.5, -0.061)]
QUILHA = {"a319": QUILHA_A319, "a320ceo": QUILHA_A320, "a320neo": QUILHA_A320,
          "a321ceo": QUILHA_A321, "a321neo": QUILHA_A321}[TAG]
X_INI = QUILHA[0][0]


def quilha_alvo(x):
    """interp linear na tabela; fora dela devolve None."""
    if x < QUILHA[0][0] or x > QUILHA[-1][0]:
        return None
    for (x0, z0), (x1, z1) in zip(QUILHA, QUILHA[1:]):
        if x0 <= x <= x1:
            return z0 + (z1 - z0) * (x - x0) / (x1 - x0)
    return None


# ------------------------------------------------------------------ utilidades
def verts_mundo(ob):
    mw = ob.matrix_world
    return [(v, mw @ v.co) for v in ob.data.vertices]


def caixa(ob):
    ws = [w for _, w in verts_mundo(ob)]
    return (min(w.x for w in ws), max(w.x for w in ws),
            min(w.y for w in ws), max(w.y for w in ws),
            min(w.z for w in ws), max(w.z for w in ws))


def mover_verts(ob, cond, dvec):
    mw = ob.matrix_world
    inv = mw.inverted()
    n = 0
    for v in ob.data.vertices:
        w = mw @ v.co
        if cond(w):
            v.co = inv @ (w + dvec)
            n += 1
    ob.data.update()
    return n


def eval_keel(x_lo, x_hi):
    """quilha avaliada (subsurf) da Fuselagem, bins de 0.5 m."""
    dg = bpy.context.evaluated_depsgraph_get()
    fus = D.objects["Fuselagem"]
    oe = fus.evaluated_get(dg)
    me = oe.to_mesh()
    mw = oe.matrix_world
    bins = {}
    for v in me.vertices:
        w = mw @ v.co
        if x_lo < w.x < x_hi and abs(w.y) < 0.7:
            b = round(w.x * 2) / 2
            bins[b] = min(bins.get(b, 9.9), w.z)
    oe.to_mesh_clear()
    return dict(sorted(bins.items()))


def tailstrike(solo_z, mg_x):
    """primeiro toque por objeto, rotacao no contato do trem principal."""
    piores = []
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in D.objects:
        if ob.type != 'MESH' or ob.hide_render or ob.name == "Pista":
            continue
        oe = ob.evaluated_get(dg)
        try:
            me = oe.to_mesh()
        except RuntimeError:
            continue
        mw = oe.matrix_world
        best = None
        for v in me.vertices:
            w = mw @ v.co
            dx, dz = w.x - mg_x, w.z - solo_z
            if dx > 0.5 and dz > 0:
                t = math.atan2(dz, dx)
                if best is None or t < best:
                    best = t
        oe.to_mesh_clear()
        if best is not None:
            piores.append((math.degrees(best), ob.name))
    piores.sort()
    return piores[:6]


# -------------------------------------------------------------------- medicoes
rodas = [o for o in D.objects if o.type == 'MESH' and "Roda" in o.name and o.name.startswith("Trem")]
fundo_roda = min(caixa(o)[4] for o in rodas)
mg = [o for o in D.objects if o.name.startswith("TremPrincipal_Roda")]
mg_x = sum((caixa(o)[0] + caixa(o)[1]) / 2 for o in mg) / len(mg)
caren = D.objects["BellyFairing"]
fundo_caren = caixa(caren)[4]
log("medido: roda %.3f  carenagem %.3f  trem principal x %.2f" % (fundo_roda, fundo_caren, mg_x))
log("quilha avaliada ANTES:", {k: round(v, 3) for k, v in eval_keel(X_INI - 1, X_INI + 12).items()})
log("tailstrike ANTES:", [(round(a, 2), n) for a, n in tailstrike(fundo_roda, mg_x)])

if MODO == "medir":
    for x in [q[0] for q in QUILHA]:
        pass
    raise SystemExit(0)

# ============================================================== 1) QUILHA (casco)
fus = D.objects["Fuselagem"]
mw = fus.matrix_world
inv = mw.inverted()

# aneis da gaiola: agrupar por x (mundo, arredondado)
aneis = {}
for v in fus.data.vertices:
    w = mw @ v.co
    aneis.setdefault(round(w.x, 3), []).append(v)

fatores = []          # (x, crista, f) para reaproveitar nos apendices
n_aneis = 0
for x, verts in sorted(aneis.items()):
    if x < X_INI - 0.3 or len(verts) < 8:
        continue
    ws = [mw @ v.co for v in verts]
    crista = max(w.z for w in ws)
    quilha_velha = min(w.z for w in ws)
    alvo = quilha_alvo(x)
    if alvo is None or alvo <= quilha_velha + 0.005:
        fatores.append((x, crista, 1.0))
        continue                      # so se ergue, nunca se abaixa
    f = (crista - alvo) / (crista - quilha_velha)
    for v, w in zip(verts, ws):
        nz = crista - (crista - w.z) * f
        ny = w.y * f
        v.co = inv @ Vector((w.x, ny, nz))
    fatores.append((x, crista, f))
    n_aneis += 1
    log("anel x %.2f: quilha %.3f -> %.3f  (f %.4f)" % (x, quilha_velha, alvo, f))
fus.data.update()
log("aneis erguidos:", n_aneis)


def f_local(x):
    """(crista, f) interpolado nas estacoes corrigidas."""
    fs = sorted(fatores)
    if not fs or x <= fs[0][0]:
        return (2.07, 1.0)
    if x >= fs[-1][0]:
        return fs[-1][1], fs[-1][2]
    for (x0, c0, f0), (x1, c1, f1) in zip(fs, fs[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return c0 + (c1 - c0) * t, f0 + (f1 - f0) * t
    return (2.07, 1.0)


# apendices e portas na janela de cauda ACOMPANHAM o casco (mesmo mapa afim)
SEGUE_CASCO = ("Belly_VHF2", "Belly_Beacon", "Belly_DrenoAft", "Belly_Outflow",
               "Belly_APUIntake", "PortaCargaBulk", "PortaCargaAft")
seguidores = [o for o in D.objects if o.type == 'MESH' and
              (o.name in SEGUE_CASCO or o.name.startswith("Porta"))]
for ob in seguidores:
    x0, x1, *_ = caixa(ob)
    xc = (x0 + x1) / 2
    if xc < X_INI - 0.3:
        continue
    crista, f = f_local(xc)
    if abs(f - 1.0) < 1e-4:
        continue
    mwo = ob.matrix_world
    invo = mwo.inverted()
    for v in ob.data.vertices:
        w = mwo @ v.co
        nz = crista - (crista - w.z) * f
        ny = w.y * f
        v.co = invo @ Vector((w.x, ny, nz))
    ob.data.update()
    log("segue casco: %-16s xc %.2f f %.4f" % (ob.name, xc, f))

# ============================================================ 2) CARENAGEM VENTRAL
s = (FUNDO_CARENAGEM - Z0_CARENAGEM) / (fundo_caren - Z0_CARENAGEM)
if abs(s - 1.0) > 1e-4:
    cx0, cx1, *_ = caixa(caren)
    alvos_caren = [caren] + [o for o in D.objects if o.type == 'MESH' and
                             o.name.startswith("Belly_") and o not in seguidores and
                             (lambda b: b[4] < -2.30 and b[0] > cx0 - 0.5 and b[1] < cx1 + 0.5)(caixa(o))]
    for ob in alvos_caren:
        n = 0
        mwo = ob.matrix_world
        invo = mwo.inverted()
        for v in ob.data.vertices:
            w = mwo @ v.co
            if w.z < Z0_CARENAGEM:
                v.co = invo @ Vector((w.x, w.y, Z0_CARENAGEM + (w.z - Z0_CARENAGEM) * s))
                n += 1
        ob.data.update()
        log("carenagem s=%.3f: %-16s %d verts" % (s, ob.name, n))

# ================================================================== 3) TREM + PISTA
delta = SOLO - fundo_roda
if abs(delta) > 1e-4:
    for ob in D.objects:
        n = ob.name
        if not n.startswith("Trem"):
            continue
        if "Roda" in n or "Eixo" in n:
            ob.location.z += delta
            log("trem: %-24s desce %.3f (inteiro)" % (n, -delta if delta < 0 else delta))
        elif "Strut" in n or "Brace" in n:
            corte = -2.4 if "Brace" in n else -2.5
            m = mover_verts(ob, lambda w: w.z < corte, Vector((0, 0, delta)))
            log("trem: %-24s estica %d verts abaixo de %.1f" % (n, m, corte))
    pista = D.objects.get("Pista")
    if pista is not None:
        topo = caixa(pista)[5]
        pista.location.z += SOLO - topo
        log("pista: topo %.3f -> %.3f" % (topo, SOLO))
bpy.context.view_layer.update()

# ============================================================ 4) MASTROS DE DRENO
for nome, keel_ref in (("Belly_DrenoFwd", None), ("Belly_DrenoAft", "local")):
    ob = D.objects.get(nome)
    if ob is None:
        continue
    b = caixa(ob)
    xc = (b[0] + b[1]) / 2
    if keel_ref is None:
        keel = -2.07
    else:
        kb = eval_keel(xc - 0.6, xc + 0.6)
        keel = min(kb.values()) if kb else -2.07
    alvo_fundo = keel - PROTRUSAO_DRENO
    dz = alvo_fundo - b[4]
    if abs(dz) > 5e-3:
        ob.location.z += dz
        log("mastro %s: fundo %.3f -> %.3f (quilha local %.3f + %.2f)"
            % (nome, b[4], alvo_fundo, keel, PROTRUSAO_DRENO))

bpy.context.view_layer.update()

# ------------------------------------------------------------------- veredito
fundo_roda2 = min(caixa(o)[4] for o in rodas)
log("quilha avaliada DEPOIS:", {k: round(v, 3) for k, v in eval_keel(X_INI - 1, X_INI + 12).items()})
log("roda DEPOIS: %.3f (alvo %.3f)  carenagem DEPOIS: %.3f (alvo %.3f)"
    % (fundo_roda2, SOLO, caixa(caren)[4], FUNDO_CARENAGEM))
log("tailstrike DEPOIS:", [(round(a, 2), n) for a, n in tailstrike(fundo_roda2, mg_x)])

# rings json da aeronave (registro da gaiola)
rings_path = {
    "a319": "a319_rings.json", "a320ceo": "a320ceo_rings.json",
    "a320neo": "a320neo_rings.json", "a321ceo": "a321ceo_rings.json",
    "a321neo": "a321neo_rings.json",
}[TAG]
rp = os.path.join(PASTA, rings_path)
if os.path.exists(rp):
    rings = json.load(open(rp))
    mudou = 0
    for r in rings:
        alvo = quilha_alvo(r["x"])
        keel_velho = r["zc"] - r["rz"]
        if alvo is None or alvo <= keel_velho + 0.005:
            continue
        crista = r["zc"] + r["rz"]
        rz2 = (crista - alvo) / 2.0
        r["ry"] = round(r["ry"] * rz2 / r["rz"], 4)
        r["rz"] = round(rz2, 4)
        r["zc"] = round(crista - rz2, 4)
        mudou += 1
    if mudou:
        json.dump(rings, open(rp, "w"), indent=1)
        log("rings json: %d aneis atualizados (%s)" % (mudou, rings_path))

bpy.ops.wm.save_mainfile()
log("SALVO", bpy.data.filepath)
