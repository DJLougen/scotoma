# cd_rest.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| ours-int8pc | 99.7 | 97.9 | 16/644 (2.5%) | 0.1% | 99.5 | 21.9 |
| ours-fp32 | 99.9 | 97.6 | 3/644 (0.5%) | 0.3% | 98.1 | 41.8 |
| ours-int8 | 99.5 | 97.6 | 23/644 (3.6%) | 0.1% | 99.6 | 22.4 |

## By domain (recall %)

| | n | ours-int8pc | ours-fp32 | ours-int8 |
|---|---|---|---|---|
| clinical | 5379 | 99.7 | 99.9 | 99.5 |

## By input mode (recall %)

| | n | ours-int8pc | ours-fp32 | ours-int8 |
|---|---|---|---|---|
| chat | 673 | 99.9 | 100.0 | 99.9 |
| dictated | 602 | 100.0 | 100.0 | 100.0 |
| email | 757 | 99.1 | 99.9 | 98.7 |
| form | 634 | 99.8 | 100.0 | 99.7 |
| letter | 652 | 100.0 | 100.0 | 99.7 |
| narrative | 790 | 99.9 | 99.7 | 99.6 |
| notes | 592 | 99.3 | 100.0 | 99.2 |
| ocr | 679 | 99.7 | 100.0 | 99.7 |

## By difficulty tag (recall %)

| | n | ours-int8pc | ours-fp32 | ours-int8 |
|---|---|---|---|---|
| fmt:dash | 96 | 100.0 | 100.0 | 100.0 |
| fmt:dot | 83 | 100.0 | 100.0 | 100.0 |
| fmt:initial | 48 | 100.0 | 100.0 | 100.0 |
| fmt:iso | 73 | 100.0 | 100.0 | 100.0 |
| fmt:last_first_caps | 146 | 96.6 | 98.6 | 92.5 |
| fmt:named | 67 | 100.0 | 100.0 | 100.0 |
| fmt:named_abbr | 58 | 100.0 | 100.0 | 100.0 |
| fmt:numeric_short | 80 | 100.0 | 100.0 | 100.0 |
| fmt:numeric_us | 80 | 100.0 | 100.0 | 100.0 |
| fmt:paren | 100 | 100.0 | 100.0 | 100.0 |
| fmt:partial | 35 | 100.0 | 100.0 | 100.0 |
| m:cue | 1216 | 99.8 | 100.0 | 99.8 |
| m:digit_spaced | 50 | 100.0 | 100.0 | 100.0 |
| m:lower | 14 | 92.9 | 100.0 | 92.9 |
| m:no_cue | 4163 | 99.7 | 99.9 | 99.4 |
| m:repeat | 1158 | 99.7 | 100.0 | 99.7 |
| m:single_name | 947 | 99.8 | 100.0 | 99.9 |
| planted | 5379 | 99.7 | 99.9 | 99.5 |
| repeat | 1045 | 99.8 | 100.0 | 99.7 |
| single_name | 947 | 99.8 | 100.0 | 99.9 |
| spoken | 211 | 99.5 | 100.0 | 99.5 |

## By category (recall %)

| | n | ours-int8pc | ours-fp32 | ours-int8 |
|---|---|---|---|---|
| ACCOUNT | 305 | 100.0 | 100.0 | 100.0 |
| ADDRESS | 163 | 100.0 | 100.0 | 100.0 |
| AGE | 125 | 98.4 | 100.0 | 97.6 |
| DATE | 426 | 100.0 | 100.0 | 100.0 |
| DEVICE | 166 | 100.0 | 100.0 | 100.0 |
| EMAIL | 146 | 99.3 | 100.0 | 99.3 |
| FAX | 136 | 100.0 | 100.0 | 100.0 |
| IP | 169 | 100.0 | 100.0 | 100.0 |
| LICENSE | 168 | 100.0 | 100.0 | 100.0 |
| LOCATION | 172 | 100.0 | 100.0 | 100.0 |
| MRN | 168 | 100.0 | 100.0 | 100.0 |
| NAME | 2146 | 99.7 | 99.9 | 99.4 |
| PHONE | 162 | 100.0 | 100.0 | 100.0 |
| PLAN | 140 | 100.0 | 100.0 | 100.0 |
| SSN | 167 | 100.0 | 100.0 | 100.0 |
| URL | 155 | 100.0 | 100.0 | 100.0 |
| VEHICLE | 312 | 98.1 | 99.7 | 97.1 |
| ZIP | 153 | 100.0 | 100.0 | 100.0 |
