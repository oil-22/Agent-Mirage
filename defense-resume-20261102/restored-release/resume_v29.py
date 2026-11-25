"""Resume unfinished formal runs after target-alignment regression passes.

Retains the completed, byte-bound native baseline and all paused old attempts.
No new task, seed, injection, actor condition, budget or scoring rule is used.
"""
import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
assert not(r/'v2.9-vwa-resume.json').exists(),'Inspect existing resume; do not duplicate'
formal=json.loads((r/'v2-vwa-launch.json').read_text())
staged=json.loads((r/'v2-staging.json').read_text())
delta=json.loads((r/'v2.9-alignment-replay-launch.json').read_text())
code=r'''
import fcntl,hashlib,json,os,pathlib,subprocess,time,urllib.request
root=pathlib.Path(ROOT);release=pathlib.Path(RELEASE);previous=pathlib.Path(PREVIOUS);delta=pathlib.Path(DELTA)
assert not(root/'v2.9-resume-manifest.json').exists(),'Resume already dispatched'
state=json.loads((root/'status.json').read_text())
assert state['phase']=='paused_at_decision_boundary',state
assert not pathlib.Path('/proc/'+str(state['pid'])).exists(),'Old worker still exists'
with(root/'batch.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
summary=json.loads((delta/'summary.json').read_text());rows=json.loads((delta/'results.json').read_text())
assert summary['phase']=='completed'and summary['cases']==7 and summary['passed'],summary
assert len(rows)==7 and all(x['passed']for x in rows)
validated=pathlib.Path(VALIDATED)
bindings={name:hashlib.sha256((release/name).read_bytes()).hexdigest()for name in
    ['defense/core.py','defense/prompts.py','defense/schema.py','defense/qwen_backend.py','target_alignment_replay.py','run_vwa_pilot.py']}
assert all((release/n).read_bytes()==(validated/n).read_bytes()for n in bindings),'Changed since delta'
for name in ['native-vwa-request.json','plan80.json','defense/schema.py','defense/qwen_backend.py']:
    assert(release/name).read_bytes()==(previous/name).read_bytes(),name
completed=[]
for p in(root/'runs').glob('*/complete.json'):
    marker=json.loads(p.read_text());attempt=pathlib.Path(marker['attempt']);raw=(attempt/'complete.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==marker['sha256']
    done=json.loads(raw);assert done['run']['arm']=='baseline','Unexpected completed defense; inspect manually'
    completed.append({'run_id':done['run']['run_id'],'attempt':str(attempt),'sha256':marker['sha256'],
                      'reuse_reason':'Native baseline path and all actor/plan conditions unchanged; do not rerun completed rounds'})
assert len(completed)==1
token=(root.parent/'transport.token').read_text().strip()
request=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+token})
health=json.loads(urllib.request.urlopen(request,timeout=10).read());assert health['phase']=='ready'and health['actor_grammar']is False
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=root/('resume-v2.9-'+str(time.time_ns())+'.log')
with log.open('xb')as out:
    child=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),
       '--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(root.parent/'transport.token')],
       cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
receipt={'pid':child.pid,'root':str(root),'release':str(release),'log':str(log),'time':time.time(),
    'prior_paused_attempt':state['attempt'],'prior_version':state['defense_version'],
    'reason':'Repair observed same-kind wrong-target leak; paused old attempt retained separately',
    'completed_runs_reused':completed,'new_defense_runs_expected':19,
    'algorithm_version':'evidence-v2.9-target-alignment-20261025',
    'delta_acceptance':summary,'validated_defense_sha256':bindings,
    'plan_sha256':hashlib.sha256((release/'plan80.json').read_bytes()).hexdigest(),
    'scope':'Same original20 grid, skip existing baseline; new attempts for unfinished runs; not 20 fresh runs or a statistical effectiveness result'}
with(root/'v2.9-resume-manifest.json').open('x')as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
'''.replace('ROOT',repr(formal['root'])).replace('RELEASE',repr(staged['release'])).replace('PREVIOUS',repr(formal['release'])).replace('DELTA',repr(delta['root'])).replace('VALIDATED',repr(delta['release']))
result=json.loads(remote(code,host='4090'))
(r/'v2.9-vwa-resume.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
