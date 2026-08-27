#!/usr/bin/env python3
"""Apendices e luzes da frota — antenas, sondas, wicks, faroleria emissiva.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<pasta>/<MASTER>.blend" \
        --python apendices_familia.py -- [construir|medir]

MODULO DE FAMILIA no papel de `trem_familia.py`/`portas_familia.py`: um codigo,
onze aeronaves, a aeronave detectada pela pasta do .blend e os numeros vindos
da tabela `apendices_2026-08-27` do spec de cada tipo. Nada aqui esculpe malha
de um tipo so — o que a familia compartilha vive no modulo, o que e do tipo
vive no spec.

O QUE CONSTROI (por chave do spec; chave ausente = elemento nao se constroi):

  pitot / aoa / tat      sondas do nariz, assentadas por raycast no casco
                         avaliado (subsurf ja descontado), StrutMetal
  vhf_ventre, gps, tcas  o que faltava do fit de antenas dos Boeing (os
                         masters ja carregam 2 VHF dorsais + SATCOM; a familia
                         A320 ja tem o fit completo de fabrica)
  beacon_dorso/_ventre   os anticolisao que faltavam (777: so tinha o ventral;
                         767/787: so o dorsal), domo LuzVermelha
  estrobo_asa            strobes de ponta de asa da familia A320 e do 777
                         (767/787 ja os tem), na FUGA da ponta, LuzBranca
  estrobo_cauda          strobe branco do cone de cauda, junto a LuzCauda,
                         frota inteira
  farol_asa_raiz         landing/turnoff lights no BA da raiz da asa
                         (Boeings; na familia A320 os faroleiros de asa sao
                         retrateis e ficam EMBUTIDOS — deliberado, no spec)
  farol_taxi             farol duplo de taxi na perna do trem do nariz,
                         frota inteira (aceso em toda foto de taxi)
  luz_logo               logo light no extradorso do estabilizador, mirando a
                         deriva, frota inteira
  wicks                  descarregadores estaticos na FUGA de asa, estab e
                         deriva — contagem tipica publicada DECLARADA no spec
                         (nenhuma foto do acervo resolve unidade a unidade);
                         d=16 mm: le como fio de 1 px no perfil, como na foto
  wipers                 limpadores no para-brisa, posicao de estacionamento
                         POR FAMILIA lida das fotos head-on do acervo
  drenos                 mastros de dreno dos Boeing (A320: rodada do trem ja
                         os fez); protrusao 0.15 m = a MESMA estimativa
                         declarada de `trem_familia.py`

MATERIAIS — a licao medida do custo de render: NENHUM material novo. Todo
elemento veste um dos que TODA a frota ja carrega: StrutMetal (metal),
LuzBranca / LuzVermelha / LuzVerde (emissivos, strength 6.0, ja usados por
Nav/Beacon/LuzCauda), CinzaEscuro (borracha dos wipers), LATAM_Branco
(carenagens pintadas). Emissao CONSTANTE: strobe piscando e decisao de clipe
(25 fps), nao desta rodada — registrado na PENDENCIAS.

ASSENTAMENTO: tudo por raycast contra a cena AVALIADA (depsgraph), entao o
encolhimento do Catmull-Clark ja esta pago; a base fica 0.02 m PROUD da
superficie (regra das portas, casco-parametrico). Raycasts ventrais partem de
DENTRO da caixa da aeronave para nao acertar a Pista; um hit em objeto que nao
e casco/carenagem avanca e relanca (ha antena legada em cima da quilha).

FUGA (TE) de asa/estab/deriva: amostrada da malha avaliada do proprio objeto
(max x por bin de envergadura) — funciona no Asas espelhado da A320, nos
AsaE/AsaD do 777 e no raked tip do 787 sem tabela nenhuma.

Idempotente: todo objeto criado chama-se `Apx_*`; rodar de novo apaga e
reconstroi. `medir` so relata, nao salva.
"""
import json
import math
import os
import sys
import glob

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODO = argv[0] if argv else "construir"

D = bpy.data
PASTA = os.path.dirname(os.path.abspath(bpy.data.filepath))
log = lambda *a: print("[apx]", *a)

specs = glob.glob(os.path.join(PASTA, "spec_*.json"))
if len(specs) != 1:
    raise SystemExit("spec unico nao achado em %s: %s" % (PASTA, specs))
SPEC = json.load(open(specs[0]))
AP = SPEC.get("apendices_2026-08-27")
if AP is None:
    raise SystemExit("spec sem tabela apendices_2026-08-27 — tabela primeiro")

D_FUS = SPEC["dimensoes_gerais"].get("fuselagem_largura", 4.0)
ESC = D_FUS / 4.0          # escala suave dos apendices com o porte

# ------------------------------------------------------------------ limpeza
velhos = [o for o in D.objects if o.name.startswith("Apx_")]
for ob in velhos:
    me = ob.data if ob.type == 'MESH' else None
    D.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        D.meshes.remove(me)
if velhos:
    log("removidos %d Apx_ anteriores (idempotencia)" % len(velhos))
bpy.context.view_layer.update()
DG = bpy.context.evaluated_depsgraph_get()

CASCO_OK = ("Fuselagem", "BellyFairing", "Asas", "AsaE", "AsaD",
            "EstabHorizontal", "EstabE", "EstabD", "Deriva", "DerivaDorsal")


# ------------------------------------------------------------------ raycast
def lancar(origem, direcao, aceitar=CASCO_OK, max_saltos=8):
    """Primeiro hit num objeto aceito; hits em mais nada avancam o raio."""
    o = Vector(origem)
    d = Vector(direcao).normalized()
    for _ in range(max_saltos):
        ok, loc, nrm, _i, ob, _m = bpy.context.scene.ray_cast(DG, o, d)
        if not ok:
            return None, None
        if ob.name in aceitar or ob.name.split(".")[0] in aceitar:
            if nrm.dot(d) > 0:
                nrm = -nrm
            return Vector(loc), Vector(nrm).normalized()
        o = Vector(loc) + d * 0.03
    return None, None


def no_casco(x, theta_dir, alvo_z=0.0):
    """Assenta em (x, ...) lancando na direcao dada ('crown','keel','ladoE','ladoD')."""
    if theta_dir == "crown":
        return lancar((x, 0.0, 12.0), (0, 0, -1))
    if theta_dir == "keel":
        # de dentro da caixa (acima da Pista, abaixo da quilha) para cima NAO:
        # lanca de um ponto DENTRO do solido para baixo nao funciona; lanca de
        # baixo para cima a partir de logo acima da pista nao acerta a Pista.
        return lancar((x, 0.0, alvo_z - 1.2), (0, 0, 1))
    lado = -1.0 if theta_dir == "ladoE" else 1.0
    return lancar((x, lado * (D_FUS * 2.0 + 4.0), alvo_z), (0, -lado, 0))


# ------------------------------------------------------------- malha/objetos
def _obj(nome, verts, faces, mat, liso=False):
    me = D.meshes.new(nome)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    m = D.materials.get(mat)
    if m is None:
        raise SystemExit("material ausente no blend: " + mat)
    me.materials.append(m)
    if liso:
        for p in me.polygons:
            p.use_smooth = True
    ob = D.objects.new(nome, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _frame(eixo):
    w = Vector(eixo).normalized()
    up = Vector((0, 0, 1)) if abs(w.z) < 0.9 else Vector((1, 0, 0))
    u = w.cross(up).normalized()
    v = w.cross(u).normalized()
    return u, v, w


def cilindro(nome, base, eixo, comp, diam, mat, n=8, ponta=0.0, liso=True):
    """Cilindro de `base` ao longo de `eixo`; ponta>0 = cone final (pitot)."""
    u, v, w = _frame(eixo)
    b = Vector(base)
    r = diam / 2.0
    verts, faces = [], []
    aneis = [(0.0, r), (comp - ponta, r)] if ponta > 0 else [(0.0, r), (comp, r)]
    if ponta > 0:
        aneis.append((comp, r * 0.25))
    for (t, rr) in aneis:
        c = b + w * t
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append(c + u * (rr * math.cos(a)) + v * (rr * math.sin(a)))
    na = len(aneis)
    for k in range(na - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append([k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i])
    faces.append(list(range(n - 1, -1, -1)))
    faces.append(list(range((na - 1) * n, na * n)))
    return _obj(nome, verts, faces, mat, liso)


def lamina(nome, base, dir_corda, dir_alt, corda_raiz, corda_topo, alt,
           varredura, esp, mat):
    """Blade de antena: 8 vertices, raiz->topo com varredura para tras."""
    cd = Vector(dir_corda).normalized()
    al = Vector(dir_alt).normalized()
    nr = cd.cross(al).normalized()
    b = Vector(base)
    e = nr * (esp / 2.0)
    r0, r1 = b - cd * (corda_raiz / 2.0), b + cd * (corda_raiz / 2.0)
    t = b + al * alt + cd * varredura
    t0, t1 = t - cd * (corda_topo / 2.0), t + cd * (corda_topo / 2.0)
    verts = [r0 + e, r1 + e, t1 + e, t0 + e, r0 - e, r1 - e, t1 - e, t0 - e]
    faces = [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2],
             [2, 6, 7, 3], [3, 7, 4, 0]]
    return _obj(nome, verts, faces, mat)


def caixa(nome, centro, du, dv, dw, dims, mat):
    u, v, w = Vector(du).normalized(), Vector(dv).normalized(), Vector(dw).normalized()
    c = Vector(centro)
    hx, hy, hz = dims[0] / 2.0, dims[1] / 2.0, dims[2] / 2.0
    verts = []
    for sw in (-1, 1):
        for sv in (-1, 1):
            for su in (-1, 1):
                verts.append(c + u * (su * hx) + v * (sv * hy) + w * (sw * hz))
    faces = [[0, 1, 3, 2], [6, 7, 5, 4], [0, 2, 6, 4], [1, 5, 7, 3],
             [0, 4, 5, 1], [2, 3, 7, 6]]
    return _obj(nome, verts, faces, mat)


def disco(nome, centro, normal, diam, mat, n=10):
    u, v, w = _frame(normal)
    c = Vector(centro)
    r = diam / 2.0
    verts = [c + w * 0.005]
    for i in range(n):
        a = 2 * math.pi * i / n
        verts.append(c + u * (r * math.cos(a)) + v * (r * math.sin(a)))
    faces = [[0, 1 + i, 1 + (i + 1) % n] for i in range(n)]
    return _obj(nome, verts, faces, mat, liso=True)


def domo(nome, centro, raio, mat, alt=None, n=8, aneis=3, eixo=(0, 0, 1)):
    """Meia-cupula (beacon). `alt` estica/encolhe no eixo."""
    u, v, w = _frame(eixo)
    alt = alt if alt is not None else raio
    c = Vector(centro)
    verts, faces = [], []
    for k in range(aneis):
        ph = (math.pi / 2.0) * k / aneis
        rr, zz = raio * math.cos(ph), alt * math.sin(ph)
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append(c + u * (rr * math.cos(a)) + v * (rr * math.sin(a)) + w * zz)
    verts.append(c + w * alt)
    topo = len(verts) - 1
    for k in range(aneis - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append([k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i])
    for i in range(n):
        j = (i + 1) % n
        faces.append([(aneis - 1) * n + i, (aneis - 1) * n + j, topo])
    return _obj(nome, verts, faces, mat, liso=True)


def malha_avaliada(nome):
    ob = D.objects.get(nome)
    if ob is None:
        return []
    oe = ob.evaluated_get(DG)
    me = oe.to_mesh()
    mw = oe.matrix_world
    vs = [mw @ v.co for v in me.vertices]
    oe.to_mesh_clear()
    return vs


def fuga(vs, coord, c0, c1, lado=1.0):
    """Ponto de max x com coord (y ou z) do vertice em [c0,c1] (lado aplica em y)."""
    if coord == "y":
        sel = [p for p in vs if c0 <= lado * p.y <= c1]
    else:
        sel = [p for p in vs if c0 <= p.z <= c1]
    return max(sel, key=lambda p: p.x) if sel else None


def borda_ataque(vs, y0, y1, lado=1.0):
    sel = [p for p in vs if y0 <= lado * p.y <= y1]
    return min(sel, key=lambda p: p.x) if sel else None


# ================================================================== SONDAS
tot = {"objs": 0, "verts": 0}


def registra(ob):
    tot["objs"] += 1
    tot["verts"] += len(ob.data.vertices)


if "pitot" in AP:
    for cfg in AP["pitot"]:
        x, z = cfg["x"], cfg["z"]
        for lado, suf in ((-1, "E"), (1, "D")):
            loc, nrm = no_casco(x, "ladoE" if lado < 0 else "ladoD", z)
            if loc is None:
                log("pitot %s SEM HIT em x=%.2f z=%.2f" % (suf, x, z))
                continue
            base = loc + nrm * 0.02
            # sonda apontando para -x; CinzaEscuro: pitot le ESCURO na foto
            registra(cilindro("Apx_Pitot%s_%s" % (cfg.get("id", ""), suf),
                              base, (-1, 0, -0.08), cfg.get("comp", 0.38 * ESC),
                              cfg.get("diam", 0.045 * ESC), "CinzaEscuro",
                              n=6, ponta=0.10 * ESC))
    log("pitots:", len(AP["pitot"]) * 2)

if "aoa" in AP:
    for cfg in AP["aoa"]:
        x, z = cfg["x"], cfg["z"]
        for lado, suf in ((-1, "E"), (1, "D")):
            loc, nrm = no_casco(x, "ladoE" if lado < 0 else "ladoD", z)
            if loc is None:
                continue
            base = loc + nrm * 0.015
            registra(domo("Apx_AoAHub%s_%s" % (cfg.get("id", ""), suf), base,
                          0.05 * ESC, "CinzaEscuro", alt=0.05 * ESC, n=6,
                          aneis=2, eixo=nrm))
            registra(lamina("Apx_AoAVane%s_%s" % (cfg.get("id", ""), suf),
                            base + nrm * 0.05 * ESC, (-1, 0, 0), nrm,
                            0.16 * ESC, 0.10 * ESC, 0.02, -0.05 * ESC,
                            0.012, "CinzaEscuro"))
    log("aoa:", len(AP["aoa"]) * 2)

if "tat" in AP:
    cfg = AP["tat"]
    loc, nrm = no_casco(cfg["x"], "lado" + cfg.get("lado", "D"), cfg["z"])
    if loc is not None:
        base = loc + nrm * 0.015
        registra(lamina("Apx_TAT", base, (-1, 0, 0), nrm, 0.10 * ESC,
                        0.07 * ESC, 0.10 * ESC, -0.04 * ESC, 0.03, "CinzaEscuro"))
        log("tat em x=%.2f" % cfg["x"])

# ================================================================== ANTENAS
if "vhf_ventre" in AP:
    cfg = AP["vhf_ventre"]
    loc, nrm = no_casco(cfg["x"], "keel", cfg.get("z", -D_FUS / 2.0))
    if loc is not None:
        registra(lamina("Apx_VHF_Ventre", loc + nrm * 0.01, (1, 0, 0), nrm,
                        0.34 * ESC, 0.10 * ESC, 0.26 * ESC, 0.10 * ESC,
                        0.03, "LATAM_Branco"))
        log("vhf ventral em x=%.2f (quilha z=%.2f)" % (cfg["x"], loc.z))

if "gps" in AP:
    for cfg in AP["gps"]:
        loc, nrm = no_casco(cfg["x"], "crown")
        if loc is not None:
            registra(caixa("Apx_GPS%s" % cfg.get("id", ""), loc + nrm * 0.01,
                           (1, 0, 0), (0, 1, 0), nrm,
                           (0.34 * ESC, 0.22 * ESC, 0.075 * ESC), "LATAM_Branco"))
    log("gps:", len(AP["gps"]))

if "tcas" in AP:
    cfg = AP["tcas"]
    loc, nrm = no_casco(cfg["x"], "crown")
    if loc is not None:
        registra(lamina("Apx_TCAS_Dorso", loc + nrm * 0.01, (1, 0, 0), nrm,
                        0.22 * ESC, 0.10 * ESC, 0.14 * ESC, 0.05 * ESC,
                        0.03, "LATAM_Branco"))
        log("tcas dorsal em x=%.2f" % cfg["x"])

# ==================================================================== LUZES
if "beacon_dorso" in AP:
    x = AP["beacon_dorso"]["x"]
    loc, nrm = no_casco(x, "crown")
    if loc is not None:
        registra(domo("Apx_BeaconDorso", loc + nrm * 0.005, 0.09 * ESC,
                      "LuzVermelha", alt=0.11 * ESC, eixo=nrm))
        log("beacon dorsal em x=%.2f z=%.2f" % (x, loc.z))

if "beacon_ventre" in AP:
    x = AP["beacon_ventre"]["x"]
    loc, nrm = no_casco(x, "keel", AP["beacon_ventre"].get("z", -D_FUS / 2.0))
    if loc is not None:
        registra(domo("Apx_BeaconVentre", loc + nrm * 0.005, 0.09 * ESC,
                      "LuzVermelha", alt=0.11 * ESC, eixo=nrm))
        log("beacon ventral em x=%.2f z=%.2f" % (x, loc.z))

OBJETOS = AP.get("objetos", {})
ASAS = OBJETOS.get("asa", ["Asas"])
ESTABS = OBJETOS.get("estab", ["EstabHorizontal"])
DERIVAS = OBJETOS.get("deriva", ["Deriva"])

if "estrobo_asa" in AP:
    cfg = AP["estrobo_asa"]
    vs = sum((malha_avaliada(n) for n in ASAS), [])
    for lado, suf in ((-1, "Esq"), (1, "Dir")):
        p = fuga(vs, "y", cfg["y0"], cfg["y1"], lado)
        if p is None:
            continue
        registra(caixa("Apx_Estrobo" + suf, p + Vector((0.03, 0, 0)),
                       (1, 0, 0), (0, 1, 0), (0, 0, 1),
                       (0.16 * ESC, 0.07 * ESC, 0.07 * ESC), "LuzBranca"))
    log("estrobos de asa em |y| %.1f-%.1f" % (cfg["y0"], cfg["y1"]))

if AP.get("estrobo_cauda", False):
    ref = D.objects.get("LuzCauda")
    if ref is not None:
        bb = [ref.matrix_world @ Vector(c) for c in ref.bound_box]
        c = sum(bb, Vector()) / 8.0
        registra(caixa("Apx_EstroboCauda", c + Vector((0.10, 0, -0.14)),
                       (1, 0, 0), (0, 1, 0), (0, 0, 1),
                       (0.10, 0.08, 0.08), "LuzBranca"))
        log("estrobo de cauda junto a LuzCauda (x=%.1f)" % c.x)

if "farol_asa_raiz" in AP:
    cfg = AP["farol_asa_raiz"]
    vs = sum((malha_avaliada(n) for n in ASAS), [])
    for lado, suf in ((-1, "E"), (1, "D")):
        p = borda_ataque(vs, cfg["y0"], cfg["y1"], lado)
        if p is None:
            continue
        registra(disco("Apx_FarolAsa" + suf, p + Vector((-0.02, 0, -0.03)),
                       (-1, 0, -0.15), 0.30 * ESC, "LuzBranca"))
    log("farois de raiz de asa em |y| %.1f-%.1f" % (cfg["y0"], cfg["y1"]))

if "farol_taxi" in AP:
    cfg = AP["farol_taxi"]
    perna = next((D.objects[n] for n in cfg["objeto"].split("|")
                  if n in D.objects), None)
    if perna is not None:
        bb = [perna.matrix_world @ Vector(c) for c in perna.bound_box]
        xc = min(b.x for b in bb)
        yc = (min(b.y for b in bb) + max(b.y for b in bb)) / 2.0
        z = cfg["z"]
        registra(caixa("Apx_FarolTaxiCx", (xc - 0.06, yc, z), (1, 0, 0),
                       (0, 1, 0), (0, 0, 1), (0.12, 0.34 * ESC, 0.16 * ESC),
                       "StrutMetal"))
        for lado in (-1, 1):
            registra(disco("Apx_FarolTaxi" + ("E" if lado < 0 else "D"),
                           (xc - 0.125, yc + lado * 0.08 * ESC, z),
                           (-1, 0, -0.08), 0.14 * ESC, "LuzBranca"))
        log("farol de taxi na perna do nariz z=%.2f" % z)

if "luz_logo" in AP:
    cfg = AP["luz_logo"]
    vs = sum((malha_avaliada(n) for n in ESTABS), [])
    for lado, suf in ((-1, "E"), (1, "D")):
        sel = [p for p in vs if cfg["y0"] <= lado * p.y <= cfg["y1"]]
        if not sel:
            continue
        xm = sum(p.x for p in sel) / len(sel)
        topo = max(sel, key=lambda p: p.z - 4.0 * abs(p.x - xm))
        registra(disco("Apx_LuzLogo" + suf, topo + Vector((0, 0, 0.012)),
                       (0.0, -0.35 * lado, 1.0), 0.13, "LuzBranca"))
    log("logo lights no estab |y| %.1f-%.1f" % (cfg["y0"], cfg["y1"]))

# ==================================================================== WICKS
if "wicks" in AP:
    cfg = AP["wicks"]
    COMP = cfg.get("comp", 0.45)
    DIAM = cfg.get("diam", 0.016)
    verts, faces = [], []

    def wick(p, direcao):
        u, v, w = _frame(direcao)
        b = Vector(p)
        i0 = len(verts)
        r = DIAM / 2.0
        for t in (0.0, COMP):
            c = b + w * t
            for k in range(5):
                a = 2 * math.pi * k / 5
                verts.append(tuple(c + u * (r * math.cos(a)) + v * (r * math.sin(a))))
        for k in range(5):
            j = (k + 1) % 5
            faces.append([i0 + k, i0 + j, i0 + 5 + j, i0 + 5 + k])
        faces.append([i0 + 5 + k for k in range(4, -1, -1)])

    n_asa, n_est, n_der = 0, 0, 0
    va = sum((malha_avaliada(n) for n in ASAS), [])
    a0, a1, na = cfg["asa"]
    for lado in (-1, 1):
        for i in range(int(na)):
            y = a0 + (a1 - a0) * (i + 0.5) / na
            p = fuga(va, "y", y - 0.35, y + 0.35, lado)
            if p is not None:
                wick(p + Vector((-0.03, 0, 0)), (1, 0, -0.15))
                n_asa += 1
    ve = sum((malha_avaliada(n) for n in ESTABS), [])
    e0, e1, ne = cfg["estab"]
    for lado in (-1, 1):
        for i in range(int(ne)):
            y = e0 + (e1 - e0) * (i + 0.5) / ne
            p = fuga(ve, "y", y - 0.3, y + 0.3, lado)
            if p is not None:
                wick(p + Vector((-0.03, 0, 0)), (1, 0, -0.1))
                n_est += 1
    vd = sum((malha_avaliada(n) for n in DERIVAS), [])
    d0, d1, nd = cfg["deriva"]
    for i in range(int(nd)):
        z = d0 + (d1 - d0) * (i + 0.5) / nd
        p = fuga(vd, "z", z - 0.35, z + 0.35)
        if p is not None:
            wick(p + Vector((-0.03, 0, 0)), (1, 0, 0.12))
            n_der += 1
    if verts:
        ob = _obj("Apx_Wicks", verts, faces, "CinzaEscuro")
        registra(ob)
    log("wicks: asa %d  estab %d  deriva %d (contagem tipica declarada)"
        % (n_asa, n_est, n_der))

# =================================================================== WIPERS
if "wipers" in AP:
    cfg = AP["wipers"]
    yp, zp = cfg["pivo_yz"]
    # ang NEGATIVO = braco inclina para FORA (777: o t_up do plano tangente ja
    # deriva para dentro no nariz bojudo, e o parque real e quase paralelo)
    fora = cfg["ang"] < 0
    ang = math.radians(abs(cfg["ang"]))
    c_braco = cfg.get("comp_braco", 0.55 * ESC)
    c_lamina = cfg.get("comp_lamina", 0.60 * ESC)
    for lado, suf in ((-1, "E"), (1, "D")):
        loc, nrm = lancar((-4.0, lado * yp, zp), (1, 0, 0))
        if loc is None:
            log("wiper %s SEM HIT (y=%.2f z=%.2f)" % (suf, yp, zp))
            continue
        base = loc + nrm * 0.03
        t_up = (Vector((0, 0, 1)) - nrm * nrm.z).normalized()
        t_lado = nrm.cross(t_up).normalized()
        if t_lado.y * lado > 0:          # aponta para DENTRO (centro)
            t_lado = -t_lado
        if fora:
            t_lado = -t_lado
        d_braco = (t_lado * math.cos(ang) + t_up * math.sin(ang)).normalized()
        registra(domo("Apx_WiperPivo" + suf, base, 0.035, "CinzaEscuro",
                      alt=0.04, n=6, aneis=2, eixo=nrm))
        registra(cilindro("Apx_WiperBraco" + suf, base + nrm * 0.01, d_braco,
                          c_braco, 0.035, "CinzaEscuro", n=6))
        # lamina PARALELA ao braco no parque (foto: braco+lamina leem como uma
        # linha so; a perpendicular anterior lia como martelo cruzando o
        # montante central)
        d_lam = d_braco.cross(nrm).normalized()
        pt = base + d_braco * (c_braco * 0.85 + c_lamina * 0.35) + nrm * 0.005
        registra(caixa("Apx_WiperLamina" + suf,
                       pt + d_lam * 0.035, d_braco, d_lam, nrm,
                       (c_lamina, 0.05, 0.035), "CinzaEscuro"))
    log("wipers: parque %d graus, braco %.2f m" % (cfg["ang"], c_braco))

# =================================================================== DRENOS
if "drenos" in AP:
    for cfg in AP["drenos"]:
        x = cfg["x"]
        loc, nrm = no_casco(x, "keel", cfg.get("z", -D_FUS / 2.0))
        if loc is None:
            log("dreno x=%.1f SEM HIT" % x)
            continue
        registra(lamina("Apx_Dreno%s" % cfg.get("id", ""), loc + nrm * 0.01,
                        (1, 0, 0), nrm, 0.30, 0.16, 0.15, 0.12, 0.05,
                        "LATAM_Branco"))
    log("drenos: %d (protrusao 0.15 m — estimativa declarada, trem_familia)"
        % len(AP["drenos"]))

# ------------------------------------------------------------------ veredito
log("TOTAL: %d objetos Apx_, %d vertices adicionados" % (tot["objs"], tot["verts"]))
if MODO == "medir":
    log("modo medir — nada salvo")
    raise SystemExit(0)
bpy.ops.wm.save_mainfile()
log("SALVO", bpy.data.filepath)
