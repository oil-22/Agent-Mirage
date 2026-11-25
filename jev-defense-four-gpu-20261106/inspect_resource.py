"""Read actual holder identity, inherited locks, GPU state and preserved source seals."""
import argparse
import json
from pathlib import Path
import time
from resource_control import proc_identity, held_locks, gpu_state, sha, save

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, required=True)
a = parser.parse_args()
if not (a.root / 'lease.json').exists():
    print(json.dumps({'lease_ready': False,
                      'failure': json.loads((a.root / 'failure.json').read_bytes())
                      if (a.root / 'failure.json').exists() else None,
                      'log_tail': (a.root / 'holder.log').read_text()[-3500:]}))
    raise SystemExit(0)
lease = json.loads((a.root / 'lease.json').read_bytes())
actual = proc_identity(lease['holder']['pid'])
assert all(actual[k] == lease['holder'][k] for k in ['pid', 'uid', 'command', 'start_ticks'])
locks = held_locks(actual['pid'])
assert all(any(r['path'] == x['path'] and r['inode'] == x['inode'] for r in locks)
           for x in lease['lock_records'])
manifest = json.loads((a.root / 'retirement-seal.json').read_bytes())
assert all(sha(a.root / n) == h for n, h in manifest.items())
state = gpu_state()
result = {'holder': actual, 'held_lock_count': len(locks), 'sealed_files': len(manifest),
          'seal_sha256': sha(a.root / 'retirement-seal.json'),
          'retirement': json.loads((a.root / 'retired-services.json').read_bytes()),
          'gpu_state': state, 'new_model_calls': 0, 'new_GUI_actions': 0,
          'claimed_commands': [str(p) for p in (a.root / 'commands').glob('*.claimed')]}
target = a.root / ('inspection-' + str(time.time_ns()) + '.json')
save(target, result)
print(json.dumps({'receipt': str(target), 'holder_pid': actual['pid'], 'held_lock_count': len(locks),
                  'sealed_files': len(manifest),
                  'retired_owned_pids': [r['pid'] for r in result['retirement']['stopped']],
                  'gpu': state['gpu'], 'compute': [{'uuid': r['uuid'], 'pid': r['pid'],
                                                   'uid': r['identity']['uid']} for r in state['compute']]}))
