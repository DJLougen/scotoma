# Battery scorecard: scotoma-demo-fmt

model `/Users/djl/Projects/scotoma/models/scotoma-demo-fmt` · threshold 0.02 · rules both · **quick: first 100 docs per set** · 2026-10-04 22:27:38 · 50.4s

| set | docs | system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|---|---|
| tpl_test | 100 | scotoma-demo-fmt | 99.9 | 99.2 | 1/100 (1.0%) | 5.1% | 89.6 | 16.8 |
| tpl_test | 100 | rules+scotoma-demo-fmt | 99.9 | 99.6 | 1/100 (1.0%) | 5.1% | 89.5 | 16.5 |
| nemo_test | 100 | scotoma-demo-fmt | 99.4 | 99.1 | 3/100 (3.0%) | 0.5% | 95.4 | 42.6 |
| nemo_test | 100 | rules+scotoma-demo-fmt | 99.4 | 99.1 | 3/100 (3.0%) | 0.6% | 94.8 | 46.7 |
| clin_dev | 100 | scotoma-demo-fmt | 99.9 | 98.9 | 1/100 (1.0%) | 0.3% | 97.8 | 21.5 |
| clin_dev | 100 | rules+scotoma-demo-fmt | 99.9 | 99.1 | 1/100 (1.0%) | 0.5% | 97.7 | 23.4 |
| clin_novel_dev | 100 | scotoma-demo-fmt | 99.3 | 94.3 | 5/100 (5.0%) | 0.3% | 97.9 | 21.9 |
| clin_novel_dev | 100 | rules+scotoma-demo-fmt | 99.6 | 95.5 | 3/100 (3.0%) | 0.5% | 97.9 | 22.2 |
| clin_dev_fp32 | 100 | scotoma-demo-fmt | 100.0 | 97.5 | 0/100 (0.0%) | 0.4% | 96.4 | 42.4 |
| clin_dev_fp32 | 100 | rules+scotoma-demo-fmt | 100.0 | 97.8 | 0/100 (0.0%) | 0.6% | 96.3 | 46.2 |

## clin_dev: recall by category (scotoma-demo-fmt)

| category | n | recall |
|---|---|---|
| NAME | 336 | 99.7 |
| DATE | 66 | 100.0 |
| ACCOUNT | 51 | 100.0 |
| VEHICLE | 41 | 100.0 |
| URL | 31 | 100.0 |
| PHONE | 29 | 100.0 |
| EMAIL | 28 | 100.0 |
| LOCATION | 28 | 100.0 |
| MRN | 28 | 100.0 |
| PLAN | 28 | 100.0 |
| ADDRESS | 26 | 100.0 |
| DEVICE | 25 | 100.0 |
| LICENSE | 25 | 100.0 |
| SSN | 24 | 100.0 |
| ZIP | 23 | 100.0 |
| AGE | 21 | 100.0 |
| FAX | 20 | 100.0 |
| IP | 19 | 100.0 |
| ID | 0 | – |

## clin_novel_dev: recall by category (scotoma-demo-fmt)

| category | n | recall |
|---|---|---|
| NAME | 336 | 99.1 |
| DATE | 66 | 100.0 |
| ACCOUNT | 51 | 100.0 |
| VEHICLE | 41 | 100.0 |
| URL | 31 | 100.0 |
| PHONE | 29 | 89.7 |
| EMAIL | 28 | 100.0 |
| LOCATION | 28 | 100.0 |
| MRN | 28 | 100.0 |
| PLAN | 28 | 100.0 |
| ADDRESS | 26 | 100.0 |
| DEVICE | 25 | 100.0 |
| LICENSE | 25 | 100.0 |
| SSN | 24 | 100.0 |
| ZIP | 23 | 100.0 |
| AGE | 21 | 100.0 |
| FAX | 20 | 100.0 |
| IP | 19 | 100.0 |
| BIOMETRIC | 0 | – |
| ID | 0 | – |

## Threshold sweep on clin_dev

| threshold | recall | full | precision | leak docs | over-redaction |
|---|---|---|---|---|---|
| 0.05000000074505806 | 99.9 | 98.1 | 98.7 | 1 | 0.4% |
| 0.10000000149011612 | 99.6 | 97.5 | 99.0 | 2 | 0.3% |
| 0.20000000298023224 | 99.4 | 96.7 | 99.2 | 4 | 0.3% |
| 0.3499999940395355 | 99.1 | 96.2 | 99.8 | 7 | 0.3% |
| 0.5 | 98.7 | 95.6 | 100.0 | 10 | 0.2% |
| 0.699999988079071 | 98.0 | 95.1 | 100.0 | 16 | 0.2% |
| 0.8999999761581421 | 96.2 | 92.1 | 99.9 | 28 | 0.2% |

## Gates

| gate | set | system | actual | limit | result |
|---|---|---|---|---|---|
| over_redaction | tpl_test | scotoma-demo-fmt | 0.0506 | 0.0100 | **FAIL** |
| over_redaction | tpl_test | rules+scotoma-demo-fmt | 0.0510 | 0.0100 | **FAIL** |
| over_redaction | nemo_test | scotoma-demo-fmt | 0.0053 | 0.0100 | PASS |
| over_redaction | nemo_test | rules+scotoma-demo-fmt | 0.0061 | 0.0100 | PASS |
| over_redaction | clin_dev | scotoma-demo-fmt | 0.0030 | 0.0100 | PASS |
| over_redaction | clin_dev | rules+scotoma-demo-fmt | 0.0050 | 0.0100 | PASS |
| over_redaction | clin_novel_dev | scotoma-demo-fmt | 0.0027 | 0.0100 | PASS |
| over_redaction | clin_novel_dev | rules+scotoma-demo-fmt | 0.0047 | 0.0100 | PASS |
| leak_regression | clin_dev | scotoma-demo-fmt | 0.0100 | 0.0250 | PASS | baseline scotoma-v0-int8pc leak 2.00% -> 1.00%
| leak_regression | clin_novel_dev | scotoma-demo-fmt | 0.0500 | 0.0750 | PASS | baseline scotoma-v0-int8pc leak 7.00% -> 5.00%
| int8_fp32_gap | clin_dev | scotoma-demo-fmt | 0.0012 | 0.0050 | PASS | int8 99.88% vs fp32 100.00%
| int8_fp32_gap | clin_dev | rules+scotoma-demo-fmt | 0.0012 | 0.0050 | PASS | int8 99.88% vs fp32 100.00%

## Verdict: FAIL
