# Sealed evaluation: results (run 1, 2026-10-05)

Protocol: `SEALED_PREREG.md` (commits c30b855 and 7abc2fd, both before the run). Log: `SEALED_LOG.md`. Each sealed set
was scored once. The runner stopped once without an error message after the main `clin_sealed` table and was
resumed for the remaining pre-registered runs only, with nothing re-scored. Raw tables: `sealed/`. Merged item matrices
for the bootstrap were built with `bench/merge_responses.py`.

Shipped configuration: per-channel int8 model at threshold 0.02 plus rules (`rules+ours-shipped`). The verdict comes
from the paired bootstrap of the leak-document rate (1000 resamples, seed 0, 95% CI, `bench/bootstrap.py`).

## Headline

| set | rules+ours-shipped | best competitor (its best pre-registered point, + our rules) | competitor alone (best point) | ours-shipped alone |
|---|---|---|---|---|
| `clin_sealed` (874), training-family formats | 1.9% leak, 0.3% over-red, 19 ms/doc | OpenMed-large @0.10 + rules: **0.5%**, 0.5% over-red, 242 ms/doc | OpenMed-large @0.10: 5.7% | **1.9%** |
| `clin_novel_sealed` (874), unseen formats | 1.7% leak, 0.3% over-red, 20 ms/doc | OpenMed-large @0.10 + rules: **0.5%**, 0.5% over-red, 245 ms/doc | OpenMed-large @0.10: **2.3%** | 5.6% |

## Pre-registered verdicts (shipped configuration against each competitor at both of its points, with our rules)

| competitor | clin_sealed | clin_novel_sealed |
|---|---|---|
| OpenMed-PII-SuperClinical-Large (fp32) | **not a win**: tie at 0.35, worse at 0.10 (−1.5 pp, CI [−2.4, −0.7]) | **not a win**: tie at 0.35, worse at 0.10 (−1.3 pp, CI [−2.2, −0.5]) |
| OpenMed-PII-SuperClinical-Small | not a win: better at 0.35, tie at 0.02 | **win** at both |
| Stanford de-identifier | **win** at both | **win** at both |
| GLiNER nvidia / knowledgator large, base, edge | **win** (all four) | **win** (all four) |
| OpenAI privacy-filter | **win** | **win** |
| Presidio | **win** | **win** |
| ai4privacy en/cat, piiranha | **win** | **win** |

## Model alone, no rules

- On training-family formats, ours-shipped (1.9%) beats OpenMed-large at both points: 9.2% at 0.35 and 5.7% at 0.10,
  CIs excluding 0.
- On unseen formats, ours-shipped (5.6%) ties OpenMed-large at 0.35 (5.7%) and loses to it at 0.10 (2.3%,
  CI [−4.8, −1.9]).

## What this supports

- Supported: **"Leaks fewer clinical notes than Stanford, GLiNER (4 models), OpenAI privacy-filter, Presidio,
  ai4privacy and piiranha, on a sealed synthetic clinical set, running on-device at about 20 ms per note."**
- Not supported: **"beats every model."** OpenMed-PII-SuperClinical-Large, tuned to threshold 0.10 and combined with
  our rules engine, leaked fewer notes on both sealed sets. It is about 12× slower on CPU (about 245 ms per note) and
  its tested dynamic-int8 conversion failed (58% recall on the template test). Other compression schemes for it were
  not tried, so "it cannot ship on-device" is not established either.
- Our model loses most of its edge on identifier formats it never trained on (5.6% alone against 1.9% on
  familiar formats). Our rules recover most of it (1.7%). This is the gap the format-ingest pipeline targets.

The sealed sets are now spent for these claims. Any model trained after this point needs a fresh sealed batch
(`bench/plant_generate.py spec` with a new seed, plus a new generation run).
