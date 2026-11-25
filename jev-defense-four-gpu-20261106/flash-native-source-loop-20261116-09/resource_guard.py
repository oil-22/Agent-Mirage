"""Fresh eight-GPU lease only. No old broker, service retirement or preemption."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

LEASE = Path(os.environ.get('MIRAGE_TASK_LEASE', '/nonexistent-trusted-capture-lease'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(pid):
    p = Path('/proc', str(pid))
    s = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': int(pid), 'uid': p.stat().st_uid, 'command': (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip(),
            'start_ticks': s[19], 'state': s[0]}


def locks():
    if os.getuid() != 1033 or sha(LEASE) != os.environ['MIRAGE_TASK_LEASE_SHA256']:
        raise RuntimeError('Fresh source-bound owned lease required')
    lease = json.loads(LEASE.read_bytes())
    holder = lease['holder']
    actual = identity(holder['pid'])
    if actual['state'] in ['Z', 'X'] or any(actual[k] != holder[k] for k in ['pid', 'uid', 'command', 'start_ticks']):
        raise RuntimeError('New lease holder identity changed')
    fds = tuple(int(v) for v in os.environ['MIRAGE_GPU_LOCK_FDS'].split(','))
    if len(fds) != 17 or {r['fd'] for r in lease['lock_records']} != set(fds):
        raise RuntimeError('All fresh task/UUID locks must be inherited')
    for row in lease['lock_records']:
        fd = row['fd']
        if (os.fstat(fd).st_ino != row['inode'] or os.readlink('/proc/self/fd/' + str(fd)) != row['path'] or
                'WRITE ' + str(holder['pid']) not in Path('/proc/self/fdinfo', str(fd)).read_text()):
            raise RuntimeError('Actual inherited held lock mismatch')
    return lease, fds


def gpu_snapshot():
    cards, compute = {}, []
    for line in subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.free', '--format=csv,noheader,nounits'], text=True).splitlines():
        i, u, m = [v.strip() for v in line.split(',')]
        cards[int(i)] = {'uuid': u, 'free_mib': int(m)}
    for line in subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,used_gpu_memory', '--format=csv,noheader,nounits'], text=True).splitlines():
        if line.strip():
            u, p, m = [v.strip() for v in line.split(',')]
            compute.append({'uuid': u, 'pid': int(p), 'used_mib': m, 'identity': identity(int(p))})
    return {'gpu': cards, 'compute': compute}


def admit(config, loaded):
    lease, _ = locks()
    snapshot = gpu_snapshot()
    index = config['physical_gpu']
    uuid = snapshot['gpu'][index]['uuid']
    if index != 7 or uuid != next(r['uuid'] for r in lease['gpu'] if r['index'] == index):
        raise RuntimeError('Flash GPU not in new lease')
    pids = {r['pid'] for r in snapshot['compute'] if r['uuid'] == uuid}
    if pids != ({os.getpid()} if loaded else set()):
        raise RuntimeError('Unverified compute on Flash GPU; preserve and stop')
    if not loaded and snapshot['gpu'][index]['free_mib'] < 23000:
        raise RuntimeError('Insufficient exclusive Flash headroom')
    return snapshot


# checkpoint() is copied byte-for-byte from the already audited reference by
# prepare.py. Full weight identity is preserved without redundant full hashing.
