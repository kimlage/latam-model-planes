#!/usr/bin/env python3
"""Extrai crown/keel/meia-largura do 3-view de um ACAP/APR rasterizado.

Generalização dos extratores que funcionaram no A320 (preenchimento amarelo,
Airbus) e no 787-9 (line art, Boeing). Uso típico:

    python3 extrair_contorno.py config.json

O JSON de configuração descreve as âncoras medidas À MÃO em crops ampliados —
elas são o único passo que não dá para automatizar, porque cada desenho tem um
enquadramento diferente. Veja `exemplo_config.json` ao lado.

O script NÃO decide nada sozinho: ele aplica a receita e imprime as cotas de
sanidade para você comparar com o documento. Se a sanidade não bater dentro de
~1%, as âncoras estão erradas — corrija as âncoras, não o resultado.
"""
import json
import sys

import numpy as np
from PIL import Image

try:
    from scipy.signal import medfilt, savgol_filter
except ImportError:  # scipy é opcional; degrada para mediana simples
    medfilt = None
    savgol_filter = None


# ---------------------------------------------------------------- máscaras

def mask_linhas(img, limiar=128):
    """Desenho a traço (Boeing): pixel escuro é contorno."""
    return np.asarray(img.convert("L")).astype(np.uint8) < limiar


def mask_preenchimento_amarelo(img, dr_db=15, r_min=170):
    """Silhueta preenchida de amarelo (Airbus ACAP): R alto e R-B grande.

    Pega o miolo do avião em vez do traço, o que evita capturar as linhas de
    cota. Em compensação, os halos brancos ao redor das setas de cota mordem a
    silhueta e criam 'cinturas' fantasma — daí a monotonicidade obrigatória
    mais abaixo.
    """
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    return (a[:, :, 0] - a[:, :, 2] > dr_db) & (a[:, :, 0] > r_min)


MASCARAS = {"linhas": mask_linhas, "amarelo": mask_preenchimento_amarelo}


# ---------------------------------------------------------------- limpeza

def limpar(y, k=21, tol=15):
    """Tira outliers (linhas de cota cruzando a banda) sem achatar a curva."""
    if medfilt is None:
        return y
    med = medfilt(y, k)
    return medfilt(np.where(np.abs(y - med) > tol, med, y), 9)


def suavizar(y, janela=13, ordem=3):
    if savgol_filter is None or len(y) < janela:
        return y
    return savgol_filter(y, janela, ordem)


def pontear(xm, y, vaos):
    """Interpola por cima de trechos onde outra peça encosta no contorno.

    Asa, nacelle, trem e estabilizador cruzam a banda da fuselagem e puxam o
    contorno para longe. Melhor interpolar o vão do que acreditar no pixel.
    """
    ok = np.ones(len(xm), bool)
    for a, b in vaos:
        ok &= ~((xm > a) & (xm < b))
    if ok.sum() < 2:
        raise SystemExit("vaos consomem a curva inteira — revise a config")
    return np.interp(xm, xm[ok], y[ok])


# ---------------------------------------------------------------- extração

def banda(mask, x0, x1, y0, y1):
    """Primeiro e último pixel marcado em cada coluna dentro da faixa."""
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

    # ---- vista lateral: crown e keel
    lat = cfg["lateral"]
    xs, crown_px, keel_px = banda(mask, x_nariz, x_cauda, lat["y0"], lat["y1"])
    xm = x_m(xs)
    crown_px = pontear(xm, limpar(crown_px), lat.get("vaos_crown", []))
    keel_px = pontear(xm, limpar(keel_px), lat.get("vaos_keel", []))

    # datum vertical: meio da seção constante
    c0, c1 = cfg["secao_constante"]
    sel = (xm > c0) & (xm < c1)
    crown_ref, keel_ref = np.median(crown_px[sel]), np.median(keel_px[sel])
    H = (keel_ref - crown_ref) * escala
    z_mid = (crown_ref + keel_ref) / 2

    def z_m(py):
        return (z_mid - py) * escala

    # ---- vista de topo: meia-largura
    top = cfg["topo"]
    xs_t, esq, dir_ = banda(mask, x_nariz, x_cauda, top["y0"], top["y1"])
    xm_t = x_m(xs_t)
    sel_t = (xm_t > c0) & (xm_t < c1)
    cl = np.median((esq[sel_t] + dir_[sel_t]) / 2)
    hw = limpar(np.maximum(np.abs(cl - esq), np.abs(dir_ - cl)), 21, 12)
    W = 2 * np.median(hw[sel_t]) * escala

    # monotonicidade: a largura só cresce indo para trás no nariz e só
    # diminui indo para trás na cauda. Sem isso, um halo de cota vira uma
    # cintura fantasma no casco (aconteceu no A320: w=0.22 m em x≈6).
    lim_nariz = top.get("ate_x_nariz", c0)
    lim_cauda = top.get("de_x_cauda", c1)
    sel_n = xm_t < lim_nariz
    sel_c = xm_t > lim_cauda
    w_nariz = np.maximum.accumulate(hw[sel_n]) * escala
    w_cauda = np.maximum.accumulate(hw[sel_c][::-1])[::-1] * escala

    # ---- sanidade e normalização
    #
    # A medida nunca sai exata, e os dois desvios têm causa conhecida:
    # em máscara de traço, o contorno é a BORDA EXTERNA do risco dos dois
    # lados, então a altura sai alguns por cento a mais; em máscara de
    # preenchimento, os halos das cotas mordem a silhueta e a largura sai
    # um pouco a menos. Nos dois casos o desenho está certo e a leitura
    # tem viés de escala — então normalize cada eixo pela razão doc/medido
    # em vez de mexer nas âncoras.
    #
    # Erro grande (>4%) é outra coisa: aí é âncora errada de verdade — foi
    # o que aconteceu quando a banda lateral do 787 colou fuselagem com
    # estabilizador e a "cauda" saiu em 79 m. Nesse caso volte aos crops.
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
        "datum": "x=0 na ponta do nariz; z=0 no centro da secao constante",
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

    # amostra para conferir contra o desenho a olho
    for q in cfg.get("amostrar", [1, 2, 4, 8, 12]):
        i = int(np.argmin(np.abs(xm - q)))
        j = int(np.argmin(np.abs(xm_t - q)))
        print(f"x={q:6.1f}  crown={z_m_norm(crown_px[i]):+.2f}  "
              f"keel={z_m_norm(keel_px[i]):+.2f}  w/2={hw[j]*escala*ky:.2f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "config.json")
