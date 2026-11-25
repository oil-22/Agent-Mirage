"""Record linked attempt with actual native action, not just a launch receipt."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.8-online-resume-evidence.json';assert not out.exists()
x=json.loads((r/'v3.9.8-scroll-validation-resume.json').read_bytes())
code=r'''
import pathlib,json,hashlib,time,collections
root=pathlib.Path(X['root']);s=json.loads((root/'status.json').read_bytes());p=pathlib.Path(s['attempt'])
assert s['pid']==X['pid']and s['run']==X['only_runs'][0]and str(p)!=X['previous_failed_attempt']
raw=(p/'events.jsonl').read_bytes();events=[json.loads(l)for l in raw.splitlines()]
assert events[0]['data']['code_directory']==X['release']
counts=collections.Counter(e['kind']for e in events);assert counts['action_executed']>=1 and counts['candidate']>=1 and not(p/'technical-failure.json').exists()
link={'previous_failed_attempt':X['previous_failed_attempt'],'failure_preservation':X['failure_preservation'],'new_attempt':str(p),'resume_receipt':str(root/'v3.9.8-resume-manifest.json'),'completed_before_resume':0,'completed_result_policy':'Original20 are separate completed immutable outcomes, never restarted. Only2 unfinished scroll validations continued.'}
sidecar=p/'retry-origin.json'
if not sidecar.exists():
 with sidecar.open('x')as f:json.dump(link,f,indent=2)
else:assert json.loads(sidecar.read_bytes())==link
originals=json.loads((root/'original-20-completed-pointers.json').read_bytes())
for v in originals:
 marker=pathlib.Path(X['source_root'])/'runs'/v['run']/'complete.json'
 assert hashlib.sha256(marker.read_bytes()).hexdigest()==v['pointer_sha256']and hashlib.sha256(pathlib.Path(v['attempt'],'complete.json').read_bytes()).hexdigest()==v['sha256']
record={'time':time.time(),'state':s,'link':link,'counts':dict(counts),'events_sha256':hashlib.sha256(raw).hexdigest(),'events':events,'all20_completed_SHA_unchanged':True,'scope':'Actual early online execution after source-bound development controls; not original-step20 replay, two-run completion or efficacy.'}
snapshot=root/'resume-evidence'/('pixel-'+str(time.time_ns()));snapshot.mkdir(parents=True);(snapshot/'events.jsonl').write_bytes(raw);(snapshot/'snapshot.json').write_text(json.dumps(record,indent=2));record['remote_snapshot']=str(snapshot)
print(json.dumps(record))
'''
d=json.loads(remote('X='+repr(x)+'\n'+code,host='4090'));out.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in d.items()if k!='events'}))
