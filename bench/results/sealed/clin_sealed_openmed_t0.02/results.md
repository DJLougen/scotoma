# clin_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| openmed-t0.02 | 98.1 | 94.8 | 110/874 (12.6%) | 0.3% | 97.8 | 19.4 |
| rules+openmed-t0.02 | 99.7 | 97.3 | 20/874 (2.3%) | 0.5% | 97.8 | 19.1 |

## By domain (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| clinical | 7168 | 98.1 | 99.7 |

## By input mode (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| chat | 944 | 98.5 | 100.0 |
| dictated | 798 | 97.9 | 99.9 |
| email | 910 | 98.1 | 99.9 |
| form | 1029 | 98.2 | 99.6 |
| letter | 821 | 97.6 | 99.6 |
| narrative | 914 | 98.2 | 99.7 |
| notes | 805 | 97.6 | 99.0 |
| ocr | 947 | 98.4 | 99.8 |

## By difficulty tag (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| fmt:dash | 140 | 100.0 | 100.0 |
| fmt:dot | 115 | 100.0 | 100.0 |
| fmt:initial | 88 | 100.0 | 100.0 |
| fmt:iso | 110 | 100.0 | 100.0 |
| fmt:last_first_caps | 181 | 94.5 | 95.0 |
| fmt:named | 111 | 100.0 | 100.0 |
| fmt:named_abbr | 85 | 100.0 | 100.0 |
| fmt:numeric_short | 85 | 100.0 | 100.0 |
| fmt:numeric_us | 98 | 100.0 | 100.0 |
| fmt:paren | 150 | 100.0 | 100.0 |
| fmt:partial | 61 | 100.0 | 100.0 |
| m:cue | 1633 | 97.4 | 99.9 |
| m:digit_spaced | 76 | 31.6 | 100.0 |
| m:lower | 14 | 100.0 | 100.0 |
| m:no_cue | 5535 | 98.3 | 99.6 |
| m:repeat | 1464 | 98.6 | 99.6 |
| m:single_name | 1234 | 99.4 | 99.4 |
| planted | 7168 | 98.1 | 99.7 |
| repeat | 1222 | 97.9 | 99.8 |
| single_name | 1234 | 99.4 | 99.4 |
| spoken | 272 | 58.8 | 100.0 |

## By category (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| ACCOUNT | 415 | 89.9 | 100.0 |
| ADDRESS | 204 | 100.0 | 100.0 |
| AGE | 173 | 97.7 | 98.3 |
| DATE | 612 | 100.0 | 100.0 |
| DEVICE | 198 | 96.0 | 100.0 |
| EMAIL | 213 | 100.0 | 100.0 |
| FAX | 220 | 100.0 | 100.0 |
| IP | 209 | 100.0 | 100.0 |
| LICENSE | 187 | 93.0 | 100.0 |
| LOCATION | 201 | 100.0 | 100.0 |
| MRN | 198 | 91.9 | 100.0 |
| NAME | 2841 | 99.4 | 99.4 |
| PHONE | 205 | 100.0 | 100.0 |
| PLAN | 224 | 90.2 | 100.0 |
| SSN | 205 | 94.6 | 100.0 |
| URL | 226 | 100.0 | 100.0 |
| VEHICLE | 420 | 99.5 | 99.5 |
| ZIP | 217 | 99.5 | 99.5 |
