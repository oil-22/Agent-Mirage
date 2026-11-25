"""Seal the original20 development controls across immutable attempts, never launch inference."""
import hashlib,json
from pathlib import Path
from remote import remote
prep=Path(__file__).resolve().parent/'uitars-verifier-preparation'
receipt=prep/'real-preflight-finalization.json';assert not receipt.exists(),'Use existing finalization; do not repeat'
launches=[json.loads((prep/n).read_bytes())for n in ['real-loader-retry-launch.json','real-remaining-controls-launch.json','real-memory-diagnostic-launch.json','real-final-controls-launch.json']]
seals=[json.loads((prep/n).read_bytes())for n in ['real-loader-failure-preservation.json','real-contract-failure-preservation.json','real-long-history-oom-preservation.json','real-memory-diagnostic-preservation.json']]
code=r'''
import pathlib,json,hashlib,time,os,struct
assert os.getuid()==1015
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canon=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
for origin in SEALS:
 seal=pathlib.Path(origin['sealed_manifest']);assert sha(seal)==origin['sealed_manifest_sha256']
 for n,h in json.loads(seal.read_bytes()).items():
  assert sha(pathlib.Path(origin['original_root'])/n)==h
  assert sha(pathlib.Path(origin['preserved_root'])/n)==h
source=pathlib.Path(LAUNCHES[0]['root']);cases=json.loads((source/'public-requests.json').read_bytes());expected={c['id']:c for c in cases};assert len(expected)==20
cpu={c['id']:c for c in json.loads((source/'cpu-result.json').read_bytes())['rows']}
outcomes={};natural_replies=[];ooms=[];roots=[];total_calls=0;runtime_bound=set()
for launch in LAUNCHES:
 r=pathlib.Path(launch['root']);assert not pathlib.Path('/proc',str(launch['pid'])).exists()
 assert launch['dtype']=='BF16'and launch['attention_backend']=='sdpa'and launch['max_output_tokens_per_call']==4096
 assert launch['pinned_revision']=='683d002dd99d8f95104d31e70391a39348857f4e'
 assert sha(r/'public-requests.json')==LAUNCHES[0]['public_requests_sha256']
 manifest=json.loads((r/'final-artifacts-sha256.json').read_bytes());assert all(sha(r/n)==h for n,h in manifest.items())
 status=json.loads((r/'status.json').read_bytes());total_calls+=status['model_calls']
 result=json.loads((r/'results.json').read_bytes())if(r/'results.json').exists()else[]
 for row in result:
  assert row['id']not in outcomes;outcomes[row['id']]={'root':str(r),'kind':'strict_valid'if row['strict_format_and_citation_validation_passed']else'contract_invalid','result_sha256':sha(r/row['id']/'result.json'),'result':row}
 # Parent first control exhausted its two original requests before per-case result writer.
 if r==source:
  validation=json.loads((r/'page5-readiness/format-validation.json').read_bytes());assert len(validation)==2 and not any(v['valid']for v in validation)
  outcomes['page5-readiness']={'root':str(r),'kind':'contract_invalid','validation_sha256':sha(r/'page5-readiness/format-validation.json'),'result':None}
 for folder in r.iterdir():
  if not folder.is_dir()or not(folder/'source-request.json').exists():continue
  case=json.loads((folder/'source-request.json').read_bytes());assert canon(case)==canon(expected[case['id']])
  first=folder/'format-0/generation.json';pre=folder/'format-0/pre-inference-input.json'
  if first.exists():
   g=json.loads(first.read_bytes());actual=hashlib.sha256(b''.join(struct.pack('<q',x)for x in g['input_ids'])).hexdigest();assert actual==cpu[case['id']]['input_ids_sha256'];runtime_bound.add(case['id'])
  elif pre.exists():
   g=json.loads(pre.read_bytes());assert g['input_ids_sha256']==cpu[case['id']]['input_ids_sha256'];runtime_bound.add(case['id'])
  for generation in folder.glob('format-*/generation.json'):
   g=json.loads(generation.read_bytes());eos=g['generation_config']['eos_token_id'];eos=eos if isinstance(eos,list)else[eos]
   assert g['generated_ids']and g['generated_ids'][-1]in eos and not g['hit_output_cap']
   natural_replies.append({'root':str(r),'case':case['id'],'format':generation.parent.name,'generation_sha256':sha(generation),'input_tokens':len(g['input_ids']),'output_tokens':len(g['generated_ids']),'model_seconds':g['seconds']})
 failure=json.loads((r/'technical-failure.json').read_bytes())if(r/'technical-failure.json').exists()else None
 if failure and 'OutOfMemoryError'in failure['traceback']:ooms.append({'root':str(r),'case':'long-history-candidate','failure_sha256':sha(r/'technical-failure.json'),'actual_input_receipt_available':(r/'long-history-candidate/format-0/pre-inference-input.json').exists()})
 roots.append({'root':str(r),'uid':launch['uid'],'command':launch['command'],'status':status,'final_manifest_sha256':sha(r/'final-artifacts-sha256.json'),'process_absent':True})
assert total_calls==27 and total_calls<=40 and len(natural_replies)==25 and len(ooms)==2
assert len(outcomes)==19 and 'long-history-candidate'not in outcomes
outcomes['long-history-candidate']={'kind':'capacity_failure','attempts':ooms,'semantic_pass':None,'official_score':None}
assert set(outcomes)==set(expected)and runtime_bound==set(expected)
assert sum(v['kind']=='strict_valid'for v in outcomes.values())==13
assert sum(v['kind']=='contract_invalid'for v in outcomes.values())==6
root=source.parent/('uitars-real-preflight-finalized-'+str(time.time_ns()));root.mkdir()
summary={'time':time.time(),'scope':'Selected nonblind original20 stage-development controls, not formal GUI trial or paired27B efficacy comparison','cases':20,'cases_with_complete_natural_model_reply':19,'strict_format_and_citation_valid':13,'contract_invalid':6,'capacity_failure':1,'unattempted':0,'model_calls_including_two_prefill_OOMs':27,'complete_EOS_replies_including_format_retries':25,'original_call_cap':40,'actual_original_input_ID_bindings':len(runtime_bound),'roots':roots,'source_cases_sha256':sha(source/'public-requests.json'),'outcomes':outcomes,'reply_receipts':natural_replies,'complete_reply_input_tokens':sum(v['input_tokens']for v in natural_replies),'complete_reply_output_tokens':sum(v['output_tokens']for v in natural_replies),'complete_reply_model_seconds':sum(v['model_seconds']for v in natural_replies),'cost_scope':'Completed25reply receipts only; excludes2OOM prefill work, loading, weight hashing, CPU/development and prior27B costs. Not wall time, currency or energy.','formal_ui_ready':False,'semantic_accuracy':None,'paid_api_calls':0,'gui_actions':0,'official_scores':None,'limits':'Contract-valid does not imply semantic correctness. Capacity failures not semantic zeros. Single39598token22image input failed original BF16/SDPA24GB twice including fragmentation allocator control;32014token21image completion produced output. No resized/truncated inputs, extra retries,27B fallback or old queues.'}
(root/'summary.json').write_text(json.dumps(summary,indent=2));(root/'sha256.json').write_text(json.dumps({'summary.json':sha(root/'summary.json')},indent=2))
print(json.dumps({'root':str(root),'summary_sha256':sha(root/'summary.json'),'summary':summary}))
'''
result=json.loads(remote('LAUNCHES='+repr(launches)+'\nSEALS='+repr(seals)+'\n'+code,host='4090',timeout=60))
receipt.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items()if k!='summary'}))
print(json.dumps({k:v for k,v in result['summary'].items()if k not in {'outcomes','reply_receipts','roots','limits'}}))
