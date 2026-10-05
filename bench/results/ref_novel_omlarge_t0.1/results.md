# clin_novel_dev_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| rules+openmed-large-t0.1 | 100.0 | 93.2 | 2/844 (0.2%) | 0.5% | 97.4 | 247.7 |

## By domain (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| clinical | 7130 | 100.0 |

## By input mode (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| chat | 869 | 100.0 |
| dictated | 886 | 100.0 |
| email | 939 | 99.9 |
| form | 893 | 100.0 |
| letter | 827 | 100.0 |
| narrative | 931 | 99.8 |
| notes | 880 | 100.0 |
| ocr | 905 | 100.0 |

## By difficulty tag (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| fmt:acct_dashed | 109 | 100.0 |
| fmt:acct_dot | 99 | 100.0 |
| fmt:acct_lbl | 100 | 100.0 |
| fmt:acct_spaced | 98 | 100.0 |
| fmt:age_year_old | 51 | 100.0 |
| fmt:age_yo | 55 | 100.0 |
| fmt:age_yrs | 75 | 100.0 |
| fmt:date_dot_eu | 125 | 100.0 |
| fmt:date_dot_us | 113 | 100.0 |
| fmt:date_mon_dot | 133 | 100.0 |
| fmt:date_ord_named | 110 | 100.0 |
| fmt:date_slash_iso | 88 | 100.0 |
| fmt:dev_seg | 76 | 100.0 |
| fmt:dev_sn | 80 | 100.0 |
| fmt:dev_udi | 62 | 100.0 |
| fmt:em_dash | 54 | 100.0 |
| fmt:em_dot_sfx | 53 | 100.0 |
| fmt:em_rev_dot | 43 | 100.0 |
| fmt:em_us_tld | 51 | 100.0 |
| fmt:fax_compact | 56 | 100.0 |
| fmt:fax_intl_paren | 51 | 100.0 |
| fmt:fax_lbl | 73 | 100.0 |
| fmt:initial | 73 | 100.0 |
| fmt:ipv4_port | 49 | 100.0 |
| fmt:ipv6_full | 46 | 100.0 |
| fmt:ipv6_link | 48 | 100.0 |
| fmt:ipv6_mapped | 70 | 100.0 |
| fmt:last_first_caps | 194 | 99.0 |
| fmt:lic_hash | 65 | 100.0 |
| fmt:lic_md | 91 | 100.0 |
| fmt:lic_spaced | 74 | 100.0 |
| fmt:mrn_grouped | 63 | 100.0 |
| fmt:mrn_hash | 58 | 100.0 |
| fmt:mrn_lbl_space | 56 | 100.0 |
| fmt:mrn_mr_dash | 46 | 100.0 |
| fmt:ph_compact_paren | 34 | 100.0 |
| fmt:ph_ext | 37 | 100.0 |
| fmt:ph_intl_paren | 45 | 100.0 |
| fmt:ph_space4 | 52 | 100.0 |
| fmt:ph_tollfree | 48 | 100.0 |
| fmt:plan_alpha_mid | 51 | 100.0 |
| fmt:plan_alpha_pref | 49 | 100.0 |
| fmt:plan_digits11 | 48 | 100.0 |
| fmt:plan_grouped | 50 | 100.0 |
| fmt:ssn_dot | 84 | 100.0 |
| fmt:ssn_plain | 76 | 100.0 |
| fmt:ssn_space | 64 | 100.0 |
| fmt:url_http | 51 | 100.0 |
| fmt:url_path | 50 | 100.0 |
| fmt:url_query | 52 | 100.0 |
| fmt:url_www | 57 | 100.0 |
| fmt:veh_dash | 93 | 98.9 |
| fmt:veh_mix | 120 | 100.0 |
| fmt:veh_state | 97 | 100.0 |
| fmt:veh_vin_jt | 100 | 100.0 |
| fmt:zip4_dash | 63 | 100.0 |
| fmt:zip4_space | 63 | 100.0 |
| fmt:zip9_slash | 75 | 100.0 |
| m:cue | 1662 | 100.0 |
| m:no_cue | 5468 | 99.9 |
| m:repeat | 1511 | 99.9 |
| m:single_name | 1237 | 100.0 |
| novel_format | 3880 | 100.0 |
| planted | 7130 | 100.0 |
| repeat | 1360 | 100.0 |
| single_name | 1237 | 100.0 |

## By category (recall %)

| | n | rules+openmed-large-t0.1 |
|---|---|---|
| ACCOUNT | 406 | 100.0 |
| ADDRESS | 220 | 100.0 |
| AGE | 181 | 100.0 |
| DATE | 569 | 100.0 |
| DEVICE | 218 | 100.0 |
| EMAIL | 201 | 100.0 |
| FAX | 180 | 100.0 |
| IP | 213 | 100.0 |
| LICENSE | 230 | 100.0 |
| LOCATION | 234 | 100.0 |
| MRN | 223 | 100.0 |
| NAME | 2796 | 99.9 |
| PHONE | 216 | 100.0 |
| PLAN | 198 | 100.0 |
| SSN | 224 | 100.0 |
| URL | 210 | 100.0 |
| VEHICLE | 410 | 99.8 |
| ZIP | 201 | 100.0 |
