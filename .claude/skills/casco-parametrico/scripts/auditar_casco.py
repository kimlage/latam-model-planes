"""Audita a geometria de uma aeronave contra o seu spec, dentro do Blender.

Cole em `execute_blender_code` e chame `auditar("<pasta da aeronave>")`.

Faz três checagens que pegam classes diferentes de defeito:

1. **Gaiola vs spec, estação por estação.** Compara `max|y|`, crown e keel de
   cada anel de controle com o spec. O resultado esperado é `COMP` (1.0064) em
   toda a extensão. Onde não for, o erro está na GAIOLA — e essa é a única
   forma de distinguir isso de encolhimento do subsurf, que é o suspeito óbvio
   e quase sempre inocente. Foi assim que se achou um afilamento espúrio de
   10,5% na largura do nariz do 787-9 que nenhum render denunciava.

2. **Superfície avaliada por raycast.** Confirma que o que o Cycles vê bate com
   o spec depois do subsurf.

3. **Peças soltas.** Mede a folga entre cada peça pendurada e a superfície que
   deveria segurá-la. Carenagem de trilho de flap flutuando 0,77 m abaixo da
   asa foi achada assim.

Nenhuma delas aparece num render — por isso rodar isto depois de qualquer
reconstrução vale mais do que mais um ângulo de câmera.
"""
import json
import os

import bpy
import numpy as np
from mathutils import Vector

RAIZ = "/Users/sargam/Documents/Developer/Latam Airlines Model Planes"
COMP = 1.0064


def _estacoes(spec):
    """Normaliza os dois formatos de spec do repositorio -> [(x, crown, keel, w2)]."""
    if "nariz_estacoes" in spec:                      # formato 787
        return [tuple(r) for r in spec["nariz_estacoes"] if len(r) >= 4]
    out = []                                          # formato A320 (cavernas_nariz)
    for c in spec.get("cavernas_nariz", []):
        if all(k in c for k in ("x", "crown", "keel", "W")):
            out.append((c["x"], c["crown"], c["keel"], c["W"] / 2.0))
    return out


def auditar(pasta, obj="Fuselagem", tol_gaiola=0.02, tol_sup=0.06):
    caminho = os.path.join(RAIZ, pasta)
    spec = None
    for f in os.listdir(caminho):
        if f.startswith("spec_") and f.endswith(".json"):
            spec = json.load(open(os.path.join(caminho, f)))
            print(f"spec: {f}")
            break
    if spec is None:
        print("!! nenhum spec_*.json em", pasta); return
    est = _estacoes(spec)
    if not est:
        print("!! spec sem estacoes de nariz utilizaveis"); return

    fus = bpy.data.objects[obj]
    V = np.array([[v.co.x, v.co.y, v.co.z] for v in fus.data.vertices])

    print(f"\n--- 1) gaiola vs spec (esperado {COMP:.4f} em tudo) ---")
    # Razao so faz sentido quando o valor de referencia nao e quase zero: o crown
    # cruza z=0 no nariz e la a razao explode sem nenhum defeito real. Julgue
    # sempre pelo erro em METROS, com tolerancia absoluta + relativa.
    def desvio(medido, esperado):
        erro = abs(medido - esperado * COMP)
        limite = max(0.02, tol_gaiola * abs(esperado))
        r = medido / esperado if abs(esperado) > 1e-6 else COMP
        return erro / limite, r          # >1 significa fora

    ruins = []
    for x, cr, kl, w2 in est:
        sel = np.abs(V[:, 0] - x) < 1e-3
        if sel.sum() == 0 or w2 <= 1e-6:
            continue
        dy, rz_y = desvio(np.abs(V[sel, 1]).max(), w2)
        dc, rz_c = desvio(V[sel, 2].max(), cr)
        dk, rz_k = desvio(V[sel, 2].min(), kl)
        pior = max(dy, dc, dk)
        if pior > 1.0:
            ruins.append((x, rz_y, rz_c, rz_k))
        print(f"  x={x:6.2f}  larg {rz_y:.4f}  crown {rz_c:.4f}  keel {rz_k:.4f}"
              f"{'   <-- FORA' if pior > 1.0 else ''}")
    if ruins:
        r = np.array([t[1] for t in ruins]); xs = np.array([t[0] for t in ruins])
        print(f"  !! {len(ruins)} estacoes fora. Razao de largura vai de {r.min():.3f} a {r.max():.3f}")
        if len(ruins) > 2 and np.corrcoef(xs, r)[0, 1] > 0.9:
            print("  !! a razao cresce linearmente com x — sinal classico de afilamento espurio")
    else:
        print("  gaiola OK")

    print("\n--- 2) superficie avaliada (raycast) ---")
    ev = fus.evaluated_get(bpy.context.evaluated_depsgraph_get())
    erros = []
    for x, cr, kl, w2 in est:
        if w2 <= 0.05:
            continue
        hit, loc, _, _ = ev.ray_cast(Vector((x, -50, (cr + kl) / 2)), Vector((0, 1, 0)))[:4]
        if hit:
            erros.append((abs(abs(loc.y) - w2), x, w2, abs(loc.y)))
    erros.sort(reverse=True)
    for e, x, s_, m_ in erros[:4]:
        print(f"  x={x:6.2f}  spec {s_:.3f}  medido {m_:.3f}  erro {m_-s_:+.3f}"
              f"{'   <-- FORA' if e > tol_sup else ''}")
    if erros:
        med = np.median([e[0] for e in erros])
        print(f"  erro mediano {med*100:.1f} cm | maximo {erros[0][0]*100:.1f} cm")

    print("\n--- 3) pecas soltas (a raiz penetra a peca de apoio?) ---")
    # Raycast "para cima" nao serve: uma perna de trem esta legitimamente abaixo
    # do casco, e um ponto DENTRO de uma malha fechada tambem devolve um hit.
    # O teste certo e o sinal da distancia ao ponto mais proximo da superficie
    # de apoio: negativo = dentro (preso), positivo = folga.
    # So os membros ESTRUTURAIS primarios, com a raiz declarada explicitamente.
    # Sub-pecas (rodas, eixos, tesouras) prendem no proprio conjunto, nao no
    # casco — checa-las automaticamente so gera ruido. E "raiz = vertices mais
    # altos" nao vale para a asa, cujo topo e a PONTA: por isso cada entrada diz
    # de que lado fica a raiz.
    LIGACOES = [
        ("Asas",               obj,                "y_min"),
        ("Deriva",             obj,                "z_min"),
        ("EstabHorizontal",    obj,                "y_min"),
        ("BellyFairing",       obj,                "z_max"),
        ("FlapFairing{L}{i}",  "Asas",             "z_max"),
        ("Motor_Pylon_{L}",    "Asas",             "z_max"),
        ("Motor_Nacelle_{L}",  "Motor_Pylon_{L}",  "z_max"),
        ("TremNariz_Cilindro", obj,                "z_max"),
        ("TremP_Cilindro{L}",  "Asas",             "z_max"),
    ]
    def raiz(W, modo):
        if modo == "y_min":  idx = np.argsort(np.abs(W[:, 1]))
        elif modo == "z_min": idx = np.argsort(W[:, 2])
        else:                 idx = np.argsort(-W[:, 2])
        return W[idx[:25]]

    dg2 = bpy.context.evaluated_depsgraph_get()
    achou = False
    for padrao, paip, modo in LIGACOES:
        nomes = []
        if "{L}" in padrao:
            for L in ("E", "D"):
                nomes += ([padrao.format(L=L, i=i) for i in range(4)]
                          if "{i}" in padrao else [padrao.format(L=L)])
        else:
            nomes = [padrao]
        for n in nomes:
            o = bpy.data.objects.get(n)
            if not o or o.type != 'MESH':
                continue
            L = "E" if n.endswith("E") or "E" in n[-2:] else "D"
            pai = bpy.data.objects.get(paip.format(L=L))
            if not pai:
                continue
            alvo = pai.evaluated_get(dg2)
            W = np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices])
            melhor = 1e9
            for p in raiz(W, modo):
                ok, loc, nor, _ = alvo.closest_point_on_mesh(Vector(p))[:4]
                if ok:
                    melhor = min(melhor, (Vector(p) - loc).dot(nor))
            marca = "" if melhor <= 0.05 else f"  -> FOLGA {melhor:.2f} m"
            if marca:
                achou = True
            print(f"  {n:24} -> {pai.name:18} penetra {-melhor:+.2f} m{marca}")
    if not achou:
        print("  todas as raizes penetram a peca de apoio")
    print("\naudit concluido")
