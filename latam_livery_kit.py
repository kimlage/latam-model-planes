"""Reusable LATAM livery kit for the Blender models in the
"Latam Airlines Model Planes" folder.

Usage: run inside Blender (or via MCP execute_blender_code) with
`exec(open(".../latam_livery_kit.py").read())` and call the functions.

Official assets at the project root (Wikimedia Commons):
- latam_logo_indigo.svg  — official LATAM lockup (coral symbol #ED1651 + wordmark #2A0088)
- airbus_a320neo_logo.svg — official "AIRBUS A320neo" logotype

Project directive: a faithful replica of the real LATAM aircraft — exact brand
(official SVG, never a lookalike font) and application identical to the fleet's
(reference: photo of PT-TMN):
- Eurowhite fuselage; large lockup above the window line, behind door 1.
- Tail: INDIGO fin carrying parallel bands that cross it edge to edge, each band
  flight-gray at both ends with a coral core, plus a flight-gray cap at the tip.
  (The older reading -- white fin, thick bands, F1..F7 polylines -- is obsolete;
  see the livery-latam skill.)
- Rear fuselage: a triangular indigo wedge continuous with the indigo mass at the
  fin root. It is NOT a circumferential wrap: it is bounded by three surfaces,
  and they do not all live in the same space --
      x >= 48.77 + 0.992*z          forward, parallel to the straight fin LE
      theta <= 117.0 - 5.2*(x-48.70) lower, a straight line in (x,theta)
      x <= 57.14 + 0.3858*z         rear, the fin trailing-edge line
  (787-9 frame; the A320neo triple is in spec_a320.json). Belly and tailcone white.
- White registration on the indigo wedge.
- Sharklets: indigo outboard (white fillet on the leading edge), white+coral inboard.
- White nacelles, metallic lip, greenish liner, titanium exhaust.
- Giant mark on the belly (read from below, nose to the left).
- Wings/stabilizers in Airbus grey (#C9CDD2); grey belly fairing.
"""
import bpy
import bmesh
import math
import mathutils

# ---------------------------------------------------------------- palette
PALETA = {
    "LATAM_Indigo": ("#2A0088", 0.30, 0.0, 0.5),
    "LATAM_Coral": ("#ED1651", 0.30, 0.0, 0.5),
    "LATAM_Branco": ("#F7F9FA", 0.30, 0.0, 0.4),
    "CinzaAsa": ("#C9CDD2", 0.35, 0.0, 0.0),
    "CinzaBarriga": ("#C9CDD2", 0.35, 0.0, 0.0),
    "VidroCockpit": ("#0A0E14", 0.08, 0.0, 0.8),
    "MascaraCockpit": ("#0B0D10", 0.50, 0.0, 0.0),
    "JanelaEscura": ("#101318", 0.15, 0.0, 0.0),
    "MetalMotor": ("#8A8F94", 0.25, 1.0, 0.0),
    "TitanioExaust": ("#6E6A66", 0.35, 1.0, 0.0),
    "InletLiner": ("#9FB8B0", 0.45, 0.0, 0.0),
    "AirbusNavy": ("#1C2E63", 0.35, 0.0, 0.0),
    "Pneu": ("#1C1D1E", 0.85, 0.0, 0.0),
}

# sRGB colours for textures (rasterization)
COR_TEX = {"branco": (0.969, 0.976, 0.980),
           "coral": (0.929, 0.086, 0.318),
           "indigo": (0.165, 0.000, 0.533)}


def hex_to_linear(h):
    h = h.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def criar_paleta():
    """Creates/updates every material in the palette. Returns dict name->material."""
    mats = {}
    for nome, (hx, rough, metal, coat) in PALETA.items():
        m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = hex_to_linear(hx)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        if "Coat Weight" in b.inputs:
            b.inputs["Coat Weight"].default_value = coat
        m.diffuse_color = hex_to_linear(hx)
        mats[nome] = m
    return mats


# ------------------------------------------------- SVG -> flat 2D meshes
def importar_svg_2_camadas(filepath):
    """Imports an SVG and returns (mesh_indigo, mesh_coral) FLAT (z=0),
    normalized with the origin at the lower-left corner, with NO scale applied.
    Classifies each curve by its fill colour (R>B = coral)."""
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=filepath)
    imported = [o for o in bpy.data.objects if o not in before]

    def is_coral(obj):
        for m in obj.data.materials:
            if not m:
                continue
            col = None
            if m.use_nodes:
                for n in m.node_tree.nodes:
                    if hasattr(n, "inputs") and n.inputs and "Color" in n.inputs:
                        col = tuple(n.inputs["Color"].default_value[:3])
                        break
            if col is None:
                col = tuple(m.diffuse_color[:3])
            return col[0] > col[2]
        return False

    dg = bpy.context.evaluated_depsgraph_get()
    bms = {"i": bmesh.new(), "c": bmesh.new()}
    for o in imported:
        alvo = bms["c"] if is_coral(o) else bms["i"]
        mev = o.evaluated_get(dg).to_mesh()
        vmap = {}
        for p in mev.polygons:
            nv = []
            for vi in p.vertices:
                if vi not in vmap:
                    vmap[vi] = alvo.verts.new(o.matrix_world @ mev.vertices[vi].co)
                nv.append(vmap[vi])
            try:
                alvo.faces.new(nv)
            except ValueError:
                pass
        o.evaluated_get(dg).to_mesh_clear()
    for o in imported:
        bpy.data.objects.remove(o, do_unlink=True)

    todos_x = [v.co.x for bm in bms.values() for v in bm.verts]
    todos_y = [v.co.y for bm in bms.values() for v in bm.verts]
    x0, y0 = min(todos_x), min(todos_y)
    meshes = {}
    for k, bm in bms.items():
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        for _ in range(2):
            bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1)
        for v in bm.verts:
            v.co = mathutils.Vector((v.co.x - x0, v.co.y - y0, 0.0))
        me = bpy.data.meshes.new("svg_" + k)
        bm.to_mesh(me)
        bm.free()
        meshes[k] = me
    return meshes["i"], meshes["c"]


def decal_logo(nome, mesh, material, alvo, loc, rot, escala, eixo='Y',
               positivo=True, offset=0.012, colecao=None):
    """Creates a shrinkwrap decal from a flat 2D mesh onto `alvo`.
    The indigo layer must use a LARGER offset than the coral one (SVG painting
    order: indigo on top, e.g. 0.016 vs 0.010)."""
    me = mesh.copy()
    for v in me.vertices:
        v.co = v.co * escala
    me.materials.clear()
    me.materials.append(material)
    obj = bpy.data.objects.new(nome, me)
    (colecao or bpy.context.scene.collection).objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    sw = obj.modifiers.new("Shrinkwrap", 'SHRINKWRAP')
    sw.target = alvo
    sw.wrap_method = 'PROJECT'
    setattr(sw, "use_project_" + eixo.lower(), True)
    sw.use_positive_direction = positivo
    sw.use_negative_direction = not positivo
    sw.offset = offset
    return obj


# ------------------------------------------------- tail: rasterized sash
def raster_sash_deriva(img_nome, mesh_indigo, mesh_coral, dominio, transform,
                       flood=None, tamanho=2048):
    """Generates the fin texture by rasterizing the enlarged official symbol.
    dominio = (X0, X1, Z0, Z1) in metres in the fin plane (planar UV along Y).
    transform = (SX, SZ, S): local_symbol*(S) + (SX, SZ).
      A320neo calibration (fin ~6.5 m tall, root chord ~6.4 m):
      S ≈ 1.62x the fin height; top of the symbol ~0.15*S above the tip;
      creases falling ~60% of the mean chord. Values used: SX=26.0, SZ=-5.9, S=10.5
      with domain (27.4, 35.4, 1.4, 8.4).
    flood = (z0, slope, x_ref): paints indigo where Z <= z0 + slope*(X - x_ref)
      (the base mass that joins the wrap; used (1.9, 0.536, 29.5))."""
    import numpy as np
    W = H = tamanho
    X0, X1, Z0, Z1 = dominio
    SX, SZ, S = transform
    arr = np.empty((H, W, 4), dtype=np.float32)
    arr[..., 0:3] = COR_TEX["branco"]
    arr[..., 3] = 1.0

    def to_pix(x, z):
        return ((x - X0) / (X1 - X0) * (W - 1), (z - Z0) / (Z1 - Z0) * (H - 1))

    def raster(me, cor):
        me.calc_loop_triangles()
        vs = me.vertices
        for tri in me.loop_triangles:
            pts = [vs[i].co for i in tri.vertices]
            pix = [to_pix(SX + p.x * S, SZ + p.y * S) for p in pts]
            xs = [p[0] for p in pix]
            ys = [p[1] for p in pix]
            xlo, xhi = max(int(min(xs)), 0), min(int(max(xs)) + 1, W - 1)
            ylo, yhi = max(int(min(ys)), 0), min(int(max(ys)) + 1, H - 1)
            if xhi <= xlo or yhi <= ylo:
                continue
            gx, gy = np.meshgrid(np.arange(xlo, xhi + 1), np.arange(ylo, yhi + 1))
            (ax, ay), (bx, by), (cx, cy) = pix
            d1 = (gx - bx) * (ay - by) - (ax - bx) * (gy - by)
            d2 = (gx - cx) * (by - cy) - (bx - cx) * (gy - cy)
            d3 = (gx - ax) * (cy - ay) - (cx - ax) * (gy - ay)
            mask = ~((((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0))))
            sub = arr[ylo:yhi + 1, xlo:xhi + 1]
            for k in range(3):
                sub[..., k] = np.where(mask, cor[k], sub[..., k])

    raster(mesh_coral, COR_TEX["coral"])    # coral first
    raster(mesh_indigo, COR_TEX["indigo"])  # indigo on top (SVG order)

    if flood:
        z0, slope, xref = flood
        u = np.linspace(X0, X1, W)
        v = np.linspace(Z0, Z1, H)
        Xg, Zg = np.meshgrid(u, v)
        m = Zg <= z0 + slope * (Xg - xref)
        for k in range(3):
            arr[..., k] = np.where(m, COR_TEX["indigo"][k], arr[..., k])

    img = bpy.data.images.get(img_nome) or bpy.data.images.new(img_nome, W, H, alpha=False)
    if img.size[0] != W:
        img.scale(W, H)
    img.pixels.foreach_set(arr.ravel())
    img.pack()
    return img


def uv_planar_deriva(obj, dominio):
    """Planar UV (projection along Y) to apply the sash texture on both sides."""
    X0, X1, Z0, Z1 = dominio
    me = obj.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((co.x - X0) / (X1 - X0), (co.z - Z0) / (Z1 - Z0))
    return uv


# ------------------------------------------------- parameterized details
def fileira_janelas(nome, alvo, x_inicio, z, n, passo=0.533, w=0.23, h=0.33,
                    colecao=None):
    """Row of passenger windows (decal + array + mirror + shrinkwrap).
    Real A320 pitch: 533 mm."""
    bm = bmesh.new()
    verts = []
    rad, nseg = 0.10, 3
    corners = [(w / 2 - rad, h / 2 - rad, 0), (-w / 2 + rad, h / 2 - rad, 90),
               (-w / 2 + rad, -h / 2 + rad, 180), (w / 2 - rad, -h / 2 + rad, 270)]
    for (ccx, ccz, a0) in corners:
        for i in range(nseg + 1):
            a = math.radians(a0 + 90 * i / nseg)
            verts.append(bm.verts.new((ccx + rad * math.cos(a), 0,
                                       ccz + rad * math.sin(a))))
    bm.faces.new(verts)
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bpy.data.materials["JanelaEscura"])
    obj = bpy.data.objects.new(nome, me)
    (colecao or bpy.context.scene.collection).objects.link(obj)
    obj.location = (x_inicio, -alvo.dimensions.y, z)
    arr = obj.modifiers.new("Array", 'ARRAY')
    arr.count = n
    arr.use_relative_offset = False
    arr.use_constant_offset = True
    arr.constant_offset_displace = (passo, 0, 0)
    mir = obj.modifiers.new("Mirror", 'MIRROR')
    mir.use_axis = (False, True, False)
    mir.mirror_object = alvo
    sw = obj.modifiers.new("Shrinkwrap", 'SHRINKWRAP')
    sw.target = alvo
    sw.wrap_method = 'PROJECT'
    sw.use_project_y = True
    sw.use_positive_direction = True
    sw.use_negative_direction = True
    sw.offset = 0.012
    return obj


def moldura_porta(nome, alvo, cx, cz, w, h, borda=0.04, espelhar=True,
                  lado_y=-2.6, colecao=None):
    """Door frame (thin ring) by shrinkwrap. espelhar=False for cargo doors
    (right side only: positive lado_y + negative projection)."""
    bm = bmesh.new()

    def rrect(w_, h_, rad, nseg=3):
        pts = []
        corners = [(w_ / 2 - rad, h_ / 2 - rad, 0), (-w_ / 2 + rad, h_ / 2 - rad, 90),
                   (-w_ / 2 + rad, -h_ / 2 + rad, 180), (w_ / 2 - rad, -h_ / 2 + rad, 270)]
        for (ccx, ccz, a0) in corners:
            for i in range(nseg + 1):
                a = math.radians(a0 + 90 * i / nseg)
                pts.append((ccx + rad * math.cos(a), ccz + rad * math.sin(a)))
        return pts

    vo = [bm.verts.new((cx + px, lado_y, cz + pz)) for (px, pz) in rrect(w, h, 0.18)]
    vi = [bm.verts.new((cx + px, lado_y, cz + pz))
          for (px, pz) in rrect(w - 2 * borda, h - 2 * borda, 0.15)]
    n = len(vo)
    for i in range(n):
        bm.faces.new((vo[i], vo[(i + 1) % n], vi[(i + 1) % n], vi[i]))
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bpy.data.materials.get("MolduraPorta")
                        or bpy.data.materials["CinzaAsa"])
    obj = bpy.data.objects.new(nome, me)
    (colecao or bpy.context.scene.collection).objects.link(obj)
    if espelhar:
        mir = obj.modifiers.new("Mirror", 'MIRROR')
        mir.use_axis = (False, True, False)
        mir.mirror_object = alvo
    sw = obj.modifiers.new("Shrinkwrap", 'SHRINKWRAP')
    sw.target = alvo
    sw.wrap_method = 'PROJECT'
    sw.use_project_y = True
    sw.use_positive_direction = lado_y < 0
    sw.use_negative_direction = lado_y > 0
    sw.offset = 0.014
    return obj


def luzes_navegacao(colecao, pos_esq, pos_dir, pos_beacon=None, pos_cauda=None):
    """Red to port, green to starboard (separate objects — a mirror would swap the colour)."""
    def emissivo(nome, hx):
        m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = hex_to_linear(hx)
        b.inputs["Emission Color"].default_value = hex_to_linear(hx)
        b.inputs["Emission Strength"].default_value = 6.0
        return m

    def blob(nome, loc, mat, r=0.07):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8,
                                             radius=r, location=loc)
        o = bpy.context.active_object
        o.name = nome
        for p in o.data.polygons:
            p.use_smooth = True
        o.data.materials.append(mat)
        for c in list(o.users_collection):
            c.objects.unlink(o)
        colecao.objects.link(o)
        return o

    blob("NavEsq", pos_esq, emissivo("LuzVermelha", "#FF2A2A"))
    blob("NavDir", pos_dir, emissivo("LuzVerde", "#2AFF55"))
    if pos_beacon:
        blob("Beacon", pos_beacon, emissivo("LuzVermelha", "#FF2A2A"), r=0.06)
    if pos_cauda:
        blob("LuzCauda", pos_cauda, emissivo("LuzBranca", "#FFFFFF"), r=0.045)


# ---------------------------------------------------------------- door rings
# A TINTA VIVE NA SUPERFICIE DESENVOLVIDA.
#
# Ate 2026-08-21 as cinco Airbus pintavam o contorno das portas com um
# `rounded_rect(Xg, Zg, ...)` — um retangulo na PROJECAO LATERAL (x, z) — sobre
# uma folha construida ANALITICAMENTE NA SUPERFICIE. Em cima do ombro os dois
# divergem: na A320neo, acima de z = 1.4 a folha da porta 1 vive em |y|
# 1.571..1.831 e o anel pintado caia em |y| 0.865..1.114 — 0.5 a 0.7 m de
# distancia no mesmo casco. Era a "porta 1 fantasma" do backlog, e e o mesmo
# defeito que o para-brisa teve (b28fa20), que o 777 teve (22500e6) e que o 767
# teve duas vezes (f2f96cd, d401766).
#
# A correcao e a mesma: descrever o anel num espaco METRICO (x, w) com
# w = comprimento de ARCO da secao, medido no proprio casco, e deslocar o
# poligono NESSE espaco. O 767 tinha tentado dilatacao por bandas e ela rasgava
# as bordas em deslocamentos grandes; o offset de poligono nao rasga.
#
# Estas quatro funcoes sao a UNICA implementacao: os builders das cinco
# aeronaves as chamam em vez de carregar uma copia cada um.

def grade_arco(rx, rrz, rry, X, TH):
    """(H, W) com w(x, theta) em METROS DE ARCO a partir da crista (theta = 0).

    rx/rrz/rry sao a tabela de aneis que a propria textura ja usa (o casco e uma
    elipse por estacao: y = ry*sin(theta), z = zc + rz*cos(theta)), X e o vetor
    de x das colunas e TH o vetor de theta das linhas. w e negativo a bombordo e
    positivo a boreste, como sin(theta).
    """
    import numpy as np
    ry = np.interp(X, rx, rry)[None, :]
    rz = np.interp(X, rx, rrz)[None, :]
    th = np.asarray(TH)[:, None]
    f = np.hypot(ry * np.cos(th), rz * np.sin(th))      # |d(y,z)/dtheta|
    dth = float(TH[1] - TH[0])
    w = np.cumsum(f, axis=0) * dth - 0.5 * f * dth      # trapezio
    i0 = int(np.argmin(np.abs(np.asarray(TH))))
    return w - w[i0][None, :]


def arco_do_ponto(rx, rzc, rrz, rry, x, y, z, n=512):
    """w de pontos soltos (os vertices de uma folha de porta), mesmo referencial."""
    import numpy as np
    x = np.asarray(x, float)
    ry = np.interp(x, rx, rry)
    rz = np.interp(x, rx, rrz)
    zc = np.interp(x, rx, rzc)
    th = np.arctan2(np.asarray(y, float) / ry, (np.asarray(z, float) - zc) / rz)
    t = np.linspace(0.0, 1.0, n)[None, :] * th[:, None]
    f = np.hypot(ry[:, None] * np.cos(t), rz[:, None] * np.sin(t))
    return np.trapezoid(f, t, axis=1) if hasattr(np, "trapezoid") \
        else np.trapz(f, t, axis=1)


def caixa_porta_xw(ob, rx, rzc, rrz, rry):
    """(x0, x1, w0, w1) da folha, medida NA SUPERFICIE.

    Le a malha em coordenadas de MUNDO (a matriz do objeto entra: varias portas
    da familia carregam o deslocamento do esticamento da A321 em `location`).
    """
    import numpy as np
    P = np.array([(ob.matrix_world @ v.co)[:] for v in ob.data.vertices], float)
    w = arco_do_ponto(rx, rzc, rrz, rry, P[:, 0], P[:, 1], P[:, 2])
    return P[:, 0].min(), P[:, 0].max(), w.min(), w.max()


def anel_porta(Xg, Wg, caixa, band_w=0.0, groove_w=0.0, raio=0.15):
    """(mascara da banda FAR, mascara do sulco) para uma porta, em (x, w).

    band_w e groove_w sao METROS DE ARCO, nao graus e nao metros de projecao:
    misturar um recuo no plano com um recuo em arco foi o que distorceu os
    montantes do 767 em 20-30%.
    """
    import numpy as np

    def rr(x0, x1, w0, w1, r):
        ix0, ix1 = x0 + r, x1 - r
        iw0, iw1 = w0 + r, w1 - r
        dx = np.maximum(np.maximum(ix0 - Xg, Xg - ix1), 0)
        dw = np.maximum(np.maximum(iw0 - Wg, Wg - iw1), 0)
        return np.hypot(dx, dw) <= r

    x0, x1, w0, w1 = caixa
    dentro = rr(x0, x1, w0, w1, raio)
    banda = rr(x0 - band_w, x1 + band_w, w0 - band_w, w1 + band_w, raio) & ~dentro
    sulco = dentro & ~rr(x0 + groove_w, x1 - groove_w,
                         w0 + groove_w, w1 - groove_w, raio)
    return banda, sulco


def assentar_na_secao(ob, rx, rzc, rrz, rry, saliencia=0.010, grau=2):
    """Reassenta um painel (folha de porta) NA SECAO do casco, radialmente.

    Preserva (x, theta) de cada vertice — ou seja, a pegada ANGULAR e o tamanho
    em arco do painel nao mudam — e refaz so a distancia radial: superficie mais
    `saliencia`, mais o RELEVO PROPRIO do painel (janela, manopla, sulco), que e
    o residuo de t em relacao a uma tendencia suave em theta.

    Existe porque as folhas das portas pax das cinco Airbus foram ERGUIDAS em z
    (+0.55/+0.57, tabela de soleiras do ACAP 2-3-0) por uma translacao pura, sem
    reprojetar. Um painel que abraca o ombro, subido 0.55 m em z, sai do casco:
    no topo da porta 1 da A320neo a folha ficava em |y| 1.585 com o casco em
    0.889 — 0.70 m de fora. E o mesmo erro de classe do anel pintado em (x, z),
    so que na malha.

    Devolve (t_antes_mediano, t_depois_mediano).
    """
    import numpy as np
    if ob.data.users > 1:
        ob.data = ob.data.copy()          # portas clonadas compartilham a malha
    M = ob.matrix_world
    Mi = M.inverted()
    P = np.array([(M @ v.co)[:] for v in ob.data.vertices], float)
    zc = np.interp(P[:, 0], rx, rzc)
    rz = np.interp(P[:, 0], rx, rrz)
    ry = np.interp(P[:, 0], rx, rry)
    a = P[:, 1] / ry
    b = (P[:, 2] - zc) / rz
    th = np.arctan2(a, b)
    t = np.hypot(a, b)
    rho = np.hypot(ry * np.sin(th), rz * np.cos(th))   # raio local da secao
    tend = np.polyval(np.polyfit(th, t, grau), th)
    relevo = (t - tend) * rho
    t_novo = 1.0 + (saliencia + relevo) / rho
    novo = np.stack([P[:, 0],
                     ry * np.sin(th) * t_novo,
                     zc + rz * np.cos(th) * t_novo], axis=1)
    for v, p in zip(ob.data.vertices, novo):
        v.co = Mi @ mathutils.Vector((p[0], p[1], p[2]))
    ob.data.update()
    return float(np.median(t)), float(np.median(t_novo))
