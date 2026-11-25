"""Once-only post-GUI launcher. All admission checks precede weight loading."""
import fcntl
import os
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

import runtime_guard as guard
from runtime_guard import P, load, require, save, sha


def main():
    require(len(sys.argv)==3, 'Real authorization path and SHA required')
    from offline_worker import validate_package
    authorization_path, authorization_sha = Path(sys.argv[1]), sys.argv[2]
    manifest, authorization = validate_package(authorization_path, authorization_sha)
    require(os.getuid()==1033, 'Wrong task UID')
    previous_processes = guard.previous_models_exited()
    old, oldfds = guard.locks()
    first = guard.gpu_snapshot()
    uuids = {int(v['index']): v['uuid'] for v in old['gpu']}
    # The original lease covers4--7; bind0--3 to the previously verified
    # expanded lease, while requiring the old expanded holder to have exited.
    for row in load(guard.PREVIOUS_OUT / 'expanded-lease.json')['gpu']:
        uuids[row['index']] = row['uuid']
    guard.validate_gpu(first, uuids)
    output = Path(manifest['output'])
    output.mkdir(exist_ok=False)
    save(output / 'launcher-process.json', guard.identity(os.getpid()))
    save(output / 'previous-models-exited.json', previous_processes)
    extra, inference, child, code, failure = [], None, None, 1, None
    began = time.time()
    stopped = [False]

    def stop(*_):
        stopped[0] = True
        if child is not None and child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        for index in range(4):
            for directory in [Path('/home/researcher/.mirage-resource-locks'), Path('/home/researcher/defense-resume-20261102-retry2/resource-locks')]:
                f = (directory / (uuids[index] + '.lock')).open('a')
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                extra.append(f)
        inference = Path(old['inference_lock']).open('a')
        fcntl.flock(inference, fcntl.LOCK_EX | fcntl.LOCK_NB)
        again = guard.gpu_snapshot()
        guard.validate_gpu(again, uuids)
        require(not stopped[0], 'Manual stop before model load')
        record = lambda f: {'path': f.name, 'fd': f.fileno(), 'inode': os.fstat(f.fileno()).st_ino}
        lease = {'holder': guard.identity(os.getpid()), 'original_holder': old['holder'],
                 'gpu': [{'index': i, 'uuid': uuids[i]} for i in range(8)],
                 'extra_lock_records': [record(f) for f in extra],
                 'inference_lock_record': record(inference),
                 'original_lock_count': len(oldfds), 'created': began,
                 'actually_reserved_GPUs_including_idle7': 8,
                 'authorization_sha256': sha(authorization_path)}
        leasefile = output / 'offline-lease.json'
        save(leasefile, lease)
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1',
               'CUDA_VISIBLE_DEVICES': '0,1,2,3,4,5,6', 'CUDA_LAUNCH_BLOCKING': '1',
               'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True,garbage_collection_threshold:0.8',
               'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'TOKENIZERS_PARALLELISM': 'false',
               'MIRAGE_OFFLINE_LEASE': str(leasefile), 'MIRAGE_OFFLINE_LEASE_SHA256': sha(leasefile),
               'MIRAGE_OFFLINE_EXTRA_FDS': ','.join(str(f.fileno()) for f in extra)}
        argv = ['/opt/whz/conda-envs/webmall-vlm/bin/python', '-B', '-u', str(P / 'offline_worker.py'), str(authorization_path), authorization_sha]
        with (output / 'worker.log').open('xb') as log:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                     env=env, cwd=str(P), pass_fds=oldfds + tuple(f.fileno() for f in extra) + (inference.fileno(),))
            save(output / 'worker-launch.json', {'identity': guard.identity(child.pid), 'argv': argv})
            code = child.wait()
    except BaseException:
        failure = {'error': traceback.format_exc(), 'time': time.time(), 'no_automatic_retry': True}
        save(output / 'launcher-failure.json', failure)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=300)
            except subprocess.TimeoutExpired:
                save(output / 'shutdown-pending.json', {'identity': guard.identity(child.pid), 'no_forced_kill': True})
                # Do not release inherited resource locks under a live model.
                child.wait()
        save(output / 'exit.json', {'exit_code': code, 'child_exit': None if child is None else child.returncode,
             'failure': failure, 'began': began, 'ended': time.time(), 'reserved_GPU_count': 8,
             'reserved_seconds_scope': 'Eight inherited/expanded task reservations during this launcher interval; original holder reservation outside it excluded.',
             'no_automatic_retry': True})
        save(output / 'postexit-seal.json', {str(p.relative_to(output)): sha(p) for p in output.rglob('*') if p.is_file()})
        if inference is not None:
            inference.close()
        for f in extra:
            f.close()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
