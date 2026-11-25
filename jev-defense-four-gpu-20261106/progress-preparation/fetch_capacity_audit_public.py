"""Read-only public terminal audit export; no HTTP or model calls."""
import base64
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

STAMP = '1793985058235255298'
EXPECTED = 'fc5919611dc79e478684cbffc226cd98e40285b645f856029c694ad0173be366'
code = r'''
import base64,hashlib,json
from pathlib import Path
root=Path('/home/researcher/jev-defense-four-gpu-20261106/single-capacity-independent-audits/1793985058235255298')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'receipt.json')=='fc5919611dc79e478684cbffc226cd98e40285b645f856029c694ad0173be366'
seal=json.loads((root/'seal.json').read_bytes())
for name,expected in seal.items():assert sha(root/name)==expected
selected=['receipt.json','seal.json','copied-file-bindings.json',
 'original-service-group/terminal-manifest.json','original-service-group/exit.json',
 'original-service-group/runtime-config.json','original-service-group/launch-specification.json',
 'original-service-group/primary/loaded.json','original-service-group/pplx_flash/loaded.json',
 'original-service-group/primary-launch.json','original-service-group/pplx_flash-launch.json',
 'preparation-public/launch-specification.reviewed.json','preparation-public/layout.json',
 'actual-runtime-source/preflight_service.py','actual-runtime-source/four_gpu_contract.py',
 'actual-runtime-source/marker_stop_helpers.py']
assert not any('token'in Path(name).name.lower()or 'private'in name.lower()for name in selected)
files={name:base64.b64encode((root/name).read_bytes()).decode()for name in selected}
print(json.dumps({'root':str(root),'remote_full_seal_verified':True,'seal_files':len(seal),
 'files':files,'HTTP_model_GUI_calls':0}))
'''
result = json.loads(remote(code, timeout=180, host='3090'))
target = Path(__file__).parents[1] / 'single-capacity-independent-audits' / STAMP
target.mkdir(parents=True, exist_ok=False)
seal = json.loads(base64.b64decode(result['files']['seal.json']))
for name, encoded in result.pop('files').items():
    raw = base64.b64decode(encoded)
    if name != 'seal.json':
        assert hashlib.sha256(raw).hexdigest() == seal[name]
    path = target / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)
assert hashlib.sha256((target / 'receipt.json').read_bytes()).hexdigest() == EXPECTED
with (target / 'local-transfer-receipt.json').open('x') as handle:
    json.dump({**result, 'selected_public_files_copied':16,
        'local_copies_all_SHA_verified':True, 'private_tokens_exported':False},handle,indent=2)
receipt=json.loads((target/'receipt.json').read_bytes())
print(json.dumps({'local':str(target),'receipt_sha256':EXPECTED,
    'per_device_primary_generation_memory':receipt['per_device_primary_generation_memory'],
    'cost_accounting':receipt['cost_accounting']}))
