import copy,hashlib,json,pathlib,sys
import numpy as np,torch
from transformers import AutoConfig,AutoProcessor
from run_attention import convert,group_prompt
torch.set_num_threads(6)
root=pathlib.Path('/home/researcher/attention-20261102/source-campaign');raw=json.loads((root/'raw.json').read_text());models={'qwen27':'/opt/whz/llms/Qwen3.8-27B','qwen9':'/home/researcher/models/Qwen3.5-9B','glm':'/home/researcher/models/GLM-4.6V-Flash-411bb4d77144'}
processors={m:AutoProcessor.from_pretrained(p,local_files_only=True) for m,p in models.items()};chosen={};failed=[]
def replace(request,old,new):
 req=copy.deepcopy(request);msg=[m for m in req['messages'] if m['role']=='assistant'][1];assert isinstance(msg['content'],str) and msg['content'].count(old)==1;msg['content']=msg['content'].replace(old,new);return req
def templated_ids(processor,request):
 text=processor.apply_chat_template(convert(request['messages'],root/'assets'),tokenize=False,add_generation_prompt=True,enable_thinking=False)
 return processor.tokenizer.encode(text,add_special_tokens=False)
for item in raw:
 key=item['trajectory']
 if key in chosen:continue
 original=item['source_claim'];req=item['request'];base={m:len(templated_ids(pr,req)) for m,pr in processors.items()};selected={};counts={}
 for variant,options in [('source_withdrawn',item['withdrawals']),('meaning_preserving_sham',item['shams'])]:
  for option in options:
   lengths={m:len(templated_ids(pr,replace(req,original,option))) for m,pr in processors.items()};counts[option]=lengths
   if lengths==base:selected[variant]=option;break
  if variant not in selected:failed.append({'trajectory':key,'variant':variant,'original':original,'baseline':base,'candidate_lengths':counts})
 chosen[key]={'original':original,**selected}
root.joinpath('variant-selection.json').write_text(json.dumps({'chosen':chosen,'failed':failed},ensure_ascii=False,indent=2))
if failed:print(json.dumps(failed,ensure_ascii=False));sys.exit(2)
cases=[]
for item in raw:
 for variant,claim in chosen[item['trajectory']].items():
  case={k:v for k,v in item.items() if k not in ['withdrawals','shams']};case['id']=item['id']+'-'+variant;case['condition']=variant;case['source_claim']=claim;case['request']=replace(item['request'],item['source_claim'],claim);cases.append(case)
plan={'selection':'Fourteen distinct preselected VWA tasks with explicit state assertions at their archived missing-current-image source step 2; selected for source manipulability before new outputs. Source captures include supported, contradicted, and visually unresolved assertions; this is not a fourteen-positive Mirage sample. No selection by new attention or action changes.','scope':'Three follow-up snapshots at source gaps 1,3,6 from each shared archived Qwen27 trajectory. Only source state assertion changed, all source actions and later screenshots fixed. Withdrawal expresses uncertainty, not a ground-truth replacement or environment recovery. Same variant wording selected to preserve request token length across all three native tokenizers.','independent_tasks':len(chosen),'max_new_tokens':2048,'source_conditions':['original','source_withdrawn','meaning_preserving_sham'],'cases':cases}
root.joinpath('plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));root.joinpath('plan.sha256').write_text(hashlib.sha256(root.joinpath('plan.json').read_bytes()).hexdigest())
rows=[]
for mid,path in models.items():
 pr=processors[mid];config=AutoConfig.from_pretrained(path,local_files_only=True)
 for case in cases:
  batch=pr.apply_chat_template(convert(case['request']['messages'],root/'assets'),tokenize=True,add_generation_prompt=True,return_dict=True,return_tensors='pt',enable_thinking=False);ids=batch['input_ids'][0].tolist();groups,turns,decoded,offsets=group_prompt(pr.tokenizer,ids,config,case['request']);claim=case['source_claim'];mask=np.zeros(len(ids),bool)
  import re
  for hit in re.finditer(re.escape(claim),decoded):
   for k,(a,b) in enumerate(offsets):
    if a<hit.end() and b>hit.start() and turns[k]==1:mask[k]=True
  assert mask.any()
  rows.append({'model':mid,'id':case['id'],'trajectory':case['trajectory'],'condition':case['condition'],'input_tokens':len(ids),'input_ids_sha256':hashlib.sha256(np.asarray(ids,dtype='<i8').tobytes()).hexdigest(),'groups_sha256':hashlib.sha256(groups.astype('<i8').tobytes()).hexdigest(),'claim_mask_sha256':hashlib.sha256(mask.tobytes()).hexdigest(),'claim_tokens':int(mask.sum()),'status':'passed'})
  tmp=root/'cpu-input-audit.tmp';tmp.write_text(json.dumps(rows,indent=2));tmp.replace(root/'cpu-input-audit.json')
 by={r['id']:r for r in rows if r['model']==mid}
 for item in raw:assert len({by[item['id']+'-'+v]['input_tokens'] for v in chosen[item['trajectory']]})==1
 print(json.dumps({'model':mid,'cpu_preflight_completed':len(by)}),flush=True)
print(json.dumps({'independent_tasks':len(chosen),'cases_per_model':len(cases),'cpu_preflights':len(rows)}))
