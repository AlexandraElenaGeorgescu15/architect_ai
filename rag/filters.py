
from pathlib import Path
import re, fnmatch, hashlib, yaml

SECRET_RE = re.compile(r'(AKIA[0-9A-Z]{16}|SECRET|PASSWORD|TOKEN|API_KEY)', re.I)

# File extensions considered as code files
CODE_EXTS = (".ts", ".tsx", ".js", ".jsx", ".cs", ".py", ".sql")

def load_cfg():
    with open("rag/config.yaml","r",encoding="utf-8") as f:
        return yaml.safe_load(f)

def allow_file(path: Path, cfg) -> bool:
    if path.is_dir(): return False
    try:
        if path.stat().st_size > cfg["max_file_mb"]*1024*1024: return False
    except Exception:
        return False
    if not any(str(path).endswith(ext) for ext in cfg["allow_extensions"]): return False
    
    # Check ignore patterns using pathlib's match() which handles ** globbing
    path_str = str(path).replace('\\', '/')  # Normalize path separators
    for pat in cfg["ignore_globs"]:
        # Use Path.match() for proper ** glob support
        if path.match(pat) or fnmatch.fnmatch(path_str, pat):
            return False
    
    return True

def sanitize(text: str) -> str:
    return SECRET_RE.sub("***REDACTED***", text)

def sha1(text:str)->str:
    return hashlib.sha1(text.encode("utf-8","ignore")).hexdigest()
