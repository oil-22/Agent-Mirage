"""Fresh lease reservation bounds, checked after actual model/launcher exit."""
import json
import time
from control import HERE, manifest, remote, save, sha

CODE = r'''
import hashlib,json,time
from pathlib import Path
o=Path(O)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lease=json.loads((o/'lease.json').read_bytes());exit=json.loads((o/'exit.json').read_bytes());released=json.loads((o/'released.json').read_bytes())
for saved in[lease['holder'],json.loads((o/'primary/process.json').read_bytes()),json.loads((Path(P)/'flash/service/process.json').read_bytes())]:
 p=Path('/proc',str(saved['pid']))
 if p.exists():
  s=(p/'stat').read_text().rsplit(')',1)[1].split();assert s[0]in['Z','X']or s[19]!=saved['start_ticks']
assert exit['exit_code']==0 and exit['failure']is None and all(v['exit_code']==0 for v in exit['children'])
assert released['fresh_lease_locks_closed']==17 and released['no_broker_left_running']
before=(o/'resource-before-locks.json').stat().st_mtime_ns/1e9
assert before<=lease['created']<=exit['time']<=released['time']
print(json.dumps({'time':time.time(),'start_lower_bound':before,'start_upper_bound':lease['created'],'end_lower_bound':exit['time'],'end_upper_bound':released['time'],'GPU_seconds_lower':8*(exit['time']-lease['created']),'GPU_seconds_upper':8*(released['time']-before),'reserved_GPUs':8,'primary_GPUs':7,'Flash_GPUs':1,'lease_sha256':sha(o/'lease.json'),'release_sha256':sha(o/'released.json'),'includes_loading_and_idle_readiness':True,'no_old_broker_interval':True,'not_currency_energy_or_walltime':True,'new_model_GUI_calls':0}))
'''

if __name__ == '__main__':
    assert not (HERE / 'resource-interval-audit-current.json').exists()
    group = json.loads((HERE / 'completed-group-audit-current.json').read_bytes())
    assert sha(__import__('pathlib').Path(group['root']) / 'seal.json') == group['seal_sha256']
    assert json.loads((__import__('pathlib').Path(group['root']) / 'summary.json').read_bytes())['all_model_GUI_launcher_processes_verified_exited']
    m = manifest()
    raw, operation = remote('3090', 'O=' + repr(m['output3090']) + '\nP=' + repr(m['package3090']) + '\n' + CODE, 'fresh-protocol-reserved-eight-GPU-cost')
    root = HERE / ('resource-interval-audit-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'result.json', {'operation': str(operation), **json.loads(raw)})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(HERE / 'resource-interval-audit-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), 'GPU_seconds_bounds': [json.loads(raw)['GPU_seconds_lower'], json.loads(raw)['GPU_seconds_upper']]}))
