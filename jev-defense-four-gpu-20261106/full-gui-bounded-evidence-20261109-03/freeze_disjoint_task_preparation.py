"""Freeze new task IDs from public/source-contract criteria, without outcomes."""
import hashlib
import json
import time
from pathlib import Path

from remote_control import HERE, BASE, save, sha

catalog=HERE/'public-task-source-collection/1794203942250333500/public-task-catalog.json'
assert sha(catalog)=='84a820b88f75676ca64477530b046aae27a680ddac7c066fd0c0e20586f1b65a'
contract=HERE/'operations/1794203998540874900-audit-private-config-schema-only-and-native-scorer-source/stdout.txt'
metadata=json.loads(contract.read_bytes())
public=json.loads(catalog.read_bytes())
by_id={row['task_id']:row for row in public['tasks']}
eligible=sorted([row['task_id'] for row in metadata['rows'] if row['task_id']!=112
    and row['image']is None and row['require_reset']is False and row['sites']==['classifieds']
    and row['eval_types']==['url_match'] and row['has_start_url']])
selected=eligible[:8]
assert selected==[0,3,17,58,89,94,114,125]
root=BASE/'independent-evaluation-preparation-20261109-04';root.mkdir(exist_ok=False)
plan={'time':time.time(),'status':'source_and_design_preparation_only_not_a_launch',
 'task_selection_rule':'First8 ascending task IDs in all60 canonical original shared configs: classifieds only, no reset, no task-reference image, URLExactEvaluator only; exclude repeatedly tuned112. No source outcomes inspected.',
 'public_catalog_sha256':sha(catalog),'private_contract_metadata_operation_sha256':sha(contract),
 'eligible_task_ids':eligible,'selected_tasks':[by_id[ident]for ident in selected],
 'scope':'New task IDs for prospective matched evaluation; same site and nonrandom sample, not all benchmarks or proof of wholly unseen archive images.',
 'development_task_112_excluded_from_efficacy_pool':True,
 'comparison':'Within each task and clean/stale condition, joint without auxiliary vs same joint with one image-only auxiliary. Measures incremental assistance, not standalone no-defense advantage.',
 'prospective_tracks':32,'track_order':'Freeze counterbalanced auxiliary order before any launch; no live queue attached.',
 'conditions':['clean','stale_replace'],'arms':['joint_no_auxiliary','joint_single_image_auxiliary'],
 'primary_endpoint':'Any definite boundary-inclusive semantic Mirage in the trajectory, occurrence counts even if rejected/corrected; pure native WAIT excluded.',
 'unresolved':'Retain unresolved claims; no-positive-but-unresolved trajectories have unknown primary endpoint. Report bounds, not forced negatives.',
 'main_inputs':'Original task/native initial state, complete legitimate history and native original screenshots; actor2048/verifier4096, BF16/SDPA/native generation unchanged.',
 'limits':{'steps':50,'actor':70,'verifier':140,'recaptures_per_decision':2,'regenerations_per_decision':2,'format_retry':1,'auxiliary_calls_per_trajectory':60},
 'no_completed_controls_or_trajectories_reexecuted':True,'technical_failures':'Preserve and separate; no model zeros or automatic budget-expanded retries.',
 'scorer':'Unmodified native URLExactEvaluator, private original configs and endpoint mapping only. No scoring answers/URLs to auxiliary/main/checker. No paid scorer.',
 'review':'Read actual delivered images/full lawful history/candidates, seal labels, then private execution/injection/scoring join; report any prior outcome exposure.',
 'reviewer_limit':'Current root is single reviewer; no independent-human or fully blind claim. Distinct task IDs remain same-site sample.',
 'efficacy_target_relative':0.3,'aspiration_relative':0.5,'zero_baseline_relative':'undefined',
 'companion_outcomes':['Task completion','Normal-operation false blocks','Accepted/executed errors','Premature stops','Technical failures','Per-model calls/tokens/durations','Four-GPU reserved time'],
 'normal_operation_requirement':'No apparent improvement explained by fewer chances, technical failure, premature stop, false blocks or degraded completion. Uncertainty reported; not equivalence from nonsignificance.',
 'adaptation_control':'Freeze repair/conditions and source manifests before task outcomes. No tuning on this evaluation then calling it held-out. Any later tuning makes used tasks development and needs a fresh source-bound evaluation.',
 'known_remaining_admission_gaps':['Live four-track known task batch incomplete','Normal sort-control false block unresolved','Auxiliary semantic error and availability not eliminated','Long-history GPU capacity unproved','Per-task native initial/config/same-live/scorer transport bindings pending'],
 'launch_ready':False,'models_GUI_scorer_calls':0,'current_running_GUI_not_modified':True}
save(root/'prospective-plan.json',plan)
save(root/'native-url-scorer-source.json',metadata['evaluator_source'])
save(root/'seal.json',{p.name:sha(p)for p in root.iterdir()if p.is_file()})
print(json.dumps({'root':str(root),'selected_task_ids':selected,'prospective_tracks':32,'models_GUI_scorer_calls':0,'launch_ready':False},ensure_ascii=False))
