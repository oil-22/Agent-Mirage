"""Copy bounded-check evidence for offline review; never feed hidden captures to models."""
import base64,json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
for name in ['v2-live-diagnostic-launch.json','v2-post-diagnostic-launch.json']:
 if not(r/name).exists():continue
 launch=json.loads((r/name).read_text());code='''import pathlib,json,base64,hashlib
r=pathlib.Path(ROOT);state=json.loads((r/'status.json').read_text());a=pathlib.Path(state['attempt'])
files=list((a/'screenshots').glob('*.png'))+[a/'final-actually-captured.png']
events=[json.loads(x)for x in(a/'events.jsonl').read_text().splitlines()]
allowed={'candidate','screen_result','point_crosscheck','focus_crosscheck','recapture_requested','state_invalidated','decision_accepted','action_executed','decision_blocked','private_delivery_ledger'}
print(json.dumps({'state':state,'events':[e for e in events if e['kind']in allowed],'images':{p.name:base64.b64encode(p.read_bytes()).decode()for p in files if p.exists()},'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [a/'events.jsonl',a/'complete.json',a/'technical-failure.json',a/'paused.json']if p.exists()},'complete':json.loads((a/'complete.json').read_text())if(a/'complete.json').exists()else None}))
'''.replace('ROOT',repr(launch['root']))
 data=json.loads(remote(code,host='4090'));out=r/'live-repair-evidence'/name.removesuffix('-launch.json');out.mkdir(parents=True,exist_ok=True)
 for n,raw in data.pop('images').items():(out/n).write_bytes(base64.b64decode(raw))
 (out/'evidence.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 print(str(out),data['state']['phase'])
