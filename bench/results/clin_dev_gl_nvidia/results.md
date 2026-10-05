# clin_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| gliner-nvidia | 95.6 | 91.1 | 230/844 (27.3%) | 0.2% | 99.1 | 0.0 |
| rules+gliner-nvidia | 99.6 | 96.0 | 26/844 (3.1%) | 0.4% | 99.1 | 0.2 |

## By domain (recall %)

| | n | gliner-nvidia | rules+gliner-nvidia |
|---|---|---|---|
| clinical | 7117 | 95.6 | 99.6 |

## By input mode (recall %)

| | n | gliner-nvidia | rules+gliner-nvidia |
|---|---|---|---|
| chat | 869 | 96.1 | 99.8 |
| dictated | 885 | 95.0 | 99.8 |
| email | 937 | 96.3 | 99.6 |
| form | 890 | 96.3 | 99.9 |
| letter | 824 | 95.4 | 99.9 |
| narrative | 930 | 95.6 | 99.0 |
| notes | 880 | 95.3 | 99.7 |
| ocr | 902 | 94.5 | 99.1 |

## By difficulty tag (recall %)

| | n | gliner-nvidia | rules+gliner-nvidia |
|---|---|---|---|
| fmt:dash | 127 | 99.2 | 100.0 |
| fmt:dot | 100 | 100.0 | 100.0 |
| fmt:initial | 73 | 100.0 | 100.0 |
| fmt:iso | 97 | 100.0 | 100.0 |
| fmt:last_first_caps | 194 | 94.8 | 94.8 |
| fmt:named | 99 | 100.0 | 100.0 |
| fmt:named_abbr | 81 | 100.0 | 100.0 |
| fmt:numeric_short | 94 | 100.0 | 100.0 |
| fmt:numeric_us | 104 | 100.0 | 100.0 |
| fmt:paren | 137 | 100.0 | 100.0 |
| fmt:partial | 47 | 100.0 | 100.0 |
| m:cue | 1651 | 98.1 | 99.9 |
| m:digit_spaced | 59 | 64.4 | 100.0 |
| m:lower | 17 | 100.0 | 100.0 |
| m:no_cue | 5466 | 94.8 | 99.5 |
| m:repeat | 1511 | 97.2 | 99.7 |
| m:single_name | 1237 | 99.2 | 99.3 |
| planted | 7117 | 95.6 | 99.6 |
| repeat | 1358 | 94.5 | 99.8 |
| single_name | 1237 | 99.2 | 99.3 |
| spoken | 278 | 73.4 | 100.0 |

## By category (recall %)

| | n | gliner-nvidia | rules+gliner-nvidia |
|---|---|---|---|
| ACCOUNT | 406 | 90.4 | 99.3 |
| ADDRESS | 220 | 100.0 | 100.0 |
| AGE | 168 | 98.8 | 99.4 |
| DATE | 569 | 100.0 | 100.0 |
| DEVICE | 218 | 95.4 | 98.6 |
| EMAIL | 201 | 100.0 | 100.0 |
| FAX | 180 | 99.4 | 100.0 |
| IP | 213 | 100.0 | 100.0 |
| LICENSE | 230 | 94.3 | 99.1 |
| LOCATION | 234 | 100.0 | 100.0 |
| MRN | 223 | 97.3 | 100.0 |
| NAME | 2796 | 99.3 | 99.3 |
| PHONE | 216 | 100.0 | 100.0 |
| PLAN | 198 | 96.5 | 100.0 |
| SSN | 224 | 96.0 | 100.0 |
| URL | 210 | 1.4 | 100.0 |
| VEHICLE | 410 | 99.8 | 99.8 |
| ZIP | 201 | 99.5 | 99.5 |
