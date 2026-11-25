"""Preserve failed attempt and its actual inference receipts before any repair."""
import json
from pathlib import Path
from remote import remote

r=Path(__file__).resolve().parent
out=r/'v3.9.1-failure-preservation.json'
assert not out.exists(), 'Inspect existing preservation instead of duplicating it'
old=json.loads((r/'v3.9-vwa-launch.json').read_text(encoding='utf8'))
code=r'''
import pathlib,json,hashlib,shutil,time
root=pathlib.Path(ROOT);s=json.loads((root/'status.json').read_text())
assert s['phase']=='technical_failure' and s['run']=='vwa--classifieds_112--silent_drop--post_only'
assert not pathlib.Path('/proc',str(s['pid'])).exists()
p=pathlib.Path(s['attempt']);assert not (p/'complete.json').exists()
failure=json.loads((p/'technical-failure.json').read_text())
assert failure['blocked_reason']=='candidate_verifier_error:Candidate alone cannot ground a GUI action'
dest=root/'preservation'/('navigation-citation-'+str(time.time_ns()));dest.mkdir(parents=True)
shutil.copytree(p,dest/'failed-attempt')
for n in ['status.json','worker.log']:shutil.copy2(root/n,dest/n)
hashes={str(x.relative_to(p)):hashlib.sha256(x.read_bytes()).hexdigest() for x in p.rglob('*') if x.is_file()}
assert all(hashlib.sha256((dest/'failed-attempt'/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
(dest/'failed-attempt-sha256.json').write_text(json.dumps(hashes,indent=2))
completed=[]
for m in (root/'runs').glob('*/complete.json'):
 v=json.loads(m.read_text());q=pathlib.Path(v['attempt'])/'complete.json';assert hashlib.sha256(q.read_bytes()).hexdigest()==v['sha256']
 completed.append({'run_id':m.parent.name,**v})
assert len(completed)==9
(dest/'completed-outcomes.json').write_text(json.dumps(completed,indent=2))
events=[json.loads(x) for x in(p/'events.jsonl').read_text().splitlines()]
req=next(x for x in reversed(events) if x['kind']=='verifier_request' and x['data']['phase']=='verify' and x['data']['format_retry']==0)
print(json.dumps({'source':str(p),'preservation':str(dest),'sha256':hashes,'completed':completed,
 'failure_request_seq':req['seq'],'failure_public_sha256':hashlib.sha256(json.dumps(req['data']['public'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
 'proposal':req['data']['proposal'],'candidate':req['data']['candidate'],'service_receipts':[x['receipt'] for x in failure['calls'][-2:]]}))
'''.replace('ROOT',repr(old['root']))
d=json.loads(remote(code,host='4090'))
code=r'''
import pathlib,json,shutil,time,hashlib
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023');dest=base/('navigation-failure-preservation-'+str(time.time_ns()));dest.mkdir()
hashes={}
for s in RECEIPTS:
 p=pathlib.Path(s);assert p.parent.parent.parent==base and p.parent.name=='requests'
 target=dest/p.name;shutil.copytree(p,target)
 for x in p.rglob('*'):
  if x.is_file():
   n=str(x.relative_to(p));h=hashlib.sha256(x.read_bytes()).hexdigest();assert hashlib.sha256((target/n).read_bytes()).hexdigest()==h;hashes[p.name+'/'+n]=h
(dest/'sha256.json').write_text(json.dumps(hashes,indent=2))
print(json.dumps({'preservation':str(dest),'sha256':hashes}))
'''.replace('RECEIPTS',repr(d['service_receipts']))
d['inference_preservation']=json.loads(remote(code,host='3090'))
out.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in d.items()if k not in {'sha256','completed','inference_preservation'}},ensure_ascii=True))
