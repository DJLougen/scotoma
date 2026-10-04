# test_tpl.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| ours_int8 | 96.7 | 93.0 | 821/3000 (27.4%) | 0.5% | 97.9 | 31.5 |
| ours_fp32 | 99.0 | 97.5 | 315/3000 (10.5%) | 1.4% | 95.8 | 49.1 |

## By domain (recall %)

| | n | ours_int8 | ours_fp32 |
|---|---|---|---|
| clinical | 7154 | 92.7 | 98.4 |
| hr | 8682 | 98.9 | 99.8 |
| legal | 9599 | 96.3 | 98.1 |
| tax | 7647 | 98.5 | 99.8 |

## By input mode (recall %)

| | n | ours_int8 | ours_fp32 |
|---|---|---|---|
| chat | 3579 | 90.2 | 97.8 |
| dictated | 6449 | 97.8 | 99.1 |
| ocr | 3095 | 98.0 | 99.3 |
| written | 19959 | 97.4 | 99.2 |

## By difficulty tag (recall %)

| | n | ours_int8 | ours_fp32 |
|---|---|---|---|
| chat | 3579 | 90.2 | 97.8 |
| common_word_name | 1718 | 92.2 | 98.2 |
| cue | 6175 | 94.9 | 97.1 |
| fmt:dash | 209 | 100.0 | 100.0 |
| fmt:dashed | 670 | 99.9 | 100.0 |
| fmt:day_first | 620 | 100.0 | 100.0 |
| fmt:dot | 205 | 100.0 | 100.0 |
| fmt:initial | 1525 | 96.7 | 99.5 |
| fmt:intl | 188 | 100.0 | 100.0 |
| fmt:iso | 676 | 100.0 | 100.0 |
| fmt:last_first_caps | 263 | 86.3 | 99.6 |
| fmt:month_year | 633 | 100.0 | 100.0 |
| fmt:named | 635 | 100.0 | 100.0 |
| fmt:named_abbr | 674 | 100.0 | 100.0 |
| fmt:numeric_short | 693 | 100.0 | 100.0 |
| fmt:numeric_us | 649 | 100.0 | 100.0 |
| fmt:paren | 198 | 100.0 | 100.0 |
| fmt:partial | 626 | 99.8 | 100.0 |
| fmt:plain | 195 | 100.0 | 100.0 |
| fmt:space | 197 | 100.0 | 100.0 |
| no_cue | 26907 | 97.1 | 99.5 |
| ocr | 824 | 98.9 | 99.3 |
| relative | 6470 | 97.8 | 99.7 |
| repeat | 6626 | 98.2 | 99.8 |
| single_name | 7656 | 97.8 | 99.6 |
| spoken | 2446 | 99.2 | 100.0 |

## By category (recall %)

| | n | ours_int8 | ours_fp32 |
|---|---|---|---|
| ACCOUNT | 1828 | 99.2 | 100.0 |
| ADDRESS | 1014 | 99.8 | 100.0 |
| AGE | 414 | 13.0 | 76.1 |
| DATE | 7292 | 100.0 | 100.0 |
| DEVICE | 258 | 98.8 | 99.6 |
| EMAIL | 1647 | 99.0 | 100.0 |
| ID | 1622 | 85.0 | 89.3 |
| IP | 271 | 99.3 | 100.0 |
| LICENSE | 401 | 99.3 | 100.0 |
| LOCATION | 938 | 94.8 | 98.6 |
| MRN | 525 | 99.4 | 100.0 |
| NAME | 12233 | 97.9 | 99.7 |
| ORG | 2498 | 95.0 | 100.0 |
| PHONE | 1491 | 100.0 | 100.0 |
| SSN | 379 | 100.0 | 100.0 |
| URL | 271 | 100.0 | 100.0 |
