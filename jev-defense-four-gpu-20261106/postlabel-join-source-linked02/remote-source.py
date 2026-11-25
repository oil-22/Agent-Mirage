
import hashlib,json
from pathlib import Path
p=Path('/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-three-01/runs/image-observer-v1--classifieds_112--clean--joint--observer/attempt-1793987248242098761/events.jsonl')
raw=p.read_bytes();before=hashlib.sha256(raw).hexdigest();previous='0'*64
canon=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
kinds={};selected=[]
for i,line in enumerate(raw.splitlines()):
 row=json.loads(line);assert row['seq']==i and row['previous']==previous
 assert hashlib.sha256(canon({k:v for k,v in row.items()if k!='sha256'})).hexdigest()==row['sha256'];previous=row['sha256']
 kind=row['kind']
 if kind.startswith('private'):continue
 data=row['data'];entry=kinds.setdefault(kind,{'count':0,'data_keys':set()});entry['count']+=1
 if isinstance(data,dict):entry['data_keys'].update(data)
 if kind in {'verdict','state_invalidated','verifier_format_failure','decision_blocked','history_report_crosscheck'}:
  selected.append({'seq':i,'kind':kind,'sha256':row['sha256'],'data':data})
assert i+1==1103 and previous=='c120b3b6ea1a739a91b29726628995a0a35703ed6b8514b55fe7a7c8a6748b20'
assert p.read_bytes()==raw
for v in kinds.values():v['data_keys']=sorted(v['data_keys'])
print(json.dumps({'source':str(p),'source_sha256':before,'event_count':1103,'head':previous,'kinds':kinds,'selected_public_rows':selected,'source_unchanged':True,'PRIVATE_event_values_exported':False,'new_model_GUI_health_scorer_calls':0}))
