#!/usr/bin/env python3
"""Compare systems at matched over-redaction from `scotoma sweep --json` files.

    python bench/matched.py NAME=SWEEP.json ... [--caps 0.001,0.005,0.01,0.02]

For each cap, picks each system's threshold with the fewest leak docs among
thresholds whose over-redaction is <= cap (ties: higher threshold). A system with
no threshold under the cap shows '–'. Selection uses only the sweep rows given;
report which data the sweeps were run on.
"""
import json, sys
caps = [0.001, 0.005, 0.01, 0.02]
args = [a for a in sys.argv[1:]]
if "--caps" in args:
    i = args.index("--caps"); caps = [float(x) for x in args[i + 1].split(",")]; del args[i:i + 2]
sw = {n: json.load(open(p)) for n, _, p in (a.partition("=") for a in args)}
print("| system | " + " | ".join(f"over-red ≤ {c*100:g}%" for c in caps) + " |")
print("|---|" + "---|" * len(caps))
for n, rows in sw.items():
    cells = []
    for c in caps:
        ok = [r for r in rows if r["over_redaction"] <= c]
        if not ok: cells.append("–"); continue
        b = min(ok, key=lambda r: (r["leak_docs"], -r["threshold"]))
        cells.append(f"{b['leak_docs']} leak docs, recall {100*b['recall']:.1f} @ t={b['threshold']:.2f} (over-red {100*b['over_redaction']:.2f}%)")
    print(f"| {n} | " + " | ".join(cells) + " |")
