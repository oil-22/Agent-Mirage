"""Finish a quiescent owned worker shutdown after two graceful signals failed."""
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
from resource_control import exact_identity, gpu_state, proc_identity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, indent=2)


def alive(row):
    return Path('/proc', str(row['pid'])).exists() and proc_identity(row['pid'])['state'] not in {'Z', 'X'}


assert os.getuid() == 1033
group = BASE / 'model-preflight-group-1793975204991293922'
worker = json.loads((group / 'pplx_flash-launch.json').read_bytes())['identity']
exact_identity(worker)
requests = [p for p in (group / 'pplx_flash/requests').iterdir() if p.is_dir()]
assert len(requests) == 9
for request in requests:
    assert (request / 'response.json').exists()
    manifest = json.loads((request / 'seal.json').read_bytes())
    assert all(sha(request / name) == value for name, value in manifest.items())
for name in ['/proc/net/tcp', '/proc/net/tcp6']:
    for line in Path(name).read_text().splitlines()[1:]:
        fields = line.split()
        assert not (int(fields[1].split(':')[1], 16) == 18223 and fields[3] == '01'), 'Connected client; do not stop'
root = BASE / ('controlled-shutdown-' + str(time.time_ns()))
root.mkdir()
before = {str(p.relative_to(group)): sha(p) for p in group.rglob('*') if p.is_file()}
shutil.copytree(group, root / 'snapshot')
assert before == {str(p.relative_to(root / 'snapshot')): sha(p)
                  for p in (root / 'snapshot').rglob('*') if p.is_file()}
save(root / 'before-signals.json', {'worker': worker, 'quiescent_completed_replies': 9,
    'pending_requests': 0, 'two_prior_SIGUSR1_did_not_stop_worker': True,
    'original_snapshot_files': len(before), 'time': time.time()})
signals = []
for sig in [signal.SIGTERM, signal.SIGKILL]:
    if not alive(worker):
        break
    exact_identity(worker)
    os.kill(worker['pid'], sig)
    signals.append({'signal': sig.name, 'time': time.time()})
    deadline = time.monotonic() + 10
    while alive(worker) and time.monotonic() < deadline:
        time.sleep(0.25)
assert not alive(worker), 'Owned process still live; no relaunch'
terminal = group / 'terminal-manifest.json'
deadline = time.monotonic() + 10
while not terminal.exists() and time.monotonic() < deadline:
    time.sleep(0.25)
manifest = json.loads(terminal.read_bytes())
assert all(sha(group / name) == value for name, value in manifest.items())
state = gpu_state()
lease = json.loads((BASE / 'resource-attempt-20261106-01/lease.json').read_bytes())
uuids = {r['uuid'] for r in lease['gpu']}
assert not any(row['uuid'] in uuids for row in state['compute'])
observer = BASE / 'observer-real-preflight-20261106-01/summary.json'
receipt = {'time': time.time(), 'group': str(group), 'controlled_signals': signals,
    'natural_worker_exit_claim': False, 'terminal_manifest': str(terminal),
    'terminal_manifest_sha256': sha(terminal), 'sealed_files': len(manifest),
    'all_owned_model_workers_exited': True, 'target_compute_empty': True,
    'observer_actual_forwards': 9, 'primary_actual_forwards': 0,
    'primary_pre_forward_dependency_failure': True,
    'observer_terminal': str(observer), 'observer_terminal_sha256': sha(observer),
    'GUI_actions': 0, 'all_original_results_preserved': True,
    'holder_and_foreign_processes_signalled': False}
save(root / 'receipt.json', receipt)
save(root / 'seal.json', {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()})
print(json.dumps({'root': str(root), **receipt}), flush=True)
