# clin2_novel_sealed_tagged.jsonl

Recall = identifier touched by a redaction. Leak docs = documents with at least one identifier left untouched.

Over-redaction = share of ordinary, non-identifier text that was redacted by mistake (a system that blacks out everything scores 100% recall).

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc |
|---|---|---|---|---|---|---|
| stanford-t0.1 | 96.6 | 82.9 | 216/860 (25.1%) | 0.3% | 99.1 | 27.6 |
| rules+stanford-t0.1 | 99.3 | 90.9 | 43/860 (5.0%) | 0.5% | 99.0 | 29.2 |

## By domain (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| clinical | 7097 | 96.6 | 99.3 |

## By input mode (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| chat | 945 | 95.6 | 98.4 |
| dictated | 881 | 96.9 | 99.4 |
| email | 758 | 96.3 | 99.5 |
| form | 886 | 97.1 | 99.8 |
| letter | 772 | 96.5 | 99.6 |
| narrative | 1030 | 97.3 | 99.6 |
| notes | 815 | 96.8 | 98.5 |
| ocr | 1010 | 96.4 | 99.5 |

## By difficulty tag (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| fmt:acct_dashed | 113 | 100.0 | 100.0 |
| fmt:acct_dot | 83 | 100.0 | 100.0 |
| fmt:acct_lbl | 97 | 100.0 | 100.0 |
| fmt:acct_spaced | 119 | 100.0 | 100.0 |
| fmt:age_year_old | 68 | 11.8 | 98.5 |
| fmt:age_yo | 49 | 0.0 | 98.0 |
| fmt:age_yrs | 67 | 3.0 | 97.0 |
| fmt:date_dot_eu | 106 | 100.0 | 100.0 |
| fmt:date_dot_us | 136 | 100.0 | 100.0 |
| fmt:date_mon_dot | 115 | 100.0 | 100.0 |
| fmt:date_ord_named | 122 | 100.0 | 100.0 |
| fmt:date_slash_iso | 121 | 100.0 | 100.0 |
| fmt:dev_seg | 66 | 98.5 | 98.5 |
| fmt:dev_sn | 77 | 100.0 | 100.0 |
| fmt:dev_udi | 70 | 100.0 | 100.0 |
| fmt:em_dash | 37 | 100.0 | 100.0 |
| fmt:em_dot_sfx | 47 | 100.0 | 100.0 |
| fmt:em_rev_dot | 57 | 94.7 | 100.0 |
| fmt:em_us_tld | 46 | 100.0 | 100.0 |
| fmt:fax_compact | 55 | 100.0 | 100.0 |
| fmt:fax_intl_paren | 66 | 100.0 | 100.0 |
| fmt:fax_lbl | 75 | 100.0 | 100.0 |
| fmt:initial | 94 | 100.0 | 100.0 |
| fmt:ipv4_port | 60 | 98.3 | 100.0 |
| fmt:ipv6_full | 50 | 100.0 | 100.0 |
| fmt:ipv6_link | 67 | 100.0 | 100.0 |
| fmt:ipv6_mapped | 50 | 100.0 | 100.0 |
| fmt:last_first_caps | 209 | 100.0 | 100.0 |
| fmt:lic_hash | 67 | 100.0 | 100.0 |
| fmt:lic_md | 64 | 100.0 | 100.0 |
| fmt:lic_spaced | 63 | 100.0 | 100.0 |
| fmt:mrn_grouped | 58 | 96.6 | 98.3 |
| fmt:mrn_hash | 48 | 100.0 | 100.0 |
| fmt:mrn_lbl_space | 46 | 100.0 | 100.0 |
| fmt:mrn_mr_dash | 39 | 100.0 | 100.0 |
| fmt:ph_compact_paren | 41 | 100.0 | 100.0 |
| fmt:ph_ext | 43 | 100.0 | 100.0 |
| fmt:ph_intl_paren | 31 | 100.0 | 100.0 |
| fmt:ph_space4 | 48 | 100.0 | 100.0 |
| fmt:ph_tollfree | 38 | 100.0 | 100.0 |
| fmt:plan_alpha_mid | 42 | 100.0 | 100.0 |
| fmt:plan_alpha_pref | 50 | 100.0 | 100.0 |
| fmt:plan_digits11 | 57 | 100.0 | 100.0 |
| fmt:plan_grouped | 47 | 100.0 | 100.0 |
| fmt:ssn_dot | 68 | 97.1 | 97.1 |
| fmt:ssn_plain | 62 | 100.0 | 100.0 |
| fmt:ssn_space | 79 | 100.0 | 100.0 |
| fmt:url_http | 49 | 100.0 | 100.0 |
| fmt:url_path | 53 | 100.0 | 100.0 |
| fmt:url_query | 44 | 100.0 | 100.0 |
| fmt:url_www | 62 | 100.0 | 100.0 |
| fmt:veh_dash | 101 | 85.1 | 87.1 |
| fmt:veh_mix | 99 | 97.0 | 97.0 |
| fmt:veh_state | 101 | 95.0 | 96.0 |
| fmt:veh_vin_jt | 102 | 100.0 | 100.0 |
| fmt:zip4_dash | 67 | 100.0 | 100.0 |
| fmt:zip4_space | 74 | 100.0 | 100.0 |
| fmt:zip9_slash | 68 | 100.0 | 100.0 |
| m:cue | 1674 | 94.6 | 99.6 |
| m:no_cue | 5423 | 97.3 | 99.2 |
| m:repeat | 1487 | 98.3 | 99.0 |
| m:single_name | 1229 | 98.1 | 98.9 |
| novel_format | 3830 | 94.6 | 99.3 |
| planted | 7097 | 96.6 | 99.3 |
| repeat | 1243 | 97.7 | 98.6 |
| single_name | 1229 | 98.1 | 98.9 |

## By category (recall %)

| | n | stanford-t0.1 | rules+stanford-t0.1 |
|---|---|---|---|
| ACCOUNT | 412 | 100.0 | 100.0 |
| ADDRESS | 205 | 98.0 | 99.5 |
| AGE | 184 | 5.4 | 97.8 |
| DATE | 600 | 100.0 | 100.0 |
| DEVICE | 213 | 99.5 | 99.5 |
| EMAIL | 187 | 98.4 | 100.0 |
| FAX | 196 | 100.0 | 100.0 |
| IP | 227 | 99.6 | 100.0 |
| LICENSE | 194 | 100.0 | 100.0 |
| LOCATION | 203 | 96.6 | 96.6 |
| MRN | 191 | 99.0 | 99.5 |
| NAME | 2859 | 99.2 | 99.5 |
| PHONE | 201 | 100.0 | 100.0 |
| PLAN | 196 | 100.0 | 100.0 |
| SSN | 209 | 99.0 | 99.0 |
| URL | 208 | 100.0 | 100.0 |
| VEHICLE | 403 | 94.3 | 95.0 |
| ZIP | 209 | 100.0 | 100.0 |
