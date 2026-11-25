"""Resume unfinished runs after the reproduced reference-index safety repair.

Completed results are skipped. The paused 12-step attempt is kept intact.
Native task/model/seed/images/history/budgets/grading are unchanged.
"""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=r/'v3.4.1-vwa-resume.json'
assert not receipt.exists(),'Inspect existing continuation; never duplicate'
old=json.loads((r/'v3-vwa-launch.json').read_text());stage=json.loads((r/'v2-staging.json').read_text())
checks=(r/'checks-v3.4.1.txt').read_text();assert 'Ran 73 tests'in checks and checks.rstrip().endswith('OK')
code='''import pathlib,json,hashlib,fcntl,subprocess,os,time,urllib.request
root=pathlib.Path(ROOT);release=pathlib.Path(RELEASE);old=pathlib.Path(OLD)
state=json.loads((root/'status.json').read_text());assert state['phase']=='paused_at_decision_boundary',state
assert not pathlib.Path('/proc/'+str(state['pid'])).exists(),'Old worker still exists'
with(root/'batch.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not(root/'v3.4.1-resume-manifest.json').exists()
before=(old/'defense/core.py').read_text();after=(release/'defense/core.py').read_text()
normalized=after.replace("DEFENSE_VERSION='evidence-v3.4.1-reference-context-guard-20261025'","DEFENSE_VERSION='evidence-v3.4-neutral-evidence-repair-20261025'").replace("and e['image_index']<len(view.images)","")
assert normalized==before,'Unexpected algorithm change beyond the reviewed index guard/version'
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in ['defense/core.py','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json']}
for n in bindings:
 if n!='defense/core.py':assert(release/n).read_bytes()==(old/n).read_bytes(),n
attempt=pathlib.Path(state['attempt']);paused=json.loads((attempt/'paused.json').read_text())
assert paused['outcome']=='paused_at_decision_boundary'and paused['environment_actions']==12
assert not(attempt/'complete.json').exists(),'Completed outcome cannot be retried unchanged'
assert paused['actor_calls']==12 and paused['verifier_calls']==21
completed=[]
for marker in(root/'runs').glob('*/complete.json'):
 pointer=json.loads(marker.read_text());p=pathlib.Path(pointer['attempt'])/'complete.json';raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer['sha256']
 done=json.loads(raw);assert done['run']['arm']=='baseline'
 completed.append({'run_id':done['run']['run_id'],'attempt':pointer['attempt'],'sha256':pointer['sha256']})
assert len(completed)==1
preserve=root/'preservation'/('reference-index-final-'+str(time.time_ns()));preserve.mkdir(parents=True)
paths=[root/'status.json',attempt/'events.jsonl',attempt/'paused.json',attempt/'final-actually-captured.png',attempt/'browser_trace.zip',root/'worker.log']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
(preserve/'hashes.json').write_text(json.dumps(hashes,indent=2))
for i,p in enumerate(paths):(preserve/(str(i)+'-'+p.name)).write_bytes(p.read_bytes())
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(root.parent/'transport.token').read_text().strip()});health=json.loads(urllib.request.urlopen(req,timeout=10).read());assert health['phase']=='ready'and health['actor_grammar']is False
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=root/('resume-v3.4.1-'+str(time.time_ns())+'.log')
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(root.parent/'transport.token')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'time':time.time(),'preservation':str(preserve),'previous_paused_attempt':str(attempt),'previous_attempt_retried':False,'new_attempt_for_unfinished_round':True,'completed_results_skipped':completed,'bindings':bindings,'change':'Guard reference-only indices before looking in the current image tuple; version label; otherwise exact v3.4 bytes','checks':CHECKS,'scope':'unfinished engineering pilot continuation, not new independent tasks or proof of statistical efficacy; original paused attempt retained'}
with(root/'v3.4.1-resume-manifest.json').open('x')as f:json.dump(result,f,indent=2)
print(json.dumps(result))
'''.replace('ROOT',repr(old['root'])).replace('RELEASE',repr(stage['release'])).replace('OLD',repr(old['release'])).replace('CHECKS',repr(checks))
compile(code,'resume-v341','exec')
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
