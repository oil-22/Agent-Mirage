"""Once-only new eight-GPU lease and model launch, with no old broker actions."""
import fcntl
import json
import os
import signal
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P / 'flash'))
from resource_guard import gpu_snapshot, identity, sha


def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())


def main():
    assert os.getuid() == 1033
    manifest = json.loads((P / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(P / name) == expected, name
    from continuation_guard import verify_native_parent
    prior = verify_native_parent(P)
    out = Path(manifest['output3090'])
    out.mkdir(exist_ok=False)
    me = identity(os.getpid())
    save(out / 'launcher-process.json', me)
    save(out / 'parent-admission.json', prior)
    children, handles, held = [], [], []
    stopping = [False]
    primary_ref = [None]
    def stop(*_):
        stopping[0] = True
        if primary_ref[0] is not None and primary_ref[0].poll() is None:
            primary_ref[0].terminate()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    code, failure = 1, None
    try:
        before = gpu_snapshot()
        save(out / 'resource-before-locks.json', before)
        if before['compute'] or any(before['gpu'][i]['free_mib'] < 23000 for i in range(8)):
            raise RuntimeError('Eight empty task-allocatable GPUs required; no preemption')
        directories = [Path('/home/researcher/.mirage-resource-locks'), Path('/home/researcher/defense-resume-20261102-retry2/resource-locks')]
        for directory in directories:
            directory.mkdir(exist_ok=True)
        paths = [directories[0] / 'paper-paired-action-envelope-v2-1795357311911536100.lock'] + [directory / (before['gpu'][i]['uuid'] + '.lock')
                                                                                     for i in range(8) for directory in directories]
        for path in paths:
            f = path.open('a')
            held.append(f)
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        after = gpu_snapshot()
        if after['compute'] or any(after['gpu'][i]['free_mib'] < 23000 or after['gpu'][i]['uuid'] != before['gpu'][i]['uuid'] for i in range(8)):
            raise RuntimeError('GPU availability changed during atomic lock admission')
        for address, port in [('192.0.2.11', 19202), ('127.0.0.1', 18342)]:
            with socket.socket() as check:
                check.bind((address, port))
        lease = {'holder': me, 'created': time.time(), 'manifest_sha256': sha(P / 'manifest.json'),
                 'gpu': [{'index': i, **after['gpu'][i]} for i in range(8)],
                 'lock_records': [{'path': f.name, 'fd': f.fileno(), 'inode': os.fstat(f.fileno()).st_ino} for f in held],
                 'inference_lock': '/home/researcher/jev-defense-four-gpu-20261106/inference.lock',
                 'new_source_bound_lease': True, 'no_old_services_stopped': True}
        save(out / 'lease.json', lease)
        save(out / 'expanded-lease.json', lease)
        fds = tuple(f.fileno() for f in held)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1',
               'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True,garbage_collection_threshold:0.8',
               'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'TOKENIZERS_PARALLELISM': 'false',
               'MIRAGE_GPU_LOCK_FDS': ','.join(map(str, fds)), 'MIRAGE_TASK_LEASE': str(out / 'lease.json'),
               'MIRAGE_TASK_LEASE_SHA256': sha(out / 'lease.json'),
               'MIRAGE_RESOURCE_FORENSICS_ROOT': str(out / 'primary/resource-conflicts')}
        cfg = json.loads((P / 'flash/service-config.json').read_bytes())
        argv = [cfg['python'], '-B', '-u', str(P / 'flash/flash_service.py'), str(P / 'flash')]
        log = (out / 'Flash-service.log').open('xb')
        handles.append(log)
        child = subprocess.Popen(argv, env={**env, 'CUDA_VISIBLE_DEVICES': '7'}, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT, pass_fds=fds)
        children.append(child)
        save(out / 'Flash-launch.json', {'identity': identity(child.pid), 'argv': argv})
        deadline = time.monotonic() + 300
        while not (P / 'flash/service/ready.json').exists():
            if stopping[0] or child.poll() is not None:
                raise RuntimeError('Flash load failed/stopped; preserve, no automatic retry')
            if time.monotonic() > deadline:
                raise TimeoutError('Flash readiness timeout')
            time.sleep(.5)
        argv = ['/opt/whz/conda-envs/webmall-vlm/bin/python', '-B', '-u', str(P / 'primary_server.py'), str(out / 'primary')]
        log = (out / 'primary.log').open('xb')
        handles.append(log)
        child = subprocess.Popen(argv, env={**env, 'CUDA_VISIBLE_DEVICES': '0,1,2,3,4,5,6', 'CUDA_LAUNCH_BLOCKING': '1'},
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, pass_fds=fds)
        children.append(child)
        primary_ref[0] = child
        save(out / 'primary-launch.json', {'identity': identity(child.pid), 'argv': argv, 'held_inherited_lock_fds': list(fds)})
        code = child.wait()
        save(out / 'primary-exit.json', {'exit_code': code, 'time': time.time()})
    except BaseException:
        failure = {'error': traceback.format_exc(), 'time': time.time(), 'no_automatic_retry': True}
        save(out / 'launcher-failure.json', failure)
        traceback.print_exc()
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=300)
        for log in handles:
            log.flush()
            log.close()
        save(out / 'exit.json', {'time': time.time(), 'exit_code': code, 'failure': failure,
                                 'children': [{'pid': c.pid, 'exit_code': c.returncode} for c in children],
                                 'eight_reserved_GPU_cost_must_be_reported': True})
        for f in held:
            f.close()
        save(out / 'released.json', {'time': time.time(), 'fresh_lease_locks_closed': len(held), 'no_broker_left_running': True})
        save(out / 'postexit-seal.json', {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()} |
             {str(p.relative_to(P)): sha(p) for p in (P / 'flash/service').rglob('*') if p.is_file() and p.name != 'token'})
    return code


if __name__ == '__main__':
    raise SystemExit(main())
