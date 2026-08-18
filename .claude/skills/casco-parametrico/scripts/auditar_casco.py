"""Audits an aircraft's geometry against its spec, inside Blender.

Paste it into `execute_blender_code` and call `auditar("<aircraft folder>")`.

It runs three checks that catch different classes of defect:

1. **Cage vs spec, station by station.** Compares `max|y|`, crown and keel of
   each control ring against the spec. The expected result is `COMP` (1.0064)
   over the whole length. Where it is not, the error is in the CAGE — and this
   is the only way to tell that apart from subsurf shrinkage, which is the
   obvious suspect and almost always innocent. That is how a spurious 10.5%
   taper in the width of the 787-9 nose was found, one that no render revealed.

2. **Surface evaluated by raycast.** Confirms that what Cycles sees matches the
   spec after the subsurf.

3. **Detached parts.** Measures the gap between each hanging part and the
   surface that should be holding it. A flap track fairing floating 0.77 m below
   the wing was found this way.

None of these show up in a render — which is why running this after any rebuild
is worth more than one more camera angle.
"""
import json
import os

import bpy
import numpy as np
from mathutils import Vector

RAIZ = "/Users/sargam/Documents/Developer/Latam Airlines Model Planes"
COMP = 1.0064


def _estacoes(spec):
    """Normalizes the repository's two spec formats -> [(x, crown, keel, w2)]."""
    if "nariz_estacoes" in spec:                      # 787 format
        return [tuple(r) for r in spec["nariz_estacoes"] if len(r) >= 4]
    out = []                                          # A320 format (cavernas_nariz)
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
    # A ratio only makes sense when the reference value is not near zero: the
    # crown crosses z=0 in the nose and the ratio blows up there with no real
    # defect. Always judge by the error in METRES, with an absolute + relative
    # tolerance.
    def desvio(medido, esperado):
        erro = abs(medido - esperado * COMP)
        limite = max(0.02, tol_gaiola * abs(esperado))
        r = medido / esperado if abs(esperado) > 1e-6 else COMP
        return erro / limite, r          # >1 means out of tolerance

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
    # Raycasting "upwards" is no good: a gear leg is legitimately below the hull,
    # and a point INSIDE a closed mesh also returns a hit. The right test is the
    # sign of the distance to the closest point on the supporting surface:
    # negative = inside (attached), positive = gap.
    # Only the primary STRUCTURAL members, with the root declared explicitly.
    # Sub-parts (wheels, axles, torque links) attach to their own assembly, not
    # to the hull — checking them automatically only generates noise. And "the
    # root is the highest vertices" does not hold for the wing, whose top is the
    # TIP: hence each entry states which side the root is on.
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
