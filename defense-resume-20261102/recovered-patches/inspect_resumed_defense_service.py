"""Read-only identity, actual held locks, health and request evidence; no model calls."""
import hashlib,json,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent
def inspect():
    launch=json.loads((BASE/'defense-service-resume-current.json').read_bytes())
    code=r'''
import hashlib,json,os,urllib.request
from pathlib import Path
root=Path(LAUNCH['root']);p=Path('/proc')/str(LAUNCH['pid'])
assert p.exists() and p.stat().st_uid==1033
command=(p/'cmdline').read_bytes().split(b'\0');command=[s.decode() for s in command if s]
assert command==LAUNCH['command'],command
held=[]
for f in (p/'fdinfo').iterdir():
 text=f.read_text()
 if 'FLOCK' in text:held.append({'target':os.readlink(str(p/'fd'/f.name)),'fdinfo':text})
assert any(x['target']==str(root/'service.lock') for x in held)
for gpu in LAUNCH['gpus']:
 assert any(x['target'].endswith('/qwen27-gpu%d.lock'%gpu) for x in held),gpu
requests=[]
for q in sorted((root/'requests').glob('*')):
 if q.is_dir():requests.append({'root':str(q),'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in q.iterdir() if f.is_file()}})
pending=[r for r in requests if 'response.json'not in r['sha256']and 'failure.json'not in r['sha256']]
if pending:
 health={'phase':'authenticated_health_deferred_during_serial_inference','pending_requests':[r['root']for r in pending],'not_a_fresh_HTTP_health_confirmation':True}
else:
 token=Path('/home/researcher/mirage-defense-pilot-20261023/transport.token').read_text().strip()
 request=urllib.request.Request('http://127.0.0.1:18127',headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(request,timeout=10) as response:health=json.load(response)
 assert health['phase']=='ready' and health['dtype']=='BF16' and health['backend']=='sdpa'
print(json.dumps({'root':str(root),'uid':p.stat().st_uid,'command':command,'held_locks':held,'health':health,'status':json.loads((root/'status.json').read_bytes()),'requests':requests,'root_file_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in root.iterdir() if f.is_file()}}))
'''
    row=json.loads(remote('LAUNCH='+repr(launch)+'\n'+code,host='3090',timeout=40))
    out=BASE/('defense-service-resumed-evidence-'+str(time.time_ns())+'.json')
    out.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    pointer={'receipt':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'root':row['root'],'uid_verified':1033,'held_gpu_locks':5,'health':row['health'],'requests':len(row['requests'])}
    (BASE/'defense-service-resumed-health-current.json').write_text(json.dumps(pointer,indent=2))
    return pointer
if __name__=='__main__':print(json.dumps(inspect()))
