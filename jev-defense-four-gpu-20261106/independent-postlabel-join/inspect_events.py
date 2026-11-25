import json, hashlib, collections
from pathlib import Path
p = Path(__file__).parent / 'sources' / 'final-events.jsonl'
raw = p.read_bytes()
events = [json.loads(x) for x in raw.splitlines()]
print(json.dumps({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'events':len(events),'kinds':collections.Counter(x['kind'] for x in events),'first':{k:v for k,v in events[0].items() if k!='data'},'last':{k:v for k,v in events[-1].items() if k!='data'}}, ensure_ascii=False))
for e in events:
    if any(t in e['kind'] for t in ('candidate','accept','reject','execut','action','outcome','technical','budget','error','status','official','final')):
        d=e['data']
        print(json.dumps({'seq':e['seq'],'kind':e['kind'],'sha256':e['sha256'],'data_keys':list(d) if isinstance(d,dict) else type(d).__name__,'data':d if len(json.dumps(d))<3000 else '[large]'}, ensure_ascii=False))
