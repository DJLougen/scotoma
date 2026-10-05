//! scotoma-core: find identifiers in text, replace them, and put them back.
//!
//! Pipeline: rules (deterministic, structured identifiers) ∪ model (names,
//! addresses, free-form identifiers) → merge → name propagation → render.
//! Nothing in this crate opens a socket or writes the text to disk.

pub mod eval;
pub mod labels;
pub mod merge;
#[cfg(feature = "onnx")]
pub mod model;
pub mod precomputed;
pub mod rules;
pub mod transform;

use serde::{Deserialize, Serialize};

/// HIPAA Safe Harbor identifier classes (45 CFR 164.514(b)(2)), plus ORG which
/// is only redacted in strict mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Category {
    Name,
    Address,
    Location,
    Zip,
    Date,
    Age,
    Phone,
    Fax,
    Email,
    Ssn,
    Mrn,
    Plan,
    Account,
    License,
    Vehicle,
    Device,
    Url,
    Ip,
    Biometric,
    Id,
    Org,
}

impl Category {
    pub const ALL: [Category; 21] = [
        Category::Name, Category::Address, Category::Location, Category::Zip,
        Category::Date, Category::Age, Category::Phone, Category::Fax,
        Category::Email, Category::Ssn, Category::Mrn, Category::Plan,
        Category::Account, Category::License, Category::Vehicle, Category::Device,
        Category::Url, Category::Ip, Category::Biometric, Category::Id, Category::Org,
    ];

    pub fn tag(self) -> &'static str {
        match self {
            Category::Name => "NAME",
            Category::Address => "ADDRESS",
            Category::Location => "LOCATION",
            Category::Zip => "ZIP",
            Category::Date => "DATE",
            Category::Age => "AGE",
            Category::Phone => "PHONE",
            Category::Fax => "FAX",
            Category::Email => "EMAIL",
            Category::Ssn => "SSN",
            Category::Mrn => "MRN",
            Category::Plan => "PLAN",
            Category::Account => "ACCOUNT",
            Category::License => "LICENSE",
            Category::Vehicle => "VEHICLE",
            Category::Device => "DEVICE",
            Category::Url => "URL",
            Category::Ip => "IP",
            Category::Biometric => "BIOMETRIC",
            Category::Id => "ID",
            Category::Org => "ORG",
        }
    }

    pub fn from_tag(s: &str) -> Option<Category> {
        let up = s.to_ascii_uppercase();
        Category::ALL.iter().copied().find(|c| c.tag() == up)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Source {
    Rule,
    Model,
    /// A name found once, then matched again elsewhere in the same text.
    Propagated,
    /// Added by the person in the review window.
    Manual,
}

/// A detected identifier. `start..end` are byte offsets into the input.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Span {
    pub start: usize,
    pub end: usize,
    pub category: Category,
    pub source: Source,
    pub confidence: f32,
    /// Date of birth: the year is dropped too when it implies an age over 89.
    #[serde(default)]
    pub dob: bool,
}

impl Span {
    pub fn new(start: usize, end: usize, category: Category, source: Source, confidence: f32) -> Self {
        Span { start, end, category, source, confidence, dob: false }
    }
    pub fn overlaps(&self, o: &Span) -> bool {
        self.start < o.end && o.start < self.end
    }
}

/// Anything that can find spans in text. The ONNX model implements this; so
/// can a test double.
pub trait Detector: Send + Sync {
    fn name(&self) -> String;
    /// Returns (confident spans, sub-threshold candidates).
    fn detect(&self, text: &str, cfg: &Config) -> Result<(Vec<Span>, Vec<Span>), String>;
    /// Like detect, but names the benchmark document being scored so
    /// detectors that look spans up by id (PrecomputedDetector) can key by
    /// it. Keeps the id inside the call — no shared state to race on.
    fn detect_doc(&self, _id: Option<&str>, text: &str, cfg: &Config) -> Result<(Vec<Span>, Vec<Span>), String> {
        self.detect(text, cfg)
    }
    /// Redaction probability the model's config.json recommends
    /// (`scotoma_threshold`). Callers honour it unless the user picked one.
    fn suggested_threshold(&self) -> Option<f32> {
        None
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Config {
    /// Model probability above which a token is redacted. Lower = more recall.
    pub threshold: f32,
    /// Model probability above which a token is shown as "possible" in review.
    pub floor: f32,
    /// Also redact organisations and quasi-identifiers the model reports
    /// (occupation, nationality, ...). Off by default to keep clinical meaning.
    pub strict: bool,
    /// Re-find every detected name elsewhere in the text.
    pub propagate_names: bool,
    /// Run the deterministic rules. Off only when benchmarking a model alone.
    pub use_rules: bool,
}

impl Default for Config {
    fn default() -> Self {
        Config { threshold: 0.35, floor: 0.08, strict: false, propagate_names: true, use_rules: true }
    }
}

/// A model can ship its operating point: `"scotoma_threshold": 0.02` in its
/// `config.json` (usually alongside `"scotoma_domain": "clinical"`). This reads
/// that key from a model directory without loading the ONNX graph.
pub fn model_default_threshold(dir: &std::path::Path) -> Option<f32> {
    let cfg: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(dir.join("config.json")).ok()?).ok()?;
    cfg_threshold(&cfg)
}

/// Extract a sane (0, 1) `scotoma_threshold` from a parsed config.json.
pub(crate) fn cfg_threshold(cfg: &serde_json::Value) -> Option<f32> {
    let t = cfg.get("scotoma_threshold")?.as_f64()? as f32;
    (t > 0.0 && t < 1.0).then_some(t)
}

/// Which redaction threshold applies: the user's explicit choice wins, then
/// the model's declared default, then the built-in default.
pub fn effective_threshold(user: Option<f32>, model: Option<f32>) -> f32 {
    user.or(model).unwrap_or_else(|| Config::default().threshold)
}

impl Config {
    /// Set the redaction threshold; `floor` can never sit above it, since
    /// floor marks sub-threshold candidates for review.
    pub fn set_threshold(&mut self, t: f32) {
        self.threshold = t;
        self.floor = self.floor.min(t);
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Detection {
    /// Non-overlapping, sorted. These get redacted.
    pub spans: Vec<Span>,
    /// Sorted, never overlapping `spans`. Shown for review, not redacted.
    pub possible: Vec<Span>,
}

pub struct Scrubber {
    pub config: Config,
    model: Option<Box<dyn Detector>>,
}

impl Scrubber {
    pub fn rules_only(config: Config) -> Self {
        Scrubber { config, model: None }
    }
    pub fn with_model(config: Config, model: Box<dyn Detector>) -> Self {
        Scrubber { config, model: Some(model) }
    }
    pub fn set_model(&mut self, model: Option<Box<dyn Detector>>) {
        self.model = model;
    }
    pub fn model_name(&self) -> Option<String> {
        self.model.as_ref().map(|m| m.name())
    }
    /// Scores a benchmark document: detectors that serve precomputed spans
    /// get the document id, so they can key by it instead of text.
    pub fn detect_doc(&self, id: &str, text: &str) -> Result<Detection, String> {
        self.detect_with(if id.is_empty() { None } else { Some(id) }, text)
    }

    pub fn detect(&self, text: &str) -> Result<Detection, String> {
        self.detect_with(None, text)
    }

    fn detect_with(&self, id: Option<&str>, text: &str) -> Result<Detection, String> {
        let (mut spans, mut possible) = if self.config.use_rules {
            (rules::detect(text), rules::suspicious(text))
        } else {
            (Vec::new(), Vec::new())
        };
        if let Some(m) = &self.model {
            let (hit, maybe) = m.detect_doc(id, text, &self.config)?;
            spans.extend(hit);
            possible.extend(maybe);
        }
        if !self.config.strict {
            spans.retain(|s| s.category != Category::Org);
            possible.retain(|s| s.category != Category::Org);
        }
        let mut spans = merge::merge(text, spans);
        if self.config.propagate_names && self.config.use_rules {
            let extra = rules::propagate_names(text, &spans);
            if !extra.is_empty() {
                spans.extend(extra);
                spans = merge::merge(text, spans);
            }
        }
        let possible = merge::subtract(merge::merge(text, possible), &spans);
        Ok(Detection { spans, possible })
    }

    /// The redaction threshold the loaded model recommends, if any.
    pub fn model_suggested_threshold(&self) -> Option<f32> {
        self.model.as_ref().and_then(|m| m.suggested_threshold())
    }
}

pub(crate) fn current_year() -> i32 {
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    1970 + (secs / 31_556_952) as i32
}

/// UTF-16 code unit offset → byte offset (the review UI speaks UTF-16).
pub fn utf16_to_byte(text: &str, pos16: usize) -> usize {
    let mut u = 0;
    for (b, ch) in text.char_indices() {
        if u >= pos16 {
            return b;
        }
        u += ch.len_utf16();
    }
    text.len()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn model_declared_threshold_becomes_default() {
        let dir = std::env::temp_dir().join(format!("scotoma-cfg-threshold-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();

        // A config.json carrying scotoma_threshold advertises it.
        std::fs::write(dir.join("config.json"),
            r#"{"id2label": {"0": "O"}, "scotoma_threshold": 0.02, "scotoma_domain": "clinical"}"#).unwrap();
        assert_eq!(model_default_threshold(&dir), Some(0.02));

        // A config without the key (or without a config at all) stays on the
        // built-in default.
        let bare = dir.join("bare");
        std::fs::create_dir_all(&bare).unwrap();
        std::fs::write(bare.join("config.json"), r#"{"id2label": {"0": "O"}}"#).unwrap();
        assert_eq!(model_default_threshold(&bare), None);
        assert_eq!(model_default_threshold(&dir.join("missing")), None);

        // Priority: explicit user/CLI threshold > model default > Config::default().
        let model = model_default_threshold(&dir);
        assert_eq!(effective_threshold(None, model), 0.02);
        assert_eq!(effective_threshold(Some(0.35), model), 0.35);
        assert_eq!(effective_threshold(None, None), Config::default().threshold);

        // set_threshold keeps the review floor below the redaction line.
        let mut c = Config::default();
        c.set_threshold(effective_threshold(None, model));
        assert_eq!(c.threshold, 0.02);
        assert!(c.floor <= c.threshold);

        let _ = std::fs::remove_dir_all(&dir);
    }
}

/// Char offset → byte offset (datasets annotate in chars).
pub fn char_to_byte(text: &str, pos: usize) -> usize {
    text.char_indices().nth(pos).map(|(b, _)| b).unwrap_or(text.len())
}

/// Tidy a raw span's edges: snap to UTF-8 boundaries, trim whitespace, grow
/// to whole words so a partial hit never leaves half a surname behind, and
/// drop spans that aren't identifiers (bare honorifics, ages under 90).
/// Used by both the ONNX model and the precomputed-span replayer so external
/// systems get the same post-processing as ours.
pub fn tidy(text: &str, mut s: Span) -> Option<Span> {
    while !text.is_char_boundary(s.start) { s.start -= 1; }
    while !text.is_char_boundary(s.end) { s.end += 1; }
    let raw = &text[s.start..s.end];
    let lead = raw.len() - raw.trim_start().len();
    let trail = raw.len() - raw.trim_end().len();
    s.start += lead;
    s.end -= trail;
    if s.start >= s.end { return None; }
    while let Some(ch) = text[..s.start].chars().next_back() {
        if ch.is_alphanumeric() { s.start -= ch.len_utf8(); } else { break; }
    }
    while let Some(ch) = text[s.end..].chars().next() {
        if ch.is_alphanumeric() { s.end += ch.len_utf8(); } else { break; }
    }
    // An honorific on its own ("Dr", "Mrs") identifies nobody; some models
    // tag it as an occupation, which strict mode would then redact.
    let bare = text[s.start..s.end].trim_matches(|c: char| !c.is_alphanumeric()).to_lowercase();
    if matches!(bare.as_str(), "dr" | "mr" | "mrs" | "ms" | "miss" | "mx" | "prof" | "doctor" | "sir" | "madam") {
        return None;
    }
    // An age is only an identifier above 89.
    if s.category == Category::Age {
        let n: String = text[s.start..s.end].chars().filter(|c| c.is_ascii_digit()).collect();
        if n.parse::<u32>().map(|n| n < 90).unwrap_or(true) { return None; }
    }
    Some(s)
}
