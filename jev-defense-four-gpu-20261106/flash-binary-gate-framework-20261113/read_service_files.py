import json
from manage import remote,REMOTE
code=r'''
import json,sys
from pathlib import Path
r=Path(ROOT);sys.path.insert(0,str(r))
from resource_guard import identity
v={}
for n in ['service/process.json','service/loaded.json','service/ready.json','service/failure.json','service/terminal.json','launcher-failure.json','launcher-exit.json','integration-preflight/terminal.json','integration-preflight/failure.json','integration-launch.json']:
 p=r/n
 if p.is_file():
  v[n]=json.loads(p.read_bytes())
  if 'pid'in v[n]:
   try:v[n+' actual']=identity(v[n]['pid'])
   except FileNotFoundError:v[n+' actual']={'exists':False}
for n in ['service.log','integration-preflight.log']:
 if(r/n).exists():v[n]=(r/n).read_text()[-6000:]
v['requests']=[{'id':p.name,'files':[f.name for f in p.iterdir()if f.is_file()]}for p in (r/'service/requests').iterdir()]if(r/'service/requests').exists()else[]
print(json.dumps(v))
'''.replace('ROOT',repr(REMOTE))
raw,d=remote(code,'read-service-files');print(json.dumps({'data':json.loads(raw),'evidence':str(d)}))
