"""Fresh single-GPU lease; native inference and checkpoint identity are unchanged."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

LEASE = Path(os.environ.get('MIRAGE_TASK_LEASE', '/nonexistent-flash-buttons-lease'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(pid):
    root = Path('/proc', str(pid))
    stat = (root / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': int(pid), 'uid': root.stat().st_uid, 'command': (root / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip(), 'start_ticks': stat[19], 'state': stat[0]}


def gpu_snapshot():
    cards, compute = {}, []
    for line in subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.free', '--format=csv,noheader,nounits'], text=True).splitlines():
        index, uuid, free = [v.strip() for v in line.split(',')]
        cards[int(index)] = {'uuid': uuid, 'free_mib': int(free)}
    for line in subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,used_gpu_memory', '--format=csv,noheader,nounits'], text=True).splitlines():
        if line.strip():
            uuid, pid, used = [v.strip() for v in line.split(',')]
            compute.append({'uuid': uuid, 'pid': int(pid), 'used_mib': used, 'identity': identity(int(pid))})
    return {'time': __import__('time').time(), 'gpu': cards, 'compute': compute}


def check_card(snapshot, index, uuid, loaded, own_pid):
    card = snapshot['gpu'][index]
    if card['uuid'] != uuid:
        raise RuntimeError('GPU UUID changed')
    pids = {r['pid'] for r in snapshot['compute'] if r['uuid'] == uuid}
    if pids != ({own_pid} if loaded else set()):
        raise RuntimeError('Other compute on selected GPU; no sharing or preemption')
    if not loaded and card['free_mib'] < 23000:
        raise RuntimeError('Exclusive GPU headroom below 23000 MiB')
    return snapshot


def locks():
    if os.getuid() != 1033 or sha(LEASE) != os.environ['MIRAGE_TASK_LEASE_SHA256']:
        raise RuntimeError('Fresh owned lease required')
    lease = json.loads(LEASE.read_bytes())
    holder = lease['holder']; actual = identity(holder['pid'])
    if actual['state'] in ['Z', 'X'] or any(actual[k] != holder[k] for k in ['pid', 'uid', 'command', 'start_ticks']):
        raise RuntimeError('Fresh holder identity changed')
    fds = tuple(int(v) for v in os.environ['MIRAGE_GPU_LOCK_FDS'].split(','))
    if len(fds) != 3 or {v['fd'] for v in lease['lock_records']} != set(fds):
        raise RuntimeError('All three single-GPU locks must be inherited')
    for row in lease['lock_records']:
        fd = row['fd']
        if os.fstat(fd).st_ino != row['inode'] or os.readlink('/proc/self/fd/' + str(fd)) != row['path'] or 'WRITE ' + str(holder['pid']) not in Path('/proc/self/fdinfo', str(fd)).read_text():
            raise RuntimeError('Actual inherited kernel lock mismatch')
    return lease, fds


def admit(config, loaded):
    lease, _ = locks()
    if config['physical_gpu'] != lease['gpu']['index']:
        raise RuntimeError('Config outside fresh lease')
    return check_card(gpu_snapshot(), config['physical_gpu'], lease['gpu']['uuid'], loaded, os.getpid())


# The previously byte-audited checkpoint() is appended verbatim by preparation.
