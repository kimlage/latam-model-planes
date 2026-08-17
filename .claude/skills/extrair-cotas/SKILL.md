---
name: extrair-cotas
description: Transformar desenho cotado (ACAP/APR) e fotos em números utilizáveis — rasterizar o PDF, calibrar por cota impressa, extrair crown/keel/meia-largura do casco, medir para-brisa/portas/livery por fotogrametria, e gravar curves.json + spec_<tipo>.json. Use SEMPRE que precisar de coordenadas reais de qualquer parte de um avião: "mede o nariz do 767", "extrai as curvas do desenho", "onde fica a porta 2", "qual o formato do para-brisa", "as proporções estão erradas", "calibra isso com a foto". Use também quando o modelo não bate com a referência e a causa pode ser cota errada. Traz o script pronto e as armadilhas de calibração que já produziram cascos deformados.
---

# Extrair cotas de desenhos e fotos

O objetivo é sempre o mesmo: sair de um PDF ou de uma foto e chegar em
coordenadas em metros, no referencial da aeronave, gravadas em JSON. Uma vez
gravado, o número não precisa ser medido de novo — e o modelo pode ser
reconstruído do zero sem perder fidelidade.

## Referencial — fixe antes de medir qualquer coisa

Todo o repositório usa o mesmo, e misturar referencial é a forma mais fácil de
produzir um avião torto:

- **x = 0 na ponta do nariz**, crescendo para trás, em metros;
- **z = 0 na meia-altura da seção constante**, positivo para cima;
- **y = 0 no plano de simetria**, positivo para estibordo.

Cuidado com os data do fabricante. As *stations* da Airbus (STA) são medidas a
partir de um X0 que fica **2540 mm à frente da ponta do nariz** — então
`x = STA − 2540`. E a mesma família mistura unidades: o SRM dá STA em cm, o AMM
dá em mm. A atitude estática também não é zero (o 787-9 pousa com −0,52° de
nariz baixo); o modelo é construído no referencial do avião, não do solo.

## Do PDF para os números

### 1. Rasterizar
```bash
pdftoppm -f 21 -l 21 -r 600 -png "B787_APR_boeing.pdf" apr600_p21
```
600 dpi resolve tudo que interessa; 1200 dpi só vale a pena para detalhe fino
como para-brisa. Uma armadilha idiota que já custou tempo: **o índice de página
do `pdftoppm` não é o número impresso nem o que o Read mostra** — no ACAP do
A320 os 3-views estavam nas páginas cruas 44–45, não 6–7. Confirme abrindo o
PNG.

### 2. Ancorar à mão, em crops ampliados
Este é o único passo que não dá para automatizar, e é o que determina se todo o
resto presta. Recorte e amplie as regiões das âncoras e **olhe** para achar os
pixels exatos:

```python
from PIL import Image
im = Image.open("apr600_p21-021.png")
im.crop((825, 3960, 1320, 4488)).resize((990, 1056)).save("insp_nariz.png")
im.crop((3630, 3960, 4257, 4488)).resize((1254, 1056)).save("insp_cauda.png")
im.crop((2310, 5082, 2904, 5610)).resize((1188, 1056)).save("insp_frontal.png")
```

Guarde esses `insp_*.png` na pasta da aeronave — eles documentam de onde cada
âncora saiu.

### 3. Extrair
Use o script pronto:
```bash
python3 .claude/skills/extrair-cotas/scripts/extrair_contorno.py config.json
```
`scripts/exemplo_config.json` é a config real do 787-9, comentada. Ele já traz a
receita inteira: máscara, limpeza por mediana, ponte sobre oclusões,
monotonicidade, normalização e as cotas de sanidade. Rodado contra o desenho do
787-9 ele reproduz a spec validada do projeto dentro de poucos centímetros.

Duas máscaras, porque os dois fabricantes desenham diferente:

- **`amarelo`** — ACAP da Airbus, silhueta preenchida. Pega o miolo
  (`R−B > 15 & R > 170`) em vez do traço, o que evita capturar linhas de cota.
- **`linhas`** — APR da Boeing, desenho a traço. Pixel escuro (`< 128`) é
  contorno.

### 4. Conferir a sanidade — e entender o que o erro significa
O script imprime altura e largura medidas contra as do documento. O tamanho do
erro diz o que fazer:

| Erro | Causa | O que fazer |
|---|---|---|
| < 3% | viés de leitura (espessura do traço infla a altura; halo de cota morde a largura) | normalizar cada eixo por `doc/medido` — o script já faz |
| > 4% | âncora errada de verdade | voltar aos crops |

O caso >4% aconteceu: a banda lateral do 787 pegou fuselagem e estabilizador
juntos e a "cauda" saiu em 79 m. Nenhum ajuste de filtro conserta isso — só
reancorar.

## As três armadilhas que produziram casco errado

**Halo branco de cota vira cintura fantasma.** As setas de dimensão têm um halo
claro que morde a silhueta preenchida. No A320 isso produziu uma "cintura" de
0,22 m de meia-largura em x≈6 — o casco estrangulou ali e os decals passaram
através dele. A defesa é impor monotonicidade: a largura só cresce indo para
trás no nariz e só diminui indo para trás na cauda
(`np.maximum.accumulate`).

**Outra peça encostando no contorno.** Asa, nacelle, trem e estabilizador
cruzam a banda da fuselagem. Interpole por cima do vão em vez de acreditar no
pixel — no 787 os vãos foram `keel` em 4–8 m (trem do nariz) e 16,5–34 m
(nacelle + asa + trem principal), e `crown` em 20–30 m.

**Vista de topo mentindo na cauda.** O estabilizador horizontal atravessa a
banda e a meia-largura extraída ali é lixo. Não tente salvar: derive a largura
do raio lateral. No 787, `w = 0,96·rz`; no A320, `w = 0,954·r`.

## Calibrar pela cota certa

Escolha uma cota impressa longa e inequívoca. Mas **leia o que ela mede**: no
787-9 a cota de 62,00 m é a distância no **solo** entre as projeções verticais
do nariz e da ponta do tailcone — não o comprimento. O comprimento real é
62,81 m, porque o tailcone termina em z=+1,66, bem acima do solo. Calibrar por
ela é correto; tratá-la como comprimento não é. Esse erro passou por um
workflow inteiro de pesquisa antes de ser pego pela validação cruzada.

Por isso a regra: **calibre com uma cota e valide com pelo menos duas outras.**
Altura da fuselagem, largura, entre-eixos e envergadura do estabilizador são
boas testemunhas. Se as três batem dentro de 1–2%, a calibração está boa.

## De curvas para spec

O `curves.json` é dado cru e ruidoso. O `spec_<tipo>.json` é o que o modelo
consome, e ele guarda **estações discretas nas cavernas reais**, não a nuvem de
pixels — porque é isso que faz o casco ficar liso (ver `casco-parametrico`).
Densifique com PCHIP (interpolação C², monótona, sem oscilar entre pontos) para
gerar o `<tipo>_hull_smooth.json` intermediário.

O `spec_*.json` deve conter, no mínimo: dimensões gerais, estações do nariz
`[x, crown, keel, meia_largura]`, estações da cauda `[x, centro_z, raio]`,
seção mestre, polígonos do para-brisa, portas (pax/carga/overwing), janelas,
asa, empenagem, motor, trem, e um campo `confianca` dizendo o que é cota
oficial e o que é fotogrametria. Veja
[spec_b789.json](boeing%20787-9/spec_b789.json) e
[spec_a320.json](airbus%20A320neo/spec_a320.json) como modelo.

## Fotogrametria em foto

O que o documento não traz — aplicação da livery, tom, desgaste, variação por
matrícula — se mede em foto. A técnica que funcionou:

**Calibre com algo de tamanho conhecido dentro da própria foto.** O passo das
janelas de cabine é excelente (0,515 m no A320, 0,61 m no 787) porque se repete
ao longo de todo o casco; o centro de uma porta com x conhecido dá a segunda
âncora. Com as duas, uma foto de 1920 px de perfil dá ~51–52 px/m.

**Nunca calibre pelo comprimento total do avião na foto.** Parece a cota mais
óbvia e é a mais traiçoeira: basta o avião estar levemente angulado para o vão
nariz-cauda encurtar por perspectiva. Numa foto do CC-BGP a calibração por
nariz-cauda errou **14%** — e como o erro é uma escala, ele desloca *todas* as
medidas de forma plausível, sem nada parecer errado. O passo das janelas é
imune: é uma cota repetida, então a perspectiva aparece como variação do passo
e você percebe. Valide sempre reprojetando: se a âncora prevê a ponta do nariz
em x≈0 e a cauda no comprimento oficial, a escala está boa.

**Limiar de cor não separa peças da mesma cor que se sobrepõem na projeção.**
Medir a pintura da fuselagem traseira do 787 por "quais pixels são índigo"
falhou repetidamente porque a **deriva também é índigo** e cobre o casco na
vista lateral. O resultado eram tabelas que mudavam a cada tentativa. Quando
duas peças compartilham a cor, amplie o recorte e **leia a fronteira a olho** —
é mais confiável do que qualquer limiar, e mais rápido do que descobrir isso
depois de cinco iterações.

**Use perfil quase puro.** No meio da fuselagem a projeção é quase ortográfica.
Perto do nariz e da cauda a perspectiva já morde — declare incerteza maior lá.

**Cruze fotos.** Duas fotos independentes concordando dentro de 0,3 m é um
resultado; uma foto sozinha é uma hipótese. Registre a incerteza no spec
(`±0,3 m` é típico) e a URL de cada foto.

**Datar a foto.** A livery muda. O PT-TMN de 2016 tem a matrícula branca dentro
do índigo; hoje é índigo sobre branco. Anote a variação no spec em vez de
escolher silenciosamente — e siga a foto que o dono forneceu.

**Delegue a agentes com schema.** As medições mais completas do projeto (cauda
do PT-TMN, livery do CC-BGK, para-brisa do A320) vieram de workflows com schema
estruturado pedindo polígonos e validação cruzada. Ver `fontes-aeronave` para
como montar o schema.
