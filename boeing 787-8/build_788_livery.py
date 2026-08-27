"""787-8 livery — STAGE 2 (textures), derived from the approved 787-9 paint.

Run headless:
  blender -b "boeing 787-8/B788_LATAM.blend" --python "boeing 787-8/build_788_livery.py"

Strategy (CC-BBF, photos in refs/manifest.json):
- LiveryTex/LiveryFac/PanelBump are COLUMN-RESAMPLED from the master with the
  two plug bands removed (3-zone mapping). The tail art — indigo wedge with its
  feathered boundary, DREAMLINER, door outlines, windows — lands at the -8
  positions automatically (validated by photogrammetry: DREAMLINER measured at
  x 38.8..42.2 vs 44.85..48.21-6.09 predicted; aft cargo door 0.06 m off).
- The LATAM lockup CANNOT ride the resample (on the -9 it spans 9.7..16.6 and
  the fwd plug cuts straight through it; on CC-BBF it is scaled ~0.88 ending
  clear of the -8's door 2). Erased at the source, repainted from the official
  meshes at the measured -8 position.
- Belly symbol: erased and repainted at measured x centre 11.45 (photo shows it
  under the lockup, not at the -9's painted 17-22).
- Registration: CC-BBF is WHITE INSIDE THE INDIGO ON BOTH SIDES (stbd photo of
  CC-BBF + port photo of CC-BBB) — unlike CC-BGK's asymmetry. Both -9 regs are
  erased; CC-BBF is painted from the master's official glyphs (C,C,-,B,B) plus
  an F constructed from the font's own metrics (stem/bar/cap from B and hyphen).
- NoseMask: pure u rescale (nose identical in metres).
"""
import bpy
import json
import math
import os
import numpy as np
import mathutils

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))
log = lambda *a: print("[B788L]", *a)

# CONSOLIDACAO DO PINTOR UNICO (2026-08-27). Este arquivo e o passo de
# DERIVACAO (787-9 -> 787-8) e pinta so livery plana: erases com base
# declarada + resample de colunas. As marcas finais do CC-BBF (lockup +0.12 m
# espelhado parte a parte, matricula cap 0.30, simbolo do ventre) moram em
# refazer_marcas.py (tag b788; absorveu build_788_livery2.py, que fica como
# registro historico). Sequencia (REBUILD.md):
#     build_788_geo -> build_788_livery (este) -> nose_art.py (787-9)
#         -> refazer_marcas -- b788 -> reparar_echarpe -- b788

L_UV_8 = 57.5
L_UV_9 = 63.5
S_WING = 3.04
S_TAIL = 6.09
S1 = 13.40           # -8 coords: seam nose/wing zone  (master cut 13.40..16.44)
S2 = 34.50           # -8 coords: seam wing/tail zone  (master cut 37.54..40.59)
W, H = 4096, 1024

WHITE = np.array([0.969, 0.976, 0.980], np.float32)
INDIGO = np.array([0.165, 0.000, 0.533], np.float32)
CORAL = np.array([0.929, 0.086, 0.318], np.float32)

rings = json.load(open(os.path.join(BASE, "b788_rings.json")))
rx = np.array([r["x"] for r in rings])
rzc = np.array([r["zc"] for r in rings])
rrz = np.array([r["rz"] for r in rings])
rry = np.array([r["ry"] for r in rings])


def read_img(name):
    img = D.images[name]
    w, h = img.size
    buf = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(buf)
    return img, buf.reshape(h, w, 4)


def write_img(img, arr):
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.pack()


# ---------------------------------------------------------------- 1. source-space erase
img_tex, tex = read_img("LiveryTex")
img_fac, fac = read_img("LiveryFac")
img_pb, pb = read_img("PanelBump")

x9_cols = (np.arange(W) + 0.5) / W * L_UV_9
v_rows = (np.arange(H) + 0.5) / H            # 0 = keel(-pi) .. 0.5 crown .. 1 keel(+pi)
chroma = tex[..., :3].max(axis=2) - tex[..., :3].min(axis=2)

# lockup (both sides): chromatic texels in the column band
m = (chroma > 0.10) & (x9_cols[None, :] >= 7.2) & (x9_cols[None, :] <= 16.85)
tex[m] = list(WHITE) + [1.0]
fac[m, 0] = fac[m, 1] = fac[m, 2] = 0.0
log("lockup erased:", int(m.sum()), "texels")

# belly symbol (keel rows near the v seam)
keel = (v_rows < 0.16) | (v_rows > 0.84)
m = (chroma > 0.10) & keel[:, None] & (x9_cols[None, :] >= 16.6) & (x9_cols[None, :] <= 23.0)
tex[m] = list(WHITE) + [1.0]
fac[m, 0] = fac[m, 1] = fac[m, 2] = 0.0
log("belly symbol erased:", int(m.sum()), "texels")

# ---------------------------------------------------------------- 2. column resample
def x8_to_x9(x8):
    x9 = np.where(x8 <= S1, x8, np.where(x8 < S2, x8 + S_WING, x8 + S_TAIL))
    return x9


x8_cols = (np.arange(W) + 0.5) / W * L_UV_8
src = x8_to_x9(x8_cols) / L_UV_9 * W - 0.5
c0 = np.clip(np.floor(src).astype(int), 0, W - 1)
c1 = np.clip(c0 + 1, 0, W - 1)
f = np.clip(src - c0, 0.0, 1.0).astype(np.float32)
oob = src > W - 0.5

tex = tex[:, c0, :] * (1 - f)[None, :, None] + tex[:, c1, :] * f[None, :, None]
fac = fac[:, c0, :] * (1 - f)[None, :, None] + fac[:, c1, :] * f[None, :, None]
pb = pb[:, c0, :] * (1 - f)[None, :, None] + pb[:, c1, :] * f[None, :, None]
tex[:, oob, :3] = WHITE
fac[:, oob, :3] = 0.0
pb[:, oob, :3] = 0.5
log("column resample done; oob cols:", int(oob.sum()))

# ---------------------------------------------------------------- texel grids (-8 coords)
X = x8_cols
TH = (np.arange(H) + 0.5) / H * 2 * math.pi - math.pi     # -pi..pi, 0 = crown
Xg = np.broadcast_to(X, (H, W))
THg = np.broadcast_to(TH[:, None], (H, W))
ZCg = np.interp(X, rx, rzc)[None, :]
RZg = np.interp(X, rx, rrz)[None, :]
RYg = np.interp(X, rx, rry)[None, :]
Zg = ZCg + RZg * np.cos(THg)
Yg = RYg * np.sin(THg)
THdeg = np.degrees(np.abs(THg))

# -8 wedge rule (the -9's, shifted -6.09; validated on the CC-BBF photo)
def wedge_mask(margin=0.0):
    return ((Xg >= 42.68 + 0.992 * Zg - margin) &
            (THdeg <= 117.0 - 5.2 * (Xg - 42.61) + margin * 5) &
            (Xg <= 51.05 + 0.3858 * Zg + margin))


# ---------------------------------------------------------------- 3. erase both regs
# The -9's PAINTED regs do not match its decal objects (objects are stale);
# find the glyphs by content. Post-resample coords: white-in-indigo reg at
# x ~47.9..51.9 (was 54..58), indigo-on-white at ~48.5..50.3 (was 54.6..56.4).
lum = tex[..., :3].mean(axis=2)
inw = wedge_mask(-0.10)
xband = (Xg >= 45.5) & (Xg <= 52.6)
# O portao `abs(sin(THg)) > 0.10` que morava aqui pulava |theta| <= 5.74 deg e
# deixou o bloco retangular de tinta reamostrada do -9 atravessado na crista
# (QA-BACKLOG; medido em CC-BBF: theta -5.7..+6.0, 0.40 m). A protecao certa e
# por COR (lum > 0.55 = tinta clara sobre o indigo), nao por geometria.
m1 = xband & inw & (lum > 0.55)
tex[m1, :3] = INDIGO
fac[m1, 0] = fac[m1, 1] = fac[m1, 2] = 1.0
chroma8 = tex[..., :3].max(axis=2) - tex[..., :3].min(axis=2)
m2 = (Xg >= 44.3) & (Xg <= 52.6) & ~wedge_mask(0.15) & (chroma8 > 0.10)
tex[m2, :3] = WHITE
fac[m2, 0] = fac[m2, 1] = fac[m2, 2] = 0.0
if m1.sum():
    jj, ii = np.nonzero(m1)
    log("reg erase white-in-wedge:", int(m1.sum()), "x %.2f..%.2f" % (Xg[0, ii.min()], Xg[0, ii.max()]))
if m2.sum():
    jj, ii = np.nonzero(m2)
    log("reg erase chroma-out:", int(m2.sum()), "x %.2f..%.2f" % (Xg[0, ii.min()], Xg[0, ii.max()]))

# -------------------- MARCAS: movidas para refazer_marcas (tag b788)
# Lockup (na posicao final +0.12 m, espelhado parte a parte), simbolo do
# ventre e matricula CC-BBF (cap 0.30, caixa das fotos) sao pintados por
# refazer_marcas._marcas_b788, com as constantes deste arquivo e do
# build_788_livery2.py movidas textualmente. Este builder nao pinta marca.

# ---------------------------------------------------------------- 7. write textures
write_img(img_tex, np.concatenate([tex[..., :3], np.ones((H, W, 1), np.float32)], axis=2))
write_img(img_fac, np.concatenate([fac[..., :1].repeat(3, axis=2), np.ones((H, W, 1), np.float32)], axis=2))
write_img(img_pb, np.concatenate([pb[..., :3], np.ones((H, W, 1), np.float32)], axis=2))
log("LiveryTex/Fac/PanelBump written")

# ---------------------------------------------------------------- 8. NoseMask rescale
# SUPERSEDIDO em 2026-08-21 por "boeing 787-9/nose_art.py", que constroi a
# NoseMask dos DOIS avioes do zero, testando cada texel pela sua posicao 3D no
# proprio casco (e por isso e imune ao defeito de UV da crista do 787). Esta
# reamostragem por coluna continua aqui porque o resto do script depende do
# datablock existir com o tamanho do casco; se este script for rodado de novo,
# RODAR nose_art.py (export/build/apply) DEPOIS dele, senao a NoseMask volta a
# 4096x1024 com os montantes antigos.
img_nm, nmb = read_img("NoseMask")
src = x8_cols / L_UV_9 * W - 0.5
c0 = np.clip(np.floor(src).astype(int), 0, W - 1)
c1 = np.clip(c0 + 1, 0, W - 1)
f = np.clip(src - c0, 0, 1).astype(np.float32)
nmb = nmb[:, c0, :] * (1 - f)[None, :, None] + nmb[:, c1, :] * f[None, :, None]
write_img(img_nm, nmb)
log("NoseMask resampled")

# debug crops of the final texture for eye verification
try:
    from PIL import Image as PILImage
    arr8 = (np.clip(tex[..., :3], 0, 1) * 255).astype(np.uint8)
    arr8 = arr8[::-1, :, :]        # Blender row 0 = bottom
    full = PILImage.fromarray(arr8)
    full.crop((int(5 / L_UV_8 * W), 0, int(19 / L_UV_8 * W), H)).resize((1400, 1024)).save(
        os.path.join(BASE, "refs", "dbg_tex_fwd.png"))
    full.crop((int(38 / L_UV_8 * W), 0, int(57.4 / L_UV_8 * W), H)).resize((1382, 1024)).save(
        os.path.join(BASE, "refs", "dbg_tex_tail.png"))
    full.crop((int(8 / L_UV_8 * W), 0, int(24 / L_UV_8 * W), H)).resize((1140, 1024)).save(
        os.path.join(BASE, "refs", "dbg_tex_belly.png"))
    log("debug crops written to refs/")
except Exception as e:
    log("debug crop failed:", e)

# hide decal helpers again
for ob in D.objects:
    if ob.name.startswith(("B789_Logo", "LogoBarriga", "Reg787", "MarkDreamliner")):
        ob.hide_viewport = True
        ob.hide_render = True

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
