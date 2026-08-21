#!/usr/bin/env python3
"""Portas da familia A320 — a folha ASSENTADA no casco e o contorno em (x, w).

    /Applications/Blender.app/Contents/MacOS/Blender -b "<pasta>/<X>.blend" \
        --python "airbus A320neo/portas_familia.py" -- [medir|construir]

Este arquivo e o BUILDER DA FAMILIA para as portas, no mesmo papel que
`parabrisa_familia.py` e `asa_familia.py`. A implementacao de verdade — arco da
secao, assentamento da folha, caixa da folha e offset do poligono — mora em
`latam_livery_kit.py`, que e a UNICA copia: os builders das cinco aeronaves
passaram a chama-la.

------------------------------------------------------------------------------
O DEFEITO QUE ISTO CORRIGE — E O QUE ELE ESCONDIA
------------------------------------------------------------------------------
`door_ring()` estava copiado em CINCO builders (A320neo, A320ceo, A319, A321neo
e duas vezes na A321ceo) e nas cinco copias fazia a mesma coisa errada: tomava a
CAIXA (x, z) da folha e pintava `rounded_rect(Xg, Zg, ...)` — um retangulo na
PROJECAO LATERAL. E o mesmo defeito que o para-brisa teve (b28fa20), que o 777
teve (22500e6) e que o 767 teve duas vezes (f2f96cd, d401766): feature em casco
curvo se mede na superficie desenvolvida, nunca na projecao lateral, que achata
quem sobe o ombro.

Medido no topo da porta (15% superiores da folha), na A320neo:

    porta 1   anel velho |y| 0.832..1.417   anel novo |y| 1.286..1.417
    porta 2   anel velho |y| 0.505..1.184   anel novo |y| 1.059..1.184

Ao medir isso apareceu um SEGUNDO defeito, que o backlog nao tinha: a folha
tambem NAO esta na superficie. O raio normalizado da malha (t = 1 e o casco)
mede, nas CINCO aeronaves e em TODAS as portas pax:

    t 0.86 .. 1.22, mediana 1.11      -> no topo da porta 1 a folha esta em
                                         |y| 1.585 com o casco em 0.889

Causa: `build_a320neo_fix_geo.py` (e as receitas irmas na A319, A320ceo e
A321ceo) ERGUERAM as portas pax em z (+0.55 / +0.57, tabela de soleiras do ACAP
2-3-0) com uma TRANSLACAO PURA. Um painel que abraca o ombro, subido meio metro
em z, sai do casco — e nada reprojetou. As saidas overwing (t 0.998..1.015), as
portas de carga (0.992..1.035) e a fileira de janelas (1.007..1.018), que NAO
foram erguidas, continuam assentadas. Ou seja: o mesmo erro de classe do anel
pintado, so que na malha, e a "porta 1 fantasma" era a soma dos dois.

------------------------------------------------------------------------------
O METODO
------------------------------------------------------------------------------
1. ASSENTAR: cada folha pax volta ao casco por projecao RADIAL na secao,
   preservando (x, theta) — a pegada angular e o tamanho em arco nao mudam — e
   refazendo so o raio: superficie + 10 mm + o relevo proprio do painel (janela,
   manopla), que e o residuo de t contra uma tendencia suave em theta. A soleira
   fica onde o ACAP a poe; o TOPO desce (1.76 -> ~1.51 na porta 1), porque a
   altura de uma porta se mede na chapa, nao na projecao.
2. w = comprimento de ARCO da secao a partir da crista, integrado na PROPRIA
   tabela de aneis que a textura ja usa (elipse por estacao). Nao e theta*raio
   com um raio unico: o raio local varia entre 1.97 e 2.07 m nesta secao e um
   raio unico deixaria o anel ~5% torto no ombro.
3. A caixa da folha JA ASSENTADA sai da malha e vai para (x, w).
4. As bandas (FAR e sulco) sao offsets do poligono NESSE espaco metrico —
   dilatacao por bandas, que o 767 tentou, rasga as quinas em offsets grandes.
5. A repintura e CIRURGICA: reconstroi exatamente a mascara ANTIGA (mesma
   formula, mesmos parametros, caixa (x, z) de ANTES do assentamento), apaga so
   os texels que ela pintou, recompoe o fundo por difusao a partir da vizinhanca
   — assim o anel branco da porta 2, que vive DENTRO da cunha indigo, volta a
   indigo e nao a branco — e pinta a mascara nova com cobertura antialiasada
   (supersampling 3x nos dois eixos).
"""
import json
import math
import os
import sys

import bpy
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(BASE)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
import latam_livery_kit as kit  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODO = argv[0] if argv else "construir"

D = bpy.data
PASTA = os.path.dirname(os.path.abspath(bpy.data.filepath))
log = lambda *a: print("[portas]", *a)

# paleta unica da familia (identica nos cinco builders)
COR = {
    "branco": (0.969, 0.976, 0.980),
    "far": (0.624, 0.643, 0.663),
    "sulco": (0.098, 0.106, 0.114),
}

# ------------------------------------------------------- tabela por aeronave
# (L_UV, arquivo de aneis, [(objeto, cor da banda, band_w, cor do sulco,
#                            groove_w, lado, tem banda FAR)])
PAX = ("far", 0.05, "sulco", 0.010, True)
PAX_BRANCO = ("branco", 0.058, "branco", 0.010, True)
OVERWING = ("far", 0.03, "sulco", 0.008, False)
CARGA = ("far", 0.03, "sulco", 0.009, False)


def _lista(pares):
    out = []
    for nomes, par in pares:
        for n in nomes:
            lado = +1 if (n.endswith("_D") or not n.endswith("_E")) else -1
            out.append((n,) + par + (lado,))
    return out


FROTA = {
    "a320neo": (38.0, "a320neo_rings.json", _lista([
        (("Porta1_E", "Porta1_D"), PAX),
        (("Porta2_E", "Porta2_D"), PAX_BRANCO),
        (("Overwing1_E", "Overwing2_E", "Overwing1_D", "Overwing2_D"), OVERWING),
        (("PortaCargaFwd", "PortaCargaAft", "PortaCargaBulk"), CARGA)])),
    "a320ceo": (38.0, "a320ceo_rings.json", _lista([
        (("Porta1_E", "Porta1_D"), PAX),
        (("Porta2_E", "Porta2_D"), PAX_BRANCO),
        (("Overwing1_E", "Overwing2_E", "Overwing1_D", "Overwing2_D"), OVERWING),
        (("PortaCargaFwd", "PortaCargaAft", "PortaCargaBulk"), CARGA)])),
    "a319": (34.2, "a319_rings.json", _lista([
        (("Porta1_E", "Porta1_D"), PAX),
        (("Porta2_E", "Porta2_D"), PAX_BRANCO),
        (("Overwing1_E", "Overwing1_D"), OVERWING),
        (("PortaCargaFwd", "PortaCargaAft", "PortaCargaBulk"), CARGA)])),
    "a321neo": (45.0, "a321_rings.json", _lista([
        (("Porta1_E", "Porta1_D"), PAX),
        (("Porta3_E", "Porta3_D"), PAX),
        (("Porta2_E", "Porta2_D"), PAX_BRANCO)])),
    "a321ceo": (45.0, "a321ceo_rings.json", _lista([
        (("Porta1_E", "Porta1_D"), PAX),
        (("Porta2_E", "Porta2_D"), PAX),
        (("Porta3_E", "Porta3_D"), PAX),
        (("Porta4_E", "Porta4_D"), PAX_BRANCO)])),
}

CHAVE = os.path.basename(PASTA).split()[-1].lower()      # "airbus A320neo" -> a320neo
if CHAVE not in FROTA:
    raise RuntimeError("pasta %s nao esta na tabela (%s)" % (PASTA, list(FROTA)))
L_UV, ANEIS_JSON, PORTAS = FROTA[CHAVE]
log("aeronave %s  L_UV %.1f  %d portas" % (CHAVE, L_UV, len(PORTAS)))

# ------------------------------------------------------------------ textura
imT = D.images["LiveryTex"]
imF = D.images["LiveryFac"]
W, H = imT.size
rgb = np.array(imT.pixels[:], np.float32).reshape(H, W, 4)
fac = np.array(imF.pixels[:], np.float32).reshape(H, W, 4)

rings = json.load(open(os.path.join(PASTA, ANEIS_JSON)))
rx = np.array([r["x"] for r in rings])
rzc = np.array([r["zc"] for r in rings])
rrz = np.array([r["rz"] for r in rings])
rry = np.array([r["ry"] for r in rings])

SS = 3                                   # supersampling da cobertura
RAIO = 0.15                              # raio das quinas, em metros


def janela(x0, x1, folga):
    """Faixa de COLUNAS da textura que cobre [x0-folga, x1+folga]."""
    c0 = max(0, int(math.floor((x0 - folga) / L_UV * W)) - 1)
    c1 = min(W, int(math.ceil((x1 + folga) / L_UV * W)) + 2)
    return c0, c1


def grades(c0, c1):
    """Grades supersampled da janela: X, TH, Z, Y, W(arco) e a forma."""
    nc = (c1 - c0) * SS
    nr = H * SS
    u = (np.arange(nc) + 0.5) / (W * SS) + c0 / float(W)
    v = (np.arange(nr) + 0.5) / nr
    X = u * L_UV
    TH = v * 2 * math.pi - math.pi
    Xg = np.broadcast_to(X, (nr, nc))
    THg = np.broadcast_to(TH[:, None], (nr, nc))
    ZCg = np.interp(X, rx, rzc)[None, :]
    RZg = np.interp(X, rx, rrz)[None, :]
    RYg = np.interp(X, rx, rry)[None, :]
    Zg = ZCg + RZg * np.cos(THg)
    Yg = RYg * np.sin(THg)
    Wg = kit.grade_arco(rx, rrz, rry, X, TH)
    return Xg, THg, Zg, Yg, Wg


def ret_arred(A, B, a0, a1, b0, b1, r):
    ia0, ia1, ib0, ib1 = a0 + r, a1 - r, b0 + r, b1 - r
    da = np.maximum(np.maximum(ia0 - A, A - ia1), 0)
    db = np.maximum(np.maximum(ib0 - B, B - ib1), 0)
    return np.hypot(da, db) <= r


def reduz(m):
    """Mascara supersampled -> cobertura por texel (nr/SS, nc/SS)."""
    nr, nc = m.shape
    return m.reshape(nr // SS, SS, nc // SS, SS).mean(axis=(1, 3))


def difunde(base_rgb, base_fac, valido, n=48):
    """Recompoe o fundo dos texels apagados a partir da vizinhanca valida.

    Isso e o que evita ter de saber, por aeronave, se debaixo do anel havia
    branco ou a cunha indigo: o fundo se le do proprio entorno.
    """
    r = base_rgb.copy()
    f = base_fac.copy()
    v = valido.copy()
    for _ in range(n):
        if v.all():
            break
        soma_r = np.zeros_like(r)
        soma_f = np.zeros_like(f)
        cnt = np.zeros(v.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            vs = np.roll(v, (dy, dx), (0, 1))
            rs = np.roll(r, (dy, dx), (0, 1))
            fs = np.roll(f, (dy, dx), (0, 1))
            soma_r += rs * vs[..., None]
            soma_f += fs * vs[..., None]
            cnt += vs
        novo = (~v) & (cnt > 0)
        if not novo.any():
            break
        r[novo] = soma_r[novo] / cnt[novo][:, None]
        f[novo] = soma_f[novo] / cnt[novo][:, None]
        v |= novo
    return r, f


# --------------------------------------------------- 1. assentar as folhas
# t = raio normalizado da secao (1.0 = casco). Acima de 1.03 a folha esta fora
# do casco e foi erguida sem reprojetar; abaixo disso ja esta assentada e nao se
# mexe (overwing, cargas, janelas).
LIMITE_T = 1.03
SALIENCIA = 0.010

# caixa (x, z) de ANTES: e a que os builders usaram para pintar o anel velho, e
# e ela que precisa ser reproduzida para apagar exatamente aqueles texels.
CAIXA_Z_ORIG = {}
for _n, *_ in PORTAS:
    _o = D.objects.get(_n)
    if _o is None:
        continue
    _P = np.array([(_o.matrix_world @ v.co)[:] for v in _o.data.vertices], float)
    CAIXA_Z_ORIG[_n] = (_P[:, 2].min(), _P[:, 2].max())

for nome, *_ in PORTAS:
    ob = D.objects.get(nome)
    if ob is None:
        continue
    P = np.array([(ob.matrix_world @ v.co)[:] for v in ob.data.vertices], float)
    zc = np.interp(P[:, 0], rx, rzc)
    rz = np.interp(P[:, 0], rx, rrz)
    ry = np.interp(P[:, 0], rx, rry)
    t = np.hypot(P[:, 1] / ry, (P[:, 2] - zc) / rz)
    if abs(np.median(t) - 1.0) <= LIMITE_T - 1.0:
        log("%-15s ja assentada (t %.3f..%.3f, mediana %.3f)"
            % (nome, t.min(), t.max(), np.median(t)))
        continue
    if MODO == "medir":
        log("%-15s FORA DO CASCO: t %.3f..%.3f mediana %.3f  z %.2f..%.2f"
            % (nome, t.min(), t.max(), np.median(t), P[:, 2].min(), P[:, 2].max()))
        continue
    ta, tb = kit.assentar_na_secao(ob, rx, rzc, rrz, rry, SALIENCIA)
    Q = np.array([(ob.matrix_world @ v.co)[:] for v in ob.data.vertices], float)
    zc2 = np.interp(Q[:, 0], rx, rzc)
    rz2 = np.interp(Q[:, 0], rx, rrz)
    ry2 = np.interp(Q[:, 0], rx, rry)
    t2 = np.hypot(Q[:, 1] / ry2, (Q[:, 2] - zc2) / rz2)
    log("%-15s assentada: t %.3f..%.3f (med %.3f) -> %.3f..%.3f (med %.3f) ; "
        "z %.2f..%.2f -> %.2f..%.2f"
        % (nome, t.min(), t.max(), ta, t2.min(), t2.max(), tb,
           P[:, 2].min(), P[:, 2].max(), Q[:, 2].min(), Q[:, 2].max()))

# ------------------------------------------------------ 2. aneis na textura
relatorio = []
APAGAR = np.zeros((H, W), bool)
PINTURA = []
for nome, cor_b, band_w, cor_s, groove_w, far_band, lado in PORTAS:
    ob = D.objects.get(nome)
    if ob is None:
        log("ausente:", nome)
        continue
    # a caixa (x, z) do anel ANTIGO tem de ser a de ANTES do assentamento: e ela
    # que os builders usaram e e ela que se apaga.
    P = np.array([(ob.matrix_world @ v.co)[:] for v in ob.data.vertices], float)
    x0, x1 = P[:, 0].min(), P[:, 0].max()
    z0, z1 = CAIXA_Z_ORIG.get(nome, (P[:, 2].min(), P[:, 2].max()))
    cx = kit.caixa_porta_xw(ob, rx, rzc, rrz, rry)
    folga = max(band_w, groove_w) + RAIO + 0.40
    c0, c1 = janela(x0, x1, folga)
    Xg, THg, Zg, Yg, Wg = grades(c0, c1)
    sideok = ((Yg < 0) if lado < 0 else (Yg > 0)) & (np.abs(np.sin(THg)) > 0.25)

    # --- mascara ANTIGA, reproduzida ao pe da letra
    dentro_o = ret_arred(Xg, Zg, x0, x1, z0, z1, RAIO)
    banda_o = ret_arred(Xg, Zg, x0 - band_w, x1 + band_w,
                        z0 - band_w, z1 + band_w, RAIO) & ~dentro_o
    sulco_o = dentro_o & ~ret_arred(Xg, Zg, x0 + groove_w, x1 - groove_w,
                                    z0 + groove_w, z1 - groove_w, RAIO)
    velha = sulco_o & sideok
    if far_band:
        velha = velha | (banda_o & sideok)

    # --- mascara NOVA, na superficie
    banda_n, sulco_n = kit.anel_porta(Xg, Wg, cx, band_w, groove_w, RAIO)
    banda_n &= sideok
    sulco_n &= sideok

    # divergencia medida no topo da porta (a metrica do backlog)
    alto = Zg > (z0 + 0.85 * (z1 - z0))
    dy_v = np.abs(Yg[velha & alto]) if (velha & alto).any() else np.array([np.nan])
    dy_n = np.abs(Yg[(sulco_n | banda_n) & alto]) if ((sulco_n | banda_n) & alto).any() \
        else np.array([np.nan])
    relatorio.append((nome, x0, x1, z0, z1, cx[2], cx[3],
                      float(np.nanmin(dy_v)), float(np.nanmax(dy_v)),
                      float(np.nanmin(dy_n)), float(np.nanmax(dy_n))))
    log("%-15s x %6.2f..%6.2f  z %6.2f..%6.2f  w %6.3f..%6.3f | "
        "no topo: anel velho |y| %.3f..%.3f, novo |y| %.3f..%.3f"
        % relatorio[-1])

    if MODO == "medir":
        continue

    cov_velha = reduz(velha)
    cov_b = reduz(banda_n) if far_band else np.zeros_like(cov_velha)
    cov_s = reduz(sulco_n)

    # RESIDUO DE RODADAS ANTERIORES. Reproduzir a mascara antiga apaga o anel que
    # o builder atual pintou, mas nao o que sobrou dos anteriores: quando as
    # portas foram ERGUIDAS (+0.55 / +0.57), a limpeza da rodada de livery so
    # apagava texels claros (`is_ring = fac > 0.05 AND R > 0.55`), e a LINHA
    # ESCURA do sulco do anel antigo — R = 0.098 — passou ilesa. Ela e o contorno
    # fino que ficava 0.42 m de arco abaixo da porta, e e ela que se ve nos
    # renders como "porta fantasma", nao a banda cinza.
    # Varre-se entao a vizinhanca da porta atras de qualquer tinta de ANEL: cor
    # de banda FAR ou de sulco, com fac ALTO (1.0). O fac alto e o que separa a
    # tinta de anel da sujeira do ventre, que e cinza-escura parecida mas entra
    # com fac 0.10-0.22.
    reg = ((Xg >= x0 - 0.25) & (Xg <= x1 + 0.25)
           & (Wg >= cx[2] - 1.2) & (Wg <= cx[3] + 1.2) & sideok)
    cov_reg = reduz(reg) > 0.5

    sub_rgb = rgb[:, c0:c1, :3]
    sub_fac = fac[:, c0:c1, :3]
    # O teste nao e "e exatamente a cor do sulco": as bordas do anel antigo sao
    # ANTIALIASADAS e vivem na rampa entre o branco e o sulco. O que caracteriza
    # tinta de anel e ser ACROMATICA, mais escura que o branco e ter fac alto —
    # e isso exclui a sujeira do ventre (acromatica e escura, mas fac 0.10-0.22),
    # o titulo em navy e o coral (cromaticos) e a cunha indigo (cromatica).
    mx = sub_rgb.max(axis=2)
    mn = sub_rgb.min(axis=2)
    tinta = (mx < 0.94) & ((mx - mn) < 0.10)
    residuo = cov_reg & tinta & (sub_fac[..., 0] > 0.3)
    apagar = ((cov_velha > 0.02) | residuo) & (cov_b + cov_s < 0.98)
    # APAGAR TUDO ANTES DE PINTAR QUALQUER COISA. As duas saidas overwing ficam a
    # 0.23 m uma da outra e a varredura de residuo de uma alcanca o anel da
    # outra; apagar e pintar porta a porta comia a borda do anel recem-pintado do
    # vizinho.
    APAGAR[:, c0:c1] |= apagar
    PINTURA.append((c0, c1, cov_b, COR[cor_b], cov_s, COR[cor_s], nome))
    log("   a apagar %d texels; a pintar %d (banda) + %d (sulco)"
        % (int(apagar.sum()), int((cov_b > 0.02).sum()), int((cov_s > 0.02).sum())))

if MODO == "medir":
    raise SystemExit(0)

if APAGAR.any():
    log("difusao do fundo em %d texels" % int(APAGAR.sum()))
    rgb[..., :3], fac[..., :3] = difunde(rgb[..., :3], fac[..., :3], ~APAGAR, n=32)

for c0, c1, cov_b, cor_b, cov_s, cor_s, nome in PINTURA:
    sub_rgb = rgb[:, c0:c1, :3]
    sub_fac = fac[:, c0:c1, :3]
    for cov, cor in ((cov_b, cor_b), (cov_s, cor_s)):
        if not cov.any():
            continue
        a = cov[..., None]
        sub_rgb[...] = sub_rgb * (1 - a) + np.array(cor, np.float32) * a
        sub_fac[...] = sub_fac * (1 - a) + a

imT.pixels.foreach_set(rgb.ravel())
imT.pack()
imF.pixels.foreach_set(fac.ravel())
imF.pack()
bpy.ops.wm.save_mainfile()
log("SALVO", bpy.data.filepath)
