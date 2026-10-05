//! Neural detector: any Hugging Face token-classification model exported to
//! ONNX. Point it at a folder holding `model*.onnx`, `tokenizer.json` and
//! `config.json` (for `id2label`); the label vocabulary is mapped by keyword.
//!
//! Long inputs are processed in overlapping windows and the per-token
//! probabilities averaged, so nothing is truncated.

use crate::labels::{map_label, Mapped};
use crate::{tidy, Category, Config, Detector, Source, Span};
use ort::session::{builder::GraphOptimizationLevel, Session};
use ort::value::Tensor;
use std::path::{Path, PathBuf};
use parking_lot::Mutex;
use tokenizers::Tokenizer;

pub struct OnnxDetector {
    session: Mutex<Session>,
    tokenizer: Tokenizer,
    /// Per output class: what it means to us.
    classes: Vec<Mapped>,
    prefix: Vec<i64>,
    suffix: Vec<i64>,
    inputs: Vec<String>,
    window: usize,
    stride: usize,
    name: String,
    /// `scotoma_threshold` from config.json: the model's recommended default.
    suggested: Option<f32>,
    /// Optional per-text probability cache (benchmarks that score several
    /// configurations of one model over the same documents run inference once).
    cache: Option<Mutex<std::collections::HashMap<Vec<u32>, std::sync::Arc<Vec<f32>>>>>,
}

const CANDIDATES: &[&str] = &[
    "model_quantized.onnx", "model_int8.onnx", "model_q8.onnx", "model.onnx",
    "onnx/model_quantized.onnx", "onnx/model_int8.onnx", "onnx/model_q8.onnx", "onnx/model.onnx",
];

fn find(dir: &Path, names: &[&str]) -> Option<PathBuf> {
    names.iter().map(|n| dir.join(n)).find(|p| p.is_file())
}

impl OnnxDetector {
    pub fn load(dir: &Path) -> Result<Self, String> {
        let model_path = find(dir, CANDIDATES).ok_or_else(|| format!("no model*.onnx in {}", dir.display()))?;
        let tok_path = find(dir, &["tokenizer.json"]).ok_or("tokenizer.json not found")?;
        let cfg_path = find(dir, &["config.json"]).ok_or("config.json not found")?;

        let cfg: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(&cfg_path).map_err(|e| e.to_string())?)
            .map_err(|e| format!("config.json: {e}"))?;
        let id2label = cfg.get("id2label").and_then(|v| v.as_object()).ok_or("config.json has no id2label")?;
        let mut classes = vec![Mapped::Keep; id2label.len()];
        for (k, v) in id2label {
            let i: usize = k.parse().map_err(|_| format!("bad id2label key {k}"))?;
            if i >= classes.len() { return Err(format!("id2label index {i} out of range")); }
            classes[i] = map_label(v.as_str().unwrap_or("O"));
        }
        if !classes.iter().any(|c| matches!(c, Mapped::Phi(_))) {
            return Err("none of the model's labels map to an identifier category".into());
        }

        let mut tokenizer = Tokenizer::from_file(&tok_path).map_err(|e| format!("tokenizer.json: {e}"))?;
        tokenizer.with_padding(None);
        tokenizer.with_truncation(None).map_err(|e| e.to_string())?;
        let probe = tokenizer.encode("a", true).map_err(|e| e.to_string())?;
        let mask = probe.get_special_tokens_mask();
        let ids = probe.get_ids();
        let lead = mask.iter().take_while(|&&m| m == 1).count();
        let trail = mask.iter().rev().take_while(|&&m| m == 1).count();
        let prefix: Vec<i64> = ids[..lead].iter().map(|&x| x as i64).collect();
        let suffix: Vec<i64> = ids[ids.len() - trail..].iter().map(|&x| x as i64).collect();

        let threads = std::env::var("SCOTOMA_THREADS").ok().and_then(|v| v.parse().ok())
            .unwrap_or_else(|| std::thread::available_parallelism().map(|n| n.get().min(4)).unwrap_or(2));
        let mut builder = Session::builder().map_err(|e| e.to_string())?
            .with_optimization_level(GraphOptimizationLevel::Level3).map_err(|e| e.to_string())?
            .with_intra_threads(threads).map_err(|e| e.to_string())?;
        let session = builder.commit_from_file(&model_path)
            .map_err(|e| format!("{}: {e}", model_path.display()))?;
        let inputs: Vec<String> = session.inputs().iter().map(|i| i.name().to_string()).collect();

        let max_pos = cfg.get("max_position_embeddings").and_then(|v| v.as_u64()).unwrap_or(512) as usize;
        let window = max_pos.min(384).max(16) - prefix.len() - suffix.len();
        let name = cfg.get("_name_or_path").and_then(|v| v.as_str()).filter(|s| !s.is_empty())
            .map(|s| s.to_string())
            .unwrap_or_else(|| dir.file_name().map(|s| s.to_string_lossy().into_owned()).unwrap_or_else(|| "model".into()));
        let suggested = crate::cfg_threshold(&cfg);
        Ok(OnnxDetector { session: Mutex::new(session), tokenizer, classes, prefix, suffix, inputs, window, stride: window / 6, name, suggested,
            cache: std::env::var("SCOTOMA_PROB_CACHE").ok().filter(|v| v == "1").map(|_| Mutex::new(Default::default())) })
    }

    /// Returns per-token class probabilities (row-major, tokens × classes).
    fn infer(&self, ids: &[u32]) -> Result<Vec<f32>, String> {
        let c = self.classes.len();
        let n = ids.len();
        let mut sum = vec![0f32; n * c];
        let mut cnt = vec![0f32; n];
        let step = self.window - self.stride;
        let mut start = 0;
        let mut session = self.session.lock();
        loop {
            let end = (start + self.window).min(n);
            let mut input: Vec<i64> = self.prefix.clone();
            input.extend(ids[start..end].iter().map(|&x| x as i64));
            input.extend(&self.suffix);
            let len = input.len();
            let mut feed: Vec<(String, Tensor<i64>)> = Vec::new();
            for name in &self.inputs {
                let data = match name.as_str() {
                    "input_ids" => input.clone(),
                    "attention_mask" => vec![1i64; len],
                    "token_type_ids" => vec![0i64; len],
                    other => return Err(format!("model wants unknown input {other:?}")),
                };
                feed.push((name.clone(), Tensor::from_array(([1usize, len], data)).map_err(|e| e.to_string())?));
            }
            let outputs = session.run(feed).map_err(|e| e.to_string())?;
            let (shape, logits) = outputs[0].try_extract_tensor::<f32>().map_err(|e| e.to_string())?;
            if shape.len() != 3 || shape[1] as usize != len || shape[2] as usize != c {
                return Err(format!("unexpected logits shape {shape:?}, wanted [1, {len}, {c}]"));
            }
            for t in 0..(end - start) {
                let row = &logits[(t + self.prefix.len()) * c..(t + self.prefix.len() + 1) * c];
                let max = row.iter().cloned().fold(f32::MIN, f32::max);
                let z: f32 = row.iter().map(|&x| (x - max).exp()).sum();
                // Tokens near a window edge have less context: weight them down.
                let edge = t.min(end - start - 1 - t) as f32;
                let w = if n > self.window { 1.0 + edge.min(self.stride as f32) } else { 1.0 };
                for k in 0..c {
                    sum[(start + t) * c + k] += w * (row[k] - max).exp() / z;
                }
                cnt[start + t] += w;
            }
            if end == n { break; }
            start += step;
        }
        for t in 0..n {
            for k in 0..c { sum[t * c + k] /= cnt[t]; }
        }
        Ok(sum)
    }
}

fn glue(gap: &str) -> bool {
    gap.len() <= 2 && gap.chars().all(|ch| ch.is_whitespace() || "-'’.,/@:_".contains(ch))
}

impl Detector for OnnxDetector {
    fn name(&self) -> String { self.name.clone() }

    fn suggested_threshold(&self) -> Option<f32> { self.suggested }
    fn detect(&self, text: &str, cfg: &Config) -> Result<(Vec<Span>, Vec<Span>), String> {
        if text.trim().is_empty() { return Ok((Vec::new(), Vec::new())); }
        let enc = self.tokenizer.encode(text, false).map_err(|e| e.to_string())?;
        let ids = enc.get_ids();
        let offsets = enc.get_offsets();
        if ids.is_empty() { return Ok((Vec::new(), Vec::new())); }
        let probs: std::sync::Arc<Vec<f32>> = match &self.cache {
            Some(c) => {
                if let Some(p) = c.lock().get(ids) { p.clone() } else {
                    let p = std::sync::Arc::new(self.infer(ids)?);
                    c.lock().insert(ids.to_vec(), p.clone());
                    p
                }
            }
            None => std::sync::Arc::new(self.infer(ids)?),
        };
        let c = self.classes.len();

        // Per token: probability it is an identifier at all, and which kind.
        // Summing over B-/I- variants of a category is what makes a
        // recall-leaning threshold possible; argmax throws that mass away.
        let mut hits: Vec<Span> = Vec::new();
        let mut maybes: Vec<Span> = Vec::new();
        let mut cur: Option<(Span, f32, u32, bool)> = None;
        let flush = |cur: &mut Option<(Span, f32, u32, bool)>, hits: &mut Vec<Span>, maybes: &mut Vec<Span>| {
            if let Some((mut s, total, k, hit)) = cur.take() {
                s.confidence = total / k as f32;
                if hit { hits.push(s) } else { maybes.push(s) }
            }
        };
        for (t, &(a, b)) in offsets.iter().enumerate() {
            if a >= b || b > text.len() { continue; }
            let row = &probs[t * c..(t + 1) * c];
            let mut by_cat: Vec<(Category, f32)> = Vec::new();
            let mut ent = 0f32;
            for (k, &p) in row.iter().enumerate() {
                let cat = match self.classes[k] {
                    Mapped::Phi(cat) => cat,
                    Mapped::Quasi => Category::Org,
                    Mapped::Keep => continue,
                };
                if cat == Category::Org && !cfg.strict { continue; }
                ent += p;
                match by_cat.iter_mut().find(|(x, _)| *x == cat) {
                    Some(e) => e.1 += p,
                    None => by_cat.push((cat, p)),
                }
            }
            let hit = ent >= cfg.threshold;
            if !hit && ent < cfg.floor { flush(&mut cur, &mut hits, &mut maybes); continue; }
            let cat = by_cat.iter().cloned().fold((Category::Id, -1.0), |m, x| if x.1 > m.1 { x } else { m }).0;
            match &mut cur {
                Some((s, total, k, h)) if *h == hit && s.category == cat && a >= s.end && text.is_char_boundary(a) && glue(&text[s.end..a]) => {
                    s.end = b;
                    *total += ent;
                    *k += 1;
                }
                _ => {
                    flush(&mut cur, &mut hits, &mut maybes);
                    cur = Some((Span::new(a, b, cat, Source::Model, ent), ent, 1, hit));
                }
            }
        }
        flush(&mut cur, &mut hits, &mut maybes);

        // Tidy edges: trim whitespace, then grow to whole words so a sub-word
        // hit can never leave half a surname behind. Shared with the
        // precomputed-span replayer via crate::tidy.
        let fix = |s: Span| tidy(text, s);
        Ok((hits.into_iter().filter_map(fix).collect(), maybes.into_iter().filter_map(fix).collect()))
    }
}
