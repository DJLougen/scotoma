"""Builds a toy ONNX token classifier + tokenizer for plumbing tests.

It is a lookup table, not a real model: it exists so the Rust inference path
(tokenise → window → softmax → decode → offsets) can be tested without
downloading weights. Usage: python scripts/make_toy_model.py <out_dir>
"""
import json, sys, os
import numpy as np
import onnx
from onnx import helper, TensorProto, numpy_helper
from tokenizers import Tokenizer, models, pre_tokenizers, processors, normalizers

out = sys.argv[1]
os.makedirs(out, exist_ok=True)

labels = ["O", "B-first_name", "I-first_name", "B-last_name", "I-last_name", "B-city", "B-occupation", "B-age"]
vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "john", "smith", "toronto", "nurse", "anna", "müller", "the", "patient", "is", "a", "from", "97", "45"]
tok = Tokenizer(models.WordLevel({w: i for i, w in enumerate(vocab)}, unk_token="[UNK]"))
tok.normalizer = normalizers.Lowercase()
tok.pre_tokenizer = pre_tokenizers.Whitespace()
tok.post_processor = processors.TemplateProcessing(single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 2), ("[SEP]", 3)])
tok.save(os.path.join(out, "tokenizer.json"))

table = np.zeros((len(vocab), len(labels)), dtype=np.float32)
table[:, 0] = 6.0                      # default: confidently O
def setp(word, probs):                 # probs: {label: p}; remainder goes to O
    row = np.full(len(labels), 1e-6, dtype=np.float32)
    for k, p in probs.items(): row[labels.index(k)] = p
    row[0] = max(1e-6, 1.0 - sum(probs.values()))
    table[vocab.index(word)] = np.log(row)
setp("john", {"B-first_name": 0.97})
setp("anna", {"B-first_name": 0.30, "I-first_name": 0.25})   # argmax says O; summed mass says name
setp("smith", {"B-last_name": 0.6, "I-last_name": 0.38})
setp("müller", {"I-last_name": 0.9})
setp("toronto", {"B-city": 0.2})       # below threshold, above floor → "possible"
setp("nurse", {"B-occupation": 0.95})  # quasi-identifier: strict mode only
setp("97", {"B-age": 0.9})
setp("45", {"B-age": 0.9})             # an age under 90 is not an identifier

ids = helper.make_tensor_value_info("input_ids", TensorProto.INT64, [1, "seq"])
mask = helper.make_tensor_value_info("attention_mask", TensorProto.INT64, [1, "seq"])
logits = helper.make_tensor_value_info("logits", TensorProto.FLOAT, [1, "seq", len(labels)])
node = helper.make_node("Gather", ["table", "input_ids"], ["logits"], axis=0)
graph = helper.make_graph([node], "toy", [ids, mask], [logits], [numpy_helper.from_array(table, "table")])
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
model.ir_version = 9
onnx.checker.check_model(model)
onnx.save(model, os.path.join(out, "model.onnx"))
json.dump({"_name_or_path": "toy-lookup", "id2label": {str(i): l for i, l in enumerate(labels)}, "max_position_embeddings": 24},
          open(os.path.join(out, "config.json"), "w"), indent=1)
print("wrote", out)
