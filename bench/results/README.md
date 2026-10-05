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
- Results committed in git (33765a7); `bench/data/` stays git-ignored and is regenerable from the seeds above.

# Phase 1 (2026-10-04/05): competitor field, clinical planted-identifier test set

## How the clinical set is built (deterministic labels, no hand tagging)

1. `bench/plant_generate.py spec --n 2000 --seed 11` picks every identifier value in advance (byte-identical on rerun).
   Names, streets, cities, organisations and mail hosts come from **universe C**, a test-only pool disjoint from the
   template generator's train (A) and test (B) pools (asserted at import).
2. An LLM writes each note around typed placeholders (`[[NAME_1]]`, `[[MRN_1]]` …), never seeing a real value.
   Generator: `RedHatAI/diffusiongemma-26B-A4B-it-FP8-dynamic` (Apache-2.0) on vLLM 0.30.0, Colab A100 40 GB,
   server-default diffusion sampler (the server rejects temperature/seed for diffusion models, so the text is not
   bit-reproducible; the generated raw file `bench/data/clin_raw.jsonl` is the frozen artefact).
3. `bench/verify_planted.py` substitutes the values, so every label offset is known by construction, then
   string-checks each one and rejects any note with a missing/unknown placeholder, too few repeats, or anything that
   looks like an identifier the LLM invented (unplanted digits, dates, emails, URLs, pool names, institution names,
   rules-engine hits). Re-running the verifier locally on the downloaded raw file gives a byte-identical output.
4. Result: 1718 of 2000 accepted (282 rejected, almost all for under-used placeholders; 9 for rules-engine hits),
   split by hash of id into **dev 844** and **sealed 874**. Only dev has been scored. The sealed half has been scored
   **0 times**.

**Known bias, read before quoting:** the identifier *formats* (MRN, account, VIN, plan numbers…) come from the same
format code as our template training data (`bench/generate.py`), even though the values and names are new. That
favours our model on structured categories. Names are the least biased category. A format-novel variant and a
human-checked natural set are still needed for public claims.

## Clinical dev, 844 docs (all systems, same scorer, default threshold 0.35)

ms/doc is 0.0 for systems whose predictions were computed beforehand on GPU (privacy-filter, Presidio, GLiNER);
their speed is not measured here.

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc | source |
|---|---|---|---|---|---|---|---|
| rules+ours-fp32 | 99.7 | 97.0 | 19/844 (2.3%) | 0.2% | 99.7 | 41.8 | `clin_dev_hf` |
| ours-fp32 | 99.7 | 96.8 | 21/844 (2.5%) | 0.0% | 99.7 | 41.0 | `clin_dev_hf` |
| rules+openmed-large | 99.7 | 95.9 | 21/844 (2.5%) | 0.3% | 98.8 | 272.6 | `clin_dev_hf` |
| openmed-large | 98.5 | 94.2 | 85/844 (10.1%) | 0.1% | 98.8 | 265.8 | `clin_dev_hf` |
| rules+stanford | 98.4 | 93.8 | 93/844 (11.0%) | 0.4% | 99.0 | 30.5 | `clin_dev_hf` |
| rules+gliner-edge | 98.5 | 96.1 | 94/844 (11.1%) | 1.9% | 90.8 | 0.2 | `clin_dev_gl_edge` |
| rules+ours | 97.8 | 94.6 | 130/844 (15.4%) | 0.2% | 99.9 | 22.4 | `clin_dev_hf` |
| rules+openmed | 97.2 | 94.0 | 167/844 (19.8%) | 0.2% | 99.9 | 22.2 | `clin_dev_hf` |
| ours | 97.0 | 93.4 | 172/844 (20.4%) | 0.0% | 99.9 | 20.8 | `clin_dev_hf` |
| gliner-edge | 96.3 | 90.5 | 207/844 (24.5%) | 1.7% | 91.1 | 0.0 | `clin_dev_gl_edge` |
| rules+privacy-filter | 95.1 | 93.5 | 244/844 (28.9%) | 0.5% | 99.6 | 0.2 | `clin_dev_ext` |
| stanford | 95.1 | 83.3 | 280/844 (33.2%) | 0.3% | 99.0 | 30.6 | `clin_dev_hf` |
| openmed | 92.7 | 86.6 | 333/844 (39.5%) | 0.0% | 99.9 | 21.7 | `clin_dev_hf` |
| rules+presidio | 90.9 | 81.2 | 420/844 (49.8%) | 1.8% | 92.6 | 0.2 | `clin_dev_ext` |
| privacy-filter | 87.1 | 85.5 | 494/844 (58.5%) | 0.3% | 99.5 | 0.0 | `clin_dev_ext` |
| rules+ai4privacy-en | 83.5 | 78.0 | 563/844 (66.7%) | 0.3% | 99.2 | 109.2 | `clin_dev_hf` |
| rules+ai4privacy-cat | 81.5 | 70.8 | 580/844 (68.7%) | 0.2% | 99.6 | 104.5 | `clin_dev_hf` |
| presidio | 82.3 | 67.9 | 614/844 (72.7%) | 1.7% | 92.1 | 0.0 | `clin_dev_ext` |
| ai4privacy-en | 77.5 | 66.7 | 640/844 (75.8%) | 0.1% | 99.1 | 105.6 | `clin_dev_hf` |
| rules+piiranha | 79.7 | 74.9 | 655/844 (77.6%) | 0.3% | 99.6 | 100.9 | `clin_dev_hf` |
| ai4privacy-cat | 69.9 | 52.6 | 763/844 (90.4%) | 0.1% | 99.5 | 111.8 | `clin_dev_hf` |
| piiranha | 57.3 | 49.0 | 820/844 (97.2%) | 0.1% | 99.4 | 101.7 | `clin_dev_hf` |
| rules | 47.3 | 46.9 | 821/844 (97.3%) | 0.2% | 100.0 | 0.1 | `clin_dev_hf` |

Recall by category, model alone (from `clin_dev_hf/results.md`): our int8 model loses mainly on AGE (81.0 vs 98.2
fp32), VEHICLE (80.5 vs 96.6) and NAME (97.4 vs 99.9). Stanford never detects ages over 89 (0.6%).

## Shipping format: int8 conversion was the bottleneck

The default ONNX Runtime dynamic int8 export loses most of our model's advantage (20.4% vs 2.5% leaking docs on
clinical dev). Per-channel int8 (`quantize_dynamic(per_channel=True)`, same 172 MB) plus a lower threshold recovers
most of it. Threshold chosen on the first 200 dev docs, then checked on the other 644:

| model / threshold (644 held-out dev docs) | recall | leak docs | over-redaction | ms/doc |
|---|---|---|---|---|
| int8 per-channel @ 0.02 | 99.7 | 16/644 (2.5%) | 0.1% | 21.9 |
| int8 default @ 0.02 | 99.5 | 23/644 (3.6%) | 0.1% | 22.4 |
| fp32 @ 0.02 | 99.9 | 3/644 (0.5%) | 0.3% | 41.8 |
| fp32 @ 0.35 | 99.6 | 18/644 (2.8%) | 0.0% | 43.8 |
| int8 per-channel @ 0.35 | 97.5 | 116/644 (18.0%) | 0.0% | 21.7 |

0.02 is a clinical operating point only: on the template test it over-redacts 3.0% (above the 1% cap), on Nemotron
0.7%. Per-domain thresholds are needed. OpenMed-large's int8 export also failed (58% recall on templates); only our
tested dynamic-int8 conversion is shown to fail, other schemes (QDQ, fp16, QAT) were not tried for it.

## New competitors on the template and Nemotron tests

See `p1d_test_tpl`, `p1d3_test_tpl`, `p1d2_*`, `p1d3_nemo_test`, `p1d_pf_*`. Licences checked on Hugging Face:
piiranha is **CC BY-NC-ND 4.0** (benchmark only, not commercial); ai4privacy's real models are ModernBERT
(`llama-ai4privacy-*`), not "deberta-v3-base-pii"; ai4privacy-en's low template recall (54%) was cross-checked with its
own HF pipeline (51.5% on 40 docs) so it is not a Scotoma conversion artefact.
