"""Independent guards for the approved ten-call offline development study.

No Flash service, browser, scorer, old launcher or external model endpoint is
used here. The original holder's nine locks remain inherited; this launch must
acquire eight additional UUID locks and the inference mutex atomically.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

P = Path(__file__).resolve().parent
sys.path[:0] = [str(P / 'native/flash'), str(P / 'native/release'), str(P / 'native')]
from resource_guard import identity, locks, sha, gpu_snapshot, LEASE

CASES = [1, 2, 17, 20, 29, 43, 44, 46, 47, 48]
PREVIOUS_OUT = Path('/data/researcher/jev-defense-four-gpu-20261106/flash-ample-memory-gui-20261114-linked11')
PREVIOUS_PACKAGE = Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-ample-memory-gui-20261114-linked11')


def load(path):
    return json.loads(Path(path).read_bytes())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def save(path, value):
    with Path(path).open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())


def verify_package():
    manifest = load(P / 'offline-manifest.json')
    for name, expected in manifest['files'].items():
        require(sha(P / name) == expected, 'Frozen offline source changed: ' + name)
    decision = load(P / 'authorization.json')
    plan = load(P / 'development-plan.json')
    require(decision['authorized'] and decision['exact_answer'] == '批准10条离线开发预检（推荐）', 'Missing human authorization')
    require(sha(P / 'development-plan.json') == decision['plan_sha256'], 'Authorized plan changed')
    require(sha(P / 'proposed-system-suffix.txt') == decision['suffix_sha256'], 'Authorized suffix file changed')
    require(decision['existing_29_GUI_must_finish_first'] and not decision['formal_changed_GUI_authorized'], 'Authorization scope changed')
    require([row['case'] for row in plan['inputs']] == CASES, 'Unbound development cases')
    require(plan['max_new_primary_model_calls'] == decision['max_new_primary_model_calls'] == 10, 'Call budget changed')
    require(plan['primary_max_output_tokens_per_call'] == 2048 and plan['actor_seed'] == 42 and plan['do_sample'] is False, 'Native generation budget changed')
    require(plan['format_retry_calls'] == plan['automatic_terminal_retries'] == plan['new_Flash_calls'] == plan['new_GUI_actions'] == plan['new_official_scores'] == plan['paid_API_calls'] == 0, 'Unapproved follow-on work')
    return manifest, plan


def validate_completion(status, terminal, group_exit, admission, expected):
    require(len(expected) == len(set(expected)) == 29, 'Original29 plan changed')
    require(status['phase'] == 'completed' and status['done'] == status['expected'] == 29 and status['active'] is None, 'Original GUI queue is not completed')
    require(terminal['status'] == 'completed' and terminal['done'] == terminal['expected'] == 29, 'Original main terminal incomplete')
    require(group_exit['exit_code'] == 0 and group_exit['failure'] is None, 'Original model group did not finish normally')
    require(all(v['exit_code'] == 0 for v in group_exit['children']), 'Original child exit failed')
    require(admission['GUI_child_exit'] == 0 and admission['actual_GUI_processes_exited'], 'Original GUI process still live')
    records = admission['terminals']
    require(len(records) == 29 and {v['run_id'] for v in records} == set(expected), 'Original GUI terminals missing or duplicated')
    require(all(v['seal_verified'] and v['chain_verified'] and not v['infrastructure_failure'] and not v['cleanup_error'] for v in records), 'Original GUI terminal evidence incomplete')
    require(admission['previous_manifest_sha256'] == sha(P / 'native/manifest.json'), 'Previous source manifest is unbound')


def previous_models_exited():
    records = [PREVIOUS_OUT / 'launcher-process.json', PREVIOUS_OUT / 'primary/process.json',
               PREVIOUS_PACKAGE / 'flash/service/process.json']
    result = []
    for path in records:
        record = load(path)
        proc = Path('/proc', str(record['pid']))
        actual = identity(record['pid']) if proc.exists() else None
        same_live = actual is not None and actual['state'] not in ['Z', 'X'] and all(actual[k] == record[k] for k in ['pid', 'uid', 'command', 'start_ticks'])
        require(not same_live, 'Previous owned model/launcher is still alive')
        result.append({'record': str(path), 'saved': record, 'actual_if_pid_exists': actual, 'same_live_process': False})
    require((PREVIOUS_OUT / 'postexit-seal.json').exists(), 'Previous final model seal absent')
    return result


def validate_gpu(snapshot, uuids, loaded_pid=None):
    cards = snapshot['gpu']
    require(set(cards) == set(range(8)), 'Expected eight physical3090 devices')
    require(all(cards[i]['uuid'] == uuids[i] for i in range(8)), 'GPU UUID changed')
    for i in range(8):
        pids = {v['pid'] for v in snapshot['compute'] if v['uuid'] == uuids[i]}
        wanted = {loaded_pid} if loaded_pid is not None and i < 7 else set()
        require(pids == wanted, 'Foreign/unverified compute on physical GPU ' + str(i))
    if loaded_pid is None:
        require(all(cards[i]['free_mib'] >= 23000 for i in range(8)), 'Insufficient exclusive GPU memory')


def inherited_locks():
    old, oldfds = locks()
    leasefile = Path(os.environ['MIRAGE_OFFLINE_LEASE'])
    require(sha(leasefile) == os.environ['MIRAGE_OFFLINE_LEASE_SHA256'], 'Offline lease changed')
    lease = load(leasefile)
    holder = lease['holder']
    actual = identity(holder['pid'])
    require(actual['state'] not in ['Z', 'X'] and all(actual[k] == holder[k] for k in ['pid', 'uid', 'command', 'start_ticks']), 'Offline holder changed')
    fds = tuple(int(v) for v in os.environ['MIRAGE_OFFLINE_EXTRA_FDS'].split(','))
    require(len(fds) == 8 and not set(fds).intersection(oldfds), 'All extra GPU locks must be inherited separately')
    require([row['fd'] for row in lease['extra_lock_records']] == list(fds), 'Offline FD set changed')
    for row in lease['extra_lock_records'] + [lease['inference_lock_record']]:
        fd = row['fd']
        require(os.fstat(fd).st_ino == row['inode'] and os.readlink('/proc/self/fd/' + str(fd)) == row['path'], 'Inherited lock identity changed')
        require('WRITE ' + str(holder['pid']) in Path('/proc/self/fdinfo', str(fd)).read_text(), 'Inherited lock not actually held')
    require(len(oldfds) == 9, 'Original nine locks required')
    return lease, oldfds + fds


def resource(loaded):
    require(os.getuid() == 1033, 'Wrong task UID')
    lease, fds = inherited_locks()
    snapshot = gpu_snapshot()
    uuids = {int(v['index']): v['uuid'] for v in lease['gpu']}
    validate_gpu(snapshot, uuids, os.getpid() if loaded else None)
    if loaded:
        for record in snapshot['compute']:
            require(all(record['identity'][k] == identity(os.getpid())[k] for k in ['pid', 'uid', 'command', 'start_ticks']), 'Compute process identity is unbound')
    stat = os.statvfs(P)
    require(stat.f_bavail * stat.f_frsize >= 32 * 1024 ** 3, 'Preserve evidence and wait for storage')
    return {'time': time.time(), 'snapshot': snapshot, 'held_GPU_or_group_locks': len(fds),
            'inference_mutex_inherited': True, 'main_physical_GPUs': list(range(7)),
            'Flash_started': False, 'GPU7_reserved_by_original_lease_but_idle': True,
            'actually_reserved_GPU_count_for_cost': 8}


def validate_case(number, body_sha, body, cpu, frozen, suffix):
    require(number in CASES and frozen['case'] == number, 'Unapproved prefix')
    require(body_sha == frozen['proposed_full_body_sha256'] == cpu['proposed_full_body_sha256'], 'Proposed body file changed')
    require(body['max_tokens'] == 2048 and body['temperature'] == 0 and body['chat_template_kwargs']['enable_thinking'] is False, 'Original generation body changed')
    require(cpu['source_run'] == 'flash14-T017-clean-gate' and cpu['source_decision'] == number, 'Source prefix changed')
    require(cpu['full_input_token_delta'] == 292 and cpu['full_original_PNGs_and_non_system_history_preserved'], 'Input preparation not approved')
    require(body['messages'][0]['content'].endswith('\n\n' + suffix), 'Approved suffix text changed')
    require(hashlib.sha256(suffix.encode()).hexdigest() == cpu['suffix_sha256'], 'CPU normalized suffix binding changed')


def validate_tensor_records(actual, expected):
    require(set(actual) == set(expected), 'Native input tensor keys changed')
    for name, row in actual.items():
        require(all(row[k] == expected[name][k] for k in ['shape', 'dtype', 'bytes', 'sha256']), 'Native input tensor changed: ' + name)


def allow_next_call(attempted, number, finished):
    require(attempted < 10 and number == CASES[attempted] and number not in finished, 'Once-only ten-call limit/order violated')
