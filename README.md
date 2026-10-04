# Scotoma

A clipboard scrubber for patient information. Copy part of a note, press a hotkey, check what was
caught, paste. Then paste the model's answer back and have the real names put back in.

It is a thin shell around two detectors: a deterministic rules engine for structured identifiers and
any Hugging Face token-classification PII model exported to ONNX. The app makes no network
connections, with one opt-in exception: a speech server on the same machine (loopback only).

## What it does differently

| | |
|---|---|
| **Review before paste** | The hotkey opens a side-by-side view. Click a highlight to keep it in, select text to redact something that was missed. Sub-threshold model hits are shown dashed as "possible" instead of being silently dropped. Nothing reaches the clipboard until you approve (or turn review off for one-keystroke use). |
| **Reversible** | `[NAME_1]`, `[DATE_2:2024]` tags, or realistic stand-ins (consistent fake names, 555-01xx phone numbers, dates shifted by one per-session offset so intervals survive). A second hotkey restores originals in whatever is on the clipboard. The map lives in memory only, is zeroed on quit, on "forget", and after 30 idle minutes. |
| **Safe Harbor details** | Dates keep only the year; a birth year implying age 90+ is dropped; ages over 89 become `90+`; ZIP keeps three digits, and the 17 sparse ZIP3 prefixes become `000`. |
| **Name propagation** | Once "Eleanor Whitfield" is found, bare "Whitfield" and "Karen Whitfield" further down are caught too. |
| **Recall-leaning decode** | Per-token identifier probability is summed over B-/I- variants and thresholded (default 0.35), rather than argmax. Long notes run in overlapping windows; nothing is truncated. |
| **Measured** | `scotoma eval` scores the exact shipped pipeline per identifier type, and `scotoma sweep` shows recall against precision by threshold. |
| **Swappable model** | Labels are mapped by keyword, so most HF PII models work by dropping a folder in. |

## Layout

```
crates/core   detection, merge, redaction, vault, benchmark   (no network code)
crates/cli    scotoma scrub | eval | sweep
app/          Tauri 2 desktop app: tray, global hotkeys, review window (plain HTML/JS)
scripts/      fetch_model.py, prep_dataset.py, markup_to_jsonl.py, make_toy_model.py
eval/         fixtures/clinical_smoke.{markup,jsonl}
```

## Build

Needs Rust and Node. On Linux also the Tauri system packages (`libwebkit2gtk-4.1-dev`,
`libayatana-appindicator3-dev`, `librsvg2-dev`, `libxdo-dev`).

```sh
pip install torch "transformers>=4.57,<5" onnx onnxruntime
python scripts/fetch_model.py          # exports + int8-quantises the default model into app/src-tauri/models/default
cd app && npm install
npm run dev                            # or: npm run build   → installers in target/release/bundle
```

Without a model folder the app runs on rules alone and says so in the header.

Hotkeys: `Ctrl/⌘+Alt+S` clean selection or clipboard, `Ctrl/⌘+Alt+R` restore originals,
`Ctrl/⌘+Alt+N` blank note. All are also in the tray menu.

## Inputs (macOS overlay)

The window is a floating overlay: it appears over whatever you are doing, `esc` hides it, and it
hides itself after **Copy cleaned text** so the paste lands where you were.

| Input | Trigger | How the text is obtained |
|---|---|---|
| Selected text | `⌘⌥S` | Accessibility API; falls back to pressing ⌘C for you and then restoring your clipboard |
| Clipboard text or screenshot | `⌘⌥S` with nothing selected | Clipboard; an image is read with on-device OCR |
| Screen region | `⌘⌥D` or **Capture** | Native crosshair → clipboard → Apple Vision OCR |
| Voice, your model | `⌘⌥V` to start, again to stop, or **Dictate** | Records 16 kHz mono WAV, sends it to your speech model |
| Voice, Superwhisper | `⌘⌥N`, then dictate | Opens the overlay empty and focused; anything that types into a field lands in it |

**Speech model.** Set it in the side panel. Fastest is a server that keeps the model loaded:
`http://127.0.0.1:8080/inference` (whisper.cpp `whisper-server`) or any OpenAI-style
`/v1/audio/transcriptions` endpoint (add `#model=NAME` if it needs one). Only loopback addresses are
accepted. Alternatively give a shell command that prints the transcript, with `{audio}` for the file,
for example `whisper-cli -m ~/models/ggml-large-v3-turbo.bin -nt -np -f {audio}`; that reloads the
model on every utterance. The recording is the one thing that touches disk (a temp file, deleted
straight after transcription). The speech server connection is the only socket the app ever opens.

If you dictate with Superwhisper, use one of its local voice models with no cloud post-processing
mode: otherwise the audio has left the machine before Scotoma sees a word.

**Latency.** The footer of the left pane shows where the time went for each input, for example
`screen · read 240 ms · detect 35 ms`. The detection model is warmed at startup.

**Permissions** (System Settings → Privacy & Security): Screen Recording for capture, Accessibility
for reading the selection, Microphone for dictation. The app does not listen to the keyboard; it
only registers its own hotkeys, so no Input Monitoring permission is needed. When
launched with `npm run dev` the prompts name your terminal app rather than Scotoma.

Captured and dictated text always opens in review. The helper is `app/src-tauri/helper/main.swift`,
compiled by the build (needs the Xcode command line tools). Not available on Windows or Linux yet.

## Models

| Model | Licence | Notes |
|---|---|---|
| `OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1` (default) | Apache-2.0 | DeBERTa-v3-small, 54 entity types. Card reports micro-F1 0.954 on a 2,000-sample Nemotron-PII test split. The fp32 file is 566 MB because of the 128k-token embedding table; int8 should land near a quarter of that. |
| `StanfordAIMI/stanford-deidentifier-base` | MIT | PubMedBERT, trained on real radiology reports + i2b2. |
| `obi/deid_roberta_i2b2` | MIT | RoBERTa trained on i2b2 2014. |
| `openai/privacy-filter` | Apache-2.0 | 8 coarse classes, strong but the smallest ONNX variant is about 810 MB. |

## Benchmark and training

```
domains/    what each field's regulations name as identifying (clinical, tax, legal, hr, education)
bench/      generate.py (templates), llm_generate.py (LLM-written), run.py (compare systems)
train/      train.py (fine-tune + ONNX export), colab.ipynb
```

```sh
python bench/generate.py --universe B --n 1500 --seed 1 --out bench/data/test.jsonl     # test
python bench/generate.py --universe A --n 30000 --seed 7 --out bench/data/train.jsonl   # train
python train/train.py --train bench/data/train.jsonl --dev bench/data/dev.jsonl --out models/v0
python bench/run.py bench/data/test.jsonl --strict --system rules --system ours=models/v0 --system rules+ours=models/v0
cargo run --release -p scotoma -- eval eval/fixtures/clinical_smoke.jsonl --no-model
```

**Design.** Universe A (train) and B (test) share no names, places, organisations, sentence templates
or background sentences. Every identifier carries difficulty tags (`no_cue`, `single_name`,
`common_word_name`, `relative`, `repeat`, `spoken`, `ocr`, `chat`, `fmt:*`), and results are reported
per tag, per domain and per input mode. `run.py` scores any ONNX token classifier through the same
code and writes `responses.csv` (items x systems; 0 missed, 1 partial, 2 full) for IRT.

**Metrics.** Recall (identifier touched), full redaction, leak documents (at least one identifier
untouched), and over-redaction: the share of ordinary text redacted by mistake. Report the last two
together. A system that blacks out everything has perfect recall.

### What has and has not been measured

| System | Test set | Recall | Leak docs | Over-redaction |
|---|---|---|---|---|
| Rules only | `clinical_smoke` (18 notes, written alongside the rules) | 86.7% | 9 / 18 | n/a |
| Rules only | Templates, universe B, 1,500 docs, strict | 52.9% | 97.7% | 0.1% |
| Tiny smoke-test model (1.1M params, from scratch, CPU, 90 s) | same | 99.9% | 0.7% | **67.0%** |

The third row is the important one. The tiny model "wins" on recall by redacting two thirds of
ordinary text: trained only on templates, it learned that anything unfamiliar is an identifier.
That is why over-redaction is in the table, and why template data alone cannot train or rank a real
model. A pretrained backbone plus natural text (an open corpus, LLM-written documents) is required.

Since then (2026-10-04, Colab L4): the default OpenMed model and a DeBERTa-v3-small trained with
`train.py` on templates plus Nemotron-PII have been scored on the template test and on Nemotron-PII.
Trained this way, the model's over-redaction falls to 0.5%. Numbers, setup and caveats:
[`bench/results/README.md`](bench/results/README.md). Still not measured: ai4privacy, i2b2, and
LLM-written test documents. `bench/llm_generate.py` has not been run.

### Claiming a win honestly

A model trained on universe A and tested on universe B is still being tested on its own generator's
style. To claim it beats another model: test on documents from a different source than anything it
trained on (a different LLM, a held-out open corpus, i2b2), run the competitors through `run.py`,
and have a person verify a sample of the labels.

The domain policy files are a reading of the cited regulations, not legal advice, and are not yet
wired into the app: the app applies Safe Harbor treatment and a strict toggle regardless of domain.

## Tested / untested

Tested on Linux (Ubuntu 24.04, virtual display): unit tests, the ONNX path end to end with the toy
model, and the real app driven through hotkey → review → toggle → manual redaction → copy → restore.

Not tested: macOS and Windows builds, tray behaviour and notifications on those platforms, the
default `ort` static-link path (the Linux check linked ONNX Runtime dynamically), and the Swift
capture helper (the Rust side of capture was tested on Linux with a stand-in helper).
`fetch_model.py`, `prep_dataset.py` and `train.py` have now run on Colab, and `fetch_model.py` also on macOS.

## Limits

It can miss things. Rules cover formats, the model covers language, and neither reads minds: a
rare-disease mention or "the mayor's wife" identifies someone without containing an identifier.
Stand-in restore only works where the stand-in survives verbatim in the reply; tags are sturdier.
Read the right-hand pane before pasting.
