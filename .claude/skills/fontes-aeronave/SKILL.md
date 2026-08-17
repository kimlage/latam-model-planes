---
name: fontes-aeronave
description: Levantar as fontes de um avião antes de modelar — documento dimensional oficial do fabricante (Airbus ACAP / Boeing APR), fotos de referência da matrícula LATAM específica, e CAD/modelos 3D abertos que sirvam de referência de blocking. Use SEMPRE que precisar de dimensões, desenhos cotados, fotos de referência ou modelos existentes de uma aeronave: "acha as medidas do 777", "onde tem o desenho do 767", "tem CAD pronto desse avião?", "preciso de fotos da cauda", "quais as dimensões reais". Use também antes de começar qualquer avião novo e sempre que o modelo estiver divergindo da realidade e a causa puder ser falta de dado. Cobre licenciamento — o que pode virar malha e o que só pode virar referência.
---

# Fontes de uma aeronave

Modelo fiel começa em documento, não em Blender. Esta skill é sobre conseguir
o dado — e sobre não se contaminar com fonte que não pode ser usada.

## Passo zero: olhe o avião

**Antes de qualquer outra coisa, busque fotos da matrícula real e olhe.** Não é
a etapa de validação no fim do pipeline — é a primeira, e leva um minuto:
`WebSearch` por "<companhia> <tipo> <matrícula>", ou JetPhotos / Planespotters /
Wikimedia Commons. Se o dono já mandou uma foto, essa é a fonte de maior
autoridade que existe no projeto.

O motivo é concreto. No 787-9 o `spec_b789.json` descrevia uma echarpe índigo
descendo da deriva pelo casco até o tailcone. Esse texto atravessou
fotogrametria, medição de desenho a 600 dpi, dois workflows de pesquisa e uma
rodada de verificação adversarial — e ninguém pegou. Foram gastas horas
refinando o formato dessa echarpe: limitando por z, depois por ângulo, depois
com mergulho local para não apagar a matrícula. **A primeira foto do Google
mostrou que a fuselagem do CC-BGK é inteiramente branca e o índigo só existe na
deriva.** A echarpe não existia. Todo aquele refino foi ajuste fino da coisa
errada.

Duas consequências que valem para qualquer aeronave nova:

- **Prosa não substitui foto**, mesmo quando a prosa veio de medição. Uma
  descrição textual é uma leitura de segunda mão; a foto é o avião.
- **Quando spec e foto discordarem, a foto ganha** — e o spec é corrigido na
  hora, com o motivo escrito, senão o erro volta na próxima aeronave que
  derivar dele.

O inventário já levantado e verificado das 12 variantes da frota LATAM está em
[FONTES-FROTA.md](FONTES-FROTA.md): URL oficial por tipo, status de
verificação, CAD aberto útil e estratégia recomendada. **Comece sempre por ele.**
Se a aeronave pedida está lá, a pesquisa já foi feita — só confirme que a URL
ainda responde e siga. Se não está, pesquise e **acrescente a linha ao arquivo**,
porque o próximo avião vai precisar.

## A hierarquia das fontes

Nem toda fonte tem o mesmo peso. Misturar níveis é como o modelo fica errado.

**1. Documento dimensional do fabricante — a verdade.**
Airbus publica o *ACAP* (Aircraft Characteristics — Airport & Maintenance
Planning); Boeing publica o equivalente como *Airplane Characteristics /
APR* (ex.: D6-58333 para o 787). Ambos são públicos, gratuitos e trazem
3-views cotados em CAD vetorial, além de posições de portas, trem, motores e
envelopes de visibilidade do cockpit. Toda cota do modelo deve rastrear até
aqui.

**2. SRM/AMM e tabelas de cavernas (FR/STA) — estrutura interna.**
Dão o espaçamento real das cavernas, que é o que faz o casco ficar liso pelo
motivo certo (ver `casco-parametrico`). Nem sempre disponível; quando estiver,
vale muito.

**3. Fotos da matrícula específica — a pintura e o acabamento.**
O ACAP não diz onde a echarpe índigo cruza a porta 2. Isso se mede em foto.

**4. CAD/modelos abertos — só blocking e conferência de silhueta.**
Nunca malha-base. Ver "Licenças" abaixo.

## Baixar o documento oficial

Os PDFs passam de 10 MB — WebFetch não dá conta. Baixe com `curl` direto para a
pasta da aeronave:

```bash
curl -L -o "boeing 787-9/B787_APR_boeing.pdf" "<url-do-APR>"
```

Notas de estabilidade que já custaram tempo: a Airbus migrou a família A320 para
o CDN `mediaassets` (as URLs rotacionam — o ponto de entrada estável é a página
*Aircraft Characteristics* do site da Airbus); a Boeing moveu os ACAPs para
`content/dam/boeing/v2/airports/acaps/` e os caminhos antigos dão 404. Se um link
do FONTES-FROTA.md quebrar, procure pela página de entrada, não pelo arquivo.

Confirme que baixou o que esperava antes de gastar tempo rasterizando: tamanho
plausível, e o Read do PDF nas páginas de 3-view mostrando o avião certo.

Um único documento costuma cobrir a família inteira (o AC_A320 cobre ceo e neo
com blocos "ON A/C"; o D6-58333 cobre -8/-9/-10 com 3-views separados). Mas a
família A320 tem **um documento por membro** — o AC_A320 não cobre A319 nem
A321.

## Fotos de referência

Peça ou busque fotos da **matrícula que vai ser replicada**, não do tipo em
geral. A livery LATAM mudou entre 2016 e hoje, e o mesmo avião tem variações
documentadas: o PT-TMN saiu de fábrica com a matrícula em letras brancas dentro
do índigo e hoje voa com matrícula índigo sobre branco. Quando a foto do dono
divergir do que você achou na internet, **a foto do dono manda** — é ela que
define o alvo.

O que uma boa fonte de foto precisa ter, em ordem de utilidade:

- **perfil puro, resolução alta** (JetPhotos em 1920 px serve): é onde a
  fotogrametria funciona, porque a projeção é quase ortográfica no meio da
  fuselagem;
- **ângulo elevado** (de terminal ou passarela): mostra o dorso, onde a echarpe
  nasce;
- **vista de baixo, em decolagem**: única maneira de resolver o ventre, que
  quase nunca aparece;
- **close do nariz e da cauda**: para para-brisa e sash.

Registre a URL de cada foto usada numa medição, dentro do `spec_*.json` — quando
alguém questionar uma cota daqui a um mês, a resposta precisa estar no arquivo.

Para medir a partir dessas fotos (calibração, incerteza, o que é confiável e o
que não é), veja `extrair-cotas`, seção de fotogrametria.

## CAD e modelos 3D existentes

Eles são úteis — mas para uma coisa só: **conferir se você entendeu a forma**.
Silhueta, onde o trem recolhe, como o pylon encontra a asa, proporção do
raked wingtip. Nunca para virar a malha do modelo.

Duas razões. A primeira é fidelidade: modelo de terceiro carrega os erros do
terceiro, e você não tem como saber quais são sem conferir contra o ACAP — e
se você vai conferir tudo contra o ACAP, modele a partir do ACAP. A segunda é
licença.

Fontes que aparecem com frequência e como tratá-las:

| Fonte | Licença típica | Como usar |
|---|---|---|
| FlightGear (GitHub) | GPL — viral | Referência de blocking de trem/portas/cockpit. Nunca copiar malha. |
| Sketchfab | loteria de selos CC (muitos NC/ND) | Conferência de silhueta, **depois de checar o selo do modelo específico**. |
| GrabCAD | não-comercial, sem redistribuição | Só olhar. Qualidade irregular. |
| OpenVSP Airshow | geometria paramétrica limpa | Excelente cross-check independente das curvas extraídas do raster. |
| CGTrader "free" | royalty-free, uso pessoal | Prototipar aplicação de livery, no máximo. |

Uso pessoal não é bloqueado por nada disso, mas o projeto tem destino de
portfólio e vídeo. Malha contaminada por GPL ou NC hoje vira problema de
publicação depois, e não dá para "descontaminar" um casco. A regra do projeto é
simples e vale a pena manter: **ACAP como fonte de verdade dimensional; abertos
só como referência de blocking/silhueta, nunca como malha-base.**

## Delegar a pesquisa a agentes

O que funcionou muito bem foi rodar a pesquisa como workflow de agentes em
paralelo com **schema estruturado de saída** — cada agente devolve um objeto
com números, não prosa. O ganho não é velocidade: é que o schema força o agente
a entregar coordenadas em metros no referencial da aeronave, em vez de
"o para-brisa é bem inclinado".

O que faz um schema render:

- **declare o referencial no próprio texto do campo** — "x=0 na ponta do nariz
  indo para trás, z=0 na meia-altura da seção constante, metros";
- **peça polígonos, não adjetivos** — `corners_xz: [[x,z], ...]` fechando o
  contorno;
- **peça a validação junto** — um campo pedindo com quais cotas conhecidas o
  resultado foi cruzado, e a incerteza estimada;
- **peça o que distingue este avião de um parecido** — "o que faz ler como A320
  e não 737" extrai o detalhe que a prosa genérica esconde.

Esses workflows entregaram a geometria calibrada do para-brisa do A320, a tabela
de cavernas FR1–FR12, a fotogrametria completa da cauda do PT-TMN e a livery
medida do CC-BGK. Foi assim que o `spec_*.json` de cada avião nasceu.

Confie, mas confira: um workflow entregou "comprimento 62,00 m" para o 787-9
porque leu a cota do solo em vez do comprimento total — o valor certo é 62,81 m
até a ponta do tailcone, em z=+1,66. Todo número que vier de agente passa pelo
mesmo teste de sanidade das cotas oficiais descrito em `extrair-cotas`.
