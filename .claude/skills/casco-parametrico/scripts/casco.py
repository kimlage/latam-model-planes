"""Construtor de casco paramétrico — gaiola esparsa + Catmull-Clark.

Roda dentro do Blender (cole em `execute_blender_code` via MCP, ou
`blender arquivo.blend --python casco.py`). Destilado do código que produziu os
cascos aprovados do A320neo (v9/v10) e do 787-9 (v3).

A ideia central: os vértices NÃO descrevem a superfície, descrevem a gaiola de
controle. Quem descreve a superfície é o subsurf. Ver o SKILL.md ao lado para
por que isso importa.

Uso mínimo:

    aneis = aneis_de_spec(json.load(open("spec_b789.json")))
    fus = construir_casco(aneis, nome="Fuselagem", material="LATAM_Branco")
    uv_cilindrica(fus.data, aneis, comprimento_uv=63.5)
"""
import math

import bpy
import bmesh

SEG = 32          # segmentos por anel
COMP = 1.0064     # compensa o encolhimento do Catmull-Clark num anel de 32 lados


# ---------------------------------------------------------------- seções

def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def secao_eliptica(theta, rz, ry):
    """Seção elíptica simples — barril e cauda."""
    return ry * math.sin(theta), rz * math.cos(theta)


def secao_ovoide(theta, rz, ry, perfil_mestre, altura_ref, mistura=1.0):
    """Seção de ovo: lobo inferior cheio, ombros altos.

    `perfil_mestre(profundidade_abaixo_da_crista) -> meia_largura_normalizada`,
    tabelado a partir do desenho frontal. É isso que faz a seção ter os ombros
    ~14% mais largos que a elipse e a largura máxima ligeiramente ACIMA da
    meia-altura — a diferença entre um casco que lê como avião de verdade e um
    tubo.

    `mistura` faz a transição suave do círculo (ponta do nariz) para o ovo.
    """
    ct = math.cos(theta)
    z = rz * ct
    prof = (rz - z) / max(2 * rz, 1e-6) * altura_ref
    hw_ovo = perfil_mestre(prof)
    hw_circ = math.sqrt(max(0.0, 1.0 - ct * ct))
    hw = ((1 - mistura) * hw_circ + mistura * hw_ovo) * ry
    return math.copysign(hw, math.sin(theta)), z


def pinca_lobo_superior(x, cos_theta, sobe_em, sobe_ao_longo_de,
                        desce_em, desce_ao_longo_de, forca, expoente):
    """Estreita o lobo SUPERIOR na zona do cockpit.

    Sem isso o para-brisa não 'vira para a frente' e o nariz lê como bico de
    pato. Só se aplica acima da meia-altura (cos_theta > 0).

    Os seis parâmetros são os do spec — não os derive de outra coisa, porque
    eles foram ajustados contra a vista frontal do desenho. Valores do A320neo
    (spec_a320.json -> lobo_superior_pinca_v10):

        pinca_lobo_superior(x, ct, 1.45, 1.1, 3.1, 1.9, forca=0.46, expoente=1.6)
    """
    if cos_theta <= 0:
        return 1.0
    g = (smoothstep((x - sobe_em) / sobe_ao_longo_de)
         * (1.0 - smoothstep((x - desce_em) / desce_ao_longo_de)))
    return 1.0 - forca * g * (smoothstep(cos_theta) ** expoente)


# ---------------------------------------------------------------- gaiola

def aneis_de_spec(spec, passo_barril=3.0):
    """Monta a lista de anéis (x, zc, rz, ry) a partir de um spec_<tipo>.json.

    Espera `nariz_estacoes` = [[x, crown, keel, meia_largura], ...] e
    `cauda` = [[x, centro_z, raio], ...] — formato do spec_b789.json.

    O barril entra com anéis IDÊNTICOS espaçados regularmente. Isso não é
    desperdício: é o que garante seção constante de verdade. Amostrar o barril
    de dados extraídos faz ele ondular sob a tinta brilhante.
    """
    aneis = []
    for x, crown, keel, w2 in spec["nariz_estacoes"][1:]:
        aneis.append((x, (crown + keel) / 2, (crown - keel) / 2, max(w2, 0.05)))
    x0 = spec["nariz_estacoes"][-1][0]
    x1 = spec["cauda"][0][0]
    rz = spec["nariz_estacoes"][-1][1] - (spec["nariz_estacoes"][-1][1]
                                          + spec["nariz_estacoes"][-1][2]) / 2
    ry = spec["nariz_estacoes"][-1][3]
    n = max(1, int((x1 - x0) / passo_barril))
    for i in range(1, n + 1):
        aneis.append((x0 + i * (x1 - x0) / n, 0.0, rz, ry))
    for x, zc, r in spec["cauda"][1:]:
        aneis.append((x, zc, r, 0.96 * r))
    return aneis


def construir_casco(aneis, nome="Fuselagem", material=None, colecao="01_Estrutura",
                    ponta_frente=None, ponta_tras=None, forma=None,
                    subsurf_render=3, subsurf_view=2):
    """Loft dos anéis + tampas em ponta + subsurf.

    `forma(x, theta, zc, rz, ry) -> (y, z)` permite trocar a seção por estação
    (ovo no nariz, elipse no barril e na cauda). Sem ela, tudo vira elipse.
    """
    bm = bmesh.new()
    anelverts = []
    for (x, zc, rz, ry) in aneis:
        linha = []
        for s in range(SEG):
            th = 2 * math.pi * s / SEG
            if forma is None:
                y, z = secao_eliptica(th, rz, ry)
            else:
                y, z = forma(x, th, zc, rz, ry)
            linha.append(bm.verts.new((x, y * COMP, zc + z * COMP)))
        anelverts.append(linha)

    for a, b in zip(anelverts[:-1], anelverts[1:]):
        for s in range(SEG):
            bm.faces.new((a[s], a[(s + 1) % SEG], b[(s + 1) % SEG], b[s]))

    if ponta_frente is not None:
        v0 = bm.verts.new(ponta_frente)
        for s in range(SEG):
            bm.faces.new((anelverts[0][s], v0, anelverts[0][(s + 1) % SEG]))
    if ponta_tras is not None:
        vN = bm.verts.new(ponta_tras)
        for s in range(SEG):
            bm.faces.new((anelverts[-1][s], anelverts[-1][(s + 1) % SEG], vN))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    if material:
        me.materials.append(bpy.data.materials[material])

    ob = bpy.data.objects.get(nome)
    if ob:
        # Trocar o mesh preserva o objeto — e com ele modificadores, alvos de
        # shrinkwrap e qualquer referência por nome espalhada em outros scripts.
        antigo = ob.data
        ob.data = me
        bpy.data.meshes.remove(antigo)
    else:
        ob = bpy.data.objects.new(nome, me)
        col = bpy.data.collections.get(colecao)
        if col is None:
            col = bpy.data.collections.new(colecao)
            bpy.context.scene.collection.children.link(col)
        col.objects.link(ob)

    tem_sub = False
    for m in ob.modifiers:
        if m.type == 'SUBSURF':
            m.levels, m.render_levels = subsurf_view, subsurf_render
            tem_sub = True
    if not tem_sub:
        m = ob.modifiers.new("Sub", 'SUBSURF')
        m.levels, m.render_levels = subsurf_view, subsurf_render
    return ob


# ---------------------------------------------------------------- UV

def uv_cilindrica(me, aneis, comprimento_uv, nome="UVMap"):
    """UV (x, θ) — a base de toda a livery pintada em textura.

    u = x/comprimento, v = (θ+π)/2π medido em torno do CENTRO DA SEÇÃO naquele
    x (não do eixo z=0), senão a cauda, que sobe, distorce a textura.

    O passo final costura o wrap: faces que cruzam v=0/1 precisam ter os
    vértices do lado baixo empurrados para +1, ou aparece uma faixa espelhada
    da textura inteira na barriga.
    """
    xs = [a[0] for a in aneis]
    zcs = [a[1] for a in aneis]

    def centro(x):
        for (xa, za), (xb, zb) in zip(zip(xs[:-1], zcs[:-1]), zip(xs[1:], zcs[1:])):
            if xa <= x <= xb:
                f = (x - xa) / max(xb - xa, 1e-9)
                return za + f * (zb - za)
        return zcs[-1] if x > xs[-1] else zcs[0]

    uv = me.uv_layers.get(nome) or me.uv_layers.new(name=nome)
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        zc = centro(co.x)
        th = math.atan2(co.y, co.z - zc) if (abs(co.y) > 1e-9 or abs(co.z - zc) > 1e-9) else 0.0
        uv.data[loop.index].uv = (co.x / comprimento_uv, (th + math.pi) / (2 * math.pi))
    for p in me.polygons:
        vs = [uv.data[li].uv[1] for li in p.loop_indices]
        if max(vs) - min(vs) > 0.5:
            for li in p.loop_indices:
                if uv.data[li].uv[1] < 0.5:
                    uv.data[li].uv = (uv.data[li].uv[0], uv.data[li].uv[1] + 1.0)
    return uv


# ---------------------------------------------------------------- perfis

def naca_espessura(c, t):
    """Meia-espessura NACA de 4 dígitos em c∈[0,1], para lofts de asa/deriva."""
    return 5 * t * (0.2969 * math.sqrt(max(c, 1e-6)) - 0.126 * c
                    - 0.3516 * c * c + 0.2843 * c ** 3 - 0.1015 * c ** 4)


def secao_aerofolio(le, corda, offset_z, queda, t_max, n=16):
    """Contorno fechado de um aerofólio: extradorso LE→TE, intradorso TE→LE."""
    pts = []
    for i in range(n):
        c = i / (n - 1)
        pts.append((le + c * corda, offset_z - queda * c
                    + naca_espessura(c, t_max / corda) * corda))
    for i in range(1, n - 1):
        c = 1 - i / (n - 1)
        pts.append((le + c * corda, offset_z - queda * c
                    - naca_espessura(c, t_max / corda) * corda))
    return pts


def validar_por_raycast(ob, sondas):
    """Confere que a superfície está onde o desenho diz.

    `sondas` = [(origem, direcao, esperado_m), ...]. Depois de qualquer
    reconstrução, algumas sondas custam segundos e pegam casco furado, normal
    invertida ou escala errada antes de gastar um render.
    """
    from mathutils import Vector
    for origem, direcao, esperado in sondas:
        hit, loc, _, _ = ob.ray_cast(Vector(origem), Vector(direcao))[:4]
        if not hit:
            print(f"  SEM HIT em {origem} -> {direcao}")
            continue
        d = (Vector(loc) - Vector(origem)).length
        marca = "ok" if abs(d - esperado) < 0.05 else "FORA"
        print(f"  {origem} -> {d:.3f} m (esperado {esperado:.3f}) {marca}")
