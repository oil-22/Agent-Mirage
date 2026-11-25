"""Start a new sealed development or held-out attempt exactly once on 3090."""

import argparse
from pathlib import Path
import re
import shlex
import subprocess
import time

from launch_panel import PYTHON, SSH, archive_bytes, collect
from live_common import canonical, hash_bytes, load, put, save, sha

HERE = Path(__file__).resolve().parent
REMOTE = '/data/researcher/jev-toggle-outcome-20261122'
COMMON = {'live_plan.json', 'seal_run.py', 'live_common.py', 'source-baseline.json'}
CAPTURE = {'fixture.html', 'capture_gui.py', 'live_capture.py', 'gate_core.py', 'receipt_protocol.py',
           'temporal_request.py', 'toggle_protocol.py', 'scoped_evidence.py'}
FLASH = {'live_models.py', 'service-config.json', 'gate-contract.json', 'flash-identity.json',
         'live_lease.py', 'wire_contract.py', 'resource_guard.py', 'temporal_request.py', 'toggle_prompt.py', 'gate_core.py'}
PRIMARY = {'actor-template.json', 'four-card-placement.json', 'primary-reference.json', 'runtime-provenance.json'}


def check_published(name, prefix, outcome):
    assert re.fullmatch(prefix + '-[0-9]+', name)
    home = HERE / 'attempts' / name
    seal = load(home / 'local-seal.json')
    assert all(sha(home / k)==h for k,h in seal.items())
    assert load(home/'run/terminal.json')['status'] == outcome
    return home


def launch(stage, preflight=None, probe=None, technical_parent=None):
    files = set(COMMON)
    data = {'stage': stage, 'mode':'capture-preflight' if stage=='capture-preflight' else 'live', 'python':PYTHON}
    if stage=='probe':
        files |= FLASH | {'probe-plan.json','probe_outcome.py'}
        images={h for row in load(HERE/'probe-plan.json')['inputs'] for h in row['images']}
        assert all(re.fullmatch('[0-9a-f]{64}', h) for h in images)
        files |= {f'images/{h}.png' for h in images}
        data['max_calls'] = 8
    elif stage=='capture-preflight':
        files |= CAPTURE
        plan=load(HERE/'heldout-plan.json')
        data['preflight_ids']=plan['preflight_ids']
    elif stage=='live':
        files |= FLASH | PRIMARY | CAPTURE | {'analysis-plan.json', 'live_run.py', 'cpu-qualification.json'}
        files |= {p.relative_to(HERE).as_posix() for p in (HERE/'release').rglob('*.py')}
        pre = check_published(preflight, 'capture-preflight', 'passed')
        dev = check_published(probe, 'probe', 'completed_probe')
        source = load(pre/'manifest.json')
        assert all(sha(HERE/('heldout-plan.json' if key=='live_plan.json' else key))==source['files'][key] for key in COMMON | CAPTURE)
        assert load(pre/'run'/'terminal.json')['new_model_calls'] == 0
        assert sha(HERE/'toggle_prompt.py')==sha(dev/'toggle_prompt.py')
        assert sha(HERE/'live_models.py')==sha(dev/'live_models.py')
        audit=load(HERE/'probe-audit.json')
        assert audit['attempt']==probe and audit['local_seal_sha256']==sha(dev/'local-seal.json') and audit['preflight_qualified']
        assert audit['prompt_sha256']==sha(HERE/'toggle_prompt.py')
        q=load(HERE/'cpu-qualification.json')
        assert q['preflight_seal_sha256']==sha(pre/'local-seal.json') and all(sha(HERE/key)==h for key,h in q['files'].items())
        data.update(preflight=preflight, preflight_seal_sha256=sha(pre/'local-seal.json'), probe=probe,
                    probe_seal_sha256=sha(dev/'local-seal.json'), probe_audit_sha256=sha(HERE/'probe-audit.json'),
                    max_primary_calls=36, retries_of_model_or_action=0)
    else:
        raise ValueError(stage)
    payload = {p: (HERE/('heldout-plan.json' if p=='live_plan.json' and stage!='probe' else p)).read_bytes() for p in files}
    if technical_parent:
        failed=check_published(technical_parent, stage, 'technical_failure')
        old=load(failed/'run/terminal.json')
        assert stage=='probe' and old['calls']==old['gui_actions']==old['primary_calls']==0
        assert not list((failed/'run'/'flash').glob('*/start.json'))
        prior=load(failed/'manifest.json')['files']
        assert set(payload)-prior.keys()=={'gate_core.py'} and all(hash_bytes(payload[f])==h for f,h in prior.items())
        data['technical_parent']={'name':technical_parent,'local_seal_sha256':sha(failed/'local-seal.json'),
                                  'remote_seal_sha256':sha(failed/'remote-seal.json'),'packaging_only':['gate_core.py']}
    name = f'{stage}-{time.time_ns()}'
    local, remote = HERE/'attempts'/name, f'{REMOTE}/{name}'
    local.mkdir(parents=True,exist_ok=False)
    data.update(name=name, files={p:hash_bytes(raw) for p,raw in sorted(payload.items())})
    payload['manifest.json']=canonical(data)+b'\n'
    for p, raw in payload.items():
        where=local/p; where.parent.mkdir(parents=True,exist_ok=True); put(where,raw)
    put(local/'remote-root.txt',(remote+'\n').encode())
    print(name, 'input manifest:', sha(local/'manifest.json'), flush=True)
    marker=shlex.quote(REMOTE + '/once-' + stage + ('-linked-'+technical_parent if technical_parent else ''))
    script={'probe':'probe_outcome.py','live':'live_run.py','capture-preflight':'live_capture.py'}[stage]
    r, py = shlex.quote(remote), shlex.quote(PYTHON)
    # The marker contains the attempt handle and is created atomically. An SSH
    # disconnect is an inspection/recovery case, never grounds to launch twice.
    parent_check=''
    if technical_parent:
        authority=shlex.quote(REMOTE+'/'+technical_parent+'/remote-seal.json')
        parent_check=f'test "$(sha256sum {authority} | cut -d " " -f 1)" = {data["technical_parent"]["remote_seal_sha256"]} && '
    command=(f'umask 077; mkdir -p {shlex.quote(REMOTE)} && {parent_check}mkdir {marker} && '
             f'printf "%s\\n" {shlex.quote(name)} > {marker}/attempt && mkdir {r} && '
             f'tar -xf - -C {r} && cd {r} || exit $?; '
             f'CUDA_VISIBLE_DEVICES= {py} -B -u {script}; rc=$?; {py} -B -u seal_run.py "$rc" || exit $?; exit "$rc"')
    with (local/'driver-stderr.log').open('xb') as stderr:
        rc=subprocess.run(SSH+[command],input=archive_bytes(payload),stderr=stderr).returncode
    collect(local,remote)
    term=load(local/'run'/'terminal.json')
    print('Sealed', name, term['status'], flush=True)
    if rc:
        print(term.get('error'), flush=True)
    return rc


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('probe','capture-preflight','live'))
    p.add_argument('--preflight');p.add_argument('--probe');p.add_argument('--technical-parent')
    args=p.parse_args()
    assert (args.preflight is not None and args.probe is not None)==(args.stage=='live')
    raise SystemExit(launch(args.stage,args.preflight,args.probe,args.technical_parent))
