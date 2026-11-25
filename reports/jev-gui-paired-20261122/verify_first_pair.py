"""Read-only join of the first clean pair; no semantic labels or new calls."""
import json
from pathlib import Path

import control
from prepare import HERE, read, save, sha

JOURNAL = r'''
def events(path):
 head='0'*64;out=[]
 for i,line in enumerate(path.read_bytes().split(b'\n')[:-1]):
  v=json.loads(line);h=v.pop('sha256');assert v['seq']==i and v['previous']==head and digest(canonical(v))==h
  out.append(v);head=h
 return out
def read(q):return json.loads(q.read_bytes())
'''


def main():
    control.POINTER = read(HERE / 'frozen-current.json')
    control.ROOT = Path(control.POINTER['root'])
    control.PACKAGE = Path(control.POINTER['runtime'])
    control.MANIFEST = read(control.PACKAGE / 'manifest.json')
    assert sha(control.PACKAGE / 'manifest.json') == control.POINTER['manifest_sha256']
    target = control.ROOT / 'first-pair-evidence.json'
    assert not target.exists()
    gui = control.remote('4090', control.prefix('4090') + r'''
import json,sys
from pathlib import Path
p=Path(ROOT);sys.path[:0]=[str(p/'flash'),str(p)]
from gate_core import canonical,digest
from resource_guard import sha
from paired_contract import load_plan
assert sha(p/'manifest.json')==EXPECTED
''' + JOURNAL + r'''
_,plan=load_plan(p);out=[]
for slot in plan['queue'][:2]:
 q,=(p/'batch/runs'/slot['run_id']).glob('attempt-*')
 ts=sha(q/'terminal.json');seal=read(q/'seal.json');assert ts==seal['terminal.json']
 t=read(q/'terminal.json');assert t['run']==slot and t['scoring_status']=='complete'and not t['infrastructure_failure']
 j=q/'controller/events.jsonl';assert sha(j)==seal['controller/events.jsonl']
 records=events(j)
 first=next(v['data']for v in records if v['kind']=='PRIVATE_capture_injection')
 assert not first['injected']and first['step']==1
 image=first['captured_sha256']
 assert image==first['delivered_sha256']==sha(q/first['raw_file'])==sha(q/first['delivered_file'])
 calls=[v for v in records if v['kind']=='gate_decision']
 req=next(v['data']for v in records if v['kind']=='actual_actor_request')
 reply=next(v['data']for v in records if v['kind']=='actual_actor_reply')
 assert req['request_id']==reply['request_id']
 assert t['decisions']==t['actor_calls']==1 and t['environment_actions']==0 and t['outcome']=='native_contract_failure'
 assert not t['injection_fired'] and t['recaptures']==0
 err=next(v['data']for v in records if v['kind']=='native_actor_or_parser_failure');assert err['executed']is False
 if slot['gate_enabled']:
  a=next(v['data']for v in records if v['kind']=='capture_receipt_decision')
  assert a['decision']=='YES'and a['image_sha256']==image
  assert len(calls)==1 and calls[0]['data']['decision']=='YES' and calls[0]['data']['image_sha256']==image
  gate=calls[0]['data']['request_id']
 else:
  assert not calls and any(v['kind']=='no_gate_control' for v in records)
  gate=None
 source_score=[v for v in (json.loads(x) for x in (q/'trusted-source/events.jsonl').read_bytes().splitlines()) if v['kind']=='native_official_score']
 assert len(source_score)==1 and source_score[0]['data']['score']==t['official_reward']
 out.append({'run_id':slot['run_id'],'img':image,'actor_id':req['request_id'],'reply_sha256':reply['text_sha256'],
  'gate_id':gate,'outcome':t['outcome'],'score':t['official_reward'],'native_rejection':err['message'],
  'recaptures':t['recaptures'],'terminal_sha256':ts,'controller_events_sha256':sha(j)})
print(json.dumps(out))
''', 'verify-first-clean-GUI-pair')
    support = control.remote('3090', control.prefix('3090') + f'GUI={gui["result"]!r}\n' + r'''
import base64,json,sys
from pathlib import Path
p=Path(ROOT);base=Path(OUTPUT)/'primary';sys.path[:0]=[str(p/'flash'),str(p)]
from gate_core import canonical,digest
from resource_guard import sha
assert sha(p/'manifest.json')==EXPECTED
''' + JOURNAL + r'''
journal=events(base/'journal/events.jsonl');actual=[]
for index,g in enumerate(GUI,1):
 q=base/'requests'/f'{index:05d}';wire=(q/'wire-request.bin').read_bytes();req=json.loads(wire);resp=read(q/'response.json')
 seal=read(q/'seal.json')
 assert req['run_id']==g['run_id'] and resp['request_id']==g['actor_id']==req['request_id']
 assert resp['request_sha256']==digest(wire)==seal['wire-request.bin'] and digest(resp['text'].encode())==g['reply_sha256']
 cur,=[x['image_url']['url']for x in req['body']['messages'][-1]['content']if x['type']=='image_url']
 assert digest(base64.b64decode(cur.split(',',1)[1],validate=True))==g['img']
 assert any(x['kind']=='run_end'and x['data']['run_id']==g['run_id'] and x['data']['terminal_sha256']==g['terminal_sha256']for x in journal)
 forward=read(q/'first-forward.json');gen=read(q/'actual-generation.json');assert gen['natural_EOS']
 for row in forward.values():assert row['sha256']==seal[row['file']]==sha(q/row['file'])
 actual.append((digest(canonical(req['body'])),{k:v['sha256']for k,v in forward.items()},gen['output_ids']))
assert actual[0]==actual[1]
gate=GUI[1]['gate_id'];assert gate and GUI[0]['gate_id']is None
flash=p/'flash/service/requests'/gate;seal=read(flash/'seal.json')
for name,h in seal.items():assert sha(flash/name)==h,name
v=read(flash/'response.json');a=read(flash/'audit.json');r=read(flash/'forward-trace.json')
assert v['request_id']==gate and v['image_sha256']==GUI[1]['img']==sha(flash/'original.png')
assert v['request_sha256']==sha(flash/'wire-request.bin')and v['decision']=='YES'
assert len(r)==1 and not r[0]['use_cache'] and r[0]['past_key_values']is None
assert v['contract_sha256']==sha(p/'flash/gate-contract.json') and a['probabilities']['YES']>a['probabilities']['NO']
assert any(x['kind']=='Flash_reply_forwarded'and x['data']['request_id']==gate and x['data']['run_id']==GUI[1]['run_id']for x in journal)
print(json.dumps({'same_primary_body_actual_input_tensors_output_ids':True,'both_natural_EOS':True,
 'Flash_on_actual_yes':True,'Flash_off_calls':0,'Flash_image_sha256':v['image_sha256'],
 'Flash_probabilities':a['probabilities'],'Flash_seal_sha256':sha(flash/'seal.json')}))
''', 'join-first-clean-pair-actual-forwards')
    save(target, {'manifest_sha256': control.POINTER['manifest_sha256'], 'GUI_terminals': gui,
                  'actual_primary_and_Flash': support, 'aggregate_efficacy_inference': False})
    print(json.dumps({'receipt': str(target), 'sha256': sha(target), 'GUI_terminals': gui['result'],
                      'actual_Flash': support['result']}))


if __name__ == '__main__':
    main()
