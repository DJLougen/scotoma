# Sealed evaluation 3: results (2026-10-05)

Protocol: `SEALED3_PREREG.md`, committed before any clin3 scoring. "Ours" (`v2-small`, sha256 33be2438…) was chosen by
the pre-registered dev rule. Every run, restart and machine move is in `SEALED3_LOG.md`. Each set was scored once.
Raw outputs: `sealed3/` (`clin3_test_ours/`, `clin3_test_oml/`, `clin3_novel_all/`, `pre/`). Merged item matrices:
`sealed3/clin3_test_all_responses.csv` and `sealed3/clin3_novel_all_responses.csv`.

## Primary hypothesis (one pre-registered test)

On `clin3_test` (7,108 fresh notes, training-family identifier formats), **rules + ours** leaks fewer notes than
**rules + OpenMed-PII-SuperClinical-Large (fp32) at threshold 0.10**.

| | notes with a leak | over-redaction |
|---|---|---|
| **rules + ours (v2-small, int8, threshold 0.02)** | **2 / 7108 (0.03%)** | 0.2% |
| rules + OpenMed-large @0.10 | 26 / 7108 (0.37%) | 0.5% |

Discordant notes: only ours leaked on 1, only OpenMed-large leaked on 25, both leaked on 1.
**Exact McNemar two-sided p = 8.0 × 10⁻⁷.** Paired bootstrap of the leak-rate difference: +0.3 percentage points,
95% CI [+0.2, +0.5]. Our over-redaction (0.2%) is within the 1% constraint.

**Verdict: the primary hypothesis holds. Rules + ours leaks significantly fewer notes than rules + OpenMed-large at
its best pre-registered operating point.**

## Secondary (reported without a multiplicity correction claim)

| set | comparison | ours | OpenMed-large | exact McNemar p |
|---|---|---|---|---|
| clin3_test | rules+ours vs rules+OML @0.35 | 2 (0.03%) | 101 (1.4%) | 8.0 × 10⁻²⁹ |
| clin3_test | ours alone vs OML alone @0.10 | 4 (0.06%) | 407 (5.7%) | 5.0 × 10⁻¹¹⁸ |
| clin3_test | ours alone vs OML alone @0.35 | 4 (0.06%) | 680 (9.6%) | 9.2 × 10⁻²⁰⁰ |
| clin3_novel (unseen formats) | rules+ours vs rules+OML @0.10 | 1 (0.01%) | 33 (0.46%) | 4.7 × 10⁻¹⁰ |
| clin3_novel | rules+ours vs rules+OML @0.35 | 1 (0.01%) | 140 (2.0%) | 2.9 × 10⁻⁴² |
| clin3_novel | ours alone vs OML alone @0.10 | 3 (0.04%) | 210 (3.0%) | 1.4 × 10⁻⁵⁹ |
| clin3_novel | ours alone vs OML alone @0.35 | 3 (0.04%) | 495 (7.0%) | 1.2 × 10⁻¹⁴⁴ |

Over-redaction: ours 0.1% alone and 0.2% with rules on both sets; OpenMed-large 0.1–0.3% alone and 0.3–0.5% with rules.

## Compute (same 7,108 notes)

- **Ours:** about 26 CPU-minutes on spark-d500 (2 threads, about 13 min wall, both configs in one pass). About 20 ms
  per note on an M3 Max CPU.
- **OpenMed-large (fp32):** about 500 CPU-minutes per set on spark-d500 (9 threads, about 1 h 50 min wall).
- **Per note: about 0.2 vs about 4 CPU-seconds,** roughly 18–20× less compute for ours.
- Mac (foreground, one note at a time): about 20 ms vs about 240 ms per note.

## Limits

- **All test notes are synthetic.** They were written by DiffusionGemma around planted universe-C values. These are
  not real clinical records.
- **This is one competitor.** Only OpenMed-large was in this powered run; it was the closest on sealed 2. Sealed 2
  already showed significant wins over the other 11 systems on 860-note sets.
- **No real-data benchmark yet.** i2b2 2014 is still pending.
- **Mixed machines.** `clin3_test` "ours" ran on the Mac and everything else on spark-d500 (same source commit, same
  model files by sha256). Dev parity between the machines was exact (`SEALED3_LOG.md`).

The clin3 sealed sets are now spent.
