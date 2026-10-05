# clin3_test.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| ours | 100.0 | 99.7 | 4/7108 (0.1%) | 0.1% | 99.2 | 37.8 |
| rules+ours | 100.0 | 99.8 | 2/7108 (0.0%) | 0.2% | 99.2 | 36.4 |

## By domain (recall %)

| | n | ours | rules+ours |
|---|---|---|---|
| clinical | 58404 | 100.0 | 100.0 |

## By input mode (recall %)

| | n | ours | rules+ours |
|---|---|---|---|
| chat | 7123 | 100.0 | 100.0 |
| dictated | 7461 | 100.0 | 100.0 |
| email | 7117 | 100.0 | 100.0 |
| form | 8020 | 100.0 | 100.0 |
| letter | 6572 | 100.0 | 100.0 |
| narrative | 7451 | 100.0 | 100.0 |
| notes | 7608 | 100.0 | 100.0 |
| ocr | 7052 | 100.0 | 100.0 |

## By difficulty tag (recall %)

| | n | ours | rules+ours |
|---|---|---|---|
| fmt:dash | 1000 | 100.0 | 100.0 |
| fmt:dot | 1058 | 100.0 | 100.0 |
| fmt:initial | 708 | 100.0 | 100.0 |
| fmt:iso | 806 | 100.0 | 100.0 |
| fmt:last_first_caps | 1583 | 100.0 | 100.0 |
| fmt:named | 813 | 100.0 | 100.0 |
| fmt:named_abbr | 844 | 100.0 | 100.0 |
| fmt:numeric_short | 821 | 100.0 | 100.0 |
| fmt:numeric_us | 803 | 100.0 | 100.0 |
| fmt:paren | 1032 | 100.0 | 100.0 |
| fmt:partial | 462 | 100.0 | 100.0 |
| planted | 58404 | 100.0 | 100.0 |
| repeat | 10394 | 100.0 | 100.0 |
| single_name | 10061 | 100.0 | 100.0 |
| spoken | 2358 | 100.0 | 100.0 |

## By category (recall %)

| | n | ours | rules+ours |
|---|---|---|---|
| ACCOUNT | 3363 | 100.0 | 100.0 |
| ADDRESS | 1691 | 100.0 | 100.0 |
| AGE | 1333 | 100.0 | 100.0 |
| DATE | 5144 | 100.0 | 100.0 |
| DEVICE | 1752 | 100.0 | 100.0 |
| EMAIL | 1741 | 99.9 | 100.0 |
| FAX | 1593 | 100.0 | 100.0 |
| IP | 1744 | 100.0 | 100.0 |
| LICENSE | 1573 | 100.0 | 100.0 |
| LOCATION | 1701 | 100.0 | 100.0 |
| MRN | 1614 | 100.0 | 100.0 |
| NAME | 23313 | 100.0 | 100.0 |
| PHONE | 1698 | 100.0 | 100.0 |
| PLAN | 1596 | 100.0 | 100.0 |
| SSN | 1663 | 100.0 | 100.0 |
| URL | 1632 | 100.0 | 100.0 |
| VEHICLE | 3531 | 100.0 | 100.0 |
| ZIP | 1722 | 100.0 | 100.0 |
