#!/usr/bin/env python3
"""One-command DEV-tier test battery for a Scotoma model.

    python bench/battery.py models/scotoma-v0-int8pc --threshold 0.02
    python bench/battery.py models/scotoma-v0-int8pc --name v1 --threshold 0.02 \\
        --baseline bench/results/battery/scotoma-v0-int8pc/scorecard.json
    python bench/battery.py models/scotoma-v0-int8pc --threshold 0.02 --quick 150

Every set is scored through bench/run.py (which drives `scotoma eval`), so a
battery row is exactly the same number as any other results run. Sets:

    tpl_test        bench/data/test_tpl.jsonl        (universe B, --strict)
    nemo_test       bench/data/nemo_test.jsonl
    clin_dev        bench/data/clin_dev_tagged.jsonl
    clin_novel_dev  bench/data/clin_novel_dev.jsonl  (skipped if absent)
    sweep           `scotoma sweep --json` on clin_dev

Writes <out>/scorecard.md + scorecard.json plus per-set run.py artefacts under
<out>/sets/. Gates (exit code 1 on any failure):

    over_redaction   <= 1% on every set, per system
    leak_regression  leak-doc rate on clin_dev / clin_novel_dev no more than
                     0.5 pp above --baseline scorecard (skip without baseline)
    int8_fp32_gap    |recall(model_fp32.onnx) - recall(model_quantized.onnx)|
                     <= 0.5 pp on clin_dev, when both files exist

Safety: any data/output/model/baseline path containing "sealed" is a hard
error. This battery only ever touches dev-tier files; the sealed half of the
clinical set is never opened, let alone scored.

    python bench/battery.py --selftest    # sealed-path guard checks only
"""
import argparse, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(ROOT, "bench")
DATA = os.path.join(BENCH, "data")

SETS = [  # (key, path, strict, optional)
    ("tpl_test", os.path.join(DATA, "test_tpl.jsonl"), True, False),
    ("nemo_test", os.path.join(DATA, "nemo_test.jsonl"), False, False),
    ("clin_dev", os.path.join(DATA, "clin_dev_tagged.jsonl"), False, False),
    ("clin_novel_dev", os.path.join(DATA, "clin_novel_dev.jsonl"), False, True),
]
CLINICAL = {"clin_dev", "clin_novel_dev"}
OVER_RED_LIMIT = 0.01          # 1% of clean characters
LEAK_REGRESSION_PP = 0.005     # 0.5 percentage points over baseline
INT8_FP32_GAP = 0.005          # 0.5 pp recall gap


def die(msg):
    sys.exit(f"battery: {msg}")


def no_sealed(path, what):
    """Hard-refuse any path containing 'sealed' (the sealed half is never touched)."""
    if path and "sealed" in os.path.abspath(path).lower():
        die(f"refusing sealed path for {what}: {path}")


def find_cli():
    for p in (os.environ.get("SCOTOMA_BIN"), os.path.join(ROOT, "target/release/scotoma"),
              os.path.join(ROOT, "target/debug/scotoma")):
        if p and os.path.exists(p):
            return p
    die("build the CLI first: cargo build --release -p scotoma")


def first_n(src, dst, n):
    m = 0
    with open(src, encoding="utf-8") as f, open(dst, "w", encoding="utf-8") as g:
        for line in f:
            if m >= n:
                break
            if line.strip():
                g.write(line)
                m += 1
    return m


def run_py(data, systems, out, strict, threshold):
    """Score `systems` on `data` via bench/run.py; return {name: report}."""
    os.makedirs(out, exist_ok=True)
    cmd = [sys.executable, os.path.join(BENCH, "run.py"), data, "--out", out]
    for s in systems:
        cmd += ["--system", s]
    if strict:
        cmd.append("--strict")
    if threshold is not None:
        cmd += ["--threshold", str(threshold)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        die(f"run.py failed on {data}:\n{r.stdout}\n{r.stderr}")
    return json.load(open(os.path.join(out, "reports.json")))


def run_sweep(cli, data, model, rules_on, out):
    cmd = [cli, "sweep", data, "--model", model, "--json"]
    if not rules_on:
        cmd.append("--no-rules")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        die(f"sweep failed: {r.stderr.strip()}")
    rows = json.loads(r.stdout)
    json.dump(rows, open(os.path.join(out, "sweep.json"), "w"), indent=1)
    return rows


def metrics(rep):
    o = rep["overall"]
    return {
        "docs": rep["docs"],
        "recall": o["caught"] / o["gold"] if o["gold"] else None,
        "full": o["full"] / o["gold"] if o["gold"] else None,
        "precision": o["predicted_correct"] / o["predicted"] if o["predicted"] else None,
        "leak_docs": rep["docs_with_leak"],
        "leak_rate": rep["docs_with_leak"] / rep["docs"] if rep["docs"] else None,
        "over_redaction": rep["over_redaction"],
        "ms_per_doc": rep["ms_per_doc"],
        "by_category": {k: (v["caught"] / v["gold"] if v["gold"] else None)
                        for k, v in rep.get("by_category", {}).items()},
        "by_category_n": {k: v["gold"] for k, v in rep.get("by_category", {}).items()},
    }


def fp32_dir(model_dir, work):
    """If model_fp32.onnx sits beside the quantized model, make a shadow dir
    that exports it as model.onnx (the loader ignores *_fp32.onnx)."""
    fp = os.path.join(model_dir, "model_fp32.onnx")
    if not os.path.exists(fp):
        return None
    os.makedirs(work, exist_ok=True)
    for src, dst in [(fp, "model.onnx"),
                     (os.path.join(model_dir, "tokenizer.json"), "tokenizer.json"),
                     (os.path.join(model_dir, "config.json"), "config.json")]:
        tgt = os.path.join(work, dst)
        if os.path.exists(tgt):
            os.remove(tgt)
        os.symlink(os.path.abspath(src), tgt)
    return work


def fnum(x, pct=True):
    if x is None:
        return "–"
    return f"{100 * x:.1f}" if pct else f"{x:.1f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", nargs="?", help="model dir containing model_quantized.onnx, tokenizer.json, config.json")
    ap.add_argument("--name", default=None, help="system name in tables (default: model dir basename)")
    ap.add_argument("--threshold", default=None, help="decoder threshold (default: CLI/model default 0.35)")
    ap.add_argument("--rules", choices=["both", "off", "on"], default="both",
                    help="off = model alone, on = rules+model only, both = score both")
    ap.add_argument("--out", default=None, help="default bench/results/battery/<name>")
    ap.add_argument("--quick", nargs="?", const=150, type=int, default=None,
                    help="score only the first N docs of each set (default 150)")
    ap.add_argument("--baseline", default=None, help="scorecard.json from a previous run for the leak-regression gate")
    ap.add_argument("--selftest", action="store_true", help="run guard self-tests and exit")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return

    if not a.model:
        die("need a model dir")
    model = os.path.abspath(a.model)
    name = a.name or os.path.basename(model.rstrip("/"))
    out = os.path.abspath(a.out or os.path.join(ROOT, "bench/results/battery", name))

    # ---- sealed guard: check every path we will read or write --------------
    for p, w in [(model, "model"), (out, "output"), (a.baseline, "baseline")] + \
                [(p, f"set {k}") for k, p, _, _ in SETS]:
        no_sealed(p, w)
    if not os.path.isdir(model):
        die(f"model dir not found: {model}")

    cli = find_cli()
    systems, spec = [], f"{name}={model}"
    if a.rules in ("both", "off"):
        systems.append(spec)
    if a.rules in ("both", "on"):
        systems.append(f"rules+{name}={model}")
    primary = spec if a.rules in ("both", "off") else f"rules+{name}={model}"
    primary = primary.split("=")[0]

    t0 = time.time()
    score = {"model": model, "name": name, "threshold": a.threshold, "rules": a.rules,
             "quick": a.quick, "date": time.strftime("%Y-%m-%d %H:%M:%S"), "sets": {}, "sweep": None,
             "gates": [], "baseline": a.baseline}

    # ---- per-set scoring ----------------------------------------------------
    for key, path, strict, optional in SETS:
        if not os.path.exists(path):
            if optional:
                print(f"[{key}] {path} not present — skipping")
                continue
            die(f"missing required set {path}")
        data = path
        if a.quick:
            qd = os.path.join(out, "quick")
            os.makedirs(qd, exist_ok=True)
            data = os.path.join(qd, f"{key}.jsonl")
            n = first_n(path, data, a.quick)
            print(f"[{key}] quick subset: first {n} docs -> {data}")
        print(f"[{key}] scoring {' + '.join(s.split('=')[0] for s in systems)} ...", flush=True)
        reps = run_py(data, systems, os.path.join(out, "sets", key), strict, a.threshold)
        score["sets"][key] = {"path": os.path.relpath(data, ROOT), "strict": strict,
                              "systems": {s.split("=")[0]: metrics(reps[s.split("=")[0]]) for s in systems}}

    # ---- fp32 shadow run (int8 vs fp32 gate) --------------------------------
    fp32 = fp32_dir(model, os.path.join(out, "fp32_model"))
    if fp32 and "clin_dev" in score["sets"]:
        fp_systems = [s.replace(f"={model}", f"={fp32}") for s in systems]
        reps = run_py(score["sets"]["clin_dev"]["path"], fp_systems,
                      os.path.join(out, "sets", "clin_dev_fp32"), False, a.threshold)
        score["sets"]["clin_dev_fp32"] = {"path": score["sets"]["clin_dev"]["path"],
                                          "systems": {s.split("=")[0]: metrics(reps[s.split("=")[0]])
                                                      for s in fp_systems}}

    # ---- threshold sweep on clinical dev ------------------------------------
    if "clin_dev" in score["sets"]:
        print("[sweep] threshold sweep on clin_dev ...", flush=True)
        score["sweep"] = run_sweep(cli, score["sets"]["clin_dev"]["path"], model,
                                   rules_on=a.rules != "off", out=out)

    # ---- gates ----------------------------------------------------------------
    gates = score["gates"]

    def gate(gname, setkey, system, actual, limit, ok, note=""):
        gates.append({"gate": gname, "set": setkey, "system": system, "actual": actual,
                      "limit": limit, "pass": bool(ok), "note": note})

    for key, sdata in score["sets"].items():
        if key.endswith("_fp32"):
            continue
        for sysname, m in sdata["systems"].items():
            gate("over_redaction", key, sysname, m["over_redaction"], OVER_RED_LIMIT,
                 m["over_redaction"] <= OVER_RED_LIMIT)

    if a.baseline:
        base = json.load(open(a.baseline))
        bprim = base.get("primary") or base.get("name")
        for key in ("clin_dev", "clin_novel_dev"):
            if key not in score["sets"] or key not in base.get("sets", {}):
                continue
            bsys = base["sets"][key]["systems"]
            bname = bprim if bprim in bsys else next(iter(bsys))
            cur = score["sets"][key]["systems"][primary]["leak_rate"]
            prev = bsys[bname]["leak_rate"]
            gate("leak_regression", key, primary, cur, prev + LEAK_REGRESSION_PP,
                 cur <= prev + LEAK_REGRESSION_PP,
                 f"baseline {bname} leak {100 * prev:.2f}% -> {100 * cur:.2f}%")

    if "clin_dev_fp32" in score["sets"]:
        fsys = score["sets"]["clin_dev_fp32"]["systems"]
        for sysname in list(score["sets"]["clin_dev"]["systems"]):
            if sysname in fsys:
                i8, f32 = score["sets"]["clin_dev"]["systems"][sysname]["recall"], fsys[sysname]["recall"]
                gate("int8_fp32_gap", "clin_dev", sysname, abs(f32 - i8), INT8_FP32_GAP,
                     abs(f32 - i8) <= INT8_FP32_GAP,
                     f"int8 {100 * i8:.2f}% vs fp32 {100 * f32:.2f}%")

    score["primary"] = primary
    score["pass"] = all(g["pass"] for g in gates)
    score["wall_s"] = round(time.time() - t0, 1)

    # ---- write scorecard ------------------------------------------------------
    write_md(score, out)
    json.dump(score, open(os.path.join(out, "scorecard.json"), "w"), indent=1)
    print(f"\nscorecard: {out}/scorecard.md  + scorecard.json")
    print(f"verdict: {'PASS' if score['pass'] else 'FAIL'}  ({sum(g['pass'] for g in gates)}/{len(gates)} gates, {score['wall_s']}s)")
    sys.exit(0 if score["pass"] else 1)


def write_md(score, out):
    L = [f"# Battery scorecard: {score['name']}", "",
         f"model `{score['model']}` · threshold {score['threshold'] or '0.35 (default)'} · rules {score['rules']}"
         + (f" · **quick: first {score['quick']} docs per set**" if score["quick"] else "")
         + f" · {score['date']} · {score['wall_s']}s", ""]
    L += ["| set | docs | system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |",
          "|---|---|---|---|---|---|---|---|---|"]
    for key, sdata in score["sets"].items():
        for sysname, m in sdata["systems"].items():
            L.append(f"| {key} | {m['docs']} | {sysname} | {fnum(m['recall'])} | {fnum(m['full'])} | "
                     f"{m['leak_docs']}/{m['docs']} ({fnum(m['leak_rate'])}%) | {fnum(m['over_redaction'])}% | "
                     f"{fnum(m['precision'])} | {fnum(m['ms_per_doc'], False)} |")
    for key in ("clin_dev", "clin_novel_dev"):
        if key not in score["sets"]:
            continue
        sysname = score["primary"]
        m = score["sets"][key]["systems"].get(sysname) or next(iter(score["sets"][key]["systems"].values()))
        cats = sorted(m["by_category"], key=lambda c: m["by_category_n"].get(c, 0), reverse=True)
        L += ["", f"## {key}: recall by category ({sysname})", "", "| category | n | recall |", "|---|---|---|"]
        L += [f"| {c} | {m['by_category_n'].get(c, 0)} | {fnum(m['by_category'][c])} |" for c in cats]
    if score["sweep"]:
        L += ["", "## Threshold sweep on clin_dev", "",
              "| threshold | recall | full | precision | leak docs | over-redaction |", "|---|---|---|---|---|---|"]
        for r in score["sweep"]:
            L.append(f"| {r['threshold']} | {fnum(r['recall'])} | {fnum(r['full'])} | {fnum(r['precision'])} | "
                     f"{r['leak_docs']} | {fnum(r['over_redaction'])}% |")
    L += ["", "## Gates", "", "| gate | set | system | actual | limit | result |", "|---|---|---|---|---|---|"]
    for g in score["gates"]:
        L.append(f"| {g['gate']} | {g['set']} | {g['system']} | {g['actual']:.4f} | {g['limit']:.4f} | "
                 f"{'PASS' if g['pass'] else '**FAIL**'} |" + (f" {g['note']}" if g["note"] else ""))
    L += ["", f"## Verdict: {'PASS — all gates green' if score['pass'] else 'FAIL'}", ""]
    open(os.path.join(out, "scorecard.md"), "w").write("\n".join(L))


def selftest():
    """Prove the sealed-path guard fires. No model or data needed."""
    ok = 0
    for bad in ["bench/data/clin_sealed.jsonl", "x/SEALED/y.jsonl", "/tmp/a_sealed_b"]:
        try:
            no_sealed(bad, "selftest")
        except SystemExit:
            ok += 1
        else:
            die(f"selftest: sealed path not refused: {bad}")
    no_sealed("bench/data/clin_dev_tagged.jsonl", "selftest")   # must NOT fire
    print(f"selftest OK: {ok} sealed paths refused, dev path accepted")


if __name__ == "__main__":
    main()
