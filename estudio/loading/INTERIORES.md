# Interiores de hangar — primeira implementação

O primeiro interior detalhado é o Hangar 9 de São Carlos, nas coordenadas da sua casca já existente. O desenho usa como referência visual a foto local `scenario_sdsc/refs/mro_centro_tecnologico_2010.jpg`: treliças vermelhas, luminárias individuais e plataformas de manutenção. A foto é de outro momento do MRO, não um levantamento do Hangar 9; disposição, perfis, alturas dos equipamentos e iluminação são interpretados.

## Implementado

- Treliças abertas, colunas ligadas à cobertura, terças seguindo a inclinação do telhado, bases e travessas de parede.
- Vinte luminárias suspensas, doze fachos direcionados ao piso e duas sombras centrais. Quatro luzes de preenchimento aproximam a luz refletida; não há simulação de iluminação global.
- Juntas, faixas de circulação, identificação da baia, portas de apoio e sinalização.
- Bancadas, armários, carrinhos com gavetas e rodízios, plataformas móveis com escadas e apoios, extintores e pontos de serviço nas laterais.
- Corredor central livre para as três aeronaves. O contato visual dos pneus utiliza as sombras das luminárias e uma aproximação de oclusão calculada a partir da geometria das rodas.
- Situação **Interior e manutenção**: 14 segundos, plano geral de 8 s e aproximação do motor de 6 s. A aproximação adapta sua distância ao comprimento da aeronave. A aeronave está estacionada; motores, ferramentas e plataformas não simulam uma intervenção em execução.
- 787 usa o modelo de alta resolução; 777 e A320 usam o nível herói. Os demais cenários conservam seus níveis de detalhe.

Fonte reproduzível: `../tools/modelar_interior.py`; asset independente: `../../export/ambientes/sdsc_hangar9_interior.glb`. O contexto retira as antigas barras maciças do teto e as luminárias em faixas. Nenhum master original `.blend` foi sobrescrito.

## Próximos ganhos de realismo

1. **Materiais próximos da câmera:** microtextura do concreto, desgaste localizado, marcas de rodas, rugosidade de pintura e junções da cobertura. O piso atual ainda parece novo e uniforme.
2. **Operação completa:** prolongar o reboque até a posição final, parada gradual, desconexão da barra e estacionamento do trator, antes de movimentar plataformas. O clipe existente ainda termina na entrada.
3. **Intervenção de manutenção:** movimentos independentes de plataformas, portas e técnicos precisam de trajetórias, poses e folgas próprias; não basta mover todo o equipamento como um bloco.
4. **Interior de outros hangares:** adaptar planta, vão, estruturas e câmeras à geometria e às referências de cada aeroporto. O interior de GRU ainda não foi modelado nesta etapa.
5. **Luz e render:** materiais/reflexos e oclusão mais completos, mantendo a versão MP4 leve para uso em aplicações. Este incremento não é uma aprovação de fotorrealismo.

## Revisão

`../tests/interior-browser.js` verifica as três aeronaves, folgas contra o corredor de equipamentos e a casca, contato das rodas com o piso e posição das câmeras. A câmera ampla enquadra toda a aeronave; o segundo plano é um detalhe intencional.

Evidências em `../../output/playwright/interior-*`: seis instantes por aeronave, incluindo os dois lados do corte aos 8 s, folhas de contato e quadros dos vídeos finais. A inspeção visual complementa as medições; não é uma prova de ausência de interseção em todas as combinações editadas pelo usuário.

Validação final desta etapa: 3/3 aeronaves, 4/4 verificações de integração e 36/36 verificações do editor e das produções passaram. Vídeo interno: 1280 × 720, 350 quadros, 14 s, cerca de 3,65 MB; reboque regenerado: 960 × 540, 400 quadros, 16 s. Os quadros extraídos dos dois arquivos foram inspecionados. Resultados em `../../output/playwright/interior-results.json`.
