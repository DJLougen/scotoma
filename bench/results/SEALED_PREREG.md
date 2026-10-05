# Sealed evaluation: pre-registration

Written before any system has been run on a sealed file. Everything below is fixed now. The sealed files are scored
exactly once with this protocol, and every run is logged in `SEALED_LOG.md`.

## Sets

- `bench/data/clin_sealed.jsonl`: 874 planted-identifier clinical notes (DiffusionGemma prose, universe-C values,
  identifier formats from the training-family generator).
- `bench/data/clin_novel_sealed.jsonl`: the same 874 notes with structured identifiers re-drawn from **test-only
  formats** (`bench/formats.py`, split `test`), which no model of ours has trained on.

## Systems and operating points (all chosen on clinical dev only)

| system | threshold | why |
|---|---|---|
| ours, shipped: per-channel int8 + rules | 0.02 | clinical threshold chosen on the first 200 dev docs, confirmed on the other 644 |
| ours, per-channel int8, model alone | 0.02 | same |
| ours, fp32, model alone and + rules | 0.35 | default, reference |
| OpenMed small, OpenMed large (fp32), Stanford, piiranha (fp32), ai4privacy-en/-cat (fp32) | 0.35 | our decoder's default, same as for our model |
| OpenMed small, OpenMed large, Stanford | dev-matched | the threshold with the fewest dev leak docs among dev thresholds with over-redaction ≤ 0.5% (`bench/matched.py` on `clin_sweeps/`), so competitors also get a tuned point |
| GLiNER nvidia / knowledgator large, base, edge | card threshold (0.3) | as published by each model card |
| OpenAI privacy-filter | shipped calibration (`default` operating point) | as published |
| Presidio | defaults | as published |

Each system is scored alone and with our rules (`rules+X`), the same way as on dev.

## Metrics

- **Primary:** leak-document rate, meaning the share of notes with at least one identifier left untouched.
- **Constraint:** over-redaction ≤ 1%. A system above it is reported but not ranked as a win.
- **Secondary:** recall, fully-redacted rate, precision, per-category recall.

## Claim rule

"Ours beats system X on sealed set S" means all three of:

1. The shipped configuration's leak-doc rate is lower than X's at both of X's operating points.
2. The shipped configuration's over-redaction is ≤ 1%.
3. The gap is larger than the 95% bootstrap interval of the difference (1000 resamples over documents, seed 0).
   If it isn't, the result is reported as a tie.

If the novel-format set reverses a result from the training-family-format set, both are reported and the claim is
restricted accordingly.
