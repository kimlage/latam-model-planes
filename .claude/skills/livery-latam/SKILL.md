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

### O desenho da deriva: bandas de bordo a bordo

O sash é um conjunto de **bandas paralelas que atravessam a deriva inteira, do
bordo de ataque ao bordo de fuga**, sobre um campo **índigo**. Cada banda é um
paralelogramo **cinza-voo nas duas pontas e coral no miolo**. Acima da banda
superior o topo é cinza-voo.

O que **não** é: deriva branca com bandas grossas que morrem no meio da corda.
Essa era a leitura das polilinhas `F1..F7` herdadas, e o dono reprovou —
*"o design da faixa lateral tem que ir de ponta a ponta, a espessura das faixas
tb esta errado"*. As `F1..F7` estão obsoletas; não as use.

A geometria canônica agora é medida, em duas coordenadas lineares:

```
b = z − 0.24·x     através das bandas
e = z + 0.25·x     ao longo das bandas

banda inferior:  b ∈ [−6.725, −5.99]   coral onde e ∈ [22.006, 23.332]
banda superior:  b ∈ [−4.208, −3.35]   coral onde e ∈ [24.913, 26.192]
b ≥ −3.35 → cinza-voo (cap do topo)   ·   resto → índigo
```

(referencial do 787-9; `spec_b789.json → cauda_livery.fin_bandas_medidas_2026_08_17`)

**A marca é a mesma em todos os aviões — só muda a escala do fin.** Transfira por
coordenadas normalizadas `h = (z−z_raiz)/(z_topo−z_raiz)` e
`c = (x−LE(z))/(TE(z)−LE(z))`: converta o texel do avião novo para `(h,c)`, leve
esse `(h,c)` de volta ao referencial do 787 e avalie `b`/`e` lá. Foi assim que o
A320 recebeu o desenho sem remedir nada.

### Retificar a foto é o que destrava a medição

A deriva é **plana**, então uma foto dela é uma homografia — e para teleobjetiva,
uma afim. Reprojete a foto para o plano `(x,z)` da deriva antes de medir:
subitamente o desenho vira retângulos e o que era ilegível fica óbvio. Foi o
passo que resolveu depois de várias tentativas frustradas de ler ângulos e
espessuras na foto crua.

Determine a afim por duas direções conhecidas (bordo de ataque e corda da ponta)
mais uma escala. Depois **ajuste os parâmetros por descida coordenada** contra a
foto classificada em coral/índigo/cinza: no CC-BGP isso levou a concordância de
91,4% para **92,6%** pixel a pixel. Um número de concordância é o que permite
dizer "está certo" sem discutir se "parece".

Para achar a inclinação das bandas sem chutar: varra a inclinação `m`, agrupe os
pixels por `b = z − m·x` e escolha o `m` que **minimiza a impureza de cor por
faixa**. A banda certa é a que fica de uma cor só.

**Mas a APLICAÇÃO no casco é específica do tipo — nunca extrapole.** O desenho
da marca na deriva se repete; o que ela faz ao encontrar a fuselagem, não.
Verificado em fotos das duas matrículas:

| | A320neo PT-TMN | 787-9 CC-BGK / CC-BGP |
|---|---|---|
| Fuselagem traseira | índigo desce da deriva e **cobre a porta 2** | **cunha triangular** índigo, fronteira dianteira reta cortando a porta traseira; dorso e ventre brancos |
| Matrícula | **branca dentro do índigo** | **branca dentro do índigo**, sobre a cunha |

Nos dois casos o índigo desce até a fuselagem — mas com **formato diferente**, e
é isso que precisa ser medido por tipo. A regra é foto **daquele tipo e daquela
matrícula**.

Este ponto teve **duas correções em sentidos opostos**, e as duas valem como
aviso. Primeiro o spec descrevia uma echarpe que não existia e foram gastas
horas refinando o formato dela; depois, ao remover, removeu-se **demais** — a
fuselagem ficou toda branca, quando a foto mostra a cunha claramente. A lição
não é "a foto ganha" (isso já está na regra 4); é que **corrigir um erro para o
lado oposto também é errar**. Quando o dono aponta excesso, meça o quanto tirar
em vez de zerar.

## A écharpe do casco — o modelo, e os quatro jeitos de errar

A mancha índigo da fuselagem traseira é a **mesma massa** do índigo da raiz da
deriva, descendo para o casco. Duas fronteiras a definem, e **elas vivem em
espaços diferentes** — foi não perceber isso que custou quatro rodadas.

```
índigo ⟺ x ≥ x0 + k·z              (fronteira DIANTEIRA — reta no plano (x,z))
      E  θ ≤ θ0 − r·(x − xr)        (fronteira INFERIOR — reta no plano (x,θ))
      E  x ≤ x_tras
```

`θ` é medido a partir da crista; `z = centro_z(x) + raio(x)·cos θ`.

**787-9:** `x ≥ 48,77 + 0,992·z` ; `θ ≤ 117,0 − 5,2·(x − 48,70)` ; `x ≤ 57,14 + 0,3858·z`
**A320neo:** `x ≥ 27,39 + 0,8393·z` ; `θ ≤ 101,4 − 7,58·(x − 29,11)` ; `x ≤ 34,52 + 0,0538·z`

O limite traseiro é a **própria reta do bordo de fuga da deriva**: o índigo para na
projeção do BF, e dali para trás ficam a carenagem da raiz do BF e o cone de cauda,
ambos brancos. Cortar por um `x` constante deixa índigo por cima da carenagem — foi
o defeito que o dono apontou com o resto já aprovado.

### Erro 1 — modelar a fronteira inferior como reta em (x,z)

Foi tentada três vezes: corte horizontal, 16° medidos em foto, e a reta do
estabilizador. **As três dão cunha pequena demais.** A fronteira inferior é
reta em **(x, θ)**, não em (x, z). No bordo dianteiro ela desce a ~117° da
crista — bem abaixo da meia-largura, quase na quilha — e estreita para trás.
Qualquer reta em (x,z) para por volta de 90° e a cunha fica raquítica.

Como medir: varra a foto **coluna a coluna**; em cada coluna ache a silhueta do
casco (topo e base) e a borda inferior do índigo; converta para
`u = (y_ind − y_topo)/(y_base − y_topo)` e daí `θ = acos(1 − 2u)`. Ajuste `θ(x)`.
Sai uma reta limpa. Calibre `x` pelo **passo das janelas**, nunca pelo vão
nariz-cauda.

### Erro 2 — a fronteira dianteira não é o bordo de ataque

Ela é **paralela** ao BA reto da deriva, deslocada ~0,10·H para trás
(0,86 m no 787, 0,62 m no A320). E o BA reto do 787 é **45,2°**, não os 40,5°
que o spec trazia — 40,5° é a corda da carenagem dorsal curva. Ver
`extrair-cotas`.

### Erro 3 — desenhar a fronteira como reta na textura (x,θ)

Um corte plano `x = x0 + k·z` **não é uma reta** em UV. Traçar reta ali erra até
0,9 m na cintura. E **não resolva o `x` da fronteira uma vez por linha** da
textura: isso serrilha a borda e cria ilhas de índigo soltas, porque a linha
inteira é aceita ou descartada. Cada texel já conhece o próprio `x` e `θ`, logo
o próprio `z` — o teste é direto e vetorizado, sem iteração nenhuma.

### Erro 4 — pintar "só onde já era branco"

Deixa buraco em cada linha de painel e contorno de porta. A `LiveryTex` mistura
duas camadas: **base** (branco/índigo) e **marcações** (matrícula, portas,
painéis). Ao mover a fronteira, aplique a cor de base **só nos texels chapados**
(branco puro ou índigo puro) e deixe a camada de marcação intacta — os contornos
passam a ler por cima do índigo, como no avião real.

Não tente reconstruir por modulação relativa (`orig / base`): amplifica o ruído
da textura e duplica marcações que estavam quase invisíveis. Tentado, piorou.

**Matrícula:** letras brancas sobre o índigo. Se a fronteira mudar e ela cair
fora da mancha, pinte-a **índigo sobre branco** — é variante legítima da LATAM —
em vez de tentar recortá-la e recolá-la. Recorte com limiar sempre quebra o
glifo ou arrasta linha de painel junto.

### Erro 5 — cortar a cunha por um `x` constante atrás

O índigo não termina numa estação; termina na **reta do bordo de fuga da deriva**.
Atrás dela existe a carenagem clara da raiz do BF, que continua no cone de cauda.
Com corte em `x` constante o índigo invade essa carenagem e a junção
deriva × estabilizador × cone fica errada — foi o último defeito apontado, com o
resto da cauda já aprovado. Confira esse canto com zoom, sempre.

## Confira a PROPORÇÃO do lockup, não só o desenho

Rasterizar do SVG oficial garante a forma de cada glifo, mas **não garante que o
resultado foi colado na proporção certa**. No 787-9 o lockup da fuselagem estava
**28% esticado na vertical**: 8,96 m de comprimento por 2,67 m de altura, quando
o vetor oficial tem proporção **4,30**. O desenho estava perfeito e o conjunto,
errado — e o efeito colateral era a marca invadindo a fileira de janelas.

A verificação é aritmética e leva segundos, mas **tem uma pegadinha: os texels da
textura `(x,θ)` não são quadrados**. Converta para metros antes de dividir:

```
metros por coluna = comprimento_fuselagem / largura_da_textura
metros por linha  = 2π·raio            / altura_da_textura
proporção = (n_colunas · m_por_coluna) / (n_linhas · m_por_linha)
```

Compare com a proporção do bbox de tinta do próprio SVG. Se divergir, corrija a
dimensão que estiver errada e **ancore no lado que já está certo** — no 787 a
âncora foi o topo, o que de quebra tirou a marca de cima das janelas.

Ao reescalar tinta já rasterizada, use **média de área**, nunca vizinho mais
próximo: com nearest as letras saem serrilhadas e o dono vê. E limpe a franja
anti-aliasing da versão antiga, senão fica um fantasma — mas **restrinja a
limpeza ao bbox da própria marca**. Limpar "tudo que tem saturação" numa faixa
larga apagou pedaços dos contornos das portas, que também são levemente
tingidos.

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
