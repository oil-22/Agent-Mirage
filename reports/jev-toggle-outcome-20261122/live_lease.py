"""Acquire one 3090 cohort, sharing inherited locks only with its two owned workers."""

import fcntl
import os
from pathlib import Path
import stat
import subprocess
import time

from live_common import load, process, save, sha

HOME = Path('/home/researcher')
UID = 1033
LOCK_DIRS = (HOME / '.mirage-resource-locks', HOME / 'defense-resume-20261102-retry2/resource-locks')
INFERENCE_LOCK = HOME / 'jev-defense-four-gpu-20261106/inference.lock'


def smi(subset, query):
    cmd = ['nvidia-smi', '-i', ','.join(map(str, subset)), query, '--format=csv,noheader,nounits']
    return [[v.strip() for v in line.split(',')] for line in subprocess.check_output(cmd, text=True, timeout=18).splitlines() if line.strip()]


def compute(subset):
    rows = []
    for uuid, pid, mem in smi(subset, '--query-compute-apps=gpu_uuid,pid,used_gpu_memory'):
        try:
            owner = process(int(pid))
        except (OSError, UnicodeError):
            owner = None
        rows.append({'uuid': uuid, 'pid': int(pid), 'used_mib': int(mem), 'process': owner})
    return rows


def snapshot(indexes):
    devices = smi(indexes, '--query-gpu=index,uuid,memory.free')
    cards = {int(i): {'uuid': u, 'free_mib': int(free)} for i, u, free in devices}
    assert cards.keys() == set(indexes)
    return {'cards': cards, 'compute': compute([cards[i]['uuid'] for i in indexes]), 'at_ns': time.monotonic_ns()}


def verify_locks(lease):
    owner = lease['holder']
    assert os.getuid() == owner['uid'] == UID and process(owner['pid']) == owner, 'GPU parent identity changed'
    for lock in lease['locks']:
        fd = lock['fd']
        assert os.fstat(fd).st_ino == lock['inode'] and os.readlink(f'/proc/self/fd/{fd}') == lock['path']
        held = Path(f'/proc/self/fdinfo/{fd}').read_text().splitlines()
        assert any(f'FLOCK ADVISORY WRITE {owner["pid"]} ' in ' '.join(line.split()) + ' ' for line in held), lock['path']


def admit(lease, role, *, loaded):
    verify_locks(lease)
    if role not in lease['roles']:
        raise ValueError('Unknown role')
    uuids = lease['roles'][role]['uuids']
    assert os.environ['CUDA_VISIBLE_DEVICES'].split(',') == uuids
    apps = compute(uuids)
    if loaded:
        myself = process()
        assert {r['uuid'] for r in apps} == set(uuids) and all(r['process'] == myself for r in apps), 'Unowned or missing GPU compute'
    else:
        assert not apps, 'Another GPU worker appeared before load'
    return {'compute': apps, 'uuids': uuids, 'observed_at_ns': time.monotonic_ns(), 'lock_owner': lease['holder']}


class Cohort:
    def __init__(self, plan, out, *, flash_only=False):
        assert os.getuid() == UID
        self.out, self.files = out, []
        primary, flash = plan['primary_physical_gpus'], [plan['flash_physical_gpu']]
        assert primary == [0, 4, 5, 6] and flash == [7]
        self.indexes = indexes = flash if flash_only else primary + flash
        before = snapshot(indexes)
        save(out / 'selection-before-lock.json', before)
        assert not before['compute'] and min(v['free_mib'] for v in before['cards'].values()) >= 23000, 'Selected GPUs must be exclusive with 23000 MiB each'
        uuids = {i: before['cards'][i]['uuid'] for i in indexes}
        paths = [INFERENCE_LOCK, LOCK_DIRS[0] / 'jev-temporal-gate-20261122.lock']
        paths += [d / (u + '.lock') for u in uuids.values() for d in LOCK_DIRS]
        locks = []
        try:
            for path in sorted(paths):
                fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
                self.files.append(fd)
                st = os.fstat(fd)
                assert st.st_uid == UID and stat.S_ISREG(st.st_mode)
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locks.append({'fd': fd, 'inode': st.st_ino, 'path': str(path)})
            after = snapshot(indexes)
            assert not after['compute'] and min(v['free_mib'] for v in after['cards'].values()) >= 23000
            assert uuids == {i: after['cards'][i]['uuid'] for i in indexes}
            roles = [('flash', flash)] if flash_only else [('primary', primary), ('flash', flash)]
            self.lease = {'holder': process(), 'roles': {role: {'physical': inds, 'uuids': [uuids[i] for i in inds]}
                           for role, inds in roles}, 'locks': locks,
                           'smi_before': before, 'smi_after': after}
            verify_locks(self.lease)
            save(out / 'gpu-lease.json', self.lease)
        except BaseException:
            for fd in self.files:
                os.close(fd)
            raise

    def worker(self, role):
        return {'pass_fds': tuple(self.files), 'env': {**os.environ,
                   'MIRAGE_TEMPORAL_LEASE_SHA256': sha(self.out / 'gpu-lease.json'),
                   'CUDA_VISIBLE_DEVICES': ','.join(self.lease['roles'][role]['uuids']),
                   'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'TOKENIZERS_PARALLELISM': 'false',
                   'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True,garbage_collection_threshold:0.8'}}

    def close(self, worker_pids):
        leases = self.lease['locks']
        final = snapshot(self.indexes)
        assert {r['pid'] for r in final['compute']}.isdisjoint(worker_pids), 'Owned CUDA workers did not exit'
        # Deliberate release only after both subprocesses have fully exited.
        for fd in self.files:
            os.close(fd)
        rows = []
        for other in leases:
            with Path(other['path']).open('rb') as f:
                assert os.fstat(f.fileno()).st_ino == other['inode']
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    state = 'acquired_by_another_process_after_release'
                else:
                    state = 'released_verified'; fcntl.flock(f, fcntl.LOCK_UN)
            rows.append({'path': other['path'], 'inode': other['inode'], 'state': state})
        save(self.out / 'gpu-release.json', {'closed_worker_pids': sorted(worker_pids), 'locks': rows, 'snapshot': final})


def worker_lease(run):
    path = run / 'gpu-lease.json'
    assert sha(path) == os.environ['MIRAGE_TEMPORAL_LEASE_SHA256']
    result = load(path)
    assert result['holder']['pid'] == os.getppid(), 'Not spawned by the authorized GPU cohort'
    verify_locks(result)
    return result
