# clin_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| privacy-filter | 87.1 | 85.5 | 494/844 (58.5%) | 0.3% | 99.5 | 0.0 |
| rules+privacy-filter | 95.1 | 93.5 | 244/844 (28.9%) | 0.5% | 99.6 | 0.2 |
| presidio | 82.3 | 67.9 | 614/844 (72.7%) | 1.7% | 92.1 | 0.0 |
| rules+presidio | 90.9 | 81.2 | 420/844 (49.8%) | 1.8% | 92.6 | 0.2 |

## By domain (recall %)

| | n | privacy-filter | rules+privacy-filter | presidio | rules+presidio |
|---|---|---|---|---|---|
| clinical | 7117 | 87.1 | 95.1 | 82.3 | 90.9 |

## By input mode (recall %)

| | n | privacy-filter | rules+privacy-filter | presidio | rules+presidio |
|---|---|---|---|---|---|
| chat | 869 | 83.5 | 93.4 | 83.5 | 89.9 |
| dictated | 885 | 87.3 | 95.4 | 83.5 | 92.2 |
| email | 937 | 88.6 | 95.4 | 80.9 | 88.5 |
| form | 890 | 88.8 | 96.4 | 79.6 | 92.4 |
| letter | 824 | 90.8 | 96.6 | 83.3 | 91.6 |
| narrative | 930 | 88.4 | 95.5 | 83.8 | 92.2 |
| notes | 880 | 83.2 | 93.0 | 82.4 | 89.4 |
| ocr | 902 | 86.4 | 94.8 | 81.5 | 91.4 |

## By difficulty tag (recall %)

| | n | privacy-filter | rules+privacy-filter | presidio | rules+presidio |
|---|---|---|---|---|---|
| fmt:dash | 127 | 87.4 | 100.0 | 94.5 | 100.0 |
| fmt:dot | 100 | 97.0 | 100.0 | 98.0 | 100.0 |
| fmt:initial | 73 | 83.6 | 97.3 | 84.9 | 98.6 |
| fmt:iso | 97 | 96.9 | 100.0 | 100.0 | 100.0 |
| fmt:last_first_caps | 194 | 64.9 | 67.5 | 86.6 | 88.1 |
| fmt:named | 99 | 100.0 | 100.0 | 99.0 | 100.0 |
| fmt:named_abbr | 81 | 100.0 | 100.0 | 92.6 | 100.0 |
| fmt:numeric_short | 94 | 95.7 | 100.0 | 100.0 | 100.0 |
| fmt:numeric_us | 104 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:paren | 137 | 87.6 | 100.0 | 93.4 | 100.0 |
| fmt:partial | 47 | 87.2 | 100.0 | 100.0 | 100.0 |
| m:cue | 1651 | 90.6 | 99.4 | 76.1 | 95.2 |
| m:digit_spaced | 59 | 78.0 | 100.0 | 33.9 | 100.0 |
| m:lower | 17 | 64.7 | 76.5 | 58.8 | 82.4 |
| m:no_cue | 5466 | 86.1 | 93.7 | 84.1 | 89.6 |
| m:repeat | 1511 | 81.3 | 95.3 | 83.1 | 93.1 |
| m:single_name | 1237 | 78.5 | 93.4 | 83.5 | 94.2 |
| planted | 7117 | 87.1 | 95.1 | 82.3 | 90.9 |
| repeat | 1358 | 85.3 | 94.6 | 78.6 | 89.0 |
| single_name | 1237 | 78.5 | 93.4 | 83.5 | 94.2 |
| spoken | 278 | 80.2 | 98.6 | 47.5 | 98.2 |

## By category (recall %)

| | n | privacy-filter | rules+privacy-filter | presidio | rules+presidio |
|---|---|---|---|---|---|
| ACCOUNT | 406 | 88.9 | 96.6 | 92.1 | 100.0 |
| ADDRESS | 220 | 97.7 | 98.6 | 34.1 | 56.8 |
| AGE | 168 | 1.2 | 89.3 | 66.1 | 90.5 |
| DATE | 569 | 96.3 | 100.0 | 98.8 | 100.0 |
| DEVICE | 218 | 88.1 | 92.2 | 88.1 | 100.0 |
| EMAIL | 201 | 97.0 | 98.0 | 95.0 | 97.5 |
| FAX | 180 | 88.3 | 100.0 | 95.6 | 100.0 |
| IP | 213 | 96.7 | 100.0 | 100.0 | 100.0 |
| LICENSE | 230 | 97.8 | 98.3 | 90.9 | 100.0 |
| LOCATION | 234 | 69.7 | 70.1 | 74.4 | 75.2 |
| MRN | 223 | 91.0 | 96.4 | 80.7 | 98.7 |
| NAME | 2796 | 87.1 | 94.4 | 90.6 | 96.1 |
| PHONE | 216 | 93.1 | 100.0 | 93.5 | 100.0 |
| PLAN | 198 | 94.9 | 97.5 | 59.6 | 79.3 |
| SSN | 224 | 96.0 | 100.0 | 88.8 | 100.0 |
| URL | 210 | 68.1 | 100.0 | 100.0 | 100.0 |
| VEHICLE | 410 | 94.9 | 94.9 | 8.3 | 40.5 |
| ZIP | 201 | 79.6 | 84.1 | 53.2 | 62.2 |
