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

gliner-* — GLiNER zero-shot PII models via the `gliner` package:
    gliner-nvidia                nvidia/gliner-PII            (NVIDIA Open Model License, max_types 25)
    gliner-knowledgator-large    knowledgator/gliner-pii-large-v1.0   (Apache-2.0, max_types 30)
    gliner-knowledgator-base     knowledgator/gliner-pii-base-v1.0    (max_types 100)
    gliner-knowledgator-edge     knowledgator/gliner-pii-edge-v1.0    (max_types 100)
One fixed prompt list (GLINER_LABELS) covers every Scotoma category, using the
cards'/dataset's own label names where they exist (nvidia's native vocabulary
is nvidia/Nemotron-PII snake_case: ssn, health_plan_beneficiary_number,
certificate_license_number, vehicle_identifier, ...; knowledgator's card
documents the spaced forms). Primaries first: the first 25 prompts cover all
21 Scotoma categories (incl. ORG); synonym prompts follow. Predict calls are
split into groups of <= the loaded model's max_types (read from
model.config.max_types at runtime — fatal if absent) and merged, overlapping
spans keeping the higher score. The map, by Scotoma destination:
    NAME     <- person name, first name, last name
    ADDRESS  <- street address, coordinate
    LOCATION <- city, county          ZIP      <- zip code, postcode
    DATE     <- date, date of birth   AGE      <- age
    PHONE    <- phone number          FAX      <- fax number
    EMAIL    <- email, email address
    SSN      <- ssn, social security number
    MRN      <- medical record number
    PLAN     <- health plan beneficiary number
    ACCOUNT  <- account number, credit card, bank routing number,
                credit card number, bank account
    LICENSE  <- certificate license number, license number, driver license
    VEHICLE  <- license plate, vehicle identifier
    DEVICE   <- device identifier, mac address
    URL      <- url                   IP       <- ip address, ipv4
    BIOMETRIC<- biometric identifier
    ID       <- id number, passport number, unique id
    ORG      <- organization, company name
Prediction threshold: 0.3 for all four — nvidia's card: "evaluated using
threshold=0.3"; knowledgator's cards use 0.3 throughout and call it the
recommended production starting point (--threshold overrides).
config.max_len counts GLiNER splitter tokens (words AND punctuation;
data_processing/processor.py truncates tokens[:max_len]), so docs are split
into windows of <= max_len splitter tokens AND <= (encoder limit - prompt
subwords) measured with model.data_processor.transformer_tokenizer
(chunk_text shrinks a window until both hold). Offsets map back to the
original text; trimmed duplicate/overlapping spans merge by score
(merge_spans). Unknown predicted label -> fatal (fail closed).
GPU: GLiNER picks CUDA itself when available; --batch controls docs/batch via
model.inference(texts, labels, batch_size=...).
Unknown predicted label -> fatal (fail closed).

Colab installs:
    pip install presidio-analyzer && python -m spacy download en_core_web_lg
    pip install -U "transformers>=5.6" torch accelerate   # then --model openai/privacy-filter (~3 GB)
    pip install gliner                                   # then any gliner-* system

"""
import argparse, json, os, sys
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

# GLiNER prompt labels -> Scotoma label. One fixed natural-language list for
# all GLiNER systems, preferring each card's own names (nvidia/gliner-PII was
# trained on nvidia/Nemotron-PII's snake_case vocabulary; knowledgator's card
# documents the space-separated forms). Order matters: every Scotoma category
# gets a primary prompt in the first 25 entries so a single label group (e.g.
# nvidia's max_types=25) still covers all categories; synonym prompts follow.
GLINER_MODELS = {
    "gliner-nvidia": ("nvidia/gliner-PII", 0.3),           # card: "evaluated using threshold=0.3"
    "gliner-knowledgator-large": ("knowledgator/gliner-pii-large-v1.0", 0.3),
    "gliner-knowledgator-base": ("knowledgator/gliner-pii-base-v1.0", 0.3),
    "gliner-knowledgator-edge": ("knowledgator/gliner-pii-edge-v1.0", 0.3),
    # knowledgator cards use threshold=0.3 throughout and call it the
    # "recommended starting point for production"
}
GLINER_LABELS = {
    # --- one primary prompt per Scotoma category (fits nvidia max_types 25) ---
    "person name": "NAME", "street address": "ADDRESS",
    "city": "LOCATION", "zip code": "ZIP",
    "date": "DATE", "date of birth": "DATE", "age": "AGE",
    "phone number": "PHONE", "fax number": "FAX", "email": "EMAIL",
    "ssn": "SSN", "medical record number": "MRN",
    "health plan beneficiary number": "PLAN",
    "account number": "ACCOUNT", "credit card": "ACCOUNT",
    "bank routing number": "ACCOUNT",
    "certificate license number": "LICENSE",
    "license plate": "VEHICLE", "vehicle identifier": "VEHICLE",
    "device identifier": "DEVICE", "url": "URL", "ip address": "IP",
    "biometric identifier": "BIOMETRIC",
    "id number": "ID", "organization": "ORG",
    # --- synonyms / native-vocab alternates, sent in later label groups ---
    "first name": "NAME", "last name": "NAME",
    "coordinate": "ADDRESS", "county": "LOCATION", "postcode": "ZIP",
    "email address": "EMAIL", "social security number": "SSN",
    "credit card number": "ACCOUNT", "bank account": "ACCOUNT",
    "license number": "LICENSE", "driver license": "LICENSE",
    "mac address": "DEVICE", "ipv4": "IP",
    "passport number": "ID", "unique id": "ID", "company name": "ORG",
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

def label_groups(prompts, max_types):
    """Split prompts into predict-call groups of at most max_types.

    GLiNER configs cap labels per call (nvidia/gliner-PII: 25, knowledgator
    large: 30, base/edge: 100). GLINER_LABELS is ordered so the first group
    alone still covers every Scotoma category; later groups add synonyms.
    """
    return [prompts[i:i + max_types] for i in range(0, len(prompts), max_types)]


def predict_grouped(model, texts, groups, threshold, batch_size, max_types):
    """Run GLiNER inference once per label group; enforce the max_types cap at
    the call boundary. Returns per-(text, group) entity lists in the same
    nested order: results[g][i] -> entities for texts[i] under groups[g]."""
    out = []
    for labels in groups:
        if len(labels) > max_types:
            raise ValueError(f"label group of {len(labels)} exceeds model max_types={max_types}")
        if hasattr(model, "inference"):
            out.append(model.inference(texts, labels, threshold=threshold, batch_size=batch_size))
        else:  # very old gliner: serial fallback
            out.append([model.predict_entities(t, labels, threshold=threshold) for t in texts])
    return out


def merge_spans(raw):
    """Resolve duplicate/overlapping spans from overlapping windows and label
    groups. Exact duplicates collapse; overlapping distinct spans keep the
    higher score. raw = [(start, end, scotoma_label, score)]."""
    out = []
    for s in sorted(raw, key=lambda r: -r[3]):
        if any(not (s[1] <= t["start"] or s[0] >= t["end"]) for t in out):
            continue
        out.append({"start": s[0], "end": s[1], "label": s[2]})
    return sorted(out, key=lambda s: s["start"])


def gliner_splitter_tokens(text):
    """Default GLiNER whitespace splitter: words AND punctuation are separate
    tokens — this is what config.max_len counts (data_processing/processor.py
    truncates `tokens` at max_len). Mirrors WordsSplitter('whitespace')."""
    import re
    return [m.span() for m in re.finditer(r"\w+(?:[-_]\w+)*|\S", text)]


def chunk_text(text, tok_spans, tok_strs, max_len, measure=None,
               subword_limit=None, overlap=None):
    """Split text into (char_offset, chunk_text) windows, safe in both senses:
    <= max_len GLiNER splitter tokens per window AND, when `measure` is given,
    measure(tok_strs[i:j]) <= subword_limit (the model's real prepared+encoded
    input length, incl. the label prompt — shrink the window until it fits,
    since subword blow-up is not proportional to token count). Windows are
    whole splitter tokens, stepped max_len-overlap apart so an entity cut at
    one window's edge sits inside the next. Each chunk is an exact substring
    of text starting at its char offset."""
    overlap = max(1, max_len // 7) if overlap is None else overlap
    n = len(tok_spans)
    def fits(j_from, j_to):
        return measure is None or measure(tok_strs[j_from:j_to]) <= subword_limit
    if n <= max_len and fits(0, n):
        return [(0, text)]
    chunks, i = [], 0
    while i < n:
        if not fits(i, i + 1):
            raise ValueError(f"single splitter token at offset {tok_spans[i][0]} "
                             "exceeds the encoder subword budget — cannot window")
        hi = min(i + max_len, n)
        if not fits(i, hi):
            lo = i + 1  # binary search the largest window end that fits
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if fits(i, mid):
                    lo = mid
                else:
                    hi = mid - 1
        j = hi
        chunks.append((tok_spans[i][0], text[tok_spans[i][0]:tok_spans[j - 1][1]]))
        if j == n:
            break
        # next window starts `overlap` tokens before this window's actual end
        # (never before i+1: always makes progress, keeps the boundary overlap)
        i = max(i + 1, j - overlap)
    return chunks


def gliner_limits(model):
    """(max_types, max_len) from the loaded model's config — the only source of
    truth. max_types caps labels per predict call; max_len caps GLiNER
    splitter tokens per input. Fatal if missing or invalid."""
    cfg = getattr(model, "config", None)
    mt = getattr(cfg, "max_types", None)
    ml = getattr(cfg, "max_len", None)
    try:
        max_types, max_len = int(mt), int(ml)
    except (TypeError, ValueError):
        sys.exit(f"model config lacks usable max_types/max_len (got {mt!r}/{ml!r})")
    if max_types <= 0 or max_len <= 0:
        sys.exit(f"model config has non-positive limits: max_types={mt!r} max_len={ml!r}")
    return max_types, max_len


def encoder_limit(model, fallback):
    """The inner HF encoder's positional cap (what truncation=True cuts at when
    the tokenizer's own model_max_length is a huge sentinel). Probes the usual
    GLiNER model paths; falls back to `fallback` (max_len) — always safe since
    the encoded input is never shorter than its splitter-token count."""
    for path in (("model", "token_rep_layer", "bert_layer", "model", "config"),
                 ("model", "token_rep_layer", "bert_layer", "config"),
                 ("model", "encoder", "model", "config")):
        obj = model
        for attr in path:
            obj = getattr(obj, attr, None)
            if obj is None:
                break
        lim = getattr(obj, "max_position_embeddings", None) if obj is not None else None
        if isinstance(lim, int) and 0 < lim < 10**7:
            return lim
    return fallback

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


def run_gliner(docs, a):
    try:
        from gliner import GLiNER
    except ImportError:
        sys.exit("pip install gliner")
    hf_id, card_threshold = GLINER_MODELS[a.system]
    threshold = card_threshold if a.threshold is None else a.threshold
    model = GLiNER.from_pretrained(hf_id)
    import torch
    if torch.cuda.is_available():
        model = model.to("cuda")   # from_pretrained loads on CPU; without this a GPU box runs at CPU speed
    model.eval()
    print(f"{a.system}: device {next(model.parameters()).device}", file=sys.stderr)
    max_types, max_len = gliner_limits(model)
    prompts = list(GLINER_LABELS)
    groups = label_groups(prompts, max_types)
    # Splitter tokens are what max_len counts; measure() reproduces the model's
    # real input — dp.prepare_inputs wraps each label group in its marker
    # tokens, then the HF tokenizer encodes with is_split_into_words — so the
    # subword check is the exact tensor length, not an estimate.
    dp = getattr(model, "data_processor", None)
    enc_tok = getattr(dp, "transformer_tokenizer", None)
    splitter = getattr(dp, "words_splitter", None)
    measure = None
    if dp is not None and enc_tok is not None:
        def encoded(words, labels):
            inp, _ = dp.prepare_inputs([words], labels)
            return len(enc_tok(inp[0], is_split_into_words=True,
                               add_special_tokens=False)["input_ids"])
        def measure(words):
            return max(encoded(list(words), g) for g in groups)
    subword_limit = encoder_limit(model, max_len) - 8
    for b in range(0, len(docs), a.batch):
        chunk = docs[b:b + a.batch]
        windows = []
        for di, d in enumerate(chunk):
            if splitter is not None:
                toks = [(s, e) for _, s, e in splitter(d["text"])]
                strs = [d["text"][s:e] for s, e in toks]
            else:
                toks = gliner_splitter_tokens(d["text"])
                strs = [d["text"][s:e] for s, e in toks]
            windows += [(di, off, ct) for off, ct in
                        chunk_text(d["text"], toks, strs, max_len,
                                   measure, subword_limit)]
        texts = [ct for _, _, ct in windows]
        for g, results in enumerate(predict_grouped(model, texts, groups, threshold, a.batch, max_types)):
            for (di, off, _), ents in zip(windows, results):
                raw = chunk[di].setdefault("_raw", [])
                text = chunk[di]["text"]
                for ent in ents:
                    label = GLINER_LABELS.get(ent["label"])
                    if label is None:
                        sys.exit(f"{hf_id} returned unmapped label {ent['label']!r} — extend GLINER_LABELS")
                    s, e = trim(text, off + ent["start"], off + ent["end"])
                    if e > s:
                        raw.append((s, e, label, float(ent.get("score", 1.0))))
        for d in chunk:
            d["_pred"] = merge_spans(d.pop("_raw", []))
        print(f"{a.system}: {min(b + a.batch, len(docs))}/{len(docs)} "
              f"(thr {threshold}, {len(groups)} label group(s) <= {max_types}, "
              f"windows <= {max_len} tokens)", file=sys.stderr, flush=True)


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
    print("selftest: viterbi ok")
    selftest_chunking()


def selftest_chunking():
    """GLiNER plumbing: windows respect the splitter-token cap AND a measured
    subword budget, offsets map back to exact original substrings, spans found
    in the overlap merge to one, and no predict call exceeds max_types."""
    def split(t):
        sp = gliner_splitter_tokens(t)
        return sp, [t[s:e] for s, e in sp]
    text = "BEGIN123 " + ("filler " * 90) + "MID456 " + ("filler " * 90) + "TAIL789"
    sp, st = split(text)
    chunks = chunk_text(text, sp, st, max_len=30, overlap=8)
    assert len(chunks) >= 3, chunks
    for off, ct in chunks:
        assert text[off:off + len(ct)] == ct  # chunk is an exact substring
    # fake predictor: report the three markers wherever they appear in a chunk
    found = []
    for off, ct in chunks:
        for marker in ("BEGIN123", "MID456", "TAIL789"):
            i = ct.find(marker)
            while i >= 0:
                found.append((off + i, off + i + len(marker), "ID", 0.9))
                i = ct.find(marker, i + 1)
    spans = merge_spans(found)
    got = {text[s["start"]:s["end"]] for s in spans}
    assert got == {"BEGIN123", "MID456", "TAIL789"}, spans
    # MID456 sits inside the overlap of two windows: seen twice, merged once
    assert sum(s["end"] - s["start"] == 6 and text[s["start"]] == "M" for s in spans) == 1
    # overlapping distinct spans keep the higher score
    m = merge_spans([(10, 20, "NAME", 0.9), (12, 18, "ID", 0.5), (30, 35, "DATE", 0.4)])
    assert m == [{"start": 10, "end": 20, "label": "NAME"},
                 {"start": 30, "end": 35, "label": "DATE"}], m
    # every window overlaps the previous one: no word gap between chunks
    ends = [off + len(ct) for off, ct in chunks]
    for k in range(1, len(chunks)):
        assert chunks[k][0] < ends[k - 1]
    # short text: single whole-text window, no chunking
    assert chunk_text("short text", *split("short text"), max_len=30) == [(0, "short text")]
    # subword budget: a "wide" fake encoder (4 subwords per splitter token, plus
    # 50 of prompt overhead) forces smaller windows than the token cap alone
    wide = chunk_text(text, sp, st, max_len=60, overlap=8,
                      measure=lambda ws: 4 * len(ws) + 50, subword_limit=200)
    assert all(4 * len(gliner_splitter_tokens(ct)) + 50 <= 200 for _, ct in wide), [len(c[1]) for c in wide]
    assert all(text[o:o + len(c)] == c for o, c in wide)
    joined = "".join(c for _, c in wide)
    for marker in ("BEGIN123", "MID456", "TAIL789"):
        assert marker in joined, marker
    # shrunk windows still overlap: boundary protection survives the shrink
    for k in range(1, len(wide)):
        prev_end = wide[k - 1][0] + len(wide[k - 1][1])
        assert wide[k][0] < prev_end, (wide[k - 1], wide[k])
    # max_types is enforced at the call boundary, not just in label_groups
    class Fake:
        def __init__(self): self.seen = []
        def inference(self, texts, labels, threshold=None, batch_size=None):
            self.seen.append(len(labels)); return [[] for _ in texts]
    fake = Fake()
    predict_grouped(fake, ["x"], label_groups(list(GLINER_LABELS), 25), 0.3, 8, 25)
    assert all(n <= 25 for n in fake.seen) and len(fake.seen) == 2
    try:
        predict_grouped(fake, ["x"], [["a"] * 26], 0.3, 8, 25)
        raise SystemExit("cap not enforced")
    except ValueError:
        pass
    # first label group covers every Scotoma category (primaries listed first)
    groups = label_groups(list(GLINER_LABELS), 25)
    assert {GLINER_LABELS[p] for p in groups[0]} == set(GLINER_LABELS.values())
    print("selftest: chunking ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("system", nargs="?", choices=["presidio", "openai-privacy-filter"] + list(GLINER_MODELS))
    ap.add_argument("data", nargs="?")
    ap.add_argument("--out", required=False)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--threshold", type=float, default=None, help="GLiNER score threshold; default is each card's eval threshold")
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
    if a.limit is not None and a.limit < 0:
        ap.error("--limit must be >= 0")
    if a.batch <= 0:
        ap.error("--batch must be > 0")
    if a.threshold is not None and not 0.0 <= a.threshold <= 1.0:
        ap.error("--threshold must be in [0, 1]")
    docs = [json.loads(l) for l in open(a.data, encoding="utf-8") if l.strip()]
    if a.limit is not None: docs = docs[:a.limit]
    runner = {"presidio": run_presidio, "openai-privacy-filter": run_privacy_filter}.get(a.system, run_gliner)
    runner(docs, a)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps({"id": d.get("id"), "text": d["text"], "spans": d.get("_pred", [])}, ensure_ascii=False) + "\n")
    print(f"wrote {len(docs)} lines to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
