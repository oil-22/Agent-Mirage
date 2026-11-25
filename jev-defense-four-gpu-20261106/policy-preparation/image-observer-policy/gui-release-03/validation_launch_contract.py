"""Fail-closed input gate for the new development runner, not a GPU launcher."""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_launch_inputs(args):
    ready = json.loads(args.readiness.read_bytes())
    required = ['prompt_identity_complete', 'real_policy_preflight_review_passed',
                'same_live_environment_preflight_passed', 'owned_main_model_ready',
                'both_jev_services_owned_and_exclusive', 'actual_transport_ready',
                'new_condition_decision_recorded', 'terminal_auditor_ready']
    if ready.get('launch_ready') is not True or any(ready.get(k) is not True for k in required):
        raise RuntimeError('New GUI experiment prerequisites are incomplete; no model or GUI started')
    plan = json.loads(args.plan.read_bytes())
    assert ready['plan_sha256'] == sha(args.plan)
    assert plan['policy'] == 'jev-cued-judge-v1'
    assert plan['limits'] == {'max_recaptures_per_decision': 2,
        'max_regenerations_per_decision': 2, 'max_actor_calls': 70,
        'max_verifier_calls': 140, 'wait_seconds': [0.5, 1.0]}
    assert len(plan['queue']) == 2
    assert {q['condition'] for q in plan['queue']} == {'clean', 'stale_replace'}
    assert all(q['dataset'] == 'vwa' and q['arm'] == 'joint' for q in plan['queue'])
    assert len({q['run_id'] for q in plan['queue']}) == 2
    private = json.loads(args.native_task.read_bytes())
    assert sha(args.native_task) == 'b2dd3cef7cc6357376b95ef8c64ae4fcad839fd7f705e55afbdeb4a3d6a83603'
    assert plan['tasks']['vwa'] == [{'pilot_task_id': 'classifieds_112', 'image': None,
                                   'intent': private['intent']}]
    assert sha(args.actor_template) == 'b2a0af4ba02e3316cb060cddc2e0a1b20d6e00eabce04358387f5e8f46278add'
    assert sha(args.runtime / 'native/run_reddit_internvl_smoke.py') == 'af825cdf46601f4b12efb8fe614f1eb1c924af750a7fbc85bc6a565119267cf7'
    config = json.loads(args.auxiliary_config.read_bytes())
    assert config['policy'] == plan['policy'] and config['max_auxiliary_calls'] == 60
    assert config.get('deployment_applied') is True
    release = Path(__file__).resolve().parent
    for name, expected in ready['release_sha256'].items():
        path = (release / name).resolve()
        assert path.is_relative_to(release) and sha(path) == expected
    # This gate cannot certify actual locks from an old JSON. The outer launcher must
    # recheck UID/full commands/GPU exclusivity and hold inherited locks for the run.
    if not ready.get('launcher_performs_fresh_ownership_checks'):
        raise RuntimeError('A fresh ownership-checking launcher is required')
