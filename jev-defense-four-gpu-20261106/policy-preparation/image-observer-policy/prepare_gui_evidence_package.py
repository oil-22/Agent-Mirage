"""Freeze complete source/evidence staging package; no token, GPU or GUI launch."""
import hashlib,json,shutil,time,zipfile
from pathlib import Path,PurePosixPath
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
dest=ROOT/'gui-preparation-package-02';dest.mkdir(exist_ok=False)
remote=PurePosixPath('/data/researcher/jev-defense-four-gpu-20261106/gui-preparation-01')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
def cp(source,name):
    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);assert sha(source)==sha(target)


seal=json.loads((BASE/'policy-source-seal-04.json').read_bytes())
release=BASE/'gui-release-04'
for name,digest in seal['release_sha256'].items():
    assert sha(release/name)==digest;cp(release/name,'release/'+name)
cp(BASE/'gui-plan.json','plan.json');cp(BASE/'policy-source-seal-04.json','policy-source-seal.json')
cp(BASE/'gui-release-04-source-audit.json','gui-source-audit.json')
cp(BASE/'gui-release-04-repair.json','gui-release-04-repair.json')
cp(BASE/'observer-contract.json','observer-contract.json')
cp(BASE/'current-prompt-disclosure-04.json','current-prompt-disclosure.json')
cp(BASE/'shared-actor-instructions.txt','shared-actor-instructions.txt')
sources={
 'policy_cpu':(BASE/'cpu-evidence/1793974822119208200','evidence/policy-cpu'),
 'auditor_cpu':(BASE/'terminal-auditor-linked-02/cpu-evidence/1793976188298856100','evidence/terminal-auditor-cpu'),
 'observer_review':(ROOT/'observer-semantic-review/1793976051347383200','evidence/observer-review'),
 'same_live':(ROOT/'environment-transport-evidence-1793976484270917404','evidence/same-live-environment')}
for folder,prefix in sources.values():
    for path in folder.iterdir():
        if path.is_file():cp(path,prefix+'/'+path.name)
for name in ['audit_gui_terminals.py','test_terminal_auditor.py','prepare_auditor_receipt.py','README.md']:
    cp(BASE/'terminal-auditor-linked-02'/name,'terminal-auditor/'+name)
for name in ['summary.json','plan.json','terminal-sha256.json']:
    cp(ROOT/'observer-real-preflight-20261106-01'/name,'evidence/observer-terminal/'+name)
cp(BASE/'protocol-audit/compatibility-receipt.json','evidence/online-health-compatibility.json')
quotes=[
 {'text':'我的设定是只要一个jev模型来帮忙核验','source':'human user, available in current thread transcript'},
 {'text':'腾出4-7卡用来开始实验','source':'human user, available in current thread transcript'},
 {'text':'我的设想是这样的，依靠核验模型去识别收到的图像是什么样的，而不是给他多模态agent的上下文，让他帮助判断当前图片的样子然后把答复再给多模态agent的模型，从而避免mirage，你看看合理不，你如果觉得合理可以在这方面做一些补充和改动，我的目标是降低mirage触发率',
  'source':'exact human user text provided by parent /root from its current visible transcript'},
 {'text':'反正我的目标就是降低mirage触发率，我要一个可观的效果',
  'source':'exact human user text provided by parent /root from its current visible transcript'}]
condition={'image_only_direct_actor_authorized':True,'single_fixed_observer_authorized':True,
    'four_gpu_new_layout_authorized':True,'human_quotes':quotes,
    'scope':'Current user-authorized single observer screenshot-only development startup; four matched known-task trajectories are a bounded pilot, not new formal efficacy approval or proof of a30% effect.',
    'observer_has_no_task_history_candidate_or_injection_context':True,
    'strict_primary_validator_and_budgets_unchanged':True,'new_paid_or_expanded_budget_authorization_claimed':False}
save(dest/'evidence/user-condition.json',condition)
addendum={'parent_review_sha256':sha(ROOT/'observer-semantic-review/1793976051347383200/review.json'),
    'current_core_sha256':sha(release/'defense/core.py'),'current_runner_sha256':sha(release/'run_image_observer_vwa_validation.py'),
    'routing_order':['strict joint pre-readiness on original PublicView','if usable: actor callback runs screenshot-only observer then native actor','strict original post-verification/recovery'],
    'observer_cannot_rescue_pre_actor_readiness_false_blocks':True,
    'blank_preflight_success_does_not_prove_auxiliary_naturally_called_on_blank_in_joint_GUI':True,
    'normal_footer_readiness_success_if_any_must_not_be_automatically_attributed_to_auxiliary':True,
    'pilot_scope':'Incremental downstream actor packet only; current coarse observations have limited direct coverage of page/focus/history errors.',
    'no_routing_prompt_budget_or_prediction_changes':True,'no_model_GUI_calls':0}
save(dest/'evidence/routing-scope-addendum.json',addendum)
config={'policy':'single-flash-image-observer-actor-v1','model':'pplx_flash',
    'revision':'9ff7cf9838e59df461c276b7699d56b244d2af58','max_auxiliary_calls':60,
    'observer_contract_sha256':sha(BASE/'observer-contract.json'),
    'url':'http://127.0.0.1:28423',
    'token_file':'/data/researcher/jev-defense-four-gpu-20261106/transport-online-01/private.token',
    'deployment_applied':False,'token_created_by_this_package':False}
save(dest/'auxiliary-config.proposed.json',config)
evidence={
 'observer_independent_review':'evidence/observer-review/review.json',
 'observer_terminal':'evidence/observer-terminal/summary.json',
 'actor_observer_policy_cpu':'evidence/policy-cpu/receipt.json',
 'terminal_auditor':'evidence/terminal-auditor-cpu/receipt.json',
 'same_live_environment':'evidence/same-live-environment/receipt.json',
 'user_condition':'evidence/user-condition.json',
 'current_prompt_disclosure':'current-prompt-disclosure.json'}
ready={'policy':config['policy'],'launch_ready':False,'plan_sha256':sha(dest/'plan.json'),
    'release_sha256':seal['release_sha256'],
    'evidence':{key:{'path':str(remote/name),'sha256':sha(dest/name)}for key,name in evidence.items()},
    'unverified_required_evidence':{'primary_full_input_capacity':'pending actual request and independent original-full-input audit; never filled from loading/running flags',
        'ownership_transport':'pending final actual UID/full command/held locks/no foreign compute/new transport token and live health'},
    'deployment_applied':False,'formal_defense_efficacy_ready':False,
    'requires_new_linked_final_readiness_after_actual_pending_proofs':True,
    'no_models_GUI_or_old_queues_started_by_package':True}
save(dest/'readiness.template.json',ready)
save(dest/'launch-command.proposed.json',{'execute_now':False,'purpose':'Reviewable future command only; missing final readiness/token prevents startup',
    'argv':['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-u',str(remote/'release/run_image_observer_vwa_validation.py'),
        '--root','REQUIRES_NEW_ONCE_ONLY_GUI_BATCH_ROOT','--plan',str(remote/'plan.json'),
        '--token-file','/data/researcher/jev-defense-four-gpu-20261106/transport-online-01/private.token',
        '--runtime','/data/researcher/jev-defense-validation-20261103/runtime-stage-01',
        '--native-task','/data/researcher/jev-defense-validation-20261103/task-restore-1793683370167273452/classifieds_112.PRIVATE.json',
        '--actor-template','/data/researcher/jev-defense-validation-20261103/native-vwa-request.recovered.json',
        '--auxiliary-config','REQUIRES_NEW_LINKED_DEPLOYED_SINGLE_AUX_CONFIG',
        '--readiness','REQUIRES_NEW_LINKED_VERIFIED_FINAL_READINESS','--model-url','http://127.0.0.1:28422']})
(dest/'README.md').write_text('''# Single image observer GUI staging only\n\nOnly release/run_image_observer_vwa_validation.py is the new reviewed future runner.\nThe original77 files are immutable provenance/dependencies; no old launcher or queue\nis executed. readiness.template.json is intentionally false and capacity/ownership\nproofs remain missing. No private token is created and auxiliary deployment_applied\nis false. Root must create a new linked final gate/config only after actual evidence.\n\nEvidence reviews are evaluation provenance and never native model inputs. Observer\nreceives only one received image and the fixed generic contract; the actual actor\ngets fallible predictions under identical shared boundary instructions in both arms.\nUpstream strict readiness can block before observer is invoked, so auxiliary cannot\nbe credited with earlier readiness successes or repairs. Known sparse-button blank\nmisclassification is retained. This four-run known-task pilot cannot prove a general\nMirage reduction or the predeclared30% development target.\n''',encoding='utf8')
package={'remote_destination':str(remote),'active_runner':'release/run_image_observer_vwa_validation.py',
    'source_file_count':len(seal['release_sha256']),'policy_source_seal_sha256':sha(BASE/'policy-source-seal-04.json'),
    'private_task_auth_token_files_included':False,'launch_ready':False,'new_model_GUI_calls':0,
    'files':{str(p.relative_to(dest)).replace('\\','/'):sha(p)for p in dest.rglob('*')if p.is_file()}}
save(dest/'package-seal.json',package)
archive=ROOT/('gui-preparation-package-02-'+sha(dest/'package-seal.json')[:16]+'.zip')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED)as z:
    for p in dest.rglob('*'):
        if p.is_file():z.write(p,str(p.relative_to(dest)).replace('\\','/'))
print(json.dumps({'local':str(dest),'archive':str(archive),'archive_sha256':sha(archive),
    'package_seal_sha256':sha(dest/'package-seal.json'),'remote':str(remote),'files':len(package['files'])+1,'model_GUI_calls':0}))
