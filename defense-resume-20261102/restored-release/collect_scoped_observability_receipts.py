"""Audit actual requests, complete input IDs, output EOS and source-bound journal replies."""
import base64,json,time
from pathlib import Path
from remote import remote
from collect_native_direction_service_receipts import judge_messages,sha,canon
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
assert not(PREP/'service-audit-current.json').exists()
pointer=json.loads((PREP/'inspection-current.json').read_bytes());assert pointer['terminal']and pointer['status']['phase']=='completed'
root=Path(pointer['collected_root']);summary=json.loads((root/'summary.json').read_bytes());expected=[];chains=[];source_checks=[];format_errors=[]
for case in summary['results']:
    events=[json.loads(s)for s in(root/'journal'/case['id']/'events.jsonl').read_text(encoding='utf-8').splitlines()];head='0'*64;requests=[]
    for event in events:
        stripped={k:v for k,v in event.items()if k!='sha256'};assert event['previous']==head and sha(canon(stripped))==event['sha256'];head=event['sha256']
        kind=event['kind']
        if kind=='verifier_request':requests.append({'case':case['id'],'event':event})
        if kind=='verifier_raw':assert requests and 'reply'not in requests[-1];requests[-1]['reply']=event
        if kind=='explicit_image_source_check':source_checks.append({'case':case['id'],**event['data']})
        if kind=='verifier_format_failure':format_errors.append({'case':case['id'],**event['data']})
    assert len(requests)==len(case['calls'])
    for req,call in zip(requests,case['calls']):req['call']=call;expected.append(req)
    chains.append({'case':case['id'],'events':len(events),'head':head})
assert len(expected)==summary['new_model_calls']<=24
receipts=[x['call']['receipt']for x in expected];assert len(receipts)==len(set(receipts))
service=json.loads((BASE/'defense-service-resume-current.json').read_bytes())
code=r'''
import base64,hashlib,json
from pathlib import Path
b=Path(SERVICE)/'requests';out={}
for name in RECEIPTS:
 r=Path(name);assert r.parent==b and r.name.isdigit()and r.stat().st_uid==1033
 files={p.name:{'base64':base64.b64encode(p.read_bytes()).decode(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in r.iterdir()if p.is_file()}
 assert {'request.json','generation.json','response.json'}<=files.keys()and'failure.json'not in files
 out[name]=files
print(json.dumps(out))
'''
raw=json.loads(remote('SERVICE='+repr(service['root'])+'\nRECEIPTS='+repr(receipts)+'\n'+code,host='3090',timeout=120))
out=PREP/('service-receipts-'+str(time.time_ns()));out.mkdir();records=[]
for row in expected:
    receipt=row['call']['receipt'];files=raw[receipt];folder=out/Path(receipt).name;folder.mkdir()
    for n,d in files.items():
        b=base64.b64decode(d['base64']);assert sha(b)==d['sha256'];(folder/n).write_bytes(b)
    request=json.loads((folder/'request.json').read_bytes());generation=json.loads((folder/'generation.json').read_bytes());response=json.loads((folder/'response.json').read_bytes())
    d=row['event']['data'];public=d['public'];assert request['operation']=='judge'and request['system']==d['system']and request['candidate']==d['candidate']
    actual={k:v for k,v in request['view'].items()if k!='images'};actual['images']=[]
    for im in request['view']['images']:
        b=base64.b64decode(im['raw_base64']);h=sha(b);orig=next(x for x in public['images']if x['sha256']==h);assert orig['role']==im['role'];actual['images'].append(orig)
    assert canon(actual)==canon(public)
    assert generation['text']==response['verdict']==row['reply']['data']['response']
    messages=judge_messages(request,public);assert generation['request_messages_sha256']==sha(canon(messages))
    assert generation['generation_config']['max_new_tokens']==4096 and generation['verifier_grammar']
    eos=generation['generation_config']['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
    assert not generation['hit_output_cap']and generation['generated_ids'][-1]in eos
    assert len(generation['input_ids'])==response['input_tokens']==row['call']['input_tokens']
    assert len(generation['generated_ids'])==response['output_tokens']==row['call']['output_tokens']
    assert generation['environment_actions_executed']is False
    records.append({'case':row['case'],'phase':d['phase'],'format_retry':d['format_retry'],'receipt':receipt,'input_tokens':response['input_tokens'],'output_tokens':response['output_tokens'],'seconds':response['seconds'],'natural_eos':True,'actual_request_and_response_bound':True,'request_sha256':files['request.json']['sha256'],'generation_sha256':files['generation.json']['sha256'],'response_sha256':files['response.json']['sha256']})
audit={'records':records,'event_chains':chains,'source_checks':source_checks,'format_errors':format_errors,'verified_distinct_requests':len(records),'input_tokens':sum(r['input_tokens']for r in records),'output_tokens':sum(r['output_tokens']for r in records),'summed_generation_seconds':sum(r['seconds']for r in records),'new_actor_calls':0,'model_controlled_GUI_actions':0,'official_evaluations':0,'paid_API_calls':0,'formal_release':False,'cost_scope':'Only summed generation tokens/seconds; source-collection browser operations/loading/analysis excluded, not wall-time/currency/energy.'}
(out/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8');(out/'sha256.json').write_text(json.dumps({str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()},indent=2))
result={'directory':str(out),'audit_sha256':sha((out/'audit.json').read_bytes()),'manifest_sha256':sha((out/'sha256.json').read_bytes()),'calls':len(records)}
(PREP/'service-audit-current.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
