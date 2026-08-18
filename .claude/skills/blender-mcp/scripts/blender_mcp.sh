#!/usr/bin/env bash
# Driving Blender with the MCP addon for this project.
#
#   blender_mcp.sh start   "<path.blend>"    starts Blender with the MCP server
#   blender_mcp.sh restart "<path.blend>"    kills it and starts again (after a hang)
#   blender_mcp.sh status                       is the server listening?
#   blender_mcp.sh marca                        prints the timestamp (use BEFORE rendering)
#   blender_mcp.sh wait "<render.png>" [s] [mark]  waits for the FINAL render, with margin
#
# The `wait` exists for a specific reason: after a socket timeout the queued
# renders write to the SAME file, one after another. Whoever reads the file as
# soon as it shows up gets the intermediate render — that is what produced three
# false "black hull" diagnoses while the material was correct.
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
    # Reopening discards everything unsaved. If Blender still answers, save
    # through MCP first (bpy.ops.wm.save_mainfile) instead of killing it outright.
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
    # Take the mark BEFORE firing the render and pass it to `wait`. Without it,
    # if the render finishes before you start waiting, `wait` gets stuck waiting
    # for a write that never comes.
    date +%s
    ;;

  wait)
    alvo="$2"
    margem="${3:-20}"
    inicio="${4:-$(date +%s)}"
    # 1) wait for the file to be touched after the mark
    while :; do
      if [ -f "$alvo" ] && [ "$(stat -f %m "$alvo")" -ge "$inicio" ]; then break; fi
      sleep 4
    done
    echo "primeira escrita detectada; aguardando ${margem}s de margem…"
    sleep "$margem"
    # 2) and then wait for the file to stop changing (queue drained)
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
