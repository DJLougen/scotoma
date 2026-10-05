#!/usr/bin/env python3
"""Exact two-sided McNemar test on per-document leak indicators of two systems.

    python bench/mcnemar.py RESPONSES.csv SYSTEM_A SYSTEM_B

A document leaks under a system when any of its items has outcome 0. Counts
discordant documents (b = only A leaks, c = only B leaks) and gives the exact
binomial two-sided p-value under H0: b ~ Binomial(b+c, 0.5). Standard library only.
"""
import csv, sys
from collections import defaultdict
from math import comb


def exact_p(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, p)


def main():
    path, A, B = sys.argv[1:4]
    leak = defaultdict(lambda: [False, False])
    for r in csv.DictReader(open(path)):
        d = r["item"].rsplit("#", 1)[0]
        if r[A] == "" or r[B] == "": sys.exit(f"missing outcome on {r['item']}")
        leak[d][0] |= r[A] == "0"; leak[d][1] |= r[B] == "0"
    n = len(leak)
    a_only = sum(1 for x in leak.values() if x[0] and not x[1])
    b_only = sum(1 for x in leak.values() if x[1] and not x[0])
    both = sum(1 for x in leak.values() if x[0] and x[1])
    la, lb = a_only + both, b_only + both
    print(f"{n} docs | {A}: {la} leak ({100*la/n:.2f}%) | {B}: {lb} leak ({100*lb/n:.2f}%)")
    print(f"discordant: only {A} leaks {a_only}, only {B} leaks {b_only}, both {both}")
    print(f"exact McNemar two-sided p = {exact_p(a_only, b_only):.4g}")


if __name__ == "__main__":
    main()
