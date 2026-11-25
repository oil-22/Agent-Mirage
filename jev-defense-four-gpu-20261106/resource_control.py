"""Retire exactly two verified idle owned services, then hold GPUs4-7 for this task.

No model calls. Commands accepted by the holder are explicit sealed task launchers,
not shell strings. Every old service file is retained and snapshotted before stop.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback
import urllib.request

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
OLD = Path('/home/researcher/jev-defense-local-20261102')
UID = 1033
EXPECTED = [('neo-01', 'neohorse', 4, 19), ('style-02', 'jev_style', 5, 0)]
LOCK_DIRS = [Path('/home/researcher/.mirage-resource-locks'),
             Path('/home/researcher/defense-resume-20261102-retry2/resource-locks')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def proc_identity(pid):
    p = Path('/proc') / str(pid)
    stat = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': pid, 'uid': p.stat().st_uid,
            'command': (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip(),
            'start_ticks': stat[19], 'state': stat[0]}


def gpu_state():
    def query(kind, columns):
        return subprocess.check_output(['nvidia-smi', '--query-' + kind + '=' + columns,
                                        '--format=csv,noheader,nounits'], text=True).strip().splitlines()
    cards = {}
    for line in query('gpu', 'index,uuid,memory.free'):
        index, uuid, free = [x.strip() for x in line.split(',')]
        cards[int(index)] = {'index': int(index), 'uuid': uuid, 'free_mib': int(free)}
    compute = []
    for line in query('compute-apps', 'gpu_uuid,pid,used_gpu_memory'):
        if not line.strip():
            continue
        uuid, pid, memory = [x.strip() for x in line.split(',')]
        compute.append({'uuid': uuid, 'pid': int(pid), 'used_mib': memory,
                        'identity': proc_identity(int(pid))})
    return {'gpu': cards, 'compute': compute, 'time': time.time()}


def held_locks(pid):
    p = Path('/proc') / str(pid)
    locks = []
    for fd in (p / 'fdinfo').iterdir():
        text = fd.read_text()
        if 'lock:' in text:
            target = p / 'fd' / fd.name
            locks.append({'path': os.readlink(target), 'inode': target.stat().st_ino,
                          'fd': int(fd.name), 'info': text})
    return locks


def established_clients(port):
    found = []
    for path in ['/proc/net/tcp', '/proc/net/tcp6']:
        for line in Path(path).read_text().splitlines()[1:]:
            fields = line.split()
            if int(fields[1].split(':')[1], 16) == port and fields[3] == '01':
                found.append(line.strip())
    return found


def verify_old(name, model, index, expected_requests, state):
    run = OLD / 'services' / name
    launch = json.loads((run / 'launch.json').read_bytes())
    identity = proc_identity(launch['pid'])
    original_process = json.loads((run / 'runtime/process.json').read_bytes())
    assert launch['model'] == model and launch['physical_gpu'] == index
    assert identity['uid'] == UID and launch['uid'] == UID
    assert identity['command'] == ' '.join(launch['command'])
    assert identity['start_ticks'] == original_process['start_ticks']
    assert identity['state'] not in {'Z', 'X'}
    uuid = state['gpu'][index]['uuid']
    assert launch['gpu']['uuid'] == uuid
    assert {r['pid'] for r in state['compute'] if r['uuid'] == uuid} == {identity['pid']}
    locks = held_locks(identity['pid'])
    for lock in launch['locks']:
        assert any(l['path'] == lock['path'] and l['inode'] == lock['inode'] for l in locks)
    port = int(launch['command'][-1])
    with urllib.request.urlopen('http://127.0.0.1:' + str(port) + '/health', timeout=5) as response:
        health = json.load(response)
    assert health['phase'] == 'ready' and health['pid'] == identity['pid']
    assert health['uid'] == UID and health['model'] == model
    assert health['revision'] == launch['revision']
    assert health['exclusive_gpu'] is True
    requests = [p for p in (run / 'runtime/requests').iterdir() if p.is_dir()]
    assert len(requests) == expected_requests
    for request in requests:
        seal = json.loads((request / 'seal.json').read_bytes())
        assert (request / 'response.json').is_file() and not (request / 'failure.json').exists()
        assert all(sha(request / n) == h for n, h in seal.items())
    assert not established_clients(port), 'Old service has connected clients'
    files = {str(p.relative_to(run)): sha(p) for p in run.rglob('*') if p.is_file()}
    return {'name': name, 'model': model, 'gpu_index': index, 'gpu_uuid': uuid,
            'identity': identity, 'locks': locks, 'health': health, 'port': port,
            'completed_requests': len(requests), 'source_files': files}


def exact_identity(expected):
    actual = proc_identity(expected['pid'])
    assert all(actual[k] == expected[k] for k in ['pid', 'uid', 'command', 'start_ticks'])
    return actual


def run_holder(root):
    assert os.getuid() == UID
    save(root / 'process.json', proc_identity(os.getpid()))
    (root / 'resource_control.py').write_bytes(Path(__file__).read_bytes())
    state = gpu_state()
    save(root / 'before-gpu.json', state)
    for index in [6, 7]:
        assert not any(r['uuid'] == state['gpu'][index]['uuid'] for r in state['compute'])
        assert state['gpu'][index]['free_mib'] >= 23000
    rows = [verify_old(*spec, state) for spec in EXPECTED]
    save(root / 'before-stop.json', {'authorization': 'User: 腾出4-7卡用来开始实验',
                                    'old_services': rows, 'foreign_tasks_modified': False})
    for row in rows:
        run = OLD / 'services' / row['name']
        snapshot = root / ('old-' + row['name'])
        shutil.copytree(run, snapshot)
        assert all(sha(snapshot / name) == value for name, value in row['source_files'].items())
    time.sleep(0.4)
    for row in rows:
        exact_identity(row['identity'])
        run = OLD / 'services' / row['name']
        assert row['source_files'] == {str(p.relative_to(run)): sha(p)
                                       for p in run.rglob('*') if p.is_file()}
        assert not established_clients(row['port'])
    # Every service and snapshot is checked before the first signal.
    stopped = []
    for row in rows:
        exact_identity(row['identity'])
        os.kill(row['identity']['pid'], signal.SIGTERM)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            p = Path('/proc') / str(row['identity']['pid'])
            if not p.exists() or proc_identity(row['identity']['pid'])['state'] == 'Z':
                break
            time.sleep(0.1)
        else:
            raise RuntimeError('Verified owned service did not exit on SIGTERM; no broad kill')
        run = OLD / 'services' / row['name']
        stopped.append({**row['identity'], 'signal': 'SIGTERM', 'name': row['name'],
                        'postexit_files': {str(p.relative_to(run)): sha(p)
                                          for p in run.rglob('*') if p.is_file()}})
    save(root / 'retired-services.json', {'stopped': stopped, 'time': time.time(),
                                         'model_calls': 0, 'GUI_actions': 0})
    locks = []
    for directory in LOCK_DIRS:
        directory.mkdir(exist_ok=True)
    task_lock = (LOCK_DIRS[0] / 'jev-four-gpu-defense-20261106.lock').open('a')
    fcntl.flock(task_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    locks.append(task_lock)
    state = gpu_state()
    for index in [4, 5, 6, 7]:
        card = state['gpu'][index]
        assert not any(r['uuid'] == card['uuid'] for r in state['compute'])
        assert card['free_mib'] >= 23000
        for directory in LOCK_DIRS:
            lock = (directory / (card['uuid'] + '.lock')).open('a')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locks.append(lock)
    state = gpu_state()
    for index in [4, 5, 6, 7]:
        assert not any(r['uuid'] == state['gpu'][index]['uuid'] for r in state['compute'])
        assert state['gpu'][index]['free_mib'] >= 23000
    lease = {'root': str(root), 'holder': proc_identity(os.getpid()),
             'gpu': [state['gpu'][i] for i in [4, 5, 6, 7]],
             'lock_records': [{'path': f.name, 'inode': os.fstat(f.fileno()).st_ino,
                               'fd': f.fileno()} for f in locks],
             'inference_lock': str(BASE / 'inference.lock'),
             'created': time.time(), 'mode': 'owned_four_gpu_task_group',
             'model_calls': 0, 'GUI_actions': 0}
    save(root / 'lease.json', lease)
    save(root / 'after-gpu.json', state)
    save(root / 'retirement-seal.json', {str(p.relative_to(root)): sha(p)
                                        for p in root.rglob('*') if p.is_file()
                                        and p.name not in {'holder.log', 'retirement-seal.json'}})
    commands = root / 'commands'
    commands.mkdir()
    print(json.dumps({'lease_ready': str(root / 'lease.json'), 'stopped_owned':
                      [r['identity']['pid'] for r in rows], 'gpu': [4, 5, 6, 7]}), flush=True)
    children = []
    while True:
        for command_file in sorted(commands.glob('*.json')):
            claimed = command_file.with_suffix('.claimed')
            if claimed.exists():
                continue
            command = json.loads(command_file.read_bytes())
            save(claimed, {'sha256': sha(command_file), 'time': time.time()})
            if command['action'] == 'release':
                assert not any(p.poll() is None for p in children), 'Task launcher still active'
                fresh = gpu_state()
                target_uuids = {c['uuid'] for c in lease['gpu']}
                assert not any(r['uuid'] in target_uuids for r in fresh['compute']), 'GPU worker remains after launcher exit'
                save(root / 'released.json', {'time': time.time(), 'model_calls_by_holder': 0})
                return
            assert command['action'] == 'launch'
            argv = command['argv']
            assert argv[0] == '/opt/whz/conda-envs/webmall-vlm/bin/python'
            script = Path(argv[1]).resolve()
            assert script.is_relative_to(BASE / 'runtime-preparation') and script.suffix == '.py'
            assert sha(script) == command['script_sha256']
            assert not any(p.poll() is None for p in children), 'Duplicate active task launcher'
            fresh = gpu_state()
            target_uuids = {c['uuid'] for c in lease['gpu']}
            assert not any(r['uuid'] in target_uuids for r in fresh['compute']), 'Uncollected GPU worker; inspect before new attempt'
            child_env = dict(os.environ)
            child_env.update({'CUDA_VISIBLE_DEVICES': '4,5,6,7',
                              'MIRAGE_GPU_LOCK_FDS': ','.join(str(f.fileno()) for f in locks),
                              'MIRAGE_TASK_LEASE': str(root / 'lease.json'),
                              'PYTHONUNBUFFERED': '1'})
            log = root / (command_file.stem + '.log')
            with log.open('xb') as handle:
                p = subprocess.Popen(argv, cwd=str(BASE), env=child_env, stdout=handle,
                                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                     pass_fds=tuple(f.fileno() for f in locks), start_new_session=True)
            children.append(p)
            save(root / (command_file.stem + '-launch.json'), {'pid': p.pid, 'argv': argv,
                                                             'command_sha256': sha(command_file),
                                                             'time': time.time(), 'log': str(log)})
        for child in children:
            result = root / ('child-' + str(child.pid) + '-exit.json')
            code = child.poll()
            if code is not None and not result.exists():
                save(result, {'pid': child.pid, 'exit_code': code, 'time': time.time()})
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--worker', action='store_true')
    a = parser.parse_args()
    assert a.root.resolve().is_relative_to(BASE)
    if not a.worker:
        a.root.mkdir(parents=True, exist_ok=False)
        argv = [sys.executable, '-u', str(Path(__file__).resolve()), '--root', str(a.root), '--worker']
        with (a.root / 'holder.log').open('xb') as log:
            child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
        save(a.root / 'holder-launch.json', {'pid': child.pid, 'uid': os.getuid(),
                                            'argv': argv, 'source_sha256': sha(Path(__file__)),
                                            'time': time.time()})
        print(json.dumps({'holder_pid': child.pid, 'root': str(a.root)}))
    else:
        try:
            run_holder(a.root)
        except BaseException:
            save(a.root / 'failure.json', {'error': traceback.format_exc(), 'time': time.time(),
                                            'model_calls_by_holder': 0})
            traceback.print_exc()
            raise SystemExit(1)


if __name__ == '__main__':
    main()
