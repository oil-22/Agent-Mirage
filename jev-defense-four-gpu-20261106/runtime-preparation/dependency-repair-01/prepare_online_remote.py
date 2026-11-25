"""Upload new reviewed online sources and construct a once-only service proposal.

No submission, model load or model/GUI request. LOCAL_FILES is supplied by the
local sender, binding exact bytes from the CPU-sealed source and observer review.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
stamp = str(time.time_ns())
root = BASE / ('online-service-preparation-' + stamp)
native = BASE / 'runtime-preparation' / ('online-native-' + stamp)
online = BASE / 'runtime-preparation' / ('online-services-' + stamp)
root.mkdir(); native.mkdir(); online.mkdir()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as handle: json.dump(value, handle, indent=2)


for namespace, records in LOCAL_FILES.items():
    target = {'native': native, 'online': online, 'evidence': root / 'evidence'}[namespace]
    for relative, content in records.items():
        path = target / relative; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle: handle.write(base64.b64decode(content))
sys.path.insert(0, str(BASE))
from resource_control import proc_identity, held_locks, gpu_state
holder_root = BASE / 'resource-attempt-20261106-01'
lease = json.loads((holder_root / 'lease.json').read_bytes())
actual = proc_identity(lease['holder']['pid'])
assert all(str(actual[key]) == str(lease['holder'][key]) for key in ('pid', 'uid', 'command', 'start_ticks'))
locks = held_locks(actual['pid'])
assert len(lease['lock_records']) == 9
assert all(any(row['path'] == wanted['path'] and row['inode'] == wanted['inode'] for row in locks)
           for wanted in lease['lock_records'])
resources = gpu_state(); target = {row['uuid'] for row in lease['gpu']}
assert not any(row['uuid'] in target for row in resources['compute'])
assert all(resources['gpu'][i]['free_mib'] >= 23000 for i in (4, 5, 6, 7))
save(root / 'resource-before-proposal.json', {'holder': actual, 'held_lock_count': 9, 'resources': resources})
capacity = BASE / 'primary-capacity-independent-audits/1793977082419248935/receipt.json'
observer = root / 'evidence/observer-review/review.json'
terminal = BASE / 'model-capacity-technical-retry-1793976389484142969/terminal-manifest.json'
shutdown = BASE / 'completed-stage-shutdown-audits/1793977527152891258/receipt.json'
plan = root / 'evidence/gui-plan.json'
assert sha(capacity) == '5a89138010f8cf005cbcd03bc2a4b249af0e253178666388fb17652bb0571fb8'
assert sha(observer) == 'fa0140293d55d9525f2558fc17d1214931bf7a718b6e78c3eb8b91208c13ba26'
assert sha(terminal) == '2ccd1efc907a32f5477f0a3162bc2e6ba5aa7141e36e8534517f1e5c0c24c786'
assert sha(shutdown) == '296c82ba471af79e400393f601cf1dfb1cf8d5e9dde9365d999a23e4bb8b4ca6'
assert sha(plan) == 'a6e248f730408ab9c5bbaeb72bfa0d392ecf99f247159495273d2b3f5616ef8e'
assert sha(native / 'launch_preflight_group.py') == '6e973c4c16ccd9f75e6e308c32c3d73a12d27ea762cdc748dd6d0665ef6fae27'
assert sha(online / 'launch_online_group.py') == 'ae6723c8527285a81a89792a11a9e7cd0cd9e7f141674bb52edd351437834def'
gate = root / 'online-launch-gate.json'
save(gate, {'stage': 'online_gui_authorization', 'approved': True, 'once_only': True,
    'authorization_scope': 'Root explicitly authorized this independent online service load only; bridge and GUI remain separately coordinated by root.',
    'online_plan_sha256': sha(plan),
    'observer_contract_sha256': '98a3adb4ecb4939bb500603121e21587d454a99233ee14a32ddca8f68fa35054',
    'preflight_terminal_manifest': str(terminal), 'preflight_terminal_manifest_sha256': sha(terminal),
    'evidence': {'primary_full_input_capacity': {'path': str(capacity), 'sha256': sha(capacity)},
        'observer_independent_review': {'path': str(observer), 'sha256': sha(observer)}},
    'completed_stage_shutdown_audit': {'path': str(shutdown), 'sha256': sha(shutdown)},
    'model_requests_by_preparation': 0, 'GUI_requests_by_preparation': 0})
token = BASE / 'transport-online-01/private.token'; token.parent.mkdir(exist_ok=True)
with token.open('x') as handle: handle.write(secrets.token_hex(32))
token.chmod(0o600)
previous = BASE / 'capacity-retry-preparation-1793976389484142969/launch-specification.json'
spec = root / 'online-specification.json'
command = ['/opt/whz/conda-envs/webmall-vlm/bin/python', str(online / 'prepare_online_spec.py'),
    '--preflight-spec', str(previous), '--native-source-root', str(native),
    '--plan', str(plan), '--gate', str(gate), '--token', str(token), '--output', str(spec)]
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    env=dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1'))
(root / 'spec-stdout.txt').write_bytes(result.stdout); (root / 'spec-stderr.txt').write_bytes(result.stderr)
assert result.returncode == 0, result.stderr.decode()
sys.path[:0] = [str(online), str(native)]
from launch_online_group import verify_gate
from online_contract import validate_plan
concrete = json.loads(spec.read_bytes())
verify_gate(concrete); runs = validate_plan(json.loads(plan.read_bytes()))
assert [row['caps']['observe'] for row in runs.values()] == [0, 60, 0, 60]
assert concrete['preflight_source_sha256']['launch_preflight_group.py'] == sha(native / 'launch_preflight_group.py')
group = BASE / ('online-service-group-' + stamp)
proposal = {'action': 'launch', 'argv': ['/opt/whz/conda-envs/webmall-vlm/bin/python',
    str(online / 'launch_online_group.py'), '--root', str(group), '--spec', str(spec),
    '--spec-sha256', sha(spec)], 'script_sha256': sha(online / 'launch_online_group.py')}
proposed = root / 'holder-command.proposed.json'; save(proposed, proposal)
report = {'root': str(root), 'native_source_root': str(native), 'online_source_root': str(online),
    'group': str(group), 'spec': str(spec), 'spec_sha256': sha(spec),
    'gate': str(gate), 'gate_sha256': sha(gate),
    'proposed_command': str(proposed), 'proposed_command_sha256': sha(proposed),
    'source_sha256': {'native/' + name: sha(native / name) for name in
        ('preflight_service.py', 'four_gpu_contract.py', 'launch_preflight_group.py')},
    'online_source_sha256': {name: sha(online / name) for name in
        ('online_service.py', 'online_contract.py', 'launch_online_group.py', 'prepare_online_spec.py')},
    'run_order': list(runs), 'per_run_caps': {key: row['caps'] for key, row in runs.items()},
    'new_private_token_created_remote_only': True, 'private_token_mode': oct(token.stat().st_mode & 0o777),
    'holder_identity_and_nine_locks_verified': True, 'target_compute_empty_before_proposal': True,
    'submitted_to_holder': False, 'model_requests': 0, 'GUI_requests': 0, 'bridge_started': False}
save(root / 'receipt.json', report)
save(root / 'seal.json', {str(path.relative_to(root)): sha(path) for path in root.rglob('*') if path.is_file()})
print(json.dumps(report))
