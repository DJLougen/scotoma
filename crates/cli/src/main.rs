//! scotoma — scrub text on stdin, or benchmark the pipeline.
//!
//!   scotoma scrub  [--model DIR] [--surrogate] [--strict] [--threshold P] [--json] < note.txt
//!   scotoma eval   DATA.jsonl [--model DIR | --predictions PREDS.jsonl] [--strict] [--threshold P] [--limit N] [--misses N] [--json]
//!   scotoma sweep  DATA.jsonl --model DIR [--limit N] [--thresholds 0.02,0.05,...] [--json]
//!   scotoma convert IN.jsonl OUT.jsonl                # map any label set to Scotoma categories
//!   scotoma redact-file IN.(png|jpg|tiff|pdf) OUT [--model DIR] [--threshold P] [--json]   # macOS: black-box identifiers in a scan
//!
//! eval also takes: --no-rules (score the model alone), --responses FILE.csv (per-item outcomes).
//! --predictions replays spans written by bench/predict_external.py (one JSONL line per
//! document: {"id", "text", "spans":[{start,end,label}]}, char offsets); a missing document
//! is an error. sweep --json prints [{"threshold","recall","full","chars","precision","leak_docs",
//! "over_redaction"}, ...] and the text table gains an over-redaction column.

use scotoma_core::transform::{render, Mode, Vault};
use scotoma_core::{eval, Config, Detector, Scrubber};
use std::io::Read;

fn engine_name(sc: &Scrubber) -> String {
    match (sc.config.use_rules, sc.model_name()) {
        (true, Some(m)) => format!("rules + {m}"),
        (true, None) => "rules".into(),
        (false, Some(m)) => m,
        (false, None) => "nothing (no rules, no model)".into(),
    }
}

struct Args {
    cmd: String,
    path: Option<String>,
    model: Option<String>,
    surrogate: bool,
    json: bool,
    limit: Option<usize>,
    misses: usize,
    cfg: Config,
    /// Whether --threshold was passed; if not, a model's scotoma_threshold wins.
    threshold_set: bool,
    path2: Option<String>,
    responses: Option<String>,
    out_dir: Option<String>,
    configs: Vec<String>,
    predictions: Option<String>,
    thresholds: Option<Vec<f32>>,
}

fn parse() -> Result<Args, String> {
    let mut it = std::env::args().skip(1);
    let cmd = it.next().ok_or("usage: scotoma <scrub|eval|sweep> [options]")?;
    let mut a = Args { cmd, path: None, model: std::env::var("SCOTOMA_MODEL").ok(), surrogate: false, json: false, limit: None, misses: 25, cfg: Config::default(), threshold_set: false, path2: None, responses: None, out_dir: None, configs: Vec::new(), predictions: None, thresholds: None };
    while let Some(x) = it.next() {
        let mut val = |n: &str| it.next().ok_or(format!("{n} needs a value"));
        match x.as_str() {
            "--model" => a.model = Some(val("--model")?),
            "--no-model" => a.model = None,
            "--surrogate" => a.surrogate = true,
            "--strict" => a.cfg.strict = true,
            "--no-rules" => a.cfg.use_rules = false,
            "--responses" => a.responses = Some(val("--responses")?),
            "--out-dir" => a.out_dir = Some(val("--out-dir")?),
            "--config" => a.configs.push(val("--config")?),
            "--json" => a.json = true,
            "--threshold" => { a.cfg.threshold = val("--threshold")?.parse().map_err(|_| "bad --threshold")?; a.threshold_set = true; }
            "--limit" => a.limit = Some(val("--limit")?.parse().map_err(|_| "bad --limit")?),
            "--misses" => a.misses = val("--misses")?.parse().map_err(|_| "bad --misses")?,
            "--predictions" => a.predictions = Some(val("--predictions")?),
            "--thresholds" => a.thresholds = Some(val("--thresholds")?.split(',')
                .map(|t| t.trim().parse::<f32>().map_err(|_| "bad --thresholds".to_string()))
                .collect::<Result<Vec<f32>, String>>()?),
            s if !s.starts_with("--") && a.path.is_none() => a.path = Some(s.to_string()),
            s if !s.starts_with("--") && a.path2.is_none() => a.path2 = Some(s.to_string()),
            s => return Err(format!("unknown option {s}")),
        }
    }
    Ok(a)
}

fn scrubber(a: &mut Args) -> Result<Scrubber, String> {
    let mut sc = Scrubber::rules_only(a.cfg.clone());
    if a.model.is_some() && a.predictions.is_some() {
        return Err("use --model or --predictions, not both".into());
    }
    if let Some(dir) = &a.model {
        #[cfg(feature = "onnx")]
        {
            let det = scotoma_core::model::OnnxDetector::load(std::path::Path::new(dir))?;
            // An explicit --threshold beats the model's declared default.
            let user = a.threshold_set.then_some(a.cfg.threshold);
            a.cfg.set_threshold(scotoma_core::effective_threshold(user, det.suggested_threshold()));
            sc.set_model(Some(Box::new(det)));
            sc.config = a.cfg.clone();
        }
        #[cfg(not(feature = "onnx"))]
        return Err(format!("built without the onnx feature; cannot load {dir}"));
    }
    if let Some(p) = &a.predictions {
        let det = scotoma_core::precomputed::PrecomputedDetector::load(std::path::Path::new(p))?;
        sc.set_model(Some(Box::new(det)));
    }
    Ok(sc)
}
fn load(a: &Args) -> Result<Vec<eval::GoldDoc>, String> {
    let path = a.path.as_ref().ok_or("need a .jsonl path")?;
    let src = std::fs::read_to_string(path).map_err(|e| format!("{path}: {e}"))?;
    let mut docs = eval::parse_jsonl(&src)?;
    if let Some(n) = a.limit { docs.truncate(n); }
    Ok(docs)
}

fn run() -> Result<(), String> {
    let mut a = parse()?;
    match a.cmd.as_str() {
        "scrub" => {
            let sc = scrubber(&mut a)?;
            let mut text = String::new();
            std::io::stdin().read_to_string(&mut text).map_err(|e| e.to_string())?;
            let det = sc.detect(&text)?;
            let mut vault = Vault::new();
            let out = render(&text, &det.spans, if a.surrogate { Mode::Surrogate } else { Mode::Tag }, &mut vault);
            if a.json {
                println!("{}", serde_json::json!({ "text": out.text, "items": out.items, "possible": det.possible, "threshold": sc.config.threshold }));
            } else {
                print!("{}", out.text);
                eprintln!("\n— {} replaced, {} possible, engine: {} · threshold {}",
                    out.items.len(), det.possible.len(), engine_name(&sc), sc.config.threshold);
            }
        }
        "redact-file" => {
            // Image/PDF in → OCR word boxes → detected spans → black boxes out.
            // macOS only (Vision/PDFKit live in the helper); the output is a PNG
            // for a single-page image or an image-only PDF otherwise.
            #[cfg(not(target_os = "macos"))]
            return Err("redact-file is macOS-only: it needs the Vision/PDFKit helper".into());
            #[cfg(target_os = "macos")]
            {
                let input = a.path.clone().ok_or("redact-file needs IN OUT")?;
                let out = a.path2.clone().ok_or("redact-file needs IN OUT")?;
                let sc = scrubber(&mut a)?;
                let report = scotoma_core::redact::redact_document(
                    &sc,
                    std::path::Path::new(&input),
                    std::path::Path::new(&out),
                    None,
                )?;
                if a.json {
                    // Span offsets are within the OCR'd page text; the text
                    // itself (and anything it matched) is never printed.
                    println!("{}", serde_json::json!({
                        "words": report.words,
                        "counts": report.counts,
                        "boxes": report.boxes,
                        "spans": report.spans,
                    }));
                } else {
                    let counts = report.counts.iter().map(|(k, v)| format!("{k}×{v}")).collect::<Vec<_>>().join(" ");
                    println!("{} words OCR'd, {} identifiers ({}), {} boxes painted → {}",
                        report.words, report.spans.len(), counts, report.boxes, out);
                }
            }
        }
        "eval" => {
            let sc = scrubber(&mut a)?;
            let docs = load(&a)?;
            let r = eval::evaluate(&sc, &docs, a.misses)?;
            if let Some(path) = &a.responses {
                let mut csv = String::from("item,outcome\n");
                for (id, o) in &r.responses { csv.push_str(&format!("{id},{o}\n")); }
                std::fs::write(path, csv).map_err(|e| format!("{path}: {e}"))?;
            }
            if a.json {
                println!("{}", serde_json::to_string_pretty(&r).map_err(|e| e.to_string())?);
            } else {
                println!("engine: {} · threshold {} · strict {}\n", engine_name(&sc), sc.config.threshold, sc.config.strict);
                print!("{}", eval::format_report(&r));
                if !r.misses.is_empty() {
                    println!("\nmisses (first {}):", r.misses.len());
                    for m in &r.misses {
                        println!("  {:<9} {} {}", m.category.tag(), if m.partial { "partial" } else { "MISSED " }, m.context);
                    }
                }
            }
        }
        "evalmany" => {
            // evalmany DATA --model DIR --out-dir D --config NAME:THRESHOLD:rules|norules ...
            // Scores several configurations of one model over the same data with a single
            // inference pass (SCOTOMA_PROB_CACHE=1 is set automatically). Writes D/NAME.json
            // (same as `eval --json`) and D/NAME.csv (same as --responses).
            std::env::set_var("SCOTOMA_PROB_CACHE", "1");
            let out = a.out_dir.clone().ok_or("evalmany needs --out-dir")?;
            std::fs::create_dir_all(&out).map_err(|e| e.to_string())?;
            let mut sc = scrubber(&mut a)?;
            let docs = load(&a)?;
            for spec in a.configs.clone() {
                let parts: Vec<&str> = spec.split(':').collect();
                if parts.len() != 3 { return Err(format!("bad --config {spec}")); }
                let th: f32 = parts[1].parse().map_err(|_| format!("bad threshold in {spec}"))?;
                sc.config.set_threshold(th);
                sc.config.use_rules = match parts[2] { "rules" => true, "norules" => false, x => return Err(format!("bad rules flag {x}")) };
                let r = eval::evaluate(&sc, &docs, 0)?;
                let mut csv = String::from("item,outcome\n");
                for (id, o) in &r.responses { csv.push_str(&format!("{id},{o}\n")); }
                std::fs::write(format!("{out}/{}.csv", parts[0]), csv).map_err(|e| e.to_string())?;
                std::fs::write(format!("{out}/{}.json", parts[0]), serde_json::to_string_pretty(&r).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
                eprintln!("{}: {} docs, {} with a leak", parts[0], r.docs, r.docs_with_leak);
            }
        }
        "sweep" => {
            let mut sc = scrubber(&mut a)?;
            let docs = load(&a)?;
            let model_default = sc.model_suggested_threshold();
            let mut thresholds = a.thresholds.clone()
                .unwrap_or_else(|| vec![0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.9]);
            if let Some(t) = model_default {
                if !thresholds.iter().any(|&x| x == t) { thresholds.insert(0, t); }
            }
            thresholds.sort_by(|x, y| x.partial_cmp(y).unwrap_or(std::cmp::Ordering::Equal));
            thresholds.dedup();
            let frac = |x: f64| if x.is_nan() { serde_json::Value::Null } else { serde_json::json!(x) };
            let mut rows = Vec::new();
            if !a.json {
                println!("engine: {} · model default threshold {}", engine_name(&sc),
                    model_default.map(|t| t.to_string()).unwrap_or_else(|| "none".into()));
                println!("{:>9} {:>8} {:>8} {:>8} {:>10} {:>8}", "threshold", "recall", "full", "prec", "leak docs", "over-red");
            }
            for th in thresholds {
                sc.config.set_threshold(th);
                let r = eval::evaluate(&sc, &docs, 0)?;
                if a.json {
                    rows.push(serde_json::json!({
                        "threshold": th,
                        "model_default": model_default == Some(th),
                        "recall": frac(r.overall.recall()),
                        "full": frac(r.overall.full_recall()),
                        "chars": frac(r.overall.char_recall()),
                        "precision": frac(r.overall.precision()),
                        "leak_docs": r.docs_with_leak,
                        "over_redaction": r.over_redaction,
                        "gold_chars": r.overall.gold_chars,
                        "clean_chars": r.clean_chars,
                    }));
                } else {
                    let mark = if model_default == Some(th) { " *model default*" } else { "" };
                    println!("{:>9.2} {:>8.1} {:>8.1} {:>8.1} {:>10} {:>8.1}{}", th,
                        r.overall.recall() * 100.0, r.overall.full_recall() * 100.0,
                        r.overall.precision() * 100.0, r.docs_with_leak, r.over_redaction * 100.0, mark);
                }
            }
            if a.json {
                println!("{}", serde_json::to_string_pretty(&rows).map_err(|e| e.to_string())?);
            }
        }
        "convert" => {
            // Rewrite a dataset's labels as Scotoma categories, so training data from
            // any source shares one label space. Non-identifiers are dropped.
            use scotoma_core::labels::{map_label, Mapped};
            let src = a.path.as_ref().ok_or("need IN.jsonl OUT.jsonl")?;
            let dst = a.path2.as_ref().ok_or("need IN.jsonl OUT.jsonl")?;
            let docs = eval::parse_jsonl(&std::fs::read_to_string(src).map_err(|e| format!("{src}: {e}"))?)?;
            let mut out = String::new();
            let (mut kept, mut dropped) = (0, 0);
            for d in &docs {
                let spans: Vec<serde_json::Value> = d.spans.iter().filter_map(|g| {
                    let cat = match map_label(&g.label) {
                        Mapped::Phi(c) => c.tag(),
                        Mapped::Quasi => "ORG",
                        Mapped::Keep => { dropped += 1; return None; }
                    };
                    kept += 1;
                    // Offsets go back out in characters, as they came in.
                    let (a, b) = (d.text[..g.start].chars().count(), d.text[..g.end].chars().count());
                    Some(serde_json::json!({ "start": a, "end": b, "label": cat }))
                }).collect();
                out.push_str(&serde_json::json!({ "text": d.text, "spans": spans }).to_string());
                out.push('\n');
            }
            std::fs::write(dst, out).map_err(|e| format!("{dst}: {e}"))?;
            eprintln!("{} documents, {kept} identifiers kept, {dropped} non-identifier labels dropped", docs.len());
        }
        other => return Err(format!("unknown command {other}")),
    }
    Ok(())
}


#[cfg(target_os = "macos")]
extern "C" { fn pthread_set_qos_class_self_np(qos: u32, relpri: i32) -> i32; }

/// Benchmarks are often started from scripts or agents that macOS treats as
/// background work and squeezes onto a sliver of one core. Ask for
/// user-initiated QoS before any worker threads exist (they inherit it).
fn raise_qos() {
    #[cfg(target_os = "macos")]
    unsafe { let _ = pthread_set_qos_class_self_np(0x19 /* QOS_CLASS_USER_INITIATED */, 0); }
}

fn main() {
    raise_qos();
    if let Err(e) = run() {
        eprintln!("scotoma: {e}");
        std::process::exit(1);
    }
}
