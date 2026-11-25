"""Copy only final sealed readiness audit files; no credentials or tensor payloads."""
import base64
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
remote_root = '/home/researcher/jev-defense-four-gpu-20261106/online-readiness-independent-audits/1793978878359030429'
code = """import base64,hashlib,json
from pathlib import Path
root=Path(REMOTE_ROOT)
seal=json.loads((root/'seal.json').read_bytes())
assert hashlib.sha256((root/'receipt.json').read_bytes()).hexdigest()=='f30b0ef2655c82fe17a4c67afa983244647a49ef32719a90b6e0b9b619f1a215'
assert hashlib.sha256((root/'seal.json').read_bytes()).hexdigest()=='4a6c97e0ef5122d951b72f1e32560dd6dd60cda059b26ae9bff0add0610379f6'
for name,expected in seal.items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
files={name:base64.b64encode((root/name).read_bytes()).decode() for name in list(seal)+['seal.json']}
print(json.dumps(files))
""".replace('REMOTE_ROOT', repr(remote_root))
files = json.loads(remote(code, timeout=90))
local = Path(r'D:\MultiModel\jev-defense-four-gpu-20261106\online-evidence-receipts\1793978878359030429\readiness')
local.mkdir(parents=True, exist_ok=False)
for name, encoded in files.items():
    path = local / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle: handle.write(base64.b64decode(encoded))
seal = json.loads((local / 'seal.json').read_bytes())
for name, expected in seal.items():
    assert hashlib.sha256((local / name).read_bytes()).hexdigest() == expected
print(json.dumps({'local_receipt': str(local / 'receipt.json'),
    'receipt_sha256': hashlib.sha256((local / 'receipt.json').read_bytes()).hexdigest(),
    'all_sealed_files_verified': len(seal), 'credentials_copied': False}))
