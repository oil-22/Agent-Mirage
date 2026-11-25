"""One new finite joint worker, inherited lease, marker-only stop, postexit seal."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import traceback

from resource_gate import assert_owned_resources, identity, same_identity

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
LEASE = BASE / 'resource-attempt-20261106-01/lease.json'
PYTHON = '/opt/whz/conda-envs/webmall-vlm/bin/python'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())


def main(a):
    assert a.manifest.resolve().is_relative_to(BASE / 'runtime-preparation/joint-main-controls-20261108-01')
    assert a.output.resolve() == BASE / 'single-evidence-revision-20261107/joint-main-controls-20261108-01'
    assert not a.output.exists() and sha(a.manifest) == a.manifest_sha256
    m = json.loads(a.manifest.read_bytes()); package = a.manifest.parent
    assert m['authorized_finite_joint_development'] is True
    for n, h in m['files'].items():
        assert sha(package / n) == h
    assert sha(__file__) == m['files']['launch_joint_once.py']
    assert os.environ['MIRAGE_TASK_LEASE'] == str(LEASE) and sha(LEASE) == m['lease_sha256']
    me = identity(os.getpid())
    before = assert_owned_resources(LEASE, m['expected_holder'], {me['pid']: me}, True)
    claim_dir = package / 'claims'; claim_dir.mkdir(exist_ok=True)
    save(claim_dir / (a.manifest_sha256 + '.json'), {'manifest_sha256': a.manifest_sha256, 'identity': me,
        'started_unix': time.time(), 'once_only': True, 'no_terminal_retry': True})
    a.output.mkdir(parents=True, exist_ok=False)
    save(a.output / 'before-resources.json', before)
    save(a.output / 'launcher-process.json', me)
    (a.output / 'manifest.json').write_bytes(a.manifest.read_bytes())
    child = None; handle = None; exit_code = 1; failure = None; started = time.time()
    stop = {'value': False}
    def request_stop(*_):
        stop['value'] = True
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        assert_owned_resources(LEASE, m['expected_holder'], {me['pid']: me}, True)
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='4,5,6,7', PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True',
            HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false',
            PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2',
            MIRAGE_JEV_LAUNCHER_IDENTITY=json.dumps(me, sort_keys=True))
        command = [PYTHON, '-u', str(package / 'joint_worker.py'), '--manifest', str(a.manifest),
                   '--manifest-sha256', a.manifest_sha256, '--output', str(a.output / 'worker')]
        fds = tuple(int(x) for x in env['MIRAGE_GPU_LOCK_FDS'].split(','))
        handle = (a.output / 'worker.log').open('xb')
        child = subprocess.Popen(command, cwd=str(package), env=env, stdin=subprocess.DEVNULL,
            stdout=handle, stderr=subprocess.STDOUT, pass_fds=fds, start_new_session=True)
        actual = identity(child.pid)
        assert actual['command'] == ' '.join(command) and actual['uid'] == 1033
        save(a.output / 'worker-launch.json', {'identity': actual, 'argv': command, 'lock_FDs': fds,
            'primary_physical_GPUs': [4, 5, 6], 'auxiliary_physical_GPU': 7})
        while child.poll() is None:
            if stop['value'] and not (a.output / 'stop-requested.json').exists():
                save(a.output / 'stop-requested.json', {'time_unix': time.time(), 'no_next_request': True})
            time.sleep(0.5)
        exit_code = child.returncode
        save(a.output / 'after-resources.json', assert_owned_resources(LEASE, m['expected_holder'], {me['pid']: me}, True))
    except BaseException as exc:
        failure = {'traceback': traceback.format_exc(), 'resource_evidence': getattr(exc, 'resource_evidence', None)}
        save(a.output / 'launcher-failure.json', failure)
        if child is not None and child.poll() is None:
            if not (a.output / 'stop-requested.json').exists():
                save(a.output / 'stop-requested.json', {'reason': 'launcher_exception', 'no_next_request': True})
            while child.poll() is None:
                time.sleep(0.5)
        exit_code = 1
    finally:
        assert child is None or child.poll() is not None
        if handle is not None:
            handle.flush(); os.fsync(handle.fileno()); handle.close()
        ended = time.time()
        save(a.output / 'exit.json', {'worker_exit_code': None if child is None else child.returncode,
            'launcher_exit_code': exit_code, 'failure': failure, 'started_unix': started, 'ended_unix': ended,
            'four_GPU_reserved_seconds_in_launcher': 4 * (ended - started), 'lease_still_held_after_exit': True,
            'automatic_retry': False, 'GUI_started': False})
        save(a.output / 'terminal-manifest.json', {str(p.relative_to(a.output)): sha(p)
            for p in sorted(a.output.rglob('*')) if p.is_file()})
    return exit_code


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    try:
        code = main(a)
    except BaseException:
        target = a.manifest.parent / 'prelaunch-failures' / str(time.time_ns())
        target.mkdir(parents=True, exist_ok=False)
        save(target / 'failure.json', {'traceback': traceback.format_exc(), 'automatic_retry': False})
        code = 1
    raise SystemExit(code)
