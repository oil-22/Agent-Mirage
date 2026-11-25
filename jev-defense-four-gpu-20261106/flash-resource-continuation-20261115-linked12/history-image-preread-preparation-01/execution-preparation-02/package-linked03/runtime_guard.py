import hashlib,json,os,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'native/flash'),str(P/'native/release'),str(P/'native')]
from resource_guard import identity,locks,sha,gpu_snapshot,LEASE
PREVIOUS_OUT=Path('/data/researcher/jev-defense-four-gpu-20261106/flash-ample-memory-gui-20261114-linked11')
PREVIOUS_PACKAGE=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-ample-memory-gui-20261114-linked11')
def load(path):
    return json.loads(Path(path).read_bytes())

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def save(path, value):
    with Path(path).open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())

def previous_models_exited():
    records = [PREVIOUS_OUT / 'launcher-process.json', PREVIOUS_OUT / 'primary/process.json',
               PREVIOUS_PACKAGE / 'flash/service/process.json',
               Path('/data/researcher/jev-defense-four-gpu-20261106/flash-resource-continuation-20261115-linked12/launcher-process.json'),
               Path('/data/researcher/jev-defense-four-gpu-20261106/flash-resource-continuation-20261115-linked12/primary/process.json'),
               Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-resource-continuation-20261115-linked12/flash/service/process.json')]
    result = []
    for path in records:
        record = load(path)
        proc = Path('/proc', str(record['pid']))
        actual = identity(record['pid']) if proc.exists() else None
        same_live = actual is not None and actual['state'] not in ['Z', 'X'] and all(actual[k] == record[k] for k in ['pid', 'uid', 'command', 'start_ticks'])
        require(not same_live, 'Previous owned model/launcher is still alive')
        result.append({'record': str(path), 'saved': record, 'actual_if_pid_exists': actual, 'same_live_process': False})
    require((PREVIOUS_OUT / 'postexit-seal.json').exists(), 'Previous final model seal absent')
    return result

def validate_gpu(snapshot, uuids, loaded_pid=None):
    cards = snapshot['gpu']
    require(set(cards) == set(range(8)), 'Expected eight physical3090 devices')
    require(all(cards[i]['uuid'] == uuids[i] for i in range(8)), 'GPU UUID changed')
    for i in range(8):
        pids = {v['pid'] for v in snapshot['compute'] if v['uuid'] == uuids[i]}
        wanted = {loaded_pid} if loaded_pid is not None and i < 7 else set()
        require(pids == wanted, 'Foreign/unverified compute on physical GPU ' + str(i))
    if loaded_pid is None:
        require(all(cards[i]['free_mib'] >= 23000 for i in range(8)), 'Insufficient exclusive GPU memory')

def inherited_locks():
    old, oldfds = locks()
    leasefile = Path(os.environ['MIRAGE_OFFLINE_LEASE'])
    require(sha(leasefile) == os.environ['MIRAGE_OFFLINE_LEASE_SHA256'], 'Offline lease changed')
    lease = load(leasefile)
    holder = lease['holder']
    actual = identity(holder['pid'])
    require(actual['state'] not in ['Z', 'X'] and all(actual[k] == holder[k] for k in ['pid', 'uid', 'command', 'start_ticks']), 'Offline holder changed')
    fds = tuple(int(v) for v in os.environ['MIRAGE_OFFLINE_EXTRA_FDS'].split(','))
    require(len(fds) == 8 and not set(fds).intersection(oldfds), 'All extra GPU locks must be inherited separately')
    require([row['fd'] for row in lease['extra_lock_records']] == list(fds), 'Offline FD set changed')
    for row in lease['extra_lock_records'] + [lease['inference_lock_record']]:
        fd = row['fd']
        require(os.fstat(fd).st_ino == row['inode'] and os.readlink('/proc/self/fd/' + str(fd)) == row['path'], 'Inherited lock identity changed')
        require('WRITE ' + str(holder['pid']) in Path('/proc/self/fdinfo', str(fd)).read_text(), 'Inherited lock not actually held')
    require(len(oldfds) == 9, 'Original nine locks required')
    return lease, oldfds + fds

def resource(loaded):
    require(os.getuid() == 1033, 'Wrong task UID')
    lease, fds = inherited_locks()
    snapshot = gpu_snapshot()
    uuids = {int(v['index']): v['uuid'] for v in lease['gpu']}
    validate_gpu(snapshot, uuids, os.getpid() if loaded else None)
    if loaded:
        for record in snapshot['compute']:
            require(all(record['identity'][k] == identity(os.getpid())[k] for k in ['pid', 'uid', 'command', 'start_ticks']), 'Compute process identity is unbound')
    stat = os.statvfs(P)
    require(stat.f_bavail * stat.f_frsize >= 32 * 1024 ** 3, 'Preserve evidence and wait for storage')
    return {'time': time.time(), 'snapshot': snapshot, 'held_GPU_or_group_locks': len(fds),
            'inference_mutex_inherited': True, 'main_physical_GPUs': list(range(7)),
            'Flash_started': False, 'GPU7_reserved_by_original_lease_but_idle': True,
            'actually_reserved_GPU_count_for_cost': 8}
