"""Launch only the frozen independent scale panel on the original 3090 deployment."""

import argparse
import io
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import time

from live_common import canonical, hash_bytes, load, put, save, sha

HERE = Path(__file__).resolve().parent
REMOTE = '/data/researcher/jev-toggle-guard-20261122'
PYTHON = '/opt/whz/conda-envs/webmall-vlm/bin/python'
SSH = ['ssh', '-p', '2223', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
       '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=4', 'researcher@192.0.2.11']
CAPTURE = (
    'fixture.html', 'live_plan.json', 'live_common.py', 'live_capture.py', 'capture_gui.py',
    'gate_core.py', 'receipt_protocol.py', 'temporal_request.py', 'toggle_protocol.py', 'seal_run.py',
)
PREFLIGHT_IDS = ('atelier-quick-scoped','support-quick-scoped','vault-quick-scoped','ledger-delayed-scoped',
                 'atelier-neighbor-scoped','support-elsewhere-scoped','vault-unchanged-scoped','ledger-ordinary-scoped')


def input_files(mode, preflight):
    files = {p: (HERE / p).read_bytes() for p in CAPTURE}
    plan = load(HERE / 'live_plan.json')
    assert len(plan['cases']) == plan['max_primary_calls'] == 36 and set(PREFLIGHT_IDS) <= {r['id'] for r in plan['cases']}
    source = load(HERE / 'stage-provenance.json')
    if mode == 'live':
        previous = HERE / 'attempts' / preflight
        sealed = load(previous / 'local-seal.json')
        assert all(sha(previous / p) == h for p, h in sealed.items())
        manifest = load(previous / 'manifest.json')
        assert manifest['mode'] == 'capture-preflight' and manifest['preflight_ids'] == list(PREFLIGHT_IDS)
        assert manifest['files'] == {p: hash_bytes(raw) for p, raw in files.items()}
        terminal = load(previous / 'run/terminal.json')
        assert terminal['status'] == 'passed' and terminal['source_worker_exit'] == 0
        assert terminal['new_model_calls'] == terminal['gpu_allocations'] == 0
        assert [r['case']['id'] for r in terminal['completed']] == list(PREFLIGHT_IDS)
        for rel, digest in source['exactly_copied'].items():
            raw = (HERE / rel).read_bytes()
            assert hash_bytes(raw) == digest, rel
            files[rel] = raw
        for rel in ('live_models.py', 'live_run.py', 'analysis-plan.json', 'stage-provenance.json', 'launch_panel.py',
                    'toggle_policy.py','toggle_prompt.py'):
            files[rel] = (HERE / rel).read_bytes()
        qualification = load(HERE / 'cpu-boundaries-v3.json')
        assert qualification['status'] == 'passed'
        assert {p: hash_bytes(files[p]) for p in qualification['codes']} == qualification['codes']
        files['cpu-boundaries-v3.json'] = (HERE / 'cpu-boundaries-v3.json').read_bytes()
    return files


def archive_bytes(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tar:
        for name, raw in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(raw), 0o600
            tar.addfile(info, io.BytesIO(raw))
    return buf.getvalue()


def collect(home, remote):
    transfer = home / 'collection.tar.partial'
    with transfer.open('xb') as output:
        result = subprocess.run(SSH + [f'cd {shlex.quote(remote)} && tar -cf - run remote-seal.json'],
                                stdout=output, stderr=subprocess.PIPE, timeout=500)
    put(home / 'collection-stderr.log', result.stderr)
    result.check_returncode()
    with tarfile.open(transfer, mode='r:') as tar:
        assert all(m.name == 'remote-seal.json' or m.name == 'run' or m.name.startswith('run/') for m in tar.getmembers())
        tar.extractall(home, filter='data')
    remote_manifest = load(home / 'remote-seal.json')
    assert remote_manifest['input_manifest_sha256'] == sha(home / 'manifest.json')
    full = {p.relative_to(home).as_posix(): sha(p) for p in (home / 'run').rglob('*') if p.is_file()}
    assert full == remote_manifest['files'], 'post-exit evidence differs from the remote SHA seal'
    transfer.rename(home / 'collection.tar')
    save(home / 'local-seal.json', {p.relative_to(home).as_posix(): sha(p) for p in home.rglob('*') if p.is_file()})


def main(mode, preflight=None, parent=None):
    assert preflight is None or re.fullmatch(r'capture-preflight-[0-9]+', preflight)
    assert parent is None or re.fullmatch(mode + r'-[0-9]+', parent)
    files = input_files(mode, preflight)
    name = f'{mode}-{time.time_ns()}'
    home, remote = HERE / 'attempts' / name, f'{REMOTE}/{name}'
    manifest = {'mode': mode, 'name': name, 'parent_if_technical_retry': parent, 'python': PYTHON,
                'files': {p: hash_bytes(raw) for p, raw in sorted(files.items())}}
    if parent:
        failed = HERE / 'attempts' / parent
        seal = load(failed / 'local-seal.json')
        assert all(sha(failed / p) == h for p, h in seal.items())
        assert load(failed / 'run/terminal.json')['status'] == 'technical_failure'
        if mode == 'live':
            assert not list((failed / 'run/source').glob('*/action.json'))
            assert not list((failed / 'run').glob('*/*/start.json'))
        manifest['technical_failure_parent_seal'] = sha(failed / 'local-seal.json')
    script = 'live_capture.py' if mode == 'capture-preflight' else 'live_run.py'
    once = ''
    if mode == 'capture-preflight':
        manifest['preflight_ids'] = list(PREFLIGHT_IDS)
    else:
        proof = HERE / 'attempts' / preflight
        manifest.update(max_primary_calls=36, retries_of_model_or_action=0,
                        capture_preflight=preflight, preflight_seal_sha256=sha(proof / 'local-seal.json'))
        marker = REMOTE + '/live-once-' + (parent or 'first')
        once = f'mkdir {shlex.quote(marker)} && '
        if parent:
            old = REMOTE + '/' + parent + '/remote-seal.json'
            assert (HERE / 'attempts' / parent / 'remote-seal.json').is_file()
            old_seal = sha(HERE / 'attempts' / parent / 'remote-seal.json')
            once = f'test "$(sha256sum {shlex.quote(old)} | cut -d " " -f 1)" = {old_seal} && ' + once
        once += f'printf "%s\n" {shlex.quote(name)} > {shlex.quote(marker + "/attempt")} && '
    files['manifest.json'] = canonical(manifest) + b'\n'
    home.mkdir(parents=True, exist_ok=False)
    for rel, raw in files.items():
        path = home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        put(path, raw)
    put(home / 'remote-root.txt', (remote + '\n').encode())
    print(name, 'input manifest SHA', hash_bytes(files['manifest.json']), flush=True)
    r, python = shlex.quote(remote), shlex.quote(PYTHON)
    command = (f'umask 077; mkdir -p {shlex.quote(REMOTE)} && {once}mkdir {r} && '
               f'tar -xf - -C {r} && cd {r} || exit $?; '
               f'CUDA_VISIBLE_DEVICES= {python} -B -u {script}; run_code=$?; '
               f'{python} -B -u seal_run.py "$run_code" || exit $?; exit "$run_code"')
    with (home / 'driver-stderr.log').open('xb') as stderr:
        rc = subprocess.run(SSH + [command], input=archive_bytes(files), stderr=stderr).returncode
    collect(home, remote)
    terminal = load(home / 'run/terminal.json')
    print('Sealed', name, terminal['status'], flush=True)
    if rc:
        print(terminal.get('error'), flush=True)
    return rc


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('mode', choices=('capture-preflight', 'live'))
    cli.add_argument('--preflight')
    cli.add_argument('--parent')
    args = cli.parse_args()
    assert (args.preflight is not None) == (args.mode == 'live')
    raise SystemExit(main(args.mode, args.preflight, args.parent))
