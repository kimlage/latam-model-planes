"""A321neo (PS-LBA) — FASE 3: ACAP correction round 2026-08-20.

Run headless:
  blender -b "airbus A321neo/A321neo_LATAM.blend" --python "airbus A321neo/build_a321_fase3_acap.py"

The A321 inherited the master A320neo's mis-placed empennage and low doors.
Verified on the A321's OWN ACAP before touching anything:
- fin TE measured on FIGURE-2-2-0-991-012 p73 (fill-anchored, scale from the
  44.51 length): TE_x = 0.222*z + 41.93 vs family prediction (A320 corrected
  + 6.94) 41.85 + 0.221*z -> agreement 0.08 m / 0.001 slope. The inherited
  position (41.46 + 0.054*z) is refuted by both.
- door sills, table 2-3-0-991-048 (ACF): D1 3.39 (A320 3.381), D4 3.61
  (A320 3.615) -> same +0.55/+0.57 raises as the family;
  D3 is the ACF's RAISED SHORT door: aperture 1.52 m (not 1.85), sill 0.39 m
  above floor (FIGURE-2-7-0-991-046 C-C) -> leaf rebuilt to 1.69 m starting
  at z 0.02 (the model had a full-size clone of door 1 at door-1 height).
Fin remap (h,c) keeps the per-loop UV so the sash art and its edge-crossing
anchoring travel with the mesh; root bottom stretched (z<2.05, 1.55->1.05)
to stay buried in the thinner tailcone. Stab +0.87. Wedge boundaries stay:
they were measured on the PS-LBO photos and the rear (41.46+0.0538z) reads
as the hull-paint boundary ~0.7 m ahead of the TE-root fairing — the same
pattern the PT-TMN photo shows on the master.
Texture: old door rings erased and repainted from the corrected meshes.
"""
import bpy
import json
import math
import os
import numpy as np

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))

# a implementacao unica dos aneis de porta mora na raiz do repositorio
import sys as _sys
_sys.path.insert(0, os.path.dirname(BASE))
import latam_livery_kit as kit  # noqa: E402

log = lambda *a: print("[A321f3]", *a)
OFF = 6.94

# ------------------------------------------------------------------ fin remap
LE_O = lambda z: 0.8393 * z + 26.773 + OFF
TE_O = lambda z: 34.60 + 0.0538 * (z - 1.55) + OFF
LE_N = lambda z: 0.863 * z + 28.02 + OFF
TE_N = lambda z: 0.221 * z + 34.91 + OFF
der = D.objects["Deriva"]
dlx, dlz = der.location.x, der.location.z
xs = [v.co.x + dlx for v in der.data.vertices]
log("fin before (world): x %.2f..%.2f, loc.x %.2f" % (min(xs), max(xs), dlx))
for v in der.data.vertices:
    z = v.co.z + dlz
    xw = v.co.x + dlx
    lo, to = LE_O(z), TE_O(z)
    c = (xw - lo) / max(to - lo, 1e-6)
    v.co.x = (LE_N(z) + c * (TE_N(z) - LE_N(z))) - dlx
log("fin remapped: root LE %.2f TE %.2f ; top LE %.2f TE %.2f"
    % (LE_N(1.55), TE_N(1.55), LE_N(8.05), TE_N(8.05)))
Z_PIVOT, K = 2.05, 2.0
n_moved = 0
for v in der.data.vertices:
    zw = v.co.z + dlz
    if zw < Z_PIVOT:
        v.co.z = (Z_PIVOT - (Z_PIVOT - zw) * K) - dlz
        n_moved += 1
log("fin root bottom now %.2f (%d verts)" % (min(v.co.z + dlz for v in der.data.vertices), n_moved))

eh = D.objects["EstabHorizontal"]
for v in eh.data.vertices:
    v.co.x += 0.87
log("stab -> tip TE %.2f (world)" % (max(v.co.x for v in eh.data.vertices) + eh.location.x))

wrap = D.objects.get("WrapIndigo")
if wrap:
    log("WrapIndigo present: hide_render=%s" % wrap.hide_render)

# ------------------------------------------------------------------ doors
# Porta3 was cloned from Porta1 sharing the mesh datablock: make every pax
# door's mesh unique before transforming, or the D3 rebuild clobbers door 1.
for n in ("Porta1_E", "Porta1_D", "Porta2_E", "Porta2_D", "Porta3_E", "Porta3_D"):
    ob = D.objects[n]
    if ob.data.users > 1:
        ob.data = ob.data.copy()
        log(n, "mesh made unique")

for n, dz in (("Porta1_E", 0.55), ("Porta1_D", 0.55),
              ("Porta2_E", 0.57), ("Porta2_D", 0.57)):
    ob = D.objects[n]
    for v in ob.data.vertices:
        v.co.z += dz
    zs = [v.co.z + ob.location.z for v in ob.data.vertices]
    log(n, "z now %.2f..%.2f" % (min(zs), max(zs)))

# D3: raised short ACF door — leaf 1.52 aperture -> leaf 1.69, bottom z 0.02
S3 = 1.52 / 1.85
for n in ("Porta3_E", "Porta3_D"):
    ob = D.objects[n]
    z0 = min(v.co.z for v in ob.data.vertices) + ob.location.z
    for v in ob.data.vertices:
        zw = v.co.z + ob.location.z
        v.co.z = (0.02 + (zw - z0) * S3) - ob.location.z
    zs = [v.co.z + ob.location.z for v in ob.data.vertices]
    log(n, "z now %.2f..%.2f (ACF raised short door)" % (min(zs), max(zs)))

# D4 leaf split at the wedge boundary (z=-0.11, paint is hull-fixed): recompute
for nome in ("Porta2_E", "Porta2_D"):
    o = D.objects[nome]
    me = o.data
    names = [m.name for m in me.materials]
    if "LATAM_Branco" in names:
        wi = names.index("LATAM_Branco")
        n_up = n_dn = 0
        for p in me.polygons:
            if p.material_index in (0, wi):
                zc_face = sum(me.vertices[vi].co.z for vi in p.vertices) / len(p.vertices)
                want = wi if zc_face + o.location.z < -0.11 else 0
                if p.material_index != want:
                    p.material_index = want
                    if want == 0:
                        n_up += 1
                    else:
                        n_dn += 1
        log(nome, "split recomputed: %d faces ->indigo, %d ->white" % (n_up, n_dn))

# ------------------------------------------------------------------ camera
D.objects["CamAlvoCauda"].location.x = 39.14   # fin moved aft

# ------------------------------------------------------------------ texture rings
L_UV = 45.0
imT = D.images["LiveryTex"]
imF = D.images["LiveryFac"]
W, H = imT.size
rgb = np.array(imT.pixels[:], dtype=np.float32).reshape(H, W, 4)
facA = np.array(imF.pixels[:], dtype=np.float32).reshape(H, W, 4)

rings_p = os.path.join(BASE, "a321_rings.json")
if os.path.exists(rings_p):
    rtab = json.load(open(rings_p))
else:
    fus = D.objects["Fuselagem"]
    acc = {}
    for v in fus.data.vertices:
        acc.setdefault(round(v.co.x, 2), []).append(v.co)
    rtab = []
    for x, gl in sorted(acc.items()):
        if len(gl) < 8:
            continue
        zs = [c.z for c in gl]
        ys = [c.y for c in gl]
        rtab.append({"x": x, "zc": 0.5 * (max(zs) + min(zs)),
                     "rz": 0.5 * (max(zs) - min(zs)), "ry": max(ys)})
    json.dump(rtab, open(rings_p, "w"), indent=1)
    log("rings saved:", len(rtab))
rx = np.array([r["x"] for r in rtab])
rzc = np.array([r["zc"] for r in rtab])
rrz = np.array([r["rz"] for r in rtab])
rry = np.array([r["ry"] for r in rtab])

u = (np.arange(W) + 0.5) / W
v = (np.arange(H) + 0.5) / H
X = u * L_UV
TH = v * 2 * math.pi - math.pi
Xg = np.broadcast_to(X, (H, W))
THg = np.broadcast_to(TH[:, None], (H, W))
Zg = np.interp(X, rx, rzc)[None, :] + np.interp(X, rx, rrz)[None, :] * np.cos(THg)
Yg = np.interp(X, rx, rry)[None, :] * np.sin(THg)

C = {"branco": (0.969, 0.976, 0.980), "indigo": (0.165, 0.000, 0.533),
     "far": (0.624, 0.643, 0.663), "sulco": (0.098, 0.106, 0.114)}

def set_px(mask, cor, f):
    for k in range(3):
        rgb[..., k][mask] = cor[k]
    for k in range(3):
        facA[..., k][mask] = f

R_, G_, B_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
is_indigo = (B_ > 0.30) & (R_ < 0.40)
is_mark = is_indigo | ((facA[..., 0] > 0.05) & (R_ > 0.45))

def erase_rect(x0, x1, z0, z1, to_indigo=False):
    m = is_mark & (Xg >= x0) & (Xg <= x1) & (Zg >= z0) & (Zg <= z1)
    set_px(m, C["indigo"] if to_indigo else C["branco"], 1.0 if to_indigo else 0.0)
    log("erased rect x %.2f..%.2f z %.2f..%.2f -> %s (%d texels)"
        % (x0, x1, z0, z1, "indigo" if to_indigo else "white", int(m.sum())))

erase_rect(4.40, 5.68, -1.00, 1.40)      # old porta-1 ring
erase_rect(26.18, 27.46, -1.00, 1.40)    # old porta-3 ring (full-size, low)

# old D4 white ring: the zone straddles the wedge front boundary, so reset it
# by the wedge rule itself (spec cauda_livery_ps_lba.echarpe) instead of one color
THdeg = np.degrees(np.abs(THg))
in_zone = (Xg >= 35.95) & (Xg <= 37.23) & (Zg >= -0.85) & (Zg <= 1.50)
lower_ok = THdeg <= np.maximum(129.0 - 23.7 * (Xg - 34.45), 105.3 - 3.78 * (Xg - 36.05))
wedge = (Xg >= 35.48 + 0.822 * Zg) & (Xg <= 41.46 + 0.0538 * Zg) & lower_ok
set_px(in_zone & wedge, C["indigo"], 1.0)
set_px(in_zone & ~wedge, C["branco"], 0.0)
log("D4 zone reset by wedge rule: %d texels" % int(in_zone.sum()))

# ------------------------------------------------------------ door rings
# UMA implementacao para as cinco Airbus: `latam_livery_kit.anel_porta`.
# Este bloco era uma copia de `door_ring()` que pintava o contorno no
# RETANGULO (x, z) — a projecao lateral — enquanto a folha vive na superficie.
# Acima do ombro os dois divergiam 0.5-0.7 m: era a "porta 1 fantasma".
# O contorno agora e descrito em (x, w), com w = arco da secao. Ver
# `airbus A320neo/portas_familia.py` para a medicao e para o assentamento das
# folhas, que tinham o mesmo erro NA MALHA.
_WG = kit.grade_arco(rx, rrz, rry, X, TH)

def door_ring(name, band_cor, band_w, groove_cor, groove_w, side, far_band=False):
    ob = D.objects.get(name)
    if ob is None:
        return
    caixa = kit.caixa_porta_xw(ob, rx, rzc, rrz, rry)
    banda, sulco = kit.anel_porta(Xg, _WG, caixa, band_w, groove_w, 0.15)
    sideok = ((Yg < 0) if side < 0 else (Yg > 0)) & (np.abs(np.sin(THg)) > 0.25)
    if far_band:
        set_px(banda & sideok, band_cor, 1.0)
    set_px(sulco & sideok, groove_cor, 1.0)
    log("door ring", name, "x %.2f..%.2f w %.3f..%.3f" % caixa)

door_ring("Porta1_E", C["far"], 0.05, C["sulco"], 0.010, side=-1, far_band=True)
door_ring("Porta1_D", C["far"], 0.05, C["sulco"], 0.010, side=+1, far_band=True)
door_ring("Porta3_E", C["far"], 0.05, C["sulco"], 0.010, side=-1, far_band=True)
door_ring("Porta3_D", C["far"], 0.05, C["sulco"], 0.010, side=+1, far_band=True)
door_ring("Porta2_E", C["branco"], 0.058, C["branco"], 0.010, side=-1, far_band=True)
door_ring("Porta2_D", C["branco"], 0.058, C["branco"], 0.010, side=+1, far_band=True)

imT.pixels.foreach_set(rgb.ravel())
imT.pack()
imF.pixels.foreach_set(facA.ravel())
imF.pack()
bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
