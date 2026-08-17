"""Pinta marcações na textura UV (x,θ) do casco a partir de uma lista de itens.

Roda dentro do Blender (cole em `execute_blender_code`, ou importe). Serve para
tudo que é retangular ou faixa: antenas, drenos, portas de poço, marcações
operacionais e manchas de weathering. Marca com desenho próprio (logotipo,
matrícula) continua vindo de mesh rasterizado — ver o SKILL.md.

Cada item é um dict:

    {"nome": "dreno fwd", "tipo": "dreno",
     "x_m": [8.4, 8.7],          # faixa longitudinal (obrigatório)
     "z_m": [-2.9, -2.6],        # faixa vertical  — use um OU outro
     "y_m": [],                  # faixa lateral
     "cor_hex": "#2A2C2E",
     "lados": "ambos",           # esquerdo | direito | ambos | barriga
     "intensidade": 1.0}         # 1 = opaco; weathering fica em 0.08-0.35

O acoplamento com a seção do casco faz o resto: um item definido por z aparece
onde aquela altura existir, e um definido por y idem. Weathering com
intensidade fracionária tinge sem cobrir, que é como sujeira se comporta.
"""
import json
import math

import bpy
import numpy as np

SS = 2                      # supersample; 2 basta para faixas, 4 para bordas finas


def _srgb(hx):
    hx = hx.lstrip("#")
    return tuple(int(hx[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def perfil_do_spec(spec):
    """Arrays (x, zc, rz, ry) cobrindo nariz + barril + cauda."""
    nz = np.array(spec["nariz_estacoes"], float)
    cd = np.array(spec["cauda"], float)
    PX = list(nz[:, 0]); PZC = list((nz[:, 1] + nz[:, 2]) / 2)
    PRZ = list((nz[:, 1] - nz[:, 2]) / 2); PRY = list(nz[:, 3])
    x_bar0, x_bar1 = nz[-1, 0], cd[0, 0]
    rz_b = (nz[-1, 1] - nz[-1, 2]) / 2
    ry_b = nz[-1, 3]
    n = max(1, int((x_bar1 - x_bar0) / 4))
    for i in range(1, n + 1):
        PX.append(x_bar0 + i * (x_bar1 - x_bar0) / n)
        PZC.append(0.0); PRZ.append(rz_b); PRY.append(ry_b)
    for x, zc, r in cd:
        PX.append(x); PZC.append(zc); PRZ.append(r); PRY.append(0.96 * r)
    o = np.argsort(PX)
    return [np.array(a)[o] for a in (PX, PZC, PRZ, PRY)]


def pintar(itens, spec, comprimento_uv, tex="LiveryTex", fac="LiveryFac",
           margem=1.0, verbose=True):
    """Compõe os itens sobre a livery existente. Não apaga o que já está lá."""
    PX, PZC, PRZ, PRY = perfil_do_spec(spec)
    imT, imF = bpy.data.images[tex], bpy.data.images[fac]
    W, H = imT.size
    T = np.array(imT.pixels[:], np.float32).reshape(H, W, 4)
    F = np.array(imF.pixels[:], np.float32).reshape(H, W, 4)

    xs_all = [v for it in itens for v in it["x_m"]]
    x0 = max(0.0, min(xs_all) - margem)
    x1 = min(comprimento_uv, max(xs_all) + margem)
    i0, i1 = int(x0 / comprimento_uv * W), min(W, int(x1 / comprimento_uv * W) + 1)
    j0, j1 = 0, H                       # v inteiro: itens de barriga cruzam a costura
    w, h = (i1 - i0) * SS, (j1 - j0) * SS

    xs = (np.arange(w) + 0.5) / SS / W * comprimento_uv + i0 / W * comprimento_uv
    vv = (np.arange(h) + 0.5) / SS / H
    zc = np.interp(xs, PX, PZC); rz = np.interp(xs, PX, PRZ); ry = np.interp(xs, PX, PRY)
    TH = (2 * math.pi * vv - math.pi)[:, None]
    thb = np.arctan2(rz[None, :] * np.sin(TH), ry[None, :] * np.cos(TH))
    Y = ry[None, :] * np.sin(thb)
    Z = zc[None, :] + rz[None, :] * np.cos(thb)
    X = np.broadcast_to(xs[None, :], (h, w))

    def down(m):
        return m.reshape(h // SS, SS, w // SS, SS).mean(axis=(1, 3)).astype(np.float32)

    subT = T[j0:j1, i0:i1, :3]
    subF = F[j0:j1, i0:i1, 0]
    total = 0
    for it in itens:
        m = (X >= it["x_m"][0]) & (X <= it["x_m"][1])
        if it.get("z_m"):
            m &= (Z >= min(it["z_m"])) & (Z <= max(it["z_m"]))
        if it.get("y_m"):
            a, b = min(it["y_m"]), max(it["y_m"])
            m &= (np.abs(Y) >= a) & (np.abs(Y) <= b) if a >= 0 else (Y >= a) & (Y <= b)
        lado = it.get("lados", "ambos")
        if lado.startswith("esq"):
            m &= Y < 0
        elif lado.startswith("dir"):
            m &= Y > 0
        elif lado.startswith("barr"):
            m &= Z < zc[None, :] - 0.55 * rz[None, :]
        if not m.any():
            if verbose:
                print(f"  [vazio] {it['nome']} — faixa nao intercepta a superficie")
            continue
        cov = down(m) * float(it.get("intensidade", 1.0))
        cor = _srgb(it["cor_hex"])
        for k in range(3):
            subT[:, :, k] = subT[:, :, k] * (1 - cov) + cor[k] * cov
        subF[:] = np.maximum(subF, cov)
        total += float(cov.sum())
        if verbose:
            print(f"  {it['nome']:34} {float(cov.sum()):8.0f} px-eq  ({it.get('tipo','-')})")

    T[j0:j1, i0:i1, :3] = subT
    for k in range(3):
        F[j0:j1, i0:i1, k] = subF
    imT.pixels = T.ravel().tolist(); imT.pack()
    imF.pixels = F.ravel().tolist(); imF.pack()
    print(f"total pintado: {total:.0f} px-eq em {len(itens)} itens")
    return total
