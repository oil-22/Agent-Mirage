"""CPU metadata-only contiguous GPU placement planning; no model load."""
import json,time
from control import HERE,OUT,remote,save
code='ROOT='+repr(OUT)+'\n'+r'''
import hashlib,json,re,time
from pathlib import Path
r=Path(ROOT)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sealed=json.loads((r/'postexit-seal.json').read_bytes());assert sha(r/'primary/actual-state.json')==sealed['primary/actual-state.json']
rows=json.loads((r/'primary/actual-state.json').read_bytes());layers=[0]*64;base0=0;base6=0;group={};loaded={}
for v in rows:
 name=v['name'];loaded[v['device']]=loaded.get(v['device'],0)+v['bytes'];match=re.match(r'model\.language_model\.layers\.(\d+)\.',name)
 if match:layers[int(match[1])]+=v['bytes']
 elif name.startswith('model.visual.'):base0+=v['bytes'];group['model.visual']=0
 elif name.startswith('model.language_model.embed_tokens.'):base0+=v['bytes'];group['model.language_model.embed_tokens']=0
 elif name.startswith('model.language_model.norm.'):base6+=v['bytes'];group['model.language_model.norm']=6
 elif name.startswith('lm_head.'):base6+=v['bytes'];group['lm_head']=6
 else:raise ValueError(name)
assert all(layers)and len(rows)==1184
# Include a conservative estimate for each full-attention layer's 53167-token KV cache.
kv=[0 if i%4!=3 else 53167*2*4*256*2 for i in range(64)]
prefix=[0];pweights=[0]
for w,k in zip(layers,kv):prefix.append(prefix[-1]+w+k);pweights.append(pweights[-1]+w)
dp={(0,0):(0,[])}
for device in range(1,7):
 for end in range(device,65):
  candidates=[]
  for start in range(device-1,end):
   if(device-1,start)not in dp:continue
   old,path=dp[device-1,start];score=prefix[end]-prefix[start]+(base6 if device==6 else 0)
   candidates.append((max(old,score),path+[(start,end)]))
  if candidates:dp[device,end]=min(candidates,key=lambda x:x[0])
objective,parts=dp[6,64];placement=dict(group);budgets={0:base0};estimated={0:base0}
for device,(start,end)in enumerate(parts,1):
 for layer in range(start,end):placement['model.language_model.layers.'+str(layer)]=device
 budgets[device]=pweights[end]-pweights[start]+(base6 if device==6 else 0)
 estimated[device]=prefix[end]-prefix[start]+(base6 if device==6 else 0)
out={'time':time.time(),'source_actual_state_sha256':sha(r/'primary/actual-state.json'),'source_postexit_seal_sha256':sha(r/'postexit-seal.json'),'source_tensor_count':len(rows),'source_total_weight_bytes':sum(v['bytes']for v in rows),'old_auto_placed_tensor_bytes':loaded,'device_map':placement,'weight_bytes_by_device':budgets,'layer_ranges_inclusive':{str(d):[a,b-1]for d,(a,b)in enumerate(parts,1)},'estimated_weights_plus_53167_token_full_attention_KV_bytes':estimated,'KV_estimate_not_runtime_fit_proof':True,'optimizer':'contiguous full decoder blocks; minimize max(weight bytes + estimated full-attention KV); visual+embedding on0, norm+lm_head on6','GPU_or_weights_loaded_by_planner':False,'new_model_GUI_calls':0}
print(json.dumps(out))
'''
raw,op=remote('3090',code,'CPU-explicit-layer-placement-source-bound');result=json.loads(raw);path=HERE/('explicit-placement-'+str(time.time_ns())+'.json');save(path,{'result':result,'operation':str(op)})
print(json.dumps({'receipt':str(path),**{k:v for k,v in result.items()if k!='device_map'}}))
