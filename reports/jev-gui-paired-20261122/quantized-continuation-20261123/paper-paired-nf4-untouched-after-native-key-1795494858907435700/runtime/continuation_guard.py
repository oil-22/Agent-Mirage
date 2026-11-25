"""Link the four-card continuation to both immutable BF16 prefixes."""
import json
import os
from pathlib import Path

from gate_core import canonical, digest
from paired_contract import load_plan
from resource_guard import identity, sha

SITE = Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock')


def read(p):
    return json.loads(p.read_bytes())


def gone(saved):
    try:
        current = identity(saved['pid'])
    except (FileNotFoundError, ProcessLookupError):
        return True
    return (current['state'] in ('Z', 'X') or any(current[k] != saved[k]
            for k in ('uid', 'command', 'start_ticks')))


def sealed(root, seal, *names):
    for name in names:
        assert sha(root/name) == seal[name], (root, name)


def events(path):
    head = '0' * 64
    rows = []
    for i, line in enumerate(path.read_bytes().splitlines()):
        event = json.loads(line)
        h = event.pop('sha256')
        assert event['seq'] == i and event['previous'] == head and h == digest(canonical(event)), path
        head = h
        rows.append(event)
    assert rows, path
    return rows, head


def check_gui(runtime, rows, interrupted):
    control = runtime/'control'
    batch = runtime/'batch'
    assert all(gone(read(control/n)) for n in ('process.json', 'runner-process.json'))
    assert read(control/'exit.json')['child_exit'] == 0
    ctl_seal = read(control/'postexit-seal.json')
    sealed(control, ctl_seal, 'exit.json', 'batch-terminal-seal.json')
    seal = read(control/'batch-terminal-seal.json')
    sealed(batch, seal, 'status.json')
    state = read(batch/'status.json')
    assert state['processed'] == len(rows) and state['completed'] == len(rows) - interrupted
    assert state['phase'] == ('technical_failure' if interrupted else 'manually_stopped')
    runs = batch/'runs'
    assert {f.name for f in runs.iterdir() if f.is_dir()} == {r['run_id'] for r in rows}
    result, chain_heads = {}, {}
    for idx, row in enumerate(rows):
        attempt, = (runs/row['run_id']).glob('attempt-*')
        local = read(attempt/'seal.json')
        t = attempt/'terminal.json'
        log = attempt/'controller/events.jsonl'
        sealed(attempt, local, 'terminal.json', 'controller/events.jsonl')
        sealed(batch, seal, *(f.relative_to(batch).as_posix() for f in (t, log, attempt/'seal.json')))
        data = read(t)
        assert data['run'] == row
        if interrupted and idx == len(rows)-1:
            assert data['infrastructure_failure'] and data.get('official_reward') is None
        else:
            assert not data['infrastructure_failure'] and data['scoring_status'] == 'complete'
            result[row['run_id']] = sha(t)
        chain_heads[row['run_id']] = events(log)[1]
    return {'terminals_scored': result, 'controller_heads': chain_heads,
            'technical_terminal_sha256': sha(t) if interrupted else None,
            'batch_seal_sha256': sha(control/'batch-terminal-seal.json')}


def check_model(runtime, output, rows, interrupted):
    assert all(gone(read(p)) for p in (output/'launcher-process.json', output/'primary/process.json',
                                      runtime/'flash/service/process.json'))
    seal = read(output/'postexit-seal.json')
    path = 'primary/journal/events.jsonl'
    sealed(output, seal, 'exit.json', 'released.json', 'primary/terminal.json', path)
    assert read(output/'released.json')['fresh_lease_locks_closed'] == 17
    terminal = read(output/'primary/terminal.json')
    assert terminal['status'] == 'stopped' and terminal['done'] == len(rows) - interrupted
    journal, head = events(output/path)
    begin = [x['data']['run_id'] for x in journal if x['kind'] == 'run_begin']
    assert begin == [x['run_id'] for x in rows]
    ends = [x['data'] for x in journal if x['kind'] == 'run_end']
    scored = [x for x in ends if not x['infrastructure_failure'] and not x['manual_stop']]
    assert [x['run_id'] for x in scored] == [x['run_id'] for x in rows[:len(rows)-interrupted]]
    result = {'terminals_scored': {x['run_id']: x['terminal_sha256'] for x in scored},
              'service_head': head, 'model_seal_sha256': sha(output/'postexit-seal.json')}
    if interrupted:
        assert journal[-1]['kind'] == 'technical_failure'
        failure = output/'primary/requests'/f"{terminal['attempted_actor_calls']:05d}"
        sealed(failure, read(failure/'seal.json'), 'wire-request.bin', 'body.json', 'failure.json')
        sealed(output, seal, (failure/'seal.json').relative_to(output).as_posix())
        assert read(failure/'wire-request.bin')['run_id'] == rows[-1]['run_id']
        assert not (failure/'first-forward.json').exists() and not (failure/'response.json').exists()
        result['technical_request_seal_sha256'] = sha(failure/'seal.json')
    return result


def verify_stage_parent(package, host):
    m, _ = load_plan(package)
    assert host in ('3090', '4090') and os.getuid() == (1033 if host == '3090' else 1015)
    assert Path(m['package'+host]) == package
    link = read(package/'quantized-parent.json')
    full = read(package/'parent-full-plan.json')['queue']
    a = Path(link['original'][host]); b = Path(link['envelope'][host])
    for runtime, entry in [(a, link['original']), (b, link['envelope'])]:
        assert sha(runtime/'manifest.json') == entry['manifest_sha256']
        assert sha(runtime/'plan.json') == entry['plan_sha256']
    assert read(a/'plan.json')['queue'] == full and read(b/'plan.json')['queue'] == full[22:]
    assert read(b/'actor-template.json') == read(package/'actor-template.json')
    assert m['preserved_prefix_count'] == 29
    if host == '3090':
        v1 = check_model(a, Path(link['original']['output3090']), full[:22], 0)
        v2 = check_model(b, Path(link['envelope']['output3090']), full[22:26], 1)
    else:
        v1 = check_gui(a, full[:22], 0)
        v2 = check_gui(b, full[22:26], 1)
        st = SITE.stat()
        key = f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}'
        holders = [line.split()[4] for line in Path('/proc/locks').read_text().splitlines() if key in line]
        assert not holders or (holders == [str(os.getpid())] and str(package/'gui_outer.py') in identity(os.getpid())['command'])
    assert v1['terminals_scored'] == link['original']['terminals_scored']
    from verify_native_key_parent import verify_prior_nf4
    parent = verify_prior_nf4(package, host, full, gone, events)
    return {'host': host, 'preserved_prefix': 29, 'prior_NF4': parent, 'native_BF16': v1, 'envelope_BF16': v2,
            'continuation_trajectories': 71, 'existing_trajectories_reexecuted': 0}


def verify_native_parent(package):
    return verify_stage_parent(package, '3090')


def verify_gui_parent(package):
    return verify_stage_parent(package, '4090')
