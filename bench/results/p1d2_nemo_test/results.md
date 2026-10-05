# nemo_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| stanford | 92.5 | 76.2 | 652/2000 (32.6%) | 1.0% | 89.8 | 70.4 |
| rules+stanford | 96.9 | 93.8 | 261/2000 (13.1%) | 1.1% | 88.3 | 71.3 |
| presidio | 79.9 | 72.3 | 1289/2000 (64.5%) | 1.6% | 80.2 | 0.0 |
| rules+presidio | 85.0 | 80.1 | 1070/2000 (53.5%) | 1.8% | 79.6 | 0.4 |

## By category (recall %)

| | n | stanford | rules+stanford | presidio | rules+presidio |
|---|---|---|---|---|---|
| ACCOUNT | 1041 | 93.0 | 93.0 | 66.7 | 70.2 |
| ADDRESS | 464 | 94.8 | 95.3 | 32.8 | 64.2 |
| BIOMETRIC | 227 | 100.0 | 100.0 | 100.0 | 100.0 |
| DATE | 2176 | 97.8 | 97.8 | 96.6 | 97.2 |
| DEVICE | 124 | 77.4 | 100.0 | 83.9 | 83.9 |
| EMAIL | 1086 | 95.5 | 98.9 | 98.9 | 98.9 |
| FAX | 113 | 100.0 | 100.0 | 94.7 | 98.2 |
| ID | 1282 | 97.7 | 97.7 | 44.1 | 55.9 |
| IP | 195 | 95.9 | 100.0 | 96.9 | 99.5 |
| LICENSE | 61 | 100.0 | 100.0 | 83.6 | 90.2 |
| LOCATION | 703 | 76.8 | 77.0 | 60.9 | 61.6 |
| MRN | 250 | 100.0 | 100.0 | 98.8 | 99.6 |
| NAME | 2872 | 98.9 | 99.3 | 86.4 | 92.0 |
| PHONE | 464 | 99.8 | 100.0 | 96.8 | 97.6 |
| PLAN | 221 | 100.0 | 100.0 | 68.8 | 82.8 |
| SSN | 122 | 100.0 | 100.0 | 100.0 | 100.0 |
| URL | 883 | 45.4 | 97.7 | 95.7 | 95.9 |
| VEHICLE | 178 | 99.4 | 100.0 | 7.9 | 41.6 |
| ZIP | 141 | 95.0 | 95.0 | 46.8 | 57.4 |
