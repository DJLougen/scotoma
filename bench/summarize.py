#!/usr/bin/env python3
"""Collect the headline row of every system from several results.md files into one table.

    python bench/summarize.py OUT.md TITLE results_dir1 results_dir2 ... [--only sys1,sys2]

Rows are copied verbatim from each run's results.md (no recomputation), sorted by leak-doc rate.
"""
import os, re, sys

out, title, dirs = sys.argv[1], sys.argv[2], [d for d in sys.argv[3:] if not d.startswith("--")]
only = None
if "--only" in sys.argv: only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
rows, seen = [], set()
for d in dirs:
    if d == (only and sys.argv[sys.argv.index("--only") + 1]): continue
    for line in open(os.path.join(d, "results.md")):
        m = re.match(r"\| ([^|]+) \| ([\d.–]+) \| ([\d.–]+) \| (\d+)/(\d+) \(([\d.]+)%\) \| ([\d.]+)% \| ([\d.–]+) \| ([\d.]+) \|", line)
        if not m: continue
        name = m.group(1).strip()
        if (only and name not in only) or name in seen: continue
        seen.add(name); rows.append((float(m.group(6)), line.strip(), d))
rows.sort()
L = [f"# {title}", "", "| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc | source |", "|---|---|---|---|---|---|---|---|"]
L += [r[1] + f" `{os.path.basename(r[2])}` |" for r in rows]
open(out, "w").write("\n".join(L) + "\n"); print("\n".join(L))
