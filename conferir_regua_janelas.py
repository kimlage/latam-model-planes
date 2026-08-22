#!/usr/bin/env python3
"""Measure a photographed fuselage with the CABIN WINDOW ROW as the ruler.

    python3 conferir_regua_janelas.py                       # the A319, PT-TMT
    python3 conferir_regua_janelas.py --foto <jpg>          # another print

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------
`conferir_echarpe.py` rectifies a photograph onto the model's own (x, z) with a
homography fitted to the model's SILHOUETTE and controlled on the FIN. On
2026-08-22 that instrument reported the A319's aft passenger door 1.21 m aft of
where the photograph put it, against an ACAP that says otherwise. The ACAP was
right. The homography is about 3% short in x, and the fin cannot catch that:
the fin's leading and trailing edges are two near-vertical lines standing at the
same station, so matching them pins position and lean and barely pins SCALE.

This file measures the same photograph without any homography.

THE INSTRUMENT. The cabin windows are evenly spaced, they lie on the SAME skin
as the doors, the titles and the registration, and they run the length of the
cabin. Under any perspective camera, equally spaced collinear points map to a
1-D projective sequence, so

    t(n) = (a n + b) / (c n + 1)

fits the photographed window centres exactly, with n the window index and t the
distance along the row in the image. Three parameters, dozens of observations.
Invert it and any feature on that line reads directly in WINDOW PITCHES — a
unit that needs no plane, no camera, and no scale.

To turn pitches into metres you need one real length. Use two stations the
aircraft's own ACAP PRINTS. For the A319 that is figure 2-7-0-991-002 sheet 2:
5.04 / 12.83 / 13.68 / 25.81 / 8.16 / 20.56 m, all from the nose. Anchoring on
the two passenger doors gives a pitch of 0.535 m — the 21-inch frame — and
then a station that was NOT used in the anchoring, the aft cargo door, lands
0.15 m from its printed 20.56. That is the check that the ruler is honest.

WHAT IT FOUND, 2026-08-22. See QA-BACKLOG.md, section 2026-08-22, item 1. The
short version: the model's door 4 (25.81) is the printed ACAP station and is
correct; the model's window PITCH (0.515 m, 35 windows, inherited from the
A320neo master) is 3% short and carries one window too many; and the wedge's
forward-boundary rule, with the paint that was laid to it, sits ~0.8 m ahead of
the boundary the photograph shows. The photographs are NOT
committed (see NOTICE.md); fetch them with `python3 refs_fetch.py` first.

HOW TO POINT IT AT ANOTHER AEROPLANE. Give `--foto`, then re-measure `EIXO`
(two points on the window row, nose-ward second) and `COTAS` (two printed ACAP
stations and the pixel positions of the features that carry them). Everything
else is found automatically.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

RAIZ = os.path.dirname(os.path.abspath(__file__))

# --- the A319 / PT-TMT setup -------------------------------------------------
FOTO = os.path.join(RAIZ, "airbus A319", "refs", "ref_sdu_00.jpg")
EIXO = ((1426.0, 1664.5), (2140.0, 1477.5))   # two points on the window row
CINTO = (5.07, -0.01614)                      # s of the row: s = a + b t
BUSCA = (-160.0, 1460.0)                      # t range swept for windows
# printed ACAP stations and the image position of the feature that carries them
COTAS = (("porta 1", 5.04, 1471.7), ("porta 4", 25.81, -168.6))
CONFERE = (("porta de carga traseira", 20.56, 188.0, +0.91),)  # not anchored


class Regua:
    """The 1-D projective ruler t <-> window index n, and n <-> metres."""

    def __init__(self, img, eixo, cinto, busca):
        self.A = np.asarray(img.convert("L"), float)
        p0, p1 = np.array(eixo[0]), np.array(eixo[1])
        self.p0 = p0
        self.d = (p1 - p0) / np.linalg.norm(p1 - p0)
        self.n = np.array([-self.d[1], self.d[0]])
        self.cinto = cinto
        self.janelas = self._achar(busca)
        self.par = self._ajustar(self.janelas)

    def px(self, t, ds=0.0):
        s = self.cinto[0] + self.cinto[1] * t + ds
        return self.p0 + self.d * t + self.n * s

    def amostrar(self, t, ds=0.0):
        x, y = self.px(t, ds)
        x0, y0 = int(np.floor(x)), int(np.floor(y))
        fx, fy = x - x0, y - y0
        A = self.A
        return (A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x0 + 1] * fx * (1 - fy)
                + A[y0 + 1, x0] * (1 - fx) * fy + A[y0 + 1, x0 + 1] * fx * fy)

    def _achar(self, busca):
        """Window centres: dark blobs of the right width sitting on the row."""
        ts = np.arange(busca[0], busca[1], 0.25)
        perfil = np.array([min(self.amostrar(t, ds)
                               for ds in np.arange(-11, 11.5, 1.0)) for t in ts])
        escuro = perfil < 165
        centros, i = [], 0
        while i < len(ts):
            if not escuro[i]:
                i += 1
                continue
            j = i
            while j < len(ts) and escuro[j]:
                j += 1
            larg = ts[j - 1] - ts[i]
            if 15.0 <= larg <= 24.0:            # a window pane; paint runs longer
                sub = np.arange(ts[i] - 3, ts[j - 1] + 3, 0.25)
                dss = np.arange(-13, 13.5, 0.25)
                G = np.array([[self.amostrar(t, ds) for ds in dss] for t in sub])
                w = np.clip(172.0 - G, 0, None)
                massa = w.sum()
                if massa > 3.0e5:                # a window, not a placard or a seam
                    centros.append(float((w.sum(axis=1) * sub).sum() / massa))
            i = j
        return centros

    @staticmethod
    def _indices(cent, passo):
        """Consecutive window indices, counting the ones the wing hides."""
        ns, n = [0], 0
        for a, b in zip(cent, cent[1:]):
            n += int(round((b - a) / passo))
            ns.append(n)
        return ns

    def _ajustar(self, cent):
        passo = float(np.median(np.diff(cent)))
        ns = self._indices(cent, passo)
        M = np.array([[n, 1.0, -n * t] for n, t in zip(ns, cent)])
        par, *_ = np.linalg.lstsq(M, np.array(cent), rcond=None)
        self.ns, self.rms = ns, float(np.sqrt(np.mean(
            [(self.t_de(n, par) - t) ** 2 for n, t in zip(ns, cent)])))
        return par

    @staticmethod
    def t_de(n, par):
        return (par[0] * n + par[1]) / (par[2] * n + 1)

    def n_de(self, t):
        a, b, c = self.par
        return (b - t) / (c * t - a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--foto", default=FOTO)
    a = ap.parse_args()
    if not os.path.exists(a.foto):
        sys.exit("photograph missing (they are not committed): "
                 "run `python3 refs_fetch.py \"airbus A319\"` first")

    r = Regua(Image.open(a.foto), EIXO, CINTO, BUSCA)
    print(f"{len(r.janelas)} janelas achadas, indices 0..{max(r.ns)}, "
          f"ajuste projetivo rms {r.rms:.2f} px")

    (na, xa, ta), (nb, xb, tb) = COTAS
    passo = (xb - xa) / (r.n_de(ta) - r.n_de(tb))
    print(f"ancoras impressas: {na} {xa} m, {nb} {xb} m")
    print(f"-> passo de janela {passo:.4f} m "
          f"(caverna de 21 in = 0.5334 m; modelo diz 0.515)")

    def x_de(t):
        return xa + (r.n_de(ta) - r.n_de(t)) * passo

    print(f"-> as duas portas distam {r.n_de(ta) - r.n_de(tb):.2f} passos de janela")
    print(f"-> fileira de janelas: x {x_de(r.t_de(max(r.ns), r.par)):.2f}"
          f" .. {x_de(r.t_de(0, r.par)):.2f}  ({max(r.ns) + 1} janelas)")
    for nome, cota, t, desloc in CONFERE:
        medido = x_de(t) - desloc
        print(f"conferencia (fora da ancoragem): {nome} {medido:.2f} m "
              f"contra {cota} impresso  -> {medido - cota:+.2f} m")


if __name__ == "__main__":
    main()
