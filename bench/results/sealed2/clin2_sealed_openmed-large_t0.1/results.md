# clin2_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| openmed-large-t0.1 | 99.1 | 96.0 | 49/860 (5.7%) | 0.3% | 97.8 | 238.8 |
| rules+openmed-large-t0.1 | 99.9 | 99.5 | 5/860 (0.6%) | 0.5% | 97.7 | 240.1 |

## By domain (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| clinical | 7085 | 99.1 | 99.9 |

## By input mode (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| chat | 945 | 98.8 | 99.8 |
| dictated | 878 | 99.1 | 100.0 |
| email | 758 | 98.7 | 100.0 |
| form | 884 | 99.3 | 100.0 |
| letter | 768 | 99.3 | 100.0 |
| narrative | 1028 | 99.3 | 99.7 |
| notes | 815 | 99.4 | 99.9 |
| ocr | 1009 | 98.7 | 99.8 |

## By difficulty tag (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| fmt:dash | 135 | 100.0 | 100.0 |
| fmt:dot | 124 | 100.0 | 100.0 |
| fmt:initial | 94 | 100.0 | 100.0 |
| fmt:iso | 101 | 100.0 | 100.0 |
| fmt:last_first_caps | 209 | 100.0 | 100.0 |
| fmt:named | 108 | 100.0 | 100.0 |
| fmt:named_abbr | 104 | 100.0 | 100.0 |
| fmt:numeric_short | 92 | 100.0 | 100.0 |
| fmt:numeric_us | 84 | 100.0 | 100.0 |
| fmt:paren | 113 | 99.1 | 100.0 |
| fmt:partial | 56 | 100.0 | 100.0 |
| m:cue | 1670 | 99.6 | 100.0 |
| m:digit_spaced | 65 | 55.4 | 100.0 |
| m:lower | 16 | 100.0 | 100.0 |
| m:no_cue | 5415 | 98.9 | 99.9 |
| m:repeat | 1485 | 98.9 | 99.8 |
| m:single_name | 1229 | 99.4 | 99.4 |
| planted | 7085 | 99.1 | 99.9 |
| repeat | 1239 | 98.5 | 99.8 |
| single_name | 1229 | 99.4 | 99.4 |
| spoken | 274 | 79.6 | 100.0 |

## By category (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| ACCOUNT | 412 | 92.5 | 100.0 |
| ADDRESS | 205 | 100.0 | 100.0 |
| AGE | 172 | 100.0 | 100.0 |
| DATE | 600 | 100.0 | 100.0 |
| DEVICE | 213 | 99.5 | 100.0 |
| EMAIL | 187 | 100.0 | 100.0 |
| FAX | 196 | 99.5 | 100.0 |
| IP | 227 | 100.0 | 100.0 |
| LICENSE | 194 | 97.4 | 100.0 |
| LOCATION | 203 | 100.0 | 100.0 |
| MRN | 191 | 97.9 | 100.0 |
| NAME | 2859 | 99.7 | 99.7 |
| PHONE | 201 | 100.0 | 100.0 |
| PLAN | 196 | 99.0 | 100.0 |
| SSN | 209 | 93.8 | 100.0 |
| URL | 208 | 100.0 | 100.0 |
| VEHICLE | 403 | 100.0 | 100.0 |
| ZIP | 209 | 100.0 | 100.0 |
