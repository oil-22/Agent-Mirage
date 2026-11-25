"""Read-only live diagnostic inspection, with immutable evidence copy on exit."""
import json,subprocess
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
receipt=next(r/n for n in ['v3.9.7-controller-live-launch.json','v3.9.7-sourcefix-launch.json']if(r/n).exists())
launch=json.loads(receipt.read_bytes())['live']
code='LAUNCH='+repr(launch)+'\n'+r'''
import pathlib,json,time,hashlib,pwd,collections
root=pathlib.Path(LAUNCH['root']);proc=pathlib.Path('/proc',str(LAUNCH['pid']))
def read(name):return json.loads((root/name).read_bytes())if(root/name).exists()else None
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()}
events=[]
ep=root/'events/events.jsonl'
if ep.exists():
 for line in ep.read_text().splitlines():
  try:events.append(json.loads(line))
  except json.JSONDecodeError:pass
counts=collections.Counter(e['kind']for e in events)
print(json.dumps({'time':time.time(),'process':{'owner':pwd.getpwuid(proc.stat().st_uid).pw_name,'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()}if proc.exists()else None,'status':read('status.json'),'summary':read('summary.json'),'failure':read('failure.json'),'counts':dict(counts),'recent_candidates':[e['data']for e in events if e['kind']=='candidate'][-2:],'last_event_kind':events[-1]['kind']if events else None,'last_event_age':time.time()-events[-1]['time']if events else None,'files_sha256':files,'log_tail':pathlib.Path(LAUNCH['log']).read_text()[-2500:]}))
'''
record=json.loads(remote(code,host='4090',timeout=45))
(r/'v3.9.7-live-progress.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
if not record['process']:
    dest=r/'scroll-live-evidence'/Path(launch['root']).name
    if not dest.exists():
        dest.parent.mkdir(exist_ok=True)
        subprocess.run(['D:/Git/usr/bin/scp.exe','-F','C:/Users/researcher/.ssh/config','-r','4090:'+launch['root'],str(dest.parent)],check=True,capture_output=True)
        subprocess.run(['D:/Git/usr/bin/scp.exe','-F','C:/Users/researcher/.ssh/config','4090:'+launch['log'],str(dest/'worker.log')],check=True,capture_output=True)
    record['local_copy']=str(dest)
print(json.dumps({k:v for k,v in record.items()if k not in ['files_sha256','summary']},ensure_ascii=True))
if record['summary']:print(json.dumps({k:v for k,v in record['summary'].items()if k not in ['model_calls','verdict']},ensure_ascii=True))
