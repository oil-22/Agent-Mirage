"""Retain exact big tensor bytes with chunk reuse across growing visual histories."""
import hashlib
import json
import os
from pathlib import Path

CHUNK = 8 * 1024 * 1024


def store(folder, name, raw, raw_sha, blob_root, prior=None):
    if len(raw) < CHUNK:
        from evidence_store import store as raw_store
        path = folder/(name+'.tensor')
        source = folder/prior['file'] if prior else None
        return path.name, raw_store(path, raw, source)
    path = folder/(name+'.tensor.parts.json')
    if (prior and prior['sha256'] == raw_sha and prior['bytes'] == len(raw)
            and prior['storage'] == 'exact-tensor-chunks-v1'):
        os.link(folder/prior['file'], path)
        return path.name, prior['storage']
    chunks = []
    for offset in range(0, len(raw), CHUNK):
        part = raw[offset:offset+CHUNK]
        h = hashlib.sha256(part).hexdigest()
        target = blob_root/h[:2]/h
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open('xb') as f:
                f.write(part)
                f.flush()
                os.fsync(f.fileno())
            target.chmod(0o400)
        except FileExistsError:
            assert not target.is_symlink() and target.stat().st_size == len(part), target
        chunks.append([h, len(part)])
    with path.open('x', encoding='utf-8') as f:
        json.dump({'format': 'exact-tensor-chunks-v1', 'raw_sha256': raw_sha, 'bytes': len(raw),
                   'chunks': chunks}, f, separators=(',', ':'))
    return path.name, 'exact-tensor-chunks-v1'


def reconstruct(manifest, blob_root, output=None):
    """Stream an exact tensor into a writer, or just verify all raw bytes."""
    m = json.loads(Path(manifest).read_bytes())
    assert m['format'] == 'exact-tensor-chunks-v1'
    total = 0
    whole = hashlib.sha256()
    for h, length in m['chunks']:
        assert len(h) == 64 and all(c in '0123456789abcdef' for c in h)
        p = Path(blob_root)/h[:2]/h
        raw = p.read_bytes()
        assert len(raw) == length and hashlib.sha256(raw).hexdigest() == h, p
        whole.update(raw)
        total += len(raw)
        if output is not None:
            output.write(raw)
    assert total == m['bytes'] and whole.hexdigest() == m['raw_sha256'], manifest
    return whole.hexdigest()
