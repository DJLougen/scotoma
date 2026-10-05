#!/bin/bash
# One-shot powered head-to-head (bench/results/SEALED3_PREREG.md). Refuses to run twice.
set -euo pipefail
cd "$(dirname "$0")/.."
LOG=bench/results/SEALED3_LOG.md; OUT=bench/results/sealed3
[ -e "$OUT" ] && { echo "already run; see $LOG"; exit 1; }
git diff --quiet HEAD -- bench/results/SEALED3_PREREG.md || { echo "pre-registration has uncommitted changes"; exit 1; }
mkdir -p "$OUT"
{ echo "## Sealed evaluation 3, run 1"; echo "- started: $(date -u +%FT%TZ)"; echo "- commit: $(git rev-parse --short HEAD)"; } >> "$LOG"
run() { python3 bench/run.py "$1" $2 --out "$3" "${@:4}" > "$3.log" 2>&1; }
for set in clin3_test clin3_novel; do
  D=bench/data/$set.jsonl
  run $D "" $OUT/${set}_ours --system ours=models/v2-small --system rules+ours=models/v2-small &
  run $D "--threshold 0.1" $OUT/${set}_oml_t0.1_rules --system rules+openmed-large-t0.1=models/openmed-large-fp32 &
  run $D "--threshold 0.1" $OUT/${set}_oml_t0.1 --system openmed-large-t0.1=models/openmed-large-fp32 &
  run $D "" $OUT/${set}_oml_t0.35_rules --system rules+openmed-large=models/openmed-large-fp32 &
  run $D "" $OUT/${set}_oml_t0.35 --system openmed-large=models/openmed-large-fp32 &
  wait
  echo "- scored: $set ($(wc -l < $D) notes)" >> "$LOG"
done
echo "- finished: $(date -u +%FT%TZ)" >> "$LOG"
echo "- each clin3 set scored 1 time" >> "$LOG"
echo SEALED3_DONE
