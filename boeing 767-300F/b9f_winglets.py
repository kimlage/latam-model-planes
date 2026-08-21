"""Etapa 9 (cargueiro) — pintura dos winglets.

/Applications/Blender.app/Contents/MacOS/Blender -b \
    "boeing 767-300F/B763F_LATAM_CARGO.blend" \
    --python "boeing 767-300F/b9f_winglets.py"

Os winglets blended da LATAM Cargo sao BICOLORES e as duas faces sao
DIFERENTES: face EXTERNA indigo, face INTERNA CORAL, com a secao baixa da
transicao branca.  Isso nao e o que a frota de passageiros faz — o spec do
767-300ER descreve 'face interna BRANCA com logo LATAM indigo'.

Medido na unica foto que mostra as duas faces no mesmo quadro:
refs/ref_N536LA_2021.jpg (jounigripen, CC BY 2.0, 2021-05-07), uma vista de
baixo em que o winglet de bombordo mostra a face externa (indigo) e o de
estibordo a face interna (coral).  Confere com N420LA em SJO 2026-01-24.

O objeto Asas e uma asa so, espelhada por modificador; atribuir por sinal da
NORMAL em y no lado base leva a atribuicao certa para os dois lados, porque o
espelho inverte a normal junto com a geometria.
"""
import bpy

# ARMADILHA: Base Color de um BSDF e LINEAR, nao sRGB.  Jogar #2A0088 e #ED1651
# direto divididos por 255 renderiza o winglet ROXO e ROSA-CHOQUE — foi o que a
# folha de contato mostrou na primeira passada.  Os materiais de marca que ja
# existiam no .blend guardam os valores lineares (LATAM_Indigo.001 =
# 0.0232/0/0.2462, LATAM_Coral.001 = 0.8469/0.008/0.0823); estes aqui sao a mesma
# conversao feita explicitamente.
def _srgb(h):
    def c(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (c((h >> 16) & 0xFF), c((h >> 8) & 0xFF), c(h & 0xFF), 1.0)


INDIGO = _srgb(0x2A0088)
CORAL = _srgb(0xED1651)

Y_WINGLET = 23.90     # a partir daqui e winglet (a ponta da asa esta em 23.785)
Z_TINTA = 1.15        # abaixo disto a transicao fica clara, como na foto
                      # (medido em ref_N536LA_2021: o coral da face interna
                      #  desce ate quase o encontro com a ponta da asa; so
                      #  fica clara uma lasca no proprio arco de transicao)


def material(nome, cor):
    m = bpy.data.materials.get(nome)
    if m is None:
        m = bpy.data.materials.new(nome)
        m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = cor
    # mesmos parametros da deriva (Deriva_Sash_E/D): superficie vertical grande,
    # com verniz o cartao de nuvem reflete nela inteira e lava a tinta — foi o
    # achado do 767-300ER de passageiros e vale igual aqui.
    b.inputs["Roughness"].default_value = 0.45
    b.inputs["Specular IOR Level"].default_value = 0.20
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 0.0
        b.inputs["Coat Roughness"].default_value = 0.03
    return m


ob = bpy.data.objects["Asas"]
me = ob.data
nomes = [s.name for s in ob.material_slots]
for nome, cor in (("LATAM_WingletExt", INDIGO), ("LATAM_WingletInt", CORAL)):
    mat = material(nome, cor)
    if nome not in nomes:
        me.materials.append(mat)
        nomes.append(nome)
iE, iI = nomes.index("LATAM_WingletExt"), nomes.index("LATAM_WingletInt")

nE = nI = 0
for p in me.polygons:
    c = p.center
    if abs(c.y) < Y_WINGLET or c.z < Z_TINTA:
        continue
    # normal apontando para FORA da aeronave em y => face externa
    if p.normal.y * (1.0 if c.y > 0 else -1.0) >= 0.0:
        p.material_index = iE
        nE += 1
    else:
        p.material_index = iI
        nI += 1
print(f"[winglet] {nE} faces externas (indigo), {nI} internas (coral), "
      f"acima de z={Z_TINTA} e |y|>{Y_WINGLET}")

bpy.ops.wm.save_mainfile()
print("SALVO", bpy.data.filepath)
