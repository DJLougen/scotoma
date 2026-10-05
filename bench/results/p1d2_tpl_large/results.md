# test_tpl.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules+openmed-large-fp32 | 99.6 | 93.5 | 142/3000 (4.7%) | 1.3% | 97.1 | 349.1 |

## By domain (recall %)

| | n | rules+openmed-large-fp32 |
|---|---|---|
| clinical | 7154 | 99.5 |
| hr | 8682 | 99.8 |
| legal | 9599 | 99.6 |
| tax | 7647 | 99.4 |

## By input mode (recall %)

| | n | rules+openmed-large-fp32 |
|---|---|---|
| chat | 3579 | 98.3 |
| dictated | 6449 | 99.6 |
| ocr | 3095 | 99.5 |
| written | 19959 | 99.8 |

## By difficulty tag (recall %)

| | n | rules+openmed-large-fp32 |
|---|---|---|
| chat | 3579 | 98.3 |
| common_word_name | 1718 | 99.4 |
| cue | 6175 | 99.9 |
| fmt:dash | 209 | 100.0 |
| fmt:dashed | 670 | 99.9 |
| fmt:day_first | 620 | 100.0 |
| fmt:dot | 205 | 100.0 |
| fmt:initial | 1525 | 99.9 |
| fmt:intl | 188 | 100.0 |
| fmt:iso | 676 | 100.0 |
| fmt:last_first_caps | 263 | 100.0 |
| fmt:month_year | 633 | 100.0 |
| fmt:named | 635 | 100.0 |
| fmt:named_abbr | 674 | 100.0 |
| fmt:numeric_short | 693 | 100.0 |
| fmt:numeric_us | 649 | 100.0 |
| fmt:paren | 198 | 100.0 |
| fmt:partial | 626 | 99.5 |
| fmt:plain | 195 | 100.0 |
| fmt:space | 197 | 100.0 |
| no_cue | 26907 | 99.5 |
| ocr | 824 | 98.7 |
| relative | 6470 | 99.9 |
| repeat | 6626 | 99.9 |
| single_name | 7656 | 99.8 |
| spoken | 2446 | 100.0 |

## By category (recall %)

| | n | rules+openmed-large-fp32 |
|---|---|---|
| ACCOUNT | 1828 | 100.0 |
| ADDRESS | 1014 | 100.0 |
| AGE | 414 | 100.0 |
| DATE | 7292 | 99.9 |
| DEVICE | 258 | 100.0 |
| EMAIL | 1647 | 100.0 |
| ID | 1622 | 99.7 |
| IP | 271 | 100.0 |
| LICENSE | 401 | 98.8 |
| LOCATION | 938 | 99.5 |
| MRN | 525 | 100.0 |
| NAME | 12233 | 99.9 |
| ORG | 2498 | 95.4 |
| PHONE | 1491 | 100.0 |
| SSN | 379 | 100.0 |
| URL | 271 | 100.0 |
