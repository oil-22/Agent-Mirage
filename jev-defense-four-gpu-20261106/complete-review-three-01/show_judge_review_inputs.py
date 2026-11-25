import json
from pathlib import Path
root=Path(__file__).parent/'judge-legal-projection-linked03/review/judges'
seen={}
for p in sorted(root.glob('*.json')):
 d=json.loads(p.read_bytes());phase=d['phase'];native=d['actual_native_payload']
 if phase not in seen:
  seen[phase]=True
  print('SYSTEM '+phase+'\n'+native['system'])
print('CANDIDATES')
for p in sorted(root.glob('*.json')):
 d=json.loads(p.read_bytes());c=d['actual_native_payload']['candidate']
 if c is not None:print(json.dumps({'index':int(p.stem),'phase':d['phase'],'candidate':c},ensure_ascii=False))
