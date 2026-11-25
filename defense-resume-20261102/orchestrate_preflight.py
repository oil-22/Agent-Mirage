"""Once-only owned four-GPU preflight, automatic resource release at terminal."""
import csv,fcntl,hashlib,json,os,pathlib,secrets,signal,subprocess,sys,time,traceback
B=pathlib.Path(__file__).resolve().parent;PY='/opt/whz/conda-envs/webmall-vlm/bin/python'
def write(p,x):
 with p.open('x')as f:json.dump(x,f,indent=2)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def proc(pid):
 p=pathlib.Path('/proc')/str(pid)
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().decode().replace(chr(0),' '),'start_ticks':(p/'stat').read_text().split()[21]}
def snapshot():
 rows=list(csv.reader(subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True).splitlines()))
 apps=list(csv.reader(subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_memory','--format=csv,noheader,nounits'],text=True).splitlines()))
 return {'gpus':[{'index':int(i),'uuid':u.strip(),'free_mib':int(m)}for i,u,m in rows],'compute':[{'uuid':u.strip(),'used_mib':int(m),**proc(int(pid))}for u,pid,m in apps]}
assert os.getuid()==1033
lock=(B/'startup.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not(B/'launch.json').exists(),'Inspect existing attempt; never duplicate'
manifest=json.loads((B/'package-sha256.json').read_bytes())
for n,h in manifest.items():assert sha(B/n)==h,n
admission=json.loads((B/'admission.json').read_bytes());assert admission['original_122_passed'] and admission['available_supplemental_191_passed'] and admission['full_GUI_authorized_by_this_launch'] is False
assert admission['original_input_packets_exact']==8 and admission['max_new_calls']==23
free=snapshot();selected=[x for x in free['gpus']if x['index']in [1,2,3,4]];assert len(selected)==4
for gpu in selected:
 assert gpu['free_mib']>23500 and not any(x['uuid']==gpu['uuid']for x in free['compute']),gpu
locks=[];locksdir=B/'resource-locks';locksdir.mkdir(exist_ok=True)
for gpu in selected:
 p=locksdir/(gpu['uuid']+'.lock');f=p.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);os.set_inheritable(f.fileno(),True);locks.append(f)
again=snapshot()
for gpu in selected:assert not any(x['uuid']==gpu['uuid']for x in again['compute'])
attempt=B/('remaining-preflight-'+str(time.time_ns()));attempt.mkdir();service=attempt/'service';service.mkdir();run=attempt/'controls';run.mkdir()
for n in ['inputs','images']:__import__('shutil').copytree(B/'restored-inputs'/n,run/n)
for n in ['resume-plan.json','sealed-inputs.json']:__import__('shutil').copy2(B/n,run/n)
token=B/'transport.token'
if not token.exists():token.write_text(secrets.token_hex(32));token.chmod(0o600)
env=dict(os.environ);env.update(CUDA_VISIBLE_DEVICES='1,2,3,4',PYTHONPATH=str(B/'deps')+':'+str(B/'release'),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
sv=None;worker=None;started=time.time()
try:
 with(service/'worker.log').open('xb')as log:
  sv=subprocess.Popen([PY,'-u',str(B/'resume_service.py'),'--root',str(service),'--package',str(B),'--token-file',str(token)],cwd=B/'release',env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,pass_fds=tuple(x.fileno()for x in locks))
 launch={'orchestrator':proc(os.getpid()),'service':proc(sv.pid),'attempt':str(attempt),'physical_gpus':[1,2,3,4],'resource_before':free,'resource_after_locks':again,'inherited_lock_fds':[x.fileno()for x in locks],'original24_cap_prior1_new_max23':True,'GUI_launch':False,'attention_launch':False}
 write(B/'launch.json',launch)
 for _ in range(240):
  if sv.poll()is not None:raise RuntimeError('Service exited during restore/load; inspect preserved log')
  p=service/'status.json'
  if p.exists() and json.loads(p.read_bytes()).get('phase')=='ready':break
  time.sleep(5)
 else:raise RuntimeError('Service load readiness deadline; no model request submitted')
 with(run/'worker.log').open('xb')as log:
  worker=subprocess.Popen([PY,'-u',str(B/'run_remaining_preflight.py'),'--root',str(run),'--url','http://127.0.0.1:18127','--token-file',str(token)],cwd=B/'release',env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
 write(attempt/'worker-launch.json',proc(worker.pid));code=worker.wait();write(attempt/'worker-exit.json',{'exit_code':code,'time':time.time()})
except BaseException:
 write(attempt/'orchestrator-failure.json',{'traceback':traceback.format_exc(),'worker_started':worker is not None});traceback.print_exc()
finally:
 if sv is not None and sv.poll()is None:
  assert pathlib.Path('/proc'/pathlib.Path(str(sv.pid))).stat().st_uid==os.getuid()
  sv.send_signal(signal.SIGUSR1)
  # SIGUSR1 is observed only after the active generation ends; no destructive timeout.
  sv.wait()
 end=time.time();write(attempt/'reservation.json',{'reserved_gpus':4,'reservation_seconds':end-started,'gpu_reserved_seconds':4*(end-started),'currency':None,'energy':None})
 write(attempt/'postexit-sha256.json',{str(p.relative_to(attempt)):sha(p)for p in attempt.rglob('*')if p.is_file()and p.name!='postexit-sha256.json'})
 print(json.dumps({'attempt':str(attempt),'terminal':True}),flush=True)
