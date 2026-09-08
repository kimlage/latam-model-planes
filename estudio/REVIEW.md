## Série cinematográfica configurável — 2026-09-05

A direção foi corrigida após o usuário rejeitar o avião isolado: `loading/` agora é uma biblioteca de cenas completas por aeroporto, aeronave e situação. Dez combinações em SBGR/SDSC, três aeronaves, decolagem/pátio/reboque. O reboque fica restrito ao 787 calibrado. Editor abre a combinação exata; GIF/PNG-sequência/MP4 incorporam a passagem pelo preto. O estudo anterior está preservado em `loading/isolado.html`.

Validação desta rodada: 10/10 composições com câmera móvel, projeções finitas e aeronave em quadro ao longo da cena; controles, restrições de combinação, mobile, pausa, origem de mensagens, abertura no editor, transição e poster com movimento reduzido passaram. Os 22 testes de regressão do editor/exportação passaram. Novo MP4 GRU/A320/pátio: H.264, 960×540, 25 fps, 300 quadros / 12 s, créditos CC BY e ODbL. Capturas e logs em `output/playwright/cinema-*`. Posicionamentos do pátio corrigidos após revisão dos equipamentos próximos às asas. Browser validado: Chromium. Acabamento de cenário ainda simplificado, sem aprovação fotorrealista; nenhuma publicação externa.

## Loading de aplicação — 2026-09-05

Nova produção `latam-loading` e componente em `loading/`. Loop de 4 s / 100 quadros, 777 herói, câmera fixa, PNG com alpha e MP4 para a interface. 14 verificações de loading passaram no Chromium: continuidade de pose/velocidade/câmera, ausência de progresso fictício, limites, conclusão, erro/retry, texto seguro, remoção, reprodução da volta, celular sem overflow, movimento reduzido inicial/dinâmico e fallback de vídeo. Aeronave inteira nos 100 quadros; capturas desktop, celular e painel revisadas em `output/playwright/loading-*`. A prévia não está ligada ao backend de uma aplicação externa. Safari e Firefox não foram testados nesta rodada.

# Scene Studio — retomada e revisão de 2026-09-04

## Incremento entregue: cenários, operações e câmeras

Esta seção registra a fase posterior à revisão inicial abaixo e atualiza seus
limites sobre cenários, direção e exportação. Guia atual: [PRODUCOES.md](PRODUCOES.md).

- Quatro produções: decolagem GRU (7,95 s), reboque ao hangar 9 (16 s),
  apresentação de GRU (24 s) e visita ao MRO de São Carlos (16 s).
- Contextos completos dos masters locais, preservando coordenadas, terminais,
  entorno, hangar aberto, revestimentos selecionados e iluminação interna.
- Planos editáveis com cortes, movimentos, acompanhamento e FOV; reenquadramento
  pela viewport, histórico, JSON e reprodução equivalente no embed.
- Avião, trator, barra e direção do trem de nariz coordenados a partir do master.
- Pavimentos a 22 bits de posição Draco. A grama de São Carlos estava coplanar
  com o concreto (diferença medida de cerca de 0,00017 m); a exportação a coloca
  2,5 cm abaixo, eliminando as faixas visíveis durante o reboque. Pisos e estradas
  do contexto também deixaram de projetar sombras como se fossem edifícios.
- MP4 H.264 local com ffmpeg, créditos nos metadados, limites de tamanho/origem,
  cancelamento da captura e restauração do editor. ZIP de PNG com metadados/créditos.
- Corrigida a espera por PNG em aba de segundo plano: no ensaio a 1280×720,
  `toBlob` levou aproximadamente 1009 ms e `toDataURL` 8 ms. A sequência usa
  captura síncrona com devolução do controle ao navegador entre os quadros.

**Validação final:** 22/22 testes anteriores e 13/13 das produções passaram;
2/2 testes Python do encoder passaram. Reenquadramento pela interface com arrasto
e gravação foi exercitado em uma sessão isolada. Um embed real carregou a cena
e coincidiu com a posição da câmera do editor no corte de 4 s.

Os quatro MP4s finais foram produzidos em **960×540**, decodificados para revisão
visual e conferidos por ffprobe: respectivamente 159, 400, 600 e 400 quadros,
taxas 20/25/25/25 fps, durações 7,95/16/24/16 s e créditos presentes. Capturas dos
extremos, cortes e frames intermediários registram o resultado após as correções.
`output/playwright/producoes.html` é a vitrine local; o log é
`output/playwright/producoes-regression-final.json`.

**Limites observados:** o ZIP completo fica em memória, até 512 MB. A produção
institucional de 24 s excedeu esse limite em 1280×720 e foi exportada em 960×540;
o limite restaurou o editor corretamente. A modelagem do entorno/equipamentos
continua simplificada e parte da arquitetura é interpretada; não é fotogrametria
nem simulação operacional certificada. O reboque termina com entrada parcial.
Nenhum master Blender foi sobrescrito. O trabalho permanece local e sem commit.

## Histórico: revisão inicial da interface

## Estado encontrado

Checkout `main` em `8cce2f4`, limpo no início da revisão, dez commits à frente
da referência local `origin/main`. Apenas um worktree registrado. Não houve
fetch, portanto essa comparação não afirma o estado atual do GitHub.

O Claude já havia construído um editor funcional em JavaScript/Three.js,
sem build ou dependências remotas: 11 aeronaves, 46 peças dos aeroportos,
9 props autorais, nove cenas iniciais, gizmos, histórico, iluminação,
animação por keyframes e receitas de voo. As cinco saídas implementadas
eram GIF, PNG, sequência PNG em ZIP, JSON e embed navegável.

Os commits de maior relevância para a continuidade eram `844f19d` (nível
heroi), `76d57df` (detalhe por objeto, câmera e contato com o solo), `c3c9d3b`
(clipe de GRU) e `0870a93` (preservação do trabalho interrompido).
O histórico posterior contém principalmente validações e documentação
das exportações. Os arquivos do estúdio e os dois clipes JSON estão presentes.

## Diagnóstico e correções implementadas

| Problema observado no código ou no navegador | Comportamento após a correção |
|---|---|
| Recarregar sempre abria o preset inicial | Sessão automática, indicador de gravação, recuperação após reload e cópia ao trocar de cena |
| Renomear podia perder a original se a gravação falhasse | Uma gravação atômica, colisões recusadas e erros visíveis |
| Biblioteca ilegível podia ser sobrescrita pelo fallback vazio | Bytes originais preservados; gravação recusada |
| JSON arbitrário substituía o documento antes da validação | Validação de schema, tipos, dimensões, números, render, câmera, objetos e animação antes de alterar a cena |
| Erro de asset era apenas escrito no console e a cena ficava incompleta | Construção antes da substituição e mensagem de erro ao usuário |
| Troca de asset com o mesmo ID podia reutilizar outra geometria | Sincronização considera ID, slug, tipo e nível |
| Delete podia atingir simultaneamente objeto e keyframe | Keyframe selecionado tem prioridade e a ação é desfeita corretamente |
| Atalhos continuavam ativos atrás de diálogos | Fundo inerte, foco contido e restauração do foco ao fechar |
| Seleção aditiva permitia incluir objetos travados | Mesma regra de bloqueio e visibilidade em seleção simples e aditiva |
| Câmera visual não acompanhava undo/redo | Restauração da pose, projeção e câmera do gizmo; enquadramento e poses entram no histórico |
| Navegação ortográfica era sobrescrita a cada render | Controle da câmera persistente que origina a projeção ortográfica |
| JSON formava caminhos como `export/web/heroi/...` | Uma raiz `export/`, mantendo a subpasta de cada asset |
| Texto da cena podia encerrar o script no embed | JSON escapado para HTML e validação das URLs de base |
| Clipboard anunciava sucesso sem aguardar a gravação | Resultado aguardado; falha apresentada |
| Colunas permanentes espremiam o canvas em telas pequenas | Painéis recolhíveis e drawers abaixo de 900 px |
| Biblioteca longa, busca sem resultado ficava vazia | Filtro por categoria, estado vazio e operação por teclado |
| Timeline aberta ocupava espaço em cenas sem animação | Recolhida inicialmente para cenas estáticas |
| Preset Single hero usava malha web e contraluz escura | Nível heroi e luz frontal, sem modificar o arquivo 3D |
| Ajustes de luz recriavam chão e grade sem necessidade | Reutilização da geometria quando os parâmetros não mudam; descarte de recursos próprios ao substituir |

O executável `python3 estudio/serve.py` serve a raiz correta em loopback,
porta 8137, com revalidação de cache. O servidor genérico de Python continua
compatível. Não foi introduzido gerenciador de pacotes ou etapa de build.

## Evidências desta execução

- **22/22 casos de regressão passaram** em Chromium/Playwright, usando
  `tests/regression.js`. Incluem carregamento real de todos os nove presets,
  normalização dos dois clipes JSON existentes, falhas de documento/asset,
  biblioteca, câmera, atalhos e exportações.
- PNG gerado e decodificado em 480 × 270; GIF de oito quadros gerado,
  com restauração do documento e da câmera; ZIP com quatro PNGs verificado.
  São testes funcionais curtos, não medição de exportações longas.
- JSON com aeronave heroi e peças de aeroporto: os caminhos exportados
  responderam HTTP 200. Embed HTML realmente baixado e aberto em outra aba.
- Edição do nome, gravação automática e reload: a sessão foi recuperada.
  Filtro de aeronaves devolveu os onze itens; busca inexistente mostrou a mensagem.
- Revisão visual em 1440 × 900 e 390 × 844; em 390 px, largura do corpo e
  do viewport igual a 390 px, sem overflow horizontal. Biblioteca abriu e fechou.
- Nível do B777 confirmado no documento e na instância: `heroi`.
  O contador estabilizado mostrou 171.119 triângulos na cena de um objeto.
- Verificação de sintaxe dos módulos alterados, compilação do lançador Python
  e `git diff --check` passaram.

Artefatos locais, ignorados pelo Git: `../output/playwright/`. O log final
é `regression-final.log`; capturas numeradas registram a interface original,
desktop, celular, biblioteca, novo preset e embed. As mensagens deliberadas
de erro da biblioteca corrompida pertencem ao teste de preservação.

## Limites e próximos itens

1. **Exportações longas:** quantização/encoding de GIF ainda ocorrem na thread
   principal. Próximo incremento: worker, cancelamento e limites de memória
   com teste de interrupção e retomada do editor.
2. **Qualidade dos assets:** esta revisão melhora seleção do nível e iluminação,
   mas não reconstrói motores, materiais procedurais, aeroportos ou os `.blend`.
   A aparência do motor no preset ainda é simplificada. O nível heroi por si só
   não certifica fidelidade geométrica; isso exige a revisão própria dos modelos.
3. **Animação:** rotas continuam sendo editadas numericamente; faltam alças no
   viewport e editor de curvas. Não houve aprovação quadro a quadro do clipe
   completo de decolagem ou reboque nesta execução.
4. **Persistência:** continua local ao navegador/origem. Cópias de recuperação
   ocupam a biblioteca e podem ser removidas pela interface. JSON é necessário
   para backup fora do navegador. Sincronização entre abas ou máquinas não foi
   implementada; evitar edição simultânea da mesma sessão em múltiplas abas.
5. **Compatibilidade:** funcionamento observado em Chromium desktop com viewport
   estreito. Safari, Firefox, gestos em dispositivo físico e acessibilidade com
   leitor de tela não foram certificados. Ao mudar drasticamente a proporção,
   usar “frame all” para reenquadrar; a câmera autoral não é reescrita pelo resize.

As alterações desta revisão estão locais, sem commit, push ou publicação.

## Complemento: loadings cinematográficos

A revisão de 5 de setembro das dez combinações está em [loading/REVISAO-VISUAL.md](loading/REVISAO-VISUAL.md). Inclui comparação de imagens, correções nas fachadas, copas e relevo de GRU e preenchimento da grama de SDSC, além da regeneração dos três MP4s usados pelo componente. Essa inspeção por amostragem amplia a revisão anterior; não representa aprovação quadro a quadro de todos os filmes nem aprovação de fotorrealismo.

## Frota e bases — 2026-09-05, câmera externa

A série passa a 122 combinações nas 3 bases e 11 aeronaves, com trajetórias aéreas compartilhadas por avião e câmera, trem recolhido, aproximações e revelações do entorno. Santiago agora tem contexto e relevo Copernicus próprio. O cockpit interpretado foi retirado por decisão do usuário; links antigos resolvem para passagem externa. As últimas verificações e renderizações usam Chrome headless, sem trazer janelas à frente. Evidências, limites e reproduções em `loading/BASES-E-VOOS.md`; estado local, não publicado.

## Realismo — 2026-09-05

Renderer e sete vídeos revistos em segundo plano: céu linear HDR, materiais procedurais em escala mundial, câmera contínua, inclinação coordenada em voo, fans independentes e correção das tampas nas entradas dos motores do 777. Validação e limitações em [loading/REALISMO.md](loading/REALISMO.md). Estado local; sem publicação. O entorno ainda apresenta simplificação visível e não foi classificado como fotorrealista.
