"""Evidence-preserving deployment of the newly authorized Flash-only image gate."""
import base64,hashlib,io,json,os,subprocess,sys,time,zipfile
from pathlib import Path
sys.stdout.reconfigure(encoding='utf8');sys.stderr.reconfigure(encoding='utf8')
HERE=Path(__file__).resolve().parent
REMOTE='/home/researcher/jev-defense-four-gpu-20261106/flash-binary-gate-framework-20261113'
SSH=['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','-o','BatchMode=yes','-o','ConnectTimeout=15']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 with Path(p).open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2)
def remote(code,label,host='3090',timeout=55):
 d=HERE/'operations'/(str(time.time_ns())+'-'+label);d.mkdir(parents=True)
 (d/'source.py').write_text(code,encoding='utf8')
 py='/opt/whz/conda-envs/webmall-vlm/bin/python'if host=='3090'else'/data/researcher/venvs/qwen35-9b-full-20261019/bin/python'
 try:
  r=subprocess.run(SSH+[host,py+' -B -'],input=code,text=True,encoding='utf8',capture_output=True,timeout=timeout)
  (d/'stdout.txt').write_text(r.stdout,encoding='utf8');(d/'stderr.txt').write_text(r.stderr,encoding='utf8')
  save(d/'receipt.json',{'returncode':r.returncode,'host':host,'source_sha256':sha(d/'source.py'),'time':time.time()})
 except BaseException as e:save(d/'failure.json',{'type':type(e).__name__,'message':str(e)});raise
 if r.returncode:raise RuntimeError(str(d)+'\n'+r.stderr[-3000:]+'\n'+r.stdout[-2000:])
 return r.stdout,d
def inspect():
 source=(HERE.parent/'binary-gate-comparison-20261112/inspect_remote.py').read_text(encoding='utf8').replace('print(json.dumps(out,ensure_ascii=False))','')
 source+=r'''
import importlib.util
out['browser_runtime']={n:bool(importlib.util.find_spec(n)) for n in ['playwright','PIL','requests']}
out['proposed_port_busy']=any(int(line.split()[1].split(':')[1],16)==18341 and line.split()[3]=='0A' for line in Path('/proc/net/tcp').read_text().splitlines()[1:])
r=B/'flash-binary-gate-framework-20261113';out['new_root_exists']=r.exists()
if r.exists():
 for n in ['launcher-process.json','service/process.json','service/loaded.json','service/ready.json','service/terminal.json','launcher-exit.json']:
  p=r/n
  if p.is_file():
   v=json.loads(p.read_bytes());out[n]=v
   if n.endswith('process.json'):out[n+' actual']=identity(v['pid'])
print(json.dumps(out))
'''
 out,d=remote(source,'inspect-resource');v=json.loads(out)
 print(json.dumps({'holder':v['holder'],'locks':len(v['verified_locks']),'gpu':v['gpu'],'compute':v['compute'],'browser_runtime':v['browser_runtime'],'port_busy':v['proposed_port_busy'],'root_exists':v['new_root_exists'],'service':v.get('service/ready.json'),'evidence':str(d)}))
def stage():
 files=list(HERE.glob('*.py'))+[HERE/n for n in ['gate-contract.json','service-config.json','user-authorization.json','flash-identity.json','preflight-plan.json']]+list((HERE/'preflight-inputs').glob('*.png'))
 manifest={str(p.relative_to(HERE)).replace('\\','/'):sha(p)for p in files}
 save(HERE/'package-manifest.json',manifest)
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED)as z:
  for p in files+[HERE/'package-manifest.json']:z.writestr(str(p.relative_to(HERE)).replace('\\','/'),p.read_bytes())
 code="""
import ast,base64,hashlib,io,json,zipfile
from pathlib import Path
root=Path(ROOT);root.mkdir(exist_ok=False)
z=zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))
for name in z.namelist():
 p=root/name
 if not p.resolve().is_relative_to(root.resolve()):raise ValueError('Invalid package path')
 p.parent.mkdir(exist_ok=True)
 with p.open('xb')as f:f.write(z.read(name))
manifest=json.loads((root/'package-manifest.json').read_bytes())
for name,h in manifest.items():
 p=root/name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==h
 if p.suffix=='.py':ast.parse(p.read_text())
target=root.parent/'runtime-preparation/launch_flash_binary_gate_20261113.py'
with target.open('xb')as f:f.write((root/'launch_flash_gate.py').read_bytes())
print(json.dumps({'root':str(root),'files':len(manifest),'launcher':str(target),'launcher_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
""".replace('ROOT',repr(REMOTE)).replace('PAYLOAD',repr(base64.b64encode(b.getvalue()).decode()))
 out,d=remote(code,'stage',timeout=55);v=json.loads(out);save(HERE/'staging-receipt.json',{**v,'evidence':str(d),'package_manifest_sha256':sha(HERE/'package-manifest.json')});print(out)
def submit():
 if (HERE/'submission-receipt.json').exists():raise RuntimeError('Already submitted; inspect actual state')
 code="""
import hashlib,json,os,time
from pathlib import Path
root=Path(ROOT)
import sys;sys.path.insert(0,str(root))
from resource_guard import LEASE,LEASE_SHA,identity,sha
assert sha(LEASE)==LEASE_SHA
lease=json.loads(LEASE.read_bytes());old=lease['holder'];a=identity(old['pid'])
assert all(a[k]==old[k]for k in ['uid','command','start_ticks'])and a['state']not in['Z','X']
for row in lease['lock_records']:
 p=Path('/proc',str(old['pid']));assert os.readlink(p/'fd'/str(row['fd']))==row['path'];assert 'WRITE '+str(old['pid'])in(p/'fdinfo'/str(row['fd'])).read_text()
assert not(root/'service').exists()and not(root/'launcher-process.json').exists()
for name,h in json.loads((root/'package-manifest.json').read_bytes()).items():assert sha(root/name)==h
script=root.parent/'runtime-preparation/launch_flash_binary_gate_20261113.py'
assert sha(script)==sha(root/'launch_flash_gate.py')
command={'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',str(script)],'script_sha256':sha(script),'new_user_authorization_sha256':sha(root/'user-authorization.json')}
p=LEASE.parent/'commands/flash-binary-gate-framework-20261113.json'
with p.open('x')as f:json.dump(command,f,indent=2)
print(json.dumps({'command':str(p),'command_sha256':sha(p),'time':time.time()}))
""".replace('ROOT',repr(REMOTE))
 out,d=remote(code,'submit');v=json.loads(out);save(HERE/'submission-receipt.json',{**v,'evidence':str(d)});print(out)
def status():
 code="""
import json,sys,urllib.request
from pathlib import Path
root=Path(ROOT);sys.path.insert(0,str(root))
from resource_guard import identity,gpu_snapshot
out={'gpu':gpu_snapshot()}
for n in ['launcher-process.json','service-launch.json','launcher-exit.json','launcher-failure.json','service/process.json','service/loaded.json','service/ready.json','service/failure.json','service/terminal.json','integration-preflight/terminal.json','integration-preflight/failure.json']:
 p=root/n
 if p.exists():
  out[n]=json.loads(p.read_bytes())
  if 'pid'in out[n]:
   try:out[n+' actual']=identity(out[n]['pid'])
   except FileNotFoundError:out[n+' actual']={'exists':False}
if(root/'service/ready.json').exists():
 try:
  req=urllib.request.Request('http://127.0.0.1:18341/health',headers={'Authorization':'Bearer '+(root/'service/token').read_text().strip()})
  with urllib.request.urlopen(req,timeout=15)as r:out['actual_health']=json.load(r)
 except Exception as e:out['health_error']=str(e)
if(root/'service.log').exists():out['log_tail']=(root/'service.log').read_text()[-6000:]
print(json.dumps(out))
""".replace('ROOT',repr(REMOTE))
 out,d=remote(code,'status');v=json.loads(out)
 print(json.dumps({'actual_health':v.get('actual_health'),'service_process':v.get('service/process.json actual'),'loaded':v.get('service/loaded.json'),'failure':v.get('service/failure.json',v.get('launcher-failure.json')),'log_tail':v.get('log_tail'),'integration':v.get('integration-preflight/terminal.json',v.get('integration-preflight/failure.json')),'evidence':str(d)}))
def preflight():
 code="""
import json,subprocess
from pathlib import Path
root=Path(ROOT)
assert not(root/'integration-preflight').exists(),'Do not repeat a completed or failed integration attempt'
with(root/'integration-preflight.log').open('xb')as log:
 p=subprocess.Popen(['/opt/whz/conda-envs/webmall-vlm/bin/python','-B','-u',str(root/'integration_preflight.py'),str(root)],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
with(root/'integration-launch.json').open('x')as f:json.dump({'pid':p.pid},f)
print(json.dumps({'pid':p.pid}))
""".replace('ROOT',repr(REMOTE))
 out,d=remote(code,'launch-new-four-call-preflight');save(HERE/'preflight-launch-receipt.json',{**json.loads(out),'evidence':str(d)});print(out)
if __name__=='__main__':
 {'inspect':inspect,'stage':stage,'submit':submit,'status':status,'preflight':preflight}[sys.argv[1]]()
