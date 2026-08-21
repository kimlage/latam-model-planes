#!/usr/bin/env python3
"""Exportacao portatil da frota - PADRAO DE FROTA.

Executado DENTRO do Blender, um master por vez, sem tocar o .blend em disco:

    blender -b "<pasta>/<X>_LATAM.blend" --factory-startup \\
        --python export/frota_portatil.py -- --lod web --saida export

O orquestrador e `export_frota.py`, na raiz. Este modulo e o equivalente de
`cameras_canonicas.py` para exportacao: a REGRA vive aqui, os numeros por
aeronave saem da propria geometria, e nao ha um ramo por aeronave em lugar
nenhum. Uma aeronave nova (o 767-300F) entra com uma linha em FROTA.

------------------------------------------------------------------------------
POR QUE ISTO EXISTE
------------------------------------------------------------------------------
O entregavel do repositorio e um .blend por aeronave. Fora do Blender ele nao
abre. glTF 2.0 binario (.glb) e o formato que a web entende, mas exportar o
master direto perde a aeronave inteira - e isso foi MEDIDO, nao suposto:

    materiais 30 -> 17,  texturas 8 -> 3,  livery: sumiu

A causa esta em `FuselagemPaint`, que e a pintura de todas as nove aeronaves.
Ela nao e um Principled: e uma arvore de TRES Principled misturados por canais
da NoseMask, com a Base Color saindo de um Mix de LiveryFac sobre LiveryTex. O
glTF so sabe representar UM Principled por material. O exportador nao avisa -
ele escreve um material cinza e segue.

Entao a etapa central deste modulo nao e chamar o exportador: e ACHAR os
materiais que o glTF nao sabe escrever e ASSAR (bake) cada um numa textura que
ele sabe. O criterio e estrutural, nao uma lista de nomes:

    o Surface do Output tem de vir direto de um Principled, e as entradas
    escalares dele so podem vir de Image Texture / Normal Map

Na frota atual isso pega exatamente dois materiais - `FuselagemPaint` nas nove e
`CinzaAsa` nas quatro Boeing - e pegara sozinho o que o 767-300F trouxer.

------------------------------------------------------------------------------
OS DOIS NIVEIS DE DETALHE
------------------------------------------------------------------------------
170 mil triangulos com 46 megapixels de textura nao e um asset de web. Mas a
resposta nao e "decimar ate parecer aceitavel": o casco e Catmull-Clark sobre
uma gaiola esparsa, entao o nivel de subdivisao E o botao de LOD, e ele preserva
UV, materiais e a silhueta melhor do que qualquer decimador.

  alta  subsurf como o autor deixou, textura nativa, PNG, sem Draco
        para desktop, DCC e uso offline
  web   subsurf limitado a 1, textura ate 2048 px, JPEG, Draco
        para three.js - os numeros medidos estao no README da pasta

------------------------------------------------------------------------------
O QUE SAI DA CENA ANTES DE EXPORTAR
------------------------------------------------------------------------------
  - `Pista`: e o chao do gate, nao a aeronave (e o material Tarmac vai junto)
  - objetos com hide_render: os LogoLATAM_*/Reg_*/Mark* sao a ORIGEM da livery,
    geometria de trabalho que virou textura. No 777 sao 67.518 triangulos
    invisiveis; na A320neo, 303.258. Exporta-los dobraria o arquivo com uma
    copia 3D da pintura que ja esta na textura.
  - cameras, luzes e os empties de mira do gate
  - `scenario/`: nunca. Ver o README da pasta - a geometria do aeroporto vem do
    OpenStreetMap e carrega ODbL share-alike, obrigacao diferente e mais estrita
    que a CC BY 4.0 do resto. Os masters nao linkam o cenario (verificado: nenhum
    tem biblioteca externa), entao aqui isso e uma garantia, nao uma remocao.

------------------------------------------------------------------------------
EIXO
------------------------------------------------------------------------------
Blender e +Z para cima; glTF, USD e FBX sao +Y. As tres exportacoes recebem a
conversao explicita - inclusive a USD, cujo padrao no Blender e MANTER o Z-up e
que sairia deitada no AR Quick Look. A prova nao e a flag: e a caixa envolvente
lida de volta do arquivo por `verificar_glb.py`, onde o comprimento tem de cair
em X, a altura em Y e a envergadura em Z.

A altura tambem e re-datumada: o repositorio usa z = 0 no meio da secao
constante (README, "Coordinate frame"), o que deixaria a aeronave enterrada 5,7 m
num visualizador que assume chao em y = 0. Um no raiz - um so, com o nome da
aeronave - carrega o deslocamento. x = 0 segue no bico e y = 0 no plano de
simetria, como no repositorio.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import cameras_canonicas  # noqa: E402  - medir() da o L, o diametro e o solo

# --------------------------------------------------------------------- frota

# Uma linha por aeronave. `L_ref` e o comprimento publicado, em metros: existe
# para que a verificacao tenha contra o que comparar a caixa lida do .glb.
# `opcional` marca a aeronave que ainda esta sendo construida - ela e pulada
# sem erro ate o .blend existir.
FROTA = {
    "A319":    {"pasta": "airbus A319",      "blend": "A319_LATAM.blend",
                "nome": "Airbus A319 (ceo)", "matricula": "PT-TMT", "L_ref": 33.84},
    "A320ceo": {"pasta": "airbus A320ceo",   "blend": "A320ceo_LATAM.blend",
                "nome": "Airbus A320ceo", "matricula": "CC-BFO", "L_ref": 37.57},
    "A320neo": {"pasta": "airbus A320neo",   "blend": "A320neo_LATAM.blend",
                "nome": "Airbus A320neo", "matricula": "PT-TMN", "L_ref": 37.57},
    "A321ceo": {"pasta": "airbus A321ceo",   "blend": "A321ceo_LATAM.blend",
                "nome": "Airbus A321-231 (ceo)", "matricula": "PT-MXP", "L_ref": 44.51},
    "A321neo": {"pasta": "airbus A321neo",   "blend": "A321neo_LATAM.blend",
                "nome": "Airbus A321neo (ACF)", "matricula": "PS-LBA", "L_ref": 44.51},
    "B763":    {"pasta": "boeing 767-300ER", "blend": "B763_LATAM.blend",
                "nome": "Boeing 767-300ER", "matricula": "CC-CWY", "L_ref": 54.94},
    "B77W":    {"pasta": "boeing 777-300ER", "blend": "B77W_LATAM.blend",
                "nome": "Boeing 777-300ER", "matricula": "PT-MUG", "L_ref": 73.86},
    "B788":    {"pasta": "boeing 787-8",     "blend": "B788_LATAM.blend",
                "nome": "Boeing 787-8 Dreamliner", "matricula": "CC-BBF", "L_ref": 56.72},
    "B789":    {"pasta": "boeing 787-9",     "blend": "B789_LATAM.blend",
                "nome": "Boeing 787-9 Dreamliner", "matricula": "CC-BGK", "L_ref": 62.81},
    # Em construcao por outra sessao. Entra sozinha quando o master aparecer.
    "B763F":   {"pasta": "boeing 767-300F",  "blend": "B763F_LATAM.blend",
                "nome": "Boeing 767-300F", "matricula": "", "L_ref": 54.94,
                "opcional": True},
}

# --------------------------------------------------------------------- LODs

LODS = {
    "alta": {
        "subsurf": None,        # None = como o autor deixou (render_levels)
        "textura_max": None,    # None = resolucao nativa
        "bake_max": 8192,       # teto do bake; a densidade sai das fontes
        "draco": False,
        "imagem": "AUTO",       # PNG
        "qualidade": 100,
        "rugosidade": "mapa",   # bake da rugosidade como textura
        "rugosidade_max": 2048,  # a rugosidade e ruido de baixa frequencia:
                                 # a 8192 ela era o MAIOR arquivo do .glb (0,76
                                 # MB) sem acrescentar nada visivel
        "formatos": ("glb", "fbx", "obj"),
        "descricao": "fiel - desktop, DCC, uso offline",
    },
    "web": {
        "subsurf": 1,
        "textura_max": 2048,
        "bake_max": 2048,
        "draco": True,
        # PNG, e nao JPEG: MEDIDO. A pintura LATAM e arte vetorial chapada, nao
        # fotografia. A q88 o JPEG deu 0,32 MB de textura contra 0,22 MB de PNG
        # e o .glb inteiro subiu de 404 kB para 512 kB - 27% maior.
        "imagem": "AUTO",
        "qualidade": 88,
        "rugosidade": "media",  # bake pequeno, reduzido a um escalar
        "formatos": ("glb", "usdz"),
        "descricao": "leve - three.js, web, AR",
    },
}

# Objetos que nao sao a aeronave. `Pista` e o chao do gate visual.
NAO_AERONAVE = {"pista", "tarmac", "chao", "ground", "solo", "cenario", "scenario"}

# Tipos que o exportador transforma em malha. MESH nao basta: a matricula da
# porta do trem das cinco Airbus (`RegPortaTrem`) e um objeto FONT, e tratar so
# MESH deixava-a fora do no raiz - ela saia como um SEGUNDO no raiz, 2,4 m
# abaixo do chao, porque nao recebia o deslocamento de datum.
TIPOS_GEO = {"MESH", "CURVE", "SURFACE", "FONT", "META"}

# Colecao cujo nome case com isto nao vai para a exportacao, qualquer que seja o
# conteudo. Hoje a `09_Cenario` de cada master so guarda a Pista e as cameras do
# gate - mas se algum dia um master linkar o aeroporto, a exclusao e estrutural
# e nao depende de alguem lembrar do nome de um objeto. Ver o README: ODbL.
COLECOES_FORA = ("cenario", "scenario", "scenery", "aeroporto", "airport")

DIREITOS = ("LATAM fleet 3D replicas - Kim Lage - CC BY 4.0. "
            "LATAM, Airbus and Boeing marks belong to their owners; "
            "independent non-commercial project, no affiliation. See NOTICE.md.")

# Entradas escalares que o material limpo herda do Principled dominante.
_FORMATO_IMAGEM = "AUTO"   # decidido em preparar(), lido por _exportar_glb()

ESCALARES = ("Metallic", "Roughness", "IOR", "Alpha", "Coat Weight", "Coat Roughness",
             "Specular IOR Level", "Emission Strength")


# ------------------------------------------------------------------ utilidades

def _kwargs_suportados(op, kwargs):
    """Filtra kwargs pelo RNA do operador.

    Os exportadores mudam de propriedade entre versoes do Blender. Perguntar ao
    operador o que ele aceita custa uma linha e evita que a exportacao inteira
    morra por causa de uma flag renomeada.
    """
    validos = {p.identifier for p in op.get_rna_type().properties}
    return {k: v for k, v in kwargs.items() if k in validos}, \
           sorted(set(kwargs) - validos)


def _caixa_mundo(objs):
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for ob in objs:
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
    return lo, hi


def _saida_ativa(ma):
    for nd in ma.node_tree.nodes:
        if nd.type == "OUTPUT_MATERIAL" and nd.is_active_output:
            return nd
    return next((n for n in ma.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None)


def _principled_dominante(ma, no=None, prof=0):
    """Primeiro Principled alcancavel a partir do Output, atravessando misturas.

    Num Mix Shader o "dominante" e o primeiro ramo. Nao e uma escolha estetica:
    nas nove aeronaves o primeiro ramo de `FuselagemPaint` E a pintura, e os
    outros dois sao o vidro e o radome, que a NoseMask isola em pedacos pequenos
    do casco. A Base Color desses pedacos vem do bake de qualquer jeito - so os
    ESCALARES seguem o ramo dominante.
    """
    if prof > 8:
        return None
    if no is None:
        out = _saida_ativa(ma)
        if out is None or not out.inputs["Surface"].is_linked:
            return None
        no = out.inputs["Surface"].links[0].from_node
    if no.type == "BSDF_PRINCIPLED":
        return no
    for s in no.inputs:
        if s.is_linked:
            r = _principled_dominante(ma, s.links[0].from_node, prof + 1)
            if r is not None:
                return r
    return None


def _exportavel(ma):
    """Lista dos motivos pelos quais o glTF NAO representa este material.

    Vazia = o exportador escreve o material fielmente e nao ha o que assar.
    """
    if not ma.node_tree:
        return ["sem node tree"]
    out = _saida_ativa(ma)
    if out is None or not out.inputs["Surface"].is_linked:
        return ["Output sem Surface"]
    origem = out.inputs["Surface"].links[0].from_node
    if origem.type != "BSDF_PRINCIPLED":
        return ["Surface<-%s" % origem.type]
    ruins = []
    for chave in ("Base Color", "Metallic", "Roughness", "Emission Color", "Alpha"):
        s = origem.inputs.get(chave)
        if s is not None and s.is_linked:
            t = s.links[0].from_node.type
            if t not in ("TEX_IMAGE", "NORMAL_MAP"):
                ruins.append("%s<-%s" % (chave, t))
    return ruins


def _carregar(img):
    """Forca a carga dos pixels de uma imagem empacotada.

    Um .blend recem-aberto traz as imagens EMPACOTADAS mas com has_data=False -
    o Blender so as descompacta quando alguem precisa dos pixels. Testar
    has_data cedo demais responde "nao ha imagem" para uma imagem que existe:
    foi assim que a faixa da deriva ficou de fora do .obj e do teto de 2048 px
    na primeira rodada, enquanto as texturas que o bake tinha tocado passaram.
    """
    if img.has_data:
        return True
    try:
        _ = img.pixels[0]                      # a leitura e que descompacta
    except (RuntimeError, IndexError):
        try:
            img.reload()
        except RuntimeError:
            return False
    return img.has_data


def _imagens_do_material(ma):
    return [n.image for n in ma.node_tree.nodes
            if n.type == "TEX_IMAGE" and n.image is not None]


def _cor_plana(soquete, prof=0):
    """Cor de recuo para objeto SEM UV, que nao pode receber textura assada.

    Desce pelo primeiro caminho ate achar um valor constante. Nao e um chute
    cego: nas quatro Boeing o material `CinzaAsa` esta em asas que nao tem
    nenhuma camada de UV, entao o Image Texture dele ja renderiza como um texel
    fixo e o resultado E o valor constante do primeiro ramo do Mix.
    """
    if prof > 8:
        return (0.8, 0.8, 0.8, 1.0)
    if not soquete.is_linked:
        v = soquete.default_value
        try:
            return (v[0], v[1], v[2], v[3] if len(v) > 3 else 1.0)
        except TypeError:
            return (float(v), float(v), float(v), 1.0)
    no = soquete.links[0].from_node
    # SO soquetes habilitados: um ShaderNodeMix carrega as variantes Float,
    # Vector e Rotation escondidas do mesmo "A", e a primeira delas e 0.0 - foi
    # assim que a asa do 777 saiu PRETA na primeira rodada.
    livres = [s for s in no.inputs if s.enabled and not s.is_linked]
    for s in livres:
        if s.type == "RGBA":
            return _cor_plana(s, prof + 1)
    for s in livres:
        if s.type == "VALUE":
            return _cor_plana(s, prof + 1)
    for s in no.inputs:
        if s.enabled and s.is_linked:
            return _cor_plana(s, prof + 1)
    return (0.8, 0.8, 0.8, 1.0)


# ---------------------------------------------------------------------- bake

def _preparar_cycles(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = False
    scene.render.bake.use_selected_to_active = False
    scene.render.bake.margin = 8
    scene.render.bake.use_clear = True


def _assar(ob, ma, tipo, larg, alt, nome, escala_nao_cor=False):
    """Assa `tipo` do material no UV do objeto e devolve a imagem.

    O bake e por (objeto, material): duas asas que compartilham material tem UV
    sobreposto, e assar as duas na mesma imagem faria uma escrever por cima da
    outra. Uma imagem por par custa alguns megabytes e nao tem esse risco.
    """
    img = bpy.data.images.new(nome, larg, alt, alpha=False, float_buffer=False)
    if escala_nao_cor:
        img.colorspace_settings.name = "Non-Color"
    nd = ma.node_tree.nodes.new("ShaderNodeTexImage")
    nd.image = img
    nd.location = (-1400, 600)
    ma.node_tree.nodes.active = nd
    for o in bpy.context.scene.objects:
        if o is not None and o.name in bpy.context.view_layer.objects:
            o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    sc = bpy.context.scene
    sc.render.bake.use_pass_direct = False
    sc.render.bake.use_pass_indirect = False
    sc.render.bake.use_pass_color = True
    bpy.ops.object.bake(type=tipo)
    return img


def _media(img):
    px = list(img.pixels)
    n = len(px) // 4
    if not n:
        return 0.5
    soma = sum(px[i * 4] for i in range(n))
    return soma / n


def _material_limpo(nome, base_cor, base_img, rug_img, rug_valor, principled):
    """Material novo com UM Principled - a forma que o glTF sabe escrever."""
    ma = bpy.data.materials.new(nome)
    ma.use_nodes = True
    nt = ma.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.location = (0, 0)
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])

    if principled is not None:
        for chave in ESCALARES:
            s_novo, s_velho = b.inputs.get(chave), principled.inputs.get(chave)
            if s_novo is not None and s_velho is not None and not s_velho.is_linked:
                s_novo.default_value = s_velho.default_value

    if base_img is not None:
        nd = nt.nodes.new("ShaderNodeTexImage")
        nd.image = base_img
        nd.location = (-400, 200)
        nt.links.new(nd.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = base_cor

    if rug_img is not None:
        nd = nt.nodes.new("ShaderNodeTexImage")
        nd.image = rug_img
        nd.location = (-400, -200)
        nt.links.new(nd.outputs["Color"], b.inputs["Roughness"])
    elif rug_valor is not None:
        b.inputs["Roughness"].default_value = rug_valor
    return ma


def remediar_materiais(scene, lod, rel):
    """Assa todo material que o glTF nao sabe escrever. Devolve o relatorio."""
    uso = {}
    for ob in scene.objects:
        if ob.type not in TIPOS_GEO:
            continue
        for i, ms in enumerate(ob.material_slots):
            if ms.material:
                uso.setdefault(ms.material.name, []).append((ob, i))

    alvos = []
    for nome, pares in sorted(uso.items()):
        ma = bpy.data.materials.get(nome)
        if ma is None:
            continue
        motivos = _exportavel(ma)
        if motivos:
            alvos.append((ma, pares, motivos))
    if not alvos:
        rel["bake"] = []
        return

    _preparar_cycles(scene)
    feito = []
    for ma, pares, motivos in alvos:
        principled = _principled_dominante(ma)
        fontes = _imagens_do_material(ma)
        teto = LODS[lod]["bake_max"]
        if fontes:
            lw = max(i.size[0] for i in fontes)
            lh = max(i.size[1] for i in fontes)
        else:
            lw, lh = 2048, 2048
        k = min(1.0, teto / float(max(lw, lh)))
        bw, bh = max(4, int(lw * k)), max(4, int(lh * k))

        for ob, slot in pares:
            tem_uv = bool(getattr(ob.data, "uv_layers", None))
            copia_nome = "%s__%s" % (ma.name, ob.name)
            base_img = rug_img = None
            rug_valor = None
            base_cor = (0.8, 0.8, 0.8, 1.0)
            if tem_uv:
                # a arvore ORIGINAL tem de estar intacta durante o bake, entao
                # assa-se numa copia e so depois ela e substituida pela limpa
                trabalho = ma.copy()
                trabalho.name = copia_nome + "__bake"
                ob.material_slots[slot].material = trabalho
                base_img = _assar(ob, trabalho, "DIFFUSE", bw, bh,
                                  copia_nome + "_BaseColor")
                principled = _principled_dominante(trabalho) or principled
                if LODS[lod]["rugosidade"] == "mapa":
                    tr = LODS[lod].get("rugosidade_max") or max(bw, bh)
                    kr = min(1.0, tr / float(max(bw, bh)))
                    rug_img = _assar(ob, trabalho, "ROUGHNESS",
                                     max(4, int(bw * kr)), max(4, int(bh * kr)),
                                     copia_nome + "_Roughness", escala_nao_cor=True)
                else:
                    pequena = _assar(ob, trabalho, "ROUGHNESS", 128, 32,
                                     copia_nome + "_RoughProbe", escala_nao_cor=True)
                    rug_valor = _media(pequena)
                    bpy.data.images.remove(pequena)
            else:
                base_cor = _cor_plana(principled.inputs["Base Color"]) if principled \
                    else base_cor

            limpo = _material_limpo(copia_nome, base_cor, base_img, rug_img,
                                    rug_valor, principled)
            ob.material_slots[slot].material = limpo
            feito.append({
                "material": ma.name, "objeto": ob.name, "motivo": "; ".join(motivos),
                "metodo": "bake" if tem_uv else "cor plana",
                "px": [bw, bh] if tem_uv else None,
                "rugosidade": ("mapa" if rug_img else
                               ("escalar %.3f" % rug_valor if rug_valor is not None
                                else "herdada")),
                "cor": [round(c, 4) for c in base_cor] if not tem_uv else None,
            })
            print("[bake] %-28s %-16s %-10s %s"
                  % (ma.name, ob.name, "bake" if tem_uv else "cor plana",
                     "%dx%d" % (bw, bh) if tem_uv else str([round(c, 3) for c in base_cor])))
    rel["bake"] = feito


# ------------------------------------------------------------------ preparacao

def preparar(lod, rel):
    """Deixa a cena com a aeronave e mais nada, no LOD pedido. Devolve medidas."""
    scene = bpy.context.scene
    bpy.context.view_layer.update()

    # --- medidas ANTES de mexer: medir() precisa da Pista para achar o solo ---
    m = cameras_canonicas.medir(scene)
    rel["medidas"] = {"L": round(m["L"], 4), "d_fus": round(m["d_fus"], 4),
                      "z_solo": round(m["z_solo"], 4), "familia": m["familia"],
                      "x_bico": round(m["x_tip"], 4)}
    print("[prep] %s  L=%.2f m  d_fus=%.2f m  solo z=%.2f m"
          % (m["familia"], m["L"], m["d_fus"], m["z_solo"]))

    # --- so a aeronave ------------------------------------------------------
    fora = []
    for ob in list(scene.objects):
        motivo = None
        cols = [c.name.lower() for c in ob.users_collection]
        if ob.type not in TIPOS_GEO:
            motivo = "auxiliar do gate (%s)" % ob.type
        elif ob.hide_render:
            motivo = "hide_render (geometria de origem da livery)"
        elif ob.name.lower() in NAO_AERONAVE:
            motivo = "nao e a aeronave"
        elif any(any(chave in c for chave in COLECOES_FORA) for c in cols):
            motivo = "colecao de cenario (%s)" % ", ".join(cols)
        elif ob.library is not None or (ob.data and getattr(ob.data, "library", None)):
            motivo = "vem de biblioteca externa (cenario)"
        if motivo:
            fora.append((ob.name, ob.type, motivo))
            try:
                bpy.data.objects.remove(ob, do_unlink=True)
            except (RuntimeError, ReferenceError):
                ob.hide_render = True
                scene.collection.objects.unlink(ob)
    rel["removidos"] = [{"nome": n, "tipo": t, "motivo": r} for n, t, r in fora]
    import collections as _c
    rel["tipos_exportados"] = dict(_c.Counter(
        o.type for o in scene.objects if o.type in TIPOS_GEO))
    print("[prep] fora da exportacao: %d objetos" % len(fora))

    malhas = [o for o in scene.objects if o.type in TIPOS_GEO]
    if not malhas:
        raise RuntimeError("nada sobrou para exportar")

    # --- subdivisao ---------------------------------------------------------
    teto = LODS[lod]["subsurf"]
    n_sub = 0
    for ob in malhas:
        for mod in ob.modifiers:
            if mod.type != "SUBSURF":
                continue
            n_sub += 1
            nivel = mod.render_levels if teto is None else min(mod.render_levels, teto)
            # os dois iguais: assim nao importa se o exportador avalia o
            # depsgraph em modo viewport ou render
            mod.levels = nivel
            mod.render_levels = nivel
            mod.show_viewport = True
            mod.show_render = True
    rel["subsurf"] = {"modificadores": n_sub, "teto": teto}

    # --- texturas -----------------------------------------------------------
    tmax = LODS[lod]["textura_max"]
    escaladas = []
    if tmax:
        for img in bpy.data.images:
            if img.users == 0 or img.source == "VIEWER":
                continue
            w, h = img.size
            if w == 0 or max(w, h) <= tmax:
                continue
            if not _carregar(img):
                print("[prep] textura %s sem pixels: nao escalada" % img.name)
                continue
            k = tmax / float(max(w, h))
            nw, nh = max(1, int(round(w * k))), max(1, int(round(h * k)))
            img.scale(nw, nh)
            escaladas.append({"nome": img.name, "de": [w, h], "para": [nw, nh]})
            print("[prep] textura %-14s %dx%d -> %dx%d" % (img.name, w, h, nw, nh))
    rel["texturas_escaladas"] = escaladas

    # --- materiais que o glTF nao sabe escrever -----------------------------
    remediar_materiais(scene, lod, rel)

    # --- formato das imagens ------------------------------------------------
    # JPEG so onde nao ha alfa. Uma textura que alimenta o Alpha de algum
    # material perderia a mascara e a aeronave ganharia buracos - entao a
    # pergunta e feita ao node tree, nao ao numero de canais do arquivo.
    if LODS[lod]["imagem"] == "JPEG":
        com_alfa = set()
        for ma in bpy.data.materials:
            if not ma.node_tree:
                continue
            for nd in ma.node_tree.nodes:
                if nd.type != "BSDF_PRINCIPLED":
                    continue
                s_a = nd.inputs.get("Alpha")
                if s_a is not None and s_a.is_linked:
                    for n2 in ma.node_tree.nodes:
                        if n2.type == "TEX_IMAGE" and n2.image:
                            com_alfa.add(n2.image.name)
        global _FORMATO_IMAGEM
        # so se NENHUMA imagem alimenta um Alpha e que se pode forcar JPEG no
        # exportador inteiro; havendo alguma, AUTO preserva o PNG de todas
        _FORMATO_IMAGEM = "AUTO" if com_alfa else "JPEG"
        for img in bpy.data.images:
            if img.users and img.name not in com_alfa and _carregar(img):
                img.file_format = "JPEG"
        rel["formato_imagem"] = _FORMATO_IMAGEM
        rel["imagens_com_alfa"] = sorted(com_alfa)

    # --- no raiz e datum de altura ------------------------------------------
    lo, hi = _caixa_mundo(malhas)
    raiz = bpy.data.objects.new(rel["slug"], None)
    raiz.empty_display_size = 1.0
    scene.collection.objects.link(raiz)
    conjunto = set(malhas)
    for ob in malhas:
        # `parent is None` NAO basta: um objeto pode estar preso a um pai que
        # nao vai para a exportacao (fora da cena, ou removido acima). Nas cinco
        # Airbus era o `RegPortaTrem`, que saiu como um SEGUNDO no raiz e ficou
        # 2,4 m abaixo do chao porque nao recebeu o deslocamento de datum.
        if ob.parent is not None and ob.parent in conjunto:
            continue
        mundo = ob.matrix_world.copy()
        ob.parent = raiz
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_world = mundo          # raiz ainda esta na origem
    raiz.location = (0.0, 0.0, -m["z_solo"])
    bpy.context.view_layer.update()

    rel["caixa_blender"] = {
        "min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi],
        "tamanho": [round(hi[i] - lo[i], 4) for i in range(3)],
        "deslocamento_z": round(-m["z_solo"], 4),
    }
    rel["n_objetos"] = len(malhas)
    soltos = [o.name for o in malhas if o.parent is not raiz and o.parent not in conjunto]
    if soltos:
        raise RuntimeError("objetos sem raiz: %s" % soltos)

    # --- triangulos avaliados, contados aqui e nao adivinhados ---------------
    dg = bpy.context.evaluated_depsgraph_get()
    tris = 0
    for ob in malhas:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        if me:
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
            ev.to_mesh_clear()
    rel["triangulos_blender"] = tris

    usadas = set()
    for ob in malhas:
        for ms in ob.material_slots:
            if ms.material and ms.material.node_tree:
                for nd in ms.material.node_tree.nodes:
                    if nd.type == "TEX_IMAGE" and nd.image is not None:
                        usadas.add(nd.image.name)
    mp = 0.0
    for img in bpy.data.images:
        if img.name in usadas and img.size[0]:
            mp += img.size[0] * img.size[1] / 1e6
    rel["megapixels"] = round(mp, 2)
    print("[prep] %d objetos  %d triangulos  %.2f MP de textura"
          % (len(malhas), tris, mp))
    return m


# ----------------------------------------------------------------- exportacao

def _exportar_glb(caminho, lod):
    cfg = LODS[lod]
    kw = dict(
        filepath=caminho, export_format="GLB", export_apply=True, export_yup=True,
        export_image_format=_FORMATO_IMAGEM, export_jpeg_quality=cfg["qualidade"],
        export_image_quality=cfg["qualidade"],
        export_draco_mesh_compression_enable=cfg["draco"],
        export_draco_mesh_compression_level=6,
        export_draco_position_quantization=14,
        export_draco_normal_quantization=10,
        export_draco_texcoord_quantization=12,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
        export_extras=False, export_copyright=DIREITOS,
        use_selection=False, use_visible=False, use_renderable=False,
    )
    kw, ignorados = _kwargs_suportados(bpy.ops.export_scene.gltf, kw)
    if ignorados:
        print("[glb] flags nao suportadas nesta versao: %s" % ignorados)
    bpy.ops.export_scene.gltf(**kw)


def _exportar_usdz(caminho):
    kw = dict(
        filepath=caminho, export_materials=True, export_textures_mode="NEW",
        export_meshes=True, export_lights=False, export_cameras=False,
        export_subdivision="TESSELLATE", evaluation_mode="RENDER",
        # o padrao do Blender MANTEM Z-up: sem isto a aeronave sai deitada no
        # AR Quick Look, que assume Y-up
        convert_orientation=True, export_global_up_selection="Y",
        export_global_forward_selection="NEGATIVE_Z",
        relative_paths=True, root_prim_path="/root", triangulate_meshes=True,
        convert_world_material=False,
    )
    kw, ignorados = _kwargs_suportados(bpy.ops.wm.usd_export, kw)
    if ignorados:
        print("[usdz] flags nao suportadas nesta versao: %s" % ignorados)
    bpy.ops.wm.usd_export(**kw)


def _exportar_fbx(caminho):
    kw = dict(
        filepath=caminho, path_mode="COPY", embed_textures=True,
        use_mesh_modifiers=True, use_mesh_modifiers_render=True,
        # OTHER cobre curva/texto/metaball, convertidos em malha na saida. Sem
        # ele o FBX das cinco Airbus vinha com 800 triangulos e um material a
        # MENOS que o GLB - o exportador descartava em silencio o `RegPortaTrem`,
        # que e um objeto FONT. Pego pela reimportacao, nao pela leitura.
        object_types={"MESH", "EMPTY", "OTHER"}, axis_up="Y", axis_forward="-Z",
        bake_space_transform=False, use_triangles=False, apply_unit_scale=True,
    )
    kw, ignorados = _kwargs_suportados(bpy.ops.export_scene.fbx, kw)
    if ignorados:
        print("[fbx] flags nao suportadas nesta versao: %s" % ignorados)
    bpy.ops.export_scene.fbx(**kw)


def _exportar_obj(caminho):
    kw = dict(
        filepath=caminho, export_materials=True, path_mode="RELATIVE",
        apply_modifiers=True, export_eval_mode="DAG_EVAL_RENDER",
        export_uv=True, export_normals=True, export_triangulated_mesh=True,
        up_axis="Y", forward_axis="NEGATIVE_Z",
    )
    kw, ignorados = _kwargs_suportados(bpy.ops.wm.obj_export, kw)
    if ignorados:
        print("[obj] flags nao suportadas nesta versao: %s" % ignorados)
    bpy.ops.wm.obj_export(**kw)


# FBX e OBJ nao sabem ler uma imagem que so existe na memoria do Blender. Como
# TODA a livery da frota e gerada (packed) ou assada aqui, sem este passo o
# .obj sai sem uma unica linha map_Kd e o .fbx embute so 2 das 4 texturas -
# ambos MEDIDOS antes de existir esta funcao.
PRECISA_DISCO = {"fbx", "obj"}


def _gravar_texturas(destino, slug, rel):
    """Escreve em <destino>/textures_<slug>/ toda imagem usada e aponta o filepath.

    Uma pasta POR AERONAVE: os nomes de textura sao os mesmos nas nove
    (`FinSashD`, `FuselagemPaint__Fuselagem_BaseColor`), entao uma pasta comum
    faria a ultima exportacao sobrescrever a pintura de todas as anteriores e o
    .obj do 777 apontaria para o casco do 787.
    """
    pasta = os.path.join(destino, "textures_%s" % slug)
    if os.path.isdir(pasta):
        for f in os.listdir(pasta):
            os.remove(os.path.join(pasta, f))
    os.makedirs(pasta, exist_ok=True)
    # so os materiais REALMENTE atribuidos a objetos da cena: os originais
    # substituidos pelo bake continuam em bpy.data com usuarios, e escreveriam
    # NoseMask/LiveryTex/PanelBump que nenhum material exportado le mais
    usadas = set()
    for ob in bpy.context.scene.objects:
        if ob.type not in TIPOS_GEO:
            continue
        for ms in ob.material_slots:
            if not ms.material or not ms.material.node_tree:
                continue
            for nd in ms.material.node_tree.nodes:
                if nd.type == "TEX_IMAGE" and nd.image is not None:
                    usadas.add(nd.image.name)
    escritas = []
    for img in bpy.data.images:
        if img.name not in usadas or not _carregar(img):
            continue
        ext = ".jpg" if img.file_format == "JPEG" else ".png"
        seguro = "".join(c if c.isalnum() or c in "._-" else "_" for c in img.name)
        caminho = os.path.join(pasta, seguro + ext)
        img.filepath_raw = caminho
        img.save()
        img.filepath = caminho
        escritas.append(os.path.relpath(caminho, destino))
    rel["texturas_em_disco"] = escritas
    print("[tex] %d texturas gravadas em %s" % (len(escritas), pasta))


ESCRITORES = {
    "glb": (".glb", lambda c, lod: _exportar_glb(c, lod)),
    "usdz": (".usdz", lambda c, lod: _exportar_usdz(c)),
    "fbx": (".fbx", lambda c, lod: _exportar_fbx(c)),
    "obj": (".obj", lambda c, lod: _exportar_obj(c)),
}


def exportar(slug, lod, pasta_saida, rel):
    destino = os.path.join(pasta_saida, lod)
    os.makedirs(destino, exist_ok=True)
    if PRECISA_DISCO & set(LODS[lod]["formatos"]):
        _gravar_texturas(destino, slug, rel)
    saidas = {}
    for fmt in LODS[lod]["formatos"]:
        ext, escrever = ESCRITORES[fmt]
        caminho = os.path.join(destino, "%s_%s%s" % (slug, lod, ext))
        escrever(caminho, lod)
        # OBJ e um trio (.obj/.mtl/texturas): o tamanho util e a soma
        bytes_ = os.path.getsize(caminho) if os.path.exists(caminho) else 0
        extras = []
        if fmt == "obj":
            mtl = caminho[:-4] + ".mtl"
            if os.path.exists(mtl):
                bytes_ += os.path.getsize(mtl)
                extras.append(os.path.basename(mtl))
            tex = os.path.join(destino, "textures_%s" % slug)
            if os.path.isdir(tex):
                for f in os.listdir(tex):
                    bytes_ += os.path.getsize(os.path.join(tex, f))
        saidas[fmt] = {"arquivo": os.path.relpath(caminho, pasta_saida),
                       "bytes": bytes_, "extras": extras}
        print("[out] %-5s %-34s %8.2f MB" % (fmt, os.path.basename(caminho),
                                             bytes_ / 1e6))
    rel["saidas"] = saidas


# ------------------------------------------------------------------------ main

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    lod = "web"
    saida = os.path.join(RAIZ, "export")
    relatorio = None
    i = 0
    while i < len(argv):
        if argv[i] == "--lod":
            lod = argv[i + 1]
            i += 2
        elif argv[i] == "--saida":
            saida = argv[i + 1]
            i += 2
        elif argv[i] == "--relatorio":
            relatorio = argv[i + 1]
            i += 2
        else:
            i += 1
    if lod not in LODS:
        raise SystemExit("LOD desconhecido: %s (ha %s)" % (lod, list(LODS)))

    blend = os.path.basename(bpy.data.filepath)
    slug = next((s for s, d in FROTA.items() if d["blend"] == blend), None)
    if slug is None:
        raise SystemExit("%s nao esta em FROTA" % blend)

    rel = {"slug": slug, "lod": lod, "blend": blend,
           "nome": FROTA[slug]["nome"], "matricula": FROTA[slug]["matricula"],
           "L_ref": FROTA[slug]["L_ref"], "blender": bpy.app.version_string}
    print("[export] %s  LOD %s  (%s)" % (slug, lod, LODS[lod]["descricao"]))
    preparar(lod, rel)
    exportar(slug, lod, saida, rel)
    if relatorio:
        with open(relatorio, "w") as f:
            json.dump(rel, f, indent=1)
    print("[export] FIM %s/%s" % (slug, lod))


if __name__ == "__main__":
    main()
