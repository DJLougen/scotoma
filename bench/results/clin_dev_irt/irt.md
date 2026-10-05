# Item analysis: clin_dev_irt_matrix.csv

844 docs, 7117 items, 14 systems. Fit: 2PL joint MAP (regularized joint MLE), N(0,1) priors on log a, b and theta; alternating damped Newton. Items answered identically by all systems are non-informative and dropped.

**Identification caveat:** 14 responses per item is far too few to pin down a and b on its own; the priors dominate for hard/easy items. Treat a and b as rankings under shrinkage, not calibrated measurements. Per-item a/b are exploratory — do not drop or rewrite items from point estimates; the tag-level aggregates below are the main output. A binary outcome across 14 systems also has at most 2^14 distinct response patterns, so items with the same pattern share fitted a and b: by-tag difficulty means are coarse-grained over those patterns.

## Systems (touched = correct)

6082 informative items (1035 dropped).

| system | theta | se | empirical p |
|---|---|---|---|
| rules | -0.81 | 0.02 | 0.473 |
| ours-fp32 | +6.97 | 0.37 | 0.997 |
| openmed | +2.27 | 0.06 | 0.927 |
| openmed-large | +5.14 | 0.21 | 0.985 |
| stanford | +2.78 | 0.07 | 0.951 |
| piiranha | -0.18 | 0.02 | 0.573 |
| ai4privacy-en | +0.51 | 0.02 | 0.775 |
| ai4privacy-cat | +0.23 | 0.02 | 0.699 |
| privacy-filter | +1.42 | 0.03 | 0.871 |
| presidio | +1.02 | 0.02 | 0.823 |
| gliner-edge | +3.06 | 0.09 | 0.963 |
| gliner-nvidia | +2.93 | 0.08 | 0.956 |
| gliner-knowledgator-large | +1.48 | 0.03 | 0.885 |
| gliner-knowledgator-base | +1.08 | 0.03 | 0.838 |

## Systems (fully redacted = correct)

6357 informative items (760 dropped).

| system | theta | se | empirical p |
|---|---|---|---|
| rules | -0.60 | 0.02 | 0.469 |
| ours-fp32 | +2.92 | 0.07 | 0.968 |
| openmed | +1.50 | 0.03 | 0.866 |
| openmed-large | +2.44 | 0.06 | 0.942 |
| stanford | +1.14 | 0.03 | 0.833 |
| piiranha | -0.33 | 0.01 | 0.490 |
| ai4privacy-en | +0.18 | 0.01 | 0.667 |
| ai4privacy-cat | -0.25 | 0.01 | 0.526 |
| privacy-filter | +1.29 | 0.03 | 0.855 |
| presidio | +0.44 | 0.02 | 0.679 |
| gliner-edge | +1.93 | 0.04 | 0.905 |
| gliner-nvidia | +2.02 | 0.04 | 0.911 |
| gliner-knowledgator-large | +1.23 | 0.03 | 0.853 |
| gliner-knowledgator-base | +0.81 | 0.02 | 0.773 |

## Item difficulty by tag (touched fit)

| tag | n | mean b | sd b | mean p |
|---|---|---|---|---|
| fmt:paren | 55 | -0.86 | 0.12 | 0.916 |
| fmt:dot | 62 | -0.78 | 0.11 | 0.914 |
| fmt:dash | 53 | -0.68 | 0.13 | 0.915 |
| fmt:numeric_us | 83 | -0.67 | 0.08 | 0.924 |
| fmt:numeric_short | 77 | -0.63 | 0.11 | 0.916 |
| fmt:iso | 57 | -0.62 | 0.15 | 0.914 |
| fmt:named_abbr | 61 | -0.60 | 0.22 | 0.907 |
| fmt:named | 65 | -0.58 | 0.19 | 0.910 |
| fmt:partial | 47 | -0.33 | 0.33 | 0.857 |
| m:cue | 1234 | -0.30 | 0.37 | 0.836 |
| m:digit_spaced | 59 | -0.19 | 0.41 | 0.680 |
| planted | 6082 | -0.17 | 0.44 | 0.809 |
| repeat | 1142 | -0.15 | 0.44 | 0.789 |
| m:no_cue | 4848 | -0.14 | 0.45 | 0.802 |
| spoken | 258 | -0.11 | 0.45 | 0.700 |
| m:repeat | 1360 | -0.03 | 0.46 | 0.760 |
| m:single_name | 1151 | +0.08 | 0.46 | 0.731 |
| single_name | 1151 | +0.08 | 0.46 | 0.731 |
| fmt:initial | 73 | +0.15 | 0.36 | 0.702 |
| m:lower | 17 | +0.28 | 0.44 | 0.664 |
| fmt:last_first_caps | 194 | +0.34 | 0.56 | 0.615 |

**216 items with near-zero discrimination (a < 0.5)** — with this few systems these are exploratory point estimates, not grounds to drop or rewrite the items; use the tag aggregates above.

Examples: `C-clinical-11-00006#7` (PLAN), `C-clinical-11-00026#6` (ACCOUNT), `C-clinical-11-00026#7` (ACCOUNT), `C-clinical-11-00030#4` (ACCOUNT), `C-clinical-11-00054#3` (URL), `C-clinical-11-00054#6` (URL), `C-clinical-11-00068#8` (VEHICLE), `C-clinical-11-00100#6` (ACCOUNT), `C-clinical-11-00100#7` (ACCOUNT), `C-clinical-11-00112#4` (AGE)

## Character-level operating-point diagnostic (d' and criterion)

H = identifier characters redacted (`chars`, span recall when the sweep predates it), F = ordinary characters redacted (over-redaction). Rates get the loglinear correction (hits+0.5)/(n+1); n = 84700 identifier chars for H (7117 spans in the recall fallback) and 1e+06 ordinary chars for F (pass --id-chars/--clean-chars from the eval report for exact values). d' = z(H)-z(F) measures sensitivity; c = -(z(H)+z(F))/2 measures how conservative the operating point is (c>0 = cautious).

### ours-shipped

n(H) = 84700 identifier chars, n(F) = 339298 ordinary chars (from sweep).

max d' = 5.46 at threshold 0.10000000149011612; d' at default 0.35 = 5.34 (nearest threshold 0.3499999940395355).

| threshold | H (chars) | F | d' | c |
|---|---|---|---|---|
| 0.009999999776482582 | 0.9931 | 0.00202 | 5.34 | +0.21 |
| 0.019999999552965164 | 0.9906 | 0.00120 | 5.39 | +0.34 |
| 0.05000000074505806 | 0.9862 | 0.00058 | 5.45 | +0.52 |
| 0.10000000149011612 | 0.9822 | 0.00038 | 5.46 | +0.63 |
| 0.20000000298023224 | 0.9754 | 0.00028 | 5.41 | +0.74 |
| 0.3499999940395355 | 0.9645 | 0.00020 | 5.34 | +0.87 |
| 0.5 | 0.9527 | 0.00010 | 5.38 | +1.02 |
| 0.699999988079071 | 0.9311 | 0.00006 | 5.33 | +1.18 |
| 0.8999999761581421 | 0.8847 | 0.00001 | 5.40 | +1.50 |

### ours-fp32

n(H) = 84700 identifier chars, n(F) = 339298 ordinary chars (from sweep).

max d' = 5.71 at threshold 0.3499999940395355; d' at default 0.35 = 5.71 (nearest threshold 0.3499999940395355).

| threshold | H (chars) | F | d' | c |
|---|---|---|---|---|
| 0.009999999776482582 | 0.9949 | 0.00476 | 5.16 | +0.01 |
| 0.019999999552965164 | 0.9942 | 0.00297 | 5.28 | +0.11 |
| 0.05000000074505806 | 0.9937 | 0.00161 | 5.44 | +0.23 |
| 0.10000000149011612 | 0.9929 | 0.00093 | 5.56 | +0.33 |
| 0.20000000298023224 | 0.9925 | 0.00055 | 5.70 | +0.42 |
| 0.3499999940395355 | 0.9906 | 0.00039 | 5.71 | +0.50 |
| 0.5 | 0.9894 | 0.00033 | 5.71 | +0.55 |
| 0.699999988079071 | 0.9858 | 0.00023 | 5.70 | +0.66 |
| 0.8999999761581421 | 0.9762 | 0.00016 | 5.57 | +0.81 |

### openmed-large

n(H) = 84700 identifier chars, n(F) = 339298 ordinary chars (from sweep).

max d' = 4.99 at threshold 0.5; d' at default 0.35 = 4.90 (nearest threshold 0.3499999940395355).

| threshold | H (chars) | F | d' | c |
|---|---|---|---|---|
| 0.009999999776482582 | 0.9897 | 0.00989 | 4.65 | +0.01 |
| 0.019999999552965164 | 0.9878 | 0.00789 | 4.66 | +0.08 |
| 0.05000000074505806 | 0.9851 | 0.00509 | 4.74 | +0.20 |
| 0.10000000149011612 | 0.9819 | 0.00320 | 4.82 | +0.32 |
| 0.20000000298023224 | 0.9773 | 0.00202 | 4.88 | +0.44 |
| 0.3499999940395355 | 0.9710 | 0.00134 | 4.90 | +0.55 |
| 0.5 | 0.9642 | 0.00071 | 4.99 | +0.69 |
| 0.699999988079071 | 0.9501 | 0.00048 | 4.95 | +0.83 |
| 0.8999999761581421 | 0.9085 | 0.00029 | 4.77 | +1.06 |

### openmed

n(H) = 84700 identifier chars, n(F) = 339298 ordinary chars (from sweep).

max d' = 4.96 at threshold 0.20000000298023224; d' at default 0.35 = 4.91 (nearest threshold 0.3499999940395355).

| threshold | H (chars) | F | d' | c |
|---|---|---|---|---|
| 0.009999999776482582 | 0.9644 | 0.00590 | 4.32 | +0.36 |
| 0.019999999552965164 | 0.9599 | 0.00309 | 4.49 | +0.49 |
| 0.05000000074505806 | 0.9514 | 0.00101 | 4.74 | +0.71 |
| 0.10000000149011612 | 0.9421 | 0.00050 | 4.86 | +0.86 |
| 0.20000000298023224 | 0.9273 | 0.00023 | 4.96 | +1.02 |
| 0.3499999940395355 | 0.9069 | 0.00017 | 4.91 | +1.13 |
| 0.5 | 0.8850 | 0.00012 | 4.87 | +1.23 |
| 0.699999988079071 | 0.8425 | 0.00007 | 4.80 | +1.39 |
| 0.8999999761581421 | 0.7347 | 0.00002 | 4.71 | +1.73 |

### stanford

n(H) = 84700 identifier chars, n(F) = 339298 ordinary chars (from sweep).

max d' = 3.89 at threshold 0.20000000298023224; d' at default 0.35 = 3.86 (nearest threshold 0.3499999940395355).

| threshold | H (chars) | F | d' | c |
|---|---|---|---|---|
| 0.009999999776482582 | 0.9321 | 0.00948 | 3.84 | +0.43 |
| 0.019999999552965164 | 0.9196 | 0.00728 | 3.85 | +0.52 |
| 0.05000000074505806 | 0.9021 | 0.00512 | 3.86 | +0.64 |
| 0.10000000149011612 | 0.8888 | 0.00391 | 3.88 | +0.72 |
| 0.20000000298023224 | 0.8740 | 0.00304 | 3.89 | +0.80 |
| 0.3499999940395355 | 0.8582 | 0.00264 | 3.86 | +0.86 |
| 0.5 | 0.8441 | 0.00240 | 3.83 | +0.90 |
| 0.699999988079071 | 0.8218 | 0.00200 | 3.80 | +0.98 |
| 0.8999999761581421 | 0.7851 | 0.00150 | 3.76 | +1.09 |

