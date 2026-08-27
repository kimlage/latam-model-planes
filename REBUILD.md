# REBUILD — a sequência única de reconstrução por aeronave

Consolidação do pintor único (2026-08-27). Regra do repositório a partir desta
rodada:

> **Os builders pintam só livery plana** — base branca, cunha, portas, janelas,
> parabrisa, deriva, desgaste. **Toda MARCA — lockup LATAM, matrícula, título
> de tipo, bandeira, marca do ventre — é pintada por `refazer_marcas.py`**, e
> por mais ninguém. **A cunha tem uma regra única por aeronave**
> (`reparar_echarpe.FROTA`) **e uma ponte única** (`latam_livery_kit.
> secoes_do_casco` / `cobertura_echarpe`); `reparar_echarpe.py` é quem a
> repara/fecha numa textura já pintada.

Rodar um builder antigo re-inseria o defeito que a rodada das cunhas tirou
(QA-BACKLOG "The wedge rasterizer is shared now"); depois desta rodada, rodar
a sequência abaixo reproduz a textura embarcada dentro das tolerâncias
medidas e citadas em baixo.

## As sequências

Cada linha é executada como
`Blender -b "<pasta>/<MASTER>.blend" --python <script> -- <args>`.

### Boeing de linha (builders de textura completos, re-executáveis)

| aeronave | sequência |
|---|---|
| 767-300ER | `b5_livery.py` → `refazer_marcas.py -- b763er` → `reparar_echarpe.py -- b763er` |
| 767-300F | `b5f_livery.py` → `refazer_marcas.py -- b763f` (reparar é auditoria: borda dura embarcada fica) |
| 767-300BCF | `b5b_livery.py` → `refazer_marcas.py -- b763bcf` (idem) |
| 777-300ER | `build_77w_fase2_livery.py` → `refazer_marcas.py -- b77w` → `reparar_echarpe.py -- b77w` |

### Família A320 (builders de textura completos + rodada das portas)

| aeronave | sequência |
|---|---|
| A319 | `build_a319_livery.py` → `airbus A320neo/portas_familia.py -- construir` → `refazer_marcas.py -- a319 lockup marcas` → `reparar_echarpe.py -- a319 --forcar` |
| A320ceo | `build_a320ceo_livery.py` → `portas_familia.py -- construir` → `refazer_marcas.py -- a320ceo lockup marcas` (reparar é auditoria) |
| A320neo | `build_a320neo_fix_livery.py` → `portas_familia.py -- construir` → `refazer_marcas.py -- a320neo lockup marcas` (reparar é auditoria) |

### Derivações (o fase2 é passo de derivação, não repintor)

Reconstruir um A321/787-8 do zero é re-derivar do pai (fase1/geo → fase2 →
fase3) e então rodar os dois pintores; **manter** um master existente é só
rodar os dois pintores:

| aeronave | manutenção da textura |
|---|---|
| A321neo | `refazer_marcas.py -- a321neo lockup marcas` → `reparar_echarpe.py -- a321neo` |
| A321ceo | `refazer_marcas.py -- a321ceo lockup marcas` → `reparar_echarpe.py -- a321ceo` |
| 787-8 | `refazer_marcas.py -- b788` → `reparar_echarpe.py -- b788` |
| 787-9 | `refazer_marcas.py -- b789 lockup marcas` → `reparar_echarpe.py -- b789` (não há builder de livery: o master é a origem) |

Scripts históricos absorvidos por `refazer_marcas.py` e que **não se rodam
mais**: `build_a321_fase2b_espelho.py`, `fix_reg_ghosts.py`,
`fix_titulo_a321.py`, `build_788_livery2.py`, `fix_matricula_a319.py`
(a matrícula do A319 agora é pintada da recombinação P,T,-,T,M,T do próprio
`Reg_E`, na caixa final que o fix mediu).

## A aceitação medida (dump-and-diff, cor EFETIVA, em cópias — nada embarcado)

Todo diff abaixo é `mix(#E6E7EA, LiveryTex, LiveryFac)` texel a texel contra a
textura embarcada de 2026-08-27; "flips" são texels de contraste cheio
(branco↔indigo), sempre de 1 texel de largura (9–18 mm no casco, contra 32
mm/pixel do gate — nenhum ângulo do gate resolve).

| aeronave | texels ≠ | veredito |
|---|---|---|
| 767-300ER | **25** | byte-idêntico fora 23 flips na zona da emenda x=41 (o defeito que a ponte única mata) + 2 texels guardados junto à última janela. Re-rodar: byte-idêntico (idempotente). |
| 767-300F | 432 | jitter de 1 texel da fronteira (ponte da malha vs tabela do spec), tudo no segmento branco→indigo; marcas byte-exatas. |
| 767-300BCF | 430 | idem. |
| 777-300ER | 914 | 480 quantização ≤0.02 + 424 flips = canto do `poupar` + o pente de texels vizinhos de janela que o reparo não podia tocar (o rebuild pinta-os pela regra). `reparar` escreve **zero** depois do builder. |
| A320neo | 7.5k | ~6k é o ruído do `portas_familia` (apagar+difusão+repintar de anéis NÃO é byte-estável: re-rodar portas sozinho sobre o embarcado diverge 5.9k texels — pré-existente, não desta rodada); resto = fronteiras AA e marcas re-blendadas. `reparar --seco`: 4.3k (o mesmo número da auditoria embarcada). |
| A320ceo | 10.3k | mesmas classes (ruído de anéis + marcas movidas para refazer re-rasterizadas + cunha auditada 5.4k vs 5.6k embarcado). |
| A319 | 11.0k | atribuído zona a zona: matrícula 4.5k (MESMAS linhas e colunas de glifo; só o peso do traço — o embarcado é resample duplo de tinta, o rebuild é raster de primeira geração), anéis 4.1k (classe portas), título 0.5k (a arte do builder restaura o "19"+swirl que a cunha velha destruiu — QA-BACKLOG "AIRBUS A3"), lockup 0.3k, resto 1.1k (fronteiras AA). |
| A321neo | 2.2k | 532 flips = bordas de glifo da matrícula (re-raster na posição do spec x 37.15 vs tinta embarcada movida por sessão não versionada); título byte-exato; `reparar`: **nada a reparar**. |
| A321ceo | 1.4k | 466 flips idem; título byte-exato; anel D4 excluído dos erases (é o AA do portas). |
| 787-8 | 4.6k | 1.0k flips = matrícula re-rasterizada da arte na caixa final (o embarcado é resample duplo); ventre re-blendado; lockup deriva AA. |
| 787-9 | 6.7k | re-rodar refazer+reparar sobre o embarcado: **3** texels de contraste cheio; o resto é deriva de re-blend ≤0.5 (lockup, espelho de janelas). `reparar` escreve 5. |

## As três lições de método desta rodada

1. **`portas_familia` não é byte-estável** — o apagar+difusão lê o fundo do
   entorno, e o entorno muda a cada rodada. É pré-existente e cosmético
   (bordas de anel), mas significa que anel de porta não entra em teste
   byte a byte; entra por classe.
2. **Blender devolve rc=0 com traceback no script** — todo pipeline headless
   tem de grep'ar Traceback no log, não confiar no exit code (um passo
   ausente "passou" silenciosamente duas vezes nesta rodada).
3. **A ponte das MARCAS não muda junto com a da cunha.** As marcas foram
   AUTORADAS nas pontes antigas dos builders (inclusive a emendada do 767);
   re-pintá-las na ponte da malha as moveria — mover marca é rodada de
   textura com gate. Por isso `refazer_marcas` guarda as pontes legadas por
   família, citadas, só para as marcas.
