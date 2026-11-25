"""Inspect actual worker identity, locks and immutable event-chain prefix, no model calls."""
import hashlib,json,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-history-fullgui-development'
launch=json.loads((PREP/'fullgui-launch-current.json').read_bytes())
code=r'''
import collections,hashlib,json,os,time
from pathlib import Path
r=Path(LAUNCH['root']);p=Path('/proc')/str(LAUNCH['pid']);process=None
if p.exists():
 cmd=[x.decode()for x in(p/'cmdline').read_bytes().split(b'\0')if x]
 assert p.stat().st_uid==1015 and cmd==LAUNCH['command'],cmd
 held=[]
 for f in(p/'fdinfo').iterdir():
  try:
   info=f.read_text()
   if 'FLOCK'in info:held.append({'target':os.readlink(str(p/'fd'/f.name)),'fdinfo':info})
  except FileNotFoundError:pass
 assert all(any(x['target']==old['target']for x in held)for old in LAUNCH['held_locks'])
 process={'uid':1015,'command':cmd,'held_locks':held}
state=json.loads((r/'status.json').read_bytes())if(r/'status.json').exists()else{}
rows=[]
for attempt in sorted(r.glob('runs/*/attempt-*')):
 f=attempt/'events.jsonl';events=[];partial=False;previous='0'*64
 if f.exists():
  for line in f.read_text().splitlines():
   try:e=json.loads(line)
   except json.JSONDecodeError:partial=True;break
   data={k:v for k,v in e.items()if k!='sha256'}
   assert e['previous']==previous and e['seq']==len(events)
   assert hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==e['sha256']
   events.append(e);previous=e['sha256']
 counts=collections.Counter(e['kind']for e in events)
 terminal={n:json.loads((attempt/n).read_bytes())for n in ['complete.json','technical-failure.json','failure.json']if(attempt/n).exists()}
 rows.append({'attempt':str(attempt),'event_count':len(events),'chain_head':previous,'complete_prefix_chain_verified':True,'partial_last_line':partial,'counts':dict(counts),'last_event':{'kind':events[-1]['kind'],'time':events[-1]['time']}if events else None,'terminal':terminal})
failures={f.name:json.loads(f.read_bytes())for f in r.glob('*failure.json')}
print(json.dumps({'time':time.time(),'root':str(r),'process':process,'status':state,'rows':rows,'failures':failures,'log_sha256':hashlib.sha256((r/'worker.log').read_bytes()).hexdigest(),'log_tail':(r/'worker.log').read_text()[-1200:]}))
'''
row=json.loads(remote('LAUNCH='+repr(launch)+'\n'+code,host='4090',timeout=40))
out=PREP/('inspection-'+str(time.time_ns())+'.json');out.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
pointer={'receipt':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'root':row['root'],'actual_worker_verified':row['process']is not None,'status':row['status'],'attempts':[{k:v for k,v in r.items()if k!='terminal'}for r in row['rows']],'terminal':row['process']is None,'failures':row['failures']}
(PREP/'inspection-current.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(pointer))
