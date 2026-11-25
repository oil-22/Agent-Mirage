"""Seal a new CPU-only GUI transport preparation; never starts a service."""
import hashlib
import json
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import time

base = Path(__file__).resolve().parent
previous = sorted((base / 'cpu-evidence').glob('*/receipt.json'))
root = base / 'cpu-evidence' / str(time.time_ns()); root.mkdir(parents=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
parent_files = {name: sha(base.parent / name) for name in
    ('preflight_service.py', 'four_gpu_contract.py', 'launch_preflight_group.py', 'layout.proposed.json')}
(root / 'source').mkdir()
for source in base.glob('*.py'):
    shutil.copyfile(source, root / 'source' / source.name)
    py_compile.compile(str(source), doraise=True)
result = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_online_contract.py'],
    cwd=base, capture_output=True, text=True)
(root / 'test-output.txt').write_text(result.stdout + result.stderr, encoding='utf8')
assert parent_files == {name: sha(base.parent / name) for name in parent_files}
receipt = {'scope': 'new finite GUI service CPU admission/journal/syntax only',
    'test_returncode': result.returncode, 'tests_passed': 25 if result.returncode == 0 else None,
    'native_preflight_sources_unchanged': parent_files, 'new_online_sources': {
        path.name: sha(path) for path in base.glob('*.py')}, 'GPU_allocations': 0,
    'model_calls': 0, 'GUI_actions': 0, 'online_started': False,
    'original_generation_methods_reused': True, 'new_independent_group_and_token_required': True}
if previous: receipt.update(previous_receipt=str(previous[-1]), previous_receipt_sha256=sha(previous[-1]))
(root / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
(root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)): sha(p) for p in root.rglob('*')
    if p.is_file()}, indent=2), encoding='utf8')
print(json.dumps({'root': str(root), **receipt}))
if result.returncode: raise SystemExit(result.returncode)
