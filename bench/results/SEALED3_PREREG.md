# Sealed evaluation 3: a powered head-to-head with OpenMed-large

Written while `clin3` is still being generated on Colab. No clin3 file has been downloaded or read. The sample size,
systems, test and decision rule are fixed below. They will not change after any clin3 result is seen, and the test
runs exactly once.

## Why

Sealed evaluation 2 gave rules + ours-v1 0.2% vs rules + OpenMed-large @0.10 0.6% (860 notes per set): a tie, because
there were only 5 discordant notes. Discordant notes are those where exactly one of the two systems leaks; in run 2
we leaked alone on 1 note and they leaked alone on 4.

Power simulation (exact McNemar, two-sided α = 0.05, Poisson discordance):

| assumed per-note discordance (ours-only, theirs-only) | 4,000 notes | 6,000 notes | 8,000 notes |
|---|---|---|---|
| observed (0.12%, 0.47%) | 0.81 | 0.94 | 0.98 |
| conservative (0.15%, 0.35%) | 0.34 | 0.52 | 0.68 |

## Data

- `clin3`: fresh planted batch, `plant_generate.py spec --n 8200 --seed 13` (test pool: universe-C values,
  training-family formats), written by DiffusionGemma, verified with `verify_planted.py --scotoma`.
  **All** accepted notes form the sealed set (`clin3_test.jsonl`). There is no dev split.
- `clin3_novel`: the same notes with test-only formats (`build_novel.py --seed 25`).
- N is whatever the verifier accepts from the 8,200 specs, expected around 7,000. There is no stopping early and no
  topping up.

## Primary hypothesis (one test)

On `clin3_test.jsonl`, **rules + ours** leaks fewer notes than **rules + OpenMed-PII-SuperClinical-Large (fp32) at
threshold 0.10**, its best pre-registered point.

- Test: exact two-sided McNemar test on per-note leak indicators, α = 0.05.
- Reported alongside: the paired bootstrap 95% CI of the leak-rate difference (1000 resamples, seed 0).
- Claim "significantly fewer leaked notes than OpenMed-large" only if p < 0.05 **and** ours leaks less.
- Over-redaction of ours must be ≤ 1% for the claim to stand.

## Secondary (reported, no multiplicity correction claimed)

1. Same test on `clin3_novel`.
2. Rules + ours vs rules + OpenMed-large at 0.35, on both sets.
3. Ours alone vs OpenMed-large alone at 0.10, on both sets.

## Which "ours"

Fixed before scoring by this rule. Candidates are `v1-small` (`SEALED2_PREREG.md`, sha256 f3ea1a68…) and `v2-small`
(same recipe plus about 7–8k more Qwen3-written planted training notes, training now). Choose v2-small only if, on
`clin2_dev` + `clin2_novel_dev` with rules at threshold 0.02, it leaks strictly fewer notes than v1-small, with
over-redaction ≤ 0.5% on both. Otherwise use v1-small. The choice and the model's sha256 are appended here, and
committed, before the sealed run.

## Selection of "ours" (done before any clin3 scoring)

`bench/data/clin3_*` was downloaded and only line-counted: 7,108 accepted notes in each of `clin3_test.jsonl` and
`clin3_novel.jsonl`. No system has been run on them.

Selection rule on clin2_dev + clin2_novel_dev, rules + model at threshold 0.02 (leak docs / over-redaction):

| model | clin2_dev | clin2_novel_dev | total leaks |
|---|---|---|---|
| v1-small | 4 / 0.2% | 2 / 0.2% | 6 |
| v2-small | 2 / 0.2% | 0 / 0.2% | 2 |

v2-small leaks strictly fewer notes and its over-redaction is ≤ 0.5%, so **ours = v2-small** at threshold 0.02 + rules.

`models/v2-small/model_quantized.onnx` sha256 `33be24386b0bbdb2758a86087140f7a4a93bd21923a85fe20085bf611ba87e41`. Training mix: `train_v2.manifest.json` (v0 data plus 12,273
Qwen3-written planted notes).
