"""Fresh four-GPU lease only. No old broker, service retirement or preemption."""
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
    if [r['index'] for r in lease['gpu']] != [0,1,2,3] or len(fds) != 9 or {r['fd'] for r in lease['lock_records']} != set(fds):
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
            try: owner = identity(int(p))
            except OSError: owner = None
            compute.append({'uuid': u, 'pid': int(p), 'used_mib': m, 'identity': owner})
    return {'gpu': cards, 'compute': compute}


def admit(config, loaded):
    lease, _ = locks()
    snapshot = gpu_snapshot()
    index = config['physical_gpu']
    uuid = snapshot['gpu'][index]['uuid']
    if index != 3 or uuid != next(r['uuid'] for r in lease['gpu'] if r['index'] == index):
        raise RuntimeError('Flash GPU not in new lease')
    pids = {r['pid'] if r['identity'] and r['identity']['uid']==1033 else -1 for r in snapshot['compute'] if r['uuid'] == uuid}
    if pids != ({os.getpid()} if loaded else set()):
        raise RuntimeError('Unverified compute on Flash GPU; preserve and stop')
    if not loaded and snapshot['gpu'][index]['free_mib'] < 23000:
        raise RuntimeError('Insufficient exclusive Flash headroom')
    return snapshot


# checkpoint() is copied byte-for-byte from the already audited reference by
# prepare.py. Full weight identity is preserved without redundant full hashing.


def checkpoint(config,root):
    receipt=Path(config['receipt']);stable_path=root/'flash-identity.json'
    if sha(receipt)!=config['receipt_sha256']or sha(stable_path)!=config['stable_identity_sha256']:raise RuntimeError('Model identity receipt mismatch')
    completed=json.loads(receipt.read_bytes());stable=json.loads(stable_path.read_bytes());saved={r['file']:r for r in stable['files']};model=Path(config['model_dir'])
    if completed['revision']!=config['revision']or stable['revision']!=config['revision']:raise RuntimeError('Model revision mismatch')
    rows=[]
    for row in completed['files']:
        p=model/row['file'];s=p.stat();stamp={'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'mtime_ns':s.st_mtime_ns};old=saved[row['file']]
        if p.is_symlink()or not p.resolve().is_relative_to(model.resolve())or stamp!=old['stat']or s.st_size!=row['bytes']or row['sha256']!=old['sha256']:raise RuntimeError('Checkpoint changed since complete byte verification: '+row['file'])
        if p.suffix!='.safetensors'and sha(p)!=row['sha256']:raise RuntimeError('Native source/metadata hash mismatch')
        rows.append({'file':row['file'],'sha256_from_completed_byte_audit':row['sha256'],'stable_stat':stamp})
    return {'revision':config['revision'],'completion_receipt_sha256':sha(receipt),'stable_identity_sha256':sha(stable_path),'files':rows,'no_redundant_full_weight_rehash':True}
