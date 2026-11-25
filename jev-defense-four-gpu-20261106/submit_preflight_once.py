"""Submit exactly the reviewed new preflight to the existing verified holder."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
sys.path.insert(0, str(BASE))
from resource_control import exact_identity, held_locks, gpu_state


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert os.getuid() == 1033
reviewed = BASE / 'reviewed-launch-1793975204954628374'
manifest = json.loads((reviewed / 'seal.json').read_bytes())
assert all(sha(reviewed / name) == value for name, value in manifest.items())
source = reviewed / 'holder-command.json'
receipt = json.loads((reviewed / 'receipt.json').read_bytes())
assert sha(source) == receipt['command_sha256']
command = json.loads(source.read_bytes())
assert command['argv'][-1] == '32eb1e92529aa9ce7223cbf01466dd50874410f5a12602c10b49837fe251844f'
assert sha(Path(command['argv'][command['argv'].index('--spec') + 1])) == command['argv'][-1]
assert not Path(receipt['group']).exists(), 'Reviewed group was already started; inspect it'
holder = BASE / 'resource-attempt-20261106-01'
lease = json.loads((holder / 'lease.json').read_bytes())
actual = exact_identity(lease['holder'])
locks = held_locks(actual['pid'])
assert all(any(row['path'] == x['path'] and row['inode'] == x['inode'] for row in locks)
           for x in lease['lock_records'])
state = gpu_state()
uuids = {row['uuid'] for row in lease['gpu']}
assert not any(row['uuid'] in uuids for row in state['compute'])
assert all(state['gpu'][i]['free_mib'] >= 23000 for i in [4, 5, 6, 7])
target = holder / 'commands/preflight-1793975204991293922.json'
assert not target.exists() and not target.with_suffix('.claimed').exists()
temporary = holder / 'commands' / ('.preflight-' + str(time.time_ns()) + '.tmp')
with temporary.open('xb') as handle:
    handle.write(source.read_bytes())
    handle.flush()
    os.fsync(handle.fileno())
# Hard-link publication is atomic and fails if the destination already exists.
os.link(temporary, target)
temporary.unlink()
print(json.dumps({'submitted': str(target), 'command_sha256': sha(target),
    'group': receipt['group'], 'verified_holder_pid': actual['pid'],
    'held_lock_count': len(locks), 'duplicated_old_queue': False,
    'scope': 'new finite9 observer+1 capacity preflight, no GUI admission'}), flush=True)
