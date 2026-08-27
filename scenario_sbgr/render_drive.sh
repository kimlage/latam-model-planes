#!/bin/bash
# Chunked clip render driver - the anti-stall shape the reboot lesson set:
# one blender process per chunk (none lives long), frames INSIDE the repo
# (git-ignored, survive a reboot), existing frames skipped so any rerun
# resumes. Usage:
#   bash scenario_sbgr/render_drive.sh <scene.blend> <frames_dir> <end> [chunk]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
BLEND="$1"; DIR="$2"; END="$3"; CHUNK="${4:-30}"
mkdir -p "$DIR"
f=1
while [ "$f" -le "$END" ]; do
  t=$((f + CHUNK - 1)); [ "$t" -gt "$END" ] && t="$END"
  blender -b "$BLEND" -P "$HERE/render_chunks.py" -- \
      --dir "$DIR" --start "$f" --end "$t" --no-blur 2>&1 | \
      grep -E "^frame |CHUNK DONE|Error|error|Traceback" || true
  f=$((t + 1))
done
n=$(ls "$DIR" | grep -c '\.png$')
echo "DRIVE DONE $DIR $n frames"
