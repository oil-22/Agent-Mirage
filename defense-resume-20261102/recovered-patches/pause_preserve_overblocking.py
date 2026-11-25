"""Preserve actual semantic failures, then request this owned worker's safe pause."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent
out=here/'v3.8.3-overblocking-pause.json';assert not out.exists()
r=json.loads((here/'v3.8.3-vwa-resume.json').read_text())
code=r'''
import os,pathlib,json,time,hashlib,shutil,signal
root=pathlib.Path(ROOT);pid=PID;proc=pathlib.Path('/proc')/str(pid)
assert proc.stat().st_uid==os.getuid()
args=proc.joinpath('cmdline').read_bytes().split(b'\0')
assert str(root).encode()in args and (RELEASE+'/run_vwa_pilot.py').encode()in args
state=json.loads((root/'status.json').read_text());assert state['pid']==pid and state['phase']=='running'
dest=root/'preservation'/('overblocking-v383-'+str(time.time_ns()));dest.mkdir()
hashes={};blocked=[];completed=[]
def copy_file(p,target):
 raw=p.read_bytes();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 hashes[str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'copy':str(target),'size':len(raw)}
for marker in sorted((root/'runs').glob('*/complete.json')):
 pointer=json.loads(marker.read_text());attempt=pathlib.Path(pointer['attempt']);summary=attempt/'complete.json'
 assert hashlib.sha256(summary.read_bytes()).hexdigest()==pointer['sha256']
 result=json.loads(summary.read_text());completed.append({'run_id':marker.parent.name,**pointer})
 copy_file(marker,dest/'pointers'/marker.parent.name/'complete.json')
 if result['outcome']=='blocked'and result['blocked_reason']=='observation_not_confirmed':
  blocked.append(str(attempt))
  for p in attempt.rglob('*'):
   if p.is_file():copy_file(p,dest/'blocked'/marker.parent.name/p.relative_to(attempt))
assert len(blocked)>=3
copy_file(root/'status.json',dest/'pre-pause-status.json');copy_file(pathlib.Path(LOG),dest/'worker-pre-pause.log')
active=pathlib.Path(state['attempt'])
copy_file(active/'events.jsonl',dest/'active-event-prefix.jsonl')
(dest/'hashes.json').write_text(json.dumps(hashes,indent=2))
receipt={'root':str(root),'pid':pid,'preservation':str(dest),'completed':completed,'blocked_attempts':blocked,
 'active_attempt':str(active),'time':time.time(),'signal':'SIGUSR1','scope':'Decision-boundary pause; semantic blocked results preserved, never relabeled unfinished'}
(dest/'pause-request.json').write_text(json.dumps(receipt,indent=2))
os.kill(pid,signal.SIGUSR1)
print(json.dumps(receipt))
'''.replace('ROOT',repr(r['root'])).replace('PID',str(r['pid'])).replace('RELEASE',repr(r['release'])).replace('LOG',repr(r['log']))
data=json.loads(remote(code,host='4090',timeout=90));out.write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in data.items()if k!='completed'}))
