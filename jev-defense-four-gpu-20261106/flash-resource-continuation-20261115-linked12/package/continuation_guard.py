"""Admit only the exact 13 remaining configurations and preserved stopped parent."""
import json
import os
from pathlib import Path


def validate_leased_UUIDs(original_lease, current_cards):
    bound = {r['index']: r['uuid'] for r in original_lease['gpu']}
    assert set(bound) == {4, 5, 6, 7}
    for index, expected in bound.items():
        assert current_cards[index]['uuid'] == expected, 'Original physical GPU/held UUID lock binding changed'


def validate_contract(plan, contract, original):
    assert plan['queue'] == contract['remaining_queue']
    assert len(plan['queue']) == plan['expected_trajectories'] == 13
    normal = set(contract['normal_completed_run_ids'])
    assert len(normal) == 16
    assert plan['queue'] == [v for v in original['queue'] if v['run_id'] not in normal]
    assert len(original['queue']) == 29
    assert not normal.intersection(v['run_id'] for v in plan['queue'])
    assert plan['tasks'] == original['tasks']
    for key in ['max_steps', 'max_actor_calls_per_trajectory', 'actor_output_tokens', 'browser_seed',
                'actor_seed', 'NO', 'recapture_limit', 'auxiliary_call_cap', 'conditions', 'injection',
                'gate', 'recapture_seconds', 'native_main_history', 'contextual_judge',
                'main_gpu_physical', 'Flash_gpu_physical', 'placement', 'primary_allocator_limit_fraction',
                'CUDA_LAUNCH_BLOCKING', 'native_unused_cache_GC_threshold', 'in_forward_allocator_cache_purge']:
        assert plan[key] == original[key], key
    assert plan['queue'][0]['run_id'] == contract['failed_attempt_preserved']['run_id']
    assert contract['new_linked_attempt_required']
    assert contract['failed_T089_source_positive_remains_in_any_logical_aggregate_despite_retry']
    assert contract['parent_partial_attempt_costs_and_actions_remain_separate_not_erased']


def verify_exited(records, identity):
    rows = []
    for record in records:
        p = Path('/proc', str(record['pid']))
        actual = identity(record['pid']) if p.exists() else None
        same = actual is not None and actual['state'] not in ['Z', 'X'] and all(actual[k] == record[k] for k in ['uid', 'command', 'start_ticks'])
        assert not same, 'Parent process is still active'
        rows.append({'saved': record, 'actual_if_PID_exists': actual, 'same_live_process': False})
    return rows


def verify_native_parent(package):
    from resource_guard import identity, sha
    b = json.loads((package / 'parent-bindings.json').read_bytes())
    p, r = Path(b['package3090']), Path(b['output3090'])
    assert sha(p / 'manifest.json') == b['manifest_sha256']
    manifest = json.loads((p / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(p / name) == expected, name
    assert sha(r / 'postexit-seal.json') == b['postexit_seal_sha256']
    assert sha(r / 'capacity/seal.json') == b['capacity_seal_sha256']
    assert sha(Path(b['failure_snapshot3090']) / 'seal.json') == b['failure_snapshot3090_seal_sha256']
    status = json.loads((r / 'primary/status.json').read_bytes())
    assert status['phase'] == 'technical_failure' and status['done'] == 16
    assert status['attempted_actor_calls'] == 397 and status['complete_actor_replies'] == 396
    assert json.loads((r / 'exit.json').read_bytes())['exit_code'] == 1
    failed = r / 'primary/requests/00397'
    assert sha(failed / 'seal.json') == b['failed_request_seal_sha256']
    assert (failed / 'failure.json').exists() and not (failed / 'response.json').exists()
    generated = json.loads((failed / 'actual-generation.json').read_bytes())
    assert generated['natural_EOS'] and generated['input_tokens'] == 28120 and generated['output_tokens'] == 32
    exited = verify_exited(b['processes3090'], identity)
    plan = json.loads((package / 'plan.json').read_bytes())
    contract = json.loads((package / 'technical-continuation-contract.json').read_bytes())
    validate_contract(plan, contract, json.loads((p / 'plan.json').read_bytes()))
    return {'actual_parent_processes_exited': exited, 'parent_sources': len(manifest['files']),
            'parent_postexit_seal_sha256': b['postexit_seal_sha256'], 'parent_failed_request_preserved': True,
            'remaining13_exact_original_queue_subset': True, 'all_old_raw_freshly_rehashed': False,
            'completed_capacity_controls_reexecuted': False, 'new_model_GUI_calls': 0}


def verify_gui_parent(package):
    from resource_guard import identity, sha
    b = json.loads((package / 'parent-bindings.json').read_bytes())
    r = Path(b['package4090'])
    assert sha(r / 'manifest.json') == b['manifest_sha256']
    assert sha(r / 'control/postexit-seal.json') == b['GUI_control_postexit_seal_sha256']
    for name, expected in json.loads((r / 'control/postexit-seal.json').read_bytes()).items():
        assert sha(r / 'control' / name) == expected
    assert sha(Path(b['failure_snapshot4090']) / 'seal.json') == b['failure_snapshot4090_seal_sha256']
    exited = verify_exited(b['processes4090'], identity)
    terminals = []
    for row in b['GUI_terminals']:
        path = Path(row['terminal'])
        assert sha(path) == row['terminal_sha256'] and sha(path.parent / 'seal.json') == row['seal_sha256']
        t = json.loads(path.read_bytes())
        assert t['run']['run_id'] == row['run_id'] and t['infrastructure_failure'] == row['infrastructure_failure']
        terminals.append({'run_id': row['run_id'], 'terminal_sha256': row['terminal_sha256'],
                          'seal_sha256': row['seal_sha256'], 'infrastructure_failure': row['infrastructure_failure']})
    assert len(terminals) == 17 and sum(not v['infrastructure_failure'] for v in terminals) == 16
    actual_paths = set((r / 'batch/runs').glob('*/attempt-*/terminal.json'))
    assert actual_paths == {Path(v['terminal']) for v in b['GUI_terminals']}
    validate_contract(json.loads((package / 'plan.json').read_bytes()),
                      json.loads((package / 'technical-continuation-contract.json').read_bytes()),
                      json.loads((r / 'plan.json').read_bytes()))
    return {'actual_parent_GUI_processes_exited': exited, 'parent_terminals_preserved': terminals,
            'only_remaining13': True, 'no_old_terminal_reexecution': True, 'new_model_GUI_calls': 0}
