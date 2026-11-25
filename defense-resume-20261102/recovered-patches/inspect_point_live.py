"""Read-only diagnostic and immutable evidence copy after worker exit."""
import json,subprocess
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;launch=json.loads((r/'v3.9.9-controller-live-launch.json').read_bytes())
code=r'''
import pathlib,json,pwd,time,hashlib,collections
root=pathlib.Path(X['root']);proc=pathlib.Path('/proc',str(X['pid']))
process=None
if proc.exists():
 process={'uid':proc.stat().st_uid,'owner':pwd.getpwuid(proc.stat().st_uid).pw_name,'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()};assert process['uid']==1015 and X['release']in process['command']and X['root']in process['command']
def read(n):return json.loads((root/n).read_bytes())if(root/n).exists()else None
events=[json.loads(l)for l in(root/'events/events.jsonl').read_text().splitlines()]if(root/'events/events.jsonl').exists()else[]
print(json.dumps({'time':time.time(),'process':process,'status':read('status.json'),'summary':read('summary.json'),'failure':read('failure.json'),'counts':dict(collections.Counter(e['kind']for e in events)),'candidates':[e['data']for e in events if e['kind']=='candidate'],'recovery_events':[e['data']for e in events if e['kind']=='point_evidence_unavailable'],'source_initialization':[e['data']for e in events if e['kind']=='source_initialized_decision'],'last_event_age_seconds':time.time()-events[-1]['time']if events else None,'sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()},'log_tail':pathlib.Path(X['log']).read_text()[-1800:]}))
'''
d=json.loads(remote('X='+repr(launch)+'\n'+code,host='4090',timeout=45));(r/'v3.9.9-live-progress.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
if not d['process']:
 dest=r/'point-live-evidence'/Path(launch['root']).name
 if not dest.exists():
  dest.parent.mkdir(exist_ok=True);subprocess.run(['D:/Git/usr/bin/scp.exe','-F','C:/Users/researcher/.ssh/config','-r','4090:'+launch['root'],str(dest.parent)],check=True,capture_output=True)
  subprocess.run(['D:/Git/usr/bin/scp.exe','-F','C:/Users/researcher/.ssh/config','4090:'+launch['log'],str(dest/'worker.log')],check=True,capture_output=True)
print(json.dumps({k:v for k,v in d.items()if k not in ['sha256','summary']},ensure_ascii=True))
if d['summary']:print(json.dumps({k:v for k,v in d['summary'].items()if k!='model_calls'},ensure_ascii=True))
