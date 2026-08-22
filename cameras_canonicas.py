#!/usr/bin/env python3
"""Padrao de camera do gate visual - PADRAO DE FROTA (v2).

Executado DENTRO do Blender. Constroi as OITO cameras canonicas de qualquer
aeronave do repositorio a partir da propria geometria, sem tocar no .blend em
disco (as cameras sao montadas em memoria, na hora do render).

------------------------------------------------------------------------------
POR QUE ISTO EXISTE
------------------------------------------------------------------------------
O gate julgava toda a frota atraves de duas cameras curtas e proximas:
CamNariz a 45 mm / 18 m de um nariz de 6,2 m, CamFrontal a 70 mm / 27 m. Nenhuma
foto de referencia e assim - fotografia de aeronave e teleobjetiva a 90-250 m.

A distorcao nao e estetica, e mensuravel: a 18 m a superficie proxima do nariz
(1,85 m mais perto que a linha de centro) e ampliada ~9%, enquanto o barril
10 m atras e reduzido ~38%. O resultado le como "bico estufado em corpo que
afina" - exatamente a queixa que o dono levantou no 777-300ER, cuja geometria
estava certa contra o APR (coroa/quilha dentro de 0,03 m). A camera era a re.

A perspectiva depende SO DA DISTANCIA relativa a profundidade do assunto; a
distancia focal apenas recorta. Logo o padrao fixa a DISTANCIA e deriva a lente.

------------------------------------------------------------------------------
O PADRAO
------------------------------------------------------------------------------
Sensor 36 mm (full frame) em todas.

  D_LONGE = clamp(3,00 x L, 90, 250) m   angulos de aeronave inteira
                                         (Frontal, Perfil, Hero, Cauda, Barriga)
  D_PERTO = clamp(1,25 x L, 70, 150) m   close-ups do nariz (Nariz, HeadOn)

L = comprimento total da aeronave. A distancia escala com o tamanho, como na
fotografia real: a A319 fica a 102 m, o 777-300ER a 222 m.

A lente sai da distancia e do ENQUADRAMENTO preservado. Para cada angulo o
enquadramento e a largura W do quadro no plano do alvo; W e lido da camera
existente (W = 36 x d / f), de modo que o assunto ocupa o mesmo pedaco de
mundo que antes. Entao:

  f_nova = 36 x D / W

Como W' = 36 x D / f_nova = W, aplicar duas vezes da o mesmo resultado.

O QUE SE PRESERVA AO AFASTAR. Nao o angulo de elevacao - a ALTURA. Puxar a
camera para tras ao longo do proprio raio multiplica o desnivel pela mesma razao
da distancia: CamNariz, 2,2 m acima do alvo a 13 m, iria para 11,7 m acima a
70 m, virando um plano de guindaste; e CamBarriga da A319 iria para 1,9 m ABAIXO
da pista. O que um fotografo faz e andar para tras, nao subir. Entao preserva-se

  - o AZIMUTE (rotacao em torno da vertical: e invariante de escala), e
  - o DESNIVEL dz em METROS entre camera e alvo,

e a distancia horizontal vira sqrt(D^2 - dz^2). O angulo de elevacao achata
sozinho, que e exatamente o que acontece quando se afasta na mesma altura.

REGRA DO PISO. Se ainda assim a camera cair abaixo de PISO_CAM acima da pista,
dz sobe ate o piso. Na frota atual isso so morde a CamBarriga, por 3 cm.

VALIDACAO DO PADRAO. A regra D_PERTO reproduz sozinha a CamHeadOn que o agente
do 777 tinha achado a mao: 1,25 x 73,94 = 92,4 m contra os 93 m dele, e a mira
na altura do para-brisa a partir da altura do olho da 2,99 graus contra os
3 graus dele. Uma regra que reencontra um numero medido por outro caminho.

------------------------------------------------------------------------------
OS OITO ANGULOS
------------------------------------------------------------------------------
  CamFrontal   3/4 frontal        proporcao do nariz, para-brisa, motores
  CamNariz     close-up do NARIZ  vidro, radome, contorno da porta 1
  CamPerfil    perfil puro        comparacao direta com a foto de referencia
  CamHero      3/4 classico       leitura geral; e o render que entrega
  CamCauda     cauda              faixa da deriva, cunha do casco, matricula
  CamBarriga   frontal baixa      barriga, carenagem, trem, nacelles
  CamHeadOn    de frente          para-brisa e secao frontal - o unico angulo
                                  que pega o "V" do vidro do 777
  CamEstibordo perfil de ESTIBORDO o outro bordo - o unico angulo que ve a
                                  metade da pele que o gate nunca julgou

CamEstibordo foi ACRESCENTADA. As sete cameras anteriores tinham todas a
componente y negativa (CamPerfil -1.0, CamNariz -0.687, CamFrontal -0.459,
CamHero -0.630, CamCauda -0.719, CamBarriga -0.585) ou estavam no eixo
(CamHeadOn). Em outras palavras: o gate julgava sempre BOMBORDO, e a pele de
estibordo de toda a frota nunca passou por nenhum quadro.

O que se escondia ali era uma classe inteira de defeito, nao um caso. A pintura
do casco e uma textura em (x, theta) e o mesmo u vale para os dois bordos, mas
visto de estibordo o +x da pele aponta para a ESQUERDA da tela: qualquer marca
assimetrica tem de ser espelhada naquele lado. Quando nao e, ela sai ao
contrario - e nenhum dos sete angulos podia dizer. Assim passaram a matricula e
o titulo de tipo do 767-300ER, do 767-300F e do 777-300ER (lendo 'YWC-CC',
'AL635N', 'GUM-TP') e a matricula da A320neo, esta por espelhamento a MAIS.
O lockup do 787-8 ja tinha sido pego uma vez pelo mesmo caminho, com uma camera
de estibordo montada a mao para a ocasiao; o que faltava era torna-la padrao.

E o PERFIL de estibordo, e nao um 3/4, porque o perfil poe a pele inteira de
frente: lockup, titulo, matricula, portas e janelas no mesmo quadro, e a
comparacao direta com CamPerfil - a mesma foto espelhada - torna a diferenca
obvia sem precisar ler letra por letra.

CamNariz foi RE-ESPECIFICADA. Nas cinco Airbus ela estava em (11; 7,5; 1,6)
olhando para tras: o quadro caia sobre a PORTA 1 e as janelas de cabine, e o
para-brisa ficava recortado na borda. O painel "NOSE CLOSE-UP" da folha de
contato nunca mostrou o para-brisa de nenhuma Airbus - foi assim que um defeito
de para-brisa sobreviveu a um gate. Agora todas as nove usam a mesma geometria
Boeing: 44,2 graus fora do eixo do nariz, 9,6 graus acima do alvo, a frente.
"""
import math

import bpy
from mathutils import Vector

# ---------------------------------------------------------------- constantes

SENSOR = 36.0        # mm, full frame
PISO_CAM = 1.30      # m acima da pista: altura minima de qualquer camera
OLHO = 1.60          # m acima da pista: altura da CamHeadOn (altura do olho)

FATOR_LONGE = 3.00
LIM_LONGE = (90.0, 250.0)
FATOR_PERTO = 1.25
LIM_PERTO = (70.0, 150.0)

# Enquadramento dos dois angulos re-especificados, em multiplos do diametro da
# fuselagem (o nariz escala com o barril, nao com o comprimento: o nariz da
# A321 e o mesmo da A319).
W_NARIZ = 2.20       # x diametro da fuselagem
W_HEADON = 1.40      # x diametro da fuselagem
Z_HEADON = 0.12      # mira: z_centro + este fator x diametro (altura do vidro)
DZ_NARIZ = 0.46      # desnivel camera-alvo, x diametro (era 0,44-0,48 na frota)

# Ate que preenchimento de quadro a silhueta da fuselagem conta como "cabia
# inteira". Acima disso o angulo e um recorte deliberado e preserva-se W.
LIM_SILHUETA = 1.05

# Direcao unitaria DO ALVO PARA A CAMERA. Define a identidade de cada angulo.
# Medidas nos masters antes da correcao; so a distancia mudou.
DIRECOES = {
    "airbus": {
        "CamFrontal": (-0.8884, -0.4585, -0.0229),
        "CamNariz": (-0.7066, -0.6871, 0.1672),
        "CamPerfil": (0.0, -1.0, 0.0),
        "CamHero": (-0.7760, -0.6300, 0.0320),
        "CamCauda": (0.6930, -0.7190, -0.0510),
        "CamBarriga": (-0.8100, -0.5850, -0.0410),
        "CamEstibordo": (0.0, 1.0, 0.0),
    },
    "boeing": {
        "CamFrontal": (-0.8890, -0.4590, -0.0090),
        "CamNariz": (-0.7066, -0.6871, 0.1672),
        "CamPerfil": (0.0, -1.0, 0.0),
        "CamHero": (-0.7760, -0.6300, 0.0350),
        "CamCauda": (0.6190, -0.7590, 0.2000),
        "CamBarriga": (-0.8100, -0.5850, -0.0220),
        "CamEstibordo": (0.0, 1.0, 0.0),
    },
}

# Alvo (empty) de cada camera. CamPerfil e CamHeadOn ganham alvo proprio.
ALVOS = {
    "CamFrontal": "CamAlvoFrontal",
    "CamNariz": "CamAlvoNariz",
    "CamPerfil": "CamAlvoPerfil",
    "CamHero": "CamAlvo",
    "CamCauda": "CamAlvoCauda",
    "CamBarriga": "CamAlvoBarriga",
    "CamHeadOn": "CamAlvoHeadOn",
    "CamEstibordo": "CamAlvoEstibordo",
}

PERTO = ("CamNariz", "CamHeadOn")     # usam D_PERTO; o resto usa D_LONGE

# Enquadramento de emergencia (x L) quando a aeronave nao tem a camera ainda.
W_PADRAO = {
    "CamFrontal": 0.25,
    "CamPerfil": 1.10,
    "CamHero": 0.90,
    "CamCauda": 0.45,
    "CamBarriga": 0.60,
}

# Desnivel de emergencia (x diametro da fuselagem), mesma situacao.
DZ_PADRAO = {
    "airbus": {"CamFrontal": -0.06, "CamPerfil": 0.0, "CamHero": 0.40,
               "CamCauda": -0.25, "CamBarriga": -0.15},
    "boeing": {"CamFrontal": -0.06, "CamPerfil": 0.0, "CamHero": 0.40,
               "CamCauda": 1.85, "CamBarriga": -0.15},
}

VISTAS = [
    ("CamFrontal", "render_frontal.png"),
    ("CamNariz", "render_nariz.png"),
    ("CamPerfil", "render_perfil.png"),
    ("CamHero", "render_hero.png"),
    ("CamCauda", "render_cauda.png"),
    ("CamBarriga", "render_frente_baixa.png"),
    ("CamHeadOn", "render_headon.png"),
    # depois de CamPerfil: reaproveita o enquadramento dela (ver `aplicar`)
    ("CamEstibordo", "render_estibordo.png"),
]

CENARIO = ("pista", "cenario", "scenario", "scenery", "ground", "solo", "hdri")


# ------------------------------------------------------------------ medicao

def _caixa(ob):
    return [ob.matrix_world @ Vector(c) for c in ob.bound_box]


def medir(scene=None):
    """Dimensoes da aeronave que alimentam o padrao."""
    scene = scene or bpy.context.scene

    fus = bpy.data.objects.get("Fuselagem")
    if fus is None:
        cand = [o for o in scene.objects if o.type == "MESH"
                and not any(s in o.name.lower() for s in CENARIO)]
        fus = max(cand, key=lambda o: sum(
            (max(p[i] for p in _caixa(o)) - min(p[i] for p in _caixa(o))) for i in (0,)))
    b = _caixa(fus)
    d_fus = max(p.y for p in b) - min(p.y for p in b)
    z_c = (max(p.z for p in b) + min(p.z for p in b)) / 2.0
    x_tip = min(p.x for p in b)

    pista = bpy.data.objects.get("Pista")
    if pista is not None:
        z_solo = max(p.z for p in _caixa(pista))
    else:
        z_solo = min(min(p.z for p in _caixa(o)) for o in scene.objects
                     if o.type == "MESH" and not any(s in o.name.lower() for s in CENARIO))

    xs = []
    for o in scene.objects:
        if o.type != "MESH" or any(s in o.name.lower() for s in CENARIO):
            continue
        c = _caixa(o)
        xs += [min(p.x for p in c), max(p.x for p in c)]
    L = max(xs) - min(xs)

    familia = "airbus" if d_fus < 4.6 else "boeing"
    return {
        "L": L, "x_tip": x_tip, "d_fus": d_fus, "z_c": z_c, "z_solo": z_solo,
        "familia": familia,
        "D_longe": min(max(FATOR_LONGE * L, LIM_LONGE[0]), LIM_LONGE[1]),
        "D_perto": min(max(FATOR_PERTO * L, LIM_PERTO[0]), LIM_PERTO[1]),
    }


# ------------------------------------------------------------- construcao

def _empty(nome, loc):
    ob = bpy.data.objects.get(nome)
    if ob is None or ob.type != "EMPTY":
        ob = bpy.data.objects.new(nome, None)
        ob.empty_display_size = 0.5
        bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    ob.parent = None
    return ob


def _camera(nome):
    ob = bpy.data.objects.get(nome)
    if ob is None or ob.type != "CAMERA":
        cam = bpy.data.cameras.new(nome)
        ob = bpy.data.objects.new(nome, cam)
        bpy.context.scene.collection.objects.link(ob)
    ob.parent = None
    ob.data.type = "PERSP"
    ob.data.sensor_fit = "AUTO"
    ob.data.sensor_width = SENSOR
    ob.data.shift_x = 0.0
    ob.data.shift_y = 0.0
    ob.data.clip_start = 0.1
    ob.data.clip_end = 4000.0
    ob.data.dof.use_dof = False
    return ob


def _mirar(cam, alvo):
    for c in list(cam.constraints):
        cam.constraints.remove(c)
    con = cam.constraints.new("TRACK_TO")
    con.target = alvo
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"


def _vertices_fuselagem(scene):
    """Vertices avaliados da fuselagem - o assunto comum a todos os angulos."""
    fus = bpy.data.objects.get("Fuselagem")
    if fus is None:
        return []
    dg = bpy.context.evaluated_depsgraph_get()
    ev = fus.evaluated_get(dg)
    me = ev.to_mesh()
    if me is None:
        return []
    M = ev.matrix_world
    vs = [M @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return vs


def _ganho(P, alvo, res_x, res_y, verts):
    """Fracao do quadro ocupada pela silhueta, POR MILIMETRO de lente.

    preenchimento = ganho x f. Vale 1 quando a silhueta encosta na borda.
    Compara-se ganho_velho x f_velha com ganho_novo para achar a lente que
    mantem o assunto ocupando o mesmo pedaco do quadro.
    """
    P = Vector(P)
    fwd = (Vector(alvo) - P).normalized()
    right = fwd.cross(Vector((0.0, 0.0, 1.0)))
    if right.length < 1e-9:
        right = Vector((1.0, 0.0, 0.0))
    right.normalize()
    up = right.cross(fwd)
    meia_l = SENSOR / 2.0
    meia_a = meia_l * res_y / float(res_x)      # sensor_fit AUTO, res_x > res_y
    g = 0.0
    for v in verts:
        d = v - P
        z = d.dot(fwd)
        if z <= 0.05:
            continue
        g = max(g, abs(d.dot(right)) / z / meia_l, abs(d.dot(up)) / z / meia_a)
    return g


def _original(nome):
    """(posicao, lente) da camera como esta no .blend, antes de mexer."""
    ob = bpy.data.objects.get(nome)
    if ob is None or ob.type != "CAMERA" or ob.data.type != "PERSP":
        return None
    return Vector(ob.matrix_world.translation), float(ob.data.lens)


def _posicionar(alvo_pos, azimute, dz, D, z_solo):
    """Camera a distancia D do alvo: azimute preservado, desnivel dz em metros.

    Se a camera cair abaixo de z_solo + PISO_CAM, dz sobe ate o piso.
    """
    alvo = Vector(alvo_pos)
    piso = False
    z_piso = z_solo + PISO_CAM
    if alvo.z + dz < z_piso:
        dz = z_piso - alvo.z
        piso = True
    dz = max(-D * 0.999, min(D * 0.999, dz))
    horiz = math.sqrt(max(D * D - dz * dz, 0.0))
    h = Vector((azimute[0], azimute[1], 0.0))
    if h.length < 1e-9:
        h = Vector((1.0, 0.0, 0.0))
    h.normalize()
    return Vector((alvo.x + h.x * horiz, alvo.y + h.y * horiz, alvo.z + dz)), piso


def aplicar(scene=None, verbose=True):
    """Monta as oito cameras canonicas no padrao de frota. Devolve o relatorio."""
    scene = scene or bpy.context.scene
    bpy.context.view_layer.update()   # matrix_world fresca: senao `antes` mente
    m = medir(scene)
    dirs = DIRECOES[m["familia"]]
    rel = {"medidas": m, "cameras": {}}

    # fotografia do estado original ANTES de mexer em nada: e dela que saem o
    # enquadramento e o desnivel a preservar.
    antes = {nome: _original(nome) for nome, _ in VISTAS}
    verts = _vertices_fuselagem(scene)
    res_x = scene.render.resolution_x
    res_y = scene.render.resolution_y
    if res_y > res_x:                     # o padrao do gate e paisagem 16:9
        res_x, res_y = 16, 9

    for nome, _fn in VISTAS:
        nome_alvo = ALVOS[nome]

        # --- alvo -----------------------------------------------------------
        alvo = bpy.data.objects.get(nome_alvo)
        if nome == "CamPerfil":
            velha = bpy.data.objects.get("CamPerfil")
            if alvo is not None and alvo.type == "EMPTY":
                pos = tuple(alvo.matrix_world.translation)
            elif velha is not None:
                p = velha.matrix_world.translation
                pos = (p.x, 0.0, p.z)
            else:
                pos = (m["x_tip"] + m["L"] / 2.0, 0.0, m["z_c"] + 0.3)
        elif nome == "CamEstibordo":
            # o mesmo ponto de mira de CamPerfil (y = 0, logo nao espelha)
            pos = tuple(rel["cameras"]["CamPerfil"]["alvo"])
        elif nome == "CamHeadOn":
            nariz = bpy.data.objects.get("CamAlvoNariz")
            x = nariz.matrix_world.translation.x if nariz is not None \
                else m["x_tip"] + 0.45 * m["d_fus"]
            pos = (x, 0.0, m["z_c"] + Z_HEADON * m["d_fus"])
        else:
            if alvo is None or alvo.type != "EMPTY":
                raise RuntimeError("alvo ausente: %s" % nome_alvo)
            pos = tuple(alvo.matrix_world.translation)
        alvo = _empty(nome_alvo, pos)

        # --- enquadramento e desnivel ---------------------------------------
        orig = antes[nome]
        if nome == "CamNariz":
            W = W_NARIZ * m["d_fus"]
            dz = DZ_NARIZ * m["d_fus"]
        elif nome == "CamHeadOn":
            W = W_HEADON * m["d_fus"]
            dz = (m["z_solo"] + OLHO) - pos[2]
        elif nome == "CamEstibordo":
            # NAO se deriva de camera nenhuma no .blend (nao existe em nenhum) e
            # NAO leva enquadramento proprio: copia o de CamPerfil, ja resolvido
            # nesta mesma passagem. As duas so servem de par se forem a MESMA
            # foto espelhada - e a comparacao que faz o defeito saltar.
            cp = rel["cameras"]["CamPerfil"]
            W = cp["W"]
            dz = cp["loc"][2] - cp["alvo"][2]
        elif orig is not None:
            W = SENSOR * (orig[0] - Vector(pos)).length / orig[1]
            dz = orig[0].z - pos[2]
        else:
            W = W_PADRAO[nome] * m["L"]
            dz = DZ_PADRAO[m["familia"]][nome] * m["d_fus"]

        # --- distancia, posicao, lente --------------------------------------
        D = m["D_perto"] if nome in PERTO else m["D_longe"]
        if nome == "CamHeadOn":
            # de frente, na linha de centro, na altura do olho
            horiz = math.sqrt(max(D * D - dz * dz, 0.0))
            P = Vector((pos[0] - horiz, 0.0, pos[2] + dz))
            piso = False
        else:
            P, piso = _posicionar(pos, dirs[nome], dz, D, m["z_solo"])

        d_real = (P - Vector(pos)).length
        lente = SENSOR * d_real / W
        modo = "quadro"

        # Preservar W mantem o mesmo pedaco de MUNDO no quadro, mas achatar a
        # perspectiva encolhe a silhueta: as partes proximas deixam de ser
        # ampliadas. Nos angulos em que a fuselagem cabia inteira no quadro,
        # casa-se o PREENCHIMENTO da silhueta em vez de W, e o assunto volta a
        # ocupar o quadro como antes.
        if orig is not None and verts and nome != "CamEstibordo":
            g_velho = _ganho(orig[0], pos, res_x, res_y, verts)
            cheio = g_velho * orig[1]
            if cheio <= LIM_SILHUETA:
                g_novo = _ganho(P, pos, res_x, res_y, verts)
                if g_novo > 1e-9:
                    lente = cheio / g_novo
                    W = SENSOR * d_real / lente
                    modo = "silhueta %.2f" % cheio

        cam = _camera(nome)
        cam.location = P
        cam.rotation_euler = (0.0, 0.0, 0.0)
        _mirar(cam, alvo)
        cam.data.lens = lente

        el = math.degrees(math.asin(max(-1.0, min(1.0, (P.z - pos[2]) / max(d_real, 1e-9)))))
        rel["cameras"][nome] = {
            "d": d_real, "lens": lente, "W": W, "modo": modo,
            "loc": tuple(round(v, 3) for v in P), "alvo": tuple(round(v, 3) for v in pos),
            "elev": el, "piso": piso, "h_pista": P.z - m["z_solo"],
        }

    if verbose:
        print("[cam] %s  L=%.2f m  d_fus=%.2f m  pista z=%.2f  D_longe=%.1f  D_perto=%.1f"
              % (m["familia"], m["L"], m["d_fus"], m["z_solo"], m["D_longe"], m["D_perto"]))
        for nome, _ in VISTAS:
            c = rel["cameras"][nome]
            print("[cam] %-11s d=%7.1f m  f=%7.1f mm  quadro=%6.2f m  elev=%+6.2f deg"
                  "  h=%5.2f m  %s%s" % (nome, c["d"], c["lens"], c["W"], c["elev"],
                                         c["h_pista"], c["modo"],
                                         "  (PISO)" if c["piso"] else ""))
    return rel


# --------------------------------------------------------------- render

def renderizar(pasta, larg=1600, amostras=96, alvos=None, scene=None):
    """Aplica o padrao e renderiza os oito angulos em `pasta`."""
    import os
    scene = scene or bpy.context.scene
    # resolucao ANTES de aplicar: o preenchimento da silhueta depende do aspecto
    scene.render.resolution_x = larg
    scene.render.resolution_y = int(round(larg * 9 / 16))
    scene.render.resolution_percentage = 100
    rel = aplicar(scene)
    scene.render.engine = "CYCLES"
    if hasattr(scene, "cycles"):
        scene.cycles.samples = amostras
        scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "PNG"
    for nome, fn in VISTAS:
        if alvos and fn not in alvos and nome not in alvos:
            continue
        scene.camera = bpy.data.objects[nome]
        scene.render.filepath = os.path.join(pasta, fn)
        bpy.ops.render.render(write_still=True)
        print("[render] %s" % fn)

    # procedencia da camera ao lado dos renders: a folha de contato rotula cada
    # painel com a lente e a distancia que o produziram.
    import json
    with open(os.path.join(pasta, "cameras_gate.json"), "w") as f:
        json.dump({"medidas": {k: (v if isinstance(v, str) else round(float(v), 4))
                               for k, v in rel["medidas"].items()},
                   "cameras": {k: {kk: (vv if isinstance(vv, (str, bool, tuple, list))
                                        else round(float(vv), 4))
                                   for kk, vv in v.items()}
                               for k, v in rel["cameras"].items()}}, f, indent=1)
    return rel
