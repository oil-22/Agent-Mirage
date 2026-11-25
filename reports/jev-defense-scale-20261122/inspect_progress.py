"""Inspect and optionally audit completed records while the immutable live run advances."""

import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import time

from audit_panel import chain, escape_references, verify_flash, verify_frames, verify_gate, verify_main
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
            assert not observed.get('locks'), 'The original driver still holds locks'
            saved = HERE / 'attempts' / name / 'run'
            assert observed['completed'] == load(saved / 'terminal.json')['planned_episodes'] == 96
            identities = [load(saved / 'gpu-lease.json')['holder']]
            identities += [load(saved / role / 'loaded.json')['process'] for role in ('primary', 'flash')]
            recorded = load(saved / 'gpu-release.json')
            assert all(lock['state'] in ('released_verified', 'acquired_by_another_process_after_release') for lock in recorded['locks'])
            if observed['compute'] is not None:
                assert not any(app['identity'] in identities for app in observed['compute'])
            assert {x['pid'] for x in recorded['snapshot']['compute']}.isdisjoint(recorded['closed_worker_pids'])
            save(postexit, observed)
            print(f'Post-exit verified: {len(recorded["locks"])} released locks; original workers absent; 96 terminal episodes.')
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
    origin, lease, plan, template = (load(view / n) for n in ('run/source/source.json', 'run/gpu-lease.json',
                                                              'live_plan.json', 'actor-template.json'))
    flash, primary = (load(view / 'run' / n / 'loaded.json') for n in ('flash', 'primary'))
    escape_refs = escape_references(view / 'run', plan)
    counts = []
    for case in plan['cases']:
        folder = view / 'run/episodes' / case['id']
        if not folder.is_dir():
            continue
        term = load(folder / 'terminal.json')
        head, events = chain(folder / 'events.jsonl')
        assert head == term['journal_head']
        frames, action, old = verify_frames(folder, view / 'run/source' / case['id'], case, events, term, origin, plan['viewport'],
                                            escape_refs.get(case['family'], ()))
        asked = [e['data'] for e in events if e['kind'] == 'flash_requested']
        f = [verify_flash(view, got, want, frames, old, action, flash, lease)
             for got, want in zip(term['flash'], asked, strict=True)]
        main, current = verify_main(view, template, case, events, term, frames, old, action, primary, lease)
        held, _ = verify_gate(case, events, frames, f, action, old, term)
        post = [fr for fr in frames.values() if fr['action_sequence']]
        counts.append({'id': case['id'], 'status': term['status'], 'first_truth': post[0]['truth'] if post else None,
                       'held': [frames[x]['truth'] for x in held], 'delivery': current['truth'] if main else None,
                       'gate_seconds': (term['delivery']['gate_accepted_ns']-action['send_end_ns'])/1e9 if main else None})
    save(view / 'provisional-audit.json', {'scope': 'in progress inspection; selection is not a rate', 'snapshot': view.as_posix(), 'verified': counts})
    print(json.dumps(counts, indent=2))
    print(view)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('attempt')
    cli.add_argument('--sample', action='store_true')
    cli.add_argument('--postexit', type=Path)
    args = cli.parse_args()
    assert not (args.sample and args.postexit)
    inspect(args.attempt, args.sample, args.postexit)
