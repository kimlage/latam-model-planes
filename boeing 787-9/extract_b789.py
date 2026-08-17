#!/usr/bin/env python3
"""Extrai curvas do casco do 787-9 do 3-view do Boeing APR D6-58333 Rev P (p.21 @600dpi).

Ancoras medidas por inspecao (crops ampliados):
- vista lateral: nariz px (867, 4210); ponta do tailcone px 3893; linha do solo py 4378
- calibracao: cota do solo 203FT5IN = 62.00 m entre as projecoes verticais (px 867 -> 3893)
- vista frontal: circulo da fuselagem centro ~(2576, 5360) r~141px (secao ~circular 5.77;
  APR da H=5.94 -> ovoide leve; modelamos semi-eixos 2.885 x 2.97)
Datum do modelo: x=0 no nariz; z=0 no centro da secao constante.
Saida: b789_curves.json
"""
import json
import numpy as np
from PIL import Image
from scipy.signal import medfilt

IMG = "apr600_p21-021.png"
im = np.asarray(Image.open(IMG).convert("L")).astype(np.uint8)
dark = im < 128

X_NOSE, Y_NOSE = 867, 4210
X_TAIL = 3893
Y_GROUND = 4378
SCALE = 62.00 / (X_TAIL - X_NOSE)
print(f"escala {SCALE*1000:.3f} mm/px (62.00 m em {X_TAIL-X_NOSE}px)")

def x_m(px):
    return (px - X_NOSE) * SCALE

# ---------------- lateral: crown/keel ----------------
BAND = (3940, 4368)      # inclui crown ~3990, exclui solo 4378
sl = dark[BAND[0]:BAND[1], :]
xs, crown_px, keel_px = [], [], []
for c in range(X_NOSE, X_TAIL + 1):
    col = np.where(sl[:, c])[0]
    if len(col) == 0:
        continue
    xs.append(c)
    crown_px.append(col[0] + BAND[0])
    keel_px.append(col[-1] + BAND[0])
xs = np.array(xs)
crown_px = np.array(crown_px, float)
keel_px = np.array(keel_px, float)

def clean(y, k=21, tol=15):
    med = medfilt(y, k)
    out = np.where(np.abs(y - med) > tol, med, y)
    return medfilt(out, 9)

crown_px = clean(crown_px)
keel_px = clean(keel_px)
xm_cols = x_m(xs)

# pontes no keel: trem do nariz, nacelle+asa+trem principal
keel_ok = np.ones(len(xs), bool)
for a, b in [(4.0, 8.0), (16.5, 34.0)]:
    keel_ok &= ~((xm_cols > a) & (xm_cols < b))
keel_bridged = np.interp(xm_cols, xm_cols[keel_ok], keel_px[keel_ok])
# ponte no crown: zona da asa sobre a fuselagem (linhas da asa cruzam)
crown_ok = np.ones(len(xs), bool)
for a, b in [(20.0, 30.0)]:
    crown_ok &= ~((xm_cols > a) & (xm_cols < b))
crown_bridged = np.interp(xm_cols, xm_cols[crown_ok], crown_px[crown_ok])

# datum: secao constante em x 36-44 m
selc = (xm_cols > 36) & (xm_cols < 44)
crown_ref = np.median(crown_bridged[selc])
keel_ref = np.median(keel_bridged[selc])
H_meas = (keel_ref - crown_ref) * SCALE
z_mid_px = (crown_ref + keel_ref) / 2
print(f"crown_ref {crown_ref:.0f} keel_ref {keel_ref:.0f} | H medida {H_meas:.3f} m (APR 5.94)")
print(f"clearance keel-solo: {(Y_GROUND - keel_ref)*SCALE:.2f} m")

def z_m(py):
    return (z_mid_px - py) * SCALE

print(f"ponta do nariz: z = {z_m(Y_NOSE):.3f} m")

# ---------------- topo: meia-largura ----------------
BAND_T = (2190, 2470)
tp = dark[BAND_T[0]:BAND_T[1], :]
mids = []
for c in range(X_NOSE + int(36/SCALE), X_NOSE + int(44/SCALE)):
    col = np.where(tp[:, c])[0]
    if len(col):
        mids.append((col[0] + col[-1]) / 2)
CL = np.median(mids) + BAND_T[0]
xs_t, hw = [], []
for c in range(X_NOSE, X_TAIL + 1):
    col = np.where(tp[:, c])[0]
    if len(col) == 0:
        continue
    xs_t.append(c)
    hw.append(max(abs(CL - (col[0] + BAND_T[0])), abs((col[-1] + BAND_T[0]) - CL)))
xs_t = np.array(xs_t)
hw = clean(np.array(hw, float), 21, 12)
xm_t = x_m(xs_t)
W_meas = 2 * np.median(hw[(xm_t > 36) & (xm_t < 44)]) * SCALE
print(f"W medida {W_meas:.3f} m (APR 5.77) | centerline topo {CL:.0f}")

sel_n = xm_t < 20.0
w_nose = np.maximum.accumulate(hw[sel_n]) * SCALE
sel_tl = xm_t > 44.0
w_tail = (np.maximum.accumulate(hw[sel_tl][::-1])[::-1]) * SCALE

# ---------------- gravar ----------------
step = 4
out = {
    "fonte": "Boeing APR D6-58333 Rev P p.21 @600dpi; ancoras por inspecao",
    "escala_mm_px": round(SCALE * 1000, 3),
    "datum": "x=0 nariz; z=0 centro da secao constante",
    "sanidade": {"H_medida": round(H_meas, 3), "W_medida": round(W_meas, 3),
                 "H_APR": 5.94, "W_APR": 5.77,
                 "ponta_nariz_z": round(z_m(Y_NOSE), 3),
                 "clearance_solo": round((Y_GROUND - keel_ref) * SCALE, 2)},
    "lateral": {
        "x": [round(v, 3) for v in xm_cols[::step]],
        "crown": [round(z_m(v), 3) for v in crown_bridged[::step]],
        "keel": [round(z_m(v), 3) for v in keel_bridged[::step]],
    },
    "topo_nariz": {"x": [round(v, 3) for v in xm_t[sel_n][::step]],
                   "meia_larg": [round(v, 3) for v in w_nose[::step]]},
    "topo_cauda": {"x": [round(v, 3) for v in xm_t[sel_tl][::step]],
                   "meia_larg": [round(v, 3) for v in w_tail[::step]]},
    "secao_mestre": {"modelo": "ovoide quase-eliptico: semi-eixos y=2.885, z=2.97 (frontal r_h=141px, r_v~142px)"},
}
with open("b789_curves.json", "w") as f:
    json.dump(out, f, indent=1)
print("gravado b789_curves.json")
for q in (0.5, 1, 2, 3, 5, 8, 12, 16, 46, 50, 54, 58, 61):
    i = int(np.argmin(np.abs(xm_cols - q)))
    j = int(np.argmin(np.abs(xm_t - q)))
    print(f"x={q:5.1f}  crown={z_m(crown_bridged[i]):+.2f}  keel={z_m(keel_bridged[i]):+.2f}  w/2={hw[j]*SCALE:.2f}")
