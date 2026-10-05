# test_tpl.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| piiranha | 58.2 | 44.3 | 2970/3000 (99.0%) | 0.7% | 97.1 | 76.1 |
| rules+piiranha | 87.6 | 79.6 | 2238/3000 (74.6%) | 0.7% | 98.0 | 76.4 |
| ai4privacy-en | 54.2 | 42.5 | 2935/3000 (97.8%) | 1.0% | 91.7 | 89.7 |
| rules+ai4privacy-en | 69.5 | 64.0 | 2758/3000 (91.9%) | 1.1% | 93.2 | 91.9 |
| ai4privacy-cat | 43.7 | 29.2 | 2989/3000 (99.6%) | 1.5% | 88.8 | 90.1 |
| rules+ai4privacy-cat | 65.1 | 60.3 | 2864/3000 (95.5%) | 1.5% | 91.8 | 87.2 |

## By domain (recall %)

| | n | piiranha | rules+piiranha | ai4privacy-en | rules+ai4privacy-en | ai4privacy-cat | rules+ai4privacy-cat |
|---|---|---|---|---|---|---|---|
| clinical | 7154 | 50.8 | 88.5 | 55.9 | 77.0 | 46.2 | 73.5 |
| hr | 8682 | 60.7 | 87.4 | 46.7 | 63.4 | 35.2 | 56.7 |
| legal | 9599 | 56.8 | 85.5 | 52.9 | 64.3 | 43.0 | 61.5 |
| tax | 7647 | 63.8 | 89.9 | 62.6 | 76.2 | 52.1 | 71.2 |

## By input mode (recall %)

| | n | piiranha | rules+piiranha | ai4privacy-en | rules+ai4privacy-en | ai4privacy-cat | rules+ai4privacy-cat |
|---|---|---|---|---|---|---|---|
| chat | 3579 | 61.4 | 76.6 | 42.0 | 46.0 | 36.0 | 42.5 |
| dictated | 6449 | 58.0 | 90.1 | 48.7 | 72.3 | 36.5 | 67.2 |
| ocr | 3095 | 57.8 | 83.5 | 55.6 | 69.6 | 44.5 | 63.8 |
| written | 19959 | 57.7 | 89.5 | 57.9 | 72.9 | 47.3 | 68.6 |

## By difficulty tag (recall %)

| | n | piiranha | rules+piiranha | ai4privacy-en | rules+ai4privacy-en | ai4privacy-cat | rules+ai4privacy-cat |
|---|---|---|---|---|---|---|---|
| chat | 3579 | 61.4 | 76.6 | 42.0 | 46.0 | 36.0 | 42.5 |
| common_word_name | 1718 | 65.2 | 70.9 | 20.1 | 36.4 | 13.2 | 29.8 |
| cue | 6175 | 75.9 | 97.7 | 50.3 | 80.2 | 42.8 | 76.9 |
| fmt:dash | 209 | 67.5 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:dashed | 670 | 8.1 | 85.1 | 99.6 | 99.6 | 93.9 | 97.6 |
| fmt:day_first | 620 | 5.2 | 84.7 | 95.8 | 96.6 | 83.1 | 88.2 |
| fmt:dot | 205 | 82.9 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:initial | 1525 | 80.2 | 83.9 | 1.8 | 5.8 | 1.4 | 6.9 |
| fmt:intl | 188 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:iso | 676 | 5.9 | 96.3 | 100.0 | 100.0 | 97.6 | 99.9 |
| fmt:last_first_caps | 263 | 57.8 | 99.2 | 0.8 | 82.5 | 0.0 | 81.7 |
| fmt:month_year | 633 | 0.3 | 82.5 | 63.5 | 90.2 | 57.7 | 85.0 |
| fmt:named | 635 | 7.7 | 86.9 | 82.5 | 94.2 | 58.1 | 93.1 |
| fmt:named_abbr | 674 | 7.3 | 85.9 | 82.0 | 92.7 | 55.2 | 89.9 |
| fmt:numeric_short | 693 | 2.3 | 97.8 | 99.3 | 99.9 | 68.0 | 97.5 |
| fmt:numeric_us | 649 | 6.8 | 96.6 | 100.0 | 100.0 | 95.5 | 99.2 |
| fmt:paren | 198 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:partial | 626 | 0.6 | 84.0 | 17.9 | 85.0 | 6.4 | 84.2 |
| fmt:plain | 195 | 26.2 | 58.5 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:space | 197 | 43.1 | 99.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| no_cue | 26907 | 54.1 | 85.4 | 55.1 | 67.1 | 43.9 | 62.4 |
| ocr | 824 | 51.7 | 68.0 | 61.4 | 70.3 | 49.0 | 61.4 |
| relative | 6470 | 87.9 | 91.4 | 12.4 | 39.8 | 7.8 | 38.1 |
| repeat | 6626 | 89.1 | 93.2 | 16.3 | 37.6 | 7.6 | 32.7 |
| single_name | 7656 | 87.8 | 91.2 | 21.0 | 45.0 | 9.7 | 37.1 |
| spoken | 2446 | 31.3 | 96.0 | 60.2 | 99.7 | 47.6 | 99.9 |

## By category (recall %)

| | n | piiranha | rules+piiranha | ai4privacy-en | rules+ai4privacy-en | ai4privacy-cat | rules+ai4privacy-cat |
|---|---|---|---|---|---|---|---|
| ACCOUNT | 1828 | 40.2 | 95.4 | 99.8 | 100.0 | 99.5 | 100.0 |
| ADDRESS | 1014 | 100.0 | 100.0 | 89.4 | 99.1 | 88.6 | 98.4 |
| AGE | 414 | 0.0 | 100.0 | 98.6 | 100.0 | 77.5 | 100.0 |
| DATE | 7292 | 4.9 | 91.1 | 77.3 | 96.3 | 62.0 | 94.3 |
| DEVICE | 258 | 12.0 | 100.0 | 90.7 | 100.0 | 93.4 | 100.0 |
| EMAIL | 1647 | 93.1 | 100.0 | 33.8 | 100.0 | 10.0 | 100.0 |
| ID | 1622 | 43.0 | 66.3 | 99.3 | 99.5 | 96.1 | 99.7 |
| IP | 271 | 97.4 | 99.3 | 100.0 | 100.0 | 100.0 | 100.0 |
| LICENSE | 401 | 1.5 | 1.5 | 99.3 | 99.3 | 98.5 | 98.5 |
| LOCATION | 938 | 95.0 | 95.0 | 51.6 | 51.6 | 23.3 | 23.3 |
| MRN | 525 | 48.6 | 81.5 | 91.8 | 100.0 | 96.2 | 100.0 |
| NAME | 12233 | 88.1 | 91.9 | 18.6 | 38.5 | 7.9 | 31.7 |
| ORG | 2498 | 52.5 | 52.5 | 27.4 | 27.4 | 18.6 | 18.6 |
| PHONE | 1491 | 66.3 | 94.3 | 100.0 | 100.0 | 100.0 | 100.0 |
| SSN | 379 | 98.4 | 98.4 | 100.0 | 100.0 | 99.7 | 99.7 |
| URL | 271 | 0.4 | 100.0 | 100.0 | 100.0 | 91.5 | 100.0 |
