"""Exactly twenty new Flash decisions. No primary, GUI, service or retry queue."""
import base64
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P / 'flash'))
from resource_guard import admit, check_card, gpu_snapshot, identity, locks, sha
from flash_runtime import FlashRuntime, save
from gate_core import Journal, canonical, digest
from wire_contract import decode_request, REVISION


def worker(out):
    manifest = json.loads((P / 'manifest.json').read_bytes())
    config = json.loads((P / 'flash/service-config.json').read_bytes())
    contract = json.loads((P / 'flash/gate-contract.json').read_bytes())
    assert config['revision'] == contract['revision'] == REVISION
    assert os.environ['CUDA_VISIBLE_DEVICES'] == str(config['physical_gpu'])
    root = out / 'service'; root.mkdir(exist_ok=False); (root / 'requests').mkdir()
    _, fds = locks()
    save(root / 'process.json', {**identity(os.getpid()), 'visible_devices': os.environ['CUDA_VISIBLE_DEVICES'], 'lock_fds': list(fds)})
    journal = Journal(root / 'journal'); attempted = complete = 0
    status = 'technical_failure'; exit_code = 1
    try:
        runtime = FlashRuntime(root, config, contract)
        journal.emit('loaded', {'loaded_sha256': sha(root / 'loaded.json'), 'contract_sha256': sha(P / 'flash/gate-contract.json')})
        cases = manifest['cases']
        assert len(cases) == len({v['sha256'] for v in cases}) == len({v['request_id'] for v in cases}) == 20
        assert manifest['max_calls'] == 20 and manifest['automatic_retries'] == 0
        for case in cases:
            assert attempted < 20
            png = (P / 'images' / (case['id'] + '.png')).read_bytes()
            assert digest(png) == case['sha256']
            raw = canonical({'request_id': case['request_id'], 'image_sha256': case['sha256'], 'image_png_base64': base64.b64encode(png).decode()})
            request, original = decode_request(raw); assert original == png
            directory = root / 'requests' / request['request_id']; directory.mkdir(exist_ok=False)
            (directory / 'wire-request.bin').write_bytes(raw); (directory / 'original.png').write_bytes(png)
            journal.emit('request_received', {'case_id': case['id'], 'request_id': request['request_id'], 'request_sha256': digest(raw), 'image_sha256': digest(png)})
            try:
                save(directory / 'admission-before.json', admit(config, True))
                attempted += 1
                journal.emit('native_call_started', {'request_id': request['request_id'], 'attempted_calls': attempted})
                choice, audit = runtime.decide(png, directory)
                save(directory / 'admission-after.json', admit(config, True))
                save(directory / 'audit.json', audit)
                save(directory / 'response.json', {'status': 'ok', 'decision': choice, 'request_id': request['request_id'], 'request_sha256': digest(raw), 'image_sha256': digest(png), 'revision': REVISION, 'contract_sha256': sha(P / 'flash/gate-contract.json')})
                complete += 1
            except BaseException:
                save(directory / 'failure.json', {'error': traceback.format_exc(), 'attempted_calls': attempted, 'no_automatic_retry': True, 'not_a_model_NO': True})
                raise
            finally:
                save(directory / 'seal.json', {q.name: sha(q) for q in directory.iterdir() if q.is_file()})
                journal.emit('request_sealed', {'request_id': request['request_id'], 'seal_sha256': sha(directory / 'seal.json'), 'complete': (directory / 'response.json').exists()})
            print(json.dumps({'case_id': case['id'], 'complete': complete, 'attempted': attempted}), flush=True)
        assert attempted == complete == 20
        from resource_guard import checkpoint
        final_identity = checkpoint(config, out)
        assert final_identity == json.loads((root / 'checkpoint-before.json').read_bytes())
        save(root / 'checkpoint-final.json', final_identity)
        status = 'completed'; exit_code = 0
    except BaseException:
        save(root / 'failure.json', {'error': traceback.format_exc(), 'attempted_calls': attempted, 'complete_replies': complete, 'no_automatic_retry': True})
        traceback.print_exc()
    finally:
        journal.emit('terminal', {'status': status, 'attempted_calls': attempted, 'complete_replies': complete})
        save(root / 'terminal.json', {'status': status, 'attempted_calls': attempted, 'complete_replies': complete, 'journal_events': journal.seq, 'journal_head': journal.head, 'time': time.time(), 'new_primary_calls': 0, 'GUI_actions': 0, 'paid_API_calls': 0, 'automatic_retries': 0})
        sys.stdout.flush(); sys.stderr.flush()
    return exit_code


def launch():
    assert os.getuid() == 1033
    manifest = json.loads((P / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(P / name) == expected, name
    out = Path(manifest['output']); out.mkdir(exist_ok=False)
    save(out / 'launcher-process.json', identity(os.getpid()))
    (out / 'flash-identity.json').write_bytes((P / 'flash/flash-identity.json').read_bytes())
    config = json.loads((P / 'flash/service-config.json').read_bytes())
    before = gpu_snapshot(); save(out / 'resource-before-locks.json', before)
    index = config['physical_gpu']; uuid = before['gpu'][index]['uuid']
    held = []; child = None; failure = None; code = 1
    def stop(*_):
        if child is not None and child.poll() is None:
            child.terminate()
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    try:
        check_card(before, index, uuid, False, os.getpid())
        directories = [Path('/home/researcher/.mirage-resource-locks'), Path('/home/researcher/defense-resume-20261102-retry2/resource-locks')]
        for directory in directories:
            directory.mkdir(exist_ok=True)
        paths = [directories[0] / 'jev-flash-buttons-offline-20261116-07.lock'] + [directory / (uuid + '.lock') for directory in directories]
        for path in paths:
            handle = path.open('a'); held.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        after = check_card(gpu_snapshot(), index, uuid, False, os.getpid())
        lease = {'holder': identity(os.getpid()), 'created': time.time(), 'gpu': {'index': index, **after['gpu'][index]}, 'manifest_sha256': sha(P / 'manifest.json'), 'lock_records': [{'path': h.name, 'fd': h.fileno(), 'inode': os.fstat(h.fileno()).st_ino} for h in held], 'reserved_GPUs': 1, 'no_old_broker': True}
        save(out / 'lease.json', lease)
        fds = tuple(h.fileno() for h in held)
        env = {**os.environ, 'CUDA_VISIBLE_DEVICES': str(index), 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1', 'TOKENIZERS_PARALLELISM': 'false', 'OMP_NUM_THREADS': '4', 'MIRAGE_TASK_LEASE': str(out / 'lease.json'), 'MIRAGE_TASK_LEASE_SHA256': sha(out / 'lease.json'), 'MIRAGE_GPU_LOCK_FDS': ','.join(map(str, fds))}
        argv = [config['python'], '-B', '-u', str(P / 'run_offline.py'), '--worker', str(out)]
        with (out / 'worker.log').open('xb') as handle:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT, env=env, pass_fds=fds)
            save(out / 'worker-launch.json', {'identity': identity(child.pid), 'argv': argv, 'lock_fds': list(fds)})
            code = child.wait()
        save(out / 'worker-exit.json', {'exit_code': code, 'time': time.time()})
    except BaseException:
        failure = traceback.format_exc(); save(out / 'launcher-failure.json', {'error': failure, 'no_automatic_retry': True})
        traceback.print_exc()
    finally:
        if child is not None and child.poll() is None:
            child.terminate(); child.wait(timeout=60)
        save(out / 'exit.json', {'exit_code': code, 'failure': failure, 'time': time.time(), 'child_exit_code': child.returncode if child else None})
        for handle in held:
            handle.close()
        save(out / 'released.json', {'time': time.time(), 'fresh_locks_closed': len(held), 'no_broker_left_running': True})
        save(out / 'postexit-seal.json', {q.relative_to(out).as_posix(): sha(q) for q in out.rglob('*') if q.is_file()})
        sys.stdout.flush(); sys.stderr.flush()
    return code


if __name__ == '__main__':
    raise SystemExit(worker(Path(sys.argv[2])) if len(sys.argv) == 3 and sys.argv[1] == '--worker' else launch())
