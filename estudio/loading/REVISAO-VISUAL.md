# Revisão visual — 5 de setembro de 2026

A revisão encontrou defeitos reais e corrigiu os exports e a iluminação. Não constitui aprovação de fotorrealismo nem prova de ausência de interseção em todos os triângulos.

## Correções verificadas em imagem

- GRU: faixas de auto-sombreamento nas fachadas. A sombra dinâmica agora acompanha a aeronave protagonista e usa menor afastamento; fachadas do contexto deixam de receber a projeção instável, enquanto pisos continuam recebendo sombras de contato.
- GRU: copas fragmentadas pela redução de malha. O export preserva as copas completas. O relevo sob a vegetação foi incluído como asset separado, derivado do campo de alturas local, com créditos Copernicus.
- SDSC: preenchimento de grama com células grosseiras, produzindo recortes triangulares no enquadramento. O export agora usa os contornos OSM, recortados contra a triangulação do terreno, com 2,5 cm de separação. Os masters `.blend` não foram alterados.
- Exportação: três MP4s e respectivos posters regenerados em 960 × 540 com supersampling 2×. A passagem pelo preto está incorporada aos vídeos; o player não aplica uma segunda passagem.

## Evidência local

Em `../../output/playwright/qa-cinema/`:

- `after-*-0.png` a `after-*-4.png`: 50 quadros das dez combinações, incluindo início, quartos e fim da ação. Verificados cenário, enquadramento, asas, cauda, motores, rodas, proximidade de edifícios e solo.
- `movie-*.png`: quadros extraídos dos três MP4s finais, a cada segundo. Células pretas excedentes das folhas de contato são preenchimento da folha, não quadros do filme.
- `comparacao-solo.png`: antes/depois do solo de São Carlos.
- `player-reviewed.png`: player com vídeo em reprodução, conferido no navegador.
- `results.json`: testes de enquadramento, interface e produção.

Os três vídeos têm 400 quadros / 16 s (reboque), 159 / 7,95 s (decolagem) e 300 / 12 s (pátio A320). A transição inicial e final também foi medida nos arquivos codificados. Créditos conferidos no metadata dos MP4s e no arquivo de atribuição.

Não observei novos atravessamentos visíveis entre a aeronave e os edifícios nos quadros revisados. A aparência de materiais, vegetação e arquitetura permanece simplificada; a revisão não equivale a uma inspeção manual de cada um dos 859 quadros dos vídeos, nem certifica outros aeroportos ou câmeras editadas posteriormente.

Validação final: 10/10 combinações com câmera móvel e aeronave no enquadramento; 14/14 testes de produções e 22/22 testes do editor/exportação passaram. Também foram conferidos os controles em viewport estreito e o modo de movimento reduzido. A validação numérica de documentos foi corrigida para permitir contagens de bytes acima de 10 MB sem relaxar os limites das coordenadas.
