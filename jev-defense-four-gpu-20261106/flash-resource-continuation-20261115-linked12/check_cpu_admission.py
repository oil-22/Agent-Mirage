"""New continuation admission/proof boundary checks; no historical controls or inference."""
import ast
import copy
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE / 'package'
sys.path[:0] = [str(P / 'flash'), str(P)]
from continuation_guard import validate_contract
from historical_memory import validate_proof
from expanded_guard import validate_compute
from control import sha, save


def main():
    assert not (HERE / 'CPU-admission-checks.json').exists()
    plan = json.loads((P / 'plan.json').read_bytes())
    parent = json.loads((HERE.parent / 'flash-ample-memory-gui-20261114-linked11/package/plan.json').read_bytes())
    contract = json.loads((P / 'technical-continuation-contract.json').read_bytes())
    capacity = json.loads((P / 'parent-capacity.json').read_bytes())
    validate_contract(plan, contract, parent)
    validate_proof(capacity)
    rows = [{'case': 'exact_remaining13_and_original_conditions', 'passed': True},
            {'case': 'exact_historical_proof_admitted_without_inference', 'passed': True}]

    def reject(name, action):
        try:
            action()
        except (AssertionError, RuntimeError):
            rows.append({'case': name, 'strictly_rejected': True})
        else:
            raise AssertionError('Failed to reject ' + name)

    for name, key, value in [('missing_remaining', 'queue', plan['queue'][:-1]),
                             ('wrong_queue_size', 'expected_trajectories', 12),
                             ('changed_main_output', 'actor_output_tokens', 4096),
                             ('changed_step_budget', 'max_steps', 51),
                             ('changed_call_budget', 'max_actor_calls_per_trajectory', 71),
                             ('history_changed', 'native_main_history', 'trimmed'),
                             ('finite_recap_changed', 'recapture_limit', 2),
                             ('seed_changed', 'actor_seed', 1),
                             ('precision_placement_changed', 'main_gpu_physical', [0, 1, 2]),
                             ('gate_prompt_context_changed', 'gate', 'task-conditioned')]:
        amended = copy.deepcopy(plan)
        amended[key] = value
        reject(name, lambda amended=amended: validate_contract(amended, contract, parent))
    wrong = copy.deepcopy(plan)
    wrong['queue'][0] = parent['queue'][0]
    reject('completed_run_cannot_reenter_queue', lambda: validate_contract(wrong, contract, parent))
    wrong = copy.deepcopy(plan)
    wrong['tasks'][0]['intent'] += ' changed'
    reject('task_hint_change_rejected', lambda: validate_contract(wrong, contract, parent))
    for name, path, value in [
        ('missing_capacity_pass', ['status'], 'failed'),
        ('missing_kernel_bitwise', ['memory_lifetime_patch', 'all_kernel_tests_bitwise_equal'], False),
        ('missing_full_logit_equivalence', ['memory_lifetime_patch', 'all_full_vocab_logits_and_sequence_ids_bitwise_equal'], False),
        ('missing_MLP_weight_test', ['memory_lifetime_patch', 'MLP_memory_proof', 'actual_weight_GPU_output_bitwise_tests'], 13),
        ('wrong_stress_length', ['probes', 0, 'input_tokens'], 12000),
        ('insufficient_historical_headroom', ['probes', 0, 'memory', 0, 'headroom_at_reserved_peak_bytes'], 1),
    ]:
        wrong = copy.deepcopy(capacity)
        target = wrong['capacity_terminal']
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        reject(name, lambda wrong=wrong: validate_proof(wrong))
    root = HERE / ('CPU-forensic-boundaries-' + str(time.time_ns()))
    root.mkdir()
    os.environ['MIRAGE_RESOURCE_FORENSICS_ROOT'] = str(root)
    cards = {0: {'uuid': 'GPU-test-0', 'free_mib': 24253}, 1: {'uuid': 'GPU-test-1', 'free_mib': 24253}}
    own = {'uuid': 'GPU-test-0', 'pid': 100, 'used_mib': '1000', 'identity': {'uid': 1033, 'command': 'simulation own', 'start_ticks': '1'}}
    unexpected = {'uuid': 'GPU-test-0', 'pid': 200, 'used_mib': '1', 'identity': {'uid': 777, 'command': 'simulation other', 'start_ticks': '2'}}
    validate_compute(cards, [own], {0: 100, 1: None})
    rows.append({'case': 'exact_compute_accepted', 'passed': True})
    reject('compute_mismatch_rejected_and_preserved', lambda: validate_compute(cards, [own, unexpected], {0: 100, 1: None}))
    receipts = list(root.glob('*.json'))
    assert len(receipts) == 1
    record = json.loads(receipts[0].read_bytes())
    assert record['compute'] == [own, unexpected] and record['not_model_NO'] and record['no_automatic_retry']
    rows.append({'case': 'full_UID_command_UUID_snapshot_preserved_before_reject', 'passed': True})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    old = (HERE.parent / 'flash-ample-memory-gui-20261114-linked11/package/primary_server.py').read_text(encoding='utf8')
    new = (P / 'primary_server.py').read_text(encoding='utf8')
    actor = lambda s: ast.dump(next(n for n in ast.parse(s).body if isinstance(n, ast.ClassDef) and n.name == 'NativeActor'), include_attributes=False)
    assert actor(old) == actor(new)
    startup = next(n for n in ast.parse(new).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    assert not any(isinstance(n, ast.Name) and n.id in ['capacity_run', 'install_validated'] for n in ast.walk(startup))
    rows.append({'case': 'NativeActor_unchanged_and_completed_capacity_entrypoint_absent', 'passed': True})
    manifest = json.loads((P / 'manifest.json').read_bytes())
    assert all(sha(P / name) == h for name, h in manifest['files'].items())
    save(HERE / 'CPU-admission-checks.json', {
        'time': time.time(), 'manifest_sha256': sha(P / 'manifest.json'), 'cases': rows,
        'passed': len(rows), 'forensic_simulation_seal_sha256': sha(root / 'seal.json'),
        'new_model_GUI_calls': 0, 'GPU_allocations': 0,
        'not_reexecution_of_completed_parent_capacity_controls': True,
        'current_real_weight_invariance_or_capacity_not_tested': True,
    })
    print(json.dumps({'passed': len(rows), 'new_model_GUI_calls': 0, 'receipt': str(HERE / 'CPU-admission-checks.json')}))


if __name__ == '__main__':
    main()
