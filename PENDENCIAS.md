# Pendências — lista viva do projeto

Ordenada por impacto no realismo. Regra de trabalho: **nada de micro-correções
isoladas** — cada rodada ataca o item mais alto que estiver destravado, e os
itens micro só entram anexados a uma rodada maior que já re-renderize o que
eles tocam.

## Em andamento

1. **GRU (SBGR) fase 1 — pesquisa e dados.** Terceira base: maior hub da LATAM
   e casa da manutenção do 777-300ER (o único tipo sem presença em cenário).

## Fechado em 2026-08-26 — rodada da verdade da tinta

As duas metades resolvidas com UMA aeronave repintada, não cinco:
- **As 4 cunhas suspeitas eram paralaxe de flanco**, não tinta: a retificação
  de 08-22 era controlada na deriva (y=0) mas a pele vive em |y|~2, e o
  deslocamento y·v aparece inteiro na fronteira. Com v medido no estabilizador
  de cada quadro e dois quadros por aeronave: A320ceo −0,03, A321neo
  +0,25/+0,18 (flancos opostos), 767-300ER +0,03/+0,15 — exoneradas. A320neo:
  sem veredito no quadro PT-TMN (1024 px); a frota atual (PR-XBP) veste a
  fronteira +0,95 m atrás — variante de era, registrada, não aplicada.
- **A "contradição" do A319 era o mesmo artefato**: porta 4 está no ACAP
  (−0,10±0,19 m corrigido). O que estava errado era a CORREÇÃO de 08-22 da
  cunha, que carregava a paralaxe: fronteira movida +0,76 m para trás
  (cruza o topo da porta 4 a 58%/57% em dois airframes), traseira restaurada
  à linha do BF da deriva. Única repintura da rodada.
- **O casco "branco-puro" era diagnóstico velho**: os 76% em 1.0 são texels
  mortos (fac=0); as onze bases de shader já vestem #E6E7EA e os renders
  seguram o branco em 0,69–0,72 sem clipe. Fechado no QA-BACKLOG com o censo;
  a única constante defasada (PALETA) corrigida; os dois brancos-sentinela
  (#F2F3F5 marcas, #F7F9FA arte) documentados como deliberados.

## Próximas, em ordem de impacto

3. **Re-sync SCL + SDSC depois da rodada da tinta.** Os clipes da capa ainda
   mostram A319/777 com a cunha antiga (corrigida em 29664d9, depois dos
   clipes). Uma re-renderização captura cauda + cunha + casco de uma vez —
   não re-renderizar antes, para não pagar duas vezes.
4. **GRU fases 2–3** — construção do cenário e clipes.
5. **Consolidação da pintura**: fazer de `refazer_marcas.py` o único pintor de
   marcas. Hoje os 11 builders carregam rasterizadores próprios e re-rodar
   qualquer um re-insere o defeito que a rodada das cunhas tirou (QA-BACKLOG).
6. **787-8/-9: assentamento da cunha** (+0,48/+0,56 m vs regra) — precisa de
   uma foto de perfil retificável de CC-BBF ou CC-BGK. Não copiar um no outro.
7. **Cargueiros: cunha sem veredito** (a asa cruza a cunha nas fotos
   disponíveis) — precisa de foto de ângulo melhor.
8. **Export GLB desatualizado** vs rodadas de QA — rodar `export_frota.py`
   depois da rodada da tinta (mecânico).
9. ~~Outras bases além de GRU~~ — **decidido (2026-08-26): só GRU por
   enquanto**; o ciclo fecha com 3 bases (SCL, São Carlos, GRU) em qualidade
   máxima antes de qualquer ampliação.
10. **E195-E2** — **decidido (2026-08-26): modelar quando houver foto de
    matrícula LATAM real** (chega no 2º semestre de 2026; o padrão do projeto
    exige foto da matrícula específica).

## Micro (não fazer isoladamente)

Detalhes em `QA-BACKLOG.md`: polo de valência 32 no nariz, pinch do cockpit do
767, UV da coroa do 787, título do A319 enterrado pela cunha, ângulos de
tailstrike, altura do 787-8, proporção do símbolo, portas de capô autorais no
SDSC, stand MID fora do solver, docks dimensionados pelo proxy nominal.
