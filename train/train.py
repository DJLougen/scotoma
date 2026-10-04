#!/usr/bin/env python3
"""Fine-tune a token classifier on Scotoma's category set and export it in the
form the app loads (model_quantized.onnx + tokenizer.json + config.json).

    pip install torch transformers onnx onnxruntime onnxscript
    python train/train.py --train bench/data/train.jsonl more.jsonl --dev bench/data/dev.jsonl \\
        --base microsoft/deberta-v3-small --out models/scotoma-v0 --epochs 3

Input is benchmark JSONL: {"text", "spans":[{"start","end","label"}]} with
character offsets and Scotoma category labels (use `scotoma convert` to map
other datasets onto them). Runs on CUDA, Apple MPS or CPU.

`--tiny` trains a 2-layer model from scratch with its own tokenizer. It exists
to smoke-test this script without downloading anything; it is not a real model.
"""
import argparse, json, math, os, random, time
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

CATS = "NAME ADDRESS LOCATION ZIP DATE AGE PHONE FAX EMAIL SSN MRN PLAN ACCOUNT LICENSE VEHICLE DEVICE URL IP BIOMETRIC ID ORG".split()
LABELS = ["O"] + [f"{p}-{c}" for c in CATS for p in ("B", "I")]
L2I = {l: i for i, l in enumerate(LABELS)}


def read(paths, limit=None):
    docs = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    docs.append((d["text"], [(s["start"], s["end"], s["label"]) for s in d.get("spans", []) if s["label"] in CATS]))
    random.shuffle(docs)
    return docs[:limit] if limit else docs


class Chunks(Dataset):
    """Tokenise with overlapping windows; label each token from the character spans."""
    def __init__(self, docs, tok, max_len, stride):
        self.items = []
        for text, spans in docs:
            enc = tok(text, truncation=True, max_length=max_len, stride=stride, return_overflowing_tokens=True,
                      return_offsets_mapping=True, return_special_tokens_mask=True)
            spans = sorted(spans)
            for ids, offs, special in zip(enc["input_ids"], enc["offset_mapping"], enc["special_tokens_mask"]):
                labels, prev = [], None
                for (a, b), sp in zip(offs, special):
                    if sp or a == b:
                        labels.append(-100); continue
                    hit = next((s for s in spans if s[0] < b and a < s[1]), None)
                    if hit is None:
                        labels.append(0); prev = None
                    else:
                        labels.append(L2I[("I-" if prev is hit else "B-") + hit[2]]); prev = hit
                self.items.append((ids, labels))

    def __len__(self): return len(self.items)
    def __getitem__(self, i): return self.items[i]


def collate(pad_id):
    def f(batch):
        n = max(len(x[0]) for x in batch)
        ids = torch.full((len(batch), n), pad_id, dtype=torch.long)
        mask = torch.zeros((len(batch), n), dtype=torch.long)
        lab = torch.full((len(batch), n), -100, dtype=torch.long)
        for i, (a, b) in enumerate(batch):
            ids[i, :len(a)] = torch.tensor(a); mask[i, :len(a)] = 1; lab[i, :len(b)] = torch.tensor(b)
        return ids, mask, lab
    return f


def tiny_tokenizer(texts, out_dir, vocab=6000):
    from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, processors, trainers, decoders
    from transformers import PreTrainedTokenizerFast
    t = Tokenizer(models.WordPiece(unk_token="[UNK]"))
    t.normalizer = normalizers.NFC()
    t.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
    t.train_from_iterator(texts, trainers.WordPieceTrainer(vocab_size=vocab, special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]))
    t.post_processor = processors.TemplateProcessing(single="[CLS] $A [SEP]", special_tokens=[("[CLS]", t.token_to_id("[CLS]")), ("[SEP]", t.token_to_id("[SEP]"))])
    t.decoder = decoders.WordPiece()
    return PreTrainedTokenizerFast(tokenizer_object=t, unk_token="[UNK]", pad_token="[PAD]", cls_token="[CLS]", sep_token="[SEP]", mask_token="[MASK]")


@torch.no_grad()
def evaluate(model, loader, device):
    """Token-level: is an identifier token flagged as *some* identifier?"""
    model.eval()
    tp = fp = fn = 0
    for ids, mask, lab in loader:
        pred = model(input_ids=ids.to(device), attention_mask=mask.to(device)).logits.argmax(-1).cpu()
        keep = lab != -100
        gold, got = (lab > 0) & keep, (pred > 0) & keep
        tp += int((gold & got).sum()); fp += int((~gold & got).sum()); fn += int((gold & ~got).sum())
    r, p = tp / max(1, tp + fn), tp / max(1, tp + fp)
    f2 = 5 * p * r / max(1e-9, 4 * p + r)     # recall counts double: a miss is a leak
    return r, p, f2


def export(model, tok, out, name, max_len, quantize=True):
    """Write model.onnx (+ int8 copy), tokenizer.json and config.json, then check the ONNX output."""
    import onnxruntime as ort
    model = model.cpu().eval()

    class Wrap(torch.nn.Module):
        def __init__(self, m): super().__init__(); self.m = m
        def forward(self, input_ids, attention_mask): return self.m(input_ids=input_ids, attention_mask=attention_mask).logits

    ids = torch.tensor([tok("Patient John Smith seen 2024-01-01.")["input_ids"]])
    mask = torch.ones_like(ids)
    path = os.path.join(out, "model.onnx")
    wrapped = Wrap(model).eval()      # a fresh Module starts in train mode; dropout would corrupt the check
    with torch.no_grad(): ref = wrapped(ids, mask).numpy()
    kw = dict(input_names=["input_ids", "attention_mask"], output_names=["logits"],
              dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"}, "logits": {0: "batch", 1: "seq"}},
              opset_version=17, do_constant_folding=True)
    try:      # torch >= 2.9 defaults to the dynamo exporter; keep the TorchScript path that dynamic_axes was written for
        torch.onnx.export(wrapped, (ids, mask), path, dynamo=False, **kw)
    except TypeError:
        torch.onnx.export(wrapped, (ids, mask), path, **kw)
    got = ort.InferenceSession(path, providers=["CPUExecutionProvider"]).run(None, {"input_ids": ids.numpy(), "attention_mask": mask.numpy()})[0]
    diff = float(np.abs(ref - got).max())
    print(f"onnx check: max |torch - onnx| = {diff:.5f}")
    assert diff < 1e-2, "exported ONNX does not reproduce the PyTorch model"
    if quantize:
        from onnxruntime.quantization import QuantType, quantize_dynamic
        qpath = os.path.join(out, "model_quantized.onnx")
        quantize_dynamic(path, qpath, weight_type=QuantType.QInt8)
        q = ort.InferenceSession(qpath, providers=["CPUExecutionProvider"]).run(None, {"input_ids": ids.numpy(), "attention_mask": mask.numpy()})[0]
        agree = float((q.argmax(-1) == ref.argmax(-1)).mean())
        print(f"int8: {os.path.getsize(qpath)/1e6:.1f} MB (fp32 {os.path.getsize(path)/1e6:.1f} MB), label agreement on probe {agree:.2f}")
        # The app prefers model_quantized.onnx. Keep fp32 beside it as model_fp32.onnx
        # so both can be benchmarked; delete it before bundling.
        os.replace(path, os.path.join(out, "model_fp32.onnx"))
    tok.backend_tokenizer.save(os.path.join(out, "tokenizer.json"))
    cfg = {"_name_or_path": name, "id2label": {str(i): l for i, l in enumerate(LABELS)},
           "max_position_embeddings": int(getattr(model.config, "max_position_embeddings", 512)), "scotoma_max_len": max_len}
    json.dump(cfg, open(os.path.join(out, "config.json"), "w"), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", nargs="+", required=True)
    ap.add_argument("--dev", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default="microsoft/deberta-v3-small")
    ap.add_argument("--name", default=None, help="model name written to config.json")
    ap.add_argument("--tiny", action="store_true")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--max-len", type=int, default=384)
    ap.add_argument("--stride", type=int, default=64)
    ap.add_argument("--o-weight", type=float, default=1.0, help="<1 down-weights the O class: more recall, less precision")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-quantize", action="store_true")
    a = ap.parse_args()
    random.seed(a.seed); torch.manual_seed(a.seed)
    os.makedirs(a.out, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

    train_docs, dev_docs = read(a.train, a.limit), read(a.dev, 2000)
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer, BertConfig, BertForTokenClassification, get_linear_schedule_with_warmup
    id2label = dict(enumerate(LABELS))
    if a.tiny:
        tok = tiny_tokenizer([t for t, _ in train_docs], a.out)
        cfg = BertConfig(vocab_size=tok.vocab_size, hidden_size=128, num_hidden_layers=2, num_attention_heads=4, intermediate_size=256,
                         max_position_embeddings=512, num_labels=len(LABELS), id2label=id2label, label2id=L2I, pad_token_id=tok.pad_token_id)
        model = BertForTokenClassification(cfg)
        name = a.name or "scotoma-tiny-smoke"
    else:
        tok = AutoTokenizer.from_pretrained(a.base)
        assert tok.is_fast, "need a fast tokenizer (tokenizer.json)"
        model = AutoModelForTokenClassification.from_pretrained(a.base, num_labels=len(LABELS), id2label=id2label, label2id=L2I, ignore_mismatched_sizes=True)
        name = a.name or f"scotoma/{os.path.basename(a.base)}"
    max_len = min(a.max_len, int(getattr(model.config, "max_position_embeddings", 512)))

    t0 = time.time()
    tr, dv = Chunks(train_docs, tok, max_len, a.stride), Chunks(dev_docs, tok, max_len, a.stride)
    print(f"{len(train_docs)} train docs → {len(tr)} windows, {len(dev_docs)} dev docs → {len(dv)} windows, device {device}, {sum(p.numel() for p in model.parameters())/1e6:.1f}M params ({time.time()-t0:.0f}s to tokenise)")
    pad = tok.pad_token_id or 0
    tl = DataLoader(tr, batch_size=a.batch, shuffle=True, collate_fn=collate(pad))
    dl = DataLoader(dv, batch_size=a.batch * 2, collate_fn=collate(pad))

    model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    steps = len(tl) * a.epochs
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    w = torch.ones(len(LABELS), device=device); w[0] = a.o_weight
    loss_fn = torch.nn.CrossEntropyLoss(weight=w, ignore_index=-100)
    amp = device == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    best, best_state = -1.0, None
    for ep in range(a.epochs):
        model.train(); tot = 0.0; t0 = time.time()
        for i, (ids, mask, lab) in enumerate(tl):
            ids, mask, lab = ids.to(device), mask.to(device), lab.to(device)
            with torch.autocast("cuda", enabled=amp):
                logits = model(input_ids=ids, attention_mask=mask).logits
                loss = loss_fn(logits.float().view(-1, len(LABELS)), lab.view(-1))
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scale = scaler.get_scale()
            scaler.step(opt); scaler.update()
            if scaler.get_scale() >= scale: sched.step()   # GradScaler skips opt.step() on overflow (and lowers the scale); keep the LR schedule in step
            tot += loss.item()
            if (i + 1) % 200 == 0: print(f"  ep {ep+1} step {i+1}/{len(tl)} loss {tot/(i+1):.4f}")
        r, p, f2 = evaluate(model, dl, device)
        print(f"epoch {ep+1}: loss {tot/len(tl):.4f}  dev token recall {r:.4f} precision {p:.4f} F2 {f2:.4f}  ({time.time()-t0:.0f}s)")
        if f2 > best:
            best, best_state = f2, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    model.save_pretrained(os.path.join(a.out, "hf")); tok.save_pretrained(os.path.join(a.out, "hf"))
    export(model, tok, a.out, name, max_len, quantize=not a.no_quantize)
    print(f"done. app-loadable model in {a.out}  (best dev F2 {best:.4f})")


if __name__ == "__main__":
    main()
