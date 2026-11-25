"""Seal the exact source-only scene change and its deployment tradeoff."""
import ast,hashlib,json,re,time
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'scene-only-fullgui-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not(P/'fullgui-ready-current.json').exists()
d=read(B/'scene-only-repair-development/completed-current.json');assert d['worker_exited']and d['source_review_complete']and d['fullgui_candidate_eligible']
assert sha(Path(d['directory'])/'review.json')==d['review_sha256']
stage=read(P/'fullgui-staging-current.json');out=Path(stage['directory']);release=Path(stage['release'])
for n,h in read(out/'release-sha256.json').items():assert sha(release/n)==h,n
oldready=read(B/'completion-source-fullgui-development/fullgui-ready-current.json');oldproposal=read(Path(oldready['proposal']));old=Path(oldproposal['release'])
for n in ['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','current_only_history_scope.py','completion_frame_price_source.py']:
 assert(old/n).read_bytes()==(release/n).read_bytes(),n
defs=lambda p:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
before,after=defs(old/'defense/core.py'),defs(release/'defense/core.py');assert set(before)==set(after)and[k for k in before if before[k]!=after[k]]==['Controller']
cpu=read(out/'cpu-results.json');rcpu=read(out/'environment-evidence/remote-cpu-tests.json');counts=lambda rows:[int(re.search(r'Ran (\d+) tests',r['stderr']).group(1))for r in rows]
assert all(r['returncode']==0 for r in cpu+rcpu)and counts(cpu)==counts(rcpu)==[122,184]
env=read(out/'environment-receipt.json');assert env['child_exited']and env['model_calls']==0 and env['status']['phase']=='environment_preflight_complete'
proposal={**oldproposal,'version':'evidence-v4.0.8-dev-scene-only-source-20261029','status':'USER_AUTHORIZED_ITERATIVE_REPAIR',
 'release':str(release),'remote_release':stage['remote_preparation_root']+'/release','release_manifest_sha256':stage['release_manifest_sha256'],
 'condition_changes':oldproposal['condition_changes']+['Auxiliary scene readiness now receives only CURRENT original image and SHA provenance, with task/recentaction/executionfeedback removed from this auxiliary stage only. Actor/main full original inputs remain unchanged. Compact source-only prompt replaces old task-aware scene prompt; all validators/recovery limits remain.'],
 'tradeoff':'Scene readability is task-independent and may admit coherent irrelevant destinations to later checks. It certifies no target, action, focus, historical execution, coverage, minimum or success. The main/focus/history/completion checks retain full original inputs and strict validation. Additional reads still consume original140judgecap. Do not force usable or alter generated replies.',
 'parent_diagnostic_review_sha256':d['review_sha256'],
 'residuals':['Four selected same-task image controls passed source/format/readability review; not a general scene accuracy or defense efficacy estimate','Artificial WAIT is zero-call routing, not a real natural semantic pass','Prior v4.0.7 GUI technical verifier failure is sealed, not restarted; source-only condition is a new development trajectory','Current-only historical scope guard and original one-formatretry remain active; new paraphrases/false blocks still possible','Completion numerical source checking has not yet demonstrated full GUI recovery; clothing/globalminimum ambiguity remains'],
 'completed_preparation':{'local_CPU_tests':306,'remote_CPU_tests':306,'fresh_logged_in_environment_preflight':True,'same_live_recapture':True,'environment_worker_exited':True,'model_calls':0},
 'launcher':str(B/'launch_scene_only_fullgui.py'),'remote_active_must_not_exist':'scene-only-fullgui-active-20261029.json',
 'human_decision_required':'Current human continuing repair instruction authorizes this concrete linked repair/validation, unchanged original limits.'}
(out/'fullgui-proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding='utf-8')
ready={**oldready,'directory':str(out),'proposal':str(out/'fullgui-proposal.json'),'proposal_sha256':sha(out/'fullgui-proposal.json'),'release_manifest_sha256':stage['release_manifest_sha256'],'status':'USER_AUTHORIZED_PENDING_FRESH_LAUNCH_CHECK','launcher_sha256':sha(B/'launch_scene_only_fullgui.py'),'report':None,'report_sha256':None,'fullGUI_started':False,'new_model_calls':0}
(P/'user-launch-decision.json').write_text(json.dumps({'approved':True,'proposal_sha256':ready['proposal_sha256'],'scope':'one-new-scoped-joint-stale-fullgui','user_authorization_text':'继续修复，直到能防御成功为止','authorization_context':'Direct iterative repair authorization; preserve old terminals and original budgets.','time':time.time()},ensure_ascii=False,indent=2),encoding='utf-8')
(out/'preparation-seal.json').write_text(json.dumps({str(p.relative_to(out)).replace('\\','/'):sha(p)for p in out.rglob('*')if p.is_file()and'__pycache__'not in str(p)},indent=2));ready['preparation_seal_sha256']=sha(out/'preparation-seal.json')
(P/'fullgui-ready-current.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'proposal_sha256':ready['proposal_sha256'],'local_CPU_tests':306,'remote_CPU_tests':306,'authorized':True,'new_model_calls':0}))
