"""Collect immutable inference receipts and verify the actual sent full inputs; no model calls."""
import base64,hashlib,json,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'source-evidence-preview-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
launches=[json.loads((PREP/n).read_bytes())for n in ['launch.json','controls-launch.json','routing-launch.json']]
requests={};responses={};calls=[];chains=[]
for launch in launches:
 folder=Path(launch['local_root'])/'collected';summary=json.loads((folder/'summary.json').read_bytes());assert summary['phase']=='completed'
 calls.extend(summary['calls']);head='0'*64
 for line in(folder/'journal/events.jsonl').read_text(encoding='utf-8').splitlines():
  e=json.loads(line);got=e.pop('sha256');assert e['previous']==head and sha(canon(e))==got;head=got
  if e['kind'] in {'development_actor_request','development_preview_request'}:pending=e
  if e['kind'] in {'development_actor_response','development_preview_response'}:
   d=e['data'];assert d['case']==pending['data']['case'];assert len(d['calls'])==1
   rec=d['calls'][0]['receipt'];requests[rec]=pending;responses[rec]=e
 chains.append({'root':launch['root'],'event_chain_head':head,'summary_sha256':sha((folder/'summary.json').read_bytes())})
assert len(calls)==len(requests)==31 and len(set(c['receipt']for c in calls))==31
code='RECEIPTS='+repr(list(requests))+'\n'+r'''
import pathlib,json,base64,hashlib
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023/inference-service-v10-1792914231469085180/requests')
out={}
for name in RECEIPTS:
 p=pathlib.Path(name);assert p.parent==base and p.name.isdigit()
 assert p.stat().st_uid==1033
 files={}
 for f in p.iterdir():
  if f.is_file():files[f.name]={'base64':base64.b64encode(f.read_bytes()).decode(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
 assert {'request.json','generation.json','response.json'}<=files.keys()and'failure.json'not in files
 out[name]=files
print(json.dumps(out))
'''
raw=json.loads(remote(code,host='3090',timeout=120));outdir=PREP/('service-receipts-'+str(time.time_ns()));outdir.mkdir();records=[]
for rec,files in raw.items():
 folder=outdir/Path(rec).name;folder.mkdir()
 for name,d in files.items():
  b=base64.b64decode(d['base64']);assert sha(b)==d['sha256'];(folder/name).write_bytes(b)
 request=json.loads((folder/'request.json').read_bytes());generation=json.loads((folder/'generation.json').read_bytes());response=json.loads((folder/'response.json').read_bytes())
 event=requests[rec];reply=responses[rec];d=event['data']
 if event['kind']=='development_actor_request':
  assert request=={'operation':'actor','body':d['body']}
  assert response['text']==reply['data']['candidate']==generation['text']
  assert generation['request_messages_sha256']==sha(canon(d['body']['messages']))
  assert generation['verifier_grammar']is None and generation['generation_config']['max_new_tokens']==2048
 else:
  assert request['operation']=='judge'and request['candidate']is None and request['system']==d['system']
  v=request['view'];projected={k:val for k,val in v.items()if k!='images'};projected['images']=[]
  for image in v['images']:
   b=base64.b64decode(image['raw_base64']);original=next(i for i in d['public']['images']if i['sha256']==sha(b));assert image['role']==original['role'];projected['images'].append(original)
  assert canon(projected)==canon(d['public'])
  assert response['verdict']==reply['data']['raw']==generation['text']
  assert generation['verifier_grammar']and generation['generation_config']['max_new_tokens']==4096
 eos=generation['generation_config']['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
 assert not generation['hit_output_cap']and generation['generated_ids'][-1]in eos
 assert len(generation['input_ids'])==response['input_tokens']and len(generation['generated_ids'])==response['output_tokens']
 records.append({'receipt':rec,'case':d['case'],'arm':d.get('arm','preview'),'operation':request['operation'],'request_sha256':files['request.json']['sha256'],'generation_sha256':files['generation.json']['sha256'],'response_sha256':files['response.json']['sha256'],'input_tokens':response['input_tokens'],'output_tokens':response['output_tokens'],'seconds':response['seconds'],'natural_eos':True,'actual_sent_input_matches_journal':True})
result={'roots':chains,'verified_distinct_requests':len(records),'input_tokens':sum(x['input_tokens']for x in records),'output_tokens':sum(x['output_tokens']for x in records),'summed_model_seconds':sum(x['seconds']for x in records),'new_gui_actions':0,'official_evaluations':0,'paid_api_calls':0,'directory':str(outdir),'records':records,'cost_scope':'Summed model generation seconds/tokens only, excluding service loading, shared GPU occupancy, development and review; not wall time, money or energy.'}
(outdir/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(outdir/'sha256.json').write_text(json.dumps({str(p.relative_to(outdir)):sha(p.read_bytes())for p in outdir.rglob('*')if p.is_file()},indent=2),encoding='utf-8')
(PREP/'service-audit-current.json').write_text(json.dumps({'directory':str(outdir),'audit_sha256':sha((outdir/'audit.json').read_bytes()),'manifest_sha256':sha((outdir/'sha256.json').read_bytes())},indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items()if k not in {'records','roots'}},ensure_ascii=False))
