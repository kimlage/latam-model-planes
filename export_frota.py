#!/usr/bin/env python3
"""Exporta a frota para fora do Blender - GLB, USDZ, FBX, OBJ.

    python3 export_frota.py                    # frota inteira, os dois LODs
    python3 export_frota.py B77W A320neo       # so estas
    python3 export_frota.py --lod web          # so o nivel leve
    python3 export_frota.py --verificar        # nao exporta: so le de volta

Este e o unico script de exportacao na raiz, no mesmo papel que `render_gate.py`
tem para o gate visual: um driver fino. A regra vive em
[`export/frota_portatil.py`](export/frota_portatil.py), que roda DENTRO do
Blender; a leitura de volta vive em
[`export/verificar_glb.py`](export/verificar_glb.py), que roda em Python puro.

O driver abre um Blender por (aeronave, LOD). Isso e mais lento do que um
processo so, e e deliberado: cada master e aberto limpo com --factory-startup, e
uma aeronave que falhe - por estar sendo editada por outra sessao - nao derruba
as outras. Os .blend NUNCA sao gravados.

VERIFICAR NAO E OPCIONAL. Um arquivo que existe nao e um arquivo que carrega:
todo .glb escrito e reaberto no nivel do byte e conferido contra a medida da
propria aeronave - triangulos, materiais, texturas embutidas, NaN, e a caixa
envolvente contra o comprimento publicado. O manifesto (`export/manifest.json`)
guarda os numeros medidos, nao os esperados.
"""
import argparse
import json
import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(RAIZ, "export")
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")

sys.path.insert(0, PASTA)
import verificar_glb  # noqa: E402

# A tabela da frota e dos LODs mora do lado do Blender. Le-la aqui sem importar
# `bpy` mantem UMA fonte de verdade: o driver nao repete a lista.
_MOD = os.path.join(PASTA, "frota_portatil.py")


def _tabelas():
    """FROTA e LODS lidos de frota_portatil.py sem importar bpy."""
    fonte = open(_MOD).read()
    ns = {}
    import ast
    arv = ast.parse(fonte)
    for no in arv.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1 \
                and isinstance(no.targets[0], ast.Name) \
                and no.targets[0].id in ("FROTA", "LODS"):
            ns[no.targets[0].id] = ast.literal_eval(no.value)
    return ns["FROTA"], ns["LODS"]


FROTA, LODS = _tabelas()


# ------------------------------------------------------------------ exportacao

def exportar(slug, lod, verboso=False):
    """Um Blender headless por (aeronave, LOD). Devolve o relatorio ou o erro."""
    d = FROTA[slug]
    blend = os.path.join(RAIZ, d["pasta"], d["blend"])
    if not os.path.exists(blend):
        return {"slug": slug, "lod": lod, "erro": "master ausente: %s" % blend,
                "opcional": d.get("opcional", False)}
    rel_json = os.path.join(PASTA, ".rel_%s_%s.json" % (slug, lod))
    if os.path.exists(rel_json):
        os.remove(rel_json)
    cmd = [BLENDER, "-b", blend, "--factory-startup", "--python", _MOD, "--",
           "--lod", lod, "--saida", PASTA, "--relatorio", rel_json]
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t
    if not os.path.exists(rel_json):
        cauda = "\n".join((p.stdout + p.stderr).strip().splitlines()[-12:])
        return {"slug": slug, "lod": lod, "erro": "Blender nao produziu relatorio",
                "codigo": p.returncode, "cauda": cauda,
                "opcional": d.get("opcional", False)}
    with open(rel_json) as f:
        rel = json.load(f)
    os.remove(rel_json)
    rel["segundos"] = round(dt, 1)
    if verboso:
        print(p.stdout)
    return rel


# ----------------------------------------------------------------- verificacao

def verificar(rel):
    """Le de volta cada .glb do relatorio e confronta com a medida da aeronave.

    Tres checagens que so um leitor independente pode fazer:

      geometria  os triangulos do .glb batem com os que o Blender avaliou
      eixo       X = comprimento, Y = altura, Z = envergadura, em metros, e
                 o comprimento bate com o publicado
      chao       a menor cota Y e ~0: a aeronave pousa no plano do visualizador
    """
    saidas = rel.get("saidas", {})
    if "glb" not in saidas:
        return
    caminho = os.path.join(PASTA, saidas["glb"]["arquivo"])
    try:
        v = verificar_glb.inspecionar(caminho)
    except verificar_glb.GLBError as exc:
        rel["verificacao"] = {"ok": False, "erros": ["container: %s" % exc]}
        return
    erros = list(v["erros"])
    avisos = list(v["avisos"])

    # UM no raiz. Um segundo no raiz e a assinatura de uma peca que escapou do
    # deslocamento de datum e ficou boiando fora do chao - foi assim que o
    # `RegPortaTrem` das cinco Airbus apareceu 2,4 m abaixo da pista.
    if v["n_raizes_da_cena"] != 1:
        erros.append("%d nos raiz na cena, esperado 1 (a aeronave)"
                     % v["n_raizes_da_cena"])

    tb = rel.get("triangulos_blender")
    if tb and abs(v["triangulos"] - tb) > max(4, tb * 0.001):
        erros.append("triangulos %d no .glb x %d avaliados no Blender"
                     % (v["triangulos"], tb))

    caixa = v["caixa"]
    if caixa:
        cx, cy, cz = caixa["tamanho"]
        L = rel.get("medidas", {}).get("L") or rel["L_ref"]
        if not (cx > cy and cx > cz * 0.45):
            erros.append("eixo: X=%.2f nao e o comprimento (Y=%.2f Z=%.2f)"
                         % (cx, cy, cz))
        if abs(cx - rel["L_ref"]) > 0.6:
            erros.append("comprimento %.2f m no .glb x %.2f m publicado"
                         % (cx, rel["L_ref"]))
        if abs(cx - L) > 0.02:
            avisos.append("comprimento %.3f m x %.3f m medido no Blender" % (cx, L))
        if abs(caixa["min"][1]) > 0.05:
            avisos.append("piso em Y=%.3f m, esperado 0" % caixa["min"][1])
        if abs(caixa["min"][2] + caixa["max"][2]) > 0.05:
            avisos.append("envergadura assimetrica em Z: %.3f .. %.3f"
                          % (caixa["min"][2], caixa["max"][2]))
    if v["n_imagens"] == 0 and rel.get("bake"):
        erros.append("nenhuma textura embutida, mas houve bake")

    rel["verificacao"] = {
        "ok": not erros, "erros": erros, "avisos": avisos,
        "triangulos": v["triangulos"], "vertices": v["vertices"],
        "materiais": v["n_materiais"], "materiais_clearcoat": v["materiais_com_clearcoat"],
        "imagens": v["n_imagens"], "megapixels": v["megapixels"],
        "bytes_imagens": v["bytes_imagens"], "caixa": caixa,
        "extensoes": v["extensoes"], "draco": v["draco"], "nos": v["n_nos"],
        "raizes_da_cena": v["n_raizes_da_cena"],
        "gerador": v["gerador"],
    }


# ----------------------------------------------------------------- reimportacao

_REIMP = os.path.join(PASTA, "reimportar.py")


def reimportar(rel):
    """Abre cada saida num Blender vazio e mede o que voltou.

    O leitor de GLB nao serve para USDZ, FBX e OBJ, e um eixo errado nao aparece
    em nenhuma contagem - so na caixa envolvente do arquivo REABERTO. Devolve uma
    linha por formato, com os numeros medidos na volta.
    """
    arquivos = [os.path.join(PASTA, d["arquivo"])
                for d in rel.get("saidas", {}).values()]
    arquivos = [a for a in arquivos if os.path.exists(a)]
    if not arquivos:
        return []
    p = subprocess.run([BLENDER, "-b", "--factory-startup", "--python", _REIMP,
                        "--"] + arquivos, capture_output=True, text=True)
    linhas = [l for l in (p.stdout + p.stderr).splitlines()
              if l.startswith("ROUNDTRIP")]
    rel["reimportacao"] = linhas
    return linhas


# ------------------------------------------------------------------- manifesto

def escrever_manifesto(rels):
    caminho = os.path.join(PASTA, "manifest.json")
    antigo = {}
    if os.path.exists(caminho):
        try:
            with open(caminho) as f:
                antigo = {(r["slug"], r["lod"]): r for r in json.load(f)["exportacoes"]}
        except Exception:
            antigo = {}
    for r in rels:
        antigo[(r["slug"], r["lod"])] = r
    # o tempo de execucao sai do manifesto: e a unica coisa que muda entre duas
    # rodadas iguais, e o manifesto e versionado - tem de ficar identico quando
    # nada mudou. Os .glb ja sao byte a byte identicos entre rodadas; o .usdz
    # nao e, porque zip guarda mtime, e por isso ele nao vai para o git.
    antigo = {k: {kk: vv for kk, vv in v.items() if kk != "segundos"}
              for k, v in antigo.items()}
    ordem = list(FROTA)
    itens = sorted(antigo.values(),
                   key=lambda r: (ordem.index(r["slug"]) if r["slug"] in ordem else 99,
                                  r["lod"]))
    with open(caminho, "w") as f:
        json.dump({
            "gerado_por": "export_frota.py",
            "licenca": ("Modelos CC BY 4.0 - LATAM fleet 3D replicas - Kim Lage. "
                        "Marcas de LATAM/Airbus/Boeing pertencem aos titulares. "
                        "Ver export/README.md e NOTICE.md."),
            "lods": LODS,
            "exportacoes": itens,
        }, f, indent=1)
    return caminho


def _linha(r):
    v = r.get("verificacao") or {}
    s = r.get("saidas", {})
    tam = " ".join("%s %.1fMB" % (k, d["bytes"] / 1e6) for k, d in sorted(s.items()))
    if r.get("erro"):
        return "%-8s %-5s  FALHOU  %s" % (r["slug"], r["lod"], r["erro"])
    c = (v.get("caixa") or {}).get("tamanho", [0, 0, 0])
    return ("%-8s %-5s  %7d tri  %2d mat  %2d tex %6.1f MP  "
            "X%6.2f Y%5.2f Z%6.2f  %-28s %s"
            % (r["slug"], r["lod"], v.get("triangulos", 0), v.get("materiais", 0),
               v.get("imagens", 0), v.get("megapixels", 0.0), c[0], c[1], c[2],
               tam, "OK" if v.get("ok") else "VERIFICACAO FALHOU"))


# ------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("aeronaves", nargs="*", help="siglas; vazio = todas (%s)"
                    % ", ".join(FROTA))
    ap.add_argument("--lod", default="todos", help="alta | web | todos")
    ap.add_argument("--verificar", action="store_true",
                    help="nao exporta: so le de volta o que ja esta em export/")
    ap.add_argument("--reimportar", action="store_true",
                    help="alem de verificar, reabre cada saida num Blender vazio"
                         " e mede a caixa (unica prova de eixo para USDZ/FBX/OBJ)")
    ap.add_argument("-v", "--verboso", action="store_true")
    a = ap.parse_args()

    alvos = a.aeronaves or list(FROTA)
    desconhecidas = [s for s in alvos if s not in FROTA]
    if desconhecidas:
        raise SystemExit("aeronave desconhecida: %s (ha %s)"
                         % (", ".join(desconhecidas), ", ".join(FROTA)))
    lods = list(LODS) if a.lod == "todos" else [a.lod]
    for l in lods:
        if l not in LODS:
            raise SystemExit("LOD desconhecido: %s (ha %s)" % (l, ", ".join(LODS)))

    os.makedirs(PASTA, exist_ok=True)

    if a.verificar:
        caminho = os.path.join(PASTA, "manifest.json")
        if not os.path.exists(caminho):
            raise SystemExit("sem manifest.json: rode a exportacao primeiro")
        with open(caminho) as f:
            itens = json.load(f)["exportacoes"]
        rels = [r for r in itens if r["slug"] in alvos and r["lod"] in lods]
        for r in rels:
            verificar(r)
            print(_linha(r))
            if a.reimportar:
                for l in reimportar(r):
                    print("         " + l)
        escrever_manifesto(rels)
        return 1 if any(not (r.get("verificacao") or {}).get("ok") for r in rels) else 0

    if not os.path.exists(BLENDER):
        raise SystemExit("Blender nao encontrado em %s (defina BLENDER=)" % BLENDER)

    rels, faltando, ruins = [], [], []
    for slug in alvos:
        for lod in lods:
            print("--- %s / %s" % (slug, lod))
            r = exportar(slug, lod, a.verboso)
            if r.get("erro"):
                if r.get("opcional"):
                    faltando.append(slug)
                    print("    pulada (ainda em construcao): %s" % r["erro"])
                    continue
                ruins.append(r)
                print("    FALHOU: %s" % r["erro"])
                if r.get("cauda"):
                    print("    " + r["cauda"].replace("\n", "\n    "))
                continue
            verificar(r)
            if a.reimportar:
                reimportar(r)
            rels.append(r)
            print("    " + _linha(r).strip())
            for l in r.get("reimportacao", []):
                print("         " + l)

    caminho = escrever_manifesto(rels)
    print("\n%s" % ("=" * 108))
    for r in rels:
        print(_linha(r))
    print("=" * 108)
    print("manifesto: %s" % os.path.relpath(caminho, RAIZ))
    if faltando:
        print("ainda sem master (esperado): %s" % ", ".join(sorted(set(faltando))))
    if ruins:
        print("FALHARAM, precisam de nova rodada: %s"
              % ", ".join("%s/%s" % (r["slug"], r["lod"]) for r in ruins))
    print("visualizador: cd export && python3 -m http.server 8000"
          "  ->  http://localhost:8000/viewer.html")
    mal = [r for r in rels if not (r.get("verificacao") or {}).get("ok")]
    return 1 if (ruins or mal) else 0


if __name__ == "__main__":
    sys.exit(main())
