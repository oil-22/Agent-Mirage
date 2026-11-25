"""Own native browser/site lease until the new full GUI experiment exits."""
import fcntl,json,os,subprocess,sys,time,traceback,urllib.request
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
 lease=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock').open('a');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
 from continuation_guard import verify_gui_parent
 save(control/'parent-admission.json',verify_gui_parent(P))
 from native_environment import NATIVE_ENV
 argv=['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-B','-u',str(P/'gui_experiment.py')]
 child=None;code=1
 try:
  with(control/'runner.log').open('xb')as log:
   child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,**NATIVE_ENV,'PYTHONDONTWRITEBYTECODE':'1'},start_new_session=True)
   save(control/'runner-process.json',identity(child.pid));code=child.wait()
 finally:
  batch_status=json.loads((P/'batch/status.json').read_bytes()) if (P/'batch/status.json').exists() else {}
  if batch_status.get('phase')!='completed':
   try:
    req=urllib.request.Request(m['main_url']+'/abort',data=b'{"reason":"paired_GUI_controller_stopped"}',headers={'Authorization':'Bearer '+(P/'private.token').read_text().strip(),'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=20)as response:save(control/'model-abort-response.json',json.load(response))
   except Exception:save(control/'model-abort-unavailable.json',{'error':traceback.format_exc()})
  save(control/'exit.json',{'child_exit':None if child is None else code,'time':time.time(),'no_automatic_retry':True})
  if(P/'batch').exists():save(control/'batch-terminal-seal.json',{str(p.relative_to(P/'batch')):sha(p)for p in(P/'batch').rglob('*')if p.is_file()})
  save(control/'postexit-seal.json',{p.name:sha(p)for p in control.iterdir()if p.is_file()})
 return code
if __name__=='__main__':raise SystemExit(main())
