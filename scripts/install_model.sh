#!/usr/bin/env bash
# Install a locally trained/quantized model dir into the app bundle.
#
#   scripts/install_model.sh SRC_DIR THRESHOLD [DOMAIN]
#
# Example (the shipped clinical model):
#   scripts/install_model.sh models/scotoma-v0-int8pc 0.02 clinical
#
# Copies model_quantized.onnx (or model.onnx), tokenizer.json and config.json
# from SRC_DIR into app/src-tauri/models/default, then stamps
# scotoma_threshold (and scotoma_domain when given) into config.json so the
# app and the scotoma CLI adopt it as the default redaction threshold.
set -euo pipefail

SRC="${1:?usage: install_model.sh SRC_DIR THRESHOLD [DOMAIN]}"
THRESHOLD="${2:?usage: install_model.sh SRC_DIR THRESHOLD [DOMAIN]}"
DOMAIN="${3:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/app/src-tauri/models/default"

[ -f "$SRC/tokenizer.json" ] || { echo "no tokenizer.json in $SRC" >&2; exit 1; }
[ -f "$SRC/config.json" ]    || { echo "no config.json in $SRC" >&2; exit 1; }
if [ ! -f "$SRC/model_quantized.onnx" ] && [ ! -f "$SRC/model.onnx" ]; then
    echo "no model_quantized.onnx / model.onnx in $SRC" >&2; exit 1
fi

mkdir -p "$DEST"
rm -f "$DEST"/*     # a stale second model file would shadow the new one
for f in model_quantized.onnx model.onnx tokenizer.json config.json; do
    [ -f "$SRC/$f" ] && cp "$SRC/$f" "$DEST/$f"
done

python3 - "$DEST/config.json" "$THRESHOLD" "$DOMAIN" <<'PY'
import json, sys
path, threshold, domain = sys.argv[1], float(sys.argv[2]), sys.argv[3]
cfg = json.load(open(path))
cfg["scotoma_threshold"] = threshold
if domain:
    cfg["scotoma_domain"] = domain
json.dump(cfg, open(path, "w"), indent=1)
print(f"config.json: scotoma_threshold={threshold}" + (f", scotoma_domain={domain!r}" if domain else ""))
PY

echo "installed $SRC -> $DEST"
