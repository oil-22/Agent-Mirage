"""Preserve a completed finite model group, then request a clean owned stop."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
sys.path.insert(0, str(BASE))
from resource_control import exact_identity, proc_identity, gpu_state


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, indent=2)


parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, required=True)
a = parser.parse_args()
assert os.getuid() == 1033 and a.root.resolve().is_relative_to(BASE)
assert not (a.root / 'exit.json').exists(), 'Already exited; inspect terminal instead'
config = json.loads((a.root / 'runtime-config.json').read_bytes())
launcher = json.loads((a.root / 'process.json').read_bytes())
exact_identity(launcher)
workers = []
for role in ['primary', 'pplx_flash']:
    worker = json.loads((a.root / (role + '-launch.json')).read_bytes())['identity']
    exact_identity(worker)
    assert (a.root / role / 'ready.json').exists()
    for request in (a.root / role / 'requests').iterdir():
        if not request.is_dir():
            continue
        assert (request / 'response.json').exists() and not (request / 'failure.json').exists()
        manifest = json.loads((request / 'seal.json').read_bytes())
        assert all(sha(request / name) == value for name, value in manifest.items())
    workers.append(worker)
before = {str(path.relative_to(a.root)): sha(path) for path in a.root.rglob('*') if path.is_file()}
preserved = BASE / ('completed-group-preservation-' + str(time.time_ns()))
preserved.mkdir()
shutil.copytree(a.root, preserved / 'snapshot')
assert before == {str(path.relative_to(preserved / 'snapshot')): sha(path)
                  for path in (preserved / 'snapshot').rglob('*') if path.is_file()}
assert before == {str(path.relative_to(a.root)): sha(path) for path in a.root.rglob('*') if path.is_file()}
save(preserved / 'before-stop.json', {'group': str(a.root), 'launcher': launcher,
    'workers': workers, 'all_requests_complete_and_sealed': True, 'files': before,
    'time': time.time()})
save(a.root / 'stop-requested.json', {'reason': 'finite stage completed and audited', 'time': time.time()})
exact_identity(launcher)
os.kill(launcher['pid'], signal.SIGUSR1)
deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    live = [row for row in [launcher] + workers if Path('/proc', str(row['pid'])).exists()
            and proc_identity(row['pid'])['state'] not in {'Z', 'X'}]
    if not live and (a.root / 'terminal-manifest.json').exists():
        break
    time.sleep(0.25)
else:
    raise RuntimeError('Clean completed-group stop incomplete; inspect without relaunch')
terminal = a.root / 'terminal-manifest.json'
manifest = json.loads(terminal.read_bytes())
assert all(sha(a.root / name) == value for name, value in manifest.items())
exit_record = json.loads((a.root / 'exit.json').read_bytes())
assert all(row['exit_code'] == 0 for row in exit_record['workers'])
state = gpu_state()
lease = json.loads((BASE / 'resource-attempt-20261106-01/lease.json').read_bytes())
uuids = {row['uuid'] for row in lease['gpu']}
assert not any(row['uuid'] in uuids for row in state['compute'])
result = {'group': str(a.root), 'time': time.time(),
    'terminal_manifest': str(terminal), 'terminal_manifest_sha256': sha(terminal),
    'sealed_files': len(manifest), 'all_worker_exit_codes_zero': True,
    'target_compute_empty': True, 'holder_untouched': True, 'GUI_actions': 0}
save(preserved / 'receipt.json', result)
save(preserved / 'seal.json', {str(path.relative_to(preserved)): sha(path)
    for path in preserved.rglob('*') if path.is_file()})
print(json.dumps({'preservation_root': str(preserved), **result}), flush=True)
