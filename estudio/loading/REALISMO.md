# Realismo — revisão local de 5 de setembro de 2026

A revisão melhora o renderer compartilhado e regenera os sete MP4s ativos. O catálogo continua com 122 combinações; 115 usam o runtime 3D, sete têm vídeo pronto. Não houve publicação externa. Cockpit continua desativado. Toda a revisão de navegador desta etapa ocorreu em Chrome headless, sem ativar janelas.

## Alterações observadas

- Céu em textura HDR linear: elimina a dupla conversão de cor que escurecia o ambiente; disco solar menor e névoa ajustada nos voos.
- Concreto, asfalto, terreno e fachadas recebem variação de cor e rugosidade em escala mundial. Micro-relevo do piso e detalhes de fachada filtrados por distância. Sem duplicar juntas existentes nem modificar a pintura das aeronaves.
- Passagens próximas usam curva contínua de câmera. Atitude da aeronave acompanha a curva; a inclinação deriva da velocidade e mudança de direção. Não há paradas artificiais nos antigos pontos intermediários nem saltos de Euler.
- Dois fans independentes em todas as 11 aeronaves. Nos modelos Airbus, a malha que reunia os dois fans foi separada por motor antes de animar.
- No 777, faces do modelo original fechavam a entrada dos motores. A instância do runtime remove essas tampas e mantém o lábio externo. 777 e 787 recebem rotores com pás curvas e fundo escuro; os arquivos Blender e GLB originais ficam preservados.

O GE90-115B usa 22 pás, conforme [GE Aerospace](https://www.geaerospace.com/news/press-releases/commercial-engines/ge90-fan-blade-receives-best-show-honors-composites-competition). O Trent 1000 usa 20 pás e diâmetro de 112 polegadas, conforme [Rolls-Royce](https://www.rolls-royce.com/~/media/Files/R/Rolls-Royce/documents/civil-aerospace-downloads/280717-Trent-1000-infographic.pdf). Os perfis das pás são interpretações visuais; não são CAD de engenharia. A rotação visual de 24 rad/s não reproduz N1 operacional. Os fans animam em sobrevoo e aproximação; a sequência antiga de decolagem ainda precisa dessa extensão.

## Exportação e evidências

Sete vídeos em 1280 × 720, com renderização em resolução dupla antes da redução. Seis usam 25 fps; a decolagem preserva 20 fps e 7,95 s. Pátio: 12 s; reboque: 16 s; interior: 14 s; três voos: 24 s cada.

`tests/render-realismo.js` exporta blocos de até 150 quadros via `intervaloQuadros: [inicio, fimExclusivo]`. O tempo é absoluto na sequência completa, inclusive nas transições. Isso respeita o limite de memória de 512 MB por sequência PNG. Os MP4s parciais em `output/realismo-parts/` foram concatenados pelo ffmpeg com `-c copy -movflags +faststart`; os cartazes foram extraídos dos vídeos novos. Os vídeos anteriores foram preservados em `output/realismo-before/`.

- `output/playwright/realismo-results.json`: cinco cenários com continuidade de movimento, materiais e shaders; 33 combinações de geometria (11 aeronaves × três bases); 36 verificações de editor/produção/exportação; cinco verificações de interface; teste do intervalo de exportação.
- `output/playwright/realismo-video-results.json`: duração, fps, contagem de quadros e bytes dos sete MP4s concatenados.
- `output/playwright/final-*.png`: folhas de contato extraídas dos vídeos finais a cada três segundos. Células pretas excedentes são espaços vazios da montagem, não quadros pretos do vídeo.
- `output/playwright/realismo-*.png`: quadros do runtime, incluindo closes dos motores e interiores.
- `output/playwright/fleet-ui-desktop.png` e `fleet-ui-mobile.png`: reprodução dos vídeos novos na interface.

## Limites visuais restantes

O resultado ainda não é fotorrealista. A revisão dos quadros finais mostra terreno facetado, vegetação simplificada, edifícios pouco detalhados, fachadas repetitivas e superfícies de aeronaves excessivamente limpas. A variação procedural do solo não substitui ortofotos ou levantamento do local. O interior tem estrutura, iluminação e equipamentos, mas ainda precisa de maior densidade de detalhes de manutenção.

A trajetória de voo é cinematográfica, não um procedimento aeronáutico validado. A câmera faz closes que cortam partes da aeronave nas bordas por enquadramento; não entra na cabine. Não há desfoque de movimento por obturador físico. Esta revisão amostra os sete vídeos e cenas representativas: não certifica ausência de todo possível clipping em cada quadro das 122 combinações.

Os próximos ganhos exigem principalmente malhas e texturas de entorno melhores, detalhes próprios de cada aeroporto e acabamento das aeronaves, além de iluminação indireta e reflexos mais ricos.

## Correção após relato de asa cinza e telhados cintilando

O usuário encontrou falhas na reprodução web que a primeira revisão não identificou adequadamente. Na passagem de Santiago, a câmera alcançava near 0,44 m e far 592,8 km. O plano próximo agora acompanha 10% da distância ao alvo (antes 1%), preservando o limite de 8 m. A alternativa logarítmica foi rejeitada após causar ruído visual no hangar. Os detalhes procedurais também são filtrados conforme sua dimensão na tela.

O teste com e sem recepção de sombra isolou a asa azul-acinzentada: era principalmente auto-sombreamento indevido. O viés de sombra foi ajustado apenas nos voos, preservando o ajuste de contato em solo. A textura clara e as linhas de painel foram mantidas; o acabamento CinzaAsa usa rugosidade 0,35, conforme o kit local de materiais.

Os vídeos e cartazes são regenerados pelo mesmo pipeline. As URLs recebem uma revisão de mídia para evitar reaproveitamento do vídeo anterior após recarregar a página. Evidências desta correção usam o prefixo `renderfix-` em `output/playwright/`; a comparação de profundidade é feita por `tests/roof-depth.js` com deslocamentos subpixel da câmera.

No teste final de 30 amostras quase estacionárias sobre o telhado de Santiago, eventos de mudança de cor acima do limiar caíram de 10.943 para 239 (97,8% neste recorte controlado). Isso mede a cintilação nesse teste, não uma garantia global de ausência de aliasing. Os sete MP4s finais foram concatenados sem nova compressão e decodificados integralmente; a asa clara foi conferida em quadros do vídeo, além do runtime.
