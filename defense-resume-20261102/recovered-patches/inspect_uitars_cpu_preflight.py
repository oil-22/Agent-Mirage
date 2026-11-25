"""Inspect existing isolated CPU preflight; never starts or restarts work."""
import hashlib,json,time
from pathlib import Path
from remote import remote
base=Path(__file__).resolve().parent/'uitars-verifier-preparation';p=base/'cpu-preflight-launch.json'
if not p.exists():
 d=json.loads(remote("import pathlib;print(pathlib.Path('/data/researcher/mirage-defense-pilot-20261023/uitars-cpu-preflight-active.json').read_text())",host='4090',timeout=30))
 p.write_text(json.dumps(d,indent=2),encoding='utf8')
launch=json.loads(p.read_bytes())
code=r'''
import pathlib,json,hashlib,time
root=pathlib.Path(L['root']);p=pathlib.Path('/proc')/str(L['pid']);process=None
if p.exists():process={'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().split(b'\0')[:-1]};process['command']=[v.decode()for v in process['command']];assert process['uid']==L['uid']and process['command']==L['command']
result=root/'cpu-result.json';progress=root/'cpu-progress.json';log=root/'cpu.log'
print(json.dumps({'time':time.time(),'root':str(root),'process':process,'completed':result.exists(),'result':json.loads(result.read_bytes())if result.exists()else None,'result_sha256':hashlib.sha256(result.read_bytes()).hexdigest()if result.exists()else None,'progress':json.loads(progress.read_bytes())if progress.exists()else[],'log_tail':log.read_text(errors='replace')[-6000:]if log.exists()else None,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()if log.exists()else None}))
'''
data=json.loads(remote('L='+repr(launch)+'\n'+code,host='4090',timeout=40));dest=base/('cpu-inspection-'+str(time.time_ns())+'.json')
dest.write_text(json.dumps(data,indent=2),encoding='utf8')
(base/'cpu-preflight-current.json').write_text(json.dumps({'inspection':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'completed':data['completed'],'root':data['root']},indent=2),encoding='utf8')
if data['result']:print(json.dumps({k:v for k,v in data['result'].items()if k!='rows'}));print(json.dumps(data['result']['rows']))
else:print(json.dumps({k:v for k,v in data.items()if k!='progress'}))
