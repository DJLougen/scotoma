# Hugging Face packaging for scotoma-clinical-deid-v2

`scotoma-clinical-deid-v2/` is the HF repo directory: `README.md` is the model
card (tracked in git here), and `stage.sh` copies the binary artefacts into it
from `models/v2-small`. The copied binaries are git-ignored — they live on the
HF hub, not in this repo.

## Files the HF repo needs

From `models/v2-small` (sha256 recorded for provenance):

| file | required | notes |
|---|---|---|
| `config.json` | yes | carries `id2label`, `scotoma_threshold` (0.02), `scotoma_max_len` (384), `scotoma_domain` |
| `tokenizer.json` | yes | fast tokenizer; load via `tokenizers.Tokenizer.from_file` or HF `AutoTokenizer` |
| `model_quantized.onnx` | yes | per-channel int8, 172 MB, sha256 `33be2438…e41` — the shipped weights |
| `model_fp32.onnx` | optional | 566 MB reference weights, for debugging / re-quantizing |

Also copy `README.md` (the model card). Upload with
`huggingface-cli upload <repo> scotoma-clinical-deid-v2 .` or the web UI —
large ONNX files go through Git LFS automatically. **Nothing in this directory
uploads by itself; staging only.**

## Staging

```sh
./stage.sh            # copies the required files (+ fp32 with --fp32), prints sha256
./stage.sh --fp32     # include model_fp32.onnx
```

It refuses to overwrite a file whose contents differ unless you pass `--force`,
and it never pushes anything — upload is a separate, manual step after review.
