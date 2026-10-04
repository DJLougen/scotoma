//! End-to-end check of the ONNX path against a lookup-table model built by
//! scripts/make_toy_model.py. Set SCOTOMA_TEST_MODEL to its folder.
#![cfg(feature = "onnx")]

use scotoma_core::{model::OnnxDetector, Category, Config, Scrubber};

fn texts(t: &str, spans: &[scotoma_core::Span]) -> Vec<(Category, String)> {
    spans.iter().map(|s| (s.category, t[s.start..s.end].to_string())).collect()
}

#[test]
fn toy_model_end_to_end() {
    let Ok(dir) = std::env::var("SCOTOMA_TEST_MODEL") else {
        eprintln!("SCOTOMA_TEST_MODEL not set; skipping");
        return;
    };
    let det = OnnxDetector::load(std::path::Path::new(&dir)).expect("load");
    let mut sc = Scrubber::with_model(Config::default(), Box::new(det));

    let t = "The patient is John Smith, a nurse from Toronto. Anna Müller is 97, John is 45.";
    let d = sc.detect(t).unwrap();
    let got = texts(t, &d.spans);
    // Adjacent first+last name tokens fuse into one span; "Anna" is caught by
    // summed B-/I- mass (0.55) although argmax alone would call it O.
    assert!(got.contains(&(Category::Name, "John Smith".into())), "{got:?}");
    assert!(got.contains(&(Category::Name, "Anna Müller".into())), "{got:?}");
    assert!(got.contains(&(Category::Age, "97".into())), "{got:?}");
    assert!(!got.iter().any(|(_, s)| s == "45"), "{got:?}");
    assert!(!got.iter().any(|(_, s)| s == "nurse"), "{got:?}");
    // Bare repeat of "John" is picked up (model or propagation).
    assert_eq!(got.iter().filter(|(c, s)| *c == Category::Name && s == "John").count(), 1, "{got:?}");
    // Sub-threshold city is offered for review, not redacted.
    assert_eq!(texts(t, &d.possible), vec![(Category::Location, "Toronto".to_string())]);

    sc.config.strict = true;
    let d = sc.detect(t).unwrap();
    assert!(texts(t, &d.spans).contains(&(Category::Org, "nurse".into())));

    // Longer than one window (24 positions): offsets must still line up.
    sc.config.strict = false;
    let long = format!("{} {}", "the patient is a ".repeat(30), "John Smith from Toronto");
    let d = sc.detect(&long).unwrap();
    assert_eq!(texts(&long, &d.spans), vec![(Category::Name, "John Smith".to_string())]);
}
