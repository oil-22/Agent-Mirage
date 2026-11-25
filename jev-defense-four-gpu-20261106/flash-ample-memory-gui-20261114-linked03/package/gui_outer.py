"""Own native browser/site lease until the new full GUI experiment exits."""
import fcntl,json,os,subprocess,sys,time,traceback
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'flash'))
from resource_guard import identity,sha
def save(p,v):
 with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def main():
 assert os.getuid()==1015
 m=json.loads((P/'manifest.json').read_bytes())
 for n,h in m['files'].items():assert sha(P/n)==h,n
 assert sha(P/'private.token')==m['auth_token_sha256']
 control=P/'control';control.mkdir(exist_ok=False);save(control/'process.json',identity(os.getpid()))
 lease=(P.parent/'.full-gui-site29980.lock').open('a');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
 from native_environment import NATIVE_ENV
 argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(P/'gui_experiment.py')]
 child=None;code=1
 try:
  with(control/'runner.log').open('xb')as log:
   child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,**NATIVE_ENV,'PYTHONDONTWRITEBYTECODE':'1'},start_new_session=True)
   save(control/'runner-process.json',identity(child.pid));code=child.wait()
 finally:
  save(control/'exit.json',{'child_exit':None if child is None else code,'time':time.time(),'no_automatic_retry':True})
  if(P/'batch').exists():save(control/'batch-terminal-seal.json',{str(p.relative_to(P/'batch')):sha(p)for p in(P/'batch').rglob('*')if p.is_file()})
  save(control/'postexit-seal.json',{p.name:sha(p)for p in control.iterdir()if p.is_file()})
 return code
if __name__=='__main__':raise SystemExit(main())
