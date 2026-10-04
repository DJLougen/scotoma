//! Benchmark harness. Scores the exact pipeline the app ships, not a proxy.
//!
//! The headline metric is leak-oriented: what fraction of gold identifier
//! spans (and characters) survived into the cleaned text. A span counts as
//! caught if any prediction touches it and as fully covered only if every
//! character is redacted.

use crate::labels::{map_label, Mapped};
use crate::{char_to_byte, Category, Scrubber, Span};
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Debug, Clone)]
pub struct GoldSpan {
    pub start: usize,
    pub end: usize,
    pub label: String,
    /// Difficulty tags from the benchmark generator (may be empty).
    pub tags: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct GoldDoc {
    pub id: String,
    pub domain: String,
    pub mode: String,
    pub text: String,
    pub spans: Vec<GoldSpan>,
}

#[derive(Debug, Default, Clone, Serialize)]
pub struct Stats {
    pub gold: usize,
    /// Touched by at least one prediction.
    pub caught: usize,
    /// Every character redacted.
    pub full: usize,
    pub gold_chars: usize,
    pub covered_chars: usize,
    pub predicted: usize,
    pub predicted_correct: usize,
}

impl Stats {
    pub fn recall(&self) -> f64 { ratio(self.caught, self.gold) }
    pub fn full_recall(&self) -> f64 { ratio(self.full, self.gold) }
    pub fn char_recall(&self) -> f64 { ratio(self.covered_chars, self.gold_chars) }
    pub fn precision(&self) -> f64 { ratio(self.predicted_correct, self.predicted) }
    fn add(&mut self, o: &Stats) {
        self.gold += o.gold; self.caught += o.caught; self.full += o.full;
        self.gold_chars += o.gold_chars; self.covered_chars += o.covered_chars;
        self.predicted += o.predicted; self.predicted_correct += o.predicted_correct;
    }
}

fn ratio(a: usize, b: usize) -> f64 { if b == 0 { f64::NAN } else { a as f64 / b as f64 } }

#[derive(Debug, Clone, Serialize)]
pub struct Miss {
    pub category: Category,
    pub label: String,
    pub text: String,
    pub context: String,
    pub partial: bool,
}

#[derive(Debug, Serialize)]
pub struct Report {
    pub docs: usize,
    /// Documents in which at least one identifier got through untouched.
    pub docs_with_leak: usize,
    pub overall: Stats,
    pub by_category: BTreeMap<String, Stats>,
    /// Recall by difficulty tag, domain and input mode (benchmark files only).
    pub by_tag: BTreeMap<String, Stats>,
    pub by_domain: BTreeMap<String, Stats>,
    pub by_mode: BTreeMap<String, Stats>,
    /// One row per gold identifier: (item id, caught 0/1/2 = missed/partial/full).
    /// The item-by-system response matrix is built from these.
    #[serde(skip)]
    pub responses: Vec<(String, u8)>,
    pub misses: Vec<Miss>,
    /// Share of NON-identifier characters that were redacted anyway. A system
    /// can reach perfect recall by blacking out everything; this is the cost.
    pub over_redaction: f64,
    pub ms_per_doc: f64,
    pub chars_per_sec: f64,
}

/// Parse JSONL. Accepts the common shapes:
/// `{"text": ..., "spans": [{"start": 0, "end": 4, "label": "name"}]}` where the
/// list may also be called `entities`/`privacy_mask`, may be JSON-encoded as a
/// string, and the label key may be `label`/`entity_type`/`type`/`entity`.
/// Offsets are in characters (Python convention).
pub fn parse_jsonl(src: &str) -> Result<Vec<GoldDoc>, String> {
    let mut docs = Vec::new();
    for (n, line) in src.lines().enumerate() {
        if line.trim().is_empty() { continue; }
        let v: serde_json::Value = serde_json::from_str(line).map_err(|e| format!("line {}: {e}", n + 1))?;
        let text = ["text", "source_text", "full_text", "document"].iter()
            .find_map(|k| v.get(*k).and_then(|x| x.as_str()))
            .ok_or_else(|| format!("line {}: no text field", n + 1))?.to_string();
        let list = ["spans", "entities", "privacy_mask", "labels"].iter().find_map(|k| v.get(*k));
        let parsed;
        let list = match list {
            Some(serde_json::Value::String(s)) => {
                parsed = serde_json::from_str::<serde_json::Value>(s).map_err(|e| format!("line {}: spans string: {e}", n + 1))?;
                parsed.as_array().cloned().unwrap_or_default()
            }
            Some(serde_json::Value::Array(a)) => a.clone(),
            _ => Vec::new(),
        };
        let mut spans = Vec::new();
        for s in list {
            let (Some(a), Some(b)) = (s.get("start").and_then(|x| x.as_u64()), s.get("end").and_then(|x| x.as_u64())) else { continue };
            let label = ["label", "entity_type", "type", "entity"].iter()
                .find_map(|k| s.get(*k).and_then(|x| x.as_str())).unwrap_or("").to_string();
            let (a, b) = (char_to_byte(&text, a as usize), char_to_byte(&text, b as usize));
            let tags = s.get("tags").and_then(|t| t.as_array())
                .map(|t| t.iter().filter_map(|x| x.as_str().map(String::from)).collect()).unwrap_or_default();
            if a < b { spans.push(GoldSpan { start: a, end: b, label, tags }); }
        }
        let field = |k: &str| v.get(k).and_then(|x| x.as_str()).unwrap_or("").to_string();
        let id = if field("id").is_empty() { format!("doc{}", n + 1) } else { field("id") };
        docs.push(GoldDoc { id, domain: field("domain"), mode: field("mode"), text, spans });
    }
    Ok(docs)
}

fn covered(pred: &[Span], a: usize, b: usize) -> usize {
    pred.iter().map(|p| p.end.min(b).saturating_sub(p.start.max(a))).sum()
}

fn context(text: &str, a: usize, b: usize) -> String {
    let mut s = a.saturating_sub(30);
    while !text.is_char_boundary(s) { s -= 1; }
    let mut e = (b + 30).min(text.len());
    while !text.is_char_boundary(e) { e += 1; }
    format!("…{}⟦{}⟧{}…", &text[s..a], &text[a..b], &text[b..e]).replace('\n', " ")
}

pub fn evaluate(scrubber: &Scrubber, docs: &[GoldDoc], max_misses: usize) -> Result<Report, String> {
    let mut by: BTreeMap<String, Stats> = BTreeMap::new();
    let (mut by_tag, mut by_domain, mut by_mode): (BTreeMap<String, Stats>, BTreeMap<String, Stats>, BTreeMap<String, Stats>) = Default::default();
    let mut responses = Vec::new();
    let mut misses = Vec::new();
    let mut docs_with_leak = 0;
    let mut chars = 0usize;
    let (mut clean_chars, mut clean_redacted) = (0usize, 0usize);
    let t0 = std::time::Instant::now();
    for doc in docs {
        chars += doc.text.len();
        let det = scrubber.detect_doc(&doc.id, &doc.text)?;
        let mut gold_regions: Vec<(usize, usize)> = Vec::new();
        let mut leaked = false;
        for (gi, g) in doc.spans.iter().enumerate() {
            gold_regions.push((g.start, g.end));
            let cat = match map_label(&g.label) {
                Mapped::Phi(c) => c,
                Mapped::Quasi if scrubber.config.strict => Category::Org,
                _ => continue, // not an identifier under the active policy
            };
            // Ages are only identifiers above 89.
            if cat == Category::Age {
                let n: String = doc.text[g.start..g.end].chars().filter(|c| c.is_ascii_digit()).collect();
                if n.parse::<u32>().map(|n| n < 90).unwrap_or(true) { continue; }
            }
            let st = by.entry(cat.tag().to_string()).or_default();
            // Score on non-whitespace characters so "John Smith" split in two
            // predictions still counts as fully covered.
            let body: usize = doc.text[g.start..g.end].chars().filter(|c| !c.is_whitespace()).map(|c| c.len_utf8()).sum();
            let ws = (g.end - g.start) - body;
            let cov = covered(&det.spans, g.start, g.end);
            st.gold += 1;
            st.gold_chars += body;
            st.covered_chars += cov.saturating_sub(ws.min(cov)).min(body).max(if cov >= g.end - g.start { body } else { 0 });
            if cov > 0 { st.caught += 1; }
            let full = cov + ws >= g.end - g.start && cov > 0;
            responses.push((format!("{}#{}", doc.id, gi), if full { 2 } else if cov > 0 { 1 } else { 0 }));
            for t in &g.tags {
                let grp = by_tag.entry(t.clone()).or_default();
                grp.gold += 1; grp.gold_chars += body;
                if cov > 0 { grp.caught += 1; }
                if full { grp.full += 1; }
            }
            for (map, key) in [(&mut by_domain, &doc.domain), (&mut by_mode, &doc.mode)] {
                if key.is_empty() { continue; }
                let grp = map.entry(key.clone()).or_default();
                grp.gold += 1; grp.gold_chars += body;
                if cov > 0 { grp.caught += 1; }
                if full { grp.full += 1; }
            }
            if full {
                st.full += 1;
            } else {
                if cov == 0 { leaked = true; }
                if misses.len() < max_misses {
                    misses.push(Miss {
                        category: cat, label: g.label.clone(),
                        text: doc.text[g.start..g.end].to_string(),
                        context: context(&doc.text, g.start, g.end), partial: cov > 0,
                    });
                }
            }
        }
        if leaked { docs_with_leak += 1; }
        // Collateral damage: redacted characters that no annotation covers.
        let mut gold_mask = vec![false; doc.text.len()];
        for &(a, b) in &gold_regions { for m in &mut gold_mask[a..b.min(doc.text.len())] { *m = true; } }
        let mut pred_mask = vec![false; doc.text.len()];
        for p in &det.spans { for m in &mut pred_mask[p.start..p.end.min(doc.text.len())] { *m = true; } }
        for (i, ch) in doc.text.char_indices() {
            if ch.is_whitespace() || gold_mask[i] { continue; }
            clean_chars += 1;
            if pred_mask[i] { clean_redacted += 1; }
        }
        for p in &det.spans {
            let st = by.entry(p.category.tag().to_string()).or_default();
            st.predicted += 1;
            // Overlapping any annotated region is not a false alarm, even if the
            // policy keeps that region (e.g. a state name).
            if gold_regions.iter().any(|&(a, b)| p.start < b && a < p.end) { st.predicted_correct += 1; }
        }
    }
    let el = t0.elapsed().as_secs_f64();
    let mut overall = Stats::default();
    for s in by.values() { overall.add(s); }
    Ok(Report {
        docs: docs.len(), docs_with_leak, overall, by_category: by, by_tag, by_domain, by_mode, responses, misses,
        over_redaction: if clean_chars == 0 { 0.0 } else { clean_redacted as f64 / clean_chars as f64 },
        ms_per_doc: if docs.is_empty() { 0.0 } else { el * 1000.0 / docs.len() as f64 },
        chars_per_sec: if el > 0.0 { chars as f64 / el } else { 0.0 },
    })
}

fn pct(x: f64) -> String { if x.is_nan() { "    –".into() } else { format!("{:5.1}", x * 100.0) } }

pub fn format_report(r: &Report) -> String {
    let mut s = String::new();
    s.push_str(&format!("{:<10} {:>6} {:>7} {:>7} {:>7} {:>6} {:>7}\n", "category", "gold", "recall", "full", "chars", "pred", "prec"));
    s.push_str(&format!("{}\n", "-".repeat(58)));
    let mut row = |name: &str, st: &Stats| {
        s.push_str(&format!("{:<10} {:>6} {:>7} {:>7} {:>7} {:>6} {:>7}\n", name, st.gold, pct(st.recall()), pct(st.full_recall()), pct(st.char_recall()), st.predicted, pct(st.precision())));
    };
    for (k, st) in &r.by_category { row(k, st); }
    row("ALL", &r.overall);
    s.push_str(&format!(
        "\n{} docs · {} with at least one identifier untouched · {:.1}% of ordinary text redacted by mistake · {:.1} ms/doc · {:.0} chars/s\n",
        r.docs, r.docs_with_leak, r.over_redaction * 100.0, r.ms_per_doc, r.chars_per_sec
    ));
    for (title, map) in [("by difficulty tag", &r.by_tag), ("by domain", &r.by_domain), ("by input mode", &r.by_mode)] {
        if map.is_empty() { continue; }
        s.push_str(&format!("\n{:<22} {:>6} {:>7} {:>7}\n{}\n", title, "gold", "recall", "full", "-".repeat(46)));
        for (k, st) in map {
            s.push_str(&format!("{:<22} {:>6} {:>7} {:>7}\n", k, st.gold, pct(st.recall()), pct(st.full_recall())));
        }
    }
    s.push_str("recall = span touched · full = every character redacted · chars = share of identifier characters redacted\n");
    s
}
