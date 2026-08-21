"""Etapa 3 — motores CF6-80C2B7F, trem reposicionado, detalhes dorsais.

/Applications/Blender.app/Contents/MacOS/Blender -b "boeing 767-300F/B763F_LATAM_CARGO.blend" --python "boeing 767-300F/b3_motores_trem.py"
"""
import bpy
import bmesh
import math
from mathutils import Vector

D = bpy.data

# ATENCAO: o bloco do trem/detalhes move vertices RELATIVAMENTE (herdados do
# 787), portanto NAO e idempotente — rodar b3 duas vezes no mesmo .blend
# aplicava o deslocamento duas vezes e punha o trem de nariz em x=3.7 e o
# principal em x=23.8.  Foi assim que aconteceu.  A marca abaixo registra no
# proprio .blend que a reposicao ja foi feita; os motores sao reconstruidos
# sempre, porque o lathe usa coordenadas ABSOLUTAS e e idempotente.
JA_FEITO = bool(bpy.context.scene.get("b3_trem_reposicionado", False))

def transform_mesh(nomes, anchor_old, anchor_new, s):
    for n in nomes:
        o = D.objects.get(n)
        if o is None or o.type != 'MESH':
            continue
        me = o.data
        for v in me.vertices:
            v.co.x = anchor_new[0] + s * (v.co.x - anchor_old[0])
            v.co.y = anchor_new[1] + s * (v.co.y - anchor_old[1])
            v.co.z = anchor_new[2] + s * (v.co.z - anchor_old[2])

def translate_mesh(nomes, d):
    for n in nomes:
        o = D.objects.get(n)
        if o is None or o.type != 'MESH':
            continue
        for v in o.data.vertices:
            v.co.x += d[0]; v.co.y += d[1]; v.co.z += d[2]

if not JA_FEITO:
    # ---------------------------------------------------------------- trem
    nariz = [n for n in ("TremNariz_Braco", "TremNariz_Cilindro", "TremNariz_Eixo",
                         "TremNariz_Pistao", "TremNariz_TesouraA", "TremNariz_TesouraB",
                         "TremNariz_RodaD", "TremNariz_RodaE")]
    transform_mesh(nariz, (5.41, 0.0, -4.88), (4.55, 0.0, -4.61), 0.965)
    # alonga o cilindro p/ dentro do poco (raiz enterrada)
    o = D.objects["TremNariz_Cilindro"]
    ztop = max(v.co.z for v in o.data.vertices)
    for v in o.data.vertices:
        if v.co.z > ztop - 0.4:
            v.co.z += 0.45

    principais = [n.name for n in D.objects if n.name.startswith("TremP")]
    esq = [n for n in principais if ("E" in n.replace("Trem", "").replace("Eixo", "x")[:14] and "D" not in n.split("_")[-1][:6]) or "_RodaE" in n or "EixoE" in n or "CilindroE" in n or "PistaoE" in n or "BraceE" in n or "BogieE" in n or "TesouraE" in n]
    # mais simples: classifica pelo bbox y
    esq, dirt = [], []
    for n in principais:
        o = D.objects[n]
        ymed = sum(v.co.y for v in o.data.vertices) / len(o.data.vertices)
        (esq if ymed < 0 else dirt).append(n)
    transform_mesh(dirt, (31.24, 4.9, -4.88), (27.31, 4.65, -4.61), 0.889)
    transform_mesh(esq, (31.24, -4.9, -4.88), (27.31, -4.65, -4.61), 0.889)
    for n in principais:
        if "Cilindro" in n or "Brace" in n:
            o = D.objects[n]
            ztop = max(v.co.z for v in o.data.vertices)
            for v in o.data.vertices:
                if v.co.z > ztop - 0.5:
                    v.co.z += 0.55

    # ---------------------------------------------------------------- detalhes dorsais
    translate_mesh(["AntenaVHF_Dorso1"], (-1.6, 0, -0.28))     # -> x ~12
    translate_mesh(["AntenaVHF_Dorso2"], (-9.2, 0, -0.28))     # -> x ~31
    translate_mesh(["AntenaSAT"], (-17.2, 0, -0.28))           # -> x ~16.5
    translate_mesh(["BeaconDorso"], (-2.5, 0, -0.24))          # -> x ~20.5
    translate_mesh(["LuzCauda"], (-8.3, 0, -0.71))             # -> (54.2, 0, ~0.95)
    # luzes p/ ponta do winglet
    for n, y in (("NavEsq", -1), ("NavDir", 1)):
        o = D.objects[n]
        c = sum((v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
        alvo = Vector((34.55, y * 25.30, 1.62))
        dvec = alvo - c
        for v in o.data.vertices:
            v.co += dvec
    for n, y in (("EstroboEsq", -1), ("EstroboDir", 1)):
        o = D.objects[n]
        c = sum((v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
        alvo = Vector((35.35, y * 25.32, 1.55))
        dvec = alvo - c
        for v in o.data.vertices:
            v.co += dvec
    # limpadores: 767 parabrisa x 1.5-3.0, z 0.44-1.2
    for n in ("Limpador_Braco_E", "Limpador_Pivo_E", "Limpador_Palheta_E",
              "Limpador_Braco_D", "Limpador_Pivo_D", "Limpador_Palheta_D"):
        translate_mesh([n], (-0.18, 0, 0.12))

    # Dreamliner: nao existe no 767
    mk = D.objects.get("MarkDreamliner")
    if mk:
        D.objects.remove(mk, do_unlink=True)
    bpy.context.scene["b3_trem_reposicionado"] = True
    print("trem/detalhes reposicionados (uma vez so)")
else:
    print("trem/detalhes JA reposicionados neste .blend — pulando")

# ---------------------------------------------------------------- motores CF6
def lathe(nome, perfil, y0, z0, material, colecao="02_Motores", seg=48, flip=False):
    """perfil: [(x, r)] revolucao em torno do eixo x local (y0,z0)."""
    bm = bmesh.new()
    aneis = []
    for (x, r) in perfil:
        linha = []
        for s in range(seg):
            th = 2 * math.pi * s / seg
            linha.append(bm.verts.new((x, y0 + r * math.sin(th), z0 + r * math.cos(th))))
        aneis.append(linha)
    for a, b in zip(aneis[:-1], aneis[1:]):
        for s in range(seg):
            bm.faces.new((a[s], a[(s + 1) % seg], b[(s + 1) % seg], b[s]))
    for anel, first in ((aneis[0], True), (aneis[-1], False)):
        if abs(perfil[0][1] if first else perfil[-1][1]) > 1e-4:
            try:
                bm.faces.new(anel if first else list(reversed(anel)))
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(D.materials[material])
    ob = D.objects.get(nome)
    if ob:
        antigo = ob.data
        mats = None
        ob.data = me
        bpy.data.meshes.remove(antigo)
    else:
        ob = D.objects.new(nome, me)
        D.collections[colecao].objects.link(ob)
    return ob

# Entrada em x=18.54: cota IMPRESSA no ACAP p29 ("GE ENGINES 60 FT 10 IN"),
# nao os 18.2 do bico DESENHADO.  A foto de perfil parece dar 18.2, mas o motor
# esta 7.9 m mais perto da camera do que o plano de simetria onde o mapa foi
# calibrado — a paralaxe encolhe justamente esses 0.34 m.
# Perfil da nacelle remedido na foto (CC-CWY, grade metrica): a CF6-80C2 e um
# CILINDRO com bico afilado, nao um ovo — mantem ~2.67 m de diametro de x=19.6
# a x=21.4 e so entao afila.  O perfil anterior (max 2.80 em 19.8, 2.17 em
# 22.6) lia como uma bolha lisa sem entrada nem escape.
CLZ = -2.34
for lado, sgn in (("E", -1), ("D", 1)):
    y0 = sgn * 7.90
    # nacelle externa: fan cowl + reverser (branco)
    lathe(f"Motor_Nacelle_{lado}", [
        (18.54, 1.170), (18.66, 1.262), (18.95, 1.315), (19.60, 1.335),
        (20.60, 1.335), (21.40, 1.320), (22.10, 1.285), (22.80, 1.215),
        (23.25, 1.130),
    ], y0, CLZ, "LATAM_Branco")
    # duto interno (liner)
    lathe(f"Motor_Duto_{lado}", [
        (18.54, 1.170), (18.80, 1.100), (19.24, 1.120), (19.29, 1.165),
    ], y0, CLZ, "InletLiner")
    # lip polido
    lathe(f"Motor_Lip_{lado}", [
        (18.51, 1.165), (18.54, 1.235), (18.64, 1.292), (18.89, 1.330),
    ], y0, CLZ, "MetalMotor")
    # fan (2.36 m) + spinner
    lathe(f"Motor_Fan_{lado}", [(19.31, 0.0), (19.30, 1.130)], y0, CLZ, "CinzaEscuro")
    lathe(f"Motor_Spinner_{lado}", [(18.94, 0.0), (19.14, 0.12), (19.33, 0.28)],
          y0, CLZ, "SpinnerCinza")
    # core cowl (metal escuro) + bocal inconel + plug — o escape do CF6 e longo
    lathe(f"Motor_Core_{lado}", [
        (23.10, 1.070), (23.60, 0.960), (24.20, 0.830), (24.90, 0.690),
        (25.35, 0.605),
    ], y0, CLZ, "MetalMotor")
    lathe(f"Motor_Bocal_{lado}", [
        (25.35, 0.605), (25.60, 0.535), (25.75, 0.495),
    ], y0, CLZ, "TitanioExaust")
    lathe(f"Motor_Plug_{lado}", [
        (25.20, 0.360), (25.70, 0.265), (26.10, 0.0),
    ], y0, CLZ, "TitanioExaust")
    # pas do fan: manter herdadas se existirem — reescalar/reposicionar
    pas = D.objects.get(f"Motor_Pas_{lado}")
    if pas:
        me = pas.data
        cs = [Vector((0, 0, 0))]
        cx = sum(v.co.x for v in me.vertices) / len(me.vertices)
        cy = sum(v.co.y for v in me.vertices) / len(me.vertices)
        cz = sum(v.co.z for v in me.vertices) / len(me.vertices)
        s = 2.36 / 2.85
        for v in me.vertices:
            v.co.x = 19.28 + s * (v.co.x - cx)
            v.co.y = y0 + s * (v.co.y - cy)
            v.co.z = CLZ + s * (v.co.z - cz)
    ch = D.objects.get(f"Motor_Chevrons_{lado}")
    if ch:
        D.objects.remove(ch, do_unlink=True)
    # pylon: carenagem larga que ENTRA na nacelle em baixo e na asa em cima
    # (raiz enterrada: a aresta superior fica dentro do perfil da asa, e a
    # inferior dentro da nacelle).  A cunha de 0.28 m que existia aqui lia como
    # uma sombra e deixava o motor visualmente solto sob a asa.
    bm = bmesh.new()
    perfil = [                      # (x, z, meia-largura)
        (19.20, -1.02, 0.13), (21.20, -0.70, 0.20), (22.70, -0.52, 0.26),
        (24.50, -0.48, 0.30), (26.60, -0.58, 0.30), (26.60, -1.12, 0.30),
        (24.20, -1.30, 0.28), (22.00, -1.26, 0.24), (19.70, -1.18, 0.14),
    ]
    vs_e = [bm.verts.new((x, y0 - w, z)) for (x, z, w) in perfil]
    vs_d = [bm.verts.new((x, y0 + w, z)) for (x, z, w) in perfil]
    bm.faces.new(vs_e)
    bm.faces.new(list(reversed(vs_d)))
    for i in range(len(perfil)):
        j = (i + 1) % len(perfil)
        bm.faces.new((vs_e[i], vs_e[j], vs_d[j], vs_d[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(f"Motor_Pylon_{lado}")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    me.materials.append(D.materials["LATAM_Branco"])
    obp = D.objects.get(f"Motor_Pylon_{lado}")
    if obp:
        antigo = obp.data
        obp.data = me
        bpy.data.meshes.remove(antigo)
    else:
        obp = D.objects.new(f"Motor_Pylon_{lado}", me)
        D.collections["02_Motores"].objects.link(obp)
    for m in list(obp.modifiers):
        if m.type == "SUBSURF":
            obp.modifiers.remove(m)

print("motores CF6 ok; trem reposicionado (nariz x=4.55, principal x=27.31, solo -4.61)")
bpy.ops.wm.save_mainfile()
print("SALVO", bpy.data.filepath)
