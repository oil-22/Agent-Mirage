"""New defense-version batch, retaining the completed native baseline by hash.

Requires actual-model developer checks AND explicit offline evidence review.
Failed v2/v3 development outcomes and completed v2 blocked outcome are retained.
"""
import json,argparse
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;receipt=r/'v3-vwa-launch.json'
ap=argparse.ArgumentParser();ap.add_argument('--positive-version',default='v3.4');a=ap.parse_args()
assert not receipt.exists(),'Inspect existing version batch; never duplicate'
stage=json.loads((r/'v2-staging.json').read_text());old=json.loads((r/'v2.9-vwa-resume.json').read_text())
positive=json.loads((r/(a.positive_version+'-state-repair-launch.json')).read_text());negative=json.loads((r/'v3.2-completion-negative-launch.json').read_text())
review=json.loads((r/(a.positive_version+'-development-review.json')).read_text())
assert review['allow_online']and review['scope']=='development acceptance only, not independent Mirage labels or statistical efficacy'
code='''import pathlib,json,hashlib,time,os,subprocess,fcntl,urllib.request,ast
base=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');old=pathlib.Path(OLD);release=pathlib.Path(RELEASE)
state=json.loads((old/'status.json').read_text());assert state['phase']=='paused_at_decision_boundary'
assert not pathlib.Path('/proc/'+str(state['pid'])).exists()
with(old/'batch.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in ['defense/core.py','defense/prompts.py','defense/schema.py','defense/qwen_backend.py','defense/http_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json']}
checks=[]
def negative_core_binding(path):
 tree=ast.parse(path.read_text())
 tree.body=[n for n in tree.body if not(isinstance(n,ast.FunctionDef)and n.name in {'pending_claim_patch','correction_message'})and not(isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='DEFENSE_VERSION'for t in n.targets))]
 return ast.dump(tree,include_attributes=False)
for index,launch in enumerate([POSITIVE,NEGATIVE]):
 assert not pathlib.Path('/proc/'+str(launch['pid'])).exists()
 path=pathlib.Path(launch['root'])/'summary.json';summary=json.loads(path.read_text())
 assert summary['phase']=='completed'and summary['passed'],summary
 assert hashlib.sha256(path.read_bytes()).hexdigest()==REVIEW['positive_summary_sha256'if index==0 else'negative_summary_sha256'],'Reviewed summary changed'
 for name,sha in bindings.items():
  tested=pathlib.Path(launch['release'])/name
  if index==1 and name=='defense/core.py':
   assert negative_core_binding(release/name)==negative_core_binding(tested),'Core differs beyond unused state-feedback helpers/version in negative-only control'
  else:assert hashlib.sha256(tested.read_bytes()).hexdigest()==sha,name
 checks.append({'root':launch['root'],'summary_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'passed':True,'binding':'exact files; negative core AST also permits changed feedback helpers not invoked by this control'if index else'exact files'})
prior_release=pathlib.Path(PRIORRELEASE)
for name in ['native-vwa-request.json','plan80.json','defense/qwen_backend.py']:
 assert (release/name).read_bytes()==(prior_release/name).read_bytes(),name
assert (release/'run_vwa_pilot.py').read_text().replace(',full_completion_history=True','')==(prior_release/'run_vwa_pilot.py').read_text(),'Runner differs beyond the declared verifier-only history flag'
native=BASELINE;attempt=pathlib.Path(native['attempt']);marker=attempt.parent/'complete.json'
bound=json.loads(marker.read_text());assert bound['attempt']==str(attempt)and bound['sha256']==native['sha256']
raw=(attempt/'complete.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==native['sha256']
done=json.loads(raw);assert done['run']['arm']=='baseline'and done['outcome']=='model_stop'
assert not list(base.glob('vwa-v3-*/launch.json')),'A v3 launch already exists'
preserve=base/('v3-formal-preservation-'+str(time.time_ns()));preserve.mkdir()
files=[old/'status.json']+list((old/'runs').glob('*/complete.json'))+[pathlib.Path(POSITIVE['root'])/'summary.json',pathlib.Path(NEGATIVE['root'])/'summary.json']
(preserve/'hashes.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in files},indent=2))
for i,p in enumerate(files):(preserve/(str(i)+'-'+p.name)).write_bytes(p.read_bytes())
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(base/'transport.token').read_text().strip()})
health=json.loads(urllib.request.urlopen(req,timeout=10).read());assert health['phase']=='ready'and health['actor_grammar']is False
root=base/('vwa-v3-'+str(time.time_ns()));run=root/'runs'/done['run']['run_id'];run.mkdir(parents=True)
(run/'complete.json').write_bytes(marker.read_bytes())
reuse={'source_batch':str(old),'run_id':done['run']['run_id'],'attempt':str(attempt),'sha256':native['sha256'],'reason':'unchanged native actor, task, input protocol, seed, processing, budgets and grading; completed result retained without rerun'}
(root/'reused-native-baseline.json').write_text(json.dumps(reuse,indent=2))
(root/'development-review.json').write_text(json.dumps(REVIEW,ensure_ascii=False,indent=2))
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
log=root/'worker.log'
with log.open('xb')as stream:
 p=subprocess.Popen(['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(base/'transport.token')],cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
result={'pid':p.pid,'root':str(root),'release':str(release),'log':str(log),'time':time.time(),'developer_checks':checks,'bindings':bindings,'completed_baseline_reused':reuse,'preservation':str(preserve),'expected_configurations':20,'new_runs_expected':19,'scope':'one fixed task x five conditions x four arms, version-separated engineering pilot; not 20 independent tasks or statistical efficacy; old blocked outcomes retained'}
(root/'launch.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('PRIORRELEASE',repr(old['release'])).replace('RELEASE',repr(stage['release'])).replace('OLD',repr(old['root'])).replace('POSITIVE',repr(positive)).replace('NEGATIVE',repr(negative)).replace('BASELINE',repr(old['completed_runs_reused'][0])).replace('REVIEW',repr(review))
compile(code,'launch-v3-formal','exec')
result=json.loads(remote(code,host='4090'));receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
