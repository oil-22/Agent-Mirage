import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;x=json.loads((r/'v3.9.7-scroll-validation-launch.json').read_bytes())
code='LAUNCH='+repr(x)+'\n'+r'''
import pathlib,json,time,hashlib,shutil
root=pathlib.Path(LAUNCH['root']);state=json.loads((root/'status.json').read_bytes());p=pathlib.Path(state['attempt']);events=[json.loads(x)for x in(p/'events.jsonl').read_text().splitlines()]
tail=[]
for e in events[-18:]:
 d=e['data'];row={'seq':e['seq'],'kind':e['kind']}
 if e['kind']=='verifier_request':row.update(phase=d['phase'],candidate=d.get('candidate'),system=d['system'],observation=d['public']['observation_id'],images=d['public']['images'])
 elif e['kind']in ['verifier_raw','verifier_format_failure','candidate','decision_blocked']:row['data']=d
 tail.append(row)
print(json.dumps({'time':time.time(),'launch':LAUNCH,'state':state,'attempt':str(p),'tail':tail,'last_calls':json.loads((p/'technical-failure.json').read_bytes())['calls'][-5:]}))
'''
record=json.loads(remote(code,host='4090',timeout=75));(r/'v3.9.7-point-failure-inspection.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in record.items()if k!='launch'},ensure_ascii=True))
