# Pacote completo de animações — 8 de setembro de 2026

[Baixar ZIP](https://github.com/kimlage/latam-model-planes/releases/download/scene-studio-2026-09-08/latam-animacoes-completo-2026-09-08.zip) · [SHA-256](https://github.com/kimlage/latam-model-planes/releases/download/scene-studio-2026-09-08/latam-animacoes-completo-2026-09-08.zip.sha256)

O pacote distribui as **122 combinações suportadas em MP4 e JSON editável**. Inclui o Scene Studio, bibliotecas web locais, modelos GLB das 11 aeronaves nos níveis disponíveis, geometrias dos três aeroportos e as atribuições. Os masters Blender e as fotografias de referência não fazem parte deste pacote de reprodução.

## Cobertura

| Base | Pátio | Sobrevoo | Passagem próxima | Decolagem | Manutenção | Reboque | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| GRU / SBGR | 11 | 11 | 11 | 11 | — | — | 44 |
| São Carlos / SDSC | 11 | 11 | 11 | — | 11 | 1 | 45 |
| Santiago / SCL | 11 | 11 | 11 | — | — | — | 33 |
| **Total** | **33** | **33** | **33** | **11** | **11** | **1** | **122** |

Aeronaves: A319, A320ceo, A320neo, A321ceo, A321neo, 767-300ER, 767-300F, 767-300BCF, 777-300ER, 787-8 e 787-9. O reboque usa somente o 787-9; não há encaixe de trator/barra validado para o restante da frota.

## Como usar

1. Extraia o ZIP inteiro.
2. Abra `index.html` para escolher e assistir aos MP4s, sem instalar o Studio.
3. Para editar cenas, execute `python3 estudio/serve.py` na pasta extraída e abra `http://127.0.0.1:8137/estudio/loading/`.
4. Escolha aeroporto, aeronave e situação; clique em **Editar câmeras e exportar**. Também é possível importar um arquivo de `cenas/` pelo editor.

Reprodução dos MP4s não exige Python ou ffmpeg. O editor exige navegador com WebGL2 e servidor local Python 3; exportação de novos MP4s exige ffmpeg no PATH. Three.js, Draco e gifenc estão incluídos para que a interface não dependa de CDNs. Se a porta 8137 estiver ocupada, use `python3 estudio/serve.py --port 8138` e ajuste a URL.

## Organização

- `animacoes/<base>/<aeronave>/<situacao>.mp4`: 122 vídeos H.264, 1280 × 720, sem áudio.
- `cenas/<base>/<aeronave>/<situacao>.json`: documentos com modelos, ambiente, câmeras, planos e animações.
- `estudio/`: interface, runtime e exportação.
- `export/`: modelos GLB, manifestos e geometrias dos aeroportos.
- `catalogo.json`: relação entre as configurações, os vídeos e os documentos.
- `manifest-sha256.json`: tamanho e checksum de cada arquivo distribuído.
- `LICENSE`, `NOTICE.md` e atribuições: licenças de código, modelos e geometrias.

Os MP4s usam o fps e a duração de cada cena e renderização com supersampling 2×. Os sete destaques são os mesmos arquivos revisados na biblioteca web. Os vídeos contêm a cena cinematográfica: logo, mensagens e indicador de progresso são adicionados pelo componente web, para que possam ser personalizados pela aplicação.

## Qualidade e limites

Os GIFs do README são capturas da interface real, reduzidas a oito quadros por segundo para documentação; não representam o fps dos vídeos. Terreno, vegetação, fachadas e parte dos detalhes de manutenção ainda são simplificados. As trajetórias são cinematográficas, não procedimentos de voo validados. Não há cenas de cockpit.

Ver [registro de realismo](../estudio/loading/REALISMO.md) e [licenças](../NOTICE.md). LATAM, Airbus e Boeing são marcas de seus respectivos titulares; este projeto independente não tem afiliação ou endosso dessas empresas.
