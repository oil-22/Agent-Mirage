"""Read-only outcome join for an already source-reviewed native sort click."""
import hashlib
import json
import time
from pathlib import Path

from remote_control import HERE, ROOT4090, remote, save, sha


labels = HERE / 'semantic-review-first-four-01' / 'labels.json'
assert sha(labels) == '7559124e77864d920425f5cdc114ceb23000902e21d752dea60512576422b240'
row = next(v for v in json.loads(labels.read_bytes())['rows'] if v['id'] == '441acb274a10d93eb556')
code = 'ROOT=' + repr(ROOT4090) + '\nEXPECTED=' + repr(row['candidate_event_sha256']) + '\n' + r'''
from pathlib import Path
import hashlib,json,time
root=Path(ROOT);matches=[]
for attempt in sorted((root/'batch/runs').glob('*/attempt-*')):
 p=attempt/'events.jsonl'
 if not p.exists():continue
 raw=p.read_bytes();lines=raw.splitlines()
 if not raw.endswith(b'\n'):lines=lines[:-1]
 events=[];previous='0'*64
 for line in lines:
  event=json.loads(line);sig=event.pop('sha256')
  assert event['seq']==len(events) and event['previous']==previous
  assert hashlib.sha256(json.dumps(event,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==sig
  event['sha256']=sig;events.append(event);previous=sig
 for index,event in enumerate(events):
  if event['sha256']!=EXPECTED:continue
  assert event['kind']=='candidate'
  subsequent=[]
  allowed={'candidate','verifier_raw','candidate_claim_origin_check','verdict','point_crosscheck','target_alignment','state_invalidated','recapture_requested','decision_accepted','decision_blocked','action_executed'}
  for value in events[index:]:
   if value['seq']>index and value['kind'] in {'actor_request','candidate'}:break
   if value['kind']in allowed:subsequent.append(value)
  matches.append({'attempt':str(attempt),'candidate_event':event,'source_bound_window':subsequent,'snapshot_chain_events':len(events),'snapshot_chain_head':previous})
assert len(matches)==1
print(json.dumps({'read_only':True,'new_model_GUI_scorer_calls':0,'time':time.time(),'match':matches[0]},ensure_ascii=False))
'''
out, operation = remote('4090', code, 'join-reviewed-normal-sort-click', timeout=55)
data = json.loads(out)
target = HERE / 'reviewed-sort-false-block-join' / str(time.time_ns())
target.mkdir(parents=True, exist_ok=False)
save(target / 'join.json', data)
save(target / 'receipt.json', {'source_labels':str(labels), 'source_labels_sha256':sha(labels),
    'join_sha256':sha(target/'join.json'), 'operation':str(operation),
    'source_labels_preceded_private_join':True, 'new_model_GUI_scorer_calls':0})
save(target / 'seal.json', {p.name:sha(p) for p in target.iterdir() if p.is_file()})
print(json.dumps({'root':str(target),'data':data},ensure_ascii=False))
