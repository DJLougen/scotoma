# clin_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| v1base | 99.5 | 98.7 | 34/844 (4.0%) | 0.4% | 97.3 | 38.7 |
| rules+v1base | 99.7 | 99.5 | 18/844 (2.1%) | 0.6% | 97.2 | 38.6 |

## By domain (recall %)

| | n | v1base | rules+v1base |
|---|---|---|---|
| clinical | 7117 | 99.5 | 99.7 |

## By input mode (recall %)

| | n | v1base | rules+v1base |
|---|---|---|---|
| chat | 869 | 100.0 | 100.0 |
| dictated | 885 | 99.8 | 99.9 |
| email | 937 | 99.6 | 99.8 |
| form | 890 | 99.4 | 99.6 |
| letter | 824 | 99.6 | 100.0 |
| narrative | 930 | 99.9 | 100.0 |
| notes | 880 | 98.1 | 99.0 |
| ocr | 902 | 99.2 | 99.6 |

## By difficulty tag (recall %)

| | n | v1base | rules+v1base |
|---|---|---|---|
| fmt:dash | 127 | 100.0 | 100.0 |
| fmt:dot | 100 | 100.0 | 100.0 |
| fmt:initial | 73 | 100.0 | 100.0 |
| fmt:iso | 97 | 100.0 | 100.0 |
| fmt:last_first_caps | 194 | 94.8 | 100.0 |
| fmt:named | 99 | 100.0 | 100.0 |
| fmt:named_abbr | 81 | 100.0 | 100.0 |
| fmt:numeric_short | 94 | 100.0 | 100.0 |
| fmt:numeric_us | 104 | 100.0 | 100.0 |
| fmt:paren | 137 | 100.0 | 100.0 |
| fmt:partial | 47 | 100.0 | 100.0 |
| m:cue | 1651 | 99.8 | 99.9 |
| m:digit_spaced | 59 | 100.0 | 100.0 |
| m:lower | 17 | 64.7 | 88.2 |
| m:no_cue | 5466 | 99.4 | 99.7 |
| m:repeat | 1511 | 99.8 | 99.9 |
| m:single_name | 1237 | 98.9 | 99.2 |
| planted | 7117 | 99.5 | 99.7 |
| repeat | 1358 | 99.7 | 99.9 |
| single_name | 1237 | 98.9 | 99.2 |
| spoken | 278 | 97.5 | 99.3 |

## By category (recall %)

| | n | v1base | rules+v1base |
|---|---|---|---|
| ACCOUNT | 406 | 100.0 | 100.0 |
| ADDRESS | 220 | 99.5 | 99.5 |
| AGE | 168 | 98.8 | 98.8 |
| DATE | 569 | 99.8 | 100.0 |
| DEVICE | 218 | 100.0 | 100.0 |
| EMAIL | 201 | 97.0 | 99.0 |
| FAX | 180 | 100.0 | 100.0 |
| IP | 213 | 100.0 | 100.0 |
| LICENSE | 230 | 100.0 | 100.0 |
| LOCATION | 234 | 98.3 | 98.3 |
| MRN | 223 | 100.0 | 100.0 |
| NAME | 2796 | 99.1 | 99.6 |
| PHONE | 216 | 100.0 | 100.0 |
| PLAN | 198 | 100.0 | 100.0 |
| SSN | 224 | 100.0 | 100.0 |
| URL | 210 | 100.0 | 100.0 |
| VEHICLE | 410 | 100.0 | 100.0 |
| ZIP | 201 | 100.0 | 100.0 |
