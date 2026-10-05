# clin3_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules+openmed-large-t0.1 | 99.9 | 99.7 | 26/7108 (0.4%) | 0.5% | 97.6 | 764.7 |
| openmed-large-t0.1 | 99.1 | 96.1 | 407/7108 (5.7%) | 0.3% | 97.7 | 0.4 |
| rules+openmed-large | 99.8 | 98.3 | 101/7108 (1.4%) | 0.3% | 99.0 | 1.0 |
| openmed-large | 98.5 | 94.0 | 680/7108 (9.6%) | 0.1% | 99.0 | 0.4 |

## By domain (recall %)

| | n | rules+openmed-large-t0.1 | openmed-large-t0.1 | rules+openmed-large | openmed-large |
|---|---|---|---|---|---|
| clinical | 58404 | 99.9 | 99.1 | 99.8 | 98.5 |

## By input mode (recall %)

| | n | rules+openmed-large-t0.1 | openmed-large-t0.1 | rules+openmed-large | openmed-large |
|---|---|---|---|---|---|
| chat | 7123 | 99.9 | 98.9 | 99.6 | 98.2 |
| dictated | 7461 | 100.0 | 99.2 | 99.9 | 98.9 |
| email | 7117 | 100.0 | 99.0 | 99.9 | 98.8 |
| form | 8020 | 100.0 | 99.3 | 99.9 | 98.6 |
| letter | 6572 | 100.0 | 99.3 | 99.8 | 98.8 |
| narrative | 7451 | 100.0 | 99.4 | 99.9 | 98.8 |
| notes | 7608 | 99.9 | 98.8 | 99.6 | 97.9 |
| ocr | 7052 | 99.9 | 99.0 | 99.7 | 98.1 |

## By difficulty tag (recall %)

| | n | rules+openmed-large-t0.1 | openmed-large-t0.1 | rules+openmed-large | openmed-large |
|---|---|---|---|---|---|
| fmt:dash | 1000 | 100.0 | 100.0 | 100.0 | 99.9 |
| fmt:dot | 1058 | 100.0 | 99.9 | 100.0 | 99.8 |
| fmt:initial | 708 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:iso | 806 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:last_first_caps | 1583 | 100.0 | 99.8 | 99.9 | 98.7 |
| fmt:named | 813 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:named_abbr | 844 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:numeric_short | 821 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:numeric_us | 803 | 100.0 | 100.0 | 100.0 | 100.0 |
| fmt:paren | 1032 | 100.0 | 99.2 | 100.0 | 96.4 |
| fmt:partial | 462 | 100.0 | 100.0 | 100.0 | 100.0 |
| planted | 58404 | 99.9 | 99.1 | 99.8 | 98.5 |
| repeat | 10394 | 99.9 | 98.7 | 99.7 | 98.2 |
| single_name | 10061 | 99.7 | 99.7 | 99.5 | 99.5 |
| spoken | 2358 | 100.0 | 80.2 | 100.0 | 72.1 |

## By category (recall %)

| | n | rules+openmed-large-t0.1 | openmed-large-t0.1 | rules+openmed-large | openmed-large |
|---|---|---|---|---|---|
| ACCOUNT | 3363 | 100.0 | 92.1 | 99.2 | 89.7 |
| ADDRESS | 1691 | 100.0 | 100.0 | 100.0 | 100.0 |
| AGE | 1333 | 99.9 | 99.9 | 99.8 | 99.8 |
| DATE | 5144 | 100.0 | 100.0 | 100.0 | 100.0 |
| DEVICE | 1752 | 100.0 | 98.5 | 100.0 | 95.9 |
| EMAIL | 1741 | 100.0 | 100.0 | 100.0 | 100.0 |
| FAX | 1593 | 100.0 | 99.6 | 100.0 | 98.7 |
| IP | 1744 | 100.0 | 100.0 | 100.0 | 100.0 |
| LICENSE | 1573 | 100.0 | 98.5 | 100.0 | 97.4 |
| LOCATION | 1701 | 99.9 | 99.9 | 99.7 | 99.7 |
| MRN | 1614 | 100.0 | 96.9 | 100.0 | 94.6 |
| NAME | 23313 | 99.9 | 99.9 | 99.8 | 99.7 |
| PHONE | 1698 | 100.0 | 99.9 | 100.0 | 98.8 |
| PLAN | 1596 | 100.0 | 97.8 | 100.0 | 96.6 |
| SSN | 1663 | 100.0 | 96.0 | 100.0 | 94.5 |
| URL | 1632 | 100.0 | 100.0 | 100.0 | 100.0 |
| VEHICLE | 3531 | 99.9 | 99.9 | 99.2 | 99.1 |
| ZIP | 1722 | 99.9 | 99.9 | 99.5 | 99.4 |
