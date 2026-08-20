# Boeing 777-300ER LATAM — fase 1: geometria completa a partir do spec_77w.json
# Roda headless: blender --background B77W_LATAM.blend --python build_77w_fase1_geo.py
import bpy, bmesh, json, math, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
SPEC = json.load(open(os.path.join(ROOT, "spec_77w.json")))
sys.path.insert(0, os.path.join(REPO, ".claude/skills/casco-parametrico/scripts"))
exec(open(os.path.join(REPO, ".claude/skills/casco-parametrico/scripts/casco.py")).read())

S = SPEC

# ---------------------------------------------------------------- 0. limpeza
KEEP_TYPES = {'CAMERA', 'LIGHT', 'EMPTY'}
KEEP_NAMES = {'Pista'}
# guardar as marcas oficiais (mesma marca LATAM — reusar geometria)
BRAND = {'B789_LogoLATAM_E', 'B789_LogoLATAM_E_Coral', 'B789_LogoLATAM_D',
         'B789_LogoLATAM_D_Coral', 'LogoBarriga', 'LogoBarriga_Coral',
         'B77W_LogoLATAM_E', 'B77W_LogoLATAM_E_Coral', 'B77W_LogoLATAM_D',
         'B77W_LogoLATAM_D_Coral'}
for o in list(bpy.data.objects):
    if o.type in KEEP_TYPES or o.name in KEEP_NAMES:
        continue
    if o.name in BRAND:
        o.name = o.name.replace('B789_', 'B77W_')
        if o.data: o.data.use_fake_user = True
        o.hide_viewport = True; o.hide_render = True
        continue
    bpy.data.objects.remove(o, do_unlink=True)
# limpar meshes orfaos (matriculas 787, dreamliner)
for me in list(bpy.data.meshes):
    if me.users == 0 and not me.use_fake_user:
        bpy.data.meshes.remove(me)
print("limpeza ok; restam", len(bpy.data.objects), "objetos")

def col(nome):
    c = bpy.data.collections.get(nome)
    if c is None:
        c = bpy.data.collections.new(nome)
        bpy.context.scene.collection.children.link(c)
    return c

def obj_novo(nome, me, colecao, mat=None):
    ob = bpy.data.objects.get(nome)
    if ob:
        old = ob.data; ob.data = me
        if isinstance(old, bpy.types.Mesh) and old.users == 0: bpy.data.meshes.remove(old)
    else:
        ob = bpy.data.objects.new(nome, me)
        col(colecao).objects.link(ob)
    if mat and me.materials.find(mat) < 0:
        me.materials.append(bpy.data.materials[mat])
    for p in me.polygons: p.use_smooth = True
    return ob

# ---------------------------------------------------------------- 1. casco
def interp(x, tab, ci, vi):
    xs = [r[ci] for r in tab]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i+1]:
            f = (x - xs[i]) / max(xs[i+1] - xs[i], 1e-9)
            return tab[i][vi] + f * (tab[i+1][vi] - tab[i][vi])
    return tab[-1][vi] if x > xs[-1] else tab[0][vi]

def w_ratio_cone(x):
    if x <= 68.0: return 0.96
    return 0.96 + (0.35 - 0.96) * (x - 68.0) / (73.86 - 68.0)

aneis = []          # (x, zc, rz, ry)
for x, crown, keel, w2 in S["nariz_estacoes"][1:]:
    aneis.append((x, (crown + keel) / 2, (crown - keel) / 2, max(w2, 0.05)))
x0, x1 = S["secao_constante_x"]
n = 14
for i in range(1, n + 1):
    aneis.append((x0 + i * (x1 - x0) / n, 0.0, 3.10, 3.10))
for x, zc, r in S["cauda"][1:-1]:
    aneis.append((x, zc, r, w_ratio_cone(x) * r))
fus = construir_casco(aneis, nome="Fuselagem", material="FuselagemPaint",
                      ponta_frente=(0.0, 0.0, -0.60), ponta_tras=(73.86, 0.0, 1.97))
uv_cilindrica(fus.data, aneis, comprimento_uv=74.5)
print("casco:", len(aneis), "aneis")

# ---------------------------------------------------------------- 2. asas
def loft_fechado(nome, secoes, colecao, mat, eixo='y'):
    """secoes = lista de listas de (x, y, z) já em 3D, mesma contagem de pontos."""
    bm = bmesh.new()
    linhas = []
    for sec in secoes:
        linhas.append([bm.verts.new(p) for p in sec])
    for a, b in zip(linhas[:-1], linhas[1:]):
        m = len(a)
        for i in range(m):
            bm.faces.new((a[i], a[(i+1) % m], b[(i+1) % m], b[i]))
    for linha in (linhas[0], linhas[-1]):
        try: bm.faces.new(linha[::-1])
        except ValueError: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me); bm.free()
    ob = obj_novo(nome, me, colecao, mat)
    m = ob.modifiers.get("Sub") or ob.modifiers.new("Sub", 'SUBSURF')
    m.levels, m.render_levels = 2, 2
    return ob

A = S["asa"]
RT = A["raked_tip"]
def wing_le(y): return 24.69 + 0.681 * y
def wing_te(y):
    if y <= 7.1: return 40.19
    if y <= 12.5: return 40.19 + (41.0 - 40.19) * (y - 7.1) / (12.5 - 7.1)
    if y <= 29.5: return 36.57 + 0.358 * y
    return 47.13 + (RT["tip_te_x"] - 47.13) * (y - 29.5) / (32.4 - 29.5)
def wing_le_tip(y):
    if y <= 31.4: return wing_le(y)
    t = (y - 31.4) / (32.4 - 31.4)
    return wing_le(31.4) + (RT["tip_le_x"] - wing_le(31.4)) * (t ** 1.5)
def wing_z(y): return -1.0 + math.tan(math.radians(A["diedro_graus"])) * max(0.0, y - 3.1)

def secao_asa(y, tc, lado=1):
    le = wing_le_tip(y); te = wing_te(y)
    corda = max(te - le, 0.3)
    z0 = wing_z(y)
    queda = 0.055 * corda            # leve twist/camber cai para o BF
    pts = secao_aerofolio(le, corda, z0, queda, tc * corda, n=14)
    return [(px, lado * y, pz) for (px, pz) in pts]

ys = [1.5, 3.1, 5.0, 7.1, 9.61, 12.5, 16.0, 20.0, 24.0, 27.0, 29.5, 31.4, 32.05, 32.38]
tcs = [0.135, 0.13, 0.125, 0.12, 0.115, 0.11, 0.105, 0.10, 0.095, 0.095, 0.09, 0.085, 0.08, 0.075]
for lado, nome in ((1, "AsaD"), (-1, "AsaE")):
    loft_fechado(nome, [secao_asa(y, tc, lado) for y, tc in zip(ys, tcs)],
                 "01_Estrutura", "CinzaAsa")
print("asas ok")

# ---------------------------------------------------------------- 3. empenagem
E = S["empenagem"]
def fin_le(z): return 57.996 + 1.0104 * z
def fin_te(z): return 68.254 + 0.3960 * z
def secao_fin(z, tc):
    le, te = fin_le(z), fin_te(z)
    if z > 12.2:                      # ponta arredondada
        t = (z - 12.2) / (12.9 - 12.2)
        le = le + (70.9 - le) * t * 0.35
        te = te - (te - 73.0) * t * 0.55
    corda = max(te - le, 0.4)
    pts = secao_aerofolio(le, corda, 0, 0, tc * corda, n=12)
    return [(px, pz, z) for (px, pz) in pts]     # aerofolio no plano xz -> y=espessura
fzs = [1.9, 3.1, 4.5, 6.0, 8.0, 10.0, 11.5, 12.4, 12.85]
ftc = [0.11, 0.11, 0.105, 0.10, 0.095, 0.09, 0.09, 0.085, 0.08]
loft_fechado("Deriva", [secao_fin(z, tc) for z, tc in zip(fzs, ftc)], "01_Estrutura", "Deriva_Sash")

# carenagem dorsal: o BA da deriva curva PARA A FRENTE abaixo de z~4.6 e morre
# na crista do casco (spec: "abaixo de z~4.5 o BA curva para a frente ate a
# crista em x~58.5-60"). Fatia fina entre essa curva e o BA reto.
def dorsal():
    bm = bmesh.new()
    zs = [2.95, 3.30, 3.70, 4.10, 4.45, 4.75]
    linhas = []
    for k, z in enumerate(zs):
        t = (z - zs[0]) / (zs[-1] - zs[0])
        # BA da carenagem: parabola que sai da crista em x=58.55 e encontra o
        # BA reto (57.996+1.0104 z) no topo
        x_le_reto = fin_le(z)
        x_le = 58.55 + (x_le_reto - 58.55) * (t ** 1.6)
        x_te = x_le_reto + 0.55 * (1.0 - t)      # some dentro da deriva
        w = 0.50 * (1 - t) ** 0.8 + 0.10
        n = 8
        sec = []
        for i in range(n + 1):                       # lado +y, do BA ao BF
            c = i / n
            x = x_le + c * (x_te - x_le)
            esp = w * math.sin(math.pi * min(1.0, c * 1.15)) ** 0.7
            sec.append((x, esp, z))
        fila = [bm.verts.new(p) for p in sec]
        fila += [bm.verts.new((p[0], -p[1], p[2])) for p in sec[::-1][1:-1]]
        linhas.append(fila)
    for a, b in zip(linhas[:-1], linhas[1:]):
        m = len(a)
        for i in range(m):
            bm.faces.new((a[i], a[(i+1) % m], b[(i+1) % m], b[i]))
    for f, inv in ((linhas[0], False), (linhas[-1], True)):
        try: bm.faces.new(f if inv else f[::-1])
        except ValueError: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("DerivaDorsal"); bm.to_mesh(me); bm.free()
    ob = obj_novo("DerivaDorsal", me, "01_Estrutura", "LATAM_Branco")
    m = ob.modifiers.get("Sub") or ob.modifiers.new("Sub", 'SUBSURF')
    m.levels, m.render_levels = 2, 2
dorsal()

def stab_le(y): return 62.59 + 0.813 * y
def stab_te(y): return 69.82 + 0.378 * y
def secao_stab(y, lado=1):
    le, te = stab_le(y), stab_te(y)
    if y > 10.2:
        t = (y - 10.2) / (10.765 - 10.2)
        te = te - (te - 73.5) * t * 0.3
        le = le + 0.45 * t
    corda = max(te - le, 0.4)
    z0 = 0.6 + math.tan(math.radians(E["estab"]["diedro_graus"])) * max(0.0, y - 1.8)
    pts = secao_aerofolio(le, corda, z0, 0.02 * corda, 0.09 * corda, n=12)
    return [(px, lado * y, pz) for (px, pz) in pts]
sys_ = [0.8, 1.8, 3.0, 5.0, 7.0, 9.0, 10.2, 10.72]
for lado, nome in ((1, "EstabD"), (-1, "EstabE")):
    loft_fechado(nome, [secao_stab(y, lado) for y in sys_], "01_Estrutura", "CinzaAsa")
print("empenagem ok")

# ---------------------------------------------------------------- 4. carenagem ventral
def belly():
    C = A["carenagem_ventral"]
    xs = [24.8, 26.5, 28.5, 31.0, 33.5, 36.0, 38.5, 41.0, 42.5, 43.6]
    bm = bmesh.new()
    linhas = []
    for x in xs:
        # profundidade e largura com rampas suaves nas pontas
        t_in = smoothstep((x - 24.8) / 6.0)
        t_out = 1.0 - smoothstep((x - 40.5) / 3.1)
        f = min(t_in, t_out)
        fundo = -3.10 + (C["fundo_z"] + 3.10) * f - 0.02
        meiaw = 3.05 + (C["meia_larg_max"] - 3.05) * f
        sec = []
        N = 12
        # A borda superior da carenagem tem de morrer DENTRO do casco: com ela
        # em y=+-meiaw e z=-1.0 sobrava 0.11 m para fora da fuselagem (a
        # auditoria acusou "peca solta"). Enterrada em 0.86*meiaw / z=-0.90.
        for i in range(N + 1):
            th = math.pi * i / N          # so o hemisferio de baixo
            # perfil: caixa arredondada entre a borda enterrada e o fundo
            zz = -1.0 + (fundo + 1.0) * (math.sin(th) ** 0.55)
            if i in (0, N):
                sec.append((x, math.copysign(0.86 * meiaw, math.cos(th) or 1.0), -0.90))
            else:
                sec.append((x, meiaw * math.cos(th), zz))
        linhas.append([bm.verts.new(p) for p in sec])
    for a, b in zip(linhas[:-1], linhas[1:]):
        for i in range(len(a) - 1):
            bm.faces.new((a[i], a[i+1], b[i+1], b[i]))
    for f_ in (linhas[0], linhas[-1]):
        try: bm.faces.new(f_[::-1])
        except ValueError: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("BellyFairing"); bm.to_mesh(me); bm.free()
    ob = obj_novo("BellyFairing", me, "01_Estrutura", "CinzaBarriga")
    m = ob.modifiers.get("Sub") or ob.modifiers.new("Sub", 'SUBSURF')
    m.levels, m.render_levels = 2, 2
belly()
print("belly fairing ok")

# ---------------------------------------------------------------- 5. motores GE90
M = S["motor_ge90_115b"]
def corpo_revolucao(nome, perfil, cy, cz, colecao, mat, seg=28):
    """perfil = [(x, r)] em coords do eixo do motor."""
    bm = bmesh.new()
    linhas = []
    for x, r in perfil:
        fila = []
        for i in range(seg):
            th = 2 * math.pi * i / seg
            fila.append(bm.verts.new((x, cy + r * math.sin(th), cz + r * math.cos(th))))
        linhas.append(fila)
    for a, b in zip(linhas[:-1], linhas[1:]):
        for i in range(seg):
            bm.faces.new((a[i], a[(i+1) % seg], b[(i+1) % seg], b[i]))
    for fila, inv in ((linhas[0], True), (linhas[-1], False)):
        try:
            bm.faces.new(fila if inv else fila[::-1])
        except ValueError: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = obj_novo(nome, me, colecao, mat)
    m = ob.modifiers.get("Sub") or ob.modifiers.new("Sub", 'SUBSURF')
    m.levels, m.render_levels = 2, 2
    return ob

def motor(lado, suf):
    cy, cz = lado * M["cl_y"], M["cl_z"]
    xi = M["inlet_x"]
    RM = M["nacelle_od_max"] / 2          # 1.98
    # nacelle externa (fan cowl) — branca
    corpo_revolucao(f"Motor_Nacelle_{suf}", [
        (xi, 1.72), (xi + 0.25, 1.86), (xi + 0.9, 1.95), (xi + 1.7, RM),
        (xi + 2.9, 1.96), (xi + 4.0, 1.85), (M["fan_cowl_te_x"], 1.52)],
        cy, cz, "02_Motores", "LATAM_Branco")
    # lip metalico
    corpo_revolucao(f"Motor_Lip_{suf}", [
        (xi - 0.02, 1.60), (xi - 0.045, 1.68), (xi, 1.725)],
        cy, cz, "02_Motores", "MetalMotor")
    # duto interno ate o fan
    corpo_revolucao(f"Motor_Duto_{suf}", [
        (xi - 0.01, 1.60), (xi + 0.45, 1.63), (xi + 0.85, 1.625)],
        cy, cz, "02_Motores", "InletLiner")
    # disco do fan + spinner
    corpo_revolucao(f"Motor_Fan_{suf}", [
        (xi + 0.86, 1.62), (xi + 0.88, 0.30)], cy, cz, "02_Motores", "CinzaEscuro")
    corpo_revolucao(f"Motor_Spinner_{suf}", [
        (xi + 0.55, 0.02), (xi + 0.75, 0.22), (xi + 0.90, 0.30)],
        cy, cz, "02_Motores", "SpinnerCinza")
    # core cowl (cinza) e bocal
    corpo_revolucao(f"Motor_Core_{suf}", [
        (M["fan_cowl_te_x"] - 0.05, 1.50), (M["fan_cowl_te_x"] + 0.5, 1.28),
        (M["core_cowl_te_x"] - 0.3, 0.95), (M["core_cowl_te_x"], 0.78)],
        cy, cz, "02_Motores", "MetalMotor")
    corpo_revolucao(f"Motor_Bocal_{suf}", [
        (M["core_cowl_te_x"] - 0.02, 0.77), (M["core_cowl_te_x"] + 0.5, 0.62),
        (M["core_cowl_te_x"] + 0.85, 0.47)],
        cy, cz, "02_Motores", "TitanioExaust")
    corpo_revolucao(f"Motor_Plug_{suf}", [
        (M["core_cowl_te_x"] + 0.3, 0.44), (M["core_cowl_te_x"] + 1.0, 0.22),
        (M["core_cowl_te_x"] + 1.45, 0.03)],
        cy, cz, "02_Motores", "TitanioExaust")
    # pylon: caixa afinada ligando nacelle ao intradorso da asa
    bm = bmesh.new()
    zw = wing_z(M["cl_y"])                # plano da corda na estacao do motor
    pts = []
    x_le_w = wing_le(M["cl_y"])
    perfil_low = [(xi + 1.2, cz + 1.85), (xi + 2.6, cz + 1.9), (31.6, cz + 1.5),
                  (33.2, zw - 0.55), (33.8, zw - 0.35)]
    perfil_top = [(xi + 1.2, cz + 2.05), (x_le_w - 0.6, zw + 0.35), (31.8, zw + 0.42),
                  (33.2, zw + 0.40), (33.8, zw + 0.30)]
    W = 0.55
    linhas = []
    for (xl, zl), (xt, zt) in zip(perfil_low, perfil_top):
        fila = [bm.verts.new((xl, cy - W/2, zl)), bm.verts.new((xt, cy - W/2, zt)),
                bm.verts.new((xt, cy + W/2, zt)), bm.verts.new((xl, cy + W/2, zl))]
        linhas.append(fila)
    for a, b in zip(linhas[:-1], linhas[1:]):
        for i in range(4):
            bm.faces.new((a[i], a[(i+1) % 4], b[(i+1) % 4], b[i]))
    for f_, inv in ((linhas[0], False), (linhas[-1], True)):
        bm.faces.new(f_ if inv else f_[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(f"Motor_Pylon_{suf}"); bm.to_mesh(me); bm.free()
    ob = obj_novo(f"Motor_Pylon_{suf}", me, "02_Motores", "LATAM_Branco")
    m = ob.modifiers.get("Sub") or ob.modifiers.new("Sub", 'SUBSURF')
    m.levels, m.render_levels = 2, 2
motor(1, "D"); motor(-1, "E")
print("motores GE90 ok")

# ---------------------------------------------------------------- 6. trem
T = S["trem"]
def cilindro(nome, p0, p1, r, colecao, mat, seg=16):
    import mathutils
    v = mathutils.Vector(p1) - mathutils.Vector(p0)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=r, radius2=r, depth=v.length, segments=seg)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = obj_novo(nome, me, colecao, mat)
    ob.location = (mathutils.Vector(p0) + mathutils.Vector(p1)) / 2
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = v.to_track_quat('Z', 'Y')
    return ob

def roda(nome, cx, cy, cz, diam, larg):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=diam/2, radius2=diam/2, depth=larg, segments=24)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    ob = obj_novo(nome, me, "03_Trem", "Pneu")
    ob.rotation_euler = (math.pi/2, 0, 0)
    ob.location = (cx, cy, cz)
    return ob

solo = T["solo_z"]
# nariz
nx = T["nariz_x"]; nr = T["nariz_rodas"]
axle_nz = solo + nr["diam"]/2
cilindro("TremNariz_Perna", (nx, 0, -2.2), (nx, 0, axle_nz + 0.1), 0.14, "03_Trem", "StrutMetal")
cilindro("TremNariz_Eixo", (nx, -nr["gap"]/2 - 0.1, axle_nz), (nx, nr["gap"]/2 + 0.1, axle_nz), 0.07, "03_Trem", "StrutMetal")
for lado, sn in ((-1, "E"), (1, "D")):
    roda(f"TremNariz_Roda{sn}", nx, lado * nr["gap"]/2, axle_nz, nr["diam"], nr["larg"])
# principal
mb = T["principal_bogie"]; mx = T["principal_x"]; halftrack = T["bitola"]/2
axle_z = solo + mb["pneu_diam"]/2
for lado, sn in ((-1, "E"), (1, "D")):
    cy = lado * halftrack
    cilindro(f"TremP_Perna{sn}", (mx, cy, -1.6), (mx, cy, axle_z + 0.35), 0.20, "03_Trem", "StrutMetal")
    cilindro(f"TremP_Bogie{sn}", (mx - mb["entre_eixos_total"]/2 - 0.25, cy, axle_z + 0.28),
             (mx + mb["entre_eixos_total"]/2 + 0.25, cy, axle_z + 0.28), 0.16, "03_Trem", "StrutMetal")
    for k, dx in enumerate((-mb["entre_eixos"], 0.0, mb["entre_eixos"])):
        lat = mb["entre_rodas_lat_aft"] if k == 2 else mb["entre_rodas_lat"]
        ax = mx + dx
        cilindro(f"TremP_Eixo{sn}{k}", (ax, cy - lat/2 - 0.1, axle_z), (ax, cy + lat/2 + 0.1, axle_z), 0.08, "03_Trem", "StrutMetal")
        for l2, s2 in ((-1, "i"), (1, "o")):
            roda(f"TremP_Roda{sn}{k}{s2}", ax, cy + l2 * lat/2, axle_z, mb["pneu_diam"], mb["pneu_larg"])
print("trem ok (bogies de 6 rodas)")

# ---------------------------------------------------------------- 7. janelas + antenas
def fileira_janelas_77w():
    J = S["janelas_pax"]
    bm = bmesh.new()
    w, h, rad, nseg = J["abertura"][0], J["abertura"][1], 0.09, 3
    corners = [(w/2 - rad, h/2 - rad, 0), (-w/2 + rad, h/2 - rad, 90),
               (-w/2 + rad, -h/2 + rad, 180), (w/2 - rad, -h/2 + rad, 270)]
    verts = []
    for (ccx, ccz, a0) in corners:
        for i in range(nseg + 1):
            ang = math.radians(a0 + 90 * i / nseg)
            verts.append(bm.verts.new((ccx + rad * math.cos(ang), 0, ccz + rad * math.sin(ang))))
    bm.faces.new(verts)
    me = bpy.data.meshes.new("JanelasPax"); bm.to_mesh(me); bm.free()
    me.materials.append(bpy.data.materials["JanelaEscura"])
    ob = bpy.data.objects.get("JanelasPax")
    if ob: ob.data = me
    else:
        ob = bpy.data.objects.new("JanelasPax", me); col("04_Detalhes").objects.link(ob)
    ob.location = (J["faixa_x"][0], -3.4, J["centro_z"])
    n = int((J["faixa_x"][1] - J["faixa_x"][0]) / J["pitch"])
    arr = ob.modifiers.get("Array") or ob.modifiers.new("Array", 'ARRAY')
    arr.count = n; arr.use_relative_offset = False; arr.use_constant_offset = True
    arr.constant_offset_displace = (J["pitch"], 0, 0)
    mir = ob.modifiers.get("Mirror") or ob.modifiers.new("Mirror", 'MIRROR')
    mir.use_axis = (False, True, False)
    mir.mirror_object = bpy.data.objects["Fuselagem"]
    sw = ob.modifiers.get("Shrinkwrap") or ob.modifiers.new("Shrinkwrap", 'SHRINKWRAP')
    sw.target = bpy.data.objects["Fuselagem"]
    sw.wrap_method = 'PROJECT'; sw.use_project_y = True
    sw.use_positive_direction = True; sw.use_negative_direction = True
    sw.offset = 0.012
fileira_janelas_77w()

def antena(nome, x, z, comp, alt):
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in [(x, 0, z), (x + comp, 0, z), (x + comp * 0.75, 0, z + alt), (x + comp * 0.35, 0, z + alt)]]
    bm.faces.new(v)
    r = bmesh.ops.solidify(bm, geom=bm.faces[:] + bm.verts[:] + bm.edges[:], thickness=0.05)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    obj_novo(nome, me, "04_Detalhes", "LATAM_Branco")
antena("AntenaVHF1", 20.0, 3.05, 0.9, 0.42)
antena("AntenaVHF2", 44.0, 3.05, 0.9, 0.42)
# SATCOM lombada
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0)
for v in bm.verts:
    v.co.x = v.co.x * 1.9 + 31.0
    v.co.y *= 0.45
    v.co.z = max(v.co.z, 0) * 0.28 + 3.02
me = bpy.data.meshes.new("AntenaSAT"); bm.to_mesh(me); bm.free()
obj_novo("AntenaSAT", me, "04_Detalhes", "LATAM_Branco")
print("detalhes ok")

# ---------------------------------------------------------------- 8. validacao
import mathutils
dg = bpy.context.evaluated_depsgraph_get()
fus_ev = bpy.data.objects["Fuselagem"].evaluated_get(dg)
print("--- raycast sanity ---")
sondas = [
    ((30.0, -10.0, 0.0), (0, 1, 0), 10.0 - 3.10),
    ((30.0, 0.0, 10.0), (0, 0, -1), 10.0 - 3.10),
    ((30.0, 0.0, -10.0), (0, 0, 1), 10.0 - 3.10),
    ((3.0, -10.0, 0.0), (0, 1, 0), 10.0 - 1.833 * 1.0),
    ((65.0, 0.0, 10.0), (0, 0, -1), 10.0 - (0.765 + 2.015)),
]
for origem, d, esperado in sondas:
    hit, loc, *_ = fus_ev.ray_cast(mathutils.Vector(origem), mathutils.Vector(d))[:2] + (0,)
    if hit:
        dist = (mathutils.Vector(loc) - mathutils.Vector(origem)).length
        print(f"  {origem} -> {dist:.3f} (esp {esperado:.3f}) {'ok' if abs(dist-esperado)<0.08 else 'FORA'}")
    else:
        print(f"  {origem} SEM HIT")

# camadas de cena: reposicionar alvos/cameras pela razao de comprimento 777/787.
# IDEMPOTENTE: so aplica uma vez (rerodar o build nao pode empurrar as cameras
# para longe outra vez).
K = 73.86 / 62.81
if not bpy.context.scene.get("cams_reescaladas_77w"):
    for nome in ["CamAlvo", "CamAlvoCauda", "CamAlvoFrontal", "CamAlvoNariz", "CamAlvoBarriga",
                 "CamHero", "CamCauda", "CamFrontal", "CamNariz", "CamBarriga", "CamPerfil",
                 "CamOrtoFrente", "CamBomb", "CamEstib"]:
        o = bpy.data.objects.get(nome)
        if o: o.location = tuple(v * K for v in o.location)
    bpy.context.scene["cams_reescaladas_77w"] = 1
    print("cameras reescaladas x%.3f" % K)
else:
    print("cameras ja estavam reescaladas — nada a fazer")

bpy.ops.wm.save_mainfile()
print("SALVO B77W_LATAM.blend")
