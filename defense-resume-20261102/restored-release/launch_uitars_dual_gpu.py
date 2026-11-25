"""Resource-guarded once-only NEW dual-GPU condition; no old queue is resumed."""
import hashlib
import json
import time
from pathlib import Path
from remote import remote

BASE=Path(__file__).resolve().parent;PREP=BASE/'uitars-verifier-preparation'
stage=json.loads((PREP/'dual-gpu-staging.json').read_bytes())
authorization=json.loads((PREP/'dual-gpu-user-authorization-20261027.json').read_bytes())
assert authorization['authorized'] and authorization['user_reply']=='另设双 GPU 预检，保留完整输入和 BF16，并按双卡计算部署成本'
guard=(BASE/'uitars_dual_resource_guard.py').read_text(encoding='utf-8')
code='STAGE='+repr(stage)+'\n'+guard+'\n'+r'''
import pathlib,json,time,os,fcntl,subprocess,hashlib,pwd
assert os.getuid()==1015
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');root=pathlib.Path(STAGE['root'])
startup=(base/'uitars-dual-gpu-start.lock').open('a');fcntl.flock(startup,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=base/'uitars-dual-gpu-active.json'
if active.exists():
 record=json.loads(active.read_bytes());print(json.dumps({'state':'already_launched_do_not_duplicate','launch':record}));raise SystemExit(0)
assert hashlib.sha256((root/'staged-sha256.json').read_bytes()).hexdigest()==STAGE['staged_manifest_sha256']
for n,h in json.loads((root/'staged-sha256.json').read_bytes()).items():
 assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
locks=[];lease_owners={};lock_paths={3:'/data/researcher/crossmodel-injection-attention-20261025/glm-gpu3.lock',1:str(base/'uitars-dual-gpu1.lock')}
for gpu in [3,1]:
 p=pathlib.Path(lock_paths[gpu]);f=p.open('a');assert p.stat().st_uid==1015
 try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  print(json.dumps({'state':'waiting_resources','time':time.time(),'reason':'taskGPUlock held','gpu':gpu,'model_calls':0}));raise SystemExit(0)
 locks.append(f);lease_owners[gpu]=p.stat().st_uid
def snapshot():
 gpus={};processes=[]
 for gpu in [3,1]:
  mem=subprocess.run(['nvidia-smi','--id='+str(gpu),'--query-gpu=memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15)
  apps=subprocess.run(['nvidia-smi','--id='+str(gpu),'--query-compute-apps=pid','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15)
  ok=mem.returncode==0 and apps.returncode==0 and mem.stdout.strip().isdigit()
  gpus[gpu]={'free_mib':int(mem.stdout.strip())if mem.stdout.strip().isdigit()else None,'query_ok':ok}
  if apps.returncode==0:
   for s in apps.stdout.splitlines():
    if not s.strip():continue
    assert s.strip().isdigit(),'Unrecognized process query; never infer free GPU'
    p=pathlib.Path('/proc')/s.strip()
    try:row={'pid':int(s),'physical_gpu':gpu,'uid':p.stat().st_uid,'owner':pwd.getpwuid(p.stat().st_uid).pw_name,'full_command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()}
    except OSError:row={'pid':int(s),'physical_gpu':gpu,'uid':None,'owner':'unresolved_exiting_process'}
    processes.append(row)
 return {'time':time.time(),'gpus':gpus,'processes':processes,'lease_owners':lease_owners}
s=snapshot();reasons=resource_reasons(s['gpus'],s['processes'],lease_owners)
if reasons:
 print(json.dumps({'state':'waiting_resources','time':time.time(),'reasons':reasons,'resource_snapshot':s,'model_calls':0,'gpu_allocations':0}));raise SystemExit(0)
assert not(root/'launch.json').exists()and not(root/'status.json').exists()
record=dict(STAGE);record.update(lease_started_at=time.time(),inference_started=True,resource_snapshot=s,
 locks=lock_paths,uid=1015,condition='independent_dual_gpu_bf16_full_input',cost_device_count=2)
command=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-u',str(root/'release/uitars_dual_gpu_preflight.py'),'--root',str(root)]
env=dict(os.environ,CUDA_VISIBLE_DEVICES='3,1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONPATH=str(root/'deps')+':'+str(root/'release'),MIRAGE_GPU_LOCK_FDS=','.join(str(f.fileno())for f in locks),PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
(root/'launch.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
s2=snapshot();assert not resource_reasons(s2['gpus'],s2['processes'],lease_owners),'Resource state changed before launch'
log=root/'worker.log'
with log.open('xb')as f:p=subprocess.Popen(command,cwd=root/'release',env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=tuple(x.fileno()for x in locks))
proc=pathlib.Path('/proc')/str(p.pid);assert proc.stat().st_uid==1015
record.update(pid=p.pid,command=command,log=str(log));(root/'launch.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
with active.open('x')as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'state':'launched','launch':record}))
'''
result=json.loads(remote(code,host='4090',timeout=60))
snapshot=PREP/('dual-gpu-resource-check-'+str(time.time_ns())+'.json');snapshot.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(PREP/'dual-gpu-resource-current.json').write_text(json.dumps({'snapshot':str(snapshot),'sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),**result},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if 'launch'in result:
 receipt=PREP/'dual-gpu-launch.json'
 if not receipt.exists():receipt.write_text(json.dumps(result['launch'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'state':result['state'],'snapshot':str(snapshot),'reasons':result.get('reasons'),'launch_root':result.get('launch',{}).get('root'),'model_calls':result.get('model_calls')}))
