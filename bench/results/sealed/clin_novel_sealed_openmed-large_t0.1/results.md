# clin_novel_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| openmed-large-t0.1 | 99.7 | 91.7 | 20/874 (2.3%) | 0.4% | 97.5 | 249.5 |
| rules+openmed-large-t0.1 | 99.9 | 93.0 | 4/874 (0.5%) | 0.5% | 97.5 | 245.3 |

## By domain (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| clinical | 7190 | 99.7 | 99.9 |

## By input mode (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| chat | 944 | 99.7 | 99.8 |
| dictated | 800 | 99.8 | 100.0 |
| email | 912 | 100.0 | 100.0 |
| form | 1032 | 99.9 | 100.0 |
| letter | 824 | 99.8 | 100.0 |
| narrative | 919 | 99.3 | 100.0 |
| notes | 811 | 99.1 | 99.6 |
| ocr | 948 | 99.9 | 100.0 |

## By difficulty tag (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| fmt:acct_dashed | 128 | 100.0 | 100.0 |
| fmt:acct_dot | 94 | 100.0 | 100.0 |
| fmt:acct_lbl | 94 | 100.0 | 100.0 |
| fmt:acct_spaced | 99 | 100.0 | 100.0 |
| fmt:age_year_old | 56 | 100.0 | 100.0 |
| fmt:age_yo | 69 | 100.0 | 100.0 |
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
| fmt:ph_tollfree | 32 | 50.0 | 100.0 |
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
| fmt:url_www | 48 | 97.9 | 100.0 |
| fmt:veh_dash | 95 | 97.9 | 97.9 |
| fmt:veh_mix | 108 | 100.0 | 100.0 |
| fmt:veh_state | 132 | 100.0 | 100.0 |
| fmt:veh_vin_jt | 85 | 100.0 | 100.0 |
| fmt:zip4_dash | 68 | 100.0 | 100.0 |
| fmt:zip4_space | 77 | 100.0 | 100.0 |
| fmt:zip9_slash | 72 | 100.0 | 100.0 |
| m:cue | 1644 | 99.9 | 100.0 |
| m:no_cue | 5546 | 99.6 | 99.9 |
| m:repeat | 1465 | 99.8 | 99.8 |
| m:single_name | 1234 | 99.8 | 99.8 |
| novel_format | 3944 | 99.5 | 99.9 |
| planted | 7190 | 99.7 | 99.9 |
| repeat | 1224 | 99.8 | 99.8 |
| single_name | 1234 | 99.8 | 99.8 |

## By category (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| ACCOUNT | 415 | 100.0 | 100.0 |
| ADDRESS | 204 | 100.0 | 100.0 |
| AGE | 195 | 100.0 | 100.0 |
| DATE | 612 | 100.0 | 100.0 |
| DEVICE | 198 | 100.0 | 100.0 |
| EMAIL | 213 | 100.0 | 100.0 |
| FAX | 220 | 100.0 | 100.0 |
| IP | 209 | 100.0 | 100.0 |
| LICENSE | 187 | 100.0 | 100.0 |
| LOCATION | 201 | 100.0 | 100.0 |
| MRN | 198 | 100.0 | 100.0 |
| NAME | 2841 | 99.9 | 99.9 |
| PHONE | 205 | 92.2 | 100.0 |
| PLAN | 224 | 100.0 | 100.0 |
| SSN | 205 | 100.0 | 100.0 |
| URL | 226 | 99.6 | 100.0 |
| VEHICLE | 420 | 99.5 | 99.5 |
| ZIP | 217 | 100.0 | 100.0 |
