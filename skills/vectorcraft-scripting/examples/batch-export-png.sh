#!/bin/sh
# batch-export-png.sh: export every readable file in a folder as PNG (port of batch-export-png.jsx).
#
#   batch-export-png.sh IN_DIR OUT_DIR [SCALE] [--per-file]
#
# The original exported every *open* Illustrator document as PNG-24 with a transparent background,
# clipped to the artboard at 100 %. VectorCraft has no script engine; this drives the headless CLI:
#
#   default     one `vectorcraft-cli run` that plays action.batch over IN_DIR (and its subfolders):
#               each file is opened, its first artboard exported to OUT_DIR/<stem>.png and closed.
#               One process; up to 500 files; a file that fails is reported and the rest go on.
#   --per-file  one `vectorcraft-cli convert` per file: slower, but each file is isolated, and the
#               loop is easy to change (filters, naming, parallel runs with xargs -P).
#
# SCALE is pixels per point (default 1 = 72 ppi, the original's 100 %; 2 for @2x). PNG export is
# transparent and uses the first artboard by default. Files with the same stem in different
# subfolders write the same OUT_DIR/<stem>.png: the last one wins.
# For the live app's open documents, use `vc_control.py export-open OUT_DIR` instead.
set -eu

VC=${VECTORCRAFT_CLI:-vectorcraft-cli}
[ $# -ge 2 ] || { echo "usage: $0 IN_DIR OUT_DIR [SCALE] [--per-file]" >&2; exit 64; }
IN=$1 OUT=$2 SCALE=1 MODE=batch
shift 2
for arg in "$@"; do
  case $arg in
    --per-file) MODE=per-file ;;
    *) SCALE=$arg ;;
  esac
done
[ -d "$IN" ] || { echo "not a folder: $IN" >&2; exit 66; }
mkdir -p "$OUT"
IN=$(cd "$IN" && pwd) OUT=$(cd "$OUT" && pwd)   # action.batch wants absolute folders

# JSON string escaping for paths (backslash and double quote).
json_str() { printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"; }

if [ "$MODE" = per-file ]; then
  status=0
  for f in "$IN"/*; do
    [ -f "$f" ] || continue
    name=$(basename "$f"); stem=${name%.*}
    case $(printf '%s' "${name##*.}" | tr 'A-Z' 'a-z') in
      vectorcraft|drawcraft|svg|svgz|pdf|ai|ait|eps|epsf|ps|dxf|emf|wmf|psd|psb|af|afdesign|afpub|vctemplate|png|jpg|jpeg|gif|webp|tif|tiff|bmp|tga) ;;
      *) continue ;;
    esac
    # convert prints {path, bytes, format, warnings} (and importWarnings when reading lost something).
    if ! "$VC" convert "$f" "$OUT/$stem.png" --scale "$SCALE"; then
      echo "failed: $f" >&2; status=1
    fi
  done
  exit $status
fi

# One step, read from standard input: the action's commands run on every file action.batch opens.
# overrideExport (default true) points document.export at OUT/<stem>.png; leaving `destination`
# out means "save nothing" (destination "folder" would also save a copy of each source file there).
# `run` exits 0 when action.batch itself ran, even if files failed: check its "failed" count.
result=$("$VC" run --commands - <<EOF
[{"command": "action.batch", "params": {
  "folder": $(json_str "$IN"),
  "includeSubdirs": true,
  "destinationFolder": $(json_str "$OUT"),
  "stopOnError": false,
  "commands": [
    {"command": "document.export", "params": {"format": "png", "scale": $SCALE, "background": "transparent"}},
    {"command": "file.close", "params": {}}
  ]}}]
EOF
)
printf '%s\n' "$result"
case $result in
  *'"failed":0,'*) ;;
  *) echo "some files failed: see \"processed\" in the result above" >&2; exit 1 ;;
esac
