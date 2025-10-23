
import re
from tiktoken import get_encoding

enc = get_encoding("cl100k_base")

FUNC_RE = re.compile(r'^(\s)*(export\s+)?(async\s+)?(class|function|interface|type)\s+[A-Za-z0-9_]+|^\s*\w+\s*=\s*\(', re.M)

def _token_slices(tokens, tok_limit, overlap):
    i = 0
    n = len(tokens)
    while i < n:
        j = min(n, i + tok_limit)
        yield tokens[i:j]
        if j == n: break
        i = j - overlap

def chunk_text(path, text, tok_limit=550, overlap=60):
    # Disable special token checking to handle any text content
    tokens = enc.encode(text, disallowed_special=())
    out = []
    for idx, sl in enumerate(_token_slices(tokens, tok_limit, overlap)):
        content = enc.decode(sl)
        out.append({
            "id": f"{path}::text::{idx}",
            "content": f"FILE: {path}\nSECTION: {idx}\n{content}",
            "meta": {"path": str(path), "kind": "text", "chunk": idx}
        })
    return out

def chunk_code(path, text, tok_limit=360, overlap=60):
    parts = []
    last = 0
    for m in FUNC_RE.finditer(text):
        s = m.start()
        if s-last > 300:
            parts.append(text[last:s]); last = s
    parts.append(text[last:])
    out=[]
    for i,p in enumerate(parts):
        # Disable special token checking to handle any text content
        toks = enc.encode(p, disallowed_special=())
        if len(toks) <= tok_limit:
            out.append({
                "id": f"{path}::code::{i}",
                "content": f"FILE: {path}\nSECTION: {i}\n{p}",
                "meta": {"path": str(path), "kind": "code", "chunk": i}
            })
        else:
            for j, sl in enumerate(_token_slices(toks, tok_limit, overlap)):
                out.append({
                    "id": f"{path}::code::{i}.{j}",
                    "content": f"FILE: {path}\nSECTION: {i}.{j}\n{enc.decode(sl)}",
                    "meta": {"path": str(path), "kind": "code", "chunk": f"{i}.{j}"}
                })
    return out
