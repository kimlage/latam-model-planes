---
name: nova-aeronave
description: Pipeline completo para construir (ou retomar) a réplica 3D de uma aeronave da frota LATAM no Blender — do documento oficial do fabricante até o modelo aprovado no gate visual. Use SEMPRE que o pedido envolver começar, continuar, derivar ou refinar um avião deste repositório: "vamos fazer o 767-300ER", "constrói o A321neo", "duplica o A320 pro A319", "continua o 787", "por que o modelo está diferente da foto". Também use quando alguém perguntar como o projeto funciona ou qual a ordem das etapas. Esta skill é o roteador — ela decide qual das skills específicas (fontes-aeronave, extrair-cotas, casco-parametrico, livery-latam, verificacao-visual, blender-mcp) entra em cada fase.
---

# Nova aeronave — pipeline do projeto

Este repositório existe para uma coisa: réplicas que um engenheiro da LATAM
reconheceria como o avião dele. A régua não é "parece um avião" — é
"as cotas batem com o documento do fabricante e a pintura bate com a foto
daquela matrícula".

Duas aeronaves já passaram por esse pipeline (A320neo/PT-TMN e 787-9/CC-BGK).
Quase todo o custo delas foi retrabalho por pular etapa. A ordem abaixo é o
resultado desse retrabalho — siga-a mesmo quando parecer mais rápido modelar
"no olho".

## A regra zero: olhe o avião antes de tudo

Antes do documento, antes do spec, antes de abrir o Blender: **busque fotos da
matrícula real e olhe**. Um minuto de `WebSearch` ou JetPhotos. Se o dono
mandou foto, ela é a fonte de maior autoridade do projeto.

Isso não é a validação do fim — é o ponto de partida, e existe porque já falhou
de forma cara: o spec do 787-9 descrevia uma echarpe índigo no casco que
simplesmente **não existe** no avião real. A descrição sobreviveu a
fotogrametria, medição de desenho, dois workflows de pesquisa e verificação
adversarial. A primeira foto do Google resolveu em segundos.

Ver o avião é o que permite acertar o detalhe fino — e o que impede de passar
horas refinando cuidadosamente algo que não deveria estar ali. Detalhe em
`fontes-aeronave`.

## A regra que organiza tudo: dado antes de malha

Nunca modele antes de ter número. Se a cota existe num documento oficial,
buscá-la custa minutos; descobrir depois que o casco inteiro está errado custa
horas e uma rodada de frustração do dono do projeto. Toda vez que o modelo
divergiu da foto, a causa foi a mesma: alguém estimou onde havia dado.

Quando o dado não existir em documento (aplicação da livery, tom exato,
desgaste), meça em foto por fotogrametria — também é dado, com incerteza
declarada. O que não vale é chutar.

## As seis fases

### 1. Fontes — antes de abrir o Blender
Levantar o documento dimensional oficial (Airbus ACAP / Boeing APR), as fotos
da matrícula específica que vai ser replicada, e o que existe de CAD aberto
como referência de blocking.

→ Use **`fontes-aeronave`**. O inventário já pronto dos 12 tipos da frota está
em [FONTES-FROTA.md](FONTES-FROTA.md) — comece por ele.

Antes de tratar a aeronave como nova, verifique se ela não é derivada de uma já
construída. A frota tem muita célula compartilhada (A320ceo/neo, A321ceo/neo,
767-300ER/-300F/-300BCF, 787-8/-9). Derivar por stretch/plug paramétrico de um
casco validado é mais rápido e mais fiel do que extrair do zero — mas valide o
derivado contra o 3-view próprio dele, porque portas, trem e ponta de asa mudam.

### 2. Extração — desenho cotado vira números
Rasterizar as vistas do PDF a 600 dpi, calibrar por uma cota impressa, extrair
crown/keel/meia-largura, e gravar `<aeronave>/<tipo>_curves.json` +
`spec_<tipo>.json`.

→ Use **`extrair-cotas`**.

O `spec_*.json` é o artefato mais valioso do repositório: é ele que sobrevive a
qualquer refação do modelo. Trate-o como a fonte da verdade e mantenha-o
atualizado quando medir algo novo.

### 3. Casco e estrutura — a geometria
Gaiola de controle esparsa nas cavernas reais + subsurf Catmull-Clark, seções
ovoides no nariz, asas/empenagem por loft NACA, raízes enterradas no corpo.

→ Use **`casco-parametrico`**.

### 4. Livery — a marca
Vetores oficiais da marca (nunca fonte parecida), aplicação medida na foto da
matrícula, pintura como textura UV `(x,θ)` — não como casca 3D.

→ Use **`livery-latam`**.

### 5. Detalhes — o avião inteiro
Portas, janelas, trem, motores, antenas, ventre. O dono já reprovou modelo com
"vários elementos desconectados da carroceria" e "trens de pouso fora voando":
o critério é o avião completo e conexo, não o casco pintado.

Coberto por `casco-parametrico` (geometria analítica sobre a superfície) e
`livery-latam` (contornos e marcações pintadas na textura).

### 6. Gate visual — só então está pronto
Renderizar os 6 ângulos canônicos, montar a folha de contato e **olhar**,
comparando com as fotos de referência.

→ Use **`verificacao-visual`**. Nada é entregue sem passar por aqui.

Em qualquer fase que envolva falar com o Blender, **`blender-mcp`** tem as
armadilhas operacionais (timeout de socket, corrida de arquivo de render,
matriz obsoleta) que já causaram diagnósticos falsos caros.

## Estrutura de pastas

Uma pasta por aeronave, na raiz do repositório, com o nome comercial em
minúsculas (`airbus A320neo/`, `boeing 787-9/`). Dentro:

| Arquivo | O que é |
|---|---|
| `<TIPO>_LATAM.blend` | o modelo |
| `spec_<tipo>.json` | especificação de engenharia — a fonte da verdade |
| `<tipo>_curves.json` | contornos crus extraídos do desenho |
| `<tipo>_hull_smooth.json` | curvas densificadas (PCHIP) prontas para loft |
| `extract_<tipo>.py` | o script de extração daquele desenho, com as âncoras |
| `<DOC>_<fabricante>.pdf` | o documento oficial |
| `render_*.png` | os 6 ângulos canônicos |
| `insp_*.png` | crops de inspeção usados para ancorar/medir |
| `verificacao_visual.png` | a folha de contato do gate |

Compartilhado na raiz: `latam_livery_kit.py`, os SVGs oficiais da marca,
`verificacao_visual.py`, `FONTES-FROTA.md`, `README.md`.

## Reaproveitar entre aviões

O segundo avião custou uma fração do primeiro porque reaproveitou. Ao começar
um novo, duplique o `.blend` de um já pronto: materiais, câmeras, cenário e
mundo vêm juntos, e as câmeras só precisam ser reescaladas pela razão de
comprimento (787/A320 = ×1,672). As marcas oficiais podem ser importadas do
outro blend com `bpy.data.libraries.load` — é a mesma marca, então é literalmente
a mesma geometria, sem risco de divergir.

## Quando aparecer spec melhor

Diretriz do dono: **spec melhor achada → refinar o que já existe.** Se a
pesquisa encontrar um documento mais novo ou mais preciso de uma aeronave já
construída (ex.: ACAP A320 Rev 46 de jul/2026 substituindo o Jun/24 usado),
diffe os desenhos e ajuste o modelo. Não deixe o modelo antigo divergir da
melhor fonte disponível só porque "já estava pronto".

## Um aviso sobre ritmo

O ciclo real é: construir → renderizar → olhar → o dono aponta o defeito →
corrigir. Você vai fazer muitas voltas. As voltas caras são as que gastam uma
rodada inteira para descobrir algo que um render de 320 px teria mostrado.
Renderize barato e cedo, olhe você mesmo antes de mostrar, e só chame o dono
quando tiver algo que você mesmo aprovaria.
