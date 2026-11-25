"""Actual eight-card compute and inherited-lock admission for every main call."""
import json
import os
import time
from pathlib import Path
from resource_guard import locks, identity, sha, gpu_snapshot


def expanded_locks():
    return locks()


def resource(package, loaded):
    lease, fds = locks()
    snapshot = gpu_snapshot()
    cards = snapshot['gpu']
    for row in lease['gpu']:
        if cards[row['index']]['uuid'] != row['uuid']:
            raise RuntimeError('Freshly leased GPU UUID changed')
    saved = json.loads((package / 'flash/service/process.json').read_bytes())
    actual = identity(saved['pid'])
    if any(saved[k] != actual[k] for k in ['pid', 'uid', 'command', 'start_ticks']):
        raise RuntimeError('Flash identity changed')
    expected = {**{i: os.getpid() if loaded else None for i in range(7)}, 7: saved['pid']}
    for index, pid in expected.items():
        pids = {r['pid'] for r in snapshot['compute'] if r['uuid'] == cards[index]['uuid']}
        if pids != ({pid} if pid is not None else set()):
            root = Path(os.environ['MIRAGE_RESOURCE_FORENSICS_ROOT'])
            root.mkdir(parents=True, exist_ok=True)
            with (root / (str(time.time_ns()) + '.json')).open('x') as f:
                json.dump({'snapshot': snapshot, 'expected': expected, 'not_model_NO': True}, f, indent=2)
            raise RuntimeError('Unverified compute on reserved GPU ' + str(index))
    if not loaded and any(cards[i]['free_mib'] < 23000 for i in range(7)):
        raise RuntimeError('Insufficient empty primary memory')
    stat = os.statvfs(Path(json.loads((package / 'manifest.json').read_bytes())['output3090']))
    if stat.f_bavail * stat.f_frsize < 16 * 1024 ** 3:
        raise RuntimeError('Insufficient evidence storage headroom')
    return {'cards': cards, 'compute': snapshot['compute'], 'held_inherited_locks': len(fds),
            'primary_physical_gpus': list(range(7)), 'Flash_physical_gpu': 7,
            'expanded_lease_sha256': sha(Path(os.environ['MIRAGE_TASK_LEASE']))}
