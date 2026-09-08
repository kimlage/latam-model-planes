# Série cinematográfica de loadings LATAM

Abra **http://127.0.0.1:8137/estudio/loading/** com `python3 estudio/serve.py` rodando na raiz. A versão atual mostra aeroportos completos, aeronaves e ação/câmera em movimento. O estudo anterior sem cenário foi preservado em `isolado.html` e `README-isolado.md`.

## Combinações disponíveis

| Aeroporto | Situações | Aeronaves |
|---|---|---|
| GRU / SBGR, São Carlos / SDSC, Santiago / SCL | Pátio, sobrevoo e passagem próxima | Todas as 11 |
| GRU / SBGR | Decolagem 10L | Todas as 11 |
| São Carlos / SDSC | Interior e manutenção | Todas as 11 |
| São Carlos / SDSC | Entrada no hangar com trator e barra | 787-9 |

São **122 combinações** nas três bases existentes no projeto. A frota inclui A319, A320ceo, A320neo, A321ceo, A321neo, 767-300ER, 777-300ER, 787-8, 787-9, 767-300F e 767-300BCF. A troca de base preserva as escolhas compatíveis; a URL reabre a combinação exata. Reboque continua restrito ao 787-9, pois barra e trem têm encaixe próprio. Não foram inventadas operações de manutenção nos hangares de GRU ou SCL.

Os novos voos têm 24 segundos. Uma trajetória amostrada movimenta aeronave e câmera juntas, com leve curva e trem recolhido. **Passagem próxima** se aproxima do nariz, acompanha a lateral e se afasta para revelar a base. Todo o movimento é externo: o cockpit interpretado foi retirado do fluxo a pedido do usuário. Links antigos com `situation=cockpit` agora abrem `aproximacao`.

**Ver como loading** amplia a cena, mantendo seu quadro 16:9 inteiro, inclusive no celular. **Editar câmeras e exportar** abre a combinação exata no estúdio, mantendo a recuperação da cena anterior. A animação e seus planos continuam editáveis. Não há progresso fictício: a barra representa espera indeterminada até a aplicação informar um valor real.

## Imagem e repetição

Os planos avançam no tempo. Uma breve passagem pelo preto esconde o reposicionamento no reinício; não há aeronaves andando de ré para fechar o loop. A transição de 0,55 s está no player 3D e é incorporada às exportações de GIF, sequência PNG e MP4 quando `producao.transicao` é `fade-black`. O PNG avulso continua sendo um quadro limpo para poster. O embed genérico do estúdio ainda não inclui essa transição; use `latam-cinema` para incorporar a experiência de loading.

A geometria dos aeroportos e as réplicas da frota vêm dos modelos existentes. Os posicionamentos do pátio foram deslocados das pontes/equipamentos fixos para liberar as aeronaves. A trajetória de decolagem adapta o enquadramento à dimensão do modelo, mas **não é uma simulação de desempenho certificada**. Edificações, vegetação, veículos e materiais ainda são simplificados: esta é uma série 3D funcional, não um acabamento fotorrealista aprovado.

## Incorporar à aplicação

No mesmo servidor que fornece o estúdio e `export/`:

```html
<script type="module" src="/estudio/loading/latam-cinema.js"></script>
<latam-cinema id="loading"
  airport="scl" aircraft="B789" situation="aproximacao">
</latam-cinema>
```

```js
const loading = document.querySelector('#loading');
loading.configure({aeroporto:'sbgr', aeronave:'A320neo', situacao:'patio'});
// Valores fornecidos pelo carregamento real da aplicação:
loading.setAttribute('message', 'Preparando sua viagem');
loading.setAttribute('progress', '42'); // omita quando não houver progresso mensurável
loading.setAttribute('state', 'ready');
// Quando a tela da aplicação estiver pronta:
loading.remove();
```

`paused` pausa, `restart()` reinicia e `configure()` troca a combinação de forma agrupada. `state="error"` permite mostrar a mensagem de erro do carregamento da aplicação. O componente emite `scene-ready` quando o cenário/vídeo está disponível; esse evento **não** indica que os dados da aplicação terminaram de carregar.

Sete combinações usam MP4: os quatro exemplos anteriores e GRU/777/passagem próxima, SCL/787/passagem próxima e SDSC/A320neo/sobrevoo. Os três novos vídeos têm 24 s, 1280 × 720 e 20 fps, com supersampling 2×. As outras 115 combinações usam a mesma cena editável no runtime 3D, em iframe isolado descartado na troca. Elas precisam dos módulos do estúdio, Three.js e dos GLBs de `export/`; copiar somente esta pasta não basta. Para entregar apenas vídeos, exporte as combinações escolhidas e registre-as em `renderPronto()`.

Movimento reduzido usa poster nos vídeos e quadro estático nas cenas 3D. Vídeos e cenas pausam quando a página está oculta, quando o componente sai da tela ou quando a aplicação termina. O player preserva os planos completos; layouts verticais com outra direção de câmera exigem uma nova composição, em vez de cortar o avião.

## Arquivos e validação

- `catalogo.js`: combinações permitidas, rótulos, URLs e renderizações prontas.
- `cenas-cinema.js`: documentos com aeroporto, aeronave, ação e câmera.
- `latam-cinema.js`: componente reutilizável, vídeo/3D, status e ciclo de vida.
- `runtime.html`: renderer e timeline compartilhados com o estúdio.
- `../js/transicao.js`: repetição editorial compartilhada com os exportadores.
- `voos-cinema.js`: trajetória compartilhada, dimensões da frota e planos aéreos.
- `../tests/fleet-cinema.js`, `fleet-geometry.js`, `fleet-final-visual.js`: matriz, chão, trem, câmeras e quadros.
- `../tests/render-fleet.js`: reprodução dos três novos vídeos.
- `media/cinema/gru-a320-patio.mp4`: novo render, 960 × 540, 25 fps, 300 quadros / 12 s, supersampling 2× e transição incorporada.

Evidências locais em `../../output/playwright/cinema-*`. Créditos em [media/cinema/ATRIBUICAO.txt](media/cinema/ATRIBUICAO.txt): modelos CC BY 4.0 — Kim Lage; geometrias derivadas do OpenStreetMap sob ODbL 1.0. Ver também `../../export/ambientes/README.md` e `../../NOTICE.md`. Nenhuma publicação ou integração a uma aplicação externa foi feita.

A [revisão visual](REVISAO-VISUAL.md) registra os defeitos encontrados e os quadros usados na conferência. Os três MP4s foram regenerados com as correções de fachadas, vegetação, relevo e solo. Todos incluem a transição editorial; o relevo de GRU acrescenta os avisos Copernicus aos créditos.

## Interior do Hangar 9

A situação `manutencao` está disponível em São Carlos para todas as 11 aeronaves. O [registro dos interiores](INTERIORES.md) descreve a modelagem, os dois planos, as referências e os próximos ganhos de realismo.

## Expansão da frota e bases

[BASES-E-VOOS.md](BASES-E-VOOS.md) registra a expansão, a direção de câmera exclusivamente externa, o relevo de Santiago e a validação desta etapa. Resultados estruturados em `../../output/playwright/fleet-results.json`. O estado permanece local, sem publicação.

## Revisão de realismo

A [revisão de realismo](REALISMO.md) substitui os sete vídeos ativos por renders novos em 720p com supersampling 2×, atualiza os cartazes e registra iluminação HDR linear, materiais de superfície, continuidade de câmera e correções dos motores. As limitações de geometria e as evidências de validação estão separadas dos ganhos implementados.

O logo sobreposto usa `media/latam-logo-light.svg`, derivado do vetor local `latam_logo_indigo.svg`: mesma geometria e símbolo coral, com letras brancas para contraste sobre o vídeo. Substitui o marcador provisório em texto.
