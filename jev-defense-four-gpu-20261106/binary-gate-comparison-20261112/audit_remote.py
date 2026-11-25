"""Independent postexit CPU audit; no model loading or inference."""
import hashlib,json,math,os,sys,time
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
import torch
R=Path('/home/researcher/jev-defense-four-gpu-20261106/binary-gate-comparison-20261112')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def save(p,v):
 with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
terminal=json.loads((R/'terminal.json').read_bytes())
assert terminal['status']=='completed' and terminal['complete_replies']==54 and terminal['attempted_calls']==54
protocol=json.loads((R/'protocol.json').read_bytes())
outroot=R/('independent-audit-'+str(time.time_ns()));outroot.mkdir()
all_results=[]
for name in protocol['model_order']:
 root=R/'results'/name;post=json.loads((R/(name+'-postexit-seal.json')).read_bytes())
 assert post['exit_code']==0
 assert all(sha(root/n)==h for n,h in post['files'].items())
 assert sha(R/(name+'-worker.log'))==post['log_sha256']
 previous='0'*64;n=0;kinds={}
 for raw in (root/'events.jsonl').read_bytes().splitlines():
  v=json.loads(raw);s=v.pop('sha256');assert v['seq']==n and v['previous']==previous and hashlib.sha256(canon(v)).hexdigest()==s
  previous=s;n+=1;kinds[v['kind']]=kinds.get(v['kind'],0)+1
 t=json.loads((root/'terminal.json').read_bytes());assert t['journal_head']==previous and t['journal_events']==n
 config=protocol['models'][name];rows=[]
 if name=='neohorse':
  sys.path.insert(0,str(Path(config['model_dir'])/'package/src'))
  from neohorse_decision._vendor.schema import SystemOneRequest,to_record
 for case in protocol['cases']:
  d=root/'requests'/case['id'];seal=json.loads((d/'seal.json').read_bytes());assert all(sha(d/k)==h for k,h in seal.items())
  req=json.loads((d/'request.json').read_bytes());resp=json.loads((d/'response.json').read_bytes());nat=json.loads((d/'native-result.json').read_bytes());native_req=json.loads((d/'native-request.json').read_bytes())
  assert req['image_sha256']==resp['image_sha256']==case['sha256']==sha(R/'inputs'/case['file'])
  assert req['state']==protocol['state'] and req['question']==protocol['question'] and req['options']==protocol['options']
  assert req['empty_context'] and req['single_complete_image'] and resp['new_context'] and resp['output_tokens']==0
  trace=json.loads((d/'forward-trace.json').read_bytes());assert len(trace)==1 and trace[0]['cache_present'] is False and trace[0]['use_cache'] is not True
  actual=torch.load(d/'actual-forward-inputs.pt',map_location='cpu',weights_only=True)
  for key,value in actual.items():
   v=value.contiguous();record=trace[0][key];assert list(v.shape)==record['shape'] and str(v.dtype)==record['dtype']
   assert hashlib.sha256(v.view(torch.uint8).numpy().tobytes()).hexdigest()==record['sha256']
   if 'values' in record:assert v.tolist()==record['values']
  assert actual['input_ids'].shape[0]==1 and actual['image_grid_thw'].shape[0]==1
  assert actual['pixel_values'].numel()>0 and resp['input_tokens']==actual['input_ids'].shape[1]
  raw=json.loads((d/'raw-readout.json').read_bytes())
  if name=='flash':
   temp=json.loads((Path(config['model_dir'])/'decision_config.json').read_bytes())['temperature'];logits=raw[0]['values'][0][:2];keys=list(protocol['options'])
   p=(torch.tensor(logits,dtype=torch.float32)/float(temp)).softmax(-1).tolist()
   probs=nat['answers']['usable']['probabilities'];answer=nat['answers']['usable']['choice']
  elif name=='neohorse':
   _,meta=to_record(SystemOneRequest(**native_req));keys=meta[0]['keys'];logits=raw[0]['values'];p=torch.tensor(logits,dtype=torch.float32).softmax(-1).tolist()
   probs=nat['answers']['evidence']['probabilities'];answer=nat['answers']['evidence']['choice']
  else:
   keys=list(raw['scores']);logits=[raw['scores'][k]/raw['temperature'] for k in keys];m=max(logits);vals=[math.exp(v-m) for v in logits];p=[v/sum(vals) for v in vals]
   probs=nat['probabilities'];answer=nat['answer']
  assert set(keys)=={'YES','NO'}
  assert all(abs(float(probs[k])-float(p[i]))<2e-6 for i,k in enumerate(keys))
  assert probs==resp['probabilities'] and answer==resp['answer'] and answer==max(probs,key=probs.__getitem__)
  for n1 in ['admission-before.json','admission-after.json']:
   adm=json.loads((d/n1).read_bytes());uuid=adm['gpu']['4']['uuid'];pids=[r['identity']['pid'] for r in adm['compute'] if r['uuid']==uuid]
   proc=json.loads((root/'process.json').read_bytes());assert pids==[proc['pid']] and proc['uid']==1033 and proc['visible_devices']=='4'
  rows.append({'case_id':case['id'],'image_sha256':case['sha256'],'answer':answer,'probabilities':probs,'input_tokens':resp['input_tokens'],'grid':resp['image_grid_thw'],'seal_sha256':sha(d/'seal.json'),'actual_runtime_tensor_bytes_verified':True,'raw_score_probability_binding_verified':True})
 result={'model':name,'complete_replies':len(rows),'all_postexit_files_verified':len(post['files']),'journal_events':n,'journal_head':previous,'kinds':kinds,'requests':rows}
 save(outroot/(name+'.json'),result);all_results.append(result)
assert not torch.cuda.is_initialized()
summary={'status':'passed','models':[{k:v for k,v in r.items() if k!='requests'} for r in all_results],'verified_replies':54,'input_tensors_cpu_reloaded':54,'raw_scores_verified':54,'new_model_calls':0,'GPU_allocations':0,'path':str(outroot),'time':time.time()}
save(outroot/'audit.json',summary);save(outroot/'seal.json',{p.name:sha(p) for p in outroot.iterdir() if p.is_file()})
print(json.dumps(summary))
