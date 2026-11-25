"""Read-only compact development progress, retaining the complete raw summary."""
import json,sys
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
for name in ['v3.1-state-repair','v3.1-completion-negative','v3.2-state-repair','v3.2-completion-negative','v3.3-state-repair','v3.4-state-repair']:
    if len(sys.argv)>1 and not any(part in name for part in sys.argv[1:]):continue
    path=r/(name+'-launch.json')
    if not path.exists():continue
    launch=json.loads(path.read_text())
    code='''import pathlib,json
r=pathlib.Path(ROOT);s=r/'summary.json';rounds=r/'rounds.json';log=pathlib.Path(LOG)
events=r/'repair/events.jsonl';texts=[]
if events.exists():
 for line in events.read_text().splitlines():
  e=json.loads(line)
  if e['kind']=='candidate':texts.append(e['data']['text'])
print(json.dumps({'running':pathlib.Path('/proc/'+str(PID)).exists(),'summary':json.loads(s.read_text())if s.exists()else None,'rounds':json.loads(rounds.read_text())if rounds.exists()else None,'candidates':texts,'log_tail':log.read_text()[-1000:]if not s.exists()else None}))
'''.replace('ROOT',repr(launch['root'])).replace('PID',str(launch['pid'])).replace('LOG',repr(launch['log']))
    data=json.loads(remote(code,host='4090'))
    (r/(name+'-progress.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    summary=data['summary'];short={'name':name,'running':data['running'],'passed':summary.get('passed')if summary else None,'candidates':data['candidates']}
    if summary:
        short['actor_equivalence']=summary.get('actor_equivalence',{}).get('same_output_text')
        rows=summary.get('rounds',[{'result':summary.get('result',{})}])
        short['verdicts']=[{'passed':row.get('passed'),'action':row['result'].get('action'),'claims':[{k:c[k]for k in ['text','kind','status','reason']}for c in row['result'].get('claims',[])]}for row in rows]
    else:short['log_tail']=data['log_tail']
    print(json.dumps(short,ensure_ascii=False))
