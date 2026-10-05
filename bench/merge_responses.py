#!/usr/bin/env python3
"""Join responses.csv files from separate bench/run.py runs on the same data into one matrix.

    python bench/merge_responses.py OUT.csv A/responses.csv B/responses.csv [--drop SYSTEM ...]

Items must match exactly across files (same data, same scorer); fails closed otherwise.
The scorer is deterministic, so columns from different runs are comparable.
"""
import argparse, csv, sys

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("inputs", nargs="+")
ap.add_argument("--drop", action="append", default=[])
a = ap.parse_args()
cols, items = {}, None
for p in a.inputs:
    rows = list(csv.DictReader(open(p)))
    ids = [r["item"] for r in rows]
    if items is None: items = ids
    elif set(ids) != set(items): sys.exit(f"{p}: item set differs ({len(ids)} vs {len(items)})")
    for name in rows[0]:
        if name == "item" or name in a.drop: continue
        col = {r["item"]: r[name] for r in rows}
        if name in cols and cols[name] != col: sys.exit(f"{p}: column {name} disagrees with an earlier file")
        cols[name] = col
with open(a.out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["item"] + list(cols))
    for it in items: w.writerow([it] + [cols[n][it] for n in cols])
print(f"{a.out}: {len(items)} items x {len(cols)} systems: {', '.join(cols)}")
