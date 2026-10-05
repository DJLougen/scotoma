#!/usr/bin/env python3
"""Paired bootstrap of the leak-document rate difference between systems.

    python bench/bootstrap.py RESPONSES.csv REF [OTHER ...] [--n 1000] [--seed 0]

A document leaks under a system when any of its items has outcome 0 (untouched).
For each OTHER, it resamples documents with replacement and reports
rate(OTHER) - rate(REF) with a 95% percentile interval. A positive difference
means REF leaks less. Standard library only.
"""
import argparse, csv, random
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("responses"); ap.add_argument("ref"); ap.add_argument("others", nargs="*")
    ap.add_argument("--n", type=int, default=1000); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.responses)))
    systems = [s for s in rows[0] if s != "item"]
    others = a.others or [s for s in systems if s != a.ref]
    leak = defaultdict(lambda: defaultdict(bool))
    for r in rows:
        doc = r["item"].rsplit("#", 1)[0]
        for s in systems:
            if r[s] == "": raise SystemExit(f"missing outcome for {s} on {r['item']}")
            leak[doc][s] |= r[s] == "0"
    docs = sorted(leak)
    rng = random.Random(a.seed)
    samples = [[rng.randrange(len(docs)) for _ in docs] for _ in range(a.n)]
    rate = lambda s, idx: sum(leak[docs[i]][s] for i in idx) / len(idx)
    full = range(len(docs))
    print(f"{len(docs)} docs, {a.n} resamples, reference {a.ref} leak rate {100*rate(a.ref, full):.1f}%")
    print("| system | leak rate | diff vs ref (pp) | 95% CI | verdict |\n|---|---|---|---|---|")
    for o in others:
        d = 100 * (rate(o, full) - rate(a.ref, full))
        ds = sorted(100 * (rate(o, idx) - rate(a.ref, idx)) for idx in samples)
        lo, hi = ds[int(0.025 * a.n)], ds[int(0.975 * a.n) - 1]
        v = "ref better" if lo > 0 else "ref worse" if hi < 0 else "tie"
        print(f"| {o} | {100*rate(o, full):.1f}% | {d:+.1f} | [{lo:+.1f}, {hi:+.1f}] | {v} |")


if __name__ == "__main__":
    main()
