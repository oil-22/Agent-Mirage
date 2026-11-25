import json
from control import remote,R3090,HERE,save
code=r'''
import hashlib,json,os,time
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
import torch
p=Path(ROOT);root=p/'flash';config=json.loads((root/'service-config.json').read_bytes());contract=json.loads((root/'gate-contract.json').read_bytes());keys=list(contract['options']);temperature=json.loads((Path(config['model_dir'])/'decision_config.json').read_bytes())['temperature']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for d in sorted((root/'service/requests').iterdir()):
 if not(d/'seal.json').exists():continue
 if(d/'failure.json').exists():continue
 seal=json.loads((d/'seal.json').read_bytes());assert all(sha(d/n)==h for n,h in seal.items())
 trace=json.loads((d/'forward-trace.json').read_bytes());assert len(trace)==1 and trace[0]['past_key_values']is None and trace[0]['use_cache']is False
 actual=torch.load(d/'actual-forward-inputs.pt',map_location='cpu',weights_only=True)
 for k,v in actual.items():
  v=v.contiguous();record=trace[0][k];assert list(v.shape)==record['shape']and str(v.dtype)==record['dtype']and hashlib.sha256(v.view(torch.uint8).numpy().tobytes()).hexdigest()==record['sha256']
 raw=json.loads((d/'raw-readout.json').read_bytes());head=torch.tensor(raw[0]['values'],dtype=getattr(torch,raw[0]['dtype'].split('.')[-1]));assert hashlib.sha256(head.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()==raw[0]['sha256']
 probabilities=(head[0,:2].float()/float(temperature)).softmax(-1).tolist();native=json.loads((d/'native-result.json').read_bytes())['answers']['usable'];response=json.loads((d/'response.json').read_bytes());wire=json.loads((d/'wire-request.bin').read_bytes());request=json.loads((d/'native-request.json').read_bytes())
 assert set(wire)=={'request_id','image_png_base64','image_sha256'}
 assert request['state']==contract['state']and request['questions']=={'usable':{'type':'choice','instructions':contract['question'],'criteria':contract['options']}}and len(request['images'])==1
 assert all(abs(native['probabilities'][k]-probabilities[i])<2e-6 for i,k in enumerate(keys))and response['decision']==native['choice']==max(native['probabilities'],key=native['probabilities'].__getitem__)
 rows.append({'request_id':d.name,'decision':response['decision'],'image_sha256':response['image_sha256'],'actual_forward_tensor_bytes_verified':True,'full_raw_head_probability_binding_verified':True,'input_tokens':trace[0]['input_ids']['shape'][1],'seal_sha256':sha(d/'seal.json')})
assert rows and not torch.cuda.is_initialized()
out={'time':time.time(),'new_inference_by_audit':0,'GPU_allocations_by_audit':0,'verified_complete_Flash_replies':len(rows),'requests':rows,'all_complete_at_read_time_only':True}
target=p/('Flash-runtime-CPU-audit-'+str(time.time_ns())+'.json')
with target.open('x')as f:json.dump(out,f,indent=2)
print(json.dumps({'audit':str(target),**out}))
'''.replace('ROOT',repr(R3090))
raw,op=remote('3090',code,'CPU-audit-new-live-Flash-only-no-forward');out=json.loads(raw);save(HERE/('Flash-live-audit-'+str(__import__('time').time_ns())+'.json'),{'result':out,'operation':str(op)});print(json.dumps({k:v for k,v in out.items()if k!='requests'}))
