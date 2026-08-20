"""Fase 3 — detalhes que identificam o 777: canoas de flap, escape da APU,
luzes de navegacao e sondas do nariz.

blender -b "boeing 777-300ER/B77W_LATAM.blend" --python "boeing 777-300ER/build_77w_fase3_detalhes.py"

As canoas (flap track fairings) do 777 sao LONGAS e sobressaem bem atras do
bordo de fuga — sem elas a asa nao le como a de um 777. Posicoes conferidas na
foto de PT-MUG (FRA 2022, em voo, tres canoas visiveis por semiasa).
"""
import bpy
import bmesh
import json
import math
import os

BASE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(BASE, "spec_77w.json")))
A = S["asa"]


def col(nome):
    c = bpy.data.collections.get(nome)
    if c is None:
        c = bpy.data.collections.new(nome)
        bpy.context.scene.collection.children.link(c)
    return c


def obj_novo(nome, me, colecao, mat=None, sub=2):
    ob = bpy.data.objects.get(nome)
    if ob:
        old = ob.data
        ob.data = me
        if isinstance(old, bpy.types.Mesh) and old.users == 0:
            bpy.data.meshes.remove(old)
    else:
        ob = bpy.data.objects.new(nome, me)
        col(colecao).objects.link(ob)
    if mat and me.materials.find(mat) < 0:
        me.materials.append(bpy.data.materials[mat])
    for p in me.polygons:
        p.use_smooth = True
    if sub:
        m = ob.modifiers.get("Sub") or ob.modifiers.new("Sub", 'SUBSURF')
        m.levels, m.render_levels = sub, sub
    return ob


def wing_le(y):
    return 24.69 + 0.681 * y


def wing_te(y):
    if y <= 7.1:
        return 40.19
    if y <= 12.5:
        return 40.19 + (41.0 - 40.19) * (y - 7.1) / (12.5 - 7.1)
    return 36.57 + 0.358 * y


def wing_z(y):
    return -1.0 + math.tan(math.radians(A["diedro_graus"])) * max(0.0, y - 3.1)


# ------------------------------------------------- canoas de flap
def canoa(nome, y, lado, comp_tras=2.6, r_max=0.42):
    """Corpo de revolucao achatado, alinhado com o fluxo, sob o bordo de fuga."""
    te = wing_te(y)
    x0 = te - 4.6                       # entra por baixo da asa
    x1 = te + comp_tras
    zc = wing_z(y) - 0.52               # bem por baixo do plano da corda
    perfil = [(0.00, 0.02), (0.08, 0.20), (0.20, 0.33), (0.38, 0.41),
              (0.56, 0.42), (0.72, 0.38), (0.88, 0.28), (1.00, 0.14)]
    seg = 16
    bm = bmesh.new()
    linhas = []
    for t, rr in perfil:
        x = x0 + t * (x1 - x0)
        r = rr / 0.42 * r_max
        z0 = zc + 0.28 * (1 - abs(2 * t - 1)) * 0.3     # leve arqueamento
        fila = []
        for i in range(seg):
            th = 2 * math.pi * i / seg
            fila.append(bm.verts.new((x, lado * y + r * 0.82 * math.sin(th),
                                      z0 + r * math.cos(th))))
        linhas.append(fila)
    for a, b in zip(linhas[:-1], linhas[1:]):
        for i in range(seg):
            bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
    for fila, inv in ((linhas[0], True), (linhas[-1], False)):
        try:
            bm.faces.new(fila if inv else fila[::-1])
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    return obj_novo(nome, me, "01_Estrutura", "LATAM_Branco")


ys = A["carenagens_flap"]["y_aprox"]
comps = [3.0, 2.7, 2.3]
raios = [0.46, 0.42, 0.36]
for lado, sn in ((1, "D"), (-1, "E")):
    for k, (y, cmp_, rr) in enumerate(zip(ys, comps, raios)):
        canoa(f"Canoa{sn}{k}", y, lado, cmp_, rr)
print("canoas de flap ok:", 2 * len(ys))

# ------------------------------------------------- escape da APU
bm = bmesh.new()
seg = 20
perfil = [(73.30, 0.30), (73.70, 0.26), (73.95, 0.20)]
linhas = []
for x, r in perfil:
    fila = []
    for i in range(seg):
        th = 2 * math.pi * i / seg
        fila.append(bm.verts.new((x, r * 0.85 * math.sin(th), 1.90 + r * math.cos(th))))
    linhas.append(fila)
for a, b in zip(linhas[:-1], linhas[1:]):
    for i in range(seg):
        bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
try:
    bm.faces.new(linhas[-1][::-1])
except ValueError:
    pass
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("APUExaust")
bm.to_mesh(me)
bm.free()
obj_novo("APUExaust", me, "04_Detalhes", "TitanioExaust", sub=1)
print("escape da APU ok")

# ------------------------------------------------- luzes de navegacao
exec(open(os.path.join(os.path.dirname(BASE), "latam_livery_kit.py")).read())
c = col("04_Detalhes")
ytip = A["raked_tip"]["tip_y"]
xtip = 0.5 * (A["raked_tip"]["tip_le_x"] + A["raked_tip"]["tip_te_x"])
ztip = wing_z(ytip)
luzes_navegacao(c,
                pos_esq=(xtip - 0.6, -ytip + 0.15, ztip + 0.05),
                pos_dir=(xtip - 0.6, ytip - 0.15, ztip + 0.05),
                pos_beacon=(31.0, 0.0, -3.35),
                pos_cauda=(73.9, 0.0, 1.55))
print("luzes ok")

bpy.ops.wm.save_mainfile()
print("SALVO", bpy.data.filepath)
