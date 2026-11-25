"""New primary+Flash attempt, inherited owned locks, no old queue entrypoint."""
import json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'flash'))
from resource_guard import identity,locks,sha
def save(p,v):
 with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def main():
 assert os.environ['CUDA_VISIBLE_DEVICES']=='4,5,6,7';_,fds=locks()
 manifest=json.loads((P/'manifest.json').read_bytes())
 for n,h in manifest['files'].items():assert sha(P/n)==h,n
 out=Path(manifest['output3090']);out.mkdir(exist_ok=False);save(out/'launcher-process.json',identity(os.getpid()));children=[]
 try:
  env=dict(os.environ);env.update({'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'})
  flashargv=[json.loads((P/'flash/service-config.json').read_bytes())['python'],'-B','-u',str(P/'flash/flash_service.py'),str(P/'flash')]
  with(out/'Flash-service.log').open('xb')as log:
   flash=subprocess.Popen(flashargv,env={**env,'CUDA_VISIBLE_DEVICES':'7'},stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,pass_fds=fds);children.append(flash);save(out/'Flash-launch.json',{'identity':identity(flash.pid),'argv':flashargv})
  # Confirm actual service ownership and ready receipt before any main load.
  deadline=time.monotonic()+300
  while not(P/'flash/service/ready.json').exists():
   if flash.poll()is not None:raise RuntimeError('New Flash attempt exited during load')
   if time.monotonic()>deadline:raise TimeoutError('Flash readiness timeout, no model retry')
   time.sleep(0.5)
  record=json.loads((P/'flash/service/process.json').read_bytes());actual=identity(record['pid']);assert all(actual[k]==record[k]for k in ['uid','command','start_ticks'])
  argv=['/opt/whz/conda-envs/webmall-vlm/bin/python','-B','-u',str(P/'primary_server.py'),str(out/'primary')]
  with(out/'primary.log').open('xb')as log:
   primary=subprocess.Popen(argv,env={**env,'CUDA_VISIBLE_DEVICES':'4,5,6'},stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,pass_fds=fds);children.append(primary);save(out/'primary-launch.json',{'identity':identity(primary.pid),'argv':argv})
  code=primary.wait();save(out/'primary-exit.json',{'exit_code':code,'time':time.time()})
 finally:
  for child in reversed(children):
   if child.poll()is None:
    # These are exact Popen handles to this new task's own children.
    child.terminate()
    try:child.wait(timeout=300)
    except subprocess.TimeoutExpired:save(out/('child-'+str(child.pid)+'-shutdown-pending.json'),{'pid':child.pid,'no_forced_kill':True});raise
  save(out/'postexit-seal.json',{str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}|{str(p.relative_to(P)):sha(p)for p in(P/'flash/service').rglob('*')if p.is_file()and p.name!='token'})
  save(out/'exit.json',{'time':time.time(),'children':[{'pid':c.pid,'exit_code':c.returncode}for c in children]})
 return code
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception:traceback.print_exc();raise
