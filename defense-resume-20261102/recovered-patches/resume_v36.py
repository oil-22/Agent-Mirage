"""Resume unfinished formal configurations only after reviewed actual-model controls."""
import json,argparse
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--version',choices=['v3.6','v3.6.1','v3.6.2'],default='v3.6');a=ap.parse_args()
receipt=r/(a.version+'-vwa-resume.json');assert not receipt.exists()
old=json.loads((r/'v3.4.1-vwa-resume.json').read_text());probe=json.loads((r/(a.version+'-probe-launch.json')).read_text())
negative=json.loads((r/'v3.5-negative-launch.json').read_text());review=json.loads((r/(a.version+'-development-review.json')).read_text(encoding='utf-8'))
assert review['allow_online']and review['scope']=='development acceptance only, not independent Mirage labels or statistical efficacy'
code=r'''
import pathlib,json,hashlib,time,os,subprocess,fcntl,urllib.request
root=pathlib.Path(ROOT);release=pathlib.Path(RELEASE);prior=pathlib.Path(PRIOR)
assert not(root/'v3.6-resume-manifest.json').exists()
state=json.loads((root/'status.json').read_text());assert state['phase']=='technical_failure'
assert state['pid']==OLDPID and not pathlib.Path('/proc/'+str(state['pid'])).exists()
with(root/'batch.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
for launch,key in [(PROBE,'probe_summary_sha256'),(NEGATIVE,'negative_summary_sha256')]:
 assert not pathlib.Path('/proc/'+str(launch['pid'])).exists(),'Development request still running'
 path=pathlib.Path(launch['root'])/'summary.json';raw=path.read_bytes();data=json.loads(raw)
 assert data['phase']=='completed'and data['passed']
 assert hashlib.sha256(raw).hexdigest()==REVIEW[key]
for n in ['defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','native-vwa-request.json','plan80.json']:
 assert(release/n).read_bytes()==(prior/n).read_bytes(),n
assert(release/'run_vwa_pilot.py').read_text().replace(',probe_completion=True','')==(prior/'run_vwa_pilot.py').read_text()
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in ['defense/core.py','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json']}
assert all(bindings[n]==sha for n,sha in REVIEW['formal_bindings'].items())
attempt=pathlib.Path(state['attempt']);assert not(attempt/'complete.json').exists()
failure=json.loads((attempt/'technical-failure.json').read_text());assert failure['technical_status']=='verifier_failure'
completed=[]
for marker in(root/'runs').glob('*/complete.json'):
 pointer=json.loads(marker.read_text());p=pathlib.Path(pointer['attempt'])/'complete.json';raw=p.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==pointer['sha256']
 completed.append({'run_id':marker.parent.name,'attempt':pointer['attempt'],'sha256':pointer['sha256']})
assert len(completed)==1 and completed[0]['run_id']=='vwa--classifieds_112--clean--baseline'
preserve=root/'preservation'/('v36-resume-'+str(time.time_ns()));preserve.mkdir(parents=True)
paths=[root/'status.json',attempt/'events.jsonl',attempt/'technical-failure.json',attempt/'final-actually-captured.png',attempt/'browser_trace.zip',pathlib.Path(OLDLOG)]
hashes={}
for i,p in enumerate(paths):
 raw=p.read_bytes();hashes[str(p)]=hashlib.sha256(raw).hexdigest();(preserve/(str(i)+'-'+p.name)).write_bytes(raw)
(preserve/'hashes.json').write_text(json.dumps(hashes,indent=2))
(preserve/'review.json').write_text(json.dumps(REVIEW,indent=2))
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(root.parent/'transport.token').read_text().strip()})
health=json.loads(urllib.request.urlopen(req,timeout=10).read());assert health['phase']=='ready'and health['actor_grammar']is False
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=root/('resume-v3.6-'+str(time.time_ns())+'.log')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(root.parent/'transport.token')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'time':time.time(),'preservation':str(preserve),'previous_failed_attempt':str(attempt),'completed_results_skipped':completed,'bindings':bindings,'review':REVIEW,'scope':'new defense algorithm, new attempt for unfinished technical round, original outcomes retained; no statistical efficacy claim','changes':'independent image-only completion evidence and frozen scope comparison, original actor/main full history and original 140/70 call caps retained'}
with(root/'v3.6-resume-manifest.json').open('x')as f:json.dump(result,f,indent=2)
print(json.dumps(result))
'''.replace('ROOT',repr(old['root'])).replace('RELEASE',repr(probe['release'])).replace('PRIOR',repr(old['release'])).replace('OLDPID',repr(old['pid'])).replace('OLDLOG',repr(old['log'])).replace('PROBE',repr(probe)).replace('NEGATIVE',repr(negative)).replace('REVIEW',repr(review))
code=code.replace('v3.6-resume-manifest.json',a.version+'-resume-manifest.json').replace('v36-resume-',a.version+'-resume-').replace('resume-v3.6-', 'resume-'+a.version+'-')
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
