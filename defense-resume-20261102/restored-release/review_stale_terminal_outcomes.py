"""Read preserved complete stale outcomes; no retries or changes to final labels."""
import base64,json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=json.loads((r/'v3.9.6-vwa-resume.json').read_text())
code=r'''
import pathlib,json,hashlib,base64,time
root=pathlib.Path(ROOT);rows=[]
for arm in ['joint','post_only']:
 run=root/'runs'/('vwa--classifieds_112--stale_replace--'+arm);ptr=json.loads((run/'complete.json').read_text());p=pathlib.Path(ptr['attempt'])
 raw=(p/'complete.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==ptr['sha256'];complete=json.loads(raw)
 es=[json.loads(l)for l in(p/'events.jsonl').read_text().splitlines()]
 candidates=[e for e in es if e['kind']=='candidate'];verdicts=[e for e in es if e['kind']=='verdict']
 req=next(e for e in reversed(es)if e['kind']=='verifier_request'and e['data']['phase']=='verify')
 im=next(i for i in req['data']['public']['images']if i['role']=='current')
 image=(p/(im['sha256']+'.image')).read_bytes();assert hashlib.sha256(image).hexdigest()==im['sha256']
 rows.append({'arm':arm,'attempt':str(p),'sha256':ptr['sha256'],'complete':complete,'last_candidates':candidates[-3:],'last_verdicts':verdicts[-3:],'last_point_crosschecks':[e for e in es if e['kind']=='point_crosscheck'][-3:],'last_alignments':[e for e in es if e['kind']=='target_alignment'][-3:],'final_block':es[-1],'image_sha256':im['sha256'],'image':base64.b64encode(image).decode(),'full_events_sha256':hashlib.sha256((p/'events.jsonl').read_bytes()).hexdigest()})
print(json.dumps({'time':time.time(),'rows':rows}))
'''
d=json.loads(remote(code.replace('ROOT',repr(receipt['root'])),host='4090'));folder=r/'stale-terminal-reviews';folder.mkdir(exist_ok=True)
for row in d['rows']:(folder/(row['arm']+'-current.png')).write_bytes(base64.b64decode(row.pop('image')))
(folder/'evidence.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
print(json.dumps([{'arm':row['arm'],'outcome':row['complete']['outcome'],'blocked_reason':row['complete']['blocked_reason'],'last_candidates':row['last_candidates'],'last_verdict':row['last_verdicts'][-1],'last_alignment':row['last_alignments'][-1]if row['last_alignments']else None}for row in d['rows']],ensure_ascii=True))
