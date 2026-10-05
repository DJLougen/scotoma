#!/usr/bin/env python3
"""Ctrl-F verifier for the planted clinical test set. Standard library only.

    python bench/verify_planted.py bench/data/clin_spec.jsonl bench/data/clin_raw.jsonl \\
        --out bench/data/clin_test.jsonl --rejects bench/data/clin_rejects.jsonl \\
        [--scotoma target/release/scotoma]
    python bench/verify_planted.py --selftest

How labels are recovered:

  sentinel specs  Raw text is scanned for [[TOKEN]] placeholders. Unknown
      tokens, malformed brackets, missing placeholders or wrong repeat
      counts => reject. Accepted docs get each spec value substituted
      left-to-right; span offsets are therefore known BY CONSTRUCTION
      (labels never depend on the generator model). A final grep sanity
      check confirms text[start:end] == value for every span, and a verbatim
      search flags any value appearing outside substituted spans
      (an echoed value list) -> reject.

  verbatim specs  Every planted value is found with exact str.find plus a
      word-boundary check ('12' inside '1234' does not count). Missing
      values or too few repeats => reject. Overlapping matches resolve
      deterministically: longest match wins; equal length keeps the
      leftmost.

Unplanted-identifier screens (any hit outside labelled spans => reject with
reason). These exist because an identifier we did not plant would be an
unlabeled gold error:

  name-pool    capitalised token in the copied name lists or any A/B/C
               pool entry. Sentence-initial tokens that are also common
               English words (the STOP list below) are allowed; common-word
               names (May, Rose, ...) are only flaggable mid-sentence because
               months/auxiliaries at sentence start are legitimate prose.
               Documented trade-off: erring toward rejection where ambiguous.
  digits       any run of >=4 digits (or comma-grouped like 1,200) outside
               spans, UNLESS immediately followed by a clinical unit
               (mg, mcg, g, mL, L, mmHg, %, bpm, cm, kg, mmol/L, umol/L,
               mEq/L, IU, mOsm, kcal, Hz, x). Decimal numbers like 1240.5
               are allowed (lab values).
  date-like    d/d[/d] or d-d[-d] patterns, HH:MM times, 'Month d[, yyyy]'
               or 'd Month' outside spans. A plausible blood-pressure ratio
               (sys 70-250 / dia 30-150) is allowed.
  net          e-mail addresses, http(s)/www URLs, IPv4 literals outside
               spans.
  institution  a capitalised multi-word phrase ending in Hospital, Clinic,
               Medical, Center, Pharmacy, Health, Laboratory, Care, Group,
               Imaging, Hospice, Pediatrics, Rehabilitation, Dialysis,
               University, Institute outside spans.
  scotoma      optional --scotoma BIN: rules-only `scotoma scrub --json`
               detections (byte offsets -> chars) not overlapping labelled
               spans => reject. Per-doc subprocess, sequential.

Accepted docs are emitted in the benchmark JSONL schema (id, domain
clinical, mode=<style slug>, universe C, text, spans[{start,end,label,kind,
tags+'planted'}]). A deterministic split field 'dev'/'sealed' is set by
sha256(id) parity, and split files clin_dev.jsonl / clin_sealed.jsonl are
written next to --out. Rejects go to --rejects with id+reason.

This is a constructed, deterministically-labelled TEST set. It does not
replace a human-checked natural gold set for public/marketing claims.
"""
import argparse, hashlib, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as g
import plant_generate as pg

# ----------------------------------------------------------------------------
# Screens.
# ----------------------------------------------------------------------------

SENT_RE = re.compile(r"\[\[([A-Z]+_?[A-Z0-9_]*)\]\]")
ANY_BRACKET = re.compile(r"[\[\]]")

# Capitalised tokeniser for the name screen (letters incl. accents); at least
# two chars so 'A'/'I' never match.
CAPTOK = re.compile(r"(?u)(?<![\w.])[A-ZÀ-Þ][a-zà-ÿ'ʼ-]+")

# Sentence-initial tokens that are legitimate English words (months, aux,
# articles...). A pool-name hit is allowed only in this set AND at a sentence
# boundary. Common-word names are flaggable only mid-sentence.
STOP = {w.lower() for w in """A An The In On At For To From By With Without After Before During If When While
Although Though Because Since Until Unless As But And Or Nor So Yet This That These Those It Its His Her Their Our
Your My He She They We You I Not No Yes Then Than Thus Hence However Moreover Furthermore Therefore Otherwise Instead
Meanwhile Still Also Just Only Even Very More Most Less Least Much Many Few Some Any Each Every All Both Either Neither
One Two Three Four Five Six Seven Eight Nine Ten Monday Tuesday Wednesday Thursday Friday Saturday Sunday
January February March April May June July August September October November December
Mr Mrs Ms Dr Prof Patient Patients Pt Male Female Admission Discharge Assessment Plan Diagnosis History Physical
Examination Review Systems Impression Recommendations Follow Past Family Social Medications Allergies Vital Signs Labs
Laboratory Radiology Pathology Note Notes Report Summary Chart Consultation Referral""".split()}
# Of COMMON_* only these are also plausible month/auxiliary words; the rest
# (Hunter, Banks, Fields...) flag even mid-sentence.
COMMON_AMBIGUOUS = {w.lower() for w in "May June Will Mark Art Bill Pat Frank Rich Dawn".split()}
# Tokens like 'Dr.'/'Mr.' mean the '.' before a capital word is an abbreviation,
# not a sentence boundary.
TITLES = {"dr", "mr", "mrs", "ms", "prof", "st", "vs", "no", "fig", "rev", "sr", "jr"}

REAL_POOL = {n.lower() for n in g.FIRST["A"] + g.FIRST["B"] + g.LAST["A"] + g.LAST["B"]
             + pg.C_FIRST + pg.C_LAST + pg._load_names("first_names.txt") + pg._load_names("surnames.txt")}
COMMON_POOL = {w.lower() for w in g.COMMON_FIRST + g.COMMON_LAST}

# Case-sensitive phrases from every non-name pool plus multi-word surnames:
# an unplanted 'Van der Merwe' or 'Lakeridge Health' must reject.
PHRASE_POOL = sorted({p for p in
    g.STREET["A"] + g.STREET["B"] + g.STREET["C"]
    + [c for c, _ in g.CITY["A"] + g.CITY["B"] + g.CITY["C"]]
    + g.ORG["A"] + g.ORG["B"] + g.ORG["C"]
    + g.MAILHOST["A"] + g.MAILHOST["B"] + g.MAILHOST["C"]
    + [s for s in g.LAST["A"] + g.LAST["B"] + pg.C_LAST if " " in s]
    if len(p) >= 3}, key=len, reverse=True)


DIGITS = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?![\w,])|(?<![\w.,])\d{4,}(?![\w.,])")
UNITS = re.compile(r"(?i)^\s*(?:mg|mcg|µg|g|ml|l|mmhg|%|bpm|cm|mm|kg|mmol/l|µmol/l|umol/l|meq/l|iu|mosm|kcal|hz|x)\b")
SLASH = re.compile(r"(?<!\w)(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?!\w)")
DASH_DATE = re.compile(r"(?<!\w)\d{1,2}-\d{1,2}(?:-\d{2,4})?(?!\w)")
TIME = re.compile(r"(?<!\w)\d{1,2}:\d{2}(?::\d{2})?(?!\w)")
MONTH_DATE = re.compile(r"(?i)\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b")
PHONE = re.compile(r"(?<!\w)\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\w)|\(?\d{3}\)? ?\d{3} ?\d{4}(?!\w)")
EMAIL_RE = re.compile(r"(?i)(?<!\w)[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>()]+")
IP_RE = re.compile(r"(?<!\w)(?:\d{1,3}\.){3}\d{1,3}(?!\w)")
INSTITUTION = re.compile(r"(?u)\b[A-ZÀ-Þ][\w'&.-]*(?:\s+[A-ZÀ-Þ][\w'&.-]*)*\s+(?:Hospital|Hospitals|Clinic|Clinics|Medical|Center|Centre|Pharmacy|Health|Laboratory|Laboratories|Care|Group|Imaging|Hospice|Pediatrics|Rehabilitation|Dialysis|University|Institute)\b")
ECHO_PHRASES = ["VERBATIM", "identifying details", "placeholder below", "values below", "the required number of times"]


def _word_bounds(text, s, e):
    """True iff text[s:e] is not glued to word characters on either side."""
    return (s == 0 or not (text[s - 1].isalnum() or text[s - 1] == "_")) and \
           (e == len(text) or not (text[e].isalnum() or text[e] == "_"))


def find_all(text, value):
    """Every word-bounded occurrence of value in text -> [(start,end)]."""
    out, pos = [], 0
    while True:
        i = text.find(value, pos)
        if i < 0:
            break
        if _word_bounds(text, i, i + len(value)):
            out.append((i, i + len(value)))
        pos = i + 1
    return out


def _overlaps(spans, s, e):
    return any(s < b and a < e for a, b, *_ in spans)


def _sentence_initial(text, s):
    """Is position s right after sentence-ending punctuation or text start?
    A '.' preceded by a title abbreviation (Dr., Mr.) doesn't count."""
    i = s - 1
    while i >= 0 and text[i] in " \t\n":
        i -= 1
    if i < 0:
        return True
    if text[i] in ".!?;:\n»\"":
        if text[i] == ".":
            j = i - 1
            while j >= 0 and (text[j].isalpha()):
                j -= 1
            if text[j + 1:i].lower() in TITLES:
                return False
        return True
    return False


def screens(text, spans, use_scotoma=None):
    """Return list of reject reasons for unplanted identifiers outside spans."""
    reasons = []
    def outside(s, e):
        return not _overlaps(spans, s, e)

    for m in CAPTOK.finditer(text):
        if not outside(m.start(), m.end()):
            continue
        tok = m.group(0).lower()
        initial = _sentence_initial(text, m.start())
        if tok in REAL_POOL:
            if not (initial and tok in STOP):
                reasons.append(f"name-pool:{m.group(0)}@{m.start()}")
        elif tok in COMMON_POOL:
            if not initial or tok not in COMMON_AMBIGUOUS:
                reasons.append(f"common-name:{m.group(0)}@{m.start()}")

    for m in DIGITS.finditer(text):
        if not outside(m.start(), m.end()):
            continue
        if UNITS.match(text[m.end():m.end() + 12]):
            continue
        reasons.append(f"digits:{m.group(0)}@{m.start()}")

    for m in SLASH.finditer(text):
        if not outside(m.start(), m.end()):
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if m.group(3) is None and 70 <= a <= 250 and 30 <= b <= 150:
            continue  # plausible blood pressure
        reasons.append(f"date-like:{m.group(0)}@{m.start()}")
    for name, rx in (("date-like", DASH_DATE), ("time", TIME), ("date-like", MONTH_DATE), ("phone", PHONE),
                     ("email", EMAIL_RE), ("url", URL_RE), ("ip", IP_RE), ("institution", INSTITUTION)):
        for m in rx.finditer(text):
            if outside(m.start(), m.end()):
                reasons.append(f"{name}:{m.group(0)[:40]}@{m.start()}")
    for phrase in PHRASE_POOL:
        for s, e in find_all(text, phrase):
            if outside(s, e):
                reasons.append(f"pool-phrase:{phrase}@{s}")

    if use_scotoma:
        for s, e, cat in scotoma_detections(use_scotoma, text):
            if outside(s, e):
                reasons.append(f"scotoma:{cat}@{s}")
    return reasons


def scotoma_detections(binary, text):
    """rules-only detections as (start, end, category) in CHAR offsets.
    Fail closed: any subprocess or parse error raises, and verify_doc turns
    that into a 'scotoma-error' reject — the screen must never silently pass."""
    env = dict(os.environ)
    env.pop("SCOTOMA_MODEL", None)
    try:
        p = subprocess.run([binary, "scrub", "--json"], input=text.encode(), capture_output=True, env=env, timeout=60)
        items = json.loads(p.stdout)["items"] if p.returncode == 0 else None
    except Exception as e:
        raise RuntimeError(f"scotoma subprocess failed: {e}") from e
    if items is None:
        raise RuntimeError(f"scotoma exited {p.returncode}: {p.stderr[:200]!r}")
    out = []
    for it in items:
        s = len(text.encode("utf-8")[:it["start"]].decode("utf-8"))  # bytes -> chars
        e = len(text.encode("utf-8")[:it["end"]].decode("utf-8"))
        out.append((s, e, it["category"]))
    return out


# ----------------------------------------------------------------------------
# Sentinel substitution.
# ----------------------------------------------------------------------------

def substitute(spec, raw):
    """Replace [[TOKEN]] occurrences with spec values. Returns (text, spans,
    reasons). Spans: (start, end, item)."""
    ph_map = {it["ph"]: it for it in spec["planted"]}
    reasons = []
    tokens = list(SENT_RE.finditer(raw))
    found = {}
    for m in tokens:
        if m.group(1) not in ph_map:
            reasons.append(f"unknown-placeholder:[[{m.group(1)}]]")
        else:
            found[m.group(1)] = found.get(m.group(1), 0) + 1
    stripped = SENT_RE.sub("", raw)
    if ANY_BRACKET.search(stripped):
        reasons.append("malformed-brackets")
    for it in spec["planted"]:
        n = found.get(it["ph"], 0)
        if n == 0:
            reasons.append(f"missing-placeholder:{it['ph']}")
        elif n < it["count"]:
            # Extra uses are harmless (every substituted occurrence is labelled);
            # too few would make the `repeat` tag a lie.
            reasons.append(f"repeat-count:{it['ph']}:{n}<{it['count']}")
    if reasons:
        return None, [], reasons
    text, spans, pos = "", [], 0
    for m in tokens:
        it = ph_map[m.group(1)]
        text += raw[pos:m.start()]
        s = len(text)
        text += it["value"]
        spans.append((s, len(text), it))
        pos = m.end()
    text += raw[pos:]
    return text, spans, reasons


# ----------------------------------------------------------------------------
# Per-document verification.
# ----------------------------------------------------------------------------

def echo_check(raw_text, spec):
    """Detect the model echoing the prompt's list instead of writing prose.
    Sentinel mode: >=3 lines carrying '[[PH]] = description' or a bare
    '[[PH]]'. Verbatim mode: >=3 lines consisting of exactly one planted
    value, or a 'value (role' line like the prompt shows."""
    phs = {it["ph"] for it in spec["planted"]}
    vals = {it["value"] for it in spec["planted"]}
    hits = 0
    for ln in raw_text.splitlines():
        ln = ln.strip()
        m = re.match(r"^\[\[([A-Z]+_?[A-Z0-9_]*)\]\]", ln)
        if m and m.group(1) in phs and (m.end() == len(ln) or ln[m.end():].lstrip().startswith("=")):
            hits += 1
            continue
        core = ln.strip(" .;-*")
        if core in vals or (core.split(" (")[0] in vals and " (" in ln):
            hits += 1
    return hits >= 3


def verify_doc(spec, raw, scotoma_bin=None):
    """-> (record_dict | None, reason_list)."""
    reasons = []
    mode = spec.get("spec_mode", "sentinel")
    text = raw.get("text") or ""
    raw_text = text
    if not text.strip():
        return None, ["empty-text"]
    if raw.get("finish_reason") not in (None, "stop", "end_turn"):
        reasons.append(f"finish:{raw.get('finish_reason')}")
        return None, reasons
    for ph in ECHO_PHRASES:
        if ph.lower() in text.lower():
            reasons.append(f"instruction-echo:{ph.split()[0]}")

    if mode == "sentinel":
        text, spans, r2 = substitute(spec, text)
        reasons += r2
        if text is None:
            return None, reasons
        # grep sanity: every span text equals its value (offsets by construction)
        for s, e, it in spans:
            assert text[s:e] == it["value"], "substitution offset bug"
        # verbatim echo: a planted value occurring outside substituted spans
        for it in spec["planted"]:
            for s, e in find_all(text, it["value"]):
                if not _overlaps(spans, s, e):
                    reasons.append(f"value-echo:{it['ph']}@{s}")
    else:  # verbatim
        occ = []  # (start, end, item)
        for it in spec["planted"]:
            hits = find_all(text, it["value"])
            if len(hits) < it["count"]:
                reasons.append(f"missing-value:{it['value'][:30]}:{len(hits)}<{it['count']}")
            for s, e in hits:
                occ.append((s, e, it))
        # deterministic overlap resolution: longest wins, ties keep leftmost
        occ.sort(key=lambda x: (-(x[1] - x[0]), x[0]))
        spans = []
        for s, e, it in occ:
            if not _overlaps(spans, s, e):
                spans.append((s, e, it))
        spans.sort()

    if reasons:
        return None, reasons
    if echo_check(raw_text, spec):
        return None, ["echoed-value-list"]
    try:
        reasons = screens(text, spans, scotoma_bin)
    except RuntimeError as e:
        return None, [f"scotoma-error:{e}"]
    if reasons:
        return None, reasons
    return {"id": spec["id"], "domain": "clinical", "mode": spec.get("mode", ""),
            "universe": "C", "style": spec.get("style", ""), "generator": raw.get("model", ""),
            "prompt_sha256": raw.get("prompt_sha256", ""),
            "split": "dev" if int(hashlib.sha256(spec["id"].encode()).hexdigest(), 16) % 2 == 0 else "sealed",
            "text": text,
            "spans": [{"start": s, "end": e, "label": it["label"], "kind": it["kind"],
                       "tags": it["tags"] + ["planted"]} for s, e, it in spans]}, []


def split_paths(out_path):
    base = out_path
    for suf in ("_test", "_all"):
        if base.endswith(suf + ".jsonl"):
            base = base[: -len(suf + ".jsonl")]
            break
    else:
        base = re.sub(r"\.jsonl$", "", base)
    return base + "_dev.jsonl", base + "_sealed.jsonl"


def run(spec_path, raw_path, out_path, rejects_path, scotoma_bin=None):
    t0 = time.time()
    specs = {json.loads(ln)["id"]: json.loads(ln) for ln in open(spec_path, encoding="utf-8") if ln.strip()}
    raws = {}
    for ln in open(raw_path, encoding="utf-8"):
        if ln.strip():
            r = json.loads(ln)
            raws[r["id"]] = r
    accepted, rejected = [], []
    for sid, spec in specs.items():
        raw = raws.get(sid)
        if raw is None:
            rejected.append({"id": sid, "reasons": ["no-raw-output"]})
            continue
        rec, reasons = verify_doc(spec, raw, scotoma_bin)
        (accepted if rec else rejected).append(rec or {"id": sid, "reasons": reasons})
    with open(out_path, "w", encoding="utf-8") as f:
        for d in accepted:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    if rejects_path:
        with open(rejects_path, "w", encoding="utf-8") as f:
            for d in rejected:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
    dev_p, sealed_p = split_paths(out_path)
    for path, want in ((dev_p, "dev"), (sealed_p, "sealed")):
        with open(path, "w", encoding="utf-8") as f:
            for d in accepted:
                if d["split"] == want:
                    f.write(json.dumps(d, ensure_ascii=False) + "\n")
    # summary
    from collections import Counter
    rc = Counter(r for d in rejected for r in d["reasons"])
    lc = Counter(s["label"] for d in accepted for s in d["spans"])
    print(f"accepted {len(accepted)} / rejected {len(rejected)} in {time.time() - t0:.2f}s")
    print("reject reasons:", dict(rc.most_common()))
    print("label counts:", dict(lc.most_common()))
    print(f"split: dev={sum(1 for d in accepted if d['split'] == 'dev')} sealed={sum(1 for d in accepted if d['split'] == 'sealed')} -> {dev_p}, {sealed_p}")


# ----------------------------------------------------------------------------
# Self test.
# ----------------------------------------------------------------------------

def selftest():
    ok = []
    def check(name, cond):
        ok.append((name, bool(cond)))

    spec = {"id": "T-1", "spec_mode": "sentinel", "mode": "notes", "style": "x", "planted": [
        {"ph": "NAME_1", "value": "Jane Horn", "label": "NAME", "kind": "person", "role": "p", "count": 1, "tags": []},
        {"ph": "NAME_1_LAST", "value": "Horn", "label": "NAME", "kind": "person", "role": "p", "count": 2, "tags": ["repeat"]},
        {"ph": "MRN_1", "value": "M1234567", "label": "MRN", "kind": "mrn", "role": "m", "count": 1, "tags": []}]}
    raw = {"id": "T-1", "model": "t",
           "text": "Pt [[NAME_1]] seen. [[NAME_1_LAST]] tolerated. Dr noted [[NAME_1_LAST]] stable. MRN [[MRN_1]]."}
    rec, rs = verify_doc(spec, raw)
    check("sentinel basic", rec and not rs)
    if rec:
        spans = [(s["start"], s["end"]) for s in rec["spans"]]
        check("offsets", all(rec["text"][a:b] == v for (a, b), v in zip(spans, ["Jane Horn", "Horn", "Horn", "M1234567"])))
        check("repeat labelled", sum(1 for s in rec["spans"] if "Horn" == rec["text"][s["start"]:s["end"]]) == 2)

    # multibyte chars before/in values: offsets must be Python char offsets
    spec2 = {"id": "T-2", "spec_mode": "sentinel", "mode": "x", "planted": [
        {"ph": "NAME_1", "value": "Lúcás Ó Súilleabháin", "label": "NAME", "kind": "person", "count": 1, "tags": []},
        {"ph": "NAME_1_LAST", "value": "Ó Súilleabháin", "label": "NAME", "kind": "person", "count": 2, "tags": ["repeat"]},
        {"ph": "MRN_1", "value": "M1234567", "label": "MRN", "kind": "mrn", "count": 1, "tags": []}]}
    rec2, _ = verify_doc(spec2, {"id": "T-2", "model": "t",
                                 "text": "Résumé: [[NAME_1]] came in. [[NAME_1_LAST]] left. [[NAME_1_LAST]] ok. [[MRN_1]]"})
    check("multibyte offsets", rec2 and all(rec2["text"][s["start"]:s["end"]] == v
          for s, v in zip(rec2["spans"], ["Lúcás Ó Súilleabháin", "Ó Súilleabháin", "Ó Súilleabháin", "M1234567"])))
    if rec2:
        check("multibyte exact", rec2["spans"][0]["start"] == len("Résumé: "))
    # missing placeholder
    rec, rs = verify_doc(spec, {"id": "T-1", "text": "Pt [[NAME_1]]. [[NAME_1_LAST]]. [[NAME_1_LAST]]."})
    check("missing ph", rec is None and any(r.startswith("missing-placeholder:MRN_1") for r in rs))
    # wrong repeat count
    rec, rs = verify_doc(spec, {"id": "T-1", "text": "[[NAME_1]] [[NAME_1_LAST]] [[MRN_1]]"})
    check("repeat count", rec is None and any(r.startswith("repeat-count:NAME_1_LAST") for r in rs))
    # extra uses are accepted and every occurrence is labelled
    rec, rs = verify_doc(spec, {"id": "T-1", "text": "[[NAME_1]] [[NAME_1]] [[NAME_1_LAST]] [[NAME_1_LAST]] [[NAME_1_LAST]] [[MRN_1]]"})
    check("over-count ok", rec is not None and sum(1 for x in rec["spans"] if x["label"] == "NAME") == 5)
    # unknown placeholder
    rec, rs = verify_doc(spec, {"id": "T-1", "text": "[[NAME_1]] [[NAME_1_LAST]] [[NAME_1_LAST]] [[MRN_1]] [[ZIP_9]]"})
    check("unknown ph", rec is None and any("unknown-placeholder" in r for r in rs))
    # malformed brackets
    rec, rs = verify_doc(spec, {"id": "T-1", "text": "[[NAME_1] ok [[NAME_1_LAST]] [[NAME_1_LAST]] [[MRN_1]]"})
    check("malformed", rec is None and "malformed-brackets" in rs)

    # verbatim mode: word boundary + overlap resolution + repeat counting
    vspec = {"id": "V-1", "spec_mode": "verbatim", "mode": "notes", "planted": [
        {"ph": "AGE_1", "value": "92", "label": "AGE", "kind": "age_over_89", "count": 1, "tags": []},
        {"ph": "NAME_1", "value": "Ana Rios", "label": "NAME", "kind": "person", "count": 2, "tags": ["repeat"]},
        {"ph": "MRN_1", "value": "92001234", "label": "MRN", "kind": "mrn", "count": 1, "tags": []}]}
    rec, rs = verify_doc(vspec, {"id": "V-1", "text": "Ana Rios, age 92. MRN 92001234. Ana Rios left."})
    check("verbatim basic", rec and not rs)
    rec, rs = verify_doc(vspec, {"id": "V-1", "text": "Ana Rios age 92, record x9200123400 noted. Ana Rios."})
    check("verbatim substring reject", rec is None and any("missing-value:92001234" in r for r in rs))
    rec, rs = verify_doc(vspec, {"id": "V-1", "text": "Ana Rios 92. 92001234."})
    check("verbatim repeat reject", rec is None and any("missing-value:Ana Rios" in r for r in rs))

    # screens: positive and negative examples
    pool_name = sorted(REAL_POOL)[0].title()  # e.g. from copied list
    good = {"id": "G", "spec_mode": "sentinel", "mode": "x", "planted": [
        {"ph": "NAME_1", "value": "Zebulan Quimby", "label": "NAME", "kind": "person", "count": 1, "tags": []}]}
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] takes metoprolol 25 mg twice daily."})
    check("screen clean dose", rec and not rs)
    rec, rs = verify_doc(good, {"id": "G", "text": f"[[NAME_1]] seen by Dr. {pool_name} today."})
    check("screen pool name", rec is None and any(r.startswith("name-pool:") for r in rs))
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] scored 1200 on the test."})
    check("screen digits", rec is None and any(r.startswith("digits:") for r in rs))
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] creatinine 1240.5 umol/L noted."})
    check("screen decimal allowed", rec and not rs)
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] visited 03/15/2024."})
    check("screen date", rec is None and any(r.startswith("date-like:") for r in rs))
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] BP 128/82 stable."})
    check("screen bp allowed", rec and not rs)
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] emailed j.doe@example.com."})
    check("screen email", rec is None and any(r.startswith("email:") for r in rs))
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] transferred to Lakeside General Hospital."})
    check("screen institution", rec is None and any(r.startswith("institution:") for r in rs))
    rec, rs = verify_doc(good, {"id": "G", "text": "May be discharged soon, said [[NAME_1]]."})
    check("sentence-initial May allowed", rec and not rs)
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] came in.\n[[NAME_1]]\n[[NAME_1]]\n[[NAME_1]]"})
    check("echo list", rec is None)
    rec, rs = verify_doc(good, {"id": "G", "text": "", "finish_reason": "stop"})
    check("empty text", rec is None and "empty-text" in rs)
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]]", "finish_reason": "length"})
    check("finish length", rec is None and any(r.startswith("finish:") for r in rs))

    # overlap resolution: 'Ana' vs 'Ana Rios' — longest wins, leftmost kept
    ospec = {"id": "O-1", "spec_mode": "verbatim", "mode": "x", "planted": [
        {"ph": "NAME_1", "value": "Ana Rios", "label": "NAME", "kind": "person", "count": 1, "tags": []},
        {"ph": "NAME_2", "value": "Ana", "label": "NAME", "kind": "person", "count": 1, "tags": []}]}
    rec, rs = verify_doc(ospec, {"id": "O-1", "text": "Ana Rios reviewed. Ana agreed."})
    check("overlap longest wins", rec and len(rec["spans"]) == 2
          and rec["text"][rec["spans"][0]["start"]:rec["spans"][0]["end"]] == "Ana Rios")

    # screens: url / ip / phone / time
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] visited https://portal.example.net/x."})
    check("screen url", rec is None and any(r.startswith("url:") for r in rs))
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] host 10.0.3.44 logged."})
    check("screen ip", rec is None and any(r.startswith("ip:") for r in rs))
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] called from 416-555-0987."})
    check("screen phone", rec is None and any(r.startswith("phone:") for r in rs))
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] seen at 08:30 rounds."})
    check("screen time", rec is None and any(r.startswith("time:") for r in rs))
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] takes 81 mg daily. HR 72 bpm."})
    check("screen clean vitals", rec and not rs)

    # reply cleaning: DiffusionGemma literal 'thought\n' prefix and tags
    check("thought prefix strip", pg.clean_llm_text("thought\n[[NAME_1]] ok") == "[[NAME_1]] ok")
    check("think tag strip", pg.clean_llm_text("<think>blah</think> ok") == "ok")
    check("unclosed thought", pg.clean_llm_text("<thought>rest is thought") == "")

    # scotoma screen fails closed on a bad binary
    rec, rs = verify_doc(good, {"id": "G", "text": "[[NAME_1]] ok"}, "/nonexistent-scotoma")
    check("scotoma fail-closed", rec is None and any(r.startswith("scotoma-error:") for r in rs))

    bad = [n for n, c in ok if not c]
    for n, c in ok:
        print(("PASS " if c else "FAIL ") + n)
    print(f"{sum(c for _, c in ok)}/{len(ok)} selftest checks passed")
    return not bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?")
    ap.add_argument("raw", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--rejects")
    ap.add_argument("--scotoma", help="path to scotoma binary for optional rules screen")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not (a.spec and a.raw and a.out):
        ap.error("need SPEC RAW --out")
    run(a.spec, a.raw, a.out, a.rejects, a.scotoma)


if __name__ == "__main__":
    main()
