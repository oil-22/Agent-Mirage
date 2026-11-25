"""Resume unfinished formal configurations with explicit reviewed development bindings."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;output=here/'v3.8.1-vwa-resume.json';assert not output.exists()
old=json.loads((here/'v3.6.2-vwa-resume.json').read_text());dev=json.loads((here/'v3.8.1-history-launch.json').read_text())
review=json.loads((here/'v3.8.1-development-review.json').read_text(encoding='utf-8'))
service=json.loads((here/'v9-service-launch.json').read_text());capacity=json.loads((here/'v9-capacity-replay-launch.json').read_text())
assert review['allow_online']and review['scope']=='development acceptance only, not independent Mirage labels or statistical efficacy'
assert 'Ran 96 tests' in (here/'checks-v3.8.1.txt').read_text()
cap=json.loads(remote('import pathlib,json,hashlib\np=pathlib.Path('+repr(capacity['root'])+')/"summary.json"\nprint(json.dumps({"summary":json.loads(p.read_text()),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}))',host='3090'))
assert cap['summary']['passed']and cap['sha256']==review['capacity_summary_sha256']
code=r'''import pathlib,json,hashlib,ast,time,subprocess,os,fcntl,urllib.request
root=pathlib.Path(ROOT);release=pathlib.Path(RELEASE);prior=pathlib.Path(PRIOR);review=REVIEW
state=json.loads((root/'status.json').read_text());assert state['phase']=='technical_failure'and state['pid']==OLDPID
for pid in [OLDPID,DEVPID]:
 proc=pathlib.Path('/proc')/str(pid);assert not proc.exists()or(proc/'stat').read_text().split()[2]=='Z'
with(root/'batch.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not(root/'v3.8.1-resume-manifest.json').exists()
summary=pathlib.Path(DEVROOT)/'summary.json';assert hashlib.sha256(summary.read_bytes()).hexdigest()==review['development_summary_sha256']
data=json.loads(summary.read_text());assert data['phase']=='completed'and data['passed']
assert set(review['reviewed_cases'])=={x['case']for x in data['results']}
assert all(x['accepted']for x in review['reviewed_cases'].values())
for name in ['defense/http_backend.py','native-vwa-request.json','plan80.json','inference_server.py']:
 assert(release/name).read_bytes()==(prior/name).read_bytes(),name
before=(prior/'run_vwa_pilot.py').read_text();after=(release/'run_vwa_pilot.py').read_text()
assert after.replace(',probe_history_reports=True','')==before
def method(path,name):return next(ast.dump(n,include_attributes=False)for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,ast.FunctionDef)and n.name==name)
assert method(release/'defense/qwen_backend.py','generate')==method(prior/'defense/qwen_backend.py','generate')
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in ['defense/core.py','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json']}
assert bindings==review['formal_bindings']
attempt=pathlib.Path(state['attempt']);assert not(attempt/'complete.json').exists()
assert json.loads((attempt/'technical-failure.json').read_text())['technical_status']=='verifier_failure'
completed=[]
for marker in(root/'runs').glob('*/complete.json'):
 pointer=json.loads(marker.read_text());p=pathlib.Path(pointer['attempt'])/'complete.json';assert hashlib.sha256(p.read_bytes()).hexdigest()==pointer['sha256'];completed.append({'run_id':marker.parent.name,**pointer})
assert len(completed)==1 and completed[0]['run_id']=='vwa--classifieds_112--clean--baseline'
preserve=root/'preservation'/('v381-resume-'+str(time.time_ns()));preserve.mkdir()
hashes={}
for i,p in enumerate([root/'status.json',attempt/'events.jsonl',attempt/'technical-failure.json',attempt/'final-actually-captured.png',attempt/'browser_trace.zip',pathlib.Path(OLDLOG)]):
 raw=p.read_bytes();hashes[str(p)]=hashlib.sha256(raw).hexdigest();(preserve/(str(i)+'-'+p.name)).write_bytes(raw)
(preserve/'hashes.json').write_text(json.dumps(hashes,indent=2));(preserve/'review.json').write_text(json.dumps(review,indent=2))
health=json.load(urllib.request.urlopen(urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(root.parent/'transport.token').read_text().strip()}),timeout=10));assert health['phase']=='ready'and not health['actor_grammar']
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=root/('resume-v3.8.1-'+str(time.time_ns())+'.log')
with log.open('xb')as stream:p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(root.parent/'transport.token')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'time':time.time(),'previous_failed_attempt':str(attempt),'preservation':str(preserve),'completed_results_skipped':completed,'bindings':bindings,'review':review,'service':SERVICE,'scope':'Changed verifier algorithm; all failures retained; unfinished configurations use fresh attempts. One task20 configurations, no statistical efficacy claim.'}
with(root/'v3.8.1-resume-manifest.json').open('x')as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
'''.replace('ROOT',repr(old['root'])).replace('RELEASE',repr(dev['release'])).replace('PRIOR',repr(old['release'])).replace('REVIEW',repr(review)).replace('OLDPID',str(old['pid'])).replace('DEVPID',str(dev['pid'])).replace('DEVROOT',repr(dev['root'])).replace('OLDLOG',repr(old['log'])).replace('SERVICE',repr(service))
data=json.loads(remote(code,host='4090'));output.write_text(json.dumps(data,indent=2));print(json.dumps({k:v for k,v in data.items()if k not in {'review','bindings'}}))
