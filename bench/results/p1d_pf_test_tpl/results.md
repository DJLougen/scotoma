# test_tpl.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| privacy-filter | 74.2 | 72.8 | 2605/3000 (86.8%) | 1.6% | 96.8 | 0.0 |
| rules+privacy-filter | 85.2 | 84.4 | 2379/3000 (79.3%) | 1.7% | 97.2 | 0.2 |

## By domain (recall %)

| | n | privacy-filter | rules+privacy-filter |
|---|---|---|---|
| clinical | 7154 | 60.8 | 83.4 |
| hr | 8682 | 82.6 | 85.7 |
| legal | 9599 | 71.2 | 84.0 |
| tax | 7647 | 80.8 | 87.8 |

## By input mode (recall %)

| | n | privacy-filter | rules+privacy-filter |
|---|---|---|---|
| chat | 3579 | 64.3 | 70.0 |
| dictated | 6449 | 67.5 | 86.4 |
| ocr | 3095 | 78.6 | 86.2 |
| written | 19959 | 77.4 | 87.3 |

## By difficulty tag (recall %)

| | n | privacy-filter | rules+privacy-filter |
|---|---|---|---|
| chat | 3579 | 64.3 | 70.0 |
| common_word_name | 1718 | 73.3 | 77.8 |
| cue | 6175 | 86.2 | 96.1 |
| fmt:dash | 209 | 72.7 | 99.0 |
| fmt:dashed | 670 | 93.9 | 98.1 |
| fmt:day_first | 620 | 89.4 | 97.7 |
| fmt:dot | 205 | 66.8 | 99.0 |
| fmt:initial | 1525 | 85.4 | 86.4 |
| fmt:intl | 188 | 77.7 | 99.5 |
| fmt:iso | 676 | 94.2 | 99.6 |
| fmt:last_first_caps | 263 | 43.0 | 95.1 |
| fmt:month_year | 633 | 84.7 | 96.5 |
| fmt:named | 635 | 83.9 | 96.2 |
| fmt:named_abbr | 674 | 86.9 | 97.0 |
| fmt:numeric_short | 693 | 96.0 | 99.7 |
| fmt:numeric_us | 649 | 98.2 | 100.0 |
| fmt:paren | 198 | 67.7 | 99.0 |
| fmt:partial | 626 | 75.6 | 94.7 |
| fmt:plain | 195 | 68.7 | 88.7 |
| fmt:space | 197 | 65.5 | 98.5 |
| no_cue | 26907 | 71.4 | 82.7 |
| ocr | 824 | 81.1 | 84.3 |
| relative | 6470 | 86.3 | 90.9 |
| repeat | 6626 | 85.5 | 91.7 |
| single_name | 7656 | 82.1 | 89.2 |
| spoken | 2446 | 66.1 | 99.4 |

## By category (recall %)

| | n | privacy-filter | rules+privacy-filter |
|---|---|---|---|
| ACCOUNT | 1828 | 94.8 | 99.6 |
| ADDRESS | 1014 | 88.1 | 98.1 |
| AGE | 414 | 0.2 | 100.0 |
| DATE | 7292 | 84.1 | 98.2 |
| DEVICE | 258 | 79.8 | 100.0 |
| EMAIL | 1647 | 95.8 | 100.0 |
| ID | 1622 | 69.7 | 88.8 |
| IP | 271 | 55.7 | 97.4 |
| LICENSE | 401 | 47.4 | 47.4 |
| LOCATION | 938 | 4.3 | 4.3 |
| MRN | 525 | 78.1 | 98.3 |
| NAME | 12233 | 84.4 | 90.4 |
| ORG | 2498 | 10.9 | 10.9 |
| PHONE | 1491 | 69.7 | 97.9 |
| SSN | 379 | 98.7 | 100.0 |
| URL | 271 | 25.5 | 100.0 |
