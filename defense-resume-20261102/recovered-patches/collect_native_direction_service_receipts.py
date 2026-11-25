"""Bind terminal journals to full actual service requests, token IDs, EOS and replies."""
import base64,copy,hashlib,json,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'native-direction-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def judge_messages(request,public):
    view=copy.deepcopy(public)
    for message in view['messages']:
        if not isinstance(message['content'],list):continue
        blocks=[]
        for block in message['content']:
            if block['type']=='image_url':
                url=block['image_url'];url=url['url']if isinstance(url,dict)else url
                h=sha(base64.b64decode(url.split(',',1)[1]));indices=[i for i,im in enumerate(view['images'])if im['sha256']==h];assert indices
                blocks.append({'type':'image_reference','image_index':indices[0]})
            else:blocks.append(block)
        message['content']=blocks
    blocks=[{'type':'text','text':json.dumps({'public':view,'candidate':request['candidate']},ensure_ascii=False)}]
    for i,im in enumerate(request['view']['images']):
        blocks.extend([{'type':'text','text':f"Image index {i}, role {im['role']}, original pixels:"},
                       {'type':'image_url','image_url':{'url':'data:image/png;base64,'+im['raw_base64']}}])
    return [{'role':'system','content':request['system']},{'role':'user','content':blocks}]
def collect():
    assert not(PREP/'service-audit-current.json').exists(),'Already collected; do not rewrite terminal audit'
    pointer=json.loads((PREP/'inspection-current.json').read_bytes());assert pointer['terminal']and pointer['status']['phase']=='completed'
    root=Path(pointer['collected_root']);summary=json.loads((root/'summary.json').read_bytes());template=json.loads((root/'release/native-vwa-request.json').read_bytes())
    expected=[];chains=[];candidates=[];guards=[];verdicts=[];format_failures=[]
    for case in summary['results']:
        events=[json.loads(s)for s in(root/'journal'/case['id']/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        requests=[];head='0'*64
        for event in events:
            stripped={k:v for k,v in event.items()if k!='sha256'};assert event['previous']==head and sha(canon(stripped))==event['sha256'];head=event['sha256']
            kind=event['kind'];d=event['data']
            if kind in {'actor_request','verifier_request'}:requests.append({'case':case['id'],'event':event})
            if kind in {'candidate','verifier_raw'}:
                assert requests and 'reply'not in requests[-1]
                assert (requests[-1]['event']['kind']=='actor_request')==(kind=='candidate')
                requests[-1]['reply']=event
            if kind=='candidate':candidates.append({'case':case['id'],**d})
            if kind=='native_direction_consistency':guards.append({'case':case['id'],**d})
            if kind=='verdict':verdicts.append({'case':case['id'],**d})
            if kind=='verifier_format_failure':format_failures.append({'case':case['id'],**d})
        assert len(requests)==len(case['calls'])
        for row,call in zip(requests,case['calls']):row['call']=call;expected.append(row)
        chains.append({'case':case['id'],'events':len(events),'head':head})
    assert len(expected)==summary['new_model_calls']<=24
    receipts=[r['call']['receipt']for r in expected];assert len(set(receipts))==len(receipts)
    service=json.loads((BASE/'defense-service-resume-current.json').read_bytes())
    code=r'''
import base64,hashlib,json
from pathlib import Path
base=Path(SERVICE)/'requests';out={}
for name in RECEIPTS:
 r=Path(name);assert r.parent==base and r.name.isdigit()and r.stat().st_uid==1033
 files={f.name:{'base64':base64.b64encode(f.read_bytes()).decode(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}for f in r.iterdir()if f.is_file()}
 assert {'request.json','generation.json','response.json'}<=files.keys()and 'failure.json'not in files
 out[name]=files
print(json.dumps(out))
'''
    raw=json.loads(remote('SERVICE='+repr(service['root'])+'\nRECEIPTS='+repr(receipts)+'\n'+code,host='3090',timeout=120))
    out=PREP/('service-receipts-'+str(time.time_ns()));out.mkdir();records=[]
    for row in expected:
        receipt=row['call']['receipt'];files=raw[receipt];folder=out/Path(receipt).name;folder.mkdir()
        for n,entry in files.items():
            b=base64.b64decode(entry['base64']);assert sha(b)==entry['sha256'];(folder/n).write_bytes(b)
        request=json.loads((folder/'request.json').read_bytes());generation=json.loads((folder/'generation.json').read_bytes());response=json.loads((folder/'response.json').read_bytes())
        event=row['event'];d=event['data'];reply=row['reply']['data'];public=d['public']
        if event['kind']=='actor_request':
            body=copy.deepcopy(template);body['messages']=public['messages'];assert request=={'operation':'actor','body':body}
            assert response['text']==reply['text']==generation['text'];messages=body['messages'];limit=2048
            assert generation['verifier_grammar']is None
        else:
            assert request['operation']=='judge'and request['candidate']==d['candidate']and request['system']==d['system']
            got={k:v for k,v in request['view'].items()if k!='images'};got['images']=[]
            for im in request['view']['images']:
                b=base64.b64decode(im['raw_base64']);h=sha(b);orig=next(x for x in public['images']if x['sha256']==h);assert orig['role']==im['role'];got['images'].append(orig)
            assert canon(got)==canon(public)
            assert response['verdict']==reply['response']==generation['text'];messages=judge_messages(request,public);limit=4096
            assert generation['verifier_grammar']
        assert generation['request_messages_sha256']==sha(canon(messages))
        assert generation['generation_config']['max_new_tokens']==limit
        eos=generation['generation_config']['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
        assert not generation['hit_output_cap']and generation['generated_ids'][-1]in eos
        assert response['input_tokens']==len(generation['input_ids'])and response['output_tokens']==len(generation['generated_ids'])
        assert row['call']['input_tokens']==response['input_tokens']and row['call']['output_tokens']==response['output_tokens']
        for message in public['messages']:
            if isinstance(message['content'],list):
                for block in message['content']:
                    if block['type']=='image_url':
                        url=block['image_url'];url=url['url']if isinstance(url,dict)else url;h=sha(base64.b64decode(url.split(',',1)[1]));assert any(im['sha256']==h for im in public['images'])
        records.append({'case':row['case'],'receipt':receipt,'operation':request['operation'],'input_tokens':response['input_tokens'],'output_tokens':response['output_tokens'],'seconds':response['seconds'],'natural_eos':True,'full_request_and_output_match_journal':True,'request_sha256':files['request.json']['sha256'],'generation_sha256':files['generation.json']['sha256'],'response_sha256':files['response.json']['sha256']})
    audit={'directory':str(out),'remote_root':pointer['root'],'verified_distinct_requests':len(records),'actor_calls':sum(r['operation']=='actor'for r in records),'judge_calls':sum(r['operation']=='judge'for r in records),'input_tokens':sum(r['input_tokens']for r in records),'output_tokens':sum(r['output_tokens']for r in records),'summed_generation_seconds':sum(r['seconds']for r in records),'records':records,'event_chains':chains,'candidates':candidates,'guards':guards,'verdicts':verdicts,'format_failures':format_failures,'gui_actions':0,'official_scores':0,'paid_api_calls':0,'formal_release':False,'cost_scope':'Summed generation tokens/seconds only; not wall time/currency/energy/end-to-end cost'}
    (out/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'sha256.json').write_text(json.dumps({str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()},indent=2))
    result={'directory':str(out),'audit_sha256':sha((out/'audit.json').read_bytes()),'manifest_sha256':sha((out/'sha256.json').read_bytes()),'calls':len(records)}
    (PREP/'service-audit-current.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':print(json.dumps(collect()))
