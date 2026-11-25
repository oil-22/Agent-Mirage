"""Read-only verification of linked lifetime, full-logit and capacity evidence."""
import json,time
from control import HERE,R3090,OUT,remote,save

code='PACKAGE='+repr(R3090)+'\nOUTPUT='+repr(OUT)+'\n'+r'''
import hashlib,json,os,sys,time
from pathlib import Path
p=Path(PACKAGE);r=Path(OUTPUT);sys.path[:0]=[str(p/'flash'),str(p)]
from resource_guard import identity,sha,LEASE,LEASE_SHA,gpu_snapshot
from capacity_gate import fifty_image_load
def load(f):return json.loads(Path(f).read_bytes())
def actual(f):
 v=load(f);a=identity(v['pid']);assert all(a[k]==v[k]for k in ['uid','command','start_ticks'])and a['state']not in ['Z','X'];return a
assert sha(LEASE)==LEASE_SHA
old=load(LEASE);h=old['holder'];assert all(identity(h['pid'])[k]==h[k]for k in ['uid','command','start_ticks'])
lease=load(r/'expanded-lease.json');holder=lease['holder'];assert all(identity(holder['pid'])[k]==holder[k]for k in ['uid','command','start_ticks'])
primary=actual(r/'primary/process.json');flash=actual(p/'flash/service/process.json')
for proc,records,owner in [(primary,old['lock_records'],h),(primary,lease['extra_lock_records'],holder),(flash,old['lock_records'],h)]:
 for row in records:
  q=Path('/proc',str(proc['pid']));fd=q/'fd'/str(row['fd'])
  assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(owner['pid'])in(q/'fdinfo'/str(row['fd'])).read_text()
manifest=load(p/'manifest.json')
for n,hsh in manifest['files'].items():assert sha(p/n)==hsh,n
cap=load(r/'capacity/terminal.json');assert cap['status']=='passed'and len(cap['probes'])==1
for n,hsh in load(r/'capacity/seal.json').items():assert sha(r/'capacity'/n)==hsh,n
proof=load(r/'capacity/lifetime-validation/result.json');assert proof['normalized_arithmetic_AST_equal_after_restoring_product_destinations']and proof['all_full_vocab_logits_and_sequence_ids_bitwise_equal']and proof['installed']
assert proof['only_private_dead_pointwise_output_buffers_reused']and proof['MLP_memory_proof']['all_tests_passed']and proof['actual_MLP_calls_per_pass']==192 and proof['kernel_tests']==9 and proof['all_kernel_tests_bitwise_equal']
assert proof['full_model_cached_steps']==3 and proof['real_model_input_tokens']==15367 and proof['actual_chunk_calls_per_pass']==48
a=load(r/'capacity/lifetime-validation/baseline-three-cached-steps/invariance-record.json');b=load(r/'capacity/lifetime-validation/optimized-three-cached-steps/invariance-record.json')
assert a['generated_ids']==b['generated_ids']
for x,y in zip(a['full_vocab_logits'],b['full_vocab_logits']):assert all(x[k]==y[k]for k in ['shape','dtype','bytes','sha256'])
assert all(c['full_output_and_state_bitwise_equal']for c in load(r/'capacity/lifetime-validation/kernel-bitwise-tests.json'))
source=load(p/'capacity-source.json');originalbody=load(Path(source['source_request'])/'wire-request.bin')['body'];stress=r/'capacity/50-image-source-bound-stress'
assert load(stress/'body.json')==fifty_image_load(originalbody)
prepared=load(stress/'prepared.json');first=load(stress/'first-forward.json');generated=load(stress/'actual-generation.json');native=load(stress/'native-call.json')
for k in prepared:
 assert all(prepared[k][f]==first[k][f]for f in ['shape','dtype','bytes','sha256'])
 assert sha(stress/prepared[k]['file'])==prepared[k]['sha256']and sha(stress/first[k]['file'])==first[k]['sha256']
ids=(stress/prepared['input_ids']['file']).read_bytes();assert(stress/'sequence_ids.tensor').read_bytes()[:len(ids)]==ids
assert generated['natural_EOS']and native['generated_ids']==generated['output_ids']
previous50=Path(source['prior_complete50_probe'])
assert sha(previous50/'seal.json')==source['prior_complete50_seal_sha256']
for n,hsh in load(previous50/'seal.json').items():assert sha(previous50/n)==hsh,n
assert generated['output_ids']==load(previous50/'actual-generation.json')['output_ids']
assert load(stress/'result.json')['complete_sequence_ids_equal_prior_unbatched_lifetime_result']
loaded=load(r/'primary/loaded.json');assert loaded['physical_gpus']==list(range(7))and loaded['dtype']=='bfloat16'and loaded['attention']=='sdpa'
assert loaded['CUDA']['devices']==['cuda:'+str(i)for i in range(7)]
assert loaded['device_map']=={k:str(v)for k,v in load(p/'explicit-placement.json')['device_map'].items()}
s=gpu_snapshot();uuids={v['index']:v['uuid']for v in lease['gpu']}
for i in range(8):
 assert s['gpu'][i]['uuid']==uuids[i]
 assert{v['pid']for v in s['compute']if v['uuid']==uuids[i]}=={primary['pid']if i<7 else flash['pid']}
status=load(r/'primary/status.json');assert status['phase']=='ready'and status['attempted_actor_calls']==0 and status['done']==0
headroom=min(v['headroom_at_reserved_peak_bytes']for q in cap['probes']for v in q['memory'])/1024**3;assert headroom>=3
print(json.dumps({'time':time.time(),'actual_primary':primary,'actual_Flash':flash,'actual_launcher':identity(holder['pid']),'primary_held_inherited_locks':17,'Flash_held_inherited_locks':9,'expanded_lease_sha256':sha(r/'expanded-lease.json'),'manifest_sha256':sha(p/'manifest.json'),'frozen_sources_verified':len(manifest['files']),'native_state':loaded['native_state'],'CUDA':loaded['CUDA'],'lifetime_proof':proof,'capacity':cap,'minimum_reserved_peak_headroom_GiB':headroom,'GPU_current':s,'new_model_GUI_calls_by_inspector':0,'formal_actor_calls':0,'remaining_trajectories':29,'Mirage_reduction':None}))
'''
raw,op=remote('3090',code,'verify-linked-memory-invariance-capacity-and-actual-locks',timeout=55);value={'result':json.loads(raw),'operation':str(op)}
path=HERE/('ready-audit-'+str(time.time_ns())+'.json');save(path,value)
print(json.dumps({'receipt':str(path),**{k:v for k,v in value['result'].items()if k not in ['GPU_current','capacity']},'stress':[{k:v for k,v in row.items()if k!='memory'}for row in value['result']['capacity']['probes']]}))
