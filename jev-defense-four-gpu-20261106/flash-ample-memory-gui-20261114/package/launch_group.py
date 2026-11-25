"""Once-only seven-primary/one-Flash launcher, with original plus expanded locks."""
import fcntl,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'flash'))
from resource_guard import locks,identity,sha,gpu_snapshot

def save(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())

def main():
    old,oldfds=locks();manifest=json.loads((P/'manifest.json').read_bytes())
    assert manifest['ample_memory_authorized']and os.getuid()==1033
    for n,h in manifest['files'].items():assert sha(P/n)==h,n
    out=Path(manifest['output3090']);out.mkdir(exist_ok=False);me=identity(os.getpid());save(out/'launcher-process.json',me)
    children=[];handles=[];extra=[];code=1;failure=None
    try:
        before=gpu_snapshot();assert not before['compute']and all(before['gpu'][i]['free_mib']>=23000 for i in range(8))
        save(out/'resource-before-expansion.json',before)
        for i in range(4):
            for parent in [Path('/home/researcher/.mirage-resource-locks'),Path('/home/researcher/defense-resume-20261102-retry2/resource-locks')]:
                f=(parent/(before['gpu'][i]['uuid']+'.lock')).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);extra.append(f)
        again=gpu_snapshot();assert not again['compute']and all(again['gpu'][i]['free_mib']>=23000 for i in range(8))
        for i in range(8):assert again['gpu'][i]['uuid']==before['gpu'][i]['uuid']
        lease={'holder':me,'original_lease':os.environ['MIRAGE_TASK_LEASE'],'original_lease_sha256':sha(Path(os.environ['MIRAGE_TASK_LEASE'])),'original_lock_holder':old['holder'],'original_lock_count':len(oldfds),'extra_lock_records':[{'path':f.name,'fd':f.fileno(),'inode':os.fstat(f.fileno()).st_ino}for f in extra],'gpu':[{'index':i,**again['gpu'][i]}for i in range(8)],'authorization':manifest['user_memory_authorization'],'created':time.time(),'main_gpus':list(range(7)),'Flash_gpu':7}
        leasefile=out/'expanded-lease.json';save(leasefile,lease)
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false'}
        config=json.loads((P/'flash/service-config.json').read_bytes())
        flashargv=[config['python'],'-B','-u',str(P/'flash/flash_service.py'),str(P/'flash')]
        log=(out/'Flash-service.log').open('xb');handles.append(log)
        flash=subprocess.Popen(flashargv,env={**env,'CUDA_VISIBLE_DEVICES':'7'},stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=oldfds);children.append(flash)
        save(out/'Flash-launch.json',{'identity':identity(flash.pid),'argv':flashargv})
        deadline=time.monotonic()+300
        while not(P/'flash/service/ready.json').exists():
            if flash.poll()is not None:raise RuntimeError('Flash load failed; no automatic retry')
            if time.monotonic()>deadline:raise TimeoutError('Flash readiness timeout')
            time.sleep(0.5)
        allfds=oldfds+tuple(f.fileno()for f in extra)
        env.update({'CUDA_VISIBLE_DEVICES':'0,1,2,3,4,5,6','MIRAGE_EXTRA_GPU_LOCK_FDS':','.join(str(f.fileno())for f in extra),'MIRAGE_EXPANDED_LEASE':str(leasefile),'MIRAGE_EXPANDED_LEASE_SHA256':sha(leasefile)})
        argv=['/opt/whz/conda-envs/webmall-vlm/bin/python','-B','-u',str(P/'primary_server.py'),str(out/'primary')]
        log=(out/'primary.log').open('xb');handles.append(log)
        primary=subprocess.Popen(argv,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=allfds);children.append(primary)
        save(out/'primary-launch.json',{'identity':identity(primary.pid),'argv':argv,'held_inherited_lock_fds':list(allfds)})
        code=primary.wait();save(out/'primary-exit.json',{'exit_code':code,'time':time.time()})
    except BaseException:
        failure={'error':traceback.format_exc(),'time':time.time(),'no_automatic_retry':True};save(out/'launcher-failure.json',failure)
    finally:
        for child in reversed(children):
            if child.poll()is None:
                child.terminate()
                try:child.wait(timeout=300)
                except subprocess.TimeoutExpired:
                    save(out/('child-'+str(child.pid)+'-shutdown-pending.json'),{'pid':child.pid,'no_forced_kill':True});raise
        for h in handles:h.flush();h.close()
        save(out/'exit.json',{'time':time.time(),'exit_code':code,'failure':failure,'children':[{'pid':c.pid,'exit_code':c.returncode}for c in children],'eight_reserved_GPU_cost_must_be_reported':True})
        save(out/'postexit-seal.json',{str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}|{str(p.relative_to(P)):sha(p)for p in(P/'flash/service').rglob('*')if p.is_file()and p.name!='token'})
        for f in extra:f.close()
    return code
if __name__=='__main__':raise SystemExit(main())
