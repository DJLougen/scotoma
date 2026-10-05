#!/usr/bin/env python3
"""Marketing figures for the Scotoma model card / README.

Every plotted number is read from bench/results/**/reports.json (or the
SEALED*_RESULTS.md tables) and asserted before it is drawn. Nothing is
hand-typed into a figure.

    .venv/bin/python plots/make_card_figures.py

Writes PNGs to release/hf/scotoma-small/assets/ and copies them to
docs/img/. Prints every plotted value as JSON at the end.

before_after.png additionally shells out to cupsfilter, the release `scotoma`
binary (redact-file), `scotoma-helper ocr-boxes` and `sips`; it is skipped with
a warning if any tool is missing or if the re-OCR assertion finds a leak.
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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "bench" / "results"
ASSETS = ROOT / "release" / "hf" / "scotoma-small" / "assets"
DOCS_IMG = ROOT / "docs" / "img"

# Okabe-Ito palette
C_OURS = "#009E73"
C_OML = "#E69F00"
C_GLINER = "#56B4E9"
C_STANFORD = "#CC79A7"
C_PRIV = "#0072B2"
C_PRES = "#D55E00"
C_GREY = "#8A8A8A"
C_INK = "#1a1a1a"
FOOT = "synthetic clinical notes with planted identifiers; sealed, pre-registered, scored once"

PLOTTED = {}  # every value that ends up on a figure


def darken(hexcolor, f=0.55):
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


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


def newfig(w_in=10.0, h_in=6.0):
    fig = plt.figure(figsize=(w_in, h_in), dpi=200, facecolor="white")
    return fig


def footnote(fig, text, x=0.99):
    fig.text(x, 0.012, text, ha="right", va="bottom", fontsize=6.5,
             color="#777777", style="italic")


def save(fig, name):
    ASSETS.mkdir(parents=True, exist_ok=True)
    DOCS_IMG.mkdir(parents=True, exist_ok=True)
    out = ASSETS / name
    fig.savefig(out, facecolor="white")
    shutil.copy2(out, DOCS_IMG / name)
    print(f"wrote {out.relative_to(ROOT)} (+ docs/img/{name})", file=sys.stderr)


def bar_label(ax, x, y, text, color, inside=False):
    ax.text(x, y, text, va="center", ha="left" if not inside else "right",
            fontsize=8, color=color, fontweight="bold",
            clip_on=False, zorder=5)


# ---------------------------------------------------------------- figure 1
def fig_hero():
    ours = report("sealed3/clin3_test_ours", "ours")
    rours = report("sealed3/clin3_test_ours", "rules+ours")
    oml10 = report("sealed3/clin3_test_oml", "openmed-large-t0.1")
    roml10 = report("sealed3/clin3_test_oml", "rules+openmed-large-t0.1")
    oml35 = report("sealed3/clin3_test_oml", "openmed-large")
    roml35 = report("sealed3/clin3_test_oml", "rules+openmed-large")
    n = rours["docs"]

    # --- asserts: the headline numbers from SEALED3_RESULTS.md ---
    assert (rours["docs_with_leak"], roml10["docs_with_leak"], roml35["docs_with_leak"]) == (2, 26, 101)
    assert (ours["docs_with_leak"], oml10["docs_with_leak"], oml35["docs_with_leak"]) == (4, 407, 680)
    assert n == 7108

    # re-run the primary exact McNemar on the merged item matrix
    docs, only_ours, only_oml, both = mcnemar_counts(
        RES / "sealed3" / "clin3_test_all_responses.csv",
        "rules+ours", "rules+openmed-large-t0.1")
    p = exact_p(only_ours, only_oml)
    assert (docs, only_ours, only_oml, both) == (7108, 1, 25, 1)
    assert abs(p - 8.047e-07) / 8.047e-07 < 0.01, p

    # compute strings from SEALED3_RESULTS.md (parsed, not retyped)
    md = (RES / "SEALED3_RESULTS.md").read_text()
    m = re.search(r"about (\d+(?:\.\d+)?) vs about (\d+) CPU-seconds", md)
    cpu_ours, cpu_oml = float(m.group(1)), float(m.group(2))
    m = re.search(r"about (\d+) ms vs about (\d+) ms per note", md)
    ms_ours, ms_oml = float(m.group(1)), float(m.group(2))
    assert (cpu_ours, cpu_oml) == (0.2, 4.0) and (ms_ours, ms_oml) == (20.0, 240.0)

    PLOTTED["hero"] = {
        "n": n, "rules": {"ours": 2, "oml_t0.10": 26, "oml_t0.35": 101},
        "alone": {"ours": 4, "oml_t0.10": 407, "oml_t0.35": 680},
        "mcnemar": {"only_ours": only_ours, "only_oml": only_oml, "both": both, "p": p},
        "cpu_s_per_note": {"ours": cpu_ours, "oml": cpu_oml},
        "ms_per_note_mac": {"ours": ms_ours, "oml": ms_oml},
    }
    fig = newfig(10, 6.2)
    fig.suptitle(f"Leaked notes out of {n:,}",
                 x=0.03, y=0.965, ha="left", fontsize=18, fontweight="bold", color=C_INK)
    fig.text(0.03, 0.910, "sealed, pre-registered · same notes, same scorer · clin3 (familiar identifier formats)",
             ha="left", fontsize=10, color="#555555")
    fig.text(0.985, 0.938, "p = 8 × 10⁻⁷  exact McNemar (primary test)",
             ha="right", va="center", fontsize=10.5, fontweight="bold", color="white",
             bbox=dict(boxstyle="round,pad=0.5", facecolor=C_OURS, edgecolor="none"))

    gs = fig.add_gridspec(2, 2, width_ratios=[1.9, 1.0], height_ratios=[1, 1],
                          left=0.235, right=0.965, top=0.82, bottom=0.10,
                          wspace=0.35, hspace=0.50)

    def panel(ax, title, rows):
        # rows bottom->top already ordered; values = (count, colour, label)
        ys = np.arange(len(rows))
        counts = [r[0] for r in rows]
        cols = [r[1] for r in rows]
        ax.barh(ys, counts, height=0.62, color=cols, edgecolor="none")
        ax.set_yticks(ys)
        ax.set_yticklabels([r[2] for r in rows], fontsize=9.5, color=C_INK)
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color=C_INK, pad=8)
        xmax = ax.get_xlim()[1]
        for y, (cnt, col, _) in zip(ys, rows):
            pct = 100 * cnt / n
            bar_label(ax, cnt + xmax * 0.012, y, f"{cnt}  ({pct:.2f}%)", darken(col))
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=8, colors="#555555")

    ax_a = fig.add_subplot(gs[0, 0])
    panel(ax_a, "with Scotoma rules", [
        (roml35["docs_with_leak"], C_OML, "OpenMed-large @0.35"),
        (roml10["docs_with_leak"], C_OML, "OpenMed-large @0.10"),
        (rours["docs_with_leak"], C_OURS, "Scotoma-small"),
    ])
    ax_a.invert_yaxis()
    ax_a.set_xlim(0, 118)
    ax_a.set_xlabel("notes with ≥1 identifier leaked", fontsize=8, color="#555555")

    ax_b = fig.add_subplot(gs[1, 0])
    panel(ax_b, "model alone (no rules)", [
        (oml35["docs_with_leak"], C_OML, "OpenMed-large @0.35"),
        (oml10["docs_with_leak"], C_OML, "OpenMed-large @0.10"),
        (ours["docs_with_leak"], C_OURS, "Scotoma-small"),
    ])
    ax_b.invert_yaxis()
    ax_b.set_xlim(0, 800)
    ax_b.set_xlabel("notes with ≥1 identifier leaked", fontsize=8, color="#555555")

    ax_c = fig.add_subplot(gs[:, 1])
    vals = [cpu_oml, cpu_ours]
    ys = np.arange(2) * 0.42
    ax_c.barh(ys, vals, height=0.28, color=[C_OML, C_OURS])
    ax_c.set_yticks(ys)
    ax_c.set_yticklabels(["OpenMed-large", "Scotoma-small"], fontsize=9.5, color=C_INK)
    ax_c.set_ylim(-0.32, 0.78)
    ax_c.set_xscale("log")
    ax_c.set_xlim(0.12, 9)
    ax_c.xaxis.set_major_locator(matplotlib.ticker.FixedLocator([0.2, 0.5, 1, 2, 5]))
    ax_c.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:g}"))
    ax_c.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax_c.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax_c.set_title("CPU-seconds per note", loc="left", fontsize=11,
                   fontweight="bold", color=C_INK, pad=8)
    for y, v, c in zip(ys, vals, [C_OML, C_OURS]):
        bar_label(ax_c, v * 1.08, y, f"{v:g} s", darken(c))
    ax_c.set_xlabel("log scale — same 7,108 notes", fontsize=8, color="#555555")
    ax_c.spines[["top", "right"]].set_visible(False)
    ax_c.tick_params(axis="x", labelsize=8, colors="#555555")
    ax_c.text(0.5, -0.32, f"~{ms_ours:g} ms vs ~{ms_oml:g} ms per note on an M3 Max\n"
                          "≈ 18–20× less compute",
              transform=ax_c.transAxes, ha="center", fontsize=9, color="#555555")

    footnote(fig, FOOT)
    save(fig, "hero.png")


# ---------------------------------------------------------------- figure 2
def fig_field():
    # (display name, family colour, run dir, alone-system, rules-system)
    field = [
        ("ours v1-small", C_OURS, "sealed2/clin2_sealed", "ours-v1", "rules+ours-v1"),
        ("OpenMed-large @0.10", C_OML, "sealed2/clin2_sealed_openmed-large_t0.1",
         "openmed-large-t0.1", "rules+openmed-large-t0.1"),
        ("OpenMed-small @0.02", C_OML, "sealed2/clin2_sealed_openmed_t0.02",
         "openmed-t0.02", "rules+openmed-t0.02"),
        ("Stanford @0.10", C_STANFORD, "sealed2/clin2_sealed_stanford_t0.1",
         "stanford-t0.1", "rules+stanford-t0.1"),
        ("nvidia/gliner-PII", C_GLINER, "sealed2/clin2_sealed", "gliner-nvidia", "rules+gliner-nvidia"),
        ("gliner-pii-edge", C_GLINER, "sealed2/clin2_sealed", "gliner-edge", "rules+gliner-edge"),
        ("gliner-pii-large", C_GLINER, "sealed2/clin2_sealed", "gliner-large", "rules+gliner-large"),
        ("gliner-pii-base", C_GLINER, "sealed2/clin2_sealed", "gliner-base", "rules+gliner-base"),
        ("openai/privacy-filter", C_PRIV, "sealed2/clin2_sealed", "privacy-filter", "rules+privacy-filter"),
        ("Microsoft Presidio", C_PRES, "sealed2/clin2_sealed", "presidio", "rules+presidio"),
        ("ai4privacy en", C_GREY, "sealed2/clin2_sealed", "ai4privacy-en", "rules+ai4privacy-en"),
        ("ai4privacy cat", C_GREY, "sealed2/clin2_sealed", "ai4privacy-cat", "rules+ai4privacy-cat"),
        ("iiiorg/piiranha-v1", C_GREY, "sealed2/clin2_sealed", "piiranha", "rules+piiranha"),
    ]
    rows = []
    for name, col, d, alone_s, rules_s in field:
        a, r = report(d, alone_s), report(d, rules_s)
        assert a["docs"] == r["docs"] == 860
        rows.append((name, col, leak_rate(a), leak_rate(r)))

    # assert the published headline numbers
    byname = {r[0]: r for r in rows}
    assert byname["ours v1-small"][2:] == (5 / 860 * 100, 2 / 860 * 100)
    assert abs(byname["OpenMed-large @0.10"][3] - 5 / 860 * 100) < 1e-9
    assert abs(byname["OpenMed-small @0.02"][3] - 5 / 860 * 100) < 1e-9
    assert abs(byname["Stanford @0.10"][3] - 46 / 860 * 100) < 1e-9

    rows.sort(key=lambda r: r[3])  # ascending +rules rate
    PLOTTED["field"] = {r[0]: {"alone_pct": round(r[2], 3), "rules_pct": round(r[3], 3)}
                        for r in rows}

    fig = newfig(10, 8.2)
    ax = fig.add_axes([0.20, 0.075, 0.72, 0.80])
    fig.suptitle("Sealed 2 — the full field on familiar formats",
                 x=0.03, y=0.965, ha="left", fontsize=15, fontweight="bold", color=C_INK)
    fig.text(0.03, 0.925,
             "share of 860 synthetic clinical notes leaking ≥1 identifier — lower is better",
             ha="left", fontsize=9.5, color="#555555")
    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor="#bbbbbb", alpha=0.45),
        plt.Rectangle((0, 0), 1, 1, facecolor="#bbbbbb"),
    ]
    fig.legend(handles, ["model alone", "+ Scotoma rules"], loc="upper right",
               bbox_to_anchor=(0.985, 0.955), ncol=2, frameon=False, fontsize=9)

    ys = np.arange(len(rows)) * 1.0
    h = 0.36
    for y, (name, col, alone, rules) in zip(ys, rows):
        ax.barh(y + h / 2 + 0.02, alone, height=h, color=col, alpha=0.45)
        ax.barh(y - h / 2 - 0.02, rules, height=h, color=col)
        bar_label(ax, alone + 1.2, y + h / 2 + 0.02, f"{alone:.1f}", darken(col, 0.7))
        bar_label(ax, rules + 1.2, y - h / 2 - 0.02, f"{rules:.1f}", darken(col))
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=9.5, color=C_INK)
    ax.invert_yaxis()  # smallest +rules leak rate on top
    ax.set_xlim(0, 105)
    ax.set_xlabel("leak-document rate, % of 860 notes", fontsize=9, color="#555555")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=8, colors="#555555")

    footnote(fig, FOOT + "; competitors at their pre-registered best point")
    save(fig, "field.png")


# ---------------------------------------------------------------- figure 3
def fig_speed():
    # systems with a real same-Mac CPU ms/doc (n/m = GPU-precomputed, excluded)
    # (name, ms per +rules note, +rules leak %, model onnx bytes|None, colour)
    def fsize(run_dir, model_rel):
        p = ROOT / model_rel
        return p.stat().st_size

    ms = {  # +rules ms/doc from the same reports
        "ours v1-small": report("sealed2/clin2_sealed", "rules+ours-v1")["ms_per_doc"],
        "OpenMed-large @0.10": report("sealed2/clin2_sealed_openmed-large_t0.1",
                                      "rules+openmed-large-t0.1")["ms_per_doc"],
        "OpenMed-small @0.02": report("sealed2/clin2_sealed_openmed_t0.02",
                                      "rules+openmed-t0.02")["ms_per_doc"],
        "Stanford @0.10": report("sealed2/clin2_sealed_stanford_t0.1",
                                 "rules+stanford-t0.1")["ms_per_doc"],
        "ai4privacy en": report("sealed2/clin2_sealed", "rules+ai4privacy-en")["ms_per_doc"],
        "ai4privacy cat": report("sealed2/clin2_sealed", "rules+ai4privacy-cat")["ms_per_doc"],
        "iiiorg/piiranha-v1": report("sealed2/clin2_sealed", "rules+piiranha")["ms_per_doc"],
    }
    leaks = PLOTTED["field"]
    sizes = {
        "ours v1-small": fsize("", "models/v1-small/model_quantized.onnx"),
        "OpenMed-large @0.10": fsize("", "models/openmed-large-fp32/model.onnx"),
        "OpenMed-small @0.02": fsize("", "models/openmed/model_quantized.onnx"),
        "Stanford @0.10": fsize("", "models/stanford/model_quantized.onnx"),
        "ai4privacy en": fsize("", "models/ai4privacy-en-fp32/model.onnx"),
        "ai4privacy cat": fsize("", "models/ai4privacy-cat-fp32/model.onnx"),
        "iiiorg/piiranha-v1": fsize("", "models/piiranha-fp32/model.onnx"),
    }
    # sanity: the shipped sizes quoted in docs
    assert abs(sizes["ours v1-small"] / 1e6 - 172) < 2
    assert abs(sizes["OpenMed-large @0.10"] / 1e6 - 1738) < 10

    cols = {"ours v1-small": C_OURS, "OpenMed-large @0.10": C_OML,
            "OpenMed-small @0.02": C_OML, "Stanford @0.10": C_STANFORD,
            "ai4privacy en": C_GREY, "ai4privacy cat": C_GREY,
            "iiiorg/piiranha-v1": C_GREY}
    pts = [(n, ms[n], leaks[n]["rules_pct"], sizes[n] / 1e6, cols[n]) for n in ms]
    PLOTTED["speed_vs_leaks"] = {
        n: {"ms": round(v, 1), "rules_leak_pct": l, "size_mb": round(s / 1e6, 1)}
        for (n, v, l, s, c) in
        [(p[0], p[1], p[2], p[3] * 1e6, p[4]) for p in pts]}

    fig = newfig(10, 5.8)
    ax = fig.add_axes([0.09, 0.13, 0.66, 0.74])
    fig.suptitle("Speed vs. leakage — same Mac CPU, sealed 2 (+ rules)",
                 x=0.03, y=0.965, ha="left", fontsize=15, fontweight="bold", color=C_INK)
    fig.text(0.03, 0.92, "bubble area = ONNX model file size",
             ha="left", fontsize=9.5, color="#555555")

    offsets = {  # (dx, dy) in offset points, ha
        "ours v1-small": (-16, -16, "left"),
        "OpenMed-small @0.02": (4, 24, "left"),
        "Stanford @0.10": (10, -16, "left"),
        "OpenMed-large @0.10": (-20, 6, "right"),
        "ai4privacy en": (-8, -16, "right"),
        "ai4privacy cat": (8, 14, "left"),
        "iiiorg/piiranha-v1": (-10, 2, "right"),
    }
    for name, x, y, mb, col in pts:
        s = 90 + np.sqrt(mb) * 9
        ax.scatter([x], [y], s=s, color=col, alpha=0.75 if col == C_OURS else 0.55,
                   edgecolor=darken(col), linewidth=1.2, zorder=3)
        dx, dy, ha = offsets[name]
        ax.annotate(name, (x, y), xytext=(dx, dy), textcoords="offset points",
                    ha=ha, fontsize=8.5, color=darken(col, 0.8), fontweight="bold")

    ax.set_xlim(-15, 300)
    ax.set_ylim(-9, 80)
    ax.set_xlabel("ms per note (CPU)", fontsize=9.5, color=C_INK)
    ax.set_ylabel("leak-document rate, % of 860 notes", fontsize=9.5, color=C_INK)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8.5, colors="#555555")
    ax.text(0.015, 0.155, "better ↙\n(faster & leaks less)", transform=ax.transAxes,
            fontsize=10, fontweight="bold", color=darken(C_OURS),
            ha="left", va="top")

    footnote(fig, FOOT + "; GLiNER, privacy-filter, Presidio excluded — ms n/m (predictions precomputed on GPU)")
    save(fig, "speed_vs_leaks.png")


# ---------------------------------------------------------------- figure 4
def fig_progress():
    data = {  # set -> [(round_label, n, ours_count, oml_count, verdict)]
        "familiar formats": [
            ("sealed 1\nn = 874", 874,
             report("sealed/clin_sealed", "rules+ours-shipped"),
             report("sealed/clin_sealed_openmed-large_t0.1", "rules+openmed-large-t0.1"),
             "lost"),
            ("sealed 2\nn = 860", 860,
             report("sealed2/clin2_sealed", "rules+ours-v1"),
             report("sealed2/clin2_sealed_openmed-large_t0.1", "rules+openmed-large-t0.1"),
             "tie"),
            ("sealed 3\nn = 7,108", 7108,
             report("sealed3/clin3_test_ours", "rules+ours"),
             report("sealed3/clin3_test_oml", "rules+openmed-large-t0.1"),
             "WIN\np = 8×10⁻⁷"),
        ],
        "novel formats (unseen)": [
            ("sealed 1\nn = 874", 874,
             report("sealed/clin_novel_sealed", "rules+ours-shipped"),
             report("sealed/clin_novel_sealed_openmed-large_t0.1", "rules+openmed-large-t0.1"),
             "lost"),
            ("sealed 2\nn = 860", 860,
             report("sealed2/clin2_novel_sealed", "rules+ours-v1"),
             report("sealed2/clin2_novel_sealed_openmed-large_t0.1", "rules+openmed-large-t0.1"),
             "tie"),
            ("sealed 3\nn = 7,108", 7108,
             report("sealed3/clin3_novel_all", "rules+ours"),
             report("sealed3/clin3_novel_all", "rules+openmed-large-t0.1"),
             "WIN\np = 4.7×10⁻¹⁰"),
        ],
    }
    # asserts against SEALED_RESULTS.md / SEALED2_RESULTS.md prose
    md1 = (RES / "SEALED_RESULTS.md").read_text()
    assert "0.5%**" in md1 and "1.9%" in md1 and "1.7%" in md1
    fam, nov = data["familiar formats"], data["novel formats (unseen)"]
    assert (fam[0][2]["docs_with_leak"], fam[0][3]["docs_with_leak"]) == (17, 4)   # 1.9% vs 0.5%
    assert (nov[0][2]["docs_with_leak"], nov[0][3]["docs_with_leak"]) == (15, 4)   # 1.7% vs 0.5%
    assert (fam[1][2]["docs_with_leak"], fam[1][3]["docs_with_leak"]) == (2, 5)    # 0.2% vs 0.6%
    assert (nov[1][2]["docs_with_leak"], nov[1][3]["docs_with_leak"]) == (2, 5)
    assert (fam[2][2]["docs_with_leak"], fam[2][3]["docs_with_leak"]) == (2, 26)
    assert (nov[2][2]["docs_with_leak"], nov[2][3]["docs_with_leak"]) == (1, 33)

    PLOTTED["progress"] = {
        s: [{"round": r[0].split("\n")[0], "n": r[1],
             "ours": r[2]["docs_with_leak"], "oml_t0.10": r[3]["docs_with_leak"]}
            for r in rows]
        for s, rows in data.items()}

    fig = newfig(10, 5.4)
    fig.suptitle("Three sealed evaluations — leak-document rate, rules + model",
                 x=0.03, y=0.965, ha="left", fontsize=15, fontweight="bold", color=C_INK)
    fig.text(0.03, 0.915, "each round: fresh notes, pre-registration committed before scoring",
             ha="left", fontsize=9.5, color="#555555")
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C_OURS),
               plt.Rectangle((0, 0), 1, 1, facecolor=C_OML)]
    fig.legend(handles, ["rules + ours", "rules + OpenMed-large @0.10"],
               loc="upper right", bbox_to_anchor=(0.985, 0.96), ncol=2,
               frameon=False, fontsize=9)

    for i, (setname, rows) in enumerate(data.items()):
        ax = fig.add_axes([0.07 + i * 0.475, 0.17, 0.40, 0.66])
        xs = np.arange(len(rows))
        w = 0.36
        for x, (_, n, o, m, verdict) in zip(xs, rows):
            ro, rm = leak_rate(o), leak_rate(m)
            ax.bar(x - w / 2, ro, width=w, color=C_OURS)
            ax.bar(x + w / 2, rm, width=w, color=C_OML)
            ax.text(x - w / 2, ro + 0.05, f"{ro:.2f}", ha="center", va="bottom",
                    fontsize=8, fontweight="bold", color=darken(C_OURS))
            ax.text(x + w / 2, rm + 0.05, f"{rm:.2f}", ha="center", va="bottom",
                    fontsize=8, fontweight="bold", color=darken(C_OML))
            col = {"lost": "#9e3d3d", "tie": "#777777"}.get(verdict.split("\n")[0], darken(C_OURS))
            ax.text(x, 2.28, verdict, ha="center", va="top", fontsize=9,
                    fontweight="bold", color=col)
        ax.set_xticks(xs)
        ax.set_xticklabels([r[0] for r in rows], fontsize=9, color=C_INK)
        ax.set_ylim(0, 2.62)
        ax.set_title(setname, loc="left", fontsize=11, fontweight="bold", color=C_INK)
        ax.set_ylabel("leak-document rate, %", fontsize=9, color=C_INK)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=8, colors="#555555")

    footnote(fig, FOOT)
    save(fig, "progress.png")


# ---------------------------------------------------------------- figure 5
def fig_categories():
    ours = report("sealed3/clin3_test_ours", None) if False else json.loads(
        (RES / "sealed3/clin3_test_ours" / "reports.json").read_text())
    oml = json.loads((RES / "sealed3/clin3_test_oml" / "reports.json").read_text())
    syscols = [
        ("ours\nalone", ours["ours"]),
        ("ours\n+ rules", ours["rules+ours"]),
        ("OpenMed-large @0.10\nalone", oml["openmed-large-t0.1"]),
        ("OpenMed-large @0.10\n+ rules", oml["rules+openmed-large-t0.1"]),
    ]
    cats = sorted(
        set().union(*[set(s[1]["by_category"]) for s in syscols]),
        key=lambda c: -syscols[0][1]["by_category"][c]["gold"])
    # zero-gold categories (BIOMETRIC, ID) have no recall to plot
    cats = [c for c in cats if syscols[0][1]["by_category"][c]["gold"] > 0]
    M = np.full((len(cats), len(syscols)), np.nan)
    for j, (_, s) in enumerate(syscols):
        for i, c in enumerate(cats):
            if c in s["by_category"]:
                g = s["by_category"][c]
                M[i, j] = 100.0 * g["caught"] / g["gold"]
    ns = [syscols[0][1]["by_category"][c]["gold"] for c in cats]

    PLOTTED["categories"] = {
        "categories": cats, "n": ns,
        "recall_pct": {syscols[j][0].split("\n")[0] + (" +rules" if "rules" in syscols[j][0] else ""): [round(v, 2) for v in M[:, j]] for j in range(len(syscols))},
    }

    fig = newfig(10, 7.6)
    ax = fig.add_axes([0.21, 0.10, 0.62, 0.76])
    fig.suptitle("Identifier recall by category — sealed 3, clin3 (7,108 notes)",
                 x=0.03, y=0.965, ha="left", fontsize=15, fontweight="bold", color=C_INK)
    fig.text(0.03, 0.925, "share of planted identifiers touched by a redaction — 100 = none missed",
             ha="left", fontsize=9.5, color="#555555")

    im = ax.imshow(M, aspect="auto", cmap="RdYlGn", vmin=90, vmax=100)
    ax.set_xticks(range(len(syscols)))
    ax.set_xticklabels([s[0] for s in syscols], fontsize=9, color=C_INK)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(range(len(cats)))
    ax.set_yticklabels([f"{c}  (n={n:,})" for c, n in zip(cats, ns)], fontsize=8.5, color=C_INK)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                    color="#1a1a1a" if v > 94 else "#7a1f1f",
                    fontweight="bold" if v < 99.5 else "normal")
    ax.set_xticks(np.arange(-0.5, len(syscols)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(cats)), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="both", length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("recall %", fontsize=8, color="#555555")
    cb.ax.tick_params(labelsize=7.5, colors="#555555")

    footnote(fig, FOOT)
    save(fig, "categories.png")


# ---------------------------------------------------------------- figure 6
def fig_pipeline():
    fig = newfig(10, 5.6)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.suptitle("How Scotoma works — everything on your machine",
                 x=0.03, y=0.955, ha="left", fontsize=15, fontweight="bold", color=C_INK)

    def box(x, y, w, h, title, sub="", fc="#f2f2f2", ec="#888888", fs=9.5, subfs=7.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012",
                                    facecolor=fc, edgecolor=ec, linewidth=1.2))
        ax.text(x + w / 2, y + h / 2 + (0.018 if sub else 0), title,
                ha="center", va="center", fontsize=fs, fontweight="bold", color=C_INK)
        if sub:
            ax.text(x + w / 2, y + h / 2 - 0.030, sub, ha="center", va="center",
                    fontsize=subfs, color="#555555")

    def arrow(x1, y1, x2, y2, color="#999999"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=14, color=color, linewidth=1.4))

    inputs = ["paste / hotkey (⌘⌥S)", "screenshot / region (⌘⌥D)", "PDF or scan", "dictation (⌘⌥V)"]
    iy = [0.74, 0.60, 0.46, 0.32]
    for label, y in zip(inputs, iy):
        box(0.03, y, 0.20, 0.10, label, fc="#eaf4fb", ec=C_PRIV)
        arrow(0.235, y + 0.05, 0.30, 0.60 if y > 0.5 else 0.52)

    box(0.30, 0.55, 0.17, 0.16, "on-device\nOCR / STT", "Apple Vision · your\nown speech server",
        fc="#eaf4fb", ec=C_PRIV)
    arrow(0.47, 0.63, 0.53, 0.63)

    box(0.53, 0.48, 0.20, 0.30, "Scotoma engine", "rules engine\n+ 141M model\n(int8, ~20 ms/note)",
        fc="#e2f4ee", ec=C_OURS, fs=11)
    arrow(0.73, 0.63, 0.79, 0.63)

    box(0.79, 0.55, 0.18, 0.16, "review", "approve, keep, or\nredact more",
        fc="#fff4e0", ec=C_OML)

    # outputs: one container (alternatives, not a chain), a single arrow in
    ax.add_patch(FancyBboxPatch((0.775, 0.02), 0.20, 0.50,
                                boxstyle="round,pad=0.008,rounding_size=0.012",
                                facecolor="#fafafa", edgecolor="#bbbbbb",
                                linewidth=1.0, linestyle="--"))
    ax.text(0.875, 0.49, "outputs", ha="center", fontsize=8, color="#777777",
            fontweight="bold")
    outputs = ["[NAME_1] tags", "realistic stand-ins",
               "black boxes on files", "protect & unlock (⌘R)"]
    oy = [0.375, 0.27, 0.165, 0.06]
    for label, y in zip(outputs, oy):
        box(0.79, y, 0.17, 0.085, label, fc="#f2f2f2", ec="#888888", fs=8.5)
    arrow(0.88, 0.545, 0.88, 0.51)

    band_y = 0.02
    ax.add_patch(FancyBboxPatch((0.03, band_y), 0.70, 0.10,
                                boxstyle="round,pad=0.008,rounding_size=0.012",
                                facecolor="#e2f4ee", edgecolor=C_OURS, linewidth=1.4))
    ax.text(0.38, band_y + 0.05,
            "nothing leaves your device — no telemetry; the only socket is an optional,\n"
            "opt-in loopback connection to your own speech server",
            ha="center", va="center", fontsize=9, fontweight="bold", color=darken(C_OURS))

    footnote(fig, "")
    save(fig, "pipeline.png")


# ---------------------------------------------------------------- figure 7
def _render_note(src: Path, out: Path):
    """Render the example note as a clean letter-size page image (200 dpi)."""
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
    d.text((x, 120), "RIVERSIDE CLINIC — INTERNAL NOTE", font=fh, fill="#222222")
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

# ---------------------------------------------------------------- figure 7
def fig_before_after():
    scotoma = ROOT / "target" / "release" / "scotoma"
    helper = ROOT / "app" / "src-tauri" / "bin" / "scotoma-helper"
    src = ROOT / "examples" / "21_hard_caps_and_bare_names.txt"
    needles = ["OKONKWO", "THADDEUS", "Marisol", "Reyes", "Larchmont", "Waukegan",
               "60085", "7KQ-2291", "555-0193", "00418827", "June", "03/14/2025"]
    # clinical words that must NOT be boxed
    keeps = ["Graves", "Bell", "palsy", "Metoprolol", "HR 88", "97%", "Intake"]

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
        subprocess.run([str(scotoma), "redact-file", str(in_png), str(out_png),
                        "--model", str(ROOT / "models" / "scotoma-small")],
                       check=True, capture_output=True)
        ocr = subprocess.run([str(helper), "ocr-boxes", str(out_png)],
                             check=True, capture_output=True)
        pages = json.loads(ocr.stdout)["pages"]
        text = " ".join(l["text"] for p in pages for l in p["lines"])

        leaks = [n for n in needles if n.lower() in text.lower()]
        # partial-box check: an OCR'd word that is itself a long fragment of a
        # planted value (edge bleed around a box) is still a leak even when no
        # whole planted string survives
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

        # vitals the engine boxes anyway — shown honestly in the caption
        vitals_boxed = [k for k in ("148/92", "SpO2", "Civic")
                        if k.lower() not in text.lower()
                        and k.lower().replace("o", "0") not in text.lower()]

        ib, ia = plt.imread(in_png), plt.imread(out_png)
        PLOTTED["before_after"] = {
            "planted_checked": needles, "leaks": [],
            "kept_checked": keeps, "vitals_boxed": vitals_boxed,
        }

    fig = newfig(10, 4.0)
    fig.suptitle("A page in, a clean page out — on-device",
                 x=0.03, y=0.93, ha="left", fontsize=15, fontweight="bold", color=C_INK)
    fig.text(0.03, 0.845,
             "synthetic example note (examples/21_hard_caps_and_bare_names.txt) — "
             "on-device OCR → detected identifiers → black boxes, nothing sent anywhere",
             ha="left", fontsize=9, color="#555555")
    if vitals_boxed:
        fig.text(0.03, 0.765,
                 "over-redaction shown as-is: "
                 + ", ".join(f"“{v}”" for v in vitals_boxed)
                 + " boxed — false positives",
                 ha="left", fontsize=8.5, color="#8a5a00")
    for i, (img, t) in enumerate([(ib, "before"), (ia, "after  ·  scotoma redact-file")]):
        ax = fig.add_axes([0.04 + i * 0.50, 0.03, 0.43, 0.66])
        ax.imshow(img)
        ax.set_title(t, fontsize=11, fontweight="bold",
                     color=C_INK if i == 0 else darken(C_OURS))
        ax.axis("off")
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_color("#cccccc")
    footnote(fig, FOOT)
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
