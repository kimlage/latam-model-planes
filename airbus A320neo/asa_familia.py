#!/usr/bin/env python3
"""Asa da familia A320 — o planform medido na VISTA SUPERIOR do ACAP.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<pasta>/<X>.blend" \
        --python "airbus A320neo/asa_familia.py" -- [medir|construir]

Este arquivo e o BUILDER DA FAMILIA, no mesmo papel que `parabrisa_familia.py`:
A320neo (mestre), A319, A320ceo, A321neo e A321ceo tem a MESMA asa — o mesmo
mesh de 448 vertices, com a A319 cortada e as duas A321 apenas deslocadas em x —
e as tres pranchas do ACAP (A320 sharklet, A320 fence, A319) desenham o mesmo
planform. As cotas moram em `spec_a320.json -> asa`.

------------------------------------------------------------------------------
O DEFEITO QUE ISTO CORRIGE
------------------------------------------------------------------------------
Ate 2026-08-21 a asa media 38.23 m de ponta a ponta contra os 35.80 m
declarados (A319: 36.92 contra 34.10). O erro tinha DOIS componentes somados,
e nenhum dos dois era uma escala global:

  (a) o PAINEL DA ASA ia ate |y| = 17.90 — mas 17.90 e a PONTA DO SHARKLET
      (metade dos 35.80 m), nao a ponta da asa. Na prancha o segmento reto do
      bordo de ataque acaba em |y| = 16.41, e dali para fora e concordancia de
      sharklet;
  (b) o SHARKLET era enxertado POR FORA desse painel ja longo, saindo de 18.13
      e terminando em 19.142.

      17.90 + 1.242 = 19.142  ->  19.142*2 - 35.80 = 2.484 m

O bordo de ataque estava CERTO (11.80+0.510y no modelo contra 11.865+0.5096y no
desenho, 0.06 m). O bordo de FUGA nao: enflechamento 0.270 contra 0.3063, e a
reta interna em x=19.19 contra 18.890, o que deixava a corda 5-10% grande.

------------------------------------------------------------------------------
O METODO
------------------------------------------------------------------------------
1. As cotas vem da VISTA SUPERIOR lida no VETOR (`pdftocairo -svg`), nao no
   raster — a prancha e CAD e os vertices sao exatos.
2. A prancha e ANISOTROPICA em 0.96%: 495.02 u/m em x (comprimento 37.57 m) e
   490.28 u/m em y (largura da fuselagem 3.95 m entre as duas retas dos
   flancos). Calibrar os dois eixos com um fator so erra a envergadura em
   0.35 m. O eixo y foi conferido por uma cota independente: o centro da nacele
   mede 5.76 m contra os 5.75 m impressos.
3. O remap e o mesmo (h, c) que a deriva ja usa: cada anel do loft e reposto
   por (fracao de corda, fracao de espessura) sobre as leis novas. Isso preserva
   o perfil, o t/c e — o que mais importa aqui — a ATRIBUICAO DE MATERIAL POR
   FACE. O indigo do sharklet viaja com as faces; `fix_sharklet_indigo.py` NAO
   deve ser rodado de novo (suas constantes sao posicionais e valem para a asa
   antiga).
4. O que se move junto: as cinco carenagens de flap (mesmo mapa de envergadura,
   reancoradas no bordo de fuga novo) e as luzes de navegacao (vao na ponta).
   O que NAO se move: motores (|y| 5.75 do ACAP), trem (bitola 7.59 do ACAP),
   fuselagem, empenagem. Sao cotas independentes da asa.
"""
import json
import math
import os
import sys

import bpy

BASE = os.path.dirname(os.path.abspath(__file__))
MESTRE = os.path.join(BASE, "spec_a320.json")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODO = argv[0] if argv else "construir"

D = bpy.data
PASTA = os.path.dirname(os.path.abspath(bpy.data.filepath))
log = lambda *a: print("[asa]", *a)

# --------------------------------------------------------------- cotas do ACAP
ASA = json.load(open(MESTRE))["asa"]

LE_A, LE_B = 11.865, 0.5096          # x = LE_A + LE_B*|y|
TE_RETA = 18.890                     # bordo de fuga interno, paralelo ao eixo
TE_A, TE_B = 16.8918, 0.3063         # x = TE_A + TE_B*|y| para fora do joelho
Y_JOELHO = (TE_RETA - TE_A) / TE_B   # 6.523
Z_RAIZ, DIEDRO = -1.0645, 0.0924     # z do meio da secao em |y|=1.20 e tg(diedro)
Y_RAIZ = 1.20

# estacoes novas dos 9 aneis da asa, em fracao do semi-envergadura do PAINEL.
# a quarta cai EM CIMA do joelho do bordo de fuga para o loft nao o borrar.
ESTACOES = [1.200, 1.950, 3.800, Y_JOELHO, 9.200, 11.800, 14.000, 15.600, None]
ESTACOES_ANTIGAS = [1.20, 1.95, 3.80, 6.00, 9.00, 12.00, 15.00, 17.20, 17.90]

# perfil do sharklet: o mesh e uma LAMINA RETA sobre a corda da curva medida.
SHARKLET_PONTA_Y = ASA["sharklet"]["ponta_y"]        # 17.90
SHARKLET_ALTURA = ASA["sharklet"]["altura_m"]        # 2.43
PONTA_ASA_Y = ASA["ponta_da_asa_y"]                  # 16.40


def le(y):
    return LE_A + LE_B * y


def te(y):
    return TE_RETA if y <= Y_JOELHO else TE_A + TE_B * y


def zmid(y):
    return Z_RAIZ + DIEDRO * (y - Y_RAIZ)


# ------------------------------------------------------- variante da aeronave
def variante():
    """(nome, envergadura declarada, ponta do painel, ponta da extremidade)."""
    loc = None
    for f in sorted(os.listdir(PASTA)):
        if f.startswith("spec_") and f.endswith(".json"):
            loc = json.load(open(os.path.join(PASTA, f)))
            nome = f
            break
    if loc is None:
        raise RuntimeError("nenhum spec_*.json em %s" % PASTA)
    dg = loc.get("dimensoes_gerais", {})
    if "envergadura_sharklets" in dg:
        env = dg["envergadura_sharklets"]
        # sharklet: a prancha do sharklet mede 35.83 contra os 35.80 impressos;
        # a ponta do painel sai direto do desenho.
        return nome, env, PONTA_ASA_Y, env / 2.0, "sharklet"
    if "envergadura_fence" in dg:
        env = dg["envergadura_fence"]
        # fence: a prancha desenha a ponta em |y| 17.203 e imprime 34.10 (17.05).
        # a cota impressa manda; o joelho do bordo de ataque (16.509 no desenho)
        # entra reescalado pela mesma razao.
        ponta = env / 2.0
        painel = 16.509 * ponta / 17.203
        return nome, env, painel, ponta, "fence"
    raise RuntimeError("spec sem envergadura declarada: %s" % nome)


SPEC_LOCAL, ENVERGADURA, Y_PAINEL, Y_PONTA, TIPO = variante()
log("aeronave %s  %s  envergadura %.2f m  painel ate |y| %.3f, ponta %.3f"
    % (os.path.basename(bpy.data.filepath), TIPO, ENVERGADURA, Y_PAINEL, Y_PONTA))

# ------------------------------------------------------------------ leitura
ASAS = D.objects["Asas"]
ME = ASAS.data
V = ME.vertices
if len(V) % 28:
    raise RuntimeError("Asas com %d vertices, nao e multiplo de 28" % len(V))
N_ANEIS = len(V) // 28
aneis = [[V[k * 28 + i] for i in range(28)] for k in range(N_ANEIS)]


def caixa(anel):
    xs = [v.co.x for v in anel]
    ys = [v.co.y for v in anel]
    zs = [v.co.z for v in anel]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


planos = [k for k in range(N_ANEIS) if caixa(aneis[k])[3] - caixa(aneis[k])[2] < 1e-4]
if planos != list(range(9)):
    raise RuntimeError("esperava 9 aneis planos (a asa) nos indices 0..8, achei %s" % planos)

y_antigas = [round(caixa(a)[2], 3) for a in aneis[:9]]
if [round(v, 2) for v in y_antigas] != ESTACOES_ANTIGAS:
    raise RuntimeError("estacoes da asa ja mudaram (%s) — provavelmente ja corrigida"
                       % y_antigas)

DX = caixa(aneis[0])[0] - 12.422            # A319 = -1.60 ; A320/A321 = 0
log("deslocamento x do mesh em relacao ao mestre: %+.3f" % DX)

# leis ANTIGAS medidas no proprio mesh (para reancorar o que anda junto)
YS_OLD = [caixa(a)[2] for a in aneis[:9]]
TE_OLD = [caixa(a)[1] for a in aneis[:9]]
ZM_OLD = [(caixa(a)[4] + caixa(a)[5]) / 2.0 for a in aneis[:9]]


def _interp(t, xs, ys):
    if t <= xs[0]:
        return ys[0] + (ys[1] - ys[0]) * (t - xs[0]) / (xs[1] - xs[0])
    if t >= xs[-1]:
        return ys[-1] + (ys[-1] - ys[-2]) * (t - xs[-1]) / (xs[-1] - xs[-2])
    for i in range(len(xs) - 1):
        if xs[i] <= t <= xs[i + 1]:
            f = (t - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + f * (ys[i + 1] - ys[i])
    return ys[-1]


te_old = lambda y: _interp(y, YS_OLD, TE_OLD)
zm_old = lambda y: _interp(y, YS_OLD, ZM_OLD)

TIP_OLD = caixa(aneis[8])
Y_TIP_OLD, LE_TIP_OLD = TIP_OLD[2], TIP_OLD[0]
C_TIP_OLD = TIP_OLD[1] - TIP_OLD[0]
ZM_TIP_OLD = (TIP_OLD[4] + TIP_OLD[5]) / 2.0

pontas = [v for k in range(9, N_ANEIS) for v in aneis[k]]
Y_EXT_OLD = max(v.co.y for v in pontas)
Z_EXT_OLD = max(v.co.z for v in pontas)

est = list(ESTACOES)
est[8] = Y_PAINEL
LE_TIP_NEW = le(Y_PAINEL) + DX
C_TIP_NEW = te(Y_PAINEL) - le(Y_PAINEL)
ZM_TIP_NEW = zmid(Y_PAINEL)
K_CORDA_TIP = C_TIP_NEW / C_TIP_OLD
K_PONTA_Y = (Y_PONTA - Y_PAINEL) / (Y_EXT_OLD - Y_TIP_OLD)
K_PONTA_Z = (SHARKLET_ALTURA / (Z_EXT_OLD - ZM_TIP_OLD)) if TIPO == "sharklet" else 1.0

log("ponta antiga |y| %.3f z %.3f -> nova |y| %.3f ; ky %.4f kz %.4f kc %.4f"
    % (Y_EXT_OLD, Z_EXT_OLD, Y_PONTA, K_PONTA_Y, K_PONTA_Z, K_CORDA_TIP))

if MODO == "medir":
    for k in range(9):
        x0, x1, y0, y1, z0, z1 = caixa(aneis[k])
        yn = est[k]
        log("anel %d  |y| %6.3f -> %6.3f   corda %5.3f -> %5.3f   LE %6.3f -> %6.3f"
            % (k, y0, yn, x1 - x0, te(yn) - le(yn), x0, le(yn) + DX))
    raise SystemExit(0)

# ------------------------------------------------------------------ remap
for k in range(9):
    x0, x1, y0, y1, z0, z1 = caixa(aneis[k])
    yn = est[k]
    c_old = x1 - x0
    c_new = te(yn) - le(yn)
    kk = c_new / c_old
    zm_o = (z0 + z1) / 2.0
    zm_n = zmid(yn)
    xn0 = le(yn) + DX
    for v in aneis[k]:
        v.co.x = xn0 + (v.co.x - x0) * kk
        v.co.z = zm_n + (v.co.z - zm_o) * kk
        v.co.y = yn
    log("anel %d |y| %6.3f -> %6.3f  corda %5.3f -> %5.3f  zmeio %+.3f -> %+.3f"
        % (k, y0, yn, c_old, c_new, zm_o, zm_n))

PONTA_ORIG = [(v.co.x, v.co.y, v.co.z) for v in pontas]

# A319: a cerca de ponta de asa e um objeto separado, `WingFence`, e e ELA que
# define a envergadura publicada (34.10 m e medido SOBRE as cercas). Anda com a
# ponta, mas por TRANSLACAO rigida em y — escalar a espessura de uma placa de
# 90 mm pelo fator da ponta a engrossaria em 58%.
CERCA = next((D.objects.get(n) for n in ("WingFence", "Fence", "Sharklet")
              if D.objects.get(n)), None)
CERCA_ORIG = [(v.co.x, v.co.y, v.co.z) for v in CERCA.data.vertices] if CERCA else []
if CERCA:
    log("extremidade separada: %s (%d verts, |y| max %.3f)"
        % (CERCA.name, len(CERCA_ORIG), max(abs(p[1]) for p in CERCA_ORIG)))


def remap_pontas(ky):
    for v, (xo, yo, zo) in zip(pontas, PONTA_ORIG):
        v.co.x = LE_TIP_NEW + (xo - LE_TIP_OLD) * K_CORDA_TIP
        v.co.y = Y_PAINEL + (yo - Y_TIP_OLD) * ky
        v.co.z = ZM_TIP_NEW + (zo - ZM_TIP_OLD) * K_PONTA_Z
    ME.update()
    if CERCA:
        dy = (Y_PAINEL + (Y_EXT_OLD - Y_TIP_OLD) * ky) - Y_EXT_OLD
        dz = ZM_TIP_NEW - ZM_TIP_OLD
        for v, (xo, yo, zo) in zip(CERCA.data.vertices, CERCA_ORIG):
            v.co.x = LE_TIP_NEW + (xo - LE_TIP_OLD) * K_CORDA_TIP
            v.co.y = math.copysign(abs(yo) + dy, yo)
            v.co.z = zo + dz
        CERCA.data.update()


def envergadura_avaliada():
    """Meia-envergadura da SUPERFICIE LIMITE (com subsurf) da asa e da cerca.

    So esses dois: o casco e a empenagem nunca chegam perto, e deixar uma luz de
    navegacao entrar na conta foi como a A319 passou a medir 36.92 com a asa em
    36.74."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    m = 0.0
    for ob in ([ASAS, CERCA] if CERCA else [ASAS]):
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        m = max(m, max(abs((ob.matrix_world @ v.co).y) for v in me.vertices))
        ev.to_mesh_clear()
    return m


# o subsurf ENCOLHE a ponta (Catmull-Clark puxa o vertice para dentro do seu
# 1-anel): no mestre antigo o mesh tinha 19.142 e a superficie 19.116. A cota
# do ACAP e da SUPERFICIE, entao a gaiola vai um tanto para fora — quanto,
# mede-se, nao se supoe.
ky = K_PONTA_Y
for it in range(8):
    remap_pontas(ky)
    med = envergadura_avaliada()
    err = Y_PONTA - med
    log("iter %d  ky %.5f  meia-envergadura avaliada %.4f  erro %+.4f"
        % (it, ky, med, err))
    if abs(err) < 0.001:
        break
    ky *= 1.0 + err / max(med - Y_PAINEL, 1e-6) * 0.9
K_PONTA_Y = ky
xs = [v.co.x for v in V]
ys = [v.co.y for v in V]
zs = [v.co.z for v in V]
log("Asas agora X[%.3f,%.3f] Y[%.3f,%.3f] Z[%.3f,%.3f]"
    % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))

# ------------------------------------------------------- o que anda com a asa
F_ENV = (Y_PAINEL - Y_RAIZ) / (Y_TIP_OLD - Y_RAIZ)
for nome in ("FlapFairing0", "FlapFairing1", "FlapFairing2", "FlapFairing3",
             "FlapFairing4"):
    ob = D.objects.get(nome)
    if not ob:
        continue
    yo = abs(ob.location.y)
    yn = Y_RAIZ + (yo - Y_RAIZ) * F_ENV
    dxs = (te(yn) + DX) - te_old(yo)
    dzs = zmid(yn) - zm_old(yo)
    ob.location.y = math.copysign(yn, ob.location.y)
    ob.location.x += dxs
    ob.location.z += dzs
    log("%s |y| %.3f -> %.3f  dx %+.3f dz %+.3f" % (nome, yo, yn, dxs, dzs))

# as luzes de navegacao ficam no bordo de ataque da PONTA DA ASA, na raiz do
# sharklet — nao na ponta do sharklet. Postas por fora do painel, como estavam,
# elas e que decidiam a envergadura da A319 (18.46 contra 18.37 da asa).
for nome in ("NavDir", "NavEsq"):
    ob = D.objects.get(nome)
    if not ob:
        continue
    raio = max(abs(v.co.x) for v in ob.data.vertices) if ob.data.vertices else 0.07
    # as luzes ficam em coordenada ABSOLUTA; a asa da A321 mora num objeto
    # deslocado +4.26 em x, entao o offset do objeto entra aqui.
    xn = ASAS.location.x + LE_TIP_NEW + 0.02 * K_CORDA_TIP
    yn = Y_PAINEL - raio - 0.01
    zn = ZM_TIP_NEW + (ob.location.z - ZM_TIP_OLD) * K_PONTA_Z
    log("%s (%.3f,%.3f,%.3f) -> (%.3f,%.3f,%.3f)"
        % (nome, ob.location.x, ob.location.y, ob.location.z, xn,
           math.copysign(yn, ob.location.y), zn))
    ob.location.x, ob.location.z = xn, zn
    ob.location.y = math.copysign(yn, ob.location.y)

# ------------------------------------------------------------------ conferido
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
yy = []
for ob in D.objects:
    if ob.type != "MESH" or ob.name == "Pista" or not ob.data.vertices:
        continue
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    for v in me.vertices:
        yy.append((ob.matrix_world @ v.co).y)
    ev.to_mesh_clear()
env = max(yy) - min(yy)
log("ENVERGADURA avaliada: %.3f m  (declarada %.2f, delta %+.3f)"
    % (env, ENVERGADURA, env - ENVERGADURA))

bpy.ops.wm.save_mainfile()
log("SALVO", bpy.data.filepath)
