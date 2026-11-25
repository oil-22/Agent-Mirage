import json
from control import remote,R3090,R4090,OUT
for host,root in [('3090',OUT),('4090',R4090)]:
 code=r'''
import json
from pathlib import Path
r=Path(ROOT);v={}
for n in ['primary/status.json','primary/terminal.json','primary/failure.json','batch/status.json','GUI-uncaught-failure.json','control/exit.json']:
 if(r/n).exists():v[n]=json.loads((r/n).read_bytes())
for n in ['control/runner.log','background/outer.log']:
 if(r/n).exists():v[n]=(r/n).read_text()[-1600:]
if(r/'primary/requests').exists():v['sealed_main_replies']=len(list((r/'primary/requests').glob('*/seal.json')))
events=list((r/'batch/runs').glob('*/attempt-*/controller/events.jsonl'))
if events:
 p=max(events,key=lambda x:x.stat().st_mtime_ns);v['current_controller']=str(p);v['latest_events']=[json.loads(s)for s in p.read_text().splitlines()[-3:]]
print(json.dumps(v))
'''.replace('ROOT',repr(root))
 out,op=remote(host,code,'inspect-actual-activity-'+host);print(json.dumps({'host':host,'data':json.loads(out),'evidence':str(op)}))
