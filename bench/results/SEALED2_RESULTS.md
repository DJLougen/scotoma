# Sealed evaluation 2: results (2026-10-05)

Protocol: `SEALED2_PREREG.md` (commit 43ec838, before the run). Log: `SEALED2_LOG.md`. Each fresh set was scored
once, with no interruptions. Raw tables: `sealed2/`. The verdict uses a paired bootstrap of the leak-document rate
(1000 resamples, seed 0, 95% CI).

Candidate: **ours-v1 = `models/v1-small` (per-channel int8, sha256 f3ea1a68…) at threshold 0.02, plus rules.** It was
trained on the v0 data plus 4,658 Qwen3-written planted clinical notes, and the rules include the new `SURNAME, GIVEN`
detection.

## Headline (860 notes per set)

| system | clin2_sealed leak / over-red | clin2_novel_sealed leak / over-red | ms per note (CPU) |
|---|---|---|---|
| **rules + ours-v1** | **2 (0.2%)** / 0.2% | **2 (0.2%)** / 0.2% | 19–20 |
| rules + OpenMed-large @0.10 | 5 (0.6%) / 0.5% | 5 (0.6%) / 0.5% | 240–249 |
| rules + OpenMed-large @0.35 | 11 (1.3%) / 0.3% | 10 (1.2%) / 0.3% | 237–245 |
| rules + ours-v0 (reference) | 6 (0.7%) / 0.3% | 5 (0.6%) / 0.3% | 19–20 |
| ours-v1 alone | 5 (0.6%) / 0.1% | 22 (2.6%) / 0.1% | 19–20 |
| OpenMed-large @0.10 alone | 49 (5.7%) / 0.3% | 28 (3.3%) / 0.3% | 239–255 |

Precision of rules + ours-v1 is 99.7%. Rules + OpenMed-large @0.10 is at 97.5–97.7%.

## Pre-registered verdicts (rules + ours-v1 against each competitor at both of its points, with our rules)

| competitor | clin2_sealed | clin2_novel_sealed |
|---|---|---|
| OpenMed-large (fp32) | **tie**: better than @0.35 (+1.0 pp, CI [+0.3, +1.9]), tie with @0.10 (+0.3 pp, CI [−0.1, +0.9]) | **tie**: better than @0.35, tie with @0.10 (+0.3 pp, CI [−0.1, +0.8]) |
| OpenMed-small | tie (tie with @0.02) | **win** |
| Stanford | **win** | **win** |
| GLiNER nvidia / large / base / edge | **win** | **win** |
| OpenAI privacy-filter, Presidio, ai4privacy en/cat, piiranha | **win** | **win** |

Model alone: ours-v1 beats OpenMed-large at both points on clin2_sealed. On unseen formats it beats OpenMed-large @0.35
and ties @0.10.

## What changed since sealed evaluation 1

On the earlier sealed sets, OpenMed-large @0.10 + rules leaked 0.5% against our 1.9% / 1.7%, a significant loss.
On these fresh sets our shipped configuration leaks the fewest notes of any system (0.2%), which counts as a
**statistical tie** with OpenMed-large @0.10 + rules (0.6%). It also has lower over-redaction (0.2% vs 0.5%), higher
precision, about 12× lower CPU latency, and a working int8 format.

## Claims this supports

- "Fewest leaked notes of every system tested on two fresh sealed synthetic clinical sets (0.2%), statistically tied
  with OpenMed-PII-SuperClinical-Large tuned with our rules engine, at about 12× lower latency on a laptop CPU."
- "Significantly fewer leaked notes than Stanford, GLiNER (4 models), OpenAI privacy-filter, Presidio, ai4privacy and
  piiranha."

Still unsupported: a significant win over OpenMed-large, or anything about real clinical text (i2b2 has not been
run). The clin2 sealed sets are now spent.
