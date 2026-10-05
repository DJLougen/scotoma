# clin2_novel_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| openmed-large-t0.1 | 99.5 | 91.6 | 28/860 (3.3%) | 0.3% | 97.6 | 254.8 |
| rules+openmed-large-t0.1 | 99.9 | 95.4 | 5/860 (0.6%) | 0.5% | 97.5 | 249.3 |

## By domain (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| clinical | 7097 | 99.5 | 99.9 |

## By input mode (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| chat | 945 | 99.7 | 99.8 |
| dictated | 881 | 99.7 | 100.0 |
| email | 758 | 99.9 | 100.0 |
| form | 886 | 99.9 | 100.0 |
| letter | 772 | 99.6 | 100.0 |
| narrative | 1030 | 98.9 | 99.7 |
| notes | 815 | 99.3 | 99.9 |
| ocr | 1010 | 99.6 | 99.8 |

## By difficulty tag (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| fmt:acct_dashed | 113 | 100.0 | 100.0 |
| fmt:acct_dot | 83 | 100.0 | 100.0 |
| fmt:acct_lbl | 97 | 100.0 | 100.0 |
| fmt:acct_spaced | 119 | 100.0 | 100.0 |
| fmt:age_year_old | 68 | 100.0 | 100.0 |
| fmt:age_yo | 49 | 100.0 | 100.0 |
| fmt:age_yrs | 67 | 100.0 | 100.0 |
| fmt:date_dot_eu | 106 | 100.0 | 100.0 |
| fmt:date_dot_us | 136 | 100.0 | 100.0 |
| fmt:date_mon_dot | 115 | 100.0 | 100.0 |
| fmt:date_ord_named | 122 | 100.0 | 100.0 |
| fmt:date_slash_iso | 121 | 100.0 | 100.0 |
| fmt:dev_seg | 66 | 100.0 | 100.0 |
| fmt:dev_sn | 77 | 100.0 | 100.0 |
| fmt:dev_udi | 70 | 100.0 | 100.0 |
| fmt:em_dash | 37 | 100.0 | 100.0 |
| fmt:em_dot_sfx | 47 | 100.0 | 100.0 |
| fmt:em_rev_dot | 57 | 100.0 | 100.0 |
| fmt:em_us_tld | 46 | 100.0 | 100.0 |
| fmt:fax_compact | 55 | 100.0 | 100.0 |
| fmt:fax_intl_paren | 66 | 100.0 | 100.0 |
| fmt:fax_lbl | 75 | 100.0 | 100.0 |
| fmt:initial | 94 | 100.0 | 100.0 |
| fmt:ipv4_port | 60 | 100.0 | 100.0 |
| fmt:ipv6_full | 50 | 100.0 | 100.0 |
| fmt:ipv6_link | 67 | 100.0 | 100.0 |
| fmt:ipv6_mapped | 50 | 100.0 | 100.0 |
| fmt:last_first_caps | 209 | 100.0 | 100.0 |
| fmt:lic_hash | 67 | 100.0 | 100.0 |
| fmt:lic_md | 64 | 100.0 | 100.0 |
| fmt:lic_spaced | 63 | 100.0 | 100.0 |
| fmt:mrn_grouped | 58 | 100.0 | 100.0 |
| fmt:mrn_hash | 48 | 100.0 | 100.0 |
| fmt:mrn_lbl_space | 46 | 100.0 | 100.0 |
| fmt:mrn_mr_dash | 39 | 100.0 | 100.0 |
| fmt:ph_compact_paren | 41 | 100.0 | 100.0 |
| fmt:ph_ext | 43 | 100.0 | 100.0 |
| fmt:ph_intl_paren | 31 | 100.0 | 100.0 |
| fmt:ph_space4 | 48 | 95.8 | 100.0 |
| fmt:ph_tollfree | 38 | 50.0 | 100.0 |
| fmt:plan_alpha_mid | 42 | 100.0 | 100.0 |
| fmt:plan_alpha_pref | 50 | 100.0 | 100.0 |
| fmt:plan_digits11 | 57 | 100.0 | 100.0 |
| fmt:plan_grouped | 47 | 100.0 | 100.0 |
| fmt:ssn_dot | 68 | 100.0 | 100.0 |
| fmt:ssn_plain | 62 | 100.0 | 100.0 |
| fmt:ssn_space | 79 | 100.0 | 100.0 |
| fmt:url_http | 49 | 100.0 | 100.0 |
| fmt:url_path | 53 | 100.0 | 100.0 |
| fmt:url_query | 44 | 100.0 | 100.0 |
| fmt:url_www | 62 | 95.2 | 100.0 |
| fmt:veh_dash | 101 | 100.0 | 100.0 |
| fmt:veh_mix | 99 | 100.0 | 100.0 |
| fmt:veh_state | 101 | 100.0 | 100.0 |
| fmt:veh_vin_jt | 102 | 100.0 | 100.0 |
| fmt:zip4_dash | 67 | 100.0 | 100.0 |
| fmt:zip4_space | 74 | 100.0 | 100.0 |
| fmt:zip9_slash | 68 | 100.0 | 100.0 |
| m:cue | 1674 | 99.9 | 100.0 |
| m:no_cue | 5423 | 99.4 | 99.9 |
| m:repeat | 1487 | 99.7 | 99.8 |
| m:single_name | 1229 | 99.4 | 99.4 |
| novel_format | 3830 | 99.4 | 100.0 |
| planted | 7097 | 99.5 | 99.9 |
| repeat | 1243 | 99.7 | 99.8 |
| single_name | 1229 | 99.4 | 99.4 |

## By category (recall %)

| | n | openmed-large-t0.1 | rules+openmed-large-t0.1 |
|---|---|---|---|
| ACCOUNT | 412 | 100.0 | 100.0 |
| ADDRESS | 205 | 100.0 | 100.0 |
| AGE | 184 | 100.0 | 100.0 |
| DATE | 600 | 100.0 | 100.0 |
| DEVICE | 213 | 100.0 | 100.0 |
| EMAIL | 187 | 100.0 | 100.0 |
| FAX | 196 | 100.0 | 100.0 |
| IP | 227 | 100.0 | 100.0 |
| LICENSE | 194 | 100.0 | 100.0 |
| LOCATION | 203 | 100.0 | 100.0 |
| MRN | 191 | 100.0 | 100.0 |
| NAME | 2859 | 99.7 | 99.7 |
| PHONE | 201 | 89.6 | 100.0 |
| PLAN | 196 | 100.0 | 100.0 |
| SSN | 209 | 100.0 | 100.0 |
| URL | 208 | 98.6 | 100.0 |
| VEHICLE | 403 | 100.0 | 100.0 |
| ZIP | 209 | 100.0 | 100.0 |
