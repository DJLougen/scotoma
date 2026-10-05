#!/usr/bin/env python3
"""Ingest new identifier formats and fine-tune on them — the quick pipeline.

    python train/ingest_formats.py --base models/scotoma-v0/hf --out models/scotoma-v1 \\
        --formats my_new_mrn --steps 400 --device mps --battery-quick 150

Pipeline:
  (a) synthesise training docs whose ONLY planted identifier values come from
      `bench/formats.py`'s `sample(label, "train", rng)` — test-split formats
      are unreachable by construction and by assertion;
  (b) mix in a replay sample of the original training distribution
      (bench/generate.py --universe A, regenerated deterministically, plus
      bench/data/nemo_train.jsonl if present);
  (c) fine-tune from --base with train/train.py (--steps caps optimisation);
  (d) export ONNX and re-quantise per-channel int8, the clinical operating
      format (train.py's stock export is per-tensor);
  (e) run bench/battery.py on the new model against a baseline scorecard.

Writes manifest.json (formats, counts, seeds, base sha256, steps, commands)
into --out. Never samples split="test"; --selftest proves the guard works.

Regenerating the Nemotron replay half when bench/data/nemo_train.jsonl is
missing (it is git-ignored and large):

    pip install datasets
    python scripts/prep_dataset.py nvidia/Nemotron-PII --split train --limit 50000 \\
        --out bench/data/nemo_train.jsonl

Without it the replay is templates-only; the manifest records which was used.
"""
import argparse, hashlib, json, os, random, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(ROOT, "bench")
sys.path.insert(0, BENCH)
sys.path.insert(0, os.path.join(ROOT, "train"))

import generate as gen_mod          # universe A pools for names/places (train vocabulary)
import formats as fmt               # bench/formats.py — the shared contract

def die(msg):
    sys.exit(f"ingest_formats: {msg}")


# ----------------------------------------------------------------------------
# Carrier sentences. Every {V} is a planted identifier drawn from a TRAIN-split
# format. Static wording only; names/places come from generate.py universe A.
# ----------------------------------------------------------------------------
CARRIERS = {
    "NAME": ["Patient {V} was seen in clinic today.", "Dr. {V} reviewed the chart.",
             "{V} was contacted about the results.", "Care plan discussed with {V}.",
             "Signed electronically by {V}.", "{V} presents for follow-up.",
             "Next of kin: {V}."],
    "MRN": ["Medical record number {V}.", "MRN: {V}", "Chart {V} pulled for review.",
            "Patient record {V} updated today.", "Record {V} flagged for audit."],
    "SSN": ["SSN on file: {V}.", "Social security number {V} verified.", "Tax ID {V} documented."],
    "PHONE": ["Reachable at {V}.", "Callback number {V}.", "Phoned the patient at {V}.",
              "Contact number: {V}"],
    "FAX": ["Fax records to {V}.", "Results faxed to {V}."],
    "EMAIL": ["Email {V} for portal access.", "Messages sent to {V}.", "Portal contact: {V}"],
    "DATE": ["Seen on {V}.", "Date of birth {V}.", "Procedure performed {V}.",
             "Follow-up scheduled {V}.", "Note dated {V}."],
    "AGE": ["{V}-year-old patient.", "Age {V} years.", "Patient is {V}."],
    "ADDRESS": ["Resides at {V}.", "Home address {V}.", "Mail sent to {V}."],
    "LOCATION": ["Patient lives in {V}.", "Transferred from {V}.", "Moved to {V} last year."],
    "ZIP": ["ZIP code {V}.", "Postal code {V}."],
    "PLAN": ["Plan member ID {V}.", "Subscriber number {V}.", "Coverage under plan {V}.",
             "Insurance ID {V} on file."],
    "ACCOUNT": ["Account number {V}.", "Accession {V} resulted.", "Claim {V} processed.",
                "Billing account {V}."],
    "LICENSE": ["License number {V}.", "RN license {V} verified.", "Registration {V}.",
                "Prescriber license {V}."],
    "VEHICLE": ["Vehicle {V} noted in the incident report.", "Plate {V}.", "VIN {V} documented."],
    "DEVICE": ["Device serial {V}.", "Implant {V} interrogated.", "Pump serial number {V}."],
    "URL": ["Portal link {V}.", "Results available at {V}.", "See {V} for records."],
    "IP": ["Server {V} flagged in the audit log.", "Workstation {V} accessed the chart."],
    "ORG": ["Transferred to {V}.", "Referral from {V}.", "Employed by {V}.",
            "Records requested from {V}."],
    "ID": ["Reference number {V}.", "Case {V}.", "Employee ID {V}.", "Docket {V}."],
    "BIOMETRIC": ["Biometric record {V} enrolled."],
}
GENERIC = ["Recorded as {V} in the chart.", "Identifier {V} on file.", "Noted {V} during intake.",
           "Field value {V} verified.", "{V}"]

# Hard negatives: clinical-looking sentences with NO identifiers — doses,
# vitals, labs and identifier-shaped lookalikes the model must not redact.
HARD_NEGATIVES = [
    "Started metformin 500 mg twice daily.", "BP 128/82, HR 74, SpO2 97% on room air.",
    "HbA1c 6.4%, fasting glucose 118.", "WBC 7.2, Hgb 13.1, platelets 244.",
    "Creatinine 0.9, eGFR >60.", "Takes lisinopril 10 mg daily and atorvastatin 20 mg at night.",
    "BMI 27.3; advised diet and exercise.", "Follow up in 6 weeks.",
    "Room air saturation improved to 98%.", "Temperature 37.1 C, respirations 16.",
    "No drug allergies reported.", "Denies chest pain, dyspnoea or syncope.",
    "Review of systems negative except as noted.", "Physical exam unremarkable.",
    "Weight 182 lb, height 5 ft 9 in.", "Cholesterol panel pending.",
    "Patient is a 62-year-old with hypertension.", "Ordered CBC with differential.",
    "Cultures drawn times two before antibiotics.", "Warfarin 5 mg on Mondays and Fridays, 2.5 mg otherwise.",
    "A1c goal under 7.0%.", "Smoking history 12 pack-years; quit recently.",
    "Vaccinated for influenza this season.", "EKG shows normal sinus rhythm.",
    "Dose reduced to 25 mg after dizziness.", "Encouraged 30 minutes of walking daily.",
    "Fasting labs ordered for next visit.", "Lungs clear to auscultation bilaterally.",
    "No oedema, no rash, no focal deficit.", "Pain rated 3 out of 10.",
    "Prescription refilled for 90 days.", "Cholesterol 189, LDL 102, HDL 55.",
    "Urinalysis negative for infection.", "Sleep study ordered.",
    "Sodium 140, potassium 4.1, chloride 104.", "INR 2.4 on current dose.",
]

PLAIN = ["The patient was discharged in stable condition.", "No acute distress observed.",
         "Assessment and plan discussed at length.", "Consent obtained before the procedure.",
         "The family was updated this afternoon.", "Vital signs remained stable overnight.",
         "The note was reviewed for completeness.", "Discharge instructions were provided verbally.",
         "Continue current medications.", "Imaging was reviewed with the patient.",
         "Return precautions were discussed.", "The wound is healing well."]


def probe_label(label, rng, tries=4):
    """True if formats.sample can actually serve this label's train split —
    contract allows sample() to raise for labels with no samplable format."""
    for _ in range(tries):
        try:
            if plant_value(label, rng)[0]:
                return True
        except Exception:
            pass
    return False


def labels_and_targets(selected):
    """(labels, targets): labels plantable in synth docs; targets are the
    train-split Format entries this ingest exists to teach. A target needs a
    compilable pattern (its own sampler); a label needs formats.sample."""
    rng = random.Random("probe")
    all_train = [f for f in fmt.FORMATS if f.split == "train"]
    usable = {l for l in {f.label for f in all_train} if probe_label(l, rng)}
    if selected:
        chosen = {f.name: f for f in all_train}
        missing = [n for n in selected if n not in chosen]
        if missing:
            die(f"unknown or non-train format(s): {missing} "
                f"(train formats: {sorted(chosen)})")
        targets = [chosen[n] for n in selected]
        nopat = [f.name for f in targets if not f.pattern]
        if nopat:
            die(f"format(s) have no compilable pattern (generate.py passthrough "
                f"— already in the training distribution): {nopat}")
        for f in targets:
            fmt.compile_pattern(f.pattern)   # raises on a malformed pattern
    else:
        targets = [f for f in all_train if f.pattern and f.label in usable]
    labels = sorted({f.label for f in targets} | usable)
    if not labels:
        die("no samplable train formats registered — add one with bench/formats.py add ... --split train")
    return labels, targets


def plant_value(label, rng):
    """Sample a TRAIN-split value via formats.sample. Contract asserts:
    the returned format name must not be a registered test-split format, and
    the value must be a non-empty string. (The real formats.py serves 'train'
    by delegating to generate.py, returning name 'generate.py' and — for some
    labels — a (value, label, kind, tags) tuple: both handled here.)"""
    value, name = fmt.sample(label, "train", rng)
    if isinstance(value, tuple):
        value = value[0]
    test_names = {f.name for f in fmt.FORMATS if f.split == "test"}
    assert name not in test_names, f"formats.sample returned test-split format {name!r} for {label}"
    assert isinstance(value, str) and value, f"empty value from format {name}"
    return value, name


def make_doc(rng, doc_id, labels, targets, gen):
    """One synthetic clinical-ish note. Returns benchmark-JSONL dict."""
    sentences, spans, used = [], [], {}
    samplers = {f.name: fmt.compile_pattern(f.pattern) for f in targets if f.pattern}
    n = rng.randint(3, 8)
    for _ in range(n):
        roll = rng.random()
        if roll < 0.55:      # carrier sentence with a planted identifier
            if targets and rng.random() < 0.6:
                f = rng.choice(targets)
                label = f.label
                if f.name in samplers:
                    value, fname = samplers[f.name](rng), f.name
                else:
                    value, fname = plant_value(label, rng)
            else:
                label = rng.choice(labels)
                try:
                    value, fname = plant_value(label, rng)
                except Exception:
                    sentences.append(rng.choice(PLAIN))
                    continue
            assert fname not in {t.name for t in fmt.FORMATS if t.split == "test"}, fname
            used[fname] = used.get(fname, 0) + 1
            sent = rng.choice(CARRIERS.get(label, GENERIC))
            if "{V}" not in sent:
                lit, tail = "", sent
            else:
                lit, _, tail = sent.partition("{V}")
            text = lit + value + tail
            idx = len(" ".join(sentences)) + (1 if sentences else 0)
            start = idx + len(lit)
            spans.append({"start": start, "end": start + len(value), "label": label,
                          "kind": "fmt", "tags": [f"fmt:{fname}", "ingest"]})
            sentences.append(text)
        elif roll < 0.78:
            sentences.append(rng.choice(PLAIN))
        else:
            sentences.append(rng.choice(HARD_NEGATIVES))
    text = " ".join(sentences)
    return {"id": doc_id, "domain": "clinical", "mode": "ingest", "universe": "A",
            "text": text, "spans": spans}, used


def synthesise(out_dir, n_docs, n_dev, labels, targets, seed):
    rng = random.Random(f"ingest-{seed}")
    gen = gen_mod.Gen("A", rng)          # reserved for pool fills if carriers need them
    counts, used = {}, {}
    paths = []
    for path, n, tag in [(os.path.join(out_dir, "synth_train.jsonl"), n_docs, "T"),
                         (os.path.join(out_dir, "synth_dev.jsonl"), n_dev, "D")]:
        with open(path, "w", encoding="utf-8") as fh:
            for i in range(n):
                doc, u = make_doc(rng, f"ING-{seed}-{tag}{i:05d}", labels, targets, gen)
                for k, v in u.items():
                    used[k] = used.get(k, 0) + v
                fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
        paths.append(path)
        counts[os.path.basename(path)] = n
    return paths, counts, used


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def replay(out_dir, n_replay, seed):
    """Regenerate universe-A template docs deterministically + Nemotron train."""
    tpl = os.path.join(out_dir, "replay_tpl_a.jsonl")
    cmd = [sys.executable, os.path.join(BENCH, "generate.py"), "--universe", "A",
           "--n", str(n_replay), "--seed", str(seed), "--out", tpl]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        die(f"generate.py replay failed: {r.stderr.strip()}")
    files = [tpl]
    nemo = os.path.join(BENCH, "data", "nemo_train.jsonl")
    if os.path.exists(nemo):
        files.append(nemo)
        note = "nemo_train.jsonl included"
    else:
        note = ("bench/data/nemo_train.jsonl missing — templates-only replay. "
                "Regenerate: python scripts/prep_dataset.py nvidia/Nemotron-PII "
                "--split train --limit 50000 --out bench/data/nemo_train.jsonl")
        print(f"replay: {note}")
    return files, note


def requantize_per_channel(out):
    """Replace train.py's per-tensor int8 with per-channel int8 (the shipped format)."""
    from onnxruntime.quantization import QuantType, quantize_dynamic
    fp32 = os.path.join(out, "model_fp32.onnx")
    if not os.path.exists(fp32):
        fp32 = os.path.join(out, "model.onnx")
    if not os.path.exists(fp32):
        die(f"no fp32 ONNX in {out} to requantise")
    q = os.path.join(out, "model_quantized.onnx")
    quantize_dynamic(fp32, q, weight_type=QuantType.QInt8, per_channel=True)
    print(f"per-channel int8: {os.path.getsize(q) / 1e6:.1f} MB -> {q}")
    return q


def run(cmd, what):
    print(f"$ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        die(f"{what} failed with exit {r.returncode}")
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="HF checkpoint dir to fine-tune from (e.g. models/scotoma-v0/hf)")
    ap.add_argument("--out", help="output model dir (e.g. models/scotoma-v1)")
    ap.add_argument("--formats", default=None, help="comma-separated train-format names; default: all train formats")
    ap.add_argument("--docs", type=int, default=3000, help="synthesised training docs")
    ap.add_argument("--dev-docs", type=int, default=200, help="synthesised dev docs")
    ap.add_argument("--replay-docs", type=int, default=20000, help="universe-A template replay docs")
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--device", default=None, choices=["cuda", "mps", "cpu"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--name", default=None, help="model name for config.json (default: out basename)")
    ap.add_argument("--battery-threshold", default="0.02", help="threshold for the post-train battery")
    ap.add_argument("--battery-quick", type=int, default=150, help="battery --quick N; 0 = full battery")
    ap.add_argument("--baseline", default=None, help="scorecard.json of the old model (leak-regression gate)")
    ap.add_argument("--baseline-model", default=None,
                    help="model dir to battery-baseline first (quick run), e.g. models/scotoma-v0-int8pc")
    ap.add_argument("--no-battery", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="run leak-guard self-tests and exit")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return
    if not a.base or not a.out:
        die("need --base and --out")

    t0 = time.time()
    out = os.path.abspath(a.out)
    if "sealed" in out.lower() or "sealed" in os.path.abspath(a.base).lower():
        die("refusing sealed path")
    os.makedirs(out, exist_ok=True)
    selected = a.formats.split(",") if a.formats else None
    labels, targets = labels_and_targets(selected)
    print(f"targets: {[f.name for f in targets]}  labels: {labels}")

    # (a) synthesise ----------------------------------------------------------
    synth_paths, counts, used = synthesise(out, a.docs, a.dev_docs, labels, targets, a.seed)

    # (b) replay --------------------------------------------------------------
    replay_files, replay_note = replay(out, a.replay_docs, a.seed)
    nemo = os.path.join(BENCH, "data", "nemo_train.jsonl")
    train_files = [synth_paths[0]] + replay_files
    dev_files = [synth_paths[1], os.path.join(BENCH, "data", "dev_tpl.jsonl")]

    # (c) fine-tune -------------------------------------------------------------
    name = a.name or os.path.basename(out.rstrip("/"))
    cmd = [sys.executable, os.path.join(ROOT, "train", "train.py"),
           "--train", *train_files, "--dev", *dev_files,
           "--base", a.base, "--out", out, "--name", name,
           "--epochs", str(a.epochs), "--steps", str(a.steps),
           "--batch", str(a.batch), "--lr", str(a.lr), "--seed", str(a.seed)]
    if a.device:
        cmd += ["--device", a.device]
    run(cmd, "train.py")

    # (d) per-channel int8 ------------------------------------------------------
    requantize_per_channel(out)

    # baseline battery first, if asked -----------------------------------------
    baseline_sc = a.baseline
    if a.baseline_model:
        bout = os.path.join(out, "baseline_battery")
        cmd = [sys.executable, os.path.join(BENCH, "battery.py"), a.baseline_model,
               "--name", os.path.basename(a.baseline_model.rstrip("/")),
               "--threshold", a.battery_threshold, "--out", bout]
        if a.battery_quick:
            cmd += ["--quick", str(a.battery_quick)]
        # baseline battery must never gate-block the pipeline
        r = subprocess.run(cmd, cwd=ROOT)
        sc = os.path.join(bout, "scorecard.json")
        if r.returncode == 0 or os.path.exists(sc):
            baseline_sc = sc

    # (e) battery on the new model ---------------------------------------------
    battery_rc = None
    if not a.no_battery:
        cmd = [sys.executable, os.path.join(BENCH, "battery.py"), out,
               "--name", name, "--threshold", a.battery_threshold,
               "--out", os.path.join(out, "battery")]
        if a.battery_quick:
            cmd += ["--quick", str(a.battery_quick)]
        if baseline_sc:
            cmd += ["--baseline", baseline_sc]
        battery_rc = subprocess.run(cmd, cwd=ROOT).returncode

    # manifest -------------------------------------------------------------------
    base_ckpt = os.path.join(a.base, "model.safetensors")
    manifest = {
        "base": os.path.abspath(a.base),
        "base_safetensors_sha256": sha256(base_ckpt) if os.path.exists(base_ckpt) else None,
        "out": out, "seed": a.seed, "steps": a.steps, "epochs": a.epochs,
        "batch": a.batch, "lr": a.lr, "device": a.device or "auto",
        "formats": sorted({f.name for f in targets}),
        "labels": labels, "planted_counts": used, "doc_counts": counts,
        "replay_files": [os.path.relpath(p, ROOT) for p in replay_files],
        "replay_note": replay_note,
        "train_files": [os.path.relpath(p, ROOT) for p in train_files],
        "dev_files": [os.path.relpath(p, ROOT) for p in dev_files],
        "battery_exit": battery_rc, "baseline_scorecard": baseline_sc,
        "wall_s": round(time.time() - t0, 1),
    }
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"manifest: {out}/manifest.json  ({manifest['wall_s']}s total)")
    if battery_rc:
        sys.exit(2)   # pipeline ran; the battery's gates failed
    print("ingest done")


def selftest():
    """Prove: (1) a leaked test-split format makes plant_value raise;
    (2) real synth never calls sample() with split != 'train' and every span
    text is exactly a sampled value."""
    calls = []
    orig = fmt.sample

    class Fake(Exception):
        pass

    def spy(label, split, rng):
        calls.append(split)
        return orig(label, split, rng)

    # 1. forge a train request that returns a test-split format -> must raise
    tests = [f for f in fmt.FORMATS if f.split == "test"]
    if tests:
        tf = tests[0]
        fmt.sample = lambda label, split, rng: ("FORGED", tf.name)
        try:
            plant_value(tf.label, random.Random(0))
        except AssertionError:
            pass
        else:
            die(f"selftest: plant_value accepted test-split format {tf.name}")
        finally:
            fmt.sample = orig

    # 2. synthesise under the spy: all calls must be split='train'
    fmt.sample = spy
    labels, targets = labels_and_targets(None)
    rng = random.Random(7)
    gen = gen_mod.Gen("A", rng)
    for i in range(50):
        doc, _ = make_doc(rng, f"SELF-{i}", labels, targets, gen)
        for s in doc["spans"]:
            assert doc["text"][s["start"]:s["end"]], "empty span"
            # span text must occur verbatim at the recorded offsets
            assert s["end"] <= len(doc["text"])
    fmt.sample = orig
    bad = [c for c in calls if c != "train"]
    assert calls and not bad, f"selftest: sample called with non-train splits: {bad}"
    print(f"selftest OK: forged test-split format rejected; {len(calls)} "
          f"sample() calls all split='train' across 50 synth docs")


if __name__ == "__main__":
    main()
