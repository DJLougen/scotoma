# clin_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| gliner-knowledgator-large | 88.5 | 85.3 | 449/844 (53.2%) | 0.1% | 100.0 | 0.0 |
| rules+gliner-knowledgator-large | 96.3 | 93.5 | 171/844 (20.3%) | 0.2% | 100.0 | 0.2 |

## By domain (recall %)

| | n | gliner-knowledgator-large | rules+gliner-knowledgator-large |
|---|---|---|---|
| clinical | 7117 | 88.5 | 96.3 |

## By input mode (recall %)

| | n | gliner-knowledgator-large | rules+gliner-knowledgator-large |
|---|---|---|---|
| chat | 869 | 88.5 | 96.0 |
| dictated | 885 | 88.7 | 96.3 |
| email | 937 | 90.3 | 96.9 |
| form | 890 | 88.1 | 95.7 |
| letter | 824 | 91.7 | 97.3 |
| narrative | 930 | 88.7 | 96.5 |
| notes | 880 | 86.5 | 95.6 |
| ocr | 902 | 85.9 | 96.2 |

## By difficulty tag (recall %)

| | n | gliner-knowledgator-large | rules+gliner-knowledgator-large |
|---|---|---|---|
| fmt:dash | 127 | 100.0 | 100.0 |
| fmt:dot | 100 | 100.0 | 100.0 |
| fmt:initial | 73 | 46.6 | 97.3 |
| fmt:iso | 97 | 93.8 | 100.0 |
| fmt:last_first_caps | 194 | 68.0 | 70.1 |
| fmt:named | 99 | 94.9 | 100.0 |
| fmt:named_abbr | 81 | 92.6 | 100.0 |
| fmt:numeric_short | 94 | 95.7 | 100.0 |
| fmt:numeric_us | 104 | 90.4 | 100.0 |
| fmt:paren | 137 | 99.3 | 100.0 |
| fmt:partial | 47 | 93.6 | 100.0 |
| m:cue | 1651 | 92.5 | 99.3 |
| m:digit_spaced | 59 | 64.4 | 100.0 |
| m:lower | 17 | 17.6 | 82.4 |
| m:no_cue | 5466 | 87.3 | 95.4 |
| m:repeat | 1511 | 71.7 | 92.9 |
| m:single_name | 1237 | 65.1 | 90.2 |
| planted | 7117 | 88.5 | 96.3 |
| repeat | 1358 | 78.3 | 91.9 |
| single_name | 1237 | 65.1 | 90.2 |
| spoken | 278 | 55.0 | 98.9 |

## By category (recall %)

| | n | gliner-knowledgator-large | rules+gliner-knowledgator-large |
|---|---|---|---|
| ACCOUNT | 406 | 81.8 | 94.8 |
| ADDRESS | 220 | 97.3 | 97.7 |
| AGE | 168 | 97.6 | 97.6 |
| DATE | 569 | 93.0 | 100.0 |
| DEVICE | 218 | 85.8 | 97.7 |
| EMAIL | 201 | 92.0 | 98.5 |
| FAX | 180 | 99.4 | 100.0 |
| IP | 213 | 98.1 | 100.0 |
| LICENSE | 230 | 97.0 | 98.7 |
| LOCATION | 234 | 95.3 | 95.3 |
| MRN | 223 | 98.7 | 100.0 |
| NAME | 2796 | 80.7 | 93.5 |
| PHONE | 216 | 98.1 | 100.0 |
| PLAN | 198 | 81.3 | 96.0 |
| SSN | 224 | 96.0 | 100.0 |
| URL | 210 | 96.7 | 100.0 |
| VEHICLE | 410 | 95.6 | 95.6 |
| ZIP | 201 | 98.5 | 98.5 |
