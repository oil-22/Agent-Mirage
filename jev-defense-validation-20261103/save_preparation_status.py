"""Seal this preparation snapshot without claiming semantic or full-GUI completion."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

base = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parent = json.loads((base / 'parent-source-sha256.json').read_bytes())
assert all(sha(base / 'release' / name) == expected for name, expected in parent.items())
release = {}
for p in sorted((base / 'release').rglob('*.py')):
    ast.parse(p.read_text(encoding='utf-8-sig'))
    release[p.relative_to(base / 'release').as_posix()] = sha(p)
environment = base / 'environment-evidence'
verified = []
remote_only = []
for d in [environment, environment / 'missing-dependency', environment / 'startup-race']:
    seal = json.loads((d / 'seal.json').read_bytes())
    for name, expected in seal.items():
        path = d / name
        if path.exists():
            assert sha(path) == expected, path
            verified.append(path.relative_to(base).as_posix())
        else:
            remote_only.append({'root': str(d), 'file': name, 'sha256': expected})
receipt = json.loads((environment / 'receipt.json').read_bytes())
assert receipt['phase'] == 'environment_preflight_complete'
assert receipt['initial_sha256'] == receipt['recapture_sha256']
transport = base / 'transport-evidence/1793684341497946700'
for name, expected in json.loads((transport / 'seal.json').read_bytes()).items():
    assert sha(transport / name) == expected
transport_status = json.loads((transport / 'receipt.json').read_bytes())
assert transport_status['temporary_bridges_closed']
sources = json.loads((base / 'prerequisites/inspection-1793684299449578394.json').read_bytes())
active = [s for s in sources['services'] if s['exists']]
assert len(active) == 2 and all(s['exclusive_gpu'] and s['command_matches'] and
                              s['uid'] == 1033 and len(s['fd_locks']) == 3 for s in active)
stamp = str(time.time_ns())
snapshot = base / 'preparation-snapshots' / stamp
snapshot.mkdir(parents=True, exist_ok=False)
(snapshot / 'release-sha256.json').write_text(json.dumps(release, indent=2), encoding='utf-8')
status = {
    'updated_at': datetime.now(timezone.utc).isoformat(),
    'phase': 'policy_implemented_environment_recovered_real_validation_pending',
    'policy': 'jev-cued-judge-v1',
    'new_27B_calls': 0, 'new_jev_calls': 0, 'GUI_task_actions': 0, 'official_scores': 0,
    'full_GUI_started': False, 'defense_effectiveness_established': False,
    'original_parent_python_files_unchanged': len(parent),
    'policy_and_original_controller_tests_passed': 45,
    'test_scope': 'CPU control flow with scripted primary replies, not semantic accuracy',
    'sealed_previous_jev_predictions_reused': 36,
    'offline_replay': 'offline-replay-02',
    'environment_preflight': 'environment-evidence/receipt.json',
    'environment_failures_preserved': ['environment-evidence/missing-dependency', 'environment-evidence/startup-race'],
    'environment_public_files_verified': verified,
    'environment_remote_only_sealed_files': remote_only,
    'task_configuration_historical_sha_restored': True,
    'actor_template_actual_request_bound': True,
    'whole_historical_dependency_environment_reproduced': False,
    'prompt_constants_exact_archived_request_matches': 6,
    'potentially_active_unbound_prompt_constants': ['COMPLETION_RELATION', 'NATIVE_NAVIGATION'],
    'whole_historical_prompts_file_sha_restored': False,
    'gui_runner': 'release/run_jev_vwa_validation.py',
    'gui_runner_status': 'staged; not executed; original 8 critical native functions unchanged',
    'gui_plan': 'gui-plan.proposed.json',
    'launch_ready': False,
    'current_resource_receipts': ['prerequisites/prerequisites-3090-1793684167096532673.json',
                                  'prerequisites/prerequisites-4090-1793684170134028643.json'],
    'owned_jev_inspection': 'prerequisites/inspection-1793684299449578394.json',
    'resource_summary': '3090 free candidates 6,7 only; owned Jev 4,5; all four 4090 cards have foreign compute',
    'new_GPU_allocations': 0,
    'transport_health_verified': 'transport-evidence/1793684341497946700/receipt.json',
    'transport_status': 'temporary loopback bridges closed; inference credentials not copied',
    'remaining_work': [
        'Bind two potentially active recovered prompt constants or disclose concrete differences',
        'Freeze exact legal-input real-main-model preflight packet, review expectations and finite budget',
        'Implement and inspect new owned-resource launcher, inference transport lifecycle and post-exit seals',
        'Obtain four verified exclusive GPUs for original27B without preempting Jev or foreign tasks',
        'Run new finite primary preflight and independent review before formal new GUI condition decision',
        'Run and review clean/stale new full trajectories if prerequisites and decision permit'
    ],
    'existing_deployment_monitor': 'jev-gpu paused after deployment completion',
    'new_background_scheduler': False,
    'snapshot': str(snapshot.relative_to(base)).replace('\\', '/'),
}
(base / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
for name in ['status.json', 'README.md', 'HANDOFF.md', '辅助证据判定规则与GUI验证方案-20261103.md',
             'GUI判定与结果审查标准.md', 'gui-runner-static-audit.json', 'gui-runner-staging.json',
             'gui-plan.proposed.json', 'launch-readiness.json', 'gui-runner-diff.patch']:
    (snapshot / name).write_bytes((base / name).read_bytes())
(snapshot / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in snapshot.iterdir() if p.is_file()}, indent=2), encoding='utf-8')
print(json.dumps({'snapshot': str(snapshot), 'parent_files_unchanged': len(parent),
                  'python_sources': len(release), 'local_environment_files_verified': len(verified),
                  'launch_ready': False, 'new_model_calls': 0}))
