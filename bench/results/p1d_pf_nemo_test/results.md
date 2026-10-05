# nemo_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| privacy-filter | 78.6 | 78.0 | 1106/2000 (55.3%) | 0.3% | 97.9 | 0.0 |
| rules+privacy-filter | 89.5 | 88.8 | 695/2000 (34.8%) | 0.5% | 96.3 | 0.2 |

## By category (recall %)

| | n | privacy-filter | rules+privacy-filter |
|---|---|---|---|
| ACCOUNT | 1041 | 77.5 | 79.4 |
| ADDRESS | 464 | 79.5 | 84.9 |
| BIOMETRIC | 227 | 90.3 | 90.3 |
| DATE | 2176 | 79.2 | 94.6 |
| DEVICE | 124 | 91.1 | 98.4 |
| EMAIL | 1086 | 96.4 | 98.9 |
| FAX | 113 | 69.9 | 98.2 |
| ID | 1282 | 85.3 | 91.3 |
| IP | 195 | 88.2 | 100.0 |
| LICENSE | 61 | 86.9 | 91.8 |
| LOCATION | 703 | 22.8 | 22.9 |
| MRN | 250 | 93.2 | 97.2 |
| NAME | 2872 | 91.9 | 96.3 |
| PHONE | 464 | 87.7 | 98.7 |
| PLAN | 221 | 90.5 | 96.4 |
| SSN | 122 | 96.7 | 100.0 |
| URL | 883 | 24.3 | 93.8 |
| VEHICLE | 178 | 96.6 | 97.8 |
| ZIP | 141 | 74.5 | 75.2 |
