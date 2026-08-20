"""Etapa 2 — asas (com winglets API), deriva, estabilizador, belly fairing e
canoas de flap do 767-300ER. Substitui as meshes herdadas do 787.

/Applications/Blender.app/Contents/MacOS/Blender -b "boeing 767-300ER/B763_LATAM.blend" --python "boeing 767-300ER/b2_asas.py"
"""
import bpy
import bmesh
import math

TAN_DIH = math.tan(math.radians(5.3))

def naca_t(c, t):
    return 5 * t * (0.2969 * math.sqrt(max(c, 1e-6)) - 0.126 * c
                    - 0.3516 * c * c + 0.2843 * c ** 3 - 0.1015 * c ** 4)

def perfil(le, corda, z0, queda, t_rel, n=14):
    pts = []
    for i in range(n):
        c = i / (n - 1)
        pts.append((le + c * corda, z0 - queda * c + naca_t(c, t_rel) * corda))
    for i in range(1, n - 1):
        c = 1 - i / (n - 1)
        pts.append((le + c * corda, z0 - queda * c - naca_t(c, t_rel) * corda * 0.85))
    return pts

def loft(nome, estacoes, material, colecao="01_Estrutura", espelhar_de=None):
    """estacoes: lista de (pts_xz, y). Fecha com caps."""
    bm = bmesh.new()
    aneis = []
    for pts, y in estacoes:
        aneis.append([bm.verts.new((px, y, pz)) for (px, pz) in pts])
    for a, b in zip(aneis[:-1], aneis[1:]):
        n = len(a)
        for s in range(n):
            bm.faces.new((a[s], a[(s + 1) % n], b[(s + 1) % n], b[s]))
    for anel, flip in ((aneis[0], True), (aneis[-1], False)):
        try:
            f = bm.faces.new(anel if flip else list(reversed(anel)))
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(bpy.data.materials[material])
    ob = bpy.data.objects.get(nome)
    if ob:
        antigo = ob.data
        ob.data = me
        bpy.data.meshes.remove(antigo)
    else:
        ob = bpy.data.objects.new(nome, me)
        bpy.data.collections[colecao].objects.link(ob)
    sub = None
    for m in ob.modifiers:
        if m.type == 'SUBSURF':
            sub = m
    if sub is None:
        sub = ob.modifiers.new("Sub", 'SUBSURF')
    sub.levels, sub.render_levels = 2, 2
    return ob

# ---------------------------------------------------------------- asa
def le_x(y):
    return 17.17 + 0.694 * y

def te_x(y):
    if y <= 9.41:
        return 29.29 + 0.143 * (y - 2.515)
    return 30.44 + 0.376 * (y - 9.41)

def z_le(y):
    return -1.15 + TAN_DIH * max(0.0, y - 2.515)

WING_Y = [1.2, 2.515, 5.0, 7.9, 9.41, 12.0, 15.0, 18.0, 21.0, 23.0, 23.785]
TREL = {1.2: 0.145, 2.515: 0.145, 5.0: 0.14, 7.9: 0.13, 9.41: 0.125,
        12.0: 0.115, 15.0: 0.108, 18.0: 0.102, 21.0: 0.098, 23.0: 0.095,
        23.785: 0.095}

est = []
for y in WING_Y:
    le, te = le_x(y), te_x(y)
    corda = te - le
    queda = 0.5 if y < 2.6 else max(0.12, 0.5 - 0.02 * (y - 2.515))
    est.append((perfil(le, corda, z_le(y), queda, TREL[y]), y))

# winglet blended: arco de transicao + trecho reto; ponta em y=25.45, z +2.9
z_tip = z_le(23.785)
LE_T, TE_T = le_x(23.785), te_x(23.785)     # 33.67 / 35.85
WGL = [
    # (frac_arco 0..1, dy, dz, le, corda)
    (0.15, 0.28, 0.10, 33.90, 1.85),
    (0.35, 0.62, 0.42, 34.20, 1.50),
    (0.55, 0.95, 0.90, 34.52, 1.18),
    (0.75, 1.25, 1.55, 34.82, 0.95),
    (0.90, 1.48, 2.25, 35.05, 0.78),
    (1.00, 1.665, 2.90, 35.22, 0.66),
]
for _f, dy, dz, le, corda in WGL:
    y = 23.785 + dy
    pts = perfil(le, corda, z_tip + dz, 0.05, 0.09)
    est.append((pts, y))

asaD = loft("Asas", est, "CinzaAsa")
mir = None
for m in asaD.modifiers:
    if m.type == 'MIRROR':
        mir = m
if mir is None:
    mir = asaD.modifiers.new("Mirror", 'MIRROR')
mir.use_axis = (False, True, False)

# ---------------------------------------------------------------- deriva
def fin_le(z):
    if z >= 3.9:
        return 41.39 + 1.0014 * z
    # carenagem dorsal: curva para a frente ate (43.0, 2.66)
    t = (z - 2.66) / (3.9 - 2.66)
    t = max(0.0, min(1.0, t))
    x39 = 41.39 + 1.0014 * 3.9
    return 43.0 + (x39 - 43.0) * (t ** 1.6) - 0.0

def fin_te(z):
    return 50.55 + 0.398 * z

est_fin = []
for z in [1.5, 2.2, 2.66, 3.2, 3.9, 5.0, 6.5, 8.0, 9.5, 10.6, 11.15]:
    le = fin_le(max(z, 2.66)) if z >= 2.66 else fin_le(2.66) - 0.6
    te = fin_te(z)
    corda = te - le
    t_rel = 0.105 if z > 3.9 else 0.09
    pts = [(le + c / 13 * corda, z) for c in range(14)]
    # perfil simetrico no plano xz -> loft em z com espessura em y
    est_fin.append((z, le, corda, t_rel))

bm = bmesh.new()
aneis = []
for (z, le, corda, t_rel) in est_fin:
    linha = []
    n = 14
    for i in range(n):
        c = i / (n - 1)
        linha.append(bm.verts.new((le + c * corda, naca_t(c, t_rel) * corda, z)))
    for i in range(1, n - 1):
        c = 1 - i / (n - 1)
        linha.append(bm.verts.new((le + c * corda, -naca_t(c, t_rel) * corda, z)))
    aneis.append(linha)
for a, b in zip(aneis[:-1], aneis[1:]):
    n = len(a)
    for s in range(n):
        bm.faces.new((a[s], a[(s + 1) % n], b[(s + 1) % n], b[s]))
for anel, flip in ((aneis[0], True), (aneis[-1], False)):
    try:
        bm.faces.new(anel if flip else list(reversed(anel)))
    except ValueError:
        pass
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("Deriva")
bm.to_mesh(me)
bm.free()
for p in me.polygons:
    p.use_smooth = True
obf = bpy.data.objects["Deriva"]
mats = [m for m in obf.data.materials]
antigo = obf.data
obf.data = me
bpy.data.meshes.remove(antigo)
for m in mats:
    me.materials.append(m)
for m in obf.modifiers:
    if m.type == 'SUBSURF':
        m.levels, m.render_levels = 2, 2

# UV planar da deriva p/ sash (dominio x 40..55.5, z 1.4..11.4 -> 0..1)
uvf = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
for loop in me.loops:
    co = me.vertices[loop.vertex_index].co
    uvf.data[loop.index].uv = ((co.x - 40.0) / 15.5, (co.z - 1.4) / 10.0)

# ---------------------------------------------------------------- estab
def st_le(y):
    return 47.26 + 0.768 * (max(y, 0.8) - 2.515)

def st_te(y):
    return 52.54 + 0.247 * (max(y, 0.8) - 2.515)

est_st = []
for y in [0.5, 2.515, 4.5, 6.5, 8.2, 9.31]:
    le, te = st_le(y), st_te(y)
    corda = te - le
    z0 = 0.55 + math.tan(math.radians(7)) * max(0.0, y - 0.8)
    est_st.append((perfil(le, corda, z0, 0.10, 0.10, n=12), y))
stab = loft("EstabHorizontal", est_st, "LATAM_Branco")
mir2 = None
for m in stab.modifiers:
    if m.type == 'MIRROR':
        mir2 = m
if mir2 is None:
    mir2 = stab.modifiers.new("Mirror", 'MIRROR')
mir2.use_axis = (False, True, False)

# ---------------------------------------------------------------- belly fairing
bm = bmesh.new()
aneisb = []
BF = [
    (17.5, -2.55, 1.9), (19.0, -2.80, 2.5), (21.0, -2.93, 2.9),
    (24.0, -2.95, 3.0), (27.0, -2.92, 2.9), (29.5, -2.80, 2.5),
    (31.5, -2.60, 1.9),
]
for (x, fundo, meia) in BF:
    linha = []
    n = 12
    for i in range(n + 1):
        t = i / n
        yy = meia * math.cos(t * math.pi)          # +meia .. -meia
        zz = fundo + ((-1.9) - fundo) * (abs(math.sin(t * math.pi)) ** 0) * 0
        z = -1.9 + (fundo + 1.9) * (math.sin(t * math.pi) ** 0.8) * 0 + 0
        # superelipse: z entre -1.9 (bordas) e fundo (centro)
        z = -1.9 + (fundo + 1.9) * (1 - abs(yy / meia) ** 2.6)
        linha.append(bm.verts.new((x, yy, z)))
    aneisb.append(linha)
for a, b in zip(aneisb[:-1], aneisb[1:]):
    n = len(a)
    for s in range(n - 1):
        bm.faces.new((a[s], a[s + 1], b[s + 1], b[s]))
for anel, flip in ((aneisb[0], True), (aneisb[-1], False)):
    try:
        bm.faces.new(anel if flip else list(reversed(anel)))
    except ValueError:
        pass
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("BellyFairing")
bm.to_mesh(me)
bm.free()
for p in me.polygons:
    p.use_smooth = True
obb = bpy.data.objects["BellyFairing"]
matsb = [m for m in obb.data.materials]
antigo = obb.data
obb.data = me
bpy.data.meshes.remove(antigo)
for m in matsb:
    me.materials.append(m)

# ---------------------------------------------------------------- canoas de flap
# 2 grandes no flap interno + 4 menores no externo (fotos CC-CWY)
velhas = [o for o in bpy.data.objects if o.name.startswith("FlapFairing")]
for o in velhas:
    bpy.data.objects.remove(o, do_unlink=True)

def canoa(nome, y, comprimento, prof, larg):
    te = te_x(abs(y))
    x0 = te - comprimento * 0.55
    x1 = te + comprimento * 0.45
    zw = z_le(abs(y)) - 0.45 - 0.02 * abs(y)   # ~superficie inferior da asa
    bm = bmesh.new()
    aneis = []
    for i in range(9):
        t = i / 8
        x = x0 + (x1 - x0) * t
        r = prof * math.sin(math.pi * min(1.0, 0.15 + 0.85 * (1 - abs(2 * t - 1))))
        rw = larg * (0.4 + 0.6 * math.sin(math.pi * min(1.0, 0.2 + 0.8 * (1 - abs(2 * t - 1)))))
        linha = []
        for s in range(10):
            th = math.pi * s / 9
            linha.append(bm.verts.new((x, y + rw * math.cos(th), zw - r * math.sin(th))))
        aneis.append(linha)
    for a, b in zip(aneis[:-1], aneis[1:]):
        for s in range(9):
            bm.faces.new((a[s], a[s + 1], b[s + 1], b[s]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(bpy.data.materials["CinzaAsa"])
    ob = bpy.data.objects.new(nome, me)
    bpy.data.collections["01_Estrutura"].objects.link(ob)
    return ob

for lado, sg in (("E", -1), ("D", 1)):
    canoa(f"FlapCanoa{lado}0", sg * 4.9, 3.8, 0.55, 0.30)
    canoa(f"FlapCanoa{lado}1", sg * 7.4, 3.6, 0.50, 0.28)
    canoa(f"FlapCanoa{lado}2", sg * 10.8, 2.6, 0.34, 0.20)
    canoa(f"FlapCanoa{lado}3", sg * 13.6, 2.5, 0.32, 0.19)
    canoa(f"FlapCanoa{lado}4", sg * 16.4, 2.4, 0.30, 0.18)
    canoa(f"FlapCanoa{lado}5", sg * 19.2, 2.3, 0.28, 0.17)

print("asa: LE raiz", le_x(2.515), "TE raiz", te_x(2.515), "tip", le_x(23.785), te_x(23.785))
print("deriva: LE(11.15)", fin_le(11.15), "TE(11.15)", fin_te(11.15))
bpy.ops.wm.save_mainfile()
print("SALVO", bpy.data.filepath)
