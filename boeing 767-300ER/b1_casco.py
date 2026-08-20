"""Etapa 1 — casco do 767-300ER a partir do spec_763.json.

Roda headless:
/Applications/Blender.app/Contents/MacOS/Blender -b "boeing 767-300ER/B763_LATAM.blend" --python "boeing 767-300ER/b1_casco.py"

Gaiola esparsa nas estacoes reais + Catmull-Clark 3 (metodo casco-parametrico).
Secao mestre = uniao de dois circulos medida na p43; pinca do lobo superior no
cockpit; cauda com elipse (rz, ry) — o 767 comprime a cauda lateralmente.
"""
import bpy
import bmesh
import json
import math
import os

BASE = "/Users/sargam/Documents/Developer/Latam Airlines Model Planes/boeing 767-300ER"
spec = json.load(open(os.path.join(BASE, "spec_763.json")))

SEG = 32
COMP = 1.0064

# ---------------- secao mestre: dois circulos de raio IGUAL ----------------
# Ajuste por minimos quadrados ao contorno desenhado na p43 do ACAP a 600 dpi
# (2026-08-20, 318+311 amostras, RMS 0.3-0.4 cm): os dois lobos tem o MESMO
# raio ~2.515 (= metade da largura impressa 5.03) e os centros ficam a 2.514 e
# 2.9035 de profundidade abaixo da crista, ou seja z=+0.191 e z=-0.1985 no
# referencial do projeto.  Fecha a quilha em -2.706, contra os 5.41 impressos.
# (O modelo anterior — lobo inferior r=2.466 centrado a 3.078 — passava do
# fundo e precisava de um fecho artificial que deixava uma quilha chata de
# 1.60 m de largura; era ele que engordava a barriga.)
RU, CU = 2.521, 0.191      # lobo superior: raio, centro_z
RL, CL = 2.5075, -0.1985   # lobo inferior
ZTOP, ZBOT = 2.712, -2.706

def hw_master(z):
    """meia-largura da secao mestre em z (constante), normalizada p/ 2.515."""
    if z >= CU:
        h = RU * RU - (z - CU) ** 2
    elif z <= CL:
        h = RL * RL - (z - CL) ** 2
    else:
        return 1.0                      # flanco reto entre os dois centros
    return (math.sqrt(h) if h > 0 else 0.0) / 2.515

def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def pinca(x, cos_t):
    """pinca do lobo superior na zona do cockpit (a validar no gate)."""
    if cos_t <= 0:
        return 1.0
    g = smoothstep((x - 1.2) / 1.2) * (1.0 - smoothstep((x - 3.2) / 2.0))
    return 1.0 - 0.30 * g * (smoothstep(cos_t) ** 1.6)

# ---------------- aneis ----------------
aneis = []   # (x, zc, rz, ry, mistura_master)
for x, crown, keel, w2 in spec["nariz_estacoes"][1:]:
    zc = (crown + keel) / 2.0
    rz = (crown - keel) / 2.0
    mix = smoothstep((x - 0.4) / 4.6)      # circulo na ponta -> master em x~5
    aneis.append((x, zc, rz, max(w2, 0.05), mix))
# barril: aneis identicos a cada ~2.8 m (7.5 .. 40.0)
x0, x1 = 7.5, 40.0
n = int(round((x1 - x0) / 2.8))
for i in range(1, n + 1):
    aneis.append((x0 + i * (x1 - x0) / n, 0.0, 2.705, 2.515, 1.0))
# cauda: elipses (rz, ry)
for x, zc, rz, ry in spec["cauda_estacoes"]:
    aneis.append((x, zc, rz, ry, -1.0))    # -1 => elipse pura

def secao(x, th, zc, rz, ry, mix):
    ct = math.cos(th)
    st = math.sin(th)
    z = rz * ct
    if mix < 0:                             # cauda: elipse
        y = ry * st
        return y, z
    # nariz/barril: master profile por profundidade normalizada
    z_master = ZTOP - (1.0 - ct) / 2.0 * (ZTOP - ZBOT)   # mapeia theta -> z da secao mestre
    hwn = hw_master(z_master)               # 0..1
    hw_circ = abs(st)
    hw = (1.0 - mix) * hw_circ + mix * hwn
    y = math.copysign(hw * ry / (1.0 if mix < 0.5 else 1.0), st)
    # a largura do spec (w2) e a MAXIMA da secao; hwn max = 1 -> escala direta
    y = math.copysign(hw * ry, st)
    y *= pinca(x, ct)
    return y, z

# ---------------- construir ----------------
bm = bmesh.new()
anelverts = []
for (x, zc, rz, ry, mix) in aneis:
    linha = []
    for s in range(SEG):
        th = 2 * math.pi * s / SEG
        y, z = secao(x, th, zc, rz, ry, mix)
        linha.append(bm.verts.new((x, y * COMP, zc + z * COMP)))
    anelverts.append(linha)
for a, b in zip(anelverts[:-1], anelverts[1:]):
    for s in range(SEG):
        bm.faces.new((a[s], a[(s + 1) % SEG], b[(s + 1) % SEG], b[s]))
# pontas
v0 = bm.verts.new((0.0, 0.0, -0.458))
for s in range(SEG):
    bm.faces.new((anelverts[0][s], v0, anelverts[0][(s + 1) % SEG]))
vN = bm.verts.new((54.30, 0.0, 0.95))
for s in range(SEG):
    bm.faces.new((anelverts[-1][s], anelverts[-1][(s + 1) % SEG], vN))

bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("Fuselagem")
bm.to_mesh(me)
bm.free()
for p in me.polygons:
    p.use_smooth = True

ob = bpy.data.objects["Fuselagem"]
mat_antigo = ob.data.materials[0] if ob.data.materials else None
antigo = ob.data
ob.data = me
bpy.data.meshes.remove(antigo)
if mat_antigo:
    me.materials.append(mat_antigo)
for m in ob.modifiers:
    if m.type == 'SUBSURF':
        m.levels, m.render_levels = 2, 3

# ---------------- UV (x, theta) ----------------
xs = [a[0] for a in aneis]
zcs = [a[1] for a in aneis]
COMPRIMENTO_UV = 55.5

def centro(x):
    if x <= xs[0]:
        return zcs[0]
    for (xa, za), (xb, zb) in zip(zip(xs[:-1], zcs[:-1]), zip(xs[1:], zcs[1:])):
        if xa <= x <= xb:
            f = (x - xa) / max(xb - xa, 1e-9)
            return za + f * (zb - za)
    return zcs[-1]

uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
for loop in me.loops:
    co = me.vertices[loop.vertex_index].co
    zc = centro(co.x)
    th = math.atan2(co.y, co.z - zc) if (abs(co.y) > 1e-9 or abs(co.z - zc) > 1e-9) else 0.0
    uv.data[loop.index].uv = (co.x / COMPRIMENTO_UV, (th + math.pi) / (2 * math.pi))
for p in me.polygons:
    vs = [uv.data[li].uv[1] for li in p.loop_indices]
    if max(vs) - min(vs) > 0.5:
        for li in p.loop_indices:
            if uv.data[li].uv[1] < 0.5:
                uv.data[li].uv = (uv.data[li].uv[0], uv.data[li].uv[1] + 1.0)

# ---------------- validacao ----------------
dg = bpy.context.evaluated_depsgraph_get()
oev = ob.evaluated_get(dg)
from mathutils import Vector
print("== sondas raycast (superficie subdividida) ==")
sondas = [
    ((20.0, 10.0, 0.19), (0, -1, 0), 10.0 - 2.515),
    ((20.0, -10.0, 0.19), (0, 1, 0), 10.0 - 2.515),
    ((20.0, 0.0, 10.0), (0, 0, -1), 10.0 - 2.705),
    ((20.0, 0.0, -10.0), (0, 0, 1), 10.0 - 2.705),
    ((5.7, 10.0, 0.0), (0, -1, 0), 10.0 - 2.435),   # spec 2.427 em x=5.7 x COMP
    ((48.0, 10.0, 0.65), (0, -1, 0), 10.0 - 1.445),
    ((48.0, 0.0, 10.0), (0, 0, -1), 10.0 - (0.65 + 1.608)),
]
for origem, direcao, esperado in sondas:
    hit, loc, _n, _i = oev.ray_cast(Vector(origem), Vector(direcao))[:4]
    if not hit:
        print("  SEM HIT", origem)
        continue
    d = (Vector(loc) - Vector(origem)).length
    print(f"  {origem} -> {d:.3f} (esp {esperado:.3f}) {'ok' if abs(d-esperado)<0.05 else 'FORA'}")

print("== gaiola: max|y|/w2_spec por anel (alvo=COMP) ==")
import numpy as np
for (x, zc, rz, ry, mix) in aneis[::4]:
    vs = [v.co for v in me.vertices if abs(v.co.x - x) < 1e-6]
    if not vs:
        continue
    maxy = max(abs(v.y) for v in vs)
    print(f"  x={x:6.2f} max|y|={maxy:.3f} ry_spec={ry:.3f} ratio={maxy/max(ry,1e-9):.4f}")

bpy.ops.wm.save_mainfile()
print("SALVO", bpy.data.filepath)
