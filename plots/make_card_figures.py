#!/usr/bin/env python3
"""Marketing figures for the Scotoma model card / README.

Every plotted number is read from bench/results/**/reports.json (or the
SEALED*_RESULTS.md tables) and asserted before it is drawn. Nothing is
hand-typed into a figure.

    .venv/bin/python plots/make_card_figures.py

Writes PNGs to release/hf/scotoma-small/assets/ and copies them to
docs/img/. Prints every plotted value as JSON at the end.

before_after.png additionally renders the example note to a clean PNG (PIL),
runs the release `scotoma` binary (redact-file) on it, and re-OCRs the result
with `scotoma-helper ocr-boxes`; it is skipped (and any stale PNG removed) if
a planted string or fragment survives or clinical text is over-redacted.
"""
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from math import comb
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle, Rectangle

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "bench" / "results"
ASSETS = ROOT / "release" / "hf" / "scotoma-small" / "assets"
DOCS_IMG = ROOT / "docs" / "img"
ICON = ROOT / "app" / "src-tauri" / "icons" / "128x128@2x.png"

# --- brand -------------------------------------------------------------
TEAL, TEAL_HI = "#0F9D8A", "#14B8A6"
AMBER, AMBER_HI = "#E8930C", "#F5B545"
BLUE = "#3E9BD6"      # GLiNER family
PLUM = "#B469AE"      # Stanford
NAVY = "#3D6FB4"      # privacy-filter
RUST = "#C1543C"      # Presidio
GREY = "#9AA0A6"      # ai4privacy / piiranha / generic
INK = "#1d1d22"
SUB = "#6b6f76"
PAGE_TOP, PAGE_BOT = "#ffffff", "#eef1f2"
INK_D, SUB_D = "#f2f4f6", "#9aa4ae"
PAGE_D_TOP, PAGE_D_BOT = "#1b2126", "#11161a"
CARD_D = "#20272d"
FOOT = "synthetic clinical notes with planted identifiers · sealed, pre-registered, scored once"

FONTS = [f.name for f in font_manager.fontManager.ttflist]
for _cand in ("Helvetica Neue", "SF Pro Display", "SF Pro", "Avenir Next",
              "Avenir", "Inter"):
    if _cand in FONTS:
        plt.rcParams["font.family"] = _cand
        break
plt.rcParams["axes.unicode_minus"] = False

PLOTTED = {}  # every value that ends up on a figure


def darken(hexcolor, f=0.6):
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def tint(hexcolor, f=0.85):
    """Blend towards white."""
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r + (255 - r) * f),
                            int(g + (255 - g) * f), int(b + (255 - b) * f))


def report(run_dir, system):
    return json.loads((RES / run_dir / "reports.json").read_text())[system]


def leak_rate(rep):
    return 100.0 * rep["docs_with_leak"] / rep["docs"]


def exact_p(b, c):
    """Exact two-sided McNemar p; same definition as bench/mcnemar.py."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


def mcnemar_counts(csv_path, A, B):
    leak = defaultdict(lambda: [False, False])
    for r in csv.DictReader(open(csv_path)):
        d = r["item"].rsplit("#", 1)[0]
        assert r[A] != "" and r[B] != "", f"missing outcome on {r['item']}"
        leak[d][0] |= r[A] == "0"
        leak[d][1] |= r[B] == "0"
    a_only = sum(1 for v in leak.values() if v[0] and not v[1])
    b_only = sum(1 for v in leak.values() if v[1] and not v[0])
    both = sum(1 for v in leak.values() if v[0] and v[1])
    return len(leak), a_only, b_only, both


# --- shared chrome ------------------------------------------------------
def brand_fig(w_in, h_in, title, dark=False, foot=FOOT):
    """Page gradient + header strip (icon, wordmark, one title line).
    Method notes live in the footnote — no subtitle per style pass."""
    face = "#11161a" if dark else "white"
    fig = plt.figure(figsize=(w_in, h_in), dpi=200, facecolor=face)
    bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
    bg.set_xlim(0, 1)
    bg.set_ylim(0, 1)
    bg.axis("off")
    top = np.array(matplotlib.colors.to_rgb(
        PAGE_D_TOP if dark else PAGE_TOP))
    bot = np.array(matplotlib.colors.to_rgb(
        PAGE_D_BOT if dark else PAGE_BOT))
    t = np.linspace(0, 1, 256)[:, None]
    img = (top[None, :] * (1 - t) + bot[None, :] * t)[:, None, :]
    bg.imshow(img, extent=[0, 1, 0, 1], aspect="auto",
              interpolation="bicubic")

    ink = INK_D if dark else INK
    sub = SUB_D if dark else SUB
    hdr = 1 - 0.55 / h_in
    iw = 0.42 / w_in
    ih = 0.42 / h_in
    ax_ic = fig.add_axes([0.030, hdr - ih / 2, iw, ih], zorder=5)
    ax_ic.imshow(plt.imread(ICON))
    ax_ic.axis("off")
    xw = 0.030 + iw + 0.012
    fig.text(xw, hdr, "Scotoma", fontsize=12.5, fontweight="bold",
             color=TEAL if not dark else TEAL_HI, va="center")
    tx = xw + 0.110
    fig.text(tx, hdr, title, fontsize=16, fontweight="bold",
             color=ink, va="center")
    if foot:
        fig.text(0.985, 0.014, foot, ha="right", va="bottom",
                 fontsize=6.5, color=sub, style="italic")
    return fig


def _ext(artist, renderer):
    try:
        bb = artist.get_window_extent(renderer=renderer)
    except Exception:
        return None
    if bb is None or not np.isfinite([bb.x0, bb.x1, bb.y0, bb.y1]).all():
        return None
    if bb.width <= 0 or bb.height <= 0:
        return None
    return bb


def overlap_check(fig, name):
    """Fail if any visible text intersects another text, a patch it is not
    fully inside (chips/cards/bars own their inner labels), or the figure
    edge. Prints offending pairs."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox

    texts = []
    for t in fig.texts:
        bb = _ext(t, renderer)
        if bb and t.get_text().strip() and t.get_visible():
            texts.append((bb, f"fig:{t.get_text()[:38]!r}"))
    for ax in fig.axes:
        for t in [ax.title] + list(ax.texts):
            bb = _ext(t, renderer)
            if bb and t.get_text().strip() and t.get_visible():
                texts.append((bb, f"ax:{t.get_text()[:38]!r}"))
        if ax.axison:
            for t in (ax.get_xticklabels() + ax.get_yticklabels()):
                bb = _ext(t, renderer)
                if bb and t.get_text().strip() and t.get_visible():
                    texts.append((bb, f"tick:{t.get_text()[:38]!r}"))

    solids = []
    for p in fig.patches:
        bb = _ext(p, renderer)
        if bb:
            solids.append((bb, "figpatch"))
    for ax in fig.axes:
        for p in ax.patches:
            if isinstance(p, FancyArrowPatch):
                continue  # annotation leaders intentionally meet text
            bb = _ext(p, renderer)
            if bb:
                solids.append((bb, "axpatch"))

    def hits(a, b, pad=0.5):
        return (a.x0 < b.x1 + pad and a.x1 > b.x0 - pad and
                a.y0 < b.y1 + pad and a.y1 > b.y0 - pad)

    bad = []
    for i, (ba, da) in enumerate(texts):
        if (ba.x0 < canvas.x0 + 2 or ba.x1 > canvas.x1 - 2 or
                ba.y0 < canvas.y0 + 2 or ba.y1 > canvas.y1 - 2):
            bad.append(f"{da} crosses figure edge")
        for bb, db in texts[i + 1:]:
            if hits(ba, bb):
                bad.append(f"{da} × {db}")
        for pb, _pd in solids:
            if hits(ba, pb):
                if da.startswith("tick:"):
                    continue  # ticks sit on their axis/baseline by design

                inside = (pb.x0 - 2 <= ba.x0 and ba.x1 <= pb.x1 + 2 and
                          pb.y0 - 2 <= ba.y0 and ba.y1 <= pb.y1 + 2)
                if not inside:
                    bad.append(f"{da} crosses patch")
    if bad:
        raise AssertionError(
            f"{name}: {len(bad)} overlaps:\n  " + "\n  ".join(bad[:60]))


def card(fig, rect, dark=False, r=0.014):
    """Rounded white content card with a soft shadow."""
    x, y, w, h = rect
    shadow = FancyBboxPatch((x + 0.004, y - 0.006), w, h,
                            boxstyle=f"round,pad=0,rounding_size={r}",
                            facecolor="#00000022" if not dark else "#00000066",
                            edgecolor="none", transform=fig.transFigure,
                            zorder=-4)
    fig.patches.append(shadow)
    cardp = FancyBboxPatch((x, y), w, h,
                           boxstyle=f"round,pad=0,rounding_size={r}",
                           facecolor=CARD_D if dark else "white",
                           edgecolor="#e2e5e8" if not dark else "#2c343b",
                           linewidth=1.0, transform=fig.transFigure,
                           zorder=-3)
    fig.patches.append(cardp)


def chip(fig, x, y, text, sub="", color=TEAL, dark=False, w=0.150, h=0.085):
    """Coloured callout chip (figure coords)."""
    fig.patches.append(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.016",
        facecolor=tint(color, 0.0 if dark else 0.0),
        edgecolor="none", transform=fig.transFigure, zorder=4))
    fig.text(x + w / 2, y + h * (0.62 if sub else 0.5), text,
             ha="center", va="center", fontsize=13, fontweight="bold",
             color="white", zorder=5)
    if sub:
        fig.text(x + w / 2, y + h * 0.26, sub, ha="center", va="center",
                 fontsize=6.6, color="#ffffffcc", zorder=5)


def rbarh(ax, y, width, height, color, glow=False, x0=0.0):
    """Rounded horizontal bar from x0 to x0+width. Rounding is clamped to
    1/3 of the bar length so tiny bars never render as blobs."""
    w = max(width, 1e-9)
    r = min(height * 0.5, abs(w) * 0.33)
    if glow:
        ax.add_patch(FancyBboxPatch(
            (x0, y - height / 2 - height * 0.22), w, height * 1.44,
            boxstyle=f"round,pad=0,rounding_size={r}",
            facecolor=TEAL_HI, alpha=0.28, edgecolor="none", zorder=2))
    ax.add_patch(FancyBboxPatch(
        (x0, y - height / 2), w, height,
        boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=color, edgecolor="none", zorder=3))


def vbar(ax, x, height_v, width, color):
    r = min(width * 0.42, max(height_v, 1e-9) * 0.33, 0.16)
    ax.add_patch(FancyBboxPatch(
        (x - width / 2, 0), width, max(height_v, 1e-6),
        boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=color, edgecolor="none", zorder=3))


def card_axes(fig, rect, dark=False, pad=0.012):
    card(fig, rect, dark=dark)
    x, y, w, h = rect
    ax = fig.add_axes([x + pad, y + pad * 0.8, w - 2 * pad, h - 2 * pad])
    ax.set_facecolor("none")
    return ax


def style_ax(ax, dark=False):
    ax.set_facecolor("none")
    col = SUB_D if dark else SUB
    for s in ax.spines.values():
        s.set_color("#d9dde1" if not dark else "#3a444c")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=col, labelsize=8)


def save(fig, name):
    ASSETS.mkdir(parents=True, exist_ok=True)
    DOCS_IMG.mkdir(parents=True, exist_ok=True)
    overlap_check(fig, name)
    out = ASSETS / name
    fig.savefig(out, facecolor=fig.get_facecolor())
    shutil.copy2(out, DOCS_IMG / name)
    print(f"wrote {out.relative_to(ROOT)} (+ docs/img/{name})",
          file=sys.stderr)


def tip_label(ax, x, y, text, color, fs=8):
    ax.text(x, y, text, va="center", ha="left", fontsize=fs,
            color=color, fontweight="bold", clip_on=False, zorder=6)


# ---------------------------------------------------------------- figure 1
def load_hero_data():
    ours = report("sealed3/clin3_test_ours", "ours")
    rours = report("sealed3/clin3_test_ours", "rules+ours")
    oml10 = report("sealed3/clin3_test_oml", "openmed-large-t0.1")
    roml10 = report("sealed3/clin3_test_oml", "rules+openmed-large-t0.1")
    oml35 = report("sealed3/clin3_test_oml", "openmed-large")
    roml35 = report("sealed3/clin3_test_oml", "rules+openmed-large")
    n = rours["docs"]

    assert (rours["docs_with_leak"], roml10["docs_with_leak"],
            roml35["docs_with_leak"]) == (2, 26, 101)
    assert (ours["docs_with_leak"], oml10["docs_with_leak"],
            oml35["docs_with_leak"]) == (4, 407, 680)
    assert n == 7108

    docs, only_ours, only_oml, both = mcnemar_counts(
        RES / "sealed3" / "clin3_test_all_responses.csv",
        "rules+ours", "rules+openmed-large-t0.1")
    p = exact_p(only_ours, only_oml)
    assert (docs, only_ours, only_oml, both) == (7108, 1, 25, 1)
    assert abs(p - 8.047e-07) / 8.047e-07 < 0.01, p

    md = (RES / "SEALED3_RESULTS.md").read_text()
    m = re.search(r"about (\d+(?:\.\d+)?) vs about (\d+) CPU-seconds", md)
    cpu_ours, cpu_oml = float(m.group(1)), float(m.group(2))
    m = re.search(r"about (\d+) ms vs about (\d+) ms per note", md)
    ms_ours, ms_oml = float(m.group(1)), float(m.group(2))
    assert (cpu_ours, cpu_oml) == (0.2, 4.0) and (ms_ours, ms_oml) == (20.0, 240.0)

    PLOTTED["hero"] = {
        "n": n, "rules": {"ours": 2, "oml_t0.10": 26, "oml_t0.35": 101},
        "alone": {"ours": 4, "oml_t0.10": 407, "oml_t0.35": 680},
        "mcnemar": {"only_ours": only_ours, "only_oml": only_oml,
                    "both": both, "p": p},
        "cpu_s_per_note": {"ours": cpu_ours, "oml": cpu_oml},
        "ms_per_note_mac": {"ours": ms_ours, "oml": ms_oml},
        "ratio_leaks": roml10["docs_with_leak"] / rours["docs_with_leak"],
        "ratio_cpu": cpu_oml / cpu_ours,
    }
    return dict(ours=ours, rours=rours, oml10=oml10, roml10=roml10,
                oml35=oml35, roml35=roml35, n=n, p=p,
                cpu_ours=cpu_ours, cpu_oml=cpu_oml,
                ms_ours=ms_ours, ms_oml=ms_oml)


def draw_hero(d, dark=False):
    n = d["n"]
    fig = brand_fig(10, 6.4, f"Leaked notes out of {n:,}", dark=dark,
                    foot="synthetic clinical notes · sealed, pre-registered, "
                         "scored once · same notes, same scorer · "
                         "exact McNemar p = 8 × 10⁻⁷")
    ink = INK_D if dark else INK
    sub = SUB_D if dark else SUB
    teal = TEAL if not dark else TEAL_HI

    card(fig, (0.028, 0.055, 0.555, 0.80), dark=dark)
    card(fig, (0.610, 0.055, 0.365, 0.50), dark=dark)
    # single big callout
    chip(fig, 0.610, 0.605,
         f"{d['roml10']['docs_with_leak'] // d['rours']['docs_with_leak']}× "
         "fewer leaked notes",
         "vs rules + OpenMed-L @0.10 · p = 8 × 10⁻⁷",
         color=teal, dark=dark, w=0.365, h=0.115)

    def leak_panel(rect, title, rows, xmax):
        ax = card_axes(fig, rect, dark=dark, pad=0.010)
        ax.set_position([rect[0] + 0.115, rect[1] + 0.015,
                         rect[2] - 0.135, rect[3] - 0.055])
        ys = np.arange(len(rows))
        for y, (cnt, col, lab, glow) in zip(ys, rows):
            rbarh(ax, y, cnt, 0.55, col, glow=glow)
            tip_label(ax, cnt + xmax * 0.02, y, str(cnt), darken(col), fs=10)
        ax.set_yticks(ys)
        ax.set_yticklabels([r[2] for r in rows], fontsize=8.5, color=ink)
        ax.set_title(title, loc="left", fontsize=9.5, fontweight="bold",
                     color=sub, pad=6)
        ax.set_xlim(0, xmax)
        ax.set_xticks([])
        style_ax(ax, dark)
        ax.spines[["bottom", "left"]].set_visible(False)
        ax.invert_yaxis()

    ow, ro = d["rours"], d["roml10"]
    leak_panel((0.028, 0.465, 0.555, 0.39), "+ Scotoma rules", [
        (ow["docs_with_leak"], teal, "Scotoma-small", True),
        (ro["docs_with_leak"], AMBER, "OpenMed-L @0.10", False),
        (d["roml35"]["docs_with_leak"], AMBER_HI, "OpenMed-L @0.35", False),
    ], 118)
    leak_panel((0.028, 0.055, 0.555, 0.39), "model alone", [
        (d["ours"]["docs_with_leak"], teal, "Scotoma-small", True),
        (d["oml10"]["docs_with_leak"], AMBER, "OpenMed-L @0.10", False),
        (d["oml35"]["docs_with_leak"], AMBER_HI, "OpenMed-L @0.35", False),
    ], 780)

    # compute panel: log bars, plain rectangles (rounding distorts on log x)
    ax_c = card_axes(fig, (0.610, 0.055, 0.365, 0.50), dark=dark, pad=0.012)
    ax_c.set_position([0.700, 0.105, 0.255, 0.375])
    vals = [d["cpu_oml"], d["cpu_ours"]]
    ys = np.array([0.72, 0.30])
    cols = [AMBER, teal]
    for y, v, c in zip(ys, vals, cols):
        ax_c.add_patch(Rectangle((0.12, y - 0.09), v, 0.18,
                                 facecolor=c, edgecolor="none", zorder=3))
        tip_label(ax_c, (0.12 + v) * 1.18, y, f"{v:g} s", darken(c), fs=9)
    ax_c.set_yticks(ys)
    ax_c.set_yticklabels(["OpenMed-L", "Scotoma-small"], fontsize=8.5,
                       color=ink)
    ax_c.set_xscale("log")
    ax_c.set_xlim(0.12, 30)
    ax_c.set_ylim(0.0, 1.0)
    ax_c.xaxis.set_major_locator(
        matplotlib.ticker.FixedLocator([0.2, 0.5, 1, 2, 5]))
    ax_c.xaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:g}"))
    ax_c.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax_c.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax_c.set_title("CPU-s / note (log)", loc="left", fontsize=9.5,
                   fontweight="bold", color=sub, pad=6)
    style_ax(ax_c, dark)
    ax_c.spines[["bottom", "left"]].set_visible(False)
    return fig



def fig_hero():
    d = load_hero_data()
    save(draw_hero(d, dark=False), "hero.png")
    save(draw_hero(d, dark=True), "hero_dark.png")


# ---------------------------------------------------------------- figure 2
def fig_field():
    field = [
        ("Scotoma-small v1", TEAL, "sealed2/clin2_sealed", "ours-v1",
         "rules+ours-v1"),
        ("OpenMed-large @0.10", AMBER, "sealed2/clin2_sealed_openmed-large_t0.1",
         "openmed-large-t0.1", "rules+openmed-large-t0.1"),
        ("OpenMed-small @0.02", AMBER_HI, "sealed2/clin2_sealed_openmed_t0.02",
         "openmed-t0.02", "rules+openmed-t0.02"),
        ("Stanford @0.10", PLUM, "sealed2/clin2_sealed_stanford_t0.1",
         "stanford-t0.1", "rules+stanford-t0.1"),
        ("nvidia/gliner-PII", BLUE, "sealed2/clin2_sealed", "gliner-nvidia",
         "rules+gliner-nvidia"),
        ("gliner-pii-edge", BLUE, "sealed2/clin2_sealed", "gliner-edge",
         "rules+gliner-edge"),
        ("gliner-pii-large", BLUE, "sealed2/clin2_sealed", "gliner-large",
         "rules+gliner-large"),
        ("gliner-pii-base", BLUE, "sealed2/clin2_sealed", "gliner-base",
         "rules+gliner-base"),
        ("openai/privacy-filter", NAVY, "sealed2/clin2_sealed", "privacy-filter",
         "rules+privacy-filter"),
        ("Microsoft Presidio", RUST, "sealed2/clin2_sealed", "presidio",
         "rules+presidio"),
        ("ai4privacy en", GREY, "sealed2/clin2_sealed", "ai4privacy-en",
         "rules+ai4privacy-en"),
        ("ai4privacy cat", GREY, "sealed2/clin2_sealed", "ai4privacy-cat",
         "rules+ai4privacy-cat"),
        ("iiiorg/piiranha-v1", GREY, "sealed2/clin2_sealed", "piiranha",
         "rules+piiranha"),
    ]
    rows = []
    for name, col, d, alone_s, rules_s in field:
        a, r = report(d, alone_s), report(d, rules_s)
        assert a["docs"] == r["docs"] == 860
        rows.append((name, col, leak_rate(a), leak_rate(r)))

    byname = {r[0]: r for r in rows}
    assert byname["Scotoma-small v1"][2:] == (5 / 860 * 100, 2 / 860 * 100)
    assert abs(byname["OpenMed-large @0.10"][3] - 5 / 860 * 100) < 1e-9
    assert abs(byname["OpenMed-small @0.02"][3] - 5 / 860 * 100) < 1e-9
    assert abs(byname["Stanford @0.10"][3] - 46 / 860 * 100) < 1e-9

    rows.sort(key=lambda r: r[3])  # ascending +rules rate → top after invert
    PLOTTED["field"] = {r[0]: {"alone_pct": round(r[2], 3),
                               "rules_pct": round(r[3], 3)} for r in rows}

    fig = brand_fig(10, 8.4, "The full field — sealed 2",
                    foot="synthetic clinical notes · sealed, pre-registered, "
                         "scored once · % of 860 notes leaking ≥1 identifier · "
                         "familiar formats")
    ax = card_axes(fig, (0.028, 0.055, 0.945, 0.80), pad=0.02)
    ax.set_position([0.215, 0.095, 0.68, 0.685])

    h = 0.36
    ys = np.arange(len(rows))
    for y, (name, col, alone, rules) in zip(ys, rows):
        glow = name.startswith("Scotoma")
        rbarh(ax, y + h / 2 + 0.02, alone, h,
              col if not glow else tint(TEAL, 0.55), glow=False)
        rbarh(ax, y - h / 2 - 0.02, rules, h, col, glow=glow)
        tip_label(ax, alone + 1.4, y + h / 2 + 0.02, f"{alone:.1f}",
                  darken(col, 0.75))
        tip_label(ax, rules + 1.4, y - h / 2 - 0.02, f"{rules:.1f}",
                  darken(col))
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=9.5, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75])
    ax.set_xlabel("% of notes", fontsize=9, color=SUB)
    style_ax(ax)

    handles = [Rectangle((0, 0), 1, 1, facecolor="#bbbbbb"),
               Rectangle((0, 0), 1, 1, facecolor="#bbbbbb", alpha=0.45)]
    fig.legend(handles, ["+ Scotoma rules", "model alone"], loc="upper right",
               bbox_to_anchor=(0.965, 0.895), ncol=1, frameon=False,
               fontsize=8.5)
    save(fig, "field.png")



def fig_speed():
    ms = {
        "Scotoma-small v1": report("sealed2/clin2_sealed",
                                   "rules+ours-v1")["ms_per_doc"],
        "OpenMed-large @0.10": report(
            "sealed2/clin2_sealed_openmed-large_t0.1",
            "rules+openmed-large-t0.1")["ms_per_doc"],
        "OpenMed-small @0.02": report("sealed2/clin2_sealed_openmed_t0.02",
                                      "rules+openmed-t0.02")["ms_per_doc"],
        "Stanford @0.10": report("sealed2/clin2_sealed_stanford_t0.1",
                                 "rules+stanford-t0.1")["ms_per_doc"],
        "ai4privacy en": report("sealed2/clin2_sealed",
                                "rules+ai4privacy-en")["ms_per_doc"],
        "ai4privacy cat": report("sealed2/clin2_sealed",
                                 "rules+ai4privacy-cat")["ms_per_doc"],
        "iiiorg/piiranha-v1": report("sealed2/clin2_sealed",
                                     "rules+piiranha")["ms_per_doc"],
    }
    leaks = PLOTTED["field"]
    sizes = {
        "Scotoma-small v1": (ROOT / "models/v1-small/model_quantized.onnx")
        .stat().st_size,
        "OpenMed-large @0.10": (ROOT / "models/openmed-large-fp32/model.onnx")
        .stat().st_size,
        "OpenMed-small @0.02": (ROOT / "models/openmed/model_quantized.onnx")
        .stat().st_size,
        "Stanford @0.10": (ROOT / "models/stanford/model_quantized.onnx")
        .stat().st_size,
        "ai4privacy en": (ROOT / "models/ai4privacy-en-fp32/model.onnx")
        .stat().st_size,
        "ai4privacy cat": (ROOT / "models/ai4privacy-cat-fp32/model.onnx")
        .stat().st_size,
        "iiiorg/piiranha-v1": (ROOT / "models/piiranha-fp32/model.onnx")
        .stat().st_size,
    }
    assert abs(sizes["Scotoma-small v1"] / 1e6 - 172) < 2
    assert abs(sizes["OpenMed-large @0.10"] / 1e6 - 1738) < 10

    cols = {"Scotoma-small v1": TEAL, "OpenMed-large @0.10": AMBER,
            "OpenMed-small @0.02": AMBER_HI, "Stanford @0.10": PLUM,
            "ai4privacy en": GREY, "ai4privacy cat": GREY,
            "iiiorg/piiranha-v1": GREY}
    pts = [(n, ms[n], leaks[n]["rules_pct"], sizes[n] / 1e6, cols[n])
           for n in ms]
    PLOTTED["speed_vs_leaks"] = {
        n: {"ms": round(v, 1), "rules_leak_pct": l, "size_mb": round(s, 1)}
        for (n, v, l, s, c) in pts}

    fig = brand_fig(10, 6.0, "Fast and sealed-tight",
                    foot="synthetic clinical notes · sealed, pre-registered, "
                         "scored once · + rules, 860 notes, one Mac CPU · "
                         "bubble = ONNX file size · not shown: GLiNER ×4, "
                         "privacy-filter, Presidio (GPU-precomputed, n/m)")
    ax = card_axes(fig, (0.028, 0.055, 0.70, 0.80), pad=0.03)
    ax.set_position([0.095, 0.10, 0.60, 0.70])

    # better-quadrant: soft teal gradient, bottom-left
    ax.set_xlim(-15, 300)
    ax.set_ylim(-9, 80)
    gx = np.linspace(0, 1, 200)[None, :, None]
    quad = np.zeros((1, 200, 4))
    quad[..., :3] = matplotlib.colors.to_rgb(tint(TEAL, 0.55))
    quad[..., 3] = (1 - gx[0, :, 0]) ** 1.5 * 0.5
    ax.imshow(np.repeat(quad, 4, axis=0), extent=[-15, 120, -9, 30],
              aspect="auto", zorder=0)
    ax.text(10, 24, "better", fontsize=13, fontweight="bold",
            color=darken(TEAL), alpha=0.75, ha="left")
    ax.annotate("", xy=(6, 3), xytext=(28, 16),
                arrowprops=dict(arrowstyle="-|>", color=darken(TEAL), lw=1.6))

    # label boxes in data coords (x-ms, y-%, ha): fanned around the
    # clustered bottom-left points so nothing collides
    labels = {
        "Scotoma-small v1": (34, -3.0, "left"),
        "OpenMed-small @0.02": (2, 9.5, "left"),
        "Stanford @0.10": (44, 1.8, "left"),
        "OpenMed-large @0.10": (225, 4.5, "left"),
        "ai4privacy en": (114, 54, "left"),
        "ai4privacy cat": (114, 64, "left"),
        "iiiorg/piiranha-v1": (114, 73, "left"),
    }
    for name, x, y, mb, col in pts:
        s = 90 + np.sqrt(mb) * 9
        ours = name.startswith("Scotoma")
        if ours:
            ax.scatter([x], [y], s=s * 2.4, color=TEAL_HI, alpha=0.25,
                       edgecolor="none", zorder=2)
        ax.scatter([x], [y], s=s, color=col,
                   alpha=0.85 if ours else 0.55,
                   edgecolor=darken(col, 0.75), linewidth=1.4, zorder=3)
        lx, ly, ha = labels[name]
        ax.plot([x, lx], [y, ly], color="#c8ccd0", lw=0.7, zorder=2)
        ax.text(lx, ly, name, ha=ha, va="center", fontsize=8.5,
                color=darken(col, 0.8), fontweight="bold", zorder=4)

    ax.set_xlabel("ms per note (CPU)", fontsize=9.5, color=INK)
    ax.set_ylabel("leaks, % of notes", fontsize=9.5, color=INK)
    style_ax(ax)

    card(fig, (0.755, 0.055, 0.218, 0.80))
    fig.text(0.775, 0.78, "model size", fontsize=9.5, fontweight="bold",
             color=INK)
    fig.text(0.775, 0.55,
             "Scotoma 172 MB int8\nOpenMed-L 1.74 GB fp32\n"
             "piiranha 1.11 GB\nai4privacy 0.60 GB",
             fontsize=8, color=SUB)
    save(fig, "speed_vs_leaks.png")



def fig_progress():
    data = {
        "familiar formats": [
            ("sealed 1", 874,
             report("sealed/clin_sealed", "rules+ours-shipped"),
             report("sealed/clin_sealed_openmed-large_t0.1",
                    "rules+openmed-large-t0.1"), "lost"),
            ("sealed 2", 860,
             report("sealed2/clin2_sealed", "rules+ours-v1"),
             report("sealed2/clin2_sealed_openmed-large_t0.1",
                    "rules+openmed-large-t0.1"), "tie"),
            ("sealed 3", 7108,
             report("sealed3/clin3_test_ours", "rules+ours"),
             report("sealed3/clin3_test_oml",
                    "rules+openmed-large-t0.1"), "win"),
        ],
        "novel formats (unseen)": [
            ("sealed 1", 874,
             report("sealed/clin_novel_sealed", "rules+ours-shipped"),
             report("sealed/clin_novel_sealed_openmed-large_t0.1",
                    "rules+openmed-large-t0.1"), "lost"),
            ("sealed 2", 860,
             report("sealed2/clin2_novel_sealed", "rules+ours-v1"),
             report("sealed2/clin2_novel_sealed_openmed-large_t0.1",
                    "rules+openmed-large-t0.1"), "tie"),
            ("sealed 3", 7108,
             report("sealed3/clin3_novel_all", "rules+ours"),
             report("sealed3/clin3_novel_all",
                    "rules+openmed-large-t0.1"), "win"),
        ],
    }
    md1 = (RES / "SEALED_RESULTS.md").read_text()
    assert "0.5%**" in md1 and "1.9%" in md1 and "1.7%" in md1
    fam, nov = data["familiar formats"], data["novel formats (unseen)"]
    assert (fam[0][2]["docs_with_leak"], fam[0][3]["docs_with_leak"]) == (17, 4)
    assert (nov[0][2]["docs_with_leak"], nov[0][3]["docs_with_leak"]) == (15, 4)
    assert (fam[1][2]["docs_with_leak"], fam[1][3]["docs_with_leak"]) == (2, 5)
    assert (nov[1][2]["docs_with_leak"], nov[1][3]["docs_with_leak"]) == (2, 5)
    assert (fam[2][2]["docs_with_leak"], fam[2][3]["docs_with_leak"]) == (2, 26)
    assert (nov[2][2]["docs_with_leak"], nov[2][3]["docs_with_leak"]) == (1, 33)

    PLOTTED["progress"] = {
        s: [{"round": r[0], "n": r[1], "ours": r[2]["docs_with_leak"],
             "oml_t0.10": r[3]["docs_with_leak"]} for r in rows]
        for s, rows in data.items()}

    fig = brand_fig(10, 5.8, "Three sealed evaluations",
                    foot="synthetic clinical notes · sealed, pre-registered, "
                         "scored once · rules + model, leak rate %")
    handles = [Rectangle((0, 0), 1, 1, facecolor=TEAL),
               Rectangle((0, 0), 1, 1, facecolor=AMBER)]
    fig.legend(handles, ["rules + ours", "rules + OpenMed-L @0.10"],
               loc="upper right", bbox_to_anchor=(0.965, 0.92), ncol=1,
               frameon=False, fontsize=8.5)

    vstyle = {"lost": ("LOST", "#9e5b4f"), "tie": ("TIE", "#8a8f96"),
              "win": ("WIN", TEAL)}
    pnote = {"familiar formats": "p = 8 × 10⁻⁷",
             "novel formats (unseen)": "p = 4.7 × 10⁻¹⁰"}

    for i, (setname, rows) in enumerate(data.items()):
        ax = card_axes(fig, (0.028 + i * 0.485, 0.075, 0.455, 0.76), pad=0.025)
        ax.set_position([0.075 + i * 0.485, 0.115, 0.395, 0.60])
        xs = np.arange(len(rows))
        w = 0.34
        for x, (label, n, o, m, verdict) in zip(xs, rows):
            ro, rm = leak_rate(o), leak_rate(m)
            vbar(ax, x - w / 2, ro, w, TEAL)
            vbar(ax, x + w / 2, rm, w, AMBER)
            ax.text(x - w / 2, ro + 0.08, f"{ro:.2f}", ha="center",
                    va="bottom", fontsize=8, fontweight="bold",
                    color=darken(TEAL))
            ax.text(x + w / 2, rm + 0.08, f"{rm:.2f}", ha="center",
                    va="bottom", fontsize=8, fontweight="bold",
                    color=darken(AMBER))
            txt, col = vstyle[verdict]
            ax.text(x, -0.52, f"{label} · n={n:,}", ha="center", va="top",
                    fontsize=8.5, color=INK, fontweight="bold")
            ax.text(x, -0.85, txt + ("  " + pnote[setname]
                                     if verdict == "win" else ""),
                    ha="center", va="top", fontsize=8, color=darken(col),
                    fontweight="bold")
        ax.set_xlim(-0.6, 2.6)
        ax.set_ylim(-1.15, 2.35)
        ax.set_xticks([])
        ax.set_title(setname, loc="left", fontsize=10, fontweight="bold",
                     color=INK, pad=6)
        ax.set_ylabel("leaks, %", fontsize=9, color=INK)
        style_ax(ax)
        ax.spines["bottom"].set_visible(False)
    save(fig, "progress.png")



def fig_categories():
    ours = json.loads(
        (RES / "sealed3/clin3_test_ours" / "reports.json").read_text())
    oml = json.loads((RES / "sealed3/clin3_test_oml" / "reports.json").read_text())
    syscols = [
        ("ours\nalone", ours["ours"]),
        ("ours\n+ rules", ours["rules+ours"]),
        ("OML @0.10\nalone", oml["openmed-large-t0.1"]),
        ("OML @0.10\n+ rules", oml["rules+openmed-large-t0.1"]),
    ]
    cats = sorted(
        set().union(*[set(s[1]["by_category"]) for s in syscols]),
        key=lambda c: -syscols[0][1]["by_category"][c]["gold"])
    cats = [c for c in cats if syscols[0][1]["by_category"][c]["gold"] > 0]
    M = np.full((len(cats), len(syscols)), np.nan)
    for j, (_, s) in enumerate(syscols):
        for i, c in enumerate(cats):
            g = s["by_category"][c]
            M[i, j] = 100.0 * g["caught"] / g["gold"]
    ns = [syscols[0][1]["by_category"][c]["gold"] for c in cats]

    PLOTTED["categories"] = {
        "categories": cats, "n": ns,
        "recall_pct": {syscols[j][0].split("\n")[0]: [round(v, 2) for v in
                                                     M[:, j]]
                       for j in range(len(syscols))},
    }

    tealmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "scotoma_teal", ["#fdf3ec", "#f6c98e", "#7cc7b8", TEAL, "#0a6f60"])
    fig = brand_fig(10, 7.8, "Recall by identifier type — sealed 3",
                    foot="synthetic clinical notes · sealed, pre-registered, "
                         "scored once · clin3, 7,108 notes · share of planted "
                         "identifiers touched (100 = none missed) · OML = "
                         "OpenMed-PII-SuperClinical-Large")
    card(fig, (0.028, 0.055, 0.945, 0.80))
    ax = fig.add_axes([0.215, 0.10, 0.60, 0.575])
    ax.set_facecolor("none")
    ax.set_xlim(-0.5, len(syscols) - 0.5)
    ax.set_ylim(-0.5, len(cats) - 0.5)
    ax.invert_yaxis()

    norm = matplotlib.colors.Normalize(vmin=90, vmax=100)
    for i in range(len(cats)):
        for j in range(len(syscols)):
            v = M[i, j]
            if np.isnan(v):
                continue
            ax.add_patch(FancyBboxPatch(
                (j - 0.46, i - 0.44), 0.92, 0.88,
                boxstyle="round,pad=0,rounding_size=0.14",
                facecolor=tealmap(norm(v)), edgecolor="white",
                linewidth=1.4, zorder=2))
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.2,
                    color="white" if v > 97.5 else "#8a4a12",
                    fontweight="bold" if v < 99.5 else "normal", zorder=3)
    ax.set_xticks(range(len(syscols)))
    ax.set_xticklabels([s[0] for s in syscols], fontsize=9, color=INK)
    ax.xaxis.set_ticks_position("top")
    ax.tick_params(axis="x", pad=6)
    ax.set_yticks(range(len(cats)))
    ax.set_yticklabels([f"{c}  (n={n:,})" for c, n in zip(cats, ns)],
                       fontsize=8, color=INK)
    ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_visible(False)

    sm = matplotlib.cm.ScalarMappable(norm=norm, cmap=tealmap)
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02)
    cb.set_label("recall %", fontsize=8, color=SUB)
    cb.ax.tick_params(labelsize=7.5, colors=SUB)
    cb.outline.set_visible(False)

    # ours columns framed
    ax.add_patch(FancyBboxPatch((-0.5, -0.5), 2.0, len(cats),
                                boxstyle="round,pad=0,rounding_size=0.10",
                                facecolor="none", edgecolor=TEAL,
                                linewidth=1.6, zorder=4))
    save(fig, "categories.png")



def fig_pipeline():
    fig = brand_fig(10, 5.9, "How it works",
                    foot="all processing on-device · no telemetry")
    ax = fig.add_axes([0, 0, 1, 1], zorder=1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor("none")

    def box(x, y, w, h, title, sub="", fc="white", ec="#d9dde1", fs=9,
            subfs=7, tc=INK):
        ax.add_patch(FancyBboxPatch(
            (x + 0.004, y - 0.006), w, h,
            boxstyle="round,pad=0,rounding_size=0.014",
            facecolor="#00000014", edgecolor="none", zorder=2))
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.014",
            facecolor=fc, edgecolor=ec, linewidth=1.2, zorder=3))
        ax.text(x + w / 2, y + h / 2 + (0.020 if sub else 0), title,
                ha="center", va="center", fontsize=fs, fontweight="bold",
                color=tc, zorder=4)
        if sub:
            ax.text(x + w / 2, y + h / 2 - 0.028, sub, ha="center",
                    va="center", fontsize=subfs, color=SUB, zorder=4)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=15,
            color=TEAL, linewidth=1.8, zorder=2))

    def glyph(kind, cx, cy, s=0.018):
        col = NAVY
        lw = 1.8
        if kind == "paste":  # clipboard
            ax.add_patch(FancyBboxPatch((cx - s * 0.7, cy - s), s * 1.4,
                                        s * 1.8,
                                        boxstyle="round,pad=0,rounding_size=0.004",
                                        facecolor="none", edgecolor=col,
                                        lw=lw))
            ax.plot([cx - s * 0.35, cx + s * 0.35], [cy + s * 0.95] * 2,
                    color=col, lw=lw)
        elif kind == "shot":  # crop corners
            for dx, dy in [(-1, 1), (1, 1), (-1, -1), (1, -1)]:
                ax.plot([cx + dx * s, cx + dx * s * 0.4],
                        [cy + dy * s, cy + dy * s], color=col, lw=lw)
                ax.plot([cx + dx * s, cx + dx * s],
                        [cy + dy * s, cy + dy * s * 0.4], color=col, lw=lw)
        elif kind == "pdf":  # page glyph
            ax.add_patch(FancyBboxPatch((cx - s * 0.7, cy - s), s * 1.3,
                                        s * 1.8,
                                        boxstyle="round,pad=0,rounding_size=0.003",
                                        facecolor="none", edgecolor=col,
                                        lw=lw))
            for k in range(3):
                ax.plot([cx - s * 0.45, cx + s * 0.4],
                        [cy + s * (0.45 - k * 0.4)] * 2, color=col, lw=1.1)
        elif kind == "mic":
            ax.add_patch(FancyBboxPatch((cx - s * 0.42, cy - s * 0.4),
                                        s * 0.84, s * 1.5,
                                        boxstyle="round,pad=0,rounding_size=0.012",
                                        facecolor="none", edgecolor=col,
                                        lw=lw))
            ax.plot([cx, cx], [cy - s * 0.5, cy - s * 1.15], color=col, lw=lw)
            ax.plot([cx - s * 0.55, cx + s * 0.55], [cy - s * 1.15] * 2,
                    color=col, lw=lw)
            ax.add_patch(matplotlib.patches.Arc(
                (cx, cy - s * 0.35), s * 1.5, s * 1.5, theta1=180, theta2=360,
                color=col, lw=lw))
        elif kind == "lock":
            ax.add_patch(FancyBboxPatch((cx - s, cy - s * 0.9), s * 2, s * 1.7,
                                        boxstyle="round,pad=0,rounding_size=0.006",
                                        facecolor=TEAL, edgecolor="none"))
            ax.add_patch(matplotlib.patches.Arc(
                (cx, cy + s * 0.75), s * 1.3, s * 1.5, theta1=0, theta2=180,
                color=TEAL, lw=2.4))

    inputs = [("paste / hotkey", "⌘⌥S", "paste"),
              ("screenshot / region", "⌘⌥D", "shot"),
              ("PDF or scan", "", "pdf"),
              ("dictation", "⌘⌥V", "mic")]
    iy = [0.665, 0.52, 0.375, 0.23]
    for (label, hk, g), y in zip(inputs, iy):
        box(0.035, y, 0.19, 0.115, "", fc="white", ec=tint(NAVY, 0.35))
        glyph(g, 0.062, y + 0.058)
        ax.text(0.088, y + 0.070, label, fontsize=8.2, fontweight="bold",
                color=INK, va="center", zorder=4)
        ax.text(0.088, y + 0.032, hk, fontsize=7, color=SUB, va="center",
                zorder=4, fontfamily="SF Pro")
        arrow(0.228, y + 0.058, 0.298, 0.615 if y > 0.5 else 0.545)

    box(0.30, 0.55, 0.16, 0.14, "on-device\nOCR / STT",
        "Apple Vision · own\nspeech server",
        fc=tint(NAVY, 0.90), ec=tint(NAVY, 0.35))
    arrow(0.46, 0.62, 0.525, 0.62)

    # engine card with glow — the app wraps the model + rules
    ax.add_patch(FancyBboxPatch(
        (0.525 - 0.008, 0.485 - 0.010), 0.21 + 0.016, 0.28 + 0.020,
        boxstyle="round,pad=0,rounding_size=0.02",
        facecolor=TEAL_HI, alpha=0.22, edgecolor="none", zorder=2))
    box(0.525, 0.485, 0.21, 0.28, "Scrub N Paste (app)",
        "Scotoma model + rules\nint8 · ~20 ms/note",
        fc=tint(TEAL, 0.88), ec=TEAL, fs=10.5)
    arrow(0.735, 0.62, 0.80, 0.62)

    box(0.80, 0.55, 0.165, 0.14, "review",
        "approve, keep,\nor redact more", fc=tint(AMBER, 0.88),
        ec=tint(AMBER, 0.25))

    # outputs container
    ax.add_patch(FancyBboxPatch(
        (0.795, 0.035), 0.175, 0.475,
        boxstyle="round,pad=0,rounding_size=0.016",
        facecolor="white", edgecolor="#d9dde1", linewidth=1.1,
        linestyle="--", zorder=2))
    ax.text(0.8825, 0.46, "outputs", ha="center", fontsize=8,
            fontweight="bold", color=SUB, zorder=4)
    outputs = ["[NAME_1] tags", "realistic stand-ins",
               "black boxes on files", "protect & unlock"]
    oy = [0.35, 0.25, 0.15, 0.05]
    for label, y in zip(outputs, oy):
        box(0.808, y, 0.149, 0.088, label, fc="#f7f8f9", ec="#d9dde1", fs=8)
    arrow(0.8825, 0.545, 0.8825, 0.505)

    # privacy band with lock
    band_y = 0.055
    ax.add_patch(FancyBboxPatch(
        (0.035, band_y), 0.685, 0.115,
        boxstyle="round,pad=0,rounding_size=0.016",
        facecolor=tint(TEAL, 0.85), edgecolor=TEAL, linewidth=1.6, zorder=3))
    glyph("lock", 0.075, band_y + 0.055)
    ax.text(0.105, band_y + 0.058,
            "nothing leaves your device — no telemetry; the only socket is an\n"
            "optional, opt-in loopback connection to your own speech server",
            ha="left", va="center", fontsize=8.8, fontweight="bold",
            color=darken(TEAL, 0.7), zorder=4)
    save(fig, "pipeline.png")



def _render_note(src: Path, out: Path):
    """Render the example note as a clean page image (≈200 dpi)."""
    from PIL import Image, ImageDraw, ImageFont
    import glob
    mono = glob.glob(str(ROOT / ".venv/lib/python*/site-packages/"
                         "matplotlib/mpl-data/fonts/ttf/DejaVuSansMono.ttf"))
    mono = mono[0] if mono else "/System/Library/Fonts/SFNSMono.ttf"
    monob = mono.replace("Mono.ttf", "Mono-Bold.ttf")
    if not Path(monob).exists():
        monob = mono
    W, H = 1700, 2200
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fh = ImageFont.truetype(monob, 40)
    fb = ImageFont.truetype(mono, 32)
    x = 120
    d.text((x, 120), "RIVERSIDE CLINIC — INTERNAL NOTE", font=fh,
           fill="#222222")
    d.line((x, 195, W - x, 195), fill="#bbbbbb", width=3)
    y, lh = 270, int(32 * 1.7)
    for para in src.read_text().rstrip("\n").split("\n"):
        line = ""
        for w in para.split():
            if len(line) + len(w) + 1 > 72:
                d.text((x, y), line, font=fb, fill="#111111")
                y += lh
                line = w
            else:
                line = (line + " " + w).strip()
        d.text((x, y), line, font=fb, fill="#111111")
        y += lh
    img.crop((0, 0, W, min(H, y + 70))).save(out)


def fig_before_after():
    scotoma = ROOT / "target" / "release" / "scotoma"
    helper = ROOT / "app" / "src-tauri" / "bin" / "scotoma-helper"
    src = ROOT / "examples" / "21_hard_caps_and_bare_names.txt"
    needles = ["OKONKWO", "THADDEUS", "Marisol", "Reyes", "Larchmont",
               "Waukegan", "60085", "7KQ-2291", "555-0193", "00418827",
               "June", "03/14/2025"]
    keeps = ["Graves", "Bell", "palsy", "Metoprolol", "HR 88", "97%",
             "Intake"]

    def _skip(reason):
        for p in (ASSETS / "before_after.png", DOCS_IMG / "before_after.png"):
            p.unlink(missing_ok=True)
        print(f"before_after: {reason} — figure NOT shipped", file=sys.stderr)
        PLOTTED["before_after"] = f"skipped: {reason}"

    if not (scotoma.exists() and helper.exists()):
        _skip("required tool missing")
        return

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        in_png, out_png = td / "in.png", td / "out.png"
        _render_note(src, in_png)
        subprocess.run([str(scotoma), "redact-file", str(in_png),
                        str(out_png), "--model",
                        str(ROOT / "models" / "v2-small")],
                       check=True, capture_output=True)
        ocr = subprocess.run([str(helper), "ocr-boxes", str(out_png)],
                             check=True, capture_output=True)
        pages = json.loads(ocr.stdout)["pages"]
        text = " ".join(l["text"] for p in pages for l in p["lines"])

        leaks = [n for n in needles if n.lower() in text.lower()]
        vals = [re.sub(r"[^a-z0-9]", "", n.lower()) for n in needles]
        for w in re.split(r"\s+", text):
            wn = re.sub(r"[^a-z0-9]", "", w.lower())
            floor = 4 if any(c.isdigit() for c in wn) else 5
            if len(wn) < floor:
                continue
            frags = [n for n, v in zip(needles, vals)
                     if wn in v or (len(v) >= floor and v in wn) or
                     any(wn[i:i + floor] in v
                         for i in range(len(wn) - floor + 1))]
            for n in frags:
                if n not in leaks:
                    leaks.append(f"{n} (partial: {w!r})")
        if leaks:
            _skip(f"OCR found leaks {leaks}")
            return

        missing = [k for k in keeps if k.lower() not in text.lower()]
        if missing:
            _skip(f"clinical text over-redacted: {missing}")
            return

        vitals_boxed = [k for k in ("148/92", "SpO2", "Civic")
                        if k.lower() not in text.lower()
                        and k.lower().replace("o", "0") not in text.lower()]

        ib, ia = plt.imread(in_png), plt.imread(out_png)
        PLOTTED["before_after"] = {
            "planted_checked": needles, "leaks": [],
            "kept_checked": keeps, "vitals_boxed": vitals_boxed,
        }

    fig = brand_fig(10, 4.4, "A page in, a clean page out",
                    foot="synthetic example "
                         "(examples/21_hard_caps_and_bare_names.txt) · "
                         "scotoma redact-file, fully on-device")
    ink = INK
    if vitals_boxed:
        fig.text(0.5, 0.795,
                 "over-redaction shown as-is: "
                 + ", ".join(f"“{v}”" for v in vitals_boxed)
                 + " boxed — false positives",
                 ha="center", fontsize=8.5, color="#8a5a00")

    for i, (img, t) in enumerate([(ib, "before"),
                                  (ia, "after — Scrub N Paste")]):
        rect = (0.045 + i * 0.50, 0.10, 0.40, 0.60)
        card(fig, rect)
        ax = fig.add_axes([rect[0] + 0.012, rect[1] + 0.055,
                           rect[2] - 0.024, rect[3] - 0.085])
        ax.imshow(img)
        ax.set_title(t, fontsize=10.5, fontweight="bold",
                     color=ink if i == 0 else darken(TEAL), pad=4)
        ax.axis("off")
        for s in ax.spines.values():
            s.set_visible(False)

    # arrow between the two cards
    axm = fig.add_axes([0.455, 0.36, 0.09, 0.09], zorder=6)
    axm.axis("off")
    axm.add_patch(FancyBboxPatch(
        (0.02, 0.06), 0.96, 0.88, boxstyle="round,pad=0,rounding_size=0.25",
        facecolor=TEAL, edgecolor="none"))
    axm.text(0.5, 0.5, "→", ha="center", va="center", fontsize=17,
             color="white", fontweight="bold", fontfamily="SF Pro")
    axm.set_xlim(0, 1)
    axm.set_ylim(0, 1)
    save(fig, "before_after.png")


def main():
    fig_hero()
    fig_field()
    fig_speed()
    fig_progress()
    fig_categories()
    fig_pipeline()
    fig_before_after()
    print(json.dumps(PLOTTED, indent=1, default=str))


if __name__ == "__main__":
    main()
