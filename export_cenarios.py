#!/usr/bin/env python3
"""Exporta os CENARIOS para a web - pedacos componiveis dos tres aerodromos.

    python3 export_cenarios.py                    # tudo
    python3 export_cenarios.py --campo sbgr       # so Guarulhos
    python3 export_cenarios.py sdsc_hangar9 ...   # so estes assets
    python3 export_cenarios.py --verificar        # nao exporta: so le de volta
    python3 export_cenarios.py --listar           # o catalogo, sem abrir Blender

Irmao de [`export_frota.py`](export_frota.py) e com o mesmo formato: um driver
fino aqui, a regra dentro do Blender em
[`export/cenarios_portateis.py`](export/cenarios_portateis.py), a leitura de
volta em [`export/verificar_glb.py`](export/verificar_glb.py). Um Blender por
CAMPO (nao por asset): abrir `sbgr_field.blend` custa segundos e todos os assets
daquele campo saem da mesma sessao.

POR QUE ISTO PODE EXISTIR. A rodada anterior do estudio se recusou a tocar em
`scenario*/` achando que ODbL e CC BY "conflitam" e que portanto a malha do
aerodromo nunca poderia sair. NOTICE.md e explicito: a malha PODE ser
redistribuida sob ODbL desde que a atribuicao viaje junto e o share-alike seja
honrado - e o repositorio ja redistribui renders dela em todo GIF publicado. A
solucao nao e nao exportar, e LICENCIAR POR ASSET: cada linha do manifesto
carrega seu `licenca`, o .glb carrega a atribuicao no proprio arquivo, e o
estudio mostra as licencas que a cena aberta realmente usa.

VERIFICAR NAO E OPCIONAL, pela mesma razao que na frota: um arquivo que existe
nao e um arquivo que carrega. Todo .glb escrito e reaberto no nivel do byte e
conferido - triangulos, materiais, NaN, eixo, e a base em y = 0 (excecao
declarada: as placas de campo tem datum na cabeceira, entao descem abaixo de
zero de proposito).
"""
import argparse
import json
import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(RAIZ, "export")
SAIDA = os.path.join(PASTA, "cenarios")
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")

sys.path.insert(0, PASTA)
import verificar_glb  # noqa: E402

_MOD = os.path.join(PASTA, "cenarios_portateis.py")


def _tabelas():
    """CATALOGO, CAMPOS e LICENCAS lidos sem importar bpy."""
    import ast
    fonte = open(_MOD).read()
    arv = ast.parse(fonte)
    ns = {}
    # As helpers de regiao viram dicts na avaliacao; reimplementadas aqui.
    def circ(x, y, r):
        return {"tipo": "circulo", "x": x, "y": y, "r": r}

    def rect(x0, x1, y0, y1):
        return {"tipo": "retangulo", "x0": x0, "x1": x1, "y0": y0, "y1": y1}

    def obb(cx, cy, c, l, h):
        return {"tipo": "obb", "x": cx, "y": cy, "L": c, "W": l, "hdg": h}

    amb = {"circ": circ, "rect": rect, "obb": obb, "dict": dict}
    for no in arv.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1 \
                and isinstance(no.targets[0], ast.Name) \
                and no.targets[0].id in ("CATALOGO", "CAMPOS", "LICENCAS",
                                         "MARCAS", "TETO_FACES"):
            ns[no.targets[0].id] = eval(compile(ast.Expression(no.value),
                                                "<cat>", "eval"), amb)
    return ns


T = _tabelas()
CATALOGO, CAMPOS, LICENCAS = T["CATALOGO"], T["CAMPOS"], T["LICENCAS"]
MARCAS, TETO_FACES = T["MARCAS"], T["TETO_FACES"]

CATEGORIAS = {
    "estrutura": "airport structures",
    "superficie": "ground & surfaces",
    "veiculo": "vehicles & GSE",
    "adereco": "props",
}


# ------------------------------------------------------------------ exportar

def exportar(campo, slugs, verboso=False):
    d = CAMPOS[campo]
    blend = os.path.join(RAIZ, d["blend"])
    if not os.path.exists(blend):
        return {"campo": campo, "erro": "campo ausente: %s" % blend, "assets": []}
    rel_json = os.path.join(PASTA, ".rel_cen_%s.json" % campo)
    if os.path.exists(rel_json):
        os.remove(rel_json)
    cmd = [BLENDER, "-b", blend, "--factory-startup", "--python", _MOD, "--",
           "--campo", campo, "--saida", SAIDA, "--relatorio", rel_json]
    if slugs:
        cmd += ["--assets", ",".join(slugs)]
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t
    if verboso:
        print(p.stdout)
    if not os.path.exists(rel_json):
        cauda = "\n".join((p.stdout + p.stderr).strip().splitlines()[-14:])
        return {"campo": campo, "erro": "Blender nao produziu relatorio",
                "codigo": p.returncode, "cauda": cauda, "assets": []}
    with open(rel_json) as f:
        rel = json.load(f)
    os.remove(rel_json)
    rel["segundos"] = round(dt, 1)
    return rel


# --------------------------------------------------------------- verificacao

def verificar(a):
    """Le o .glb de volta e confronta com o que o Blender disse ter escrito."""
    caminho = os.path.join(SAIDA, a["arquivo"])
    try:
        v = verificar_glb.inspecionar(caminho)
    except Exception as exc:                     # noqa: BLE001
        a["verificacao"] = {"ok": False, "erros": ["container: %s" % exc]}
        return
    erros, avisos = list(v["erros"]), list(v["avisos"])

    if v["n_raizes_da_cena"] != 1:
        erros.append("%d nos raiz, esperado 1" % v["n_raizes_da_cena"])
    if abs(v["triangulos"] - a["triangulos"]) > max(4, a["triangulos"] * 0.001):
        erros.append("triangulos %d no .glb x %d no Blender"
                     % (v["triangulos"], a["triangulos"]))
    if not v["draco"]:
        erros.append("sem Draco")
    cx = v["caixa"]
    if cx:
        for i, eixo in enumerate("XYZ"):
            if abs(cx["tamanho"][i] - a["caixa"]["tamanho"][i]) > 0.02:
                erros.append("%s: %.2f m no .glb x %.2f m medido"
                             % (eixo, cx["tamanho"][i], a["caixa"]["tamanho"][i]))
        # a base em y = 0, com a excecao declarada das placas de campo
        if a["fonte"]["datum"] == "min":
            if abs(cx["min"][1]) > 0.02:
                erros.append("base em y=%.3f m, esperado 0" % cx["min"][1])
            # pivo no centro X/Z
            for i, eixo in ((0, "X"), (2, "Z")):
                c = (cx["min"][i] + cx["max"][i]) / 2
                if abs(c) > 0.02:
                    erros.append("pivo fora do centro %s: %.3f m" % (eixo, c))
        else:
            avisos.append("datum na cabeceira: base em y=%.1f m, de proposito"
                          % cx["min"][1])
    a["verificacao"] = {
        "ok": not erros, "erros": erros, "avisos": avisos,
        "triangulos": v["triangulos"], "vertices": v["vertices"],
        "materiais": v["n_materiais"], "imagens": v["n_imagens"],
        "caixa": cx, "draco": v["draco"], "nos": v["n_nos"],
        "extensoes": v["extensoes"],
    }


# ----------------------------------------------------------------- manifesto

def escrever_manifesto(assets, achatados):
    caminho = os.path.join(SAIDA, "manifest.json")
    antigo = {}
    if os.path.exists(caminho):
        try:
            with open(caminho) as f:
                m = json.load(f)
            antigo = {a["slug"]: a for a in m.get("assets", [])}
            achatados = {**m.get("materiais_achatados", {}), **achatados}
        except Exception:                        # noqa: BLE001
            antigo = {}
    for a in assets:
        antigo[a["slug"]] = a
    ordem = list(CATALOGO)
    itens = sorted(antigo.values(),
                   key=lambda a: ordem.index(a["slug"]) if a["slug"] in ordem else 999)
    os.makedirs(SAIDA, exist_ok=True)
    with open(caminho, "w") as f:
        json.dump({
            "schema": "latam-cenarios/1",
            "gerado_por": "export_cenarios.py",
            "aviso": ("Geometria de aerodromo derivada de OpenStreetMap. Cada "
                      "asset carrega seu proprio campo `licenca`; a tabela "
                      "`licencas` diz o que cada id exige. ODbL e share-alike: "
                      "uma cena que use qualquer asset odbl-1.0 carrega essa "
                      "obrigacao junto."),
            "licencas": LICENCAS,
            "marcas": MARCAS,
            "categorias": CATEGORIAS,
            "campos": {k: {"rotulo": v["rotulo"], "blend": v["blend"],
                           "datum_z": v["datum_z"]} for k, v in CAMPOS.items()},
            "teto_faces": TETO_FACES,
            "materiais_achatados": dict(sorted(achatados.items())),
            "assets": itens,
        }, f, indent=1)
    return caminho


# --------------------------------------------------------------------- saida

def _linha(a):
    if a.get("erro"):
        return "%-24s FALHOU  %s" % (a["slug"], a["erro"])
    v = a.get("verificacao") or {}
    t = a["caixa"]["tamanho"]
    return ("%-24s %-11s %7d f %7d tri %2d mat  %7.1f x %6.1f x %7.1f m  "
            "%8.1f kB  %s"
            % (a["slug"], a["categoria"], a["faces"], a["triangulos"],
               a["materiais"], t[0], t[1], t[2], a["bytes"] / 1024,
               "OK" if v.get("ok") else "VERIFICACAO FALHOU"))


def listar():
    for campo in CAMPOS:
        print("--- %s  (%s)" % (campo, CAMPOS[campo]["rotulo"]))
        for slug, d in CATALOGO.items():
            if d["campo"] != campo:
                continue
            print("    %-24s %-11s %s" % (slug, d["categoria"], d["rotulo"]))
    print("\n%d assets, %d campos" % (len(CATALOGO), len(CAMPOS)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("assets", nargs="*", help="slugs; vazio = todos")
    ap.add_argument("--campo", default=None, help="scl | sdsc | sbgr")
    ap.add_argument("--verificar", action="store_true",
                    help="nao exporta: so le de volta o que ja esta em export/cenarios/")
    ap.add_argument("--listar", action="store_true", help="o catalogo, so isso")
    ap.add_argument("-v", "--verboso", action="store_true")
    a = ap.parse_args()

    if a.listar:
        listar()
        return 0

    desconhecidos = [s for s in a.assets if s not in CATALOGO]
    if desconhecidos:
        raise SystemExit("asset desconhecido: %s" % ", ".join(desconhecidos))

    if a.verificar:
        caminho = os.path.join(SAIDA, "manifest.json")
        if not os.path.exists(caminho):
            raise SystemExit("sem manifest.json: rode a exportacao primeiro")
        with open(caminho) as f:
            m = json.load(f)
        itens = [x for x in m["assets"]
                 if (not a.assets or x["slug"] in a.assets)
                 and (not a.campo or x["campo"] == a.campo)]
        for x in itens:
            verificar(x)
            print(_linha(x))
        escrever_manifesto(itens, m.get("materiais_achatados", {}))
        return 1 if any(not (x.get("verificacao") or {}).get("ok") for x in itens) else 0

    if not os.path.exists(BLENDER):
        raise SystemExit("Blender nao encontrado em %s (defina BLENDER=)" % BLENDER)
    os.makedirs(SAIDA, exist_ok=True)

    campos = [a.campo] if a.campo else list(CAMPOS)
    todos, achatados, ruins = [], {}, []
    for campo in campos:
        slugs = [s for s in a.assets if CATALOGO[s]["campo"] == campo] if a.assets else []
        if a.assets and not slugs:
            continue
        print("=== campo %s" % campo)
        rel = exportar(campo, slugs, a.verboso)
        if rel.get("erro"):
            print("    FALHOU: %s" % rel["erro"])
            if rel.get("cauda"):
                print("    " + rel["cauda"].replace("\n", "\n    "))
            ruins.append(campo)
            continue
        achatados.update(rel.get("materiais_achatados", {}))
        for x in rel["assets"]:
            if not x.get("erro"):
                verificar(x)
            todos.append(x)
            print("    " + _linha(x))
        print("    %.1f s" % rel.get("segundos", 0))

    bons = [x for x in todos if not x.get("erro")]
    caminho = escrever_manifesto(bons, achatados)
    print("\n%s" % ("=" * 116))
    for x in todos:
        print(_linha(x))
    print("=" * 116)
    tot_b = sum(x["bytes"] for x in bons)
    tot_f = sum(x["faces"] for x in bons)
    print("%d assets  %d faces  %.2f MB" % (len(bons), tot_f, tot_b / 1e6))
    print("manifesto: %s" % os.path.relpath(caminho, RAIZ))
    mal = [x for x in bons if not (x.get("verificacao") or {}).get("ok")]
    falhos = [x for x in todos if x.get("erro")]
    if falhos:
        print("FALHARAM: %s" % ", ".join(x["slug"] for x in falhos))
    if mal:
        print("VERIFICACAO FALHOU: %s" % ", ".join(x["slug"] for x in mal))
    return 1 if (ruins or mal or falhos) else 0


if __name__ == "__main__":
    sys.exit(main())
