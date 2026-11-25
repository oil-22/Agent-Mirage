"""Bind the independently audited repair to one new original-budget GUI attempt."""
import ast,hashlib,json,re,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'price-history-fullgui-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'fullgui-ready-current.json').exists()
diagnostic=read(BASE/'price-history-repair-development/completed-current.json')
assert diagnostic['worker_exited']and diagnostic['source_review_complete']and diagnostic['fullgui_candidate_eligible']
assert sha((Path(diagnostic['directory'])/'review.json').read_bytes())==diagnostic['review_sha256']
stage=read(P/'fullgui-staging-current.json');out=Path(stage['directory']);release=Path(stage['release'])
for n,h in read(out/'release-sha256.json').items():assert sha((release/n).read_bytes())==h,n
oldready=read(BASE/'focus-conflict-fullgui-development/fullgui-ready-current.json');oldproposal=read(Path(oldready['proposal']));old=Path(oldproposal['release'])
defs=lambda p:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a,b=defs(old/'defense/core.py'),defs(release/'defense/core.py');assert set(a)==set(b)and[k for k in a if a[k]!=b[k]]==['Controller']
for n in ['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py']:
    assert(old/n).read_bytes()==(release/n).read_bytes(),n
cpu=read(out/'cpu-results.json');remote_cpu=read(out/'environment-evidence/remote-cpu-tests.json')
counts=lambda rows:[int(re.search(r'Ran (\d+) tests',r['stderr']).group(1))for r in rows]
assert all(r['returncode']==0 for r in cpu+remote_cpu)and counts(cpu)==counts(remote_cpu)==[122,132]
env=read(out/'environment-receipt.json');assert env['child_exited']and env['model_calls']==0 and env['status']['phase']=='environment_preflight_complete'
proposal={**oldproposal,'version':'evidence-v4.0.4-dev-price-history-binding-20261029','status':'USER_AUTHORIZED_ITERATIVE_REPAIR',
 'release':str(release),'remote_release':stage['remote_preparation_root']+'/release','release_manifest_sha256':stage['release_manifest_sha256'],
 'condition_changes':oldproposal['condition_changes']+['Supplemental internal equal-price/minimum reason consistency after original validator; retain original result and use original single format retry','For non-WAIT outputs with concrete past-price language, read every original delivered frame for separate item-price rows without candidate or narrative, freeze SHA, compare factual price-object assertions in isolated text relation; never certify appearance or minimum from that relation'],
 'tradeoff':'Additional independent reading and relation calls consume the original 140-verifier cap. Readers and conservative routing can still fail or falsely block. Narrow textual routing can miss paraphrases; a nontrigger is not approval. Appearance/coverage remains under existing checks. No original input/model/action/parser/budget changes and no supplied minimum answer.',
 'residuals':['Known-task selected development only, no general efficacy or first-trigger reduction claim','Tiny cheaper-card clothing remains unresolved unless independently readable evidence establishes it','Price relation compatible does not establish global minimum/current action/task completion','Pure authored WAIT only, no new natural WAIT/loading-positive proof'],
 'completed_preparation':{'local_CPU_tests':254,'remote_CPU_tests':254,'fresh_logged_in_environment_preflight':True,'same_live_recapture':True,'environment_worker_exited':True,'model_calls':0},
 'decision_scope':'one-new-scoped-joint-stale-fullgui','launcher':str(BASE/'launch_price_history_fullgui.py'),
 'remote_active_must_not_exist':'price-history-fullgui-active-20261029.json','parent_diagnostic_review_sha256':diagnostic['review_sha256'],
 'human_decision_required':'Current direct human instruction 继续修复，直到能防御成功为止 authorizes this concrete linked repair and validation iteration, with unchanged original limits.'}
(out/'fullgui-proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding='utf-8')
ready={**oldready,'directory':str(out),'proposal':str(out/'fullgui-proposal.json'),'proposal_sha256':sha((out/'fullgui-proposal.json').read_bytes()),'release_manifest_sha256':stage['release_manifest_sha256'],'status':'USER_AUTHORIZED_PENDING_FRESH_LAUNCH_CHECK','launcher_sha256':sha((BASE/'launch_price_history_fullgui.py').read_bytes()),'preparation_seal_sha256':None,'report':None,'report_sha256':None,'fullGUI_started':False,'new_model_calls':0}
decision={'approved':True,'proposal_sha256':ready['proposal_sha256'],'scope':'one-new-scoped-joint-stale-fullgui','user_authorization_text':'继续修复，直到能防御成功为止','authorization_context':'Direct current human iterative repair instruction, original budgets. Preserve all older terminals and decisions.','time':time.time()}
(P/'user-launch-decision.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'preparation-seal.json').write_text(json.dumps({str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'__pycache__'not in str(p)},indent=2))
ready['preparation_seal_sha256']=sha((out/'preparation-seal.json').read_bytes());(P/'fullgui-ready-current.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'proposal_sha256':ready['proposal_sha256'],'local_CPU_tests':254,'remote_CPU_tests':254,'authorized':True,'new_model_calls':0}))
