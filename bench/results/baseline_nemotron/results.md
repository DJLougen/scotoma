# nemo_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules | 51.5 | 50.9 | 1788/2000 (89.4%) | 0.2% | 96.6 | 0.2 |
| openmed | 97.3 | 94.5 | 196/2000 (9.8%) | 0.1% | 98.5 | 91.1 |
| rules+openmed | 97.8 | 97.0 | 157/2000 (7.8%) | 0.3% | 96.8 | 79.6 |

## By category (recall %)

| | n | rules | openmed | rules+openmed |
|---|---|---|---|---|
| ACCOUNT | 1041 | 24.7 | 98.0 | 98.1 |
| ADDRESS | 464 | 41.4 | 98.3 | 98.3 |
| BIOMETRIC | 227 | 0.0 | 100.0 | 100.0 |
| DATE | 2176 | 92.7 | 96.0 | 96.0 |
| DEVICE | 124 | 71.0 | 99.2 | 100.0 |
| EMAIL | 1086 | 98.6 | 98.1 | 98.9 |
| FAX | 113 | 93.8 | 98.2 | 100.0 |
| ID | 1282 | 30.7 | 98.8 | 99.0 |
| IP | 195 | 97.4 | 99.0 | 100.0 |
| LICENSE | 61 | 57.4 | 100.0 | 100.0 |
| LOCATION | 703 | 3.1 | 84.9 | 85.5 |
| MRN | 250 | 58.0 | 100.0 | 100.0 |
| NAME | 2872 | 17.9 | 98.7 | 99.6 |
| PHONE | 464 | 82.5 | 98.3 | 100.0 |
| PLAN | 221 | 46.6 | 99.5 | 99.5 |
| SSN | 122 | 100.0 | 100.0 | 100.0 |
| URL | 883 | 86.4 | 98.5 | 99.5 |
| VEHICLE | 178 | 38.2 | 99.4 | 99.4 |
| ZIP | 141 | 16.3 | 90.1 | 90.8 |
