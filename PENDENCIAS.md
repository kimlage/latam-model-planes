# Pendências — lista viva do projeto

Ordenada por impacto no realismo. Regra de trabalho: **nada de micro-correções
isoladas** — cada rodada ataca o item mais alto que estiver destravado, e os
itens micro só entram anexados a uma rodada maior que já re-renderize o que
eles tocam.

## Em andamento — programa de aprofundamento (ordem do dono, 2026-08-27:
## "continuar atacando os próximos aviões e detalhes, o mais realista possível")

1. ~~Rodada da verdade geométrica (frota)~~ — **fechada 2026-08-27**, cinco
   defeitos medidos e quatro corrigidos na fonte: (a) tailstrike A320 — era
   trem 0,28 curto + carenagem 0,20 funda + quilha traseira 0,29 baixa;
   agora 12,6°/15,0°/10,3° (A320/A319/A321), cada um entre o comprimido e o
   estendido publicados (`trem_familia.py` + tabelas ACAP nos specs); (b)
   polo de valência 32 — tampa quad com ápice ogiva em DEZ dos onze cascos
   (`nariz_quad_cap.py`; o 777 FICA com o polo — radome rombudo vira botão
   na emenda da tampa, 3 variantes medidas, QA; a sobra em V sob o nariz é
   lei de seção medida, QA novo); (c) 787: altura 17,02/16,92 — a deriva era inocente, as pernas
   eram curtas, com motor 0,52 alto e carenagem 0,33 funda corrigidos juntos
   (`trem_787.py`); (d) UV da coroa — só o -9 carregava, 152+152 loops
   corrigidos; (e) pinch do 767 — planta EXONERADA contra o ACAP (±0,03 m),
   lobo superior sem fonte que o meça: fica aberto com a medição registrada.
2. **Rodada de apêndices e luzes (frota)** — antenas VHF, pitots, AoA,
   descarregadores estáticos, beacon/strobe/nav/landing lights emissivas;
   transforma clipes e gates de uma vez. PRÓXIMA.
3. **Rodada de impressão de superfície (frota)** — linhas de painel e
   cutlines de comandos, matrícula sob a asa, e a arte SVG dos títulos
   (fecha o "AIRBUS A3" do A319). DEPOIS.
4. **Detalhe de cena** — jetbridges articuladas, GSE fino, variantes de
   luz (anoitecer GRU). DEPOIS.

## Fechado em 2026-08-27 — a caça às fotos das cunhas

O item 6 caiu com quatro fotografias: CC-BGF em PEK + CC-BGG em MAD (787-9,
flancos opostos, uma delas domínio público) e os quadros CC-BBF/CC-BBB que a
pasta do -8 já tinha. Lidas SEM homografia — reta da fronteira × anel pintado
da porta 4, a altura do anel (2,06 m) como escala local — as quatro dizem a
mesma coisa: **a regra escrita era a medida** (fronteira real = regra +0,10
±0,12 nos dois tipos, e c(-9)−c(-8) = 6,09 m = exatamente o deslocamento da
deriva — arte de frota rígida). A tinta é que estava 0,5 m atrás, deriva do
pintor do -9 ecoada no -8 pelo resample de colunas. As duas cunhas repintadas
na regra, gates re-renderizados, galeria e capa atualizadas. De quebra: o "OK"
de 08-22 dos dois 787 era artefato de uma homografia que encaixou a silhueta
inteira num quadro que corta o nariz — instrumento antes do modelo, sempre.

O item 7 andou meio caminho: as fotos com a asa limpa da cunha EXISTEM agora
(CC-CXE appr2 — que já estava na pasta —, N536LA em pouso, N540LA em
aproximação; manifestos com a trilha de busca completa), e as primeiras
leituras derrubaram uma suposição: a frota cargueira não veste um layout
único — as matrículas medem ~1,7/2,2/2,6 m em CC-CXE/N540LA/N536LA contra os
1,53 m da caixa herdada da N568LA, e a folga fronteira→matrícula vai de ~0 m
(CC-CXE) a ~0,8 m (N540LA). O veredito da cunha cargueira agora é uma rodada
de medição por aeronave-alvo, não uma caça a foto. Detalhe no QA-BACKLOG §5.

## Fechado em 2026-08-27 — re-sync das bases

Os sobrevoos de Santiago (v8) e São Carlos (v4) re-renderizados sobre cenas
reconstruídas com os masters atuais: nenhum render público do projeto exibe
mais cunha ou sash defasado. O rebuild do SDSC caiu na mesma armadilha
documentada no do SCL (rodar sem o arquivo-base constrói cena vazia
silenciosamente) e foi pego pelo TAMANHO anômalo do GIF (4,7 MB) — regra
que fica: todo rebuild de cena derivada prova UM frame antes de renderizar
o lote, sem exceção, e um GIF fora da faixa histórica é sintoma, não sorte.

## Fechado em 2026-08-27 — GRU completa

As três fases de Guarulhos entregues e publicadas: survey por AIP, campo
povoado, entorno realista (floresta na serra, bairros, cinturão logístico —
rodada extra após o dono apontar o vazio), e os três clipes na capa:
decolagem do 777 na 10L (v2), tour aéreo (v2) e o roll-out de ré pela porta
de 76 m (v1). Três reinícios de máquina e cinco stalls de agente no caminho;
as regras que ficaram: frames dentro do repo, chunks de ≤40 frames, Metal
fixado, blur desligado por memória, um único escritor no fim do pipeline.

## Fechado em 2026-08-26 — rodada da verdade da tinta

As duas metades resolvidas com UMA aeronave repintada, não cinco:
- **As 4 cunhas suspeitas eram paralaxe de flanco**, não tinta: a retificação
  de 08-22 era controlada na deriva (y=0) mas a pele vive em |y|~2, e o
  deslocamento y·v aparece inteiro na fronteira. Com v medido no estabilizador
  de cada quadro (e dois quadros independentes onde havia): A320ceo −0,03, A321neo
  +0,25/+0,18 (flancos opostos), 767-300ER +0,03/+0,15 — exoneradas. A320neo:
  sem veredito no quadro PT-TMN (1024 px); a frota atual (PR-XBP) veste a
  fronteira +0,95 m atrás — variante de era, registrada, não aplicada.
- **A "contradição" do A319 era o mesmo artefato**: porta 4 está no ACAP
  (−0,10±0,19 m corrigido). O que estava errado era a CORREÇÃO de 08-22 da
  cunha, que carregava a paralaxe: fronteira movida +0,76 m para trás
  (cruza o topo da porta 4 a 58%/57% em dois airframes), traseira restaurada
  à linha do BF da deriva. Única repintura da rodada.
- **O casco "branco-puro" era diagnóstico velho**: os 76% em 1.0 são texels
  mortos (fac=0); as onze bases de shader já vestem #E6E7EA e os renders
  seguram o branco em 0,69–0,72 sem clipe. Fechado no QA-BACKLOG com o censo;
  a única constante defasada (PALETA) corrigida; os dois brancos-sentinela
  (#F2F3F5 marcas, #F7F9FA arte) documentados como deliberados.

## Próximas, em ordem de impacto

3. **Re-sync SCL + SDSC depois da rodada da tinta.** Os clipes da capa ainda
   mostram A319/777 com a cunha antiga (corrigida em 29664d9, depois dos
   clipes). Uma re-renderização captura cauda + cunha + casco de uma vez —
   não re-renderizar antes, para não pagar duas vezes.
4. **GRU fases 2–3** — construção do cenário e clipes.
5. ~~Consolidação da pintura~~ — **fechado 2026-08-27**: `refazer_marcas.py` é
   o único pintor de marcas (três motores legados, constantes citadas); os 11
   builders pintam só livery plana com a cunha da regra única; os três
   ofensores nomeados (emenda x=41, máscara-diferença dos A321, portão
   `abs(sin θ)>0.10` do 787-8) morreram. Aceitação por dump-and-diff em
   cópias: 767-300ER byte-idêntico fora a assinatura da emenda (25 texels) e
   idempotente; tabela completa e a sequência única por aeronave em
   `REBUILD.md`. Zero renders, nenhuma textura embarcada mudou. Fica nomeado
   (QA-BACKLOG): o repintar de anéis do `portas_familia` não é byte-estável
   (difusão), e as bordas duras das sete cunhas seguem deferidas de propósito.
6. ~~787-8/-9: assentamento da cunha~~ — **fechado 2026-08-27**: quatro fotos,
   veredito pela porta 4, cunhas repintadas NA REGRA (a tinta é que derivava).
7. **Cargueiros: cunha sem veredito — mas as fotos existem agora.** A asa não
   é mais a desculpa (CC-CXE appr2, N536LA em pouso, N540LA em aproximação).
   O que falta é rodada de medição por aeronave-alvo com âncora na deriva e
   estab mascarado, porque a frota cargueira não veste um layout único
   (matrículas de 1,7 a 2,6 m; folgas de 0 a 0,8 m) — QA-BACKLOG §5.
8. ~~Export GLB desatualizado~~ — **fechado 2026-08-26**: frota portátil
   re-exportada pós-QA e os DOIS cargueiros exportados pela primeira vez
   (a tabela ainda os tratava como "em construção"; export/ tinha 9 de 11).
9. ~~Outras bases além de GRU~~ — **decidido (2026-08-26): só GRU por
   enquanto**; o ciclo fecha com 3 bases (SCL, São Carlos, GRU) em qualidade
   máxima antes de qualquer ampliação.
10. **E195-E2** — **decidido (2026-08-26): modelar quando houver foto de
    matrícula LATAM real** (chega no 2º semestre de 2026; o padrão do projeto
    exige foto da matrícula específica).

## Micro (não fazer isoladamente)

Detalhes em `QA-BACKLOG.md`: vinco de quilha das seções do nariz (lei do
expoente, medido 2026-08-27), lobo superior do cockpit do 767 (sem fonte),
polo de valência 32 da CAUDA (~3 cm, sub-visível), zona do cone da APU dos
A320 (0,1-0,2 acima do desenho, cota AP ambígua), título do A319 enterrado
pela cunha, proporção do símbolo, portas de capô autorais no SDSC, stand MID
fora do solver, docks dimensionados pelo proxy nominal.
