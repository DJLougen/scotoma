#!/usr/bin/env python3
"""Planted-value clinical TEST set generator. Standard library only.

We choose every identifier value ourselves ("plant" it), an LLM writes a
natural clinical note around it, and bench/verify_planted.py recovers exact
character offsets deterministically. No LLM-produced tags are ever trusted.

Two spec modes:

  sentinel (default)  The LLM never sees real values. The prompt lists typed
      placeholders like [[NAME_1]], [[NAME_1_LAST]] (same patient by surname
      only), [[MRN_1]] ... each with a role description, and instructs the
      model to emit each placeholder exactly as written, the required number
      of times, with no other identifying details. verify_planted substitutes
      the spec's values left-to-right, so label offsets are known BY
      CONSTRUCTION — determinism of labels comes from substitution, not from
      the generator model.

  verbatim            The prompt lists the literal values and demands each
      appear verbatim; verify_planted recovers offsets by exact string
      search with word-boundary checks. Kept for comparison.

    python bench/plant_generate.py spec --n 2000 --seed 11 --out bench/data/clin_spec.jsonl
    python bench/plant_generate.py gen bench/data/clin_spec.jsonl \\
        --base-url http://127.0.0.1:8000/v1 --model google/diffusiongemma-26B-A4B-it \\
        --out bench/data/clin_raw.jsonl --workers 8

Universe C: test-only value pools disjoint from generate.py's A (train) and
B (test). The COMMON_FIRST/COMMON_LAST lists count as B (Gen.person draws
from them for universe B), so they are excluded from C too — asserted at
import time. This set is a constructed, deterministically-labelled TEST set;
it does not replace a human-checked natural gold set for public/marketing
claims.

Generator model: google/diffusiongemma-26B-A4B-it (Apache-2.0, Gemma 4 chat
template) served by vLLM >= 0.24 on a Colab A100. Training data should later
use a different model family; the model id, vLLM version and sampling params
are recorded in <out>.manifest.json next to the raw outputs.
"""
import argparse, hashlib, json, os, random, re, sys, threading, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as g

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "names")

# ----------------------------------------------------------------------------
# Universe C pools. Disjoint from A and B, AND from the COMMON_* name lists
# (those belong to B's person generator). Asserted below.
# ----------------------------------------------------------------------------

def _load_names(fname):
    with open(os.path.join(NAMES_DIR, fname), encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def _cap(word):
    """'o'connor' -> \"O'Connor\", 'smith-jones' -> 'Smith-Jones'."""
    return re.sub(r"(^|[-' ])([a-z])", lambda m: m.group(1) + m.group(2).upper(), word)


def _build_name_pools():
    """C first/last pools: copied name lists minus every string B can emit."""
    blocked = {n.lower() for n in g.FIRST["A"] + g.FIRST["B"] + g.LAST["A"] + g.LAST["B"]
               + g.COMMON_FIRST + g.COMMON_LAST}
    firsts = [_cap(w) for w in _load_names("first_names.txt") if w.lower() not in blocked]
    lasts = [_cap(w) for w in _load_names("surnames.txt") if w.lower() not in blocked]
    if len(firsts) < 50 or len(lasts) < 50:  # fall back to a fixed pool
        firsts = ["Aleron", "Bexley", "Caspian", "Delmira", "Elsinore", "Faustino", "Gisborne", "Hollis",
                  "Iver", "Jorunn", "Kestrel", "Liora", "Morven", "Niall", "Ottavia", "Perrin",
                  "Quillon", "Roswitha", "Sable", "Theron", "Una", "Virelai", "Wendelin", "Xanthe"]
        lasts = ["Abernathy", "Braidwood", "Carmody", "Dunmore", "Ellery", "Fenwick", "Grimsley", "Halloway",
                 "Inverness", "Jellicoe", "Kingsmill", "Loxley", "Merridew", "Norcastle", "Oxenford", "Pemberton",
                 "Quarles", "Ravensworth", "Stamford", "Thistledown", "Ullswater", "Vanderholm", "Winterbourne", "Yardley"]
    return firsts, lasts


C_FIRST, C_LAST = _build_name_pools()

C_STREET = "Bexhill Cranborne Dewhurst Ferncliffe Grasmere Haverstock Inkerman Jessamine Kildare Larksong Marrowgate Netherby Owlswick Pemberton Quillbeck Ravenscar Stillwater Thistlemere Undercliff Vervain Wexford Yarrow Zennor".split()
C_STYPE = ["Close", "Gardens", "Grove", "Mews", "Parade", "Rise", "Row", "Square", "Walk", "Yard"]
C_CITY = [("Alma", "MI"), ("Brevard", "NC"), ("Corry", "PA"), ("Defiance", "OH"), ("Escanaba", "MI"),
          ("Fort Morgan", "CO"), ("Galesburg", "IL"), ("Hutchinson", "KS"), ("Ironton", "OH"), ("Junction City", "KS"),
          ("Klamath Falls", "OR"), ("Lumberton", "NC"), ("Menomonie", "WI"), ("Nogales", "AZ"), ("Owatonna", "MN")]
C_ORG = ["Harborview Regional Hospital", "Cascade Family Clinic", "Meridian Park Pharmacy", "BlueRidge Diagnostics Laboratory",
         "Fern Hollow Urgent Care", "Copperline Rehabilitation Center", "Summitview Women's Health", "Northfield Pediatrics Group",
         "Redwood Grove Hospice", "Willow Bend Imaging Center", "Clearwater Dialysis Clinic", "Amberwood Community Hospital"]
C_MAILHOST = ["example.health", "mail.example.health", "example.care", "example.invalid"]

# Extend generate.py's pools with universe C, then assert disjointness.
g.FIRST["C"], g.LAST["C"] = C_FIRST, C_LAST
g.STREET["C"], g.STYPE["C"], g.CITY["C"], g.ORG["C"], g.MAILHOST["C"] = C_STREET, C_STYPE, C_CITY, C_ORG, C_MAILHOST


def _assert_disjoint():
    def low(xs):
        return {x.lower() for x in xs}
    a, b, c = low(g.FIRST["A"]) | low(g.LAST["A"]), low(g.FIRST["B"]) | low(g.LAST["B"]), low(C_FIRST) | low(C_LAST)
    common = low(g.COMMON_FIRST + g.COMMON_LAST)
    assert not (c & (a | b | common)), f"C names collide with A/B/common: {sorted(c & (a | b | common))[:5]}"
    for pool in ("STREET", "ORG", "MAILHOST"):
        cp = low(getattr(g, pool)["C"])
        ab = low(getattr(g, pool)["A"]) | low(getattr(g, pool)["B"])
        assert not (cp & ab), f"C {pool} collides: {sorted(cp & ab)}"
    cc = {c[0].lower() for c in C_CITY}
    ab_c = {c[0].lower() for c in g.CITY["A"] + g.CITY["B"]}
    assert not (cc & ab_c), f"C cities collide: {sorted(cc & ab_c)}"


_assert_disjoint()


class CGen(g.Gen):
    """Universe C value generators on top of generate.Gen."""

    def person(self):
        # No common-word names in C (COMMON_* belong to B); plain pool draws.
        return {"first": self.pick(g.FIRST["C"]), "last": self.pick(g.LAST["C"]), "common": False}

    def fax(self):
        v, _, _, tags = self.phone()
        return v, "FAX", "fax", tags

    def vin(self):
        r = self.r
        return (f"{r.choice(['1HG', '2T1', '3GN', '5YJ', 'JM1'])}"
                f"{''.join(r.choice('ABCDEFGHJKLMNPRSTUVWXYZ0123456789') for _ in range(14))}"), "VEHICLE", "vin", []

    def plate(self):
        r = self.r
        return (f"{r.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{r.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}"
                f"{r.choice('ABCDEFGHJKLMNPRSTUVWXYZ')} {self.digits(4)}"), "VEHICLE", "plate", []


# ----------------------------------------------------------------------------
# Spec construction. One JSON object per line: id, domain, spec_mode, style,
# length, planted [{ph, value, label, kind, role, count, tags}].
# ----------------------------------------------------------------------------

STYLES = ["a formal discharge letter", "terse internal chart notes with abbreviations", "an email thread between clinic staff",
          "a dictated memo transcribed by speech-to-text", "a chat message, lower-case and unpunctuated",
          "an intake form with labelled fields", "a narrative referral summary with no field labels at all",
          "clinic documentation recovered by OCR with a few character errors"]
STYLE_MODES = ["letter", "notes", "email", "dictated", "chat", "form", "narrative", "ocr"]
LENGTHS = ["3-5 sentences", "1-2 short paragraphs", "2-3 paragraphs"]

ROLES = {
    "patient": "the patient", "relative": "a relative of the patient", "clinician": "a clinician involved in the care",
    "date": "a date relevant to the visit", "dob": "the patient's date of birth",
    "old_age": "the patient's age in years", "phone": "a telephone number", "fax": "a fax number",
    "email": "an email address", "address": "a street address", "city": "a city name", "zip": "a ZIP code",
    "mrn": "the medical record number", "ssn": "a social security number", "plan": "the health plan member ID",
    "account": "an account or accession number", "accession": "a lab accession number", "license": "a license or registration number",
    "device": "an implanted device serial number", "vin": "a vehicle VIN", "plate": "a licence plate",
    "url": "a patient-portal URL", "ip": "a server IP address", "org": "the hospital or clinic name",
}
FORM_SUFFIX = {"full": ("", ""), "last": ("_LAST", ", surname only"), "first": ("_FIRST", ", first name only"),
               "last_first": ("_LF", ", surname-first in capitals"), "initial": ("_INIT", ", first initial plus surname")}

# Round-robin deck covering every clinical category; names are handled
# separately below (patient/relative/clinician, several forms per person).
DECK = ["date", "date", "dob", "phone", "email", "address", "city", "zip", "mrn", "org",
        "old_age", "fax", "ssn", "plan", "account", "accession", "license", "device", "vin", "plate", "url", "ip"]
SPOKEN_OK = {"date", "dob", "phone", "old_age", "email", "mrn", "plan", "ssn", "account", "accession", "license", "device", "fax"}


def _name_items(gen, ctr, person, role, forms, rng, out):
    """Emit one planted item per requested form of the same person."""
    for form in forms:
        # Borrow generate.Gen.name's form rendering deterministically.
        saved = form
        s, label, kind, tags = g.Gen.name(gen, person, form=saved)
        suf, desc = FORM_SUFFIX[saved]
        n = ctr["NAME"]
        ph = f"NAME_{n}{suf}"
        count = 2 if (form in ("last", "first") and rng.random() < 0.25) else 1
        tags = tags + (["repeat"] if count > 1 else [])
        out.append({"ph": ph, "value": s, "label": label, "kind": kind,
                    "role": ROLES[role] + desc, "count": count, "tags": tags})
    ctr["NAME"] += 1


def _value_for(kind, gen, rng, ctx):
    spoken = rng.random() < 0.12 and kind in SPOKEN_OK
    if kind == "old_age":
        v, label, k, tags = gen.old_age(spoken)
    elif kind == "fax":
        v, label, k, tags = gen.fax()
    elif kind == "vin":
        v, label, k, tags = gen.vin()
    elif kind == "plate":
        v, label, k, tags = gen.plate()
    elif kind == "email":
        v, label, k, tags = gen.email(ctx["patient"], spoken)
    elif kind == "url":
        v, label, k, tags = gen.url()
    elif kind == "ip":
        v, label, k, tags = gen.ip()
    elif kind == "address":
        v, label, k, tags = gen.address()
    elif kind == "city":
        v, label, k, tags = gen.city()
    elif kind == "zip":
        v, label, k, tags = gen.zip()
    elif kind == "org":
        v, label, k, tags = gen.org()
    elif kind == "phone":
        v, label, k, tags = gen.phone(spoken)
    elif kind in ("date", "dob"):
        v, label, k, tags = gen.date(dob=(kind == "dob"), spoken=spoken)
    else:  # mrn ssn plan account accession license
        v, label, k, tags = gen.idnum(kind, spoken)
    return v, label, k, tags


def build_spec(seed, n, spec_mode):
    rng0 = random.Random(seed)
    deck = DECK[:]
    rng0.shuffle(deck)
    di = 0
    docs = []
    for i in range(n):
        rng = random.Random(int(hashlib.sha256(f"{seed}:{i}".encode()).hexdigest()[:16], 16))
        gen = CGen("C", rng)
        items, ctr = [], {"NAME": 1}
        target = rng.randint(3, 12)

        patient = gen.person()
        forms = ["full"]
        if rng.random() < 0.6: forms.append("last")
        if rng.random() < 0.2: forms.append(rng.choice(["first", "initial"]))
        _name_items(gen, ctr, patient, "patient", forms, rng, items)
        if rng.random() < 0.45:
            rel = gen.person()
            _name_items(gen, ctr, rel, "relative", [rng.choice(["full", "last", "first"])], rng, items)
        if rng.random() < 0.6:
            clin = gen.person()
            _name_items(gen, ctr, clin, "clinician", [rng.choice(["full", "last", "last_first"])], rng, items)

        ctx = {"patient": patient}
        while len(items) < target:
            kind = deck[di % len(deck)]
            di += 1
            v, label, k, tags = _value_for(kind, gen, rng, ctx)
            num = ctr.get(label, 1)
            ctr[label] = num + 1
            ph = f"{label}_{num}"
            count = 2 if rng.random() < 0.12 and len(v) >= 4 else 1
            if count > 1: tags = tags + ["repeat"]
            items.append({"ph": ph, "value": v, "label": label, "kind": k,
                          "role": ROLES.get(k, ROLES.get(kind, "an identifier")), "count": count, "tags": tags})
        si = rng.randrange(len(STYLES))
        docs.append({"id": f"C-clinical-{seed}-{i:05d}", "domain": "clinical", "spec_mode": spec_mode,
                     "style": STYLES[si], "mode": STYLE_MODES[si], "length": rng.choice(LENGTHS), "planted": items})
    return docs


# ----------------------------------------------------------------------------
# Prompts.
# ----------------------------------------------------------------------------

def prompt_for(spec):
    """Build the generation prompt for one spec document."""
    style, length = spec["style"], spec["length"]
    if spec["spec_mode"] == "sentinel":
        lines = []
        for it in spec["planted"]:
            rep = f" — use it exactly {it['count']} times" if it["count"] > 1 else ""
            lines.append(f"  [[{it['ph']}]] = {it['role']}{rep}")
        ph_list = "\n".join(lines)
        return f"""Write ONE realistic but entirely fictional clinical document. Form: {style}. Length: {length}.

The document must contain every placeholder below, each written EXACTLY as shown — same characters, same double square brackets, same underscores and digits. Do not reformat, rename, reorder, merge or translate them.

{ph_list}

Rules:
- Use each placeholder the exact number of times stated (once unless stated otherwise).
- Include NO other identifying details: no other names, dates, ages, numbers with 4+ digits, places, organisations, emails, URLs, IPs, phone or fax numbers.
- Refer to anyone or anything else only generically ("the patient's sister", "the clinic", "the insurer"). Clinical terms, drug names, doses and vitals are fine.
- Output the document text only: no lists of the placeholders, no headings about the placeholders, no explanations."""
    # verbatim mode
    lines = []
    for it in spec["planted"]:
        rep = f" — must appear exactly {it['count']} times" if it["count"] > 1 else ""
        lines.append(f"  {it['value']}   ({it['role']}{rep})")
    vals = "\n".join(lines)
    return f"""Write ONE realistic but entirely fictional clinical document. Form: {style}. Length: {length}.

The document must contain every value below VERBATIM — exact characters, you may NOT reformat, abbreviate or translate them.

{vals}

Rules:
- Each value must appear the stated number of times (once unless stated otherwise).
- Include NO other identifying details: no other names, dates, ages, numbers with 4+ digits, places, organisations, emails, URLs, IPs, phone or fax numbers.
- Refer to anyone or anything else only generically ("the patient's sister", "the clinic", "the insurer"). Clinical terms, drug names, doses and vitals are fine.
- Output the document text only: no lists of the values, no markup, no explanations."""


# ----------------------------------------------------------------------------
# gen: call an OpenAI-compatible endpoint, write raw outputs. Resumable.
# ----------------------------------------------------------------------------

def clean_llm_text(text):
    """Normalise a reply before verification. DiffusionGemma (vLLM diffusion
    server) starts replies with a literal 'thought\\n' prefix (empty thought
    block); Gemma-style <think>/<thought> tags may also appear. An unclosed
    block means nothing trustworthy follows -> empty -> reject."""
    t = re.sub(r"(?is)<(think|thought)>.*?</\1>", "", text).strip()
    if re.match(r"(?is)^\s*<(think|thought)>", t):
        return ""
    t = re.sub(r"(?i)^\s*thought\s*\n", "", t).strip()  # literal 'thought\n' prefix
    return t


def _chat(base, model, key, prompt, max_tokens, temperature=None, seed=None, tkwargs=None, retries=5):
    """One chat completion. The vLLM diffusion server (DiffusionGemma) rejects
    temperature/seed/min_p/min_tokens/logit_bias with HTTP 400, so those are
    sent only when explicitly given; chat_template_kwargs likewise."""
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens}
    if temperature is not None:
        body["temperature"] = temperature
    if seed is not None:
        body["seed"] = seed
    if tkwargs:
        body["chat_template_kwargs"] = tkwargs
    data = json.dumps(body).encode()
    url = base.rstrip("/") + "/chat/completions"
    err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data, {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
            with urllib.request.urlopen(req, timeout=600) as r:
                ch = json.load(r)["choices"][0]
                return {"text": ch["message"].get("content") or "", "finish_reason": ch.get("finish_reason")}
        except Exception as e:  # noqa: BLE001 - retry any endpoint wobble
            err = e
            time.sleep(min(60, 5 * 2 ** attempt))
    return {"text": "", "finish_reason": "error", "error": str(err)}


def cmd_gen(a):
    specs = [json.loads(ln) for ln in open(a.spec, encoding="utf-8") if ln.strip()]
    done = set()
    if os.path.exists(a.out):
        for ln in open(a.out, encoding="utf-8"):
            if ln.strip():
                r = json.loads(ln)
                if r.get("finish_reason") != "error":   # endpoint failures are retried on resume
                    done.add(r["id"])
    todo = [s for s in specs if s["id"] not in done]
    print(f"{len(done)} already in {a.out}; {len(todo)} to generate", flush=True)
    tkwargs = json.loads(a.template_kwargs) if a.template_kwargs else None
    lock, out_f, failed = threading.Lock(), open(a.out, "a", encoding="utf-8"), []
    vllm_version = None
    try:
        with urllib.request.urlopen(re.sub(r"/v1/?$", "/", a.base_url) + "version", timeout=10) as r:
            vllm_version = json.load(r).get("version")
    except Exception:
        pass

    def work(s):
        seed = int(hashlib.sha256((a.seed_salt + s["id"]).encode()).hexdigest()[:12], 16) % (2**31) if a.send_seed else None
        p = prompt_for(s)
        r = _chat(a.base_url, a.model, a.api_key, p, a.max_tokens,
                  temperature=a.temperature, seed=seed, tkwargs=tkwargs)
        rec = {"id": s["id"], "prompt_sha256": hashlib.sha256(p.encode()).hexdigest(), "model": a.model,
               "seed": seed, "text": clean_llm_text(r["text"]), "finish_reason": r["finish_reason"]}
        if "error" in r:
            # Never record a failed call as a document: it would be skipped on resume.
            with lock:
                failed.append(s["id"])
            print(f"{s['id']}: endpoint error: {r['error']}", flush=True)
            return
        with lock:
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_f.flush()
            done_count = len(done) + 1
            done.add(s["id"])
            if done_count % 50 == 0:
                print(f"{done_count}/{len(specs)} done", flush=True)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(work, todo))
    out_f.close()
    manifest = {"generator": "bench/plant_generate.py gen", "model": a.model, "base_url": a.base_url,
                "vllm_version": vllm_version, "max_tokens": a.max_tokens,
                "sampling": a.temperature if a.temperature is not None else "server-default diffusion sampler (entropy_bound 0.1)",
                "chat_template_kwargs": tkwargs, "seed_salt": a.seed_salt if a.send_seed else None,
                "spec": os.path.abspath(a.spec), "raw": os.path.abspath(a.out),
                "docs_requested": len(specs), "docs_written": len(done),
                "note": "deterministic labels come from sentinel substitution in verify_planted.py, not from this generator",
                "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(a.out + ".manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"wrote manifest {a.out}.manifest.json")
    if failed:
        sys.exit(f"{len(failed)} endpoint failures (not written; rerun to resume)")


def cmd_spec(a):
    docs = build_spec(a.seed, a.n, a.mode)
    with open(a.out, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"wrote {len(docs)} specs to {a.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("spec")
    sp.add_argument("--n", type=int, default=2000)
    sp.add_argument("--seed", type=int, default=11)
    sp.add_argument("--mode", choices=["sentinel", "verbatim"], default="sentinel")
    sp.add_argument("--out", required=True)
    gp = sub.add_parser("gen")
    gp.add_argument("spec")
    gp.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1"))
    gp.add_argument("--model", default="google/diffusiongemma-26B-A4B-it")
    gp.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "none"))
    gp.add_argument("--temperature", type=float, default=None,
                    help="omit by default: the diffusion server rejects it with HTTP 400")
    gp.add_argument("--seed-salt", default="planted-clinical-v1")
    gp.add_argument("--send-seed", action="store_true",
                    help="send per-request seed (diffusion server rejects it; only for endpoints that accept seed)")
    gp.add_argument("--max-tokens", type=int, default=900)
    gp.add_argument("--template-kwargs", default="",
                    help='JSON chat_template_kwargs, e.g. {"enable_thinking": false}; omitted by default')
    gp.add_argument("--workers", type=int, default=16,
                    help="concurrency; match server --max-num-seqs (16)")
    gp.add_argument("--out", required=True)
    a = ap.parse_args()
    {"spec": cmd_spec, "gen": cmd_gen}[a.cmd](a)


if __name__ == "__main__":
    main()
