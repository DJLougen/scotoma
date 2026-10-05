# clin_novel_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| openmed-t0.02 | 99.2 | 89.5 | 49/874 (5.6%) | 0.3% | 97.9 | 20.2 |
| rules+openmed-t0.02 | 99.5 | 91.2 | 29/874 (3.3%) | 0.5% | 97.8 | 20.7 |

## By domain (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| clinical | 7190 | 99.2 | 99.5 |

## By input mode (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| chat | 944 | 99.8 | 99.9 |
| dictated | 800 | 99.9 | 99.9 |
| email | 912 | 99.2 | 99.3 |
| form | 1032 | 98.8 | 99.2 |
| letter | 824 | 99.6 | 99.9 |
| narrative | 919 | 99.1 | 99.7 |
| notes | 811 | 98.0 | 99.0 |
| ocr | 948 | 99.3 | 99.5 |

## By difficulty tag (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| fmt:acct_dashed | 128 | 100.0 | 100.0 |
| fmt:acct_dot | 94 | 100.0 | 100.0 |
| fmt:acct_lbl | 94 | 100.0 | 100.0 |
| fmt:acct_spaced | 99 | 100.0 | 100.0 |
| fmt:age_year_old | 56 | 98.2 | 100.0 |
| fmt:age_yo | 69 | 97.1 | 100.0 |
| fmt:age_yrs | 70 | 100.0 | 100.0 |
| fmt:date_dot_eu | 130 | 100.0 | 100.0 |
| fmt:date_dot_us | 104 | 100.0 | 100.0 |
| fmt:date_mon_dot | 118 | 100.0 | 100.0 |
| fmt:date_ord_named | 128 | 100.0 | 100.0 |
| fmt:date_slash_iso | 132 | 100.0 | 100.0 |
| fmt:dev_seg | 64 | 100.0 | 100.0 |
| fmt:dev_sn | 67 | 100.0 | 100.0 |
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
| fmt:ipv6_mapped | 57 | 100.0 | 100.0 |
| fmt:last_first_caps | 181 | 87.8 | 90.1 |
| fmt:lic_hash | 53 | 100.0 | 100.0 |
| fmt:lic_md | 73 | 98.6 | 98.6 |
| fmt:lic_spaced | 61 | 100.0 | 100.0 |
| fmt:mrn_grouped | 48 | 97.9 | 97.9 |
| fmt:mrn_hash | 46 | 100.0 | 100.0 |
| fmt:mrn_lbl_space | 54 | 100.0 | 100.0 |
| fmt:mrn_mr_dash | 50 | 100.0 | 100.0 |
| fmt:ph_compact_paren | 42 | 100.0 | 100.0 |
| fmt:ph_ext | 50 | 100.0 | 100.0 |
| fmt:ph_intl_paren | 46 | 100.0 | 100.0 |
| fmt:ph_space4 | 35 | 97.1 | 100.0 |
| fmt:ph_tollfree | 32 | 71.9 | 100.0 |
| fmt:plan_alpha_mid | 48 | 100.0 | 100.0 |
| fmt:plan_alpha_pref | 66 | 100.0 | 100.0 |
| fmt:plan_digits11 | 50 | 100.0 | 100.0 |
| fmt:plan_grouped | 60 | 100.0 | 100.0 |
| fmt:ssn_dot | 61 | 100.0 | 100.0 |
| fmt:ssn_plain | 76 | 100.0 | 100.0 |
| fmt:ssn_space | 68 | 100.0 | 100.0 |
| fmt:url_http | 50 | 100.0 | 100.0 |
| fmt:url_path | 65 | 100.0 | 100.0 |
| fmt:url_query | 63 | 100.0 | 100.0 |
| fmt:url_www | 48 | 100.0 | 100.0 |
| fmt:veh_dash | 95 | 93.7 | 95.8 |
| fmt:veh_mix | 108 | 100.0 | 100.0 |
| fmt:veh_state | 132 | 99.2 | 99.2 |
| fmt:veh_vin_jt | 85 | 100.0 | 100.0 |
| fmt:zip4_dash | 68 | 100.0 | 100.0 |
| fmt:zip4_space | 77 | 100.0 | 100.0 |
| fmt:zip9_slash | 72 | 100.0 | 100.0 |
| m:cue | 1644 | 99.5 | 99.8 |
| m:no_cue | 5546 | 99.2 | 99.5 |
| m:repeat | 1465 | 99.0 | 99.5 |
| m:single_name | 1234 | 99.0 | 99.4 |
| novel_format | 3944 | 99.4 | 99.8 |
| planted | 7190 | 99.2 | 99.5 |
| repeat | 1224 | 99.3 | 99.6 |
| single_name | 1234 | 99.0 | 99.4 |

## By category (recall %)

| | n | openmed-t0.02 | rules+openmed-t0.02 |
|---|---|---|---|
| ACCOUNT | 415 | 100.0 | 100.0 |
| ADDRESS | 204 | 100.0 | 100.0 |
| AGE | 195 | 98.5 | 100.0 |
| DATE | 612 | 100.0 | 100.0 |
| DEVICE | 198 | 100.0 | 100.0 |
| EMAIL | 213 | 100.0 | 100.0 |
| FAX | 220 | 100.0 | 100.0 |
| IP | 209 | 100.0 | 100.0 |
| LICENSE | 187 | 99.5 | 99.5 |
| LOCATION | 201 | 100.0 | 100.0 |
| MRN | 198 | 99.5 | 99.5 |
| NAME | 2841 | 98.8 | 99.1 |
| PHONE | 205 | 95.1 | 100.0 |
| PLAN | 224 | 100.0 | 100.0 |
| SSN | 205 | 100.0 | 100.0 |
| URL | 226 | 100.0 | 100.0 |
| VEHICLE | 420 | 98.3 | 98.8 |
| ZIP | 217 | 100.0 | 100.0 |
