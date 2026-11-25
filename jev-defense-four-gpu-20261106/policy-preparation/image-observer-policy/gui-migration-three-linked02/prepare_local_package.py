"""Freeze source/CPU preparation artifacts only; never create a ready launch spec."""
import difflib,hashlib,json,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DEPLOY='/data/researcher/jev-defense-four-gpu-20261106/gui-migration-three-linked02'
OLD_MIRROR='/data/researcher/jev-defense-four-gpu-20261106/independent-service-postexit-mirror-1793983761231132390-gzip-linked02'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,obj):
    with path.open('x',encoding='utf8')as f:json.dump(obj,f,ensure_ascii=False,indent=2)
old=ROOT/'gui-preparation-package-02'
shutil.copy2(old/'policy-source-seal.json',HERE/'frozen-original-policy-source-seal.json')
cap=HERE/'evidence/primary-capacity/receipt.json';cap.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'single-capacity-independent-audits/1793985058235255298/receipt.json',cap)
proof={'classification':'exact_original_unstarted_suffix_new_three_run_group',
    'original_state':{'path':OLD_MIRROR+'/service/online-state.json','sha256':'967bf98cbb5230a0a87d8151903ea725b8fc355ce3ca7ffda881468d62d26ae9'},
    'original_journal':{'path':OLD_MIRROR+'/service/journal.jsonl','sha256':'195105c64bbd82d16a7bf4e8209f5bfbee6ea1168fef6c81dfba626691ba1181'},
    'independent_postexit':{'path':OLD_MIRROR+'/receipt.json','sha256':'6cc5f640a3abd9bdeb53a990db14a5386107517846c82933b188e99e83013d36'},
    'original_structural_audit':{'path':'/data/researcher/jev-defense-four-gpu-20261106/gui-independent-postexit-integrity-audit-1793984897043253928/receipt.json',
        'sha256':'8017f765b7c68d4014cc848a098769b6348f206a81d8aeb69ca58ab18558e127'},
    'original_batch_root':'/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-retry01',
    'original_batch_manifest':{'path':'/data/researcher/jev-defense-four-gpu-20261106/gui-outer-control-retry01/batch-postexit-sha256.json',
        'sha256':'826f1bde479c12cb8a63ffdf8fa52af3e085d37a6e188d97489bfdfcf10c88f6'},
    'new_primary_call_cap':630,'new_auxiliary_call_cap':120,
    'old_clean_baseline_not_reexecuted':True,'no_old_claim_budget_or_queue_reused':True,
    'new_resource_layout_decoder_layer_counts':[14,22,22,6],
    'new_allocator':'expandable_segments:True','max_memory_gib_is_separate_runtime_spec_field':True}
save(HERE/'three-trajectory-migration-source.json',proof)
policy=json.loads((old/'policy-source-seal.json').read_bytes())
policy['plan_sha256']=sha(HERE/'plan.json')
policy['release_sha256']={p.relative_to(HERE/'release').as_posix():sha(p)for p in (HERE/'release').rglob('*')if p.is_file()}
save(HERE/'policy-source-seal.json',policy)
ready=json.loads((old/'readiness.template.json').read_bytes())
ready.update(launch_ready=False,plan_sha256=sha(HERE/'plan.json'),release_sha256=policy['release_sha256'])
ready['evidence']['primary_full_input_capacity']={'path':DEPLOY+'/evidence/primary-capacity/receipt.json','sha256':sha(cap)}
ready['evidence']['three_trajectory_migration']={'path':DEPLOY+'/three-trajectory-migration-source.json','sha256':sha(HERE/'three-trajectory-migration-source.json')}
ready['unverified_required_evidence']={'ownership_transport':'root fresh actual 120-second proof with exact three_unstarted_run_ids and new token',
    'resource_conditions':'runtime new online loaded source/actual CUDA/decoder14_22_22_6/allocator/common three trajectories',
    'terminal_auditor':'linked three-run source CPU audit receipt and original wire invariants',
    'actual_migration_source_validation':'fixed old original state/journal/GUI terminal inventory; no migrated begins or calls'}
save(HERE/'readiness.template.json',ready)
diff=[]
for name in ('observer_launch_contract.py','run_image_observer_vwa_validation.py'):
    diff.extend(difflib.unified_diff((old/'release'/name).read_text(encoding='utf8').splitlines(True),
        (HERE/'release'/name).read_text(encoding='utf8').splitlines(True),fromfile='original/'+name,tofile='linked-three/'+name))
(HERE/'source-diff.txt').write_text(''.join(diff),encoding='utf8')
print(json.dumps({'package':str(HERE),'plan_sha256':sha(HERE/'plan.json'),'policy_source_seal_sha256':sha(HERE/'policy-source-seal.json'),
    'migration_proof_sha256':sha(HERE/'three-trajectory-migration-source.json'),'launch_ready':False}))
