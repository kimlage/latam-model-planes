#!/usr/bin/env python3
"""Move PT-TMT to where the photograph puts it, before the wedge is repainted.

    /Applications/Blender.app/Contents/MacOS/Blender -b "airbus A319/A319_LATAM.blend" \
        --python "airbus A319/fix_matricula_a319.py" -- [--seco]

Then, and only then, run `reparar_echarpe.py -- a319 --forcar`.

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------
The 2026-08-22 round re-measured the A319's rear écharpe against PT-TMT's own
photograph (ref_sdu_00.jpg, CC0) and found the published rule inverted: it swept
the forward boundary FORWARD at the crown and let the paint down to |theta| 150.
The corrected boundary is

    x >= 23.50 + 1.00*z        theta <= 99.2 - 7.887*(x - 24.60)

and it leaves the registration's old box — x 26.45..28.45, z 0.22..0.66 — on
WHITE hull. White letters on white.

The same photograph says where the letters belong. Measured on the rectified
frame, PT-TMT's glyphs span 0.60..2.40 m aft of door 4's centre and their top
edge sits at theta 63.1 from the crown, with an arc height of 0.345 m — a
width/height ratio of 5.2, against 3.1 for the letters the model had. Door 4 is
the anchor, so the box below is stated relative to it, not as a bare number:

    x   26.41 .. 28.21      (= door 4 centre + 0.60 .. + 2.40)
    theta  56.5 .. 67.7     (top edge / bottom edge from the crown)

The theta band is RAISED 6.6 degrees from the photograph's own 63.1..74.3, and
that is worth saying out loud. The model's door 4 sits at x 25.81 while
PT-TMT's, measured on the same rectified frame that the fin agrees with to
0.07 m, is at 24.60 — 1.21 m forward. Anchoring the registration on the door
therefore puts it 1.21 m further aft than the aeroplane has it, where the
wedge's lower boundary has already risen 9.5 degrees, and the photograph's band
would hang the last "T" out on white hull. Raised, the box clears the boundary
by 3 degrees at its aft end. The real fix is the door; see the QA backlog.

WHY NOT `refazer_marcas.py`. Because the art is wrong. The A319's `Reg_E` mesh
still holds the MASTER A320neo's PT-TMN — painting the registration from it
writes the wrong aircraft's marks, which is exactly what a first attempt at this
change did. The glyphs that read PT-TMT exist only as PAINT, put there by
`build_a319_livery.py`. So they are moved as paint: read out of the texture,
resampled into the new box, written back, and the old box flattened.

WHY BEFORE THE WEDGE REPAINT. At this moment both boxes are inside the OLD
wedge, so both are flat indigo and "erase to indigo" is the honest operation.
Afterwards the old box is outside the new wedge and would have to be erased to
white instead — and the new box, being paint, is protected by
`reparar_echarpe`'s own rule that marks are never written.
"""
import math
import os
import sys

import bpy
import numpy as np

BRANCO_MARCA = np.array([0xF2, 0xF3, 0xF5], np.float32) / 255.0
INDIGO = np.array([0x2A, 0x00, 0x88], np.float32) / 255.0
BASE = np.array([0xE6, 0xE7, 0xEA], np.float32) / 255.0

VELHA = (26.42, 28.55, 78.0, 107.0)      # x0, x1, |theta| 0, |theta| 1
#   the glyphs alone: read off the texture they span x 26.456..28.443 and
#   |theta| 80.3..104.9, an arc height of 0.64 m against a width of 1.99 —
#   a ratio of 3.1 where the photograph gives 5.2. The box below excludes
#   door 4's outline, which starts at x 26.36 and is white ink too.
PORTA4 = 25.81                            # door 4 centre, spec_a319 -> portas
NOVA = (PORTA4 + 0.60, PORTA4 + 2.40, 56.5, 67.7)
SS = 3                                    # supersampling of the resample


def casco():
    for o in bpy.data.objects:
        o.hide_viewport = False
    bpy.context.view_layer.update()
    return bpy.data.objects.get("Fuselagem") or bpy.data.objects["Casco"]


def mapa_uv(ob):
    me = ob.data
    uvl = me.uv_layers.active.data
    M = ob.matrix_world
    X, U = [], []
    for poly in me.polygons:
        for li in poly.loop_indices:
            X.append((M @ me.vertices[me.loops[li].vertex_index].co).x)
            U.append(uvl[li].uv[0])
    a = np.polyfit(np.array(U), np.array(X), 1)
    return float(a[1]), float(a[0])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    seco = "--seco" in argv

    ob = casco()
    x0m, L = mapa_uv(ob)
    imT = bpy.data.images["LiveryTex"]
    imF = bpy.data.images["LiveryFac"]
    W, H = imT.size
    bt = np.empty(W * H * 4, np.float32); imT.pixels.foreach_get(bt)
    bf = np.empty(W * H * 4, np.float32); imF.pixels.foreach_get(bf)
    tex = bt.reshape(H, W, 4)
    fac = bf.reshape(H, W, 4)
    ef = BASE[None, None, :] * (1 - fac[..., 0:1]) + tex[..., :3] * fac[..., 0:1]

    x = x0m + L * (np.arange(W) + 0.5) / W
    thg = np.degrees(np.abs(((np.arange(H) + 0.5) / H - 0.5) * 2 * math.pi))
    print("[matricula] hull %s  u->x x0=%.3f L=%.3f  tex %dx%d"
          % (ob.name, x0m, L, W, H))

    def cols(a, b):
        return np.nonzero((x >= a) & (x <= b))[0]

    def rows(a, b, lado):
        s = np.sign(((np.arange(H) + 0.5) / H - 0.5))
        return np.nonzero((thg >= a) & (thg <= b) & (s == lado))[0]

    total = 0
    for lado in (-1, 1):
        nome = "port" if lado < 0 else "stbd"
        cv = cols(VELHA[0], VELHA[1])
        rv = rows(VELHA[2], VELHA[3], lado)
        blk = tex[rv[0]:rv[-1] + 1, cv[0]:cv[-1] + 1, :3]
        blkf = fac[rv[0]:rv[-1] + 1, cv[0]:cv[-1] + 1, 0]
        # the ink, not the hull: the white hull is E6E7EA at Fac 0, the ink is
        # F2F3F5 at Fac 1, and 0.14 of colour apart is too little to separate
        # them by colour alone — the Fac channel is what tells them apart.
        tinta = (blkf > 0.5) & \
            (np.abs(blk - BRANCO_MARCA[None, None, :]).sum(2) < 0.10)
        if tinta.sum() < 200:
            print("   [%s] no white ink found in the old box — nothing moved" % nome)
            continue
        ys, xs = np.nonzero(tinta)
        # tight box of the ink, in texels, then in (x, |theta|)
        c0 = cv[0] + xs.min(); c1 = cv[0] + xs.max()
        r0 = rv[0] + ys.min(); r1 = rv[0] + ys.max()
        recorte = tinta[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        print("   [%s] ink %d texels   x %.3f..%.3f  |theta| %.1f..%.1f"
              % (nome, int(tinta.sum()), x[c0], x[c1], thg[min(r0, r1)],
                 thg[max(r0, r1)]))

        # resample the ink mask into the new box, supersampled
        cn = cols(NOVA[0], NOVA[1])
        rn = rows(NOVA[2], NOVA[3], lado)
        nh, nw = len(rn), len(cn)
        gy = (np.arange(nh * SS) + 0.5) / (nh * SS)
        gx = (np.arange(nw * SS) + 0.5) / (nw * SS)
        # the old block runs crown-ward in the same direction on both sides
        src_y = np.clip((gy * recorte.shape[0]).astype(int), 0, recorte.shape[0] - 1)
        src_x = np.clip((gx * recorte.shape[1]).astype(int), 0, recorte.shape[1] - 1)
        amostra = recorte[src_y][:, src_x].astype(np.float32)
        cob = amostra.reshape(nh, SS, nw, SS).mean(axis=(1, 3))

        # 1. old box -> flat indigo (it IS indigo there, before the wedge round)
        R0, R1 = rv[0], rv[-1] + 1
        C0, C1 = cv[0], cv[-1] + 1
        tex[R0:R1, C0:C1, :3] = INDIGO
        tex[R0:R1, C0:C1, 3] = 1.0
        fac[R0:R1, C0:C1, :] = 1.0
        # 2. new box -> ink over whatever is there (indigo, under the old rule)
        Rn0, Rn1 = rn[0], rn[-1] + 1
        Cn0, Cn1 = cn[0], cn[-1] + 1
        alvo = tex[Rn0:Rn1, Cn0:Cn1, :3]
        novo = alvo * (1 - cob[..., None]) + BRANCO_MARCA[None, None, :] * cob[..., None]
        tex[Rn0:Rn1, Cn0:Cn1, :3] = novo
        tex[Rn0:Rn1, Cn0:Cn1, 3] = 1.0
        fac[Rn0:Rn1, Cn0:Cn1, :] = 1.0
        total += int(cob.sum())
        print("   [%s] moved to x %.3f..%.3f  |theta| %.1f..%.1f  (%d texels of ink)"
              % (nome, x[cn[0]], x[cn[-1]], NOVA[2], NOVA[3], int(cob.sum())))

    if seco:
        print("[matricula] DRY RUN — nothing written")
        return
    imT.pixels.foreach_set(tex.ravel()); imT.update()
    imF.pixels.foreach_set(fac.ravel()); imF.update()
    for im in (imT, imF):
        if im.packed_file:
            im.pack()
    bpy.ops.wm.save_mainfile()
    print("[matricula] blend saved  (%d texels of ink)" % total)


if __name__ == "__main__":
    main()
