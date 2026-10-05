#!/usr/bin/env python3
"""Item analysis for the benchmark: 2PL IRT on the response matrix.

    python bench/irt.py bench/results/phase0_templates/responses.csv bench/data/test_tpl.jsonl --out DIR
    python bench/irt.py responses.csv data.jsonl --out DIR --sweep rules=sweep_rules.json

responses.csv comes from bench/run.py: one row per gold identifier,
`item` = `<doc id>#<gold index>` where the gold index is the position of the
span in the doc's parsed span list (see crates/core/src/eval.rs), and each
system column is 0 = missed, 1 = partly redacted, 2 = fully redacted.

Two fits: outcome >= 1 ("identifier touched", the recall the evaler reports)
and outcome == 2 ("fully redacted"). The model is a 2PL

    p_ij = sigmoid( a_i * (theta_j - b_i) )

fitted by joint MAP (regularized joint MLE): alternating damped Newton steps
on (log a_i, b_i) and theta_j, all under N(0,1) priors. With only a handful of
systems per item the item parameters are weakly identified; the priors pull
estimates toward a = 1, b = 0, theta = 0 rather than let them blow up. Items
answered identically by every system carry no information and are dropped
from the fit.

--sweep NAME=FILE.json reads `scotoma sweep --json` output (a list of
{"threshold", "chars", "recall", "over_redaction", ...} rows) and reports a
character-level operating-point diagnostic: d' = z(H)-z(F) and criterion
c = -(z(H)+z(F))/2 with H = `chars` (falls back to `recall` with a warning),
F = `over_redaction`, loglinear-corrected (hits+0.5)/(n+1). Denominators:
identifier characters of the response items (override --id-chars) and
--clean-chars for F.

Writes DIR/items.csv and DIR/irt.md. numpy only for the fit.
"""
import argparse, csv, json, os, sys
from statistics import NormalDist

import numpy as np

Z = NormalDist().inv_cdf
SPAN_LIST_KEYS = ("spans", "entities", "privacy_mask", "labels")
TEXT_KEYS = ("text", "source_text", "full_text", "document")
LABEL_KEYS = ("label", "entity_type", "type", "entity")


# ---------------------------------------------------------------------------
# Data, mirroring crates/core/src/eval.rs::parse_jsonl and the responses id:
# doc id = "id" field or doc<1-based line number>; item id = <doc id>#<span index>.
# ---------------------------------------------------------------------------

def load_data(path):
    """Return ({item_id: (label, tags, span_text)}, n_docs)."""
    items = {}
    n = 0
    for lineno, line in enumerate(open(path, encoding="utf-8"), start=1):
        if not line.strip():
            continue
        v = json.loads(line)
        n += 1
        doc_id = str(v.get("id") or f"doc{lineno}")
        text = next((str(v[k]) for k in TEXT_KEYS if isinstance(v.get(k), str)), "")
        spans = next((v[k] for k in SPAN_LIST_KEYS if k in v), []) or []
        if isinstance(spans, str):
            spans = json.loads(spans)
        gi = 0
        for s in spans:
            if not isinstance(s, dict):
                continue
            a, b = s.get("start"), s.get("end")
            if not isinstance(a, int) or not isinstance(b, int) or not a < b:
                continue
            label = next((str(s[k]) for k in LABEL_KEYS if isinstance(s.get(k), str)), "")
            tags = [str(t) for t in s.get("tags", []) if isinstance(t, str)]
            items[f"{doc_id}#{gi}"] = (label, tags, text[a:b])
            gi += 1
    return items, n


def load_responses(path):
    """Return (system names, {item: {system: outcome or None}})."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    systems = [c for c in rows[0] if c != "item"]
    out = {}
    for r in rows:
        out[r["item"]] = {s: (int(r[s]) if r.get(s) not in (None, "") else None) for s in systems}
    return systems, out


# ---------------------------------------------------------------------------
# 2PL joint MAP fit. All parameters under N(0,1) priors; Newton with step
# halving on the per-item / per-system objective.
# ---------------------------------------------------------------------------

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def nll_items(Y, M, alpha, b, th):
    """Per-item negative joint log-posterior (I,) — used for step halving."""
    a = np.exp(alpha)[:, None]
    z = a * (th[None, :] - b[:, None])
    ll = M * (Y * (-np.logaddexp(0, -z)) + (1 - Y) * (-np.logaddexp(0, z)))
    return -ll.sum(axis=1) + 0.5 * (alpha ** 2 + b ** 2)


def nll_systems(Y, M, alpha, b, th):
    a = np.exp(alpha)[:, None]
    z = a * (th[None, :] - b[:, None])
    ll = M * (Y * (-np.logaddexp(0, -z)) + (1 - Y) * (-np.logaddexp(0, z)))
    return -ll.sum(axis=0) + 0.5 * th ** 2


def fit(Y, M, iters=80):
    """Joint MAP 2PL. Y (I,S) with NaN for missing; M = ~isnan(Y). Returns
    a, b, th, se_th."""
    I, S = Y.shape
    p_hat = np.where(M.sum(axis=1) > 0, np.nan_to_num(Y).sum(axis=1) / np.maximum(M.sum(axis=1), 1), 0.5)
    alpha = np.zeros(I)
    b = np.clip(np.log((1 - np.clip(p_hat, 0.02, 0.98)) / np.clip(p_hat, 0.02, 0.98)), -4, 4)
    th = np.zeros(S)
    Y = np.nan_to_num(Y)

    for _ in range(iters):
        a = np.exp(alpha)[:, None]
        z = a * (th[None, :] - b[:, None])
        p = sigmoid(z)
        r = M * (Y - p)
        q = M * p * (1 - p)
        # item (alpha, b): gradient and Hessian of the negative posterior
        ga = (r * a * (th[None, :] - b[:, None])).sum(axis=1) - alpha
        gb = (-r * a).sum(axis=1) - b
        haa = ((r - q * a * (th[None, :] - b[:, None])) * a * (th[None, :] - b[:, None])).sum(axis=1) - 1.0
        hbb = (-q * a * a).sum(axis=1) - 1.0
        hab = ((-r + q * a * (th[None, :] - b[:, None])) * a).sum(axis=1)
        det = haa * hbb - hab * hab
        det = np.where(np.abs(det) < 1e-9, -1e-9, det)
        da = -(hbb * ga - hab * gb) / det
        db = -(-hab * ga + haa * gb) / det
        base = nll_items(Y, M, alpha, b, th)
        for shrink in (1.0, 0.5, 0.25, 0.125, 0.0625):
            na, nb = alpha + shrink * da, b + shrink * db
            better = nll_items(Y, M, na, nb, th) <= base + 1e-9
            alpha = np.where(better, na, alpha)
            b = np.where(better, nb, b)
            if better.all():
                break
        # system theta: scalar Newton per system
        a = np.exp(alpha)[:, None]
        z = a * (th[None, :] - b[:, None])
        p = sigmoid(z)
        r = M * (Y - p)
        q = M * p * (1 - p)
        gt = (r * a).sum(axis=0) - th
        ht = (-q * a * a).sum(axis=0) - 1.0
        dt = -gt / ht
        base = nll_systems(Y, M, alpha, b, th)
        for shrink in (1.0, 0.5, 0.25, 0.125):
            nt = th + shrink * dt
            better = nll_systems(Y, M, alpha, b, nt) <= base + 1e-9
            th = np.where(better, nt, th)
            if better.all():
                break
        if max(np.abs(da).max(initial=0), np.abs(db).max(initial=0), np.abs(dt).max(initial=0)) < 1e-5:
            break
    a = np.exp(alpha)[:, None]
    info = (M * sigmoid(a * (th[None, :] - b[:, None])) * (1 - sigmoid(a * (th[None, :] - b[:, None]))) * a * a).sum(axis=0) + 1.0
    return np.exp(alpha), b, th, 1.0 / np.sqrt(info)


# ---------------------------------------------------------------------------
def dprime(rows, n_span, n_id_chars, n_clean):
    """rows: sweep --json list. Hit rate H is the identifier-character
    redaction rate (`chars`), falling back to span recall with a warning when
    the sweep was produced before C4 added `chars`. Rates get the loglinear
    correction (hits+0.5)/(n+1); n = n_id_chars for H with `chars` (n_span for
    the `recall` fallback) and n_clean for F. Boundary rates are flagged:
    correction turns a 0/1 into a bound, not a measurement.
    Returns (table, (max_d', thr, bounded), (d'@~0.35, thr), h_key)."""
    h_key = "chars" if rows and all("chars" in r for r in rows) else "recall"
    n_h = n_id_chars if h_key == "chars" else n_span
    table, best, at35 = [], None, None
    for r in sorted(rows, key=lambda r: r["threshold"]):
        raw_h, raw_f = r[h_key], r["over_redaction"]
        h = (raw_h * n_h + 0.5) / (n_h + 1)
        f = (raw_f * n_clean + 0.5) / (n_clean + 1)
        bounded = raw_h <= 0 or raw_h >= 1 or raw_f <= 0 or raw_f >= 1
        d, c = Z(h) - Z(f), -(Z(h) + Z(f)) / 2
        table.append((r["threshold"], raw_h, raw_f, d, c, bounded))
        if best is None or d > best[0]:
            best = (d, r["threshold"], bounded)
        if at35 is None or abs(r["threshold"] - 0.35) < abs(at35[1] - 0.35):
            at35 = (d, r["threshold"])
    return table, best, at35, h_key


# ---------------------------------------------------------------------------

def run(correct, iters=80):
    """correct: (I,S) float with NaN missing. Returns keep mask + fit.
    Informative = at least one observed 0 and one observed 1; missing cells
    are neutral, they cannot make an item informative."""
    M = ~np.isnan(correct)
    informative = ((correct == 0) & M).any(axis=1) & ((correct == 1) & M).any(axis=1)
    keep = np.where(informative)[0]
    a, b, th, se = fit(np.where(M[keep], correct[keep], np.nan), M[keep], iters)
    return keep, a, b, th, se


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("responses")
    ap.add_argument("data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sweep", action="append", default=[], metavar="NAME=SWEEP.json")
    ap.add_argument("--clean-chars", type=float, default=1e6,
                    help="non-identifier characters the sweep covered; the false-alarm "
                         "denominator for d' (default 1e6)")
    ap.add_argument("--id-chars", type=int, default=None,
                    help="identifier characters the sweep covered; the hit-rate denominator "
                         "for d' (default: non-whitespace chars of the response items' spans)")
    a = ap.parse_args()

    systems, resp = load_responses(a.responses)
    meta, n_docs = load_data(a.data)
    items = sorted(resp)
    missing = [it for it in items if it not in meta]
    if missing:
        sys.exit(f"{len(missing)} response items do not match any gold span "
                 f"(first: {missing[:3]}). responses.csv and data file disagree.")
    outcome = np.array([[resp[it][s] for s in systems] for it in items], dtype=float)
    touched = np.where(np.isnan(outcome), np.nan, (outcome >= 1).astype(float))
    full = np.where(np.isnan(outcome), np.nan, (outcome == 2).astype(float))
    # Identifier-character denominator for the character-level d': the
    # non-whitespace UTF-8 bytes of exactly the spans the evaler scored —
    # same quantity as the report's gold_chars, without re-implementing
    # the policy filter.
    id_chars = a.id_chars or sum(
        len("".join(meta[it][2].split()).encode("utf-8")) for it in items)

    fits = {}
    for name, Y in [("touched", touched), ("full", full)]:
        keep, fa, fb, th, se = run(Y)
        fits[name] = (keep, fa, fb, th, se)

    keep, fa, fb, th, se = fits["touched"]
    keep_set = set(keep.tolist())
    p_corr = np.nanmean(touched, axis=1)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "items.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "a", "b", "p-correct", "tags"])
        for i, it in enumerate(items):
            k = np.searchsorted(keep, i)
            fitted = i in keep_set
            _, tags, _ = meta[it]
            if not fitted:
                tags = tags + ["non-informative"]
            w.writerow([it,
                        f"{fa[k]:.3f}" if fitted else "",
                        f"{fb[k]:.3f}" if fitted else "",
                        f"{p_corr[i]:.3f}", "|".join(sorted(tags))])

    # ---- irt.md -----------------------------------------------------------
    L = [f"# Item analysis: {os.path.basename(a.responses)}", "",
         f"{n_docs} docs, {len(items)} items, {len(systems)} systems. "
         f"Fit: 2PL joint MAP (regularized joint MLE), N(0,1) priors on "
         f"log a, b and theta; alternating damped Newton. "
         f"Items answered identically by all systems are non-informative and dropped.", "",
         f"**Identification caveat:** {len(systems)} responses per item is far too few to pin down "
         "a and b on its own; the priors dominate for hard/easy items. Treat a and b as "
         "rankings under shrinkage, not calibrated measurements. Per-item a/b are "
         "exploratory — do not drop or rewrite items from point estimates; the "
         "tag-level aggregates below are the main output. A binary outcome across "
         f"{len(systems)} systems also has at most 2^{len(systems)} distinct response patterns, so "
         "items with the same pattern share fitted a and b: by-tag difficulty means are "
         "coarse-grained over those patterns.", ""]
    for name, (keep, fa, fb, th, se) in fits.items():
        L += [f"## Systems ({'touched' if name == 'touched' else 'fully redacted'} = correct)", "",
              f"{len(keep)} informative items ({len(items) - len(keep)} dropped).", "",
              "| system | theta | se | empirical p |", "|---|---|---|---|"]
        for j, s in enumerate(systems):
            emp = np.nanmean((touched if name == "touched" else full)[:, j])
            L.append(f"| {s} | {th[j]:+.2f} | {se[j]:.2f} | {emp:.3f} |")
        L += [""]
    keep, fa, fb, _, _ = fits["touched"]
    fa_map = dict(zip(keep.tolist(), fa))
    fb_map = dict(zip(keep.tolist(), fb))
    by_tag = {}
    for i in keep:
        for t in meta[items[i]][1]:
            by_tag.setdefault(t, []).append(i)
    L += ["## Item difficulty by tag (touched fit)", "",
          "| tag | n | mean b | sd b | mean p |", "|---|---|---|---|---|"]
    for t, idx in sorted(by_tag.items(), key=lambda kv: np.mean([fb_map[i] for i in kv[1]])):
        bs = np.array([fb_map[i] for i in idx])
        L.append(f"| {t} | {len(idx)} | {bs.mean():+.2f} | {bs.std():.2f} | {p_corr[idx].mean():.3f} |")
    near0 = [i for i in keep if fa_map[i] < 0.5]
    L += ["", f"**{len(near0)} items with near-zero discrimination (a < 0.5)** "
          "— with this few systems these are exploratory point estimates, not "
          "grounds to drop or rewrite the items; use the tag aggregates above.", ""]
    if near0:
        ex = ", ".join(f"`{items[i]}` ({meta[items[i]][0]})" for i in near0[:10])
        L += [f"Examples: {ex}", ""]

    sweeps = [s.partition("=") for s in a.sweep]
    if sweeps:
        L += ["## Character-level operating-point diagnostic (d' and criterion)", "",
              "H = identifier characters redacted (`chars`, span recall when the sweep "
              "predates it), F = ordinary characters redacted (over-redaction). "
              "Rates get the loglinear correction (hits+0.5)/(n+1); "
              f"n = {id_chars} identifier chars for H ({len(items)} spans in the "
              f"recall fallback) and {a.clean_chars:g} ordinary chars for F "
              "(pass --id-chars/--clean-chars from the eval report for exact values). "
              "d' = z(H)-z(F) measures sensitivity; c = -(z(H)+z(F))/2 measures how "
              "conservative the operating point is (c>0 = cautious).", ""]
        for name, _, path in sweeps:
            rows = json.load(open(path))
            # Exact denominators from the sweep when present (scotoma sweep --json emits
            # gold_chars/clean_chars); otherwise the estimates/overrides above.
            n_id = rows[0].get("gold_chars") or id_chars
            n_cl = rows[0].get("clean_chars") or a.clean_chars
            table, best, at35, h_key = dprime(rows, len(items), n_id, n_cl)
            warn = (f"⚠ `{path}` has no `chars` column — H is span recall, "
                    "not the identifier-character rate. ") if h_key == "recall" else ""
            L += [f"### {name}", "", f"n(H) = {n_id:g} identifier chars, n(F) = {n_cl:g} ordinary chars" + (" (from sweep)" if rows[0].get('clean_chars') else " (estimated; pass --id-chars/--clean-chars)") + ".", "",
                  warn + f"max d' = {best[0]:.2f} at threshold {best[1]}"
                  + (" (boundary rate corrected: a bound, not a measurement)" if best[2] else "")
                  + f"; d' at default 0.35 = {at35[0]:.2f} (nearest threshold {at35[1]}).", "",
                  f"| threshold | H ({h_key}) | F | d' | c |", "|---|---|---|---|---|"]
            for thr, h, f, d, c, bounded in table:
                L.append(f"| {thr} | {h:.4f} | {f:.5f}{' *' if bounded else ''} | {d:.2f} | {c:+.2f} |")
            if any(t[5] for t in table):
                L += ["", "\\* boundary rate (0 or 1) — loglinear correction makes z a bound."]
            L += [""]
    open(os.path.join(a.out, "irt.md"), "w").write("\n".join(L) + "\n")
    print(f"wrote {a.out}/items.csv and {a.out}/irt.md "
          f"({len(keep)} informative of {len(items)} items, {len(systems)} systems)")


if __name__ == "__main__":
    main()
