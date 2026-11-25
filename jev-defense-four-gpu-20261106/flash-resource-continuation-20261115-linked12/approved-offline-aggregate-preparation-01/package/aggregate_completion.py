"""Require all 29 logical GUI configurations across the immutable stopped and new roots.

The stopped parent remains a technical failure. Sixteen retained terminals plus
thirteen normally finished continuation terminals establish coverage; its failed
partial T089 attempt, source occurrences and costs remain separate and preserved.
"""
import json
from pathlib import Path


def validate_cover(parent_rows, current_rows, expected, contract):
    assert len(expected) == len(set(expected)) == 29
    assert len(parent_rows) == 17 and len(current_rows) == 13
    completed = [v for v in parent_rows if not v['infrastructure_failure']]
    technical = [v for v in parent_rows if v['infrastructure_failure']]
    assert len(completed) == 16 and len(technical) == 1
    assert {v['run_id'] for v in completed} == set(contract['normal_completed_run_ids'])
    assert technical[0]['run_id'] == contract['failed_attempt_preserved']['run_id']
    assert technical[0]['terminal_sha256'] == contract['failed_attempt_preserved']['terminal_sha256']
    assert technical[0]['seal_sha256'] == contract['failed_attempt_preserved']['seal_sha256']
    assert all(not v['infrastructure_failure'] and not v['cleanup_error'] for v in current_rows)
    assert {v['run_id'] for v in current_rows} == {v['run_id'] for v in contract['remaining_queue']}
    normal = completed + current_rows
    assert len(normal) == len({v['run_id'] for v in normal}) == 29
    assert {v['run_id'] for v in normal} == set(expected)
    assert all(v['seal_verified'] and v['chain_verified'] and not v['cleanup_error'] for v in parent_rows + current_rows)
    return normal, technical


def validate(package, parent_status, parent_terminal, parent_group, admission, expected):
    # Importing the existing guard provides its frozen source verifier only;
    # no launcher, model, browser or scorer is entered by this metadata gate.
    import offline_guard as guard
    from resource_guard import identity
    b = guard.load(package / 'aggregate-bindings.json')
    parent = Path(b['parent_output'])
    current = Path(b['continuation_output'])
    current_package = Path(b['continuation_package'])
    assert guard.sha(parent / 'postexit-seal.json') == b['parent_postexit_seal_sha256']
    assert guard.sha(Path(b['parent_package']) / 'manifest.json') == b['parent_manifest_sha256']
    assert parent_status['phase'] == 'technical_failure' and parent_status['done'] == 16
    assert parent_status['attempted_actor_calls'] == 397 and parent_status['complete_actor_replies'] == 396
    assert parent_terminal['done'] == 16 and parent_terminal['expected'] == 29
    assert parent_group['exit_code'] == 1 and parent_group['failure'] is None
    assert guard.sha(current_package / 'manifest.json') == b['continuation_manifest_sha256']
    manifest = guard.load(current_package / 'manifest.json')
    for name, digest in manifest['files'].items():
        assert guard.sha(current_package / name) == digest, name
    status = guard.load(current / 'primary/status.json')
    terminal = guard.load(current / 'primary/terminal.json')
    group = guard.load(current / 'exit.json')
    assert status['phase'] == 'completed' and status['done'] == status['expected'] == 13 and status['active'] is None
    assert terminal['status'] == 'completed' and terminal['done'] == terminal['expected'] == 13
    assert terminal['attempted_actor_calls'] == terminal['complete_actor_replies']
    assert group['exit_code'] == 0 and group['failure'] is None and all(v['exit_code'] == 0 for v in group['children'])
    assert admission['continuation_native_postexit_seal_sha256'] == guard.sha(current / 'postexit-seal.json')
    seal = guard.load(current / 'postexit-seal.json')
    for name in ['primary/status.json', 'primary/terminal.json', 'exit.json', 'expanded-lease.json']:
        assert guard.sha(current / name) == seal[name]
    assert admission['parent_native_postexit_seal_sha256'] == b['parent_postexit_seal_sha256']
    assert admission['parent_manifest_sha256'] == b['parent_manifest_sha256']
    assert admission['continuation_manifest_sha256'] == b['continuation_manifest_sha256']
    assert admission['actual_GUI_processes_exited'] and admission['actual_model_and_launcher_processes_exited']
    assert admission['parent_GUI_child_exit'] == 0 and admission['continuation_GUI_child_exit'] == 0
    assert admission['parent_GUI_phase'] == 'technical_failure' and admission['continuation_GUI_phase'] == 'completed'
    normal, technical = validate_cover(admission['parent_terminals'], admission['continuation_terminals'], expected, b['contract'])
    assert admission['terminals'] == normal and admission['preserved_technical_attempts'] == technical
    assert len(normal) == 29 and len(technical) == 1
    assert admission['failed_partial_costs_and_source_occurrences_retained']
    assert admission['stopped_parent_relabelled_completed'] is False
    # Recheck all model process identities at actual submission and again in
    # the launcher. Old PIDs and a boolean "running" flag are never sufficient.
    paths = [parent / 'launcher-process.json', parent / 'primary/process.json',
             Path(b['parent_package']) / 'flash/service/process.json', current / 'launcher-process.json',
             current / 'primary/process.json', current_package / 'flash/service/process.json']
    for path in paths:
        saved = guard.load(path)
        proc = Path('/proc', str(saved['pid']))
        actual = identity(saved['pid']) if proc.exists() else None
        same = actual is not None and actual['state'] not in ['Z', 'X'] and all(actual[k] == saved[k] for k in ['uid', 'command', 'start_ticks'])
        assert not same, 'GUI model group still active; offline study remains unsubmitted'
    assert guard.sha(package / 'development-plan.json') == b['authorized_plan_sha256']
    assert guard.sha(package / 'native/manifest.json') == b['parent_manifest_sha256']
