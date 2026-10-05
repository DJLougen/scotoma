# nemo_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules+v1small | 99.5 | 99.4 | 37/2000 (1.9%) | 0.8% | 92.8 | 38.1 |

## By category (recall %)

| | n | rules+v1small |
|---|---|---|
| ACCOUNT | 1041 | 99.9 |
| ADDRESS | 464 | 100.0 |
| BIOMETRIC | 227 | 100.0 |
| DATE | 2176 | 99.2 |
| DEVICE | 124 | 100.0 |
| EMAIL | 1086 | 99.3 |
| FAX | 113 | 100.0 |
| ID | 1282 | 99.6 |
| IP | 195 | 100.0 |
| LICENSE | 61 | 100.0 |
| LOCATION | 703 | 96.4 |
| MRN | 250 | 100.0 |
| NAME | 2872 | 99.9 |
| PHONE | 464 | 100.0 |
| PLAN | 221 | 100.0 |
| SSN | 122 | 100.0 |
| URL | 883 | 100.0 |
| VEHICLE | 178 | 100.0 |
| ZIP | 141 | 99.3 |
