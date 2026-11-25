"""Read-only GET-only online-service readiness inspection; no model requests."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

BASE = Path('/home/researcher/jev-defense-four-gpu-20261106')
GROUP = BASE / 'online-service-group-1793978182501156243'
PREP = BASE / 'online-service-preparation-1793978182501156243'
config = json.loads((PREP / 'online-specification.json').read_bytes())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
token = Path(config['token_file']).read_text().strip()
health = {}
for role, port in [('primary', 18127), ('pplx_flash', 18223)]:
    request = urllib.request.Request('http://127.0.0.1:%s/health' % port,
        headers={'Authorization': 'Bearer ' + token}, method='GET')
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        assert response.status == 200
    row = json.loads(raw)
    assert row['phase'] == 'ready_gui' and row['stage'] == 'online_ready', row
    state = row['state']
    assert state['phase'] == 'ready' and state['active'] is None and state['next_run_index'] == 0
    assert len(state['runs']) == 4
    assert all(run['status'] == 'not_started' and run['last_decision_index'] == 0 and
        run['calls'] == {'actor': 0, 'judge': 0, 'observe': 0} for run in state['runs'].values())
    health[role] = row
    assert not list((GROUP / role / 'requests').iterdir())
sys.path.insert(0, str(BASE))
from resource_control import proc_identity, held_locks, gpu_state
lease = json.loads((BASE / 'resource-attempt-20261106-01/lease.json').read_bytes())
workers = {}
for role in ('primary', 'pplx_flash'):
    registered = json.loads((GROUP / 'processes' / (role + '.json')).read_bytes())
    actual = proc_identity(registered['identity']['pid'])
    assert actual == registered['identity']
    assert actual['uid'] == 1033 and actual['command'] == ' '.join(config['commands'][role])
    locks = held_locks(actual['pid'])
    assert all(any(row['path'] == wanted['path'] and row['inode'] == wanted['inode']
                   for row in locks) for wanted in lease['lock_records'])
    loaded = json.loads((GROUP / role / 'loaded.json').read_bytes())
    workers[role] = {'identity': actual, 'held_lock_count': len(locks),
        'loaded_sha256': sha(GROUP / role / 'loaded.json'),
        'ready_sha256': sha(GROUP / role / 'ready.json'), 'loaded': loaded}
resources = gpu_state()
target = {row['uuid'] for row in lease['gpu']}
assert all(row['pid'] in {worker['identity']['pid'] for worker in workers.values()}
           for row in resources['compute'] if row['uuid'] in target)
print(json.dumps({'status': 'ready', 'health': health, 'workers': workers,
    'resources': resources, 'group_files': [p.name for p in GROUP.iterdir()],
    'config_keys': list(config), 'model_requests': 0, 'GUI_requests': 0}))
