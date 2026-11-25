"""CPU metadata/source qualification of a future prepared reserve; no calls."""
import ast
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, manifest, save, sha
from join_reviewed_results import verify

BASE_NAME = 'flash-four-mode-scale10-20261116-12'


def function_ast(path, name):
    return ast.dump(next(node for node in ast.parse(Path(path).read_text('utf8')).body
                         if isinstance(node, ast.FunctionDef) and node.name == name))


def main():
    assert not (HERE / 'CPU-routing-current.json').exists()
    base = HERE.parent / BASE_NAME
    assert HERE != base, 'The running initial campaign must retain its original qualification'
    prep = json.loads((HERE / 'preparation-current.json').read_bytes())
    prep_root = verify(prep['root'], prep['seal_sha256'])
    m = manifest()
    assert sha(PACKAGE / 'manifest.json') == prep['manifest_sha256']
    assert m['same_protocol_reserve_metadata_only'] is True
    count = m['trajectories']
    assert 2 <= count <= 5
    parent = json.loads((PACKAGE / 'source-parent-manifest.json').read_bytes())
    assert sha(PACKAGE / 'source-parent-manifest.json') == m['source_parent_manifest_sha256']
    for member, digest in m['files'].items():
        assert sha(PACKAGE / member) == digest, member
    assert sha(PACKAGE / 'private.token') == m['auth_token_sha256']
    invariants = json.loads((prep_root / 'source-invariance.json').read_bytes())['unchanged_runtime_files']
    for member, digest in invariants.items():
        assert sha(PACKAGE / member) == parent['files'][member] == digest, member
    plan = json.loads((PACKAGE / 'plan.json').read_bytes())
    reserve = json.loads((PACKAGE / 'current-reserve-plan.json').read_bytes())
    assert len(plan['queue']) == count == plan['expected_trajectories']
    assert plan['queue'] == m['remaining_queue']
    assert len({row['run_id'] for row in plan['queue']}) == count
    assert len(plan['tasks']) == 1 and plan['tasks'][0]['task_id'] == reserve['next_task_id']
    assert [row['condition'] for row in plan['queue']] == reserve['conditions']
    assert all(row['task_id'] == reserve['next_task_id'] for row in plan['queue'])
    assert sum(row['condition'] == 'clean_control' for row in plan['queue']) == 1
    assert len({(row['task_id'], row['condition']) for row in plan['queue']}) == count
    reserve_root = verify(m['reserve_plan_binding']['root'], m['reserve_plan_binding']['seal_sha256'])
    assert (PACKAGE / 'current-reserve-plan.json').read_bytes() == (reserve_root / 'plan.json').read_bytes()
    native = json.loads((PACKAGE / 'native-bindings-public.json').read_bytes())
    assert native['prospective_plan_SHA'] == sha(PACKAGE / 'plan.json')
    assert native['tasks'] == [reserve['task_binding']]
    assert all(row['eligible'] and row['eval_types'] == ['url_match'] and row['image'] is None
               and row['require_reset'] is False for row in native['tasks'])
    assert m['Flash_contract_sha256'] == sha(PACKAGE / 'flash/gate-contract.json') == plan['single_image_quality_contract_sha256']
    auth = json.loads((PACKAGE / 'user-current-authorization.json').read_bytes())
    assert auth['new_trusted_capture_protocol_authorized'] and auth['same_protocol_scaleup_authorized']
    assert auth['no_old_terminal_rerun'] and auth['no_expanded_per_trajectory_or_paid_budget']
    # Compare the complete original plan locally from the parent preparation,
    # without reaching out to a service or substituting a shorter history.
    parent_report = reserve['completed_campaign_report']
    parent_study = Path(parent_report['root']).parent
    parent_prep = json.loads((parent_study / 'preparation-current.json').read_bytes())
    previous_plan = json.loads((Path(parent_prep['package']) / 'plan.json').read_bytes())
    allowed = {'version', 'protocol_version', 'created', 'tasks', 'queue', 'expected_trajectories',
               'current_user_authorization_sha256', 'reserve_plan_binding',
               'prior_verified_per_condition', 'acceptance', 'interpretation'}
    differences = {key for key in set(previous_plan) | set(plan) if previous_plan.get(key) != plan.get(key)}
    assert differences <= allowed, differences - allowed
    assert plan['acceptance']['required'] == previous_plan['acceptance']['required']
    assert plan['acceptance']['normal_frame_primary_text_accuracy_required'] is False
    assert plan['acceptance']['all_failures_preserved'] is True
    assert sha(PACKAGE / 'native-parser-source.py') == parent['files']['native-parser-source.py']

    # These exact count-only variants were qualified before any reserve call.
    reader_root = verify(base / 'reserve-reader-metadata-staging-1794841585726283000',
                         '133b3d5dc9ec04f7900fa329c1b7a80b1675eea158147df5acf775534fd5c5e0')
    join_root = verify(base / 'reserve-join-metadata-staging-1794847763748042900',
                       '055c3e655dd5a920eb88014136bc5ec32f4d3b728af202b4c3ea39f9453e545a')
    for member in ['control.py', 'audit_completed_group_bound_reuse.py', 'bound_request_audit_reuse.py']:
        assert sha(HERE / member) == sha(reader_root / ('count-%d' % count) / member)
    assert sha(HERE / 'join_reviewed_results.py') == sha(join_root / ('count-%d' % count) / 'join_reviewed_results.py')
    for member in ['audit_finished_trajectory.py', 'protocol_audit_components.py',
                   'watch_campaign_review_linked.py', 'reserve_cumulative_accounting.py']:
        assert sha(HERE / member) == sha(base / member)
    assert function_ast(HERE / 'bound_request_audit_reuse.py', 'strict_bind') == function_ast(base / 'bound_request_audit_reuse.py', 'strict_bind')
    from audit_completed_group_bound_reuse import readers
    _, values = readers()
    assert "status['expected']==%d" % count in values['ADMISSION']
    assert "status['expected']==%d" % count in values['GUI']
    for source in list(HERE.glob('*.py')) + list(PACKAGE.rglob('*.py')):
        ast.parse(source.read_text('utf8'))
    old = HERE.parent / 'flash-native-source-loop-20261116-linked11'
    reused = []
    for name in ['CPU-routing-current.json', 'CPU-source-current.json']:
        proof = json.loads((old / name).read_bytes())
        assert proof['passed']
        verify(proof['root'], proof['seal_sha256'])
        reused.append({'pointer': str(old / name), 'pointer_sha256': sha(old / name),
                       'proof': proof, 'new_control_executions': 0})
    root = HERE / ('cpu-reserve-metadata-qualification-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'result.json', {
        'passed': True, 'manifest_sha256': prep['manifest_sha256'],
        'new_task_id': reserve['next_task_id'], 'conditions': reserve['conditions'],
        'expected_trajectories': count, 'one_matched_clean_control': True,
        'original_plan_nonmetadata_fields_identical': True,
        'same_native_full_input_history_precision_gate_capture_and_dispatch_sources': True,
        'qualified_count_only_raw_audit_and_join_sources_identical': True,
        'reused_unchanged_routing_and_source_qualifications': reused,
        'algorithm_control_reexecutions': 0, 'new_model_GUI_calls': 0,
        'fresh_actual_GPU_admission_still_required': True,
    })
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(HERE / 'CPU-routing-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
        'passed': True, 'manifest_sha256': prep['manifest_sha256'],
        'qualification_type': 'reserve metadata and exact source-identical qualification reuse'})
    managers = ['audit_finished_trajectory.py', 'audit_completed_group_bound_reuse.py',
                'bound_request_audit_reuse.py', 'protocol_audit_components.py',
                'export_examples_sealed.py', 'watch_campaign_review_linked.py',
                'export_review_frames.py', 'build_review_sheets.py', 'review_checkpoint.py',
                'join_reviewed_results.py', 'audit_resource_interval.py',
                'audit_released_resources.py', 'audit_gui_site_lock.py',
                'reserve_cumulative_accounting.py', 'write_reserve_report.py']
    audit = HERE / ('audit-preparation-' + str(time.time_ns()))
    audit.mkdir()
    for member in managers:
        (audit / member).write_bytes((HERE / member).read_bytes())
    save(audit / 'result.json', {'scope': 'future reserve read-only auditors; unchanged strict raw readers',
         'expected_trajectories': count, 'manifest_sha256': prep['manifest_sha256'],
         'files': {name: sha(HERE / name) for name in managers}, 'new_model_GUI_calls': 0})
    save(audit / 'seal.json', {p.name: sha(p) for p in audit.iterdir() if p.is_file()})
    save(HERE / 'audit-preparation-current.json', {'root': str(audit), 'seal_sha256': sha(audit / 'seal.json')})
    print(json.dumps({'root': str(root), 'passed': True, 'trajectories': count,
                      'new_model_GUI_calls': 0, 'fresh_actual_GPU_admission_still_required': True}))


if __name__ == '__main__':
    main()
