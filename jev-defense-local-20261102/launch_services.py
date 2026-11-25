"""Once-only startup; GPU process recheck plus inherited ownership locks."""
import argparse, fcntl, hashlib, json, os, pathlib, secrets, subprocess, time
B=pathlib.Path(__file__).resolve().parent
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2)
def gpu_state():
    def query(args):return subprocess.check_output(['nvidia-smi',*args,'--format=csv,noheader,nounits'],text=True).strip().splitlines()
    g={}
    for line in query(['--query-gpu=index,uuid,memory.free']):
        i,u,m=[x.strip() for x in line.split(',')];g[int(i)]={'uuid':u,'free_mib':int(m)}
    used={line.split(',')[0].strip() for line in query(['--query-compute-apps=gpu_uuid,pid'])}
    return g,used
def main(a):
    assert os.getuid()==1033
    model=a.model;env='env-style' if model=='jev_style' else 'env-neohorse'
    dest=B/'models-verified'/model
    receipt=json.loads((dest/'download-complete-receipt.json').read_bytes())
    for item in receipt['files']:
        p=dest/item['file'];assert p.stat().st_size==item['bytes'],p
        h=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
        assert h.hexdigest()==item['sha256'],p
    run=B/'services'/a.attempt;run.mkdir(parents=True,exist_ok=False)
    lockdir=pathlib.Path('/home/researcher/.mirage-resource-locks');lockdir.mkdir(exist_ok=True)
    g,used=gpu_state();gpu=g[a.gpu]
    assert gpu['uuid'] not in used and gpu['free_mib']>=23000,'GPU unavailable'
    service_lock=(lockdir/('jev-service-'+model+'.lock')).open('a')
    fcntl.flock(service_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    locks=[service_lock]
    for directory in [lockdir,pathlib.Path('/home/researcher/defense-resume-20261102-retry2/resource-locks')]:
        directory.mkdir(exist_ok=True)
        f=(directory/(gpu['uuid']+'.lock')).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    g,used=gpu_state();assert gpu['uuid'] not in used and g[a.gpu]['free_mib']>=23000,'GPU changed while acquiring locks'
    token=B/'transport.token'
    if not token.exists():
        fd=os.open(token,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:f.write(secrets.token_hex(32))
    (run/'serve_local.py').write_bytes((B/'serve_local.py').read_bytes())
    envvars={**os.environ,'CUDA_VISIBLE_DEVICES':str(a.gpu),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','MIRAGE_GPU_LOCK_FDS':','.join(str(x.fileno()) for x in locks),'PYTHONUNBUFFERED':'1'}
    cmd=[str(B/env/'bin/python'),'-u',str(run/'serve_local.py'),'--model',model,'--model-dir',str(dest),'--root',str(run/'runtime'),'--token-file',str(token),'--port',str(a.port)]
    with (run/'service.log').open('xb') as log:
        proc=subprocess.Popen(cmd,env=envvars,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,pass_fds=tuple(x.fileno() for x in locks),start_new_session=True)
    save(run/'launch.json',{'pid':proc.pid,'uid':os.getuid(),'command':cmd,'model':model,'revision':receipt['revision'],'physical_gpu':a.gpu,'gpu':gpu,'time':time.time(),'locks':[{'path':x.name,'inode':os.fstat(x.fileno()).st_ino} for x in locks],'script_sha256':hashlib.sha256((run/'serve_local.py').read_bytes()).hexdigest()})
    print(json.dumps({'run':str(run),'pid':proc.pid,'model':model,'port':a.port}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['jev_style','neohorse'],required=True);p.add_argument('--gpu',type=int,required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--attempt',required=True);main(p.parse_args())
