"""Read the independent four-step diagnostic, never a formal completion count."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;r=json.loads((here/'v3.8.3-baseline-diagnostic-launch.json').read_text())
code=r'''import pathlib,json,time,hashlib
root=pathlib.Path(ROOT);state=json.loads((root/'status.json').read_text());runs=[]
for attempt in(root/'runs').glob('*/attempt-*'):
 p=attempt/'events.jsonl';events=[json.loads(l)for l in p.read_text().splitlines()]
 candidates=[e for e in events if e['kind']=='candidate'];marker=attempt/'complete.json'
 runs.append({'attempt':str(attempt),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'candidates':candidates,'injections':[e for e in events if e['kind']=='private_delivery_ledger'and e['data']['fired']],'complete':json.loads(marker.read_text())if marker.exists()else None,'failures':[str(p)for p in attempt.glob('*failure.json')]})
print(json.dumps({'time':time.time(),'status':state,'runs':runs,'log_tail':pathlib.Path(LOG).read_text()[-1200:],'diagnostic_only':True}))
'''.replace('ROOT',repr(r['root'])).replace('LOG',repr(r['log']))
data=json.loads(remote(code,host='4090'));(here/'v3.8.3-baseline-diagnostic-progress.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(data))
