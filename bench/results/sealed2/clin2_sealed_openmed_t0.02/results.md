# clin2_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| openmed-t0.02 | 97.6 | 94.4 | 131/860 (15.2%) | 0.4% | 97.3 | 19.0 |
| rules+openmed-t0.02 | 99.9 | 99.4 | 5/860 (0.6%) | 0.5% | 97.2 | 19.4 |

## By domain (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| clinical | 7085 | 97.6 | 99.9 |

## By input mode (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| chat | 945 | 98.2 | 100.0 |
| dictated | 878 | 97.5 | 100.0 |
| email | 758 | 97.2 | 99.7 |
| form | 884 | 97.4 | 100.0 |
| letter | 768 | 97.4 | 100.0 |
| narrative | 1028 | 97.6 | 100.0 |
| notes | 815 | 97.4 | 99.4 |
| ocr | 1009 | 97.6 | 100.0 |

## By difficulty tag (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| fmt:dash | 135 | 100.0 | 100.0 |
| fmt:dot | 124 | 100.0 | 100.0 |
| fmt:initial | 94 | 100.0 | 100.0 |
| fmt:iso | 101 | 100.0 | 100.0 |
| fmt:last_first_caps | 209 | 85.2 | 99.0 |
| fmt:named | 108 | 100.0 | 100.0 |
| fmt:named_abbr | 104 | 100.0 | 100.0 |
| fmt:numeric_short | 92 | 100.0 | 100.0 |
| fmt:numeric_us | 84 | 100.0 | 100.0 |
| fmt:paren | 113 | 99.1 | 100.0 |
| fmt:partial | 56 | 100.0 | 100.0 |
| m:cue | 1670 | 97.6 | 100.0 |
| m:digit_spaced | 65 | 20.0 | 100.0 |
| m:lower | 16 | 100.0 | 100.0 |
| m:no_cue | 5415 | 97.5 | 99.9 |
| m:repeat | 1485 | 97.8 | 99.7 |
| m:single_name | 1229 | 99.4 | 99.7 |
| planted | 7085 | 97.6 | 99.9 |
| repeat | 1239 | 97.0 | 99.8 |
| single_name | 1229 | 99.4 | 99.7 |
| spoken | 274 | 52.9 | 100.0 |

## By category (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| ACCOUNT | 412 | 88.3 | 100.0 |
| ADDRESS | 205 | 100.0 | 100.0 |
| AGE | 172 | 97.1 | 99.4 |
| DATE | 600 | 100.0 | 100.0 |
| DEVICE | 213 | 92.0 | 100.0 |
| EMAIL | 187 | 100.0 | 100.0 |
| FAX | 196 | 100.0 | 100.0 |
| IP | 227 | 100.0 | 100.0 |
| LICENSE | 194 | 87.6 | 100.0 |
| LOCATION | 203 | 100.0 | 100.0 |
| MRN | 191 | 94.8 | 100.0 |
| NAME | 2859 | 98.7 | 99.8 |
| PHONE | 201 | 99.5 | 100.0 |
| PLAN | 196 | 93.9 | 100.0 |
| SSN | 209 | 91.4 | 100.0 |
| URL | 208 | 100.0 | 100.0 |
| VEHICLE | 403 | 100.0 | 100.0 |
| ZIP | 209 | 100.0 | 100.0 |
