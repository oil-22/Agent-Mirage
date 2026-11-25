import json
from manage import remote,REMOTE
code=r'''
import json,sys
from pathlib import Path
r=Path(ROOT);sys.path.insert(0,str(r))
from resource_guard import identity
v={}
if(r/'audit-runtime.log').exists():v['log']=(r/'audit-runtime.log').read_text()[-6000:]
if(r/'audit-launch.json').exists():
 p=json.loads((r/'audit-launch.json').read_bytes())['pid']
 try:v['actual_process']=identity(p)
 except FileNotFoundError:v['actual_process']={'pid':p,'exists':False}
v['audit_results']=[]
for p in sorted(r.glob('audits/*/audit.json')):
 result=json.loads(p.read_bytes());v['audit_results'].append({'path':str(p),'status':result['status'],'verified_calls':result['new_Flash_calls_verified'],'journal':result['journal'],'dtype_elements':result['actual_dtype_elements'],'requests':result['requests']})
print(json.dumps(v))
'''.replace('ROOT',repr(REMOTE))
raw,op=remote(code,'read-audit-status');print(json.dumps({'data':json.loads(raw),'evidence':str(op)}))
