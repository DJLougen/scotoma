# nemo_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| scotoma-v0-int8pc | 99.6 | 99.4 | 34/2000 (1.7%) | 0.7% | 93.8 | 43.3 |
| rules+scotoma-v0-int8pc | 99.6 | 99.5 | 33/2000 (1.6%) | 0.8% | 92.3 | 40.5 |

## By category (recall %)

| | n | scotoma-v0-int8pc | rules+scotoma-v0-int8pc |
|---|---|---|---|
| ACCOUNT | 1041 | 99.9 | 99.9 |
| ADDRESS | 464 | 100.0 | 100.0 |
| BIOMETRIC | 227 | 100.0 | 100.0 |
| DATE | 2176 | 99.3 | 99.3 |
| DEVICE | 124 | 100.0 | 100.0 |
| EMAIL | 1086 | 99.4 | 99.4 |
| FAX | 113 | 100.0 | 100.0 |
| ID | 1282 | 99.7 | 99.7 |
| IP | 195 | 100.0 | 100.0 |
| LICENSE | 61 | 100.0 | 100.0 |
| LOCATION | 703 | 97.6 | 97.6 |
| MRN | 250 | 100.0 | 100.0 |
| NAME | 2872 | 99.8 | 99.9 |
| PHONE | 464 | 100.0 | 100.0 |
| PLAN | 221 | 100.0 | 100.0 |
| SSN | 122 | 100.0 | 100.0 |
| URL | 883 | 100.0 | 100.0 |
| VEHICLE | 178 | 100.0 | 100.0 |
| ZIP | 141 | 98.6 | 98.6 |
