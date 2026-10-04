//! Replace detected spans, remember what was replaced, and put it back.
//!
//! Two modes:
//! * `Tag` — `[NAME_1]`, `[DATE_2:2024]`. Safe Harbor-shaped output (year kept,
//!   ZIP3 kept, ages over 89 pooled) and exactly reversible.
//! * `Surrogate` — realistic stand-ins ("Marek Lindqvist", shifted dates) that
//!   read naturally to a model. Reversible as long as the stand-in survives
//!   verbatim in the reply.
//!
//! The vault lives in memory only and is wiped on `clear()` and on drop.

use crate::{current_year, Category, Span};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::OnceLock;
use zeroize::Zeroize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum Mode {
    #[default]
    Tag,
    Surrogate,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Item {
    /// Byte range in the original text.
    pub start: usize,
    pub end: usize,
    pub category: Category,
    pub replacement: String,
    /// Byte range in the cleaned text.
    pub out_start: usize,
    pub out_end: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Rendered {
    pub text: String,
    pub items: Vec<Item>,
}

struct Person {
    id: u32,
    tokens: Vec<String>,
    forms: Vec<String>,
}

pub struct Vault {
    /// "NAME_1.2" → original text.
    tags: HashMap<String, String>,
    seen_tag: HashMap<(Category, String), String>,
    counters: HashMap<Category, u32>,
    persons: Vec<Person>,
    /// (stand-in, original), exact strings.
    fakes: Vec<(String, String)>,
    seen_fake: HashMap<(Category, String), String>,
    /// lowercased original name token → stand-in token.
    name_tok: HashMap<String, String>,
    rng: u64,
    date_shift: i64,
}

impl Default for Vault {
    fn default() -> Self { Self::new() }
}

impl Drop for Vault {
    fn drop(&mut self) { self.clear(); }
}

/// ZIP3 prefixes with fewer than 20,000 residents (2000 census): must become 000.
const SPARSE_ZIP3: &[&str] = &[
    "036", "059", "063", "102", "203", "556", "692", "790", "821", "823", "830", "831", "878",
    "879", "884", "890", "893",
];

// Stand-ins are deliberately uncommon as English words and as medical eponyms,
// so restoring a reply cannot rewrite "Bell's palsy" into a patient's name.
const FIRST: &[&str] = &[
    "Marek", "Anneli", "Tobias", "Ilse", "Rafael", "Noemi", "Kellan", "Sunniva", "Darius",
    "Oriana", "Lennart", "Mirela", "Corwin", "Yelena", "Emeric", "Talitha", "Joaquin", "Saskia",
    "Bertrand", "Lucinda", "Anselm", "Rosalind", "Thaddeus", "Ottilie", "Leopold", "Marisol",
    "Evander", "Henrike", "Cormac", "Briseis",
];
const LAST: &[&str] = &[
    "Lindqvist", "Marchetti", "Okonjo", "Vandersloot", "Tanizaki", "Abernethy", "Kowalczyk",
    "Delacroix", "Hargreave", "Montalvo", "Rasmussen", "Petrakis", "Thornbury", "Villanueva",
    "Brannigan", "Castellan", "Dunmore", "Eszterhas", "Fairweather", "Galloway", "Ibarra",
    "Jaramillo", "Kilbride", "Lazarev", "Novotny", "Quintero", "Rothwell", "Sandoval",
    "Uchimura", "Whitlock",
];
const CITY: &[&str] = &[
    "Larkhaven", "Brindlemoor", "Eastwick", "Calder Falls", "Northbrook Mills", "Sorrel Bay",
    "Thistledown", "Marrow Creek", "Aldergate", "Penrose Hollow",
];
const STREETS: &[&str] = &["Alder", "Juniper", "Larch", "Hemlock", "Tamarack", "Sycamore", "Linden", "Hawthorn"];
const TITLES: &[&str] = &["dr", "mr", "mrs", "ms", "miss", "mx", "prof", "md", "do", "rn", "np", "phd", "jr", "sr"];
const MONTHS: [&str; 12] = [
    "January", "February", "March", "April", "May", "June", "July", "August", "September",
    "October", "November", "December",
];

fn norm(cat: Category, s: &str) -> String {
    match cat {
        Category::Phone | Category::Fax | Category::Ssn => s.chars().filter(|c| c.is_ascii_digit()).collect(),
        _ => s.split_whitespace().collect::<Vec<_>>().join(" ").to_lowercase(),
    }
}

fn name_tokens(s: &str) -> Vec<String> {
    s.split(|c: char| !(c.is_alphabetic() || c == '\'' || c == '’' || c == '-'))
        .map(|t| t.trim_matches(|c: char| !c.is_alphabetic()).to_lowercase())
        .filter(|t| t.chars().count() >= 2 && !TITLES.contains(&t.as_str()))
        .collect()
}

fn year_of(s: &str) -> Option<i32> {
    static Y4: OnceLock<Regex> = OnceLock::new();
    static Y2: OnceLock<Regex> = OnceLock::new();
    let y4 = Y4.get_or_init(|| Regex::new(r"\b((?:19|20)\d{2})\b").unwrap());
    if let Some(m) = y4.captures(s) {
        return m[1].parse().ok();
    }
    let y2 = Y2.get_or_init(|| Regex::new(r"[/.\- ](\d{2})$").unwrap());
    let yy: i32 = y2.captures(s)?.get(1)?.as_str().parse().ok()?;
    // Only for numeric dates: "Mar 14" has no year.
    if s.chars().filter(|c| matches!(c, '/' | '.' | '-')).count() < 2 { return None; }
    let now = current_year();
    Some(if 2000 + yy <= now + 1 { 2000 + yy } else { 1900 + yy })
}

// --- civil calendar (Howard Hinnant's algorithms) ---------------------------
fn days_from_civil(y: i64, m: i64, d: i64) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = y - era * 400;
    let doy = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}
fn civil_from_days(z: i64) -> (i64, i64, i64) {
    let z = z + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (if m <= 2 { y + 1 } else { y }, m, d)
}
fn valid_ymd(y: i64, m: i64, d: i64) -> bool {
    (1..=12).contains(&m) && d >= 1 && civil_from_days(days_from_civil(y, m, d)) == (y, m, d)
}

/// Shift a date string by `shift` days, keeping its format. None if unparsed.
fn shift_date(s: &str, shift: i64) -> Option<String> {
    static ISO: OnceLock<Regex> = OnceLock::new();
    static NUM: OnceLock<Regex> = OnceLock::new();
    static NAMED: OnceLock<Regex> = OnceLock::new();
    let iso = ISO.get_or_init(|| Regex::new(r"^(\d{4})-(\d{2})-(\d{2})(.*)$").unwrap());
    let num = NUM.get_or_init(|| Regex::new(r"^(\d{1,2})([/.-])(\d{1,2})[/.-](\d{4})$").unwrap());
    let named = NAMED.get_or_init(|| Regex::new(r"^([A-Za-z]{3,9})(\.?)\s+(\d{1,2})(st|nd|rd|th)?(,?)\s+(\d{4})$").unwrap());

    if let Some(c) = iso.captures(s) {
        let (y, m, d): (i64, i64, i64) = (c[1].parse().ok()?, c[2].parse().ok()?, c[3].parse().ok()?);
        if !valid_ymd(y, m, d) { return None; }
        let (y, m, d) = civil_from_days(days_from_civil(y, m, d) + shift);
        return Some(format!("{y:04}-{m:02}-{d:02}{}", &c[4]));
    }
    if let Some(c) = num.captures(s) {
        let (a, b, y): (i64, i64, i64) = (c[1].parse().ok()?, c[3].parse().ok()?, c[4].parse().ok()?);
        let sep = &c[2];
        let day_first = a > 12;
        let (m, d) = if day_first { (b, a) } else { (a, b) };
        if !valid_ymd(y, m, d) { return None; }
        let (y2, m2, d2) = civil_from_days(days_from_civil(y, m, d) + shift);
        let pad = c[1].len() == 2 && c[3].len() == 2;
        let (x, z) = if day_first { (d2, m2) } else { (m2, d2) };
        // A day-first date must stay unambiguous after the shift.
        if day_first && x <= 12 { return None; }
        return Some(if pad { format!("{x:02}{sep}{z:02}{sep}{y2}") } else { format!("{x}{sep}{z}{sep}{y2}") });
    }
    if let Some(c) = named.captures(s) {
        let mon = c[1].to_lowercase();
        let m = MONTHS.iter().position(|n| n.to_lowercase().starts_with(&mon[..3.min(mon.len())]) && n.to_lowercase().starts_with(&mon) || (mon == "sept" && *n == "September"))? as i64 + 1;
        let (d, y): (i64, i64) = (c[3].parse().ok()?, c[6].parse().ok()?);
        if !valid_ymd(y, m, d) { return None; }
        let (y2, m2, d2) = civil_from_days(days_from_civil(y, m, d) + shift);
        let full = MONTHS[(m2 - 1) as usize];
        let abbreviated = c[1].len() <= 4 && full.len() > c[1].len();
        let mut name = if abbreviated { full[..3].to_string() } else { full.to_string() };
        if c[1].chars().all(|ch| ch.is_uppercase()) { name = name.to_uppercase(); }
        let dot = if abbreviated { &c[2] } else { "" };
        let ord = if c.get(4).is_some() {
            match (d2 % 10, d2 % 100) { (1, 11) | (2, 12) | (3, 13) => "th", (1, _) => "st", (2, _) => "nd", (3, _) => "rd", _ => "th" }
        } else { "" };
        return Some(format!("{name}{dot} {d2}{ord}{} {y2}", &c[5]));
    }
    None
}

impl Vault {
    pub fn new() -> Self {
        let mut seed = [0u8; 8];
        let _ = getrandom::getrandom(&mut seed);
        let mut v = Vault {
            tags: HashMap::new(),
            seen_tag: HashMap::new(),
            counters: HashMap::new(),
            persons: Vec::new(),
            fakes: Vec::new(),
            seen_fake: HashMap::new(),
            name_tok: HashMap::new(),
            rng: u64::from_le_bytes(seed) | 1,
            date_shift: 0,
        };
        v.date_shift = -(7 + (v.next() % 54) as i64);
        v
    }

    /// Deterministic vault for tests.
    pub fn seeded(seed: u64) -> Self {
        let mut v = Vault::new();
        v.rng = seed | 1;
        v.date_shift = -(7 + (v.next() % 54) as i64);
        v
    }

    fn next(&mut self) -> u64 {
        let mut x = self.rng;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.rng = x;
        x.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }

    /// Number of remembered originals.
    pub fn len(&self) -> usize { self.tags.len() + self.fakes.len() }
    pub fn is_empty(&self) -> bool { self.len() == 0 }

    /// Wipe every remembered original from memory.
    pub fn clear(&mut self) {
        for (_, v) in self.tags.iter_mut() { v.zeroize(); }
        for (a, b) in self.fakes.iter_mut() { a.zeroize(); b.zeroize(); }
        for p in self.persons.iter_mut() {
            for t in p.tokens.iter_mut() { t.zeroize(); }
            for t in p.forms.iter_mut() { t.zeroize(); }
        }
        // Keys hold normalised originals too; rebuild the maps to drop them.
        for ((_, mut k), _) in std::mem::take(&mut self.seen_tag) { k.zeroize(); }
        for ((_, mut k), _) in std::mem::take(&mut self.seen_fake) { k.zeroize(); }
        for (mut k, _) in std::mem::take(&mut self.name_tok) { k.zeroize(); }
        self.tags.clear();
        self.fakes.clear();
        self.persons.clear();
        self.counters.clear();
    }

    fn bump(&mut self, cat: Category) -> u32 {
        let c = self.counters.entry(cat).or_insert(0);
        *c += 1;
        *c
    }

    fn tag_for(&mut self, span: &Span, original: &str) -> String {
        let cat = span.category;
        let key = (cat, norm(cat, original));
        if let Some(t) = self.seen_tag.get(&key) {
            return t.clone();
        }
        let id = if cat == Category::Name {
            let toks = name_tokens(original);
            let hit = self.persons.iter().position(|p| toks.iter().any(|t| p.tokens.contains(t)));
            let idx = match hit {
                Some(i) => i,
                None => {
                    let id = self.bump(cat);
                    self.persons.push(Person { id, tokens: Vec::new(), forms: Vec::new() });
                    self.persons.len() - 1
                }
            };
            let p = &mut self.persons[idx];
            for t in toks { if !p.tokens.contains(&t) { p.tokens.push(t); } }
            p.forms.push(key.1.clone());
            if p.forms.len() == 1 { format!("{}", p.id) } else { format!("{}.{}", p.id, p.forms.len()) }
        } else {
            self.bump(cat).to_string()
        };
        let suffix = match cat {
            Category::Date => match year_of(original) {
                Some(y) if !(span.dob && current_year() - y >= 90) => format!(":{y}"),
                _ => String::new(),
            },
            Category::Zip => {
                let d: String = original.chars().filter(|c| c.is_ascii_digit()).take(3).collect();
                if d.len() == 3 && original.trim().len() <= 10 && original.trim().as_bytes()[0].is_ascii_digit() {
                    format!(":{}", if SPARSE_ZIP3.contains(&d.as_str()) { "000" } else { d.as_str() })
                } else { String::new() }
            }
            Category::Age => ":90+".into(),
            _ => String::new(),
        };
        let k = format!("{}_{}", cat.tag(), id);
        self.tags.insert(k.clone(), original.to_string());
        let t = format!("[{k}{suffix}]");
        self.seen_tag.insert(key, t.clone());
        t
    }

    fn scramble(&mut self, s: &str) -> String {
        s.chars().map(|c| {
            let r = self.next();
            if c.is_ascii_digit() { (b'0' + (r % 10) as u8) as char }
            else if c.is_ascii_uppercase() { (b'A' + (r % 26) as u8) as char }
            else if c.is_ascii_lowercase() { (b'a' + (r % 26) as u8) as char }
            else { c }
        }).collect()
    }

    fn fake_name(&mut self, original: &str, context: &str) -> String {
        // Tokenise, keeping separators, and map each real token to a stand-in.
        let mut out = String::new();
        let mut pieces: Vec<(bool, &str)> = Vec::new();
        let mut last = 0;
        let is_tok = |c: char| c.is_alphabetic() || c == '\'' || c == '’' || c == '-';
        let mut in_tok = false;
        for (i, c) in original.char_indices() {
            if is_tok(c) != in_tok {
                if i > last { pieces.push((in_tok, &original[last..i])); }
                last = i;
                in_tok = is_tok(c);
            }
        }
        if last < original.len() { pieces.push((in_tok, &original[last..])); }
        let comma_form = original.contains(',');
        let tok_idx: Vec<usize> = pieces.iter().enumerate().filter(|(_, p)| p.0).map(|(i, _)| i).collect();
        let surname_idx = if comma_form { tok_idx.first().copied() } else { tok_idx.last().copied() };
        let ctx_low = context.to_lowercase();
        for (i, (is_token, piece)) in pieces.iter().enumerate() {
            if !*is_token { out.push_str(piece); continue; }
            let low = piece.to_lowercase();
            if TITLES.contains(&low.as_str()) { out.push_str(piece); continue; }
            if piece.chars().count() == 1 {
                // Initials: stable stand-in letter.
                let c = piece.chars().next().unwrap();
                out.push((b'A' + ((c as u32 * 7 + 3) % 26) as u8) as char);
                continue;
            }
            let fake = match self.name_tok.get(&low) {
                Some(f) => f.clone(),
                None => {
                    let pool = if Some(i) == surname_idx && tok_idx.len() > 1 || tok_idx.len() == 1 && self.name_tok.is_empty() { LAST } else { FIRST };
                    let pool = if tok_idx.len() == 1 { LAST } else { pool };
                    let start = (self.next() % pool.len() as u64) as usize;
                    let mut pick = None;
                    for k in 0..pool.len() {
                        let cand = pool[(start + k) % pool.len()];
                        let cl = cand.to_lowercase();
                        if self.name_tok.values().any(|v| v.to_lowercase() == cl) || ctx_low.contains(&cl) { continue; }
                        pick = Some(cand.to_string());
                        break;
                    }
                    let f = pick.unwrap_or_else(|| format!("Person{}", self.name_tok.len() + 1));
                    self.name_tok.insert(low.clone(), f.clone());
                    self.fakes.push((f.clone(), piece.to_string()));
                    f
                }
            };
            if piece.chars().all(|c| !c.is_lowercase()) { out.push_str(&fake.to_uppercase()); } else { out.push_str(&fake); }
        }
        out
    }

    fn fake_for(&mut self, span: &Span, original: &str, context: &str) -> Option<String> {
        use Category::*;
        let cat = span.category;
        let key = (cat, norm(cat, original));
        if let Some(f) = self.seen_fake.get(&key) { return Some(f.clone()); }
        let mut tries = 0;
        let fake = loop {
            tries += 1;
            if tries > 8 { return None; }
            let f = match cat {
                Name => self.fake_name(original, context),
                Phone | Fax => {
                    let n = digits(original);
                    let mut k = 0;
                    let line = 100 + self.next() % 100; // 555-01xx is reserved for fiction
                    let area = 200 + self.next() % 800;
                    let ten = format!("{area}555{line:04}");
                    let rnd = self.scramble(original);
                    if n >= 10 {
                        let lead = n - 10;
                        original.chars().zip(rnd.chars()).map(|(c, r)| {
                            if c.is_ascii_digit() {
                                k += 1;
                                if k <= lead { c } else if k - lead <= 10 { ten.as_bytes()[k - lead - 1] as char } else { r }
                            } else { c }
                        }).collect()
                    } else if n == 7 {
                        let seven = format!("555{line:04}");
                        original.chars().map(|c| if c.is_ascii_digit() { k += 1; seven.as_bytes()[k - 1] as char } else { c }).collect()
                    } else { rnd }
                }
                Ssn => {
                    let rnd = self.scramble(original);
                    let mut k = 0;
                    original.chars().zip(rnd.chars()).map(|(c, r)| {
                        if c.is_ascii_digit() { k += 1; if k <= 5 { '0' } else { r } } else { c }
                    }).collect()
                }
                Email => format!("contact{}@example.com", self.bump(Email)),
                Url => format!("https://example.com/r{}", self.bump(Url)),
                Ip => format!("192.0.2.{}", 1 + self.next() % 254),
                Mrn | Plan | Account | License | Device | Id | Vehicle => self.scramble(original),
                Zip => {
                    let d: String = original.chars().filter(|c| c.is_ascii_digit()).collect();
                    if d.len() != 5 && d.len() != 9 { return None; }
                    let p = if SPARSE_ZIP3.contains(&&d[..3]) { "000" } else { &d[..3] };
                    format!("{p}{:02}", self.next() % 100)
                }
                Address => {
                    let n = 100 + self.next() % 9800;
                    let s = STREETS[(self.next() % STREETS.len() as u64) as usize];
                    format!("{n} {s} Street")
                }
                Location => CITY[(self.next() % CITY.len() as u64) as usize].to_string(),
                Date => {
                    if span.dob && year_of(original).map(|y| current_year() - y >= 90).unwrap_or(false) { return None; }
                    shift_date(original, self.date_shift)?
                }
                Age | Biometric | Org => return None,
            };
            if f == original { continue; }
            // A stand-in must map back to exactly one original.
            if cat != Name && self.fakes.iter().any(|(k, v)| *k == f && v != original) { continue; }
            if cat != Name && context.contains(&f) { continue; }
            break f;
        };
        if !self.fakes.iter().any(|(k, _)| *k == fake) {
            self.fakes.push((fake.clone(), original.to_string()));
        }
        self.seen_fake.insert(key, fake.clone());
        Some(fake)
    }

    /// Put originals back into text that came back from the outside world.
    /// Returns (restored text, number of replacements).
    pub fn restore(&self, text: &str) -> (String, usize) {
        static TAG: OnceLock<Regex> = OnceLock::new();
        let tag = TAG.get_or_init(|| {
            Regex::new(r"(?i)\[\s*([A-Z]+)[_ ](\d+(?:\.\d+)?)\s*(?::[^\]\n]{0,12})?\]").unwrap()
        });
        let mut count = 0;
        let mut out = tag.replace_all(text, |c: &regex::Captures| {
            let key = format!("{}_{}", c[1].to_ascii_uppercase(), &c[2]);
            match self.tags.get(&key) {
                Some(orig) => { count += 1; orig.clone() }
                None => c[0].to_string(),
            }
        }).into_owned();

        if !self.fakes.is_empty() {
            let mut fakes: Vec<&(String, String)> = self.fakes.iter().collect();
            fakes.sort_by_key(|(f, _)| std::cmp::Reverse(f.len()));
            let word = |c: Option<char>| c.map(|c| c.is_alphanumeric() || c == '_').unwrap_or(false);
            let alt = fakes.iter().map(|(f, _)| {
                let e = regex::escape(f);
                let pre = if word(f.chars().next()) { r"\b" } else { "" };
                let post = if word(f.chars().last()) { r"\b" } else { "" };
                format!("{pre}{e}{post}")
            }).collect::<Vec<_>>().join("|");
            if let Ok(re) = Regex::new(&alt) {
                let map: HashMap<&str, &str> = fakes.iter().map(|(f, o)| (f.as_str(), o.as_str())).collect();
                let upper: HashMap<String, &str> = fakes.iter().map(|(f, o)| (f.to_uppercase(), o.as_str())).collect();
                out = re.replace_all(&out, |c: &regex::Captures| {
                    let m = &c[0];
                    if let Some(o) = map.get(m).or_else(|| upper.get(m)) { count += 1; (*o).to_string() } else { m.to_string() }
                }).into_owned();
            }
        }
        (out, count)
    }
}

fn digits(s: &str) -> usize { s.bytes().filter(|b| b.is_ascii_digit()).count() }

/// Replace `spans` (sorted, non-overlapping) in `text`.
pub fn render(text: &str, spans: &[Span], mode: Mode, vault: &mut Vault) -> Rendered {
    let mut out = String::with_capacity(text.len());
    let mut items = Vec::with_capacity(spans.len());
    let mut pos = 0;
    for s in spans {
        if s.start < pos || s.end > text.len() || s.start >= s.end { continue; }
        out.push_str(&text[pos..s.start]);
        let original = &text[s.start..s.end];
        let replacement = match mode {
            Mode::Surrogate => vault.fake_for(s, original, text),
            Mode::Tag => None,
        }.unwrap_or_else(|| vault.tag_for(s, original));
        let out_start = out.len();
        out.push_str(&replacement);
        items.push(Item { start: s.start, end: s.end, category: s.category, replacement, out_start, out_end: out.len() });
        pos = s.end;
    }
    out.push_str(&text[pos..]);
    Rendered { text: out, items }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Config, Scrubber};

    const NOTE: &str = "Patient: Maria Gonzalez, DOB: 02/11/1961, MRN: 00482913.\n\
Seen 03/14/2024 by Dr. Priya Raman. Gonzalez reports chest pain since March 2, 2024.\n\
Lives at 42 Wallaby Way, Springfield, IL 62704. Phone (217) 555-2368, maria.g@example.org.\n\
Her mother is 94 years old. Follow up in 2 weeks; metoprolol 25 mg BID.";

    fn scrub(mode: Mode, vault: &mut Vault) -> Rendered {
        let sc = Scrubber::rules_only(Config::default());
        let det = sc.detect(NOTE).unwrap();
        render(NOTE, &det.spans, mode, vault)
    }

    #[test]
    fn tag_mode_is_safe_harbor_shaped_and_round_trips() {
        let mut v = Vault::seeded(7);
        let r = scrub(Mode::Tag, &mut v);
        for leak in ["Maria", "Gonzalez", "Raman", "00482913", "02/11", "03/14", "March 2", "Wallaby", "62704", "555-2368", "example.org", "94"] {
            assert!(!r.text.contains(leak), "leaked {leak}:\n{}", r.text);
        }
        for keep in ["chest pain", "metoprolol 25 mg BID", ":2024]", ":1961]", ":627]", ":90+]", "IL", "2 weeks"] {
            assert!(r.text.contains(keep), "lost {keep}:\n{}", r.text);
        }
        // Same person, linked tags.
        assert!(r.text.contains("[NAME_1]") && r.text.contains("[NAME_1.2]"), "{}", r.text);
        let (back, n) = v.restore(&r.text);
        assert_eq!(back, NOTE);
        assert_eq!(n, r.items.len());
    }

    #[test]
    fn restore_tolerates_reformatted_tags() {
        let mut v = Vault::seeded(7);
        let _ = scrub(Mode::Tag, &mut v);
        let reply = "Summary for [name_1]: seen [ DATE_2 ] by Dr. [NAME_2]. Unknown [NAME_99].";
        let (back, n) = v.restore(reply);
        assert_eq!(n, 3);
        assert!(back.starts_with("Summary for Maria Gonzalez: seen 03/14/2024 by Dr. Priya Raman."), "{back}");
        assert!(back.contains("[NAME_99]"));
    }

    #[test]
    fn surrogate_mode_reads_naturally_and_round_trips() {
        let mut v = Vault::seeded(11);
        let r = scrub(Mode::Surrogate, &mut v);
        for leak in ["Maria", "Gonzalez", "Raman", "00482913", "02/11/1961", "03/14/2024", "Wallaby", "62704", "555-2368", "example.org"] {
            assert!(!r.text.contains(leak), "leaked {leak}:\n{}", r.text);
        }
        assert!(!r.text.contains("[NAME"), "{}", r.text);
        assert!(r.text.contains("555-01"), "{}", r.text);
        let (back, _) = v.restore(&r.text);
        assert_eq!(back, NOTE);
        // The surname alone maps to the same stand-in surname.
        let full = &r.items.iter().find(|i| &NOTE[i.start..i.end] == "Maria Gonzalez").unwrap().replacement;
        let last = &r.items.iter().find(|i| &NOTE[i.start..i.end] == "Gonzalez").unwrap().replacement;
        assert!(full.ends_with(last.as_str()), "{full} / {last}");
    }

    #[test]
    fn date_shift_keeps_format_and_intervals() {
        assert_eq!(shift_date("03/14/2024", -14).unwrap(), "02/29/2024");
        assert_eq!(shift_date("3/4/2024", -4).unwrap(), "2/29/2024");
        assert_eq!(shift_date("2024-01-05T08:30", -10).unwrap(), "2023-12-26T08:30");
        assert_eq!(shift_date("March 2, 2024", -2).unwrap(), "February 29, 2024");
        assert_eq!(shift_date("Mar 2 2024", -1).unwrap(), "Mar 1 2024");
        assert!(shift_date("02/30/2024", -1).is_none());
    }

    #[test]
    fn old_dob_drops_year_and_sparse_zip_is_zeroed() {
        let sc = Scrubber::rules_only(Config::default());
        let t = "DOB: 02/11/1931. Zip code: 03601.";
        let det = sc.detect(t).unwrap();
        let mut v = Vault::seeded(3);
        let r = render(t, &det.spans, Mode::Tag, &mut v);
        assert_eq!(r.text, "DOB: [DATE_1]. Zip code: [ZIP_1:000].");
    }

    #[test]
    fn clear_forgets_everything() {
        let mut v = Vault::seeded(7);
        let r = scrub(Mode::Tag, &mut v);
        assert!(v.len() > 0);
        v.clear();
        assert_eq!(v.len(), 0);
        assert_eq!(v.restore(&r.text).0, r.text);
    }
}
