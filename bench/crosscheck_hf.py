#!/usr/bin/env python3
"""Score a Hugging Face token classifier in PyTorch on raw-label JSONL, with no
Scotoma code in the path (no ONNX, no label mapping, no Rust scorer).

    python bench/crosscheck_hf.py bench/data/nemo_test_raw.jsonl --model OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1 --last 2000

Follows the protocol OpenMed's cards describe: whitespace words, BIO tags,
the first sub-token of each word carries the word's label, 384-token
truncation, entity-level micro P/R/F1 in the seqeval (conlleval) style on the
dataset's own labels. Also reports touch recall (gold entity with any word
predicted non-O), the analogue of what `scotoma eval` calls recall.

If the card number reproduces here but `scotoma eval` is far off, the bug is in
Scotoma's ONNX export, label mapping or scorer.
"""
import argparse, json, re
from collections import Counter

WORDS = {"space": r"\S+", "punct": r"\w+|[^\w\s]"}


def entities(tags):
    """conlleval chunking: B-x starts, I-x continues only the same type, anything else ends."""
    out, cur = [], None
    for i, t in enumerate(tags + ["O"]):
        p, _, typ = t.partition("-")
        if cur and (t == "O" or p == "B" or typ != cur[2]):
            out.append(tuple(cur)); cur = None
        if t != "O" and cur is None:
            cur = [i, i, typ]
        elif cur:
            cur[1] = i
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--model", required=True)
    ap.add_argument("--last", type=int, default=None, help="use the last N lines (bench/data/nemo_test.jsonl is the tail 2000)")
    ap.add_argument("--max-len", type=int, default=384)
    ap.add_argument("--words", choices=["space", "punct"], default="space", help="space: whitespace words; punct: punctuation split off as its own words")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    docs = [json.loads(l) for l in open(a.data, encoding="utf-8") if l.strip()]
    if a.last: docs = docs[-a.last:]
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForTokenClassification.from_pretrained(a.model).eval()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(dev)
    id2label = model.config.id2label

    tp = fp = fn = touched = gold_n = truncated_words = 0
    missed = Counter()
    for b in range(0, len(docs), a.batch):
        chunk = docs[b:b + a.batch]
        words, golds = [], []
        for d in chunk:
            t = d["text"]
            w = [m.span() for m in re.finditer(WORDS[a.words], t)]
            tags = ["O"] * len(w)
            for s in sorted(d["spans"], key=lambda s: s["start"]):
                idx = [i for i, (x, y) in enumerate(w) if x < s["end"] and s["start"] < y]
                for j, i in enumerate(idx):
                    tags[i] = ("B-" if j == 0 else "I-") + s["label"]
            words.append([t[x:y] for x, y in w]); golds.append(tags)
        enc = tok(words, is_split_into_words=True, truncation=True, max_length=a.max_len, padding=True, return_tensors="pt")
        with torch.no_grad():
            pred = model(**{k: v.to(dev) for k, v in enc.items()}).logits.argmax(-1).cpu()
        for k, gold in enumerate(golds):
            wid = enc.word_ids(k)
            ptags, seen = {}, set()
            for ti, w in enumerate(wid):
                if w is None or w in seen: continue
                seen.add(w); ptags[w] = id2label[int(pred[k, ti])]
            n = len(ptags)                        # words that survived truncation
            truncated_words += len(gold) - n
            g, p = gold[:n], [ptags[i] for i in range(n)]
            ge, pe = set(entities(g)), set(entities(p))
            tp += len(ge & pe); fp += len(pe - ge); fn += len(ge - pe)
            for e in ge - pe: missed[e[2]] += 1
            for s, e, _ in ge:
                gold_n += 1
                touched += any(p[i] != "O" for i in range(s, e + 1))
    P, R = tp / max(1, tp + fp), tp / max(1, tp + fn)
    res = {"model": a.model, "data": a.data, "docs": len(docs), "protocol": f"{a.words} words, first-subtoken, BIO, conlleval entities, max_len {a.max_len}",
           "precision": P, "recall": R, "micro_f1": 2 * P * R / max(1e-9, P + R), "touch_recall": touched / max(1, gold_n),
           "gold_entities": gold_n, "words_dropped_by_truncation": truncated_words, "most_missed_labels": missed.most_common(10)}
    print(json.dumps(res, indent=1))
    if a.out: json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
