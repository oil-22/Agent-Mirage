"""Classify one preserved completed-stage control exit; never alter exit codes.

This accepts only this known -SIGUSR1/0 lifecycle case after the independent EOS
capacity proof, complete stopped receipts, immutable request seals and no remaining
compute. It cannot approve an inference failure or an unfinished request.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
CAPACITY = BASE / 'primary-capacity-independent-audits/1793977082419248935/receipt.json'
CAPACITY_SHA = '5a89138010f8cf005cbcd03bc2a4b249af0e253178666388fb17652bb0571fb8'
WORKER_SHA = '482d98e9674d0e568106b9ebfadd5e7a3a61f3ce6d6ba26f7d36b453e6b034aa'
LAUNCHER_SHA = '6847f75f2733172ad0eece2568c3abd3e9655357d82182b63046db3dab41d54e'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as handle: json.dump(value, handle, indent=2)


def verify(root, filename='seal.json'):
    for relative, expected in json.loads((root / filename).read_bytes()).items():
        if sha(root / relative) != expected: raise RuntimeError('Immutable SHA mismatch: ' + str(root / relative))


def run(a, root):
    group = a.group
    verify(group, 'terminal-manifest.json')
    verify(CAPACITY.parent)
    assert sha(CAPACITY) == CAPACITY_SHA
    capacity = json.loads(CAPACITY.read_bytes())
    assert capacity['group'] == str(group)
    assert all(capacity[key] is True for key in ('capacity_passed', 'full_input_preserved',
        'actual_input_forward_audited', 'output_budget_4096_preserved', 'natural_EOS'))
    config = json.loads((group / 'runtime-config.json').read_bytes())
    native = Path(config['commands']['primary'][2]).parent
    launcher, worker = native / 'launch_preflight_group.py', native / 'preflight_service.py'
    assert sha(launcher) == LAUNCHER_SHA and sha(worker) == WORKER_SHA
    tree = ast.parse(launcher.read_text())
    stop = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'stop_owned')
    signal_calls = [node for node in ast.walk(stop) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute) and node.func.attr == 'kill'
        and len(node.args) == 2 and isinstance(node.args[1], ast.Attribute)
        and node.args[1].attr == 'SIGUSR1']
    assert len(signal_calls) == 1
    exited = json.loads((group / 'exit.json').read_bytes())
    codes = {row['role']: row['exit_code'] for row in exited['workers']}
    assert codes == {'primary': -10, 'pplx_flash': 0}
    residency = json.loads((CAPACITY.parent / 'actual-residency-after.json').read_bytes())
    calls = {}
    original_processes_no_longer_live = {}
    for role in ('primary', 'pplx_flash'):
        stopped = json.loads((group / role / 'stopped.json').read_bytes())
        calls[role] = stopped['calls']
        assert stopped['time'] <= exited['time']
        identity = next(row['identity'] for row in exited['workers'] if row['role'] == role)
        assert identity == residency['workers'][role]['identity']
        proc = Path('/proc') / str(identity['pid'])
        if proc.exists():
            current_cmd = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip()
            current_start = (proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]
            assert current_cmd != identity['command'] or current_start != identity['start_ticks']
            original_processes_no_longer_live[role] = 'PID reused with different identity'
        else:
            original_processes_no_longer_live[role] = 'PID absent'
        assert (group / 'stop-requested.json').stat().st_mtime_ns <= (group / role / 'stopped.json').stat().st_mtime_ns
        (root / (role + '-stopped.json')).write_bytes((group / role / 'stopped.json').read_bytes())
    assert calls == {'primary': 1, 'pplx_flash': 0}
    primary = list((group / 'primary/requests').glob('*'))
    helper = list((group / 'pplx_flash/requests').glob('*'))
    assert len(primary) == 1 and helper == []
    for request in primary:
        verify(request)
        assert not (request / 'failure.json').exists() and (request / 'response.json').exists()
        assert (request / 'generation.json').exists() and (request / 'forward-trace.json').exists()
        assert sha(request / 'seal.json') == capacity['request_seal_sha256']
        assert sha(request / 'request.json') == capacity['original_wire_sha256']
        assert (request / 'response.json').stat().st_mtime_ns <= (group / 'primary/stopped.json').stat().st_mtime_ns
        generation = json.loads((request / 'generation.json').read_bytes())
        eos = generation['generation_config']['eos_token_id']
        eos = eos if isinstance(eos, list) else [eos]
        assert not generation['hit_output_cap'] and generation['generated_ids'][-1] in eos
        assert len(generation['generated_ids']) == capacity['output_tokens'] == 1102
        assert len(generation['input_ids']) == capacity['input_tokens'] == 15720
    lease_flag = config['commands']['primary'].index('--lease')
    lease = json.loads(Path(config['commands']['primary'][lease_flag + 1]).read_bytes())
    target = {row['uuid'] for row in lease['gpu']}
    assert {row['index'] for row in lease['gpu']} == {4, 5, 6, 7}
    raw = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
        '--format=csv,noheader,nounits'], text=True)
    remaining = [line for line in raw.splitlines() if line.split(',')[0].strip() in target]
    assert remaining == []
    for name, path in [('original-exit.json', group / 'exit.json'),
        ('original-terminal-manifest.json', group / 'terminal-manifest.json'),
        ('original-stop-requested.json', group / 'stop-requested.json'),
        ('original-launcher-source.py', launcher), ('original-worker-source.py', worker),
        ('original-capacity-audit.json', CAPACITY)]:
        (root / name).write_bytes(path.read_bytes())
    return {'status': 'passed', 'classification': 'completed_stage_control_exit_after_stopped_receipts',
        'infrastructure_only': True, 'accepted_for_completed_stage_only': True,
        'no_real_model_failure_bypassed': True, 'group': str(group),
        'terminal_manifest_sha256': sha(group / 'terminal-manifest.json'),
        'actual_worker_exit_codes': codes, 'both_stopped_before_exit': True,
        'exact_calls_primary1_helper0': True, 'all_existing_inference_requests_complete': True,
        'capacity_natural_EOS_and_forward_audit_preserved': True, 'request_seals_unchanged': True,
        'pending_request_count': 0, 'target_compute_process_count': 0,
        'primary_request_count': 1, 'helper_request_count': 0,
        'capacity_audit_receipt': str(CAPACITY), 'capacity_audit_receipt_sha256': CAPACITY_SHA,
        'old_launcher_source_sha256': LAUNCHER_SHA, 'old_worker_source_sha256': WORKER_SHA,
        'old_launcher_sends_worker_USR1': True, 'original_exit_codes_preserved': True,
        'original_processes_no_longer_live': original_processes_no_longer_live,
        'nvidia_compute_raw': raw, 'GPU_allocations_by_auditor': 0, 'model_requests_by_auditor': 0,
        'scope': 'completed capacity-stage shutdown infrastructure only; not semantic or GUI success',
        'mechanism_limit': 'Old source sends worker USR1 after stop marker; -10 is SIGUSR1. This is consistent with delivery during teardown after completed stopped receipts; exact kernel delivery timing was not recorded.'}


def main(a):
    root = a.output_root / str(time.time_ns()); root.mkdir(parents=True)
    (root / 'auditor-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        result = run(a, root); save(root / 'receipt.json', result)
        print(json.dumps({'root': str(root), **result}))
    except BaseException:
        save(root / 'failure.json', {'status': 'shutdown_audit_failed', 'traceback': traceback.format_exc(),
             'model_requests_by_auditor': 0, 'GPU_allocations_by_auditor': 0})
        raise
    finally:
        save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    main(parser.parse_args())
