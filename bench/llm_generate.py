#!/usr/bin/env python3
"""Have an LLM write benchmark or training documents for a domain.

The template generator (generate.py) gives exact control over difficulty but
its prose is stilted. This script produces natural documents: it reads the
domain's policy file (domains/<domain>.json: which identifiers that field's
regulations name), asks a model to write realistic documents with every
identifier wrapped as {{LABEL|text}}, and converts them to benchmark JSONL.

    python bench/llm_generate.py --domain tax --n 500 --out bench/data/tax_llm.jsonl \\
        --base-url http://127.0.0.1:1234/v1 --model qwen3-32b

Works with any OpenAI-compatible endpoint (LM Studio, Ollama, vLLM, llama.cpp).
Standard library only. NOT run in the environment this was written in.

Use a DIFFERENT model for test data than for training data, and have a person
check a sample: LLMs miss tags and invent labels. Documents with unbalanced
or unknown tags are dropped and counted.
"""
import argparse, json, os, random, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATS = "NAME ADDRESS LOCATION ZIP DATE AGE PHONE FAX EMAIL SSN MRN PLAN ACCOUNT LICENSE VEHICLE DEVICE URL IP BIOMETRIC ID ORG".split()
STYLES = ["a formal letter", "terse internal notes with abbreviations", "an email thread", "a dictated memo transcribed by speech-to-text (numbers read out digit by digit, dates spoken)",
          "a chat message, lower-case and unpunctuated", "a form with labelled fields", "a narrative summary with no field labels at all", "text recovered by OCR with a few character errors"]
TAG = re.compile(r"\{\{([A-Z]+)\|(.*?)\}\}", re.S)


def prompt(policy, style, rng):
    ids = "\n".join(f"- {i['category']}: {', '.join(i['kinds']) or 'any'} ({i['treatment']})" for i in policy["identifiers"])
    return f"""Write one realistic but entirely fictional document from this field: {policy['title']}.
Form: {style}. Length: {rng.choice(['3-5 sentences', '1-2 short paragraphs', '2-3 paragraphs'])}.

Wrap EVERY identifying detail as {{{{LABEL|text}}}} using only these labels:
{ids}

Rules:
- Tag every occurrence, including repeats, bare first names, relatives and third parties.
- Invent unusual, diverse names; make a few of them ordinary words (May, Hunter, Rose).
- Put several identifiers where no label word announces them.
- Include domain terms that look like identifiers but are not (eponyms, form numbers, statute cites, scores, doses) and do NOT tag those.
- Use phone numbers in the 555-01xx range and example.com/.org/.net addresses.
- Output the document only. No preamble, no explanation."""


def chat(base, model, key, content, temperature):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": content}], "temperature": temperature}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", body, {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def parse(doc):
    """{{LABEL|text}} markup → (text, spans). None if malformed."""
    doc = re.sub(r"<think>.*?</think>", "", doc, flags=re.S).strip()
    text, spans, pos = "", [], 0
    for m in TAG.finditer(doc):
        if m.group(1) not in CATS: return None
        text += doc[pos:m.start()]
        spans.append({"start": len(text), "end": len(text) + len(m.group(2)), "label": m.group(1), "kind": "llm", "tags": ["llm"]})
        text += m.group(2)
        pos = m.end()
    text += doc[pos:]
    if "{{" in text or "}}" in text or not spans: return None
    return text, spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1"))
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "none"))
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    policy = json.load(open(os.path.join(ROOT, "domains", f"{a.domain}.json")))
    rng = random.Random(a.seed)
    kept = dropped = 0
    with open(a.out, "w", encoding="utf-8") as f:
        while kept < a.n and dropped < a.n * 3 + 20:
            style = rng.choice(STYLES)
            try:
                got = parse(chat(a.base_url, a.model, a.api_key, prompt(policy, style, rng), a.temperature))
            except Exception as e:
                print("request failed:", e); dropped += 1; continue
            if not got: dropped += 1; continue
            text, spans = got
            f.write(json.dumps({"id": f"{a.domain}-llm-{a.seed}-{kept:05d}", "domain": a.domain, "mode": "llm", "generator": a.model, "style": style, "text": text, "spans": spans}, ensure_ascii=False) + "\n")
            kept += 1
            if kept % 25 == 0: print(f"{kept}/{a.n} kept, {dropped} dropped")
    print(f"wrote {kept} documents to {a.out} ({dropped} malformed replies dropped)")


if __name__ == "__main__":
    main()
