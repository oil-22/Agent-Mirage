"""Read only the original Controller chain, exporting a public schema inventory."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

CODE = r'''
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
 if any(term in kind for term in ['accepted','rejected','executed','candidate','recapture','regenerat']):
  selected.append({'seq':i,'kind':kind,'sha256':row['sha256'],'data':data})
assert i+1==1103 and previous=='c120b3b6ea1a739a91b29726628995a0a35703ed6b8514b55fe7a7c8a6748b20'
assert p.read_bytes()==raw
for v in kinds.values():v['data_keys']=sorted(v['data_keys'])
print(json.dumps({'source':str(p),'source_sha256':before,'event_count':1103,'head':previous,'kinds':kinds,'selected_public_rows':selected,'source_unchanged':True,'PRIVATE_event_values_exported':False,'new_model_GUI_health_scorer_calls':0}))
'''

if __name__ == '__main__':
    out=Path(__file__).parent/'postlabel-join-preparation-01'
    out.mkdir(exist_ok=False)
    data=json.loads(remote(CODE,timeout=60,host='4090'))
    with(out/'public-controller-join-source.json').open('x',encoding='utf8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    mapping={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()}
    with(out/'seal.json').open('x',encoding='utf8')as f:json.dump(mapping,f,indent=2)
    print(json.dumps({'out':str(out),'source_sha256':data['source_sha256'],'event_count':data['event_count'],'selected_count':len(data['selected_public_rows']),'kinds':data['kinds'],'seal_sha256':hashlib.sha256((out/'seal.json').read_bytes()).hexdigest()}))
