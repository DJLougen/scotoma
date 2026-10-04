//! Overlap resolution. Recall-first: overlapping detections are unioned, never
//! intersected, so a disagreement between rules and model can only widen a span.

use crate::{Source, Span};

fn rank(s: &Span) -> f32 {
    let bonus = match s.source {
        Source::Manual => 3.0,
        Source::Rule => 1.0,
        Source::Model => 0.5,
        Source::Propagated => 0.0,
    };
    bonus + s.confidence
}

/// Sort and union overlapping spans; the highest-ranked member names the category.
pub fn merge(text: &str, mut spans: Vec<Span>) -> Vec<Span> {
    spans.retain(|s| s.start < s.end && s.end <= text.len());
    for s in spans.iter_mut() {
        // Never split a UTF-8 sequence.
        while !text.is_char_boundary(s.start) { s.start -= 1; }
        while !text.is_char_boundary(s.end) { s.end += 1; }
    }
    spans.sort_by(|a, b| a.start.cmp(&b.start).then(b.end.cmp(&a.end)));
    let mut out: Vec<Span> = Vec::with_capacity(spans.len());
    for s in spans {
        match out.last_mut() {
            Some(last) if s.start < last.end => {
                let best_new = rank(&s) > rank(last);
                let end = last.end.max(s.end);
                if best_new {
                    let start = last.start;
                    *last = s;
                    last.start = start;
                }
                last.end = end;
            }
            _ => out.push(s),
        }
    }
    out
}

/// Remove from `a` anything overlapping `b` (both sorted).
pub fn subtract(a: Vec<Span>, b: &[Span]) -> Vec<Span> {
    a.into_iter().filter(|s| !b.iter().any(|o| o.overlaps(s))).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Category;

    #[test]
    fn union_keeps_rule_category() {
        let t = "MRN 12345678 today";
        let v = merge(t, vec![
            Span::new(4, 12, Category::Mrn, Source::Rule, 0.95),
            Span::new(2, 9, Category::Id, Source::Model, 0.99),
        ]);
        assert_eq!(v.len(), 1);
        assert_eq!((v[0].start, v[0].end, v[0].category), (2, 12, Category::Mrn));
    }
}
