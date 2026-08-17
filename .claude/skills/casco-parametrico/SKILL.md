---
name: casco-parametrico
description: Construir a geometria da aeronave no Blender a partir do spec — fuselagem por gaiola de controle esparsa + subsurf Catmull-Clark, seções ovoides no nariz, asas e empenagem por loft NACA, carenagem ventral, motores, trem, portas e janelas analíticas sobre a superfície. Use SEMPRE que for modelar, reconstruir ou consertar geometria de avião neste repositório: "o nariz está amassado", "o casco ficou deformado", "monta as asas", "as peças estão desconectadas", "o trem está flutuando", "refaz a fuselagem", "as portas sumiram". Traz o construtor pronto e, principalmente, os erros de método que já produziram cascos ondulados e peças soltas.
---

# Casco e estrutura paramétrica

Toda a geometria vem do `spec_<tipo>.json`. O modelo é descartável; o spec não.
Se o casco precisar ser refeito, refaça — desde que refaça a partir do spec.

## A lição central: a gaiola não é a superfície

Este foi o erro que custou mais tempo no projeto, e ele é contra-intuitivo.

A primeira tentativa amostrou o contorno extraído em anéis densos, a cada 10 cm.
Parecia certo: mais dados, mais fidelidade. O resultado foi um casco **amassado**
— as micro-ondulações do dado extraído de pixel viraram ondas visíveis sob a
tinta brilhante, porque verniz automotivo amplifica variação de normal que uma
superfície fosca esconderia. Adensar mais piorou.

O que funciona é o oposto: **poucos anéis, nos lugares certos, e deixar o
Catmull-Clark fazer o faireamento.** A gaiola de controle fica só nas cavernas
reais (ponta + FR1–FR12 + as estações de porta + o barril + a cauda), tipicamente
~33 anéis de 32 segmentos, e o subsurf em nível 3 no render entrega curvatura
contínua de verdade. Não é aproximação: Catmull-Clark converge para uma
superfície G², que é exatamente o que uma fuselagem é.

Três consequências práticas:

- **Longitudinais por PCHIP nas cavernas oficiais**, não pela nuvem de pixels.
  A extração serve para descobrir a forma; a gaiola usa as estações do
  fabricante.
- **O barril leva anéis idênticos e igualmente espaçados** (a cada 2–3 m). Se
  você amostrar o barril dos dados extraídos, ele ondula. Seção constante
  significa anéis literalmente iguais.
- **Compense o encolhimento.** Catmull-Clark encolhe a superfície para dentro da
  gaiola. Num anel de 32 lados o fator medido é **×1,0064** aplicado radialmente
  em torno do centro da seção. Sem isso o avião nasce fino e as portas ficam
  enterradas.

## O construtor

`scripts/casco.py` traz a receita pronta: `aneis_de_spec()`, `construir_casco()`,
`uv_cilindrica()`, os perfis NACA e `validar_por_raycast()`. Cole em
`execute_blender_code` ou rode com `blender arquivo.blend --python`.

```python
aneis = aneis_de_spec(json.load(open("spec_b789.json")))
fus = construir_casco(aneis, nome="Fuselagem", material="LATAM_Branco",
                      ponta_frente=(0.0, 0.0, -1.16), ponta_tras=(62.85, 0.0, 1.66))
uv_cilindrica(fus.data, aneis, comprimento_uv=63.5)
```

`construir_casco` troca o `mesh` do objeto existente em vez de recriar o objeto.
Isso preserva modificadores, alvos de shrinkwrap e referências por nome — várias
regressões vieram de recriar o objeto e quebrar essas ligações silenciosamente.

## Seções: o nariz não é elipse

Esta é a diferença entre um nariz que lê como A320 e um que lê como bico de pato.

As seções do nariz são **ovoides**: lobo inferior cheio (largura de planta), lobo
superior pinçado na zona do cockpit. Modele a meia-largura como
`y = w(x)·(1−t²)^e(x)`, com o expoente `e(x)` variando ao longo de x — no A320,
0,5 até x≈1,2, subindo para 1,0 entre 2,4 e 3,2, voltando a 0,5 a partir de 5,5.

É o expoente que faz o para-brisa "virar para a frente" sem faceta manual.
Validação: na vista frontal do ACAP os vidros frontais chegam a y≈±0,05 no poste
central e a borda externa a ±0,86 em z≈0,9 — com `e=1`, `y(2,8; z=0,9)=0,89`,
que fecha.

A seção mestre do barril também não é elipse: ombros ~14% mais largos, largura
máxima 8–10 cm **acima** da meia-altura, e um tuck suave embaixo. Tabele a
meia-largura por profundidade abaixo da crista a partir do desenho frontal.

A cauda, em compensação, é elipse: `w = 0,954·r` no A320, `0,96·r` no 787.
Aplicar a seção ovoide na cauda quebra o wrap da livery e as matrículas — já
aconteceu.

## Raízes enterradas

Regra que veio de um ciclo inteiro de "vários elementos desconectados da
carroceria": **raiz de asa, deriva, estabilizador e pylon nunca nasce na
superfície do casco — sempre 1 a 1,5 m para dentro.**

O motivo é geométrico. Se a raiz começa exatamente na superfície, qualquer
diferença entre a curvatura da asa e a do casco abre fresta, e o subsurf ainda
puxa a superfície para dentro. Enterrar a raiz faz a interseção acontecer dentro
do sólido, onde ninguém vê. No 787: asa em y=1,6 (casco tem 2,885), base da
deriva em z=1,9, pylon em cunha entrando na asa, pernas do trem principal
subindo até dentro da asa.

Mesma lógica no trem: a perna precisa **entrar** no poço, não terminar na
superfície. Um trem "voando" é quase sempre uma perna curta demais, não um
posicionamento errado.

## Asas e empenagem

Loft de perfis NACA entre estações com corda e offset interpolados do spec:
`secao_aerofolio()` gera o contorno fechado (extradorso LE→TE, intradorso
TE→LE). Feche com tampa na raiz e na ponta, senão o render mostra o interior.

Respeite as quebras reais: no 787-9 o bordo de fuga tem 11° até y=10 m e 22,9°
depois, e a ponta raked vai de x=40,69 a 43,36 — a silhueta da ponta é uma das
coisas que identifica o tipo à distância. Diedro é estático no modelo (7° no
787), embora na vida real dependa da carga.

Subsurf 2 basta para asa; o casco é que precisa de 3.

## Portas, janelas e detalhes de superfície

Construa analiticamente **sobre** a superfície, avaliando a função `y_of(x, z)`
do casco e derivando a normal numericamente — assim o detalhe acompanha a dupla
curvatura em vez de flutuar.

Duas correções que vieram de feedback direto:

**Compense o subsurf.** O encolhimento enterra as portas. Empurre-as ~22 mm para
fora (`±0,022` em y conforme o lado). Sem isso a porta aparece pela metade.

**Contorno de porta que só depende de sombra não lê.** Sulco geométrico só
aparece onde a luz cria sombra — nos ângulos canônicos isso significa que só os
arcos de cima e de baixo aparecem, e a porta lê "pela metade". A solução que
funcionou foi **pintar o contorno na textura da livery**: um anel de faixa cinza
(a banda FAR) mais um anel escuro de sulco, rasterizados no espaço (x,θ). Ver
`livery-latam`.

## Motores

O motor é identidade visual, não decoração — errar o motor faz o avião ler como
outro. Confira qual variante a LATAM opera antes de modelar: o A320neo da LATAM
é **PW1100G-GTF, não LEAP** (pedido de 2013 + acordo de 2023, exclusivo na
frota), o que significa fan cowl branco, lip polido, sem chevrons, e bocal com
tailcone longo em inconel. O 787-9 é Trent 1000, com chevrons serrilhados no
bordo de fuga do fan sleeve.

## Validar antes de renderizar

Depois de qualquer reconstrução, gaste segundos em `validar_por_raycast()` com
algumas sondas nas cotas que você conhece. Casco furado, normal invertida e
escala errada aparecem ali, antes de você gastar minutos num render e uma
rodada de conversa.

`scripts/auditar_casco.py` faz as três checagens de uma vez — rode-o depois de
qualquer reconstrução:

```python
exec(open(".claude/skills/casco-parametrico/scripts/auditar_casco.py").read())
auditar("boeing 787-9")
```

**Compare a gaiola com o spec estação por estação, não só a superfície.** Meça
`max|y|` dos vértices de cada anel e divida pelo `meia_largura` do spec: o
resultado tem que ser `COMP` (1,0064) em toda a extensão. Onde não for, o erro
está na gaiola, não no subsurf — e essa é a única forma de distinguir os dois.

Foi assim que se achou, no 787-9, um afilamento espúrio no nariz: a razão saía
0,911 na ponta subindo linearmente até 1,000 em x=5, enquanto o barril estava
correto. Alguém tinha aplicado um `1 − 0,105·(1 − x/5)` à largura e esquecido.
Crown e keel estavam certos, então o casco parecia plausível em todos os
renders — nenhum ângulo denuncia 8% de estreitamento em planta. Corrigido, o
erro mediano contra o spec caiu de 1,2 cm para 0,4 cm.

Se precisar corrigir, escale **só o eixo errado, anel por anel**, mexendo nos
vértices existentes. Reconstruir a malha do zero jogaria fora a UV — e com ela
todo o registro da livery pintada.

Duas armadilhas ao escrever esse tipo de checagem, ambas descobertas na prática:
razão contra valor quase zero explode sem defeito nenhum (o crown cruza z=0 no
nariz), então **julgue por erro em metros**, com tolerância absoluta mais
relativa; e "a raiz de uma peça são seus vértices mais altos" é falso para a asa,
cujo topo é a **ponta** — declare de que lado fica a raiz de cada peça em vez de
inferir. Um teste que dispara trinta falsos positivos é pior que teste nenhum,
porque ensina a ignorá-lo.

Cheque também as três vistas entre si. Foi assim que se descobriu que a "vista
de topo anamórfica" do A320 era falso alarme (um run fragmentado clipou uma
borda) — validando contra a envergadura do estabilizador: 6,012 medido contra
6,225 oficial, uniforme. Uma vista sozinha não prova nada.
