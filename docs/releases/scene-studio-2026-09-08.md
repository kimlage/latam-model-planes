Biblioteca cinematográfica para revisar, reproduzir e editar animações de aeronaves LATAM.

- 122 MP4s em 1280 × 720: 11 aeronaves, GRU, São Carlos e Santiago, nas situações suportadas pelo catálogo.
- 122 documentos JSON com câmeras, planos, animações e configuração de cena.
- Scene Studio e modelos GLB, com dependências web locais e índice HTML para assistir aos vídeos.
- README atualizado com sete vídeos em destaque e dois GIFs da interface em funcionamento.

Baixe o ZIP e extraia a pasta inteira. Abra `index.html` para assistir aos vídeos. Para editar, execute `python3 estudio/serve.py` e abra `http://127.0.0.1:8137/estudio/loading/`. Exportar novos MP4s exige ffmpeg; reproduzir os vídeos prontos não exige instalação.

O arquivo `.sha256` permite verificar o download; o ZIP também contém checksums individuais. Código sob MIT; modelos/renders sob CC BY 4.0; geometrias derivadas de OpenStreetMap mantêm suas atribuições e termos ODbL. Consulte NOTICE.md no pacote.

Esta versão ainda tem simplificações de terreno, vegetação e edifícios. As trajetórias são cinematográficas, não procedimentos aeronáuticos validados. Reboque disponível somente para o 787-9 em São Carlos; cockpit não incluído.
