# Sealed evaluation 2: pre-registration

Written before any system has been run on `clin2_sealed` or `clin2_novel_sealed`. Fixed now. The protocol and claim
rule are the same as `SEALED_PREREG.md`, except for the new candidate below.

## Sets (fresh, never scored)

- `bench/data/clin2_sealed.jsonl`: the sealed half of a new planted batch (spec seed 12, DiffusionGemma prose,
  universe-C values, training-family formats). 1730 notes were accepted in total, split dev/sealed by hash of id.
- `bench/data/clin2_novel_sealed.jsonl`: the same notes with structured identifiers in test-only formats
  (`build_novel.py --seed 24`).
- `clin2_dev` / `clin2_novel_dev` are not used for selection either. Nothing below was tuned on any clin2 file.

## Candidate (ours)

- **ours-v1 shipped: `models/v1-small` per-channel int8 at threshold 0.02, plus rules (commit df7d012).**
  - DeBERTa-v3-small, fresh, 3 epochs.
  - Trained on the v0 data (Nemotron train 50k + universe-A templates 30k) plus 4,658 Qwen3-14B planted clinical notes
    (`train_planted.jsonl`, manifest `train_v1.manifest.json`).
  - Threshold kept at 0.02: on clinical dev with rules it gave 0 leak docs on both dev sets, at 0.22% over-redaction.
  - The best epoch was selected on token F2 over `dev_tpl` + `clin_dev`.
- References (no claims): `ours-v1` alone; ours-v0 shipped (`scotoma-v0-int8pc` @0.02 + current rules).
- Dropped on dev before this run: `v1-base` (DeBERTa-v3-base). At 0.02 with rules it leaked 18/844 dev docs at 0.6%
  over-redaction, worse than v1-small, and it is twice as slow.

## Competitors and operating points

These are unchanged from `SEALED_PREREG.md`:

| competitor | points |
|---|---|
| OpenMed large (fp32) | 0.35 and 0.10 |
| OpenMed small | 0.35 and 0.02 |
| Stanford | 0.35 and 0.10 |
| piiranha, ai4privacy-en, ai4privacy-cat | 0.35 |
| GLiNER (nvidia, knowledgator large / base / edge) | card threshold 0.3 |
| OpenAI privacy-filter | shipped default |
| Presidio | defaults |

Each competitor is scored alone and with our rules.

## Claim rule

Same as before: leak-document rate, over-redaction ≤ 1%, paired bootstrap (1000 resamples, seed 0, 95% CI).
"Beats X" requires a lower leak rate than X at both of X's points, with intervals excluding 0. Otherwise the result is
a tie or a loss, reported as such.

Model file under test: `models/v1-small/model_quantized.onnx`, sha256 `f3ea1a686e094622d2c1261b4dfaf8aa1680c9ac987907470f22ac0ede641f71`. `models/` is git-ignored, so this hash is the record.
