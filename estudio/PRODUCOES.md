# Produções, câmeras e vídeo

O estúdio monta operações com ambientes completos de GRU e São Carlos,
trajetórias de aeronaves/equipamentos e uma montagem de câmeras. Os ambientes
usam os masters locais: não são reconstruções fotogramétricas nem um levantamento
atualizado dos aeroportos. Há arquitetura interpretada e vegetação simplificada.

## Abrir e dirigir

Inicie `python3 estudio/serve.py` na raiz do repositório e abra
[Scene Studio](http://127.0.0.1:8137/estudio/). Na aba **Scenes**, escolha:

| Produção | Duração / quadros | Conteúdo |
| --- | --- | --- |
| GRU · decolagem 10L | 7,95 s / 159 a 20 fps | 777 heroi, rotação e subida, câmera de acompanhamento, aeroporto e cidade |
| São Carlos · entrada no hangar 9 | 16 s / 400 a 25 fps | 787, trator, barra e direção do trem de nariz coordenados; aproximação e entrada parcial no hangar |
| GRU · apresentação do aeroporto | 24 s / 600 a 25 fps | Três planos: implantação, terminais e frota no pátio |
| São Carlos · visita ao MRO | 16 s / 400 a 25 fps | Três planos, da base à entrada do reboque |

As posições da frota estacionada são ilustrativas, usando a tabela de stands dos
masters; não representam uma alocação operacional real em uma data específica.

1. Reproduza com **▶**; clique na faixa de planos para ir a um corte.
2. Abra **Câmeras…** para alterar nome, início/fim, interpolação, FOV ou objeto seguido.
3. Use **Enquadrar início/fim**, ajuste a viewport e clique **◆ Gravar enquadramento**.
4. **Câmera livre** permite explorar. **▶** volta à montagem. A exploração não reescreve os planos.
5. **Save scene** guarda a edição neste navegador; JSON é o backup portátil.

Planos não podem se sobrepor. No instante de um corte vale o plano que começa.
Seguir um objeto usa deslocamentos nos eixos do mundo; posição e alvo acompanham
seu movimento. A avaliação é compartilhada por viewport, GIF, PNG, MP4 e embed.
As câmeras importadas preservam seus percursos; alterar um extremo distribui a
correção ao longo desse percurso. Cenas antigas sem planos continuam válidas.

## Exportar

**Export… → MP4** produz H.264 sem áudio, com taxa e duração da timeline.
Precisa de `ffmpeg` disponível no PATH do servidor. A conversão ocorre neste
computador: nenhuma API externa recebe as imagens. O MP4 inclui os créditos
no campo `comment`. O servidor está restrito a loopback e confere a origem dos
pedidos; não executa comandos fornecidos pelo cliente.

960 × 540 é o padrão do MP4. Há opções até 1920 px de largura e formatos
16:9, 4:3, quadrado e vertical. Reenquadre os planos para uma proporção diferente.
O pipeline mantém um ZIP de PNGs em memória, limitado a 512 MB. Se ultrapassar,
reduza resolução ou duração. **Cancelar** interrompe a captura/espera e restaura
o editor; uma codificação já recebida pelo servidor termina e limpa seus temporários.

**PNG seq** mantém transparência e inclui `ATRIBUICAO.txt` e `sequencia.json`.
**GIF**, **PNG**, **JSON** e **Embed** continuam disponíveis também com um servidor
estático comum. MP4 não está disponível no servidor genérico de Python.

## Fontes e reprodução

- `tools/exportar_ambientes.py`: lê `scenario_sbgr/sbgr_field.blend` e
  `scenario_sdsc/sdsc_hangar_tow.blend`, sem salvar os masters. Converte entorno,
  arquitetura e equipamento; preserva a abertura do hangar, revestimentos
  selecionados e aproxima as luminárias de área com luzes pontuais glTF.
- `tools/exportar_pavimentos.py`: reconstrói as superfícies a 22 bits de posição
  Draco. A compressão anterior, a 14 bits, era insuficiente para superfícies
  separadas por centímetros em um campo de quilômetros. Em São Carlos, separa
  também a grama do concreto por 2,5 cm, corrigindo a sobreposição do master.
- `producoes/reboque-trajetoria.json`: 400 poses do master para aeronave, trator,
  barra, direção e câmera. A versão web reaproveita o modelo B789 da frota.
- `export/ambientes/manifest.json`: arquivos, dimensões, triângulos, fontes e licença.

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P estudio/tools/exportar_ambientes.py
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P estudio/tools/exportar_pavimentos.py
```

A geometria aeroportuária continua ODbL, e os modelos de aeronaves CC BY 4.0.
Os heightfields Copernicus não foram incluídos. Parte dos materiais do entorno
usa cor PBR representativa; os cenários não equivalem ao render Cycles dos masters.
O trator ainda tem geometria simplificada, e a direção do trem usa um pivô medido
na malha. Não há simulação de tráfego aeroportuário, giro das rodas ou retração
mecânica completa do trem; o canal existente de trem recolhido controla visibilidade.

## Validação

No console do estúdio:

```js
await (await import('./tests/regression.js')).run();
await (await import('./tests/producoes.js')).run();
```

Backend: `python3 estudio/tests/test_video.py`. A revisão visual deve usar os
vídeos completos e amostras nos cortes, incluindo chão, portas, asas e sombras.
As capturas e MP4s desta execução ficam em `output/playwright/`, ignorado pelo Git.

## Série de loadings cinematográficos

A [biblioteca](loading/) permite selecionar aeroporto, aeronave e situação em dez combinações de GRU/São Carlos, 777/787/A320 e decolagem/pátio/reboque. As cenas têm contexto completo e câmera móvel. **Editar câmeras e exportar** transfere a combinação ao estúdio. A passagem pelo preto é incorporada ao GIF, sequência e MP4 da série. Veja [integração, matriz disponível e limites de acabamento](loading/README.md). O estudo `latam-loading` anterior, sem cenário, permanece identificado como estudo isolado.
