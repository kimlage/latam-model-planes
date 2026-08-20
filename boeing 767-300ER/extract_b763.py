#!/usr/bin/env python3
"""Extrai curvas do casco do 767-300ER do 3-view do Boeing ACAP D6-58328 Rev K
(p.29 do PDF = pagina 2-9, General Dimensions 767-300/-300ER, @600dpi) e a
secao mestre da p.43 (2-23, Cabin Cross-Sections).

Ancoras medidas por inspecao (crops ampliados, insp_*.png):
- vista lateral: ponta do nariz px (1232, 3806); linha de cota 180FT3IN=54.94m
  em y=1009 com setas em x=1235 e x=3748 (nariz -> ponta do BF da deriva).
- ESCALA X: 54.94 m / (3748-1235) px = 21.86 mm/px  (45.74 px/m)
- ESCALA Z (lateral): a cota 17FT9IN=5.41m tem setas em y=3658 (crown) e
  y=3912 (keel): 254 px / 5.41 m = 46.95 px/m. A vista lateral e ~2.6%
  anamorfica na vertical em relacao ao eixo x — normalizar por eixo.
- vista de topo: eixo em y=2311; barril (2193..2199)/(2423..2428) centros
  2196/2425.5 -> largura 229.5 px = 5.017 m (ACAP 5.03: -0.26%).
Datum do modelo: x=0 no nariz; z=0 no centro da secao constante.
Saida: b763_curves.json
"""
import json
import numpy as np
from PIL import Image
from scipy.signal import medfilt

BASE = "/Users/sargam/Documents/Developer/Latam Airlines Model Planes/boeing 767-300ER/"
im = np.asarray(Image.open(BASE + "acap600-029.png").convert("RGB")).astype(int)
R, G, B = im[..., 0], im[..., 1], im[..., 2]
blue = (B - R > 60) & (B > 120)

X_NOSE = 1233.5
SC_X = 54.94 / (3748 - 1235)          # m/px eixo x
CROWN_REF, KEEL_REF = 3658.0, 3912.0  # centros das linhas na secao constante
SC_Z = 5.41 / (KEEL_REF - CROWN_REF)  # m/px eixo z (lateral)
Z_MID = (CROWN_REF + KEEL_REF) / 2
CL_TOP = 2310.75                      # eixo da vista de topo
SC_Y = 5.03 / (2425.5 - 2196.0)       # m/px meia-largura no topo

def x_m(px):
    return (px - X_NOSE) * SC_X

def px_of_x(m):
    return X_NOSE + m / SC_X

def z_m(py):
    return (Z_MID - py) * SC_Z

def runs_of(col):
    if len(col) == 0:
        return []
    d = np.diff(col)
    brk = np.where(d > 3)[0]
    runs = []
    s = col[0]
    for i in brk:
        runs.append((s, col[i]))
        s = col[i + 1]
    runs.append((s, col[-1]))
    return [(a, b) for a, b in runs if b - a >= 1]

# ---------------- lateral: crown/keel ----------------
BAND = (3645, 3932)   # exclui deriva acima e trem/cotas abaixo
side = blue[BAND[0]:BAND[1], :]
xs, crown_px, keel_px = [], [], []
for c in range(1232, 3716):
    col = np.where(side[:, c])[0] + BAND[0]
    rr = runs_of(col)
    if not rr:
        continue
    xs.append(c)
    crown_px.append((rr[0][0] + rr[0][1]) / 2)
    keel_px.append((rr[-1][0] + rr[-1][1]) / 2)
xs = np.array(xs)
crown_px = np.array(crown_px, float)
keel_px = np.array(keel_px, float)

def clean(y, k=21, tol=12):
    med = medfilt(y, k)
    out = np.where(np.abs(y - med) > tol, med, y)
    return medfilt(out, 9)

crown_px = clean(crown_px)
keel_px = clean(keel_px)
xm_cols = x_m(xs)

# pontes: trem do nariz; asa+nacelle+trem principal (keel);
# a crista fica limpa (a deriva esta acima da banda)
keel_ok = np.ones(len(xs), bool)
for a, b in [(3.2, 6.8), (16.5, 34.5)]:
    keel_ok &= ~((xm_cols > a) & (xm_cols < b))
keel_b = np.interp(xm_cols, xm_cols[keel_ok], keel_px[keel_ok])
crown_ok = np.ones(len(xs), bool)
for a, b in [(19.0, 33.0)]:   # linhas da asa sobre o flanco nao tocam a crista, mas por seguranca
    pass
crown_b = crown_px

selc = (xm_cols > 12) & (xm_cols < 38)
H_meas = (np.median(keel_b[selc]) - np.median(crown_b[selc])) * SC_Z
print(f"H barril medida {H_meas:.3f} m (ACAP 5.41) | crown {np.median(crown_b[selc]):.1f} keel {np.median(keel_b[selc]):.1f}")
print(f"ponta do nariz: z = {z_m(3806.5):+.3f} m")

# ---------------- topo: meia-largura ----------------
BAND_T = (2150, 2472)
top = blue[BAND_T[0]:BAND_T[1], :]
xs_t, hw = [], []
for c in range(1232, 3716):
    col = np.where(top[:, c])[0] + BAND_T[0]
    rr = runs_of(col)
    if not rr:
        continue
    xs_t.append(c)
    lo = (rr[0][0] + rr[0][1]) / 2
    hi = (rr[-1][0] + rr[-1][1]) / 2
    hw.append(max(abs(CL_TOP - lo), abs(hi - CL_TOP)))
xs_t = np.array(xs_t)
hw = clean(np.array(hw, float), 21, 10)
xm_t = x_m(xs_t)
W_meas = 2 * np.median(hw[(xm_t > 12) & (xm_t < 38)]) * SC_Y
print(f"W barril medida {W_meas:.3f} m (ACAP 5.03)")

sel_n = xm_t < 12.0
w_nose = np.maximum.accumulate(hw[sel_n]) * SC_Y

# cauda do topo: o estabilizador cruza a banda a partir de x~47 — extrair so
# 40..46.5 automaticamente; 47+ vai a mao por inspecao (ver spec)
sel_tl = (xm_t > 40.0) & (xm_t < 46.5)
w_tail = (np.maximum.accumulate(hw[sel_tl][::-1])[::-1]) * SC_Y

# ---------------- secao mestre (p43, 2-23) ----------------
sec = np.asarray(Image.open(BASE + "acap600-043.png").convert("L")).astype(int)
dsec = sec < 128
# contorno externo por inspecao (insp_secao.png): casco y 1660..4130,
# x 1364..3660; janela apertada para excluir linhas de cota
SEC_X0, SEC_X1 = 1350, 3680
SEC_Y0, SEC_Y1 = 1655, 4140
win = dsec[SEC_Y0:SEC_Y1, SEC_X0:SEC_X1]
rows = []
for r in range(win.shape[0]):
    row = np.where(win[r, :])[0]
    if len(row) == 0:
        continue
    rows.append((r + SEC_Y0, row.min() + SEC_X0, row.max() + SEC_X0))
rows = np.array(rows)
# a linha mais larga e o equador da secao; o topo/fundo fecham
wid = rows[:, 2] - rows[:, 1]
i_eq = int(np.argmax(wid))
y_top_sec, y_bot_sec = rows[0, 0], rows[-1, 0]
H_sec_px = y_bot_sec - y_top_sec
W_sec_px = wid[i_eq]
print(f"secao p43: H {H_sec_px}px W {W_sec_px}px  ratio {W_sec_px/H_sec_px:.4f} (ACAP 5.03/5.41={5.03/5.41:.4f})")
SC_SEC_Z = 5.41 / H_sec_px
SC_SEC_Y = 5.03 / W_sec_px
cx_sec = (rows[i_eq, 1] + rows[i_eq, 2]) / 2
prof_tab = []
for (yy, xlo, xhi) in rows[::14]:
    depth = (yy - y_top_sec) * SC_SEC_Z
    hw_n = max(cx_sec - xlo, xhi - cx_sec) * SC_SEC_Y
    prof_tab.append([round(depth, 3), round(hw_n, 3)])
print("perfil mestre (prof abaixo da crista -> meia-larg):")
for p in prof_tab[:6] + prof_tab[-4:]:
    print("  ", p)
print(f"equador em profundidade {(rows[i_eq,0]-y_top_sec)*SC_SEC_Z:.3f} m (meio = {5.41/2:.3f})")

# ---------------- gravar ----------------
step = 4
out = {
    "fonte": "Boeing ACAP D6-58328 Rev K p.29 (2-9) e p.43 (2-23) @600dpi; ancoras por inspecao",
    "escala": {"x_mm_px": round(SC_X * 1000, 4), "z_mm_px": round(SC_Z * 1000, 4),
               "y_topo_mm_px": round(SC_Y * 1000, 4),
               "nota": "vista lateral ~2.6% anamorfica na vertical; normalizado por eixo"},
    "datum": "x=0 nariz; z=0 centro da secao constante",
    "sanidade": {"H_medida": round(H_meas, 3), "W_medida": round(W_meas, 3),
                 "H_ACAP": 5.41, "W_ACAP": 5.03,
                 "ponta_nariz_z": round(z_m(3806.5), 3)},
    "lateral": {
        "x": [round(v, 3) for v in xm_cols[::step]],
        "crown": [round(z_m(v), 3) for v in crown_b[::step]],
        "keel": [round(z_m(v), 3) for v in keel_b[::step]],
    },
    "topo_nariz": {"x": [round(v, 3) for v in xm_t[sel_n][::step]],
                   "meia_larg": [round(v, 3) for v in w_nose[::step]]},
    "topo_cauda_40_465": {"x": [round(v, 3) for v in xm_t[sel_tl][::step]],
                          "meia_larg": [round(v, 3) for v in w_tail[::step]]},
    "secao_mestre": {"tabela_prof_meialarg": prof_tab,
                     "nota": "p43 contorno externo; H=5.41 W=5.03"},
}
with open(BASE + "b763_curves.json", "w") as f:
    json.dump(out, f, indent=1)
print("gravado b763_curves.json")
for q in (0.25, 0.5, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 40, 42, 44, 46, 48, 50, 52, 53, 54):
    i = int(np.argmin(np.abs(xm_cols - q)))
    print(f"x={q:5.2f}  crown={z_m(crown_b[i]):+.3f}  keel={z_m(keel_b[i]):+.3f}", end="")
    j = int(np.argmin(np.abs(xm_t - q)))
    if abs(xm_t[j] - q) < 0.1:
        print(f"  w/2={hw[j]*SC_Y:.3f}")
    else:
        print()
