"""Identifier-FORMAT registry: which surface shapes a value can take.

Standard library only (bench sibling imports inside check/sample).

generate.py (and plant_generate.py's CGen on top of it) define the TRAIN
universe: every value shape they can emit counts as SEEN. This module
registers those shapes as split="train" Format entries — pattern is a
superset description where expressible, or "" for a generate.py passthrough
that cannot be sampled here — plus a battery of realistic NOVEL shapes as
split="test" that no same-label generator can produce (`check` proves this;
novelty is per-label: a test SSN shape may coincidentally resemble an ABA
routing number, which is a different label's format, so cross-label matches
are reported as warnings only).

Pattern mini-language (compile_pattern / infer_pattern / check):
  {dN}     N digits 0-9        {DN} N digits first non-zero
  {LN}     N uppercase A-Z     {lN} N lowercase a-z
  {xN}     N lowercase alnum   {wN} N uppercase alnum
  {hN}     N lowercase hex     {c:SET} one char from SET    {a:X|Y} alternative
  {n:LO-HI} integer in [LO,HI], unpadded
  {mm} {dd} {yy} {yyyy}        padded month/day, 2/4-digit year
  {Mon} {Month}                abbrev / full month name
  {do}     day-of-month with ordinal suffix (1st, 2nd, ...)
  {fn} {ln} lowercase first/last-name pools (email/url local parts)
  {fi}     lowercase first initial
Anything else is literal text.

Splits are enforced by sample(): 'train' draws only generate.py values,
'test' only registered novel patterns — a novel test shape can never leak
into a training pipeline through this module.

CLI:
  python bench/formats.py list [--label L] [--split S]
  python bench/formats.py add LABEL --split train|test --name NAME \
      (--pattern P | --examples "ex1" "ex2" ...) [--example EX]
  python bench/formats.py check
"""
import argparse, json, os, random, re, sys
from dataclasses import dataclass, asdict

HERE = os.path.dirname(os.path.abspath(__file__))
USER_PATH = os.path.join(HERE, "formats_user.json")

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
MONS = [m[:3] for m in MONTHS]

# Small embedded pools for email/url local parts: realistic name-derived
# shapes without needing a person record. Deliberately NOT A/B/C name pools.
_FN = ["avery", "blair", "casey", "devon", "ellis", "finley", "gray", "harper",
       "india", "jules", "kennedy", "logan", "marlowe", "nell", "oakley",
       "parker", "quinn", "reese", "rowan", "sutton", "teagan", "wren"]
_LN = ["ashford", "bell", "carver", "dalton", "everly", "fox", "greer",
       "hayes", "ingram", "judd", "keller", "lowery", "merrick", "nolan",
       "osgood", "priest", "quincy", "rourke", "slater", "tate", "vance", "wolfe"]

_TOK = re.compile(r"\{([A-Za-z]+\d*)(?::([^}]*))?\}")
_ALNUM = "abcdefghijklmnopqrstuvwxyz0123456789"
_POOLS = {"d": "0123456789", "D": "123456789",
          "L": "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "l": "abcdefghijklmnopqrstuvwxyz",
          "x": _ALNUM, "w": _ALNUM.upper(), "h": "0123456789abcdef"}
_POOL_RX = {"d": r"\d", "D": r"[1-9]", "L": r"[A-Z]", "l": r"[a-z]",
            "x": r"[a-z0-9]", "w": r"[A-Z0-9]", "h": r"[0-9a-f]"}


def _sample_token(name, arg, r):
    if name == "c" and arg is not None:
        assert arg, "{c:} needs a non-empty char set"
        return r.choice(list(dict.fromkeys(arg)))
    if name == "a" and arg is not None:
        opts = arg.split("|")
        assert all(opts), "{a:} needs non-empty alternatives"
        return r.choice(opts)
    if name == "n" and arg is not None:
        lo, hi = arg.split("-", 1)
        return str(r.randint(int(lo), int(hi)))
    if arg is not None:
        raise ValueError(f"token {name!r} takes no argument")
    if name and name[0] in _POOLS and (len(name) == 1 or name[1:].isdigit()):
        n = int(name[1:]) if len(name) > 1 else 1
        return "".join(r.choice(_POOLS[name[0]]) for _ in range(n))
    if name == "mm": return f"{r.randint(1, 12):02d}"
    if name == "dd": return f"{r.randint(1, 28):02d}"
    if name == "yy": return f"{r.randint(0, 99):02d}"
    if name == "yyyy": return str(r.randint(1920, 2026))
    if name == "Mon": return r.choice(MONS)
    if name == "Month": return r.choice(MONTHS)
    if name == "do":
        d = r.randint(1, 28)
        suf = "th" if 11 <= d <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
        return f"{d}{suf}"
    if name == "fn": return r.choice(_FN)
    if name == "ln": return r.choice(_LN)
    if name == "fi": return r.choice("abcdefghijklmnopqrstuvwxyz")
    raise ValueError(f"unknown token {{{name}}}")


def _token_regex(name, arg):
    if name == "c" and arg is not None:
        return "[" + re.escape(arg) + "]"
    if name == "a" and arg is not None:
        return "(?:" + "|".join(re.escape(o) for o in arg.split("|")) + ")"
    if name == "n" and arg is not None:
        return r"\d+"
    if arg is not None:
        raise ValueError(f"token {name!r} takes no argument")
    if name and name[0] in _POOL_RX and (len(name) == 1 or name[1:].isdigit()):
        n = int(name[1:]) if len(name) > 1 else 1
        return _POOL_RX[name[0]] + ("{%d}" % n if n > 1 else "")
    if name == "mm": return r"(?:0[1-9]|1[0-2])"
    if name == "dd": return r"(?:0[1-9]|[12]\d|3[01])"
    if name == "yy": return r"\d{2}"
    if name == "yyyy": return r"(?:19|20)\d{2}"
    if name == "Mon": return r"(?:" + "|".join(MONS) + r")"
    if name == "Month": return r"(?:" + "|".join(MONTHS) + r")"
    if name == "do": return r"\d{1,2}(?:st|nd|rd|th)"
    if name == "fn": return r"[a-z]+"
    if name == "ln": return r"[a-z]+"
    if name == "fi": return r"[a-z]"
    raise ValueError(f"unknown token {{{name}}}")


def _pieces(pattern):
    """-> [('lit', text) | ('tok', (name, arg))]."""
    out, pos = [], 0
    for m in _TOK.finditer(pattern):
        out.append(("lit", pattern[pos:m.start()]))
        out.append(("tok", (m.group(1), m.group(2))))
        pos = m.end()
    out.append(("lit", pattern[pos:]))
    return out


def _validate_pattern(pattern):
    """Compile pattern to a fullmatch regex; raises on unknown tokens."""
    rx = "".join(re.escape(p) if k == "lit" else _token_regex(p[0], p[1])
                 for k, p in _pieces(pattern))
    return re.compile(rx)


def pattern_regex(pattern):
    return _validate_pattern(pattern)


def compile_pattern(pattern):
    """-> callable(rng) -> value string."""
    _validate_pattern(pattern)  # fail early on unknown tokens
    pieces = _pieces(pattern)

    def gen(rng):
        return "".join(p if k == "lit" else _sample_token(p[0], p[1], rng)
                       for k, p in pieces)

    return gen


def infer_pattern(examples):
    """Generalise example strings into one pattern: digit runs -> {dN},
    uppercase runs -> {LN}, lowercase runs -> {lN}, all else literal.
    Every example must share the same skeleton; raises otherwise."""
    skels = []
    for ex in examples:
        out, i = [], 0
        for m in re.finditer(r"\d+|[A-Z]+|[a-z]+", ex):
            out.append(ex[i:m.start()])
            t = m.group(0)
            out.append("{%s%d}" % ("d" if t[0].isdigit() else "L" if t[0].isupper() else "l", len(t)))
            i = m.end()
        out.append(ex[i:])
        skels.append("".join(out))
    if len(set(skels)) != 1:
        raise ValueError(f"inconsistent examples: {examples!r}")
    _validate_pattern(skels[0])
    return skels[0]


# ----------------------------------------------------------------------------
# Registries.
# ----------------------------------------------------------------------------

@dataclass
class Format:
    name: str
    label: str                 # Scotoma label (MRN, SSN, DATE, ...)
    split: str                 # "train" | "test"
    pattern: str               # mini-language; "" = generate.py passthrough
    example: str


# split="train": documentation of what generate.py/plant_generate.py emit.
# Patterns are supersets of the true generator output; unexpressible shapes
# use "" and are never sampled from this module.
BUILTIN = [
    # DATE (kinds date + dob)
    Format("date_numeric_us", "DATE", "train", "{mm}/{dd}/{yyyy}", "03/05/2024"),
    Format("date_numeric_short", "DATE", "train", "", "3/5/24"),
    Format("date_iso", "DATE", "train", "{yyyy}-{mm}-{dd}", "2024-03-05"),
    Format("date_named", "DATE", "train", "{Month} {n:1-28}, {yyyy}", "March 5, 2024"),
    Format("date_named_abbr", "DATE", "train", "", "Mar 5, 2024"),
    Format("date_day_first", "DATE", "train", "", "5 March 2024"),
    Format("date_dashed_mon", "DATE", "train", "", "05-Mar-2024"),
    Format("date_partial", "DATE", "train", "", "March 5"),
    Format("date_month_year", "DATE", "train", "", "March 2024"),
    Format("date_spoken", "DATE", "train", "", "the fifth of March 2024"),
    # AGE (kind age_over_89)
    Format("age_digits", "AGE", "train", "{n:90-103}", "93"),
    Format("age_spoken_word", "AGE", "train", "", "ninety-one"),
    # PHONE (shapes reused for FAX via CGen)
    Format("phone_paren", "PHONE", "train", "({d3}) {d3}-{d4}", "(747) 555-0181"),
    Format("phone_dash", "PHONE", "train", "{d3}-{d3}-{d4}", "747-555-0181"),
    Format("phone_dot", "PHONE", "train", "{d3}.{d3}.{d4}", "747.555.0181"),
    Format("phone_space", "PHONE", "train", "{d3} {d3} {d4}", "747 555 0181"),
    Format("phone_intl", "PHONE", "train", "+1 {d3} {d3} {d4}", "+1 747 555 0181"),
    Format("phone_plain", "PHONE", "train", "{d10}", "7475550181"),
    Format("phone_spoken", "PHONE", "train", "", "7 4 7 5 5 5 0 1 8 1"),
    Format("fax_phone_shapes", "FAX", "train", "", "(747) 555-0181"),
    # EMAIL / URL / IP
    Format("email_person_host", "EMAIL", "train", "", "jane.horn@example.com"),
    Format("email_spoken", "EMAIL", "train", "", "jane dot horn at example dot com"),
    Format("url_portal_id", "URL", "train", "", "https://portal.example.com/view?id=123456"),
    Format("ipv4", "IP", "train", "{n:0-255}.{n:0-255}.{n:0-255}.{n:1-254}", "203.0.113.7"),
    # ID numbers
    Format("mrn_digits8", "MRN", "train", "{d8}", "48291736"),
    Format("mrn_dash", "MRN", "train", "{d4}-{d5}", "4829-17364"),
    Format("mrn_alpha", "MRN", "train", "{L1}{d7}", "A4829173"),
    Format("ssn_dash", "SSN", "train", "{d3}-{d2}-{d4}", "555-12-3456"),
    Format("itin_dash", "SSN", "train", "9{d2}-7{d1}-{d4}", "955-70-1234"),
    Format("plan_card", "PLAN", "train", "", "4829-173-645-ZR"),
    Format("plan_alpha", "PLAN", "train", "", "HX-173-6452-91"),
    Format("account_digits", "ACCOUNT", "train", "", "4829173654"),
    Format("accession", "ACCOUNT", "train", "{L3}-{yyyy}{d4}-{d4}", "RAD-20241516-5176"),
    Format("aba_routing", "ACCOUNT", "train", "{d9}", "021000021"),
    Format("iban", "ACCOUNT", "train", "", "GB29 NWBK 6016 1331 9268 19"),
    Format("claim", "ACCOUNT", "train", "CLM-{d9}", "CLM-482917365"),
    Format("device_prefix", "DEVICE", "train", "{L3}-{d8}", "BSX-48291736"),
    Format("license_rn", "LICENSE", "train", "RN-{d7}", "RN-4829173"),
    Format("license_seg", "LICENSE", "train", "{L1}{d4}-{d5}-{d5}", "D4829-17364-55176"),
    Format("license_bar", "LICENSE", "train", "{d6}", "482917"),
    Format("vin", "VEHICLE", "train", "{a:1HG|2T1|3GN|5YJ|JM1}{w14}", "1HGBH41JXMN109186"),
    Format("plate_lll_dddd", "VEHICLE", "train", "{L3} {d4}", "ABC 1234"),
    Format("ein", "ID", "train", "{d2}-{d7}", "48-2917364"),
    Format("docket", "ID", "train", "", "3:24-cv-12345"),
    Format("matter", "ID", "train", "{d5}.{d4}", "48291.7364"),
    Format("employee", "ID", "train", "E{d6}", "E482917"),
    # places / names
    Format("zip5", "ZIP", "train", "{d5}", "60614"),
    Format("street_address", "ADDRESS", "train", "", "742 Maple Street"),
    Format("city", "LOCATION", "train", "", "Hamilton"),
    Format("org", "ORG", "train", "", "Lakeridge Health"),
    Format("person_forms", "NAME", "train", "", "HORN, Jane"),
]

# split="test": NOVEL shapes — plausible in US clinical text, unproducible by
# any same-label generate.py/CGen value generator (enforced by `check`).
NOVEL = [
    # MRN
    Format("mrn_lbl_space", "MRN", "test", "MRN {d7}", "MRN 4829173"),
    Format("mrn_mr_dash", "MRN", "test", "MR-{d3}-{d4}", "MR-482-9173"),
    Format("mrn_grouped", "MRN", "test", "{d3} {d3} {d2}", "482 917 36"),
    Format("mrn_hash", "MRN", "test", "#{d8}", "#48291736"),
    # SSN
    Format("ssn_plain", "SSN", "test", "{D}{d2}{d2}{d4}", "555123456"),
    Format("ssn_space", "SSN", "test", "{d3} {d2} {d4}", "555 12 3456"),
    Format("ssn_dot", "SSN", "test", "{d3}.{d2}.{d4}", "555.12.3456"),
    # PLAN
    Format("plan_digits11", "PLAN", "test", "{D}{d10}", "48291736547"),
    Format("plan_grouped", "PLAN", "test", "{d3} {d3} {d3}", "482 917 365"),
    Format("plan_alpha_pref", "PLAN", "test", "{L3}{d9}", "XEP482917365"),
    Format("plan_alpha_mid", "PLAN", "test", "{d6}{L2}{d4}", "482917ZX3654"),
    # ACCOUNT
    Format("acct_spaced", "ACCOUNT", "test", "{d4} {d4} {d4}", "4829 1736 5470"),
    Format("acct_dashed", "ACCOUNT", "test", "{d4}-{d4}-{d4}", "4829-1736-5470"),
    Format("acct_lbl", "ACCOUNT", "test", "ACCT {d4}-{d4}-{d4}", "ACCT 4829-1736-5470"),
    Format("acct_dot", "ACCOUNT", "test", "{d4}.{d4}.{d4}", "4829.1736.5470"),
    # LICENSE
    Format("lic_md", "LICENSE", "test", "MD-{d2}-{d5}", "MD-48-29173"),
    Format("lic_spaced", "LICENSE", "test", "RN {d6}", "RN 482917"),
    Format("lic_hash", "LICENSE", "test", "LIC#{d8}", "LIC#48291736"),
    # DEVICE
    Format("dev_sn", "DEVICE", "test", "SN {d8}", "SN 48291736"),
    Format("dev_seg", "DEVICE", "test", "{L3}-{d4}-{d4}", "BSX-4829-1736"),
    Format("dev_udi", "DEVICE", "test", "(01){d14}", "(01)00384829173654"),
    # VEHICLE
    Format("veh_dash", "VEHICLE", "test", "{L3}-{d4}", "TGK-4829"),
    Format("veh_state", "VEHICLE", "test", "{L2} {d5}", "NV 48291"),
    Format("veh_mix", "VEHICLE", "test", "{d1}{L3}{d3}", "4TGK482"),
    Format("veh_vin_jt", "VEHICLE", "test", "JT{w15}", "JTHBH41JXMN109186"),
    # PHONE (555 exchange keeps the fake-number convention)
    Format("ph_intl_paren", "PHONE", "test", "+1 ({d3}) 555-01{d2}", "+1 (747) 555-0142"),
    Format("ph_compact_paren", "PHONE", "test", "({d3})555.01{d2}", "(747)555.0142"),
    Format("ph_space4", "PHONE", "test", "({d3}) 555 01{d2}", "(747) 555 0142"),
    Format("ph_ext", "PHONE", "test", "{d3}.{d3}.01{d2} x{d3}", "747.555.0142 x312"),
    Format("ph_tollfree", "PHONE", "test", "1-800-555-01{d2}", "1-800-555-0142"),
    # FAX
    Format("fax_intl_paren", "FAX", "test", "+1 ({d3}) 555-01{d2}", "+1 (312) 555-0142"),
    Format("fax_compact", "FAX", "test", "({d3})555-01{d2}", "(312)555-0142"),
    Format("fax_lbl", "FAX", "test", "Fax: {d3}-{d3}-01{d2}", "Fax: 312-555-0142"),
    # DATE
    Format("date_slash_iso", "DATE", "test", "{yyyy}/{mm}/{dd}", "2024/03/05"),
    Format("date_dot_eu", "DATE", "test", "{dd}.{mm}.{yyyy}", "05.03.2024"),
    Format("date_dot_us", "DATE", "test", "{mm}.{dd}.{yyyy}", "03.05.2024"),
    Format("date_mon_dot", "DATE", "test", "{Mon}. {dd}, {yyyy}", "Mar. 05, 2024"),
    Format("date_ord_named", "DATE", "test", "{Month} {do}, {yyyy}", "March 5th, 2024"),
    # ZIP
    Format("zip4_dash", "ZIP", "test", "{d5}-{d4}", "60614-2917"),
    Format("zip4_space", "ZIP", "test", "{d5} {d4}", "60614 2917"),
    Format("zip9_slash", "ZIP", "test", "{d5}/{d4}", "60614/2917"),
    # IP
    Format("ipv6_full", "IP", "test", "{h4}:{h4}:{h4}:{h4}:{h4}:{h4}:{h4}:{h4}",
           "2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
    Format("ipv6_link", "IP", "test", "fe80::{h4}:{h4}", "fe80::8a2e:0370"),
    Format("ipv6_mapped", "IP", "test", "::ffff:{n:0-255}.{n:0-255}.{n:0-255}.{n:1-254}", "::ffff:203.0.113.7"),
    Format("ipv4_port", "IP", "test", "{n:0-255}.{n:0-255}.{n:0-255}.{n:1-254}:{n:1024-9999}", "203.0.113.7:8443"),
    # EMAIL
    Format("em_dash", "EMAIL", "test", "{fn}-{ln}@example.org", "avery-ashford@example.org"),
    Format("em_rev_dot", "EMAIL", "test", "{ln}.{fi}@example.net", "ashford.a@example.net"),
    Format("em_dot_sfx", "EMAIL", "test", "{fn}.{ln}.{d2}@example.com", "avery.ashford.42@example.com"),
    Format("em_us_tld", "EMAIL", "test", "{fi}{ln}@mail.example.us", "aashford@mail.example.us"),
    # URL
    Format("url_http", "URL", "test", "http://{ln}-portal.example.org/patient/{d6}",
           "http://ashford-portal.example.org/patient/482917"),
    Format("url_path", "URL", "test", "https://{l2}health.example.io/records/mrn-{d8}",
           "https://myhealth.example.io/records/mrn-48291736"),
    Format("url_www", "URL", "test", "www.example.org/chart/{d7}", "www.example.org/chart/4829173"),
    Format("url_query", "URL", "test", "https://portal.example.net/patients?mrn={d7}&v={d1}",
           "https://portal.example.net/patients?mrn=4829173&v=2"),
    # AGE
    Format("age_yo", "AGE", "test", "{n:90-99} y/o", "93 y/o"),
    Format("age_year_old", "AGE", "test", "{n:90-103}-year-old", "93-year-old"),
    Format("age_yrs", "AGE", "test", "{n:90-103} yrs", "93 yrs"),
]


def _load_user():
    if not os.path.exists(USER_PATH):
        return []
    with open(USER_PATH, encoding="utf-8") as f:
        return [Format(**d) for d in json.load(f)]


def _all():
    return BUILTIN + NOVEL + _load_user()


def _save_user(formats):
    with open(USER_PATH, "w", encoding="utf-8") as f:
        json.dump([asdict(x) for x in formats], f, indent=2, ensure_ascii=False)
        f.write("\n")


FORMATS = _all()


def formats_for(label, split):
    return [f for f in FORMATS if f.label == label and f.split == split]


def sample(label, split, rng):
    """-> (value, format_name). Raises if nothing registered for (label,split).

    'test' draws from registered novel patterns. 'train' delegates to
    generate.py/CGen itself so training data always uses real generator code
    paths (single source of truth)."""
    if split == "test":
        fmts = formats_for(label, "test")
        if not fmts:
            raise KeyError(f"no test formats for label {label!r}")
        f = rng.choice(fmts)
        if not f.pattern:
            raise ValueError(f"test format {f.name!r} has no pattern")
        return compile_pattern(f.pattern)(rng), f.name
    if split == "train":
        sys.path.insert(0, HERE)
        import plant_generate as pg
        r = rng
        gen = pg.CGen("C", r)  # superset of g.Gen behaviours
        person = {"first": r.choice(_FN).title(), "last": r.choice(_LN).title()}
        sp = lambda: r.random() < 0.15
        dispatch = {
            "DATE": lambda: gen.date(dob=r.random() < 0.4, spoken=sp()),
            "AGE": lambda: gen.old_age(spoken=sp()),
            "PHONE": lambda: gen.phone(spoken=sp()),
            "FAX": lambda: gen.fax(),
            "EMAIL": lambda: gen.email(person, spoken=sp()),
            "URL": lambda: gen.url(),
            "IP": lambda: gen.ip(),
            "ZIP": lambda: gen.zip(),
            "ADDRESS": lambda: gen.address(),
            "LOCATION": lambda: gen.city(),
            "ORG": lambda: gen.org(),
            "VEHICLE": lambda: r.choice([gen.vin(), gen.plate()]),
            "MRN": lambda: gen.idnum("mrn", sp()),
            "SSN": lambda: gen.idnum(r.choice(["ssn", "itin"]), sp()),
            "PLAN": lambda: gen.idnum("plan", sp()),
            "ACCOUNT": lambda: gen.idnum(r.choice(["account", "accession", "routing", "iban", "claim"])),
            "LICENSE": lambda: gen.idnum(r.choice(["license", "bar"]), sp()),
            "DEVICE": lambda: gen.idnum("device", sp()),
            "ID": lambda: gen.idnum(r.choice(["ein", "docket", "matter", "employee"])),
        }
        if label not in dispatch:
            raise KeyError(f"no train formats for label {label!r}")
        return dispatch[label](), "generate.py"
    raise ValueError(f"bad split {split!r}")


# ----------------------------------------------------------------------------
# check: prove every split='test' format is unproducible by the generators.
# ----------------------------------------------------------------------------

GEN_KINDS = ["mrn", "ssn", "plan", "account", "accession", "device", "license",
             "ein", "itin", "routing", "iban", "docket", "matter", "bar",
             "employee", "claim"]


def _gen_label_values(n=2000):
    """-> {label: set(values)} sampled from every generate.py/CGen value
    generator over universes A, B and C (spoken variants included)."""
    sys.path.insert(0, HERE)
    import generate as g
    import plant_generate as pg
    out = {}
    for u, cls in (("A", g.Gen), ("B", g.Gen), ("C", pg.CGen)):
        r = random.Random(f"fmtcheck:{u}")
        gen = cls(u, r)
        person = {"first": "Jane", "last": "Horn"}
        kinds = {
            "DATE": [lambda: gen.date(dob=False), lambda: gen.date(dob=True),
                     lambda: gen.date(spoken=True)],
            "AGE": [lambda: gen.old_age(), lambda: gen.old_age(spoken=True)],
            "PHONE": [lambda: gen.phone(), lambda: gen.phone(spoken=True)],
            "FAX": [lambda: gen.fax()] if cls is pg.CGen else [lambda: gen.phone()],
            "EMAIL": [lambda: gen.email(person), lambda: gen.email(person, spoken=True)],
            "URL": [lambda: gen.url()],
            "IP": [lambda: gen.ip()],
            "ZIP": [lambda: gen.zip()],
            "ADDRESS": [lambda: gen.address()],
            "LOCATION": [lambda: gen.city()],
            "ORG": [lambda: gen.org()],
            "VEHICLE": [lambda: gen.vin(), lambda: gen.plate()] if cls is pg.CGen else [],
            "MRN": [lambda: gen.idnum("mrn"), lambda: gen.idnum("mrn", True)],
            "SSN": [lambda: gen.idnum("ssn"), lambda: gen.idnum("itin"),
                    lambda: gen.idnum("ssn", True)],
            "PLAN": [lambda: gen.idnum("plan"), lambda: gen.idnum("plan", True)],
            "ACCOUNT": [lambda: gen.idnum(k) for k in ("account", "accession", "routing", "iban", "claim")],
            "LICENSE": [lambda: gen.idnum("license"), lambda: gen.idnum("bar"),
                        lambda: gen.idnum("license", True)],
            "DEVICE": [lambda: gen.idnum("device"), lambda: gen.idnum("device", True)],
            "ID": [lambda: gen.idnum(k) for k in ("ein", "docket", "matter", "employee")],
        }
        for _ in range(n):
            for lab, fns in kinds.items():
                for fn in fns:
                    v = fn()
                    out.setdefault(lab, set()).add(v[0] if isinstance(v, tuple) else v)
    return out


def check(verbose=True):
    test_fmts = [f for f in FORMATS if f.split == "test"]
    train_fmts = [f for f in FORMATS if f.split == "train"]

    # 1) each test format's own sampler produces regex-matching values,
    #    and its stated example matches.
    rng = random.Random(7)
    for f in test_fmts:
        rx = pattern_regex(f.pattern)
        for _ in range(200):
            v = compile_pattern(f.pattern)(rng)
            assert rx.fullmatch(v), f"{f.name}: sampled {v!r} fails own regex"
        assert rx.fullmatch(f.example), f"{f.name}: example {f.example!r} fails own regex"

    # 2) no same-label generated value fully matches a test-format regex.
    gen_by_label = _gen_label_values(2000)
    for f in test_fmts:
        rx = pattern_regex(f.pattern)
        for v in gen_by_label.get(f.label, ()):
            assert not rx.fullmatch(v), \
                f"test format {f.name} matches generate.py {f.label} value {v!r}"

    # 2b) cross-label collisions are informative warnings only (a novel SSN
    # shape resembling an ABA number is fine — different label).
    warns = []
    for f in test_fmts:
        rx = pattern_regex(f.pattern)
        for lab, vs in gen_by_label.items():
            if lab == f.label:
                continue
            for v in vs:
                if rx.fullmatch(v):
                    warns.append(f"{f.name}({f.label}) ~ {lab}:{v!r}")
                    break

    # 3) test values never match an expressible same-label train pattern.
    train_rx = [(t, pattern_regex(t.pattern)) for t in train_fmts if t.pattern]
    for f in test_fmts:
        gen = compile_pattern(f.pattern)
        same = [(t.name, rx) for t, rx in train_rx if t.label == f.label]
        r2 = random.Random(11)
        for _ in range(2000):
            v = gen(r2)
            for tn, rx in same:
                assert not rx.fullmatch(v), \
                    f"test {f.name} value {v!r} matches train pattern {tn}"

    # 4) sanity: every required label has >=3 test formats.
    need = {"MRN", "PLAN", "ACCOUNT", "LICENSE", "DEVICE", "VEHICLE", "SSN",
            "PHONE", "FAX", "DATE", "ZIP", "IP", "EMAIL", "URL", "AGE"}
    for lab in sorted(need):
        have = formats_for(lab, "test")
        assert len(have) >= 3, f"label {lab} has only {len(have)} test formats"

    if verbose:
        print(f"check OK: {len(test_fmts)} test formats, {len(train_fmts)} train formats, "
              f"{sum(len(v) for v in gen_by_label.values())} distinct generator values screened")
        if warns:
            print(f"cross-label resemblances (ok, different label): {len(warns)}")
            for w in warns:
                print("  warn:", w)
    return True


# ----------------------------------------------------------------------------
# CLI.
# ----------------------------------------------------------------------------

def cmd_list(a):
    for f in FORMATS:
        if a.label and f.label != a.label.upper():
            continue
        if a.split and f.split != a.split:
            continue
        print(f"{f.split:5} {f.label:8} {f.name:18} {f.pattern or '(generate.py)':58} {f.example}")


def cmd_add(a):
    if a.examples:
        pattern = infer_pattern(a.examples)
        example = a.example or a.examples[0]
    else:
        if not a.pattern:
            sys.exit("need --pattern or --examples")
        pattern = a.pattern
        _validate_pattern(pattern)
        example = a.example or compile_pattern(pattern)(random.Random(0))
    label = a.label.upper()
    if any(f.name == a.name and f.label == label for f in FORMATS):
        sys.exit(f"format {a.name!r} already exists for {label}")
    if a.split == "test":
        rx = pattern_regex(pattern)
        assert rx.fullmatch(example), "example does not match pattern"
        # novel-format guard: no same-label generated value may match
        for v in _gen_label_values(400).get(label, ()):
            assert not rx.fullmatch(v), f"pattern matches generate.py value {v!r} — not novel"
    user = _load_user()
    user.append(Format(a.name, label, a.split, pattern, example))
    _save_user(user)
    FORMATS.clear()
    FORMATS.extend(_all())
    print(f"added {a.split} format {a.name} ({label}): {pattern!r} -> {USER_PATH}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="list registered formats")
    p.add_argument("--label")
    p.add_argument("--split", choices=["train", "test"])
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("add", help="append a user format to formats_user.json")
    p.add_argument("label")
    p.add_argument("--split", required=True, choices=["train", "test"])
    p.add_argument("--name", required=True)
    p.add_argument("--pattern")
    p.add_argument("--examples", nargs="+")
    p.add_argument("--example")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("check", help="prove test formats are novel")
    p.set_defaults(fn=lambda a: check())
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
