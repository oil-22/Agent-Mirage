"""Resume unfinished configurations after source-reviewed controls, once only."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.5-vwa-resume.json';assert not out.exists(),'Inspect current formal worker'
old=json.loads((r/'v3.9.3-vwa-resume.json').read_text());dev=json.loads((r/'v3.9.5-staging.json').read_text());saved=json.loads((r/'v3.9.4-failure-preservation.json').read_text(encoding='utf8'));review=json.loads((r/'v3.9.5-development-review.json').read_text(encoding='utf8'))
assert review['allow_online']and review['scope']=='Nonblind development acceptance, not independent Mirage labels or efficacy'
code=r'''
import pathlib,json,hashlib,time,subprocess,os,fcntl,urllib.request
root=pathlib.Path(OLD['root']);release=pathlib.Path(DEV['release']);source=pathlib.Path(SAVED['source'])
gate=(root/'factual-resume.lock').open('a');fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
receipt=root/'v3.9.5-resume-manifest.json';assert not receipt.exists()
state=json.loads((root/'status.json').read_text());assert state['phase']=='technical_failure'and state['attempt']==str(source)
assert not pathlib.Path('/proc',str(state['pid'])).exists()and not pathlib.Path('/proc',str(DEV['pid'])).exists()
batch=(root/'batch.lock').open('a');fcntl.flock(batch,fcntl.LOCK_EX|fcntl.LOCK_NB)
summary=pathlib.Path(DEV['root'])/'summary.json';raw=summary.read_bytes();v=json.loads(raw)
assert v['phase']=='completed'and v['passed']and hashlib.sha256(raw).hexdigest()==REVIEW['summary_sha256']
assert len(v['results'])==4 and all(x['passed']and x['full_public_inputs_unchanged']for x in v['results'])
assert REVIEW['exact_history_indices']==[21,23]and REVIEW['pure_wait_preserved']and REVIEW['negative_controls_rejected']
for n,h in DEV['bindings'].items():assert hashlib.sha256((release/n).read_bytes()).hexdigest()==h
prior=pathlib.Path(OLD['release'])
for n in ['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py','inference_server.py']:
 assert(release/n).read_bytes()==(prior/n).read_bytes(),n
assert(source/'technical-failure.json').exists()and not(source/'complete.json').exists()
assert hashlib.sha256((source/'events.jsonl').read_bytes()).hexdigest()==SAVED['sha256']['events.jsonl']
assert len(list((root/'runs').glob('*/complete.json')))==10
for m in SAVED['completed']:
 p=root/'runs'/m['run_id']/'complete.json';ptr=json.loads(p.read_text());assert ptr['attempt']==m['attempt']and ptr['sha256']==m['sha256']
 assert hashlib.sha256((pathlib.Path(ptr['attempt'])/'complete.json').read_bytes()).hexdigest()==m['sha256']
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(root.parent/'transport.token').read_text().strip()});health=json.load(urllib.request.urlopen(req,timeout=10));assert health['phase']=='ready'and not health['actor_grammar']
preserve=pathlib.Path(SAVED['preservation']);(preserve/'v3.9.5-development-review.json').write_text(json.dumps(REVIEW,indent=2));(preserve/'v3.9.5-model-controls.json').write_bytes(raw)
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=root/('resume-v3.9.5-'+str(time.time_ns())+'.log');priority=['vwa--classifieds_112--blank_replace--post_only']
fcntl.flock(batch,fcntl.LOCK_UN);batch.close()
with log.open('xb')as f:p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(root.parent/'transport.token'),'--priority-runs',*priority],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'time':time.time(),'bindings':DEV['bindings'],'previous_failed_attempt':str(source),'failure_preservation':str(preserve),'completed_results_skipped':SAVED['completed'],'priority_runs':priority,'review':REVIEW,'completed_before_resume':10,'remaining_configurations':10,'scope':'Only unfinished configurations in new attempts. Ten completed old outcomes retain actual version labels, including the blocked/official0 result. Native actor/model/images/fullhistory/seed/injections/50steps/budgets/scoring unchanged.'}
with receipt.open('x')as f:json.dump(result,f,indent=2)
print(json.dumps(result))
'''
code='OLD='+repr(old)+'\nDEV='+repr(dev)+'\nSAVED='+repr(saved)+'\nREVIEW='+repr(review)+'\n'+code
d=json.loads(remote(code,host='4090'));out.write_text(json.dumps(d,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in d.items()if k not in {'bindings','review','completed_results_skipped'}}))
