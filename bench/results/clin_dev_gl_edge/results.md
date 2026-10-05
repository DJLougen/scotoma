# clin_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| gliner-edge | 96.3 | 90.5 | 207/844 (24.5%) | 1.7% | 91.1 | 0.0 |
| rules+gliner-edge | 98.5 | 96.1 | 94/844 (11.1%) | 1.9% | 90.8 | 0.2 |

## By domain (recall %)

| | n | gliner-edge | rules+gliner-edge |
|---|---|---|---|
| clinical | 7117 | 96.3 | 98.5 |

## By input mode (recall %)

| | n | gliner-edge | rules+gliner-edge |
|---|---|---|---|
| chat | 869 | 96.3 | 98.5 |
| dictated | 885 | 96.5 | 98.6 |
| email | 937 | 96.4 | 98.2 |
| form | 890 | 95.2 | 97.9 |
| letter | 824 | 97.5 | 99.0 |
| narrative | 930 | 97.2 | 98.6 |
| notes | 880 | 95.0 | 99.1 |
| ocr | 902 | 96.6 | 98.3 |

## By difficulty tag (recall %)

| | n | gliner-edge | rules+gliner-edge |
|---|---|---|---|
| fmt:dash | 127 | 100.0 | 100.0 |
| fmt:dot | 100 | 100.0 | 100.0 |
| fmt:initial | 73 | 91.8 | 100.0 |
| fmt:iso | 97 | 99.0 | 100.0 |
| fmt:last_first_caps | 194 | 78.9 | 80.4 |
| fmt:named | 99 | 99.0 | 100.0 |
| fmt:named_abbr | 81 | 95.1 | 100.0 |
| fmt:numeric_short | 94 | 98.9 | 100.0 |
| fmt:numeric_us | 104 | 96.2 | 100.0 |
| fmt:paren | 137 | 100.0 | 100.0 |
| fmt:partial | 47 | 100.0 | 100.0 |
| m:cue | 1651 | 98.2 | 99.8 |
| m:digit_spaced | 59 | 45.8 | 100.0 |
| m:lower | 17 | 70.6 | 94.1 |
| m:no_cue | 5466 | 95.7 | 98.1 |
| m:repeat | 1511 | 94.9 | 99.1 |
| m:single_name | 1237 | 91.7 | 96.5 |
| planted | 7117 | 96.3 | 98.5 |
| repeat | 1358 | 95.8 | 99.0 |
| single_name | 1237 | 91.7 | 96.5 |
| spoken | 278 | 73.7 | 99.6 |

## By category (recall %)

| | n | gliner-edge | rules+gliner-edge |
|---|---|---|---|
| ACCOUNT | 406 | 92.9 | 100.0 |
| ADDRESS | 220 | 97.7 | 98.6 |
| AGE | 168 | 99.4 | 100.0 |
| DATE | 569 | 97.9 | 100.0 |
| DEVICE | 218 | 96.8 | 100.0 |
| EMAIL | 201 | 97.5 | 99.5 |
| FAX | 180 | 100.0 | 100.0 |
| IP | 213 | 100.0 | 100.0 |
| LICENSE | 230 | 99.1 | 100.0 |
| LOCATION | 234 | 92.7 | 92.7 |
| MRN | 223 | 96.9 | 100.0 |
| NAME | 2796 | 94.5 | 97.0 |
| PHONE | 216 | 100.0 | 100.0 |
| PLAN | 198 | 92.9 | 99.5 |
| SSN | 224 | 95.5 | 100.0 |
| URL | 210 | 100.0 | 100.0 |
| VEHICLE | 410 | 100.0 | 100.0 |
| ZIP | 201 | 100.0 | 100.0 |
