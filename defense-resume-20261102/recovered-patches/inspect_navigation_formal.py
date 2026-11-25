"""Read actual new attempt/process/evidence; never confuse preserved failed attempt."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=next(r/n for n in ['v3.9.6-vwa-resume.json','v3.9.5-site-recovery-resume.json','v3.9.5-vwa-resume.json','v3.9.3-vwa-resume.json']if(r/n).exists());x=json.loads(receipt.read_text())
code=r'''
import pathlib,json,time,hashlib,pwd,collections
root=pathlib.Path(ROOT);s=json.loads((root/'status.json').read_text());proc=pathlib.Path('/proc',str(PID));p=pathlib.Path(s['attempt'])if s.get('attempt')else None
cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()if proc.exists()else None
if cmd:assert RELEASE in cmd and str(root)in cmd
events=[]
if p and(p/'events.jsonl').exists():
 for line in(p/'events.jsonl').read_text().splitlines():
  try:events.append(json.loads(line))
  except json.JSONDecodeError:pass
counts=collections.Counter(e['kind']for e in events)
completed=[]
for m in(root/'runs').glob('*/complete.json'):
 pointer=json.loads(m.read_text());assert hashlib.sha256((pathlib.Path(pointer['attempt'])/'complete.json').read_bytes()).hexdigest()==pointer['sha256'];completed.append(m.parent.name)
print(json.dumps({'time':time.time(),'state':s,'worker_alive':proc.exists(),'worker_owner':pwd.getpwuid(proc.stat().st_uid).pw_name if proc.exists()else None,'worker_cmdline':cmd,'actual_completed':len(completed),'counts':{k:counts[k]for k in ['candidate','action_executed','verifier_request','verifier_raw','verifier_format_failure','state_invalidated','recapture_requested']},'last_event_kind':events[-1]['kind']if events else None,'event_age_seconds':time.time()-events[-1]['time']if events else None,'technical_failure':bool(p and((p/'failure.json').exists()or(p/'technical-failure.json').exists())),'implementation':events[0]['data']if events and events[0]['kind']=='implementation'else None,'log_tail':pathlib.Path(LOG).read_text()[-1200:]}))
'''.replace('ROOT',repr(x['root'])).replace('PID',str(x['pid'])).replace('RELEASE',repr(x['release'])).replace('LOG',repr(x['log']))
d=json.loads(remote(code,host='4090'));(r/'latest-navigation-formal-progress.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');(r/(receipt.stem.replace('-vwa-resume','')+'-formal-progress.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in d.items()if k not in {'implementation','worker_cmdline','log_tail'}},ensure_ascii=True))
