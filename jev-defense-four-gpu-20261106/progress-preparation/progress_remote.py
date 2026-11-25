"""Read-only running evidence snapshots. No HTTP, signals, models or private task files."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return digest(Path(path).read_bytes())


def process_identity(pid):
    root = Path('/proc') / str(pid)
    if not root.exists():
        return None
    fields = (root / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': int(pid), 'uid': root.stat().st_uid, 'start_ticks': fields[19],
            'command': (root / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip()}


def identity_record(expected):
    actual = process_identity(expected['pid'])
    matches = actual is not None and all(str(actual[key]) == str(expected[key])
        for key in ('pid', 'uid', 'command', 'start_ticks'))
    return {'expected': expected, 'actual': actual, 'identity_matches': matches,
            'phase': 'alive' if matches else 'pid_absent' if actual is None else 'identity_mismatch'}


def lock_records(pid, lease):
    rows = []
    for expected in lease['lock_records']:
        fd = Path('/proc', str(pid), 'fd', str(expected['fd']))
        info = Path('/proc', str(pid), 'fdinfo', str(expected['fd'])).read_text()
        target = os.readlink(str(fd))
        assert target == expected['path'] and fd.stat().st_ino == expected['inode']
        assert 'lock:' in info
        rows.append({'fd': expected['fd'], 'path': target, 'inode': expected['inode']})
    assert len(rows) == 9
    return rows


def chain_snapshot(path, controller=False):
    if not path.exists():
        return {'exists': False, 'event_count': 0}
    raw = path.read_bytes()
    lines = raw.split(b'\n')
    partial = lines.pop()
    previous = '0' * 64 if controller else None
    counts = {}
    last = None
    for index, line in enumerate(lines):
        assert line, 'Empty complete event line'
        event = json.loads(line)
        expected = event.pop('sha256')
        sequence = event['seq'] if controller else event['index']
        prior = event['previous'] if controller else event['previous_sha256']
        assert sequence == index and prior == previous and digest(canonical(event)) == expected
        previous = expected
        kind = event['kind'] if controller else event['event']
        counts[kind] = counts.get(kind, 0) + 1
        last = {'sequence': sequence, 'kind': kind, 'time': event['time']}
    return {'exists': True, 'snapshot_sha256': digest(raw), 'snapshot_bytes': len(raw),
        'event_count': len(lines), 'chain_head': previous, 'complete_line_chain_verified': True,
        'uncommitted_partial_tail_bytes': len(partial), 'kind_counts': counts, 'last_event': last}


def sealed_request(path):
    seal_path = path / 'seal.json'
    if not seal_path.exists():
        return {'path': str(path), 'status': 'pending_unsealed',
            'request_present': (path / 'request.json').exists()}
    seal = read(seal_path)
    for name, expected in seal.items():
        relative = Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        assert sha(path / relative) == expected
    actual_files = {p.name for p in path.iterdir() if p.is_file() and p.name != 'seal.json'}
    assert actual_files == set(seal), 'Seal file inventory changed'
    row = {'path': str(path), 'seal_sha256': sha(seal_path), 'seal_verified': True,
        'sealed_files': len(seal), 'status': 'failed' if (path / 'failure.json').exists() else 'completed'}
    request = read(path / 'request.json')
    row.update({key: request[key] for key in ('trajectory_id', 'decision_index', 'attempt_index', 'request_id')
                if key in request})
    payload = request.get('payload', {})
    row['operation'] = payload.get('operation', 'observe' if 'questions' in payload else 'transition')
    if (path / 'generation.json').exists():
        generation = read(path / 'generation.json')
        output = generation['generated_ids']
        eos = generation['generation_config'].get('eos_token_id')
        eos = eos if isinstance(eos, list) else [eos]
        row['generation'] = {'input_tokens': len(generation['input_ids']), 'output_tokens': len(output),
            'last_token_is_native_EOS': bool(output) and output[-1] in eos,
            'hit_output_cap': generation['hit_output_cap'], 'seconds': generation['seconds']}
    return row


def service_snapshot(group):
    config = read(group / 'runtime-config.json')
    lease = read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
    holder = identity_record(lease['holder'])
    if holder['identity_matches']:
        holder['actual_locks'] = lock_records(holder['actual']['pid'], lease)
    launcher = identity_record(read(group / 'process.json'))
    if launcher['identity_matches']:
        launcher['actual_locks'] = lock_records(launcher['actual']['pid'], lease)
    workers = {}
    for role in ('primary', 'pplx_flash'):
        registration = read(group / 'processes' / (role + '.json'))
        row = identity_record(registration['identity'])
        assert registration['identity']['command'] == ' '.join(config['commands'][role])
        if row['identity_matches']:
            row['actual_locks'] = lock_records(row['actual']['pid'], lease)
        row['requests'] = [sealed_request(p) for p in sorted((group / role / 'requests').iterdir()) if p.is_dir()]
        row['request_counts'] = {key: sum(r['status'] == key for r in row['requests'])
                                 for key in ('completed', 'failed', 'pending_unsealed')}
        row['sealed_native_EOS_count'] = sum(r.get('generation', {}).get('last_token_is_native_EOS', False)
                                             for r in row['requests'])
        row['loaded_sha256'] = sha(group / role / 'loaded.json')
        row['log'] = {'bytes': (group / (role + '.log')).stat().st_size,
                      'sha256': sha(group / (role + '.log'))}
        workers[role] = row
    lines = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.free,memory.used',
        '--format=csv,noheader,nounits'], universal_newlines=True).splitlines()
    gpu = {}
    for line in lines:
        index, uuid, free, used = [part.strip() for part in line.split(',')]
        gpu[int(index)] = {'uuid': uuid, 'free_mib': int(free), 'used_mib': int(used)}
    lines = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
        '--format=csv,noheader,nounits'], universal_newlines=True).splitlines()
    compute = [{'uuid': line.split(',')[0].strip(), 'pid': int(line.split(',')[1])}
               for line in lines if line.strip()]
    targets = {row['uuid'] for row in lease['gpu']}
    allowed = {row['actual']['pid'] for row in workers.values() if row['identity_matches']}
    target_compute = [row for row in compute if row['uuid'] in targets]
    foreign = [row for row in target_compute if row['pid'] not in allowed]
    transitions = [sealed_request(path) for path in sorted((group / 'transitions').iterdir()) if path.is_dir()]
    return {'group': str(group), 'holder': holder, 'launcher': launcher, 'workers': workers,
        'physical_GPU4_7': {str(i): gpu[i] for i in (4, 5, 6, 7)},
        'target_compute': target_compute, 'foreign_target_compute': foreign,
        'all_actual_peer_identities_valid': all(row['identity_matches'] for row in workers.values()),
        'state_snapshot': read(group / 'online-state.json'), 'journal': chain_snapshot(group / 'journal.jsonl'),
        'transitions': transitions, 'launcher_failure_present': (group / 'launcher-failure.json').exists()}


def controller_snapshot(batch, control, background):
    result = {'batch': str(batch), 'batch_exists': batch.exists(), 'processes': {}, 'eventchains': []}
    for role, path in [('wrapper', control / 'wrapper-process.json'), ('runner', control / 'runner-process.json')]:
        if path.exists():
            result['processes'][role] = identity_record(read(path))
    if (background / 'actualprocess.json').exists():
        result['processes']['background_recorded_wrapper'] = identity_record(read(background / 'actualprocess.json')['identity'])
    if (batch / 'status.json').exists():
        status = read(batch / 'status.json')
        result['status_snapshot'] = {key: status[key] for key in
            ('pid', 'phase', 'run', 'attempt', 'step', 'completed', 'expected', 'updated', 'started') if key in status}
    for path in sorted(batch.glob('runs/*/attempt-*/events.jsonl')):
        row = {'path': str(path), **chain_snapshot(path, controller=True)}
        terminal = next((path.parent / name for name in
            ('complete.json', 'technical-failure.json', 'failure.json', 'paused.json') if (path.parent / name).exists()), None)
        if terminal:
            value = read(terminal)
            row['terminal'] = {'filename': terminal.name, 'sha256': sha(terminal),
                **{key: value[key] for key in ('outcome', 'decisions', 'environment_actions', 'actor_calls',
                    'verifier_calls', 'auxiliary_calls', 'observer_technical_failures', 'technical_status') if key in value}}
        result['eventchains'].append(row)
    result['failure_markers'] = [str(path) for path in
        [control / 'wrapper-failure.json', control / 'safe-boundary-stop-request.json',
         background / 'launch-failure.json', batch / 'uncaught-failure.json'] if path.exists()]
    result['outer_finalization_present'] = (control / 'finalization.json').exists()
    result['outer_postexit_seal_present'] = (control / 'postexit-sha256.json').exists()
    return result


if __name__ == '__main__':
    mode = PROGRESS_CONFIG['mode']
    value = (service_snapshot(Path(PROGRESS_CONFIG['group'])) if mode == 'service' else
        controller_snapshot(Path(PROGRESS_CONFIG['batch']), Path(PROGRESS_CONFIG['control']),
                            Path(PROGRESS_CONFIG['background'])))
    print(json.dumps({'time': time.time(), 'mode': mode, 'evidence': value,
        'HTTP_requests': 0, 'model_requests': 0, 'GUI_actions': 0,
        'private_task_answer_or_trajectory_files_read': False, 'remote_files_written': 0}))
