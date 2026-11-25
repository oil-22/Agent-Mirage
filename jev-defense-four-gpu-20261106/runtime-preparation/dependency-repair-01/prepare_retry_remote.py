"""Prepare a reviewed once-only technical retry command. Never submit or launch."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
stamp = str(time.time_ns())
root = BASE / ('capacity-retry-preparation-' + stamp); root.mkdir()
runtime = BASE / 'runtime-preparation' / ('technical-retry-' + stamp); runtime.mkdir()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as handle: json.dump(value, handle, indent=2)


for relative, content in SOURCE_FILES.items():
    path = runtime / relative; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle: handle.write(base64.b64decode(content))
parent = BASE / 'model-preflight-group-1793975204991293922'
terminal = parent / 'terminal-manifest.json'
assert sha(terminal) == 'f8ab779ff8449a34acde7394958fef9c5081dccf69d0e93572b70fad9c8ec12f'
for name, expected in json.loads(terminal.read_bytes()).items(): assert sha(parent / name) == expected
old = list((parent / 'primary/requests').glob('*'))
assert len(old) == 1
assert sha(old[0] / 'request.json') == '921d1df12734b116f3a920e6caa769c9b148990c2efb6439febe9c47231e6a92'
assert not (old[0] / 'generation.json').exists()
assert json.loads((old[0] / 'forward-trace.json').read_bytes()) == []
assert 'ModuleNotFoundError' in json.loads((old[0] / 'failure.json').read_bytes())['error']
assert 'lmformatenforcer' in json.loads((old[0] / 'failure.json').read_bytes())['error']
observer = BASE / 'observer-real-preflight-20261106-01/summary.json'
assert sha(observer) == '943327883b0239e49738e209f35e559ec42eaaa10ba4cb6af915cf4853c52466'
summary = json.loads(observer.read_bytes())
assert summary['complete_replies'] == 9
dep = BASE / 'dependency-cpu-checks/1793975726799714627/receipt.json'
assert sha(dep) == '711f6c45f763d2248cc1b623ce26c926675d2c39ade36f1639eafe95826ff989'
proof = {'scope': 'one linked original full-input technical retry, no completed observer reruns',
    'parent_group': str(parent), 'parent_terminal_manifest_sha256': sha(terminal),
    'failed_primary_request': str(old[0]), 'same_request_wire_sha256': sha(old[0] / 'request.json'),
    'prior_primary_HTTP_attempts': 1, 'prior_primary_actual_model_forwards': 0,
    'new_primary_attempt_cap': 1, 'new_helper_attempt_cap': 0,
    'completed_observer_summary': str(observer), 'completed_observer_summary_sha256': sha(observer),
    'completed_observer_replies_not_reexecuted': 9, 'dependency_cpu_receipt': str(dep),
    'dependency_cpu_receipt_sha256': sha(dep), 'GPU_allocations_by_preparation': 0,
    'model_calls_by_preparation': 0, 'GUI_actions': 0, 'submitted_to_holder': False}
save(root / 'technical-retry-proof.json', proof)
resident = root / 'resident-only-admission.json'
save(resident, {'mode': 'resident_only', 'max_new_calls': 0, 'GUI_actions': 0,
    'requests': [], 'completed_terminal': str(observer), 'completed_terminal_sha256': sha(observer),
    'reason': 'retain actual co-residency for main capacity without rerunning any of nine completed observer controls'})
previous_paths = BASE / 'reviewed-launch-1793975204954628374/paths.json'
paths = json.loads(previous_paths.read_bytes())
paths.update(primary_dependency_receipt=str(dep), primary_dependency_receipt_sha256=sha(dep),
             flash_admission=str(resident), token_file=str(root / 'transport.token'))
token = root / 'transport.token'
with token.open('x') as handle: handle.write(secrets.token_hex(32))
token.chmod(0o600)
save(root / 'paths.json', paths)
command = ['/opt/whz/conda-envs/webmall-vlm/bin/python', str(runtime / 'prepare_launch_spec.py'),
           '--paths', str(root / 'paths.json'), '--output', str(root / 'launch-specification.json')]
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    env=dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1'))
(root / 'spec-stdout.txt').write_bytes(result.stdout); (root / 'spec-stderr.txt').write_bytes(result.stderr)
assert result.returncode == 0, result.stderr.decode()
group = BASE / ('model-capacity-technical-retry-' + stamp)
spec = root / 'launch-specification.json'
proposal = {'action': 'launch', 'argv': ['/opt/whz/conda-envs/webmall-vlm/bin/python',
    str(runtime / 'launch_preflight_group.py'), '--root', str(group), '--spec', str(spec),
    '--spec-sha256', sha(spec)], 'script_sha256': sha(runtime / 'launch_preflight_group.py')}
save(root / 'holder-command.proposed.json', proposal)
report = {'root': str(root), 'runtime_source_root': str(runtime), 'new_group': str(group),
    'paths': str(root / 'paths.json'), 'paths_sha256': sha(root / 'paths.json'),
    'spec': str(spec), 'spec_sha256': sha(spec),
    'proposed_command': str(root / 'holder-command.proposed.json'),
    'proposed_command_sha256': sha(root / 'holder-command.proposed.json'),
    'source_sha256': {name: sha(runtime / name) for name in
        ('preflight_service.py', 'four_gpu_contract.py', 'launch_preflight_group.py', 'prepare_launch_spec.py')},
    'resident_admission_sha256': sha(resident), 'technical_retry_proof_sha256': sha(root / 'technical-retry-proof.json'),
    'submitted_to_holder': False, 'model_calls': 0, 'GUI_actions': 0}
save(root / 'receipt.json', report)
# Do not copy private token bytes into an ordinary evidence bundle. Its existence
# and mode are transport setup; its SHA is deliberately not a model input claim.
save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file() and p != token})
print(json.dumps(report))
