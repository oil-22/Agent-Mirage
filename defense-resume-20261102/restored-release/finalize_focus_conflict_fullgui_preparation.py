"""Bind reviewed diagnostics, unchanged native conditions and current iteration authority."""
import ast,hashlib,json,re,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-fullgui-development'
sha=lambda b:hashlib.sha256(b).hexdigest();read=lambda p:json.loads(p.read_bytes())
assert not(PREP/'fullgui-ready-current.json').exists()
diagnostic=read(BASE/'focus-conflict-repair-development/completed-current.json')
assert diagnostic['worker_exited']and diagnostic['source_review_complete']
linked=read(BASE/'plan-present-report-repair-development/current.json');assert linked['fullgui_candidate_eligible']and linked['archived_full_validator_replay']and linked['new_model_calls']==0
review=Path(diagnostic['directory'])/'review.json';assert sha(review.read_bytes())==diagnostic['review_sha256']
stage=read(PREP/'fullgui-staging-current.json');out=Path(stage['directory']);release=Path(stage['release'])
for n,h in read(out/'release-sha256.json').items():assert sha((release/n).read_bytes())==h,n
oldready=read(BASE/'focus-history-fullgui-development/fullgui-ready-current.json');oldproposal=read(Path(oldready['proposal']));old=Path(oldproposal['release'])
defs=lambda p:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a,b=defs(old/'defense/core.py'),defs(release/'defense/core.py');assert set(a)==set(b)and[k for k in a if a[k]!=b[k]]==['Controller']
for n in ['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py']:
    assert(old/n).read_bytes()==(release/n).read_bytes(),n
cpu=read(out/'cpu-results.json');rcpu=read(out/'environment-evidence/remote-cpu-tests.json')
counts=lambda rows:[int(re.search(r'Ran (\d+) tests',r['stderr']).group(1))for r in rows]
assert all(r['returncode']==0 for r in cpu+rcpu)and counts(cpu)==counts(rcpu)==[122,105]
env=read(out/'environment-receipt.json');assert env['child_exited']and env['model_calls']==0 and env['status']['phase']=='environment_preflight_complete'
proposal={**oldproposal,'version':'evidence-v4.0.3b-dev-focus-plan-report-20261029','status':'USER_AUTHORIZED_ITERATIVE_REPAIR',
 'release':str(release),'remote_release':stage['remote_preparation_root']+'/release','release_manifest_sha256':stage['release_manifest_sha256'],
 'condition_changes':oldproposal['condition_changes']+['Independent focus read for explicit no-focus-cue assertions across non-WAIT actions; preserve disagreement during typing checks','Plan-only assistant citations cannot certify a completed-event report; original format retry, no action/verdict rewrite','Comparative rank-history fence includes first-in-price-order','Withdraw unsupported details everywhere in correction feedback; distinguish cheaper prices/ties without inventing coverage'],
 'tradeoff':'Additional blind focus checks and conservative source eligibility can falsely block and consume the unchanged original budgets. Regex checks are narrow and readers can still err. Price-order scope does not supply actual ordering, cheaper-item coverage or a minimum certificate. No forced action/STOP or relaxed strict validator.',
 'residuals':['Selected authored/source-bound diagnostics are not natural actor trajectories or general efficacy','Main judge still falsely supports focus absence in f01; independent disagreement withholds it','Independent focus reader not ground truth; target alignment and minimum evidence require actual GUI validation','Known-task development, no claim of first-trigger reduction or no candidate Mirage'],
 'completed_preparation':{'local_CPU_tests':227,'remote_CPU_tests':227,'fresh_logged_in_environment_preflight':True,'same_live_recapture':True,'environment_worker_exited':True,'model_calls':0},
 'decision_scope':'one-new-scoped-joint-stale-fullgui','launcher':str(BASE/'launch_focus_conflict_fullgui.py'),
 'remote_active_must_not_exist':'focus-conflict-fullgui-active-20261029.json','parent_diagnostic_review_sha256':diagnostic['review_sha256'],
 'human_decision_required':'Direct current instruction 继续修复，直到能防御成功为止 authorizes this concrete linked validation iteration. Preserve the older single-run authority and outcomes.'}
(out/'fullgui-proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding='utf-8')
ready={**oldready,'directory':str(out),'proposal':str(out/'fullgui-proposal.json'),'proposal_sha256':sha((out/'fullgui-proposal.json').read_bytes()),'release_manifest_sha256':stage['release_manifest_sha256'],'status':'USER_AUTHORIZED_PENDING_FRESH_LAUNCH_CHECK','launcher_sha256':sha((BASE/'launch_focus_conflict_fullgui.py').read_bytes()),'preparation_seal_sha256':None,'report':None,'report_sha256':None,'fullGUI_started':False,'new_model_calls':0}
decision={'approved':True,'proposal_sha256':ready['proposal_sha256'],'scope':'one-new-scoped-joint-stale-fullgui','user_authorization_text':'继续修复，直到能防御成功为止','authorization_context':'Direct current human request authorizes iterative repairs and separate validations with original budgets; this exact proposal uses one linked attempt. Old terminal/active receipts remain immutable.','user_facing_date':'2026-10-29','time':time.time()}
(PREP/'user-launch-decision.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'preparation-seal.json').write_text(json.dumps({str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'__pycache__'not in str(p)},indent=2))
ready['preparation_seal_sha256']=sha((out/'preparation-seal.json').read_bytes())
(PREP/'fullgui-ready-current.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'proposal_sha256':ready['proposal_sha256'],'local_CPU_tests':227,'remote_CPU_tests':227,'user_authorized':True,'new_model_calls':0}))
