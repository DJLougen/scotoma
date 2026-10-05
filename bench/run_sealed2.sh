#!/bin/bash
# One-shot sealed evaluation, exactly as pre-registered in bench/results/SEALED2_PREREG.md.
# Refuses to run twice: the log is the record of how many times sealed data was scored.
set -euo pipefail
cd "$(dirname "$0")/.."
LOG=bench/results/SEALED2_LOG.md
OUT=bench/results/sealed2
if [ -e "$OUT" ]; then echo "sealed results already exist at $OUT; see $LOG (not re-running)"; exit 1; fi
git diff --quiet HEAD -- bench/results/SEALED2_PREREG.md || { echo "pre-registration has uncommitted changes"; exit 1; }
mkdir -p "$OUT"
{
  echo "## Sealed evaluation 2, run 1"
  echo "- started: $(date -u +%FT%TZ)"
  echo "- commit: $(git rev-parse --short HEAD) (pre-registration $(git log -1 --format=%h -- bench/results/SEALED2_PREREG.md))"
} >> "$LOG"

for set in clin2_sealed clin2_novel_sealed; do
  python3 bench/tag.py bench/data/$set.jsonl /tmp/${set}_tagged.jsonl
  D=/tmp/${set}_tagged.jsonl
  P=clin2_test; [ $set = clin2_novel_sealed ] && P=clin2_novel
  # 1) systems at their pre-registered default points
  S="--system rules --system ours-v1=models/v1-small --system rules+ours-v1=models/v1-small --system rules+ours-v0=models/scotoma-v0-int8pc"
  for n in openmed:openmed openmed-large-fp32:openmed-large stanford:stanford piiranha-fp32:piiranha ai4privacy-en-fp32:ai4privacy-en ai4privacy-cat-fp32:ai4privacy-cat; do
    d=${n%%:*}; s=${n#*:}; S="$S --system $s=models/$d --system rules+$s=models/$d"
  done
  for p in openai-privacy-filter:privacy-filter presidio:presidio gliner-nvidia:gliner-nvidia gliner-knowledgator-large:gliner-large gliner-knowledgator-base:gliner-base gliner-knowledgator-edge:gliner-edge; do
    f=preds/${p%%:*}_$P.jsonl; s=${p#*:}
    [ -s "$f" ] || { echo "missing $f"; exit 1; }
    S="$S --system $s@$f --system rules+$s@$f"
  done
  python3 bench/run.py "$D" --out "$OUT/$set" $S
  # 2) competitors at their dev-matched thresholds (separate runs: --threshold is global)
  for m in openmed:0.02:openmed openmed-large-fp32:0.1:openmed-large stanford:0.1:stanford; do
    IFS=: read d t s <<< "$m"
    python3 bench/run.py "$D" --threshold $t --out "$OUT/${set}_${s}_t$t" --system $s-t$t=models/$d --system rules+$s-t$t=models/$d
  done
  echo "- scored: $set ($(wc -l < bench/data/$set.jsonl) docs)" >> "$LOG"
done
echo "- finished: $(date -u +%FT%TZ)" >> "$LOG"
echo "- sealed sets scored: 1 time each" >> "$LOG"
echo SEALED_DONE
