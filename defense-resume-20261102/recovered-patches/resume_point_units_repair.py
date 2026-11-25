"""Resume six unfinished configurations once; keep all fourteen terminal outcomes."""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.9.6-vwa-resume.json';assert not out.exists(),'Inspect existing formal launch'
old=json.loads((r/'v3.9.5-site-recovery-resume.json').read_text());dev=json.loads((r/'v3.9.6-staging.json').read_text());saved=json.loads((r/'v3.9.6-failure-preservation.json').read_text(encoding='utf8'));review=json.loads((r/'v3.9.6-development-review.json').read_text(encoding='utf8'))
assert review['allow_online']and review['scope']=='Nonblind development acceptance, not independent Mirage labels or efficacy'
code=r'''
import pathlib,json,time,hashlib,subprocess,fcntl,urllib.request,os
root=pathlib.Path(OLD['root']);release=pathlib.Path(DEV['release']);source=pathlib.Path(SAVED['source'])
gate=(root/'point-units-resume.lock').open('a');fcntl.flock(gate,fcntl.LOCK_EX|fcntl.LOCK_NB)
receipt=root/'v3.9.6-resume-manifest.json';assert not receipt.exists()
s=json.loads((root/'status.json').read_text());assert s['phase']=='technical_failure'and s['attempt']==str(source)
assert not pathlib.Path('/proc',str(s['pid'])).exists()and not pathlib.Path('/proc',str(DEV['pid'])).exists()
batch=(root/'batch.lock').open('a');fcntl.flock(batch,fcntl.LOCK_EX|fcntl.LOCK_NB)
raw=pathlib.Path(DEV['root'],'summary.json').read_bytes();summary=json.loads(raw)
assert summary['phase']=='completed'and summary['passed']and len(summary['results'])==7
assert all(x['passed']for x in summary['results'])and hashlib.sha256(raw).hexdigest()==REVIEW['summary_sha256']
assert summary['results'][0]['exact_public_and_query_unchanged']and REVIEW['engineering_tests']==116
for n,h in DEV['bindings'].items():assert hashlib.sha256((release/n).read_bytes()).hexdigest()==h
assert(source/'technical-failure.json').exists()and not(source/'complete.json').exists()
assert hashlib.sha256((source/'events.jsonl').read_bytes()).hexdigest()==SAVED['sha256']['events.jsonl']
assert len(list((root/'runs').glob('*/complete.json')))==14
for v in SAVED['completed']:
 p=root/'runs'/v['run_id']/'complete.json';ptr=json.loads(p.read_text());assert ptr['attempt']==v['attempt']and ptr['sha256']==v['sha256']
 assert hashlib.sha256(pathlib.Path(ptr['attempt'],'complete.json').read_bytes()).hexdigest()==v['sha256']
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(root.parent/'transport.token').read_text().strip()});health=json.load(urllib.request.urlopen(req,timeout=10));assert health['phase']=='ready'and not health['actor_grammar']
with urllib.request.urlopen('http://192.0.2.10:29980/index.php?page=login',timeout=15)as site:assert site.status==200
preserve=pathlib.Path(SAVED['preservation']);(preserve/'v3.9.6-development-review.json').write_text(json.dumps(REVIEW,indent=2));(preserve/'v3.9.6-model-controls.json').write_bytes(raw)
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=root/('resume-v3.9.6-'+str(time.time_ns())+'.log');priority=['vwa--classifieds_112--stale_replace--joint']
fcntl.flock(batch,fcntl.LOCK_UN);batch.close()
with log.open('xb')as f:p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(root.parent/'transport.token'),'--priority-runs',*priority],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'time':time.time(),'bindings':DEV['bindings'],'previous_failed_attempt':str(source),'failure_preservation':str(preserve),'completed_results_skipped':SAVED['completed'],'priority_runs':priority,'review':REVIEW,'completed_before_resume':14,'remaining_configurations':6,'scope':'Only unfinished configurations in new linked attempts. All14 terminal outcomes retained including both blocked/official0. Only point coordinate prompt changed; actor/images/history/seed/injections/50steps/call budgets/precision/scoring unchanged.'}
with receipt.open('x')as f:json.dump(result,f,indent=2)
print(json.dumps(result))
'''
d=json.loads(remote('OLD='+repr(old)+'\nDEV='+repr(dev)+'\nSAVED='+repr(saved)+'\nREVIEW='+repr(review)+'\n'+code,host='4090'));out.write_text(json.dumps(d,indent=2));print(json.dumps({k:v for k,v in d.items()if k not in {'bindings','review','completed_results_skipped'}}))
