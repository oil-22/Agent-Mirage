"""Record new-attempt provenance and read real execution evidence after resume."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;launch=json.loads((r/'v3.9.6-vwa-resume.json').read_text())
code=r'''
import pathlib,json,hashlib,time,collections
root=pathlib.Path(X['root']);s=json.loads((root/'status.json').read_text());p=pathlib.Path(s['attempt'])
assert s['pid']==X['pid']and s['run']==X['priority_runs'][0]and str(p)!=X['previous_failed_attempt']
events=[json.loads(l)for l in(p/'events.jsonl').read_text().splitlines()]
assert events[0]['data']['code_directory']==X['release']
link={'previous_failed_attempt':X['previous_failed_attempt'],'failure_preservation':X['failure_preservation'],'new_attempt':str(p),'resume_receipt':str(root/'v3.9.6-resume-manifest.json'),'completed_before_resume':14,'completed_result_policy':'Preserve/skip all14, including both blocked outcomes; only unfinished failure retried.'}
sidecar=p/'retry-origin.json'
if not sidecar.exists():
 with sidecar.open('x')as f:json.dump(link,f,indent=2)
else:assert json.loads(sidecar.read_text())==link
for v in X['completed_results_skipped']:
 ptr=json.loads((root/'runs'/v['run_id']/'complete.json').read_text());assert ptr['attempt']==v['attempt']and ptr['sha256']==v['sha256']
 assert hashlib.sha256(pathlib.Path(ptr['attempt'],'complete.json').read_bytes()).hexdigest()==v['sha256']
counts=collections.Counter(e['kind']for e in events)
print(json.dumps({'time':time.time(),'state':s,'link':link,'counts':dict(counts),'events_sha256':hashlib.sha256((p/'events.jsonl').read_bytes()).hexdigest(),'events':events,'all14_completed_SHA_unchanged':True}))
'''
d=json.loads(remote('X='+repr(launch)+'\n'+code,host='4090'));(r/'v3.9.6-online-resume-evidence.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in d.items()if k!='events'},ensure_ascii=True))
