"""Manual compact factual check. Does not start, stop or relaunch anything."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
replay=json.loads((r/'v2-replay-launch.json').read_text())
code='''import pathlib,json,time
r=pathlib.Path(ROOT)
rows=json.loads((r/'results.json').read_text())if(r/'results.json').exists()else[]
out={'root':str(r),'rows':[{'category':x['category'],'protocol_valid':x['protocol_valid'],'screen':x.get('result',{}).get('status'),'action':x.get('result',{}).get('action',{}).get('status'),'point':x.get('point_probe',{}).get('kind'),'point_agrees':x.get('point_agrees'),'error':x.get('error','')[-350:]}for x in rows]}
out['summary']=json.loads((r/'summary.json').read_text())if(r/'summary.json').exists()else None
print(json.dumps(out))
'''.replace('ROOT',repr(replay['root']))
data=json.loads(remote(code,host='4090'));(r/'latest-repair-replay.json').write_text(json.dumps(data,indent=2));print(json.dumps(data,indent=2))
if(r/'v2-vwa-launch.json').exists():
 launch=json.loads((r/'v2-vwa-launch.json').read_text())
 code='''import sys,json
sys.path.insert(0,RELEASE)
from audit_vwa_v2 import audit
v=audit(ROOT)
print(json.dumps(v))
'''.replace('RELEASE',repr(launch['release'])).replace('ROOT',repr(launch['root']))
 data=json.loads(remote(code,host='4090'));(r/'latest-v2-live-audit.json').write_text(json.dumps(data,indent=2))
 print(json.dumps({k:v for k,v in data.items()if k!='rows'},indent=2))
 for row in data['rows'][-2:]:print(json.dumps(row))
