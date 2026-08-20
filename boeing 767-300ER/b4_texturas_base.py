"""Etapa 4a — texturas independentes da fotogrametria:
PanelBump (767 e de aluminio: juntas de barril + lap joints + junta do radome)
e AsaLinhas (linhas de comando da asa).

/Applications/Blender.app/Contents/MacOS/Blender -b "boeing 767-300ER/B763_LATAM.blend" --python "boeing 767-300ER/b4_texturas_base.py"
"""
import bpy
import numpy as np

D = bpy.data
LUV = 55.5          # comprimento do dominio UV (u = x/LUV)
W, H = 4096, 1024

# ---------------------------------------------------------------- PanelBump
# meio-cinza = neutro; claro = crista de junta
arr = np.full((H, W), 0.5, np.float32)

def linha_circ(x_m, forca=0.22, larg_px=2):
    c = int(x_m / LUV * W)
    arr[:, max(0, c - larg_px):c + larg_px + 1] += forca

def lap_joint(v_frac, forca=0.10):
    r = int(v_frac * H)
    arr[max(0, r - 1):r + 2, :] += forca

# junta do radome (x~2.0) e juntas de producao do 767 (sec 41/43/44/46/48)
linha_circ(2.00, 0.30, 2)
for xj in (10.3, 16.8, 23.3, 29.8, 36.3, 42.8, 47.5):
    linha_circ(xj, 0.16, 1)
# lap joints longitudinais (theta: v=0 quilha, 0.5 crista)
for vf in (0.30, 0.385, 0.62, 0.70):     # abaixo/acima da linha de janelas, 2 lados
    lap_joint(vf, 0.08)
for vf in (0.46, 0.54):                  # crista
    lap_joint(vf, 0.06)

img = D.images.get("PanelBump")
if img is None or img.size[0] != W:
    img = D.images.new("PanelBump", W, H, alpha=False, float_buffer=False)
rgba = np.empty((H, W, 4), np.float32)
arr = np.clip(arr, 0.0, 1.0)
rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = arr
rgba[..., 3] = 1.0
img.pixels.foreach_set(rgba.ravel())
img.pack()
print("PanelBump 767 gravado")

# ---------------------------------------------------------------- AsaLinhas
# UV planar 'UVAsa': x 18..46 -> u, y -32..32 -> v (mesma conveniencia do 787)
WA = HA = 2048
la = np.zeros((HA, WA, 4), np.float32)
la[..., 3] = 1.0

def uv_asa(x, y):
    return int((x - 18.0) / 28.0 * (WA - 1)), int((y + 32.0) / 64.0 * (HA - 1))

def seg(x0, y0, x1, y1, canal, forca=1.0, esp=2):
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 40) + 2
    for i in range(n + 1):
        t = i / n
        px, py = uv_asa(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
        if 0 <= px < WA and 0 <= py < HA:
            la[max(0, py - esp // 2):py + esp // 2 + 1,
               max(0, px - esp // 2):px + esp // 2 + 1, canal] = forca

def le_x(y):
    return 17.17 + 0.694 * abs(y)

def te_x(y):
    ya = abs(y)
    if ya <= 9.41:
        return 29.29 + 0.143 * (ya - 2.515)
    return 30.44 + 0.376 * (ya - 9.41)

for sgn in (-1, 1):
    # bordo de fuga: flap interno (3.2..7.4), aileron interno (7.4..9.4),
    # flap externo (9.4..17.6), aileron externo (17.6..22.3)
    for (y0, y1, cfrac) in ((3.2, 7.4, 0.72), (7.4, 9.4, 0.70),
                            (9.4, 17.6, 0.75), (17.6, 22.3, 0.74)):
        for yy in (y0, y1):
            y = sgn * yy
            xle, xte = le_x(y), te_x(y)
            xc = xle + (xte - xle) * cfrac
            seg(xc, y, xte, y, 0, 1.0, 3)   # R = 2 lados
        y0s, y1s = sgn * y0, sgn * y1
        seg(le_x(y0s) + (te_x(y0s) - le_x(y0s)) * cfrac, y0s,
            le_x(y1s) + (te_x(y1s) - le_x(y1s)) * cfrac, y1s, 0, 1.0, 2)
    # spoilers (so extradorso, canal G): 6 paineis
    for (y0, y1) in ((3.4, 5.2), (5.2, 7.2), (9.6, 11.8), (11.8, 14.0),
                     (14.0, 16.2), (16.2, 17.6)):
        for yy in (y0, y1):
            y = sgn * yy
            xle, xte = le_x(y), te_x(y)
            seg(xle + (xte - xle) * 0.62, y, xle + (xte - xle) * 0.74, y, 1, 1.0, 2)
        ya, yb = sgn * y0, sgn * y1
        for cf in (0.62, 0.74):
            seg(le_x(ya) + (te_x(ya) - le_x(ya)) * cf, ya,
                le_x(yb) + (te_x(yb) - le_x(yb)) * cf, yb, 1, 1.0, 2)
    # slats: 6 segmentos com corte no pylon (y 7.2..8.6)
    for (y0, y1) in ((3.0, 7.2), (8.6, 11.6), (11.6, 14.6), (14.6, 17.6),
                     (17.6, 20.6), (20.6, 23.5)):
        ya, yb = sgn * y0, sgn * y1
        seg(le_x(ya) + 0.55, ya, le_x(yb) + 0.55, yb, 0, 0.85, 2)
        for yy in (y0, y1):
            y = sgn * yy
            seg(le_x(y), y, le_x(y) + 0.55, y, 0, 0.85, 2)

img2 = D.images.get("AsaLinhas")
if img2 is None or img2.size[0] != WA:
    img2 = D.images.new("AsaLinhas", WA, HA, alpha=False, float_buffer=False)
img2.pixels.foreach_set(la.ravel())
img2.pack()
print("AsaLinhas 767 gravado")

# UV planar 'UVAsa' na asa nova
asa = D.objects["Asas"]
me = asa.data
uva = me.uv_layers.get("UVAsa") or me.uv_layers.new(name="UVAsa")
for loop in me.loops:
    co = me.vertices[loop.vertex_index].co
    uva.data[loop.index].uv = ((co.x - 18.0) / 28.0, (co.y + 32.0) / 64.0)

bpy.ops.wm.save_mainfile()
print("SALVO")
