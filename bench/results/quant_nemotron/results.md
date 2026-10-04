# nemo_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| ours_int8 | 98.5 | 98.3 | 99/2000 (5.0%) | 0.1% | 99.1 | 74.2 |
| ours_fp32 | 99.1 | 99.0 | 61/2000 (3.0%) | 0.1% | 98.5 | 113.8 |

## By category (recall %)

| | n | ours_int8 | ours_fp32 |
|---|---|---|---|
| ACCOUNT | 1041 | 99.8 | 99.8 |
| ADDRESS | 464 | 100.0 | 100.0 |
| BIOMETRIC | 227 | 100.0 | 100.0 |
| DATE | 2176 | 96.0 | 97.6 |
| DEVICE | 124 | 100.0 | 100.0 |
| EMAIL | 1086 | 98.9 | 99.1 |
| FAX | 113 | 100.0 | 100.0 |
| ID | 1282 | 99.4 | 99.5 |
| IP | 195 | 99.5 | 100.0 |
| LICENSE | 61 | 100.0 | 100.0 |
| LOCATION | 703 | 91.7 | 96.0 |
| MRN | 250 | 100.0 | 100.0 |
| NAME | 2872 | 99.6 | 99.8 |
| PHONE | 464 | 100.0 | 100.0 |
| PLAN | 221 | 100.0 | 100.0 |
| SSN | 122 | 100.0 | 100.0 |
| URL | 883 | 99.7 | 99.9 |
| VEHICLE | 178 | 100.0 | 100.0 |
| ZIP | 141 | 95.7 | 97.2 |
