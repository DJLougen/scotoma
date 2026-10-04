"""Turn a Hugging Face PII dataset into the JSONL the benchmark reads.

    pip install datasets
    python scripts/prep_dataset.py nvidia/Nemotron-PII --split test --limit 2000 --out eval/nemotron_test.jsonl
    scotoma eval eval/nemotron_test.jsonl --model app/src-tauri/models/default

Handles the usual layouts: a text column plus a list (or JSON/repr string) of
{start, end, label} dicts. NOTE: not run in the environment this project was
built in (no access to huggingface.co there); check the first printed row.
"""
import argparse, ast, json

TEXT = ["text", "source_text", "full_text", "document"]
SPANS = ["spans", "entities", "privacy_mask", "labels"]
LABEL = ["label", "entity_type", "type", "entity"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    from datasets import load_dataset
    ds = load_dataset(a.dataset, split=a.split)
    ds = ds.shuffle(seed=0).select(range(min(a.limit, len(ds))))
    tcol = next(c for c in TEXT if c in ds.column_names)
    scol = next(c for c in SPANS if c in ds.column_names)
    n = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for row in ds:
            spans = row[scol]
            if isinstance(spans, str):
                try: spans = json.loads(spans)
                except json.JSONDecodeError: spans = ast.literal_eval(spans)
            out = []
            for s in spans or []:
                lab = next((s[k] for k in LABEL if k in s), None)
                if lab is None or "start" not in s or "end" not in s: continue
                out.append({"start": int(s["start"]), "end": int(s["end"]), "label": str(lab)})
            rec = {"text": row[tcol], "spans": out}
            if n == 0: print("first row:", json.dumps(rec)[:400])
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} documents to {a.out}")

if __name__ == "__main__":
    main()
