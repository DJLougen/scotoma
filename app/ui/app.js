// Review window. Talks to the Rust side through nine commands and nothing else.
const { invoke } = window.__TAURI__.core;
const { listen } = window.__TAURI__.event;
const $ = (id) => document.getElementById(id);

const GROUP = {
  NAME: "person", DATE: "time", AGE: "time",
  PHONE: "contact", FAX: "contact", EMAIL: "contact", URL: "contact", IP: "contact",
  SSN: "ident", MRN: "ident", PLAN: "ident", ACCOUNT: "ident", LICENSE: "ident", VEHICLE: "ident", DEVICE: "ident", BIOMETRIC: "ident", ID: "ident",
  ADDRESS: "geo", LOCATION: "geo", ZIP: "geo", ORG: "org",
};
const PICKABLE = ["NAME", "DATE", "LOCATION", "ADDRESS", "PHONE", "ID", "ORG"];
const SOURCE = { rule: "rule", model: "model", propagated: "repeat of a detected name", manual: "added by you" };

let text = "";
let spans = [];          // {start,end,category,source,confidence,dob,on}  (UTF-16 offsets)
let settings = null;
let fresh = new Set();   // spans to animate once
let seq = 0;             // guards against out-of-order async replies

function toast(msg) {
  const t = $("toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), 2600);
}

function mac() { return /Mac/i.test(navigator.platform || navigator.userAgent); }
function prettyKey(k) {
  return k.replace("CmdOrCtrl", mac() ? "⌘" : "Ctrl").replace("Alt", mac() ? "⌥" : "Alt").split("+").join(mac() ? "" : "+");
}

function applyStatus(s) {
  settings = s.settings;
  const e = $("engine");
  if (s.model) { e.textContent = "rules + " + s.model.split("/").pop(); e.className = "chip ok"; e.title = "Detection model: " + s.model; }
  else { e.textContent = "rules only · no model"; e.className = "chip bad"; e.title = s.model_error || "No model folder found. Names without context will be missed. See README."; }
  $("vault-n").textContent = s.vault_entries;
  // s.threshold is the effective value (user override, else the model's
  // declared default); settings.threshold is null when following the model.
  $("threshold").value = Math.min(0.98, Math.max(0.02, +(1 - s.threshold).toFixed(2)));
  $("threshold-out").textContent = Math.round((1 - s.threshold) * 100) + "%" + (settings.threshold == null ? " (model default)" : "");
  $("threshold").disabled = !s.model;
  $("threshold-reset").hidden = !s.model || settings.threshold == null;
  $("strict").checked = settings.strict;
  $("review").checked = settings.review;
  document.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === settings.mode)));
  $("k-scrub").textContent = prettyKey(s.hotkey_scrub);
  $("k-restore").textContent = prettyKey(s.hotkey_restore);
  $("capture").hidden = $("k-capture-row").hidden = !s.capture_available;
  $("k-capture").textContent = prettyKey(s.hotkey_capture);
  const speech = (settings.transcribe_cmd || "").trim();
  $("speech-row").hidden = !s.capture_available;
  if (document.activeElement !== $("speech")) $("speech").value = settings.transcribe_cmd || "";
  $("dictate").hidden = !s.capture_available || !speech;
  $("dictate").textContent = s.dictating ? "Stop" : "Dictate";
  $("dictate").classList.toggle("live", s.dictating);
  $("k-hold-row").hidden = !(s.capture_available && speech);
  $("k-dictate").textContent = prettyKey(s.hotkey_dictate);
  $("k-blank").textContent = prettyKey(s.hotkey_blank);
}

function el(tag, cls, txt) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (txt != null) n.textContent = txt;
  return n;
}

// Render `str` with non-overlapping marks; each piece carries its offset so a
// DOM selection can be mapped back to text offsets.
function paint(host, str, marks, decorate) {
  host.textContent = "";
  host.classList.remove("empty");
  let pos = 0;
  const plain = (a, b) => { if (b > a) { const s = el("span", null, str.slice(a, b)); s.dataset.o = a; host.append(s); } };
  marks.forEach((m, i) => {
    if (m.start < pos) return;
    plain(pos, m.start);
    const k = el("mark", "g-" + GROUP[m.category], str.slice(m.start, m.end));
    k.dataset.o = m.start;
    decorate(k, m, i);
    host.append(k);
    pos = m.end;
  });
  plain(pos, str.length);
}

function renderOriginal() {
  paint($("original"), text, spans, (k, m, i) => {
    k.dataset.i = i;
    const maybe = !m.on && m.source !== "manual" && !m.touched;
    if (!m.on) k.classList.add(maybe ? "maybe" : "off");
    if (fresh.has(m)) k.classList.add("fresh");
    const conf = m.source === "model" ? ` · ${Math.round(m.confidence * 100)}%` : "";
    k.title = `${m.category} · ${SOURCE[m.source]}${conf}\n${m.on ? "Click to keep this in the text" : "Click to redact"}`;
  });
  fresh.clear();
}

function renderSide() {
  const on = spans.filter((s) => s.on);
  const maybe = spans.filter((s) => !s.on && !s.touched).length;
  $("n-on").textContent = on.length;
  $("n-maybe").textContent = maybe;
  $("maybe-box").classList.toggle("active", maybe > 0);
  $("maybe-note").hidden = maybe === 0;
  const counts = {};
  on.forEach((s) => (counts[s.category] = (counts[s.category] || 0) + 1));
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = rows.length ? rows[0][1] : 1;
  const bars = $("bars");
  const have = new Map([...bars.children].map((b) => [b.dataset.cat, b]));
  rows.forEach(([cat, n], idx) => {
    let b = have.get(cat);
    if (!b) {
      b = el("div", "bar g-" + GROUP[cat]);
      b.dataset.cat = cat;
      b.append(el("span", "lbl", cat), el("span", "track"), el("span", "n"));
      b.children[1].append(el("span", "fill"));
      bars.append(b);
    }
    have.delete(cat);
    b.style.order = idx;
    b.lastChild.textContent = n;
    requestAnimationFrame(() => (b.children[1].firstChild.style.width = (100 * n) / max + "%"));
  });
  have.forEach((b) => b.remove());
  $("approve").disabled = !text;
}

async function refreshPreview() {
  const my = ++seq;
  if (!text) { $("cleaned").textContent = "Cleaned text appears here."; $("cleaned").classList.add("empty"); return; }
  const p = await invoke("preview", { text, spans });
  if (my !== seq) return;
  paint($("cleaned"), p.text, p.items, () => {});
  listen("blank", () => {
  document.querySelector('.tabs button[data-tab="clean"]').click();
  ++seq; $("input").value = ""; reset(); setTimeout(() => $("input").focus(), 60);
});
if (mac()) document.body.classList.add("mac");
invoke("status").then(applyStatus);
invoke("pending").then((a) => { if (a && !text) { ++seq; show(a); } });
}

function show(analysis) {
  text = analysis.text;
  spans = analysis.spans;
  spans.forEach((s) => fresh.add(s));
  $("input").hidden = true; $("original").hidden = false; $("edit").hidden = false;
  const bits = [];
  if (analysis.origin && analysis.origin !== "typed") bits.push(analysis.origin);
  if (analysis.acquire_ms) bits.push(`read ${analysis.acquire_ms} ms`);
  if (analysis.detect_ms != null) bits.push(`detect ${analysis.detect_ms} ms`);
  bits.push("click a highlight to toggle, select text to add");
  $("orig-hint").textContent = bits.join(" · ");
  renderOriginal(); renderSide(); refreshPreview();
}

async function analyze(str) {
  if (!str.trim()) return reset();
  const my = ++seq;
  try {
    const a = await invoke("analyze", { text: str });
    if (my === seq) show(a);
  } catch (e) { toast("Could not analyse: " + e); }
}

function reset() {
  text = ""; spans = [];
  $("input").hidden = false; $("original").hidden = true; $("edit").hidden = true; $("seltool").hidden = true;
  $("orig-hint").textContent = "stays on this machine";
  renderSide(); refreshPreview();
}

// --- interactions -----------------------------------------------------------
$("original").addEventListener("click", (ev) => {
  const k = ev.target.closest("mark");
  if (!k || !window.getSelection().isCollapsed) return;
  const m = spans[+k.dataset.i];
  m.on = !m.on; m.touched = true;
  renderOriginal(); renderSide(); refreshPreview();
});

function offsetOf(node, off) {
  const host = node.nodeType === 3 ? node.parentElement : node;
  const piece = host.closest("[data-o]");
  return piece ? +piece.dataset.o + (node.nodeType === 3 ? off : 0) : null;
}

let pending = null;
document.addEventListener("selectionchange", () => {
  const sel = window.getSelection();
  const tool = $("seltool");
  if (tool.contains(document.activeElement)) return;
  if (sel.isCollapsed || !sel.rangeCount || !$("original").contains(sel.anchorNode) || !$("original").contains(sel.focusNode)) { tool.hidden = true; pending = null; return; }
  let a = offsetOf(sel.anchorNode, sel.anchorOffset), b = offsetOf(sel.focusNode, sel.focusOffset);
  if (a == null || b == null || a === b) { tool.hidden = true; return; }
  if (a > b) [a, b] = [b, a];
  while (a < b && /\s/.test(text[a])) a++;
  while (b > a && /\s/.test(text[b - 1])) b--;
  if (a === b) return;
  pending = { start: a, end: b };
  const r = sel.getRangeAt(0).getBoundingClientRect(), host = tool.parentElement.getBoundingClientRect();
  tool.hidden = false;
  tool.style.left = Math.max(8, Math.min(r.left - host.left, host.width - tool.offsetWidth - 8)) + "px";
  tool.style.top = Math.min(r.bottom - host.top + 6, host.height - tool.offsetHeight - 8) + "px";
});

function addManual() {
  if (!pending) return;
  let { start, end } = pending;
  // Absorb anything the selection overlaps.
  spans = spans.filter((s) => {
    if (s.start < end && start < s.end) { if (s.on) { start = Math.min(start, s.start); end = Math.max(end, s.end); } return false; }
    return true;
  });
  const m = { start, end, category: $("selcat").value, source: "manual", confidence: 1, dob: false, on: true, touched: true };
  spans.push(m); spans.sort((x, y) => x.start - y.start);
  fresh.add(m); pending = null;
  window.getSelection().removeAllRanges(); $("seltool").hidden = true;
  renderOriginal(); renderSide(); refreshPreview();
}
$("selgo").addEventListener("click", addManual);

let timer;
$("input").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => analyze($("input").value), 120); });
$("edit").addEventListener("click", () => { $("input").value = text; reset(); $("input").focus(); });
$("paste").addEventListener("click", async () => {
  try { const t = await invoke("read_clipboard"); $("input").value = t; analyze(t); } catch (e) { toast("Clipboard has no text."); }
});

async function approve() {
  if (!text) return;
  try {
    const p = await invoke("approve", { text, spans });
    const left = spans.filter((s) => !s.on && !s.touched).length;
    toast(`Copied. ${p.items.length} replaced${left ? `, ${left} possible left in` : ""}.`);
    // Overlay behaviour: get out of the way so the paste lands where you were.
    setTimeout(() => invoke("hide_window"), 700);
  } catch (e) { toast("Could not copy: " + e); }
}
$("approve").addEventListener("click", approve);
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") { ev.preventDefault(); invoke("hide_window"); return; }
  if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter") { ev.preventDefault(); approve(); }
  if (ev.key === "r" && pending && !ev.metaKey && !ev.ctrlKey && document.activeElement.tagName !== "TEXTAREA") { ev.preventDefault(); addManual(); }
});

async function saveSettings(patch, reanalyze) {
  applyStatus(await invoke("set_settings", { settings: { ...settings, ...patch } }));
  if (!text) return;
  if (reanalyze) analyze(text); else refreshPreview();
}
document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => saveSettings({ mode: b.dataset.mode }, false)));
$("strict").addEventListener("change", (e) => saveSettings({ strict: e.target.checked }, true));
$("review").addEventListener("change", (e) => saveSettings({ review: e.target.checked }, false));
$("threshold").addEventListener("input", (e) => ($("threshold-out").textContent = Math.round(e.target.value * 100) + "%"));
$("threshold").addEventListener("change", (e) => saveSettings({ threshold: +(1 - e.target.value).toFixed(2) }, true));
$("threshold-reset").addEventListener("click", () => saveSettings({ threshold: null }, true));
$("capture").addEventListener("click", () => invoke("capture"));
$("dictate").addEventListener("click", () => invoke("dictate"));
$("speech").addEventListener("change", (e) => saveSettings({ transcribe_cmd: e.target.value.trim() }, false));
$("forget").addEventListener("click", async () => { applyStatus(await invoke("clear_vault")); toast("Remembered originals wiped."); refreshRestore(); });

// --- tabs & restore ----------------------------------------------------------
document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".tabs button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
  $("clean").hidden = b.dataset.tab !== "clean";
  $("restore").hidden = b.dataset.tab !== "restore";
}));
let restored = "";
async function refreshRestore() {
  const v = $("rinput").value;
  if (!v.trim()) { $("routput").textContent = "Restored text appears here."; $("routput").classList.add("empty"); $("rcount").textContent = ""; $("rcopy").disabled = true; return; }
  const r = await invoke("restore_text", { text: v });
  restored = r.text;
  $("routput").textContent = r.text; $("routput").classList.remove("empty");
  $("rcount").textContent = r.count ? `${r.count} put back · contains patient information` : "no known placeholders found";
  $("rcopy").disabled = false;
}
$("rinput").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(refreshRestore, 250); });
$("rpaste").addEventListener("click", async () => { try { $("rinput").value = await invoke("read_clipboard"); refreshRestore(); } catch (e) { toast("Clipboard has no text."); } });
$("rcopy").addEventListener("click", async () => { await invoke("copy_text", { text: restored }); toast("Restored text copied. It contains patient information."); });

// --- boot ----------------------------------------------------------------------
PICKABLE.forEach((c) => $("selcat").append(new Option(c[0] + c.slice(1).toLowerCase(), c)));
listen("status", (e) => applyStatus(e.payload));
listen("review", (e) => {
  document.querySelector('.tabs button[data-tab="clean"]').click();
  ++seq; show(e.payload);
});
invoke("status").then(applyStatus);
invoke("pending").then((a) => { if (a && !text) { ++seq; show(a); } });
renderSide();
