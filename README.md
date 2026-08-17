# Réplicas 3D da frota LATAM

![Boeing 787-9 e Airbus A320neo da LATAM, renderizados em vários ângulos](capa.png)

Modelos 3D em Blender de aeronaves da LATAM Airlines, construídos com um
critério único: **as cotas têm que bater com o documento do fabricante e a
pintura tem que bater com a foto daquela matrícula**. Não é "parece um avião" —
é um engenheiro da LATAM reconhecer o avião dele.

Dois aviões prontos:

| Aeronave | Matrícula | Arquivo | Comprimento |
|---|---|---|---|
| **Boeing 787-9 Dreamliner** | CC-BGK | [`boeing 787-9/B789_LATAM.blend`](boeing%20787-9/B789_LATAM.blend) | 62,81 m |
| **Airbus A320neo** | PT-TMN | [`airbus A320neo/A320neo_LATAM.blend`](airbus%20A320neo/A320neo_LATAM.blend) | 37,57 m |

![A320neo em voo, câmera orbital, trem recolhendo](airbus%20A320neo/a320_voo.gif)

---

## Por que este repositório existe

Modelar avião "no olho" é rápido e dá errado. Este projeto é a tentativa oposta:
**nenhuma malha antes de existir número**. Toda dimensão rastreia até um
documento oficial do fabricante (Airbus *ACAP*, Boeing *Airplane
Characteristics*), e o que o documento não traz — como a livery é aplicada, onde
a cunha índigo cruza a porta, o tom exato — é medido por fotogrametria em fotos
da matrícula específica, com a incerteza registrada.

O resultado prático é que **o modelo é reconstruível**. Se o `.blend` sumir, o
`spec_<tipo>.json` de cada aeronave contém a especificação de engenharia
completa — estações do nariz, seção mestre, polígonos do para-brisa, portas,
janelas, planform da asa, empenagem, motor, trem — e os scripts reconstroem a
partir dele.

## As seis fases

1. **Fontes** — documento dimensional oficial, fotos da matrícula, CAD aberto só
   como conferência de silhueta. → skill `fontes-aeronave`
2. **Extração** — rasterizar as vistas a 600 dpi, calibrar por cota impressa,
   extrair crown/keel/meia-largura → `curves.json` + `spec_<tipo>.json`.
   → skill `extrair-cotas`
3. **Casco** — gaiola de controle esparsa **nas cavernas reais** + subsurf
   Catmull-Clark. Gaiola densa é o que produz nariz amassado; a esparsa é o que
   deixa liso. → skill `casco-parametrico`
4. **Livery** — vetores oficiais da marca, aplicação medida na foto, pintura como
   textura UV em `(x, θ)` — nunca como casca 3D. → skill `livery-latam`
5. **Detalhes** — portas, janelas, trem, motores, antenas, ventre. O critério é o
   avião completo e conexo, não o casco pintado.
6. **Gate visual** — 6 ângulos canônicos, folha de contato, comparação com a
   foto. → skill `verificacao-visual`

```bash
python3 verificacao_visual.py "boeing 787-9"
```

## Skills

O pipeline está codificado como skills em [`.claude/skills/`](.claude/skills/) —
cada uma carrega as armadilhas que já custaram retrabalho.

| Skill | Fase |
|---|---|
| [`nova-aeronave`](.claude/skills/nova-aeronave/SKILL.md) | roteador: pipeline ponta a ponta de um avião novo ou derivado |
| [`fontes-aeronave`](.claude/skills/fontes-aeronave/SKILL.md) | ACAP/APR oficial, fotos da matrícula, CAD aberto e licenças |
| [`extrair-cotas`](.claude/skills/extrair-cotas/SKILL.md) | desenho e foto → `curves.json` + `spec_<tipo>.json` |
| [`casco-parametrico`](.claude/skills/casco-parametrico/SKILL.md) | casco, asas, empenagem e detalhes no Blender |
| [`livery-latam`](.claude/skills/livery-latam/SKILL.md) | marca oficial, pintura como textura UV, sash, materiais |
| [`blender-mcp`](.claude/skills/blender-mcp/SKILL.md) | operação do Blender via MCP: timeouts, corrida de render |
| [`verificacao-visual`](.claude/skills/verificacao-visual/SKILL.md) | gate de qualidade: 6 ângulos, folha de contato, checklist |

[`FONTES-FROTA.md`](FONTES-FROTA.md) traz o inventário das 12 variantes da frota:
documento oficial verificado por tipo, CAD aberto útil e estratégia recomendada.

## Referencial

Todo o repositório usa o mesmo — misturar referencial é a forma mais fácil de
produzir um avião torto:

- **x = 0 na ponta do nariz**, crescendo para trás, em metros
- **z = 0 na meia-altura da seção constante**, positivo para cima
- **y = 0 no plano de simetria**, positivo para estibordo

Cuidado com os *data* do fabricante: as *stations* da Airbus são medidas a partir
de um X0 que fica 2540 mm à frente do nariz (`x = STA − 2540`), e a mesma família
mistura unidades entre SRM e AMM.

## Paleta LATAM

| Cor | Hex | Onde |
|---|---|---|
| Branco | `#E6E7EA` | fuselagem |
| Índigo | `#2A0088` | deriva, wordmark, cunha traseira |
| Coral | `#ED1651` | bandas da deriva, símbolo |
| Cinza-voo | `#C8CACC` | bandas claras da deriva, filete do bordo de ataque |

## Regras de fidelidade (não negociar)

**0. Olhe o avião antes de modelar.** Buscar fotos da matrícula real é o primeiro
passo — antes do ACAP, antes do spec, antes de qualquer pesquisa. Não é a
validação do fim: é a partida, e custa um minuto. **Nenhuma descrição em prosa
substitui ver o avião**, nem quando veio de fotogrametria, nem quando passou por
verificação adversarial. No 787-9 o spec descrevia uma echarpe índigo descendo
pelo casco até o tailcone; horas de fotogrametria, medição de desenho e revisão
por agentes não pegaram o erro — a primeira foto do Google resolveu em segundos.

**1.** Marca exata: importar os vetores oficiais — nunca aproximar com fonte
parecida.

**2.** Aplicação igual à frota — conferida na foto, não na descrição.

**3.** Geometria pelo documento do fabricante: dimensões, portas, trem, motores.

**4.** Quando spec e foto discordarem, **a foto ganha** — e o spec é corrigido na
mesma hora, com o motivo escrito, senão o erro volta na próxima aeronave que
derivar dele.

**5.** Nada é entregue sem passar pelo gate visual, e "passar pelo gate" significa
**abrir as imagens e olhar** — não gerar os arquivos e presumir.

## Como o desenho da deriva foi resolvido

Vale como exemplo do método, porque foi o ponto que mais resistiu. O sash da
LATAM é um conjunto de **bandas paralelas que atravessam a deriva de bordo a
bordo**, cada uma cinza nas duas pontas e coral no miolo, sobre um campo índigo.
Versões anteriores tinham a deriva branca com bandas grossas — errado.

A geometria saiu de uma foto do CC-BGP **retificada para o plano da deriva** por
uma transformação afim, o que transforma o problema em leitura direta em `(x, z)`:

```
b = z − 0.24·x     (coordenada através das bandas)
e = z + 0.25·x     (coordenada ao longo das bandas)

banda inferior:  b ∈ [−6.725, −5.99]   coral onde e ∈ [22.006, 23.332]
banda superior:  b ∈ [−4.208, −3.35]   coral onde e ∈ [24.913, 26.192]
acima da superior: cinza-voo   ·   entre e abaixo: índigo
```

Ajustado por descida coordenada contra a foto classificada, o modelo chega a
**92,6% de concordância** pixel a pixel dentro do contorno da deriva. O mesmo
desenho foi transferido para o A320 por coordenadas normalizadas da deriva
`(h, c)` — é a mesma marca, só muda a escala.

Duas armadilhas que valem para qualquer medição em foto:

- **Nunca calibre pelo comprimento total do avião.** Basta o avião estar
  levemente angulado para o vão nariz-cauda encurtar. Numa foto do CC-BGP isso
  errou 14% — e como o erro é uma escala, ele desloca *todas* as medidas de forma
  plausível. Use o passo das janelas, que é uma cota repetida.
- **Limiar de cor não separa peças da mesma cor que se sobrepõem na projeção.**
  Medir a cunha traseira por "quais pixels são índigo" falhou repetidamente
  porque a deriva também é índigo e cobre o casco na vista lateral.

## Reproduzir

Blender 5.2+. Abra o `.blend` da aeronave e renderize — texturas e materiais vêm
empacotados no arquivo.

Para rodar o pipeline do zero você precisa dos documentos do fabricante e dos
vetores de marca, que **não estão neste repositório** por questão de licença.
[`NOTICE.md`](NOTICE.md) lista cada um e onde obter.

## Licença

- Código, skills e dados de engenharia: **[MIT](LICENSE)**
- Modelos 3D, renders e animações: **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**

**LATAM**, **Airbus**, **Boeing** e **Dreamliner** são marcas registradas de seus
titulares. Projeto independente e não comercial, **sem vínculo, patrocínio ou
endosso** de nenhuma dessas empresas. Detalhes e material de terceiros excluído:
[`NOTICE.md`](NOTICE.md).
