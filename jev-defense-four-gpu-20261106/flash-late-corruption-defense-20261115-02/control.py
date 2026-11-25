"""New-study orchestration only. Commands and GPU leases are once-only."""
import base64
import hashlib
import importlib.util
import io
import json
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'package'
spec = importlib.util.spec_from_file_location('prior_readonly_transport', HERE.parent / 'flash-resource-continuation-20261115-linked12/control.py')
transport = importlib.util.module_from_spec(spec); spec.loader.exec_module(transport)
remote = transport.remote


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with Path(p).open('x', encoding='utf8') as f: json.dump(value, f, ensure_ascii=False, indent=2)


def manifest(): return json.loads((PACKAGE / 'manifest.json').read_bytes())


def stage():
    assert json.loads((HERE / 'CPU-injection-order.json').read_bytes())['passed'] >= 20
    m = manifest(); data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in [*m['files'], 'manifest.json', 'private.token']:
            if name in m['files']: assert sha(PACKAGE / name) == m['files'][name]
            archive.writestr(name, (PACKAGE / name).read_bytes())
    for host in ['3090', '4090']:
        pointer = HERE / ('stage-' + host + '.json'); assert not pointer.exists()
        code = 'ROOT=' + repr(m['package' + host]) + '\nEXPECTED=' + repr(sha(PACKAGE / 'manifest.json')) + '\n' + r'''
import ast,base64,hashlib,io,json,os,zipfile
from pathlib import Path
p=Path(ROOT);p.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD,validate=True)))as z:
 for name in z.namelist():
  dest=p/name;assert dest.resolve().is_relative_to(p.resolve());dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb')as f:f.write(z.read(name))
(p/'private.token').chmod(0o600)
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
assert sha(p/'manifest.json')==EXPECTED
m=json.loads((p/'manifest.json').read_bytes());assert m['trajectories']==12
for name,h in m['files'].items():
 assert sha(p/name)==h,name
 if name.endswith('.py'):ast.parse((p/name).read_text())
assert sha(p/'private.token')==m['auth_token_sha256']
print(json.dumps({'package':str(p),'files':len(m['files']),'manifest_sha256':EXPECTED,'new_model_GUI_calls':0}))
'''
        raw, op = remote(host, code, 'stage-new-injection-first-' + host, private_prefix='PAYLOAD=' + repr(base64.b64encode(data.getvalue()).decode()) + '\n')
        save(pointer, {'operation': str(op), 'result': json.loads(raw)}); print(raw)


def submit():
    assert all((HERE / ('stage-' + h + '.json')).exists() for h in ['3090', '4090'])
    assert not (HERE / 'service-submission.json').exists()
    m = manifest()
    code = 'PACKAGE=' + repr(m['package3090']) + '\nEXPECTED=' + repr(sha(PACKAGE / 'manifest.json')) + '\n' + r'''
import json,os,socket,sys,time
from pathlib import Path
p=Path(PACKAGE);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import LEASE,LEASE_SHA,identity,sha,gpu_snapshot
from continuation_guard import verify_native_parent,validate_leased_UUIDs
assert sha(p/'manifest.json')==EXPECTED and sha(LEASE)==LEASE_SHA
m=json.loads((p/'manifest.json').read_bytes());assert not Path(m['output3090']).exists()
proof=verify_native_parent(p);lease=json.loads(LEASE.read_bytes());h=lease['holder'];a=identity(h['pid'])
assert a['state']not in ['Z','X']and all(a[k]==h[k]for k in ['uid','command','start_ticks'])
for row in lease['lock_records']:
 q=Path('/proc',str(h['pid']));fd=q/'fd'/str(row['fd'])
 assert fd.stat().st_ino==row['inode']and os.readlink(fd)==row['path']and 'WRITE '+str(h['pid'])in(q/'fdinfo'/str(row['fd'])).read_text()
s=gpu_snapshot();assert not s['compute']and all(s['gpu'][i]['free_mib']>=23000 for i in range(8));validate_leased_UUIDs(lease,s['gpu'])
for address,port in [('192.0.2.11',19202),('127.0.0.1',18342)]:
 with socket.socket()as sock:sock.bind((address,port))
assert all(f.with_suffix('.claimed').exists()for f in(LEASE.parent/'commands').glob('*.json'))
stat=os.statvfs(p);assert stat.f_bavail*stat.f_frsize>64*1024**3
command=LEASE.parent/'commands'/(''' + repr(HERE.name + '.json') + r''')
v={'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',str(p/'launch_group.py')],'script_sha256':sha(p/'launch_group.py')}
with command.open('x')as f:json.dump(v,f,indent=2);f.flush();os.fsync(f.fileno())
print(json.dumps({'command':str(command),'command_sha256':sha(command),'original_holder':a,'original_locks':len(lease['lock_records']),'GPU':s,'authorization':m['current_user_authorization_sha256'],'time':time.time(),'new_study_only':True}))
'''
    raw, op = remote('3090', code, 'submit-new-injection-first-study-once')
    value = json.loads(raw); save(HERE / 'service-submission.json', {'operation': str(op), 'result': value})
    print(json.dumps({'original_holder': value['original_holder'], 'command': value['command'], 'new_study_only': True}))


def inspect():
    m = manifest()
    for host in ['3090', '4090']:
        code = 'PACKAGE=' + repr(m['package' + host]) + '\nOUTPUT=' + repr(m['output3090']) + '\nHOST=' + repr(host) + '\n' + r'''
import json,os,time
from pathlib import Path
p=Path(PACKAGE);out=Path(OUTPUT);paths=['launcher-process.json','primary/process.json','primary/status.json','exit.json','launcher-failure.json']if HOST=='3090'else['batch/status.json','control/process.json','control/runner-process.json','control/exit.json']
records={}
for name in paths:
 q=(out if HOST=='3090'else p)/name
 if q.exists():records[name]=json.loads(q.read_bytes())
if HOST=='3090':
 for name in ['flash/service/process.json','flash/service/ready.json','flash/service/loaded.json','flash/service/terminal.json']:
  if(p/name).exists():records[name]=json.loads((p/name).read_bytes())
actual=[]
for name,row in list(records.items()):
 if not isinstance(row,dict)or not all(k in row for k in ['pid','uid','command','start_ticks']):continue
 proc=Path('/proc',str(row['pid']));v=None
 if proc.exists():
  stat=(proc/'stat').read_text().rsplit(')',1)[1].split();v={'pid':row['pid'],'uid':proc.stat().st_uid,'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':stat[19],'state':stat[0]}
 actual.append({'record':name,'current':v,'same':v is not None and all(v.get(k)==row.get(k)for k in ['uid','command','start_ticks'])})
logs={}
for q in ([out/'Flash-service.log',out/'primary.log']if HOST=='3090'else[p/'control/runner.log',p/'background/outer.log']):
 if q.exists():logs[str(q)]=q.read_text(errors='replace')[-1800:]
print(json.dumps({'time':time.time(),'host':HOST,'records':records,'actual':actual,'logs':logs}))
'''
        raw, op = remote(host, code, 'inspect-new-injection-first-' + host)
        value = json.loads(raw); save(HERE / ('inspection-' + host + '-' + str(time.time_ns()) + '.json'), {'operation': str(op), 'result': value})
        records = value['records']
        print(json.dumps({'host': host, 'status': records.get('primary/status.json', records.get('batch/status.json')),
                          'actual': value['actual'], 'failure': records.get('launcher-failure.json'),
                          'logs': value['logs']}))


def gui():
    assert (HERE / 'service-submission.json').exists() and not (HERE / 'GUI-submission.json').exists()
    m = manifest()
    code = 'ROOT=' + repr(m['package4090']) + '\nEXPECTED=' + repr(sha(PACKAGE / 'manifest.json')) + '\n' + r'''
import fcntl,json,os,subprocess,sys,time,requests
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import sha
from continuation_guard import verify_gui_parent
assert sha(p/'manifest.json')==EXPECTED
proof=verify_gui_parent(p)
assert not(p/'control').exists()and not(p/'batch').exists()and not(p/'background').exists()
with(p.parent/'.full-gui-site29980.lock').open('a')as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
token=(p/'private.token').read_text().strip()
r=requests.get('http://192.0.2.11:19202/health',headers={'Authorization':'Bearer '+token},timeout=20);r.raise_for_status();h=r.json()
assert h['phase']=='ready'and h['actor_attempts']==h['actor_replies']==h['done']==0 and h['expected']==12 and h['manifest_sha256']==EXPECTED
(p/'background').mkdir()
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(p/'gui_outer.py')]
with(p/'background/outer.log').open('xb')as log:
 child=subprocess.Popen(argv,env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=str(p),start_new_session=True)
with(p/'background/launch.json').open('x')as f:json.dump({'pid':child.pid,'argv':argv,'time':time.time(),'pre_GUI_health':h,'new_queue':True,'proof':proof},f,indent=2)
print(json.dumps({'pid':child.pid,'argv':argv,'expected_trajectories':12,'injection_before_gate':True,'no_new_primary_preread':True}))
'''
    raw, op = remote('4090', code, 'launch-new-injection-first-GUI-only')
    save(HERE / 'GUI-submission.json', {'operation': str(op), 'result': json.loads(raw)}); print(raw)


if __name__ == '__main__':
    {'stage': stage, 'submit': submit, 'inspect': inspect, 'gui': gui}[sys.argv[1]]()
