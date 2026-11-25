import json,sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
code=r'''
import json
from pathlib import Path
p=Path('/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-three-01/runs/image-observer-v1--classifieds_112--clean--joint--observer/attempt-1793987248242098761/events.jsonl')
found=[]
for line in p.read_text().splitlines():
 e=json.loads(line)
 if e['kind']=='actual_primary_wire_request':
  d=e['data'];b=d['body'];payload=b.get('payload',{})
  found.append({'seq':e['seq'],'data_keys':list(d),'body_keys':list(b),'payload_keys':list(payload),'body_scalars':{k:v for k,v in b.items() if not isinstance(v,(dict,list))},'payload_scalars':{k:v for k,v in payload.items() if not isinstance(v,(dict,list)) and len(str(v))<100}})
  if len(found)==3:break
print(json.dumps(found))
'''
print(remote(code,host='4090',timeout=30))
