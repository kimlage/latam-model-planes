"""A321neo PS-LBA — phase 2: livery texture, marks, materials.

Run: blender -b --factory-startup "airbus A321neo/A321neo_LATAM.blend" -P build_a321_fase2_livery.py

Everything measured on ref_PS-LBO_wikimedia_DSC00834.jpg (see medir_echarpe_v2.py):
  fwd wedge boundary   x >= 35.48 + 0.822*z
  lower wedge boundary theta <= max(129.0 - 23.7*(x-34.45), 105.3 - 3.78*(x-36.05))
  rear boundary        x <= 41.46 + 0.0538*z   (fin TE line, +6.94 from A320)
  title "AIRBUS A321neo": x 33.55..35.35, caps z 0.88..1.03 (cap 0.145 m)
  registration PS-LBA: white in the wedge, x 36.75.., cap 0.40 m, bottom z 0.70
The old A320 texture is remapped column-wise with the same piecewise map used
for the hull, then fixed: cargo/overwing outlines moved, PT-TMN marks erased,
wedge boundary re-solved, new marks rasterized.
"""
import bpy
import bmesh
import math
import numpy as np
import os
import sys as _sys
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in _sys.path:
    _sys.path.insert(0, _RAIZ)
import latam_livery_kit as kit  # noqa: E402
import reparar_echarpe as _re   # noqa: E402

# CONSOLIDACAO DO PINTOR UNICO (2026-08-27). Este arquivo e o passo de
# DERIVACAO (A320neo -> A321neo) e pinta so livery plana: remap de colunas,
# contornos movidos, limpeza dos fantasmas do master COM BASE DECLARADA, e a
# cunha ABSOLUTA pela regra unica (kit.cobertura_echarpe + kit.reparar_echarpe
# — nunca mais diferenca de duas regras com portao flat_w/flat_i, nem
# fac[m]=0 sobre a cunha: eram a fronteira pontilhada, a lasca destacada e o
# retangulo branco do QA-BACKLOG). As marcas (matricula PS-LBA, titulo)
# moram em refazer_marcas.py (tag a321neo); build_a321_fase2b_espelho.py
# fica como registro historico. Sequencia (REBUILD.md):
#     fase1 -> fase2 (este) -> fase3 -> portas_familia
#           -> refazer_marcas -- a321neo lockup marcas
#           -> reparar_echarpe -- a321neo

D = bpy.data
W, H = 4096, 1024
L_OLD, L_NEW = 38.0, 45.0
CUT1, CUT2, D_FWD, D_TOT = 11.5, 26.4, 4.26, 6.94
BRANCO = np.array([0.969, 0.976, 0.980])
INDIGO = np.array([0.165, 0.000, 0.533])

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
rx = np.array(rx); rzc = np.array(rzc); rr = np.array(rr)
def zc_of(x): return np.interp(x, rx, rzc)
def r_of(x):  return np.interp(x, rx, rr)

# texel grids
ux = (np.arange(W) + 0.5) / W * L_NEW               # x per column
vv = (np.arange(H) + 0.5) / H                        # v per row
TH = vv * 2 * math.pi - math.pi                      # theta in [-pi, pi], 0 = crown
XG = np.broadcast_to(ux, (H, W))
THG = np.broadcast_to(TH[:, None], (H, W))
ZCG = np.broadcast_to(zc_of(ux), (H, W))
RG = np.broadcast_to(r_of(ux), (H, W))
ZG = ZCG + RG * np.cos(THG)                          # z of each texel
THDEG = np.degrees(np.abs(THG))                      # angle from crown, symmetric

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

# ------------------------------------------------ column remap (old -> new)
def src_x_of(xn):
    if xn <= CUT1: return xn
    if xn <= CUT1 + D_FWD: return 19.0 + (xn % 2.0)          # plug: clean barrel tile
    if xn <= CUT2 + D_FWD: return xn - D_FWD
    if xn <= CUT2 + D_TOT: return 19.0 + (xn % 2.0)          # aft plug tile
    return xn - D_TOT

src_cols = np.array([src_x_of(x) / L_OLD * W - 0.5 for x in ux])
c0 = np.clip(np.floor(src_cols).astype(int), 0, W - 1)
c1 = np.clip(c0 + 1, 0, W - 1)
t = np.clip(src_cols - c0, 0, 1)[None, :, None]
tex = tex[:, c0, :] * (1 - t) + tex[:, c1, :] * t
fac = fac[:, c0, :] * (1 - t) + fac[:, c1, :] * t
print("remap done")

# NoseMask: metre-identity remap (content lives in the nose only)
nm = load("NoseMask")
src_cols = ux / L_OLD * W - 0.5
c0 = np.clip(np.floor(src_cols).astype(int), 0, W - 1)
c1n = np.clip(c0 + 1, 0, W - 1)
t = np.clip(src_cols - c0, 0, 1)[None, :, None]
valid = (ux < L_OLD - 0.2)
nm2 = nm[:, c0, :] * (1 - t) + nm[:, c1n, :] * t
nm2[:, ~valid, :] = 0.0
store("NoseMask", nm2)
print("nosemask remapped")

# ------------------------------------------------ helpers
def box(x0, x1, z0, z1, lado="ambos"):
    """texel mask for x/z box on one or both sides."""
    m = (XG >= x0) & (XG <= x1) & (ZG >= z0) & (ZG <= z1)
    if lado == "E":   m &= THG < 0
    elif lado == "D": m &= THG > 0
    return m

def bluish(a):
    return (a[..., 2] - a[..., 0] > 0.05) & (a[..., 2] > 0.08)

def erase(mask):
    fac[mask, 0:3] = 0.0
    if fac.shape[2] > 3: fac[mask, 3] = 1.0

# capture/paste for outline moves: work on COLUMN bands within a v range
def cap_paste(x0s, x1s, dx, v0, v1, clear_ranges):
    """capture tex/fac in src cols [x0s,x1s] rows v0..v1, clear old zones, paste at +dx."""
    r0, r1 = int(v0 * H), int(v1 * H)
    j0, j1 = int(x0s / L_NEW * W), int(x1s / L_NEW * W)
    keep_t = tex[r0:r1, j0:j1].copy()
    keep_f = fac[r0:r1, j0:j1].copy()
    for (cx0, cx1) in clear_ranges:
        q0, q1 = int(cx0 / L_NEW * W), int(cx1 / L_NEW * W)
        fac[r0:r1, q0:q1, 0:3] = 0.0
    p0 = int((x0s + dx) / L_NEW * W)
    tex[r0:r1, p0:p0 + (j1 - j0)] = keep_t
    fac[r0:r1, p0:p0 + (j1 - j0)] = keep_f

# ------------------------------------------------ outline moves
# after the remap: fwd cargo ring sits at its OLD metres (7.24..9.08, x<=CUT1)
cap_paste(7.10, 9.25, +0.40, 0.77, 0.93, [(7.10, 9.25)])        # fwd cargo -> 8.56
cap_paste(26.00, 27.92, +3.07, 0.77, 0.93, [(26.00, 27.92)])    # aft cargo 26.95 -> 30.02
# bulk: torn across the cut; erase both fragments, rebuild by pasting from the
# aft fragment source... simplest: erase fragments and paste the ORIGINAL bulk
# columns from the +6.94 region (they landed intact at 32.74..33.72 already).
r0, r1 = int(0.77 * H), int(0.93 * H)
for (cx0, cx1) in [(29.95, 30.75)]:                              # +4.26 fragment
    q0, q1 = int(cx0 / L_NEW * W), int(cx1 / L_NEW * W)
    fac[r0:r1, q0:q1, 0:3] = 0.0
# overwing outline 2: landed at 19.61..20.23, want 19.23..19.85
for vb in [(0.23, 0.35), (0.65, 0.77)]:
    cap_paste(19.55, 20.30, -0.38, vb[0], vb[1], [(19.55, 20.30)])
# door 3: copy D1's painted ring/FAR band to +21.78 on both sides
for vb in [(0.15, 0.38), (0.62, 0.85)]:
    cap_paste(4.45, 5.65, +21.78, vb[0], vb[1], [])
print("outlines moved")

# ------------------------------------------------ erase PT-TMN-specific marks
# BASE DECLARADA (refazer_marcas._basemap e a licao): a caixa que cruza a
# cunha restaura INDIGO do lado de dentro e casco branco do lado de fora.
# `fac=0` incondicional aqui era o retangulo branco dentro do indigo.
THDEG_ = np.degrees(np.abs(THG))
_regra = _re.FROTA["a321neo"]["regra"]
_dentro = _regra(XG, ZG, THDEG_)
INDIGO_F = np.array([0.165, 0.000, 0.533], np.float32)
m = box(3.15, 6.25, -0.85, -0.02) & bluish(tex)                  # nose titles/logo (branco)
erase(m)
for bx in (box(36.9, 38.45, 0.95, 1.50), box(33.70, 37.05, 1.10, 1.55)):
    m = bx & bluish(tex)
    erase(m & ~_dentro)                       # fora da cunha: casco branco
    tex[m & _dentro, 0:3] = INDIGO_F          # dentro: indigo chapado
    fac[m & _dentro, 0:3] = 1.0
print("old marks erased (base declarada)")

# ------------------------------------------------ cunha ABSOLUTA (regra unica)
# A cunha e pintada pela cobertura absoluta da regra do proprio aviao
# (reparar_echarpe._r_a321) sobre a ponte da malha, com o escritor que protege
# marcas por COR (kit.reparar_echarpe, limiar 0.10) — o mesmo par que a rodada
# da cauda usa para reparar. Nada de velha/nova, nada de flat_w/flat_i.
_rxm, _rzcm, _rrzm, _rrym = kit.secoes_do_casco(fus)
_cov = kit.cobertura_echarpe(_regra, _rxm, _rzcm, _rrzm, 0.0, L_NEW, W, H, ss=3)
_zona = (XG > 32.0) & (XG < 43.0)
_BR = np.array([0xE6, 0xE7, 0xEA], np.float32) / 255.0
_n, _muda = kit.reparar_echarpe(tex, fac, _cov, _zona, _BR, INDIGO_F)
print("wedge: %d texels rewritten (absolute)" % _n)

# ------------------------- MARCAS: movidas para refazer_marcas (tag a321neo)
# Matricula PS-LBA e titulo AIRBUS A321neo — bombordo E estibordo espelhado —
# moram em refazer_marcas.py (_marcas_a321neo), constantes do fase2/fase2b
# movidas textualmente. Rodar refazer_marcas e o proximo passo (REBUILD.md).

store("LiveryTex", tex)
store("LiveryFac", fac)
print("livery stored")

# ------------------------------------------------ PanelBump regenerate
pb = np.full((H, W, 4), 1.0, dtype=np.float32)
joints = [0.96, 1.79, 2.65, 3.51, 4.4, 5.3, 6.96]
xj = 8.9
while xj < 31.2:
    joints.append(xj); xj += 1.99
joints += [33.69, 35.6, 37.4, 39.2, 41.0, 42.5]
for j in joints:
    cjj = int(j / L_NEW * W)
    pb[:, cjj:cjj + 2, 0:3] = 0.55
for vrow in (0.285, 0.375, 0.625, 0.715):   # lap joints
    rj = int(vrow * H)
    pb[rj:rj + 1, :, 0:3] = 0.75
img = D.images["PanelBump"]
img.pixels.foreach_set(pb.ravel())
img.pack()
print("panelbump regenerated")

# ------------------------------------------------ materials & objects
# stabilizer extrados: flight grey per PS-LBO photos (not indigo)
st = D.objects["EstabHorizontal"]
st.data.materials[0] = D.materials["CinzaAsa"]

# D4 leaf split at the wedge boundary (z -0.11): white below
for nome in ("Porta2_E", "Porta2_D"):
    o = D.objects[nome]
    me = o.data if o.data.users == 1 else o.data.copy()
    o.data = me
    if "LATAM_Branco" not in [m.name for m in me.materials]:
        me.materials.append(D.materials["LATAM_Branco"])
    wi = [m.name for m in me.materials].index("LATAM_Branco")
    for p in me.polygons:
        if p.material_index == 0:  # indigo leaf
            zc_face = sum(me.vertices[vi].co.z for vi in p.vertices) / len(p.vertices)
            if zc_face + o.location.z < -0.11:
                p.material_index = wi
print("porta2 split done")

# nose gear door registration
D.objects["RegPortaTrem"].data.body = "LBA"

# window count refined to the photo (last window centre ~34.9)
jp = D.objects["JanelasPax"]
arr = next(m2 for m2 in jp.modifiers if m2.type == 'ARRAY')
arr.count = 57
print("windows ->", arr.count)

bpy.ops.wm.save_mainfile()
print("SAVED")
