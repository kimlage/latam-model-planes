---
name: blender-mcp
description: Operar o Blender via addon MCP neste projeto sem perder trabalho nem tirar conclusão errada — subir/reiniciar o servidor, sobreviver a timeout de socket em execuções longas, evitar a corrida de arquivo de render que faz você ler o render anterior, e as regras de salvamento. Use SEMPRE que estiver executando código no Blender, renderizando, ou quando algo estranho acontecer: "o Blender travou", "não recebeu resposta", "o render está preto", "sumiu o objeto", "reiniciei o computador", "o servidor caiu". Leia ANTES de diagnosticar qualquer resultado de render inesperado — vários "bugs" deste projeto eram artefato de operação, não de modelagem.
---

# Operar o Blender via MCP

O addon MCP escuta na porta **9876** e executa Python arbitrário dentro do
Blender. É rápido de usar e tem três comportamentos que enganam. Todos os três
já produziram diagnóstico falso e retrabalho neste projeto.

`scripts/blender_mcp.sh` encapsula a parte operacional:

```bash
.claude/skills/blender-mcp/scripts/blender_mcp.sh start "airbus A320neo/A320neo_LATAM.blend"
.claude/skills/blender-mcp/scripts/blender_mcp.sh status
T=$(.claude/skills/blender-mcp/scripts/blender_mcp.sh marca)   # ANTES de renderizar
.claude/skills/blender-mcp/scripts/blender_mcp.sh wait "airbus A320neo/render_perfil.png" 20 "$T"
```

Pegue o marco **antes** de disparar o render. Um lote de 6 ângulos leva ~2,5 min
e frequentemente termina antes de você voltar a esperar por ele; um waiter que
só olha para o futuro fica preso aguardando uma escrita que já aconteceu. O
mesmo vale para `find -newermt` com tempo relativo: `-newermt '1 minute ago'`
avaliado depois do lote enxerga só os últimos arquivos e faz parecer que o
render travou.

## Armadilha 1 — "No data received" não quer dizer que falhou

Render longo estoura o timeout do socket. O que você recebe é um erro; o que
está acontecendo dentro do Blender é a execução seguindo normalmente até o fim.

Se você reagir ao erro reenviando o comando, agora há **dois** renders na fila,
os dois escrevendo no mesmo arquivo. Foi assim que nasceu a armadilha 2.

Depois de um timeout: não reenvie. Verifique o efeito colateral (o arquivo, ou
um `print` que você deixou no código) e siga a partir do estado real.

## Armadilha 2 — a corrida do arquivo de render

Renders enfileirados escrevem no mesmo caminho, um atrás do outro. Um waiter
ingênuo — "o arquivo existe, então leia" — pega o **primeiro** deles, que é o
render antigo, feito com o grafo de material anterior.

Isso custou três diagnósticos falsos de "casco preto" enquanto o material estava
correto — provado depois por renders de teste de 320 px, todos brancos.

A defesa está no `wait` do script: espera a primeira escrita posterior ao início,
aplica uma margem de 15–25 s, e depois espera o arquivo **parar de mudar** em
tamanho e mtime. Só então lê.

Complemento barato: renderize a 320 px para responder perguntas binárias ("o
material está preto ou não?"). Segundos em vez de minutos, e isola material de
geometria antes de gastar um render bom.

## Armadilha 3 — estado que não sobrevive ao reload

**`matrix_world` de objeto oculto vem obsoleto.** Depois de reabrir o `.blend`,
objetos com `hide_viewport` podem devolver matriz identidade. Antes de qualquer
código que leia posição de objeto oculto (rasterizar decals, por exemplo),
revele temporariamente e chame `bpy.context.view_layer.update()`. O sintoma é
cruel: nada falha, só o resultado sai errado — títulos somem da textura e a
contagem de pixels pintados cai sem nenhum erro.

**Malha sem usuário some no purge.** Malhas de apoio (glyphs de matrícula,
alvos temporários) são coletadas quando ninguém as referencia. Se você vai
depender delas depois de um reload, marque `use_fake_user = True`.

**Crash no meio da execução deixa o arquivo pela metade.** Um script que apaga
antes de recriar, interrompido no meio, salva o estado apagado. Prefira criar o
novo e só então remover o antigo; e salve com `bpy.ops.wm.save_mainfile()` ao
fim de cada bloco que deu certo — o `.blend1` é o único backup que existe.

## Subir e reiniciar

```bash
/Applications/Blender.app/Contents/MacOS/Blender "<caminho.blend>" \
  --python-expr "import bpy; bpy.ops.preferences.addon_enable(module='blender_mcp_addon'); bpy.ops.blendermcp.start_server()"
```

O `start` do script confere antes se a porta já está ocupada e não sobe uma
segunda instância — duas instâncias disputando o mesmo `.blend` corrompem o
arquivo.

Reiniciar descarta tudo que não foi salvo. Se o Blender ainda responde ao MCP,
salve por lá antes de matar o processo. Se travou de vez, `restart` mata e sobe
de novo — e você perde desde o último `save_mainfile`, o que é mais um argumento
para salvar cedo e com frequência.

Depois de reinício da máquina, o Blender não volta sozinho: a primeira coisa a
fazer numa sessão nova é `status`, e `start` se estiver fechado.

## Higiene do código enviado

**Imprima o que dá para conferir.** Contagem de pixels pintados, número de
vértices, cotas medidas por raycast. Como o socket pode cair, o `print` é
frequentemente a única evidência do que aconteceu — e é o que permite comparar
entre execuções ("os pixels pintados caíram de 250444 para 192238" é um sinal
de que algo sumiu).

**Um bloco, um assunto.** Blocos longos que fazem geometria, material e render
juntos são difíceis de retomar depois de um timeout, porque você não sabe até
onde foi.

**Renderize por último, e salve antes.** Se o render estourar o socket, o
trabalho já está no disco.
