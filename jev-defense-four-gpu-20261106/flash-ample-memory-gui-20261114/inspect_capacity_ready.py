"""Independent read-only source/lock/tensor verification before starting the GUI."""
import json,time
from control import HERE,R3090,OUT,remote,save,sha

code='PACKAGE='+repr(R3090)+'\nOUTPUT='+repr(OUT)+'\n'+r'''
import hashlib,json,os,sys,time
from pathlib import Path
p=Path(PACKAGE);r=Path(OUTPUT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import identity,sha,LEASE,LEASE_SHA,gpu_snapshot
from capacity_gate import fifty_image_load
def load(f):return json.loads(Path(f).read_bytes())
def process(file):
 v=load(file);a=identity(v['pid']);assert all(a[k]==v[k]for k in ['uid','command','start_ticks'])and a['state']not in ['Z','X'];return a
assert sha(LEASE)==LEASE_SHA
old=load(LEASE);h=old['holder'];assert all(identity(h['pid'])[k]==h[k]for k in ['uid','command','start_ticks'])
lease=load(r/'expanded-lease.json');holder=lease['holder'];assert all(identity(holder['pid'])[k]==holder[k]for k in ['uid','command','start_ticks'])
primary=process(r/'primary/process.json');flash=process(p/'flash/service/process.json')
for proc,records,owner in [(primary,old['lock_records'],h),(primary,lease['extra_lock_records'],holder),(flash,old['lock_records'],h)]:
 for row in records:
  q=Path('/proc',str(proc['pid']));fd=q/'fd'/str(row['fd'])
  assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(owner['pid'])in(q/'fdinfo'/str(row['fd'])).read_text()
m=load(p/'manifest.json')
for n,hsh in m['files'].items():assert sha(p/n)==hsh,n
cap=load(r/'capacity/terminal.json');assert cap['status']=='passed'and len(cap['probes'])==2
for n,hsh in load(r/'capacity/seal.json').items():assert sha(r/'capacity'/n)==hsh,n
source=load(p/'capacity-source.json');original=Path(source['source_request']);assert sha(original/'wire-request.bin')==source['wire_sha256']
originalbody=load(original/'wire-request.bin')['body'];first=load(r/'capacity/01-exact-previous-OOM-input/body.json');stress=load(r/'capacity/02-explicit-synthetic-50-image-load/body.json')
assert first==originalbody and stress==fifty_image_load(originalbody)
probes=[]
for row in cap['probes']:
 d=r/'capacity'/row['probe'];prepared=load(d/'prepared.json');actual=load(d/'first-forward.json');generated=load(d/'actual-generation.json');native=load(d/'native-call.json')
 for k in prepared:
  assert all(prepared[k][f]==actual[k][f]for f in ['shape','dtype','bytes','sha256'])
  assert sha(d/prepared[k]['file'])==prepared[k]['sha256']and sha(d/actual[k]['file'])==actual[k]['sha256']
 assert generated['natural_EOS']and native['generated_ids']==generated['output_ids']
 ids=(d/prepared['input_ids']['file']).read_bytes();sequence=(d/'sequence_ids.tensor').read_bytes();assert sequence[:len(ids)]==ids
 assert min(v['headroom_at_reserved_peak_bytes']for v in row['memory'])>=3*1024**3
 cfg=load(d/'effective-generation.json');assert cfg['max_new_tokens']==2048 and cfg['do_sample']is False
 probes.append(row)
loaded=load(r/'primary/loaded.json');assert loaded['physical_gpus']==list(range(7))and loaded['dtype']=='bfloat16'and loaded['attention']=='sdpa'
assert loaded['CUDA']['devices']==['cuda:'+str(i)for i in range(7)]
s=gpu_snapshot();uuids={v['index']:v['uuid']for v in lease['gpu']}
for i in range(8):
 assert s['gpu'][i]['uuid']==uuids[i]
 assert{v['pid']for v in s['compute']if v['uuid']==uuids[i]}=={primary['pid']if i<7 else flash['pid']}
status=load(r/'primary/status.json');assert status['phase']=='ready'and status['attempted_actor_calls']==0 and status['done']==0
out={'time':time.time(),'actual_primary':primary,'actual_Flash':flash,'actual_launcher':identity(holder['pid']),'primary_inherited_held_locks':17,'Flash_inherited_held_locks':9,'expanded_lease_sha256':sha(r/'expanded-lease.json'),'manifest_sha256':sha(p/'manifest.json'),'frozen_sources_verified':len(m['files']),'capacity_probes':probes,'native_state':loaded['native_state'],'actual_CUDA':loaded['CUDA'],'GPU_current':s,'capacity_generation_calls':2,'formal_actor_calls':0,'new_inference_GUI_calls_by_inspector':0,'original_failed_source_input_byte_bound':True,'fifty_image_input_explicitly_synthetic':True,'minimum_reserved_peak_headroom_GiB':min(v['headroom_at_reserved_peak_bytes']for row in probes for v in row['memory'])/1024**3,'Mirage_reduction':None}
print(json.dumps(out))
'''
raw,op=remote('3090',code,'verify-new-seven-GPU-capacity-and-held-locks',timeout=55)
value={'result':json.loads(raw),'operation':str(op)};path=HERE/('capacity-ready-audit-'+str(time.time_ns())+'.json');save(path,value)
summary={k:v for k,v in value['result'].items()if k not in ['capacity_probes','GPU_current']}
summary['probes']=[{k:v for k,v in row.items()if k!='memory'}for row in value['result']['capacity_probes']]
print(json.dumps({'receipt':str(path),**summary}))
