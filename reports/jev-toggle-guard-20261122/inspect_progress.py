"""Inspect and optionally audit completed records while the immutable live run advances."""

import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import time

from audit_toggle import outcome, verify_case
from launch_panel import HERE, PYTHON, REMOTE, SSH
from live_common import load, save


def inspect(name, sample=False, postexit=None):
    assert re.fullmatch(r'live-[0-9]+', name)
    remote = shlex.quote(REMOTE + '/' + name)
    mode = 'sample' if sample else 'progress'
    command = f'cd {remote} && {shlex.quote(PYTHON)} -B - {mode}'
    code = (HERE / 'progress_remote.py').read_bytes()
    if not sample:
        result = subprocess.run(SSH + [command], input=code, capture_output=True, timeout=30, check=True)
        observed = json.loads(result.stdout)
        if postexit:
            assert observed['driver_terminal'] == 'completed_panel' and observed['uid'] == 1033
            assert len(observed['lease_processes']) == 3 and not any(p['matches'] for p in observed['lease_processes'])
            assert len(observed['capture_processes']) == 2 and not any(p['matches'] for p in observed['capture_processes'])
            assert not observed.get('locks'), 'The original driver still holds locks'
            saved = HERE / 'attempts' / name / 'run'
            assert observed['completed'] == load(saved / 'terminal.json')['planned_episodes'] == 36
            identities = [load(saved / 'gpu-lease.json')['holder']]
            identities += [load(saved / role / 'loaded.json')['process'] for role in ('primary', 'flash')]
            recorded = load(saved / 'gpu-release.json')
            assert all(lock['state'] in ('released_verified', 'acquired_by_another_process_after_release') for lock in recorded['locks'])
            if observed['compute'] is not None:
                assert not any(app['identity'] in identities for app in observed['compute'])
            assert {x['pid'] for x in recorded['snapshot']['compute']}.isdisjoint(recorded['closed_worker_pids'])
            save(postexit, observed)
            print(f'Post-exit verified: {len(recorded["locks"])} released locks; original model and browser identities exited; 36 terminal episodes.')
            if observed['compute'] is None:
                print('Fresh nvidia-smi unavailable; ownership proof uses the sealed release snapshot and fresh /proc evidence.')
        else:
            print(json.dumps(observed, ensure_ascii=False, indent=2))
        return
    view = HERE / 'provisional-snapshots' / f'{name}-{time.time_ns()}'
    view.mkdir(parents=True)
    with (view / 'snapshot.tar').open('xb') as f:
        result = subprocess.run(SSH + [command], input=code, stdout=f, stderr=subprocess.PIPE, timeout=90, check=True)
    with tarfile.open(view / 'snapshot.tar') as tar:
        tar.extractall(view, filter='data')
    audit_sample(view)


def audit_sample(view):
    origin, lease, plan, template = (load(view / n) for n in ('run/source/source.json', 'run/gpu-lease.json',
                                                              'live_plan.json', 'actor-template.json'))
    models = {role: load(view / 'run' / role / 'loaded.json') for role in ('flash', 'primary')}
    counts = []
    for case in plan['cases']:
        folder = view / 'run/episodes' / case['id']
        if not folder.is_dir():
            continue
        r = verify_case(view, case, plan, template, origin, models, lease)
        counts.append({'id': r['id'], 'status': r['status'], 'first_truth': (r['first'] or {}).get('truth'),
                       'held': [h['truth'] for h in r['holds']], 'delivery': outcome(r),
                       'gate_seconds': r['post_gate_seconds'], 'targeted_calls': r['calls']['toggle_check'],
                       'delivery_extra': r['delivery_extra']})
    save(view / 'provisional-audit.json', {'scope': 'in progress inspection; selection is not a rate', 'snapshot': view.as_posix(), 'verified': counts})
    print(json.dumps(counts, indent=2))
    print(view)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('attempt')
    cli.add_argument('--sample', action='store_true')
    cli.add_argument('--postexit', type=Path)
    cli.add_argument('--from-snapshot', type=Path)
    args = cli.parse_args()
    assert sum(bool(x) for x in (args.sample, args.postexit, args.from_snapshot)) <= 1
    if args.from_snapshot:
        audit_sample(args.from_snapshot.resolve())
    else:
        inspect(args.attempt, args.sample, args.postexit)
