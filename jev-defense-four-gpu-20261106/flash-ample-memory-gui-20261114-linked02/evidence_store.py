"""Retain complete actual tensor bytes; hardlink only after full byte-hash equality."""
import hashlib,os
from pathlib import Path

def store(path,raw,source=None):
    path=Path(path);h=hashlib.sha256(raw).hexdigest()
    if path.exists():raise FileExistsError(path)
    if source is not None:
        source=Path(source)
        if source.stat().st_size==len(raw)and hashlib.sha256(source.read_bytes()).hexdigest()==h:
            os.link(source,path)
            return 'full-byte-verified-hardlink'
    with path.open('xb')as f:f.write(raw)
    return 'independent-raw-bytes'
