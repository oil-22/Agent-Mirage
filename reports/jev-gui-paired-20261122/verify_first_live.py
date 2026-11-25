"""Bind the first live screenshot and forward to its native disposition."""
from pathlib import Path

import control
from prepare import HERE, read, save, sha


def main():
    control.POINTER = read(HERE / 'frozen-current.json')
    control.ROOT = Path(control.POINTER['root'])
    control.PACKAGE = Path(control.POINTER['runtime'])
    control.MANIFEST = read(control.PACKAGE / 'manifest.json')
    assert sha(control.PACKAGE / 'manifest.json') == control.POINTER['manifest_sha256']
    root = control.ROOT
    result_file = root / 'first-live-evidence.json'
    assert not result_file.exists()
    start = control.remote('3090', control.prefix('3090') + r'''
import base64,hashlib,json,os,sys
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from gate_core import canonical,digest
from resource_guard import sha
from paired_contract import load_plan
assert sha(p/'manifest.json')==EXPECTED
_,plan=load_plan(p);q=Path(OUTPUT)/'primary/requests/00001'
if not(q/'seal.json').exists() or not(q/'response.json').exists():
 print(json.dumps({'pending_first_primary_reply':True}));raise SystemExit(0)
def read(f):return json.loads(f.read_bytes())
seal=read(q/'seal.json')
for name,h in seal.items():assert sha(q/name)==h,name
raw=(q/'wire-request.bin').read_bytes();req=json.loads(raw);response=read(q/'response.json');gen=read(q/'actual-generation.json')
assert req['run_id']==plan['queue'][0]['run_id']and req['decision_index']==1
assert response['request_id']==req['request_id'] and response['request_sha256']==digest(raw)
assert gen['natural_EOS'] and gen['actual_forward_calls']>0
assert read(q/'body.json')==req['body']
prepared=read(q/'prepared.json');first=read(q/'first-forward.json')
assert first.keys()==prepared.keys() and {'input_ids','pixel_values','image_grid_thw'}<=first.keys()
for key,v in first.items():
 assert all(v[k]==prepared[key][k]for k in ('shape','dtype','sha256','bytes'))
 assert seal[v['file']]==v['sha256']
current=[v['image_url']['url'] for v in req['body']['messages'][-1]['content']if v['type']=='image_url'];assert len(current)==1
print(json.dumps({'run_id':req['run_id'],'step':1,'body_sha256':digest(canonical(req['body'])),'request_id':req['request_id'],
 'current_image_sha256':digest(base64.b64decode(current[0].split(',',1)[1],validate=True)),
 'reply_sha256':digest(response['text'].encode()),'input_tokens':gen['input_tokens'],'output_tokens':gen['output_tokens'],
 'native_EOS':True,'actual_first_forward_tensor_hashes':{k:v['sha256']for k,v in first.items()},
 'request_folder':str(q),'request_seal_sha256':sha(q/'seal.json')}))
''', 'verify-first-primary-forward', timeout=40)
    model = start['result']
    if model.get('pending_first_primary_reply'):
        return model
    gui = control.remote('4090', control.prefix('4090') + f'MODEL={model!r}\n' + r'''
import json,sys
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from gate_core import canonical,digest
from resource_guard import sha
assert sha(p/'manifest.json')==EXPECTED
attempts=list((p/'batch/runs'/MODEL['run_id']).glob('attempt-*'));assert len(attempts)==1
q=attempts[0]
if not(q/'controller/events.jsonl').exists():
 print(json.dumps({'pending_controller':True}));raise SystemExit(0)
# Ignore only a non-terminated last line if the live writer is appending it.
lines=(q/'controller/events.jsonl').read_bytes().split(b'\n')[:-1]
head='0'*64;events=[]
for i,line in enumerate(lines):
 item=json.loads(line);h=item.pop('sha256')
 assert i==item['seq'] and head==item['previous'] and h==digest(canonical(item))
 head=h;events.append(item)
if not any(v['kind']=='actual_actor_reply'and v['data']['request_id']==MODEL['request_id']for v in events):
 print(json.dumps({'pending_controller_reply':True}));raise SystemExit(0)
pre=next(v['data']for v in events if v['kind']=='PRIVATE_capture_injection')
assert pre['step']==1 and not pre['injected'] and pre['captured_sha256']==pre['delivered_sha256']==MODEL['current_image_sha256']
assert sha(q/pre['raw_file'])==sha(q/pre['delivered_file'])==MODEL['current_image_sha256']
req=next(v['data']for v in events if v['kind']=='actual_actor_request'and v['data']['request_id']==MODEL['request_id']);assert req['body_sha256']==MODEL['body_sha256']
reply=next(v['data']for v in events if v['kind']=='actual_actor_reply'and v['data']['request_id']==MODEL['request_id']);assert reply['text_sha256']==MODEL['reply_sha256']
bypass=next(v['data']for v in events if v['kind']=='no_gate_control')
assert bypass['capture_id']==pre['capture_id'] and bypass['no_auxiliary_model_called']
dispatched=next((v['data'] for v in events if v['kind']=='native_proposal_dispatched' and v['data']['capture_id']==pre['capture_id']),None)
native_rejection=None
if dispatched is None:
 if not (q/'terminal.json').exists() or not (q/'seal.json').exists():
  print(json.dumps({'pending_native_disposition':True}));raise SystemExit(0)
 t=json.loads((q/'terminal.json').read_bytes());seal=json.loads((q/'seal.json').read_bytes())
 assert sha(q/'terminal.json')==seal['terminal.json']
 assert t['outcome']=='native_contract_failure' and not t['infrastructure_failure']
 native_rejection=next(v['data']for v in events if v['kind']=='native_actor_or_parser_failure')
 assert native_rejection['executed']is False
else:assert dispatched['candidate_sha256']==MODEL['reply_sha256']
action=[v['data']for v in events if v['kind']=='native_environment_action'and v['data']['step']==1]
assert len(action)==int(dispatched is not None and dispatched['environment_action'] is True)
print(json.dumps({'actual_run':MODEL['run_id'],'attempt':str(q),'capture_id':pre['capture_id'],
 'native_environment_action':action[0]if action else None,'native_dispatched':dispatched,'native_rejection':native_rejection,
 'controller_events':len(events),'controller_prefix_head':head,'no_gate_in_baseline':True}))
''', 'join-first-capture-primary-and-action', timeout=40)
    if any(key.startswith('pending_') for key in gui['result']):
        return gui['result']
    result = {'manifest_sha256': control.POINTER['manifest_sha256'], 'first_primary_forward': start,
              'first_native_disposition': gui, 'paired_result_claimed': False}
    save(result_file, result)
    return {'first_live_evidence': str(result_file), 'sha256': sha(result_file),
            'first_run': model['run_id'], 'main_EOS': True,
            'native_environment_action': gui['result']['native_environment_action'] is not None,
            'native_rejection': gui['result']['native_rejection']}


if __name__ == '__main__':
    import json
    print(json.dumps(main(), ensure_ascii=False))
