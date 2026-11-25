"""Read-only ownership gates for one new image-only JEV worker on physical GPU7.

No torch import, GPU allocation, lock acquisition, signals, or HTTP. Existing
FLOCK open descriptions must be inherited from the original four-card holder.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import time


EXPECTED_UID = 1033
PHYSICAL_INDICES = (4, 5, 6, 7)
LEASE_PATH = PurePosixPath('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
LOCK_DIRS = (
    '/home/researcher/.mirage-resource-locks',
    '/home/researcher/defense-resume-20261102-retry2/resource-locks',
)


class ResourceGateError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ResourceGateError(message)


def identity(pid):
    p = Path('/proc') / str(int(pid))
    text = (p / 'stat').read_text()
    tail = text[text.rfind(')') + 2:].split()
    uid = next(line for line in (p / 'status').read_text().splitlines() if line.startswith('Uid:')).split()[1:]
    require(len(set(uid)) == 1, 'Process real/effective/saved/fs UIDs differ')
    return {'pid': int(pid), 'uid': int(uid[0]),
            'command': (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip(),
            'start_ticks': str(tail[19]), 'state': tail[0]}


def same_identity(actual, expected):
    return all(str(actual.get(k)) == str(expected.get(k)) for k in ['pid', 'uid', 'command', 'start_ticks'])


def lock_rows(pid):
    directory = Path('/proc') / str(int(pid))
    rows = []
    for entry in (directory / 'fdinfo').iterdir():
        try:
            info = entry.read_text()
        except FileNotFoundError:
            continue  # A transient unrelated FD is not evidence of a held lock.
        lines = [line for line in info.splitlines() if line.startswith('lock:')]
        if not lines:
            continue
        target = directory / 'fd' / entry.name
        stat = target.stat()
        rows.append({'fd': int(entry.name), 'path': os.readlink(target),
                     'inode': stat.st_ino, 'device': stat.st_dev,
                     'held_lock_lines': lines, 'fdinfo': info})
    return rows


def gpu_state():
    def query(kind, fields):
        result = subprocess.run(['nvidia-smi', '--query-' + kind + '=' + fields,
                                 '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=20)
        require(result.returncode == 0, 'nvidia-smi query failed: ' + kind)
        return result.stdout.splitlines()
    cards = {}
    for line in query('gpu', 'index,uuid,memory.free'):
        index, uuid, free = [x.strip() for x in line.split(',')]
        cards[int(index)] = {'index': int(index), 'uuid': uuid, 'free_mib': int(free)}
    compute = []
    for line in query('compute-apps', 'gpu_uuid,pid,used_memory'):
        if not line.strip():
            continue
        uuid, pid, memory = [x.strip() for x in line.split(',')]
        row = {'uuid': uuid, 'pid': int(pid), 'used_mib': memory}
        target_uuids = {cards[i]['uuid'] for i in PHYSICAL_INDICES if i in cards}
        if uuid in target_uuids:
            try:
                row['actual_identity'] = identity(int(pid))
            except Exception as exc:
                row['identity_read_error'] = {'type': type(exc).__name__, 'detail': str(exc)}
        else:
            row['identity_not_required_outside_task_GPU_scope'] = True
        compute.append(row)
    return {'cards': cards, 'compute': compute}


def expected_lock_paths(lease):
    require(len(lease['gpu']) == 4, 'Lease GPU record count differs')
    cards = {int(row['index']): row['uuid'] for row in lease['gpu']}
    require(sorted(cards) == list(PHYSICAL_INDICES), 'Lease must cover exactly physical GPUs4–7')
    paths = {LOCK_DIRS[0] + '/jev-four-gpu-defense-20261106.lock'}
    for uuid in cards.values():
        for directory in LOCK_DIRS:
            paths.add(directory + '/' + uuid + '.lock')
    require(len(paths) == 9, 'Duplicate GPU UUID or incomplete lease')
    return paths


def validate_snapshot(lease, expected_holder, allow_pids, snapshot, require_empty, minimum_free_mib=23000):
    """Pure checks used by the real collector and CPU resource boundary controls.

    allow_pids is a mapping of PID to full registered identity, never bare PIDs.
    In a worker call only that caller may compute, and only on physical GPU7.
    A registered launcher can be present but cannot compute on any task card.
    """
    require(type(require_empty) is bool, 'require_empty must be boolean')
    require(type(minimum_free_mib) is int and minimum_free_mib >= 23000, 'Initial free-memory floor cannot be lowered')
    require(isinstance(allow_pids, dict) and 1 <= len(allow_pids) <= 2, 'Expected identity mapping of at most worker and launcher')
    require(int(expected_holder['uid']) == EXPECTED_UID, 'Expected holder UID differs')
    require(same_identity(lease['holder'], expected_holder), 'Lease holder differs from reviewed holder')
    actual_holder = snapshot['holder_identity']
    require(same_identity(actual_holder, expected_holder) and actual_holder['state'] not in ['Z', 'X'], 'Holder actual identity is stale')
    require(snapshot['self_identity']['uid'] == EXPECTED_UID, 'Caller UID differs')
    current = int(snapshot['self_identity']['pid'])
    registered = {int(k): v for k, v in allow_pids.items()}
    require(current in registered, 'Caller is not registered')
    for pid, expected in registered.items():
        require(int(expected['pid']) == pid and int(expected['uid']) == EXPECTED_UID, 'Registered PID/UID mismatch')
        actual = snapshot['actual_allowed_identities'].get(pid)
        require(actual is not None and same_identity(actual, expected) and actual['state'] not in ['Z', 'X'], 'Registered process identity is stale')
    cards = {int(row['index']): row['uuid'] for row in lease['gpu']}
    paths = expected_lock_paths(lease)
    records = lease['lock_records']
    require(len(records) == 9 and {x['path'] for x in records} == paths, 'Lease nine lock paths differ')
    require(len({int(x['fd']) for x in records}) == 9, 'Lease FD collision')
    fds = {int(x['fd']) for x in records}
    require(set(snapshot['inherited_fd_numbers']) == fds and len(snapshot['inherited_fd_numbers']) == 9, 'Not exactly nine inherited lease FDs')
    for role in ['holder_locks', 'self_locks']:
        rows = snapshot[role]
        require(len(rows) == 9, 'Actual holder/caller does not have exactly nine held lock FDs')
        by_fd = {int(x['fd']): x for x in rows}
        require(set(by_fd) == fds, 'Actual held lock FDs differ from inherited lease FDs')
        for expected in records:
            row = by_fd[int(expected['fd'])]
            require(row['path'] == expected['path'] and row['inode'] == expected['inode'], 'Held lock file/path/inode differs')
            peer = next(x for x in snapshot['holder_locks'] if int(x['fd']) == int(expected['fd']))
            require(row['device'] == peer['device'], 'Inherited FD device differs from holder')
            require(len(row['held_lock_lines']) == 1, 'Held FLOCK record count differs')
            pieces = row['held_lock_lines'][0].split()
            require('FLOCK' in pieces and 'ADVISORY' in pieces and 'WRITE' in pieces, 'Required FLOCK WRITE is absent')
            require(pieces[pieces.index('WRITE') + 1] == str(expected_holder['pid']), 'FLOCK owner differs from original holder')
    actual_cards = {int(k): v for k, v in snapshot['gpu']['cards'].items()}
    for index, uuid in cards.items():
        require(index in actual_cards and actual_cards[index]['uuid'] == uuid, 'Physical GPU UUID changed')
        if require_empty:
            require(actual_cards[index]['free_mib'] >= minimum_free_mib, 'Not enough exclusive initial GPU headroom')
    task_uuids = set(cards.values())
    for row in snapshot['gpu']['compute']:
        if row['uuid'] not in task_uuids:
            continue
        require(not row.get('identity_read_error'), 'Target GPU process identity is unreadable; refuse inference')
        require(not require_empty, 'Task GPU already has compute before initial load')
        require(row['pid'] in registered, 'Unregistered late compute entered GPUs4–7')
        if 'actual_identity' in row:
            require(same_identity(row['actual_identity'], registered[row['pid']]), 'Actual compute identity differs from registration')
        require(row['pid'] == current and row['uuid'] in task_uuids, 'Only joint caller worker may compute, only on GPUs4–7')
        require(snapshot['cuda_visible_devices'] == '4,5,6,7', 'Joint worker visibility differs from owned GPUs4–7')
    return {'owned_task_group': True, 'require_empty': require_empty,
            'actual_holder': actual_holder, 'actual_allowed_identities': snapshot['actual_allowed_identities'],
            'cards': [actual_cards[i] for i in PHYSICAL_INDICES], 'compute': snapshot['gpu']['compute'],
            'holder_fdinfo': snapshot['holder_locks'], 'inherited_fdinfo': snapshot['self_locks'],
            'four_GPU_reservation_still_active': True, 'actual_compute_role': 'primary_4_5_6_and_single_auxiliary_7_in_one_process',
            'captured_unix': snapshot['captured_unix']}


def assert_owned_resources(lease_path, expected_holder, allow_pids, require_empty, minimum_free_mib=23000):
    lease_path = Path(lease_path)
    require(lease_path.resolve() == LEASE_PATH, 'Unreviewed original lease path')
    raw = lease_path.read_bytes()
    lease = json.loads(raw)
    registered = {int(k): v for k, v in allow_pids.items()} if isinstance(allow_pids, dict) else allow_pids
    snapshot = {
        'holder_identity': identity(expected_holder['pid']), 'self_identity': identity(os.getpid()),
        'actual_allowed_identities': {pid: identity(pid) for pid in registered} if isinstance(registered, dict) else {},
        'holder_locks': lock_rows(expected_holder['pid']), 'self_locks': lock_rows(os.getpid()),
        'inherited_fd_numbers': [int(x) for x in os.environ.get('MIRAGE_GPU_LOCK_FDS', '').split(',') if x],
        'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'gpu': gpu_state(), 'captured_unix': time.time(),
    }
    try:
        result = validate_snapshot(lease, expected_holder, registered, snapshot, require_empty, minimum_free_mib)
    except ResourceGateError as exc:
        exc.resource_evidence = snapshot
        raise
    result['lease_path'] = str(lease_path)
    result['lease_sha256'] = hashlib.sha256(raw).hexdigest()
    return result
