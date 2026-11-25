"""Preserve exited five-GPU service; recover unchanged release once in a NEW root."""
import hashlib,json,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent
OLD=json.loads((BASE/'defense-service-resume-current.json').read_bytes())
CODE=r'''
import fcntl,hashlib,json,os,shutil,socket,subprocess,time
from pathlib import Path
assert os.getuid()==1033
base=Path('/home/researcher/mirage-defense-pilot-20261023')
startup=(base/'defense-recovery-start-20261029.lock').open('a')
fcntl.flock(startup,fcntl.LOCK_EX|fcntl.LOCK_NB)
marker=base/'defense-recovery-active-20261029.json'
assert not marker.exists(),'Existing recovery receipt: inspect, never relaunch'
old=Path(OLD['root']);assert OLD['gpus']==[0,1,2,3,4]
assert not Path('/proc/%d'%OLD['pid']).exists()
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:cmd=(p/'cmdline').read_bytes()
 except (OSError,PermissionError):continue
 assert not (b'inference_server.py' in cmd and b'--root' in cmd),'An inference service exists'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
pres=base/('exited-service-preservation-'+str(time.time_ns()));pres.mkdir()
manifest={}
for p in sorted(old.rglob('*')):
 if not p.is_file():continue
 assert not p.is_symlink()
 name=str(p.relative_to(old));h=digest(p);out=pres/'snapshot'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
 assert digest(out)==h==digest(p),name
 manifest[name]=h
requests=[]
for p in sorted((old/'requests').iterdir()):
 if p.is_dir():requests.append({'name':p.name,'files':sorted(x.name for x in p.iterdir() if x.is_file())})
pending=[x for x in requests if 'response.json'not in x['files']and 'failure.json'not in x['files']]
incident={'old':OLD,'request_count':len(requests),'pending':pending,'log_tail':(old/'worker.log').read_text(errors='replace')[-5000:],'exit_cause':'Unknown: PID absent; log BrokenPipe in request handler does not establish process-exit cause.','source_files':len(manifest),'time':time.time()}
(pres/'incident.json').write_text(json.dumps(incident,indent=2))
(pres/'preservation-sha256.json').write_text(json.dumps(manifest,indent=2))
seal=digest(pres/'preservation-sha256.json')
assert not pending,'Preserved pending requests require explicit diagnosis before recovery'
release=Path(OLD['release'])
assert digest(release/'inference_server.py')=='fdf9a5839123f291a9f7bb30ad7e48bb23f4b05e1967a6e4edb1ba8aa422e4bc'
assert digest(release/'defense/qwen_backend.py')=='11b6cd7a45a31c614b385909b3f43cc1484168fc6c2d2b0796face8495d359eb'
for n,h in json.loads((old/'unchanged-release-sha256.json').read_bytes()).items():assert digest(release/n)==h,n
connections=subprocess.check_output(['ss','-ntap'],text=True)
assert not any(':18127' in line for line in connections.splitlines()),'18127 listener/client exists'
gpus=[0,1,2,3,4];locks=[];snap=[]
for gpu in gpus:
 p=Path('/home/researcher/crossmodel-injection-attention-20261025')/('qwen27-gpu%d.lock'%gpu)
 fd=os.open(str(p),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600);assert os.fstat(fd).st_uid==1033
 fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(fd)
 q=subprocess.check_output(['nvidia-smi','--id='+str(gpu),'--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True)
 m=subprocess.check_output(['nvidia-smi','--id='+str(gpu),'--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True)
 assert not q.strip() and int(m.strip())>23500,(gpu,q,m)
 snap.append({'gpu':gpu,'free_mib':int(m.strip()),'compute_processes':[]})
root=base/('inference-service-recovery-'+str(time.time_ns()));root.mkdir()
shutil.copy2(old/'unchanged-release-sha256.json',root/'unchanged-release-sha256.json')
command=list(OLD['command']);command[command.index('--root')+1]=str(root)
record={'phase':'reserved_before_spawn','root':str(root),'release':str(release),'previous':str(old),'uid':1033,'gpus':gpus,'placement':'balanced','gpu_snapshot':snap,'command':command,'source_unchanged':True,'preservation_root':str(pres),'preservation_manifest_sha256':seal,'preserved_requests':len(requests),'exit_cause':incident['exit_cause'],'user_authorization':'Continue repairing until defense succeeds','old_queues_resumed':False,'formal_trial':False,'condition_change':False}
with marker.open('x')as f:json.dump(record,f,indent=2)
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=','.join(map(str,gpus)),PYTHONPATH=str(base/'repair-deps-v2')+':'+str(release),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
with(root/'worker.log').open('xb')as log:
 child=subprocess.Popen(command,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=tuple(locks))
record.update(phase='spawned_verify_readiness',pid=child.pid,time=time.time())
(root/'launch.json').write_text(json.dumps(record,indent=2));tmp=marker.with_suffix('.tmp');tmp.write_text(json.dumps(record,indent=2));tmp.replace(marker)
print(json.dumps(record))
'''
if __name__=='__main__':
 row=json.loads(remote('OLD='+repr(OLD)+'\n'+CODE,host='3090',timeout=300))
 stamp=str(time.time_ns());out=BASE/('defense-service-recovery-'+stamp+'.json');out.write_text(json.dumps(row,indent=2),encoding='utf-8')
 current=BASE/'defense-service-resume-current.json'
 (BASE/('defense-service-resume-pointer-before-recovery-'+stamp+'.json')).write_bytes(current.read_bytes())
 current.write_text(json.dumps({'receipt':str(out),**row},indent=2),encoding='utf-8')
 print(json.dumps(row))
