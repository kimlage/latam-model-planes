#!/usr/bin/env python3
"""Le um .glb de volta e diz o que ha DENTRO dele. Python puro, sem dependencias.

    python3 export/verificar_glb.py export/glb/B77W_LATAM_web.glb [...]

Um arquivo que existe nao e um arquivo que carrega. Este modulo abre o container
GLB no nivel do byte - cabecalho, chunk JSON, chunk BIN - reconstroi a hierarquia
de nos, soma triangulos pelos accessors dos indices, confere que cada textura
esta EMBUTIDA (bufferView, nao URI externa), mede a caixa envolvente pelos
min/max dos accessors POSITION propagados pelas matrizes dos nos, e procura NaN.

A caixa envolvente e a prova do eixo: o glTF e +Y para cima e o Blender e +Z.
Se a conversao falhar, a envergadura aparece em Y e a altura em Z, e a aeronave
carrega deitada em qualquer visualizador. Aqui isso e um numero, nao uma opiniao.
"""
import base64
import json
import math
import struct
import sys

# ---------------------------------------------------------------- container

MAGIC = 0x46546C67          # "glTF"
JSON_CHUNK = 0x4E4F534A     # "JSON"
BIN_CHUNK = 0x004E4942      # "BIN\0"

# accessor componentType -> (struct fmt, bytes)
CT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
      5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
         "MAT2": 4, "MAT3": 9, "MAT4": 16}
MODE_TRIS = 4


class GLBError(Exception):
    pass


def ler_glb(caminho):
    """Devolve (json_dict, bytes_do_chunk_BIN). Valida o container."""
    with open(caminho, "rb") as f:
        blob = f.read()
    if len(blob) < 12:
        raise GLBError("arquivo com %d bytes: nem o cabecalho cabe" % len(blob))
    magic, versao, total = struct.unpack("<III", blob[:12])
    if magic != MAGIC:
        raise GLBError("magic 0x%08X, esperado 0x%08X (nao e GLB)" % (magic, MAGIC))
    if versao != 2:
        raise GLBError("versao %d, esperado 2" % versao)
    if total != len(blob):
        raise GLBError("cabecalho diz %d bytes, arquivo tem %d" % (total, len(blob)))
    js, binario, off = None, b"", 12
    while off + 8 <= len(blob):
        clen, ctipo = struct.unpack("<II", blob[off:off + 8])
        dados = blob[off + 8:off + 8 + clen]
        if len(dados) != clen:
            raise GLBError("chunk truncado em %d: %d de %d bytes" % (off, len(dados), clen))
        if ctipo == JSON_CHUNK:
            js = json.loads(dados.decode("utf-8"))
        elif ctipo == BIN_CHUNK:
            binario = dados
        off += 8 + clen + ((4 - clen % 4) % 4)
    if js is None:
        raise GLBError("sem chunk JSON")
    return js, binario


# ---------------------------------------------------------------- accessors

def _dados_bufferview(js, binario, idx):
    bv = js["bufferViews"][idx]
    buf = js["buffers"][bv["buffer"]]
    if "uri" in buf:
        uri = buf["uri"]
        if not uri.startswith("data:"):
            raise GLBError("buffer %d externo (%s): GLB deixou de ser autocontido"
                           % (bv["buffer"], uri[:60]))
        base = base64.b64decode(uri.split(",", 1)[1])
    else:
        base = binario
    ini = bv.get("byteOffset", 0)
    return base[ini:ini + bv["byteLength"]], bv.get("byteStride")


def ler_accessor(js, binario, idx):
    """Lista de tuplas com os valores do accessor. Respeita byteStride."""
    ac = js["accessors"][idx]
    if "bufferView" not in ac:                       # accessor esparso/zerado
        return [(0.0,) * NCOMP[ac["type"]]] * ac["count"]
    dados, stride = _dados_bufferview(js, binario, ac["bufferView"])
    fmt, tam = CT[ac["componentType"]]
    n = NCOMP[ac["type"]]
    elem = tam * n
    stride = stride or elem
    ini = ac.get("byteOffset", 0)
    saida = []
    for i in range(ac["count"]):
        o = ini + i * stride
        saida.append(struct.unpack_from("<" + fmt * n, dados, o))
    return saida


def _mat_do_no(no):
    """Matriz 4x4 (lista de 16, ordem coluna) do no, de `matrix` ou TRS."""
    if "matrix" in no:
        return list(no["matrix"])
    t = no.get("translation", [0.0, 0.0, 0.0])
    r = no.get("rotation", [0.0, 0.0, 0.0, 1.0])
    s = no.get("scale", [1.0, 1.0, 1.0])
    x, y, z, w = r
    rot = [
        1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w),
        2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w),
        2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y),
    ]
    m = [0.0] * 16
    for c in range(3):
        for l in range(3):
            m[c * 4 + l] = rot[c * 3 + l] * s[c]
    m[12], m[13], m[14], m[15] = t[0], t[1], t[2], 1.0
    return m


def _mul(a, b):
    """a @ b, ambas 4x4 em ordem coluna."""
    r = [0.0] * 16
    for c in range(4):
        for l in range(4):
            r[c * 4 + l] = sum(a[k * 4 + l] * b[c * 4 + k] for k in range(4))
    return r


def _aplicar(m, p):
    return tuple(m[0 + i] * p[0] + m[4 + i] * p[1] + m[8 + i] * p[2] + m[12 + i]
                 for i in range(3))


# ---------------------------------------------------------------- inspecao

def inspecionar(caminho):
    """Relatorio do que ha dentro do GLB. Levanta GLBError se o container mente."""
    import os
    js, binario = ler_glb(caminho)
    rel = {
        "arquivo": os.path.basename(caminho),
        "bytes": os.path.getsize(caminho),
        "bin_bytes": len(binario),
        "gerador": js.get("asset", {}).get("generator", ""),
        "versao_gltf": js.get("asset", {}).get("version", ""),
        "extensoes": sorted(set(js.get("extensionsUsed", []))),
        "extensoes_requeridas": sorted(set(js.get("extensionsRequired", []))),
        "n_nos": len(js.get("nodes", [])),
        "n_malhas": len(js.get("meshes", [])),
        "n_materiais": len(js.get("materials", [])),
        "n_texturas": len(js.get("textures", [])),
        "n_imagens": len(js.get("images", [])),
        "erros": [],
        "avisos": [],
    }

    # --- imagens: embutidas ou nao ------------------------------------------
    imgs, mp = [], 0.0
    for i, im in enumerate(js.get("images", [])):
        if "uri" in im and not im["uri"].startswith("data:"):
            rel["erros"].append("imagem %d aponta para arquivo externo: %s" % (i, im["uri"]))
            imgs.append({"i": i, "externa": im["uri"]})
            continue
        if "bufferView" in im:
            dados, _ = _dados_bufferview(js, binario, im["bufferView"])
            n = len(dados)
        else:
            dados = base64.b64decode(im["uri"].split(",", 1)[1])
            n = len(dados)
        larg, alt = _dim_imagem(dados)
        mp += (larg * alt) / 1e6
        imgs.append({"i": i, "nome": im.get("name", ""), "mime": im.get("mimeType", ""),
                     "bytes": n, "larg": larg, "alt": alt})
    rel["imagens"] = imgs
    rel["megapixels"] = round(mp, 2)
    rel["bytes_imagens"] = sum(im.get("bytes", 0) for im in imgs)

    # --- materiais -----------------------------------------------------------
    mats, sem_tex, com_coat = [], 0, 0
    for i, ma in enumerate(js.get("materials", [])):
        pbr = ma.get("pbrMetallicRoughness", {})
        tex = [k for k in ("baseColorTexture", "metallicRoughnessTexture") if k in pbr]
        tex += [k for k in ("normalTexture", "emissiveTexture", "occlusionTexture") if k in ma]
        coat = "KHR_materials_clearcoat" in ma.get("extensions", {})
        com_coat += 1 if coat else 0
        sem_tex += 0 if tex else 1
        mats.append({"i": i, "nome": ma.get("name", ""), "texturas": tex, "clearcoat": coat,
                     "baseColorFactor": pbr.get("baseColorFactor"),
                     "metallic": pbr.get("metallicFactor"),
                     "roughness": pbr.get("roughnessFactor")})
    rel["materiais"] = mats
    rel["materiais_sem_textura"] = sem_tex
    rel["materiais_com_clearcoat"] = com_coat

    # --- hierarquia de nos + geometria --------------------------------------
    nodes = js.get("nodes", [])
    filhos = set()
    for no in nodes:
        filhos.update(no.get("children", []))
    raizes = [i for i in range(len(nodes)) if i not in filhos]
    cenas = js.get("scenes", [])
    if not cenas:
        rel["erros"].append("nenhuma cena declarada")
    rel["raizes"] = len(raizes)
    rel["n_raizes_da_cena"] = len(cenas[0].get("nodes", [])) if cenas else 0

    tris = 0
    prims = 0
    verts = 0
    mats_usados = set()
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    nan = []
    profundidade = [0]

    def andar(i, pai, prof):
        profundidade[0] = max(profundidade[0], prof)
        no = nodes[i]
        m = _mul(pai, _mat_do_no(no))
        if "mesh" in no:
            malha = js["meshes"][no["mesh"]]
            for p in malha.get("primitives", []):
                nonlocal tris, prims, verts
                prims += 1
                modo = p.get("mode", MODE_TRIS)
                if modo != MODE_TRIS:
                    rel["avisos"].append("primitiva modo %d (nao triangulos) em %s"
                                         % (modo, malha.get("name", "?")))
                pos_i = p["attributes"].get("POSITION")
                if pos_i is None:
                    rel["erros"].append("primitiva sem POSITION em %s" % malha.get("name", "?"))
                    continue
                ac = js["accessors"][pos_i]
                verts += ac["count"]
                if "indices" in p:
                    n_i = js["accessors"][p["indices"]]["count"]
                else:
                    n_i = ac["count"]
                if modo == MODE_TRIS:
                    tris += n_i // 3
                if "material" in p:
                    mats_usados.add(p["material"])
                # caixa: min/max do accessor bastam quando ha matriz afim
                mn, mx = ac.get("min"), ac.get("max")
                if mn and mx:
                    if any(_ehnan(v) for v in mn + mx):
                        nan.append(malha.get("name", "?"))
                    for cx in (0, 1):
                        for cy in (0, 1):
                            for cz in (0, 1):
                                p3 = ((mx if cx else mn)[0], (mx if cy else mn)[1],
                                      (mx if cz else mn)[2])
                                w = _aplicar(m, p3)
                                for k in range(3):
                                    lo[k] = min(lo[k], w[k])
                                    hi[k] = max(hi[k], w[k])
                else:
                    rel["avisos"].append("accessor POSITION sem min/max em %s"
                                         % malha.get("name", "?"))
        for c in no.get("children", []):
            andar(c, m, prof + 1)

    ident = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
    for i in (cenas[0].get("nodes", raizes) if cenas else raizes):
        andar(i, ident, 1)

    rel["triangulos"] = tris
    rel["primitivas"] = prims
    rel["vertices"] = verts
    rel["profundidade_no"] = profundidade[0]
    rel["materiais_usados"] = len(mats_usados)
    if math.isinf(lo[0]):
        rel["erros"].append("nenhuma geometria alcancavel a partir da cena")
        rel["caixa"] = None
    else:
        rel["caixa"] = {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi],
                        "tamanho": [round(hi[k] - lo[k], 4) for k in range(3)]}
    if nan:
        rel["erros"].append("NaN/Inf na caixa de: %s" % ", ".join(sorted(set(nan))))

    # --- checagens que valem por si -----------------------------------------
    if tris == 0:
        rel["erros"].append("zero triangulos")
    if rel["n_materiais"] == 0:
        rel["erros"].append("zero materiais")
    if rel["n_imagens"] == 0:
        rel["avisos"].append("nenhuma imagem embutida")
    if "KHR_draco_mesh_compression" in rel["extensoes_requeridas"]:
        rel["draco"] = True
    else:
        rel["draco"] = False
    # NaN nos dados, nao so nos min/max: varre POSITION do maior accessor
    rel["nan_amostrado"] = _varrer_nan(js, binario)
    if rel["nan_amostrado"]:
        rel["erros"].append("NaN em POSITION: %s" % rel["nan_amostrado"])
    return rel


def _ehnan(v):
    return isinstance(v, float) and (math.isnan(v) or math.isinf(v))


def _varrer_nan(js, binario, limite=12):
    """Le de verdade os POSITION dos maiores accessors e procura NaN/Inf.

    Draco guarda a geometria comprimida no bufferView, entao ali so se pode
    confiar no min/max - que ja foi conferido acima.
    """
    if "KHR_draco_mesh_compression" in js.get("extensionsRequired", []):
        return ""
    alvos = []
    for m in js.get("meshes", []):
        for p in m.get("primitives", []):
            i = p["attributes"].get("POSITION")
            if i is not None:
                alvos.append((js["accessors"][i]["count"], i, m.get("name", "?")))
    alvos.sort(reverse=True)
    for _c, i, nome in alvos[:limite]:
        try:
            for v in ler_accessor(js, binario, i):
                if any(math.isnan(x) or math.isinf(x) for x in v):
                    return nome
        except Exception as exc:                      # container coerente > varredura
            return "falha ao ler accessor %d: %s" % (i, exc)
    return ""


def _dim_imagem(dados):
    """(largura, altura) de PNG, JPEG ou WebP, sem decodificar a imagem."""
    if dados[:8] == b"\x89PNG\r\n\x1a\n" and dados[12:16] == b"IHDR":
        return struct.unpack(">II", dados[16:24])
    if dados[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(dados):
            if dados[i] != 0xFF:
                i += 1
                continue
            marca = dados[i + 1]
            if marca in (0xD8, 0x01) or 0xD0 <= marca <= 0xD7:
                i += 2
                continue
            tam = struct.unpack(">H", dados[i + 2:i + 4])[0]
            if 0xC0 <= marca <= 0xCF and marca not in (0xC4, 0xC8, 0xCC):
                alt, larg = struct.unpack(">HH", dados[i + 5:i + 9])
                return larg, alt
            i += 2 + tam
        return 0, 0
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        if dados[12:16] == b"VP8L":
            b = dados[21:25]
            n = struct.unpack("<I", b)[0]
            return (n & 0x3FFF) + 1, ((n >> 14) & 0x3FFF) + 1
        if dados[12:16] == b"VP8 ":
            larg, alt = struct.unpack("<HH", dados[26:30])
            return larg & 0x3FFF, alt & 0x3FFF
        if dados[12:16] == b"VP8X":
            larg = int.from_bytes(dados[24:27], "little") + 1
            alt = int.from_bytes(dados[27:30], "little") + 1
            return larg, alt
    return 0, 0


# ------------------------------------------------------------------ linha de comando

def _imprimir(rel):
    print("== %s  %.2f MB" % (rel["arquivo"], rel["bytes"] / 1e6))
    print("   gerador   %s  glTF %s" % (rel["gerador"], rel["versao_gltf"]))
    print("   geometria %d triangulos, %d vertices, %d primitivas, %d nos (prof. %d)"
          % (rel["triangulos"], rel["vertices"], rel["primitivas"], rel["n_nos"],
             rel["profundidade_no"]))
    c = rel["caixa"]
    if c:
        print("   caixa     X %8.2f  Y %8.2f  Z %8.2f  m   (glTF: X compr., Y alt., Z env.)"
              % tuple(c["tamanho"]))
        print("             min %s  max %s" % (c["min"], c["max"]))
    print("   materiais %d declarados, %d usados, %d com clearcoat, %d sem textura"
          % (rel["n_materiais"], rel["materiais_usados"], rel["materiais_com_clearcoat"],
             rel["materiais_sem_textura"]))
    print("   texturas  %d imagens, %.2f MP, %.2f MB embutidos  (bin total %.2f MB)"
          % (rel["n_imagens"], rel["megapixels"], rel["bytes_imagens"] / 1e6,
             rel["bin_bytes"] / 1e6))
    for im in rel["imagens"]:
        if "externa" in im:
            print("             EXTERNA %s" % im["externa"])
        else:
            print("             %-26s %5dx%-5d %-15s %7.2f MB"
                  % (im["nome"][:26], im["larg"], im["alt"], im["mime"], im["bytes"] / 1e6))
    if rel["extensoes"]:
        print("   extensoes %s" % ", ".join(rel["extensoes"]))
    for a in rel["avisos"][:8]:
        print("   AVISO  %s" % a)
    for e in rel["erros"]:
        print("   ERRO   %s" % e)
    print("   -> %s" % ("OK" if not rel["erros"] else "FALHOU"))


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    ruim = 0
    for caminho in argv:
        try:
            rel = inspecionar(caminho)
        except GLBError as exc:
            print("== %s\n   ERRO   %s\n   -> FALHOU" % (caminho, exc))
            ruim += 1
            continue
        _imprimir(rel)
        ruim += 1 if rel["erros"] else 0
    return 1 if ruim else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
