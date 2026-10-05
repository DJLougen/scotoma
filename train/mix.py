#!/usr/bin/env python3
"""Assemble a training mix from labelled JSONL sources. Standard library only.

    python train/mix.py --out bench/data/train_v1.jsonl \\
        --manifest bench/data/train_v1.manifest.json \\
        --source planted=bench/data/train_planted.jsonl:30 \\
        --source nemo=bench/data/nemo_train.jsonl:60 \\
        --source tpl=bench/data/train_tpl.jsonl:10 \\
        --total 60000 --seed 0

Defaults match the plan: planted-LLM 30%, Nemotron train 60%, universe-A
templates 10% (templates capped low — they cause over-redaction if they
dominate).

Each --source is NAME=PATH:RATIO. RATIO is a share of --total (ratios are
normalised if they don't sum to 1); counts are deterministic largest-
remainder allocations. A source with fewer docs than its share fails closed.

Hard refusals (leak containment):
  - any path/record containing 'sealed', 'dev', 'clin_test' or 'clin_novel'
    in its name is refused;
  - records carrying a 'split' field must say 'train' (planted records do);
    a 'dev'/'sealed' record aborts the mix.

If the default template source bench/data/train_tpl.jsonl is missing it is
regenerated deterministically:
    python3 bench/generate.py --universe A --n 30000 --seed 7 --out bench/data/train_tpl.jsonl

The manifest records every source (path, sha256, count), the ratio, the seed,
generator models recovered from records/sidecar manifests, and the output
sha256 — every trained model points back at its manifest.
"""
import argparse, hashlib, json, os, random, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "bench", "data")

BANNED = ("sealed", "dev", "clin_test", "clin_novel")

DEFAULT_SOURCES = [
    ("planted", os.path.join(DATA, "train_planted.jsonl"), 30.0),
    ("nemo", os.path.join(DATA, "nemo_train.jsonl"), 60.0),
    ("tpl", os.path.join(DATA, "train_tpl.jsonl"), 10.0),
]


def die(msg):
    sys.exit(f"mix: {msg}")


def check_path(p, what):
    low = os.path.basename(p).lower()
    if any(b in low for b in BANNED):
        die(f"refusing {what} path {p!r} (contains banned marker)")
    if os.path.basename(p) == "dev_tpl.jsonl":
        die(f"refusing {what} path {p!r}")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_source(s):
    m = re.match(r"^([A-Za-z0-9_-]+)=(.+):(\d+(?:\.\d+)?)$", s)
    if not m:
        die(f"bad --source {s!r} (want name=path:ratio)")
    return m.group(1), m.group(2), float(m.group(3))


def ensure_tpl(path):
    """Regenerate the default template source if it is missing."""
    if os.path.exists(path):
        return
    if os.path.abspath(path) != os.path.abspath(os.path.join(DATA, "train_tpl.jsonl")):
        die(f"missing source {path}")
    cmd = [sys.executable, os.path.join(ROOT, "bench", "generate.py"),
           "--universe", "A", "--n", "30000", "--seed", "7", "--out", path]
    print(f"mix: regenerating {os.path.basename(path)}: {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode or not os.path.exists(path):
        die("template regeneration failed")


def load_source(name, path):
    check_path(path, f"source {name!r}")
    recs = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            d = json.loads(line)
            split = d.get("split")
            if split is not None and split != "train":
                die(f"{path}:{ln} record {d.get('id', '?')!r} has split={split!r} — not training data")
            recs.append(d)
    models = sorted({str(d.get("generator")) for d in recs if d.get("generator")})
    # A gen manifest sidecar (raw file + .manifest.json) names the LLM too.
    side = path + ".manifest.json"
    if os.path.exists(side):
        try:
            m = json.load(open(side, encoding="utf-8"))
            if m.get("model"):
                models = sorted(set(models) | {m["model"]})
        except Exception:
            pass
    return recs, models


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--source", action="append",
                    help="NAME=PATH:RATIO (repeatable). Default: planted 30 / nemo 60 / tpl 10")
    ap.add_argument("--total", type=int, default=60000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    check_path(a.out, "--out")
    check_path(a.manifest, "--manifest")
    sources = [parse_source(s) for s in a.source] if a.source else DEFAULT_SOURCES
    if not sources:
        die("no sources")
    wsum = sum(w for _, _, w in sources)
    if wsum <= 0:
        die("source ratios sum to 0")
    # exact counts: floor each share, hand the remainder to the biggest leftovers
    shares = [(n, p, w / wsum * a.total) for n, p, w in sources]
    counts = {n: int(s) for n, _, s in shares}
    left = a.total - sum(counts.values())
    for n, _, s in sorted(shares, key=lambda t: t[2] - int(t[2]), reverse=True)[:left]:
        counts[n] += 1

    rng = random.Random(a.seed)
    picked, meta = [], []
    for name, path, want in sources:
        if name == "tpl":
            ensure_tpl(path)
        recs, models = load_source(name, path)
        need = counts[name]
        if len(recs) < need:
            die(f"source {name!r} has {len(recs)} docs < required {need}")
        idx = list(range(len(recs)))
        rng.shuffle(idx)
        take = [recs[i] for i in idx[:need]]
        picked += take
        meta.append({"name": name, "path": os.path.abspath(path), "sha256": sha256_file(path),
                     "records": len(recs), "taken": need, "ratio": want / wsum,
                     "generator_models": models})
    rng.shuffle(picked)
    with open(a.out, "w", encoding="utf-8") as f:
        for d in picked:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    manifest = {"generator": "train/mix.py", "seed": a.seed, "total": len(picked),
                "sources": meta, "out": os.path.abspath(a.out), "out_sha256": sha256_file(a.out)}
    with open(a.manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"wrote {len(picked)} records to {a.out}")
    for m in meta:
        print(f"  {m['name']}: {m['taken']} of {m['records']} ({m['ratio'] * 100:.0f}%) {os.path.relpath(m['path'], ROOT)}")
    print(f"manifest: {a.manifest}")


if __name__ == "__main__":
    main()
