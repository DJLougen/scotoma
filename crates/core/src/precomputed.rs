//! Replays spans another system already produced, so external tools
//! (Presidio, OpenMed, the Stanford de-identifier...) are scored by the
//! exact same pipeline and metrics as ours. `bench/predict_external.py`
//! writes the file; `scotoma eval DATA --predictions PREDS` scores it.
//!
//! One JSONL line per benchmark document, in order:
//! `{"id": <doc id or null>, "text": <exact doc text>,
//!   "spans": [{"start": ..., "end": ..., "label": ...}]}`.
//! Offsets are characters, like the benchmark files themselves.
//!
//! Labels go through labels::map_label exactly like ONNX model classes:
//! Phi -> its category, Quasi -> ORG (dropped unless --strict), anything
//! else dropped. Every span is a confident hit; nothing lands in the
//! "possible" review list. Spans get the same tidy pass as model output
//! (trim whitespace, grow to whole words, drop bare honorifics and
//! ages under 90) — it's cheap and keeps the comparison apples-to-apples.
//!
//! Lookup: the evaluator names each document (Detector::detect_doc) using
//! eval's id convention — an explicit id wins, otherwise `doc<lineno>` —
//! and the same convention applies to prediction rows, so duplicate texts
//! can't collide and a reordered file still lines up. The text at that id
//! is a consistency check: if it differs, or no row carries the doc's id,
//! that's an error — silently scoring a missing document as "no
//! detections" would fabricate a recall hit.

use crate::labels::{map_label, Mapped};
use crate::{char_to_byte, tidy, Category, Config, Detector, Source, Span};
use std::collections::HashMap;
use std::path::Path;

struct PredSpan {
    start: usize,
    end: usize,
    label: String,
}

struct Entry {
    text: String,
    spans: Vec<PredSpan>,
}

pub struct PrecomputedDetector {
    entries: Vec<Entry>,
    /// Document id -> entry, using eval's convention: the row's own id, or
    /// `doc<lineno>` when it has none, so rows always have a stable key.
    by_id: HashMap<String, usize>,
    /// Exact text -> entry, used only when the caller can't name the doc
    /// (scrub) — eval always passes an id. Duplicated texts keep the first.
    by_text: HashMap<String, usize>,
    name: String,
}

impl PrecomputedDetector {
    pub fn load(path: &Path) -> Result<Self, String> {
        let src = std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
        let (mut entries, mut by_id, mut by_text) = (Vec::new(), HashMap::new(), HashMap::new());
        for (n, line) in src.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let v: serde_json::Value =
                serde_json::from_str(line).map_err(|e| format!("line {}: {e}", n + 1))?;
            let text = v.get("text").and_then(|x| x.as_str())
                .ok_or_else(|| format!("line {}: no text field", n + 1))?.to_string();
            let mut spans = Vec::new();
            for s in v.get("spans").and_then(|x| x.as_array()).cloned().unwrap_or_default() {
                let (Some(a), Some(b)) = (
                    s.get("start").and_then(|x| x.as_u64()),
                    s.get("end").and_then(|x| x.as_u64()),
                ) else { continue };
                let label = s.get("label").and_then(|x| x.as_str()).unwrap_or("").to_string();
                spans.push(PredSpan { start: a as usize, end: b as usize, label });
            }
            let id = v.get("id").and_then(|x| x.as_str()).filter(|i| !i.is_empty())
                .map(str::to_string).unwrap_or_else(|| format!("doc{}", n + 1));
            if by_id.insert(id, entries.len()).is_some() {
                return Err(format!("line {}: duplicate id", n + 1));
            }
            by_text.entry(text.clone()).or_insert(entries.len());
            entries.push(Entry { text, spans });
        }
        let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("predictions").to_string();
        Ok(PrecomputedDetector { entries, by_id, by_text, name })
    }
}

impl Detector for PrecomputedDetector {
    fn name(&self) -> String { format!("precomputed:{}", self.name) }

    fn detect(&self, text: &str, cfg: &Config) -> Result<(Vec<Span>, Vec<Span>), String> {
        self.detect_doc(None, text, cfg)
    }

    fn detect_doc(&self, id: Option<&str>, text: &str, cfg: &Config)
        -> Result<(Vec<Span>, Vec<Span>), String>
    {
        let i = match id {
            // Eval always names the document; text is only a consistency
            // check so a stale or reordered file fails loudly.
            Some(id) => match self.by_id.get(id).copied() {
                Some(i) if self.entries[i].text == text => i,
                Some(_) => {
                    return Err(format!(
                        "predictions: id {id:?} matched but the text differs; \
                         the file is out of order or belongs to another dataset"
                    ))
                }
                None => {
                    return Err(format!(
                        "no prediction for id {id:?} — the file needs one line per benchmark document"
                    ))
                }
            },
            // Scrub and other callers without an id fall back to exact text.
            None => match self.by_text.get(text) {
                Some(&i) => i,
                None => {
                    return Err(format!(
                        "no prediction for text {:?} — the file needs one line per benchmark document",
                        text.chars().take(40).collect::<String>()
                    ))
                }
            },
        };
        let mut hits = Vec::new();
        for p in &self.entries[i].spans {
            let cat = match map_label(&p.label) {
                Mapped::Phi(c) => c,
                Mapped::Quasi => Category::Org,
                Mapped::Keep => continue,
            };
            if cat == Category::Org && !cfg.strict {
                continue;
            }
            let (a, b) = (char_to_byte(text, p.start), char_to_byte(text, p.end));
            if a >= b {
                continue;
            }
            if let Some(s) = tidy(text, Span::new(a, b, cat, Source::Model, 1.0)) {
                hits.push(s);
            }
        }
        Ok((hits, Vec::new()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn load(lines: &str) -> PrecomputedDetector {
        let p = std::env::temp_dir().join(format!("scotoma-preds-{}-{}.jsonl",
            std::process::id(), lines.len()));
        std::fs::write(&p, lines).unwrap();
        PrecomputedDetector::load(&p).unwrap()
    }

    #[test]
    fn finds_by_id_and_text_and_fails_closed() {
        let d = load(concat!(
            "{\"id\":\"d1\",\"text\":\"Patient Ana Costa called.\",",
            "\"spans\":[{\"start\":8,\"end\":17,\"label\":\"NAME\"}]}\n",
            "{\"id\":null,\"text\":\"No identifiers here.\",\"spans\":[]}\n",
        ));
        let cfg = Config::default();
        let (hits, maybe) = d.detect_doc(Some("d1"), "Patient Ana Costa called.", &cfg).unwrap();
        assert!(maybe.is_empty());
        assert_eq!(hits.len(), 1);
        assert_eq!((hits[0].start, hits[0].end, hits[0].category), (8, 17, Category::Name));
        // A row without an id is keyed doc<lineno>, like eval's docs.
        assert!(d.detect_doc(Some("doc2"), "No identifiers here.", &cfg).unwrap().0.is_empty());
        // A caller that can't name the doc (scrub) falls back to exact text.
        assert!(d.detect_doc(None, "No identifiers here.", &cfg).unwrap().0.is_empty());
        // No prediction at all is an error, not a silent zero.
        assert!(d.detect_doc(None, "Unknown document.", &cfg).is_err());
        // Id present but absent from the file is an error even when another
        // row's text matches — id is the key, text is only a check.
        assert!(d.detect_doc(Some("zzz"), "No identifiers here.", &cfg).is_err());
        // Id matches but the text doesn't: the file is stale -> error.
        assert!(d.detect_doc(Some("d1"), "Tampered text.", &cfg).is_err());
    }

    #[test]
    fn quasi_only_in_strict_and_keep_dropped() {
        let d = load(concat!(
            "{\"id\":\"d\",\"text\":\"Acme Corp hired a nurse.\",\"spans\":[",
            "{\"start\":0,\"end\":9,\"label\":\"company_name\"},",
            "{\"start\":18,\"end\":23,\"label\":\"occupation\"},",
            "{\"start\":0,\"end\":4,\"label\":\"state\"}]}\n",
        ));
        let mut cfg = Config::default();
        let t = "Acme Corp hired a nurse.";
        assert!(d.detect_doc(Some("d"), t, &cfg).unwrap().0.is_empty());
        cfg.strict = true;
        let (hits, _) = d.detect_doc(Some("d"), t, &cfg).unwrap();
        assert_eq!(hits.len(), 2);
        assert!(hits.iter().all(|h| h.category == Category::Org));
    }
}
