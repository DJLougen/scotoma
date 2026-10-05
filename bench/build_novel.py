#!/usr/bin/env python3
"""Build the novel-format clinical benchmark: same accepted LLM raw notes as
clin_test.jsonl, but every planted identifier whose label has registered
split='test' formats (bench/formats.py) is re-substituted with a fresh,
model-unseen value.

- Same sentinel raw text, same docs: only the substituted values change.
- rng is seeded from (seed, doc id) so runs are deterministic; every
  occurrence of one placeholder gets the same new value.
- NAME / LOCATION / ORG / ADDRESS keep their universe-C spec values
  (no novel formats registered for them — formats.py covers structured
  identifier shapes only; note in output via unchanged spans).
- After re-substitution the new text runs through verify_planted's real
  screens (caps/digits/date/phone/email/url/ip/institution/pool-phrase) so
  a novel value that collides with free text or a broken doc still rejects.
- dev/sealed split uses the same sha256(id) parity rule as verify_planted,
  so dev/sealed membership is identical to clin_dev/clin_sealed.

Usage:
  python bench/build_novel.py --spec bench/data/clin_spec.jsonl \
      --raw bench/data/clin_raw.jsonl --seed 23 \
      --out bench/data/clin_novel.jsonl [--rejects bench/data/clin_novel_rejects.jsonl]

Convention: spec clin_<X>.jsonl implies the accepted set clin_<X> is the
sibling clin_test.jsonl; if absent, all specs with raw output are tried.
"""
import argparse, hashlib, json, os, random, re, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import formats as fm
import verify_planted as vp


def _accepted_ids(spec_path, raw_path):
    """Doc ids that passed the original verification: convention
    clin_spec.jsonl -> clin_test.jsonl; else accept every spec id that has
    a raw record (caller's responsibility)."""
    m = re.match(r"(.*)_spec(_pilot)?\.jsonl$", os.path.basename(spec_path))
    cand = None
    if m:
        cand = os.path.join(os.path.dirname(spec_path),
                            f"{m.group(1)}_test.jsonl")
    if cand and os.path.exists(cand):
        return {json.loads(ln)["id"] for ln in open(cand, encoding="utf-8") if ln.strip()}, cand
    raws = {json.loads(ln)["id"] for ln in open(raw_path, encoding="utf-8") if ln.strip()}
    return raws, None


def novel_spec(spec, seed):
    """Copy of spec with test-formattable items' values replaced.
    -> (spec', {ph: (label, fmt_name)}). rng seeded by (seed, doc id) and
    consumed in planted order -> same doc always gets the same values."""
    sid = spec["id"]
    rng = random.Random(int(hashlib.sha256(f"novel:{seed}:{sid}".encode()).hexdigest()[:16], 16))
    planted, swapped = [], {}
    for it in spec["planted"]:
        it = dict(it)
        if fm.formats_for(it["label"], "test"):
            value, fname = fm.sample(it["label"], "test", rng)
            it["value"] = value
            # Retire shape tags that describe the OLD value; record the new one.
            it["tags"] = [t for t in it.get("tags", [])
                          if not t.startswith("fmt:") and t != "spoken"]
            it["tags"] += ["novel_format", f"fmt:{fname}"]
            swapped[it["ph"]] = (it["label"], fname)
        planted.append(it)
    return {**spec, "planted": planted}, swapped


def verify_novel_doc(spec2, raw):
    """verify_planted.verify_doc on the re-valued spec, sentinel mode only."""
    if spec2.get("spec_mode", "sentinel") != "sentinel":
        return None, ["spec-mode-not-sentinel"]
    return vp.verify_doc(spec2, raw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rejects", default=None)
    a = ap.parse_args()
    t0 = time.time()

    specs = [json.loads(ln) for ln in open(a.spec, encoding="utf-8") if ln.strip()]
    raws = {}
    for ln in open(a.raw, encoding="utf-8"):
        if ln.strip():
            r = json.loads(ln)
            raws[r["id"]] = r
    accepted_ids, acc_src = _accepted_ids(a.spec, a.raw)
    if acc_src:
        print(f"accepted-set source: {acc_src} ({len(accepted_ids)} docs)")

    out_docs, rejected, stats = [], [], Counter()
    for spec in specs:
        sid = spec["id"]
        if sid not in accepted_ids:
            stats["skipped-not-accepted"] += 1
            continue
        raw = raws.get(sid)
        if raw is None:
            rejected.append({"id": sid, "reasons": ["no-raw-output"]})
            continue
        spec2, swapped = novel_spec(spec, a.seed)
        rec, reasons = verify_novel_doc(spec2, raw)
        if rec is None:
            rejected.append({"id": sid, "reasons": reasons})
            continue
        for ph, (lab, fname) in swapped.items():
            stats[f"swap:{lab}"] += 1
            stats[f"fmt:{fname}"] += 1
        out_docs.append(rec)

    with open(a.out, "w", encoding="utf-8") as f:
        for d in out_docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    if a.rejects:
        with open(a.rejects, "w", encoding="utf-8") as f:
            for d in rejected:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
    dev_p, sealed_p = vp.split_paths(a.out)
    for path, want in ((dev_p, "dev"), (sealed_p, "sealed")):
        with open(path, "w", encoding="utf-8") as f:
            for d in out_docs:
                if d["split"] == want:
                    f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"accepted {len(out_docs)} / rejected {len(rejected)} "
          f"(skipped {stats['skipped-not-accepted']} non-accepted specs) in {time.time()-t0:.2f}s")
    print("reject reasons:", dict(Counter(r for d in rejected for r in d["reasons"]).most_common()))
    print("swaps per label:", {k[5:]: v for k, v in stats.most_common() if k.startswith("swap:")})
    print("swaps per format:", {k[4:]: v for k, v in stats.most_common() if k.startswith("fmt:")})
    lc = Counter(s["label"] for d in out_docs for s in d["spans"])
    print("label counts:", dict(lc.most_common()))
    print(f"split: dev={sum(1 for d in out_docs if d['split']=='dev')} "
          f"sealed={sum(1 for d in out_docs if d['split']=='sealed')} -> {dev_p}, {sealed_p}")


if __name__ == "__main__":
    main()
