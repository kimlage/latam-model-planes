#!/usr/bin/env python3
"""Regra da exportacao dos CENARIOS - roda DENTRO do Blender.

Irmao de [`frota_portatil.py`](frota_portatil.py): aquele leva UMA aeronave
inteira para fora; este recorta PEDACOS COMPONIVEIS de um aerodromo e leva cada
um como um .glb proprio, com o mesmo eixo, o mesmo datum e o mesmo Draco.

    Blender -b <campo>.blend --factory-startup --python cenarios_portateis.py \
        -- --campo sbgr --saida <pasta> --relatorio rel.json [--assets a,b,c]

O PROBLEMA que este arquivo resolve: os construtores de cenario juntam tudo em
poucas malhas gigantes por material - `SBGR_Jetbridges` e TODAS as pontes de
embarque do aeroporto numa malha so, espalhadas por 1,7 km. Nao existe "objeto
ponte de embarque" para exportar. Entao um asset aqui e definido por uma REGIAO
do campo, e ha dois jeitos de recortar, escolhidos por peca:

  ilhas   componentes conexos cujo CENTRO cai na regiao entram INTEIROS. E o
          certo para predios, veiculos, mastros - ninguem quer meio caminhao.
  corte   bisseccao pelos quatro planos da regiao. E o certo para pavimento,
          pintura e chao, que sao tapetes: cortar no meio de um quad e o
          resultado desejado, e filtrar por centro daria tudo-ou-nada num
          poligono de 3,7 km.

LICENCA - a razao de este arquivo existir e nao ser obvio. A malha do aerodromo
e derivada de OpenStreetMap (ver NOTICE.md, secao "The airport mesh is an OSM
derivative"). ODbL PERMITE a redistribuicao desde que a atribuicao viaje junto e
o share-alike seja honrado. Entao cada asset carrega seu proprio campo
`licenca` no manifesto, o .glb carrega a atribuicao no `copyright` do asset
glTF, e o estudio mostra as licencas que a cena realmente usa. Terreno
Copernicus NAO e exportado por este arquivo - nenhum asset o referencia.

MATERIAIS: os materiais do cenario sao redes de nos procedurais (ruido, mapas de
range, o grupo de neblina) que glTF nao sabe representar e que so um bake
resolveria. Este exportador os ACHATA numa cor representativa - lida de
`material.diffuse_color`, que os construtores ja definem como a cor base de cada
material, com o Principled como segunda fonte. Esta perda e real e esta no
relatorio: `materiais_achatados`.
"""
import argparse
import json
import math
import os
import sys

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

# ---------------------------------------------------------------------------
# Licencas. Uma tabela, citada por id em cada asset.
# ---------------------------------------------------------------------------

LICENCAS = {
    "odbl-1.0": {
        "nome": "ODbL 1.0 (Open Database License)",
        "url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "atribuicao": "Airport geometry (c) OpenStreetMap contributors, ODbL 1.0",
        "share_alike": True,
        "nota": ("A malha do aerodromo e gerada a partir de OpenStreetMap "
                 "(footprints, eixos de taxiway, poligonos de patio, posicoes "
                 "de stand e ponte). Uma malha feita a partir de um banco ODbL "
                 "e um banco derivado: redistribuir exige a atribuicao acima E "
                 "share-alike sobre a geodata derivada. O levantamento de pista "
                 "(cabeceiras, larguras, distancias declaradas, geometria de "
                 "pintura) vem de AIP/DECEA/DGAC e e citado como fato."),
    },
    "cc-by-4.0": {
        "nome": "CC BY 4.0",
        "url": "https://creativecommons.org/licenses/by/4.0/",
        "atribuicao": "LATAM fleet 3D replicas - Kim Lage - CC BY 4.0",
        "share_alike": False,
        "nota": ("Geometria original deste repositorio, construida a partir dos "
                 "documentos dimensionais publicados pelos fabricantes."),
    },
    "copernicus": {
        "nome": "Copernicus WorldDEM-30 (Free & Open)",
        "url": "https://spacedata.copernicus.eu/",
        "atribuicao": ("produced using Copernicus WorldDEM-30 (c) DLR e.V. "
                       "2010-2014 and (c) Airbus Defence and Space GmbH "
                       "2014-2018 provided under COPERNICUS by the European "
                       "Union and ESA; all rights reserved"),
        "share_alike": False,
        "nota": ("As organizacoes responsaveis pelo programa Copernicus por lei "
                 "ou delegacao nao incorrem em qualquer responsabilidade por "
                 "qualquer uso do Copernicus WorldDEM-30. NENHUM asset desta "
                 "exportacao usa terreno Copernicus - a tabela esta aqui porque "
                 "o estudio a exibe se algum dia usar."),
    },
}

MARCAS = ("LATAM, Airbus e Boeing sao marcas de seus titulares. Projeto "
          "independente, nao comercial, sem afiliacao ou endosso.")

# ---------------------------------------------------------------------------
# Os campos e o datum de cada um.
#
# `datum_z` e a cota Blender que vira y = 0 no .glb para as PLACAS DE CAMPO: a
# cabeceira da pista. Assim uma aeronave em y = 0 pousa na pista, e o resto do
# campo fica onde o terreno o poe - abaixo, quando o terreno desce. Para as
# pecas soltas o datum e o proprio ponto mais baixo da peca.
# ---------------------------------------------------------------------------

CAMPOS = {
    "scl": {
        "blend": "scenario/scl_field.blend",
        "rotulo": "SCEL - Santiago / Arturo Merino Benitez",
        "datum_z": 0.0,          # SCL_17L_Threshold
        "prefixo": "SCL_",
    },
    "sdsc": {
        "blend": "scenario_sdsc/sdsc_field.blend",
        "rotulo": "SDSC - Sao Carlos / base de manutencao LATAM",
        "datum_z": -2.33,        # SDSC_02_Threshold
        "prefixo": "SDSC_",
    },
    "sbgr": {
        "blend": "scenario_sbgr/sbgr_field.blend",
        "rotulo": "SBGR - Guarulhos / Sao Paulo",
        "datum_z": -4.76,        # SBGR_10L_Threshold
        "prefixo": "SBGR_",
    },
}

# ---------------------------------------------------------------------------
# O CATALOGO.
#
# Cada asset:
#   rotulo      o nome que o estudio mostra
#   categoria   estrutura | superficie | veiculo | adereco
#   pecas       malhas recortadas por ILHA (componente conexo inteiro)
#   superficies malhas recortadas por CORTE (bisseccao)
#   regiao      None = tudo; senao {"tipo": "circulo"|"retangulo"|"obb", ...}
#   datum       "min" (base da peca em y=0) | "campo" (cabeceira em y=0)
#   centrar_em  lista de malhas cuja caixa define a ORIGEM XY. Sem isto a
#               origem e o centro da caixa de TUDO, e um PAPI de um lado so da
#               pista puxa esse centro 20 m para fora do eixo - foi o que
#               deixou o 777 do cenario inicial com o trem na borda.
#   nota        o que a peca e, e o que nela e inferencia
# ---------------------------------------------------------------------------

def circ(x, y, r):
    return {"tipo": "circulo", "x": x, "y": y, "r": r}


def rect(x0, x1, y0, y1):
    return {"tipo": "retangulo", "x0": x0, "x1": x1, "y0": y0, "y1": y1}


def obb(cx, cy, comprimento, largura, hdg):
    """Retangulo orientado. `hdg` em graus, medido de +X para +Y.
    A peca sai girada de -hdg, ou seja alinhada a +X no .glb."""
    return {"tipo": "obb", "x": cx, "y": cy, "L": comprimento, "W": largura,
            "hdg": hdg}


CATALOGO = {

    # ------------------------------------------------------------ SBGR ----
    "sbgr_hangar_latam": dict(
        campo="sbgr", categoria="estrutura", rotulo="LATAM hangar (GRU)",
        pecas=["SBGR_LATAM_Hangar", "SBGR_LATAM_HangarTruss",
               "SBGR_LATAM_HangarDoors", "SBGR_LATAM_HangarBand",
               "SBGR_LATAM_HangarFloor", "SBGR_LATAM_HangarOpenBay",
               "SBGR_LATAM_Hangar_Wordmark", "SBGR_LATAM_Hangar_Brandmark"],
        nota="O hangar da base LATAM em Guarulhos, com a fachada, a porta, a "
             "faixa e a marca. Footprint do OSM; altura estimada."),

    "sbgr_hangar_mro": dict(
        campo="sbgr", categoria="estrutura", rotulo="MRO hangar, second bay (GRU)",
        pecas=["SBGR_AA_Hangar", "SBGR_AA_HangarDoors"],
        nota="O segundo hangar da area de manutencao, com a porta."),

    "sbgr_torre": dict(
        campo="sbgr", categoria="estrutura", rotulo="Control tower (GRU)",
        pecas=["SBGR_TWR_Shaft", "SBGR_TWR_Cab", "SBGR_TWR_Galleries",
               "SBGR_TWR_Radome"],
        nota="Torre de controle: fuste, galerias, cabine e radome."),

    "sbgr_terminal_t3": dict(
        campo="sbgr", categoria="estrutura", rotulo="Terminal 3 pier (GRU)",
        pecas=["SBGR_TerminalBodies", "SBGR_TerminalGlassBand"],
        regiao=rect(-230, 410, 545, 1010),
        nota="O pier inteiro do Terminal 3: 624 m de frente. E um fundo de "
             "cena, nao uma peca de montar - use-o atras dos stands."),

    "sbgr_terminal_bloco": dict(
        campo="sbgr", categoria="estrutura", rotulo="Terminal block (GRU)",
        pecas=["SBGR_TerminalBodies", "SBGR_TerminalGlassBand"],
        regiao=rect(-760, -630, 350, 640),
        nota="Um bloco de terminal de ~104 x 276 m, do tamanho certo para "
             "compor uma cena de stand sem engolir a aeronave."),

    "sbgr_ponte_embarque": dict(
        campo="sbgr", categoria="estrutura", rotulo="Jetbridge (GRU)",
        pecas=["SBGR_Jetbridges", "SBGR_JetbridgeDark"],
        regiao=circ(-10.0, 625.0, 30.0),
        nota="Uma ponte de embarque articulada: rotunda, tunel, cabine e as "
             "colunas. Posicao vem do stand mapeado no OSM."),

    "sbgr_galpao_carga": dict(
        campo="sbgr", categoria="estrutura", rotulo="Cargo shed (GRU)",
        pecas=["SBGR_CargoSheds"],
        regiao=circ(2213.8, 1440.1, 120.0),
        nota="Galpao de carga junto a base LATAM."),

    "sbgr_pista_secao": dict(
        campo="sbgr", categoria="superficie",
        rotulo="Runway 10R threshold, 500 m (GRU)",
        superficies=["SBGR_RwyS_Pavement", "SBGR_RunwayShoulders",
                     "SBGR_RunwayMarkings"],
        pecas=["SBGR_RunwayEdgeLights", "SBGR_PAPI"],
        regiao=obb(-289.9, -462.3, 500.0, 150.0, 16.354),
        centrar_em=["SBGR_RwyS_Pavement"],
        nota="Cabeceira da 10R com as marcas de soleira, o numero e as luzes "
             "de borda. Pintura conforme AIP-Brasil / DECEA."),

    "sbgr_taxi_secao": dict(
        campo="sbgr", categoria="superficie",
        rotulo="Taxiway section with centreline (GRU)",
        superficies=["SBGR_TaxiwayPavement", "SBGR_TaxiwayCentrelines"],
        regiao=obb(231.5, -507.0, 320.0, 90.0, 16.354),
        centrar_em=["SBGR_TaxiwayPavement"],
        nota="Trecho de taxiway paralela com o eixo pintado."),

    "sbgr_patio": dict(
        campo="sbgr", categoria="superficie", rotulo="Apron slab (GRU)",
        superficies=["SBGR_ApronConcrete", "SBGR_ApronLaneEdges"],
        regiao=obb(-10.0, 625.0, 300.0, 200.0, 16.354),
        centrar_em=["SBGR_ApronConcrete"],
        nota="Laje de patio com as linhas de faixa, recortada dos poligonos "
             "de patio mapeados."),

    "sbgr_placa_campo": dict(
        campo="sbgr", categoria="superficie",
        rotulo="Field plate - GRU (runways, taxiways, aprons, infield)",
        superficies=["SBGR_RwyN_Pavement", "SBGR_RwyS_Pavement",
                     "SBGR_RunwayShoulders", "SBGR_RunwayMarkings",
                     "SBGR_TaxiwayPavement", "SBGR_TaxiwayCentrelines",
                     "SBGR_ApronConcrete", "SBGR_ApronLaneEdges",
                     "SBGR_AerodromeGround"],
        datum="campo",
        nota="As duas pistas, as taxiways, os patios e o campo verde em volta, "
             "6,1 x 4,8 km. y = 0 e a cabeceira da 10L: uma aeronave em y = 0 "
             "pousa na pista. Sem terreno Copernicus, sem cidade, sem mata."),

    "sbgr_mastro": dict(
        campo="sbgr", categoria="adereco",
        rotulo="Apron floodlight mast, 30 m (GRU)",
        pecas=["SBGR_MastsRing"], regiao=circ(14.5, -691.4, 4.0),
        nota="Mastro de iluminacao de patio. Altura estimada de foto."),

    "sbgr_mastro_trelica": dict(
        campo="sbgr", categoria="adereco",
        rotulo="Lattice floodlight mast, 28 m (GRU)",
        pecas=["SBGR_MastsLattice"], regiao=circ(1.1, -545.5, 6.0),
        nota="Mastro em trelica de quatro pernas."),

    "sbgr_gse_escada": dict(
        campo="sbgr", categoria="veiculo", rotulo="Boarding stairs (GRU)",
        pecas=["SBGR_GSE_White", "SBGR_GSE_Dark"],
        regiao=circ(2208.5, 1108.0, 3.2),
        nota="Escada de embarque da fila remota. Posicao e inferencia; que uma "
             "posicao remota TENHA escada nao e."),

    "sbgr_gse_onibus": dict(
        campo="sbgr", categoria="veiculo", rotulo="Apron bus (GRU)",
        pecas=["SBGR_GSE_Bus", "SBGR_GSE_Dark"],
        regiao=circ(2220.4, 1096.1, 6.5),
        nota="Onibus de patio, 12 m."),

    "sbgr_gse_catering": dict(
        campo="sbgr", categoria="veiculo", rotulo="Catering truck (GRU)",
        pecas=["SBGR_GSE_White", "SBGR_GSE_Dark"],
        regiao=circ(-2.8, 612.7, 4.5),
        nota="Caminhao de comissaria, com a caixa elevatoria."),

    "sbgr_gse_loader": dict(
        campo="sbgr", categoria="veiculo", rotulo="Cargo loader (GRU)",
        pecas=["SBGR_GSE_Yellow", "SBGR_GSE_Dark"],
        regiao=circ(-634.3, 531.4, 4.6),
        nota="Loader de carga da frente de carga."),

    "sbgr_gse_dolly": dict(
        campo="sbgr", categoria="veiculo", rotulo="Dolly train with ULDs (GRU)",
        pecas=["SBGR_GSE_Dolly", "SBGR_GSE_Uld"],
        regiao=rect(-616.0, -598.0, 498.0, 524.0),
        nota="Comboio de dollies com contentores ULD em cima."),

    "sbgr_gse_bowser": dict(
        campo="sbgr", categoria="veiculo", rotulo="Fuel bowser (GRU)",
        pecas=["SBGR_GSE_White", "SBGR_GSE_Dark"],
        regiao=circ(2100.0, 1395.0, 5.2),
        nota="Caminhao-tanque da fila do parque de combustivel."),

    # ------------------------------------------------------------ SDSC ----
    "sdsc_hangar9": dict(
        campo="sdsc", categoria="estrutura", rotulo="Hangar 9 (Sao Carlos MRO)",
        pecas=["SDSC_Hangar9", "SDSC_Hangar9_SpaceFrame", "SDSC_Hangar9_Door",
               "SDSC_Hangar9_Band", "SDSC_Hangar9_Floor",
               "SDSC_Hangar9_Wordmark", "SDSC_Hangar9_Brandmark"],
        nota="Hangar 9 do centro de manutencao LATAM em Sao Carlos - o hangar "
             "de widebody, 133 x 100 x 28 m, com a marca na fachada."),

    "sdsc_mro_hangar": dict(
        campo="sdsc", categoria="estrutura", rotulo="MRO hangar bay (Sao Carlos)",
        pecas=["SDSC_MRO_Hangars", "SDSC_MRO_HangarBay", "SDSC_MRO_HangarDoors",
               "SDSC_MRO_SpaceFrame", "SDSC_MRO_HangarFloor"],
        regiao=circ(960.0, 1809.0, 80.0),
        nota="Uma baia de hangar da linha MRO, com a porta, a trelica e o "
             "piso. A faixa de fachada com a marca e um asset a parte - ela "
             "atravessa 450 m de frente e nao pertence a esta baia."),

    "sdsc_mro_fachada": dict(
        campo="sdsc", categoria="estrutura",
        rotulo="MRO frontage band + LATAM wordmark (Sao Carlos)",
        pecas=["SDSC_MRO_FasciaBand", "SDSC_MRO_Wordmark",
               "SDSC_MRO_Brandmark"],
        nota="A faixa de fachada do centro de manutencao, 450 m, com o "
             "letreiro LATAM. Encoste-a numa fila de baias de hangar."),

    "sdsc_mro_oficinas": dict(
        campo="sdsc", categoria="estrutura", rotulo="MRO workshop spine (Sao Carlos)",
        pecas=["SDSC_MRO_Workshops"], regiao=circ(1009.1, 1803.8, 40.0),
        nota="A espinha de oficinas atras da linha de hangares, 470 m."),

    "sdsc_museu": dict(
        campo="sdsc", categoria="estrutura", rotulo="TAM museum hangar (Sao Carlos)",
        pecas=["SDSC_Museu_TAM"],
        nota="O hangar do Museu TAM, vizinho do centro de manutencao."),

    "sdsc_torre_xadrez": dict(
        campo="sdsc", categoria="estrutura", rotulo="Chequered tower (Sao Carlos)",
        pecas=["SDSC_Chequer_Shaft", "SDSC_Chequer_Cab", "SDSC_Chequer_Roof"],
        nota="A torre quadriculada do meio de campo."),

    "sdsc_hangar_midfield": dict(
        campo="sdsc", categoria="estrutura", rotulo="Midfield hangar (Sao Carlos)",
        pecas=["SDSC_Midfield_Hangar", "SDSC_Midfield_Door",
               "SDSC_Midfield_EndPanels"],
        nota="Hangar de meio de campo com porta e empenas."),

    "sdsc_portao_mro": dict(
        campo="sdsc", categoria="estrutura", rotulo="MRO gate and guard house",
        pecas=["SDSC_MRO_Gate", "SDSC_MRO_GuardHouse", "SDSC_MRO_Boom"],
        nota="Portaria do centro de manutencao: guarita, portao e cancela."),

    "sdsc_cerca": dict(
        campo="sdsc", categoria="adereco", rotulo="Perimeter fence, 60 m run",
        pecas=["SDSC_MRO_PerimeterWall", "SDSC_MRO_PerimeterMesh",
               "SDSC_MRO_PerimeterPosts"],
        regiao=rect(619.0, 681.0, 1543.0, 1547.0),
        nota="Trecho reto de cerca de perimetro - mureta, tela e postes a cada "
             "3 m. Duplique-o em fila para fechar um perimetro."),

    "sdsc_doca_manutencao": dict(
        campo="sdsc", categoria="adereco", rotulo="Maintenance dock + tool carts",
        pecas=["SDSC_MRO_Docks", "SDSC_MRO_ToolCarts"],
        regiao=circ(874.3, 1887.0, 13.0),
        nota="Doca de manutencao com plataformas, escadas e carrinhos de "
             "ferramenta."),

    "sdsc_suporte_motor": dict(
        campo="sdsc", categoria="adereco", rotulo="Engine stands with engines",
        pecas=["SDSC_MRO_Docks", "SDSC_MRO_LooseEngines", "SDSC_MRO_ToolCarts"],
        regiao=circ(990.0, 1958.0, 13.0),
        nota="Berços de motor com motores fora da asa, na frente da oficina."),

    "sdsc_conteineres": dict(
        campo="sdsc", categoria="adereco", rotulo="ISO container row",
        pecas=["SDSC_Containers", "SDSC_ContainersRust"],
        regiao=rect(930.0, 985.0, 1860.0, 1876.0),
        nota="Fila de contentores ISO encostada na linha de hangares. "
             "Fotografado: refs/mro_centro_tecnologico_2009.jpg."),

    "sdsc_mastro": dict(
        campo="sdsc", categoria="adereco", rotulo="Floodlight mast, 16 m (Sao Carlos)",
        pecas=["SDSC_FloodlightMasts"], regiao=circ(1030.9, 2051.0, 4.0),
        nota="Mastro de iluminacao do patio de manutencao."),

    "sdsc_gse_reboque": dict(
        campo="sdsc", categoria="veiculo", rotulo="Tug with towbar",
        pecas=["SDSC_GSE_White", "SDSC_GSE_Yellow", "SDSC_GSE_Chassis"],
        regiao=circ(950.0, 1875.0, 6.0),
        nota="Trator de reboque com a barra. Um trator SEM barra parado no "
             "trem de nariz e o detalhe que denuncia quem nunca pisou num "
             "patio - por isso a barra vem junto."),

    "sdsc_gse_gpu": dict(
        campo="sdsc", categoria="veiculo", rotulo="Ground power unit",
        pecas=["SDSC_GSE_Yellow", "SDSC_GSE_Chassis"],
        regiao=circ(957.4, 1875.0, 2.6), nota="GPU do parque de equipamentos."),

    "sdsc_gse_airstart": dict(
        campo="sdsc", categoria="veiculo", rotulo="Air start unit",
        pecas=["SDSC_GSE_Yellow", "SDSC_GSE_Chassis"],
        regiao=circ(964.8, 1875.0, 2.8), nota="Unidade de partida pneumatica."),

    "sdsc_gse_beltloader": dict(
        campo="sdsc", categoria="veiculo", rotulo="Belt loader",
        pecas=["SDSC_GSE_White", "SDSC_GSE_Chassis"],
        regiao=circ(972.2, 1875.0, 3.6), nota="Esteira de bagagem."),

    "sdsc_gse_van": dict(
        campo="sdsc", categoria="veiculo", rotulo="Service van",
        pecas=["SDSC_GSE_White", "SDSC_GSE_Chassis"],
        regiao=circ(979.6, 1875.0, 3.0), nota="Van de servico."),

    "sdsc_gse_bowser": dict(
        campo="sdsc", categoria="veiculo", rotulo="Fuel bowser",
        pecas=["SDSC_GSE_White", "SDSC_GSE_Chassis"],
        regiao=circ(994.4, 1875.0, 5.0), nota="Caminhao-tanque, 9 m."),

    "sdsc_gse_cherrypicker": dict(
        campo="sdsc", categoria="veiculo", rotulo="Cherry picker",
        pecas=["SDSC_GSE_Yellow", "SDSC_GSE_Chassis"],
        regiao=circ(1001.8, 1875.0, 3.4), nota="Plataforma elevatoria."),

    "sdsc_placa_campo": dict(
        campo="sdsc", categoria="superficie",
        rotulo="Field plate - Sao Carlos (runway, taxiways, apron, infield)",
        superficies=["SDSC_RunwayPavement", "SDSC_RunwayShoulders",
                     "SDSC_RunwayMarkings", "SDSC_TaxiwayPavement",
                     "SDSC_TaxiwayCentrelines", "SDSC_ApronConcrete",
                     "SDSC_MownGrass", "SDSC_AerodromeGround"],
        datum="campo",
        nota="A pista 02/20, as taxiways, o patio e o campo, 2,5 x 3,0 km. "
             "y = 0 e a cabeceira 02; o terreno de Sao Carlos desce 35 m dali "
             "ate o patio do MRO, e isso esta na malha."),

    # ------------------------------------------------------------- SCL ----
    "scl_torre": dict(
        campo="scl", categoria="estrutura", rotulo="Control tower + DGAC block (SCL)",
        pecas=["SCL_Tower_Shaft", "SCL_Tower_Cab", "SCL_Tower_Decks",
               "SCL_Tower_Equipment", "SCL_DGAC_Building"],
        nota="A torre de Santiago, 48 m de fuste, com o bloco da DGAC embaixo."),

    "scl_base_latam": dict(
        campo="scl", categoria="estrutura", rotulo="LATAM base frontage (SCL)",
        pecas=["SCL_LATAM_Buildings", "SCL_LATAM_HangarDoors",
               "SCL_LATAM_WindowBand", "SCL_LATAM_SignBand",
               "SCL_LATAM_Wordmark", "SCL_LATAM_Brandmark"],
        nota="A frente da base LATAM em Santiago, com a faixa de letreiro e a "
             "marca."),

    "scl_terminal_t2": dict(
        campo="scl", categoria="estrutura", rotulo="Terminal 2 (SCL)",
        pecas=["SCL_Terminal_Volumes", "SCL_Terminal_Roofs",
               "SCL_Terminal_Glazing", "SCL_T2_Brise", "SCL_T2_GreenPanels"],
        regiao=rect(-830, -440, -2975, -2640),
        nota="O Terminal 2 com a cobertura ondulada, o brise e os paineis "
             "verdes - 367 x 317 m."),

    "scl_hangar": dict(
        campo="scl", categoria="estrutura", rotulo="Hangar block (SCL)",
        pecas=["SCL_Hangar_SkyAirline"],
        nota="Um hangar de terceiros no lado sul, 98 x 96 x 21 m."),

    "scl_mastro": dict(
        campo="scl", categoria="adereco",
        rotulo="Apron floodlight mast, 30 m (SCL)",
        pecas=["SCL_LightMasts"], regiao=circ(-759.7, -324.7, 4.0),
        nota="Mastro de patio de Santiago."),

    "scl_placa_campo": dict(
        campo="scl", categoria="superficie",
        rotulo="Field plate - Santiago (runways, taxiways, apron, infield)",
        superficies=["SCL_RunwayPavement_17L", "SCL_RunwayPavement_17R",
                     "SCL_RunwayShoulders", "SCL_RunwayMarkings",
                     "SCL_TaxiwayPavement", "SCL_TaxiwayCentrelines",
                     "SCL_ApronConcrete", "SCL_AerodromeGround"],
        regiao=rect(-1760, 440, -4010, 1090), datum="campo",
        nota="As duas pistas paralelas 17L/35R e 17R/35L, as taxiways, o patio "
             "e o campo, 2,2 x 5,1 km. y = 0 e a cabeceira 17L."),
}

# Teto de faces por asset. Acima disto entra um Decimate e o relatorio diz
# quanto caiu. Nenhum asset do catalogo atual passa disto - a checagem existe
# para a peca que alguem adicionar amanha.
TETO_FACES = 60000

DRACO = dict(
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
    export_draco_position_quantization=14,
    export_draco_normal_quantization=10,
    export_draco_texcoord_quantization=12,
)


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------

def argv_apos_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _limpar_temporarios():
    for o in [o for o in bpy.data.objects if o.name.startswith("__tmp_")]:
        bpy.data.objects.remove(o, do_unlink=True)


def _cor_do_material(m):
    """Cor representativa de um material procedural, e de onde ela veio.

    `diffuse_color` e a primeira fonte porque os construtores de cenario a
    definem DE PROPOSITO com a cor base de cada material (foi feita para o
    Workbench). O Principled e a segunda. O cinza 0.8 padrao do Blender e
    tratado como "nao definido"."""
    dc = tuple(round(v, 4) for v in m.diffuse_color[:3])
    padrao = dc == (0.8, 0.8, 0.8)
    base, rough, metal, emiss, forca = None, m.roughness, m.metallic, None, 0.0

    nt = m.node_tree if m.use_nodes else None
    princ = None
    if nt:
        for n in nt.nodes:
            if n.type == "BSDF_PRINCIPLED":
                princ = n
                break
    if princ:
        bc = princ.inputs.get("Base Color")
        if bc is not None and not bc.is_linked:
            v = tuple(round(x, 4) for x in bc.default_value[:3])
            if v != (0.8, 0.8, 0.8):
                base = v
        r = princ.inputs.get("Roughness")
        if r is not None and not r.is_linked:
            rough = r.default_value
        mt = princ.inputs.get("Metallic")
        if mt is not None and not mt.is_linked:
            metal = mt.default_value
        ec = princ.inputs.get("Emission Color")
        es = princ.inputs.get("Emission Strength")
        if ec is not None and es is not None and not es.is_linked \
                and es.default_value > 0.0 and not ec.is_linked:
            e = tuple(round(x, 4) for x in ec.default_value[:3])
            if max(e) > 0.001:
                emiss, forca = e, float(es.default_value)

    if not padrao:
        cor, fonte = dc, "diffuse_color"
    elif base:
        cor, fonte = base, "principled"
    else:
        cor, fonte = (0.55, 0.56, 0.58), "fallback"
    return cor, fonte, float(rough), float(metal), emiss, forca


_ACHATADOS = {}


def _achatar(m, relatorio):
    """Um Principled liso com a cor representativa. glTF exporta isto inteiro."""
    if m is None:
        return None
    if m.name in _ACHATADOS:
        return _ACHATADOS[m.name]
    cor, fonte, rough, metal, emiss, forca = _cor_do_material(m)
    novo = bpy.data.materials.new("flat_" + m.name)
    novo.use_nodes = True
    nt = novo.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*cor, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emiss:
        b.inputs["Emission Color"].default_value = (*emiss, 1.0)
        b.inputs["Emission Strength"].default_value = forca
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    _ACHATADOS[m.name] = novo
    relatorio.setdefault("materiais_achatados", {})[m.name] = {
        "cor": list(cor), "fonte": fonte, "rugosidade": round(rough, 3),
        "emissivo": bool(emiss),
    }
    return novo


# ---------------------------------------------------------------------------
# recorte
# ---------------------------------------------------------------------------

def _dentro(regiao, x, y):
    t = regiao["tipo"]
    if t == "circulo":
        return math.hypot(x - regiao["x"], y - regiao["y"]) <= regiao["r"]
    if t == "retangulo":
        return regiao["x0"] <= x <= regiao["x1"] and regiao["y0"] <= y <= regiao["y1"]
    if t == "obb":
        a = math.radians(regiao["hdg"])
        dx, dy = x - regiao["x"], y - regiao["y"]
        u = dx * math.cos(a) + dy * math.sin(a)
        v = -dx * math.sin(a) + dy * math.cos(a)
        return abs(u) <= regiao["L"] / 2 and abs(v) <= regiao["W"] / 2
    raise ValueError("regiao desconhecida: %s" % t)


def _malha_de(nome, dep):
    """Malha avaliada de um objeto, ja em coordenadas de mundo, como objeto."""
    orig = bpy.data.objects.get(nome)
    if orig is None or orig.type != "MESH":
        return None
    me = bpy.data.meshes.new_from_object(orig.evaluated_get(dep))
    novo = bpy.data.objects.new("__tmp_" + nome, me)
    novo.matrix_world = orig.matrix_world.copy()
    bpy.context.scene.collection.objects.link(novo)
    return novo


def _juntar(objs):
    if not objs:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    alvo = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return alvo


def _cortar_ilhas(obj, regiao):
    """Mantem os componentes conexos cujo centro XY cai na regiao."""
    if regiao is None:
        return
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    vistos, fora = set(), []
    for f in bm.faces:
        if f.index in vistos:
            continue
        pilha, comp = [f], []
        vistos.add(f.index)
        while pilha:
            c = pilha.pop()
            comp.append(c)
            for e in c.edges:
                for g in e.link_faces:
                    if g.index not in vistos:
                        vistos.add(g.index)
                        pilha.append(g)
        vs = [v.co for cf in comp for v in cf.verts]
        cx = (min(v.x for v in vs) + max(v.x for v in vs)) / 2
        cy = (min(v.y for v in vs) + max(v.y for v in vs)) / 2
        if not _dentro(regiao, cx, cy):
            fora.extend(comp)
    bmesh.ops.delete(bm, geom=fora, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()


def _cortar_planos(obj, regiao):
    """Bisseccao pelos quatro planos da regiao - o certo para tapetes."""
    if regiao is None:
        return
    t = regiao["tipo"]
    if t == "circulo":
        planos = None
    elif t == "retangulo":
        planos = [((regiao["x0"], 0, 0), (-1, 0, 0)), ((regiao["x1"], 0, 0), (1, 0, 0)),
                  ((0, regiao["y0"], 0), (0, -1, 0)), ((0, regiao["y1"], 0), (0, 1, 0))]
    else:
        a = math.radians(regiao["hdg"])
        ux, uy = math.cos(a), math.sin(a)
        vx, vy = -math.sin(a), math.cos(a)
        cx, cy, L, W = regiao["x"], regiao["y"], regiao["L"], regiao["W"]
        planos = [
            ((cx + ux * L / 2, cy + uy * L / 2, 0), (ux, uy, 0)),
            ((cx - ux * L / 2, cy - uy * L / 2, 0), (-ux, -uy, 0)),
            ((cx + vx * W / 2, cy + vy * W / 2, 0), (vx, vy, 0)),
            ((cx - vx * W / 2, cy - vy * W / 2, 0), (-vx, -vy, 0)),
        ]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if planos is None:                       # circulo: cai no filtro por face
        fora = [f for f in bm.faces
                if not _dentro(regiao, f.calc_center_median().x,
                               f.calc_center_median().y)]
        bmesh.ops.delete(bm, geom=fora, context="FACES")
    else:
        for ponto, normal in planos:
            bmesh.ops.bisect_plane(
                bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                plane_co=Vector(ponto), plane_no=Vector(normal),
                clear_outer=True, use_snap_center=False)
    bm.to_mesh(obj.data)
    bm.free()


# ---------------------------------------------------------------------------
# um asset
# ---------------------------------------------------------------------------

def montar(slug, spec, campo, pasta, relatorio):
    dep = bpy.context.evaluated_depsgraph_get()
    regiao = spec.get("regiao")

    partes = []
    ausentes = []
    centrar = set(spec.get("centrar_em") or [])
    caixa_centro = None

    def _somar(nome, o):
        """Acumula a caixa das malhas eleitas para definir a origem XY."""
        nonlocal caixa_centro
        if nome not in centrar:
            return
        co = [o.matrix_world @ v.co for v in o.data.vertices]
        if not co:
            return
        b = [min(v.x for v in co), min(v.y for v in co),
             max(v.x for v in co), max(v.y for v in co)]
        caixa_centro = b if caixa_centro is None else [
            min(caixa_centro[0], b[0]), min(caixa_centro[1], b[1]),
            max(caixa_centro[2], b[2]), max(caixa_centro[3], b[3])]

    for nome in spec.get("pecas", []):
        o = _malha_de(nome, dep)
        if o is None:
            ausentes.append(nome)
            continue
        _cortar_ilhas(o, regiao)
        if len(o.data.polygons):
            _somar(nome, o)
            partes.append(o)
        else:
            bpy.data.objects.remove(o, do_unlink=True)
    for nome in spec.get("superficies", []):
        o = _malha_de(nome, dep)
        if o is None:
            ausentes.append(nome)
            continue
        _cortar_planos(o, regiao)
        if len(o.data.polygons):
            _somar(nome, o)
            partes.append(o)
        else:
            bpy.data.objects.remove(o, do_unlink=True)

    if not partes:
        return {"slug": slug, "erro": "regiao vazia: nada sobrou do recorte",
                "ausentes": ausentes}

    alvo = _juntar(partes)
    alvo.name = slug

    # gira o pedaco para o eixo, quando a regiao e orientada
    if regiao and regiao["tipo"] == "obb":
        c = Vector((regiao["x"], regiao["y"], 0.0))
        a = math.radians(-regiao["hdg"])
        ca, sa = math.cos(a), math.sin(a)

        def _girar(x, y):
            dx, dy = x - c.x, y - c.y
            return c.x + dx * ca - dy * sa, c.y + dx * sa + dy * ca

        bm = bmesh.new()
        bm.from_mesh(alvo.data)
        for v in bm.verts:
            v.co.x, v.co.y = _girar(v.co.x, v.co.y)
        bm.to_mesh(alvo.data)
        bm.free()
        if caixa_centro:
            xs, ys = [], []
            for px, py in ((caixa_centro[0], caixa_centro[1]),
                           (caixa_centro[2], caixa_centro[1]),
                           (caixa_centro[0], caixa_centro[3]),
                           (caixa_centro[2], caixa_centro[3])):
                gx, gy = _girar(px, py)
                xs.append(gx); ys.append(gy)
            caixa_centro = [min(xs), min(ys), max(xs), max(ys)]

    # medidas ANTES do datum, no frame do campo
    co = [Vector(v.co) for v in alvo.data.vertices]
    mn = Vector((min(v.x for v in co), min(v.y for v in co), min(v.z for v in co)))
    mx = Vector((max(v.x for v in co), max(v.y for v in co), max(v.z for v in co)))
    origem_bbox = [round((mn.x + mx.x) / 2, 2), round((mn.y + mx.y) / 2, 2)]

    # DATUM: origem no centro XY da caixa; z = 0 na base da peca (ou na
    # cabeceira, para as placas de campo). Depois do export_yup do glTF isto
    # vira "pivo no centro X/Z, base em y = 0" - a mesma convencao da frota.
    z0 = campo["datum_z"] if spec.get("datum") == "campo" else mn.z
    if caixa_centro:
        cx = (caixa_centro[0] + caixa_centro[2]) / 2
        cy = (caixa_centro[1] + caixa_centro[3]) / 2
    else:
        cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    origem_campo = origem_bbox if not caixa_centro else [round(cx, 2), round(cy, 2)]
    desloc = Vector((-cx, -cy, -z0))
    bm = bmesh.new()
    bm.from_mesh(alvo.data)
    for v in bm.verts:
        v.co += desloc
    bm.to_mesh(alvo.data)
    bm.free()

    # materiais achatados
    for i, m in enumerate(alvo.data.materials):
        alvo.data.materials[i] = _achatar(m, relatorio)

    faces0 = len(alvo.data.polygons)
    razao = None
    if faces0 > TETO_FACES:
        mod = alvo.modifiers.new("dec", "DECIMATE")
        mod.ratio = TETO_FACES / faces0
        razao = mod.ratio
        bpy.context.view_layer.objects.active = alvo
        bpy.ops.object.modifier_apply(modifier=mod.name)

    alvo.data.calc_loop_triangles()
    tris = len(alvo.data.loop_triangles)
    co = [Vector(v.co) for v in alvo.data.vertices]
    mn = Vector((min(v.x for v in co), min(v.y for v in co), min(v.z for v in co)))
    mx = Vector((max(v.x for v in co), max(v.y for v in co), max(v.z for v in co)))

    arquivo = os.path.join(pasta, "%s.glb" % slug)
    bpy.ops.object.select_all(action="DESELECT")
    alvo.select_set(True)
    bpy.context.view_layer.objects.active = alvo
    direitos = "%s | %s" % (LICENCAS[spec.get("licenca", "odbl-1.0")]["atribuicao"],
                            MARCAS)
    bpy.ops.export_scene.gltf(
        filepath=arquivo, export_format="GLB", export_apply=True,
        export_yup=True, use_selection=True,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
        export_extras=False, export_copyright=direitos, **DRACO)

    bytes_ = os.path.getsize(arquivo)
    faces = len(alvo.data.polygons)
    n_mat = len(alvo.data.materials)
    bpy.data.objects.remove(alvo, do_unlink=True)

    # glTF: X = Blender X, Y = Blender Z, Z = -Blender Y
    caixa = {
        "min": [round(mn.x, 3), round(mn.z, 3), round(-mx.y, 3)],
        "max": [round(mx.x, 3), round(mx.z, 3), round(-mn.y, 3)],
        "tamanho": [round(mx.x - mn.x, 3), round(mx.z - mn.z, 3),
                    round(mx.y - mn.y, 3)],
    }
    return {
        "slug": slug, "rotulo": spec["rotulo"], "categoria": spec["categoria"],
        "campo": spec["campo"], "licenca": spec.get("licenca", "odbl-1.0"),
        "arquivo": os.path.basename(arquivo), "bytes": bytes_,
        "faces": faces, "faces_origem": faces0, "decimado": razao,
        "triangulos": tris, "vertices": len(co),
        "materiais": n_mat,
        "caixa": caixa,
        "fonte": {
            "blend": campo["blend"],
            "pecas": spec.get("pecas", []),
            "superficies": spec.get("superficies", []),
            "regiao": regiao,
            "origem_no_campo_m": origem_campo,
            "datum": spec.get("datum", "min"),
            "centrar_em": spec.get("centrar_em") or [],
        },
        "nota": spec.get("nota", ""),
        "ausentes": ausentes,
    }


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campo", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--relatorio", required=True)
    ap.add_argument("--assets", default="")
    a = ap.parse_args(argv_apos_dashdash())

    campo = CAMPOS[a.campo]
    os.makedirs(a.saida, exist_ok=True)
    alvos = [s for s in a.assets.split(",") if s] or \
        [s for s, d in CATALOGO.items() if d["campo"] == a.campo]

    relatorio = {"campo": a.campo, "assets": [], "materiais_achatados": {}}
    for slug in alvos:
        spec = CATALOGO[slug]
        _limpar_temporarios()
        try:
            r = montar(slug, spec, campo, a.saida, relatorio)
        except Exception as exc:            # noqa: BLE001 - queremos o motivo
            import traceback
            r = {"slug": slug, "erro": str(exc),
                 "traceback": traceback.format_exc()[-1200:]}
        relatorio["assets"].append(r)
        print("[cenario] %-24s %s" % (slug, r.get("erro") or
              "%d faces, %d bytes" % (r["faces"], r["bytes"])))

    with open(a.relatorio, "w") as f:
        json.dump(relatorio, f, indent=1)
    print("[cenario] relatorio: %s" % a.relatorio)


if __name__ == "__main__":
    main()
