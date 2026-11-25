"""Bind the exact approved wrapper receipt to its sealed native CPU result."""
import hashlib
import json
from pathlib import Path

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def load(path):
    return json.loads(Path(path).read_bytes())

def verify_cpu_receipt(package, source, frozen, manifest):
    package, source = Path(package), Path(source)
    wrapper_path = package / 'CPU-receipts' / ('case-%02d.json' % frozen['case'])
    require(digest(wrapper_path) == frozen['native_CPU_input_receipt_sha256'], 'Approved wrapper receipt changed')
    wrapper = load(wrapper_path)
    require(wrapper['remote_case'] == str(source), 'Approved native CPU source path changed')
    require(digest(source / 'seal.json') == wrapper['remote_seal_sha256'] == manifest['CPU_case_seals'][str(frozen['case'])], 'Original native CPU seal changed')
    seal = load(source / 'seal.json')
    require('result.json' in seal and 'proposed-full-body.json' in seal, 'Incomplete original native CPU seal')
    for name, expected in seal.items():
        require(digest(source / name) == expected, 'Original native CPU member changed: ' + name)
    result = load(source / 'result.json')
    require(result == wrapper['result'], 'Sealed native result differs from approved wrapper payload')
    require(result['source_body_sha256'] == frozen['original_body_sha256'], 'Original full body identity changed')
    require(digest(source / 'proposed-full-body.json') == frozen['proposed_full_body_sha256'] == result['proposed_full_body_sha256'], 'Approved proposed full body changed')
    require(result['full_input_token_delta'] == 292 and result['full_original_PNGs_and_non_system_history_preserved'] is True, 'Original input conditions changed')
    return result

def verify_zero_call_parent(package):
    package = Path(package)
    contract = load(package / 'linked-zero-call-failure.json')
    old = Path(contract['output'])
    require(digest(old / 'postexit-seal.json') == contract['postexit_seal_sha256'], 'Preserved zero-call attempt seal changed')
    seal = load(old / 'postexit-seal.json')
    require({str(f.relative_to(old)) for f in old.rglob('*') if f.is_file() and f.name != 'postexit-seal.json'} == set(seal), 'Preserved zero-call attempt file set changed')
    for name, expected in seal.items():
        require(digest(old / name) == expected, 'Preserved zero-call attempt member changed: ' + name)
    terminal, exit_record = load(old / 'worker/terminal.json'), load(old / 'exit.json')
    require(terminal['status'] == 'preserved_failure' and terminal['attempted_calls'] == 0 and terminal['completed_reply_cases'] == [], 'A previous approved model call has already been spent')
    require(exit_record['exit_code'] == exit_record['child_exit'] == 1, 'Unexpected prior technical terminal')
    require('Frozen CPU receipt changed' in load(old / 'worker/failure.json')['error'], 'Different parent failure')
    from offline_guard import identity
    for name in ['launcher-process.json', 'worker/process.json']:
        saved = load(old / name)
        try:
            actual = identity(saved['pid'])
        except FileNotFoundError:
            actual = None
        same = actual is not None and actual['state'] not in ['Z', 'X'] and all(actual[k] == saved[k] for k in ['pid', 'uid', 'command', 'start_ticks'])
        require(not same, 'Prior zero-call worker/launcher is still live')
    return {'prior_attempted_calls': 0, 'remaining_shared_maximum_calls': 10, 'old_postexit_seal_sha256': contract['postexit_seal_sha256']}
