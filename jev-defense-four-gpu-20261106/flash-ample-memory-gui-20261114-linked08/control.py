"""Source-bound once-only orchestration for the user's ample-memory continuation."""
import base64,hashlib,io,json,subprocess,sys,time,zipfile
from pathlib import Path
sys.stdout.reconfigure(encoding='utf8');sys.stderr.reconfigure(encoding='utf8')
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
OLD=BASE/'flash-gated-full-gui-20261113'
R3090='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-ample-memory-gui-20261114-linked08'
R4090='/data/researcher/jev-defense-four-gpu-20261106/flash-ample-memory-gui-20261114-linked08'
OUT=R4090
SSH=['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','-o','BatchMode=yes','-o','ConnectTimeout=15']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 with Path(p).open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2)
def remote(host,code,label,timeout=55,private_prefix=''):
 d=HERE/'operations'/(str(time.time_ns())+'-'+label);d.mkdir(parents=True)
 (d/'source.py').write_text(code,encoding='utf8')
 py='/opt/whz/conda-envs/webmall-vlm/bin/python'if host=='3090'else'/data/researcher/venvs/qwen35-9b-full-20261019/bin/python'
 try:
  r=subprocess.run(SSH+[host,py+' -B -'],input=private_prefix+code,text=True,encoding='utf8',capture_output=True,timeout=timeout)
  (d/'stdout.txt').write_text(r.stdout,encoding='utf8');(d/'stderr.txt').write_text(r.stderr,encoding='utf8');save(d/'receipt.json',{'host':host,'returncode':r.returncode,'source_sha256':sha(d/'source.py'),'time':time.time()})
 except BaseException as e:save(d/'failure.json',{'type':type(e).__name__,'message':str(e)});raise
 if r.returncode:raise RuntimeError(str(d)+'\n'+r.stderr[-3500:]+'\n'+r.stdout[-1500:])
 return r.stdout,d

def inspect():
 code=r'''
import fcntl,json,os,socket,subprocess,sys,time
from pathlib import Path
b=Path('/home/researcher/jev-defense-four-gpu-20261106');old=b/'runtime-preparation/flash-gated-full-gui-20261113';sys.path.insert(0,str(old/'flash'))
from resource_guard import identity,sha,LEASE,LEASE_SHA,gpu_snapshot
l=json.loads(LEASE.read_bytes());h=l['holder'];a=identity(h['pid']);assert sha(LEASE)==LEASE_SHA and all(a[k]==h[k]for k in ['uid','command','start_ticks'])
for row in l['lock_records']:
 p=Path('/proc',str(h['pid']));fd=p/'fd'/str(row['fd']);assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and 'WRITE '+str(h['pid'])in(p/'fdinfo'/str(row['fd'])).read_text()
s=gpu_snapshot();assert not s['compute'],'GPU compute changed; inspect ownership, never preempt.'
assert all(s['gpu'][i]['free_mib']>=23000 for i in range(8))
held=[]
for i in range(4):
 for directory in [Path('/home/researcher/.mirage-resource-locks'),Path('/home/researcher/defense-resume-20261102-retry2/resource-locks')]:
  f=(directory/(s['gpu'][i]['uuid']+'.lock')).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(f)
for f in held:f.close()
with socket.socket()as sock:sock.bind(('192.0.2.11',19202))
with socket.socket()as sock:sock.bind(('127.0.0.1',18342))
assert all(f.with_suffix('.claimed').exists()for f in(LEASE.parent/'commands').glob('*.json'))
oldout=Path('/data/researcher/jev-defense-four-gpu-20261106/flash-gated-full-gui-20261113')
proc=[]
for f in [oldout/'launcher-process.json',oldout/'primary/process.json',old/'flash/service/process.json']:
 v=json.loads(f.read_bytes());p=Path('/proc',str(v['pid']));same=False
 if p.exists():
  actual=identity(v['pid']);same=all(actual[k]==v[k]for k in ['uid','command','start_ticks'])and actual['state']not in ['Z','X']
 assert not same,'Prior model still running';proc.append({'record':v,'same_live_process':same})
v=os.statvfs(oldout.parent)
out={'time':time.time(),'UID':os.getuid(),'original_holder':a,'original_held_locks':len(l['lock_records']),'original_lease_sha256':sha(LEASE),'gpu':s,'extra_0_3_locks_available_but_not_leased':True,'prior_model_processes':proc,'available_RAM':next(x for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')),'storage_free_bytes':v.f_bavail*v.f_frsize,'prior_postexit_seal_sha256':sha(oldout/'postexit-seal.json'),'old_failed_request':str(oldout/'primary/requests/00031'),'new_model_calls':0,'new_root_exists':Path(ROOT).exists()}
# Index only original metadata for the longest real delivered prefix; do not load weights or generate.
roots=[b/'remaining28-source-reference-gui-20261110-40',Path('/data/researcher/jev-defense-four-gpu-20261106/remaining28-source-reference-gui-20261110-40')]
prefixes=[]
for root in roots:
 if not root.exists():continue
 for f in root.glob('**/prepared.json'):
  try:
   q=json.loads(f.read_bytes());ids=q.get('input_ids',{});n=ids.get('shape',[0,0])[-1]
   if n:prefixes.append({'prepared':str(f),'input_tokens':n,'files':[x.name for x in f.parent.iterdir()if x.is_file()and x.suffix in ['.json','.bin']]})
  except (ValueError,KeyError,IndexError):pass
out['longest_historical_metadata']=sorted(prefixes,key=lambda x:x['input_tokens'],reverse=True)[:5]
print(json.dumps(out))
'''.replace('ROOT',repr(R3090))
 out,op=remote('3090',code,'fresh-eight-GPU-and-prefix-inspection');value={'result':json.loads(out),'operation':str(op)};p=HERE/('resource-inspection-'+str(time.time_ns())+'.json');save(p,value);print(json.dumps({'receipt':str(p),**value}))
 code=r'''
import fcntl,json,os,subprocess,time
from pathlib import Path
b=Path('/data/researcher/jev-defense-four-gpu-20261106');old=b/'flash-gated-full-gui-20261113'
with(b/'.full-gui-site29980.lock').open('a')as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
for n in ['control/process.json','control/runner-process.json']:
 v=json.loads((old/n).read_bytes());p=Path('/proc',str(v['pid']))
 if p.exists():assert(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()!=v['command']
ids=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
rows=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True));assert all(v['Id']==i and v['Config']['Labels']['owner']=='whz-qwen27-vwa'and v['State']['Running']for v,i in zip(rows,ids))
assert rows[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
assert any(m.get('Name')=='qwen27_vwa_db_data'for m in rows[1]['Mounts'])
v=os.statvfs(b)
print(json.dumps({'time':time.time(),'UID':os.getuid(),'site_owned_running':True,'site_lock_available':True,'no_reset_or_import':True,'storage_free_bytes':v.f_bavail*v.f_frsize,'new_root_exists':Path(ROOT).exists(),'new_model_GUI_calls':0}))
'''.replace('ROOT',repr(R4090))
 out,op=remote('4090',code,'fresh-original-site-inspection');save(HERE/('site-inspection-'+str(time.time_ns())+'.json'),{'result':json.loads(out),'operation':str(op)});print(out)

def stage():
 package=HERE/'package';manifest=json.loads((package/'manifest.json').read_bytes());payload=io.BytesIO()
 with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED)as z:
  for n in list(manifest['files'])+['manifest.json','private.token']:z.writestr(n,(package/n).read_bytes())
 for host,root in [('3090',R3090),('4090',R4090)]:
  assert not(HERE/('stage-'+host+'.json')).exists()
  code='ROOT='+repr(root)+'\nEXPECTED='+repr(sha(package/'manifest.json'))+'\n'+r'''
import ast,base64,hashlib,io,json,os,zipfile
from pathlib import Path
r=Path(ROOT);r.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for n in z.namelist():
  p=r/n;assert p.resolve().is_relative_to(r.resolve());p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb')as f:f.write(z.read(n))
(r/'private.token').chmod(0o600)
assert hashlib.sha256((r/'manifest.json').read_bytes()).hexdigest()==EXPECTED
m=json.loads((r/'manifest.json').read_bytes())
for n,h in m['files'].items():
 assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h
 if n.endswith('.py'):ast.parse((r/n).read_text())
if os.getuid()==1033:
 assert not Path(m['output3090']).exists()
assert len(m['remaining_queue'])==29
print(json.dumps({'root':str(r),'files':len(m['files']),'manifest_sha256':EXPECTED,'new_model_GUI_calls':0}))
'''
  out,op=remote(host,code,'stage-ample-memory-'+host,private_prefix='PAYLOAD='+repr(base64.b64encode(payload.getvalue()).decode())+'\n');save(HERE/('stage-'+host+'.json'),{'result':json.loads(out),'operation':str(op)});print(out)

def service():
 assert all((HERE/('stage-'+h+'.json')).exists()for h in ['3090','4090'])and not(HERE/'service-submission.json').exists()
 code='ROOT='+repr(R3090)+'\nOUTPUT='+repr(OUT)+'\n'+r'''
import json,os,socket,sys,time
from pathlib import Path
p=Path(ROOT);sys.path.insert(0,str(p/'flash'));from resource_guard import LEASE,identity,sha
l=json.loads(LEASE.read_bytes());h=l['holder'];a=identity(h['pid']);assert all(a[k]==h[k]for k in ['uid','command','start_ticks'])
for row in l['lock_records']:
 q=Path('/proc',str(h['pid']));assert os.readlink(q/'fd'/str(row['fd']))==row['path']and 'WRITE '+str(h['pid'])in(q/'fdinfo'/str(row['fd'])).read_text()
assert not Path(OUTPUT).exists();assert all(f.with_suffix('.claimed').exists()for f in(LEASE.parent/'commands').glob('*.json'))
with socket.socket()as s:s.bind(('192.0.2.11',19202))
c=LEASE.parent/'commands/flash-ample-memory-gui-20261114-linked08.json';v={'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',str(p/'launch_group.py')],'script_sha256':sha(p/'launch_group.py')}
with c.open('x')as f:json.dump(v,f,indent=2)
print(json.dumps({'command':str(c),'command_sha256':sha(c),'time':time.time(),'once_only':True,'extra_GPU_locks_must_be_acquired_by_new_launcher':True}))
'''
 out,op=remote('3090',code,'submit-ample-memory-group-once');save(HERE/'service-submission.json',{'result':json.loads(out),'operation':str(op)});print(out)

def activity():
 for host,root in [('3090',OUT),('4090',R4090)]:
  code='ROOT='+repr(root)+'\nPACKAGE='+repr(R3090)+'\n'+r'''
import json
from pathlib import Path
r=Path(ROOT);v={}
for n in ['launcher-process.json','expanded-lease.json','primary/status.json','primary/loaded.json','primary/ready.json','primary/terminal.json','launcher-failure.json','capacity/terminal.json','capacity-failure.json','exit.json','batch/status.json','GUI-uncaught-failure.json','control/exit.json']:
 f=r/n
 if f.exists():
  q=json.loads(f.read_bytes())
  if n=='primary/loaded.json':q={k:q[k]for k in ['physical_gpus','dtype','attention','load_seconds','memory','CUDA']}
  if n=='expanded-lease.json':q={'holder':q['holder'],'original_lock_count':q['original_lock_count'],'extra_lock_count':len(q['extra_lock_records']),'main_gpus':q['main_gpus'],'Flash_gpu':q['Flash_gpu']}
  if n=='capacity/terminal.json':q={**q,'probes':[{k:v for k,v in probe.items()if k!='memory'}for probe in q['probes']]}
  v[n]=q
for n in ['primary.log','Flash-service.log','control/runner.log']:
 if(r/n).exists():v[n]=(r/n).read_text()[-2200:]
print(json.dumps(v))
'''
  out,op=remote(host,code,'actual-ample-activity-'+host);print(json.dumps({'host':host,'data':json.loads(out),'operation':str(op)}))

def gui():
 assert(HERE/'service-submission.json').exists()and not(HERE/'GUI-submission.json').exists()
 code='ROOT='+repr(R4090)+'\nEXPECTED='+repr(sha(HERE/'package/manifest.json'))+'\n'+r'''
import json,os,subprocess,requests,time
from pathlib import Path
p=Path(ROOT);assert not(p/'control').exists()and not(p/'batch').exists()and not(p/'background').exists()
token=(p/'private.token').read_text().strip()
r=requests.get('http://192.0.2.11:19202/health',headers={'Authorization':'Bearer '+token},timeout=30);r.raise_for_status();h=r.json()
assert h['phase']=='ready'and h['actor_attempts']==0 and h['done']==0 and h['expected']==29 and h['manifest_sha256']==EXPECTED
(p/'background').mkdir()
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(p/'gui_outer.py')]
with(p/'background/outer.log').open('xb')as log:
 child=subprocess.Popen(argv,env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=str(p),start_new_session=True)
with(p/'background/launch.json').open('x')as f:json.dump({'pid':child.pid,'argv':argv,'pre_GUI_health':h,'time':time.time()},f,indent=2)
print(json.dumps({'pid':child.pid,'argv':argv,'expected_trajectories':29,'prior_completed_or_failed_reexecuted':False}))
'''
 out,op=remote('4090',code,'launch-unstarted-29-native-GUI-once');save(HERE/'GUI-submission.json',{'result':json.loads(out),'operation':str(op)});print(out)

if __name__=='__main__':globals()[sys.argv[1]]()
