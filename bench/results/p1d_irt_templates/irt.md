# Item analysis: p1d_irt_test_tpl.csv

3000 docs, 33082 items, 7 systems. Fit: 2PL joint MAP (regularized joint MLE), N(0,1) priors on log a, b and theta; alternating damped Newton. Items answered identically by all systems are non-informative and dropped.

**Identification caveat:** 7 responses per item is far too few to pin down a and b on its own; the priors dominate for hard/easy items. Treat a and b as rankings under shrinkage, not calibrated measurements. Per-item a/b are exploratory — do not drop or rewrite items from point estimates; the tag-level aggregates below are the main output. A binary outcome across 7 systems also has at most 2^7 distinct response patterns, so items with the same pattern share fitted a and b: by-tag difficulty means are coarse-grained over those patterns.

## Systems (touched = correct)

20545 informative items (12537 dropped).

| system | theta | se | empirical p |
|---|---|---|---|
| rules | -1.53 | 0.02 | 0.529 |
| openmed | +2.33 | 0.03 | 0.923 |
| stanford | +4.14 | 0.07 | 0.970 |
| openmed-large-fp32 | +5.09 | 0.10 | 0.977 |
| presidio | +1.57 | 0.02 | 0.883 |
| ours | +4.14 | 0.07 | 0.967 |
| privacy-filter | +0.33 | 0.01 | 0.742 |

## Systems (fully redacted = correct)

24072 informative items (9010 dropped).

| system | theta | se | empirical p |
|---|---|---|---|
| rules | -1.09 | 0.01 | 0.514 |
| openmed | +1.25 | 0.01 | 0.826 |
| stanford | +1.98 | 0.02 | 0.885 |
| openmed-large-fp32 | +1.97 | 0.02 | 0.907 |
| presidio | +1.07 | 0.01 | 0.809 |
| ours | +2.66 | 0.03 | 0.930 |
| privacy-filter | +0.30 | 0.01 | 0.728 |

## Item difficulty by tag (touched fit)

| tag | n | mean b | sd b | mean p |
|---|---|---|---|---|
| fmt:dot | 83 | -0.30 | 0.18 | 0.843 |
| fmt:space | 76 | -0.29 | 0.20 | 0.838 |
| fmt:dash | 70 | -0.26 | 0.25 | 0.835 |
| fmt:paren | 90 | -0.24 | 0.23 | 0.817 |
| fmt:numeric_us | 37 | -0.24 | 0.21 | 0.834 |
| fmt:intl | 107 | -0.24 | 0.23 | 0.810 |
| fmt:dashed | 134 | -0.24 | 0.27 | 0.839 |
| fmt:named_abbr | 180 | -0.24 | 0.27 | 0.840 |
| fmt:day_first | 162 | -0.23 | 0.27 | 0.837 |
| fmt:named | 177 | -0.22 | 0.29 | 0.837 |
| fmt:month_year | 190 | -0.21 | 0.31 | 0.833 |
| fmt:plain | 171 | -0.20 | 0.30 | 0.834 |
| fmt:partial | 224 | -0.19 | 0.35 | 0.824 |
| fmt:numeric_short | 47 | -0.17 | 0.32 | 0.809 |
| fmt:iso | 61 | -0.17 | 0.32 | 0.815 |
| fmt:initial | 1471 | -0.13 | 0.37 | 0.812 |
| spoken | 1327 | -0.12 | 0.33 | 0.745 |
| repeat | 5275 | -0.12 | 0.38 | 0.806 |
| relative | 4568 | -0.12 | 0.38 | 0.804 |
| cue | 3197 | -0.10 | 0.35 | 0.756 |
| single_name | 5688 | -0.06 | 0.42 | 0.792 |
| fmt:last_first_caps | 231 | -0.02 | 0.36 | 0.734 |
| no_cue | 17348 | +0.02 | 0.44 | 0.770 |
| ocr | 663 | +0.06 | 0.43 | 0.759 |
| common_word_name | 1535 | +0.06 | 0.49 | 0.744 |
| chat | 2854 | +0.16 | 0.49 | 0.721 |

**1799 items with near-zero discrimination (a < 0.5)** — with this few systems these are exploratory point estimates, not grounds to drop or rewrite the items; use the tag aggregates above.

Examples: `B1-000002#8` (ID), `B1-000003#4` (ID), `B1-000005#2` (LOCATION), `B1-000009#4` (MRN), `B1-000013#0` (ACCOUNT), `B1-000013#1` (ACCOUNT), `B1-000014#7` (NAME), `B1-000016#1` (AGE), `B1-000016#9` (ORG), `B1-000017#0` (NAME)

## Character-level operating-point diagnostic (d' and criterion)

H = identifier characters redacted (`chars`, span recall when the sweep predates it), F = ordinary characters redacted (over-redaction). Rates get the loglinear correction (hits+0.5)/(n+1); n = 401074 identifier chars for H (33082 spans in the recall fallback) and 1e+06 ordinary chars for F (pass --id-chars/--clean-chars from the eval report for exact values). d' = z(H)-z(F) measures sensitivity; c = -(z(H)+z(F))/2 measures how conservative the operating point is (c>0 = cautious).

### ours

n(H) = 133750 identifier chars, n(F) = 225933 ordinary chars (from sweep).

max d' = 4.37 at threshold 0.3499999940395355; d' at default 0.35 = 4.37 (nearest threshold 0.3499999940395355).

| threshold | H (chars) | F | d' | c |
|---|---|---|---|---|
| 0.05000000074505806 | 0.9818 | 0.01632 | 4.23 | +0.02 |
| 0.10000000149011612 | 0.9768 | 0.01028 | 4.31 | +0.16 |
| 0.20000000298023224 | 0.9686 | 0.00648 | 4.35 | +0.31 |
| 0.3499999940395355 | 0.9585 | 0.00422 | 4.37 | +0.45 |
| 0.5 | 0.9480 | 0.00336 | 4.34 | +0.54 |
| 0.699999988079071 | 0.9283 | 0.00261 | 4.26 | +0.67 |
| 0.8999999761581421 | 0.8791 | 0.00158 | 4.12 | +0.89 |

