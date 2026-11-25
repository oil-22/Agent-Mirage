"""Read completed inference receipts only; no requests, tokens or auth are exposed."""
import json,csv
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;receipt=json.loads((here/'v10-service-launch.json').read_text())
code=r'''import pathlib,json,time,collections
root=pathlib.Path(ROOT);ns={};exec((pathlib.Path(RELEASE)/'defense/prompts.py').read_text(),ns)
rows=[]
for path in(root/'requests').iterdir():
 if not(path/'response.json').exists():continue
 request=json.loads((path/'request.json').read_text());response=json.loads((path/'response.json').read_text())
 phase='actor'
 if request['operation']=='judge':
  system=request['system'];phase=next((name.lower()for name in ['HISTORY_REPORT','COMPLETION_RELATION','COMPLETION','POINT','ALIGN','SCREEN','VERIFY']if system.startswith(ns[name])),'other_verifier')
  if phase=='screen'and 'verify CURRENT visible input focus before typing'in system:phase='focus'
 rows.append({'request':path.name,'phase':phase,'input_tokens':response['input_tokens'],'output_tokens':response['output_tokens'],'seconds':response['seconds']})
groups={}
for row in rows:
 g=groups.setdefault(row['phase'],{'calls':0,'seconds':0,'output_tokens':0});g['calls']+=1;g['seconds']+=row['seconds'];g['output_tokens']+=row['output_tokens']
for g in groups.values():g['mean_seconds']=round(g['seconds']/g['calls'],1)
print(json.dumps({'time':time.time(),'service':str(root),'groups':groups,'completed_receipts':rows,'scope':'Completed service receipts across development and formal calls; not whole-task completion or speedup estimate'}))
'''.replace('ROOT',repr(receipt['root'])).replace('RELEASE',repr(receipt['release']))
data=json.loads(remote(code));(here/'latest-runtime-cost.json').write_text(json.dumps(data,indent=2))
print(json.dumps({'groups':data['groups'],'scope':data['scope']}))
