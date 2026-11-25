"""Once-only orchestration for the new, source-bound 13-item technical continuation."""
import base64
import hashlib
import io
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding='utf8')
sys.stderr.reconfigure(encoding='utf8')
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
R3090 = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name
R4090 = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name
OUT = R4090
SSH = ['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, v):
    with Path(p).open('x', encoding='utf8') as f:
        json.dump(v, f, ensure_ascii=False, indent=2)


def remote(host, code, label, timeout=55, private_prefix=''):
    directory = HERE / 'operations' / (str(time.time_ns()) + '-' + label)
    directory.mkdir(parents=True)
    (directory / 'source.py').write_text(code, encoding='utf8')
    py = '/opt/whz/conda-envs/webmall-vlm/bin/python' if host == '3090' else '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python'
    try:
        r = subprocess.run(SSH + [host, py + ' -B -'], input=private_prefix + code, text=True, encoding='utf8', capture_output=True, timeout=timeout)
        (directory / 'stdout.txt').write_text(r.stdout, encoding='utf8')
        (directory / 'stderr.txt').write_text(r.stderr, encoding='utf8')
        save(directory / 'receipt.json', {'host': host, 'returncode': r.returncode, 'source_sha256': sha(directory / 'source.py'), 'time': time.time()})
    except BaseException as exc:
        save(directory / 'failure.json', {'type': type(exc).__name__, 'message': str(exc)})
        raise
    if r.returncode:
        raise RuntimeError(str(directory) + '\n' + r.stderr[-3500:] + '\n' + r.stdout[-1500:])
    return r.stdout, directory


def stage():
    assert (HERE / 'CPU-admission-checks.json').exists()
    package = HERE / 'package'
    assert json.loads((HERE / 'CPU-UUID-binding-checks.json').read_bytes())['manifest_sha256'] == sha(package / 'manifest.json')
    manifest = json.loads((package / 'manifest.json').read_bytes())
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in list(manifest['files']) + ['manifest.json', 'private.token']:
            z.writestr(name, (package / name).read_bytes())
    for host, root in [('3090', R3090), ('4090', R4090)]:
        assert not (HERE / ('stage-' + host + '.json')).exists()
        code = 'ROOT=' + repr(root) + '\nEXPECTED=' + repr(sha(package / 'manifest.json')) + '\n' + r'''
import ast,base64,hashlib,io,json,os,zipfile
from pathlib import Path
r=Path(ROOT);r.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for n in z.namelist():
  p=r/n;assert p.resolve().is_relative_to(r.resolve());p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb')as f:f.write(z.read(n))
(r/'private.token').chmod(0o600)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(r/'manifest.json')==EXPECTED
m=json.loads((r/'manifest.json').read_bytes())
for n,h in m['files'].items():
 assert sha(r/n)==h,n
 if n.endswith('.py'):ast.parse((r/n).read_text())
assert len(m['remaining_queue'])==m['trajectories']==13
if os.getuid()==1033:assert not Path(m['output3090']).exists()
print(json.dumps({'root':str(r),'files':len(m['files']),'manifest_sha256':EXPECTED,'new_model_GUI_calls':0}))
'''
        out, op = remote(host, code, 'stage-isolated-linked12-' + host,
                         private_prefix='PAYLOAD=' + repr(base64.b64encode(payload.getvalue()).decode()) + '\n')
        save(HERE / ('stage-' + host + '.json'), {'result': json.loads(out), 'operation': str(op)})
        print(out)


def inspect():
    for host, package in [('3090', R3090), ('4090', R4090)]:
        code = 'PACKAGE=' + repr(package) + '\nEXPECTED=' + repr(sha(HERE / 'package/manifest.json')) + '\n' + r'''
import fcntl,json,os,socket,subprocess,sys,time
from pathlib import Path
p=Path(PACKAGE);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import identity,sha,LEASE,LEASE_SHA,gpu_snapshot
from continuation_guard import verify_native_parent,verify_gui_parent
assert sha(p/'manifest.json')==EXPECTED
if os.getuid()==1033:
 proof=verify_native_parent(p);l=json.loads(LEASE.read_bytes());h=l['holder'];a=identity(h['pid'])
 assert sha(LEASE)==LEASE_SHA and a['state']not in ['Z','X']and all(a[k]==h[k]for k in ['uid','command','start_ticks'])
 for row in l['lock_records']:
  proc=Path('/proc',str(h['pid']));fd=proc/'fd'/str(row['fd'])
  assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and 'WRITE '+str(h['pid'])in(proc/'fdinfo'/str(row['fd'])).read_text()
 s=gpu_snapshot();assert not s['compute']and all(s['gpu'][i]['free_mib']>=23000 for i in range(8))
 handles=[]
 try:
  for i in range(4):
   for parent in [Path('/home/researcher/.mirage-resource-locks'),Path('/home/researcher/defense-resume-20261102-retry2/resource-locks')]:
    f=(parent/(s['gpu'][i]['uuid']+'.lock')).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(f)
 finally:
  for f in handles:f.close()
 for address,port in [('192.0.2.11',19202),('127.0.0.1',18342)]:
  with socket.socket()as sock:sock.bind((address,port))
 assert all(f.with_suffix('.claimed').exists()for f in(LEASE.parent/'commands').glob('*.json'))
 assert not Path(json.loads((p/'manifest.json').read_bytes())['output3090']).exists()
 out={'parent':proof,'actual_original_holder':a,'actual_original_locks':len(l['lock_records']),'GPU':s,'new_GPU_lease_acquired':False,'extra_locks_available_not_yet_leased':True}
else:
 assert os.getuid()==1015;proof=verify_gui_parent(p)
 with(p.parent/'.full-gui-site29980.lock').open('a')as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 ids=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
 rows=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
 assert all(v['Id']==i and v['Config']['Labels']['owner']=='whz-qwen27-vwa'and v['State']['Running']for v,i in zip(rows,ids))
 assert rows[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
 assert any(m.get('Name')=='qwen27_vwa_db_data'for m in rows[1]['Mounts'])
 out={'parent':proof,'site_lock_available':True,'exact_owned_containers_running':True,'no_site_reset_or_import':True}
v=os.statvfs(p)
assert v.f_bavail*v.f_frsize>32*1024**3
print(json.dumps({'time':time.time(),'UID':os.getuid(),'storage_free_bytes':v.f_bavail*v.f_frsize,'new_model_GUI_calls':0,**out}))
'''
        out, op = remote(host, code, 'fresh-actual-linked12-admission-' + host)
        path = HERE / ('admission-' + host + '-' + str(time.time_ns()) + '.json')
        save(path, {'result': json.loads(out), 'operation': str(op)})
        print(json.dumps({'receipt': str(path), 'result': json.loads(out)}))


def service():
    assert all((HERE / ('stage-' + h + '.json')).exists() for h in ['3090', '4090'])
    assert not (HERE / 'service-submission.json').exists()
    code = 'PACKAGE=' + repr(R3090) + '\n' + r'''
import json,os,socket,sys,time
from pathlib import Path
p=Path(PACKAGE);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import LEASE,identity,sha,gpu_snapshot
from continuation_guard import verify_native_parent,validate_leased_UUIDs
proof=verify_native_parent(p);l=json.loads(LEASE.read_bytes());h=l['holder'];a=identity(h['pid'])
assert a['state']not in ['Z','X']and all(a[k]==h[k]for k in ['uid','command','start_ticks'])
for row in l['lock_records']:
 q=Path('/proc',str(h['pid']));fd=q/'fd'/str(row['fd'])
 assert fd.stat().st_ino==row['inode']and os.readlink(fd)==row['path']and 'WRITE '+str(h['pid'])in(q/'fdinfo'/str(row['fd'])).read_text()
assert not Path(json.loads((p/'manifest.json').read_bytes())['output3090']).exists()
s=gpu_snapshot();assert not s['compute']and all(s['gpu'][i]['free_mib']>=23000 for i in range(8))
validate_leased_UUIDs(l,s['gpu'])
output_parent=Path(json.loads((p/'manifest.json').read_bytes())['output3090']).parent
storage=os.statvfs(output_parent);assert storage.f_bavail*storage.f_frsize>64*1024**3
assert all(f.with_suffix('.claimed').exists()for f in(LEASE.parent/'commands').glob('*.json'))
for address,port in [('192.0.2.11',19202),('127.0.0.1',18342)]:
 with socket.socket()as sock:sock.bind((address,port))
c=LEASE.parent/'commands/flash-resource-continuation-20261115-linked12.json'
v={'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',str(p/'launch_group.py')],'script_sha256':sha(p/'launch_group.py')}
with c.open('x')as f:json.dump(v,f,indent=2);f.flush();os.fsync(f.fileno())
print(json.dumps({'command':str(c),'command_sha256':sha(c),'time':time.time(),'once_only':True,'new_launcher_will_acquire_and_inherit_eight_extra_locks':True,'parent_admission':proof}))
'''
    out, op = remote('3090', code, 'submit-new-linked12-services-once')
    save(HERE / 'service-submission.json', {'result': json.loads(out), 'operation': str(op)})
    print(out)


def verify_ready():
    code = 'PACKAGE=' + repr(R3090) + '\nOUTPUT=' + repr(OUT) + '\nEXPECTED=' + repr(sha(HERE / 'package/manifest.json')) + '\n' + r'''
import json,os,sys,time,requests
from pathlib import Path
p=Path(PACKAGE);r=Path(OUTPUT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import identity,sha,LEASE,LEASE_SHA,gpu_snapshot
from continuation_guard import verify_native_parent,validate_leased_UUIDs
assert sha(p/'manifest.json')==EXPECTED
for n,h in json.loads((p/'manifest.json').read_bytes())['files'].items():assert sha(p/n)==h,n
proof=verify_native_parent(p)
records=[json.loads((r/'launcher-process.json').read_bytes()),json.loads((r/'primary/process.json').read_bytes()),json.loads((p/'flash/service/process.json').read_bytes())]
actual=[]
for record in records:
 a=identity(record['pid']);assert a['state']not in ['Z','X']and all(a[k]==record[k]for k in ['uid','command','start_ticks']);actual.append(a)
original=json.loads(LEASE.read_bytes());assert sha(LEASE)==LEASE_SHA
expanded=json.loads((r/'expanded-lease.json').read_bytes());holder=identity(original['holder']['pid'])
assert all(holder[k]==original['holder'][k]for k in ['uid','command','start_ticks'])
assert expanded['holder']['pid']==records[0]['pid']and expanded['original_lock_count']==9 and len(expanded['extra_lock_records'])==8
for process,rows in [(actual[1],original['lock_records']+expanded['extra_lock_records']),(actual[2],original['lock_records'])]:
 for row in rows:
  proc=Path('/proc',str(process['pid']));fd=proc/'fd'/str(row['fd']);owner=original['holder']['pid']if row in original['lock_records']else records[0]['pid']
  assert fd.stat().st_ino==row['inode']and os.readlink(fd)==row['path']and 'WRITE '+str(owner)in(proc/'fdinfo'/str(row['fd'])).read_text()
s=gpu_snapshot()
validate_leased_UUIDs(original,s['gpu'])
for i in range(8):
 assert s['gpu'][i]['uuid']==next(v['uuid']for v in expanded['gpu']if v['index']==i)
 assert {v['pid']for v in s['compute']if v['uuid']==s['gpu'][i]['uuid']}=={records[1 if i<7 else 2]['pid']}
installation=r/'primary/historical-memory-installation'
for n,h in json.loads((installation/'seal.json').read_bytes()).items():assert sha(installation/n)==h
installed=json.loads((installation/'result.json').read_bytes())
assert installed['exact_historical_function_code_installed']and installed['new_capacity_or_invariance_generate_calls']==0
assert not installed['current_process_capacity_tested']and not installed['current_process_full_logit_invariance_tested']
loaded=json.loads((r/'primary/loaded.json').read_bytes());assert loaded['physical_gpus']==list(range(7))and loaded['dtype']=='bfloat16'and loaded['attention']=='sdpa'
assert not list((r/'primary/requests').iterdir())and not list((p/'flash/service/requests').iterdir())
headers={'Authorization':'Bearer '+(p/'private.token').read_text().strip()}
res=requests.get('http://192.0.2.11:19202/health',headers=headers,timeout=15);res.raise_for_status();health=res.json()
assert health['phase']=='ready'and health['done']==0 and health['expected']==13 and health['actor_attempts']==health['actor_replies']==0 and health['active']is None and health['manifest_sha256']==EXPECTED
fres=requests.get('http://127.0.0.1:18342/health',headers={'Authorization':'Bearer '+(p/'flash/service/token').read_text().strip()},timeout=15);fres.raise_for_status();flash=fres.json()
assert flash['status']=='ready'and flash['attempted_calls']==flash['complete_replies']==flash['retained_context_entries']==0
assert flash['contract_sha256']==json.loads((p/'manifest.json').read_bytes())['Flash_contract_sha256']
print(json.dumps({'time':time.time(),'actual_processes':actual,'actual_GPU':s,'primary_held_inherited_locks':17,'Flash_held_inherited_locks':9,'health':health,'Flash_health':flash,'installation':installed,'installation_seal_sha256':sha(installation/'seal.json'),'parent':proof,'model_GUI_calls_before_new_GUI':0}))
'''
    out, op = remote('3090', code, 'verify-actual-model-locks-and-historical-install-before-GUI')
    path = HERE / ('native-ready-' + str(time.time_ns()) + '.json')
    value = json.loads(out)
    save(path, {'result': value, 'operation': str(op)})
    print(json.dumps({'receipt': str(path), 'actual_processes': value['actual_processes'],
                      'primary_held_locks': 17, 'Flash_held_locks': 9, 'model_GUI_calls_before_new_GUI': 0}))
    return path


def gui():
    assert (HERE / 'service-submission.json').exists() and not (HERE / 'GUI-submission.json').exists()
    ready = verify_ready()
    code = 'ROOT=' + repr(R4090) + '\nEXPECTED=' + repr(sha(HERE / 'package/manifest.json')) + '\n' + r'''
import fcntl,json,os,subprocess,sys,requests,time
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from continuation_guard import verify_gui_parent
from resource_guard import sha
assert sha(p/'manifest.json')==EXPECTED
proof=verify_gui_parent(p)
assert not(p/'control').exists()and not(p/'batch').exists()and not(p/'background').exists()
with(p.parent/'.full-gui-site29980.lock').open('a')as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
token=(p/'private.token').read_text().strip()
r=requests.get('http://192.0.2.11:19202/health',headers={'Authorization':'Bearer '+token},timeout=15);r.raise_for_status();h=r.json()
assert h['phase']=='ready'and h['actor_attempts']==h['actor_replies']==h['done']==0 and h['expected']==13 and h['manifest_sha256']==EXPECTED
(p/'background').mkdir()
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(p/'gui_outer.py')]
with(p/'background/outer.log').open('xb')as log:
 child=subprocess.Popen(argv,env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=str(p),start_new_session=True)
with(p/'background/launch.json').open('x')as f:json.dump({'pid':child.pid,'argv':argv,'pre_GUI_health':h,'time':time.time(),'parent_admission':proof},f,indent=2)
print(json.dumps({'pid':child.pid,'argv':argv,'expected_new_trajectories':13,'old_completed_16_reexecuted':False,'historical_failed_T089_and_costs_retained':True}))
'''
    out, op = remote('4090', code, 'launch-only-remaining13-GUI-in-new-linked-attempt')
    save(HERE / 'GUI-submission.json', {'result': json.loads(out), 'operation': str(op), 'native_ready': str(ready)})
    print(out)


def activity():
    for host, root, package in [('3090', OUT, R3090), ('4090', R4090, R4090)]:
        code = 'ROOT=' + repr(root) + '\nPACKAGE=' + repr(package) + '\n' + r'''
import json,sys,time
from pathlib import Path
r=Path(ROOT);p=Path(PACKAGE);sys.path.insert(0,str(p/'flash'));from resource_guard import identity
out={}
for n in ['launcher-process.json','primary/status.json','primary/ready.json','primary/terminal.json','primary/failure.json','launcher-failure.json','exit.json','batch/status.json','GUI-uncaught-failure.json','control/exit.json','primary/historical-memory-installation/result.json']:
 if(r/n).exists():out[n]=json.loads((r/n).read_bytes())
for label,record in [('launcher',r/'launcher-process.json'),('main',r/'primary/process.json'),('Flash',p/'flash/service/process.json'),('GUI',r/'control/runner-process.json')]:
 if not record.exists():continue
 v=json.loads(record.read_bytes());actual=identity(v['pid'])if Path('/proc',str(v['pid'])).exists()else None
 out[label+'_actual']={'saved':v,'actual':actual,'same_live':actual is not None and actual['state']not in ['Z','X']and all(actual[k]==v[k]for k in ['uid','command','start_ticks'])}
for n in ['primary.log','Flash-service.log','control/runner.log','background/outer.log']:
 if(r/n).exists():out[n]=(r/n).read_text()[-1700:]
if(p/'flash/service').exists():out['Flash_complete_replies']=len(list((p/'flash/service/requests').glob('*/response.json')))
print(json.dumps({'time':time.time(),**out}))
'''
        out, op = remote(host, code, 'actual-linked12-activity-' + host)
        path = HERE / ('activity-' + host + '-' + str(time.time_ns()) + '.json')
        save(path, {'result': json.loads(out), 'operation': str(op)})
        print(json.dumps({'host': host, 'receipt': str(path), 'data': json.loads(out)}))


if __name__ == '__main__':
    globals()[sys.argv[1]]()
