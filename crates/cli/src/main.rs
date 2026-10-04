//! scotoma — scrub text on stdin, or benchmark the pipeline.
//!
//!   scotoma scrub  [--model DIR] [--surrogate] [--strict] [--threshold P] [--json] < note.txt
//!   scotoma eval   DATA.jsonl [--model DIR] [--strict] [--threshold P] [--limit N] [--misses N] [--json]
//!   scotoma sweep  DATA.jsonl --model DIR [--limit N]      # recall/precision vs threshold
//!   scotoma convert IN.jsonl OUT.jsonl                # map any label set to Scotoma categories
//!
//! eval also takes: --no-rules (score the model alone), --responses FILE.csv (per-item outcomes)

use scotoma_core::transform::{render, Mode, Vault};
use scotoma_core::{eval, Config, Scrubber};
use std::io::Read;

struct Args {
    cmd: String,
    path: Option<String>,
    model: Option<String>,
    surrogate: bool,
    json: bool,
    limit: Option<usize>,
    misses: usize,
    cfg: Config,
    path2: Option<String>,
    responses: Option<String>,
}

fn parse() -> Result<Args, String> {
    let mut it = std::env::args().skip(1);
    let cmd = it.next().ok_or("usage: scotoma <scrub|eval|sweep> [options]")?;
    let mut a = Args { cmd, path: None, model: std::env::var("SCOTOMA_MODEL").ok(), surrogate: false, json: false, limit: None, misses: 25, cfg: Config::default(), path2: None, responses: None };
    while let Some(x) = it.next() {
        let mut val = |n: &str| it.next().ok_or(format!("{n} needs a value"));
        match x.as_str() {
            "--model" => a.model = Some(val("--model")?),
            "--no-model" => a.model = None,
            "--surrogate" => a.surrogate = true,
            "--strict" => a.cfg.strict = true,
            "--no-rules" => a.cfg.use_rules = false,
            "--responses" => a.responses = Some(val("--responses")?),
            "--json" => a.json = true,
            "--threshold" => a.cfg.threshold = val("--threshold")?.parse().map_err(|_| "bad --threshold")?,
            "--limit" => a.limit = Some(val("--limit")?.parse().map_err(|_| "bad --limit")?),
            "--misses" => a.misses = val("--misses")?.parse().map_err(|_| "bad --misses")?,
            s if !s.starts_with("--") && a.path.is_none() => a.path = Some(s.to_string()),
            s if !s.starts_with("--") && a.path2.is_none() => a.path2 = Some(s.to_string()),
            s => return Err(format!("unknown option {s}")),
        }
    }
    Ok(a)
}

fn scrubber(a: &Args) -> Result<Scrubber, String> {
    #[allow(unused_mut)]
    let mut sc = Scrubber::rules_only(a.cfg.clone());
    if let Some(dir) = &a.model {
        #[cfg(feature = "onnx")]
        {
            let det = scotoma_core::model::OnnxDetector::load(std::path::Path::new(dir))?;
            sc.set_model(Some(Box::new(det)));
        }
        #[cfg(not(feature = "onnx"))]
        return Err(format!("built without the onnx feature; cannot load {dir}"));
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
    let a = parse()?;
    match a.cmd.as_str() {
        "scrub" => {
            let sc = scrubber(&a)?;
            let mut text = String::new();
            std::io::stdin().read_to_string(&mut text).map_err(|e| e.to_string())?;
            let det = sc.detect(&text)?;
            let mut vault = Vault::new();
            let out = render(&text, &det.spans, if a.surrogate { Mode::Surrogate } else { Mode::Tag }, &mut vault);
            if a.json {
                println!("{}", serde_json::json!({ "text": out.text, "items": out.items, "possible": det.possible }));
            } else {
                print!("{}", out.text);
                eprintln!("\n— {} replaced, {} possible, engine: rules{}", out.items.len(), det.possible.len(),
                    sc.model_name().map(|n| format!(" + {n}")).unwrap_or_default());
            }
        }
        "eval" => {
            let sc = scrubber(&a)?;
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
                println!("engine: rules{} · threshold {} · strict {}\n", sc.model_name().map(|n| format!(" + {n}")).unwrap_or_default(), sc.config.threshold, sc.config.strict);
                print!("{}", eval::format_report(&r));
                if !r.misses.is_empty() {
                    println!("\nmisses (first {}):", r.misses.len());
                    for m in &r.misses {
                        println!("  {:<9} {} {}", m.category.tag(), if m.partial { "partial" } else { "MISSED " }, m.context);
                    }
                }
            }
        }
        "sweep" => {
            let mut sc = scrubber(&a)?;
            let docs = load(&a)?;
            println!("{:>9} {:>8} {:>8} {:>8} {:>10}", "threshold", "recall", "full", "prec", "leak docs");
            for th in [0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.9] {
                sc.config.threshold = th;
                sc.config.floor = sc.config.floor.min(th);
                let r = eval::evaluate(&sc, &docs, 0)?;
                println!("{:>9.2} {:>8.1} {:>8.1} {:>8.1} {:>10}", th, r.overall.recall() * 100.0, r.overall.full_recall() * 100.0, r.overall.precision() * 100.0, r.docs_with_leak);
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

fn main() {
    if let Err(e) = run() {
        eprintln!("scotoma: {e}");
        std::process::exit(1);
    }
}
