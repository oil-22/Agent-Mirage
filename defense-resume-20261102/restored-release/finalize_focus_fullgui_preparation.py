"""Freeze the updated condition and preserve this turn's explicit launch instruction."""
import ast,hashlib,json,re,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-history-fullgui-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_bytes())
assert not(PREP/'fullgui-ready-current.json').exists()
stage=read(PREP/'fullgui-staging-current.json');out=Path(stage['directory']);release=Path(stage['release'])
for n,h in read(out/'release-sha256.json').items():assert sha((release/n).read_bytes())==h,n
oldready=read(BASE/'scoped-observability-development/fullgui-ready-current.json')
oldproposal=read(Path(oldready['proposal']));old=Path(oldproposal['release'])
def defs(p):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a,b=defs(old/'defense/core.py'),defs(release/'defense/core.py')
assert set(a)==set(b)and[k for k in a if a[k]!=b[k]]==['Controller']
for n in ['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py']:
 assert(old/n).read_bytes()==(release/n).read_bytes(),n
cpu=read(out/'cpu-results.json');rcpu=read(out/'environment-evidence/remote-cpu-tests.json')
counts=lambda rows:[int(re.search(r'Ran (\d+) tests',r['stderr']).group(1))for r in rows]
assert all(r['returncode']==0 for r in cpu+rcpu)
assert counts(cpu)==counts(rcpu)==[122,74]
env=read(out/'environment-receipt.json');assert env['child_exited']and env['model_calls']==0 and env['status']['phase']=='environment_preflight_complete'
proposal={**oldproposal,'version':'evidence-v4.0.2-dev-current-only-scope-20261028','status':'USER_REQUESTED_LAUNCH',
 'release':str(release),'remote_release':stage['remote_preparation_root']+'/release','release_manifest_sha256':stage['release_manifest_sha256'],
 'condition_changes':oldproposal['condition_changes']+['Focus reader separates visible focus cue from prior-click causality','History plan versus execution prompts','Narrow current-only execution-history/source eligibility checks using original1formatretry; no verdict/action edits'],
 'residuals':['Dedicated6focus controls matched blue/ordinary; readiness still not guaranteed to report cue','Prompt-only history errors retained','Current-only guard actually rejected one unsupported execution claim; main historical source guard0online rejects','Eligibility does not establish truth; earlier assistant plan/report not independent execution proof','Possible false blocks for legitimate current-screen history/log UIs and paraphrase misses','No fullGUI efficacy, naturalWAIT/loading positive or typing recovery demonstrated'],
 'tradeoff':oldproposal['tradeoff']+' Supplemental history source eligibility may conservatively reject valid current-screen historical evidence; retries consume the unchanged budget. Narrow guards do not establish opposite facts or semantic approval.',
 'completed_preparation':{'local_CPU_tests':196,'remote_CPU_tests':196,'fresh_logged_in_environment_preflight':True,'same_live_recapture':True,'environment_worker_exited':True,'model_calls':0,'reporter_race_preserved_and_recovered':True},
 'decision_scope':'one-new-scoped-joint-stale-fullgui','launcher':str(BASE/'launch_focus_history_fullgui.py'),
 'remote_active_must_not_exist':'focus-history-fullgui-active-20261029.json','human_decision_required':'Latest explicit human instruction 启动实验 authorizes this new single repaired-condition run in current session; previous repair-first decision preserved separately.',
 'parent_repair_receipt_sha256':sha((BASE/'focus-history-repair-development/repair-combined-current.json').read_bytes())}
(out/'fullgui-proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding='utf-8')
ready={**oldready,'directory':str(out),'proposal':str(out/'fullgui-proposal.json'),'proposal_sha256':sha((out/'fullgui-proposal.json').read_bytes()),'release_manifest_sha256':stage['release_manifest_sha256'],'status':'USER_AUTHORIZED_PENDING_FRESH_LAUNCH_CHECK','launcher_sha256':sha((BASE/'launch_focus_history_fullgui.py').read_bytes()),'preparation_seal_sha256':None,'report':None,'report_sha256':None,'fullGUI_started':False,'new_model_calls':0}
decision={'approved':True,'proposal_sha256':ready['proposal_sha256'],'scope':'one-new-scoped-joint-stale-fullgui','user_authorization_text':'启动实验','authorization_context':'Direct human request after completed focus/history repair report; start one new fullGUI experiment with latest repaired condition, same previously described joint/stale basketball task and original budgets. Earlier refusal of unrepaired condition preserved.','user_facing_date':'2026-10-29','time':time.time()}
(PREP/'user-launch-decision.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'preparation-seal.json').write_text(json.dumps({str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'__pycache__'not in str(p)},indent=2))
ready['preparation_seal_sha256']=sha((out/'preparation-seal.json').read_bytes())
(PREP/'fullgui-ready-current.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'proposal_sha256':ready['proposal_sha256'],'local_CPU_tests':196,'remote_CPU_tests':196,'user_authorized':True,'new_model_calls':0}))
