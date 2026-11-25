"""Preserve first metadata-only failure without changing its terminal directory."""
import hashlib
import json
from pathlib import Path
import shutil
import time

base = Path(__file__).resolve().parent
old = base / 'download-attempts/1793972196492570417'
root = base / 'failure-preservations' / str(time.time_ns())
root.mkdir(parents=True, exist_ok=False)
shutil.copytree(old, root / 'failed-attempt-snapshot')
shutil.copyfile(base / 'download_pinned_flash.py', root / 'original-downloader.py')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
seal = json.loads((old / 'seal.json').read_bytes())
assert all(sha(old / name) == expected for name, expected in seal.items())
(root / 'preservation.json').write_text(json.dumps({
    'original': str(old), 'original_seal_sha256': sha(old / 'seal.json'),
    'failure': 'HF tree expand pagination limit1000 rejected HTTP400 before any weights',
    'linked_repair': str(base / 'download-attempts/1793972286914423476'),
    'repair_only': 'API page limit50; model revision and every file identity unchanged',
    'model_calls': 0, 'GPU_allocations': 0,
}, indent=2))
(root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)): sha(p)
    for p in root.rglob('*') if p.is_file()}, indent=2))
print(json.dumps({'failure_preservation': str(root)}))
