"""A321ceo PT-MXP — phase 2: livery texture deltas.

Run: blender -b "airbus A321ceo/A321ceo_LATAM.blend" --python "airbus A321ceo/build_a321ceo_fase2_livery.py"

The wedge, fin sash, LATAM lockups and belly stay EXACTLY as inherited from the
A321neo (measured identical on PT-XPB: forward boundary 35.52+0.816z vs neo
35.48+0.822z, rms 0.06 — see medir_echarpe_xpb2.py). Deltas:
- overwing hatch outlines erased (ceo has none);
- D3 ring 26.82 -> repainted at 24.79 in ceo exit size; new D2 ring at 13.84;
- cargo fwd/aft rings -0.40 (8.56->8.16, 30.02->29.62);
- PS-LBA -> PT-MXP (white in the wedge, x 37.15, both sides, D mirrored);
- title AIRBUS A321neo -> AIRBUS A321, aft end at 34.75 (measured on two ceo
  photos: XPB 34.65, PT-MXP-2024 ~34.77 by window count);
- moderate weathering (2014 airframe): gear spray fan, drain streaks;
- nose-gear door text LBA -> MXP.
"""
import bpy
import bmesh
import math
import os
import numpy as np

# CONSOLIDACAO DO PINTOR UNICO (2026-08-27). Passo de DERIVACAO (A321neo ->
# A321ceo); pinta so livery plana (contornos, limpezas em base branca). As
# marcas finais do PT-MXP — matricula, anel D4 branco, titulo AIRBUS A321 —
# moram em refazer_marcas.py (tag a321ceo; absorveu fix_reg_ghosts.py e
# fix_titulo_a321.py, que ficam como registro historico). A cunha nao se toca
# aqui: e identica a do neo (medida em PT-XPB) e pertence a
# reparar_echarpe -- a321ceo. Sequencia (REBUILD.md):
#     fase1 -> fase2 (este) -> fase3 -> portas_familia
#           -> refazer_marcas -- a321ceo lockup marcas
#           -> reparar_echarpe -- a321ceo

D = bpy.data
W, H = 4096, 1024
L_UV = 45.0
INDIGO = np.array([0.165, 0.000, 0.533])
NAVY = np.array([0.110, 0.180, 0.388])
FAR_GREY = np.array([0.624, 0.643, 0.663])
GROOVE = np.array([0.098, 0.106, 0.114])
log = lambda *a: print("[A321ceo]", *a)

# ------------------------------------------------ hull section geometry
fus = D.objects["Fuselagem"]
rings = {}
for v in fus.data.vertices:
    rings.setdefault(round(v.co.x, 3), []).append(v.co)
rx, rzc, rr = [], [], []
for k in sorted(rings):
    vs = rings[k]
    if len(vs) < 8:
        continue
    zmax = max(p.z for p in vs); zmin = min(p.z for p in vs)
    rx.append(k); rzc.append((zmax + zmin) / 2); rr.append((zmax - zmin) / 2)
def zc_of(x): return np.interp(x, rx, rzc)
def r_of(x):  return np.interp(x, rx, rr)

ux = (np.arange(W) + 0.5) / W * L_UV
vv = (np.arange(H) + 0.5) / H
TH = vv * 2 * math.pi - math.pi
XG = np.broadcast_to(ux, (H, W))
THG = np.broadcast_to(TH[:, None], (H, W))
ZG = np.broadcast_to(zc_of(ux), (H, W)) + np.broadcast_to(r_of(ux), (H, W)) * np.cos(THG)
SIDE = np.abs(np.sin(THG)) > 0.25

def load(name):
    img = D.images[name]
    a = np.empty(W * H * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(H, W, 4)

def store(name, arr):
    img = D.images[name]
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.pack()

tex = load("LiveryTex")
fac = load("LiveryFac")

# ------------------------------------------------ erase overwing outlines
m = (XG > 18.20) & (XG < 20.15) & (ZG > -0.6) & (ZG < 1.7) & SIDE
n0 = int((fac[..., 0][m] > 0.05).sum())
fac[m, 0:3] = 0.0
log("overwing outlines erased:", n0, "painted texels in zone")

# ------------------------------------------------ erase old D3 ring (26.82)
m = (XG > 26.15) & (XG < 27.50) & (ZG > -1.15) & (ZG < 1.55) & SIDE
n0 = int((fac[..., 0][m] > 0.05).sum())
fac[m, 0:3] = 0.0
log("old D3 ring erased:", n0)

# ------------------------------------------------ move cargo rings -0.40
def cap_paste(x0s, x1s, dx, v0, v1):
    r0, r1 = int(v0 * H), int(v1 * H)
    j0, j1 = int(x0s / L_UV * W), int(x1s / L_UV * W)
    keep_t = tex[r0:r1, j0:j1].copy()
    keep_f = fac[r0:r1, j0:j1].copy()
    fac[r0:r1, j0:j1, 0:3] = 0.0
    p0 = int((x0s + dx) / L_UV * W)
    tex[r0:r1, p0:p0 + (j1 - j0)] = keep_t
    fac[r0:r1, p0:p0 + (j1 - j0)] = keep_f

cap_paste(7.45, 9.70, -0.40, 0.77, 0.93)     # fwd cargo 8.56 -> 8.16
cap_paste(28.90, 31.15, -0.40, 0.77, 0.93)   # aft cargo 30.02 -> 29.62
log("cargo rings moved -0.40")

# ------------------------------------------------ door rings (paint helpers)
# SUPERADO 2026-08-21. Este `door_ring` pinta o contorno no RETANGULO (x, z) —
# a projecao lateral — e por isso desloca o anel 0.5-0.7 m acima do ombro (a
# "porta 1 fantasma"). A implementacao correta, em (x, w) com w = arco da secao,
# e `latam_livery_kit.anel_porta`, e quem repinta os quatro aneis desta aeronave
# e `build_a321ceo_fase3_acap.py`, que roda DEPOIS desta fase e ja usa o kit.
# Nao da para trocar aqui sem mais: esta fase monta a tabela de aneis com apenas
# (x, zc, r) — secao circular — e o arco precisa dos dois semi-eixos.
def rounded_rect(px, pz, x0, x1, z0, z1, r):
    ix0, ix1, iz0, iz1 = x0 + r, x1 - r, z0 + r, z1 - r
    dx = np.maximum(np.maximum(ix0 - px, px - ix1), 0)
    dz = np.maximum(np.maximum(iz0 - pz, pz - iz1), 0)
    return np.hypot(dx, dz) <= r

def door_ring(name, band_cor, band_w, groove_cor, groove_w, far_band=True):
    ob = D.objects[name]
    vs = np.array([v.co[:] for v in ob.data.vertices])
    x0 = vs[:, 0].min() + ob.location.x; x1 = vs[:, 0].max() + ob.location.x
    z0 = vs[:, 2].min() + ob.location.z; z1 = vs[:, 2].max() + ob.location.z
    r = 0.13
    inner = rounded_rect(XG, ZG, x0, x1, z0, z1, r)
    oband = rounded_rect(XG, ZG, x0 - band_w, x1 + band_w, z0 - band_w, z1 + band_w, r)
    ogro = rounded_rect(XG, ZG, x0 + groove_w, x1 - groove_w, z0 + groove_w, z1 - groove_w, r)
    sideok = ((THG < 0) if name.endswith("E") else (THG > 0)) & SIDE
    if far_band:
        mm = (oband & ~inner) & sideok
        tex[mm, 0:3] = band_cor; fac[mm, 0:3] = 1.0
    mm = (inner & ~ogro) & sideok
    tex[mm, 0:3] = groove_cor; fac[mm, 0:3] = 1.0
    log("ring", name, f"x {x0:.2f}..{x1:.2f} z {z0:.2f}..{z1:.2f}")

for side in ("E", "D"):
    door_ring("Porta2_" + side, FAR_GREY, 0.05, GROOVE, 0.010)
    door_ring("Porta3_" + side, FAR_GREY, 0.05, GROOVE, 0.010)

# ---------------- MARCAS: movidas para refazer_marcas (tag a321ceo)
# A troca PS-LBA -> PT-MXP (apagar com base indigo declarada, anel D4 branco,
# matricula nos dois bordos) e o titulo AIRBUS A321 sao pintados por
# refazer_marcas._marcas_a321ceo, com as constantes de fix_reg_ghosts.py e
# fix_titulo_a321.py movidas textualmente. Este fase2 nao pinta marca nenhuma.

# ------------------------------------------------ weathering (2014 airframe)
clean = fac[..., 0] < 0.05
# nose-gear spray fan on the belly
sel = (XG > 6.0) & (XG < 14.0) & (np.cos(THG) < -0.75) & clean
fade = np.clip((14.0 - XG) / 8.0, 0, 1) * 0.12
tex[sel, 0:3] = np.array([0.28, 0.29, 0.30])
fac[sel, 0:3] = fade[sel][:, None]
log("spray fan texels:", int(sel.sum()))
# drain streaks
THDEG = np.degrees(np.abs(THG))
for dx0 in (8.55, 34.54):
    sel = (np.abs(XG - dx0) < 0.10) & (THDEG > 115) & (THDEG < 165) & clean
    tex[sel, 0:3] = np.array([0.55, 0.47, 0.35])
    fac[sel, 0:3] = 0.20
    log(f"drain streak at {dx0}: {int(sel.sum())} texels")

store("LiveryTex", tex)
store("LiveryFac", fac)
log("livery stored")

# ------------------------------------------------ nose gear door text
D.objects["RegPortaTrem"].data.body = "MXP"

bpy.ops.wm.save_mainfile()
print("SAVED", D.filepath)
