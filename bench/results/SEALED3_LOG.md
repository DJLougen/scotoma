## Sealed evaluation 3, run 1
- started: 2026-10-05T18:14:35Z
- commit: 2394752
- 2026-10-05T18:37:40Z: the four OpenMed-large runs on clin3_test were starved of CPU (about 1.5 CPU-minutes each in 40 min, 4 in parallel). Killed before writing any output and restarted one at a time. Nothing had been read; 'ours' (finished) was not re-run.
- 2026-10-05T18:49:59Z: processes detached from the agent's shell (nohup, launchd, async) were CPU-throttled to about 9% of a core. All remaining runs now run as foreground jobs, one at a time. Still nothing read.
- 2026-10-05T19:04:51Z: 20 s CPU-speed probe of the OpenMed-large eval command on clin3_test; output went to /dev/null, nothing read.
- 2026-10-05T19:06:52Z: on this Mac, detached processes stayed CPU-starved whatever the launch method. Remaining runs move to spark-d500 (Linux, 20 cores), same source commit 5058cdb, same model files (sha256 recorded). ms/doc from Spark runs is not comparable with Mac timings.
- 2026-10-05T21:03:08Z: spark-d500 evalmany runs finished; outputs copied to bench/results/sealed3/pre/
- 2026-10-05T21:03:59Z: sealed 3 analysis done (primary exact McNemar p = 8.0e-7, rules+ours 2/7108 vs rules+OpenMed-large@0.1 26/7108). Both clin3 sets scored once and now spent.
