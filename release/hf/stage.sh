#!/bin/sh
# Stage scotoma v2-small artefacts into the HF repo dir for manual upload.
# Copies files; prints sha256; never uploads.
set -eu

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SRC="$REPO_ROOT/models/v2-small"
DST="$REPO_ROOT/release/hf/scotoma-clinical-deid-v2"

FILES="config.json tokenizer.json model_quantized.onnx"
FORCE=0
for arg in "$@"; do
    case "$arg" in
        --fp32)  FILES="$FILES model_fp32.onnx" ;;
        --force) FORCE=1 ;;
        *) echo "usage: $0 [--fp32] [--force]" >&2; exit 2 ;;
    esac
done

mkdir -p "$DST"
for f in $FILES; do
    src="$SRC/$f"; dst="$DST/$f"
    [ -f "$src" ] || { echo "missing $src" >&2; exit 1; }
    if [ -f "$dst" ] && ! cmp -s "$src" "$dst" && [ "$FORCE" -eq 0 ]; then
        echo "$dst exists and differs — pass --force to overwrite" >&2; exit 1
    fi
    cp "$src" "$dst"
done

echo "Staged into $DST:"
cd "$DST" && shasum -a 256 $FILES
echo
echo "No upload performed. Review, then upload manually."
