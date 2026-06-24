#!/usr/bin/env bash
# extract-frames.sh — pull a still from a session recording at each insight timestamp.
# Part of the meetinginsights pipeline. Resolves "needs screen context" cards.
#
# Usage:
#   ./extract-frames.sh VIDEO MANIFEST OUTDIR [SCALE_WIDTH]
#
# MANIFEST lines: ID|HH:MM:SS|label    (blank lines / # comments ignored)
# Produces OUTDIR/ID_HHMMSS.jpg and a contact sheet OUTDIR/_contact_sheet.jpg if ImageMagick is present.

set -euo pipefail
VIDEO="${1:?video path}"; MANIFEST="${2:?manifest path}"; OUT="${3:?out dir}"; W="${4:-960}"
mkdir -p "$OUT"
n=0
while IFS='|' read -r id ts label; do
  [[ -z "${id// }" || "${id:0:1}" == "#" ]] && continue
  id="${id// }"; ts="${ts// }"
  safe="${ts//:/}"
  # -ss before -i = fast seek; one frame; scale keeping aspect
  ffmpeg -nostdin -loglevel error -ss "$ts" -i "$VIDEO" -frames:v 1 \
    -vf "scale=${W}:-2" -q:v 3 "$OUT/${id}_${safe}.jpg" -y
  echo "  $id  $ts  ${label}"
  n=$((n+1))
done < "$MANIFEST"
echo "Extracted $n frames -> $OUT"

# Optional contact sheet
if command -v montage >/dev/null 2>&1 && [ "$n" -gt 0 ]; then
  montage "$OUT"/*.jpg -tile 4x -geometry 400x+6+6 -background '#1c2024' \
    -title "Cata B session — screen-context frames" "$OUT/_contact_sheet.jpg" 2>/dev/null \
    && echo "Contact sheet -> $OUT/_contact_sheet.jpg" || true
fi
