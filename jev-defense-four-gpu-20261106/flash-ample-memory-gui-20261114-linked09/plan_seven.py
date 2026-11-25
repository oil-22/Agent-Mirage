"""Plan contiguous decoder blocks on all seven main GPUs from sealed metadata."""
import json,time
from control import HERE,BASE,OUT,remote,save
source=(BASE/'flash-ample-memory-gui-20261114-linked05/plan_explicit.py').read_text(encoding='utf8')
start=source.index("code='ROOT='");end=source.index("raw,op=remote")
scope={'OUT':OUT};exec(source[start:end],scope);code=scope['code']
a=code.index('dp={(0,0)}');b=code.index("out={'time':",a)
replacement='''dp={(0,0):(0,[])}
for stage in range(1,8):
 device=stage-1;base=base0 if device==0 else base6 if device==6 else 0
 for end in range(stage,65):
  candidates=[]
  for begin in range(stage-1,end):
   if(stage-1,begin)not in dp:continue
   old,path=dp[stage-1,begin];score=prefix[end]-prefix[begin]+base
   candidates.append((max(old,score),path+[(begin,end)]))
  if candidates:dp[stage,end]=min(candidates,key=lambda x:x[0])
objective,parts=dp[7,64];placement=dict(group);placement['model.language_model.rotary_emb']=0;budgets={};estimated={}
for device,(begin,end)in enumerate(parts):
 for layer in range(begin,end):placement['model.language_model.layers.'+str(layer)]=device
 base=base0 if device==0 else base6 if device==6 else 0
 budgets[device]=pweights[end]-pweights[begin]+base
 estimated[device]=prefix[end]-prefix[begin]+base
'''
code=code[:a]+replacement+code[b:]
code=code.replace("'old_auto_placed_tensor_bytes'","'previous_placed_tensor_bytes'").replace("enumerate(parts,1)","enumerate(parts)").replace("visual+embedding on0, norm+lm_head on6","all seven GPUs carry decoder blocks; visual+embedding on0, norm+lm_head on6")
raw,op=remote('3090',code,'CPU-source-bound-seven-card-contiguous-placement');result=json.loads(raw);path=HERE/('seven-placement-'+str(time.time_ns())+'.json');save(path,{'result':result,'operation':str(op)})
print(json.dumps({'receipt':str(path),**{k:v for k,v in result.items()if k!='device_map'}}))
