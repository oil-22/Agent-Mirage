"""Evaluation-only original capture/delivery binding after a sealed source review.

No browser query, capture, model call or runtime mutation. Private ledger stays
in evaluation provenance and is never supplied to any experimental model.
"""
import base64
import json
from pathlib import Path
import re
import time

import orchestrate


SOURCE = r'''
from pathlib import Path
import base64,hashlib,json,os,time
assert os.getuid()==1015
root=Path(ROOT).resolve();attempt=Path(ATTEMPT).resolve()
assert attempt.parent.parent==root/'batch/runs'
raw=(attempt/'events.jsonl').read_bytes();raw=raw[:raw.rfind(b'\n')+1]
events=[];previous='0'*64
canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
for line in raw.splitlines():
 e=json.loads(line);signature=e.pop('sha256')
 assert e['seq']==len(events)and e['previous']==previous
 assert hashlib.sha256(canonical(e)).hexdigest()==signature
 e['sha256']=signature;events.append(e);previous=signature
execution=next(e for e in events if e['sha256']==EXECUTED)
assert execution['kind']=='action_executed'
ledger=next(e for e in events[execution['seq']+1:]if e['kind']=='private_delivery_ledger'and e['data']['step']==STEP)
observation=next(e for e in events[ledger['seq']+1:]if e['kind']=='observation')
current=next(v for v in observation['data']['public']['images']if v['role']=='current')
assert current['sha256']==ledger['data']['delivered_sha256']
exports={};bindings={}
for label,field in [('captured','capture_sha256'),('delivered','delivered_sha256')]:
 p=attempt/'screenshots'/('%03d-%s.png'%(STEP,label));picture=p.read_bytes()
 digest=hashlib.sha256(picture).hexdigest();assert digest==ledger['data'][field]
 exports[label+'.png']=base64.b64encode(picture).decode()
 bindings[label]={'original_path':str(p),'sha256':digest,'bytes':len(picture)}
print(json.dumps({'time':time.time(),'read_only':True,'execution_event':execution,
 'private_delivery_ledger':ledger,'next_public_observation_id':observation['data']['public']['observation_id'],
 'next_public_observation_event_sha256':observation['sha256'],'bindings':bindings,'exports':exports,
 'journal_snapshot':{'count':len(events),'head':previous,'complete_prefix_sha256':hashlib.sha256(raw).hexdigest()},
 'private_evaluation_provenance_only_never_checker_input':True,
 'new_model_GUI_capture_action_scorer_paid_calls':0}))
'''


def main(joinpath, ident, step):
    root = orchestrate.HERE
    assert re.fullmatch(r'[0-9a-f]{20}', ident) and 1 <= step <= 50
    assert joinpath.parent.parent == root
    for name, expected in json.loads((joinpath.parent / 'seal.json').read_bytes()).items():
        assert orchestrate.sha(joinpath.parent / name) == expected
    joined = json.loads(joinpath.read_bytes())
    assert joined['all_source_labels_sealed_before_this_join']
    row = next(v for v in joined['rows'] if v['id'] == ident)
    assert row['accepted'] and row['executed'] and len(row['executed_events']) == 1
    pointer = root / ('capture-delivery-' + ident + '-created.json')
    assert not pointer.exists()
    prefix = ('ROOT=' + repr(orchestrate.GUIROOT) + '\nATTEMPT=' + repr(row['original_attempt'])
        + '\nEXECUTED=' + repr(row['executed_events'][0]['sha256']) + '\nSTEP=' + repr(step) + '\n')
    output, operation = orchestrate.remote('4090', prefix + SOURCE,
        'evaluation-original-capture-delivery-after-source-seal-' + ident, timeout=55)
    result = json.loads(output)
    target = root / ('capture-delivery-' + ident + '-' + str(time.time_ns()))
    target.mkdir()
    for name, encoded in result.pop('exports').items():
        assert name in {'captured.png', 'delivered.png'}
        (target / name).write_bytes(base64.b64decode(encoded, validate=True))
        assert orchestrate.sha(target / name) == result['bindings'][Path(name).stem]['sha256']
    result.update(source_sealed_execution_join=str(joinpath),
                  source_sealed_execution_join_sha256=orchestrate.sha(joinpath),
                  remote_operation=str(operation), original_pixels_require_independent_review=True)
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    orchestrate.save(target / 'receipt.json', result)
    orchestrate.save(target / 'seal.json', {p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
    authority = dict(root=str(target), receipt_sha256=orchestrate.sha(target / 'receipt.json'),
        seal_sha256=orchestrate.sha(target / 'seal.json'),
        capture_sha256=result['bindings']['captured']['sha256'],
        delivered_sha256=result['bindings']['delivered']['sha256'])
    orchestrate.save(pointer, authority)
    print(json.dumps(authority, ensure_ascii=False))
