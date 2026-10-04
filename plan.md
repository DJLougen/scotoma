# Scotoma: training and data pipeline plan

Goal: a redaction model per domain that beats public baselines on data none of them trained on, with
numbers a buyer can check. This plan covers data, training, evaluation and release. It does not cover
the app, Windows support or packaging.

## Where things stand

| Piece | State |
|---|---|
| Rules engine | Works. 52.9% recall on the template test, 0.1% over-redaction. |
| Scorer (`scotoma eval`, `bench/run.py`) | Works. Reports recall, leak documents, over-redaction, per tag / domain / mode, and an items x systems response matrix. |
| Template generator (`bench/generate.py`) | Works. Disjoint train (A) and test (B) universes, 4 domains, difficulty tags. |
| Training + ONNX export (`train/train.py`) | Run on Colab L4: DeBERTa-v3-small, 80k docs, 3 epochs, 64 min. Results: `bench/results/README.md`. |
| Domain definitions (`domains/*.json`) | Drafted for clinical, tax, legal, HR, education. Not reviewed by a lawyer. Not wired into the app. |
| LLM data pipeline (`bench/llm_generate.py`) | Written, never run. |
| Colab notebook (`train/colab.ipynb`) | Run end to end 2026-10-04 (as CLI scripts); three breakages fixed. |
| Any real model, any public benchmark | Phase 0 baseline measured (`bench/results/`). No public benchmark beyond Nemotron-PII yet. |

The one result so far that matters: the throwaway model reached 99.9% recall on the template test by
redacting 67% of ordinary text. Template data alone teaches "unfamiliar means identifier". Everything
below is shaped by that.

## Principles

1. **Leaks and over-redaction are reported together.** Recall alone is gameable.
2. **Train and test never share a source.** Different generator, different LLM, different name pools.
3. **A sealed test split exists per domain and is never looked at during development.** It is scored
   only at release points, and the count of times it has been scored is logged.
4. **Competitors run through the same scorer.** No number is published for us alone.
5. **Human-checked labels beat volume.** A few hundred verified documents anchor every claim.

## Phase 0: make the pipeline real (1 to 2 days)

Nothing here needs new code, only running what exists on a GPU.

- [x] Run `train/colab.ipynb` once. Fix whatever breaks. Likely spots: `prep_dataset.py` column names,
      DeBERTa ONNX export, the `fetch_model.py` baseline export. *(prep_dataset was fine; fetch_model
      rewritten without optimum; train.py export pinned to the TorchScript exporter.)*
- [~] Score the existing OpenMed model on Nemotron-PII test. It should land near its card's micro-F1
      of 0.954. If it is far below, the ONNX path or label mapping has a bug; stop and fix that first.
      *(Scotoma scorer: recall 97.3, precision 98.5. Independent PyTorch check on the full 100k test
      split: micro-F1 0.921 (0.914 with punctuation split). The card's 0.954 (stratified 2k) and
      test_results' 0.959 (~45k) come from OpenMed's unpublished split, so they are not comparable. ONNX matches PyTorch to 2e-5, so the
      export and mapping are taken as correct. See `bench/results/README.md`.)*
- [x] Score rules, OpenMed, and rules + OpenMed on the template test (universe B).
- [~] Record all three in `bench/results/` and commit them. This is the baseline everything else is
      measured against. *(Recorded; not committed: the folder is not a git repo and `bench/results/`
      is git-ignored.)*

**Exit:** a results table with a real model in it, and confidence the scorer is right.

## Phase 1: the benchmark (1 to 2 weeks, mostly data work)

The benchmark is the asset. Build it before training anything serious.

### 1a. Natural test documents

- [ ] Stand up one local LLM endpoint for **test** generation. Pick a model you will not use for
      training data. Write the choice down.
- [ ] Generate ~500 documents per domain with `bench/llm_generate.py`, across all eight styles.
- [ ] Measure the drop rate (malformed tags). If above ~30%, fix the prompt before generating more.

### 1b. Human verification

- [ ] Hand-check 200 documents per domain: every identifier tagged, nothing tagged that should not
      be. Budget about a minute per document.
- [ ] Record inter-annotator agreement on a 50-document overlap if a second person is available.
- [ ] Corrected documents become `bench/gold/<domain>.jsonl`. Split each 50/50 into `dev` and
      `sealed`. The sealed half is not opened again.

### 1c. Difficulty tags on LLM documents

LLM-written spans currently carry only the tag `llm`. Without tags there is no per-difficulty
breakdown on the data that matters most.

- [ ] Write `bench/tag.py`: derive tags mechanically after the fact (cue word within 28 characters,
      single token name, name in the common-word list, lower-case, digit-spaced, repeat mention).

### 1d. Item analysis

- [ ] Run at least five systems to get a usable response matrix: rules, OpenMed small, OpenMed large,
      Stanford de-identifier, OpenAI privacy-filter, Presidio. Add ours when it exists.
- [ ] Fit a 2PL model on `responses.csv`. Drop or rewrite items with near-zero discrimination.
      Report item difficulty by tag: this is the evidence that the tags mean something.
- [ ] Treat the threshold sweep as an ROC: report sensitivity (d') separately from criterion, so
      systems with different operating points can be compared.

### 1e. Real-data anchor (start now, it has lead time)

- [ ] Apply for the n2c2 / i2b2 2014 de-identification data use agreement.
- [ ] Write the XML to JSONL converter when the data arrives.
- [ ] Check that system rankings on the synthetic clinical set match rankings on i2b2. If they do
      not, the synthetic set is measuring something else and needs rework.

**Exit:** per-domain `dev` and `sealed` sets with verified labels, a response matrix across five or
more systems, and one real-data comparison for clinical.

## Phase 2: training data (about 1 week, overlaps Phase 1)

Three sources, mixed. The ratio is the main thing to tune.

| Source | Role | Risk |
|---|---|---|
| Open corpora (Nemotron-PII, ai4privacy) via `scotoma convert` | Natural background text, volume | Not domain-specific; label noise |
| LLM-written, per domain, **different model from the test generator** | Domain language and formats | Missed tags become training noise |
| Templates, universe A | Controlled hard cases: dictation, OCR, no-cue, rare formats | Causes over-redaction if it dominates |

- [ ] Generate 5k to 20k LLM documents per domain for training.
- [ ] Add hard negatives on purpose: documents with zero identifiers, eponyms (Graves, Bell, Wilson),
      statute and form numbers, scores and doses. These directly attack over-redaction.
- [ ] Build `train/mix.py`: assemble a training file from the three sources at a given ratio, with a
      manifest recording sources, seeds, generator models and counts. Every trained model points at
      its manifest.
- [ ] Start at roughly 60% open corpus, 30% LLM, 10% templates. Cap templates low.

**Exit:** a reproducible training set per domain, with a manifest.

## Phase 3: training (days per iteration; compute is cheap)

- [ ] **Baseline run:** `microsoft/deberta-v3-small`, 3 epochs, default settings, all domains pooled.
- [ ] **Backbone comparison:** DeBERTa-v3-small vs ModernBERT-base vs initialising from the OpenMed
      checkpoint with a new head. Same data, same seed.
- [ ] **One model or several:** pooled multi-domain model vs one per domain. Pooled is simpler to
      ship; per-domain may win on precision. Decide on `dev` numbers.
- [ ] **Recall lever:** sweep `--o-weight` (1.0, 0.7, 0.5) and the decode threshold together. Pick the
      operating point from the curve, not from a single run.
- [ ] **Quantisation check:** score fp32 and int8 on `dev`. If int8 costs more than about half a
      point of recall, ship fp16 or look at quantisation-aware options.
- [ ] Three seeds for any configuration that will be reported. Report the spread.

Selection rule, fixed in advance: among configurations with over-redaction under 1% on `dev`, pick
the lowest leak-document rate. Ties go to the smaller model.

**Exit:** one chosen configuration per domain (or one pooled), with dev numbers and seed variance.

## Phase 4: failure-driven iteration

Loop until the sealed-set budget says stop.

1. Score on `dev`. Read the misses list and the per-tag table.
2. Classify the misses: cluster (one pattern) or scatter.
3. Cluster: add a rule if the pattern is structural (a format, a checksum); add 1k to 3k targeted
   training examples if it is linguistic. Scatter: more natural data, or a larger backbone.
4. Retrain, rescore on `dev`, check over-redaction did not rise.

Rules and model are scored separately and together every time, so it stays clear which one is doing
the work.

## Phase 5: release gate

Run once per release candidate, on the sealed splits and i2b2.

| Check | Bar (proposed; set before looking) |
|---|---|
| Leak documents, rules + model, sealed, per domain | Lower than every baseline |
| Over-redaction, sealed | Under 1% |
| Recall on `no_cue`, `single_name`, `common_word_name` tags | Reported, and not worse than the best baseline |
| Clinical: i2b2 2014 | Reported next to published numbers |
| int8 vs fp32 | Within half a point of recall |
| Latency on the M3 Max | Reported: ms per 1,000 characters |

- [ ] Write a model card: training manifest, every number above, the baselines' numbers, known
      failure modes, the count of sealed-set evaluations.
- [ ] Publish the benchmark `dev` split and the scorer. Keep `sealed` private.

## Domain order

1. **Clinical.** Clearest rule set (Safe Harbor), a real benchmark exists, the app already works.
2. **Tax.** Identifiers are structured and checkable, so accuracy will be high and easy to show.
3. **HR.** Similar identifiers to tax; no single governing rule, so the claim is narrower.
4. **Legal.** Last. The sensitive content is often the facts, not the identifiers, so decide how the
   limits are described before building.
5. **Education.** Needs templates first; FERPA's "recognisable to classmates" limb is out of reach.

## Risks

| Risk | What to do about it |
|---|---|
| The model wins on our benchmark and loses on real text | i2b2 anchor; LLM test data from a model never used for training; ranking-agreement check in 1e |
| LLM label noise | Human-verified gold sets; drop malformed documents; measure drop rate |
| Over-redaction creeps up as recall is pushed | It is a selection constraint, not just a reported number |
| Sealed set leaks through repeated scoring | Log every sealed evaluation; rotate in a fresh sealed batch per major release |
| Benchmark gets trained on after publishing | Only `dev` is published |
| Domain definitions are wrong | Lawyer review before any compliance wording is used; they are a reading of the rules, not advice |
| Licences | Check each base model and each training corpus before shipping weights |

## Open decisions

- Which LLM generates test data, and which generates training data.
- One pooled model or one per domain.
- Whether baselines are run at their own default thresholds or tuned on `dev` (tuned is fairer and
  harder to beat).
- Who does the human verification, and whether a second annotator is available.
- The release bars in Phase 5.

## First three things to do

1. Run the Colab notebook and get one real number (Phase 0).
2. Submit the n2c2 data use agreement (lead time).
3. Pick the test-generation LLM and generate the first 500 clinical documents for verification.
