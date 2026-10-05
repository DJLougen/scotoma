# clin2_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| stanford-t0.1 | 96.4 | 87.3 | 218/860 (25.3%) | 0.3% | 99.2 | 27.2 |
| rules+stanford-t0.1 | 99.3 | 96.5 | 46/860 (5.3%) | 0.5% | 99.2 | 27.5 |

## By domain (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| clinical | 7085 | 96.4 | 99.3 |

## By input mode (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| chat | 945 | 95.9 | 98.5 |
| dictated | 878 | 97.3 | 99.8 |
| email | 758 | 96.3 | 99.7 |
| form | 884 | 97.2 | 99.9 |
| letter | 768 | 96.2 | 99.6 |
| narrative | 1028 | 96.5 | 99.4 |
| notes | 815 | 95.8 | 97.8 |
| ocr | 1009 | 95.8 | 99.6 |

## By difficulty tag (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
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
| fmt:paren | 113 | 100.0 | 100.0 |
| fmt:partial | 56 | 100.0 | 100.0 |
| m:cue | 1670 | 94.4 | 99.7 |
| m:digit_spaced | 65 | 84.6 | 100.0 |
| m:lower | 16 | 100.0 | 100.0 |
| m:no_cue | 5415 | 97.0 | 99.2 |
| m:repeat | 1485 | 97.8 | 99.2 |
| m:single_name | 1229 | 98.0 | 98.8 |
| planted | 7085 | 96.4 | 99.3 |
| repeat | 1239 | 96.5 | 99.1 |
| single_name | 1229 | 98.0 | 98.8 |
| spoken | 274 | 87.6 | 100.0 |

## By category (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| ACCOUNT | 412 | 95.9 | 100.0 |
| ADDRESS | 205 | 99.5 | 100.0 |
| AGE | 172 | 5.8 | 92.4 |
| DATE | 600 | 100.0 | 100.0 |
| DEVICE | 213 | 95.3 | 98.6 |
| EMAIL | 187 | 100.0 | 100.0 |
| FAX | 196 | 100.0 | 100.0 |
| IP | 227 | 98.7 | 100.0 |
| LICENSE | 194 | 97.9 | 100.0 |
| LOCATION | 203 | 96.1 | 96.1 |
| MRN | 191 | 100.0 | 100.0 |
| NAME | 2859 | 99.1 | 99.5 |
| PHONE | 201 | 100.0 | 100.0 |
| PLAN | 196 | 99.5 | 100.0 |
| SSN | 209 | 97.6 | 100.0 |
| URL | 208 | 100.0 | 100.0 |
| VEHICLE | 403 | 94.8 | 97.3 |
| ZIP | 209 | 100.0 | 100.0 |
