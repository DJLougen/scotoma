# nemo_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules | 51.5 | 50.9 | 1788/2000 (89.4%) | 0.2% | 96.6 | 0.2 |
| openmed | 97.3 | 94.5 | 196/2000 (9.8%) | 0.1% | 98.5 | 74.5 |
| rules+openmed | 97.8 | 97.0 | 157/2000 (7.8%) | 0.3% | 96.8 | 74.7 |
| ours | 98.5 | 98.3 | 99/2000 (5.0%) | 0.1% | 99.1 | 73.4 |
| rules+ours | 98.6 | 98.4 | 93/2000 (4.7%) | 0.3% | 97.5 | 74.4 |

## By category (recall %)

| | n | rules | openmed | rules+openmed | ours | rules+ours |
|---|---|---|---|---|---|---|
| ACCOUNT | 1041 | 24.7 | 98.0 | 98.1 | 99.8 | 99.8 |
| ADDRESS | 464 | 41.4 | 98.3 | 98.3 | 100.0 | 100.0 |
| BIOMETRIC | 227 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| DATE | 2176 | 92.7 | 96.0 | 96.0 | 96.0 | 96.0 |
| DEVICE | 124 | 71.0 | 99.2 | 100.0 | 100.0 | 100.0 |
| EMAIL | 1086 | 98.6 | 98.1 | 98.9 | 98.9 | 99.0 |
| FAX | 113 | 93.8 | 98.2 | 100.0 | 100.0 | 100.0 |
| ID | 1282 | 30.7 | 98.8 | 99.0 | 99.4 | 99.4 |
| IP | 195 | 97.4 | 99.0 | 100.0 | 99.5 | 100.0 |
| LICENSE | 61 | 57.4 | 100.0 | 100.0 | 100.0 | 100.0 |
| LOCATION | 703 | 3.1 | 84.9 | 85.5 | 91.7 | 91.7 |
| MRN | 250 | 58.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| NAME | 2872 | 17.9 | 98.7 | 99.6 | 99.6 | 99.7 |
| PHONE | 464 | 82.5 | 98.3 | 100.0 | 100.0 | 100.0 |
| PLAN | 221 | 46.6 | 99.5 | 99.5 | 100.0 | 100.0 |
| SSN | 122 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| URL | 883 | 86.4 | 98.5 | 99.5 | 99.7 | 99.9 |
| VEHICLE | 178 | 38.2 | 99.4 | 99.4 | 100.0 | 100.0 |
| ZIP | 141 | 16.3 | 90.1 | 90.8 | 95.7 | 95.7 |
