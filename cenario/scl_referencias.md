# SCL — validação por foto da base LATAM em Santiago

Levantamento fotográfico e dimensional do **Aeropuerto Internacional Comodoro Arturo
Merino Benítez (SCL / SCEL)**, Pudahuel, Santiago do Chile, para construir o cenário da
decolagem. A régua declarada pelo dono é um funcionário da LATAM que trabalha ali todo
dia reconhecer o lugar — então cada afirmação abaixo está amarrada a uma foto que eu
abri e olhei, ou a um dado geográfico, e o que eu **não** consegui confirmar está
marcado como tal.

Data do levantamento: 2026-08-18.

---

## 1. Referencial adotado

| item | valor |
|---|---|
| origem | **lat −33.3760915, lon −70.7867106** — cabeceira (threshold) da **pista 17L**, ou seja o ponto onde começa a corrida de decolagem |
| eixos | x = leste, y = norte, z = cima, em metros |
| escala local (calculada, não aproximada) | 1° lat = **110 911,1 m**; 1° lon = **93 054,7 m** na latitude da origem |
| elevação do aeródromo | **474 m** AMSL (SRTM no ponto dá 482 m) |

Por que 17L e não 17R: em SCL a operação é predominantemente para o sul
(vento de sul), e as pistas 17L/17R são as preferenciais para decolagem. O briefing
operacional da OPSGROUP registra ainda que, por restrição de ruído noturno,
**as decolagens usam 17L, não 17R**. Como 17L é a pista *leste* e todo o complexo
(base de manutenção, torre, T1, T2) fica **entre as duas pistas**, numa decolagem de 17L
a base inteira desfila **pela direita do avião**. Isso é o que faz a cena funcionar.

### O que passa pela direita durante a corrida

Projetado sobre o eixo de 17L (rumo **177,40°**), medido do threshold. "Afastamento" é a
distância perpendicular ao eixo. **Tudo fica à direita** — confirmado por cálculo, não por
impressão.

| ponto na corrida | elemento | afastamento lateral |
|---|---|---|
| 58 m | Hangar A da base FACh | 578 m à direita |
| 159 m | Torre de Control FACh (15 m de altura) | 578 m à direita |
| 1 222 m | hangar **LATAM** | 683 m à direita |
| 1 245 m | **Plataforma LATAM** (centro) | 618 m à direita |
| 1 282 m | **Base de Operaciones y Mantenimiento LATAM Airlines** | 719 m à direita |
| 1 746 m | **Torre de Controle DGAC** (65 m) | 756 m à direita |
| 2 243 m | Terminal 1 Nacional | 771 m à direita |
| 2 770 m | Terminal 2 Internacional | 762 m à direita |
| 3 204 m | threshold 35R (fim útil no sentido oposto) | — |

Um A320 rotaciona tipicamente entre 1 600 e 2 000 m de corrida: **o avião sai do chão
praticamente abeam da torre de controle**, com a base LATAM já para trás e o Terminal 1
começando a aparecer. Vale usar isso na animação.

---

## 2. Tabela de fotos

Todas as imagens abaixo estão em `refs/`, todas com licença livre (CC0 / CC BY / CC BY-SA),
**todas redistribuíveis** desde que mantida a atribuição. `refs/manifest.json` traz o
registro legível por máquina (URL da página, URL do original, autor, licença, data, dimensões).

> Nenhuma foto de licença restritiva (JetPhotos, Planespotters, imprensa LATAM) foi
> baixada para o repositório. Onde eu precisei olhar material assim, está citado como
> consulta em §6 e **não** foi copiado para cá.

### 2.1 Hangares e base de manutenção

| arquivo | autor / licença | data | o que valida exatamente |
|---|---|---|---|
| `hangar_sky_2021.jpg` | Corsario CL, CC BY-SA 4.0 | 2021-07-21 | Interior de hangar em SCL visto de dentro, com a porta aberta: **estrutura de treliça metálica escura aparente**, banzos e diagonais, luminárias high-bay penduradas nas treliças, perfil de cobertura de duas águas muito abatido. E, do outro lado do pátio, **o letreiro LATAM iluminado à noite** (recorte ampliado em `refs/_detalhe_letreiro_latam_noite.jpg`, mesmo autor e licença). |
| `hangar_sky_2021_b.jpg` | Corsario CL, CC BY-SA 4.0 | 2021-07-21 | Mesmo hangar, A320 dentro: dá a **escala vão × avião** — um A320 (37,6 m) ocupa um vão com folga confortável. |
| `latam_a320neo_landing_scel_2025.jpg` | Robert Motecinos Holda, **CC0** | 2025-08-31 | A320 CC-BAC da LATAM pousando em SCEL com **um hangar logo atrás**: cobertura em **arco abatido (curva contínua, não duas águas)**, fechamento em chapa metálica nervurada cinza-clara, testeira/rufo branco acompanhando a curva do telhado. Também dá a paleta da serra ao fundo. *Não consegui identificar qual edifício é* — ver §7. |
| `fach_base_2010_phillipc.jpg` | Phillip Capper, CC BY 2.0 | 2010-12-28 | Base da FACh no extremo norte do campo: hangares de **duas águas em chapa azul-marinho escura**, testeiras claras, chão de terra vermelho-ocre na frente, cordilheira baixa e marrom atrás. Esse é o cluster "Hangar A…G" do OSM — **não é LATAM**, é Força Aérea. Serve para não errar de bloco. |
| `refs/_mapa_mro_overlay.png` | derivado (ver §6) | — | Planta do bloco de manutenção com as pegadas do OSM sobrepostas à imagem de satélite, com grade métrica local a cada 100 m. |

### 2.2 Terminal

| arquivo | autor / licença | data | o que valida exatamente |
|---|---|---|---|
| `t2_panorama_anfiteatro.jpg` | Ivotoledo45, CC BY-SA 4.0 | 2022-07-19 | **A melhor foto do conjunto.** Panorâmica 10754×2745 do Terminal 2 pelo lado terra: **cobertura ondulada** contínua em metal cinza-escuro, com beiral longo em balanço; fachada em painéis **verde-claro (sage/menta)** alternando com **brises laranja-cobre** e vidro; passarelas e rampas em concreto e aço branco. Ao fundo, montanhas com neve (julho = inverno). |
| `t2_exterior_2022.jpg` | Corsario CL, CC BY-SA 4.0 | 2022-09-01 | T2 ao anoitecer, do viaduto de acesso: ilumina como a fachada se lê no escuro. |
| `t1_landside_spaceframe.jpg` | Nanosmile, CC BY-SA 2.0 de | — | Terminal 1 pelo lado terra: **estrutura tubular tipo space-frame com mãos-francesas em V**, cortina de vidro, beiral plano com duto branco aparente. Ônibus Centropuerto azul. |
| `apron_2022_sky_latam.jpg` | Aeveraal, CC BY-SA 4.0 | 2022-02-11 | Terminal 1 **pelo lado ar**: cortina de vidro com montantes cinza, fascia metálica clara, telhado plano com condensadoras aparentes, ponte de embarque. **Mastros de iluminação altos, brancos, com fuste helicoidal/estriado** — detalhe muito característico. Contêineres AKE marcados "LA" (LATAM). Fevereiro = verão, morro ao fundo marrom sem neve. |
| `spotting_2012_otherside.jpg` | Aeroprints.com, CC BY-SA 3.0 | 2012-10-19 | Vista do terminal **através do campo**, do outro lado das pistas: é literalmente o enquadramento da cena. Mostra o terminal como volume baixo e comprido, a fileira de mastros brancos, os aviões alinhados — e **quanta névoa há**: a 1–1,5 km o terminal já perde contraste e satura pouco. |
| `takeoff_scl_a320.jpg` | Ralphito, CC BY-SA 3.0 | — | A320 da LAN rotacionando com o terminal e o pátio atrás. Composição-alvo da animação. |
| `scl01`…`scl10.jpg` | Vmzp85, CC BY-SA 4.0 | 2022-09 | Interiores do T2 e T1. Só valem para o T2: **colunas em V ramificadas feitas de feixes de tubos metálicos sobre base tronco-cônica de concreto**, forro de lâminas metálicas. Não aparecem numa cena externa, mas registram a linguagem do prédio. `scl03.jpg` mostra o lado terra por fora. |

### 2.3 Torre de controle

| arquivo | autor / licença | data | o que valida exatamente |
|---|---|---|---|
| `apron_panoramio_2011.jpg` | Nelson Pérez, CC BY-SA 3.0 | 2011-03-05 | **A única foto boa da torre.** Fuste de **concreto aparente**, seção retangular com cantos chanfrados, afinando levemente para cima; **galeria inferior aberta com guarda-corpo**, depois a **cabine envidraçada com os vidros inclinados para fora**, depois **laje de cobertura com guarda-corpo** levando o **radar de barra horizontal** e antenas chicote. Detalhe marcante: **um pórtico de aço treliçado externo (X + montantes inclinados) encostado numa face do fuste**, pintado de cinza-claro. Concreto cinza envelhecido com escorrimento escuro. |

### 2.4 Pátio, pontes de embarque e equipamento de solo

| arquivo | autor / licença | data | o que valida exatamente |
|---|---|---|---|
| `ctj_5365.jpg` | Christer T Johansson, CC BY 3.0 | 2016-12-22 | **As pontes de embarque de SCL são azul-royal com "Banco de Chile" em letra cursiva branca** na lateral. Esse é *o* detalhe que um funcionário reconhece na hora. Também: rebocadores **"ANDES" azul-escuro** com faixa vermelha/branca, carrinhos de bagagem brancos com gradil, cones laranja, caminhão branco com xadrez vermelho e o dizer "MANTENGA EL FRENTE DE ESTE VEHÍCULO LIBRE". Piso do pátio em **lajes de concreto claro com juntas visíveis**, linhas amarelas de rolamento e vermelhas de restrição. |
| `ctj_5361.jpg`, `ctj_5369.jpg`, `ctj_5372.jpg` | Christer T Johansson, CC BY 3.0 | 2016-12-22 | Mais ângulos das mesmas pontes azuis "Banco de Chile" e do GSE. |
| `losa_carga_2015.jpg` | Omnespsx, CC BY-SA 4.0 | 2015-08-28 | Pátio de carga com um 767F da Tampa Cargo; escadas e equipamento de rampa. |
| `ramp_2010_phillipc.jpg` | Phillip Capper, CC BY 2.0 | 2010-12-28 | Fileira de caudas no pátio com os mastros de iluminação altos; dá o ritmo do espaçamento entre posições. |
| `apron_2010_phillipc.jpg`, `lan_a320_2012_ramp.jpg`, `lan_a320_2012_ramp_b.jpg`, `lan_767_2012_ramp.jpg` | ver `manifest.json` | 2010/2012 | Aviões em pátio e rolagem; contexto de fundo. |
| `latam_787_scl_2017.jpg` | Sky KoreSCL, CC BY-SA 4.0 | 2017-02-22 | 787-9 da LATAM em SCL no crepúsculo — referência de cor de luz de fim de tarde no campo. |

### 2.5 Cordilheira ao fundo

| arquivo | autor / licença | data | o que valida exatamente |
|---|---|---|---|
| `latam_a321_2022.jpg` | Maurice Becker, CC BY-SA 4.0 | **2022-06-12** (inverno) | **A foto de calibração da cordilheira.** A321 CC-BEA na pista com a serra alta atrás: **neve na parte de cima**, rocha azul-acinzentada embaixo, e uma **camada de névoa horizontal muito forte** que clareia e dessatura a montanha da base para cima. Contraste baixíssimo — a serra é quase uma silhueta azul-pálida com topo branco. |
| `latam_a321_2018.jpg` | Sky KoreSCL, CC BY-SA 4.0 | 2018-06-16 (inverno) | Serra próxima, marrom, **sem neve** — mostra que nem toda crista fica branca no inverno; a neve é só nas cotas altas. |
| `lan767_2010_phillipc.jpg` | Phillip Capper, CC BY 2.0 | 2010-12-28 (verão) | **Verão: nenhuma neve visível**, serra inteiramente marrom-acinzentada. |
| `aerial_2014.jpg` | Ivotoledo45, CC BY-SA 4.0 | 2014-11-30 | Vista aérea do campo entre nuvens; útil para a leitura geral do traçado, mas com bruma pesada. |

---

## 3. Como cada elemento se parece — resumo para modelar

### 3.1 Base de manutenção LATAM

Fica **entre as duas pistas**, a oeste de 17L. O OSM nomeia o edifício principal
**"Base de Operaciones y Mantenimiento LATAM Airlines"** (César Lavín Toro 2198,
Pudahuel) e um segundo volume simplesmente **"LATAM"** (tag `building=hangar`).

Medidas em referencial local (caixa mínima orientada, do OSM; conferidas contra a
imagem de satélite — ver §5):

| edifício | centro (x, y) m | caixa m | área m² |
|---|---|---|---|
| Base de Operaciones y Mantenimiento LATAM Airlines | (−660, −1313) | 161,9 × 123,1 | 13 447 |
| hangar "LATAM" | (−627, −1252) | 88,5 × 81,7 | 5 381 |
| anexo sem nome | (−635, −1142) | 78,2 × 51,2 | 2 845 |
| anexo sem nome | (−648, −1058) | 50,3 × 46,9 | 2 358 |
| **Plataforma LATAM** (pátio) | (−561, −1272) | 471,7 × 307,2 | **82 617** |

Aparência, do que dá para ver:

- **Cobertura clara** (branco-sujo a cinza muito claro) vista de cima, com fiadas
  regulares de lanternins/exaustores escuros. O hangar "LATAM" tem uma **junta central
  longitudinal dividindo a cobertura em dois panos** → leitura de **dois vãos**, cada um
  da ordem de **45–47 m**, o que aceita um A320 (envergadura 35,8 m) por vão com folga.
  Medi o volume na imagem de satélite em duas ampliações independentes (z18 e z19) e deu
  **90–94 m × 61–65 m**, diferente do polígono do OSM (88,5 × 81,7 m) — o polígono do OSM
  parece incluir um apêndice ao sul. **Use ≈ 92 × 63 m** e trate o valor do OSM como
  divergência conhecida.
- **Letreiro:** o edifício de escritórios da LATAM tem um **letreiro grande e iluminado
  com a palavra LATAM em branco e a marca (o feixe de traços coral/vermelho) à esquerda**,
  montado no alto da fachada, acima de uma faixa de janelas acesas de 2–3 pavimentos.
  Confirmado na foto noturna `hangar_sky_2021.jpg`.
- **Estrutura de hangar em SCL** (do interior fotografado): **treliça metálica aparente
  escura**, pórticos com banzos e diagonais, cobertura de duas águas bem abatida, porta
  de correr de vão largo, luminárias high-bay penduradas.
- **Altura: não confirmada.** Ver §7.

Vizinhos que estão no mesmo bloco e não devem ser confundidos com a LATAM:
**Base de Mantenimiento Sky Airline** (−822, −1659), 95,5 × 93,1 m, com o **logotipo "S"
da Sky pintado no telhado em magenta/vinho** (visível no satélite); **Aerocardal**
(−766, −1240), 93,0 × 36,8 m, com um telhado muito característico de **painéis
retangulares claros em duas colunas × sete fiadas**; **American Airlines** (−1072, −1296);
**Aviasur**, **Jetex**, **Santiago FBO**, **ENAER**; e **dois hangares de telhado azul
cobalto com faixas brancas** em (−981, −968) e (−982, −1040).

### 3.2 Terminais

| terminal | centro (x, y) m | caixa m | inaugurado |
|---|---|---|---|
| Terminal 2 Internacional (processador central) | (−636, −2802) | 367 × 309 | **2022-02-28** |
| Terminal 1 Nacional | (−669, −2276) | 480 × 97 | 1994-02-14 |
| Espigón C "Isla de Pascua" | (−942, −2645) | 296 × 103 | 2018-12-18 |
| Espigón E "Lagos" | (−926, −3000) | 296 × 101 | 2019-09-12 |
| Espigón D "Desierto de Atacama" | (−371, −2618) | 238 × 102 | 2021-07 |
| Espigón F "Patagonia" | (−357, −2974) | 240 × 102 | 2024 |
| Espigón B "Valle Central" | (−370, −2263) | 210 × 94 | 1994 |
| Espigón A "Costa" | (−1007, −2283) | 199 × 81 | 2024-09 |

Qual é qual: **T1 = doméstico** (o prédio de 1994, space-frame tubular, espigões A e B);
**T2 = internacional** (2022, cobertura ondulada verde/laranja, espigões C, D, E, F).
Os espigões são numerados **A a F** e cada um tem nome de região do Chile — um
funcionário chama pelo nome, não pela letra.

Linguagem visual do T2: **cobertura ondulada em metal cinza-escuro com beiral longo**,
fachada em **painéis verde-menta + brises laranja-cobre + vidro**, e no interior
**colunas em V ramificadas de feixes de tubos sobre base de concreto**. Do lado ar, os
espigões são caixas alongadas de ~100 m de largura com a mesma cobertura ondulada.

Linguagem do T1: **space-frame tubular branco/cinza com mãos-francesas em V**, cortina
de vidro, beiral plano, telhado com condensadoras aparentes.

### 3.3 Torre de controle

- **Altura: 65 m**, inaugurada em **15 de dezembro de 1999** — fonte: DGAC (o próprio
  operador). O OSM diz 60 m e 10 pavimentos; **fique com os 65 m da DGAC** e trate o
  número do OSM como divergência conhecida.
- Posição: **(−676,5, −1779)** no referencial local; planta ~15,9 × 15,8 m.
- Forma (da foto): fuste de **concreto aparente**, seção retangular de cantos chanfrados,
  afinando de leve para cima; **galeria aberta com guarda-corpo** logo abaixo da cabine;
  **cabine envidraçada com vidros inclinados para fora**, mais larga que o fuste, planta
  octogonal; **laje de cobertura com guarda-corpo** carregando **um radar de barra
  horizontal**, antena chicote e equipamentos pequenos.
- Detalhe que dá identidade: **um pórtico treliçado de aço externo (X mais montantes
  inclinados), cinza-claro, encostado numa face do fuste**, descendo da cabine.
- Cor: concreto cinza médio, envelhecido, com escorrimento escuro; aço claro; vidro
  esverdeado com reflexo azulado.
- Existe uma segunda torre, **"Torre de Control FACh"**, em (−570, −185), só **15 m**,
  3 pavimentos — no extremo norte, junto aos hangares azuis da Força Aérea.

### 3.4 Pátio, pontes e equipamento de solo

- **Pontes de embarque azul-royal com "Banco de Chile" em cursiva branca.** Sem isso a
  cena não é SCL.
- Piso: **lajes de concreto claro, quase branco-acinzentado, com juntas bem marcadas**;
  linhas **amarelas** de rolamento/posição, linhas **vermelhas** de restrição, faixas
  brancas.
- GSE: rebocadores **ANDES azul-escuro** com faixa vermelha e branca, carrinhos de
  bagagem brancos de gradil, dollies planos, contêineres **AKE** claros com marcação
  "LA", cones laranja, blocos de concreto tipo jersey.
- **Mastros de iluminação altos e brancos com fuste estriado/helicoidal** — aparecem em
  fila ao longo do pátio e são muito visíveis na silhueta.
- 208 posições de estacionamento e 65 pontes de embarque estão mapeadas no OSM
  (`refs/_medidas_osm_local.json`), com as siglas reais (A01…A16, B01…B09, C1…C11,
  D1…D10, E1…E12, F1…F9, W1…W9).

### 3.5 Cordilheira

Dois métodos independentes, e eles concordam:

**(a) Cálculo a partir do DEM.** Perfil do horizonte traçado do SRTM 30 m
(OpenTopoData) a partir da origem, no setor de azimute 40°–140°, passo de 2°, alcance
3–109 km, com correção de curvatura terrestre e refração (k = 0,13). Resultado em
`refs/_skyline_leste_dem.csv`:

| | valor |
|---|---|
| ângulo de elevação da crista, mínimo | **1,95°** (az 132°) |
| ângulo de elevação da crista, máximo | **4,89°** (az 74°, a 55,5 km, cume 5 432 m — **Cerro El Plomo**, 5 424 m nas cartas) |
| média sobre o setor leste | **3,46°** |
| primeira crista (serra próxima, Sierra de Ramón) | 2–4°, a **33–40 km** |

**(b) Medição na foto** `latam_a321_2022.jpg`, usando o A321 (44,51 m de comprimento)
como escala: a crista nevada fica a **≈ 4,8°** acima do horizonte. Bate com o DEM.

> Cuidado que me custou tempo: se você usar a distância focal do EXIF (117 mm eq. 35 mm)
> como se a imagem fosse quadro cheio, dá **6,0°** — errado, porque a foto foi recortada
> antes de ser publicada. A razão entre ângulos dentro da mesma foto é confiável; o valor
> absoluto tirado do EXIF não é. **Ancore no DEM.**

Aparência:

- **Escala angular: a cordilheira ocupa uma faixa de só 2° a 5° acima do horizonte.**
  É baixa. O erro clássico é modelar montanha grande demais.
- **Distância: 33–55 km.** A serra próxima (Sierra de Ramón, Cerro Provincia,
  Cerro San Ramón) em 33–40 km; os grandes (El Plomo) em 55 km.
- **Cor: azul-acinzentada pálida, muito dessaturada.** A perspectiva atmosférica em
  Santiago é forte — há uma camada de bruma horizontal que clareia a montanha da base
  para cima e apaga o contraste. Mesmo o terminal a 1,5 km já perde saturação
  (`spotting_2012_otherside.jpg`).
- **Neve — depende da estação, e isto precisa ser uma decisão explícita da cena:**
  - **inverno (jun–set)**: neve no terço superior. Em `latam_a321_2022.jpg` (12 de junho)
    a neve começa por volta de **3,5–3,6°** de elevação e vai até a crista em ~4,8° —
    ou seja, **branco só nos ~25% superiores da altura angular da serra**.
  - **verão (dez–mar)**: **sem neve visível** (`lan767_2010_phillipc.jpg`, 28 de dezembro).
  - nem toda crista fica branca no inverno: as serras baixas continuam marrons
    (`latam_a321_2018.jpg`, junho).
- Solo do entorno do campo: **terra marrom-ocre seca com grama rala**, faixas
  verde-oliva junto às pistas; no inverno a grama fica mais verde.

---

## 4. Pistas

| pista | de (x,y) m | para (x,y) m | rumo | comprimento |
|---|---|---|---|---|
| **17L/35R** | threshold 17L **(0, 0)** | threshold 35R **(145,1, −3200,7)** | **177,40°** | 3 204 m entre thresholds; mais **542 m** de pavimento mapeados ao sul do threshold 35R (total ≈ 3 746 m, batendo com a tag `length=3748` do OSM) |
| **17R/35L** | (−1583,5, +458,6) | (−1413,1, −3337,6) | 177,43° | 3 800 m (OSM) |

As duas pistas são praticamente paralelas e **separadas por ~1 560 m**, com todo o
complexo de terminais e manutenção no meio.

Divergência registrada: a DGAC descreve a segunda pista (17R) como tendo **4 000 m**
concluída em 2005; o OSM traz 3 800 m. Não resolvi qual é a medida homologada atual.

Auxílios visuais no referencial local: **PAPI 17L** em **(74,5, −397,6)**; PAPI 35R em
(69,0, −2801,5); birutas em (−31,7, −1899,8), (−950,7, −1438,3) e (−877,0, −1499,9).

---

## 5. Verificação cruzada geometria × imagem

Sobrepus as pegadas do OpenStreetMap à imagem de satélite Esri World Imagery e conferi
o alinhamento: `refs/_mapa_mro_overlay.png` (bloco de manutenção, grade a cada 100 m) e
`refs/_mapa_campo_overlay.png` (campo inteiro, grade a cada 500 m, com a corrida de
decolagem de 17L marcada de 500 em 500 m). O alinhamento é bom — os polígonos caem em
cima dos edifícios.

**Ressalva importante:** o mosaico Esri é de datas mistas e, na área do Terminal 2,
parece anterior à inauguração de 2022 — aparece obra. Para o T2 confie nas fotos
(`t2_panorama_anfiteatro.jpg`, `t2_exterior_2022.jpg`), não no satélite.

Esses dois PNGs são **derivados de imagem Esri World Imagery, que não é livre**. Estão
aqui como apoio de trabalho. **Não publique esses dois arquivos** — ver §8.

---

## 6. Fontes consultadas

**Dados geográficos**
- OpenStreetMap via Overpass API, extraído 2026-08-18 — pistas, hangares, terminais,
  torres, pátios, posições de estacionamento, pontes. Licença **ODbL**.
- SRTM 30 m via **OpenTopoData** (`api.opentopodata.org`) — 9 333 pontos amostrados para
  o perfil do horizonte. SRTM é de **domínio público** (NASA/USGS).
- Esri World Imagery (`server.arcgisonline.com`) — imagem de satélite, **apenas como
  verificação visual**. Termos restritivos, não redistribuível.

**Texto**
- DGAC (Dirección General de Aeronáutica Civil, Chile), "La historia del Aeropuerto
  Arturo Merino Benítez" — https://www.dgac.gob.cl/la-historia-del-aeropuerto-arturo-merino-benitez/
  → torre de 65 m inaugurada em 15/12/1999; segunda pista de 4 000 m concluída em 2005;
  terminal internacional de 25 000 m² inaugurado em 14/02/1994.
- OPSGROUP, "Santiago, Chile – Temporary Runway Changes" — https://ops.group/blog/santiago-chile-temporary-runway-changes/
  → por restrição de ruído noturno, decolagens usam 17L e não 17R.
- LATAM Airlines, "Centro de Mantenimiento en Santiago: 30 años" —
  https://www.latamairlines.com/cl/es/vamos/volar/aviacion/centro-mantenimiento-santiago
  → **não consegui abrir** (HTTP 403). Ficou como pendência.

**Fotos** — todas de Wikimedia Commons, detalhadas em `refs/manifest.json`.

---

## 7. O que eu não consegui

1. **Altura dos edifícios da base LATAM.** Nenhuma fonte traz. Tentei calibrar pelas
   sombras do satélite usando a torre de 65 m como referência, mas o mosaico Esri é de
   datas mistas e não deu para fixar a elevação solar com confiança — o número sairia
   inventado, então **não estou dando número**. Sugestão para quem for modelar: hangar de
   vão ~45 m para A320 costuma ter **18–25 m** de altura livre de porta; use isso como
   faixa declarada, não como medida.
2. **Fachada da base LATAM à luz do dia.** Só consegui o letreiro à noite. Cor das
   paredes, material do fechamento e número exato de portas de hangar continuam sem
   confirmação fotográfica direta. **Isto é a maior lacuna** e é justamente o que o
   funcionário mais reconhece.
3. **Identidade do hangar de telhado em arco** que aparece atrás do CC-BAC em
   `latam_a320neo_landing_scel_2025.jpg`. A forma está documentada; qual edifício é, não.
4. **Comprimento homologado atual de 17R** (3 800 vs 4 000 m).
5. **Nenhuma foto do lado ar do Terminal 2** com licença livre. Tudo que achei do T2 é
   lado terra ou interior. Para a cena, o que se vê da pista é justamente o lado ar dos
   espigões C/D/E/F — está inferido da forma em planta e da linguagem do lado terra,
   **não validado por foto**.
6. Wikimedia Commons **não tem nenhuma foto** com a base de manutenção da LATAM como
   assunto. Busquei por categoria e por texto livre.

---

## 8. Licenças e o que pode ser publicado

| arquivo | pode redistribuir? | condição |
|---|---|---|
| todos os **40 `.jpg`** em `refs/` | **sim** | atribuir autor + licença conforme `refs/manifest.json`; CC BY-SA exige compartilhar derivados na mesma licença |
| `refs/manifest.json`, `refs/_medidas_osm_local.json` | sim | dados do OSM → **ODbL**, citar "© OpenStreetMap contributors" |
| `refs/_skyline_leste_dem.csv` | sim | derivado de SRTM (domínio público) |
| `refs/_mapa_campo_overlay.png`, `refs/_mapa_mro_overlay.png` | **NÃO** | contêm imagem **Esri World Imagery**, licença restritiva. Uso interno de verificação. Se o repositório for público, **apague ou substitua por uma versão só com os vetores do OSM sobre fundo liso.** |

Detalhe da licença por foto (`CC0` / `CC BY 2.0` / `CC BY 3.0` / `CC BY-SA 2.0 de` /
`CC BY-SA 3.0` / `CC BY-SA 4.0`), com URL da página no Commons e URL do arquivo original,
está em `refs/manifest.json`. Duas fotos são de fotógrafos que pedem crédito nominal
explícito: **Christer T Johansson** (as quatro `ctj_*`) e **Phillip Capper**
(as quatro `*_phillipc`).
