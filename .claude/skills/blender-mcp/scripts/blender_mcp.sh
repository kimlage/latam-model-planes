#!/usr/bin/env bash
# Operação do Blender com o addon MCP para este projeto.
#
#   blender_mcp.sh start   "<caminho.blend>"   sobe o Blender com o servidor MCP
#   blender_mcp.sh restart "<caminho.blend>"   mata e sobe de novo (após travar)
#   blender_mcp.sh status                       o servidor está ouvindo?
#   blender_mcp.sh marca                        imprime o marco de tempo (use ANTES de renderizar)
#   blender_mcp.sh wait "<render.png>" [s] [marco]  espera o render FINAL com margem
#
# O `wait` existe por um motivo específico: depois de um timeout de socket os
# renders enfileirados escrevem no MESMO arquivo, um atrás do outro. Quem lê o
# arquivo assim que ele aparece pega o render intermediário — foi o que produziu
# três diagnósticos falsos de "casco preto" quando o material estava correto.
set -euo pipefail

PORT=9876
BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
ADDON="import bpy; bpy.ops.preferences.addon_enable(module='blender_mcp_addon'); bpy.ops.blendermcp.start_server()"

subir() {
  "$BLENDER" "$1" --python-expr "$ADDON" >/tmp/blender_mcp.log 2>&1 &
  for i in $(seq 1 30); do
    if nc -z localhost "$PORT" 2>/dev/null; then
      echo "servidor MCP ouvindo na porta $PORT (${i}s)"
      return 0
    fi
    sleep 1
  done
  echo "servidor NAO subiu — veja /tmp/blender_mcp.log" >&2
  tail -20 /tmp/blender_mcp.log >&2
  return 1
}

case "${1:-}" in
  start)
    if nc -z localhost "$PORT" 2>/dev/null; then
      echo "ja esta ouvindo na porta $PORT — nao subi outro"
      exit 0
    fi
    subir "$2"
    ;;

  restart)
    # Reabrir descarta tudo que não foi salvo. Se o Blender ainda responde,
    # salve antes via MCP (bpy.ops.wm.save_mainfile) em vez de matar direto.
    pgrep -x Blender >/dev/null && pkill -x Blender || true
    sleep 3
    subir "$2"
    ;;

  status)
    if nc -z localhost "$PORT" 2>/dev/null; then
      echo "MCP OK na porta $PORT"
    else
      echo "MCP fechado"
      pgrep -x Blender >/dev/null && echo "(Blender roda, mas sem servidor)" || echo "(Blender nao roda)"
    fi
    ;;

  marca)
    # Pegue o marco ANTES de disparar o render e passe-o para o `wait`. Sem isso,
    # se o render terminar antes de você começar a esperar, o `wait` fica preso
    # aguardando uma escrita que nunca vem.
    date +%s
    ;;

  wait)
    alvo="$2"
    margem="${3:-20}"
    inicio="${4:-$(date +%s)}"
    # 1) esperar o arquivo ser tocado depois do marco
    while :; do
      if [ -f "$alvo" ] && [ "$(stat -f %m "$alvo")" -ge "$inicio" ]; then break; fi
      sleep 4
    done
    echo "primeira escrita detectada; aguardando ${margem}s de margem…"
    sleep "$margem"
    # 2) e então esperar o arquivo parar de mudar (fila esvaziada)
    anterior=""
    while :; do
      atual="$(stat -f '%m %z' "$alvo")"
      [ "$atual" = "$anterior" ] && break
      anterior="$atual"
      sleep 5
    done
    echo "render estavel: $alvo  ($(stat -f '%z bytes, mtime %Sm' -t %H:%M:%S "$alvo"))"
    ;;

  *)
    sed -n '2,12p' "$0"
    exit 1
    ;;
esac
