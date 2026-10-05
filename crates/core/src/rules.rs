//! Deterministic detectors for structured identifiers, plus name heuristics
//! that hold the line when no model is loaded.

use crate::{Category, Source, Span};
use regex::Regex;
use std::sync::OnceLock;

type Check = fn(&str, &str) -> bool;

struct Rule {
    re: Regex,
    cat: Category,
    /// Capture group holding the identifier (0 = whole match).
    group: usize,
    conf: f32,
    /// Extra validation: (captured text, whole match) → keep?
    check: Option<Check>,
    dob: bool,
}

const MONTH: &str = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUNE?|JULY?|AUG(?:UST)?|SEP(?:T(?:EMBER)?)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)";
const STREET: &str = r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl|Circle|Cir|Terrace|Ter|Parkway|Pkwy|Highway|Hwy|Trail|Trl|Square|Sq|Crescent|Cres|Close|Row|Alley)";
const STATE: &str = r"(?:AL|AK|AZ|AR|CA|CO|CT|DE|DC|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|PR)";
const IDVAL: &str = r"([A-Za-z0-9][A-Za-z0-9-]{3,23})";
/// One name token: Smith, O'Brien, Al-Sayed, McDonald, SMITH.
const NTOK: &str = r"(?:(?:Mc|Mac|O['’]|D['’])[A-Z][a-z]+(?:-[A-Z][a-z]+)*|[A-Z][a-z]+(?:['’-][A-Z]?[a-z]+)*|[A-Z]{2,})";
/// Lower-case-able name particles: de la Cruz, van der Berg, bin Rashid.
const PART: &str = r"(?:de|De|la|La|van|Van|von|Von|del|Del|der|den|di|Di|da|Da|le|Le|bin|ibn|al|Al|el|El|St\.)";
/// One all-caps word: SMITH, O'NEIL, AL-SAYED, VAN.
const CTOK: &str = r"[A-Z]+(?:[-'’][A-Z]+)*";

fn digits(s: &str) -> usize {
    s.bytes().filter(|b| b.is_ascii_digit()).count()
}
fn has_digit(v: &str, _: &str) -> bool { digits(v) >= 1 }
fn has_4_digits(v: &str, _: &str) -> bool { digits(v) >= 4 }
fn has_3_digits(v: &str, _: &str) -> bool { digits(v) >= 3 }

fn luhn(v: &str, _: &str) -> bool {
    let d: Vec<u32> = v.chars().filter_map(|c| c.to_digit(10)).collect();
    if d.len() < 13 || d.len() > 19 { return false; }
    let sum: u32 = d.iter().rev().enumerate().map(|(i, &x)| {
        if i % 2 == 1 { let y = x * 2; if y > 9 { y - 9 } else { y } } else { x }
    }).sum();
    sum % 10 == 0
}

fn valid_ssn(v: &str, _: &str) -> bool {
    let d: Vec<u8> = v.bytes().filter(|b| b.is_ascii_digit()).collect();
    if d.len() != 9 { return false; }
    let area = &d[0..3];
    area != b"000" && area != b"666" && area[0] != b'9' && &d[3..5] != b"00" && &d[5..9] != b"0000"
}

/// VIN: 17 chars, mixed letters and digits, valid check digit (position 9).
fn valid_vin(v: &str, _: &str) -> bool {
    let b = v.as_bytes();
    if b.len() != 17 || digits(v) < 3 || digits(v) > 14 { return false; }
    let val = |c: u8| -> u32 {
        match c {
            b'0'..=b'9' => (c - b'0') as u32,
            b'A'..=b'H' => (c - b'A') as u32 + 1,
            b'J'..=b'N' => (c - b'J') as u32 + 1,
            b'P' => 7, b'R' => 9,
            b'S'..=b'Z' => (c - b'S') as u32 + 2,
            _ => 0,
        }
    };
    let w = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2];
    let sum: u32 = b.iter().zip(w.iter()).map(|(&c, &w)| val(c) * w).sum();
    let chk = sum % 11;
    let want = if chk == 10 { b'X' } else { b'0' + chk as u8 };
    b[8] == want
}

/// ABA routing number checksum (3-7-1 weights).
fn valid_aba(v: &str, _: &str) -> bool {
    let d: Vec<u32> = v.chars().filter_map(|c| c.to_digit(10)).collect();
    d.len() == 9 && (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + d[2] + d[5] + d[8]) % 10 == 0
        && d.iter().any(|&x| x != d[0])
}

/// IBAN shape: country + 2 check digits + 11..30 more, at least 8 digits overall.
fn valid_iban(v: &str, _: &str) -> bool {
    let c: Vec<char> = v.chars().filter(|c| !c.is_whitespace()).collect();
    (15..=34).contains(&c.len()) && c.iter().filter(|c| c.is_ascii_digit()).count() >= 8
        && c[..2].iter().all(|c| c.is_ascii_uppercase())
}

fn age_over_89(v: &str, _: &str) -> bool {
    v.parse::<u32>().map(|n| (90..=125).contains(&n)).unwrap_or(false)
}

fn not_all_same(v: &str, _: &str) -> bool {
    let d: Vec<u8> = v.bytes().filter(|b| b.is_ascii_digit()).collect();
    d.len() >= 7 && d.iter().any(|&x| x != d[0])
}

fn rules() -> &'static Vec<Rule> {
    static R: OnceLock<Vec<Rule>> = OnceLock::new();
    R.get_or_init(|| {
        let mut v: Vec<Rule> = Vec::new();
        let mut add = |pat: String, cat: Category, group: usize, conf: f32, check: Option<Check>, dob: bool| {
            v.push(Rule { re: Regex::new(&pat).expect(&pat), cat, group, conf, check, dob });
        };
        use Category::*;

        // --- contact / network -------------------------------------------------
        add(r"(?i)\b[a-z0-9][a-z0-9._%+-]*@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}\b".into(), Email, 0, 1.0, None, false);
        add(r#"(?i)\b(?:https?://|www\.)[^\s<>"'\])]+[^\s<>"'\]).,;:!?]"#.into(), Url, 0, 1.0, None, false);
        add(r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b".into(), Ip, 0, 0.9, None, false);
        add(r"(?i)\b(?:[0-9a-f]{1,4}:){7}[0-9a-f]{1,4}\b".into(), Ip, 0, 0.95, None, false);
        add(r"(?i)(?:\b[0-9a-f]{1,4}(?::[0-9a-f]{1,4}){0,5})?::(?:[0-9a-f]{1,4}(?::[0-9a-f]{1,4}){0,5})\b".into(), Ip, 0, 0.8, None, false);
        add(r"(?i)\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b".into(), Device, 0, 0.95, None, false);
        add(r"(?i)\bfax(?:\s*(?:number|no\.?|#))?\s*[:#]?\s*((?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4})\b".into(), Fax, 1, 1.0, None, false);
        add(r"(?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\b\d{3}[\s.-])\d{3}[\s.-]\d{4}\b(?:\s*(?:x|ext\.?|extension)\s*\d{1,6})?".into(), Phone, 0, 0.95, Some(not_all_same), false);
        add(r"\+\d{1,3}[\s.-]?\(?\d{1,4}\)?(?:[\s.-]?\d{2,4}){2,4}\b".into(), Phone, 0, 0.9, Some(not_all_same), false);
        add(r"(?i)\b(?:phone|tel|telephone|cell|mobile|pager|call(?:back)?|contact)(?:\s*(?:number|no\.?|#))?\s*[:#]?\s*(\d{3}[\s.-]?\d{4}|\d{10})\b".into(), Phone, 1, 0.85, None, false);

        // --- government / record numbers --------------------------------------
        add(r"\b\d{3}-\d{2}-\d{4}\b".into(), Ssn, 0, 0.97, Some(valid_ssn), false);
        add(r"(?i)\b(?:ssn|ss#|social security(?:\s*(?:number|no\.?|#))?)\s*[:#]?\s*(\d{3}[- ]?\d{2}[- ]?\d{4}|(?:[x*]{3}[- ]?[x*]{2}[- ]?)\d{4})\b".into(), Ssn, 1, 1.0, None, false);
        add(format!(r"(?i)\b(?:mrn|medical record(?:\s*(?:number|no\.?|#))?|med\.?\s?rec\.?(?:\s*(?:number|no\.?|#))?|patient\s?id|pt\.?\s?id|chart(?:\s*(?:number|no\.?|#))|unit\s*(?:number|no\.?|#)|hospital\s*(?:number|no\.?|#))\s*[:#]?\s*#?{IDVAL}"), Mrn, 1, 1.0, Some(has_3_digits), false);
        add(format!(r"(?i)\b(?:(?:member(?:ship)?|policy|subscriber|group|insurance|beneficiary|medicare|medicaid|plan|health(?:\s*card)?|ohip|nhs)\s*(?:id|number|no\.?|#)|mbi|hicn|hcn|ohip|health\s*card)\s*[:#]?\s*#?{IDVAL}"), Plan, 1, 1.0, Some(has_3_digits), false);
        add(format!(r"(?i)\b(?:account|acct\.?|invoice|claim|encounter|visit|accession|order|case|reference|ref\.?|confirmation|billing|specimen|requisition|csn|fin)\s*(?:id|number|no\.?|#)?\s*[:#]?\s*#?{IDVAL}"), Account, 1, 0.9, Some(has_4_digits), false);
        add(r"\b\d(?:[ -]?\d){12,18}\b".into(), Account, 0, 0.95, Some(luhn), false);
        add(format!(r"(?i)\b(?:driver'?s?\s*licen[sc]e|d\.?l\.?\s*(?:number|no\.?|#)|licen[sc]e\s*(?:number|no\.?|#)|dea(?:\s*(?:number|no\.?|#))?|npi(?:\s*(?:number|no\.?|#))?|passport(?:\s*(?:number|no\.?|#))?|certificate\s*(?:number|no\.?|#))\s*[:#]?\s*#?{IDVAL}"), License, 1, 1.0, Some(has_3_digits), false);
        add(r"\b[A-HJ-NPR-Z0-9]{17}\b".into(), Vehicle, 0, 0.95, Some(valid_vin), false);
        add(r"(?i)\bvin\s*[:#]?\s*([A-HJ-NPR-Z0-9]{17})\b".into(), Vehicle, 1, 1.0, None, false);
        add(r"(?i)\b(?:licen[sc]e plate|plate(?:\s*(?:number|no\.?|#))?|tag\s*(?:number|no\.?|#))\s*[:#]?\s*([A-Z0-9][A-Z0-9 -]{2,8}[A-Z0-9])\b".into(), Vehicle, 1, 0.9, Some(has_digit), false);
        add(format!(r"(?i)\b(?:serial(?:\s*(?:number|no\.?|#))?|s/n|udi|imei|lot(?:\s*(?:number|no\.?|#))?|device\s*id|implant\s*id)\s*[:#]?\s*#?{IDVAL}"), Device, 1, 1.0, Some(has_3_digits), false);

        // --- tax, banking and court identifiers ----------------------------------
        add(r"\b9\d{2}-(?:5\d|6[0-5]|7\d|8[0-8]|9[0-2]|9[4-9])-\d{4}\b".into(), Ssn, 0, 0.95, None, false);            // ITIN
        add(r"\b\d{2}-\d{7}\b".into(), Id, 0, 0.9, None, false);                                                      // EIN
        add(r"\b\d{9}\b".into(), Account, 0, 0.9, Some(valid_aba), false);                                           // ABA routing
        add(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b".into(), Account, 0, 0.9, Some(valid_iban), false);
        add(r"(?i)\b\d{1,2}:\d{2}-(?:cv|cr|mc|md|bk|ap|mj)-\d{3,6}(?:-[A-Z]{2,4})?\b".into(), Id, 0, 0.95, None, false);     // federal docket
        add(r"\b(?:CV|CR|CIV|FAM|PR)-(?:19|20)\d{2}-\d{4,8}\b".into(), Id, 0, 0.95, None, false);
        add(format!(r"(?i)\b(?:docket|case|cause|file|matter|client-matter|bar|employee|ein|tin|itin|claim)\s*(?:id|number|no\.?|#)?\s*[:#]?\s*#?{IDVAL}"), Id, 1, 0.9, Some(has_4_digits), false);

        // --- dictated identifiers -------------------------------------------------
        // Speech-to-text writes numbers as spaced digits ("3 3 0 9 1 7 7 2") or
        // spaced groups ("5512 908 441 XR"), which the compact patterns above skip.
        let spoken = r"(\d{1,4}(?:[ -]\d{1,4}){2,11}(?:[ -](?-i:[A-Z]{1,3})\b)?)";
        add(format!(r"(?i)\b(?:mrn|medical record(?:\s*(?:number|no\.?|#))?|patient\s?id|chart\s*(?:number|no\.?|#)|hospital\s*(?:number|no\.?|#))\s*(?:is|was|of)?\s*[:#]?\s*{spoken}"), Mrn, 1, 0.95, Some(has_4_digits), false);
        add(format!(r"(?i)\b(?:(?:member(?:ship)?|policy|subscriber|group|insurance|beneficiary|medicare|medicaid|plan|health(?:\s*card)?|ohip|nhs)\s*(?:id|number|no\.?|#)|mbi|hicn|hcn|health\s*card)\s*(?:is|was|of)?\s*[:#]?\s*{spoken}"), Plan, 1, 0.95, Some(has_4_digits), false);
        add(format!(r"(?i)\b(?:account|acct\.?|invoice|claim|encounter|accession|case|reference|confirmation|billing|specimen|serial|licen[sc]e|passport)\s*(?:id|number|no\.?|#)\s*(?:is|was|of)?\s*[:#]?\s*{spoken}"), Id, 1, 0.9, Some(has_4_digits), false);
        add(r"(?i)\b(?:social security(?:\s*number)?|ssn)\s*(?:is|was|of)?\s*[:#]?\s*(\d(?:[ -]?\d){8})\b".into(), Ssn, 1, 0.95, None, false);
        // Seven or more single digits read out one at a time, with no label at all.
        add(r"\b\d(?: \d){6,}\b".into(), Id, 0, 0.85, None, false);
        // "the fourteenth of May 1958", "May the fourteenth"
        let ord = r"(?:thirty[- ]first|thirtieth|twenty[- ](?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)|twentieth|nineteenth|eighteenth|seventeenth|sixteenth|fifteenth|fourteenth|thirteenth|twelfth|eleventh|tenth|ninth|eighth|seventh|sixth|fifth|fourth|third|second|first)";
        add(format!(r"(?i:\b(?:the\s+)?{ord}\s+(?:day\s+)?of\s+){MONTH}(?:,?\s+(?:of\s+)?(?:19|20)\d{{2}})?\b"), Date, 0, 0.9, None, false);
        add(format!(r"\b{MONTH}\s+(?i:(?:the\s+)?{ord})(?:,?\s+(?:19|20)\d{{2}})?\b"), Date, 0, 0.9, None, false);
        // "ninety-three years old": an age over 89, spelled out.
        add(r"(?i)\b((?:ninety(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|(?:one |a )?hundred(?: and)?(?: (?:one|two|three|four|five|six|seven|eight|nine|ten))?))[\s-]+(?:years?[\s-]+old|year[\s-]+old|years of age)\b".into(), Age, 1, 0.95, None, false);
        // "j dot akhtar at example dot com"
        add(r"(?i)\b[a-z0-9]+(?: (?:dot|underscore|dash|hyphen) [a-z0-9]+)* at [a-z0-9]+(?: (?:dot|dash|hyphen) [a-z0-9]+)* dot (?:com|org|net|ca|edu|gov|io|co|uk|us|health|info)\b".into(), Email, 0, 0.9, None, false);

        // Any "<Something> ID: value" that the specific rules above did not claim.
        add(format!(r"(?i)\b[a-z]+\s+id\s*[:#]?\s*#?{IDVAL}"), Id, 1, 0.8, Some(has_4_digits), false);

        // --- dates ---------------------------------------------------------------
        let dob = r"(?i)\b(?:dob|d\.o\.b\.?|date of birth|birth\s?date|born(?:\s+on)?)\s*[:\-]?\s*";
        let numeric = r"(?:\d{1,2}[/.-]\d{1,2}[/.-](?:\d{4}|\d{2})|(?:19|20)\d{2}-\d{2}-\d{2})";
        let named = format!(r"(?:{MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+(?:19|20)\d{{2}}|\d{{1,2}}(?:st|nd|rd|th)?[\s-]+{MONTH}\.?,?[\s-]+(?:19|20)\d{{2}})");
        add(format!(r"{dob}({numeric}|{named})"), Date, 1, 1.0, None, true);
        add(r"\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?".into(), Date, 0, 1.0, None, false);
        add(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:(?:19|20)\d{2}|\d{2})\b".into(), Date, 0, 1.0, None, false);
        add(r"\b(?:1[3-9]|2\d|3[01])[/.-](?:0?[1-9]|1[0-2])[/.-](?:(?:19|20)\d{2}|\d{2})\b".into(), Date, 0, 0.95, None, false);
        add(r"\b(?:0?[1-9]|[12]\d|3[01])\.(?:0?[1-9]|1[0-2])\.(?:19|20)\d{2}\b".into(), Date, 0, 0.95, None, false);
        add(format!(r"\b(?:(?:Mon|Tue|Tues|Wed|Thu|Thur|Thurs|Fri|Sat|Sun)[a-z]*\.?,?\s+)?{MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+(?:19|20)\d{{2}})?\b"), Date, 0, 0.95, None, false);
        add(format!(r"\b\d{{1,2}}(?:st|nd|rd|th)?[\s-]+{MONTH}\.?(?:,?[\s-]+(?:(?:19|20)\d{{2}}|\d{{2}}))?\b"), Date, 0, 0.95, None, false);
        // "March 2024": the month is an identifier, the year is not.
        add(format!(r"\b{MONTH}\.?,?\s+(?:of\s+)?(?:19|20)\d{{2}}\b"), Date, 0, 0.9, None, false);
        // Bare mm/dd only with a date cue: "4/5 strength" must survive.
        add(r"(?i)\b(?:on|since|until|from|dated?|dos|admitted|discharged|seen|scheduled(?:\s+for)?|follow[- ]?up|f/u|appointment|appt\.?|surgery|due)\s*:?\s+((?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01]))\b".into(), Date, 1, 0.7, None, false);

        add(r"\b((?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01]))\s+(?:appointment|appt|visit|admission|surgery|clinic|encounter|procedure)\b".into(), Date, 1, 0.7, None, false);
        add(format!(r"(?i:\b(?:last|this|next|in|since|until|early|late|mid|by|of)[\s-]+)({MONTH})\b"), Date, 1, 0.7, None, false);

        // --- age over 89 --------------------------------------------------------
        add(r"(?i)\b(\d{2,3})[\s-]*(?:y/?o|yrs?\.?(?:[\s-]*old)?|years?(?:[\s-]*old|[\s-]+of[\s-]+age)|year[\s-]*old)\b".into(), Age, 1, 1.0, Some(age_over_89), false);
        add(r"(?i)\b(?:age[d]?\s*(?:of|is|:)?|turned|turning)\s*(\d{2,3})\b".into(), Age, 1, 1.0, Some(age_over_89), false);

        // --- geography ------------------------------------------------------------
        add(format!(r"\b\d{{1,6}}[A-Za-z]?\s+(?:(?:N|S|E|W|NE|NW|SE|SW|North|South|East|West)\.?\s+)?(?:(?:[A-Z][A-Za-z'’]+|\d{{1,3}}(?:st|nd|rd|th))\.?\s+){{1,4}}{STREET}\b\.?(?:,?\s+(?i:apt|apartment|suite|ste|unit|rm|room|bldg|floor|fl|#)\.?\s*#?[A-Za-z0-9-]+)?"), Address, 0, 0.95, None, false);
        add(r"(?i)\bP\.?\s?O\.?\s+Box\s+\d+\b".into(), Address, 0, 1.0, None, false);
        add(format!(r"\b{STATE}\.?,?\s+(\d{{5}}(?:-\d{{4}})?)\b"), Zip, 1, 0.95, None, false);
        add(r"(?i)\b(?:zip|postal)(?:\s*code)?\s*[:#]?\s*(\d{5}(?:-\d{4})?)\b".into(), Zip, 1, 1.0, None, false);
        add(format!(r"\b([A-Z][a-z]+(?:[ -][A-Z][a-z]+){{0,2}}),\s+{STATE}\.?,?\s+\d{{5}}\b"), Location, 1, 0.9, None, false);
        // Canadian postal code.
        add(r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z][ -]?\d[ABCEGHJ-NPRSTV-Z]\d\b".into(), Zip, 0, 0.95, None, false);

        // --- names (heuristic; the model does the heavy lifting) -----------------
        let full = format!(r"(?:[A-Z]\.\s+)?(?:{PART}\s+){{0,2}}{NTOK}(?:\s+[A-Z]\.)?(?:\s+(?:{PART}\s+){{0,2}}{NTOK}){{0,2}}");
        add(format!(r"\b(?:Dr|Mr|Mrs|Ms|Miss|Mx|Prof|Sr|Sra|Nurse|Doctor|Officer|Constable|Detective|Pharmacist|Rev|Fr|Judge|Sgt|Capt)\.?\s+({full})"), Name, 1, 0.9, None, false);
        // Registration-style "LAST, FIRST" followed by demographics.
        add(r"\b([A-Z]{2,}(?:[-'][A-Z]+)?,\s+[A-Z]{2,}(?:\s+[A-Z]\.?)?)\s+(?:\d{1,3}\s*(?:y/?o|yrs?)|DOB|MRN|\(|[MF]\b)".into(), Name, 1, 0.9, None, false);
        add(r"\b(?:Patient|Pt|Client|Resident)\s+([A-Z]{2,}(?:[-'][A-Z]+)?,\s+[A-Z]{2,}(?:\s+[A-Z]\.?)?)".into(), Name, 1, 0.9, None, false);
        // Bare "SURNAME, GIVEN" pairs. Registrars, schedulers and EHR headers
        // print names in all caps ("MUELLER, GLORIA", "VAN DER BERG, ANNA"),
        // so that shape alone is evidence; the check filters clinical lists.
        add(format!(r"\b({CTOK}(?:\s+{CTOK}){{0,2}},\s*{CTOK}(?:\s+[A-Z]\b\.?)?)"), Name, 1, 0.9, Some(name_pair), false);
        // Mixed case "Mueller, Gloria" only when a header-style cue precedes it
        // ("From:", "Attn:", "cc:") or demographics follow on the same line
        // ("Mueller, Gloria DOB", "…, 62 y/o").
        let pair = format!(r"(?:{CTOK}(?:\s+{CTOK}){{0,2}}|{full}),\s*{NTOK}(?:\s+[A-Z]\b\.?)?");
        add(format!(r"(?i:\b(?:from|to|sent|attn|attention|cc|bcc|copied|fwd?|fw|forwarded|between)\s*[:–—-]\s*|\b(?:care\s+of|c/o|attention\s+of|addressed\s+to|delivered\s+to|copied\s+to|sent\s+to|forwarded\s+to|between)\s+)\s*(?:(?:Dr|Mr|Mrs|Ms|Miss|Mx|Prof)\.?\s+)?({pair})"), Name, 1, 0.8, Some(name_pair), false);
        add(format!(r"\b({pair})\s+\(?(?:(?:19|20)\d{{2}}|\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}|(?i:d\.?o\.?b\.?|mrn|m\.?r\.?#|chart|med\.?\s?rec\.?|age|male|female|born)\b|\d{{1,3}}\s*(?:y/?o|yrs?\.?)\b)"), Name, 1, 0.8, Some(name_pair), false);
        add(format!(r"(?i:\b(?:patient(?:\s+name)?|pt|name|client|resident|attending|provider|physician|surgeon|referring(?:\s+(?:physician|provider|md))?|pcp|emergency\s+contact|next\s+of\s+kin|nok|guardian|spouse|mother|father|daughter|son|wife|husband|partner|signed(?:\s+by)?|dictated\s+by|reviewed\s+by|seen\s+by|ordered\s+by|cc|author|re|assistant|an(?:a)?esthesiologist|an(?:a)?esthetist|proband|interpreter|social\s+worker|contact|caller|informant|witness))\s*:\s*(?:(?:Dr|Mr|Mrs|Ms|Miss|Mx|Prof)\.?\s+)?((?:{NTOK},\s*)?{full})"), Name, 1, 0.85, Some(name_or_pair), false);
        add(format!(r"\b({NTOK}(?:\s+[A-Z]\.)?\s+{NTOK}),?\s+(?:M\.?D\.?|D\.?O\.?|R\.?N\.?|N\.?P\.?|PA-C|Ph\.?D\.?|DDS|DPM|PharmD|LCSW|CRNA|FNP|APRN|MBBS|FRCPC)\b"), Name, 1, 0.9, None, false);
        add(format!(r"(?i:\b(?:daughter|son|wife|husband|mother|father|brother|sister|spouse|partner|friend|neighbou?r|caregiver|niece|nephew|aunt|uncle|grand(?:mother|father|son|daughter)|roommate|boyfriend|girlfriend|fianc[ée]e?)),?\s+({NTOK}(?:\s+{NTOK})?)"), Name, 1, 0.8, None, false);
        add(r"\b([A-Z][a-z]+(?:[ -][A-Z][a-z]+){0,2}),\s+(?:ON|QC|BC|AB|MB|SK|NS|NB|NL|PE|YT|NT|NU)\.?,?\s+[A-Z]\d[A-Z][ -]?\d[A-Z]\d\b".into(), Location, 1, 0.9, None, false);
        v
    })
}
/// Clinical headers, symptoms, anatomy, drugs, credentials, units, dictation
/// words and generic English/technical terms that appear in "X, Y" pairs but
/// are never names ("HISTORY, PHYSICAL", "ASPIRIN, METOPROLOL", "GET, POST").
/// Applied to either side of a "LAST, FIRST" pair.
const CLIN_STOP: &[&str] = &[
    // headers, roles and chart vocabulary
    "history", "physical", "assessment", "plan", "exam", "examination", "impression",
    "diagnosis", "diagnoses", "procedure", "procedures", "review", "systems",
    "summary", "subjective", "objective", "soap", "progress", "consult", "consultation",
    "referral", "discharge", "admission", "intake", "triage", "rounds", "findings",
    "vitals", "signs", "instructions", "orders", "recommendations", "discussion",
    "medication", "medications", "meds", "allergies", "immunizations", "vaccines",
    "labs", "laboratory", "radiology", "pathology", "cardiology", "pulmonology",
    "oncology", "neurology", "ophthalmology", "otolaryngology", "dermatology",
    "gastroenterology", "endocrinology", "rheumatology", "psychiatry", "psychology",
    "pediatrics", "geriatrics", "orthopedics", "orthopaedics", "urology", "nephrology",
    "hematology", "gynecology", "obstetrics", "anesthesia", "anaesthesia", "surgery",
    "surgical", "medical", "dental", "therapy", "therapies", "rehab", "rehabilitation",
    "pharmacy", "nursing", "care", "services", "home", "hospice", "palliative",
    "emergency", "urgent", "trauma", "icu", "ccu", "picu", "nicu", "pacu", "er",
    "ed", "or", "pt", "ot", "rt", "sla", "dietary", "nutrition", "social",
    "past", "family", "social", "current", "obstetric", "gynecologic", "hospital",
    "patient", "patients", "client", "clients", "resident", "provider", "providers",
    "physician", "physicians", "clinician", "clinicians", "nurse", "nurses",
    "practitioner", "surgeon", "doctor", "attending", "resident", "intern", "fellow",
    "consultant", "specialist", "pharmacist", "therapist", "technician", "assistant",
    "aide", "coordinator", "manager", "director", "supervisor", "administrator",
    "receptionist", "interpreter", "translator", "scribe", "coder", "biller",
    "chaperone", "escort", "driver", "caregiver", "guardian", "parent", "child",
    "adult", "infant", "newborn", "neonate", "spouse", "partner", "sibling",
    "brother", "sister", "relative", "friend", "witness", "informant", "caller",
    "contact", "author", "sender", "receiver", "recipient", "enclosure", "attachment",
    "attachments", "exhibit", "exhibits", "appendix", "appendices", "addendum",
    "subject", "re", "cc", "bcc", "ps", "pps", "note", "notes", "memo", "memorandum",
    "letter", "report", "form", "forms", "record", "records", "chart", "charts",
    "file", "files", "document", "documentation", "information", "details", "data",
    "management", "administration", "registration", "scheduling", "billing",
    "coding", "claims", "insurance", "authorization", "referrals", "appointments",
    "answer", "question", "comment", "comments", "introduction", "background",
    "methods", "results", "conclusion", "conclusions", "references", "scope",
    "purpose", "overview", "objectives", "goals", "outcomes", "followup", "follow",
    // symptoms, signs and descriptors
    "pain", "ache", "aches", "nausea", "vomiting", "emesis", "diarrhea", "diarrhoea",
    "constipation", "cough", "fever", "chills", "sweats", "rigors", "fatigue",
    "malaise", "weakness", "dizziness", "vertigo", "headache", "migraine", "syncope",
    "presyncope", "seizure", "seizures", "tremor", "rash", "pruritus", "itching",
    "hives", "urticaria", "lesion", "lesions", "wound", "swelling", "edema",
    "erythema", "redness", "bruising", "ecchymosis", "hematoma", "bleeding",
    "hemorrhage", "discharge", "drainage", "congestion", "rhinorrhea", "sneezing",
    "wheezing", "stridor", "dyspnea", "dyspnoea", "orthopnea", "apnea", "apnoea",
    "snoring", "insomnia", "somnolence", "lethargy", "anxiety", "depression",
    "confusion", "agitation", "delirium", "hallucinations", "suicidal", "homicidal",
    "sob", "doe", "cp", "soa", "palpitations", "tachycardia", "bradycardia",
    "arrhythmia", "hypertension", "hypotension", "hypoxia", "hypoxemia", "cyanosis",
    "jaundice", "icterus", "pallor", "flushing", "anemia", "infection", "sepsis",
    "inflammation", "abscess", "cellulitis", "phlegm", "sputum", "mucus", "pus",
    "vomit", "stool", "stools", "urine", "hematuria", "dysuria", "polyuria",
    "oliguria", "anuria", "incontinence", "retention", "urgency", "frequency",
    "hesitancy", "nocturia", "anorexia", "cachexia", "obesity", "overweight",
    "underweight", "dehydration", "malnutrition", "ascites", "edema", "anorexia",
    "nausea", "emesis", "heartburn", "reflux", "bloating", "cramping", "flatulence",
    "belching", "hiccups", "dysphagia", "odynophagia", "dyspepsia", "indigestion",
    "melena", "hematochezia", "hematemesis", "tenesmus", "pruritus", "erythema",
    // anatomy
    "head", "neck", "throat", "ear", "ears", "eye", "eyes", "nose", "mouth",
    "lip", "lips", "tongue", "tooth", "teeth", "gums", "jaw", "chin", "cheek",
    "face", "scalp", "skull", "brain", "spine", "back", "shoulder", "shoulders",
    "arm", "arms", "elbow", "elbows", "forearm", "wrist", "wrists", "hand",
    "hands", "finger", "fingers", "thumb", "thumbs", "chest", "breast", "breasts",
    "rib", "ribs", "abdomen", "stomach", "belly", "groin", "hip", "hips",
    "pelvis", "buttock", "buttocks", "thigh", "thighs", "leg", "legs", "knee",
    "knees", "calf", "calves", "ankle", "ankles", "foot", "feet", "toe", "toes",
    "heel", "skin", "hair", "nail", "nails", "heart", "lung", "lungs", "liver",
    "spleen", "kidney", "kidneys", "bladder", "bowel", "colon", "rectum", "anus",
    "vagina", "penis", "scrotum", "testicle", "testicles", "ovary", "ovaries",
    "uterus", "cervix", "prostate", "thyroid", "gallbladder", "pancreas",
    "esophagus", "trachea", "larynx", "pharynx", "tonsil", "tonsils", "adenoids",
    "appendix", "artery", "arteries", "vein", "veins", "nerve", "nerves",
    "muscle", "muscles", "tendon", "tendons", "ligament", "cartilage", "bone",
    "bones", "joint", "joints", "disc", "vertebra", "sternum", "clavicle",
    "scapula", "femur", "tibia", "fibula", "radius", "ulna", "humerus", "sacrum",
    "coccyx", "mandible", "maxilla", "sinus", "sinuses", "bronchus", "aorta",
    "ventricle", "atrium", "retina", "cornea", "iris", "pupil", "eardrum",
    // common drug names (generics and OTC brands)
    "aspirin", "acetaminophen", "paracetamol", "tylenol", "ibuprofen", "advil",
    "motrin", "naproxen", "aleve", "celebrex", "meloxicam", "diclofenac",
    "prednisone", "prednisolone", "methylprednisolone", "dexamethasone",
    "hydrocortisone", "lisinopril", "enalapril", "ramipril", "losartan",
    "valsartan", "irbesartan", "olmesartan", "amlodipine", "nifedipine",
    "diltiazem", "verapamil", "metoprolol", "atenolol", "carvedilol", "propranolol",
    "labetalol", "bisoprolol", "nebivolol", "hydrochlorothiazide", "hctz",
    "chlorthalidone", "furosemide", "lasix", "bumetanide", "spironolactone",
    "atorvastatin", "lipitor", "simvastatin", "zocor", "rosuvastatin", "crestor",
    "pravastatin", "ezetimibe", "fenofibrate", "gemfibrozil", "niacin",
    "metformin", "glucophage", "glipizide", "glyburide", "glimepiride",
    "sitagliptin", "januvia", "empagliflozin", "jardiance", "dapagliflozin",
    "farxiga", "liraglutide", "victoza", "semaglutide", "ozempic", "rybelsus",
    "insulin", "lantus", "humalog", "novolog", "levothyroxine", "synthroid",
    "amoxicillin", "amoxil", "augmentin", "penicillin", "cephalexin", "keflex",
    "azithromycin", "zithromax", "zpack", "ciprofloxacin", "cipro",
    "levofloxacin", "doxycycline", "clindamycin", "metronidazole", "flagyl",
    "nitrofurantoin", "macrobid", "bactrim", "septra", "vancomycin", "omeprazole",
    "prilosec", "esomeprazole", "nexium", "pantoprazole", "protonix",
    "lansoprazole", "famotidine", "pepcid", "ranitidine", "zantac", "sucralfate",
    "ondansetron", "zofran", "promethazine", "phenergan", "meclizine",
    "metoclopramide", "reglan", "sertraline", "zoloft", "fluoxetine", "prozac",
    "escitalopram", "lexapro", "citalopram", "celexa", "paroxetine", "paxil",
    "venlafaxine", "effexor", "duloxetine", "cymbalta", "bupropion", "wellbutrin",
    "trazodone", "mirtazapine", "buspirone", "lorazepam", "ativan", "alprazolam",
    "xanax", "clonazepam", "klonopin", "diazepam", "valium", "zolpidem",
    "ambien", "quetiapine", "seroquel", "olanzapine", "zyprexa", "risperidone",
    "risperdal", "aripiprazole", "abilify", "lamotrigine", "lamictal",
    "levetiracetam", "keppra", "gabapentin", "neurontin", "pregabalin", "lyrica",
    "topiramate", "topamax", "valproate", "depakote", "carbamazepine", "tegretol",
    "phenytoin", "dilantin", "tramadol", "ultram", "oxycodone", "oxycontin",
    "percocet", "hydrocodone", "norco", "vicodin", "morphine", "codeine",
    "fentanyl", "hydromorphone", "dilaudid", "methadone", "buprenorphine",
    "cyclobenzaprine", "flexeril", "methocarbamol", "robaxin", "tizanidine",
    "baclofen", "albuterol", "ventolin", "proair", "fluticasone", "flonase",
    "salmeterol", "tiotropium", "spiriva", "budesonide", "montelukast",
    "singulair", "loratadine", "claritin", "cetirizine", "zyrtec",
    "diphenhydramine", "benadryl", "fexofenadine", "allegra", "warfarin",
    "coumadin", "apixaban", "eliquis", "rivaroxaban", "xarelto", "dabigatran",
    "pradaxa", "clopidogrel", "plavix", "prasugrel", "ticagrelor", "heparin",
    "enoxaparin", "lovenox", "digoxin", "amiodarone", "isosorbide",
    "nitroglycerin", "hydralazine", "clonidine", "doxazosin", "terazosin",
    "finasteride", "proscar", "tamsulosin", "flomax", "sildenafil", "viagra",
    "tadalafil", "cialis", "allopurinol", "colchicine", "febuxostat",
    "methotrexate", "hydroxychloroquine", "plaquenil", "folic", "folate",
    "cyanocobalamin", "ferrous", "calcium", "magnesium", "potassium", "vitamin",
    "zinc", "aspirine", "insulins", "levodopa", "donepezil", "memantine",
    // abbreviations, credentials, units, verbs of dictation
    "bp", "hr", "rr", "spo2", "o2", "ekg", "ecg", "eeg", "emg", "ehr", "emr",
    "ct", "mri", "xray", "cxr", "cbc", "bmp", "cmp", "tsh", "psa", "inr", "a1c",
    "hba1c", "esr", "crp", "bnp", "bun", "gfr", "egfr", "ldl", "hdl", "alt",
    "ast", "alp", "wbc", "rbc", "hgb", "hct", "plt", "mcv", "rdw", "k", "na",
    "cl", "co2", "ca", "mg", "ph", "pco2", "po2", "hco3", "fio2", "peep", "pap",
    "hpi", "pmh", "psh", "fh", "sh", "nkda", "nka", "stat", "prn", "bid", "tid",
    "qid", "qhs", "qam", "qpm", "po", "iv", "im", "sq", "subq", "sl", "gt",
    "ng", "og", "pr", "od", "os", "ou", "ad", "as", "au", "ac", "pc", "hs",
    "qhs", "mg", "mcg", "ml", "cc", "g", "kg", "lb", "oz", "cm", "mm", "m",
    "cm", "mmhg", "bpm", "l", "dl", "iu", "meq", "mmol", "units", "tab", "tabs",
    "cap", "caps", "drop", "drops", "puff", "puffs", "spray", "patch", "cream",
    "ointment", "gel", "lotion", "suspension", "tablet", "tablets", "capsule",
    "capsules", "dose", "doses", "daily", "weekly", "monthly", "hourly", "am",
    "pm", "am.", "pm.", "qday", "qd", "bid.", "reviewed", "discussed",
    "assessed", "evaluated", "examined", "treated", "prescribed", "ordered",
    "performed", "obtained", "administered", "monitored", "documented", "noted",
    "observed", "reported", "denies", "endorses", "complains", "presents",
    "returns", "tolerated", "admitted", "discharged", "transferred", "referred",
    "scheduled", "rescheduled", "cancelled", "completed", "pending", "stable",
    "unstable", "improved", "improving", "worsening", "unchanged", "resolved",
    "negative", "positive", "normal", "abnormal", "unremarkable", "remarkable",
    "benign", "malignant", "acute", "chronic", "mild", "moderate", "severe",
    "left", "right", "bilateral", "unilateral", "upper", "lower", "anterior",
    "posterior", "medial", "lateral", "proximal", "distal", "superior",
    "inferior", "dorsal", "ventral", "internal", "external", "primary",
    "secondary", "tertiary", "initial", "follow", "final", "preliminary",
    "provisional", "definitive", "presumptive", "differential", "rule",
    "out", "versus", "vs", "et", "al", "etc", "ie", "eg", "na", "n/a", "nka",
    "unk", "unknown", "none", "nil", "no.", "pt.", "pts", "yo", "y/o", "yr",
    "yrs", "wk", "wks", "mo", "mos", "hr", "hrs", "min", "mins", "sec", "secs",
    "born", "died", "deceased", "expired", "alive", "living", "single",
    "married", "divorced", "widowed", "separated", "employed", "unemployed",
    "retired", "student", "insured", "uninsured", "smoker", "nonsmoker",
    "former", "occasional", "social", "denies", "quit", "pack", "packs", "year",
    "years", "week", "weeks", "month", "months", "day", "days", "ago", "since",
    "until", "per", "via", "with", "without", "due", "owing", "related",
    "secondary", "complaining", "complains", "presents", "presented", "states",
    "reports", "claims", "describes", "endorses", "denies", "admits", "requests",
    "refuses", "declines", "consents", "agrees", "understands", "acknowledges",
    // common english words seen in caps and discourse markers
    "the", "and", "or", "but", "for", "nor", "yet", "so", "if", "then", "than",
    "that", "this", "these", "those", "there", "here", "where", "when", "what",
    "which", "who", "whom", "whose", "why", "how", "all", "any", "both", "each",
    "every", "either", "neither", "other", "another", "such", "same",
    "different", "various", "several", "few", "many", "more", "most", "less",
    "least", "much", "some", "none", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
    "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
    "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty",
    "ninety", "hundred", "thousand", "million", "billion", "dozen", "first",
    "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth",
    "tenth", "once", "twice", "thrice", "again", "also", "too", "very", "just",
    "only", "even", "still", "already", "always", "never", "often", "sometimes",
    "usually", "rarely", "hardly", "almost", "nearly", "quite", "rather",
    "fairly", "pretty", "really", "truly", "indeed", "perhaps", "maybe",
    "possibly", "probably", "certainly", "definitely", "absolutely", "sure",
    "surely", "yes", "okay", "ok", "please", "thanks", "thank", "sorry",
    "excuse", "pardon", "hello", "hi", "dear", "sincerely", "regards",
    "respectfully", "cordially", "truly", "faithfully", "yours", "mine",
    "ours", "hers", "his", "theirs", "its", "our", "your", "their", "my",
    "me", "him", "us", "them", "i", "we", "you", "he", "she", "it", "they",
    "whoever", "whomever", "everyone", "everybody", "someone", "somebody",
    "anyone", "anybody", "nobody", "everyone", "everything", "something",
    "anything", "nothing", "new", "old", "good", "bad", "best", "worst",
    "better", "worse", "high", "low", "big", "small", "large", "little",
    "long", "short", "early", "late", "next", "last", "previous", "following",
    "above", "below", "under", "over", "between", "among", "within", "through",
    "throughout", "during", "before", "after", "around", "about", "against",
    "upon", "toward", "towards", "onto", "into", "unto", "beside", "besides",
    "beneath", "underneath", "except", "excluding", "including", "regarding",
    "concerning", "respecting", "pursuant", "notwithstanding", "hereinafter",
    "hereby", "herein", "thereof", "therein", "therefore", "however",
    "whereas", "whereby", "wherein", "furthermore", "moreover", "nevertheless",
    "nonetheless", "otherwise", "accordingly", "consequently", "hence", "thus",
    "thereby", "meanwhile", "otherwise", "likewise", "similarly", "conversely",
    "instead", "alternatively", "additionally", "further", "besides", "also",
    "plus", "minus", "times", "divided", "equals", "total", "subtotal", "sum",
    "balance", "remainder", "amount", "quantity", "number", "figure", "figures",
    "table", "tables", "section", "sections", "chapter", "chapters", "part",
    "parts", "item", "items", "line", "lines", "page", "pages", "paragraph",
    "paragraphs", "sentence", "sentences", "word", "words", "letter", "letters",
    "number", "numbers", "code", "codes", "value", "values", "result", "results",
    "finding", "findings", "level", "levels", "rate", "rates", "ratio",
    "count", "counts", "total", "average", "median", "range", "score",
    "scores", "grade", "stage", "class", "type", "category", "group", "kind",
    "sort", "variety", "version", "model", "series", "batch", "lot", "set",
    "list", "row", "column", "cell", "index", "key", "keys", "entry", "entries",
    "option", "options", "choice", "choices", "field", "fields", "parameter",
    "parameters", "variable", "variables", "constant", "input", "output",
    "response", "request", "reply", "message", "messages", "signal", "sign",
    "token", "id", "ids", "no", "nos", "num", "ref", "refs", "ver", "rev",
    "vol", "pg", "pp", "fig", "tbl", "eq", "sec", "para", "appx", "ch", "ed",
    // tech / business / legal vocabulary (non-clinical corpora)
    "api", "ascii", "binary", "byte", "cache", "compiler", "css", "csv",
    "database", "debug", "dns", "ftp", "html", "http", "https", "imap", "json",
    "jpeg", "jpg", "gif", "png", "bmp", "tiff", "svg", "pdf", "doc", "docx",
    "xls", "xlsx", "ppt", "pptx", "txt", "rtf", "odt", "zip", "tar", "gz",
    "exe", "dll", "app", "lan", "wan", "wifi", "vpn", "vlan", "tcp", "udp",
    "tls", "ssl", "ssh", "smtp", "pop", "sql", "mysql", "regex", "router",
    "sdk", "uri", "url", "usb", "utf", "xml", "yaml", "json", "get", "post",
    "put", "delete", "patch", "head", "options", "trace", "connect", "login",
    "logout", "null", "void", "true", "false", "client", "server", "proxy",
    "gateway", "host", "hosts", "node", "nodes", "cluster", "queue", "stack",
    "heap", "array", "string", "integer", "float", "boolean", "enum", "struct",
    "union", "typedef", "sizeof", "return", "break", "continue", "switch",
    "case", "default", "else", "while", "do", "for", "goto", "sizeof",
    "static", "const", "extern", "inline", "virtual", "public", "private",
    "protected", "class", "interface", "extends", "implements", "import",
    "package", "module", "namespace", "using", "include", "define", "undef",
    "ifdef", "ifndef", "endif", "pragma", "template", "typename", "new",
    "delete", "this", "self", "super", "try", "catch", "throw", "throws",
    "finally", "assert", "sizeof", "alignof", "decltype", "auto", "register",
    "volatile", "mutable", "explicit", "friend", "operator", "sizeof",
    "agreement", "contract", "lease", "warranty", "liability", "indemnity",
    "party", "parties", "landlord", "tenant", "buyer", "seller", "vendor",
    "vendee", "lessor", "lessee", "grantor", "grantee", "licensor", "licensee",
    "mortgagor", "mortgagee", "obligor", "obligee", "guarantor", "principal",
    "agent", "assignor", "assignee", "successor", "predecessor", "affiliate",
    "subsidiary", "parent", "holding", "shareholder", "stockholder",
    "director", "officer", "trustee", "beneficiary", "executor", "executrix",
    "administrator", "guardian", "conservator", "ward", "plaintiff",
    "defendant", "petitioner", "respondent", "appellant", "appellee",
    "claimant", "decadent", "deponent", "witness", "affiant", "notary",
    "attorney", "counsel", "counselor", "barrister", "solicitor", "advocate",
    "judge", "justice", "magistrate", "clerk", "bailiff", "marshal",
    "sheriff", "constable", "commissioner", "arbitrator", "mediator",
    "invoice", "invoices", "receipt", "receipts", "payment", "payments",
    "deposit", "deposits", "withdrawal", "transfer", "refund", "refunds",
    "credit", "debit", "charge", "charges", "fee", "fees", "tax", "taxes",
    "tariff", "duty", "customs", "fine", "fines", "penalty", "penalties",
    "interest", "principal", "balance", "overdraft", "statement", "statements",
    "ledger", "journal", "voucher", "memo", "audit", "accounting",
    "bookkeeping", "payroll", "salary", "wage", "wages", "bonus", "commission",
    "dividend", "royalty", "pension", "annuity", "benefit", "benefits",
    "premium", "premiums", "deductible", "copay", "coinsurance", "coverage",
    "policy", "policies", "claim", "claims", "underwriting", "actuary",
    "law", "laws", "statute", "statutes", "regulation", "regulations",
    "ordinance", "ordinances", "axis", "axes",
    // acronyms / certification / legal-jurat pairs ("LEED, BREEAM", "SUBSCRIBED, SWORN")
    "leed", "breeam", "sep", "simple", "ira", "roth", "hsa", "fsa", "ein",
    "llc", "llp", "inc", "corp", "ltd", "plc", "gmbh", "pty", "cpa", "cfa",
    "ctr", "cpc", "cpt", "hcpcs", "roi", "npv", "irr", "ebitda", "seo",
    "ppc", "sem", "far", "frr", "tpr", "fpr", "fnr", "tnr", "auc", "rmse",
    "mae", "mape", "r2", "sworn", "subscribed", "affirmed", "seal", "jurat",
    "sic", "tbd", "tba", "eta", "etd", "est", "edt", "cst", "cdt", "mst",
    "mdt", "pst", "pdt", "gmt", "utc", "fbi", "cia", "nsa", "faa", "fcc",
    "fda", "nih", "cdc", "cms", "irs", "epa", "osha", "hipaa", "hitech",
    "ada", "dea", "doj", "dod", "va", "usps", "ups", "fedex", "sec", "ftc",
    "gsa", "ssa", "dmv", "dhs", "fema", "nato", "usa", "un", "eu", "uk",
    "us", "uk", "fed",
    // temporal and structural
    "schedule", "scheduled", "appointment", "appointments", "meeting",
    "meetings", "conference", "call", "calls", "session", "sessions", "shift",
    "shifts", "weekend", "weekends", "weekday", "weekdays", "holiday",
    "holidays", "vacation", "leave", "sick", "absence", "absent", "present",
    "tardy", "overtime", "undertime", "break", "lunch", "dinner", "breakfast",
    "morning", "afternoon", "evening", "night", "noon", "midnight", "dawn",
    "dusk", "sunrise", "sunset", "today", "tomorrow", "yesterday", "tonight",
    "now", "then", "soon", "later", "earlier", "immediately", "promptly",
    "urgently", "stat", "asap", "imminent", "forthcoming", "upcoming",
    "pending", "overdue", "current", "prior", "previous", "subsequent",
    "following", "preceding", "initial", "final", "last", "first", "next",
    "home", "work", "school", "office", "building", "suite", "floor", "room",
    "unit", "apartment", "house", "residence", "address", "location",
    "facility", "facilities", "site", "sites", "campus", "wing", "floor",
    "level", "basement", "attic", "garage", "parking", "entrance", "exit",
    "lobby", "corridor", "hallway", "elevator", "stairs", "stairwell",
    "bed", "beds", "ward", "wards", "bay", "bays", "station", "counter",
    "desk", "window", "door", "gate", "terminal", "annex", "pavilion",
    "tower", "center", "centre", "institute", "institution", "foundation",
    "association", "organization", "organisation", "agency", "bureau",
    "commission", "committee", "board", "panel", "task", "force", "team",
    "group", "division", "department", "branch", "section", "unit", "office",
    "bureau", "authority", "administration", "government", "federal", "state",
    "county", "city", "municipal", "local", "national", "international",
    "regional", "district", "zone", "area", "sector", "territory", "province",
    "region", "north", "south", "east", "west", "northeast", "northwest",
    "southeast", "southwest", "central", "northern", "southern", "eastern",
    "western", "upper", "lower", "inner", "outer", "greater", "lesser",
    "metro", "metropolitan", "urban", "suburban", "rural", "downtown",
    "uptown", "midtown", "old", "historic", "modern",
    // roman numerals and placeholders
    "ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii", "xiii", "xiv",
    "xv", "xvi", "xvii", "xviii", "xix", "xx", "xxi", "xxv", "xxx", "xl",
    "xlv", "doe", "roe", "bloggs",
    "public", "sample", "example", "test", "testing", "demo",
    "placeholder", "unknown", "anonymous", "confidential", "secret",
    "private", "classified", "restricted", "internal", "draft", "final",
    "approved", "pending", "review", "revision", "supersedes", "obsolete",
    "copy", "copies", "original", "duplicate", "triplicate", "carbon",
    "attachment", "enclosure", "included", "attached", "enclosed", "herein",
    "hereof", "hereunto", "aforesaid", "aforementioned", "hereinafter",
];

/// Right-side words that indicate geography or organisation rather than a
/// given name: "PORTLAND, MAINE", "ACME, INC", "SPRINGFIELD, USA".
const GEO_STOP: &[&str] = &[
    // US states + DC (given names Virginia/Georgia/Carolina kept as names)
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "hawaii", "idaho", "illinois",
    "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland",
    "massachusetts", "michigan", "minnesota", "mississippi", "missouri",
    "montana", "nebraska", "nevada", "hampshire", "jersey", "mexico",
    "ohio", "oklahoma", "oregon", "pennsylvania", "island", "dakota",
    "tennessee", "texas", "utah", "vermont", "washington", "wisconsin",
    "wyoming", "columbia",
    // countries and regions
    "usa", "america", "canada", "ontario", "quebec", "alberta", "columbia",
    "manitoba", "saskatchewan", "scotia", "brunswick", "labrador",
    "newfoundland", "yukon", "nunavut", "england", "scotland", "wales",
    "ireland", "britain", "kingdom", "france", "germany", "italy", "spain",
    "portugal", "greece", "sweden", "norway", "denmark", "finland", "iceland",
    "poland", "austria", "switzerland", "belgium", "netherlands", "holland",
    "luxembourg", "czechia", "slovakia", "hungary", "romania", "bulgaria",
    "ukraine", "russia", "belarus", "estonia", "latvia", "lithuania",
    "slovenia", "croatia", "serbia", "bosnia", "albania", "macedonia",
    "montenegro", "kosovo", "moldova", "turkey", "cyprus", "malta",
    "australia", "zealand", "victoria", "tasmania", "queensland", "canberra",
    "sydney", "melbourne", "brisbane", "perth", "adelaide", "auckland",
    "wellington", "china", "japan", "korea", "india", "pakistan", "bangladesh",
    "indonesia", "malaysia", "singapore", "thailand", "vietnam", "philippines",
    "cambodia", "laos", "myanmar", "nepal", "mongolia", "taiwan", "kong",
    "macau", "brazil", "argentina", "chile", "peru", "colombia", "venezuela",
    "ecuador", "bolivia", "paraguay", "uruguay", "guyana", "suriname",
    "panama", "rica", "honduras", "guatemala", "salvador", "nicaragua",
    "belize", "cuba", "jamaica", "haiti", "dominican", "bahamas", "barbados",
    "trinidad", "tobago", "grenada", "lucia", "vincent", "egypt", "morocco",
    "algeria", "tunisia", "libya", "sudan", "ethiopia", "tanzania",
    "uganda", "rwanda", "ghana", "nigeria", "senegal", "mali", "niger",
    "cameroon", "congo", "angola", "zambia", "zimbabwe", "botswana",
    "namibia", "africa", "mozambique", "madagascar", "mauritius", "lebanon", "syria", "iraq", "iran", "arabia", "emirates",
    "qatar", "kuwait", "bahrain", "oman", "yemen", "afghanistan", "europe",
    "asia", "americas", "americana", "antarctica", "arctic", "atlantic",
    "pacific", "indian", "mediterranean", "caribbean", "scandinavia",
    // corporate suffixes and org words
    "inc", "llc", "llp", "corp", "co", "company", "ltd", "plc", "gmbh",
    "sarl", "pty", "bros", "sons", "associates", "partners", "partnership",
    "corporation", "incorporated", "limited", "enterprises", "holdings",
    "industries", "international", "worldwide", "global", "national",
    "university", "college", "school", "academy", "institute", "consortium",
    "coalition", "alliance", "federation", "union", "guild", "society",
    "association", "club", "church", "parish", "diocese", "ministry",
    "ministries", "temple", "mosque", "synagogue", "cathedral", "chapel",
];

/// Short surname particles allowed inside a multi-token surname.
const PARTICLES: &[&str] = &[
    "de", "del", "dela", "der", "den", "di", "da", "le", "la", "las", "los",
    "van", "von", "bin", "ibn", "al", "el", "st", "san", "santa", "ten",
    "ter", "vander", "vanden", "du", "des", "het", "op", "zu", "zum", "zur",
    "af", "av", "dos", "das", "do",
];

/// Name-suffix words that may follow a given name inside "LAST, FIRST X".
const NAME_SUFFIX: &[&str] = &[
    "jr", "sr", "ii", "iii", "iv", "v", "vi", "md", "do", "rn", "np", "pa",
    "phd", "dmd", "dds", "dpm", "od", "esq", "msw", "lcsw", "lmft", "pt",
    "ot", "dpt", "mba", "mph", "msn", "bsn", "mbbs", "frcpc", "facp", "facs",
    "facog", "faap", "faan", "cna", "lpn", "lvn", "ma", "ms", "ba", "bs",
    "pharmd", "rd", "cdn", "crt", "rrt", "emt", "cma", "cpnp", "fnp",
];

fn is_stop(tok: &str) -> bool {
    CLIN_STOP.contains(&tok) || NAME_STOP.contains(&tok)
}

/// English words that are also common surnames; allowed on the LEFT side of a
/// "LAST, FIRST" pair despite appearing in a stop list ("DAY, RICH"). Kept
/// left-only so pairs like "GOOD, DAY" still fail on the other token.
const LEFT_OK: &[&str] = &[
    "day", "week", "weeks", "key", "keys", "good", "best", "field", "fields",
    "page", "pages", "long", "little", "low", "new", "case", "summer",
    "winter", "dawn", "morning", "noon", "sunrise", "sunset",
];

/// English words that are also common given names; allowed on the RIGHT side
/// ("KING, DAWN", "WHITE, WILL").
const RIGHT_OK: &[&str] = &["will", "summer", "dawn", "morning", "page", "day"];

/// Is this raw token shaped like a name part? Letters plus intra-word
/// apostrophes/hyphens (O'NEIL, AL-SAYED, MUELLER-SMITH).
fn name_shaped(tok: &str) -> bool {
    tok.chars().all(|c| c.is_alphabetic() || c == '-' || c == '\'' || c == '’')
}

/// Validate one side of a "LAST, FIRST" pair. `right` is the given-name side.
fn side_ok(raw_toks: &[&str], right: bool) -> bool {
    let mut toks: Vec<String> = raw_toks.iter()
        .map(|t| t.trim_end_matches('.').to_lowercase())
        .collect();
    if toks.is_empty() { return false; }
    if right {
        // Drop credential/suffix tokens first: "SMITH, JOHN MD" -> "JOHN".
        while toks.len() > 1 && NAME_SUFFIX.contains(&toks.last().unwrap().as_str()) {
            toks.pop();
        }
        // A trailing single capital is a middle initial, not a name token.
        if toks.len() > 1 {
            let last_raw = raw_toks[toks.len() - 1].trim_end_matches('.');
            if last_raw.chars().count() == 1 && last_raw.chars().next().unwrap().is_uppercase() {
                toks.pop();
            }
        }
        if toks.is_empty() || toks.len() > 2 { return false; }
    } else if toks.len() > 4 { return false; }
    for (i, t) in toks.iter().enumerate() {
        let alpha = t.chars().filter(|c| c.is_alphabetic()).count();
        // Particles (van, de, al) are fine anywhere inside a surname.
        if !right && PARTICLES.contains(&t.as_str()) { continue; }
        // One-letter words and most two-letter words can't be names.
        if alpha < 3 { return false; }
        let ok = if right { RIGHT_OK } else { LEFT_OK };
        if is_stop(t) && !ok.contains(&t.as_str()) { return false; }
        if right && GEO_STOP.contains(&t.as_str()) { return false; }
        if !name_shaped(raw_toks[i]) { return false; }
    }
    true
}

/// For the label-colon rule: the captured text is either a plain name
/// (no comma) or a "LAST, FIRST" pair needing the pair check.
fn name_or_pair(v: &str, w: &str) -> bool {
    if v.contains(',') { return name_pair(v, w); }
    // A leading clinical term ("cc: Cardiology") is not a name; trailing
    // stops are left for trim_name.
    match v.split_whitespace().next() {
        Some(t) => name_shaped(t.trim_end_matches('.')) && !is_stop(&t.trim_end_matches('.').to_lowercase()),
        None => false,
    }
}

/// "SURNAME, GIVEN" pair validator: both sides must look like names and
/// neither may be a clinical, geographic or generic English term.
fn name_pair(v: &str, _: &str) -> bool {
    let Some(comma) = v.find(',') else { return false };
    let left: Vec<&str> = v[..comma].split_whitespace().collect();
    let right: Vec<&str> = v[comma + 1..].split_whitespace().collect();
    side_ok(&left, false) && side_ok(&right, true)
}

/// Words that follow a name label but are not part of the name.
const NAME_STOP: &[&str] = &[
    "date", "dob", "age", "sex", "gender", "mrn", "id", "phone", "tel", "fax", "email", "address",
    "male", "female", "is", "was", "has", "had", "will", "who", "the", "and", "with", "on", "at",
    "in", "for", "of", "to", "presents", "presented", "reports", "reported", "denies", "states",
    "md", "do", "rn", "np", "pa", "phd", "room", "bed", "unit", "ward", "dept", "department",
    "admitted", "discharged", "seen", "history", "allergies", "medications", "diagnosis", "visit",
    "chief", "complaint", "hpi", "pmh", "ros", "note", "notes", "none", "unknown", "n/a", "na",
    "yes", "no", "not", "self", "same", "see", "per", "status", "insurance", "ssn", "account",
    "medical", "record", "number", "hospital", "clinic", "center", "centre", "health", "care",
    "dr", "mr", "mrs", "ms", "miss", "mx", "prof", "he", "she", "they", "her", "his", "their",
    "called", "said", "came", "lives", "also", "but", "then", "when", "after", "before",
];

fn trim_name(text: &str, mut start: usize, mut end: usize) -> Option<(usize, usize)> {
    loop {
        let s = &text[start..end];
        let last = s.rsplit(|c: char| c.is_whitespace() || c == ',').next().unwrap_or("");
        if !last.is_empty() && last.len() < s.len() && NAME_STOP.contains(&last.to_ascii_lowercase().trim_matches('.')) {
            end -= last.len();
            end = start + text[start..end].trim_end_matches(|c: char| c.is_whitespace() || c == ',').len();
        } else {
            break;
        }
    }
    let s = &text[start..end];
    let first = s.split(|c: char| c.is_whitespace() || c == ',').next().unwrap_or("");
    if NAME_STOP.contains(&first.to_ascii_lowercase().trim_matches('.')) {
        if first.len() == s.len() { return None; }
        start += first.len();
        start += text[start..end].len() - text[start..end].trim_start_matches(|c: char| c.is_whitespace() || c == ',').len();
        if start >= end { return None; }
    }
    Some((start, end))
}

pub fn detect(text: &str) -> Vec<Span> {
    let mut out = Vec::new();
    for r in rules() {
        let mut at = 0;
        while at <= text.len() {
            let Some(caps) = r.re.captures_at(text, at) else { break };
            let whole = caps.get(0).unwrap();
            // A match that fails validation must not swallow the text after it:
            // resume one character on, not at the end of the rejected match.
            let mut retry = whole.start() + 1;
            while retry < text.len() && !text.is_char_boundary(retry) { retry += 1; }
            let next = whole.end().max(retry);
            let Some(m) = caps.get(r.group) else { at = retry; continue };
            if let Some(chk) = r.check {
                if !chk(m.as_str(), whole.as_str()) { at = retry; continue; }
            }
            let (mut s, mut e) = (m.start(), m.end());
            if r.cat == Category::Name {
                match trim_name(text, s, e) { Some(x) => (s, e) = x, None => { at = retry; continue } }
            }
            let mut span = Span::new(s, e, r.cat, Source::Rule, r.conf);
            span.dob = r.dob;
            out.push(span);
            at = next;
        }
    }
    out
}

/// Things that look like they might be identifiers but matched no rule.
/// Surfaced in review as "possible", never auto-redacted.
pub fn suspicious(text: &str) -> Vec<Span> {
    static R: OnceLock<Vec<Regex>> = OnceLock::new();
    let res = R.get_or_init(|| vec![
        // Long digit runs, or letter+digit codes.
        Regex::new(r"\b\d[\d -]{5,}\d\b").unwrap(),
        Regex::new(r"\b(?:[A-Z]{1,4}-?\d{5,}|\d{3,}[A-Z]{1,3}\d{2,})\b").unwrap(),
    ]);
    let mut out = Vec::new();
    for re in res {
        for m in re.find_iter(text) {
            if digits(m.as_str()) >= 7 || re.as_str().starts_with(r"\b(?:") {
                out.push(Span::new(m.start(), m.end(), Category::Id, Source::Rule, 0.3));
            }
        }
    }
    out
}

/// Common English/clinical words that are also surnames; never propagated.
const COMMON: &[&str] = &[
    "may", "will", "mark", "rose", "grace", "hope", "faith", "joy", "white", "black", "brown",
    "green", "gray", "grey", "young", "long", "short", "little", "small", "best", "good", "bell",
    "graves", "paget", "down", "downs", "marks", "bill", "art", "pat", "sue", "rob", "jack",
    "wells", "burns", "payne", "pain", "strong", "weeks", "day", "days", "love", "price", "rich",
    "banks", "fields", "woods", "stone", "cross", "king", "page", "cook", "hand", "head", "foot",
    "june", "april", "august", "summer", "winter", "north", "south", "east", "west", "christian",
    "frank", "miles", "hunter", "chase", "lane", "hill", "ford", "case", "parks", "moody", "savage",
    "patient", "doctor", "nurse", "the", "and", "for", "von", "van", "del", "der", "los", "las",
];

/// Once "John Smith" is found, "Smith" on line 40 is the same person. Models
/// routinely miss these bare repeats; this pass catches them.
pub fn propagate_names(text: &str, spans: &[Span]) -> Vec<Span> {
    let mut tokens: Vec<String> = Vec::new();
    for s in spans.iter().filter(|s| s.category == Category::Name) {
        for tok in text[s.start..s.end].split(|c: char| !(c.is_alphabetic() || c == '\'' || c == '’' || c == '-')) {
            let t = tok.trim_matches(|c: char| !c.is_alphabetic());
            if t.chars().count() < 3 { continue; }
            let low = t.to_lowercase();
            if COMMON.contains(&low.as_str()) || NAME_STOP.contains(&low.as_str()) { continue; }
            if !tokens.contains(&low) { tokens.push(low); }
        }
    }
    if tokens.is_empty() { return Vec::new(); }
    tokens.sort_by_key(|t| std::cmp::Reverse(t.len()));
    let alt = tokens.iter().map(|t| regex::escape(t)).collect::<Vec<_>>().join("|");
    let Ok(re) = Regex::new(&format!(r"(?i)\b(?:{alt})(?:['’]s)?\b")) else { return Vec::new() };
    let mut out = Vec::new();
    for m in re.find_iter(text) {
        // Only capitalised occurrences: "Rose" the patient, not "rose" the verb.
        if !m.as_str().chars().next().map(|c| c.is_uppercase()).unwrap_or(false) { continue; }
        if spans.iter().any(|s| s.start <= m.start() && m.end() <= s.end) { continue; }
        let mut end = m.end();
        for suf in ["'s", "’s"] {
            if m.as_str().ends_with(suf) { end -= suf.len(); }
        }
        // "Karen Whitfield": a capitalised word glued to a known surname is
        // almost always the rest of a relative's name, unless it opens a sentence.
        let mut start = m.start();
        let before = &text[..start];
        if before.ends_with(' ') {
            let head = before.trim_end_matches(' ');
            let w0 = head.rfind(|c: char| !(c.is_alphabetic() || c == '\'' || c == '-')).map(|i| i + head[i..].chars().next().unwrap().len_utf8()).unwrap_or(0);
            let word = &head[w0..];
            let low = word.to_lowercase();
            let lead = head[..w0].trim_end_matches(' ');
            let sentence_start = lead.is_empty() || lead.ends_with(['.', '!', '?', '\n', ':', ';']);
            let titlecase = word.chars().next().map(|c| c.is_uppercase()).unwrap_or(false) && word.chars().skip(1).all(|c| c.is_lowercase());
            if titlecase && word.len() >= 3 && !sentence_start && before.len() - head.len() == 1
                && !COMMON.contains(&low.as_str()) && !NAME_STOP.contains(&low.as_str())
                && !spans.iter().any(|s| s.start < start && w0 < s.end)
            {
                start = w0;
            }
        }
        out.push(Span::new(start, end, Category::Name, Source::Propagated, 0.8));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn found(text: &str) -> Vec<(Category, String)> {
        let spans = crate::merge::merge(text, detect(text));
        spans.iter().map(|s| (s.category, text[s.start..s.end].to_string())).collect()
    }
    fn has(text: &str, cat: Category, frag: &str) -> bool {
        found(text).iter().any(|(c, s)| *c == cat && s == frag)
    }

    #[test]
    fn structured_identifiers() {
        assert!(has("email j.smith+x@mail.example.org today", Category::Email, "j.smith+x@mail.example.org"));
        assert!(has("call (416) 555-0188 ext 12 tomorrow", Category::Phone, "(416) 555-0188 ext 12"));
        assert!(has("Fax: 416-555-0199", Category::Fax, "416-555-0199"));
        assert!(has("SSN 123-45-6789.", Category::Ssn, "123-45-6789"));
        assert!(has("MRN: 00482913", Category::Mrn, "00482913"));
        assert!(has("Member ID: XJK449201A", Category::Plan, "XJK449201A"));
        assert!(has("see https://portal.example.com/p/123.", Category::Url, "https://portal.example.com/p/123"));
        assert!(has("from 192.168.10.44 at night", Category::Ip, "192.168.10.44"));
        assert!(has("card 4111 1111 1111 1111 on file", Category::Account, "4111 1111 1111 1111"));
        assert!(has("pacemaker S/N: PJK-448291", Category::Device, "PJK-448291"));
        assert!(has("VIN 1HGCM82633A004352", Category::Vehicle, "1HGCM82633A004352"));
        // A rejected match ("health card" + "member") must not hide the real one.
        assert!(has("Health card member ID: 4482-719-330-KT.", Category::Plan, "4482-719-330-KT"));
    }

    #[test]
    fn dictated_identifiers() {
        assert!(has("medical record number 3 3 0 9 1 7 7 2. She was seen", Category::Mrn, "3 3 0 9 1 7 7 2"));
        assert!(has("His health card number is 5512 908 441 XR. MRI on", Category::Plan, "5512 908 441 XR"));
        assert!(has("her number in the system is 4 4 1 0 9 2 7 3 ok", Category::Id, "4 4 1 0 9 2 7 3"));
        assert!(has("reach him at j dot akhtar at example dot com.", Category::Email, "j dot akhtar at example dot com"));
        assert!(has("social security number is 421 55 8830", Category::Ssn, "421 55 8830"));
        assert!(has("date of birth the fourteenth of May 1958, medical", Category::Date, "the fourteenth of May 1958"));
        assert!(has("on October the twenty-second for review", Category::Date, "October the twenty-second"));
        assert!(has("Mr. Castillo, ninety-three years old, admitted", Category::Age, "ninety-three"));
        assert!(has("He lives at 77 Kingston Road, apartment 5.", Category::Address, "77 Kingston Road, apartment 5"));
        assert!(found("the second of two doses, a sixty-three year old").is_empty());
        // Spoken clinical numbers are left alone.
        for t in ["Blood pressure 138 over 84, weight 81 kilos.", "pain is 3 out of 10 and sats 98", "gave 2 5 0 mg then 5 0 0 mg", "seen at clinic dot. come back"] {
            assert!(found(t).is_empty(), "false positive in {t:?}: {:?}", found(t));
        }
    }

    #[test]
    fn tax_and_court_identifiers() {
        assert!(has("ITIN for the spouse is 930-74-1166.", Category::Ssn, "930-74-1166"));
        assert!(has("Tidewater Accounting (49-1957032) issued", Category::Id, "49-1957032"));
        assert!(has("routing 021000021 today", Category::Account, "021000021"));
        assert!(has("drawn on GB61 BARC 8149 9347 6523 73 cleared", Category::Account, "GB61 BARC 8149 9347 6523 73"));
        assert!(has("docket 2:25-cv-74228, hearing", Category::Id, "2:25-cv-74228"));
        assert!(has("Case No. CV-2023-004417", Category::Id, "CV-2023-004417"));
        assert!(has("Bar No. 482913, Okoro", Category::Id, "482913"));
        for t in ["See 42 U.S.C. 1983 and Rule 12(b)(6).", "Form 8829 and Section 1014 apply.", "a total of 123456789 units"] {
            assert!(found(t).is_empty(), "false positive in {t:?}: {:?}", found(t));
        }
    }

    #[test]
    fn dates() {
        for d in ["03/14/2024", "3/4/24", "2024-03-14", "March 14, 2024", "14 Mar 2024", "Mar 14", "14-Mar-2024", "25/12/2023", "March 2024"] {
            let t = format!("Seen {d} in clinic");
            assert!(has(&t, Category::Date, d), "missed {d}: {:?}", found(&t));
        }
        assert!(has("follow-up on 4/12 with ortho", Category::Date, "4/12"));
        let t = "DOB: 02/11/1931";
        let s = detect(t);
        assert!(s.iter().any(|s| s.dob && &t[s.start..s.end] == "02/11/1931"));
    }

    #[test]
    fn clinical_text_survives() {
        for t in [
            "Strength 4/5 in the left leg, pain 7/10.",
            "BP 120/80, HR 72, SpO2 98% on room air.",
            "Metoprolol 25 mg BID, HbA1c 7.2, Na 138, K 4.1.",
            "67 year old with type 2 diabetes mellitus.",
            "May repeat in 3 days if symptoms persist.",
            "ECOG 1. EF 55%. Creatinine 1.02. WBC 11.3.",
            "Lisinopril 10 mg daily; atorvastatin 40 mg qhs.",
        ] {
            assert!(found(t).is_empty(), "false positive in {t:?}: {:?}", found(t));
        }
    }

    #[test]
    fn age_over_89_only() {
        assert!(has("a 94-year-old woman", Category::Age, "94"));
        assert!(has("Age: 91", Category::Age, "91"));
        assert!(found("a 67 y/o man").is_empty());
    }

    #[test]
    fn geography() {
        assert!(has("lives at 42 Wallaby Way, Apt 3B", Category::Address, "42 Wallaby Way, Apt 3B"));
        assert!(has("Springfield, IL 62704", Category::Zip, "62704"));
        assert!(has("Springfield, IL 62704", Category::Location, "Springfield"));
        assert!(has("M5S 1A1", Category::Zip, "M5S 1A1"));
    }

    #[test]
    fn names_and_propagation() {
        let t = "Patient: Maria Gonzalez DOB: 01/02/1960\nDr. O'Brien saw Gonzalez today. Maria's labs are fine.";
        let spans = crate::merge::merge(t, detect(t));
        assert!(spans.iter().any(|s| &t[s.start..s.end] == "Maria Gonzalez"), "{:?}", found(t));
        assert!(spans.iter().any(|s| &t[s.start..s.end] == "O'Brien"));
        let extra = propagate_names(t, &spans);
        let got: Vec<&str> = extra.iter().map(|s| &t[s.start..s.end]).collect();
        assert_eq!(got, vec!["Gonzalez", "Maria"]);
        assert!(has("Reviewed by: Priya Raman, MD", Category::Name, "Priya Raman"));
        assert!(has("Attending: Dr. Samuel Okoye, MD", Category::Name, "Samuel Okoye"));
        assert!(!has("Attending: Dr. Samuel Okoye, MD", Category::Name, "Dr"));
        assert!(has("Her daughter Karen will drive.", Category::Name, "Karen"));
        let t = "Mrs. Whitfield is stable. Spoke with Karen Whitfield today. Whitfield agrees.";
        let spans = crate::merge::merge(t, detect(t));
        let got: Vec<&str> = propagate_names(t, &spans).iter().map(|s| &t[s.start..s.end]).collect();
        assert_eq!(got, vec!["Karen Whitfield", "Whitfield"]);
        assert!(has("Toronto, ON M6H 4B6", Category::Location, "Toronto"));
    }

    #[test]
    fn last_first_all_caps() {
        // Registration/header style "SURNAME, GIVEN" with no other cue.
        for (t, want) in [
            ("MUELLER, GLORIA has reviewed the chart.", "MUELLER, GLORIA"),
            ("From: HOOVER, JORDAN To: Clinic Staff", "HOOVER, JORDAN"),
            ("Please ensure MEDINA, DIANA reviews this.", "MEDINA, DIANA"),
            ("Signed by O'NEIL, PAT today.", "O'NEIL, PAT"),
            ("Consult sent to VAN DER BERG, ANNA.", "VAN DER BERG, ANNA"),
            ("Record for SMITH-ALVAREZ, JUNE.", "SMITH-ALVAREZ, JUNE"),
            ("admitting BALL, ELI for obs.", "BALL, ELI"),
        ] {
            assert!(has(t, Category::Name, want), "missed {want:?} in {t:?}: {:?}", found(t));
        }
        // Once found, bare repeats in any casing get propagated.
        let t = "MUELLER, GLORIA signed. Later Mueller returned. Gloria called back.";
        let spans = crate::merge::merge(t, detect(t));
        let got: Vec<&str> = propagate_names(t, &spans).iter().map(|s| &t[s.start..s.end]).collect();
        assert!(got.contains(&"Mueller"), "{got:?}");
        assert!(got.contains(&"Gloria"), "{got:?}");
    }

    #[test]
    fn last_first_mixed_case_needs_cue() {
        // Strongly cued mixed-case pairs are names.
        assert!(has("From: Mueller, Gloria To: Clinic", Category::Name, "Mueller, Gloria"));
        assert!(has("Attn: Mueller, Gloria", Category::Name, "Mueller, Gloria"));
        assert!(has("cc: O'Neil, Pat", Category::Name, "O'Neil, Pat"));
        assert!(has("cc: Van der Berg, Anna", Category::Name, "Van der Berg, Anna"));
        assert!(has("Contact Mueller, Gloria DOB 03/14/1958", Category::Name, "Mueller, Gloria"));
        // Uncued mixed-case "X, Y" stays untouched.
        for t in [
            "She moved to Mueller, Gloria last year.",
            "Springfield, Illinois is home.",
            "the capital of Austin, Texas",
            "Toronto, ON is north of here.",
        ] {
            assert!(!found(t).iter().any(|(c, _)| *c == Category::Name),
                "uncued mixed pair redacted in {t:?}: {:?}", found(t));
        }
    }

    #[test]
    fn caps_pairs_clinical_negatives() {
        // All-caps headers, symptom lists and drug lists are not names.
        for t in [
            "HISTORY, PHYSICAL EXAM reviewed.",
            "ASSESSMENT, PLAN as follows.",
            "NAUSEA, VOMITING, AND DIARRHEA denied.",
            "CHEST PAIN, DYSPNEA on exertion.",
            "ASPIRIN, METOPROLOL, LISINOPRIL daily.",
            "SUBJECTIVE, OBJECTIVE sections.",
            "HEART, LUNG, AND KIDNEY function.",
            "NOW, THEREFORE, the parties agree.",
            "GET, POST requests logged.",
            "JPEG, PNG files attached.",
            "HEAD, NECK exam normal.",
            "CC: CARDIOLOGY, RADIOLOGY",
            "DENIES FEVER, CHILLS.",
            "PORTLAND, MAINE resident.",
            "SPRINGFIELD, USA office.",
            "ACME, INC was contacted.",
            "STAGE II, III disease.",
        ] {
            assert!(!found(t).iter().any(|(c, _)| *c == Category::Name),
                "false positive name in {t:?}: {:?}", found(t));
        }
    }
}
