# nemo_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| openmed-large-fp32 | 99.1 | 98.8 | 64/2000 (3.2%) | 0.2% | 98.2 | 740.7 |
| rules+openmed-large-fp32 | 99.1 | 98.9 | 64/2000 (3.2%) | 0.3% | 96.7 | 741.0 |

## By category (recall %)

| | n | openmed-large-fp32 | rules+openmed-large-fp32 |
|---|---|---|---|
| ACCOUNT | 1041 | 99.8 | 99.8 |
| ADDRESS | 464 | 100.0 | 100.0 |
| BIOMETRIC | 227 | 100.0 | 100.0 |
| DATE | 2176 | 97.3 | 97.3 |
| DEVICE | 124 | 100.0 | 100.0 |
| EMAIL | 1086 | 99.2 | 99.2 |
| FAX | 113 | 100.0 | 100.0 |
| ID | 1282 | 99.4 | 99.4 |
| IP | 195 | 100.0 | 100.0 |
| LICENSE | 61 | 100.0 | 100.0 |
| LOCATION | 703 | 96.0 | 96.0 |
| MRN | 250 | 100.0 | 100.0 |
| NAME | 2872 | 99.8 | 99.8 |
| PHONE | 464 | 100.0 | 100.0 |
| PLAN | 221 | 99.5 | 99.5 |
| SSN | 122 | 100.0 | 100.0 |
| URL | 883 | 99.9 | 99.9 |
| VEHICLE | 178 | 100.0 | 100.0 |
| ZIP | 141 | 97.2 | 97.2 |
