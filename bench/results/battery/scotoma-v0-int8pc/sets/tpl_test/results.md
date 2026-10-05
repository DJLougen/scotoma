# test_tpl.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| scotoma-v0-int8pc | 99.3 | 97.5 | 199/3000 (6.6%) | 3.0% | 91.9 | 20.3 |
| rules+scotoma-v0-int8pc | 99.7 | 99.0 | 89/3000 (3.0%) | 3.1% | 91.8 | 20.8 |

## By domain (recall %)

| | n | scotoma-v0-int8pc | rules+scotoma-v0-int8pc |
|---|---|---|---|
| clinical | 7154 | 98.9 | 99.6 |
| hr | 8682 | 99.7 | 99.7 |
| legal | 9599 | 99.1 | 99.7 |
| tax | 7647 | 99.6 | 99.6 |

## By input mode (recall %)

| | n | scotoma-v0-int8pc | rules+scotoma-v0-int8pc |
|---|---|---|---|
| chat | 3579 | 97.0 | 97.5 |
| dictated | 6449 | 99.5 | 99.9 |
| ocr | 3095 | 99.8 | 100.0 |
| written | 19959 | 99.6 | 99.9 |

## By difficulty tag (recall %)

| | n | scotoma-v0-int8pc | rules+scotoma-v0-int8pc |
|---|---|---|---|
| chat | 3579 | 97.0 | 97.5 |
| common_word_name | 1718 | 96.9 | 97.0 |
| cue | 6175 | 98.7 | 99.7 |
| fmt:dash | 209 | 100.0 | 100.0 |
| fmt:dashed | 670 | 100.0 | 100.0 |
| fmt:day_first | 620 | 100.0 | 100.0 |
| fmt:dot | 205 | 100.0 | 100.0 |
| fmt:initial | 1525 | 98.4 | 98.4 |
| fmt:intl | 188 | 100.0 | 100.0 |
| fmt:iso | 676 | 100.0 | 100.0 |
| fmt:last_first_caps | 263 | 99.2 | 100.0 |
| fmt:month_year | 633 | 100.0 | 100.0 |
| fmt:named | 635 | 100.0 | 100.0 |
| fmt:named_abbr | 674 | 100.0 | 100.0 |
| fmt:numeric_short | 693 | 100.0 | 100.0 |
| fmt:numeric_us | 649 | 100.0 | 100.0 |
| fmt:paren | 198 | 100.0 | 100.0 |
| fmt:partial | 626 | 100.0 | 100.0 |
| fmt:plain | 195 | 100.0 | 100.0 |
| fmt:space | 197 | 100.0 | 100.0 |
| no_cue | 26907 | 99.5 | 99.7 |
| ocr | 824 | 100.0 | 100.0 |
| relative | 6470 | 99.2 | 99.2 |
| repeat | 6626 | 99.5 | 99.5 |
| single_name | 7656 | 99.3 | 99.3 |
| spoken | 2446 | 100.0 | 100.0 |

## By category (recall %)

| | n | scotoma-v0-int8pc | rules+scotoma-v0-int8pc |
|---|---|---|---|
| ACCOUNT | 1828 | 100.0 | 100.0 |
| ADDRESS | 1014 | 100.0 | 100.0 |
| AGE | 414 | 87.2 | 100.0 |
| DATE | 7292 | 100.0 | 100.0 |
| DEVICE | 258 | 100.0 | 100.0 |
| EMAIL | 1647 | 100.0 | 100.0 |
| ID | 1622 | 96.2 | 100.0 |
| IP | 271 | 100.0 | 100.0 |
| LICENSE | 401 | 100.0 | 100.0 |
| LOCATION | 938 | 98.0 | 98.0 |
| MRN | 525 | 100.0 | 100.0 |
| NAME | 12233 | 99.3 | 99.4 |
| ORG | 2498 | 99.5 | 99.5 |
| PHONE | 1491 | 100.0 | 100.0 |
| SSN | 379 | 100.0 | 100.0 |
| URL | 271 | 100.0 | 100.0 |
