"""Require a drained, preserved v1 pair boundary before the independent v2 lease."""
import json
import os
from pathlib import Path

from gate_core import canonical, digest
from paired_contract import load_plan
from resource_guard import identity, sha


def _read(q):
    return json.loads(q.read_bytes())


def _gone(saved):
    try:
        now = identity(saved['pid'])
    except (FileNotFoundError, ProcessLookupError):
        return True
    return now['state'] in ('Z','X') or any(now[k] != saved[k] for k in ('uid','command','start_ticks'))


def _parent(package, host):
    m, plan = load_plan(package)
    cutover = _read(package/'action-envelope-cutover.json')
    assert os.getuid() == (1033 if host == '3090' else 1015)
    assert Path(m['package'+host]) == package
    prior = Path(cutover['parent_runtime'][host])
    assert sha(prior/'manifest.json') == cutover['parent_manifest_sha256']
    assert sha(prior/'plan.json') == cutover['parent_plan_sha256']
    assert sha(package/'native-parser-source.py') == sha(prior/'native-parser-source.py')
    assert cutover['first_new_run_id'] == plan['queue'][0]['run_id']
    return m, cutover, prior


def verify_stage_parent(package, host):
    from historical_admission import verify_gui_parent as old_gui, verify_native_parent as old_model
    m, cutover, prior = _parent(package, host)
    sealed_origin = Path(m['historical_package'+host])
    assert sha(sealed_origin/'manifest.json') == m['historical_manifest_sha256']
    unchanged = (old_model if host == '3090' else old_gui)(sealed_origin)
    return {'paired_envelope_v2_stage':True, 'parent_runtime_bound':str(prior),
            'old_source_and_owned_site_proof':unchanged, 'launch_still_requires_pair_drain':True,
            'preassigned_prefix':cutover['prefix_count']}


def release_status(package, host):
    _, cutover, prior = _parent(package, host)
    n = cutover['prefix_count']
    queue = _read(prior/'plan.json')['queue']
    if host == '4090':
        ctl = prior/'control'
        stop = prior/'STOP'
        watch = prior.parent/'action-envelope-repair-drain'
        watch_result = watch/'result.json'
        if watch_result.exists():
            data = _read(watch_result)
            if data.get('status') != 'stop_marker_written_after_official_score':
                raise RuntimeError('Pair drain did not occur: '+str(data))
        files = [stop, watch_result, ctl/'exit.json', ctl/'postexit-seal.json', ctl/'batch-terminal-seal.json']
        if not all(x.exists() for x in files):
            return {'released':False,'pending':'v1 GUI same-pair drain and terminal preservation','host':host}
        if not all(_gone(_read(ctl/name)) for name in ('process.json','runner-process.json')):
            return {'released':False,'pending':'v1 GUI seal or owned exit','host':host}
        assert _read(stop) == _read(watch_result)
        assert _read(stop)['scheduled_prefix'] == n and _read(stop)['target_run_id'] == queue[n-1]['run_id']
        assert _read(ctl/'exit.json')['child_exit'] == 0
        gui_seal = _read(ctl/'postexit-seal.json')
        batch_seal = _read(ctl/'batch-terminal-seal.json')
        assert gui_seal['batch-terminal-seal.json'] == sha(ctl/'batch-terminal-seal.json')
        state = _read(prior/'batch/status.json')
        assert state['phase'] == 'manually_stopped' and state['processed'] == state['completed'] == n
        assert batch_seal['status.json'] == sha(prior/'batch/status.json')
        runs = prior/'batch/runs'
        assert {q.name for q in runs.iterdir() if q.is_dir()} == {v['run_id'] for v in queue[:n]}
        terminal_sha = {}
        for row in queue[:n]:
            attempt, = (runs/row['run_id']).glob('attempt-*')
            t = attempt/'terminal.json'
            end = _read(t)
            h = sha(t)
            assert h == _read(attempt/'seal.json')['terminal.json'] == batch_seal[t.relative_to(prior/'batch').as_posix()]
            assert end['run'] == row and not end['infrastructure_failure'] and end['scoring_status']=='complete'
            terminal_sha[row['run_id']] = h
        site_lock = Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock')
        st = site_lock.stat()
        key = f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}'
        holders = [line.split()[4] for line in Path('/proc/locks').read_text().splitlines() if key in line]
        # gui_outer acquires the same dedicated lock before it verifies this guard again.
        assert not holders or (holders == [str(os.getpid())] and str(package/'gui_outer.py') in identity(os.getpid())['command'])
        return {'released':True,'host':host,'prefix':n,'terminals':terminal_sha,
                'old_GUI_seal_sha256':sha(ctl/'postexit-seal.json'),'old_batch_seal_sha256':sha(ctl/'batch-terminal-seal.json')}

    out = Path(cutover['parent_model_output'])
    exit_files = [out/'exit.json', out/'released.json', out/'postexit-seal.json', out/'primary/terminal.json']
    if not all(q.exists() for q in exit_files):
        return {'released':False,'pending':'v1 models still serving or post-exit seal pending','host':host}
    owners = [out/'launcher-process.json',out/'primary/process.json',prior/'flash/service/process.json']
    if not all(_gone(_read(p)) for p in owners):
        return {'released':False,'pending':'v1 launcher/model identities still present','host':host}
    seal = _read(out/'postexit-seal.json')
    journal = out/'primary/journal/events.jsonl'
    for name in ('exit.json','released.json','primary/terminal.json','primary/journal/events.jsonl'):
        assert sha(out/name) == seal[name]
    assert _read(out/'released.json')['fresh_lease_locks_closed'] == 17
    assert _read(out/'primary/terminal.json')['done'] == n
    assert _read(out/'primary/terminal.json')['status'] == 'stopped'
    actual = {}
    head = '0'*64
    for idx,line in enumerate(journal.read_bytes().splitlines()):
        e = json.loads(line)
        h = e.pop('sha256')
        assert e['seq']==idx and e['previous']==head and h==digest(canonical(e))
        head = h
        if e['kind']=='run_end':
            row=e['data']
            assert not row['infrastructure_failure'] and not row['manual_stop']
            actual[row['run_id']] = row['terminal_sha256']
    assert list(actual) == [row['run_id'] for row in queue[:n]]
    old_lease=_read(out/'lease.json')
    for lock in old_lease['lock_records']:
        st=Path(lock['path']).stat()
        key=f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}'
        assert st.st_ino==lock['inode'] and not any(key in line for line in Path('/proc/locks').read_text().splitlines())
    return {'released':True,'host':host,'prefix':n,'terminals':actual,'old_model_seal_sha256':sha(out/'postexit-seal.json'),
            'old_model_event_chain_head':head,'all_17_old_GPU_locks_released':True}


def _launch(package, host):
    stage = verify_stage_parent(package, host)
    prior = release_status(package, host)
    assert prior['released'], prior
    return {'admission':stage, 'preserved_parent':prior}


def verify_native_parent(package):
    return _launch(package,'3090')


def verify_gui_parent(package):
    return _launch(package,'4090')
