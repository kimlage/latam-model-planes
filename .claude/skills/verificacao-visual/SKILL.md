---
name: verificacao-visual
description: O gate de qualidade do projeto — renderizar os 6 ângulos canônicos, montar a folha de contato, comparar contra as fotos de referência e só então declarar um avião pronto. Use SEMPRE antes de entregar, mostrar ou dizer que algo está concluído, e sempre que a pergunta for sobre estado ou qualidade: "está pronto?", "como ficou?", "verifica o modelo", "gera os renders", "compara com a foto", "o que mudou". Use também quando o dono reclamar de qualidade sem apontar o defeito — a folha de contato é a forma de achar o defeito. Traz a checklist dos erros que já passaram despercebidos.
---

# Verificação visual

Este gate existe porque a falha mais cara do projeto não foi geométrica: foi
declarar pronto sem olhar. O dono cobrou isso mais de uma vez — *"tenha certeza
de realmente conseguir fazer a verificacao final visual"*, e depois *"o criterio
de qualidade está muitooo baixo. vc nao olhou oq esta fazendo"*.

A regra é simples: **nada é entregue sem passar por aqui, e "passar por aqui"
significa você abrir as imagens e olhar** — não gerar os arquivos e presumir.

## Rodar

Renderize os seis ângulos canônicos e monte a folha:

```bash
python3 verificacao_visual.py "airbus A320neo"
```

O script está na raiz e espera estes arquivos na pasta da aeronave:

| Arquivo | Ângulo | Para que serve |
|---|---|---|
| `render_frontal.png` | 3/4 frontal | proporção do nariz, para-brisa, motores |
| `render_nariz.png` | close do nariz | vidros, contorno da porta 1, radome |
| `render_perfil.png` | perfil puro | comparação direta com a foto de referência |
| `render_hero.png` | 3/4 clássico | leitura geral, é o que vende ou entrega o modelo |
| `render_cauda.png` | cauda | sash, echarpe, matrícula, estabilizadores |
| `render_frente_baixa.png` | frente baixa | ventre, carenagem, trem, nacelles |

Saída: `verificacao_visual.png` na pasta da aeronave.

Para renderizar com segurança (a fila de render tem uma corrida conhecida), veja
`blender-mcp` — em especial o `wait`, que evita ler o render anterior.

## Comparar, não admirar

Abra a folha **lado a lado com as fotos de referência da matrícula**. O objetivo
não é achar bonito; é achar a divergência. Para cada painel, pergunte o que
mudaria se você sobrepusesse a foto.

**Se você não tem a foto, pare e busque agora** — `WebSearch` pela matrícula,
JetPhotos, Planespotters, Wikimedia. Comparar o render com a *descrição* de um
spec não é comparar com nada: a descrição pode estar errada, e nesse caso o
gate aprova o erro com convicção. Foi o que aconteceu com a echarpe do 787-9,
refinada por horas contra um texto que descrevia uma pintura inexistente.

Vale medir quando a dúvida é de proporção: recorte o mesmo trecho do render e da
foto na mesma escala e compare. É mais rápido do que discutir se "parece" certo.

## Checklist — os defeitos que já passaram

Cada item aqui é um erro real que chegou até o dono. Se você não conseguir dizer
"conferi e está ok" para todos, ainda não está pronto.

**Nariz**
- amassado ou ondulado sob a tinta brilhante (gaiola densa demais — ver
  `casco-parametrico`)
- achatado, sem o lobo superior pinçado — o para-brisa não "vira para a frente"
- para-brisa com posição ou tamanho errado em relação à ponta

**Corpo**
- cintura fantasma no barril (halo de cota na extração)
- barril ondulando em vez de seção constante
- transição visível entre nariz, barril e cauda

**Peças conectadas**
- asa, deriva, estabilizador ou pylon com fresta na raiz
- trem "voando" — perna curta demais, sem entrar no poço
- qualquer elemento visivelmente descolado da carroceria

**Superfície e detalhes**
- porta lendo "pela metade" (só os arcos de cima e de baixo)
- porta enterrada pelo encolhimento do subsurf
- janelas brancas ou espelhadas em vez de vidro escuro
- janelas ou portas ausentes num lado só

**Cauda — a região que mais reprovou**
- cunha índigo do casco pequena demais (fronteira inferior modelada como reta
  em `(x,z)` em vez de `(x,θ)` — ver `livery-latam`)
- fronteira serrilhada ou com ilhas de índigo soltas (resolvida por linha da
  textura em vez de por texel)
- buraco na pintura em cima de linha de painel e contorno de porta (pintou "só
  onde já era branco")
- matrícula quebrada ou duplicada depois de mover a fronteira
- **junção raiz do BF da deriva × estabilizador × cone de cauda** — confira
  esse canto especificamente, com zoom; é onde três peças se encontram e onde
  o dono apontou defeito com o resto já aprovado

**Livery**
- marca desenhada com fonte parecida em vez do SVG oficial
- sash da deriva com filete do bordo de ataque largo demais
- echarpe traseira como wrap circunferencial em vez de diagonal
- ventre ou tailcone índigo quando deveriam ser brancos
- matrícula no padrão errado para aquela matrícula/época

**Render**
- branco estourado (use `#E6E7EA`, exposição controlada)
- superfície com roughness constante lendo como plástico

## Quando o dono aponta um defeito

Três coisas que funcionaram melhor que responder rápido:

**Reproduza o defeito no seu render antes de mexer.** Se você não consegue ver o
que ele viu, você vai consertar outra coisa. Renderize o mesmo ângulo da
captura que ele mandou.

**E renderize esse mesmo ângulo de novo depois — antes de dizer que corrigiu.**
Medir o artefato (textura, malha, spec) prova que *alguma coisa* mudou, não que
mudou onde ele está olhando. No 787-9 uma correção da echarpe melhorou os
números de x=55 para trás e deixou x 47–55 intacto; a medição ficou ótima e o
dono respondeu "não mudou nada" — porque a região dele era justamente a que
sobrou. Um par antes/depois com a **mesma câmera e a mesma luz** é a única
evidência que vale, e é barato: dois renders de 320–900 px.

**Ataque a causa, não o sintoma.** "O bico está amassado" foi tratado três vezes
adensando a malha, e piorou nas três. A causa era o método, não a resolução.

**Feche o ciclo com evidência.** Depois da correção, renderize o mesmo ângulo e
compare com o anterior. Dizer "corrigi" sem mostrar o antes e depois é o que
gera a próxima rodada de frustração.

## Depois do gate

Quando a folha estiver aprovada, atualize o `spec_<tipo>.json` com o que foi
aprendido no ciclo e registre no `README.md` o que mudou. O modelo é
reconstruível a partir do spec; o que não estiver escrito lá se perde na próxima
refação.
