"""Once-only new full GUI launch, owns site lease and final immutable seals."""
from source_decision_gate import require_finalized
require_finalized(__file__)
import argparse,fcntl,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
from native_environment import NATIVE_ENV

HERE=Path(__file__).resolve().parent
PYTHON='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def identity(pid):
    p=Path('/proc',str(pid));tail=(p/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19]}

def main(a):
    assert os.getuid()==1015 and sha(HERE/'manifest.json')==a.manifest_sha256
    m=json.loads((HERE/'manifest.json').read_bytes())
    for n,h in m['files'].items():assert sha(HERE/n)==h,n
    assert json.loads((HERE/'environment-preflight/receipt.json').read_bytes())['status']=='passed'
    assert json.loads((HERE/'admission.json').read_bytes())['admit_new_GUI_development'] is True
    control=HERE/'control';control.mkdir(exist_ok=False)
    lock=(HERE.parent/'.full-gui-site29980.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    token=HERE/'private.token';assert token.stat().st_mode&0o077==0
    import requests
    before=requests.get(m['model_url'],headers={'Authorization':'Bearer '+token.read_text().strip()},timeout=20);before.raise_for_status()
    health=before.json();assert health['phase']=='ready_gui' and health['manifest_sha256']==a.manifest_sha256 and health['actual_prior_model_attempts']==0
    save(HERE/'readiness.json',health)
    save(control/'process.json',identity(os.getpid()))
    argv=[PYTHON,'-B','-u',str(HERE/'run_independent_gui.py'),'--root',m['GUI_output'],'--plan',str(HERE/'plan.json'),
        '--token-file',str(token),'--runtime','/data/researcher/jev-defense-validation-20261103/runtime-stage-01',
        '--native-bindings',str(HERE/'native-bindings-public.json'),
        '--actor-template',str(HERE/'actor-template.json'),'--auxiliary-config',str(HERE/'auxiliary-config.json'),
        '--readiness',str(HERE/'readiness.json'),'--model-url',m['model_url']]
    save(control/'once-only-launch.json',{'argv':argv,'manifest_sha256':a.manifest_sha256,'no_retry':True,'time':time.time()})
    started=time.time();child=None;failure=None
    try:
        with (control/'runner.log').open('xb') as log:
            child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env={**os.environ,**NATIVE_ENV,'PYTHONDONTWRITEBYTECODE':'1'},cwd=str(HERE),start_new_session=True)
            save(control/'runner-process.json',identity(child.pid));code=child.wait()
        batch=Path(m['GUI_output']);state=json.loads((batch/'status.json').read_bytes()) if (batch/'status.json').exists() else None
        if code or state is None or state['phase']!='completed':failure={'runner_exit':code,'batch_status':state}
    except BaseException:failure={'traceback':traceback.format_exc()}
    finally:
        save(control/'exit.json',{'child_exit':None if child is None else child.returncode,'failure':failure,'started':started,'ended':time.time(),'automatic_retry':False})
        # All browser/auth/private originals stay remote; terminal manifest binds every file.
        batch=Path(m['GUI_output'])
        if batch.exists():save(control/'batch-terminal-manifest.json',{p.relative_to(batch).as_posix():sha(p) for p in sorted(batch.rglob('*')) if p.is_file()})
        save(control/'seal.json',{p.relative_to(control).as_posix():sha(p) for p in control.rglob('*') if p.is_file()})
    return 1 if failure else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest-sha256',required=True);raise SystemExit(main(p.parse_args()))
