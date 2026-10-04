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
        add(format!(r"(?i:\b(?:patient(?:\s+name)?|pt|name|client|resident|attending|provider|physician|surgeon|referring(?:\s+(?:physician|provider|md))?|pcp|emergency\s+contact|next\s+of\s+kin|nok|guardian|spouse|mother|father|daughter|son|wife|husband|partner|signed(?:\s+by)?|dictated\s+by|reviewed\s+by|seen\s+by|ordered\s+by|cc|author|re|assistant|an(?:a)?esthesiologist|an(?:a)?esthetist|proband|interpreter|social\s+worker|contact|caller|informant|witness))\s*:\s*(?:(?:Dr|Mr|Mrs|Ms|Miss|Mx|Prof)\.?\s+)?((?:{NTOK},\s*)?{full})"), Name, 1, 0.85, None, false);
        add(format!(r"\b({NTOK}(?:\s+[A-Z]\.)?\s+{NTOK}),?\s+(?:M\.?D\.?|D\.?O\.?|R\.?N\.?|N\.?P\.?|PA-C|Ph\.?D\.?|DDS|DPM|PharmD|LCSW|CRNA|FNP|APRN|MBBS|FRCPC)\b"), Name, 1, 0.9, None, false);
        add(format!(r"(?i:\b(?:daughter|son|wife|husband|mother|father|brother|sister|spouse|partner|friend|neighbou?r|caregiver|niece|nephew|aunt|uncle|grand(?:mother|father|son|daughter)|roommate|boyfriend|girlfriend|fianc[ée]e?)),?\s+({NTOK}(?:\s+{NTOK})?)"), Name, 1, 0.8, None, false);
        add(r"\b([A-Z][a-z]+(?:[ -][A-Z][a-z]+){0,2}),\s+(?:ON|QC|BC|AB|MB|SK|NS|NB|NL|PE|YT|NT|NU)\.?,?\s+[A-Z]\d[A-Z][ -]?\d[A-Z]\d\b".into(), Location, 1, 0.9, None, false);
        v
    })
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
}
