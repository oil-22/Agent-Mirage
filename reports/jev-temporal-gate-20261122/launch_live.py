"""Freeze and launch separate, once-only 3090 browser trials; collect immutable evidence."""

import argparse
import io
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import time

from live_common import canonical, hash_bytes, load, put, save, sha
from prepare_and_probe import HERE, PROJECT, SSH

PACKAGE = PROJECT / 'preparation-1794820110211682400' / 'package'
CROP = HERE.parent / 'crop-visual-replay-20261120' / 'attempt-1795150772352391100'
SHADOW = HERE / 'attempts' / 'shadow-1795283017165610600'
PRIMARY_PYTHON = '/opt/whz/conda-envs/webmall-vlm/bin/python'
REMOTE = '/data/researcher/jev-temporal-gate-20261122'
CAPTURE_INPUTS = ('fixture.html', 'live_plan.json', 'live_common.py', 'live_capture.py', 'capture_gui.py',
                  'temporal_request.py', 'seal_run.py')


def inputs(mode, preflight=None):
    files = {k: (HERE / k).read_bytes() for k in CAPTURE_INPUTS}
    source_manifest = load(PACKAGE / 'manifest.json')['files']

    def copy(rel, name=None):
        v = (PACKAGE / rel).read_bytes()
        assert hash_bytes(v) == source_manifest[rel], rel
        files[name or rel] = v

    copy('receipt_protocol.py')
    copy('flash/gate_core.py', 'gate_core.py')
    if mode == 'live':
        pre = HERE / 'attempts' / preflight
        seal = load(pre / 'local-seal.json')
        assert all(sha(pre / name) == expected for name, expected in seal.items())
        manifest = load(pre / 'manifest.json')
        assert {k: hash_bytes(v) for k, v in files.items()} == manifest['files'], 'Live capture differs from preflight'
        terminal = load(pre / 'run' / 'terminal.json')
        assert terminal['status'] == 'passed' and len(terminal['completed']) == 5 and terminal['new_model_calls'] == 0
        old = load(SHADOW / 'local-seal.json')
        guard = SHADOW / 'resource_guard.py'
        assert sha(guard) == old['resource_guard.py']
        files['resource_guard.py'] = guard.read_bytes()
        for path, name in [('flash/flash-identity.json', 'flash-identity.json'),
                           ('flash/service-config.json', 'service-config.json'), ('flash/gate-contract.json', 'gate-contract.json'),
                           ('flash/wire_contract.py', 'wire_contract.py'), ('primary-reference.json', None),
                           ('actor-template.json', None)]:
            copy(path, name)
        for file in (PACKAGE / 'release').rglob('*.py'):
            copy(file.relative_to(PACKAGE).as_posix())
        for name in ('live_run.py', 'live_models.py', 'live_lease.py'):
            files[name] = (HERE / name).read_bytes()
        final = CROP / 'finalization-01'
        placement = final / 'remote-evidence' / 'public' / 'four-card-placement.json'
        completion = load(final / 'completion-receipt.json')
        assert sha(placement) == completion['files_sha256'][placement.relative_to(CROP.parent).as_posix()]
        assert sha(final / 'postexit-audit.json') == completion['postexit_audit_sha256']
        files['four-card-placement.json'] = placement.read_bytes()
        files['runtime-provenance.json'] = canonical({
            'capture_preflight': preflight, 'capture_preflight_seal': sha(pre / 'local-seal.json'),
            'capture_preflight_terminal': sha(pre / 'run' / 'terminal.json'),
            'release_package_manifest': sha(PACKAGE / 'manifest.json'),
            'pinned_flash_shadow_seal': sha(SHADOW / 'local-seal.json'),
            'main_placement_previous_seal': sha(final / 'completion-receipt.json'),
            'previous_model_attempt': '/data/researcher/jev-defense-four-gpu-20261106/flash-native-source-loop-20261116-linked11/model-attempt-01',
        }) + b'\n'
    return files


def archive_bytes(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tar:
        for name, raw in sorted(files.items()):
            info = tarfile.TarInfo(name); info.size, info.mode = len(raw), 0o600
            tar.addfile(info, io.BytesIO(raw))
    return buf.getvalue()


def collect(home, remote):
    transfer = home / 'collection.tar.partial'
    with transfer.open('xb') as output:
        result = subprocess.run(SSH + [f'cd {remote} && tar -cf - run remote-seal.json'], stdout=output,
                                stderr=subprocess.PIPE, timeout=90)
    put(home / 'collection-stderr.log', result.stderr)
    result.check_returncode()
    with tarfile.open(transfer, mode='r:') as tar:
        for member in tar.getmembers():
            assert member.name == 'remote-seal.json' or member.name == 'run' or member.name.startswith('run/')
        tar.extractall(home, filter='data')
    remote_manifest = load(home / 'remote-seal.json')
    assert remote_manifest['input_manifest_sha256'] == sha(home / 'manifest.json')
    full = {p.relative_to(home).as_posix(): sha(p) for p in (home / 'run').rglob('*') if p.is_file()}
    assert full == remote_manifest['files'], 'postexit run evidence differs from remote SHA seal'
    transfer.rename(home / 'collection.tar')
    save(home / 'local-seal.json', {p.relative_to(home).as_posix(): sha(p) for p in home.rglob('*') if p.is_file()})


def main(mode, preflight=None, parent=None):
    assert preflight is None or re.fullmatch(r'capture-preflight-[0-9]+', preflight)
    files = inputs(mode, preflight)
    name = f'{mode}-{time.time_ns()}'
    home, remote = HERE / 'attempts' / name, f'{REMOTE}/{name}'
    home.mkdir()
    script = 'live_capture.py' if mode == 'capture-preflight' else 'live_run.py'
    manifest = {'mode': mode, 'name': name, 'parent_if_technical_retry': parent,
                'files': {k: hash_bytes(v) for k, v in files.items()}, 'python': PRIMARY_PYTHON}
    if mode == 'live':
        manifest.update(max_primary_calls=7, retries_of_model_or_action=0, recapture_until='YES or explicit operator stop')
        if parent is not None:
            assert re.fullmatch(r'live-[0-9]+', parent)
            failed = HERE / 'attempts' / parent
            assert all(sha(failed / path) == h for path, h in load(failed / 'local-seal.json').items())
            assert load(failed / 'run/terminal.json')['status'] == 'technical_failure'
            # Permit only a pre-action, pre-forward failure. Capture or native
            # processor evidence may exist and remains sealed in the parent.
            assert not list((failed / 'run/source').glob('*/action.json'))
            assert not list((failed / 'run').glob('*/*/start.json'))
            assert not list((failed / 'run').glob('*/*/result.json'))
            manifest['zero_call_technical_failure_parent_seal'] = sha(failed / 'local-seal.json')
    files['manifest.json'] = canonical(manifest) + b'\n'
    for name_inner, raw in files.items():
        p = home / name_inner; p.parent.mkdir(parents=True, exist_ok=True)
        put(p, raw)
    put(home / 'remote-root.txt', (remote + '\n').encode())
    print(name, 'input SHA', hash_bytes(files['manifest.json']), flush=True)
    executable = shlex.quote(PRIMARY_PYTHON)
    command = (f'umask 077; mkdir {remote} && tar -xf - -C {remote} && cd {remote} || exit $?; '
               f'CUDA_VISIBLE_DEVICES= {executable} -B -u {script}; run_code=$?; '
               f'{executable} -B -u seal_run.py "$run_code" || exit $?; exit "$run_code"')
    with (home / 'driver-stderr.log').open('xb') as stderr:
        proc = subprocess.run(SSH + [command], input=archive_bytes(files), stderr=stderr)
    collect(home, remote)
    terminal = load(home / 'run' / 'terminal.json')
    print('Sealed', name, terminal['status'], flush=True)
    if proc.returncode:
        if terminal.get('error'):
            print(terminal['error'], flush=True)
        raise SystemExit(proc.returncode)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('mode', choices=['capture-preflight', 'live'])
    cli.add_argument('--preflight')
    cli.add_argument('--parent')
    args = cli.parse_args()
    assert (args.preflight is not None) == (args.mode == 'live')
    main(args.mode, args.preflight, args.parent)
