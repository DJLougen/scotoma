#!/usr/bin/env python3
"""Add mechanical difficulty tags to every gold span.

    python bench/tag.py bench/data/nemo_test.jsonl bench/data/nemo_test_tagged.jsonl
    python bench/tag.py bench/data/test_tpl.jsonl --check        # agreement vs generator tags

Derived from the text alone, after the fact — no generator internals needed:

    m:cue              a cue word for that category within 28 chars before the span
    m:no_cue           no cue word found
    m:single_name      NAME span that is one token
    m:common_word_name NAME containing a word that is also an ordinary word
    m:lower            span text all lower-case alphabetic
    m:digit_spaced     digits separated by spaces, "4 1 5"
    m:repeat           same span text seen earlier in the document

Derived tags are appended to `tags` prefixed `m:` so the evaler's by-tag table
keeps them apart from generator tags. --check reports precision/recall of the
derived tags against the generator's cue/no_cue, single_name,
common_word_name and repeat. Standard library only.
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate import CUE, COMMON_FIRST, COMMON_LAST

COMMON_WORDS = {w.lower() for w in COMMON_FIRST + COMMON_LAST}
NAME_LIKE = re.compile(r"name|person", re.I)
DIGIT_SPACED = re.compile(r"\d(?: +\d)+$")

# Cue words per label, on top of the generic CUE regex from generate.py (which
# only knows the words the templates use). Each fragment is anchored at the end
# of the 28 characters before the span, same convention as CUE. Announcing
# words only: bare prepositions ("in", "of", "at") are too weak to count.
EXTRA_CUE = {
    "NAME": r"named|known as|signed",
    "ORG": r"inc\.?|corp\.?|ltd\.?|llp|llc|group|company|university|hospital|clinic|bank|school",
    "DATE": r"as of|dated|effective|due",
    "AGE": r"aged?|years? old|y/?o|age",
    "ADDRESS": r"residen\w*|located|liv\w+|mov\w+",
    "LOCATION": r"located|liv\w+|mov\w+",
    "ZIP": r"zip|postal|postcode",
    "PHONE": r"call|tel|mobile|cell|reach",
    "EMAIL": r"e-?mail\w*|write",
    "SSN": r"tax ?id|security",
    "MRN": r"chart",
    "PLAN": r"policy|coverage|insur\w*",
    "ACCOUNT": r"acct|deposit|wire|refund|card",
    "LICENSE": r"permit|registration",
    "VEHICLE": r"plate|vehicle|vin|car|truck|auto",
    "DEVICE": r"implant|pacemaker|model",
    "URL": r"link|portal|site|website|http|online",
    "IP": r"host|server",
    "ID": r"password|access",
    "BIOMETRIC": r"fingerprint|biometric|scan|print",
}
EXTRA = {k: re.compile(r"(?i)(?:\b(?:" + v + r")\b)[\s:#,(]*$") for k, v in EXTRA_CUE.items()}

def span_text(doc, s):
    return doc["text"][s["start"]:s["end"]]


def mtags(doc, s):
    """Derived m:* tags for one span."""
    text = span_text(doc, s)
    label = str(s.get("label", "")).upper()
    t = []
    prefix = doc["text"][max(0, s["start"] - 28):s["start"]]
    cued = bool(CUE.search(prefix)) or any(r.search(prefix) for k, r in EXTRA.items() if k in label)
    t.append("m:cue" if cued else "m:no_cue")
    if NAME_LIKE.search(label):
        words = text.split()
        if len(words) == 1:
            t.append("m:single_name")
        if any(re.sub(r"[^a-z]", "", w.lower()) in COMMON_WORDS for w in words):
            t.append("m:common_word_name")
    letters = re.sub(r"\s+", "", text)
    if letters.isalpha() and letters.islower():
        t.append("m:lower")
    if DIGIT_SPACED.fullmatch(text.strip()):
        t.append("m:digit_spaced")
    # Same normalized text seen earlier in the document (word-bounded so
    # "Mark" does not match inside "Marks").
    norm = re.sub(r"\s+", " ", text.strip().lower())
    before = re.sub(r"\s+", " ", doc["text"][:s["start"]].lower())
    if norm and re.search(r"(?<!\w)" + re.escape(norm) + r"(?!\w)", before):
        t.append("m:repeat")
    return t


def check(docs):
    """Precision/recall of m:X against generator tag X, where it exists."""
    GEN = {"m:cue": "cue", "m:single_name": "single_name", "m:common_word_name": "common_word_name", "m:repeat": "repeat"}
    stat = {k: [0, 0, 0, 0] for k in GEN}  # tp fp fn tn
    n_gen = 0
    for d in docs:
        for s in d["spans"]:
            tags = set(s.get("tags", []))
            if not any(not t.startswith("m:") for t in tags):
                continue
            n_gen += 1
            for m, g in GEN.items():
                if g in ("cue",):
                    if "cue" not in tags and "no_cue" not in tags:
                        continue
                    gold = "cue" in tags
                else:
                    gold = g in tags
                pred = m in tags
                stat[m][0 if pred and gold else 1 if pred else 2 if gold else 3] += 1
    print(f"{'tag':<20} {'gen+':>6} {'m+':>6} {'prec':>6} {'rec':>6} {'agree':>6}")
    for m, (tp, fp, fn, tn) in stat.items():
        p = tp / (tp + fp) if tp + fp else float("nan")
        r = tp / (tp + fn) if tp + fn else float("nan")
        print(f"{m:<20} {tp + fn:>6} {tp + fp:>6} {p:>6.3f} {r:>6.3f} {(tp + tn) / (tp + fp + fn + tn):>6.3f}")
    if not n_gen:
        print("(no generator tags found)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp")
    ap.add_argument("out", nargs="?", help="output file (omit with --check)")
    ap.add_argument("--check", action="store_true", help="tag in memory, print agreement vs generator tags, write nothing")
    a = ap.parse_args()
    if not a.check and not a.out:
        ap.error("need OUT.jsonl (or --check)")

    docs = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    n = 0
    for d in docs:
        for s in d.get("spans", []):
            s["tags"] = sorted(set(s.get("tags", [])) | set(mtags(d, s)))
            n += 1
    if a.check:
        check(docs)
    else:
        with open(a.out, "w", encoding="utf-8") as f:
            for d in docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        print(f"tagged {n} spans in {len(docs)} docs -> {a.out}")


if __name__ == "__main__":
    main()
