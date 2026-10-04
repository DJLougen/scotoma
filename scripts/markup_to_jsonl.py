"""Convert inline-annotated text to the JSONL the benchmark reads.

Input: documents separated by a line containing only `---`; identifiers are
written as {{label|text}}. Offsets in the output are in characters.
Usage: python scripts/markup_to_jsonl.py in.markup out.jsonl
"""
import json, re, sys
src = open(sys.argv[1], encoding="utf-8").read()
pat = re.compile(r"\{\{([a-z0-9_]+)\|(.*?)\}\}", re.S)
n = 0
with open(sys.argv[2], "w", encoding="utf-8") as out:
    for doc in re.split(r"^---\s*$", src, flags=re.M):
        doc = doc.strip("\n")
        if not doc.strip(): continue
        text, spans, pos = "", [], 0
        for m in pat.finditer(doc):
            text += doc[pos:m.start()]
            spans.append({"start": len(text), "end": len(text) + len(m.group(2)), "label": m.group(1)})
            text += m.group(2)
            pos = m.end()
        text += doc[pos:]
        out.write(json.dumps({"text": text, "spans": spans}, ensure_ascii=False) + "\n")
        n += 1
print(f"{n} documents")
