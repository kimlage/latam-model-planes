#!/usr/bin/env python3
"""Repaint the rear echarpe of a master ABSOLUTELY, from its own measured rule.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<aircraft>/<X>.blend" \
        --python reparar_echarpe.py -- <tag> [--seco]

`--seco` (dry) measures and reports without writing anything.

------------------------------------------------------------------------------
2026-08-22 — THE RULES THEMSELVES WENT ON TRIAL
------------------------------------------------------------------------------
The round below repaired the PAINT against each aeroplane's published RULE. It
never asked whether the rule was right. Every rule has now been straddled
against its own registration's photograph: the photograph is rectified onto the
model's (x, z) by a homography fitted to the hull silhouette, and the skin is
sampled 0.35 m each side of the boundary the rule draws. Ten of the eleven put
white outside and paint inside. The A319 did not — its rule leaned the wrong way and reached |theta|
150 — and the 777's forward boundary sat 0.86 m too far aft. Both are replaced
here (see `_r_a319` and `_r_77w`), and their `auditoria` flags are gone with
them. `conferir_echarpe.py` is the test, and it stays runnable.


------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------
The owner looked at the eleven tails and said several were wrong: a white
rectangle punched into the wedge, a lower boundary that goes dotted and drops a
detached indigo splinter, a rectangular white step across the crown. Three
different types, three different symptoms, one cause:

**the wedge was never rasterized — it was edited.**

Each builder painted its wedge once and every later script that touched the
tail changed it CONDITIONALLY, and every condition has a complement that keeps
old paint:

  A321   `to_indigo = nova & ~velha & flat_w` — only repaints a texel that is
         ALREADY exactly flat. Anti-aliased edge texels inside the band that
         changed are skipped: that is the dotted boundary. Texels of the old
         wedge that were not exactly flat indigo are left behind: that is the
         splinter. Measured on PS-LBA: 92 outlier rows on the forward edge and
         a detached indigo strip 0.39 m long aft of the fin trailing-edge line.

  787-8  `np.abs(np.sin(THg)) > 0.10` on a repair that had to run everywhere —
         so the repair skipped |theta| <= 5.74 deg and left a rectangular block
         of the resampled 787-9 paint standing across the crown. Measured on
         CC-BBF: the step spans theta -5.7..+6.0 and is 0.40 m deep in x.

  fleet  `fac[m] = 0` used as "erase" restores the hull base UNCONDITIONALLY.
         An erase box that crosses the wedge prints a white rectangle in the
         indigo. On both A321s that box is `build_a321_fase2_livery.py`'s
         `box(36.9, 38.45, 0.95, 1.50)` ("old reg, remapped"), of which
         x 37.24..38.45 lies inside the wedge. `refazer_marcas.Casco._basemap`
         is the one place in the repository that solved this (base="indigo" /
         "fronteira") and it says so in its own docstring.

Under all three sits a fourth: the rule lives in (x, z), the texture lives in
(x, theta), and the bridge is a section table z(x, theta) = zc(x) + rz(x)*cos
theta that each builder also made its own way. The 767's is spliced at x = 41.0
with no continuity constraint — `zc_rz()` in `b5_livery.py` returns the constant
mid-section below and `spec_763.cauda_estacoes` above, and the two disagree by
dzc = +0.117 m, drz = -0.117 m AT ONE STATION. The wedge's forward boundary
therefore jumps from |theta| 114.02 to 117.04 there: the 3.0-degree notch the
owner saw as a torn lower edge on CC-CWY.

------------------------------------------------------------------------------
WHAT THIS DOES
------------------------------------------------------------------------------
`latam_livery_kit.secoes_do_casco` reads the section table from the MESH, in
world coordinates, one entry per station — no splice, so no step.
`cobertura_echarpe` rasterizes the aircraft's own published rule over the texel
grid with supersampling, so the boundary is anti-aliased rather than cut.
`reparar_echarpe` writes it back only where the current effective colour lies ON
the white->indigo segment and does not touch a mark: registration glyphs, door
rings, windows, grooves, titles and coral are never written, and neither is any
texel adjacent to one.

The rules below are each aircraft's OWN, copied from its builder with the
source named. Nothing here re-measures a wedge; the fix is the rasterizer, not
the geometry. Where the paint has drifted from the published rule the offset is
stated and applied, so the repair removes the defect WITHOUT moving the wedge:
that is the case on the 787-8, whose texture is a column resample of the -9's
and sits 0.48 m aft of the -8 rule it was validated against. Moving it back is a
measurement round, not this one.
"""
import math
import os
import sys

import numpy as np

RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# The rule table below is DATA, and `conferir_echarpe.py` — which puts those
# rules on trial against the photographs — has to read it from plain python.
# So Blender is optional at import time and required only to run the repair.
try:
    import bpy
    import latam_livery_kit as kit
except ImportError:  # pragma: no cover - outside Blender
    bpy = kit = None

BRANCO = np.array([0xE6, 0xE7, 0xEA], np.float32) / 255.0   # hull base
INDIGO = np.array([0x2A, 0x00, 0x88], np.float32) / 255.0


# ----------------------------------------------------------------- the fleet
# regra(X, Z, THdeg) -> bool, in the aircraft's own coordinates. Where the paint
#   has drifted from the published rule, the offset is written INTO the rule and
#   said out loud there.
# zona: (x0, x1) window the repair is allowed to write in.
# poupar: (x0, x1, th0, th1) boxes the repair must NOT write in, |theta| in
#   degrees. The colour test protects marks because a mark is off the
#   white->indigo segment — but a mark painted in PURE INDIGO on white sits ON
#   that segment and is therefore invisible to it. The A319's "AIRBUS A319"
#   title is exactly that, and its art no longer exists in the blend, so it
#   cannot be repainted if it is lost. Inside the box the old paint stays, so
#   the box has to be chosen where the OLD and NEW boundaries nearly agree. On
#   the A319 they cross at z = 1.135 and the title's ink sits at z 1.04..1.21,
#   astride that crossing: over |theta| 55.5..63.5 the two boundaries are never
#   more than 0.16 m apart, which is the size of the step left at the box's
#   edges. Choosing the band by eye instead put a 0.35 m notch in the wedge.
#   The 777's "BOEING 777-300" is the same case and easier: it sits at
#   x 55.8..58.7, and BOTH boundaries are aft of x 59.3 at its height, so the
#   spared box is white either way and leaves no step at all.
# auditoria: True means "measured clean, do not write" — the entry exists so the
#   next round can re-measure with one command instead of re-deriving the rule.
#   `--forcar` overrides it, deliberately and visibly.

def _r_763er(X, Z, T):
    # boeing 767-300ER/b5_livery.py, CC-CWY 2026-08-20
    return ((X >= 42.11 + 1.008 * Z) &
            (T <= np.clip(134.4 - 8.061 * (X - 41.5), 0.0, 180.0)) &
            (X <= 50.55 + 0.398 * Z))


def _r_a321(X, Z, T):
    # airbus A321neo/build_a321_fase2_livery.py, PS-LBO DSC00834
    return ((X >= 35.48 + 0.822 * Z) &
            (T <= np.maximum(129.0 - 23.7 * (X - 34.45),
                             105.3 - 3.78 * (X - 36.05))) &
            (X <= 41.46 + 0.0538 * Z))


def _r_788(X, Z, T):
    # boeing 787-8/build_788_livery.py, wedge_mask(); the +0.48 is the drift of
    # the resampled -9 paint from this rule, measured by minimising the
    # disagreement over the flat paint of the tail zone (3.8% residual).
    d = 0.48
    return ((X >= 42.68 + 0.992 * Z + d) &
            (T <= 117.0 - 5.2 * (X - 42.61 - d)) &
            (X <= 51.05 + 0.3858 * Z + 0.15))


def _r_a319(X, Z, T):
    # RE-MEASURED 2026-08-22 on ref_sdu_00.jpg (PT-TMT, CC0), rectified onto the
    # model's own (x, z) by a homography fitted to the hull silhouette; the fin
    # is the control, and its leading and trailing edges land within 0.07 m and
    # 0.17 m of the model's over z 2.5..7.0, so the frame is the model's frame.
    #
    # The rule this replaces leaned the WRONG WAY. It read the forward boundary
    # as a swoosh going FORWARD at the crown and AFT at the keel, and let the
    # paint down to |theta| <= 150 — nearly the whole circumference. Sampled
    # straight off the photograph on a 0.25 m grid, the crown is WHITE over the
    # whole of x 21.5..29 and nothing below z = -0.8 is painted anywhere. The
    # boundary is a straight line leaning the same way as the rest of the fleet:
    #
    #   forward   x >= 23.50 + 1.00*z      z -0.75..+1.25, first paint per row
    #                                      lands on 0.25 m grid steps exactly
    #   lower     theta <= 99.2 - 7.887*(x - 24.60)   rms 1.6 deg over 7 rows
    #   rear      x <= 30.30 + 0.10*z      paint ends 30.0..30.3 at z 1.25..1.75
    #                                      (was 31.30, never measured)
    #
    # Straddling the boundary at +-0.35 m: the published rule scored 4 right and
    # 8 wrong on the forward edge and 1 right / 6 wrong on the lower one; this
    # rule scores 9/1 and 2/0, with the rest landing on the door outline or on
    # the shaded keel where the photograph cannot say.
    return ((X >= 23.50 + 1.00 * Z) &
            (T <= np.clip(99.2 - 7.887 * (X - 24.60), 0.0, 180.0)) &
            (X <= 30.30 + 0.10 * Z))


def _r_a320ceo(X, Z, T):
    # airbus A320ceo/build_a320ceo_livery.py, spec_a320ceo.livery_cc_bfo.echarpe
    return ((X >= 28.60 + 0.66 * Z) & (X <= 30.35 + 1.83 * Z) &
            (Z >= -1.25) & (T <= 145.0))


def _r_a320neo(X, Z, T):
    # airbus A320neo/build_a320neo_fix_livery.py, PT-TMN door-4-anchored frame
    rear = np.interp(Z, [-1.2, 1.6, 1.8, 2.05], [27.75, 32.80, 33.36, 33.85])
    return ((X >= 28.51 + 0.63 * Z) & (X <= rear) & (Z >= -1.2) & (T <= 145.0))


def _r_763carga(X, Z, T):
    # boeing 767-300F/b5f_livery.py and 767-300BCF/b5b_livery.py. The freighter
    # wedge IS smaller than the passenger one — 0.54 m aft and 13 deg shallower,
    # measured on N568LA. Type-specific, not a defect.
    return ((X >= 42.65 + 1.00 * Z) &
            (T <= np.clip(121.1 - 6.44 * (X - 41.5), 0.0, 180.0)) &
            (X <= 50.55 + 0.398 * Z))


def _r_77w(X, Z, T):
    # boeing 777-300ER/build_77w_fase2_livery.py — the one builder that already
    # rasterized its wedge absolutely, with supersampling. This module is that
    # mechanism made shared.
    #
    # FORWARD BOUNDARY RE-MEASURED 2026-08-22 on ref_PT-MUG_2022_FRA.jpg, the
    # same photograph the published rule cites. Sampled on a 0.25 m grid over
    # z -0.50..+2.50, the first painted column per row is
    #
    #     -0.50 -> 57.75   0.00 -> 58.25   1.00 -> 59.50   2.50 -> 60.75
    #
    # a straight line of slope 1.00 through x = 58.25 at z = 0 — 0.86 m FORWARD
    # of the published 59.11. The rectification is controlled on the fin, whose
    # straight leading and trailing edges land within 0.18 m and 0.18 m of the
    # model's over z 6..11.5, so the disagreement is the rule's, not the frame's.
    # Written below parallel to that leading edge (x = 57.996 + 1.0104 z, the
    # value spec_77w calls "conferido em pixel"), which fits the eight sampled
    # rows to 0.02 m: the wedge starts 0.25 m aft of the fin's leading edge in x,
    # 0.18 m perpendicular, where the spec said 0.78 m perpendicular.
    #
    # Only the forward boundary moves, and it moves FORWARD, so nothing that was
    # painted becomes white: the registration and the titles keep their ground.
    # The lower boundary could not be re-read — PT-MUG's lower flank is in deep
    # shadow in this frame and the colour test has no opinion there — and the
    # rear boundary is the fin's own trailing edge. Both are left as published.
    return ((X >= 58.25 + 1.0104 * Z) &
            (T <= np.clip(108.1 + 1.03 * (X - 60.0), 0.0, 180.0)) &
            (X <= 68.254 + 0.396 * Z))


def _r_789(X, Z, T):
    # 787-9 frame, quoted in latam_livery_kit's own header. The -9's builder is
    # not in the repository and its PAINT sits +0.56 m (forward edge) / +0.65 m
    # (aft edge) from those numbers — fitted by minimising the disagreement over
    # the flat paint of the tail zone, residual 1.20%. With the offsets in, the
    # -9's wedge is clean: the drift is a siting question for a photo round, not
    # a defect. The -8 carries the same drift at +0.48 / +0.15, which is what a
    # piecewise column resample of this texture would do.
    return ((X >= 48.77 + 0.992 * Z + 0.56) &
            (T <= 117.0 - 5.2 * (X - 48.70 - 0.56)) &
            (X <= 57.14 + 0.3858 * Z + 0.65))


FROTA = {
    # --- repaired by this round
    "b763er":  dict(regra=_r_763er, zona=(38.0, 55.5),
                    nota="section-table splice at x = 41.0: 3.0 deg step"),
    "a321ceo": dict(regra=_r_a321, zona=(33.0, 45.0),
                    nota="white rectangle, dotted edge, aft splinter"),
    "a321neo": dict(regra=_r_a321, zona=(33.0, 45.0),
                    nota="white rectangle, dotted edge, aft splinter"),
    "b788":    dict(regra=_r_788, zona=(40.0, 57.5),
                    nota="crown block left by |sin theta| > 0.10"),
    # --- audited with --seco and found clean; kept here so the next round can
    #     re-measure them with one command instead of re-deriving the rules
    "a319":    dict(regra=_r_a319, zona=(20.0, 34.2),
                    poupar=[(23.35, 25.00, 55.5, 63.5)],
                    nota="rule re-measured: the swoosh leaned the wrong way and "
                         "the paint reached |theta| 150"),
    "a320ceo": dict(regra=_r_a320ceo, zona=(26.0, 38.0), auditoria=True,
                    nota="clean; 5583 texels of hard cut"),
    "a320neo": dict(regra=_r_a320neo, zona=(26.0, 38.0), auditoria=True,
                    nota="clean; 4535 texels of hard cut"),
    "b763f":   dict(regra=_r_763carga, zona=(38.0, 55.5), auditoria=True,
                    nota="clean; freighter wedge is smaller ON PURPOSE"),
    "b763bcf": dict(regra=_r_763carga, zona=(38.0, 55.5), auditoria=True,
                    nota="clean; freighter wedge is smaller ON PURPOSE"),
    "b77w":    dict(regra=_r_77w, zona=(50.0, 74.5),
                    poupar=[(55.20, 59.00, 62.0, 81.0)],
                    nota="forward boundary re-measured: 0.86 m too far aft"),
    "b789":    dict(regra=_r_789, zona=(44.0, 63.5), auditoria=True,
                    nota="clean once its own offset is applied"),
}


def casco():
    for o in bpy.data.objects:
        o.hide_viewport = False
    bpy.context.view_layer.update()
    return bpy.data.objects.get("Fuselagem") or bpy.data.objects["Casco"]


def mapa_uv(ob):
    """(x0, L) of the hull's linear u -> x map, read from the mesh's own UV."""
    me = ob.data
    uvl = me.uv_layers.active.data
    M = ob.matrix_world
    X, U = [], []
    for poly in me.polygons:
        for li in poly.loop_indices:
            X.append((M @ me.vertices[me.loops[li].vertex_index].co).x)
            U.append(uvl[li].uv[0])
    a = np.polyfit(np.array(U), np.array(X), 1)
    res = float(np.abs(np.polyval(a, np.array(U)) - np.array(X)).max())
    return float(a[1]), float(a[0]), res


def main():
    if bpy is None:
        sys.exit("reparar_echarpe repairs paint; run it inside Blender")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    tag = argv[0]
    cfg = FROTA[tag]
    seco = "--seco" in argv or (cfg.get("auditoria") and "--forcar" not in argv)

    ob = casco()
    x0, L, res = mapa_uv(ob)
    rx, rzc, rrz, rry = kit.secoes_do_casco(ob)
    imT = bpy.data.images["LiveryTex"]
    imF = bpy.data.images["LiveryFac"]
    W, H = imT.size
    bt = np.empty(W * H * 4, np.float32); imT.pixels.foreach_get(bt)
    bf = np.empty(W * H * 4, np.float32); imF.pixels.foreach_get(bf)
    tex = bt.reshape(H, W, 4)
    fac = bf.reshape(H, W, 4)

    print("[echarpe] %s  hull %s  u->x  x0=%.4f L=%.4f (resid %.2e)  %d stations"
          % (tag, ob.name, x0, L, res, len(rx)))
    print("[echarpe] %s" % cfg["nota"])

    cov = kit.cobertura_echarpe(cfg["regra"], rx, rzc, rrz, x0, L, W, H, ss=3)
    x = x0 + L * (np.arange(W) + 0.5) / W
    za, zb = cfg["zona"]
    zona = np.array(np.broadcast_to(((x >= za) & (x <= zb))[None, :], (H, W)))
    th = ((np.arange(H) + 0.5) / H - 0.5) * 2 * math.pi
    thg = np.degrees(np.abs(th))[:, None]
    for px0, px1, pt0, pt1 in cfg.get("poupar", []):
        zona &= ~(((x >= px0) & (x <= px1))[None, :] &
                  ((thg >= pt0) & (thg <= pt1)))
        print("[echarpe] poupado x %.2f..%.2f  |theta| %.0f..%.0f"
              % (px0, px1, pt0, pt1))

    n, muda = kit.reparar_echarpe(tex, fac, cov, zona, BRANCO, INDIGO)
    if n:
        ys, xs = np.nonzero(muda)
        print("[echarpe] %d texels rewritten  x %.3f..%.3f  |theta| %.1f..%.1f"
              % (n, x[xs.min()], x[xs.max()],
                 np.degrees(np.abs(th[ys])).min(), np.degrees(np.abs(th[ys])).max()))
    else:
        print("[echarpe] nothing to repair")

    if seco:
        print("[echarpe] DRY RUN — nothing written%s"
              % ("  (audit entry: pass --forcar to write)"
                 if cfg.get("auditoria") else ""))
        return
    imT.pixels.foreach_set(tex.ravel()); imT.update()
    imF.pixels.foreach_set(fac.ravel()); imF.update()
    for im in (imT, imF):
        if im.packed_file:
            im.pack()
    bpy.ops.wm.save_mainfile()
    print("[echarpe] blend saved")


if __name__ == "__main__":
    main()
