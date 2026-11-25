"""Limited outcome window for a source-first label sealed before this join."""
import argparse
import json
import time
from pathlib import Path
from remote_control import HERE, ROOT4090, remote, save, sha

def main(a):
    assert sha(a.labels)==a.labels_sha256
    rows=json.loads(a.labels.read_bytes())['rows']
    row=next(v for v in rows if v['id']==a.id)
    expected=row['candidate_event_sha256']
    code='ROOT='+repr(ROOT4090)+'\nEXPECTED='+repr(expected)+'\n'+r'''
from pathlib import Path
import hashlib,json,time
root=Path(ROOT);matches=[]
for attempt in sorted((root/'batch/runs').glob('*/attempt-*')):
 p=attempt/'events.jsonl'
 if not p.exists():continue
 raw=p.read_bytes();lines=raw.splitlines()
 if not raw.endswith(b'\n'):lines=lines[:-1]
 previous='0'*64;events=[]
 for line in lines:
  event=json.loads(line);sig=event.pop('sha256')
  assert event['seq']==len(events) and event['previous']==previous
  assert hashlib.sha256(json.dumps(event,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==sig
  event['sha256']=sig;previous=sig;events.append(event)
 for index,event in enumerate(events):
  if event['sha256']!=EXPECTED:continue
  assert event['kind']=='candidate';window=[]
  allowed={'candidate','verifier_raw','verifier_format_failure','candidate_claim_origin_check','verdict','point_crosscheck','point_evidence_unavailable','target_alignment','state_invalidated','recapture_requested','decision_accepted','decision_blocked','action_executed','appearance_absence_source','appearance_absence_abstained','native_direction_consistency'}
  for value in events[index:]:
   if value['seq']>index and value['kind']in {'actor_request','candidate'}:break
   if value['kind']in allowed:window.append(value)
  matches.append({'attempt':str(attempt),'candidate_event':event,'source_bound_window':window,'snapshot_chain_events':len(events),'snapshot_chain_head':previous})
assert len(matches)==1
print(json.dumps({'read_only':True,'new_model_GUI_scorer_calls':0,'time':time.time(),'match':matches[0]},ensure_ascii=False))
'''
    out,operation=remote('4090',code,'join-source-reviewed-candidate-'+a.id,timeout=55)
    data=json.loads(out);root=HERE/'reviewed-candidate-outcome-joins'/(str(time.time_ns())+'-'+a.id);root.mkdir(parents=True,exist_ok=False)
    save(root/'join.json',data)
    save(root/'receipt.json',{'labels':str(a.labels),'labels_sha256':sha(a.labels),'id':a.id,
        'source_labels_preceded_this_private_join':True,'operation':str(operation),'models_GUI_calls':0})
    save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
    print(json.dumps({'root':str(root),'data':data},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--labels',type=Path,required=True);p.add_argument('--labels-sha256',required=True);p.add_argument('--id',required=True)
    main(p.parse_args())
