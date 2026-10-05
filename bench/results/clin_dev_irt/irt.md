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

