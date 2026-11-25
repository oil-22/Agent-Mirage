"""Once-only child of the verified original four-card lock holder."""
import json,os,subprocess,sys,time,traceback
from pathlib import Path
PACKAGE=Path('/home/researcher/jev-defense-four-gpu-20261106/flash-binary-gate-framework-20261113')
sys.path.insert(0,str(PACKAGE))
from resource_guard import admit,identity,locks,sha
from flash_runtime import save
def main():
    config=json.loads((PACKAGE/'service-config.json').read_bytes())
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='4,5,6,7':raise RuntimeError('Original lock-holder launcher required')
    _,fds=locks();admit(config,False)
    if (PACKAGE/'service').exists():raise RuntimeError('Existing attempt must be inspected; no restart')
    save(PACKAGE/'launcher-process.json',{**identity(os.getpid()),'inherited_fds':fds,'source_sha256':sha(Path(__file__))})
    env=dict(os.environ);env.update({'CUDA_VISIBLE_DEVICES':str(config['physical_gpu']),'PYTHONUNBUFFERED':'1','PYTHONDONTWRITEBYTECODE':'1'})
    argv=[config['python'],'-B','-u',str(PACKAGE/'flash_service.py'),str(PACKAGE)]
    with (PACKAGE/'service.log').open('xb')as log:
        child=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,pass_fds=fds)
        save(PACKAGE/'service-launch.json',{'pid':child.pid,'argv':argv,'time':time.time(),'physical_gpu':config['physical_gpu']})
        code=child.wait()
    # Post-exit log seal includes any final interpreter output.
    save(PACKAGE/'service-postexit-seal.json',{str(p.relative_to(PACKAGE)):sha(p)for p in (PACKAGE/'service').rglob('*')if p.is_file()and p.name!='token'}|{'service.log':sha(PACKAGE/'service.log')})
    save(PACKAGE/'launcher-exit.json',{'exit_code':code,'time':time.time()})
    return code
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        save(PACKAGE/'launcher-failure.json',{'error':traceback.format_exc(),'no_automatic_retry':True});raise
