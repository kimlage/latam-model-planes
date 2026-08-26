# Pendências — lista viva do projeto

Ordenada por impacto no realismo. Regra de trabalho: **nada de micro-correções
isoladas** — cada rodada ataca o item mais alto que estiver destravado, e os
itens micro só entram anexados a uma rodada maior que já re-renderize o que
eles tocam.

## Em andamento

1. **Rodada da verdade da tinta (frota inteira).** Duas metades que fecham com
   uma única re-renderização do gate:
   - Casco branco-puro → branco real medido (QA-BACKLOG: LiveryTex 76% em
     1.0 puro contra #E6E7EA fotografado). Afeta todo pixel de toda aeronave
     em toda cena — o item de maior alcance do backlog.
   - As 4 cunhas suspeitas sem controle de deriva (A320ceo +0,65 m,
     A320neo +0,70, A321neo +0,78, 767-300ER −0,53) e a contradição do A319
     (porta 4/título/matrícula 1,2–2,2 m à ré da foto num quadro validado pela
     deriva, com o ACAP concordando com o modelo). Caça de fotos novas com
     deriva utilizável; sem foto, registra-se o impasse, não se chuta.
2. **GRU (SBGR) fase 1 — pesquisa e dados.** Terceira base: maior hub da LATAM
   e casa da manutenção do 777-300ER (o único tipo sem presença em cenário).

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
