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

  spec --pool train   TRAINING specs (ids T-clinical-*). Values come from
      universe A name/place/org pools (generate.py 'A') plus a train-only
      common-word name list that is asserted disjoint from B and C, and
      numeric kinds go through formats.sample(label, 'train', rng) — never
      the test split. Cluster mix over-samples the observed misses:
      ALL-CAPS 'LAST, FIRST' (and 'Last, First') name forms, bare first /
      surname mentions including common-word names, vehicle plates/VINs in
      weak transport context, bare 5-digit ZIPs, ages > 89 as bare numbers,
      spoken/dictated forms, plus ~10% hard negatives with ZERO planted
      identifiers (eponyms, doses, scores). Specs carry pool/universe/split
      fields and are verified by the same verify_planted.py, which marks
      them split='train'.

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
template) served by vLLM >= 0.24 on a Colab A100 wrote the TEST set; train
specs must use a DIFFERENT model family (Qwen3) — pass it via gen --model
(required; nothing is baked in). The model id, vLLM version and sampling
params are recorded in <out>.manifest.json next to the raw outputs.

    python bench/plant_generate.py spec --pool train --n 12000 --seed 101 \\
        --out bench/data/train_spec_v1.jsonl
    python bench/plant_generate.py leakcheck --spec bench/data/train_spec_v1.jsonl \\
        --dev bench/data/clin_dev_tagged.jsonl --dev bench/data/clin_novel_dev_tagged.jsonl
    python bench/plant_generate.py selftest
"""
import argparse, hashlib, json, os, random, re, sys, threading, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as g
import formats as fmt

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
# TRAIN pool (--pool train). Universe A values + a train-only common-word
# name list, cluster mix biased at the observed test misses, ~10% hard
# negatives with zero planted identifiers. Verified by verify_planted.py
# (records get universe 'A', split 'train').
# ----------------------------------------------------------------------------

# Train-only common-word names: real English words usable as names, disjoint
# from B's COMMON_* lists, C pools AND the copied name files (asserted at
# import). B's COMMON_* stay test-only.
TRAIN_COMMON_FIRST = "Sage Wren Rowan Jade Coral April Winter Sky Storm Rain River Brooke Cliff Drew Paige Merle Chance Destiny Brandy Ivy Basil Clare Merit Verse Anchor Beacon Ember Fable Journey Meadow Onyx Prairie Quest Sonnet Timber Unity Valor Winslow Zephyr Lark Sorrel Bay Cove Dune Fern Gale Hawk Indigo Kit Nile Oak Pike Quill Reef Sedge Thorn Umber Vale Wick Yew Zeal Ash Birch Dell Glen Isle Slate".split()
TRAIN_COMMON_LAST = "Barrow Brisk Cobble Dingle Draper Drift Fielding Flax Flint Gable Gorse Grove Harbor Hollow Inkwell Jasper Kettle Ladle Lake Loom Marrow Moor Nettle Orchard Paddock Parchment Pebble Quarry Rafter Roof Sable Sadler Shale Slate Sorrel Spur Stable Steep Storm Thicket Thorne Trill Tumble Vale Wicket Bramble Gale Glen Isle Lark Ash Birch Dell Ember".split()
# Sentence-initial carve-outs for the train common pool (verify_planted
# screens use this like COMMON_AMBIGUOUS, only for train-pool specs).
TRAIN_COMMON_AMBIGUOUS = {w.lower() for w in "April Winter Storm Rain Sky Gale Ember Harbor".split()}

# Eponyms for hard-negative prompts, already filtered against every screened
# pool: blocked ones ship pre-possessivised ('Graves'', 'Bell's'), the rest
# are written bare ('Parkinson disease'). A model echoing a bare blocked
# eponym gets rejected by the name screen — that is the screen doing its job.
TRAIN_EPONYMS = [
    "Parkinson", "Alzheimer", "Crohn", "Huntington", "Cushing", "Addison", "Marfan",
    "Kawasaki", "Sjogren", "Raynaud", "Meniere", "Guillain-Barre", "Tourette", "Hodgkin",
    "Klinefelter", "Babinski", "Romberg", "Brudzinski", "Kernig", "Tinel", "Phalen",
    "McMurray", "Lachman", "McBurney", "Homan", "Chvostek", "Trousseau", "Cullen",
    "Virchow", "Charcot", "Meckel", "Whipple", "Billroth", "Hartmann", "Trendelenburg",
    "Mallory-Weiss", "Boerhaave", "Nissen", "Roux-en-Y", "Heimlich", "Wilms", "Kaposi",
    "Burkitt", "Reed-Sternberg", "Willebrand", "Sturge-Weber", "Ehlers-Danlos",
    "Budd-Chiari", "Fanconi", "Osler", "Pancoast", "Takayasu", "Waterhouse-Friderichsen",
    "Stargardt", "Niemann-Pick", "Purtscher", "Meige", "Down", "Hashimoto", "Asperger",
    "Graves'", "Bell's", "Murphy's", "Turner's", "Ewing's", "Gilbert's", "Reiter's",
]


def _assert_train_disjoint():
    def low(xs):
        return {x.lower() for x in xs}
    t = low(TRAIN_COMMON_FIRST + TRAIN_COMMON_LAST)
    blocked = (low(g.FIRST["B"]) | low(g.LAST["B"]) | low(g.COMMON_FIRST + g.COMMON_LAST)
               | low(C_FIRST) | low(C_LAST)
               | low(_load_names("first_names.txt")) | low(_load_names("surnames.txt")))
    assert not (t & blocked), f"train common names collide with B/C/test pools: {sorted(t & blocked)}"
    ep = {e.lower().rstrip("'s") for e in TRAIN_EPONYMS}
    assert not (ep & low(g.FIRST["A"])), f"eponym collides with A pool: {sorted(ep & low(g.FIRST['A']))}"


_assert_train_disjoint()


class TrainGen(g.Gen):
    """Universe A value generator (train-only common names + C-style ids)."""

    def person(self, force_common=False):
        common = force_common or self.r.random() < 0.22
        first = (self.pick(TRAIN_COMMON_FIRST) if (common and self.r.random() < 0.5)
                 else self.pick(g.FIRST["A"]))
        last = (self.pick(TRAIN_COMMON_LAST) if (common and (first not in TRAIN_COMMON_FIRST or self.r.random() < 0.6))
                else self.pick(g.LAST["A"]))
        return {"first": first, "last": last, "common": common}

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


TRAIN_FORM_SUFFIX = dict(FORM_SUFFIX)
TRAIN_FORM_SUFFIX["last_first_title"] = ("_LFT", ", surname-first in mixed case ('Last, First')")

TRAIN_DECK = DECK + ["id"]
TRAIN_LABEL = {"date": "DATE", "dob": "DATE", "old_age": "AGE", "phone": "PHONE",
               "fax": "FAX", "zip": "ZIP", "mrn": "MRN", "ssn": "SSN", "plan": "PLAN",
               "account": "ACCOUNT", "accession": "ACCOUNT", "license": "LICENSE",
               "device": "DEVICE", "vin": "VEHICLE", "plate": "VEHICLE",
               "url": "URL", "ip": "IP", "id": "ID"}
# Kinds whose values embed pool strings: they go through TrainGen (universe A)
# directly and are never delegated to formats.sample.
_POOL_KINDS = {"email", "address", "city", "org", "url"}
TRAIN_SPOKEN = SPOKEN_OK | {"id"}

CLUSTER_WTS = {"caps_name": 12, "title_lf_name": 6, "bare_name": 15, "vehicle_weak": 10,
               "zip_bare": 8, "age90": 8, "spoken": 9, "hard_neg": 10, "mixed": 22}

# Role hints steer the generator toward the contexts we actually miss, without
# revealing any value.
TRAIN_HINTS = {
    "caps_name": "write {ph} in a header line or sign-off as 'SURNAME, FIRST' in capitals, e.g. of the form 'GARCIA, MARIA' (illustration only; use the placeholder)",
    "title_lf_name": "write {ph} in a header line or sign-off as 'Surname, First' (surname first, comma, mixed case)",
    "bare_name": "use {ph} bare, with no honorific, no 'patient:' and no field label near it — e.g. '{ph} called to reschedule' or 'From: {ph} To: triage desk'",
    "vehicle_weak": "refer to {ph} only through weak transport context — 'transported via', 'was driving', 'parked in the lot', 'the vehicle' — never write the words 'plate', 'license plate' or 'VIN'",
    "zip_bare": "use {ph} bare without the words ZIP, postal or code — e.g. 'moved to the {ph} area' or 'resides in {ph}'",
    "age90": "give the patient's age as {ph} as a bare number with no word 'age', 'year' or 'y/o' attached — e.g. '{ph} lives independently' or '{ph} is cleared for discharge'",
    "spoken": "the note is dictated: the placeholders below are spelled the way dictation transcribes them (spaced digits, 'dot', 'at'); reproduce them letter-for-letter",
}


def _train_name_items(gen, ctr, person, role, forms, rng, out):
    """_name_items for the train pool: extra 'last_first_title' form and
    common_word_name tags that cover the TRAIN_COMMON lists."""
    for form in forms:
        if form == "last_first_title":
            s, label, kind, tags = f"{person['last']}, {person['first']}", "NAME", "person", ["fmt:last_first_title"]
        else:
            s, label, kind, tags = g.Gen.name(gen, person, form=form)
        words = {"first": [person["first"]], "last": [person["last"]]}.get(form, [person["first"], person["last"]])
        if any(w in TRAIN_COMMON_FIRST or w in TRAIN_COMMON_LAST for w in words):
            tags = list(tags) + ["common_word_name"]
        suf, desc = TRAIN_FORM_SUFFIX[form]
        n = ctr["NAME"]
        ph = f"NAME_{n}{suf}"
        count = 2 if (form in ("last", "first") and rng.random() < 0.25) else 1
        if count > 1:
            tags = list(tags) + ["repeat"]
        out.append({"ph": ph, "value": s, "label": label, "kind": kind, "fmt": "person_forms",
                    "role": ROLES[role] + desc, "count": count, "tags": tags})
    ctr["NAME"] += 1


def _spoken_train(kind, gen, ctx):
    """Forced spoken rendering for a kind (dictated cluster)."""
    if kind == "old_age":
        return gen.old_age(spoken=True)
    if kind == "fax":
        v, _, _, tags = gen.phone(spoken=True)
        return v, "FAX", "fax", tags
    if kind == "phone":
        return gen.phone(spoken=True)
    if kind == "email":
        return gen.email(ctx["patient"], spoken=True)
    if kind in ("date", "dob"):
        return gen.date(dob=(kind == "dob"), spoken=True)
    if kind == "id":
        return gen.idnum(gen.r.choice(["ein", "docket", "matter", "employee"]), spoken=True)
    return gen.idnum(kind, spoken=True)


_TEST_FORMAT_NAMES = {f.name for f in fmt.FORMATS if f.split == "test"}
# Strings that must never appear inside a planted TRAIN value: the TEST
# universes (B pools, B's COMMON_*, C pools). The copied name files are a
# screening superset, not a universe — A names that also occur there
# ('Weber') are legitimately trainable.
_BLOCKED_TOKENS = {n.lower() for n in (g.FIRST["B"] + g.LAST["B"] + g.COMMON_FIRST + g.COMMON_LAST
                                       + C_FIRST + C_LAST)}
_BLOCKED_PHRASES = sorted({p for p in
    g.STREET["B"] + C_STREET + [c for c, _ in g.CITY["B"] + C_CITY] + g.ORG["B"] + C_ORG
    + g.MAILHOST["B"] + C_MAILHOST + [s for s in g.LAST["B"] + C_LAST if " " in s]
    if len(p) >= 3}, key=len, reverse=True)


def _train_value_for(kind, gen, rng, ctx, force_spoken=False):
    """(value, label, kind, tags, fmt_name) for one train planted item.
    Pool-backed kinds come from TrainGen (universe A); the rest delegate to
    formats.sample(label, 'train', rng) — asserted train-split only."""
    spoken = force_spoken and kind in TRAIN_SPOKEN
    if kind in _POOL_KINDS:
        if kind == "email": v, label, k, tags = gen.email(ctx["patient"], spoken)
        elif kind == "address": v, label, k, tags = gen.address()
        elif kind == "city": v, label, k, tags = gen.city()
        elif kind == "org": v, label, k, tags = gen.org()
        else: v, label, k, tags = gen.url()
        fname = "generate.py"
    elif spoken:
        v, label, k, tags = _spoken_train(kind, gen, ctx)
        fname = "generate.py"
    else:
        got, fname = fmt.sample(TRAIN_LABEL[kind], "train", rng)  # train split only
        if isinstance(got, tuple):
            v, label, k, tags = got
        else:
            v, label, k, tags = got, TRAIN_LABEL[kind], kind, []
    if label == "VEHICLE":
        fname = "vin" if k == "vin" else "plate_lll_dddd"
    assert fname not in _TEST_FORMAT_NAMES, f"train spec used test-split format {fname!r}"
    # Pool-backed values must actually come from universe A. Checks are
    # structural (street-type word, exact city/org) so legit overlaps like
    # the street 'Church' vs the C surname 'Church' don't false-fire.
    if label == "ADDRESS":
        words = [w.lower() for w in re.findall(r"[a-zà-ÿ]+", v.lower())]
        stypes_bc = {s.lower() for s in g.STYPE["B"] + g.STYPE["C"]}
        streets_bc = {s.lower() for s in g.STREET["B"] + g.STREET["C"]}
        assert not any(w in stypes_bc for w in words), f"address has test stype: {v!r}"
        assert not any(w in streets_bc for w in words), f"address has test street: {v!r}"
    elif label == "LOCATION":
        assert v not in {c for c, _ in g.CITY["B"] + g.CITY["C"]}, f"city from test pool: {v!r}"
    elif label == "ORG":
        assert v not in set(g.ORG["B"] + g.ORG["C"]), f"org from test pool: {v!r}"
    elif kind in ("email", "url"):
        # Universe A mailhost required (plain or spoken 'dot' rendering);
        # B/C mailhosts must not appear. (Path words like 'case' aren't pool
        # strings, so no blanket token scan.)
        low = v.lower()
        assert any(h in low or h.replace(".", " dot ") in low for h in g.MAILHOST["A"]), f"{kind} host not universe A: {v!r}"
        bc = g.MAILHOST["B"] + g.MAILHOST["C"]
        assert not any(h in low or h.replace(".", " dot ") in low for h in bc), f"{kind} host from test pool: {v!r}"
    return v, label, k, tags, fname


def _train_plant(items, ctr, v, label, k, tags, fname, rng, role=None):
    num = ctr.get(label, 1)
    ctr[label] = num + 1
    ph = f"{label}_{num}"
    count = 2 if rng.random() < 0.12 and len(v) >= 4 else 1
    if count > 1:
        tags = list(tags) + ["repeat"]
    items.append({"ph": ph, "value": v, "label": label, "kind": k, "fmt": fname,
                  "role": role or ROLES.get(k, ROLES.get({"age_over_89": "old_age"}.get(k, label.lower()), "an identifier")),
                  "count": count, "tags": tags})
    return ph


def build_train_spec(seed, n, spec_mode):
    rng0 = random.Random(seed)
    deck, di = TRAIN_DECK[:], 0
    rng0.shuffle(deck)
    clusters = []
    for name, w in CLUSTER_WTS.items():
        clusters += [name] * round(w * n / 100)
    while len(clusters) < n:
        clusters.append("mixed")
    rng0.shuffle(clusters)
    docs = []
    for i in range(n):
        cluster = clusters[i]
        rng = random.Random(int(hashlib.sha256(f"train:{seed}:{i}".encode()).hexdigest()[:16], 16))
        si = rng.randrange(len(STYLES))
        doc = {"id": f"T-clinical-{seed}-{i:05d}", "domain": "clinical", "spec_mode": spec_mode,
               "pool": "train", "universe": "A", "split": "train", "cluster": cluster,
               "style": STYLES[si], "mode": STYLE_MODES[si], "length": rng.choice(LENGTHS)}
        if cluster == "hard_neg":
            doc["style"] = rng.choice(["terse internal chart notes with abbreviations",
                                       "a dictated memo transcribed by speech-to-text",
                                       "a narrative referral summary with no field labels at all"])
            doc["mode"] = {"terse internal chart notes with abbreviations": "notes",
                           "a dictated memo transcribed by speech-to-text": "dictated",
                           "a narrative referral summary with no field labels at all": "narrative"}[doc["style"]]
            doc["planted"], doc["hard_negative"], doc["eponyms"] = [], True, rng.sample(TRAIN_EPONYMS, rng.randint(4, 7))
            docs.append(doc)
            continue

        gen = TrainGen("A", rng)
        items, ctr, hints = [], {"NAME": 1}, []
        target = rng.randint(3, 12)
        patient = gen.person(force_common=(cluster == "bare_name" and rng.random() < 0.5))

        def names_for(role, forms, p=None):
            p = p or patient if role == "patient" else gen.person()
            start = len(items)
            _train_name_items(gen, ctr, p, role, forms, rng, items)
            return items[start:], p

        if cluster == "caps_name":
            who = rng.choice(["patient", "clinician", "relative"])
            new, _ = names_for(who, ["last_first"])
            hints.append(TRAIN_HINTS["caps_name"].format(ph=f"[[{new[0]['ph']}]]"))
        elif cluster == "title_lf_name":
            who = rng.choice(["patient", "clinician", "relative"])
            new, _ = names_for(who, ["last_first_title"])
            hints.append(TRAIN_HINTS["title_lf_name"].format(ph=f"[[{new[0]['ph']}]]"))
        elif cluster == "bare_name":
            who = rng.choice(["patient", "clinician", "relative"])
            forms = ([rng.choice(["first", "last"])] if rng.random() < 0.5
                     else ["full", rng.choice(["first", "last"])])
            new, _ = names_for(who, forms)
            hints.append(TRAIN_HINTS["bare_name"].format(ph=f"[[{new[-1]['ph']}]]"))
        elif cluster == "vehicle_weak":
            for _ in range(rng.randint(1, 2)):
                v, label, k, tags, fname = _train_value_for(rng.choice(["plate", "plate", "vin"]), gen, rng, {})
                ph = _train_plant(items, ctr, v, label, k, tags, fname, rng)
                hints.append(TRAIN_HINTS["vehicle_weak"].format(ph=f"[[{ph}]]"))
        elif cluster == "zip_bare":
            for _ in range(rng.randint(1, 2)):
                v, label, k, tags, fname = _train_value_for("zip", gen, rng, {})
                ph = _train_plant(items, ctr, v, label, k, tags, fname, rng)
                hints.append(TRAIN_HINTS["zip_bare"].format(ph=f"[[{ph}]]"))
        elif cluster == "age90":
            v, label, k, tags, fname = _train_value_for("old_age", gen, rng, {})
            ph = _train_plant(items, ctr, v, label, k, tags, fname, rng)
            hints.append(TRAIN_HINTS["age90"].format(ph=f"[[{ph}]]"))
        elif cluster == "spoken":
            doc["style"] = "a dictated memo transcribed by speech-to-text"
            doc["mode"] = "dictated"
            hints.append(TRAIN_HINTS["spoken"])

        # Everyone else: patient under a normal mix of forms, plus extras.
        if cluster in ("caps_name", "title_lf_name", "bare_name"):
            if rng.random() < 0.4:
                names_for(rng.choice(["relative", "clinician"]), [rng.choice(["full", "last", "first"])])
        else:
            forms = ["full"]
            if rng.random() < 0.5: forms.append("last")
            if rng.random() < 0.2: forms.append(rng.choice(["first", "initial"]))
            names_for("patient", forms)
            if rng.random() < 0.35:
                names_for("relative", [rng.choice(["full", "last", "first"])])
            if rng.random() < 0.45:
                names_for("clinician", [rng.choice(["full", "last", "last_first"])])

        ctx = {"patient": patient}
        force_spoken = cluster == "spoken"
        while len(items) < target:
            kind = deck[di % len(deck)]
            di += 1
            if force_spoken and kind not in TRAIN_SPOKEN:
                continue
            v, label, k, tags, fname = _train_value_for(kind, gen, rng, ctx, force_spoken=force_spoken)
            _train_plant(items, ctr, v, label, k, tags, fname, rng)
        if hints:
            doc["hints"] = hints
        doc["planted"] = items
        docs.append(doc)
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


def _hard_negative_prompt(spec):
    """Zero planted identifiers: eponyms, doses, scores — all the shapes the
    screens must find clean. Ages > 89 are identifiers, so the prompt asks
    for ages under 90."""
    ep = ", ".join(spec["eponyms"])
    return f"""Write ONE realistic but entirely fictional clinical document. Form: {spec['style']}. Length: {spec['length']}.

The document must NOT contain any patient or staff identifiers at all — no names of people, no dates of birth, no medical record numbers, no social security numbers, no phone/fax numbers, no emails, no URLs, no IP addresses, no street addresses, no ZIP codes, no licence plates or VINs, and no ages over 89. Refer to everyone generically ('the patient', 'the nurse', 'the spouse').

Instead, make it clinically dense — these are NOT identifiers and must appear:
- eponymous findings or conditions, e.g. {ep}
- drug names with doses in mg or mcg
- vital signs (blood pressure, heart rate, SpO2, temperature)
- lab values including decimals
- named clinical scores written 'X out of Y' (never with a slash)
- named forms or scales (short names/numbers like Form A-12 or 'Form 700'), durations in days or weeks, anatomical terms

Rules:
- Ages, if mentioned, stay under 90.
- Numbers of 4 or more digits only ever appear attached to a clinical unit (mg, mL, mmHg, cells, etc.).
- No placeholder tokens, no lists of the above, no markup or explanations — output only the document text."""


def train_prompt_for(spec):
    """Generation prompt for a train-pool spec. Same sentinel contract as the
    test prompt (placeholders verbatim, counted, nothing else identifying) —
    phrased differently and with optional context hints."""
    if spec.get("hard_negative"):
        return _hard_negative_prompt(spec)
    style, length = spec["style"], spec["length"]
    if spec["spec_mode"] == "sentinel":
        lines = []
        for it in spec["planted"]:
            rep = f" — use it exactly {it['count']} times" if it["count"] > 1 else ""
            lines.append(f"  [[{it['ph']}]] = {it['role']}{rep}")
        hint_block = ""
        if spec.get("hints"):
            hint_block = "\nContext cues (follow them exactly; they change how the placeholders appear, not what they contain):\n" + \
                         "\n".join(f"- {h}" for h in spec["hints"]) + "\n"
        return f"""Write ONE realistic fictional clinical document. Form: {style}. Length: {length}.

Every token below is a placeholder. Copy each into the document letter-for-letter — same capitals, same underscores, same double square brackets — never reformat, merge or rename one.

{chr(10).join(lines)}
{hint_block}
Requirements:
- A placeholder appears the stated number of times (once unless stated otherwise).
- Apart from the placeholders there are NO other identifiers: no other person names, dates, ages above 89, 4+ digit numbers, places, organisations, emails, URLs, IPs, phone or fax numbers.
- Anyone or anything else is generic ('the patient's sister', 'the clinic', 'the insurer'). Clinical terms, drug names, doses and vitals are fine.
- Reply with the document text only: no placeholder list, no headings about placeholders, no commentary."""
    # verbatim mode
    lines = []
    for it in spec["planted"]:
        rep = f" — must appear exactly {it['count']} times" if it["count"] > 1 else ""
        lines.append(f"  {it['value']}   ({it['role']}{rep})")
    vals = "\n".join(lines)
    return f"""Write ONE realistic fictional clinical document. Form: {style}. Length: {length}.

Every value below must appear VERBATIM — exact characters, never reformatted, abbreviated or translated.

{vals}

Requirements:
- A value appears the stated number of times (once unless stated otherwise).
- Apart from these values there are NO other identifiers: no other person names, dates, ages above 89, 4+ digit numbers, places, organisations, emails, URLs, IPs, phone or fax numbers.
- Reply with the document text only: no value list, no markup, no commentary."""


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
        p = train_prompt_for(s) if s.get("pool") == "train" else prompt_for(s)
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
    docs = build_train_spec(a.seed, a.n, a.mode) if a.pool == "train" else build_spec(a.seed, a.n, a.mode)
    with open(a.out, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"wrote {len(docs)} specs to {a.out}")
    if a.pool == "train":
        from collections import Counter
        cc = Counter(d["cluster"] for d in docs)
        lc = Counter(s["label"] for d in docs for s in d["planted"])
        tc = Counter(t for d in docs for s in d["planted"] for t in s["tags"])
        print("cluster coverage:", dict(cc.most_common()))
        print("label coverage:  ", dict(lc.most_common()))
        print("tag coverage:    ", dict(tc.most_common()))


def cmd_leakcheck(a):
    """Planted train values must not appear in dev sets and vice versa; no
    train spec may carry a test-split format name."""
    specs = [json.loads(ln) for ln in open(a.spec, encoding="utf-8") if ln.strip()]
    train_vals, train_name_tokens, train_val_kinds = set(), set(), {}
    bad_fmt = []
    for d in specs:
        assert d["id"].startswith("T-clinical-"), f"non-train id {d['id']}"
        for it in d["planted"]:
            if it.get("fmt") in _TEST_FORMAT_NAMES:
                bad_fmt.append((d["id"], it["fmt"]))
            train_vals.add(it["value"].lower())
            train_val_kinds[it["value"].lower()] = it["kind"]
            if it["kind"] == "person":
                train_name_tokens |= {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ'’-]{2,}", it["value"])}
    assert not bad_fmt, f"test-split format names in train specs: {bad_fmt[:5]}"
    dev_vals, dev_name_tokens, dev_val_labels = set(), set(), {}
    for path in a.dev:
        for ln in open(path, encoding="utf-8"):
            if not ln.strip():
                continue
            d = json.loads(ln)
            for s in d.get("spans", []):
                v = d["text"][s["start"]:s["end"]]
                dev_vals.add(v.lower())
                dev_val_labels[v.lower()] = s.get("label")
                if s.get("label") == "NAME":
                    dev_name_tokens |= {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ'’-]{2,}", v)}
    # Value-string equality on pool-backed values is a leak. Numeric values
    # (555-phones, dates, ZIPs) share finite format spaces between the A and
    # C generators, so identical strings arise coincidentally — they are
    # gated by universe disjointness, not string equality.
    poolish = {"person", "street", "city", "organisation", "email", "url"}
    train_pool_vals = {v for v, kind in train_val_kinds.items() if kind in poolish}
    dev_pool_vals = {v for v, lab in dev_val_labels.items() if lab in ("NAME", "ADDRESS", "LOCATION", "ORG", "EMAIL", "URL")}
    ov = train_pool_vals & dev_pool_vals
    assert not ov, f"planted train pool values present in dev sets: {sorted(ov)[:10]}"
    # Person-name token overlap is a leak even inside a longer string
    # (a shared surname between a train plant and a dev name would be).
    tnames = train_name_tokens & dev_name_tokens
    assert not tnames, f"train/dev shared person-name tokens: {sorted(tnames)[:10]}"
    print(f"leakcheck OK: {len(train_vals)} planted values, {len(dev_vals)} dev span values, 0 overlaps; "
          f"{len(specs)} specs, 0 test-split format names")


def cmd_selftest(_a):
    """Cheap train-pool self checks (no LLM, no verifier import)."""
    from collections import Counter
    docs = build_train_spec(7, 300, "sentinel")
    assert all(d["id"].startswith("T-clinical-") for d in docs)
    assert all(d["universe"] == "A" and d["split"] == "train" and d["pool"] == "train" for d in docs)
    hn = [d for d in docs if d["cluster"] == "hard_neg"]
    assert hn and all(d["hard_negative"] and not d["planted"] for d in hn)
    # name values restricted to A pools + train common list
    ok_names = {n.lower() for n in g.FIRST["A"] + g.LAST["A"] + TRAIN_COMMON_FIRST + TRAIN_COMMON_LAST}
    for d in docs:
        for it in d["planted"]:
            assert it["fmt"] not in _TEST_FORMAT_NAMES
            if it["kind"] == "person":
                for w in re.findall(r"[A-Za-zÀ-ÿ'’-]+", it["value"]):
                    if len(w) >= 2:
                        assert w.lower() in ok_names, f"{d['id']}: name token {w!r} not in train pools"
    cc = Counter(d["cluster"] for d in docs)
    assert all(cc[c] for c in CLUSTER_WTS), f"missing cluster: {cc}"
    caps = [d for d in docs if d["cluster"] == "caps_name"]
    assert all(any(re.match(r"^[A-ZÀ-Þ' .-]+, [A-ZÀ-Þ' .-]+$", it["value"]) for it in d["planted"]
                   if it["kind"] == "person") for d in caps[:60]), "caps_name doc lacks LAST, FIRST value"
    tlf = [d for d in docs if d["cluster"] == "title_lf_name"]
    assert all(any(re.match(r"^[A-ZÀ-Þ][a-zà-ÿ'’-]*.*, [A-ZÀ-Þ]", it["value"]) for it in d["planted"]
                   if it["kind"] == "person") for d in tlf[:60]), "title_lf doc lacks 'Last, First' value"
    bare = [d for d in docs if d["cluster"] == "bare_name"]
    assert all(any("single_name" in it["tags"] for it in d["planted"]) for d in bare), "bare_name without single_name"
    veh = [d for d in docs if d["cluster"] == "vehicle_weak"]
    assert all(any(it["label"] == "VEHICLE" for it in d["planted"]) for d in veh)
    zp = [d for d in docs if d["cluster"] == "zip_bare"]
    assert all(any(it["label"] == "ZIP" and re.fullmatch(r"\d{5}", it["value"]) for it in d["planted"]) for d in zp)
    ag = [d for d in docs if d["cluster"] == "age90"]
    assert all(any(it["kind"] == "age_over_89" for it in d["planted"]) for d in ag)
    sp = [d for d in docs if d["cluster"] == "spoken"]
    assert all(any("spoken" in it["tags"] for it in d["planted"]) for d in sp), "spoken doc without spoken item"
    assert all(d["mode"] == "dictated" for d in sp)
    # prompts: sentinel contract preserved, hints rendered, hard-neg prompt has no placeholders
    p = train_prompt_for(next(d for d in docs if d["cluster"] == "caps_name"))
    assert "[[" in p and "Context cues" in p and "GARCIA, MARIA" in p
    hp = train_prompt_for(hn[0])
    assert "[[" not in hp and "eponym" in hp and all(e in hp for e in hn[0]["eponyms"])
    vp = train_prompt_for({**docs[0], "spec_mode": "verbatim"})
    assert docs[0]["planted"] and "VERBATIM" in vp
    print(f"train selftest OK: {len(docs)} specs, clusters {dict(cc.most_common())}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("spec")
    sp.add_argument("--n", type=int, default=2000)
    sp.add_argument("--seed", type=int, default=11)
    sp.add_argument("--mode", choices=["sentinel", "verbatim"], default="sentinel")
    sp.add_argument("--pool", choices=["test", "train"], default="test",
                    help="test: universe C clin_spec (default, byte-stable); train: universe A T-clinical specs")
    sp.add_argument("--out", required=True)
    gp = sub.add_parser("gen")
    gp.add_argument("spec")
    gp.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1"))
    gp.add_argument("--model", required=True,
                    help="generator model id (required: test used diffusiongemma; train must use a different family, e.g. Qwen/Qwen3-14B-AWQ)")
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
    lp = sub.add_parser("leakcheck")
    lp.add_argument("--spec", required=True)
    lp.add_argument("--dev", action="append", required=True)
    st = sub.add_parser("selftest")
    a = ap.parse_args()
    {"spec": cmd_spec, "gen": cmd_gen, "leakcheck": cmd_leakcheck, "selftest": cmd_selftest}[a.cmd](a)



if __name__ == "__main__":
    main()
