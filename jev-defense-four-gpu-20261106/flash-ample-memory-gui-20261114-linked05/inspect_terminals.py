"""Read-only terminal sealing and request/action count inspection; no model calls."""
import json,time
from control import HERE,R4090,remote,save

code='ROOT='+repr(R4090)+'\n'+r'''
import hashlib,json,time
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
r=Path(ROOT);out={'time':time.time(),'new_model_GUI_calls_by_inspector':0,'terminals':[]}
for p in sorted((r/'batch/runs').glob('*/attempt-*/terminal.json')):
 d=p.parent
 if not(d/'seal.json').exists():continue
 seal=json.loads((d/'seal.json').read_bytes())
 assert all(sha(d/n)==h for n,h in seal.items())
 t=json.loads(p.read_bytes());rows=[json.loads(s)for s in(d/'controller/events.jsonl').read_text().splitlines()]
 previous='0'*64;counts={}
 for index,entry in enumerate(rows):
  v=dict(entry);h=v.pop('sha256')
  assert v['seq']==index and v['previous']==previous
  assert hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==h
  previous=h;counts[v['kind']]=counts.get(v['kind'],0)+1
 assert counts.get('actual_actor_reply',0)==len(t['actor_receipts'])
 assert counts.get('native_environment_action',0)==t['environment_actions']
 out['terminals'].append({'path':str(p),'terminal_sha256':sha(p),'seal_sha256':sha(d/'seal.json'),'sealed_files_verified':len(seal),'event_chain_count':len(rows),'event_chain_head':previous,'event_kinds':counts,'run':t['run'],'outcome':t['outcome'],'decisions':t.get('decisions'),'environment_actions':t.get('environment_actions'),'actor_calls':t.get('actor_calls'),'Flash_request_attempts':t.get('Flash_request_attempts'),'Flash_replies':len(t['Flash_replies']),'recaptures':t.get('recaptures'),'injection_fired':t.get('injection_fired'),'official_reward':t['official_reward'],'scoring_status':t.get('scoring_status'),'infrastructure_failure':t['infrastructure_failure'],'semantic_mirage':t.get('semantic_mirage'),'cleanup_error':t.get('cleanup_error')})
out['batch_status_snapshot']=json.loads((r/'batch/status.json').read_bytes())
print(json.dumps(out))
'''
raw,op=remote('4090',code,'verify-new-GUI-terminals-only')
value={'result':json.loads(raw),'operation':str(op)}
path=HERE/('terminal-audit-'+str(time.time_ns())+'.json');save(path,value)
print(json.dumps({'path':str(path),**value}))
