// Scotoma desktop shell. Tray icon, two global hotkeys, one review window.
// This binary contains no networking code: text goes clipboard → memory → clipboard.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use scotoma_core::transform::{render, Mode, Vault};
use scotoma_core::{merge, utf16_to_byte, Category, Config, Detector, Scrubber, Source, Span};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::io::Write;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use parking_lot::Mutex;
use std::time::{Duration, Instant};
use tauri::menu::{CheckMenuItem, Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Emitter, Manager, State, WindowEvent};
use tauri_plugin_clipboard_manager::ClipboardExt;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};
use tauri_plugin_notification::NotificationExt;

const HOTKEY_SCRUB: &str = "CmdOrCtrl+Alt+S";
const HOTKEY_RESTORE: &str = "CmdOrCtrl+Alt+R";
const HOTKEY_CAPTURE: &str = "CmdOrCtrl+Alt+D";
const HOTKEY_BLANK: &str = "CmdOrCtrl+Alt+N";
/// Press to start dictating, press again to stop.
const HOTKEY_DICTATE: &str = "CmdOrCtrl+Alt+V";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct Settings {
    mode: Mode,
    /// Show the review window before anything reaches the clipboard.
    review: bool,
    strict: bool,
    /// User-picked redaction threshold. `None` = follow the model's declared
    /// default (scotoma_threshold in its config.json), else Config::default().
    threshold: Option<f32>,
    /// Forget remembered originals after this many idle minutes (0 = never).
    vault_minutes: u32,
    /// Bring-your-own speech model: a shell command that prints the transcript
    /// of `{audio}` (a 16 kHz mono WAV) on stdout. Empty = dictation off.
    transcribe_cmd: String,
}

impl Default for Settings {
    fn default() -> Self {
        Settings { mode: Mode::Tag, review: true, strict: false, threshold: None, vault_minutes: 30, transcribe_cmd: String::new() }
    }
}

struct AppState {
    scrubber: Mutex<Scrubber>,
    vault: Mutex<Vault>,
    settings: Mutex<Settings>,
    touched: Mutex<Instant>,
    model_error: Mutex<Option<String>>,
    settings_path: Mutex<Option<PathBuf>>,
    /// Screen capture + OCR helper (macOS only), if it was built.
    helper: Mutex<Option<PathBuf>>,
    capturing: AtomicBool,
    /// An in-progress microphone recording and the file it is writing.
    recorder: Mutex<Option<(Child, PathBuf)>>,
    pending: Mutex<Option<Analysis>>,
}

/// A span as the window sees it: UTF-16 offsets, plus the matched text.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct UiSpan {
    start: usize,
    end: usize,
    category: Category,
    source: Source,
    confidence: f32,
    #[serde(default)]
    dob: bool,
    #[serde(default)]
    on: bool,
}

#[derive(Serialize, Clone)]
struct Analysis {
    text: String,
    spans: Vec<UiSpan>,
    /// Where the text came from: typed, selection, clipboard, screen, voice.
    origin: &'static str,
    /// Time to get the text (OCR, transcription, selection grab), in ms.
    acquire_ms: u64,
    /// Time for rules + model, in ms.
    detect_ms: u64,
}

#[derive(Serialize)]
struct UiItem {
    start: usize,
    end: usize,
    category: Category,
}

#[derive(Serialize)]
struct Preview {
    text: String,
    items: Vec<UiItem>,
}

#[derive(Serialize, Clone)]
struct Status {
    model: Option<String>,
    model_error: Option<String>,
    settings: Settings,
    /// The threshold actually in use: the user's, else the model's default.
    threshold: f32,
    vault_entries: usize,
    hotkey_scrub: &'static str,
    hotkey_restore: &'static str,
    hotkey_capture: &'static str,
    hotkey_blank: &'static str,
    hotkey_dictate: &'static str,
    capture_available: bool,
    dictating: bool,
}

fn to_utf16(text: &str, byte: usize) -> usize {
    text[..byte].encode_utf16().count()
}

fn ui_span(text: &str, s: &Span, on: bool) -> UiSpan {
    UiSpan { start: to_utf16(text, s.start), end: to_utf16(text, s.end), category: s.category, source: s.source, confidence: s.confidence, dob: s.dob, on }
}

fn core_spans(text: &str, spans: &[UiSpan]) -> Vec<Span> {
    let v = spans.iter().filter(|s| s.on).map(|s| {
        let mut sp = Span::new(utf16_to_byte(text, s.start), utf16_to_byte(text, s.end), s.category, s.source, s.confidence);
        sp.dob = s.dob;
        sp
    }).collect();
    merge::merge(text, v)
}

fn status_of(state: &AppState) -> Status {
    let sc = state.scrubber.lock();
    Status {
        model: sc.model_name(),
        threshold: sc.config.threshold,
        model_error: state.model_error.lock().clone(),
        settings: state.settings.lock().clone(),
        vault_entries: state.vault.lock().len(),
        hotkey_scrub: HOTKEY_SCRUB,
        hotkey_restore: HOTKEY_RESTORE,
        hotkey_capture: HOTKEY_CAPTURE,
        hotkey_blank: HOTKEY_BLANK,
        hotkey_dictate: HOTKEY_DICTATE,
        capture_available: state.helper.lock().is_some(),
        dictating: state.recorder.lock().is_some(),
    }
}

fn touch(state: &AppState) {
    *state.touched.lock() = Instant::now();
}

fn analyze_text(state: &AppState, text: &str) -> Result<Analysis, String> {
    analyze_from(state, text, "typed", None)
}

fn analyze_from(state: &AppState, text: &str, origin: &'static str, since: Option<Instant>) -> Result<Analysis, String> {
    let acquire_ms = since.map(|t| t.elapsed().as_millis() as u64).unwrap_or(0);
    let t0 = Instant::now();
    let det = state.scrubber.lock().detect(text)?;
    let detect_ms = t0.elapsed().as_millis() as u64;
    let mut spans: Vec<UiSpan> = det.spans.iter().map(|s| ui_span(text, s, true)).collect();
    spans.extend(det.possible.iter().map(|s| ui_span(text, s, false)));
    spans.sort_by_key(|s| s.start);
    Ok(Analysis { text: text.to_string(), spans, origin, acquire_ms, detect_ms })
}

fn render_text(state: &AppState, text: &str, spans: &[UiSpan]) -> Preview {
    let mode = state.settings.lock().mode;
    let spans = core_spans(text, spans);
    let out = render(text, &spans, mode, &mut state.vault.lock());
    touch(state);
    let items = out.items.iter().map(|i| UiItem { start: to_utf16(&out.text, i.out_start), end: to_utf16(&out.text, i.out_end), category: i.category }).collect();
    Preview { text: out.text, items }
}

/// Hand text to the review window. The analysis is also kept until it is
/// approved or replaced, so a window that was still loading (or reloads) when
/// the hotkey fired can pick it up instead of silently showing nothing.
fn send_review(app: &AppHandle, analysis: Analysis) {
    *app.state::<AppState>().pending.lock() = Some(analysis.clone());
    let _ = app.emit("review", analysis);
    show_window(app);
}

fn notify(app: &AppHandle, body: &str) {
    let _ = app.notification().builder().title("Scotoma").body(body).show();
}

fn show_window(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.unminimize();
        let _ = w.set_focus();
    }
}

/// Hotkey / tray entry point. Takes, in order: the text selected in the
/// frontmost app, the text on the clipboard, a screenshot on the clipboard.
fn scrub_clipboard_impl(app: &AppHandle) {
    let app = app.clone();
    std::thread::spawn(move || {
        let state = app.state::<AppState>();
        let helper = state.helper.lock().clone();
        let t0 = Instant::now();
        if let Some(helper) = helper {
            if let Ok(out) = Command::new(&helper).arg("selection").stdin(Stdio::null()).output() {
                let text = String::from_utf8_lossy(&out.stdout).trim_end().to_string();
                if out.status.success() && !text.trim().is_empty() {
                    return scrub_text_impl(&app, text, "selection", t0);
                }
            }
        }
        let t0 = Instant::now();
        match app.clipboard().read_text() {
            Ok(t) if !t.trim().is_empty() => scrub_text_impl(&app, t, "clipboard", t0),
            // No text anywhere: perhaps a screenshot was copied. Read it instead.
            _ => ocr_then_review(&app, "ocr"),
        }
    });
}

fn scrub_text_impl(app: &AppHandle, text: String, origin: &'static str, since: Instant) {
    let state = app.state::<AppState>();
    let analysis = match analyze_from(&state, &text, origin, Some(since)) {
        Ok(a) => a,
        Err(e) => return notify(app, &format!("Could not analyse the text: {e}")),
    };
    let review = state.settings.lock().review;
    if review {
        // Nothing is written back until the person approves it in the window.
        send_review(app, analysis);
    } else {
        let out = render_text(&state, &text, &analysis.spans);
        let maybe = analysis.spans.iter().filter(|s| !s.on).count();
        match app.clipboard().write_text(out.text) {
            Ok(_) => notify(app, &format!(
                "{} identifier{} replaced{}. Read it before you paste.",
                out.items.len(), if out.items.len() == 1 { "" } else { "s" },
                if maybe > 0 { format!(", {maybe} possible left in") } else { String::new() }
            )),
            Err(e) => notify(app, &format!("Could not write the clipboard: {e}")),
        }
        let _ = app.emit("status", status_of(&state));
    }
}

/// Run the helper (`capture` = drag a region now, `ocr` = image already on the
/// clipboard), then open the recognised text for review. Recognised text always
/// goes through review: OCR can misread a character and a rule can miss because of it.
fn ocr_then_review(app: &AppHandle, verb: &'static str) {
    let state = app.state::<AppState>();
    let Some(helper) = state.helper.lock().clone() else {
        return notify(app, if verb == "ocr" { "The clipboard has no text to clean." } else { "Screen capture is only available on macOS for now." });
    };
    if state.capturing.swap(true, Ordering::SeqCst) { return; }
    let app = app.clone();
    std::thread::spawn(move || {
        let mut t0 = Instant::now();
        let out = Command::new(&helper).arg(verb).stdin(Stdio::null()).output();
        // For an interactive capture the drag itself is the user's time, not ours.
        if verb == "capture" { t0 = Instant::now(); }
        let state = app.state::<AppState>();
        state.capturing.store(false, Ordering::SeqCst);
        let out = match out {
            Ok(o) => o,
            Err(e) => return notify(&app, &format!("Could not run the capture helper: {e}")),
        };
        match out.status.code() {
            Some(0) => {}
            Some(4) => return, // cancelled with Esc
            Some(2) => return notify(&app, "The clipboard has no text or image to clean."),
            Some(3) => return notify(&app, "No text was found in that capture. If it only showed your wallpaper, allow Screen Recording for Scotoma in System Settings."),
            _ => return notify(&app, &format!("Capture failed: {}", String::from_utf8_lossy(&out.stderr).trim())),
        }
        let text = String::from_utf8_lossy(&out.stdout).trim_end().to_string();
        match analyze_from(&state, &text, "screen", if verb == "capture" { None } else { Some(t0) }) {
            Ok(a) => {
                send_review(&app, a);
            }
            Err(e) => notify(&app, &format!("Could not analyse the capture: {e}")),
        }
    });
}

fn capture_impl(app: &AppHandle) { ocr_then_review(app, "capture") }

/// POST the recording to a speech server that is already running on this
/// machine, so the model stays loaded between utterances. Works with
/// whisper.cpp's server (`/inference`) and OpenAI-style
/// `/v1/audio/transcriptions`; append `#model=NAME` if the server wants one.
/// Only loopback addresses are accepted: audio cannot be sent off the machine.
fn parse_loopback(url: &str) -> Result<(std::net::SocketAddr, String, String, Option<String>), String> {
    let rest = url.trim().strip_prefix("http://").ok_or("speech server must be an http:// address on this machine")?;
    let (rest, model) = match rest.split_once("#model=") { Some((r, m)) => (r, Some(m.to_string())), None => (rest, None) };
    let (hostport, path) = match rest.find('/') { Some(i) => (&rest[..i], rest[i..].to_string()), None => (rest, "/".to_string()) };
    let with_port = if hostport.rsplit(':').next().map(|p| p.parse::<u16>().is_ok()).unwrap_or(false) && hostport.contains(':') { hostport.to_string() } else { format!("{hostport}:80") };
    use std::net::ToSocketAddrs;
    let addr = with_port.to_socket_addrs().map_err(|e| format!("{hostport}: {e}"))?.next().ok_or("no address")?;
    if !addr.ip().is_loopback() {
        return Err(format!("{hostport} is not this machine; refusing to send audio to it"));
    }
    Ok((addr, hostport.to_string(), path, model))
}

fn transcribe_http(url: &str, wav: &[u8]) -> Result<String, String> {
    use std::io::Read;
    let (addr, host, path, model) = parse_loopback(url)?;
    let boundary = format!("scotoma{:x}", std::process::id() as u64 * 2654435761);
    let mut body: Vec<u8> = Vec::with_capacity(wav.len() + 512);
    let mut field = |name: &str, value: &str| {
        body.extend_from_slice(format!("--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").as_bytes());
    };
    field("response_format", "json");
    field("temperature", "0");
    if let Some(m) = &model { field("model", m); }
    body.extend_from_slice(format!("--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\nContent-Type: audio/wav\r\n\r\n").as_bytes());
    body.extend_from_slice(wav);
    body.extend_from_slice(format!("\r\n--{boundary}--\r\n").as_bytes());

    let mut sock = std::net::TcpStream::connect_timeout(&addr, Duration::from_secs(3)).map_err(|e| format!("speech server not reachable at {host}: {e}"))?;
    let _ = sock.set_read_timeout(Some(Duration::from_secs(120)));
    let head = format!("POST {path} HTTP/1.1\r\nHost: {host}\r\nContent-Type: multipart/form-data; boundary={boundary}\r\nContent-Length: {}\r\nAccept: application/json\r\nConnection: close\r\n\r\n", body.len());
    sock.write_all(head.as_bytes()).and_then(|_| sock.write_all(&body)).map_err(|e| e.to_string())?;
    let mut raw = Vec::new();
    sock.read_to_end(&mut raw).map_err(|e| e.to_string())?;
    let split = raw.windows(4).position(|w| w == b"\r\n\r\n").ok_or("malformed reply from speech server")?;
    let headers = String::from_utf8_lossy(&raw[..split]).to_lowercase();
    let mut payload = raw[split + 4..].to_vec();
    if headers.contains("transfer-encoding: chunked") {
        let mut out = Vec::new();
        let mut i = 0;
        while let Some(n) = payload[i..].windows(2).position(|w| w == b"\r\n") {
            let size = usize::from_str_radix(String::from_utf8_lossy(&payload[i..i + n]).split(';').next().unwrap_or("").trim(), 16).unwrap_or(0);
            let start = i + n + 2;
            if size == 0 || start + size > payload.len() { break; }
            out.extend_from_slice(&payload[start..start + size]);
            i = start + size + 2;
            if i >= payload.len() { break; }
        }
        payload = out;
    }
    let status = headers.lines().next().unwrap_or("").to_string();
    let text = String::from_utf8_lossy(&payload).to_string();
    if !status.contains(" 200") {
        return Err(format!("speech server said: {} {}", status.trim(), text.chars().take(120).collect::<String>()));
    }
    match serde_json::from_str::<serde_json::Value>(&text) {
        Ok(v) => v.get("text").and_then(|t| t.as_str()).map(|t| t.trim().to_string()).ok_or_else(|| "speech server reply had no \"text\" field".to_string()),
        Err(_) => Ok(text.trim().to_string()), // plain-text reply
    }
}

fn sh_quote(s: &str) -> String { format!("'{}'", s.replace('\'', "'\\''")) }

/// Start recording the microphone (bring-your-own speech model).
fn dictate_start(app: &AppHandle) {
    let state = app.state::<AppState>();
    if state.settings.lock().transcribe_cmd.trim().is_empty() { return; }
    let Some(helper) = state.helper.lock().clone() else { return };
    let mut slot = state.recorder.lock();
    if slot.is_some() { return; }
    static N: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);
    let path = std::env::temp_dir().join(format!("scotoma-{}-{}.wav", std::process::id(), N.fetch_add(1, Ordering::SeqCst)));
    match Command::new(&helper).arg("record").arg(&path).stdin(Stdio::piped()).stdout(Stdio::null()).stderr(Stdio::piped()).spawn() {
        Ok(child) => *slot = Some((child, path)),
        Err(e) => { drop(slot); return notify(app, &format!("Could not start recording: {e}")); }
    }
    drop(slot);
    let _ = app.emit("status", status_of(&state));
}

/// Stop recording. `keep` = transcribe and review; otherwise throw it away.
fn dictate_stop(app: &AppHandle, keep: bool) {
    let state = app.state::<AppState>();
    let Some((mut child, path)) = state.recorder.lock().take() else { return };
    let _ = app.emit("status", status_of(&state));
    let cmd = state.settings.lock().transcribe_cmd.clone();
    let app = app.clone();
    std::thread::spawn(move || {
        if keep {
            if let Some(mut stdin) = child.stdin.take() { let _ = stdin.write_all(b"\n"); }
        } else {
            let _ = child.kill();
        }
        let done = child.wait_with_output();
        let t0 = Instant::now();
        let result = (|| -> Result<String, String> {
            if !keep { return Ok(String::new()); }
            let done = done.map_err(|e| e.to_string())?;
            if !done.status.success() {
                return Err(format!("recording failed: {}", String::from_utf8_lossy(&done.stderr).trim()));
            }
            if cmd.trim_start().starts_with("http") {
                let wav = std::fs::read(&path).map_err(|e| format!("could not read the recording: {e}"))?;
                return transcribe_http(&cmd, &wav);
            }
            let quoted = sh_quote(&path.to_string_lossy());
            let line = if cmd.contains("{audio}") { cmd.replace("{audio}", &quoted) } else { format!("{cmd} {quoted}") };
            // A login shell, so the command sees the same PATH as a terminal.
            let out = Command::new("/bin/sh").arg("-lc").arg(&line).stdin(Stdio::null()).output().map_err(|e| e.to_string())?;
            if !out.status.success() {
                let err = String::from_utf8_lossy(&out.stderr);
                return Err(format!("speech command failed: {}", err.trim().lines().last().unwrap_or("no output")));
            }
            Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
        })();
        // The audio is the one thing that touches the disk; remove it either way.
        let _ = std::fs::remove_file(&path);
        if !keep { return; }
        let state = app.state::<AppState>();
        match result {
            Ok(text) if text.is_empty() => notify(&app, "The speech command returned no text."),
            Ok(text) => match analyze_from(&state, &text, "voice", Some(t0)) {
                Ok(a) => { send_review(&app, a); }
                Err(e) => notify(&app, &format!("Could not analyse the transcript: {e}")),
            },
            Err(e) => notify(&app, &e),
        }
    });
}

/// Show the overlay empty and focused, ready for typing or for any dictation
/// tool that types into the focused field (Superwhisper, macOS Dictation).
fn blank_impl(app: &AppHandle) {
    *app.state::<AppState>().pending.lock() = None;
    let _ = app.emit("blank", ());
    show_window(app);
}

fn find_helper(app: &AppHandle) -> Option<PathBuf> {
    let mut v = Vec::new();
    if let Ok(p) = std::env::var("SCOTOMA_HELPER") { v.push(PathBuf::from(p)); }
    if let Ok(p) = app.path().resource_dir() { v.push(p.join("bin").join("scotoma-helper")); }
    v.push(PathBuf::from(env!("SCOTOMA_HELPER_DEV")));
    v.into_iter().find(|p| p.is_file())
}

fn restore_clipboard_impl(app: &AppHandle) {
    let state = app.state::<AppState>();
    let Ok(text) = app.clipboard().read_text() else { return notify(app, "The clipboard has no text to restore."); };
    let (out, n) = state.vault.lock().restore(&text);
    touch(&state);
    if n == 0 {
        return notify(app, "Nothing to restore: no remembered placeholders in the clipboard.");
    }
    match app.clipboard().write_text(out) {
        Ok(_) => notify(app, &format!("{n} original{} put back. The clipboard now holds patient information.", if n == 1 { "" } else { "s" })),
        Err(e) => notify(app, &format!("Could not write the clipboard: {e}")),
    }
}

#[tauri::command]
fn status(state: State<AppState>) -> Status { status_of(&state) }

#[tauri::command]
fn analyze(state: State<AppState>, text: String) -> Result<Analysis, String> {
    *state.pending.lock() = None;
    analyze_text(&state, &text)
}

/// The review that is waiting, if the window missed the event for it.
#[tauri::command]
fn pending(state: State<AppState>) -> Option<Analysis> { state.pending.lock().clone() }

#[tauri::command]
fn preview(state: State<AppState>, text: String, spans: Vec<UiSpan>) -> Preview { render_text(&state, &text, &spans) }

/// Approve: render and place the cleaned text on the clipboard.
#[tauri::command]
fn approve(app: AppHandle, state: State<AppState>, text: String, spans: Vec<UiSpan>) -> Result<Preview, String> {
    let out = render_text(&state, &text, &spans);
    app.clipboard().write_text(out.text.clone()).map_err(|e| e.to_string())?;
    *state.pending.lock() = None;
    let _ = app.emit("status", status_of(&state));
    Ok(out)
}

#[tauri::command]
fn capture(app: AppHandle) { capture_impl(&app) }

fn dictate_toggle(app: &AppHandle) {
    let state = app.state::<AppState>();
    if state.recorder.lock().is_some() {
        return dictate_stop(app, true);
    }
    if state.settings.lock().transcribe_cmd.trim().is_empty() {
        show_window(app);
        return notify(app, "Set a speech model in Scotoma's side panel first.");
    }
    dictate_start(app);
    // Recording has no other on-screen sign, so show the window with its red Stop button.
    show_window(app);
}

#[tauri::command]
fn dictate(app: AppHandle) { dictate_toggle(&app) }

#[tauri::command]
fn hide_window(app: AppHandle) {
    if let Some(w) = app.get_webview_window("main") { let _ = w.hide(); }
}

#[tauri::command]
fn read_clipboard(app: AppHandle) -> Result<String, String> {
    app.clipboard().read_text().map_err(|e| e.to_string())
}

#[tauri::command]
fn copy_text(app: AppHandle, text: String) -> Result<(), String> {
    app.clipboard().write_text(text).map_err(|e| e.to_string())
}

#[derive(Serialize)]
struct Restored { text: String, count: usize }

#[tauri::command]
fn restore_text(state: State<AppState>, text: String) -> Restored {
    let (text, count) = state.vault.lock().restore(&text);
    touch(&state);
    Restored { text, count }
}

#[tauri::command]
fn clear_vault(app: AppHandle, state: State<AppState>) -> Status {
    state.vault.lock().clear();
    let s = status_of(&state);
    let _ = app.emit("status", s.clone());
    s
}

fn apply_settings(state: &AppState, new: Settings) {
    {
        let mut sc = state.scrubber.lock();
        sc.config.strict = new.strict;
        // A user-set threshold wins; otherwise the loaded model's declared
        // default applies, then Config::default(). Clamped to the usable range;
        // 0.02 (the clinical operating point) is allowed exactly.
        let t = scotoma_core::effective_threshold(new.threshold, sc.model_suggested_threshold());
        sc.config.set_threshold(t.clamp(0.02, 0.98));
    }
    if let Some(p) = state.settings_path.lock().as_ref() {
        if let Some(dir) = p.parent() { let _ = std::fs::create_dir_all(dir); }
        // Settings only. No text, no spans, no vault ever touches the disk.
        let _ = std::fs::write(p, serde_json::to_string_pretty(&new).unwrap_or_default());
    }
    *state.settings.lock() = new;
}

#[tauri::command]
fn set_settings(app: AppHandle, state: State<AppState>, settings: Settings) -> Status {
    apply_settings(&state, settings);
    let s = status_of(&state);
    let _ = app.emit("status", s.clone());
    s
}

fn model_dirs(app: &AppHandle) -> Vec<PathBuf> {
    let mut v = Vec::new();
    if let Ok(p) = std::env::var("SCOTOMA_MODEL") { v.push(PathBuf::from(p)); }
    if let Ok(p) = app.path().app_data_dir() { v.push(p.join("model")); }
    if let Ok(p) = app.path().resource_dir() { v.push(p.join("models").join("default")); }
    v
}

fn load_model(app: AppHandle) {
    std::thread::spawn(move || {
        let state = app.state::<AppState>();
        #[cfg(feature = "onnx")]
        {
            let mut err = None;
            for dir in model_dirs(&app).into_iter().filter(|d| d.is_dir()) {
                match scotoma_core::model::OnnxDetector::load(&dir) {
                    Ok(det) => {
                        // The model may declare its own operating point
                        // (scotoma_threshold in config.json); it applies only
                        // while the user hasn't set a sensitivity.
                        let user = state.settings.lock().threshold;
                        let mut sc = state.scrubber.lock();
                        let t = scotoma_core::effective_threshold(user, det.suggested_threshold());
                        sc.set_model(Some(Box::new(det)));
                        sc.config.set_threshold(t.clamp(0.02, 0.98));
                        // Pay the first-inference cost now, not on the first hotkey.
                        let _ = sc.detect("Patient John Smith, MRN 1234567, seen 2024-01-01.");
                        drop(sc);
                        err = None;
                        break;
                    }
                    Err(e) => err = Some(format!("{}: {e}", dir.display())),
                }
            }
            *state.model_error.lock() = err;
        }
        #[cfg(not(feature = "onnx"))]
        {
            let _ = model_dirs(&app);
            *state.model_error.lock() = Some("built without model support".into());
        }
        let _ = app.emit("status", status_of(&state));
    });
}

fn main() {
    let scrub_key: Shortcut = HOTKEY_SCRUB.parse().expect("hotkey");
    let restore_key: Shortcut = HOTKEY_RESTORE.parse().expect("hotkey");
    let capture_key: Shortcut = HOTKEY_CAPTURE.parse().expect("hotkey");
    let blank_key: Shortcut = HOTKEY_BLANK.parse().expect("hotkey");
    let dictate_key: Shortcut = HOTKEY_DICTATE.parse().expect("hotkey");

    tauri::Builder::default()
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(move |app, shortcut, event| {
                    if event.state() != ShortcutState::Pressed { return; }
                    if shortcut == &scrub_key { scrub_clipboard_impl(app) }
                    else if shortcut == &restore_key { restore_clipboard_impl(app) }
                    else if shortcut == &capture_key { capture_impl(app) }
                    else if shortcut == &blank_key { blank_impl(app) }
                    else if shortcut == &dictate_key { dictate_toggle(app) }
                })
                .build(),
        )
        .manage(AppState {
            scrubber: Mutex::new(Scrubber::rules_only(Config::default())),
            vault: Mutex::new(Vault::new()),
            settings: Mutex::new(Settings::default()),
            touched: Mutex::new(Instant::now()),
            model_error: Mutex::new(None),
            settings_path: Mutex::new(None),
            helper: Mutex::new(None),
            capturing: AtomicBool::new(false),
            recorder: Mutex::new(None),
            pending: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            status, analyze, pending, preview, approve, capture, dictate, hide_window, read_clipboard, copy_text, restore_text, clear_vault, set_settings
        ])
        .setup(|app| {
            // A menu-bar utility: no Dock icon, and the overlay can sit above
            // full-screen apps.
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Accessory);

            let handle = app.handle().clone();
            let state = app.state::<AppState>();

            // Settings (never text) persist between runs.
            if let Ok(dir) = app.path().app_config_dir() {
                let path = dir.join("settings.json");
                let saved = std::fs::read_to_string(&path).ok().and_then(|s| serde_json::from_str::<Settings>(&s).ok());
                *state.settings_path.lock() = Some(path);
                if let Some(s) = saved { apply_settings(&state, s); }
            }
            let settings = state.settings.lock().clone();

            *state.helper.lock() = find_helper(&handle);
            let can_capture = state.helper.lock().is_some();

            for key in [HOTKEY_SCRUB, HOTKEY_RESTORE, HOTKEY_CAPTURE, HOTKEY_BLANK, HOTKEY_DICTATE] {
                if let Err(e) = app.global_shortcut().register(key) {
                    eprintln!("could not register {key}: {e}");
                }
            }

            let scrub = MenuItem::with_id(app, "scrub", "Clean selection or clipboard", true, Some(HOTKEY_SCRUB))?;
            let voice = MenuItem::with_id(app, "dictate", "Dictate (start / stop)", can_capture, Some(HOTKEY_DICTATE))?;
            let blank = MenuItem::with_id(app, "blank", "New blank note (type or dictate)", true, Some(HOTKEY_BLANK))?;
            let grab = MenuItem::with_id(app, "capture", "Capture screen region", can_capture, Some(HOTKEY_CAPTURE))?;
            let restore = MenuItem::with_id(app, "restore", "Restore originals in clipboard", true, Some(HOTKEY_RESTORE))?;
            let open = MenuItem::with_id(app, "open", "Open Scotoma", true, None::<&str>)?;
            let review = CheckMenuItem::with_id(app, "review", "Review before copying", true, settings.review, None::<&str>)?;
            let standins = CheckMenuItem::with_id(app, "standins", "Realistic stand-ins", true, settings.mode == Mode::Surrogate, None::<&str>)?;
            let strict = CheckMenuItem::with_id(app, "strict", "Strict mode", true, settings.strict, None::<&str>)?;
            let forget = MenuItem::with_id(app, "forget", "Forget remembered originals", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let sep = || PredefinedMenuItem::separator(app);
            let menu = Menu::with_items(app, &[&scrub, &grab, &voice, &blank, &restore, &sep()?, &open, &sep()?, &review, &standins, &strict, &sep()?, &forget, &quit])?;

            let mut tray = TrayIconBuilder::with_id("main").tooltip("Scotoma").menu(&menu).show_menu_on_left_click(true);
            if let Some(icon) = app.default_window_icon() { tray = tray.icon(icon.clone()); }
            tray.on_menu_event(move |app, event| {
                let state = app.state::<AppState>();
                let mut s = state.settings.lock().clone();
                match event.id().as_ref() {
                    "scrub" => return scrub_clipboard_impl(app),
                    "restore" => return restore_clipboard_impl(app),
                    "capture" => return capture_impl(app),
                    "blank" => return blank_impl(app),
                    "dictate" => return dictate_toggle(app),
                    "open" => return show_window(app),
                    "quit" => {
                        state.vault.lock().clear();
                        if let Some((mut c, path)) = state.recorder.lock().take() { let _ = c.kill(); let _ = std::fs::remove_file(path); }
                        return app.exit(0);
                    }
                    "forget" => state.vault.lock().clear(),
                    "review" => s.review = !s.review,
                    "standins" => s.mode = if s.mode == Mode::Tag { Mode::Surrogate } else { Mode::Tag },
                    "strict" => s.strict = !s.strict,
                    _ => return,
                }
                apply_settings(&state, s);
                let _ = app.emit("status", status_of(&state));
            }).build(app)?;

            // Keep the tray checkmarks in step with changes made in the window.
            {
                let (review, standins, strict) = (review.clone(), standins.clone(), strict.clone());
                let h = handle.clone();
                tauri::Listener::listen(&handle, "status", move |_| {
                    let s = h.state::<AppState>().settings.lock().clone();
                    let _ = review.set_checked(s.review);
                    let _ = standins.set_checked(s.mode == Mode::Surrogate);
                    let _ = strict.set_checked(s.strict);
                });
            }

            // Idle expiry for remembered originals.
            {
                let h = handle.clone();
                std::thread::spawn(move || loop {
                    std::thread::sleep(Duration::from_secs(20));
                    let state = h.state::<AppState>();
                    let mins = state.settings.lock().vault_minutes;
                    let idle = state.touched.lock().elapsed();
                    if mins > 0 && idle > Duration::from_secs(mins as u64 * 60) {
                        let mut v = state.vault.lock();
                        if !v.is_empty() {
                            v.clear();
                            drop(v);
                            let _ = h.emit("status", status_of(&state));
                        }
                    }
                });
            }

            load_model(handle.clone());
            show_window(&handle);
            Ok(())
        })
        .on_window_event(|window, event| {
            // Closing the window keeps the tray app alive.
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Scotoma");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn speech_server_must_be_this_machine() {
        assert!(parse_loopback("http://127.0.0.1:8080/inference").is_ok());
        assert!(parse_loopback("http://localhost:8000/v1/audio/transcriptions#model=whisper-1").is_ok());
        let (_, _, path, model) = parse_loopback("http://127.0.0.1:8000/v1/audio/transcriptions#model=turbo").unwrap();
        assert_eq!((path.as_str(), model.as_deref()), ("/v1/audio/transcriptions", Some("turbo")));
        assert!(parse_loopback("http://192.168.1.20:8080/inference").unwrap_err().contains("not this machine"));
        assert!(parse_loopback("http://8.8.8.8/inference").is_err());
        assert!(parse_loopback("https://127.0.0.1/inference").is_err());
    }
}
