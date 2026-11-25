"""Read-only postexit preservation of the rejected head scheduling attempt."""
import json,time
from control import HERE,R3090,OUT,remote,save
code='PACKAGE='+repr(R3090)+'\nOUTPUT='+repr(OUT)+'\n'+r'''
import json,sys,time
from pathlib import Path
p=Path(PACKAGE);r=Path(OUTPUT);sys.path.insert(0,str(p/'flash'))
from resource_guard import identity,sha,gpu_snapshot
def load(f):return json.loads(f.read_bytes())
assert (r/'postexit-seal.json').exists()
processes=[]
for f in [r/'launcher-process.json',r/'primary/process.json',p/'flash/service/process.json']:
 old=load(f);q=Path('/proc',str(old['pid']));a=identity(old['pid'])if q.exists()else None
 same=bool(a and all(a[k]==old[k]for k in ['uid','command','start_ticks'])and a['state']not in ['Z','X'])
 assert not same
 processes.append({'record':old,'actual_at_read':a,'same_live_process':same})
seal=load(r/'postexit-seal.json')
for n,h in seal.items():assert sha((p if n.startswith('flash/service/')else r)/n)==h,n
manifest=load(p/'manifest.json')
for n,h in manifest['files'].items():assert sha(p/n)==h,n
terminal=load(r/'primary/terminal.json');assert terminal['attempted_actor_calls']==0 and terminal['done']==0
out={'time':time.time(),'frozen_sources_verified':len(manifest['files']),'manifest_sha256':sha(p/'manifest.json'),'postexit_files_verified':len(seal),'postexit_seal_sha256':sha(r/'postexit-seal.json'),'processes':processes,'exit':load(r/'exit.json'),'terminal':terminal,'failure':load(r/'primary/failure.json'),'failure_memory':load(r/'primary/failure-memory.json'),'source_proof':load(r/'capacity/lifetime-validation/source-proof.json'),'failure_before_full_model_invariance':True,'formal_GUI_calls':0,'new_calls_by_preservation':0,'GPU':gpu_snapshot()}
print(json.dumps(out))
'''
raw,op=remote('3090',code,'preserve-rejected-head-batch-with-postexit-and-source-seals')
result=json.loads(raw);path=HERE/('preservation-'+str(time.time_ns())+'.json');save(path,{'result':result,'operation':str(op)})
print(json.dumps({'preservation':str(path),'postexit_files_verified':result['postexit_files_verified'],'postexit_seal_sha256':result['postexit_seal_sha256'],'formal_GUI_calls':0}))
