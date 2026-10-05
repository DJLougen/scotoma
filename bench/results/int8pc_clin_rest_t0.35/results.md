# cd_rest.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| ours-int8pc | 97.5 | 94.0 | 116/644 (18.0%) | 0.0% | 99.9 | 21.7 |
| ours-fp32 | 99.6 | 96.8 | 18/644 (2.8%) | 0.0% | 99.8 | 43.8 |
| ours-int8 | 97.1 | 93.6 | 128/644 (19.9%) | 0.0% | 99.9 | 21.4 |

## By domain (recall %)

| | n | ours-int8pc | ours-fp32 | ours-int8 |
|---|---|---|---|---|
| clinical | 5379 | 97.5 | 99.6 | 97.1 |

## By input mode (recall %)

| | n | ours-int8pc | ours-fp32 | ours-int8 |
|---|---|---|---|---|
| chat | 673 | 97.5 | 99.1 | 98.2 |
| dictated | 602 | 98.2 | 99.8 | 97.2 |
| email | 757 | 95.9 | 99.1 | 95.6 |
| form | 634 | 98.6 | 99.8 | 97.9 |
| letter | 652 | 97.5 | 100.0 | 96.9 |
| narrative | 790 | 98.2 | 99.7 | 97.8 |
| notes | 592 | 97.5 | 99.8 | 96.6 |
| ocr | 679 | 97.1 | 99.9 | 96.2 |

## By difficulty tag (recall %)

| | n | ours-int8pc | ours-fp32 | ours-int8 |
|---|---|---|---|---|
| fmt:dash | 96 | 100.0 | 100.0 | 100.0 |
| fmt:dot | 83 | 100.0 | 100.0 | 100.0 |
| fmt:initial | 48 | 100.0 | 100.0 | 100.0 |
| fmt:iso | 73 | 100.0 | 100.0 | 100.0 |
| fmt:last_first_caps | 146 | 76.0 | 98.6 | 68.5 |
| fmt:named | 67 | 100.0 | 100.0 | 100.0 |
| fmt:named_abbr | 58 | 100.0 | 100.0 | 100.0 |
| fmt:numeric_short | 80 | 100.0 | 100.0 | 100.0 |
| fmt:numeric_us | 80 | 100.0 | 100.0 | 100.0 |
| fmt:paren | 100 | 100.0 | 100.0 | 100.0 |
| fmt:partial | 35 | 100.0 | 100.0 | 100.0 |
| m:cue | 1216 | 97.9 | 99.9 | 96.9 |
| m:digit_spaced | 50 | 96.0 | 100.0 | 94.0 |
| m:lower | 14 | 78.6 | 100.0 | 85.7 |
| m:no_cue | 4163 | 97.4 | 99.6 | 97.1 |
| m:repeat | 1158 | 98.5 | 99.9 | 97.8 |
| m:single_name | 947 | 99.2 | 99.9 | 99.5 |
| planted | 5379 | 97.5 | 99.6 | 97.1 |
| repeat | 1045 | 98.4 | 99.8 | 97.6 |
| single_name | 947 | 99.2 | 99.9 | 99.5 |
| spoken | 211 | 97.6 | 100.0 | 97.2 |

## By category (recall %)

| | n | ours-int8pc | ours-fp32 | ours-int8 |
|---|---|---|---|---|
| ACCOUNT | 305 | 97.7 | 99.3 | 96.7 |
| ADDRESS | 163 | 100.0 | 100.0 | 100.0 |
| AGE | 125 | 86.4 | 98.4 | 80.8 |
| DATE | 426 | 100.0 | 100.0 | 100.0 |
| DEVICE | 166 | 98.8 | 100.0 | 100.0 |
| EMAIL | 146 | 97.9 | 100.0 | 98.6 |
| FAX | 136 | 100.0 | 100.0 | 100.0 |
| IP | 169 | 99.4 | 100.0 | 99.4 |
| LICENSE | 168 | 100.0 | 100.0 | 99.4 |
| LOCATION | 172 | 99.4 | 100.0 | 99.4 |
| MRN | 168 | 100.0 | 100.0 | 100.0 |
| NAME | 2146 | 98.0 | 99.9 | 97.6 |
| PHONE | 162 | 100.0 | 100.0 | 100.0 |
| PLAN | 140 | 98.6 | 100.0 | 97.1 |
| SSN | 167 | 99.4 | 100.0 | 99.4 |
| URL | 155 | 100.0 | 100.0 | 100.0 |
| VEHICLE | 312 | 82.7 | 96.2 | 80.4 |
| ZIP | 153 | 98.7 | 100.0 | 98.7 |
