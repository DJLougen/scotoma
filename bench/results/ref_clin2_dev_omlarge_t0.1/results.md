# clin2_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules+openmed-large-t0.1 | 99.9 | 99.8 | 5/870 (0.6%) | 0.4% | 98.2 | 244.8 |

## By domain (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| clinical | 7360 | 99.9 |

## By input mode (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| chat | 809 | 99.8 |
| dictated | 861 | 100.0 |
| email | 902 | 100.0 |
| form | 953 | 99.9 |
| letter | 924 | 100.0 |
| narrative | 939 | 100.0 |
| notes | 1095 | 99.6 |
| ocr | 877 | 100.0 |

## By difficulty tag (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| fmt:dash | 138 | 100.0 |
| fmt:dot | 148 | 100.0 |
| fmt:initial | 82 | 100.0 |
| fmt:iso | 99 | 100.0 |
| fmt:last_first_caps | 195 | 100.0 |
| fmt:named | 104 | 100.0 |
| fmt:named_abbr | 101 | 100.0 |
| fmt:numeric_short | 110 | 100.0 |
| fmt:numeric_us | 113 | 100.0 |
| fmt:paren | 134 | 100.0 |
| fmt:partial | 62 | 100.0 |
| m:cue | 1666 | 100.0 |
| m:digit_spaced | 72 | 100.0 |
| m:lower | 20 | 100.0 |
| m:no_cue | 5694 | 99.9 |
| m:repeat | 1463 | 99.9 |
| m:single_name | 1197 | 99.6 |
| planted | 7360 | 99.9 |
| repeat | 1334 | 99.7 |
| single_name | 1197 | 99.6 |
| spoken | 315 | 100.0 |

## By category (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| ACCOUNT | 422 | 100.0 |
| ADDRESS | 222 | 100.0 |
| AGE | 182 | 99.5 |
| DATE | 660 | 100.0 |
| DEVICE | 241 | 100.0 |
| EMAIL | 213 | 100.0 |
| FAX | 228 | 100.0 |
| IP | 221 | 100.0 |
| LICENSE | 217 | 100.0 |
| LOCATION | 219 | 100.0 |
| MRN | 220 | 100.0 |
| NAME | 2789 | 99.8 |
| PHONE | 225 | 100.0 |
| PLAN | 224 | 100.0 |
| SSN | 224 | 100.0 |
| URL | 221 | 100.0 |
| VEHICLE | 422 | 99.8 |
| ZIP | 210 | 100.0 |
