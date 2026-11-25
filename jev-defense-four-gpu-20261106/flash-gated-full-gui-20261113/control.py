"""Once-only, source-bound orchestration for the new Flash full GUI experiment."""
import base64,hashlib,io,json,os,subprocess,sys,time,zipfile
from pathlib import Path
sys.stdout.reconfigure(encoding='utf8');sys.stderr.reconfigure(encoding='utf8')
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
R3090='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/flash-gated-full-gui-20261113'
R4090='/data/researcher/jev-defense-four-gpu-20261106/flash-gated-full-gui-20261113'
OUT='/data/researcher/jev-defense-four-gpu-20261106/flash-gated-full-gui-20261113'
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
 if r.returncode:raise RuntimeError(str(d)+'\n'+r.stderr[-4000:]+'\n'+r.stdout[-1000:])
 return r.stdout,d
def inspect():
 code=r'''
import hashlib,json,os,socket,subprocess,sys
from pathlib import Path
b=Path('/home/researcher/jev-defense-four-gpu-20261106');f=b/'flash-binary-gate-framework-20261113';sys.path.insert(0,str(f))
from resource_guard import identity,sha,LEASE,LEASE_SHA
lease=json.loads(LEASE.read_bytes());h=lease['holder'];actual=identity(h['pid']);assert sha(LEASE)==LEASE_SHA and all(actual[k]==h[k]for k in ['uid','command','start_ticks'])
for row in lease['lock_records']:
 p=Path('/proc',str(h['pid']));assert os.readlink(p/'fd'/str(row['fd']))==row['path']and 'WRITE '+str(h['pid'])in(p/'fdinfo'/str(row['fd'])).read_text()
out={'holder':actual,'locks':len(lease['lock_records']),'lease_sha256':sha(LEASE),'new_calls':0}
out['gpu']=subprocess.check_output(['nvidia-smi','--id=4,5,6,7','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
p=json.loads((f/'service/process.json').read_bytes());out['Flash']=identity(p['pid']);assert all(out['Flash'][k]==p[k]for k in ['uid','command','start_ticks']);out['Flash_requests']=len(list((f/'service/requests').iterdir()))
out['ports']={}
for port in [19201]:
 with socket.socket()as s:out['ports'][str(port)]=s.connect_ex(('192.0.2.11',port))==0
out['available_RAM']=next(line for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:'))
out['new_root_exists']=Path(ROOT).exists()
print(json.dumps(out))
'''.replace('ROOT',repr(R3090))
 out,d=remote('3090',code,'fresh-owned-resources');print(json.dumps({'host':'3090','data':json.loads(out),'evidence':str(d)}))
 code=r'''
import fcntl,hashlib,json,os,subprocess
from pathlib import Path
b=Path('/data/researcher/jev-defense-four-gpu-20261106')
with(b/'.full-gui-site29980.lock').open('a')as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
ids=['de6f56798c3c5a278a96d7afe6844e8be2c5673301e44e1c887eecc56118f0dd','e8fe8dfaa8010a5473c1ebf603859ba04d7d4ac1e8016b347ea8211c03a4c62c']
rows=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True));assert all(r['Id']==i and r['Config']['Labels']['owner']=='whz-qwen27-vwa'and r['State']['Running']for r,i in zip(rows,ids))
assert rows[0]['HostConfig']['PortBindings']=={'9980/tcp':[{'HostIp':'192.0.2.10','HostPort':'29980'}]}
assert any(m.get('Name')=='qwen27_vwa_db_data'for m in rows[1]['Mounts'])
runtime=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
assert all((runtime/n).is_dir()for n in ['upstream','native'])
old=b/'remaining28-source-reference-gui-20261110-40';process=json.loads((old/'control/runner-process.json').read_bytes());p=Path('/proc',str(process['pid']))
assert not p.exists()or(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()!=process['command']
v=os.statvfs(b)
print(json.dumps({'uid':os.getuid(),'site_owned_running':True,'site_lock_currently_available':True,'runtime':str(runtime),'runtime_python_exists':(runtime/'env/bin/python').exists(),'new_root_exists':Path(ROOT).exists(),'storage_free':v.f_bavail*v.f_frsize,'site_reset':False,'new_calls':0}))
'''.replace('ROOT',repr(R4090))
 out,d=remote('4090',code,'fresh-native-site');print(json.dumps({'host':'4090','data':json.loads(out),'evidence':str(d)}))
def stage():
 package=HERE/'package-linked02';manifest=json.loads((package/'manifest.json').read_bytes());payload=io.BytesIO()
 with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED)as z:
  for n in list(manifest['files'])+['manifest.json','private.token']:z.writestr(n,(package/n).read_bytes())
 private='PAYLOAD='+repr(base64.b64encode(payload.getvalue()).decode())+'\n'
 for host,root in [('3090',R3090),('4090',R4090)]:
  assert not(HERE/('stage-'+host+'.json')).exists()
  code=r'''
import ast,base64,hashlib,io,json,os,zipfile
from pathlib import Path
r=Path(ROOT);r.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as z:
 for name in z.namelist():
  p=r/name;assert p.resolve().is_relative_to(r.resolve());p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb')as f:f.write(z.read(name))
(r/'private.token').chmod(0o600)
m=json.loads((r/'manifest.json').read_bytes());assert hashlib.sha256((r/'manifest.json').read_bytes()).hexdigest()==EXPECTED
for n,h in m['files'].items():
 p=r/n;assert hashlib.sha256(p.read_bytes()).hexdigest()==h
 if p.suffix=='.py':ast.parse(p.read_text())
if os.getuid()==1033:
 out=Path(m['output3090']);assert not out.exists();v=os.statvfs(out.parent);assert v.f_bavail*v.f_frsize>1024**4
else:
 runtime=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01');assert hashlib.sha256((runtime/'native/run_reddit_internvl_smoke.py').read_bytes()).hexdigest()==m['files']['native-parser-source.py']
print(json.dumps({'root':str(r),'files':len(m['files']),'manifest_sha256':EXPECTED,'new_model_GUI_calls':0}))
'''.replace('ROOT',repr(root)).replace('EXPECTED',repr(sha(package/'manifest.json')))
  out,d=remote(host,code,'stage-new-Flash-GUI-'+host,private_prefix=private);save(HERE/('stage-'+host+'.json'),{'result':json.loads(out),'operation':str(d)});print(out)
def retire_flash():
 assert all((HERE/('stage-'+h+'.json')).exists()for h in ['3090','4090'])
 assert not(HERE/'retire-previous-Flash.json').exists()
 code=r'''
import json,os,shutil,signal,sys,time
from pathlib import Path
p=Path(ROOT);old=Path('/home/researcher/jev-defense-four-gpu-20261106/flash-binary-gate-framework-20261113');sys.path.insert(0,str(old))
from resource_guard import identity,sha
proc=json.loads((old/'service/process.json').read_bytes());a=identity(proc['pid']);assert all(a[k]==proc[k]for k in ['uid','command','start_ticks'])and a['uid']==1033
assert sha(old/'flash_service.py')==proc['script_sha256']
requests=list((old/'service/requests').iterdir());assert len(requests)==4
for d in requests:
 seal=json.loads((d/'seal.json').read_bytes());assert all(sha(d/n)==h for n,h in seal.items())and(d/'response.json').exists()
assert not any(line.split()[3]=='01'and int(line.split()[1].split(':')[1],16)==18341 for line in Path('/proc/net/tcp').read_text().splitlines()[1:]),'Existing service has a connected client'
pres=p/'retired-standalone-Flash-preservation';pres.mkdir()
shutil.copytree(old/'service',pres/'prestop-service',ignore=shutil.ignore_patterns('token'))
shutil.copyfile(old/'service.log',pres/'prestop-service.log')
seal={str(f.relative_to(pres)):sha(f)for f in pres.rglob('*')if f.is_file()}
with(pres/'prestop-seal.json').open('x')as f:json.dump(seal,f,indent=2)
with(pres/'stop-target.json').open('x')as f:json.dump(a,f,indent=2)
assert all(identity(a['pid'])[k]==a[k]for k in ['uid','command','start_ticks']);os.kill(a['pid'],signal.SIGTERM)
deadline=time.monotonic()+40
while not(old/'launcher-exit.json').exists():
 assert time.monotonic()<deadline,'Shutdown pending; inspect, do not force/duplicate'
 time.sleep(0.25)
post=json.loads((old/'service-postexit-seal.json').read_bytes());assert all(sha(old/n)==h for n,h in post.items())
shutil.copyfile(old/'service-postexit-seal.json',pres/'original-postexit-seal.json');shutil.copyfile(old/'service/terminal.json',pres/'original-terminal.json')
print(json.dumps({'stopped_verified_owned_Flash':a,'complete_old_replies_preserved':4,'postexit_files_verified':len(post),'holder_untouched':True,'no_old_model_controls_repeated':True}))
'''.replace('ROOT',repr(R3090))
 out,d=remote('3090',code,'preserve-and-retire-standalone-Flash-for-new-group');save(HERE/'retire-previous-Flash.json',{'result':json.loads(out),'operation':str(d)});print(out)
def service():
 assert(HERE/'retire-previous-Flash.json').exists()and not(HERE/'service-submission.json').exists()
 code=r'''
import json,os,socket,sys,time
from pathlib import Path
p=Path(ROOT);sys.path.insert(0,str(p/'flash'))
from resource_guard import LEASE,identity,sha
l=json.loads(LEASE.read_bytes());h=l['holder'];a=identity(h['pid']);assert all(a[k]==h[k]for k in ['uid','command','start_ticks'])
for row in l['lock_records']:
 proc=Path('/proc',str(h['pid']));assert os.readlink(proc/'fd'/str(row['fd']))==row['path']and'WRITE '+str(h['pid'])in(proc/'fdinfo'/str(row['fd'])).read_text()
assert not Path(OUTPUT).exists()
with socket.socket()as s:s.bind(('192.0.2.11',19201))
assert all(f.with_suffix('.claimed').exists()for f in(LEASE.parent/'commands').glob('*.json'))
command={'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',str(p/'launch_group.py')],'script_sha256':sha(p/'launch_group.py')}
c=LEASE.parent/'commands/flash-gated-full-gui-20261113.json'
with c.open('x')as f:json.dump(command,f,indent=2)
print(json.dumps({'command':str(c),'command_sha256':sha(c),'time':time.time(),'once_only':True}))
'''.replace('ROOT',repr(R3090)).replace('OUTPUT',repr(OUT))
 out,d=remote('3090',code,'submit-new-primary-and-Flash-group');save(HERE/'service-submission.json',{'result':json.loads(out),'operation':str(d)});print(out)
def gui():
 assert(HERE/'service-submission.json').exists()and not(HERE/'GUI-submission.json').exists()
 code=r'''
import json,os,subprocess,requests
from pathlib import Path
p=Path(ROOT);assert not(p/'control').exists()and not(p/'background').exists()and not(p/'batch').exists()
token=(p/'private.token').read_text().strip()
r=requests.get('http://192.0.2.11:19201/health',headers={'Authorization':'Bearer '+token},timeout=30);r.raise_for_status();health=r.json()
assert health['phase']=='ready'and health['actor_attempts']==0 and health['manifest_sha256']==EXPECTED
(p/'background').mkdir()
argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(p/'gui_outer.py')]
with(p/'background/outer.log').open('xb')as log:
 child=subprocess.Popen(argv,env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=str(p),start_new_session=True)
with(p/'background/launch.json').open('x')as f:json.dump({'pid':child.pid,'argv':argv,'health':health},f,indent=2)
print(json.dumps({'pid':child.pid,'argv':argv,'actor_attempts_before_GUI':0,'expected_trajectories':32}))
'''.replace('ROOT',repr(R4090)).replace('EXPECTED',repr(sha(HERE/'package-linked02/manifest.json')))
 out,d=remote('4090',code,'launch-new-native-GUI-once');save(HERE/'GUI-submission.json',{'result':json.loads(out),'operation':str(d)});print(out)
def status_now():
 for host,root in [('3090',OUT),('4090',R4090)]:
  code=r'''
import json,sys
from pathlib import Path
r=Path(ROOT);sys.path.insert(0,FLASH_PATH)
from resource_guard import identity,sha
v={'root_exists':r.exists()}
names=['launcher-process.json','Flash-launch.json','primary-launch.json','primary/process.json','primary/loaded.json','primary/status.json','primary/ready.json','primary/failure.json','primary/terminal.json','primary-exit.json','exit.json','batch/status.json','GUI-uncaught-failure.json','control/process.json','control/runner-process.json','control/exit.json']
for n in names:
 p=r/n
 if p.is_file():
  v[n]=json.loads(p.read_bytes());record=v[n].get('identity',v[n])
  if 'pid'in record:
   try:v[n+' actual']=identity(record['pid'])
   except FileNotFoundError:v[n+' actual']={'pid':record['pid'],'exists':False}
for n in ['primary.log','Flash-service.log','control/runner.log','background/outer.log']:
 if(r/n).exists():v[n]=(r/n).read_text()[-5000:]
if(r/'primary/requests').exists():v['primary_request_count']=len(list((r/'primary/requests').iterdir()))
if(r/'batch').exists():
 v['terminals']=[{'path':str(p),'sha256':sha(p),'value':json.loads(p.read_bytes())}for p in(r/'batch/runs').glob('*/attempt-*/terminal.json')]
 v['current_controller_tail']=[]
 for p in list((r/'batch/runs').glob('*/attempt-*/controller/events.jsonl'))[-1:]:v['current_controller_tail']=[json.loads(s)for s in p.read_text().splitlines()[-4:]]
print(json.dumps(v))
'''.replace('ROOT',repr(root)).replace('FLASH_PATH',repr((R3090 if host=='3090'else R4090)+'/flash'))
  out,d=remote(host,code,'actual-status-'+host);v=json.loads(out)
  save(HERE/('status-'+host+'-'+str(time.time_ns())+'.json'),{'data':v,'operation':str(d)})
  print(json.dumps({'host':host,'data':v,'evidence':str(d)}))
if __name__=='__main__':{'inspect':inspect,'stage':stage,'retire_flash':retire_flash,'service':service,'gui':gui,'status':status_now}[sys.argv[1]]()
