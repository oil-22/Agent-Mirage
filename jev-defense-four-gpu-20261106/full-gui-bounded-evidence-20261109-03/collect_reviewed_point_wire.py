"""Export exact recorded point-check inputs; no model request or GUI operation."""
import base64
import json
import time
from remote_control import HERE, ROOT4090, remote, save, sha

labels=HERE/'semantic-review-candidate-nine-01/labels.json'
assert sha(labels)=='9ee774c923a6e935c97db4e41c635c3211a5dff51b5d0f7a199feb7a1455b189'
expected=json.loads(labels.read_bytes())['rows'][0]['candidate_event_sha256']
code='ROOT='+repr(ROOT4090)+'\nEXPECTED='+repr(expected)+'\n'+r'''
from pathlib import Path
import hashlib,json
r=Path(ROOT);out=[]
for a in(r/'batch/runs').glob('*/attempt-*'):
 p=a/'events.jsonl'
 if not p.exists():continue
 raw=p.read_bytes();lines=raw.splitlines()
 if not raw.endswith(b'\n'):lines=lines[:-1]
 events=[];previous='0'*64
 for line in lines:
  v=json.loads(line);sig=v.pop('sha256');assert v['seq']==len(events)and v['previous']==previous
  assert hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==sig
  v['sha256']=sig;events.append(v);previous=sig
 active=False
 for e in events:
  if e['sha256']==EXPECTED:active=True;continue
  if not active:continue
  if e['kind']in {'candidate','actor_request'}:break
  if e['kind']=='actual_judge_wire_request':
   payload=e['data']['body']['payload']
   if isinstance(payload['candidate'],dict)and payload['candidate'].get('mode')=='point_probe':out.append(e)
assert out
print(json.dumps({'point_wire_events':out,'new_model_HTTP_GUI_calls':0}))
'''
out,operation=remote('4090',code,'export-reviewed-actual-point-wire-inputs',timeout=55)
data=json.loads(out);root=HERE/'reviewed-point-wire-inputs'/str(time.time_ns());root.mkdir(parents=True,exist_ok=False)
for index,e in enumerate(data['point_wire_events']):
    target=root/str(index);target.mkdir();save(target/'wire-event.json',e)
    payload=e['data']['body']['payload']
    for i,im in enumerate(payload['view']['images']):
        (target/('image-%d.png'%i)).write_bytes(base64.b64decode(im['raw_base64']))
    save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
save(root/'collection.json',{'operation':str(operation),'source_labels_sha256':sha(labels),'models_HTTP_GUI_calls':0})
print(json.dumps({'root':str(root),'requests':[{'index':i,'candidate':e['data']['body']['payload']['candidate'],
    'wire_sha256':e['data']['wire_sha256'],'messages':e['data']['body']['payload']['view']['messages'],
    'images':len(e['data']['body']['payload']['view']['images'])}for i,e in enumerate(data['point_wire_events'])]},ensure_ascii=False))
