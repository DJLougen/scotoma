#!/usr/bin/env python3
"""Synthetic redaction benchmark generator. Standard library only.

    python bench/generate.py --universe B --n 1500 --seed 1 --out bench/data/test.jsonl
    python bench/generate.py --universe A --n 20000 --seed 7 --out bench/data/train.jsonl

Two universes, A (train) and B (test), share NOTHING that a model could
memorise: disjoint name pools, street names, cities, organisations and
sentence templates. A model trained on A and scored on B is being tested on
the pattern, not on recall of strings it has seen.

Every identifier carries difficulty tags so results can be broken down by what
makes an item hard rather than averaged away:

  cue / no_cue        a label such as "MRN:" precedes it, or nothing does
  single_name         a bare first name or bare surname
  common_word_name    the name is also an English word (May, Rose, Hunter)
  relative            a third party, not the main subject
  repeat              a later mention of an already-introduced person
  spoken              rendered as dictation ("3 3 0 9", "the fourth of May")
  ocr                 character noise inside the identifier (O/0, l/1, rn/m)
  chat                lower-case, unpunctuated message style
  fmt:<x>             surface format of dates, phones and IDs

Output: one JSON object per line: id, domain, mode, universe, text,
spans[{start, end, label, kind, tags}]. Offsets are in characters; `label` is
a Scotoma category, `kind` the fine-grained type.
"""
import argparse, json, random, re

# ----------------------------------------------------------------------------
# Disjoint vocabularies. A = train, B = test. Do not move items between them.
# ----------------------------------------------------------------------------
FIRST = {
 "A": "James Maria Wei Aisha Carlos Fatima John Priya Ahmed Elena Kwame Yuki Sofia Dmitri Amara Luis Hannah Raj Ingrid Tomas Nadia Samuel Mei Olga Kofi Lucia Hassan Greta Diego Zainab Peter Ananya Viktor Chloe Emeka Rosa Henrik Leila Mateo Sunita Oscar Farah Daniel Keiko Andre Miriam Pablo Thandi Felix Noor Ivan Camila Jamal Astrid Rafael Huda Simon Lakshmi Bruno Esther Marco Yasmin Nikolai Carmen Tariq Freya Hugo Deepa Stefan Imani Julian Rania Anton Paloma Idris Signe".split(),
 "B": "Eleanor Vikram Beatrice Emeka2 Thomas Rachel Margaret Okonkwo Nadia2 Gordon Samantha Yusuf Claire Lucas Jonathan Raymond Ngozi Leila2 Adaeze Tobias Hana Gilles Oluwaseun Minh Abimbola Ruth Helen Aiyana Kimi Dana Fatou Cormac Saoirse Bartholomew Xiomara Thabo Anneliese Zdenek Ignacio Marisol Dariusz Wanjiru Tevita Mahnoor Soren Ximena Babajide Liesel Caoimhe Rustam Ayasha Ebele Fumiko Gwendolyn Hamza Isolde Jovan Kalinda Lorcan Mirembe Nuno Ottoline Parisa Quentin Rosalind Sipho Tamsin Ulrich Vesna Wolfgang Yevgenia Zoltan".replace("Emeka2", "Chidi").replace("Nadia2", "Nasrin").replace("Leila2", "Laleh").split(),
}
LAST = {
 "A": "Smith Garcia Chen Khan Rodriguez Hussain Johnson Patel Ali Petrov Mensah Tanaka Rossi Ivanov Okeke Martinez Schmidt Sharma Larsen Novak Haddad Cohen Wong Kuznetsov Boateng Fernandez Rahman Müller Torres Abdi Andersen Reddy Sokolov Dubois Eze Morales Nilsson Karimi Silva Gupta Lindberg Aziz Levy Sato Costa Stein Mbeki Vargas Nasser Popov Romero Jackson Berg Santos Chowdhury Fischer Ncube Moreau Sandhu Hoffman Castro Yilmaz Bianchi Farouk Olsen Delgado Mahlangu Weber Navarro Kaya Johansson Ortiz Siddiqui Meyer Pereira Demir".split(),
 "B": "Whitfield Anand Ellison Okafor Brennan Osei Castellanos Haddad2 Leclerc Whitaker Roy Demir2 Fontaine Ferreira Akhtar Castillo Nwosu Subramaniam MacPherson Tremblay Bankole-Jones Tran Adeyemi Abramson Papadakis Redcloud Kowalski Diallo O'Riordan Ní Bhraonáin Featherstonehaugh Quispe Dlamini Vandenberghe Dvořák Etxeberria Villalobos Wiśniewski Kamau Taufa Qureshi Thorvaldsen Huanca Adewale-Scott Zimmermann Ó Súilleabháin Yusupov Blackfeather Onyekachi Hayashida St. Clair Al-Mansouri de la Fuente Van der Merwe Nakagawa D'Angelo".replace("Haddad2", "Haddadin").replace("Demir2", "Demirci").split(),
}
# Fix multi-word surnames that .split() broke apart (B only).
LAST["B"] = [s for s in LAST["B"] if s not in {"Ní", "Bhraonáin", "St.", "Clair", "de", "la", "Fuente", "Van", "der", "Merwe", "Ó", "Súilleabháin"}] + [
    "Ní Bhraonáin", "St. Clair", "de la Fuente", "Van der Merwe", "Ó Súilleabháin"]
# Names that are also ordinary words: the classic false-negative trap. Test only.
COMMON_FIRST = "May Rose Grace Hunter Hope Mark Will Art Faith Joy Chase Frank June Summer Rich Bill Pat Miles Sandy Dawn".split()
COMMON_LAST = "White Brown Young Long Strong Wells Burns Payne Price Banks Fields Woods Stone Cross King Page Cook Hill Lane Day Weeks Best Little Bell Graves".split()

STREET = {"A": "Maple Oak Cedar Pine Elm Lake Hill Park Main Church Mill River Spring Forest Meadow Bridge".split(),
          "B": "Dufferin Garrison Lakeshore Kingston Wallaby Harbour Queen Broadview Saint-Denis Quarry Tamarind Osprey Bellwether Cobblestone Larkspur Windermere".split()}
STYPE = {"A": ["Street", "Avenue", "Road", "Drive", "St", "Ave", "Rd", "Dr"], "B": ["Boulevard", "Lane", "Court", "Crescent", "Terrace", "Way", "Blvd", "Ln", "Ct", "Sq"]}
CITY = {"A": [("Springfield", "IL"), ("Columbus", "OH"), ("Austin", "TX"), ("Denver", "CO"), ("Portland", "OR"), ("Raleigh", "NC"), ("Madison", "WI"), ("Tucson", "AZ"), ("Albany", "NY"), ("Tampa", "FL")],
        "B": [("Hamilton", "ON"), ("Oshawa", "ON"), ("Sudbury", "ON"), ("Scarborough", "ON"), ("Duluth", "MN"), ("Boise", "ID"), ("Spokane", "WA"), ("Mobile", "AL"), ("Reno", "NV"), ("Caledon", "ON")]}
ORG = {"A": ["Northgate Medical Group", "Hartwell & Finch LLP", "Pioneer Tax Services", "Summit Logistics Inc", "Riverside General Hospital", "Calder Bank"],
       "B": ["Lakeridge Health", "Maple Grove Residence", "Okoro Vance LLP", "Tidewater Accounting", "Brightline Freight Ltd", "Credit Valley Hospital", "First Meridian Bank"]}
MAILHOST = {"A": ["example.com", "mail.example.com", "example.org"], "B": ["example.net", "clinic.example.org", "corp.example.io"]}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth", "twenty-first", "twenty-second", "twenty-third", "twenty-fourth", "twenty-fifth", "twenty-sixth", "twenty-seventh", "twenty-eighth", "twenty-ninth", "thirtieth", "thirty-first"]


class Gen:
    def __init__(self, universe, rng):
        self.u, self.r = universe, rng

    def pick(self, xs):
        return self.r.choice(xs)

    def digits(self, n):
        return "".join(self.r.choice("0123456789") for _ in range(n))

    # --- people -------------------------------------------------------------
    def person(self):
        common = self.u == "B" and self.r.random() < 0.18
        first = self.pick(COMMON_FIRST) if common and self.r.random() < 0.6 else self.pick(FIRST[self.u])
        last = self.pick(COMMON_LAST) if common and (first not in COMMON_FIRST or self.r.random() < 0.4) else self.pick(LAST[self.u])
        return {"first": first, "last": last, "common": first in COMMON_FIRST or last in COMMON_LAST}

    def name(self, p, form=None):
        form = form or self.r.choices(["full", "full", "last", "first", "last_first", "initial"], [5, 3, 2, 2, 1, 1])[0]
        tags = []
        if form == "full": s = f"{p['first']} {p['last']}"
        elif form == "last": s, tags = p["last"], ["single_name"]
        elif form == "first": s, tags = p["first"], ["single_name"]
        elif form == "last_first": s, tags = f"{p['last'].upper()}, {p['first'].upper()}", ["fmt:last_first_caps"]
        else: s, tags = f"{p['first'][0]}. {p['last']}", ["fmt:initial"]
        word = {"first": [p["first"]], "last": [p["last"]]}.get(form, [p["first"], p["last"]])
        if any(w in COMMON_FIRST or w in COMMON_LAST for w in word): tags.append("common_word_name")
        return s, "NAME", "person", tags

    # --- dates & ages ---------------------------------------------------------
    def date(self, dob=False, spoken=False):
        y = self.r.randint(1928, 2006) if dob else self.r.randint(2019, 2025)
        m, d = self.r.randint(1, 12), self.r.randint(1, 28)
        if spoken:
            f = self.r.choice(["the {o} of {M} {y}", "{M} {o} {y}", "{M} the {o}", "{M} {d}th {y}" if d not in (1, 2, 3, 21, 22, 23) else "{M} {d} {y}"])
            return f.format(o=ORD[d - 1], M=MONTHS[m - 1], y=y, d=d), "DATE", "dob" if dob else "date", ["spoken"]
        fmts = {"numeric_us": f"{m:02d}/{d:02d}/{y}", "numeric_short": f"{m}/{d}/{str(y)[2:]}", "iso": f"{y}-{m:02d}-{d:02d}",
                "named": f"{MONTHS[m-1]} {d}, {y}", "named_abbr": f"{MONTHS[m-1][:3]} {d}, {y}", "day_first": f"{d} {MONTHS[m-1]} {y}",
                "dashed": f"{d:02d}-{MONTHS[m-1][:3]}-{y}", "partial": f"{MONTHS[m-1]} {d}", "month_year": f"{MONTHS[m-1]} {y}"}
        pool = list(fmts) if self.u == "B" else ["numeric_us", "iso", "named", "numeric_short", "named_abbr", "partial"]
        if dob: pool = [k for k in pool if k not in ("partial", "month_year")]
        k = self.pick(pool)
        return fmts[k], "DATE", "dob" if dob else "date", [f"fmt:{k}"]

    def old_age(self, spoken=False):
        n = self.r.randint(90, 103)
        if spoken and n < 100:
            return ("ninety" if n == 90 else "ninety-" + ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][n - 91]), "AGE", "age_over_89", ["spoken"]
        return str(n), "AGE", "age_over_89", []

    # --- contact ---------------------------------------------------------------
    def phone(self, spoken=False):
        a, b, c = self.r.randint(201, 989), "555", f"01{self.r.randint(0, 99):02d}"
        if spoken: return f"{a} {b} {c}", "PHONE", "phone", ["spoken"]
        fmts = {"paren": f"({a}) {b}-{c}", "dash": f"{a}-{b}-{c}", "dot": f"{a}.{b}.{c}", "space": f"{a} {b} {c}", "intl": f"+1 {a} {b} {c}", "plain": f"{a}{b}{c}"}
        k = self.pick(list(fmts) if self.u == "B" else ["paren", "dash", "dot"])
        return fmts[k], "PHONE", "phone", [f"fmt:{k}"]

    def email(self, p, spoken=False):
        local = self.pick([f"{p['first']}.{p['last']}", f"{p['first'][0]}{p['last']}", f"{p['first']}{self.r.randint(1, 99)}", f"{p['last']}_{p['first'][0]}"]).lower()
        local = re.sub(r"[^a-z0-9._]", "", local) or "user"
        host = self.pick(MAILHOST[self.u])
        if spoken:
            return f"{local.replace('.', ' dot ').replace('_', ' underscore ')} at {host.replace('.', ' dot ')}", "EMAIL", "email", ["spoken"]
        return f"{local}@{host}", "EMAIL", "email", []

    def url(self):
        return f"https://portal.{self.pick(MAILHOST[self.u])}/{self.pick(['view', 'p', 'case', 'doc'])}?id={self.digits(6)}", "URL", "url", []

    def ip(self):
        return f"{self.pick([203, 198, 192])}.{self.r.randint(0, 255)}.{self.r.randint(0, 255)}.{self.r.randint(1, 254)}", "IP", "ipv4", []

    # --- numbers ----------------------------------------------------------------
    def spaced(self, s):
        return " ".join(ch for ch in s if ch.isalnum())

    def idnum(self, kind, spoken=False):
        r = self.r
        make = {
            "mrn": lambda: ("MRN", r.choice([self.digits(8), f"{self.digits(4)}-{self.digits(5)}", f"{r.choice('ABKM')}{self.digits(7)}"])),
            "ssn": lambda: ("SSN", f"{r.randint(100, 665)}-{r.randint(10, 99)}-{self.digits(4)}"),
            "plan": lambda: ("PLAN", r.choice([f"{self.digits(4)}-{self.digits(3)}-{self.digits(3)}-{r.choice('ABKMXQ')}{r.choice('RTZW')}", f"{r.choice('HXQ')}{r.choice('XJK')}-{self.digits(3)}-{self.digits(4)}-{self.digits(2)}"])),
            "account": lambda: ("ACCOUNT", self.digits(r.choice([10, 12]))),
            "accession": lambda: ("ACCOUNT", f"{r.choice(['RAD', 'SUR', 'LAB'])}-{r.randint(2020, 2025)}{self.digits(4)}-{self.digits(4)}"),
            "device": lambda: ("DEVICE", f"{r.choice(['BSX', 'ZBK', 'PJK', 'MDT'])}-{self.digits(8)}"),
            "license": lambda: ("LICENSE", r.choice([f"RN-{self.digits(7)}", f"{r.choice('DGKS')}{self.digits(4)}-{self.digits(5)}-{self.digits(5)}"])),
            "ein": lambda: ("ID", f"{self.digits(2)}-{self.digits(7)}"),
            "itin": lambda: ("SSN", f"9{self.digits(2)}-7{self.digits(1)}-{self.digits(4)}"),
            "routing": lambda: ("ACCOUNT", self.aba()),
            "iban": lambda: ("ACCOUNT", f"GB{self.digits(2)} {r.choice(['NWBK', 'BARC', 'HBUK'])} {self.digits(4)} {self.digits(4)} {self.digits(4)} {self.digits(2)}"),
            "docket": lambda: ("ID", r.choice([f"{r.randint(1, 9)}:{r.randint(19, 25)}-cv-{self.digits(5)}", f"CV-{r.randint(2019, 2025)}-{self.digits(6)}", f"{r.randint(19, 25)}-{self.digits(4)}"])),
            "matter": lambda: ("ID", f"{self.digits(5)}.{self.digits(4)}"),
            "bar": lambda: ("LICENSE", self.digits(6)),
            "employee": lambda: ("ID", f"E{self.digits(6)}"),
            "claim": lambda: ("ACCOUNT", f"CLM-{self.digits(9)}"),
        }
        label, val = make[kind]()
        if spoken: return self.spaced(val), label, kind, ["spoken"]
        return val, label, kind, []

    def aba(self):
        d = [self.r.randint(0, 9) for _ in range(8)]
        chk = (10 - (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5])) % 10) % 10
        return "".join(map(str, d)) + str(chk)

    # --- places -----------------------------------------------------------------
    def address(self):
        s = f"{self.r.randint(1, 9900)} {self.pick(STREET[self.u])} {self.pick(STYPE[self.u])}"
        if self.r.random() < 0.3: s += f", {self.pick(['Apt', 'Unit', 'Suite'])} {self.r.randint(1, 40)}"
        return s, "ADDRESS", "street", []

    def city(self):
        return self.pick(CITY[self.u])[0], "LOCATION", "city", []

    def zip(self):
        return self.digits(5), "ZIP", "zip", []

    def org(self):
        return self.pick(ORG[self.u]), "ORG", "organisation", []


# ----------------------------------------------------------------------------
# Templates. Slots: {P}=subject  {P2}=another person  plus generator names.
# A slot may carry a cue marker: {mrn!} means "this occurrence is cued".
# Even-indexed templates belong to universe A, odd-indexed to B: no overlap.
# ----------------------------------------------------------------------------
T = {
 "clinical": [
  "Patient: {P:full}   DOB: {dob!}   MRN: {mrn!}",
  "{P:last_first} {age_y} y/o {sex}, MRN {mrn!}, brought in by EMS from {address}.",
  "Seen today in clinic. {P:first} reports the pain is better since {date}.",
  "Mrs. {P:last} is a {old_age}-year-old woman admitted on {date} with pneumonia.",
  "Attending: Dr. {P2:full}, MD   Phone: {phone!}   Fax: {phone!}",
  "{P:first} came in again with the same cough; says {P2:first} drove her and the kids were sent home from school.",
  "Spoke with the patient's daughter, {P2:full}, at {phone!}. She will pick him up on {date}.",
  "Lives near {city} with roommate {P2:first}; works nights at {org}.",
  "Referred by Dr. {P2:last} for follow-up of hypertension. Next visit {date}.",
  "Discussed with {P2:initial} in nephrology, who agreed to see {P:last} before {date}.",
  "Emergency contact: {P2:full}, {phone}. Email {email!}.",
  "Her mother turned {old_age} last spring and is moving in from {city}.",
  "Home address is {address}, {city}, {state} {zip}.",
  "Results were uploaded to {url} from {ip} and faxed to {phone}.",
  "Pacemaker serial number: {device!}. Health plan member ID: {plan!}.",
  "Implant lot {device} placed {date}; billing reference {accession}.",
  "Insurance on file. SSN {ssn!}. Policy number {plan!}.",
  "{P:full} ({mrn}) was discharged {date} to {org}.",
  "Dictated by: {P2:full}, MD. License number: {license!}.",
  "Pharmacist {P2:last} confirmed warfarin dosing; orders sent {date}.",
 ],
 "tax": [
  "Taxpayer: {P:full}   SSN: {ssn!}   Filing status: single",
  "Prepared the {year} return for {P:full} and spouse {P2:first}; ITIN for the spouse is {itin}.",
  "Employer: {org}, EIN {ein!}. Wages reported on the W-2 match payroll.",
  "{org} ({ein}) issued a 1099-NEC to {P:last} on {date}.",
  "Refund to be deposited to routing {routing!}, account {account!}.",
  "Client asked that the refund go to the joint account ending in the number {account}, routing {routing}.",
  "Mailing address: {address}, {city}, {state} {zip}.",
  "{P:first} called from {phone} about the notice dated {date}; she lives at {address}.",
  "Dependent: {P2:full}, born {dob!}.",
  "Daughter {P2:first} ({dob}) qualifies for the child credit again this year.",
  "Wire the balance from IBAN {iban!} before {date}.",
  "Estimated payment drawn on {iban} cleared {date}; confirmation emailed to {email}.",
  "Engagement letter signed by {P:full} on {date}. Contact: {email!}.",
  "Per {P2:initial} at {org}, the amended return was mailed {date}.",
 ],
 "legal": [
  "{P:full} v. {org}, Case No. {docket!}",
  "In the matter of {P:last}, docket {docket}, hearing set for {date}.",
  "Plaintiff {P:full} resides at {address}, {city}, {state} {zip}.",
  "Our client, {P:first}, was terminated on {date} after reporting her supervisor {P2:full}.",
  "Counsel for the defendant: {P2:full}, Bar No. {bar!}, {org}.",
  "Opposing counsel {P2:last} ({bar}) emailed from {email} requesting an extension to {date}.",
  "Client-matter number {matter!}. Conflict check cleared {date}.",
  "Billing for {matter} went to {P:full} at {email!}.",
  "The witness, {P2:full}, born {dob!}, gave a statement on {date}.",
  "{P2:first} told investigators she saw {P:last} leave {org} around noon on {date}.",
  "Settlement funds to be wired to account {account!}, routing {routing!}.",
  "Deposition of {P:full} scheduled {date} at the offices of {org}; call {phone} to confirm.",
  "Driver's license {license!} was produced as identification.",
  "Notice served on {P2:initial} at {address} on {date}.",
 ],
 "hr": [
  "Employee: {P:full}   ID: {employee!}   Start date: {date}",
  "{P:first} ({employee}) has asked to move to the {city} office from {date}.",
  "Manager {P2:full} approved leave for {P:last} through {date}.",
  "Complaint filed by {P:full} against {P2:first} on {date}; both report to {P2:last}.",
  "Home address on file: {address}, {city}, {state} {zip}. Phone {phone!}.",
  "Offer letter sent to {email} and a copy to her partner {P2:first} at {phone}.",
  "Background check for {P:full}, DOB {dob!}, SSN {ssn!}, completed {date}.",
  "Reference call with {P2:initial} of {org} went well; start date {date}.",
  "Direct deposit: routing {routing!}, account {account!}.",
  "Benefits claim {claim!} for dependent {P2:full} was approved.",
  "Payroll changed deposit to the account {account} after {P:first} emailed from {email}.",
  "Exit interview with {P:last} held {date}; laptop returned by {P2:first}.",
 ],
}
# Sentences with NO identifiers. Many contain things that look like identifiers
# and are not: eponyms, scores, doses, statute cites. These are the false-alarm traps.
FILLER = {
 "clinical": ["Strength 4/5 in the left leg, pain 7/10.", "BP 138/84, HR 72, SpO2 97% on room air.", "May repeat the dose in 6 hours if needed.",
              "Findings consistent with Graves disease; no signs of Bell's palsy.", "Glasgow Coma Scale 15. Apgar scores were 8 and 9.",
              "Continue metformin 1000 mg BID and lisinopril 10 mg daily.", "Hickman line flushed; Foley removed on day 2.", "Wilson's disease was ruled out.",
              "ECOG 1, EF 55%, creatinine 1.02.", "Parkinson disease stable on current regimen; Romberg negative."],
 "tax": ["Schedule C shows a net loss carried forward.", "Form 8829 was completed for the home office.", "Section 179 expense elected for equipment.",
         "Standard deduction applied; no itemizing this year.", "The 1040 was e-filed and accepted.", "Estimated payments of 4 x 1,250 were made.", "Basis was adjusted under Section 1014."],
 "legal": ["Motion to dismiss under Rule 12(b)(6) was denied.", "See 42 U.S.C. 1983 and the cases cited therein.", "The court applied the Daubert standard.",
           "Discovery closes in 90 days.", "Miranda warnings were given.", "Under the Chevron framework the agency's reading was upheld.", "Exhibit 14 was admitted without objection."],
 "hr": ["Performance rating: 4 of 5.", "Completed the 90-day probation period.", "Enrolled in the Blue plan with a 500 deductible.", "PTO balance is 12.5 days.",
        "Reviewed against the Level 3 competency rubric.", "Standard two weeks notice applies."],
}
# A cue is a word just before the identifier that announces what it is.
CUE = re.compile(r"(?i)(?:\b(?:dr|mrs?|ms|miss|prof)\.?|\b(?:counsel|manager|pharmacist|daughter|son|spouse|partner|roommate|supervisor|witness|plaintiff|client|patient|employee|taxpayer|dependent|contact|attending|mrn|record|ssn|social|itin|ein|routing|account|iban|docket|case no\.?|bar no\.?|member id|policy number|id|serial number|lot|licen[sc]e(?: number)?|phone|fax|email|dob|born|claim|matter number|number)\b)[\s:#,(]*$")
SPOKEN_OK = {"date", "dob", "phone", "old_age", "email", "mrn", "plan", "ssn", "account", "routing", "employee", "license", "device"}
OCR = [("0", "O"), ("O", "0"), ("1", "l"), ("l", "1"), ("rn", "m"), ("m", "rn"), ("5", "S"), ("8", "B"), ("cl", "d")]


def build(domain, mode, universe, rng, doc_id):
    g = Gen(universe, rng)
    pool = [t for i, t in enumerate(T[domain]) if i % 2 == (0 if universe == "A" else 1)]
    people = {"P": g.person(), "P2": g.person()}
    seen = set()
    n = rng.randint(2, 5)
    chosen = rng.sample(pool, min(n, len(pool)))
    # Background sentences are split between universes too, so a model cannot
    # learn "anything I have not seen as filler is an identifier".
    filler = [f for i, f in enumerate(FILLER[domain]) if i % 2 == (0 if universe == "A" else 1)]
    lines = []
    for t in chosen:
        lines.append(("t", t))
        if rng.random() < 0.6: lines.append(("f", rng.choice(filler)))
    rng.shuffle(lines) if rng.random() < 0.3 else None

    text, spans = "", []
    for kind, line in lines:
        if kind == "f":
            text += (line.lower() if mode == "chat" else line) + ("\n" if rng.random() < 0.5 else " ")
            continue
        pos = 0
        for m in re.finditer(r"\{(\w+)(?::(\w+))?(!)?\}", line):
            lit = line[pos:m.start()]
            text += lit.lower() if mode == "chat" else lit
            pos = m.end()
            slot, arg, cued = m.group(1), m.group(2), bool(m.group(3))
            spoken = mode == "dictated" and slot in SPOKEN_OK
            tags = []
            if slot in ("P", "P2"):
                val, label, k, tags = g.name(people[slot], arg)
                if slot == "P2": tags.append("relative")
                key = (slot, "name")
                if key in seen: tags.append("repeat")
                seen.add(key)
            elif slot == "dob": val, label, k, tags = g.date(dob=True, spoken=spoken)
            elif slot == "date": val, label, k, tags = g.date(spoken=spoken)
            elif slot == "old_age": val, label, k, tags = g.old_age(spoken)
            elif slot == "phone": val, label, k, tags = g.phone(spoken)
            elif slot == "email": val, label, k, tags = g.email(people["P"], spoken)
            elif slot in ("address", "city", "zip", "org", "url", "ip"): val, label, k, tags = getattr(g, slot)()
            elif slot == "state":
                text += rng.choice(CITY[universe])[1]; continue          # states are not identifiers
            elif slot == "age_y":
                text += str(rng.randint(18, 88)); continue                # ages under 90 are not identifiers
            elif slot == "sex":
                text += rng.choice("MF"); continue
            elif slot == "year":
                text += str(rng.randint(2019, 2025)); continue
            else: val, label, k, tags = g.idnum(slot, spoken)
            tags = list(tags) + ["cue" if cued or CUE.search(lit[-28:]) else "no_cue"]
            if mode == "chat":
                val = val.lower(); tags.append("chat")
            if mode == "ocr" and rng.random() < 0.35:
                for a, b in rng.sample(OCR, len(OCR)):
                    if a in val:
                        val = val.replace(a, b, 1); tags.append("ocr"); break
            spans.append({"start": len(text), "end": len(text) + len(val), "label": label, "kind": k, "tags": sorted(set(tags))})
            text += val
        tail = line[pos:]
        text += (tail.lower() if mode == "chat" else tail) + ("\n" if mode != "dictated" and rng.random() < 0.6 else " ")
    text = text.rstrip()
    spans = [s for s in spans if s["end"] <= len(text)]
    return {"id": doc_id, "domain": domain, "mode": mode, "universe": universe, "text": text, "spans": spans}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", choices=["A", "B"], required=True, help="A = train vocabulary/templates, B = test")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--domains", default="clinical,tax,legal,hr")
    ap.add_argument("--modes", default="written:6,dictated:2,ocr:1,chat:1", help="mode:weight,...")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rng = random.Random(f"{a.universe}-{a.seed}")
    domains = a.domains.split(",")
    modes, weights = zip(*[(m.split(":")[0], float(m.split(":")[1])) for m in a.modes.split(",")])
    with open(a.out, "w", encoding="utf-8") as f:
        for i in range(a.n):
            d = build(rng.choice(domains), rng.choices(modes, weights)[0], a.universe, rng, f"{a.universe}{a.seed}-{i:06d}")
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"wrote {a.n} documents to {a.out}")


if __name__ == "__main__":
    main()
