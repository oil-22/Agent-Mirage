"""Independent GET-only readiness audit, linked to two preserved audit-only repairs."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
GROUP = BASE / 'online-service-group-1793978182501156243'
PREP = BASE / 'online-service-preparation-1793978182501156243'
root = BASE / 'online-readiness-independent-audits' / str(time.time_ns())
root.mkdir(parents=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, value):
    with (root / name).open('x') as handle:
        json.dump(value, handle, indent=2)
def copy_bound(path, name):
    raw = path.read_bytes()
    with (root / name).open('xb') as handle: handle.write(raw)
    return hashlib.sha256(raw).hexdigest()
for name, encoded in AUDIT_SOURCES.items():
    with (root / name).open('xb') as handle: handle.write(base64.b64decode(encoded))
save('prior-audit-only-failures.json', {
    'attempt_1': {'source': 'inspect_online_ready_remote.py',
        'error': 'AssertionError: compared proc_identity entire dictionary rather than fixed identity fields',
        'model_requests': 0, 'GUI_requests': 0, 'two_authenticated_health_GETs_passed': True},
    'attempt_2': {'source': 'inspect_online_ready_remote_v2.py',
        'error': "KeyError: commands; commands are in actual runtime-config, not preparation specification",
        'model_requests': 0, 'GUI_requests': 0, 'two_authenticated_health_GETs_passed': True},
    'scope': 'read-only audit script fixes only; no live service/source/specification changed'})
spec_path = PREP / 'online-specification.json'
assert sha(spec_path) == '3daad6e94681edbcdafd49fb946e3c9f35fec13d42117cd6a3a044edacb6b505'
spec = json.loads(spec_path.read_bytes())
config = json.loads((GROUP / 'runtime-config.json').read_bytes())
assert all(config[key] == value for key, value in spec.items())
assert config['group_root'] == str(GROUP)
source_checks = {}
for namespace, source_root, records in [
    ('native', Path(spec['preflight_source_root']), spec['preflight_source_sha256']),
    ('online', Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/online-services-1793978182501156243'), spec['online_source_sha256'])]:
    for name, expected in records.items():
        actual = sha(source_root / name)
        assert actual == expected
        source_checks[namespace + '/' + name] = actual
assert sha(Path(spec['online_launch_gate'])) == spec['online_launch_gate_sha256']
assert sha(Path(spec['online_plan'])) == spec['online_plan_sha256']
assert spec['online_plan_sha256'] == 'a6e248f730408ab9c5bbaeb72bfa0d392ecf99f247159495273d2b3f5616ef8e'
save('source-checks.json', source_checks)
sys.path.insert(0, str(BASE))
from resource_control import proc_identity, held_locks, gpu_state
lease_path = BASE / 'resource-attempt-20261106-01/lease.json'
lease = json.loads(lease_path.read_bytes())
holder = proc_identity(lease['holder']['pid'])
fields = ('pid', 'uid', 'command', 'start_ticks')
assert all(str(holder[key]) == str(lease['holder'][key]) for key in fields)
assert len(lease['lock_records']) == 9
holder_locks = held_locks(holder['pid'])
assert all(any(row['path'] == wanted['path'] and row['inode'] == wanted['inode'] for row in holder_locks)
           for wanted in lease['lock_records'])
save('holder-identity-and-locks.json', {'identity': holder, 'locks': holder_locks})
workers = {}
expected_loaded = {'primary': '3bc91045fe876f81e8dd7087860a67c11f6c6229a5645cee267563b4e9b84279',
                   'pplx_flash': '61df406f47f47b87d6feedb43b739b3de9f30fc6c3a2286f677b972d6132ab4d'}
for role in ('primary', 'pplx_flash'):
    registered = json.loads((GROUP / 'processes' / (role + '.json')).read_bytes())
    actual = proc_identity(registered['identity']['pid'])
    assert all(str(actual[key]) == str(registered['identity'][key]) for key in fields)
    assert actual['uid'] == 1033 and actual['command'] == ' '.join(config['commands'][role])
    locks = held_locks(actual['pid'])
    assert all(any(row['path'] == wanted['path'] and row['inode'] == wanted['inode'] for row in locks)
               for wanted in lease['lock_records'])
    loaded_path = GROUP / role / 'loaded.json'
    assert sha(loaded_path) == expected_loaded[role]
    loaded = json.loads(loaded_path.read_bytes())
    copy_bound(loaded_path, role + '-loaded.json')
    copy_bound(GROUP / role / 'ready.json', role + '-ready.json')
    process = json.loads((GROUP / role / 'process.json').read_bytes())
    expected_visibility = '4,5,6,7' if role == 'primary' else '7'
    assert process['CUDA_VISIBLE_DEVICES'] == expected_visibility
    expected_devices = ['cuda:0', 'cuda:1', 'cuda:2', 'cuda:3'] if role == 'primary' else ['cuda:0']
    assert loaded['devices'] == expected_devices and loaded['tensor_count'] > 0
    assert loaded['online_plan_sha256'] == spec['online_plan_sha256']
    assert loaded['dtype_elements'].get('torch.bfloat16', 0) > 0
    assert all(key in ('torch.bfloat16', 'torch.int64', 'torch.int32', 'torch.bool')
               for key in loaded['dtype_elements'])
    assert not list((GROUP / role / 'requests').iterdir())
    workers[role] = {'identity': actual, 'locks': locks, 'held_lock_count': len(locks),
        'visible_physical_gpus': expected_visibility, 'loaded_sha256': sha(loaded_path),
        'request_count': 0, 'tensor_count': loaded['tensor_count'],
        'tensor_bytes_by_device': loaded['tensor_bytes_by_device'],
        'dtype_elements': loaded['dtype_elements']}
save('worker-identities-locks-and-load.json', workers)
primary = json.loads((GROUP / 'primary/loaded.json').read_bytes())
runtime = json.loads((GROUP / 'primary/runtime.json').read_bytes())
assert runtime['dtype'] == 'torch.bfloat16' and runtime['backend'] == 'sdpa'
assert runtime['placement'] == 'explicit_asymmetric_18_20_20_6'
assert runtime['history_truncation'] is False and runtime['image_preprocessing_changes'] is False
assert primary['generate_and_judge_inherited_unchanged'] is True
assert primary['actual_state_tensor_count'] == 1184 and primary['native_MTP_not_instantiated'] is True
assert primary['primary_native_class_source_sha256'] == '67cf849081143a998f0e189c551e4b5f532365a055805570747385e400372abb'
assert sha(Path(spec['primary_release']) / 'defense/qwen_backend.py') == spec['primary_backend_sha256']
metadata = {name: sha(Path(spec['primary_model']) / name) for name in runtime['metadata_sha256']}
assert metadata == runtime['metadata_sha256']
expected_runtime = json.loads(Path(spec['primary_expected_runtime']).read_bytes())
assert metadata == expected_runtime['metadata_sha256']
assert runtime['torch'] == expected_runtime['torch'] and runtime['transformers'] == expected_runtime['transformers']
dependency_path = Path(spec['primary_dependency_receipt'])
assert sha(dependency_path) == spec['primary_dependency_receipt_sha256']
dependency = json.loads(dependency_path.read_bytes())
deps = Path(dependency['dependency_root'])
actual_dependencies = {str(path.relative_to(deps)): sha(path) for path in deps.rglob('*')
    if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'}
assert actual_dependencies == dependency['dependency_files']
assert primary['primary_dependency_receipt_sha256'] == sha(dependency_path)
copy_bound(GROUP / 'primary/runtime.json', 'primary-runtime.json')
save('primary-small-file-independent-checks.json', {
    'metadata': metadata, 'dependency_receipt_sha256': sha(dependency_path),
    'dependency_files': actual_dependencies, 'backend_sha256': spec['primary_backend_sha256'],
    'native_class_source_sha256': primary['primary_native_class_source_sha256'],
    'native_class_binding': 'actual loaded audit matches original source/meta identity; no new model instance'})
flash = json.loads((GROUP / 'pplx_flash/loaded.json').read_bytes())
assert flash['revision'] == '9ff7cf9838e59df461c276b7699d56b244d2af58'
assert flash['fast'] is False and flash['questions_per_request'] == 3
assert flash['image_only_neutral_joint_observer'] is True
assert flash['native_decider'] is True and flash['noncausal_full_attention'] is True
assert sha(Path(spec['flash_stable_identity_receipt'])) == spec['flash_stable_identity_receipt_sha256']
assert flash['checkpoint_identity']['stable_identity_sha256'] == spec['flash_stable_identity_receipt_sha256']
flash_source = {name: sha(Path(spec['flash_model']) / name)
                for name in flash['checkpoint_identity']['source_sha256']}
assert flash_source == flash['checkpoint_identity']['source_sha256']
save('flash-source-independent-checks.json', flash_source)
token = Path(spec['token_file']).read_text().strip()
health = {}
for role, port in [('primary', 18127), ('pplx_flash', 18223)]:
    request = urllib.request.Request('http://127.0.0.1:%s/health' % port,
        headers={'Authorization': 'Bearer ' + token}, method='GET')
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        assert response.status == 200
    row = json.loads(raw)
    assert row['phase'] == 'ready_gui' and row['stage'] == 'online_ready'
    state = row['state']
    assert state['phase'] == 'ready' and state['active'] is None and state['next_run_index'] == 0
    assert len(state['runs']) == 4
    assert all(run['status'] == 'not_started' and run['last_decision_index'] == 0 and
        run['calls'] == {'actor': 0, 'judge': 0, 'observe': 0} for run in state['runs'].values())
    with (root / (role + '-health.json')).open('xb') as handle: handle.write(raw)
    health[role] = {'HTTP_status': 200, 'phase': row['phase'], 'stage': row['stage'],
        'sha256': hashlib.sha256(raw).hexdigest()}
resources = gpu_state()
target = {row['uuid'] for row in lease['gpu']}
allowed = {worker['identity']['pid'] for worker in workers.values()}
target_compute = [row for row in resources['compute'] if row['uuid'] in target]
assert all(row['pid'] in allowed for row in target_compute)
assert not (GROUP / 'launcher-failure.json').exists()
assert all(not list((GROUP / role / 'requests').iterdir()) for role in workers)
copy_bound(GROUP / 'online-state.json', 'online-state.json')
save('current-resources.json', resources)
receipt = {'status': 'passed', 'scope': 'new online model services ready; no bridge/GUI/model request by this audit',
    'group': str(GROUP), 'specification': str(spec_path), 'specification_sha256': sha(spec_path),
    'runtime_config_sha256': sha(GROUP / 'runtime-config.json'), 'lease_sha256': sha(lease_path),
    'online_launch_gate_sha256': spec['online_launch_gate_sha256'],
    'plan_sha256': spec['online_plan_sha256'], 'source_checks_sha256': sha(root / 'source-checks.json'),
    'holder_actual_identity_and_all9locks_verified': True,
    'both_worker_actual_identity_and_all9locks_verified': True,
    'both_authenticated_health_ready': True, 'full_native_source_metadata_dependency_bindings': True,
    'actual_loaded_CUDA_tensor_audits_bound': True, 'target_foreign_compute_count': 0,
    'workers': {role: {key: value for key, value in worker.items() if key != 'locks'}
                for role, worker in workers.items()}, 'health': health,
    'all_four_runs_not_started': True, 'active_run': None,
    'model_requests': 0, 'GUI_requests': 0, 'POST_requests': 0,
    'prior_audit_only_failures_preserved': True, 'no_live_service_spec_or_source_modified': True,
    'new_audit_root': str(root)}
save('receipt.json', receipt)
save('seal.json', {str(path.relative_to(root)): sha(path) for path in root.rglob('*') if path.is_file()})
print(json.dumps({'receipt': str(root / 'receipt.json'), 'receipt_sha256': sha(root / 'receipt.json'),
    'seal_sha256': sha(root / 'seal.json'), 'status': 'passed', 'workers': receipt['workers'],
    'model_requests': 0, 'GUI_requests': 0, 'both_authenticated_health_ready': True,
    'all_four_runs_not_started': True}))
