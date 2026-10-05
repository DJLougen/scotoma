# clin_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules+openmed-large-t0.1 | 99.9 | 97.3 | 7/844 (0.8%) | 0.5% | 97.6 | 245.3 |

## By domain (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| clinical | 7117 | 99.9 |

## By input mode (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| chat | 869 | 99.9 |
| dictated | 885 | 99.9 |
| email | 937 | 99.9 |
| form | 890 | 99.9 |
| letter | 824 | 100.0 |
| narrative | 930 | 99.7 |
| notes | 880 | 99.9 |
| ocr | 902 | 100.0 |

## By difficulty tag (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| fmt:dash | 127 | 100.0 |
| fmt:dot | 100 | 100.0 |
| fmt:initial | 73 | 100.0 |
| fmt:iso | 97 | 100.0 |
| fmt:last_first_caps | 194 | 99.0 |
| fmt:named | 99 | 100.0 |
| fmt:named_abbr | 81 | 100.0 |
| fmt:numeric_short | 94 | 100.0 |
| fmt:numeric_us | 104 | 100.0 |
| fmt:paren | 137 | 100.0 |
| fmt:partial | 47 | 100.0 |
| m:cue | 1651 | 100.0 |
| m:digit_spaced | 59 | 100.0 |
| m:lower | 17 | 100.0 |
| m:no_cue | 5466 | 99.9 |
| m:repeat | 1511 | 99.9 |
| m:single_name | 1237 | 99.9 |
| planted | 7117 | 99.9 |
| repeat | 1358 | 100.0 |
| single_name | 1237 | 99.9 |
| spoken | 278 | 100.0 |

## By category (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| ACCOUNT | 406 | 100.0 |
| ADDRESS | 220 | 100.0 |
| AGE | 168 | 100.0 |
| DATE | 569 | 100.0 |
| DEVICE | 218 | 100.0 |
| EMAIL | 201 | 100.0 |
| FAX | 180 | 100.0 |
| IP | 213 | 100.0 |
| LICENSE | 230 | 100.0 |
| LOCATION | 234 | 100.0 |
| MRN | 223 | 100.0 |
| NAME | 2796 | 99.9 |
| PHONE | 216 | 100.0 |
| PLAN | 198 | 100.0 |
| SSN | 224 | 100.0 |
| URL | 210 | 100.0 |
| VEHICLE | 410 | 98.8 |
| ZIP | 201 | 100.0 |
