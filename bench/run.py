#!/usr/bin/env python3
"""Score several systems on one benchmark file and compare them.

    python bench/run.py bench/data/test.jsonl --out bench/results \\
        --system rules \\
        --system ours=models/scotoma-v0 \\
        --system rules+ours=models/scotoma-v0 \\
        --system openmed=app/src-tauri/models/default

A system is `rules`, `NAME=MODEL_DIR` (model alone) or `rules+NAME=MODEL_DIR`.
Any Hugging Face token-classification model exported to ONNX can be a system,
so competitors are scored by exactly the same code as ours.

Writes results.md (the comparison) and responses.csv (items x systems, with
0 = missed, 1 = partly redacted, 2 = fully redacted) for IRT or any other
item-level analysis. Standard library only.
"""
import argparse, csv, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_cli():
    for p in [os.environ.get("SCOTOMA_BIN"), os.path.join(ROOT, "target/release/scotoma"), os.path.join(ROOT, "target/debug/scotoma")]:
        if p and os.path.exists(p): return p
    sys.exit("build the CLI first: cargo build --release -p scotoma")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--system", action="append", required=True)
    ap.add_argument("--out", default="bench/results")
    ap.add_argument("--strict", action="store_true", help="count organisations and quasi-identifiers (law, tax, HR policies)")
    ap.add_argument("--threshold", default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cli, reports, resp, names = find_cli(), {}, {}, []
    for spec in a.system:
        name, _, model = spec.partition("=")
        rules = name == "rules" or name.startswith("rules+")
        cmd = [cli, "eval", a.data, "--json", "--misses", "0", "--responses", os.path.join(a.out, f".{name}.csv")]
        cmd += ["--model", model] if model else ["--no-model"]
        if not rules: cmd.append("--no-rules")
        if a.strict: cmd.append("--strict")
        if a.threshold: cmd += ["--threshold", a.threshold]
        print("running", name, "...", flush=True)
        out = subprocess.run(cmd, capture_output=True, text=True)
        if out.returncode != 0: sys.exit(f"{name} failed: {out.stderr.strip()}")
        reports[name] = json.loads(out.stdout); names.append(name)
        with open(os.path.join(a.out, f".{name}.csv")) as f:
            resp[name] = {r["item"]: r["outcome"] for r in csv.DictReader(f)}
        os.remove(os.path.join(a.out, f".{name}.csv"))

    def pct(st, key="caught"): return "–" if not st or not st["gold"] else f"{100*st[key]/st['gold']:.1f}"
    def prec(st): return "–" if not st["predicted"] else f"{100*st['predicted_correct']/st['predicted']:.1f}"
    L = [f"# {os.path.basename(a.data)}", "", "Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.", "",
         "Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).", "",
         "| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |", "|---|---|---|---|---|---|---|"]
    for n in names:
        r = reports[n]; o = r["overall"]
        L.append(f"| {n} | {pct(o)} | {pct(o,'full')} | {r['docs_with_leak']}/{r['docs']} ({100*r['docs_with_leak']/max(1,r['docs']):.1f}%) | {100*r['over_redaction']:.1f}% | {prec(o)} | {r['ms_per_doc']:.1f} |")
    for title, key in [("By domain", "by_domain"), ("By input mode", "by_mode"), ("By difficulty tag", "by_tag"), ("By category", "by_category")]:
        keys = sorted({k for n in names for k in reports[n][key]})
        if not keys: continue
        L += ["", f"## {title} (recall %)", "", "| | n | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
        for k in keys:
            n_items = max(reports[n][key].get(k, {}).get("gold", 0) for n in names)
            if n_items: L.append(f"| {k} | {n_items} | " + " | ".join(pct(reports[n][key].get(k)) for n in names) + " |")
    open(os.path.join(a.out, "results.md"), "w").write("\n".join(L) + "\n")
    items = sorted(set().union(*[set(v) for v in resp.values()]))
    with open(os.path.join(a.out, "responses.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["item"] + names)
        for it in items: w.writerow([it] + [resp[n].get(it, "") for n in names])
    print("\n".join(L[:8 + len(names)]))
    print(f"\nfull tables: {a.out}/results.md   item responses: {a.out}/responses.csv ({len(items)} items x {len(names)} systems)")


if __name__ == "__main__":
    main()
