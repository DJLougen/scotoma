# clin_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| gliner-knowledgator-base | 83.8 | 77.3 | 612/844 (72.5%) | 1.3% | 94.0 | 0.0 |
| rules+gliner-knowledgator-base | 93.6 | 90.5 | 331/844 (39.2%) | 1.5% | 94.3 | 0.2 |

## By domain (recall %)

| | n | gliner-knowledgator-base | rules+gliner-knowledgator-base |
|---|---|---|---|
| clinical | 7117 | 83.8 | 93.6 |

## By input mode (recall %)

| | n | gliner-knowledgator-base | rules+gliner-knowledgator-base |
|---|---|---|---|
| chat | 869 | 81.4 | 92.8 |
| dictated | 885 | 82.7 | 92.8 |
| email | 937 | 83.6 | 92.4 |
| form | 890 | 89.4 | 96.2 |
| letter | 824 | 82.2 | 92.0 |
| narrative | 930 | 85.4 | 95.7 |
| notes | 880 | 80.8 | 92.5 |
| ocr | 902 | 84.7 | 94.0 |

## By difficulty tag (recall %)

| | n | gliner-knowledgator-base | rules+gliner-knowledgator-base |
|---|---|---|---|
| fmt:dash | 127 | 96.9 | 100.0 |
| fmt:dot | 100 | 51.0 | 100.0 |
| fmt:initial | 73 | 93.2 | 100.0 |
| fmt:iso | 97 | 96.9 | 100.0 |
| fmt:last_first_caps | 194 | 88.7 | 88.7 |
| fmt:named | 99 | 98.0 | 100.0 |
| fmt:named_abbr | 81 | 98.8 | 100.0 |
| fmt:numeric_short | 94 | 90.4 | 100.0 |
| fmt:numeric_us | 104 | 100.0 | 100.0 |
| fmt:paren | 137 | 100.0 | 100.0 |
| fmt:partial | 47 | 100.0 | 100.0 |
| m:cue | 1651 | 89.6 | 98.6 |
| m:digit_spaced | 59 | 54.2 | 100.0 |
| m:lower | 17 | 82.4 | 94.1 |
| m:no_cue | 5466 | 82.1 | 92.0 |
| m:repeat | 1511 | 70.9 | 94.9 |
| m:single_name | 1237 | 68.4 | 95.1 |
| planted | 7117 | 83.8 | 93.6 |
| repeat | 1358 | 80.9 | 92.9 |
| single_name | 1237 | 68.4 | 95.1 |
| spoken | 278 | 60.8 | 98.9 |

## By category (recall %)

| | n | gliner-knowledgator-base | rules+gliner-knowledgator-base |
|---|---|---|---|
| ACCOUNT | 406 | 50.2 | 73.4 |
| ADDRESS | 220 | 55.9 | 65.0 |
| AGE | 168 | 98.8 | 98.8 |
| DATE | 569 | 97.2 | 100.0 |
| DEVICE | 218 | 75.2 | 82.6 |
| EMAIL | 201 | 87.1 | 98.5 |
| FAX | 180 | 76.7 | 100.0 |
| IP | 213 | 90.6 | 100.0 |
| LICENSE | 230 | 75.7 | 85.2 |
| LOCATION | 234 | 95.7 | 95.7 |
| MRN | 223 | 92.8 | 95.1 |
| NAME | 2796 | 84.8 | 96.9 |
| PHONE | 216 | 94.4 | 100.0 |
| PLAN | 198 | 42.4 | 70.2 |
| SSN | 224 | 86.6 | 100.0 |
| URL | 210 | 99.5 | 100.0 |
| VEHICLE | 410 | 96.3 | 96.6 |
| ZIP | 201 | 92.0 | 92.0 |
