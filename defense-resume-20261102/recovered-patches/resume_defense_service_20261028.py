"""Resume the exact paused inference release in a NEW root with owned GPU leases.

Never restarts old experiment queues or overwrites the paused service. Once-only
remote receipt survives process exit. Five-card DEVELOPMENT placement is separate
from the original seven-card reference; no bitwise/output/cost equivalence claimed.
"""
import json
import time
from pathlib import Path
from remote import remote

HERE=Path(__file__).resolve().parent
OLD=json.loads((HERE/'v10-service-launch.json').read_bytes())
PAUSE=json.loads((HERE/'defense-user-pause-current.json').read_bytes())
CODE=r'''
import fcntl,hashlib,json,os,socket,subprocess,time
from pathlib import Path
assert os.getuid()==1033
base=Path('/home/researcher/mirage-defense-pilot-20261023')
startup=(base/'defense-resume-start.lock').open('a')
fcntl.flock(startup,fcntl.LOCK_EX|fcntl.LOCK_NB)
marker=base/'defense-resume-active-20261028.json'
assert not marker.exists(),'Once-only resume receipt exists; inspect, never relaunch.'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
pres=Path(PAUSE['preservation_root']);manifest=pres/'preservation-sha256.json'
assert digest(manifest)==PAUSE['preservation_manifest_sha256']
for n,h in json.loads(manifest.read_bytes()).items():assert digest(pres/n)==h,n
release=Path(OLD['release']);assert str(release)==str(base/'releases/de550b92fd0f6fa6')
assert digest(release/'inference_server.py')=='fdf9a5839123f291a9f7bb30ad7e48bb23f4b05e1967a6e4edb1ba8aa422e4bc'
assert digest(release/'defense/qwen_backend.py')=='11b6cd7a45a31c614b385909b3f43cc1484168fc6c2d2b0796face8495d359eb'
gate=base/'shadow-preflight-1792761125821027588/status.json'
g=json.loads(gate.read_bytes());assert g['phase']=='completed'and g['completed_cases']==20 and g['failed_cases']==0
sock=socket.socket();sock.settimeout(1);occupied=sock.connect_ex(('127.0.0.1',18127))==0;sock.close();assert not occupied
assert OLD['gpus']==[0,1,2,3,4,6,7]
gpus=[0,1,2,3,4]  # GPU6/7: foreign short-lived compute probes; GPU5 never owned.
locks=[]
for gpu in gpus:
 p=Path('/home/researcher/crossmodel-injection-attention-20261025')/('qwen27-gpu%d.lock'%gpu)
 fd=os.open(str(p),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
 assert os.fstat(fd).st_uid==1033
 fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(fd)
snap=[]
for gpu in gpus:
 q=subprocess.run(['nvidia-smi','--id='+str(gpu),'--query-compute-apps=pid','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15)
 m=subprocess.run(['nvidia-smi','--id='+str(gpu),'--query-gpu=memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15)
 assert q.returncode==m.returncode==0 and not q.stdout.strip() and m.stdout.strip().isdigit(),(gpu,q.stdout,m.stdout)
 assert int(m.stdout.strip())>23500,(gpu,m.stdout)
 snap.append({'gpu':gpu,'free_mib':int(m.stdout.strip()),'compute_processes':[]})
root=base/('inference-service-user-resumed-'+str(time.time_ns()));root.mkdir()
source_sha={str(p.relative_to(release)):digest(p)for p in release.rglob('*')if p.is_file()and p.suffix in {'.py','.json'}}
(root/'unchanged-release-sha256.json').write_text(json.dumps(source_sha,indent=2))
record={'phase':'reserved_before_spawn','root':str(root),'release':str(release),'previous':OLD['root'],'time':time.time(),'uid':1033,'gpus':gpus,'placement':'balanced','gpu_snapshot':snap,'source_unchanged':True,'original_pause_manifest':PAUSE['preservation_manifest_sha256'],'user_authorization':'2026-10-28: continue defense and advance quickly','old_queues_resumed':False,'linked_prelaunch_guard_attempt':PRIOR}
record.update(formal_trial=False,deployment_condition_change={'previous_gpus':OLD['gpus'],'development_gpus':gpus,'reason':'Avoid foreign GPU6/7 compute probes','unchanged':'original release/model/BF16/SDPA/native input and generation budgets','bitwise_equivalence_claim':False,'formal_cost_or_efficacy_comparison_allowed':False})
with marker.open('x')as f:json.dump(record,f,indent=2)
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=','.join(map(str,gpus)),PYTHONPATH=str(base/'repair-deps-v2')+':'+str(release),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
command=['/opt/whz/conda-envs/webmall-vlm/bin/python','-u',str(release/'inference_server.py'),'--root',str(root),'--token-file',str(base/'transport.token'),'--gate-shadow',str(gate),'--placement','balanced']
with(root/'worker.log').open('xb')as log:
 child=subprocess.Popen(command,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=tuple(locks))
record.update(phase='spawned_verify_readiness',pid=child.pid,command=command)
(root/'launch.json').write_text(json.dumps(record,indent=2))
tmp=marker.with_suffix('.tmp');tmp.write_text(json.dumps(record,indent=2));tmp.replace(marker)
print(json.dumps(record))
'''

if __name__=='__main__':
    prior=sorted(HERE.glob('defense-resume-preparation-preservation-*'))
    record=json.loads(remote('OLD='+repr(OLD)+'\nPAUSE='+repr(PAUSE)+'\nPRIOR='+repr(str(prior[-1])if prior else None)+'\n'+CODE,host='3090',timeout=150))
    p=HERE/('defense-service-resume-'+str(time.time_ns())+'.json')
    p.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    (HERE/'defense-service-resume-current.json').write_text(json.dumps({'receipt':str(p),**record},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record))
