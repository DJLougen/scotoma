"""Download a Hugging Face token-classification PII model, export it to ONNX,
quantise to int8, and drop it where the app bundles it from.

    pip install torch "transformers>=4.57,<5" onnx onnxruntime
    python scripts/fetch_model.py                       # default model
    python scripts/fetch_model.py --model StanfordAIMI/stanford-deidentifier-base
    python scripts/fetch_model.py --no-quantize         # keep fp32 (bigger, reference accuracy)

This is the only step that touches the network. The app itself never does.
Exports with torch.onnx directly (optimum's exporter broke against current
huggingface_hub / diffusers on Colab) and checks the ONNX output against PyTorch.
"""
import argparse, json, shutil, sys
from pathlib import Path

DEFAULT = "OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1"
ROOT = Path(__file__).resolve().parent.parent
PROBE = "Patient John Smith (MRN 4482913) was seen at 12 Elm St, Boston on 2024-01-01; call 617-555-0182."


def onnx_export(model, tok, path):
    import numpy as np, onnxruntime as ort, torch

    enc = tok(PROBE, return_tensors="pt")
    names = [n for n in ("input_ids", "attention_mask", "token_type_ids") if n in enc]

    class Wrap(torch.nn.Module):
        def __init__(self, m): super().__init__(); self.m = m
        def forward(self, *args): return self.m(**dict(zip(names, args))).logits

    wrapped = Wrap(model.cpu().eval()).eval()
    args = tuple(enc[n] for n in names)
    with torch.no_grad(): ref = wrapped(*args).numpy()
    axes = {n: {0: "batch", 1: "seq"} for n in names + ["logits"]}
    kw = dict(input_names=names, output_names=["logits"], dynamic_axes=axes, opset_version=17, do_constant_folding=True)
    try:
        torch.onnx.export(wrapped, args, str(path), dynamo=False, **kw)
    except TypeError:      # older torch without the dynamo flag
        torch.onnx.export(wrapped, args, str(path), **kw)
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    names = [i.name for i in sess.get_inputs()]     # unused inputs (DeBERTa's token_type_ids) are pruned from the graph
    got = sess.run(None, {n: enc[n].numpy() for n in names})[0]
    diff = float(np.abs(ref - got).max())
    print(f"onnx check: max |torch - onnx| = {diff:.5f}")
    if diff > 1e-2: sys.exit("exported ONNX does not reproduce the PyTorch model")
    return enc, names, ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT)
    ap.add_argument("--out", default=str(ROOT / "app" / "src-tauri" / "models" / "default"))
    ap.add_argument("--no-quantize", action="store_true")
    ap.add_argument("--keep-fp32", action="store_true", help="keep model_fp32.onnx beside the int8 model (for fp32-vs-int8 scoring; never bundle it)")
    a = ap.parse_args()

    from transformers import AutoModelForTokenClassification, AutoTokenizer

    out = Path(a.out)
    tmp = out.parent / (out.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)

    print(f"exporting {a.model} to ONNX ...")
    tok = AutoTokenizer.from_pretrained(a.model)
    if not tok.is_fast: sys.exit("this model has no fast tokenizer (tokenizer.json); pick another")
    model = AutoModelForTokenClassification.from_pretrained(a.model)
    enc, names, ref = onnx_export(model, tok, tmp / "model.onnx")
    tok.backend_tokenizer.save(str(tmp / "tokenizer.json"))
    model.config.to_json_file(str(tmp / "config.json"))
    labels = json.load(open(tmp / "config.json"))["id2label"]
    print(f"{len(labels)} labels: {', '.join(list(labels.values())[:12])} ...")

    if not a.no_quantize:
        import onnxruntime as ort
        from onnxruntime.quantization import QuantType, quantize_dynamic
        print("quantising to int8 ...")
        quantize_dynamic(str(tmp / "model.onnx"), str(tmp / "model_quantized.onnx"), weight_type=QuantType.QInt8)
        q = ort.InferenceSession(str(tmp / "model_quantized.onnx"), providers=["CPUExecutionProvider"]).run(None, {n: enc[n].numpy() for n in names})[0]
        print(f"int8 label agreement with fp32 on probe: {float((q.argmax(-1) == ref.argmax(-1)).mean()):.2f}")
        if a.keep_fp32: (tmp / "model.onnx").rename(tmp / "model_fp32.onnx")   # not loaded by the app
        else: (tmp / "model.onnx").unlink()

    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():
        if old.is_file(): old.unlink()
    for f in tmp.iterdir():
        shutil.move(str(f), str(out / f.name))
    shutil.rmtree(tmp, ignore_errors=True)

    size = sum(f.stat().st_size for f in out.iterdir()) / 1e6
    print(f"wrote {out}  ({size:.0f} MB)")
    print("check it:  scotoma eval eval/fixtures/clinical_smoke.jsonl --model", out)


if __name__ == "__main__":
    main()
