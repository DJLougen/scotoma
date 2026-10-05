//! Visual redaction: image/PDF → OCR word boxes → detected spans → black boxes.
//!
//! The macOS helper (`scotoma-helper ocr-boxes`) turns a page into lines of
//! words, each word carrying a pixel box and its character offsets within the
//! line's text. This module rebuilds the page's text, runs the normal
//! [`Scrubber`] detection on it, and maps every detected span back to the word
//! boxes it overlaps — the helper's `paint` verb then draws those boxes.
//!
//! The mapping itself is pure and portable; only `redact_document` (which runs
//! the helper binary) is macOS-only.

use serde::{Deserialize, Serialize};

use crate::{char_to_byte, Scrubber, Span};

/// Character padding applied to each side of a word box before painting, so
/// antialiased glyph edges at the boundary don't peek out.
const BOX_PAD: f64 = 2.0;

/// One recognised word. `start`/`end` are character offsets into the line's
/// `text`; `box` is `[x, y, w, h]` in page pixels, top-left origin.
#[derive(Debug, Clone, Deserialize)]
pub struct OcrWord {
    pub text: String,
    pub start: usize,
    pub end: usize,
    #[serde(rename = "box")]
    pub bbox: [f64; 4],
}

#[derive(Debug, Clone, Deserialize)]
pub struct OcrLine {
    pub text: String,
    /// The line's own pixel box — the fallback when a word's box is missing
    /// or degenerate. Optional for hand-built fixtures; the helper emits it.
    #[serde(default)]
    pub bbox: Option<[f64; 4]>,
    pub words: Vec<OcrWord>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct OcrPage {
    pub width: u32,
    pub height: u32,
    pub lines: Vec<OcrLine>,
}

/// What `scotoma-helper ocr-boxes` prints.
#[derive(Debug, Clone, Deserialize)]
pub struct OcrDoc {
    pub pages: Vec<OcrPage>,
}

impl OcrDoc {
    pub fn parse(json: &str) -> Result<Self, String> {
        serde_json::from_str(json).map_err(|e| format!("helper returned malformed OCR JSON: {e}"))
    }

    /// The text the scrubber sees for one page: lines joined by "\n".
    pub fn page_text(&self, page: usize) -> String {
        self.pages[page].lines.iter().map(|l| l.text.as_str()).collect::<Vec<_>>().join("\n")
    }

    /// Byte range of one word within its page's assembled text. OCR offsets
    /// are in characters; verify the slice so a helper quirk can't silently
    /// box the wrong word — if the slice doesn't match, locate the word's text
    /// near the stated offset instead.
    fn word_bytes(&self, page: usize, line: usize, word: usize) -> Option<(usize, usize)> {
        let p = &self.pages[page];
        let w = p.lines.get(line)?.words.get(word)?;
        // Byte offset of the start of this line within the page text.
        let mut base = 0usize;
        for l in &p.lines[..line] { base += l.text.len() + 1; }
        let line_text = &l_text(p, line);
        let mut s = base + char_to_byte(line_text, w.start);
        let mut e = base + char_to_byte(line_text, w.end);
        if e <= s || line_text.get(s - base..e - base) != Some(w.text.as_str()) {
            // Offsets don't line up (normalisation, helper bug): find the word
            // verbatim, preferring the occurrence nearest the stated offset.
            let want = w.text.as_str();
            let mut best: Option<(usize, usize)> = None;
            let mut from = 0usize;
            while let Some(i) = line_text[from..].find(want).map(|i| i + from) {
                let cand = (i, i + want.len());
                let dist = |r: (usize, usize)| (r.0 + base).abs_diff(s);
                if best.map_or(true, |b| dist(cand) < dist(b)) { best = Some(cand); }
                from = i + 1;
            }
            (s, e) = best.map(|(a, b)| (base + a, base + b))?;
        }
        Some((s, e))
    }

    /// Every word box overlapped by `span`, padded by [`BOX_PAD`] and clipped
    /// to the page. Boxes are `[x, y, w, h]` in pixels, top-left origin.
    /// A span crossing a line break yields boxes on both lines.
    pub fn boxes_for_span(&self, page: usize, span: &Span) -> Vec<[f64; 4]> {
        let p = &self.pages[page];
        let mut out = Vec::new();
        for (li, line) in p.lines.iter().enumerate() {
            for (wi, w) in line.words.iter().enumerate() {
                let Some((s, e)) = self.word_bytes(page, li, wi) else { continue };
                if s < span.end && span.start < e {
                    let [mut x, mut y, mut bw, mut bh] = w.bbox;
                    if bw < 2.0 || bh < 2.0 {
                        // Degenerate/missing word box: fall back to a
                        // proportional slice of the line's box so the
                        // redaction still covers the word.
                        if let Some([lx, ly, lw, lh]) = line.bbox {
                            let total = line.text.chars().count().max(1) as f64;
                            let x0 = lx + lw * w.start as f64 / total;
                            let x1 = lx + lw * w.end as f64 / total;
                            x = x0; y = ly; bw = (x1 - x0).max(1.0); bh = lh;
                        }
                    }
                    let x0 = (x - BOX_PAD).max(0.0);
                    let y0 = (y - BOX_PAD).max(0.0);
                    out.push([
                        x0,
                        y0,
                        (bw + 2.0 * BOX_PAD).min(p.width as f64 - x0).max(0.0),
                        (bh + 2.0 * BOX_PAD).min(p.height as f64 - y0).max(0.0),
                    ]);
                }
            }
        }
        out
    }

    pub fn word_count(&self) -> usize {
        self.pages.iter().flat_map(|p| &p.lines).map(|l| l.words.len()).sum()
    }
}

fn l_text<'a>(p: &'a OcrPage, line: usize) -> &'a str { &p.lines[line].text }

/// A detected span, annotated with the page it was found on and how many
/// boxes it produced. Never carries the matched text.
#[derive(Debug, Clone, Serialize)]
pub struct MarkedSpan {
    pub page: usize,
    pub start: usize,
    pub end: usize,
    pub category: crate::Category,
    pub source: crate::Source,
    pub confidence: f32,
    pub dob: bool,
    pub boxes: usize,
}

/// What one page contributes to the boxes file handed to `paint`:
/// `{"boxes": [{"page": P, "box": [x, y, w, h]}, ...]}`.
#[derive(Debug, Clone, Serialize)]
pub struct PaintBox {
    pub page: usize,
    #[serde(rename = "box")]
    pub bbox: [f64; 4],
}

#[derive(Debug, Clone, Serialize)]
pub struct RedactReport {
    pub words: usize,
    /// Per-category count of detected (not merely possible) spans.
    pub counts: std::collections::BTreeMap<String, usize>,
    pub spans: Vec<MarkedSpan>,
    pub boxes: usize,
}

/// Run the scrubber over every page of an OCR document and collect the boxes
/// to paint. Returns the report (safe to show: no identifier text) and the
/// JSON the helper's `paint` verb consumes.
pub fn mark_document(scrubber: &Scrubber, doc: &OcrDoc) -> Result<(RedactReport, String), String> {
    let mut report = RedactReport { words: doc.word_count(), counts: Default::default(), spans: Vec::new(), boxes: 0 };
    let mut paint: Vec<PaintBox> = Vec::new();
    for (pi, _) in doc.pages.iter().enumerate() {
        let text = doc.page_text(pi);
        if text.trim().is_empty() { continue; }
        let det = scrubber.detect(&text)?;
        for s in &det.spans {
            let boxes = doc.boxes_for_span(pi, s);
            *report.counts.entry(s.category.tag().to_string()).or_default() += 1;
            report.boxes += boxes.len();
            for bbox in &boxes { paint.push(PaintBox { page: pi, bbox: *bbox }); }
            report.spans.push(MarkedSpan {
                page: pi, start: s.start, end: s.end, category: s.category,
                source: s.source, confidence: s.confidence, dob: s.dob,
                boxes: boxes.len(),
            });
        }
    }
    let boxes_json = serde_json::to_string(&serde_json::json!({ "boxes": paint })).map_err(|e| e.to_string())?;
    Ok((report, boxes_json))
}

/// Locate the macOS helper binary next to the running executable (bundled app,
/// release dir) or in the source tree. `$SCOTOMA_HELPER` wins.
#[cfg(target_os = "macos")]
pub fn find_helper() -> Option<std::path::PathBuf> {
    let mut v: Vec<std::path::PathBuf> = Vec::new();
    if let Ok(p) = std::env::var("SCOTOMA_HELPER") { v.push(p.into()); }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            v.push(dir.join("scotoma-helper"));
            // .app bundle: helper is a resource under Contents/Resources/bin.
            if let Some(res) = dir.parent().map(|c| c.join("Resources").join("bin").join("scotoma-helper")) {
                v.push(res);
            }
            // Dev builds: target/{release,debug}/scotoma → repo/app/src-tauri/bin.
            if let Some(repo) = dir.parent().and_then(|t| t.parent()) {
                v.push(repo.join("app").join("src-tauri").join("bin").join("scotoma-helper"));
            }
        }
    }
    v.push("app/src-tauri/bin/scotoma-helper".into());
    v.into_iter().find(|p| p.is_file())
}

/// The full pipeline: OCR → detect → boxes → paint. Writes `out` (PNG for a
/// single-page image, image-only PDF for a PDF) and returns the report plus
/// the painted page previews as PNG bytes (one per page) for display.
#[cfg(target_os = "macos")]
pub fn redact_document(
    scrubber: &Scrubber,
    input: &std::path::Path,
    out: &std::path::Path,
    previews: Option<&std::path::Path>,
) -> Result<RedactReport, String> {
    let helper = find_helper().ok_or("scotoma-helper not found (build app/src-tauri/helper or set SCOTOMA_HELPER)")?;

    let run = |args: &[&std::ffi::OsStr]| -> Result<std::process::Output, String> {
        std::process::Command::new(&helper).args(args).output().map_err(|e| format!("could not run {}: {e}", helper.display()))
    };

    let o = run(&["ocr-boxes".as_ref(), input.as_os_str()])?;
    if !o.status.success() {
        return Err(format!("OCR failed: {}", String::from_utf8_lossy(&o.stderr).trim()));
    }
    let doc = OcrDoc::parse(&String::from_utf8_lossy(&o.stdout))?;
    let (report, boxes_json) = mark_document(scrubber, &doc)?;

    let boxes_path = std::env::temp_dir().join(format!("scotoma-boxes-{}.json", std::process::id()));
    std::fs::write(&boxes_path, &boxes_json).map_err(|e| format!("could not write {boxes_path:?}: {e}"))?;
    let mut args: Vec<std::ffi::OsString> = vec!["paint".into(), input.as_os_str().into(), out.as_os_str().into(), "--boxes".into(), boxes_path.as_os_str().into()];
    if let Some(d) = previews { std::fs::create_dir_all(d).ok(); args.push("--previews".into()); args.push(d.as_os_str().into()); }
    let o = run(&args.iter().map(|s| s.as_os_str()).collect::<Vec<_>>())?;
    let _ = std::fs::remove_file(&boxes_path);
    if !o.status.success() {
        return Err(format!("paint failed: {}", String::from_utf8_lossy(&o.stderr).trim()));
    }
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Category, Config, Source};

    fn doc(json: &str) -> OcrDoc { OcrDoc::parse(json).unwrap() }

    fn span(text: &str, needle: &str) -> Span {
        let s = text.find(needle).unwrap();
        Span::new(s, s + needle.len(), Category::Name, Source::Rule, 1.0)
    }

    #[test]
    fn span_within_one_word() {
        let d = doc(r#"{"pages":[{"width":100,"height":50,"lines":[
            {"text":"Patient MR12345 seen today","words":[
                {"text":"Patient","start":0,"end":7,"box":[2,4,30,10]},
                {"text":"MR12345","start":8,"end":15,"box":[36,4,40,10]},
                {"text":"seen","start":16,"end":20,"box":[80,4,10,10]},
                {"text":"today","start":21,"end":26,"box":[92,4,8,10]}]}]}]}"#);
        let text = d.page_text(0);
        let b = d.boxes_for_span(0, &span(&text, "1234")); // inside "MR12345"
        assert_eq!(b.len(), 1);
        // padded by 2px: x 34, y 2, w 44, h 14
        assert_eq!(b[0], [34.0, 2.0, 44.0, 14.0]);
    }

    #[test]
    fn span_across_words() {
        let d = doc(r#"{"pages":[{"width":200,"height":50,"lines":[
            {"text":"Maria Elena Santos arrived","words":[
                {"text":"Maria","start":0,"end":5,"box":[2,4,20,10]},
                {"text":"Elena","start":6,"end":11,"box":[26,4,20,10]},
                {"text":"Santos","start":12,"end":18,"box":[50,4,25,10]},
                {"text":"arrived","start":19,"end":26,"box":[80,4,30,10]}]}]}]}"#);
        let text = d.page_text(0);
        let b = d.boxes_for_span(0, &span(&text, "Maria Elena Santos"));
        assert_eq!(b.len(), 3);
        assert!(b.iter().all(|bb| bb[2] > 0.0 && bb[3] > 0.0));
    }
    #[test]
    fn degenerate_word_box_falls_back_to_line_slice() {
        // Vision can return a null/zero-size box for an odd glyph run; the
        // redaction must still cover the word via the line's box.
        let d = doc(r#"{"pages":[{"width":200,"height":50,"lines":[
            {"text":"call Dana Miller","bbox":[0,0,100,20],"words":[
                {"text":"call","start":0,"end":4,"box":[2,4,20,10]},
                {"text":"Dana","start":5,"end":9,"box":[0,0,0,0]},
                {"text":"Miller","start":10,"end":16,"box":[60,4,30,10]}]}]}]}"#);
        let text = d.page_text(0);
        let b = d.boxes_for_span(0, &span(&text, "Dana"));
        assert_eq!(b.len(), 1);
        assert!(b[0][2] > 5.0 && b[0][3] > 5.0, "fallback slice: {:?}", b[0]);
        assert!(b[0][0] > 0.0, "slice is positioned, x0={}", b[0][0]);
    }
    #[test]
    fn span_across_line_break() {
        let d = doc(r#"{"pages":[{"width":200,"height":80,"lines":[
            {"text":"lives at 12 Oak","words":[
                {"text":"lives","start":0,"end":5,"box":[2,4,20,10]},
                {"text":"at","start":6,"end":8,"box":[26,4,10,10]},
                {"text":"12","start":9,"end":11,"box":[40,4,10,10]},
                {"text":"Oak","start":12,"end":15,"box":[54,4,15,10]}]},
            {"text":"Street, Springfield","words":[
                {"text":"Street,","start":0,"end":7,"box":[2,20,30,10]},
                {"text":"Springfield","start":8,"end":19,"box":[36,20,50,10]}]}]}]}"#);
        let text = d.page_text(0); // "lives at 12 Oak\nStreet, Springfield"
        let b = d.boxes_for_span(0, &span(&text, "Oak\nStreet"));
        assert_eq!(b.len(), 2);
        assert!(b[0][1] < 15.0 && b[1][1] > 15.0, "boxes on both lines");
    }

    #[test]
    fn no_spans_no_boxes() {
        let d = doc(r#"{"pages":[{"width":100,"height":50,"lines":[
            {"text":"hello world","words":[
                {"text":"hello","start":0,"end":5,"box":[2,4,20,10]},
                {"text":"world","start":6,"end":11,"box":[26,4,20,10]}]}]}]}"#);
        let text = d.page_text(0);
        let sc = Scrubber::rules_only(Config::default());
        let det = sc.detect(&text).unwrap();
        assert!(det.spans.is_empty());
        let (report, boxes) = mark_document(&sc, &d).unwrap();
        assert_eq!(report.boxes, 0);
        assert!(boxes.contains("\"boxes\":[]"));
        let _ = text;
    }

    #[test]
    fn unicode_offsets() {
        // "José" is 4 chars / 5 bytes; "café ☕" has a multi-byte char + emoji.
        let line = "José café ☕ 1980";
        let mut off = 0usize;
        let words: Vec<String> = line.split_whitespace().map(|w| {
            // character offset of this word occurrence
            let byte = line[off..].find(w).unwrap() + off;
            let chars = line[..byte].chars().count();
            off = byte + w.len();
            format!("{{\"text\":\"{w}\",\"start\":{chars},\"end\":{},\"box\":[0,0,10,10]}}", chars + w.chars().count())
        }).collect();
        let json = format!("{{\"pages\":[{{\"width\":100,\"height\":50,\"lines\":[{{\"text\":\"{line}\",\"words\":[{}]}}]}}]}}", words.join(","));
        let d = doc(&json);
        let text = d.page_text(0);
        assert_eq!(text, line);
        // Span over "1980" must land on the last word's box even though every
        // earlier word has multi-byte characters.
        let b = d.boxes_for_span(0, &span(&text, "1980"));
        assert_eq!(b.len(), 1);
        // And a span over "café" must not touch "☕" or "José".
        let b = d.boxes_for_span(0, &span(&text, "café"));
        assert_eq!(b.len(), 1);
        let w = &d.pages[0].lines[0].words;
        // Verify byte ranges actually slice the right words.
        for (i, word) in w.iter().enumerate() {
            let (s, e) = d.word_bytes(0, 0, i).unwrap();
            assert_eq!(&text[s..e], word.text, "{:?}", word.text);
        }
    }

    #[test]
    fn end_to_end_mapping() {
        // Rules-only: an SSN in the middle of a two-line page.
        let d = doc(r#"{"pages":[{"width":300,"height":80,"lines":[
            {"text":"Patient MRN 987654","words":[
                {"text":"Patient","start":0,"end":7,"box":[2,4,30,10]},
                {"text":"MRN","start":8,"end":11,"box":[36,4,15,10]},
                {"text":"987654","start":12,"end":18,"box":[55,4,30,10]}]},
            {"text":"SSN 423-88-5575 today","words":[
                {"text":"SSN","start":0,"end":3,"box":[2,20,15,10]},
                {"text":"423-88-5575","start":4,"end":15,"box":[21,20,55,10]},
                {"text":"today","start":16,"end":21,"box":[80,20,25,10]}]}]}]}"#);
        let sc = Scrubber::rules_only(Config::default());
        let (report, boxes_json) = mark_document(&sc, &d).unwrap();
        assert!(report.boxes >= 2, "MRN + SSN at least: {report:?}");
        let v: serde_json::Value = serde_json::from_str(&boxes_json).unwrap();
        let boxes = v["boxes"].as_array().unwrap();
        assert_eq!(boxes.len(), report.boxes);
        assert!(boxes.iter().all(|b| b["page"] == 0));
        // The SSN box sits on the second line.
        let ssn = boxes.iter().find(|b| b["box"][1].as_f64().unwrap() > 15.0).expect("a box on line 2");
        let w = ssn["box"][2].as_f64().unwrap();
        assert!(w >= 55.0, "SSN box covers the word, w={w}");
    }
}
