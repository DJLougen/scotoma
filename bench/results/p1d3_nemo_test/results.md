# nemo_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| piiranha | 59.8 | 54.6 | 1732/2000 (86.6%) | 0.2% | 97.4 | 152.8 |
| rules+piiranha | 85.5 | 84.1 | 1032/2000 (51.6%) | 0.4% | 96.3 | 155.9 |
| ai4privacy-en | 81.7 | 71.7 | 1047/2000 (52.4%) | 0.7% | 89.5 | 186.1 |
| rules+ai4privacy-en | 88.2 | 85.4 | 661/2000 (33.0%) | 0.8% | 88.8 | 188.8 |
| ai4privacy-cat | 73.0 | 56.2 | 1316/2000 (65.8%) | 0.2% | 95.4 | 185.1 |
| rules+ai4privacy-cat | 83.9 | 79.0 | 906/2000 (45.3%) | 0.4% | 94.2 | 175.8 |

## By category (recall %)

| | n | piiranha | rules+piiranha | ai4privacy-en | rules+ai4privacy-en | ai4privacy-cat | rules+ai4privacy-cat |
|---|---|---|---|---|---|---|---|
| ACCOUNT | 1041 | 66.9 | 68.8 | 97.8 | 97.8 | 93.1 | 93.1 |
| ADDRESS | 464 | 75.9 | 76.5 | 99.1 | 99.4 | 94.0 | 94.4 |
| BIOMETRIC | 227 | 89.4 | 89.4 | 100.0 | 100.0 | 100.0 | 100.0 |
| DATE | 2176 | 19.1 | 92.7 | 96.6 | 97.0 | 90.4 | 95.4 |
| DEVICE | 124 | 4.8 | 75.0 | 91.9 | 95.2 | 45.2 | 91.1 |
| EMAIL | 1086 | 97.1 | 98.9 | 80.7 | 98.7 | 75.0 | 98.6 |
| FAX | 113 | 87.6 | 99.1 | 100.0 | 100.0 | 100.0 | 100.0 |
| ID | 1282 | 63.7 | 75.0 | 80.5 | 80.9 | 67.4 | 68.2 |
| IP | 195 | 59.0 | 97.4 | 93.3 | 99.5 | 81.5 | 98.5 |
| LICENSE | 61 | 47.5 | 73.8 | 100.0 | 100.0 | 100.0 | 100.0 |
| LOCATION | 703 | 67.9 | 68.3 | 68.7 | 68.7 | 54.2 | 55.3 |
| MRN | 250 | 64.8 | 84.0 | 100.0 | 100.0 | 99.6 | 99.6 |
| NAME | 2872 | 81.2 | 91.1 | 67.3 | 71.4 | 47.7 | 65.8 |
| PHONE | 464 | 73.7 | 92.7 | 100.0 | 100.0 | 100.0 | 100.0 |
| PLAN | 221 | 64.3 | 76.0 | 99.5 | 99.5 | 99.1 | 99.1 |
| SSN | 122 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| URL | 883 | 3.5 | 88.7 | 36.8 | 91.3 | 48.6 | 91.4 |
| VEHICLE | 178 | 1.7 | 38.8 | 100.0 | 100.0 | 97.8 | 99.4 |
| ZIP | 141 | 95.0 | 95.0 | 97.2 | 97.2 | 87.2 | 87.9 |
