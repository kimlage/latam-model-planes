---
name: livery-latam
description: Aplicar a identidade LATAM no modelo com fidelidade de frota — marca a partir dos SVGs oficiais (nunca fonte parecida), pintura rasterizada como textura UV (x,θ) em vez de decal 3D, sash da deriva por lado, echarpe traseira, matrícula, e a receita de material que faz a tinta parecer tinta. Use SEMPRE que o assunto for pintura, marca, logo, cores, cauda, matrícula, títulos, janelas brancas, ou aparência de render: "o logo da cauda não está certo", "aplica a livery", "as janelas estão brancas", "pinta a matrícula", "deixa mais realista", "as cores estão erradas". Traz a paleta oficial, o pipeline de rasterização e as armadilhas de shader que já renderizaram o avião inteiro de vidro azul.
---

# Livery LATAM

Três regras que o dono do projeto repetiu até virarem lei:

0. **Olhe a foto da matrícula antes de pintar qualquer coisa.** Uma pintura é
   um fato visual: nenhuma descrição em texto — nem a deste spec, nem a de uma
   pesquisa — vale mais do que a foto. Se você não tem uma, busque
   (`WebSearch` pela matrícula, JetPhotos, Planespotters, Wikimedia) antes de
   abrir a textura.
1. **Marca exata, nunca aproximação.** Importe o SVG oficial. Fonte parecida é
   reprovação automática — o olho reconhece o desenho da letra.
2. **Aplicação igual à da frota.** Não é "livery inspirada na LATAM": é a
   pintura daquela matrícula, medida na foto dela.

**A livery LATAM pós-2016, na prática: a fuselagem é INTEIRAMENTE BRANCA.** O
índigo e o coral vivem na deriva. Não existe cheatline, faixa ou echarpe
descendo pelo casco. No 787-9 o spec descrevia uma echarpe índigo indo da
deriva até o tailcone; ela foi refinada por horas — limite por z, depois por
ângulo, depois com mergulho local — até a foto do avião mostrar que **a echarpe
não existe**. Quando a prosa e a foto discordarem, a foto ganha e o spec é
corrigido na hora.

Os vetores oficiais estão na raiz: `latam_logo_indigo.svg` (lockup completo) e
`airbus_a320neo_logo.svg` (título de tipo).

## Paleta

| Cor | Hex | Onde |
|---|---|---|
| Índigo | `#2A0088` | wordmark, massa da cauda, echarpe |
| Coral | `#ED1651` | símbolo, bandas do sash |
| Branco de casco | `#E6E7EA` | fuselagem — **nunca branco puro** |
| Navy de títulos | `#1C2E63` | legendas secundárias |
| Cinza Airbus | `#9FA4A9` (FS16515) | carenagem ventral, intradorso |
| Flight gray Boeing | `#C8CACC` | asas do 787 |

Medições fotogramétricas dão valores levemente diferentes por foto e iluminação
(no CC-BGK saiu `#1B0088`/`#E8114B`). Os valores da marca acima vêm do SVG
oficial e são os que devem ir para o modelo; guarde o medido no spec como
observação, não como fonte.

## A decisão de arquitetura: pintura é textura, não geometria

A tentativa inicial foi decal 3D — malha do logo grudada no casco por
shrinkwrap. Falhou de várias formas ao mesmo tempo: vinca em dupla curvatura,
z-fighting, e o `shrinkwrap` com modo PROJECT usa o eixo **local** do objeto, de
modo que logos rotacionados nunca projetaram — ficaram flutuando a y=±3, z=−3,4,
e as sombras deles apareciam no casco como um "LATAM fantasma".

A arquitetura definitiva é **rasterizar tudo na textura UV (x,θ) do casco**:

1. Modele as marcas como malha plana (importada do SVG, ou `TextCurve`→mesh
   para matrícula).
2. Rasterize os triângulos dessas malhas para o espaço (x,θ), gravando um
   **código de cor inteiro** por pixel num buffer `uint8` de 8192×2048.
3. Reduza 2× (supersample) para 4096×1024, convertendo cobertura em cor e em
   máscara.
4. Grave **duas imagens**: `LiveryTex` (cor, sRGB) e `LiveryFac` (máscara,
   Non-Color).
5. Misture no shader do casco.

Vantagens que não são óbvias até você bater nelas: zero z-fighting, anti-aliasing
grátis pelo supersample, e a pintura acompanha qualquer refação do casco sem
reposicionar nada.

Para o ventre, rasterize em θ∈0..2π sem costura e depois `np.roll(H/2)` — assim
a marca da barriga não é cortada pela emenda do UV.

**Marca com desenho próprio** (logo, matrícula, títulos) vem de mesh rasterizado
como acima. **Tudo que é retângulo ou faixa** — antenas, drenos, portas de poço,
marcações operacionais, manchas de desgaste — sai mais barato pelo
`scripts/pintar_marcas.py`, que recebe uma lista de itens em coordenadas de
aeronave e compõe sobre a livery existente sem apagar nada:

```python
exec(open(".claude/skills/livery-latam/scripts/pintar_marcas.py").read())
pintar([{"nome":"dreno fwd","tipo":"dreno","x_m":[8.4,8.7],"z_m":[-2.9,-2.6],
         "cor_hex":"#2A2C2E","lados":"ambos","intensidade":1.0}],
       spec, comprimento_uv=63.5)
```

Weathering entra pela mesma porta com `intensidade` fracionária (0,08–0,35): a
cor tinge sem cobrir, que é como sujeira se comporta.

## Quatro armadilhas de shader que custaram horas

**Alfa de imagem float não sobrevive a pack/reload.** A máscara de cobertura foi
guardada no canal alfa de uma imagem float; depois de salvar e reabrir o
`.blend`, o alfa virou 1,0 em todo lugar e o casco inteiro renderizou como vidro
azul-marinho. A defesa: a máscara mora numa **imagem separada, Non-Color**
(`LiveryFac`). Nunca dependa do alfa.

**Sockets do `ShaderNodeMix` são ambíguos por nome.** O nó tem dez entradas —
`Factor_Float`, `Factor_Vector`, `A_Float`, `B_Float`, `A_Vector`, `B_Vector`,
`A_Color`, `B_Color`, `A_Rotation`, `B_Rotation` — e várias compartilham o mesmo
*nome* ("A", "B", "Factor"). Você precisa do **identifier**, mas
`node.inputs['A_Color']` **não funciona**: a busca por chave do bpy usa o nome,
não o identifier, e levanta `KeyError`. Itere:

```python
def sock(node, ident, saida=False):
    for s in (node.outputs if saida else node.inputs):
        if s.identifier == ident:
            return s
    raise KeyError(f"{ident} nao existe: " +
                   ", ".join(s.identifier for s in (node.outputs if saida else node.inputs)))
```

Use `sock(mix, "A_Color")`, `sock(mix, "Factor_Float")`,
`sock(mix, "Result_Color", saida=True)`. A mensagem de erro listando os
identifiers disponíveis paga por si na primeira vez que a versão do Blender
mudar os nomes.

**Objeto oculto tem `matrix_world` obsoleto depois de reabrir o `.blend`.** Antes
de rasterizar decals que estão com `hide_viewport`, revele temporariamente e
chame `bpy.context.view_layer.update()`. Sem isso a matriz vem identidade, os
títulos somem da textura e o único sintoma é a contagem de pixels pintados cair
— sem erro nenhum.

**Imagem BYTE com valores sRGB.** Grave em imagem byte (sRGB por padrão) com
valores sRGB. `float_buffer` sem acertar o colorspace lava as cores.

## A cauda

O sash da deriva é a parte mais difícil de acertar e a que o dono mais cobrou.

**Os dois lados não são espelhados no sentido ingênuo.** Trabalhe com
coordenadas normalizadas de altura `h` e corda `c` e gere **texturas separadas
por lado** (`FinSashE`/`FinSashD`), atribuídas por sinal do centro da face. No
A320 o estibordo é a mesma pintura em (x,z) — a fita não dá a volta pelo bordo
de ataque, como se supôs no começo.

**O filete branco do bordo de ataque existe, mas é fino** — 0,30 m constante, não
11,5% da corda. A largura errada foi exatamente o que o dono apontou.

**A "faixa" traseira não é wrap circunferencial.** É uma **echarpe diagonal** a
~45°, que desce do dorso para a frente e fecha numa ponta aguda por baixo (no
PT-TMN, em x≈27,6, z≈−1,2). Ventre e tailcone ficam **brancos**; o anel de
escape da APU é metal nu. Modelar como wrap circular deixa a cauda visivelmente
errada.

**No tailcone, limite a echarpe por ÂNGULO, nunca por z.** O cone afina, então
uma altura fixa corresponde a um ângulo cada vez maior à medida que o raio
diminui — e o índigo acaba envolvendo a barriga sem que nenhum número em metros
denuncie. No 787-9 isso produziu 50–54% da circunferência pintada entre x=51 e
60, descendo a 107–116° da crista; o dono chamou de "azul a mais" olhando de
trás e por baixo. A forma certa é `θ_max` decrescente: ~110° onde a fita cruza a
fuselagem, caindo para ~30° na ponta do cone. Meça em **percentual da
circunferência** ao verificar — é a métrica que mostra o defeito.

**Matrícula pode ser assimétrica.** No CC-BGK (787-9) é branca dentro do índigo
a bombordo e índigo sobre branco a estibordo. E varia com a idade da pintura: o
PT-TMN saiu de fábrica com matrícula branca no índigo e hoje voa com índigo
sobre branco. Siga a foto de referência do dono e documente a variação no spec.

Todos esses contornos estão tabelados em `spec_a320.json → cauda_livery` e
`spec_b789.json → livery_cc_bgk`. Reaproveite a convenção `h`/`c` ao medir um
avião novo.

**A marca é a mesma em todos os aviões — meça uma vez e reaproveite.** O sash da
deriva não muda de desenho por tipo, só de escala. As polilinhas `F1..F7` do
A320 (`spec_a320.json → cauda_livery.fin_fronteiras`) são a geometria canônica:
aplique-as na convenção `h`/`c` do avião novo em vez de remedir por prosa. Foi
assim que o 787-9 saiu de um sash aproximado para o desenho certo.

**Mas a APLICAÇÃO no casco é específica do tipo — nunca extrapole.** O desenho
da marca na deriva se repete; o que ela faz ao encontrar a fuselagem, não.
Verificado em fotos das duas matrículas:

| | A320neo PT-TMN | 787-9 CC-BGK |
|---|---|---|
| Fuselagem traseira | índigo desce da deriva e **cobre a porta 2** | **branca**, sem echarpe |
| Matrícula | **branca dentro do índigo** | **índigo sobre branco** |

Faz sentido geométrico: no narrowbody a deriva é grande em relação ao casco
curto e o bloco de cor alcança a fuselagem; no widebody, longo e esbelto, o
mesmo desenho termina na deriva. Por isso a regra é foto **daquele tipo e
daquela matrícula** — assumir que o 787 se pinta como o A320 foi exatamente o
erro que custou horas.

Um detalhe que parece defeito e não é: **existe um triângulo branco no canto
inferior dianteiro da deriva**, entre a base do swoosh (`F4`) e o topo da massa
(`F7`) — a massa não toca o bordo de ataque. Não preencha. Quando a prosa de um
spec discordar da geometria medida do outro avião sobre a marca, **a marca
ganha**.

## Reaproveitar a marca entre modelos

É a mesma marca — então deve ser literalmente a mesma geometria. Importe do
`.blend` já pronto com `bpy.data.libraries.load` em vez de reimportar o SVG e
arriscar divergência de escala ou de traçado.

## Material: fazer tinta parecer tinta

A receita que o dono aprovou, em ordem de impacto:

- **Branco `#E6E7EA`, nunca `#FFFFFF`.** Branco puro estoura e mata a forma.
- **Coat 1,0 com Coat Roughness 0,05** — o verniz é o que dá leitura de avião
  novo.
- **Quebra de roughness**: `TexNoise` (scale 5, detail 6) → `MapRange` para
  0,32–0,48 → Roughness. Superfície com roughness constante lê como plástico.
- **Orange peel no Coat Normal**: `TexNoise` scale 1000 → `Bump` strength 0,08,
  distance 0,0005. É sutil e é o que vende a escala real.
- **Sol com ângulo físico 0,53°** (o disco solar real) — sombra com penumbra
  correta.
- **Cloud card**: área retangular grande (60×20) como preenchimento, imitando
  céu.
- **AgX Punchy com exposição ≈ −0,35**, mantendo os brancos em torno de 0,8.

Vidro de janela: **escuro, não reflexivo**. O feedback "as janelas estão
brancas" veio de vidro reflexivo demais. Base `#0B0F13`, roughness 0,28, coat
0,12, specular 0,35. Sulco de porta `#191B1D`, roughness 0,75, specular 0,1.

Para-brisa é máscara UV no shader do casco (`NoseMask`: R = moldura fosca,
G = vidro brilhante), nunca decal 3D. Os polígonos exatos dos vidros estão no
spec.

## Ventre

Ninguém olha até olhar de baixo, e aí o erro salta. O real: fuselagem **toda
branca** por baixo; carenagem ventral e intradorso de asas/estabilizadores em
cinza Airbus; mapa de antenas, drenos, beacon, outflow valve e escape da APU
tabelado em `spec_a320.json → ventre_real`. Frota jovem tem desgaste leve —
leque de spray atrás do trem do nariz e escorridos tan de 1 a 3 m abaixo dos
drenos, pintados na própria `LiveryTex/Fac` com fator fracionário.
