"""Preserve the failed stale/joint attempt before any repair, including raw receipts."""
import base64,json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.6-failure-preservation.json'
if out.exists():
 print('Already preserved: '+str(out));raise SystemExit
old=json.loads((r/'v3.9.5-site-recovery-resume.json').read_text())
code=r'''
import pathlib,json,time,hashlib,shutil,base64
root=pathlib.Path(OLD['root']);s=json.loads((root/'status.json').read_text());p=pathlib.Path(s['attempt'])
assert s['phase']=='technical_failure'and not pathlib.Path('/proc',str(s['pid'])).exists()
assert s['run']=='vwa--classifieds_112--stale_replace--joint'and not(p/'complete.json').exists()
dest=root/'preservation'/('stale-joint-citation-'+str(time.time_ns()));dest.mkdir(parents=True)
shutil.copytree(p,dest/'failed-attempt')
for q in [root/'status.json',pathlib.Path(OLD['log'])]:shutil.copy2(q,dest/q.name)
shutil.copytree(OLD['release'],dest/'failed-release',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
hashes={str(q.relative_to(p)):hashlib.sha256(q.read_bytes()).hexdigest()for q in p.rglob('*')if q.is_file()}
assert all(hashlib.sha256((dest/'failed-attempt'/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
(dest/'failed-attempt-sha256.json').write_text(json.dumps(hashes,indent=2))
done=[]
for m in sorted((root/'runs').glob('*/complete.json')):
 v=json.loads(m.read_text());assert hashlib.sha256((pathlib.Path(v['attempt'])/'complete.json').read_bytes()).hexdigest()==v['sha256'];done.append({'run_id':m.parent.name,**v})
assert len(done)==14
(dest/'completed-outcomes.json').write_text(json.dumps(done,indent=2))
events=[json.loads(l)for l in(p/'events.jsonl').read_text().splitlines()]
req=next(e for e in reversed(events)if e['kind']=='verifier_request'and e['data']['format_retry']==0)
replies=[e for e in events if e['seq']>req['seq']and e['kind']in ['verifier_raw','verifier_format_failure','decision_blocked']]
failure=json.loads((p/'technical-failure.json').read_text())
print(json.dumps({'state':s,'source':str(p),'preservation':str(dest),'sha256':hashes,'completed':done,'request':req,'replies':replies,'failure':failure,'service_receipts':[x['receipt']for x in failure['calls'][-2:]],'images':[{'name':i['sha256']+'.png','role':i['role'],'raw':base64.b64encode((p/(i['sha256']+'.image')).read_bytes()).decode()}for i in req['data']['public']['images']]}))
'''
d=json.loads(remote('OLD='+repr(old)+'\n'+code,host='4090'));dest=r/'stale-joint-failure-evidence';dest.mkdir(exist_ok=True)
for i in d.pop('images'):(dest/i['name']).write_bytes(base64.b64decode(i['raw']))
code=r'''
import pathlib,json,shutil,time,hashlib
base=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023');dest=base/('stale-joint-citation-failure-'+str(time.time_ns()));dest.mkdir()
hashes={}
for s in RECEIPTS:
 p=pathlib.Path(s);assert p.parent.parent.parent==base and p.parent.name=='requests';shutil.copytree(p,dest/p.name)
 for q in p.rglob('*'):
  if q.is_file():
   n=p.name+'/'+str(q.relative_to(p));h=hashlib.sha256(q.read_bytes()).hexdigest();assert hashlib.sha256((dest/n).read_bytes()).hexdigest()==h;hashes[n]=h
(dest/'sha256.json').write_text(json.dumps(hashes,indent=2));print(json.dumps({'preservation':str(dest),'sha256':hashes}))
'''
d['inference_preservation']=json.loads(remote('RECEIPTS='+repr(d['service_receipts'])+'\n'+code,host='3090'))
out.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'source':d['source'],'preservation':d['preservation'],'phase':d['request']['data']['phase'],'candidate':d['request']['data'].get('candidate'),'proposal':d['request']['data'].get('proposal'),'replies':d['replies'],'failure_reason':d['failure'].get('blocked_reason'),'images':[x.name for x in dest.glob('*.png')]},ensure_ascii=True))
