#!/bin/bash
# Resume bench/run_sealed3.sh one run at a time; skips runs that already wrote results.md.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=bench/results/SEALED3_LOG.md; OUT=bench/results/sealed3
run() { [ -f "$3/results.md" ] && return 0; rm -rf "$3"; python3 bench/run.py "$1" $2 --out "$3" "${@:4}" > "$3.log" 2>&1; }
for set in clin3_test clin3_novel; do
  D=bench/data/$set.jsonl
  run $D "--threshold 0.1" $OUT/${set}_oml_t0.1_rules --system rules+openmed-large-t0.1=models/openmed-large-fp32
  run $D "" $OUT/${set}_ours --system ours=models/v2-small --system rules+ours=models/v2-small
  run $D "" $OUT/${set}_oml_t0.35_rules --system rules+openmed-large=models/openmed-large-fp32
  run $D "--threshold 0.1" $OUT/${set}_oml_t0.1 --system openmed-large-t0.1=models/openmed-large-fp32
  run $D "" $OUT/${set}_oml_t0.35 --system openmed-large=models/openmed-large-fp32
  echo "- scored: $set ($(wc -l < $D) notes)" >> "$LOG"
done
echo "- finished: $(date -u +%FT%TZ)" >> "$LOG"; echo "- each clin3 set scored 1 time" >> "$LOG"
echo SEALED3_DONE
