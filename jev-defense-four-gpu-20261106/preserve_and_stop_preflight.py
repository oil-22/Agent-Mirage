"""Preserve the finished9 observer replies and pre-forward technical failure."""
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


assert os.getuid() == 1033
group = BASE / 'model-preflight-group-1793975204991293922'
launcher = json.loads((group / 'process.json').read_bytes())
actual = exact_identity(launcher)
workers = [json.loads((group / (role + '-launch.json')).read_bytes())['identity']
           for role in ['primary', 'pplx_flash']]
for worker in workers:
    exact_identity(worker)
client = BASE / 'observer-real-preflight-20261106-01'
summary = json.loads((client / 'summary.json').read_bytes())
assert summary['terminal'] is True and summary['status'] == 'completed'
assert summary['complete_replies'] == summary['max_new_flash_calls'] == 9
for role, count in [('primary', 1), ('pplx_flash', 9)]:
    requests = [path for path in (group / role / 'requests').iterdir() if path.is_dir()]
    assert len(requests) == count
    for request in requests:
        manifest = json.loads((request / 'seal.json').read_bytes())
        assert all(sha(request / name) == expected for name, expected in manifest.items())
        assert (request / ('failure.json' if role == 'primary' else 'response.json')).exists()
        if role == 'primary':
            assert json.loads((request / 'forward-trace.json').read_bytes()) == []
            assert not (request / 'generation.json').exists()
            assert 'No module named' in json.loads((request / 'failure.json').read_bytes())['error']
before = {str(path.relative_to(group)): sha(path) for path in group.rglob('*') if path.is_file()}
root = BASE / ('preflight-failure-preservation-' + str(time.time_ns()))
root.mkdir()
snapshot = root / 'snapshot'
shutil.copytree(group, snapshot)
assert before == {str(path.relative_to(snapshot)): sha(path) for path in snapshot.rglob('*') if path.is_file()}
assert before == {str(path.relative_to(group)): sha(path) for path in group.rglob('*') if path.is_file()}
save(root / 'before-stop.json', {'time': time.time(), 'launcher': actual,
    'workers': workers, 'snapshot_files': len(before), 'snapshot_manifest': before,
    'observer9_completed_never_rerun': True, 'primary_failure_before_any_forward': True,
    'original_inputs_and_results_unchanged': True})
exact_identity(launcher)
os.kill(launcher['pid'], signal.SIGUSR1)
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    live = [row for row in [launcher] + workers if Path('/proc', str(row['pid'])).exists()
            and proc_identity(row['pid'])['state'] not in {'Z', 'X'}]
    if not live:
        break
    time.sleep(0.25)
else:
    raise RuntimeError('Owned group has not exited; preserve and inspect, no broad kill')
terminal = group / 'terminal-manifest.json'
manifest = json.loads(terminal.read_bytes())
assert all(sha(group / name) == expected for name, expected in manifest.items())
lease = json.loads((BASE / 'resource-attempt-20261106-01/lease.json').read_bytes())
state = gpu_state()
uuids = {row['uuid'] for row in lease['gpu']}
assert not any(row['uuid'] in uuids for row in state['compute'])
save(root / 'receipt.json', {'time': time.time(), 'group': str(group),
    'terminal_manifest': str(terminal), 'terminal_manifest_sha256': sha(terminal),
    'terminal_sealed_files': len(manifest), 'all_worker_processes_exited': True,
    'target_GPU_compute_empty': True, 'GPU_state': state,
    'observer_terminal': str(client / 'summary.json'),
    'observer_terminal_sha256': sha(client / 'summary.json'),
    'observer_actual_forwards': 9, 'primary_actual_forwards': 0,
    'primary_admitted_failed_requests': 1, 'GUI_actions': 0,
    'paid_API_calls': 0, 'resources_still_held_by_original_holder': True})
save(root / 'seal.json', {str(path.relative_to(root)): sha(path)
    for path in root.rglob('*') if path.is_file()})
print(json.dumps({'root': str(root), 'terminal_manifest_sha256': sha(terminal),
    'observer_terminal_sha256': sha(client / 'summary.json'),
    'observer_forwards': 9, 'primary_forwards': 0, 'all_workers_exited': True}), flush=True)
