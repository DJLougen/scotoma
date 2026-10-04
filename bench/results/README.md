# Phase 0 results (2026-10-04, Google Colab L4)

First end-to-end run of `train/colab.ipynb`'s steps, done as shell scripts over the Colab CLI.
Every number below is copied from the `results.md` / JSON files in this folder; logs are in `logs/`.

## Setup

| Item | Value |
|---|---|
| Hardware | Colab L4 (22 GB), 12 vCPU. Scoring (`scotoma eval`) runs on CPU through ONNX Runtime |
| Software | torch 2.11.0+cu130, transformers 4.57.6, onnxruntime 1.30.0, datasets 4.8.5 |
| Template data | `generate.py` universe A n=30000 seed 7 (train), A n=2000 seed 8 (dev), B n=3000 seed 1 (test) |
| Nemotron-PII | 50000 train docs and 4000 test docs (`shuffle(seed=0)`); test split 2000 dev / 2000 test (`nemo_test.jsonl` = last 2000) |
| Our model | `microsoft/deberta-v3-small`, 3 epochs, batch 32, lr 5e-5, o-weight 1.0, seed 0. 80000 train docs became 89677 windows. Dev = 2000 docs sampled from template dev + Nemotron dev |
| Training time | about 21 minutes per epoch, 64 minutes in total |
| Baseline | `OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1`, exported by `scripts/fetch_model.py` |
| Precision used | int8 (`model_quantized.onnx`) for both models unless the table says otherwise |

Dev token metrics per epoch: F2 0.9905, then 0.9911, then 0.9919, with recall 0.9914 and precision 0.9939 at epoch 3.
The ONNX export matches PyTorch to within 1e-5 for both models.

## Template test (universe B, `--strict`), 3000 docs

Out of distribution for OpenMed. Same family as our training data (universe A), so a win here is
expected and does not prove much.

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules | 52.9 | 51.4 | 2932/3000 (97.7%) | 0.1% | 100.0 | 0.3 |
| openmed | 92.3 | 82.6 | 1421/3000 (47.4%) | 0.4% | 98.7 | 33.0 |
| rules+openmed | 96.4 | 90.8 | 828/3000 (27.6%) | 0.5% | 98.7 | 33.0 |
| ours | 96.7 | 93.0 | 821/3000 (27.4%) | 0.5% | 97.9 | 31.9 |
| rules+ours | 98.8 | 96.6 | 293/3000 (9.8%) | 0.6% | 97.9 | 32.8 |

## Nemotron-PII test, 2000 docs

Both models trained on Nemotron-PII's train split, so treat this as a ceiling.

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules | 51.5 | 50.9 | 1788/2000 (89.4%) | 0.2% | 96.6 | 0.2 |
| openmed | 97.3 | 94.5 | 196/2000 (9.8%) | 0.1% | 98.5 | 74.5 |
| rules+openmed | 97.8 | 97.0 | 157/2000 (7.8%) | 0.3% | 96.8 | 74.7 |
| ours | 98.5 | 98.3 | 99/2000 (5.0%) | 0.1% | 99.1 | 73.4 |
| rules+ours | 98.6 | 98.4 | 93/2000 (4.7%) | 0.3% | 97.5 | 74.4 |

## Is the scorer right? (Phase 0 sanity check)

- **The rules number reproduces.** Rules recall on the template test is 52.9%, the same figure as `plan.md`.
- **Runs are deterministic.** The baseline rows came out identical in two separate runs (`baseline_*` and `phase0_*`).
- **OpenMed against its card (micro-F1 0.954): card not reproducible; scorer path checked.** `crosscheck_hf.py` scores OpenMed in plain PyTorch with no Scotoma code in the path. It uses whitespace words, labels the first sub-token of each word, truncates at 384 tokens, and counts entities conlleval-style on Nemotron's own labels. Result on the same 2000 test docs: **P 0.922, R 0.915, micro-F1 0.918**, about 3.6 points below the card. The most-missed labels are occupation, country, state, company_name, date and time. The card itself lists occupation and time as weak, and Scotoma does not redact country or state at all. My best guess is that the gap comes from protocol differences: the card uses a stratified `test_strat` sample and its exact word segmentation is not published. I have not proven that. The model behaves sensibly through both paths: 97.3% recall and 98.5% precision through Scotoma's ONNX scorer, and 95.9% touch recall through PyTorch with 384-token truncation. Neither path shows signs of a broken export or label mapping. The model repo's `test_results.json` gives Trainer-style token-classification test F1 0.959, P 0.959, R 0.959. Its runtime and throughput (189.6 s at 237.3 samples/s) work out to about 45k samples. That is a second published evaluation, separate from the card's stratified 2k `test_strat` figure (0.954). Follow-up run on the **full official test split (100,000 docs)**: micro-F1 **0.921** with whitespace words (P 0.924, R 0.918), and **0.914** with punctuation split off (P 0.902, R 0.926). Files: `crosscheck_openmed_nemotron_full_*.json`. So the gap is not sampling noise: the 2k sample (0.918) and the full split agree. Nemotron-PII ships train 100k and test 100k, OpenMed's stated 50k/5k/45k split looks like a re-split of one of those, but which split, which indices and which segmentation were used is not published. Neither published figure (0.954 on the card, 0.959 in test_results) can be reproduced from public information. **Conclusion:** OpenMed scores about 0.92 under any protocol we can reconstruct. The ONNX path agrees with PyTorch (max difference 2e-5, int8 label agreement 1.00 on the probe). Scotoma-category recall is 97.3% through the shipped scorer. I treat the ONNX path and label mapping as correct, and the card number as not comparable.
- An earlier cross-check that used the HF `pipeline(aggregation_strategy=...)` and compared character spans exactly gave F1 0.33 and later 0.68. That came from the pipeline's sub-word merging, which glues on trailing punctuation and the next word. It was a bug in the check, not a property of the model, and has been replaced.

## int8 vs fp32 (our model, test-set diagnostic only)

Phase 3 says to make this choice on `dev`. These rows are on the test files, so they are a warning sign, not the selection.

| set | system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|---|
| Nemotron test | int8 | 98.5 | 98.3 | 99/2000 (5.0%) | 0.1% | 99.1 | 74.2 |
| Nemotron test | fp32 | 99.1 | 99.0 | 61/2000 (3.0%) | 0.1% | 98.5 | 113.8 |
| Templates B | int8 | 96.7 | 93.0 | 821/3000 (27.4%) | 0.5% | 97.9 | 31.5 |
| Templates B | fp32 | 99.0 | 97.5 | 315/3000 (10.5%) | 1.4% | 95.8 | 49.1 |

int8 costs 0.6 recall points on Nemotron and 2.3 on templates. Both are over the plan's half-point bar.
fp32 also redacts more ordinary text (1.4% on templates), so the two are at different operating
points. Compare them with a threshold sweep rather than at the shared 0.35 threshold. OpenMed was
only scored in int8.

## What broke and was fixed

| Problem | Fix |
|---|---|
| `scripts/fetch_model.py`: optimum's exporter fails on Colab (`huggingface_hub` / `diffusers` import errors) | Rewritten to export with `torch.onnx` directly and to check ONNX against PyTorch. optimum is no longer needed |
| DeBERTa's ONNX graph drops `token_type_ids`, so the check fed an input that does not exist | Feed only the inputs the session declares |
| `train/train.py`: torch ≥ 2.9 defaults to the dynamo ONNX exporter | Pass `dynamo=False`, with a fallback for older torch |
| `train/train.py`: the LR scheduler stepped even when AMP's GradScaler skipped an overflowed optimizer step | Step the scheduler only when the scale did not drop (smoke-tested with `--tiny` after the run; the reported model was trained before this fix) |
| `launch.command` and the top-level README still installed optimum | Both now install `torch "transformers>=4.57,<5" onnx onnxruntime`. `fetch_model.py` no longer leaves `model_fp32.onnx` in the app bundle unless given `--keep-fp32` |
| Notebook: installing optimum silently downgraded transformers to 4.57.6 | Notebook now pins `transformers>=4.57,<5`, the version that was verified, and runs training with `python -u` so progress shows up in logs |

## Notes

- `scotoma eval` decodes by summing the probability of all identifier classes against a 0.35 threshold. A barely trained smoke model (one epoch, 300 docs) still got 98.4% recall with 5.9% over-redaction on template dev for that reason. Decoder threshold and calibration matter, and the Phase 3 threshold sweep is the right tool.
- The trained model is in `models/scotoma-v0/` (int8 + fp32 ONNX, `tokenizer.json`, `config.json`), with the PyTorch checkpoint in `models/scotoma-v0/hf/`. Both are git-ignored. sha256 of `model_quantized.onnx`: `7e08df2b695ef78c0b33ae6543187d4c498ed82cc19e2926c038c6507a15cf69`.
- `bench/results/` and `bench/data/` are listed in `.gitignore`, and this folder is not a git repository. The plan says to commit these results; that has not been done.
