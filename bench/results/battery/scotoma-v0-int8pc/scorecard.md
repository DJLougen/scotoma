# Battery scorecard: scotoma-v0-int8pc

model `models/scotoma-v0-int8pc` · threshold 0.02 · rules both · 2026-10-04 22:15:06 · 468.4s

| set | docs | system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|---|---|
| tpl_test | 3000 | scotoma-v0-int8pc | 99.3 | 97.5 | 199/3000 (6.6%) | 3.0% | 91.9 | 20.3 |
| tpl_test | 3000 | rules+scotoma-v0-int8pc | 99.7 | 99.0 | 89/3000 (3.0%) | 3.1% | 91.8 | 20.8 |
| nemo_test | 2000 | scotoma-v0-int8pc | 99.6 | 99.4 | 34/2000 (1.7%) | 0.7% | 93.8 | 43.3 |
| nemo_test | 2000 | rules+scotoma-v0-int8pc | 99.6 | 99.5 | 33/2000 (1.7%) | 0.8% | 92.3 | 40.5 |
| clin_dev | 844 | scotoma-v0-int8pc | 99.7 | 97.9 | 18/844 (2.1%) | 0.1% | 99.4 | 20.2 |
| clin_dev | 844 | rules+scotoma-v0-int8pc | 99.8 | 98.0 | 16/844 (1.9%) | 0.3% | 99.4 | 20.4 |

## clin_dev: recall by category (scotoma-v0-int8pc)

| category | n | recall |
|---|---|---|
| NAME | 2796 | 99.7 |
| DATE | 569 | 100.0 |
| VEHICLE | 410 | 98.3 |
| ACCOUNT | 406 | 100.0 |
| LOCATION | 234 | 100.0 |
| LICENSE | 230 | 100.0 |
| SSN | 224 | 100.0 |
| MRN | 223 | 100.0 |
| ADDRESS | 220 | 100.0 |
| DEVICE | 218 | 100.0 |
| PHONE | 216 | 100.0 |
| IP | 213 | 100.0 |
| URL | 210 | 100.0 |
| EMAIL | 201 | 99.5 |
| ZIP | 201 | 100.0 |
| PLAN | 198 | 100.0 |
| FAX | 180 | 100.0 |
| AGE | 168 | 98.8 |
| BIOMETRIC | 0 | – |
| ID | 0 | – |

## Threshold sweep on clin_dev

| threshold | recall | full | precision | leak docs | over-redaction |
|---|---|---|---|---|---|
| 0.019999999552965164 | 99.8 | 98.0 | 99.4 | 16 | 0.3% |
| 0.05000000074505806 | 99.5 | 97.3 | 99.7 | 31 | 0.2% |
| 0.10000000149011612 | 99.2 | 96.8 | 99.8 | 52 | 0.2% |
| 0.20000000298023224 | 98.7 | 95.9 | 99.8 | 82 | 0.2% |
| 0.3499999940395355 | 98.1 | 94.8 | 99.9 | 118 | 0.2% |
| 0.5 | 97.3 | 94.0 | 99.9 | 161 | 0.2% |
| 0.699999988079071 | 96.2 | 92.8 | 100.0 | 210 | 0.2% |
| 0.8999999761581421 | 93.6 | 90.4 | 100.0 | 329 | 0.2% |

## Gates

| gate | set | system | actual | limit | result |
|---|---|---|---|---|---|
| over_redaction | tpl_test | scotoma-v0-int8pc | 0.0305 | 0.0100 | **FAIL** |
| over_redaction | tpl_test | rules+scotoma-v0-int8pc | 0.0311 | 0.0100 | **FAIL** |
| over_redaction | nemo_test | scotoma-v0-int8pc | 0.0066 | 0.0100 | PASS |
| over_redaction | nemo_test | rules+scotoma-v0-int8pc | 0.0083 | 0.0100 | PASS |
| over_redaction | clin_dev | scotoma-v0-int8pc | 0.0012 | 0.0100 | PASS |
| over_redaction | clin_dev | rules+scotoma-v0-int8pc | 0.0028 | 0.0100 | PASS |

## Verdict: FAIL
