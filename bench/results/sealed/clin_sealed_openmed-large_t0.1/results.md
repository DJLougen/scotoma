# clin_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| openmed-large-t0.1 | 99.1 | 96.2 | 50/874 (5.7%) | 0.3% | 97.6 | 247.9 |
| rules+openmed-large-t0.1 | 99.9 | 97.3 | 4/874 (0.5%) | 0.5% | 97.6 | 242.2 |

## By domain (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| clinical | 7168 | 99.1 | 99.9 |

## By input mode (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| chat | 944 | 99.0 | 99.9 |
| dictated | 798 | 99.5 | 100.0 |
| email | 910 | 99.2 | 100.0 |
| form | 1029 | 99.0 | 100.0 |
| letter | 821 | 98.9 | 99.9 |
| narrative | 914 | 99.5 | 100.0 |
| notes | 805 | 99.1 | 99.6 |
| ocr | 947 | 98.9 | 100.0 |

## By difficulty tag (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| fmt:dash | 140 | 99.3 | 100.0 |
| fmt:dot | 115 | 100.0 | 100.0 |
| fmt:initial | 88 | 100.0 | 100.0 |
| fmt:iso | 110 | 100.0 | 100.0 |
| fmt:last_first_caps | 181 | 100.0 | 100.0 |
| fmt:named | 111 | 100.0 | 100.0 |
| fmt:named_abbr | 85 | 100.0 | 100.0 |
| fmt:numeric_short | 85 | 100.0 | 100.0 |
| fmt:numeric_us | 98 | 100.0 | 100.0 |
| fmt:paren | 150 | 100.0 | 100.0 |
| fmt:partial | 61 | 100.0 | 100.0 |
| m:cue | 1633 | 99.1 | 100.0 |
| m:digit_spaced | 76 | 55.3 | 100.0 |
| m:lower | 14 | 100.0 | 100.0 |
| m:no_cue | 5535 | 99.2 | 99.9 |
| m:repeat | 1464 | 99.3 | 99.9 |
| m:single_name | 1234 | 99.8 | 99.8 |
| planted | 7168 | 99.1 | 99.9 |
| repeat | 1222 | 98.6 | 99.8 |
| single_name | 1234 | 99.8 | 99.8 |
| spoken | 272 | 79.8 | 100.0 |

## By category (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| ACCOUNT | 415 | 92.3 | 100.0 |
| ADDRESS | 204 | 100.0 | 100.0 |
| AGE | 173 | 98.8 | 98.8 |
| DATE | 612 | 100.0 | 100.0 |
| DEVICE | 198 | 98.5 | 100.0 |
| EMAIL | 213 | 100.0 | 100.0 |
| FAX | 220 | 99.5 | 100.0 |
| IP | 209 | 100.0 | 100.0 |
| LICENSE | 187 | 100.0 | 100.0 |
| LOCATION | 201 | 100.0 | 100.0 |
| MRN | 198 | 96.5 | 100.0 |
| NAME | 2841 | 99.9 | 99.9 |
| PHONE | 205 | 100.0 | 100.0 |
| PLAN | 224 | 97.8 | 100.0 |
| SSN | 205 | 96.1 | 100.0 |
| URL | 226 | 100.0 | 100.0 |
| VEHICLE | 420 | 100.0 | 100.0 |
| ZIP | 217 | 100.0 | 100.0 |
