# clin_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| scotoma-v0-int8pc | 99.7 | 97.9 | 18/844 (2.1%) | 0.1% | 99.4 | 20.2 |
| rules+scotoma-v0-int8pc | 99.8 | 98.0 | 16/844 (1.9%) | 0.3% | 99.4 | 20.4 |

## By domain (recall %)

| | n | scotoma-v0-int8pc | rules+scotoma-v0-int8pc |
|---|---|---|---|
| clinical | 7117 | 99.7 | 99.8 |

## By input mode (recall %)

| | n | scotoma-v0-int8pc | rules+scotoma-v0-int8pc |
|---|---|---|---|
| chat | 869 | 99.9 | 99.9 |
| dictated | 885 | 99.9 | 99.9 |
| email | 937 | 99.3 | 99.3 |
| form | 890 | 99.9 | 99.9 |
| letter | 824 | 100.0 | 100.0 |
| narrative | 930 | 99.9 | 99.9 |
| notes | 880 | 99.4 | 99.5 |
| ocr | 902 | 99.8 | 99.9 |

## By difficulty tag (recall %)

| | n | scotoma-v0-int8pc | rules+scotoma-v0-int8pc |
|---|---|---|---|
| fmt:dash | 127 | 100.0 | 100.0 |
| fmt:dot | 100 | 100.0 | 100.0 |
| fmt:initial | 73 | 100.0 | 100.0 |
| fmt:iso | 97 | 100.0 | 100.0 |
| fmt:last_first_caps | 194 | 96.9 | 96.9 |
| fmt:named | 99 | 100.0 | 100.0 |
| fmt:named_abbr | 81 | 100.0 | 100.0 |
| fmt:numeric_short | 94 | 100.0 | 100.0 |
| fmt:numeric_us | 104 | 100.0 | 100.0 |
| fmt:paren | 137 | 100.0 | 100.0 |
| fmt:partial | 47 | 100.0 | 100.0 |
| m:cue | 1651 | 99.9 | 99.9 |
| m:digit_spaced | 59 | 100.0 | 100.0 |
| m:lower | 17 | 94.1 | 94.1 |
| m:no_cue | 5466 | 99.7 | 99.7 |
| m:repeat | 1511 | 99.8 | 99.9 |
| m:single_name | 1237 | 99.8 | 99.9 |
| planted | 7117 | 99.7 | 99.8 |
| repeat | 1358 | 99.9 | 99.9 |
| single_name | 1237 | 99.8 | 99.9 |
| spoken | 278 | 99.6 | 99.6 |

## By category (recall %)

| | n | scotoma-v0-int8pc | rules+scotoma-v0-int8pc |
|---|---|---|---|
| ACCOUNT | 406 | 100.0 | 100.0 |
| ADDRESS | 220 | 100.0 | 100.0 |
| AGE | 168 | 98.8 | 99.4 |
| DATE | 569 | 100.0 | 100.0 |
| DEVICE | 218 | 100.0 | 100.0 |
| EMAIL | 201 | 99.5 | 99.5 |
| FAX | 180 | 100.0 | 100.0 |
| IP | 213 | 100.0 | 100.0 |
| LICENSE | 230 | 100.0 | 100.0 |
| LOCATION | 234 | 100.0 | 100.0 |
| MRN | 223 | 100.0 | 100.0 |
| NAME | 2796 | 99.7 | 99.7 |
| PHONE | 216 | 100.0 | 100.0 |
| PLAN | 198 | 100.0 | 100.0 |
| SSN | 224 | 100.0 | 100.0 |
| URL | 210 | 100.0 | 100.0 |
| VEHICLE | 410 | 98.3 | 98.3 |
| ZIP | 201 | 100.0 | 100.0 |
