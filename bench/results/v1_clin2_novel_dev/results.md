# clin2_novel_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules+ours-v1 | 100.0 | 94.8 | 2/870 (0.2%) | 0.2% | 99.6 | 19.9 |
| ours-v1 | 99.6 | 93.2 | 23/870 (2.6%) | 0.0% | 99.6 | 19.4 |

## By domain (recall %)

| | n | rules+ours-v1 | ours-v1 |
|---|---|---|---|
| clinical | 7377 | 100.0 | 99.6 |

## By input mode (recall %)

| | n | rules+ours-v1 | ours-v1 |
|---|---|---|---|
| chat | 811 | 100.0 | 100.0 |
| dictated | 861 | 100.0 | 99.9 |
| email | 904 | 100.0 | 99.7 |
| form | 956 | 99.9 | 99.7 |
| letter | 927 | 100.0 | 99.7 |
| narrative | 941 | 100.0 | 99.9 |
| notes | 1098 | 99.9 | 99.2 |
| ocr | 879 | 100.0 | 99.3 |

## By difficulty tag (recall %)

| | n | rules+ours-v1 | ours-v1 |
|---|---|---|---|
| fmt:acct_dashed | 115 | 100.0 | 100.0 |
| fmt:acct_dot | 103 | 100.0 | 100.0 |
| fmt:acct_lbl | 96 | 100.0 | 100.0 |
| fmt:acct_spaced | 108 | 100.0 | 100.0 |
| fmt:age_year_old | 78 | 100.0 | 100.0 |
| fmt:age_yo | 63 | 100.0 | 100.0 |
| fmt:age_yrs | 58 | 100.0 | 100.0 |
| fmt:date_dot_eu | 121 | 100.0 | 100.0 |
| fmt:date_dot_us | 134 | 100.0 | 100.0 |
| fmt:date_mon_dot | 133 | 100.0 | 100.0 |
| fmt:date_ord_named | 132 | 100.0 | 100.0 |
| fmt:date_slash_iso | 140 | 100.0 | 100.0 |
| fmt:dev_seg | 67 | 100.0 | 100.0 |
| fmt:dev_sn | 83 | 100.0 | 100.0 |
| fmt:dev_udi | 91 | 100.0 | 100.0 |
| fmt:em_dash | 41 | 100.0 | 100.0 |
| fmt:em_dot_sfx | 66 | 100.0 | 100.0 |
| fmt:em_rev_dot | 41 | 100.0 | 100.0 |
| fmt:em_us_tld | 65 | 100.0 | 100.0 |
| fmt:fax_compact | 59 | 100.0 | 100.0 |
| fmt:fax_intl_paren | 73 | 100.0 | 100.0 |
| fmt:fax_lbl | 96 | 100.0 | 100.0 |
| fmt:initial | 82 | 100.0 | 100.0 |
| fmt:ipv4_port | 57 | 100.0 | 100.0 |
| fmt:ipv6_full | 62 | 100.0 | 100.0 |
| fmt:ipv6_link | 50 | 100.0 | 100.0 |
| fmt:ipv6_mapped | 52 | 100.0 | 100.0 |
| fmt:last_first_caps | 195 | 100.0 | 99.5 |
| fmt:lic_hash | 71 | 100.0 | 100.0 |
| fmt:lic_md | 81 | 100.0 | 100.0 |
| fmt:lic_spaced | 65 | 100.0 | 100.0 |
| fmt:mrn_grouped | 69 | 100.0 | 100.0 |
| fmt:mrn_hash | 54 | 100.0 | 100.0 |
| fmt:mrn_lbl_space | 47 | 100.0 | 100.0 |
| fmt:mrn_mr_dash | 50 | 100.0 | 100.0 |
| fmt:ph_compact_paren | 43 | 100.0 | 100.0 |
| fmt:ph_ext | 43 | 100.0 | 100.0 |
| fmt:ph_intl_paren | 46 | 100.0 | 100.0 |
| fmt:ph_space4 | 49 | 100.0 | 100.0 |
| fmt:ph_tollfree | 44 | 100.0 | 63.6 |
| fmt:plan_alpha_mid | 59 | 100.0 | 100.0 |
| fmt:plan_alpha_pref | 55 | 100.0 | 100.0 |
| fmt:plan_digits11 | 50 | 100.0 | 100.0 |
| fmt:plan_grouped | 60 | 100.0 | 100.0 |
| fmt:ssn_dot | 81 | 100.0 | 100.0 |
| fmt:ssn_plain | 68 | 100.0 | 100.0 |
| fmt:ssn_space | 75 | 100.0 | 100.0 |
| fmt:url_http | 46 | 100.0 | 100.0 |
| fmt:url_path | 43 | 100.0 | 100.0 |
| fmt:url_query | 65 | 100.0 | 100.0 |
| fmt:url_www | 67 | 100.0 | 92.5 |
| fmt:veh_dash | 104 | 100.0 | 100.0 |
| fmt:veh_mix | 109 | 100.0 | 100.0 |
| fmt:veh_state | 94 | 100.0 | 100.0 |
| fmt:veh_vin_jt | 115 | 100.0 | 100.0 |
| fmt:zip4_dash | 78 | 100.0 | 100.0 |
| fmt:zip4_space | 66 | 100.0 | 100.0 |
| fmt:zip9_slash | 66 | 100.0 | 100.0 |
| m:cue | 1677 | 100.0 | 99.7 |
| m:no_cue | 5700 | 100.0 | 99.6 |
| m:repeat | 1464 | 100.0 | 99.6 |
| m:single_name | 1197 | 99.9 | 99.7 |
| novel_format | 4147 | 100.0 | 99.5 |
| planted | 7377 | 100.0 | 99.6 |
| repeat | 1336 | 100.0 | 99.4 |
| single_name | 1197 | 99.9 | 99.7 |

## By category (recall %)

| | n | rules+ours-v1 | ours-v1 |
|---|---|---|---|
| ACCOUNT | 422 | 100.0 | 100.0 |
| ADDRESS | 222 | 100.0 | 100.0 |
| AGE | 199 | 100.0 | 100.0 |
| DATE | 660 | 100.0 | 100.0 |
| DEVICE | 241 | 100.0 | 100.0 |
| EMAIL | 213 | 100.0 | 100.0 |
| FAX | 228 | 100.0 | 100.0 |
| IP | 221 | 100.0 | 100.0 |
| LICENSE | 217 | 100.0 | 100.0 |
| LOCATION | 219 | 99.5 | 99.5 |
| MRN | 220 | 100.0 | 100.0 |
| NAME | 2789 | 100.0 | 99.9 |
| PHONE | 225 | 100.0 | 92.9 |
| PLAN | 224 | 100.0 | 100.0 |
| SSN | 224 | 100.0 | 100.0 |
| URL | 221 | 100.0 | 97.7 |
| VEHICLE | 422 | 100.0 | 100.0 |
| ZIP | 210 | 100.0 | 100.0 |
