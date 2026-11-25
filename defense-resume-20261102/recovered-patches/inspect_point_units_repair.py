"""Read-only development evidence download, including every raw per-control event."""
import base64,json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;x=json.loads((r/'v3.9.6-staging.json').read_text())
code=r'''
import pathlib,json,base64,time
root=pathlib.Path(X['root']);summary=root/'summary.json'
files={str(p.relative_to(root)):base64.b64encode(p.read_bytes()).decode()for p in root.rglob('*')if p.is_file()and p.suffix=='.json' or p.is_file()and p.name=='events.jsonl'}
print(json.dumps({'pid_alive':pathlib.Path('/proc',str(X['pid'])).exists(),'status':json.loads((root/'status.json').read_text())if(root/'status.json').exists()else None,'summary':json.loads(summary.read_text())if summary.exists()else None,'files':files,'log_tail':pathlib.Path(X['log']).read_text()[-1500:]}))
'''
d=json.loads(remote('X='+repr(x)+'\n'+code,host='4090'));folder=r/'point-units-development-evidence';folder.mkdir(exist_ok=True)
for n,b in d.pop('files').items():
 p=folder/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(b))
(r/'v3.9.6-development-progress.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
print(json.dumps({'pid_alive':d['pid_alive'],'status':d['status'],'results':[{'case':v['case'],'passed':v['passed'],'calls':v['verifier_calls'],'verdict':v.get('verdict'),'error':v.get('error')}for v in(d['summary']['results']if d['summary']else [])],'log_tail':d['log_tail']},ensure_ascii=True))
