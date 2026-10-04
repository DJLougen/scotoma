#!/usr/bin/env python3
"""Turn non-HF-token-classifier systems into C1 prediction files for `scotoma eval`.

    python bench/predict_external.py presidio bench/data/nemo_test.jsonl --out preds/presidio.jsonl --limit 50
    python bench/predict_external.py openai-privacy-filter bench/data/nemo_test.jsonl --out preds/opf.jsonl
    python bench/predict_external.py --selftest

Every output line is {"id": <doc id or null>, "text": <exact doc text>,
"spans": [{"start","end","label"}]} with character offsets, one line per input
line in order. All emitted labels are Scotoma labels, so the scorer's
labels::map_label is only a backstop.

SYSTEMS

presidio — presidio-analyzer AnalyzerEngine with its default recognizers on the
spaCy en_core_web_lg model (--spacy-model to override). Presidio entity types
are translated to Scotoma labels (checked against crates/core/src/labels.rs
map_label; we emit the Scotoma label directly for every span):

    NAME:      PERSON
    PHONE:     PHONE_NUMBER
    EMAIL:     EMAIL, EMAIL_ADDRESS
    SSN:       US_SSN
    DATE:      DATE_TIME
    AGE:       AGE
    LOCATION:  LOCATION, GPE, FAC, FACILITY
    ORG:       NRP, NORP, ORG, ORGANIZATION          (quasi: strict mode only)
    DEVICE:    MAC_ADDRESS
    ACCOUNT:   CREDIT_CARD, IBAN_CODE, US_BANK_NUMBER, ABA_ROUTING_NUMBER, CRYPTO
    LICENSE:   MEDICAL_LICENSE, US_DRIVER_LICENSE, IT_DRIVER_LICENSE
    ID:        ID, US_PASSPORT, US_ITIN, SG_NRIC_FIN, SG_FIN, UK_NINO, IN_PAN,
               IN_AADHAAR, IN_VOTER, IN_PASSPORT, ES_NIF, ES_NIE, IT_FISCAL_CODE,
               IT_VAT_CODE, IT_PASSPORT, IT_IDENTITY_CARD, PL_PESEL,
               FI_PERSONAL_IDENTITY_CODE, KR_RRN, AU_ABN, AU_ACN, AU_TFN
    IP:        IP_ADDRESS
    URL:       URL
    VEHICLE:   IN_VEHICLE_REGISTRATION
    MRN:       UK_NHS
    PLAN:      AU_MEDICARE
    anything else            skipped, counted, reported on stderr

openai-privacy-filter — openai/privacy-filter (model_type openai_privacy_filter,
needs transformers >= 5.6; no remote code on the repo). Follows the documented
decode path from the card and github.com/openai/privacy-filter opf/_core:
log_softmax over the 33 BIOES logits -> constrained Viterbi with the six
transition biases from viterbi_calibration.json (operating point "default")
    -> BIOES spans -> char offsets via the tokenizer's offset mapping.
    account_number   ACCOUNT   private_address  ADDRESS   private_date  DATE
    private_email    EMAIL     private_person   NAME      private_phone PHONE
    private_url      URL       secret           ID

Colab installs:
    pip install presidio-analyzer && python -m spacy download en_core_web_lg
    pip install -U "transformers>=5.6" torch accelerate   # then --model openai/privacy-filter (~3 GB)
"""
import argparse, json, sys
from collections import Counter

# Presidio entity type -> Scotoma label. Exhaustive for the default
# recognizer set shipped with presidio-analyzer (SpacyRecognizer plus the
# global and en pattern recognizers); unknown types are skipped and reported.
PRESIDIO_MAP = {
    "PERSON": "NAME", "PHONE_NUMBER": "PHONE", "EMAIL_ADDRESS": "EMAIL",
    "EMAIL": "EMAIL",
    "US_SSN": "SSN", "DATE_TIME": "DATE", "AGE": "AGE", "LOCATION": "LOCATION",
    "GPE": "LOCATION", "FAC": "LOCATION", "FACILITY": "LOCATION",
    "NRP": "ORG", "NORP": "ORG", "ORG": "ORG", "ORGANIZATION": "ORG",
    "MAC_ADDRESS": "DEVICE", "ID": "ID",
    "CREDIT_CARD": "ACCOUNT", "IBAN_CODE": "ACCOUNT", "US_BANK_NUMBER": "ACCOUNT",
    "ABA_ROUTING_NUMBER": "ACCOUNT", "CRYPTO": "ACCOUNT",
    "MEDICAL_LICENSE": "LICENSE", "US_DRIVER_LICENSE": "LICENSE",
    "IT_DRIVER_LICENSE": "LICENSE",
    "US_PASSPORT": "ID", "US_ITIN": "ID", "SG_NRIC_FIN": "ID", "SG_FIN": "ID",
    "UK_NINO": "ID", "IN_PAN": "ID", "IN_AADHAAR": "ID", "IN_VOTER": "ID",
    "IN_PASSPORT": "ID", "ES_NIF": "ID", "ES_NIE": "ID", "IT_FISCAL_CODE": "ID",
    "IT_VAT_CODE": "ID", "IT_PASSPORT": "ID", "IT_IDENTITY_CARD": "ID",
    "PL_PESEL": "ID", "FI_PERSONAL_IDENTITY_CODE": "ID", "KR_RRN": "ID",
    "AU_ABN": "ID", "AU_ACN": "ID", "AU_TFN": "ID",
    "IP_ADDRESS": "IP", "URL": "URL",
    "IN_VEHICLE_REGISTRATION": "VEHICLE",
    "UK_NHS": "MRN", "AU_MEDICARE": "PLAN",
}

# openai/privacy-filter span category -> Scotoma label.
PRIVACY_FILTER_MAP = {
    "account_number": "ACCOUNT", "private_address": "ADDRESS",
    "private_date": "DATE", "private_email": "EMAIL", "private_person": "NAME",
    "private_phone": "PHONE", "private_url": "URL", "secret": "ID",
}

VITERBI_BIAS_KEYS = (
    "transition_bias_background_stay", "transition_bias_background_to_start",
    "transition_bias_inside_to_continue", "transition_bias_inside_to_end",
    "transition_bias_end_to_background", "transition_bias_end_to_start",
)
NEG_INF = -1e9


def trim(text, start, end):
    """Shrink a char span so its text has no leading/trailing whitespace."""
    while end > start and text[end - 1].isspace(): end -= 1
    while start < end and text[start].isspace(): start += 1
    return start, end


def build_tables(id2label):
    """CRF start/end/transition masks for a BIOES label space.

    Mirrors opf/_core/decoding.py ViterbiCRFDecoder from openai/privacy-filter:
    start allows O/B/S, end allows O/E/S; from O or a closed span (E/S) you may
    go to O/B/S; from B/I you may only continue I/E of the same span label.
    Returns (id -> (tag, span), start, end, transitions[num][num]).
    """
    n = len(id2label)
    tag_of, span_of = {}, {}
    for i in range(n):
        name = id2label[i]
        if name == "O":
            tag_of[i], span_of[i] = "O", "O"
        else:
            tag, _, span = name.partition("-")
            tag_of[i], span_of[i] = tag, span
    start = [0.0 if tag_of[i] in ("O", "B", "S") else NEG_INF for i in range(n)]
    end = [0.0 if tag_of[i] in ("O", "E", "S") else NEG_INF for i in range(n)]
    trans = [[NEG_INF] * n for _ in range(n)]
    for p in range(n):
        for q in range(n):
            pt, ps, qt, qs = tag_of[p], span_of[p], tag_of[q], span_of[q]
            if pt in ("O", "E", "S"):
                ok = qt in ("O", "B", "S")
            else:  # B or I must continue the same span
                ok = qs == ps and qt in ("I", "E")
            if ok:
                trans[p][q] = 0.0
    return tag_of, span_of, start, end, trans


def add_biases(tag_of, trans, biases):
    """Add the six calibrated transition biases onto the valid-edge table."""
    for p in range(len(trans)):
        for q in range(len(trans)):
            if trans[p][q] <= NEG_INF / 2: continue
            pt, qt = tag_of[p], tag_of[q]
            if pt == "O":
                b = biases["transition_bias_background_stay"] if qt == "O" \
                    else biases["transition_bias_background_to_start"]
            elif pt in ("B", "I"):
                b = biases["transition_bias_inside_to_continue"] if qt == "I" \
                    else biases["transition_bias_inside_to_end"]
            else:  # E or S
                b = biases["transition_bias_end_to_background"] if qt == "O" \
                    else biases["transition_bias_end_to_start"]
            trans[p][q] += b


def viterbi(logprobs, id2label, biases=None):
    """Constrained Viterbi over [seq][num_classes] log-probs; returns label ids.

    Pure-Python port of the reference decode() (minus CUDA batching): same
    start/end/transition masks, same biases, same argmax fallback when no legal
    path is finite. `biases` is a dict over VITERBI_BIAS_KEYS; None = zeros.
    """
    tag_of, _, start, end, trans = build_tables(id2label)
    if biases:
        add_biases(tag_of, trans, {k: biases.get(k, 0.0) for k in VITERBI_BIAS_KEYS})
    seq = len(logprobs)
    if seq == 0: return []
    scores = [logprobs[0][i] + start[i] for i in range(len(id2label))]
    back = []
    for t in range(1, seq):
        best_s, best_p = [NEG_INF] * len(id2label), [0] * len(id2label)
        for q in range(len(id2label)):
            for p in range(len(id2label)):
                v = scores[p] + trans[p][q]
                if v > best_s[q]:
                    best_s[q], best_p[q] = v, p
            best_s[q] += logprobs[t][q]
        back.append(best_p)
        scores = best_s
    if all(s <= NEG_INF / 2 for s in scores):
        return [max(range(len(id2label)), key=lambda i: logprobs[t][i]) for t in range(seq)]
    scores = [scores[i] + end[i] for i in range(len(id2label))]
    last = max(range(len(id2label)), key=lambda i: scores[i])
    path = [0] * seq
    path[-1] = last
    for t in range(seq - 2, -1, -1):
        last = back[t][last]
        path[t] = last
    return path


def bioes_spans(path, id2label, offsets):
    """Turn a decoded label-id path into character spans.

    Tolerant like the reference labels_to_spans: B begins, I/E continue the same
    span, S is a singleton; malformed leftovers still emit a span.
    """
    spans, cur, cur_start = [], None, None
    for i, lid in enumerate(path):
        name = id2label[lid]
        if name == "O":
            if cur is not None: spans.append((cur_start, i, cur)); cur = None
            continue
        tag, _, span = name.partition("-")
        if tag == "S":
            if cur is not None: spans.append((cur_start, i, cur))
            spans.append((i, i + 1, span)); cur = None
        elif tag == "B" or (tag in ("I", "E") and cur != span):
            if cur is not None: spans.append((cur_start, i, cur))
            if tag == "E":
                spans.append((i, i + 1, span)); cur = None
            else:
                cur, cur_start = span, i
        elif tag == "E" and cur == span:
            spans.append((cur_start, i + 1, cur)); cur = None
        # I continuing the same span: just extend
    if cur is not None: spans.append((cur_start, len(path), cur))
    out = []
    for s, e, label in spans:
        cs = offsets[s][0] if s < len(offsets) else None
        ce = offsets[e - 1][1] if 0 < e <= len(offsets) else None
        if cs is not None and ce is not None and ce > cs:
            out.append({"start": cs, "end": ce, "label": label})
    return out


def run_presidio(docs, a):
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
    except ImportError:
        sys.exit("pip install presidio-analyzer && python -m spacy download " + a.spacy_model)
    nlp = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": a.spacy_model}],
    }).create_engine()
    engine = AnalyzerEngine(nlp_engine=nlp)
    skipped = Counter()
    for i, d in enumerate(docs):
        spans = []
        for r in engine.analyze(text=d["text"], language="en"):
            label = PRESIDIO_MAP.get(r.entity_type)
            if label is None:
                skipped[r.entity_type] += 1
                continue
            s, e = trim(d["text"], r.start, r.end)
            if e > s: spans.append({"start": s, "end": e, "label": label})
        d["_pred"] = sorted(spans, key=lambda s: s["start"])
        if (i + 1) % 100 == 0: print(f"presidio: {i + 1}/{len(docs)}", file=sys.stderr, flush=True)
    if skipped:
        print("presidio types with no Scotoma mapping (skipped): " + ", ".join(f"{k}x{v}" for k, v in skipped.most_common()), file=sys.stderr)


def run_privacy_filter(docs, a):
    try:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer
    except ImportError:
        sys.exit("pip install -U 'transformers>=5.6' torch")
    try:
        tok = AutoTokenizer.from_pretrained(a.model)
        model = AutoModelForTokenClassification.from_pretrained(
            a.model, dtype="auto", device_map=a.device).eval()
    except Exception as e:
        sys.exit(f"could not load {a.model}: {e}\nmodel_type openai_privacy_filter "
                 "needs transformers >= 5.6 (see config transformers_version); "
                 "pip install -U 'transformers>=5.6' or use the opf package")
    cal = load_calibration(a)
    point = cal.get("operating_points", {}).get(a.operating_point)
    if point is None:
        sys.exit(f"operating point {a.operating_point!r} not in calibration file")
    raw = point.get("biases", {})
    if set(raw) != set(VITERBI_BIAS_KEYS):
        sys.exit(f"calibration biases {sorted(raw)} != expected {sorted(VITERBI_BIAS_KEYS)}")
    biases = {k: float(v) for k, v in raw.items()}
    id2label = {int(k): v for k, v in model.config.id2label.items()}
    base_labels = {v.partition("-")[2] for v in id2label.values() if v != "O"}
    unknown = base_labels - set(PRIVACY_FILTER_MAP)
    if unknown:
        sys.exit(f"{a.model} emits labels with no Scotoma mapping: {sorted(unknown)} — extend PRIVACY_FILTER_MAP")
    for b in range(0, len(docs), a.batch):
        chunk = docs[b:b + a.batch]
        enc = tok([d["text"] for d in chunk], return_tensors="pt", padding=True,
                  truncation=True, max_length=a.max_tokens,
                  return_offsets_mapping=True, add_special_tokens=False)
        offsets = enc.pop("offset_mapping")
        with torch.no_grad():
            logits = model(**{k: v.to(model.device) for k, v in enc.items()}).logits
        logprobs = torch.log_softmax(logits.float(), dim=-1).cpu()
        mask = enc["attention_mask"]
        for k, d in enumerate(chunk):
            n = int(mask[k].sum())
            offs = [(int(s), int(e)) for s, e in offsets[k, :n].tolist()]
            path = viterbi(logprobs[k, :n].tolist(), id2label, biases)
            spans = []
            for s in bioes_spans(path, id2label, offs):
                st, en = trim(d["text"], s["start"], s["end"])
                if en > st:
                    spans.append({"start": st, "end": en, "label": PRIVACY_FILTER_MAP[s["label"]]})
            d["_pred"] = sorted(spans, key=lambda s: s["start"])
        print(f"privacy-filter: {min(b + a.batch, len(docs))}/{len(docs)}", file=sys.stderr, flush=True)


def load_calibration(a):
    """viterbi_calibration.json: --calibration path, model dir, or HF download.

    Fatal on failure — silently decoding with zero biases would claim the
    documented calibrated path without the artifact.
    """
    import os, urllib.request
    if a.calibration:
        return json.load(open(a.calibration))
    local = os.path.join(a.model, "viterbi_calibration.json")
    if os.path.exists(local):
        return json.load(open(local))
    try:
        url = f"https://huggingface.co/{a.model}/resolve/main/viterbi_calibration.json"
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.load(r)
    except Exception as e:
        sys.exit(f"no viterbi_calibration.json for {a.model} ({e}); "
                 "pass --calibration with the artifact from the model repo")


def selftest():
    """Exercise the pure-Python Viterbi + BIOES->span path on hand-made logits."""
    ids = ["O", "B-x", "I-x", "E-x", "S-x", "B-y", "I-y", "E-y", "S-y"]
    id2label = dict(enumerate(ids))
    def logits(rows):
        return [[-20.0] * len(ids) if r is None else [r.get(ids[i], -20.0) for i in range(len(ids))] for r in rows]
    # all-O background
    assert viterbi(logits([{"O": 5.0}] * 4), id2label) == [0, 0, 0, 0]
    # singleton entity beats O, then background resumes
    p = viterbi(logits([{"O": 5.0}, {"S-x": 8.0}, {"O": 5.0}]), id2label)
    assert [ids[i] for i in p] == ["O", "S-x", "O"], p
    # B-I-E span wins when each step is favored
    p = viterbi(logits([{"B-x": 9.0}, {"I-x": 9.0}, {"E-x": 9.0}]), id2label)
    assert [ids[i] for i in p] == ["B-x", "I-x", "E-x"], p
    # constraint: I/E may not start a sequence — the decoder repairs argmax into
    # the best legal path (B-x,E-x here), not independent per-token winners
    p = viterbi(logits([{"I-x": 9.0}, {"E-x": 9.0}]), id2label)
    assert [ids[i] for i in p] == ["B-x", "E-x"], p
    # end mask: a span left open at the sequence end is illegal
    p = viterbi(logits([{"O": 5.0}, {"B-x": 8.0}]), id2label)
    assert [ids[i] for i in p] == ["O", "O"], p
    # transition biases only act across edges: O->S-x->O wins by default, and a
    # negative background_to_start flips the best path to O,O,O
    rows = logits([{"O": 9.0, "S-x": 5.0}, {"O": 4.0, "S-x": 5.0}, {"O": 5.0}])
    assert [ids[i] for i in viterbi(rows, id2label)] == ["O", "S-x", "O"]
    b = {k: 0.0 for k in VITERBI_BIAS_KEYS}; b["transition_bias_background_to_start"] = -50.0
    assert [ids[i] for i in viterbi(rows, id2label, b)] == ["O", "O", "O"]
    # inside_to_continue flips a competing legal path: with zero biases
    # B-x,E-x,O beats B-x,I-x,E-x; a +5 continue bonus makes the longer span win
    rows = logits([{"B-x": 9.0, "O": -5.0}, {"E-x": 8.5, "I-x": 7.9}, {"E-x": 8.0, "O": 7.9}])
    b = {k: 0.0 for k in VITERBI_BIAS_KEYS}
    assert [ids[i] for i in viterbi(rows, id2label, b)] == ["B-x", "E-x", "O"]
    b["transition_bias_inside_to_continue"] = 5.0
    assert [ids[i] for i in viterbi(rows, id2label, b)] == ["B-x", "I-x", "E-x"]
    # bioes_spans: char offsets from token spans, label from the span name
    offs = [(0, 2), (3, 7), (8, 10)]
    p = viterbi(logits([{"B-x": 9.0}, {"I-x": 9.0}, {"E-x": 9.0}]), id2label)
    got = bioes_spans(p, id2label, offs)
    assert got == [{"start": 0, "end": 10, "label": "x"}], got
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("system", nargs="?", choices=["presidio", "openai-privacy-filter"])
    ap.add_argument("data", nargs="?")
    ap.add_argument("--out", required=False)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--spacy-model", default="en_core_web_lg")
    ap.add_argument("--model", default="openai/privacy-filter")
    ap.add_argument("--calibration", default=None, help="viterbi_calibration.json path")
    ap.add_argument("--operating-point", default="default")
    ap.add_argument("--device", default="auto", help="device_map for the privacy filter")
    ap.add_argument("--max-tokens", type=int, default=128000)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); return
    if not a.system or not a.data or not a.out:
        ap.error("SYSTEM DATA --out are required")
    docs = [json.loads(l) for l in open(a.data, encoding="utf-8") if l.strip()]
    if a.limit: docs = docs[:a.limit]
    {"presidio": run_presidio, "openai-privacy-filter": run_privacy_filter}[a.system](docs, a)
    with open(a.out, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps({"id": d.get("id"), "text": d["text"], "spans": d.get("_pred", [])}, ensure_ascii=False) + "\n")
    print(f"wrote {len(docs)} lines to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
