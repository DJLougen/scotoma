# clin_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| stanford-t0.1 | 96.6 | 86.9 | 211/874 (24.1%) | 0.4% | 98.7 | 27.7 |
| rules+stanford-t0.1 | 99.3 | 96.3 | 43/874 (4.9%) | 0.5% | 98.6 | 26.9 |

## By domain (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| clinical | 7168 | 96.6 | 99.3 |

## By input mode (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| chat | 944 | 95.9 | 98.6 |
| dictated | 798 | 97.5 | 100.0 |
| email | 910 | 96.0 | 98.8 |
| form | 1029 | 97.0 | 99.8 |
| letter | 821 | 96.1 | 99.6 |
| narrative | 914 | 96.7 | 99.6 |
| notes | 805 | 95.7 | 98.1 |
| ocr | 947 | 97.7 | 99.9 |

## By difficulty tag (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| fmt:dash | 140 | 100.0 | 100.0 |
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
| m:cue | 1633 | 92.9 | 99.8 |
| m:digit_spaced | 76 | 80.3 | 100.0 |
| m:lower | 14 | 92.9 | 92.9 |
| m:no_cue | 5535 | 97.7 | 99.2 |
| m:repeat | 1464 | 98.4 | 99.2 |
| m:single_name | 1234 | 98.6 | 98.9 |
| planted | 7168 | 96.6 | 99.3 |
| repeat | 1222 | 97.8 | 99.3 |
| single_name | 1234 | 98.6 | 98.9 |
| spoken | 272 | 91.2 | 99.6 |

## By category (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| ACCOUNT | 415 | 96.4 | 100.0 |
| ADDRESS | 204 | 99.5 | 99.5 |
| AGE | 173 | 6.4 | 94.2 |
| DATE | 612 | 100.0 | 100.0 |
| DEVICE | 198 | 100.0 | 100.0 |
| EMAIL | 213 | 99.5 | 99.5 |
| FAX | 220 | 100.0 | 100.0 |
| IP | 209 | 97.6 | 100.0 |
| LICENSE | 187 | 99.5 | 100.0 |
| LOCATION | 201 | 98.0 | 98.0 |
| MRN | 198 | 99.0 | 100.0 |
| NAME | 2841 | 99.2 | 99.4 |
| PHONE | 205 | 100.0 | 100.0 |
| PLAN | 224 | 99.6 | 100.0 |
| SSN | 205 | 98.0 | 100.0 |
| URL | 226 | 100.0 | 100.0 |
| VEHICLE | 420 | 94.0 | 96.9 |
| ZIP | 217 | 99.1 | 99.1 |
