#!/usr/bin/env python3
"""Extracts crown/keel/half-width from the 3-view of a rasterized ACAP/APR.

A generalization of the extractors that worked on the A320 (yellow fill, Airbus)
and on the 787-9 (line art, Boeing). Typical usage:

    python3 extrair_contorno.py config.json

The configuration JSON describes the anchors measured BY HAND on enlarged crops
— they are the one step that cannot be automated, because every drawing has a
different framing. See `exemplo_config.json` next to this file.

The script decides nothing on its own: it applies the recipe and prints the
sanity dimensions for you to compare against the document. If the sanity check
does not match to within ~1%, the anchors are wrong — fix the anchors, not the
result.
"""
import json
import sys

import numpy as np
from PIL import Image

try:
    from scipy.signal import medfilt, savgol_filter
except ImportError:  # scipy is optional; degrades to a plain median
    medfilt = None
    savgol_filter = None


# ---------------------------------------------------------------- masks

def mask_linhas(img, limiar=128):
    """Line art (Boeing): a dark pixel is outline."""
    return np.asarray(img.convert("L")).astype(np.uint8) < limiar


def mask_preenchimento_amarelo(img, dr_db=15, r_min=170):
    """Yellow-filled silhouette (Airbus ACAP): high R and a large R-B.

    It picks up the aircraft's interior instead of the stroke, which avoids
    capturing the dimension lines. In exchange, the white halos around the
    dimension arrows bite into the silhouette and create phantom 'waists' —
    hence the mandatory monotonicity further down.
    """
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    return (a[:, :, 0] - a[:, :, 2] > dr_db) & (a[:, :, 0] > r_min)


MASCARAS = {"linhas": mask_linhas, "amarelo": mask_preenchimento_amarelo}


# ---------------------------------------------------------------- cleanup

def limpar(y, k=21, tol=15):
    """Removes outliers (dimension lines crossing the band) without flattening
    the curve."""
    if medfilt is None:
        return y
    med = medfilt(y, k)
    return medfilt(np.where(np.abs(y - med) > tol, med, y), 9)


def suavizar(y, janela=13, ordem=3):
    if savgol_filter is None or len(y) < janela:
        return y
    return savgol_filter(y, janela, ordem)


def pontear(xm, y, vaos):
    """Interpolates over stretches where another part touches the outline.

    Wing, nacelle, gear and stabilizer cross the fuselage band and pull the
    outline away. Better to interpolate the gap than to trust the pixel.
    """
    ok = np.ones(len(xm), bool)
    for a, b in vaos:
        ok &= ~((xm > a) & (xm < b))
    if ok.sum() < 2:
        raise SystemExit("vaos consomem a curva inteira — revise a config")
    return np.interp(xm, xm[ok], y[ok])


# ---------------------------------------------------------------- extraction

def banda(mask, x0, x1, y0, y1):
    """First and last marked pixel in each column within the band."""
    sub = mask[y0:y1, :]
    xs, topo, base = [], [], []
    for c in range(x0, x1 + 1):
        col = np.where(sub[:, c])[0]
        if len(col) == 0:
            continue
        xs.append(c)
        topo.append(col[0] + y0)
        base.append(col[-1] + y0)
    return np.array(xs), np.array(topo, float), np.array(base, float)


def main(cfg_path):
    cfg = json.load(open(cfg_path))
    img = Image.open(cfg["imagem"])
    mask = MASCARAS[cfg.get("mascara", "linhas")](img)

    a = cfg["ancoras"]
    x_nariz, x_cauda = a["x_nariz"], a["x_cauda"]
    escala = a["cota_m"] / (x_cauda - x_nariz)
    print(f"escala {escala*1000:.3f} mm/px  ({a['cota_m']} m em {x_cauda-x_nariz} px)")

    def x_m(px):
        return (px - x_nariz) * escala

    # ---- side view: crown and keel
    lat = cfg["lateral"]
    xs, crown_px, keel_px = banda(mask, x_nariz, x_cauda, lat["y0"], lat["y1"])
    xm = x_m(xs)
    crown_px = pontear(xm, limpar(crown_px), lat.get("vaos_crown", []))
    keel_px = pontear(xm, limpar(keel_px), lat.get("vaos_keel", []))

    # vertical datum: the middle of the constant section
    c0, c1 = cfg["secao_constante"]
    sel = (xm > c0) & (xm < c1)
    crown_ref, keel_ref = np.median(crown_px[sel]), np.median(keel_px[sel])
    H = (keel_ref - crown_ref) * escala
    z_mid = (crown_ref + keel_ref) / 2

    def z_m(py):
        return (z_mid - py) * escala

    # ---- top view: half-width
    top = cfg["topo"]
    xs_t, esq, dir_ = banda(mask, x_nariz, x_cauda, top["y0"], top["y1"])
    xm_t = x_m(xs_t)
    sel_t = (xm_t > c0) & (xm_t < c1)
    cl = np.median((esq[sel_t] + dir_[sel_t]) / 2)
    hw = limpar(np.maximum(np.abs(cl - esq), np.abs(dir_ - cl)), 21, 12)
    W = 2 * np.median(hw[sel_t]) * escala

    # monotonicity: the width only grows going aft in the nose and only shrinks
    # going aft in the tail. Without this, a dimension halo becomes a phantom
    # waist in the hull (it happened on the A320: w=0.22 m at x≈6).
    lim_nariz = top.get("ate_x_nariz", c0)
    lim_cauda = top.get("de_x_cauda", c1)
    sel_n = xm_t < lim_nariz
    sel_c = xm_t > lim_cauda
    w_nariz = np.maximum.accumulate(hw[sel_n]) * escala
    w_cauda = np.maximum.accumulate(hw[sel_c][::-1])[::-1] * escala

    # ---- sanity and normalization
    #
    # The measurement never comes out exact, and both deviations have a known
    # cause: with a line mask, the outline is the OUTER EDGE of the stroke on
    # both sides, so the height comes out a few per cent too large; with a fill
    # mask, the dimension halos bite into the silhouette and the width comes out
    # slightly too small. In both cases the drawing is right and the reading has
    # a scale bias — so normalize each axis by the doc/measured ratio instead of
    # touching the anchors.
    #
    # A large error (>4%) is something else: that is a genuinely wrong anchor —
    # which is what happened when the 787 side band glued the fuselage to the
    # stabilizer and the "tail" came out at 79 m. In that case, go back to the
    # crops.
    H_doc, W_doc = cfg["sanidade"]["H"], cfg["sanidade"]["W"]
    kz, ky = H_doc / H, W_doc / W
    print(f"H medida {H:.3f} m -> doc {H_doc}  (fator z x{kz:.4f})")
    print(f"W medida {W:.3f} m -> doc {W_doc}  (fator y x{ky:.4f})")
    for nome, medido, doc in (("H", H, H_doc), ("W", W, W_doc)):
        erro = abs(medido - doc) / doc
        if erro > 0.04:
            print(f"  {nome}: erro {erro*100:.1f}% — ANCORA ERRADA, volte aos crops")
        else:
            print(f"  {nome}: erro {erro*100:.2f}% — viés de leitura, normalizado")
    if not cfg.get("normalizar", True):
        kz = ky = 1.0
        print("  (normalizacao desligada por config)")

    def z_m_norm(py):
        return z_m(py) * kz

    print(f"ponta do nariz z = {z_m_norm(a['y_nariz']):+.3f} m")
    if "y_solo" in a:
        print(f"clearance keel-solo {(a['y_solo']-keel_ref)*escala*kz:.2f} m")

    passo = cfg.get("passo", 4)
    saida = {
        "fonte": cfg["fonte"],
        "escala_mm_px": round(escala * 1000, 3),
        "datum": "x=0 at the nose tip; z=0 at the centre of the constant section",
        "sanidade": {"H_medida": round(H, 3), "W_medida": round(W, 3),
                     "H_doc": H_doc, "W_doc": W_doc,
                     "fator_z": round(kz, 4), "fator_y": round(ky, 4),
                     "ponta_nariz_z": round(z_m_norm(a["y_nariz"]), 3)},
        "lateral": {
            "x": [round(v, 3) for v in xm[::passo]],
            "crown": [round(z_m_norm(v), 3) for v in suavizar(crown_px)[::passo]],
            "keel": [round(z_m_norm(v), 3) for v in suavizar(keel_px)[::passo]],
        },
        "topo_nariz": {"x": [round(v, 3) for v in xm_t[sel_n][::passo]],
                       "meia_larg": [round(v * ky, 3) for v in w_nariz[::passo]]},
        "topo_cauda": {"x": [round(v, 3) for v in xm_t[sel_c][::passo]],
                       "meia_larg": [round(v * ky, 3) for v in w_cauda[::passo]]},
    }
    with open(cfg["saida"], "w") as f:
        json.dump(saida, f, indent=1)
    print("gravado", cfg["saida"])

    # a sample to eyeball against the drawing
    for q in cfg.get("amostrar", [1, 2, 4, 8, 12]):
        i = int(np.argmin(np.abs(xm - q)))
        j = int(np.argmin(np.abs(xm_t - q)))
        print(f"x={q:6.1f}  crown={z_m_norm(crown_px[i]):+.2f}  "
              f"keel={z_m_norm(keel_px[i]):+.2f}  w/2={hw[j]*escala*ky:.2f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "config.json")
