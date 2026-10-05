# clin_novel_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| stanford-t0.1 | 96.5 | 82.4 | 219/874 (25.1%) | 0.4% | 98.5 | 27.0 |
| rules+stanford-t0.1 | 99.3 | 90.8 | 38/874 (4.3%) | 0.6% | 98.5 | 29.8 |

## By domain (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| clinical | 7190 | 96.5 | 99.3 |

## By input mode (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| chat | 944 | 96.4 | 98.9 |
| dictated | 800 | 97.0 | 99.4 |
| email | 912 | 95.9 | 99.1 |
| form | 1032 | 96.6 | 99.6 |
| letter | 824 | 97.2 | 100.0 |
| narrative | 919 | 96.3 | 99.5 |
| notes | 811 | 94.3 | 98.0 |
| ocr | 948 | 98.2 | 99.7 |

## By difficulty tag (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| fmt:acct_dashed | 128 | 100.0 | 100.0 |
| fmt:acct_dot | 94 | 100.0 | 100.0 |
| fmt:acct_lbl | 94 | 100.0 | 100.0 |
| fmt:acct_spaced | 99 | 100.0 | 100.0 |
| fmt:age_year_old | 56 | 5.4 | 100.0 |
| fmt:age_yo | 69 | 0.0 | 100.0 |
| fmt:age_yrs | 70 | 1.4 | 95.7 |
| fmt:date_dot_eu | 130 | 100.0 | 100.0 |
| fmt:date_dot_us | 104 | 100.0 | 100.0 |
| fmt:date_mon_dot | 118 | 100.0 | 100.0 |
| fmt:date_ord_named | 128 | 100.0 | 100.0 |
| fmt:date_slash_iso | 132 | 100.0 | 100.0 |
| fmt:dev_seg | 64 | 100.0 | 100.0 |
| fmt:dev_sn | 67 | 92.5 | 92.5 |
| fmt:dev_udi | 67 | 100.0 | 100.0 |
| fmt:em_dash | 60 | 100.0 | 100.0 |
| fmt:em_dot_sfx | 57 | 100.0 | 100.0 |
| fmt:em_rev_dot | 46 | 100.0 | 100.0 |
| fmt:em_us_tld | 50 | 100.0 | 100.0 |
| fmt:fax_compact | 55 | 100.0 | 100.0 |
| fmt:fax_intl_paren | 86 | 100.0 | 100.0 |
| fmt:fax_lbl | 79 | 100.0 | 100.0 |
| fmt:initial | 88 | 100.0 | 100.0 |
| fmt:ipv4_port | 39 | 100.0 | 100.0 |
| fmt:ipv6_full | 60 | 100.0 | 100.0 |
| fmt:ipv6_link | 53 | 100.0 | 100.0 |
| fmt:ipv6_mapped | 57 | 96.5 | 100.0 |
| fmt:last_first_caps | 181 | 100.0 | 100.0 |
| fmt:lic_hash | 53 | 100.0 | 100.0 |
| fmt:lic_md | 73 | 100.0 | 100.0 |
| fmt:lic_spaced | 61 | 100.0 | 100.0 |
| fmt:mrn_grouped | 48 | 100.0 | 100.0 |
| fmt:mrn_hash | 46 | 100.0 | 100.0 |
| fmt:mrn_lbl_space | 54 | 100.0 | 100.0 |
| fmt:mrn_mr_dash | 50 | 100.0 | 100.0 |
| fmt:ph_compact_paren | 42 | 100.0 | 100.0 |
| fmt:ph_ext | 50 | 100.0 | 100.0 |
| fmt:ph_intl_paren | 46 | 100.0 | 100.0 |
| fmt:ph_space4 | 35 | 100.0 | 100.0 |
| fmt:ph_tollfree | 32 | 100.0 | 100.0 |
| fmt:plan_alpha_mid | 48 | 100.0 | 100.0 |
| fmt:plan_alpha_pref | 66 | 100.0 | 100.0 |
| fmt:plan_digits11 | 50 | 100.0 | 100.0 |
| fmt:plan_grouped | 60 | 98.3 | 98.3 |
| fmt:ssn_dot | 61 | 100.0 | 100.0 |
| fmt:ssn_plain | 76 | 100.0 | 100.0 |
| fmt:ssn_space | 68 | 98.5 | 98.5 |
| fmt:url_http | 50 | 100.0 | 100.0 |
| fmt:url_path | 65 | 100.0 | 100.0 |
| fmt:url_query | 63 | 100.0 | 100.0 |
| fmt:url_www | 48 | 100.0 | 100.0 |
| fmt:veh_dash | 95 | 91.6 | 93.7 |
| fmt:veh_mix | 108 | 95.4 | 95.4 |
| fmt:veh_state | 132 | 93.9 | 97.0 |
| fmt:veh_vin_jt | 85 | 100.0 | 100.0 |
| fmt:zip4_dash | 68 | 100.0 | 100.0 |
| fmt:zip4_space | 77 | 97.4 | 97.4 |
| fmt:zip9_slash | 72 | 98.6 | 98.6 |
| m:cue | 1644 | 93.0 | 99.6 |
| m:no_cue | 5546 | 97.6 | 99.2 |
| m:repeat | 1465 | 98.6 | 99.0 |
| m:single_name | 1234 | 98.6 | 98.9 |
| novel_format | 3944 | 94.3 | 99.3 |
| planted | 7190 | 96.5 | 99.3 |
| repeat | 1224 | 97.8 | 98.6 |
| single_name | 1234 | 98.6 | 98.9 |

## By category (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| ACCOUNT | 415 | 100.0 | 100.0 |
| ADDRESS | 204 | 99.5 | 99.5 |
| AGE | 195 | 2.1 | 98.5 |
| DATE | 612 | 100.0 | 100.0 |
| DEVICE | 198 | 97.5 | 97.5 |
| EMAIL | 213 | 100.0 | 100.0 |
| FAX | 220 | 100.0 | 100.0 |
| IP | 209 | 99.0 | 100.0 |
| LICENSE | 187 | 100.0 | 100.0 |
| LOCATION | 201 | 98.5 | 98.5 |
| MRN | 198 | 100.0 | 100.0 |
| NAME | 2841 | 99.2 | 99.3 |
| PHONE | 205 | 100.0 | 100.0 |
| PLAN | 224 | 99.6 | 99.6 |
| SSN | 205 | 99.5 | 99.5 |
| URL | 226 | 100.0 | 100.0 |
| VEHICLE | 420 | 95.0 | 96.4 |
| ZIP | 217 | 98.6 | 98.6 |
