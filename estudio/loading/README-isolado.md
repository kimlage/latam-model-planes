# Loading LATAM — conceito de aplicação

Abra http://127.0.0.1:8137/estudio/loading/ com `python3 estudio/serve.py` rodando na raiz. A prévia alterna tela inteira/painel, pausa movimento e simula progresso. A simulação está identificada e pertence somente à demonstração.

Aeronave: 777-300ER da frota, LOD herói, trem recolhido. Câmera fixa em três quartos, oscilação periódica discreta de posição e atitude. Loop de 4 s, 25 fps, 100 quadros, 800 × 450, supersampling 2×. MP4 H.264 sem áudio: 77.523 bytes. A aplicação usa somente vídeo + HTML/CSS; não carrega Three.js ou os modelos 3D. Poster estático aparece antes do vídeo, com movimento reduzido ou se a reprodução falhar. Vídeo pausa fora da tela, em outra aba e ao desconectar o componente.

## Incorporar

Copie esta pasta inteira para a aplicação, preservando `media/` ao lado do módulo:

```html
<script type="module" src="/loading/latam-loading.js"></script>
<latam-loading id="espera"></latam-loading>
```

```js
const espera = document.querySelector('#espera');
// Somente se o carregamento real fornecer progresso mensurável:
espera.setAttribute('progress', '42');
espera.setAttribute('message', 'Preparando sua viagem');
// Quando os dados reais estiverem disponíveis:
espera.setAttribute('state', 'ready');
// Exiba a aplicação e retire o loading quando ela estiver pronta:
espera.remove();
```

Sem `progress`, a barra é indeterminada. O componente não inventa prazos, porcentagens ou conclusão automática. Use `size="compact"` para painel e o atributo `paused` para pausar animações. Para falha, `state="error"` mostra uma mensagem e botão que emite `retry`; a aplicação deve tratar o evento e repetir sua operação. Remova `progress`/`message` e retorne `state="loading"` ao reiniciar. `prefers-reduced-motion` evita iniciar o download do vídeo e mantém o poster. O host pode controlar tamanho, bordas e `--loading-accent`. O fundo é coordenado com o MP4 opaco; trocar a cor exige recompor o vídeo.

O componente usa Shadow DOM, `role="status"`, barra com valores reais e texto por `textContent`. A demonstração não está conectada ao backend de uma aplicação LATAM. O lettering é uma composição tipográfica do conceito, não um arquivo oficial de logotipo.

## Editar e reproduzir o render

No estúdio, abra a produção **LATAM · loading da aplicação** (`../?producao=latam-loading`). Posição, câmera e loop estão em `../js/producoes.js`. Exporte a sequência PNG em 800 × 450, 2×, 25 fps; a sequência conserva transparência. Para gerar o vídeo distribuído, use `../tools/empacotar_loading.py CAMINHO_DO_ZIP`. O vídeo é composto sobre índigo, com atribuição nos metadados. Não duplica o último quadro do loop.

Licenças e créditos: [media/ATRIBUICAO.txt](media/ATRIBUICAO.txt). Réplicas 3D CC BY 4.0 — Kim Lage. Marcas pertencem aos titulares. Conceito local para revisão; sem publicação ou integração a um produto externo.

## Verificação

`../tests/loading-browser.js` executa a verificação pelo Playwright CLI em contextos isolados, incluindo o mapa de imports exclusivo dos testes. Foram aprovadas 14 verificações no Chromium; Safari e Firefox não foram testados nesta rodada. `../tests/loading.js` verifica fechamento de pose/velocidade/câmera, trem recolhido, progresso, conclusão, erro/retry, texto seguro e pausa ao remover. Revisar também a reprodução real, poster sem vídeo, movimento reduzido, desktop e celular. Os arquivos de evidência ficam em `../../output/playwright/loading-*` (ignorados pelo Git).
