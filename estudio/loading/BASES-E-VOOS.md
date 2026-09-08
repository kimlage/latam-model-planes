# Frota completa, bases e voos — 2026-09-05

## Entrega local

122 combinações: 11 aeronaves × 3 bases × 3 situações universais (pátio, sobrevoo, passagem próxima), mais 11 decolagens em GRU, 11 cenas internas de manutenção em São Carlos e um reboque calibrado para o 787-9. As bases são as três já modeladas no repositório: Guarulhos, São Carlos e Santiago. Isso não significa cobertura de todas as bases reais da companhia.

Os novos voos duram 24 segundos e usam a mesma trajetória para posição e orientação da aeronave e para as câmeras. O trem fica recolhido durante todo o voo. A passagem próxima usa o nível de detalhe `alta`, aproxima-se pelo nariz, acompanha a lateral e abre o quadro para revelar o aeroporto. O ciclo termina e reinicia com passagem pelo preto; não reproduz movimento ao contrário.

## Decisão de direção visual

O cockpit interpretado foi retirado do fluxo a pedido do usuário: faltava fidelidade específica a cada aeronave. Nenhuma situação disponível entra na cabine. Links antigos com `situation=cockpit` resolvem para `aproximacao`. O módulo experimental `../js/cockpit.js` e os vídeos anteriores ficaram sem referências no runtime ou no catálogo; não são parte da entrega visual.

As verificações seguintes usam uma sessão Chrome headless, sem janelas ou alterações de foco. Não chamar `bringToFront()` nem abrir painéis do aplicativo durante esta tarefa.

## Santiago

- Exportação das pistas e pátios com precisão de posição de 22 bits.
- Terminais, base LATAM, equipamentos e entorno nas coordenadas da placa original.
- Relevo Copernicus local em três malhas de 120, 360 e 2160 m, com máscaras internas e ajuste sob o aeródromo, incluindo a cordilheira.
- Relevo separado dos assets OSM e com seus próprios avisos no manifesto e nas exportações.
- Masters `.blend` originais preservados. Scripts reproduzíveis em `../tools/exportar_ambientes.py`, `exportar_pavimentos.py` (ambos aceitam `-- --scl-only`) e `exportar_relevo_scl.py`.

## Correções visuais

Os closes revelaram auto-sombreamento em faixas sobre a fuselagem. O diagnóstico comparou o mesmo quadro com e sem sombra; a correção ajusta bias e normal bias somente nas situações aéreas. As sombras de contato no solo e no hangar conservam sua configuração. Modelos detalhados melhoram bordas e detalhes próximos da câmera.

## Limites

Os cockpits não estão disponíveis. Edificações e materiais ainda são simplificados; há pouca textura urbana em Santiago e os entornos precisam de mais detalhe próximo. As trajetórias são cinematográficas, não procedimentos ou simulações de desempenho de cada tipo. Reboque continua restrito ao 787-9; manutenção interna continua restrita a São Carlos. Não há publicação externa.

## Evidências

A validação estrutural cobre a matriz inteira. A geometria de pátio e voo é verificada nas 33 combinações base/aeronave; o interior do hangar, nas 11 aeronaves. A inspeção visual usa quadros amostrados nas bases, closes das 11 aeronaves e quadros extraídos dos vídeos finais. Esses testes não provam ausência de interseção em toda cena arbitrariamente editada pelo usuário.

Resultados: `../../output/playwright/fleet-results.json`. Capturas: `../../output/playwright/fleet-*`. Scripts: `../tests/fleet-cinema.js`, `fleet-geometry.js`, `fleet-final-visual.js`, `fleet-regression.js`, `interior-browser.js` e `render-fleet.js`.

Validação final: 122/122 configurações, 33/33 combinações de geometria, 11/11 aeronaves no hangar, 36/36 regressões do editor/produções e 5/5 verificações do player. Os três vídeos externos têm 1280 × 720, 20 fps, 480 quadros e 24 s: GRU/777/passagem próxima (11,55 MB), SCL/787/passagem próxima (8,77 MB), SDSC/A320neo/sobrevoo (4,97 MB). As folhas de contato extraídas dos três MP4s foram inspecionadas, além dos quadros de viewport. `fleet-video-results.json` registra dimensões, duração, quadros e metadados.

### Revisão posterior de realismo

Os sete MP4s ativos foram regenerados; os três voos agora têm 600 quadros a 25 fps. Ver [REALISMO.md](REALISMO.md) para iluminação, materiais, motores, movimento, evidências e limitações. Os números anteriores de tamanho/fps descrevem a entrega anterior.
