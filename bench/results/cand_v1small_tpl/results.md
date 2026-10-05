# test_tpl.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules+v1small | 99.7 | 99.1 | 79/3000 (2.6%) | 2.5% | 91.3 | 18.2 |

## By domain (recall %)

| | n | rules+v1small |
|---|---|---|
| clinical | 7154 | 99.6 |
| hr | 8682 | 99.7 |
| legal | 9599 | 99.7 |
| tax | 7647 | 99.8 |

## By input mode (recall %)

| | n | rules+v1small |
|---|---|---|
| chat | 3579 | 97.6 |
| dictated | 6449 | 100.0 |
| ocr | 3095 | 100.0 |
| written | 19959 | 100.0 |

## By difficulty tag (recall %)

| | n | rules+v1small |
|---|---|---|
| chat | 3579 | 97.6 |
| common_word_name | 1718 | 97.7 |
| cue | 6175 | 99.7 |
| fmt:dash | 209 | 100.0 |
| fmt:dashed | 670 | 100.0 |
| fmt:day_first | 620 | 100.0 |
| fmt:dot | 205 | 100.0 |
| fmt:initial | 1525 | 98.9 |
| fmt:intl | 188 | 100.0 |
| fmt:iso | 676 | 100.0 |
| fmt:last_first_caps | 263 | 100.0 |
| fmt:month_year | 633 | 100.0 |
| fmt:named | 635 | 100.0 |
| fmt:named_abbr | 674 | 100.0 |
| fmt:numeric_short | 693 | 100.0 |
| fmt:numeric_us | 649 | 100.0 |
| fmt:paren | 198 | 100.0 |
| fmt:partial | 626 | 100.0 |
| fmt:plain | 195 | 100.0 |
| fmt:space | 197 | 100.0 |
| no_cue | 26907 | 99.7 |
| ocr | 824 | 100.0 |
| relative | 6470 | 99.4 |
| repeat | 6626 | 99.7 |
| single_name | 7656 | 99.5 |
| spoken | 2446 | 100.0 |

## By category (recall %)

| | n | rules+v1small |
|---|---|---|
| ACCOUNT | 1828 | 100.0 |
| ADDRESS | 1014 | 99.9 |
| AGE | 414 | 100.0 |
| DATE | 7292 | 100.0 |
| DEVICE | 258 | 100.0 |
| EMAIL | 1647 | 100.0 |
| ID | 1622 | 100.0 |
| IP | 271 | 100.0 |
| LICENSE | 401 | 100.0 |
| LOCATION | 938 | 97.5 |
| MRN | 525 | 100.0 |
| NAME | 12233 | 99.6 |
| ORG | 2498 | 99.2 |
| PHONE | 1491 | 100.0 |
| SSN | 379 | 100.0 |
| URL | 271 | 100.0 |
