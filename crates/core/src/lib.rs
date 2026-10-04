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

    pub fn detect(&self, text: &str) -> Result<Detection, String> {
        let (mut spans, mut possible) = if self.config.use_rules {
            (rules::detect(text), rules::suspicious(text))
        } else {
            (Vec::new(), Vec::new())
        };
        if let Some(m) = &self.model {
            let (hit, maybe) = m.detect(text, &self.config)?;
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

/// Char offset → byte offset (datasets annotate in chars).
pub fn char_to_byte(text: &str, pos: usize) -> usize {
    text.char_indices().nth(pos).map(|(b, _)| b).unwrap_or(text.len())
}
