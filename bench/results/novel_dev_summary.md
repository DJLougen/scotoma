# Clinical novel-format dev (844 docs)

| system | recall | fully redacted | leak docs | over-redaction | precision | ms/doc | source |
|---|---|---|---|---|---|---|---|
| rules+ours-shipped | 99.9 | 93.8 | 7/844 (0.8%) | 0.3% | 99.4 | 23.7 | `novel_dev_hf` |
| rules+openmed-large | 99.8 | 90.9 | 9/844 (1.1%) | 0.3% | 98.9 | 252.1 | `novel_dev_hf` |
| rules+ours-fp32 | 99.8 | 92.7 | 15/844 (1.8%) | 0.2% | 99.7 | 39.5 | `novel_dev_hf` |
| rules+gliner-nvidia | 99.2 | 91.7 | 44/844 (5.2%) | 0.4% | 99.1 | 0.2 | `novel_dev_ext` |
| ours-shipped | 99.3 | 92.3 | 46/844 (5.5%) | 0.1% | 99.4 | 21.9 | `novel_dev_hf` |
| openmed-large | 99.2 | 88.8 | 54/844 (6.4%) | 0.1% | 98.9 | 243.7 | `novel_dev_hf` |
| rules+stanford | 98.4 | 87.6 | 87/844 (10.3%) | 0.4% | 99.0 | 27.6 | `novel_dev_hf` |
| ours-fp32 | 98.3 | 90.6 | 96/844 (11.4%) | 0.0% | 99.8 | 39.6 | `novel_dev_hf` |
| rules+gliner-edge | 98.5 | 92.6 | 97/844 (11.5%) | 1.9% | 91.1 | 0.2 | `novel_dev_ext` |
| gliner-edge | 97.1 | 87.1 | 172/844 (20.4%) | 1.7% | 91.6 | 0.0 | `novel_dev_ext` |
| rules+openmed | 96.6 | 82.9 | 183/844 (21.7%) | 0.2% | 99.9 | 20.5 | `novel_dev_hf` |
| rules+gliner-large | 95.3 | 87.8 | 208/844 (24.6%) | 0.2% | 99.9 | 0.2 | `novel_dev_ext` |
| gliner-nvidia | 95.8 | 87.9 | 227/844 (26.9%) | 0.2% | 99.1 | 0.0 | `novel_dev_ext` |
| rules+privacy-filter | 95.0 | 88.6 | 236/844 (28.0%) | 0.5% | 99.6 | 0.2 | `novel_dev_ext` |
| stanford | 95.4 | 78.8 | 264/844 (31.3%) | 0.3% | 99.0 | 27.3 | `novel_dev_hf` |
| openmed | 92.2 | 75.7 | 337/844 (39.9%) | 0.0% | 100.0 | 20.9 | `novel_dev_hf` |
| rules+gliner-base | 92.3 | 84.3 | 363/844 (43.0%) | 1.5% | 94.1 | 0.2 | `novel_dev_ext` |
| gliner-large | 88.0 | 78.8 | 456/844 (54.0%) | 0.1% | 100.0 | 0.0 | `novel_dev_ext` |
| rules+presidio | 88.1 | 75.3 | 487/844 (57.7%) | 1.8% | 92.2 | 0.2 | `novel_dev_ext` |
| privacy-filter | 85.6 | 82.5 | 527/844 (62.4%) | 0.3% | 99.6 | 0.0 | `novel_dev_ext` |
| rules+ai4privacy-en | 83.9 | 72.9 | 561/844 (66.5%) | 0.3% | 99.1 | 98.3 | `novel_dev_hf` |
| rules+ai4privacy-cat | 81.6 | 64.2 | 580/844 (68.7%) | 0.2% | 99.5 | 99.1 | `novel_dev_hf` |
| gliner-base | 83.0 | 73.2 | 610/844 (72.3%) | 1.3% | 93.9 | 0.0 | `novel_dev_ext` |
| ai4privacy-en | 79.4 | 61.7 | 620/844 (73.5%) | 0.2% | 99.1 | 98.1 | `novel_dev_hf` |
| presidio | 80.2 | 67.6 | 641/844 (75.9%) | 1.7% | 91.5 | 0.0 | `novel_dev_ext` |
| rules+piiranha | 77.5 | 65.5 | 692/844 (82.0%) | 0.3% | 99.6 | 92.5 | `novel_dev_hf` |
| ai4privacy-cat | 71.1 | 46.6 | 748/844 (88.6%) | 0.1% | 99.5 | 98.1 | `novel_dev_hf` |
| piiranha | 57.1 | 46.0 | 822/844 (97.4%) | 0.1% | 99.4 | 92.0 | `novel_dev_hf` |
| rules | 42.5 | 33.7 | 829/844 (98.2%) | 0.2% | 100.0 | 0.1 | `novel_dev_hf` |
