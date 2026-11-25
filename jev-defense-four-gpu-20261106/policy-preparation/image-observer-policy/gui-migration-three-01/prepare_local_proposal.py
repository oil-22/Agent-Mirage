"""Freeze reviewable local proposal; no remote access or launch-ready switch."""
import hashlib,json,time
from pathlib import Path
import migration_contract as m
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
parent=ROOT/'gui-preparation-package-02/plan.json'
diagnostic=ROOT/'service-stop-diagnostic-1793983538956413700/receipt.json'
postexit=ROOT/'service-postexit-preservation-invocation-1793983751091430900/receipt.json'
snapshot=json.loads(diagnostic.read_bytes())['snapshot']['state_snapshot']
plan=m.prepare_plan(parent.read_bytes(),snapshot)
out=HERE/'cpu-preparation'/str(time.time_ns());out.mkdir(parents=True)
(out/'plan.proposed.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
(out/'original-state-snapshot.json').write_text(json.dumps(snapshot,indent=2),encoding='utf8')
source={name:sha(HERE/name)for name in ['PROPOSAL.zh.md','migration_contract.py','test_migration_contract.py','prepare_local_proposal.py']}
receipt={'stage':'source_CPU_migration_proposal_only','launch_ready':False,
    'original_plan':str(parent),'original_plan_sha256':sha(parent),
    'actual_source_snapshot_receipt':str(diagnostic),'actual_source_snapshot_receipt_sha256':sha(diagnostic),
    'independent_postexit_receipt':str(postexit),'independent_postexit_receipt_sha256':sha(postexit),
    'proposed_plan_sha256':sha(out/'plan.proposed.json'),'source_sha256':source,
    'cpu_boundary_tests_previously_passed':8,
    'cpu_test_command':'python -B -m unittest -v test_migration_contract.py',
    'tests_scope':'exact suffix; all spent/started controls; baseline reset/requeue; order; budgets/prompts/seed; original source SHA',
    'old_baseline_not_reexecuted':True,'old_failed_or_completed_terminal_not_changed':True,
    'maximum_new_primary_GUI_calls':630,'maximum_new_auxiliary_GUI_calls':120,
    'single_task_development_only':True,'clean_causal_comparison_not_available':True,
    'resource_change':'common primary max_memory14/22/22/6GiB and allocator; exact new spec and real capacity still pending',
    'requires_before_launch':['actual unchanged full failed-input capacity passed plus independent audit',
        'new exact resource/allocator spec for all three trajectories','actual old journal proves no migrated begin or calls',
        'new linked GUI/online contract and queue gates independently tested','actual fresh identity/9locks/no foreign compute/transport',
        'new service token, once-only claim, source seals, admission and control root','root review of exact experimental differences'],
    'actual_GPU_model_GUI_HTTP_scorer_signal_calls_during_preparation':0}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.name:sha(p)for p in out.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(out),'receipt_sha256':sha(out/'receipt.json'),'plan_sha256':sha(out/'plan.proposed.json'),
    'seal_sha256':sha(out/'seal.json'),'launch_ready':False}))
