"""Qualify exact interrupted-parent continuation metadata, without inference."""
import ast
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, manifest, save, sha
from join_reviewed_results import verify
from reserve_cumulative_accounting import counts_from_rows, combine_reviewed_rows
from write_reserve_report import previous_cohorts

BASE = HERE.parent / 'flash-four-mode-scale10-20261116-12'


def function_ast(source, name):
    return ast.dump(next(n for n in ast.parse(source).body
                         if isinstance(n, ast.FunctionDef) and n.name == name))


def assessment_loop(source):
    main = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    return ast.dump(next(n for n in main.body if isinstance(n, ast.For)
                         and isinstance(n.target, ast.Name) and n.target.id == 'audit_root'))


def replace_exact(text, before, after, count=1):
    assert text.count(before) == count, before
    return text.replace(before, after)


def main():
    assert HERE != BASE and not (HERE / 'CPU-routing-current.json').exists()
    prep = json.loads((HERE / 'preparation-current.json').read_bytes())
    prep_root = verify(prep['root'], prep['seal_sha256'])
    m = manifest()
    assert prep['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    assert m['same_protocol_unstarted_continuation_metadata_only'] is True and m['trajectories'] == 26
    parent_prep = json.loads((BASE / 'preparation-current.json').read_bytes())
    oldp = Path(parent_prep['package'])
    parent = json.loads((oldp / 'manifest.json').read_bytes())
    assert (PACKAGE / 'source-parent-manifest.json').read_bytes() == (oldp / 'manifest.json').read_bytes()
    assert sha(oldp / 'manifest.json') == m['source_parent_manifest_sha256']
    for name, digest in m['files'].items():
        assert sha(PACKAGE / name) == digest, name
    assert sha(PACKAGE / 'private.token') == m['auth_token_sha256']
    binding = m['unstarted_parent_binding']
    report_root = verify(binding['root'], binding['seal_sha256'])
    report = json.loads((report_root / 'report.json').read_bytes())
    unstarted = json.loads((report_root / 'unstarted-plan.json').read_bytes())
    queue = unstarted['exact_unstarted_queue']
    assert queue == m['remaining_queue'] == parent['remaining_queue'][14:]
    assert len(queue) == len({r['run_id'] for r in queue}) == 26
    assert len({(r['task_id'], r['condition']) for r in queue}) == 26
    assert all(r['gate_enabled'] is True for r in queue)
    assert not ({r['run_id'] for r in queue} & {r['run_id'] for r in report['rows']})
    distribution = {c: sum(r['condition'] == c for r in queue)
                    for c in ['silent_drop', 'blank_replace', 'stale_replace', 'buttons_only', 'clean_control']}
    assert distribution == dict(silent_drop=5, blank_replace=5, stale_replace=5, buttons_only=5, clean_control=6)
    assert (PACKAGE / 'current-unstarted-plan.json').read_bytes() == (report_root / 'unstarted-plan.json').read_bytes()
    plan = json.loads((PACKAGE / 'plan.json').read_bytes())
    oldplan = json.loads((oldp / 'plan.json').read_bytes())
    allowed = {'version', 'created', 'queue', 'expected_trajectories', 'tasks',
        'current_user_authorization_sha256', 'unstarted_parent_binding',
        'prior_verified_per_condition', 'acceptance', 'interpretation'}
    differences = {k for k in set(oldplan) | set(plan) if oldplan.get(k) != plan.get(k)}
    assert differences <= allowed, differences - allowed
    assert plan['queue'] == queue and plan['expected_trajectories'] == 26
    ids = list(dict.fromkeys(r['task_id'] for r in queue))
    assert ids == [17, 58, 89, 94, 112, 131]
    assert plan['tasks'] == [r for r in oldplan['tasks'] if r['task_id'] in ids]
    assert plan['acceptance']['required'] == oldplan['acceptance']['required']
    assert plan['acceptance']['normal_frame_primary_text_accuracy_required'] is False
    assert plan['acceptance']['all_failures_preserved'] is True
    native = json.loads((PACKAGE / 'native-bindings-public.json').read_bytes())
    oldnative = json.loads((oldp / 'native-bindings-public.json').read_bytes())
    assert native['tasks'] == [r for r in oldnative['tasks'] if r['task_id'] in ids]
    assert native['prospective_plan_SHA'] == sha(PACKAGE / 'plan.json')
    assert m['Flash_contract_sha256'] == sha(PACKAGE / 'flash/gate-contract.json') == plan['single_image_quality_contract_sha256']
    assert m['main_physical_gpus'] == list(range(7)) and m['Flash_physical_gpu'] == 7
    invariants = json.loads((prep_root / 'source-invariance.json').read_bytes())['unchanged_runtime_files']
    for name, digest in invariants.items():
        assert digest == sha(oldp / name) == sha(PACKAGE / name), name
    allowed_changes = {'user-current-authorization.json', 'plan.json', 'native-bindings-public.json',
        'analysis-plan.json', 'previous-completed-campaign.json', 'source-parent-manifest.json',
        'continuation_guard.py', 'launch_group.py'}
    changed = {name for name in parent['files'] if sha(PACKAGE / name) != parent['files'][name]}
    assert changed <= allowed_changes, changed - allowed_changes
    for name in parent['files']:
        if name not in allowed_changes:
            assert sha(PACKAGE / name) == sha(oldp / name), name
    oldlaunch = (oldp / 'launch_group.py').read_text('utf8')
    expected_launch = replace_exact(oldlaunch, repr('jev-four-mode-scale10-20261116-12.lock'), repr('jev-' + HERE.name + '.lock'))
    assert (PACKAGE / 'launch_group.py').read_text('utf8') == expected_launch
    oldguard = (oldp / 'continuation_guard.py').read_text('utf8')
    guard = (PACKAGE / 'continuation_guard.py').read_text('utf8')
    for function in ['verify_native_parent', 'verify_gui_parent']:
        assert function_ast(guard, function) == function_ast(oldguard, function)
    # Every original ancestor assertion remains before the new interruption
    # assertions. Normalize only the intended study and queue constants.
    normalized_oldguard = oldguard.replace(repr(parent['study']), repr(m['study'])).replace("manifest['trajectories'] == 40", "manifest['trajectories'] == 26")
    oldfn = next(n for n in ast.parse(normalized_oldguard).body if isinstance(n, ast.FunctionDef) and n.name == 'verify_completed')
    newfn = next(n for n in ast.parse(guard).body if isinstance(n, ast.FunctionDef) and n.name == 'verify_completed')
    assert ast.dump(ast.Module(body=oldfn.body[:-1], type_ignores=[])) == ast.dump(ast.Module(body=newfn.body[:len(oldfn.body)-1], type_ignores=[]))
    assert "assert interrupted['parent_preserved_interruption_not_completed']" in guard
    assert "assert interrupted['infrastructure_terminals'] == 1 and interrupted['exact_unstarted_count'] == 26" in guard
    for host in ['3090', '4090']:
        proof = json.loads((PACKAGE / ('interrupted-parent-' + host + '.json')).read_bytes())['result']
        assert proof['parent_manifest_sha256'] == m['source_parent_manifest_sha256']
        assert proof['parent_preserved_interruption_not_completed'] and proof['all_original_identities_exited_and_locks_absent']
        assert proof['unstarted_run_ids'] == [r['run_id'] for r in queue]
        assert len(proof['lock_checks']) == (17 if host == '3090' else 1)
        assert not any(row['kernel_locks'] for row in proof['lock_checks'])
    # The complete actual ledger, including the infrastructure failure, is
    # accepted once. A duplicate attempted row must fail before publication.
    cohorts = previous_cohorts(binding)
    rows = [row for c in cohorts for row in c['report']['rows']]
    counts = counts_from_rows(rows)
    assert len(cohorts) == 2 and len(rows) == 24 and rows == report['cumulative_rows']
    assert counts == m['prior_verified_per_condition'] == dict(silent_drop=4, blank_replace=4, stale_replace=3, buttons_only=3)
    assert sum(r.get('infrastructure_failure', False) for r in rows) == 1
    assert all(not r.get('user_normal_frame_delivery_passed', False) for r in rows if r.get('infrastructure_failure', False))
    hypothetical = [{'run_id': r['run_id'], 'condition': r['condition'], 'user_normal_frame_delivery_passed': False} for r in queue]
    prospective = combine_reviewed_rows(report, hypothetical)
    assert len(prospective['cumulative_rows']) == 50 and prospective['cumulative_counts'] == counts
    try:
        counts_from_rows(rows + [rows[-1]])
    except AssertionError:
        pass
    else:
        raise AssertionError('Duplicate terminal was not rejected')
    for member, transformations in {
        'control.py': [("m['trajectories']==40", "m['trajectories']==26", 1),
                       ("h['expected']==40", "h['expected']==26", 1),
                       ("'expected_trajectories':40", "'expected_trajectories':26", 1)],
        'bound_request_audit_reuse.py': [('assert len(run_ids) == 40', 'assert len(run_ids) == 26', 1)],
        'audit_completed_group_bound_reuse.py': [("status['expected']==40", "status['expected']==26", 2),
            ('<=40*70', '<=26*70', 1), ('len(controllers)==40', 'len(controllers)==26', 1),
            ("'target_per_condition': 8", "'target_per_condition': 5", 1)]}.items():
        expected = (BASE / member).read_text('utf8')
        for before, after, count in transformations:
            expected = replace_exact(expected, before, after, count)
        assert (HERE / member).read_text('utf8') == expected, member
    from audit_completed_group_bound_reuse import readers
    _, sources = readers()
    # Read the original readers in isolation with its original location.
    old_readers_source = (BASE / 'audit_completed_group_bound_reuse.py').read_text('utf8')
    reader_fn = next(n for n in ast.parse(old_readers_source).body if isinstance(n, ast.FunctionDef) and n.name == 'readers')
    namespace = {'ast': ast, 'HERE': BASE, 'Path': Path}
    exec(compile(ast.Module(body=[reader_fn], type_ignores=[]), 'original-reader-definition', 'exec'), namespace)
    _, original_sources = namespace['readers']()
    for name in ['COMMON', 'PRIMARY', 'FLASH']:
        assert sources[name] == original_sources[name], name
    assert function_ast((HERE / 'bound_request_audit_reuse.py').read_text('utf8'), 'strict_bind') == function_ast((BASE / 'bound_request_audit_reuse.py').read_text('utf8'), 'strict_bind')
    join = (HERE / 'join_reviewed_results.py').read_text('utf8')
    original_join = (BASE / 'join_reviewed_results.py').read_text('utf8')
    assert assessment_loop(join) == assessment_loop(original_join)
    for name in ['verify', 'pointer']:
        assert function_ast(join, name) == function_ast(original_join, name)
    assert "group['processed_GUI_trajectories'] == 26" in join
    assert "len({v['run_id'] for v in clean}) == 6" in join
    assert "'clean_control_trajectories': 6" in join
    assert 'ledger = combine_reviewed_rows(prior_report, rows)' in join
    assert 'v+2' not in join
    for member in ['audit_finished_trajectory.py', 'protocol_audit_components.py', 'watch_campaign_review_linked.py',
                   'reserve_cumulative_accounting.py', 'write_reserve_report.py', 'export_sealed_capture_prefix.py']:
        assert sha(HERE / member) == sha(BASE / member), member
    for path in list(HERE.glob('*.py')) + list(PACKAGE.rglob('*.py')):
        compile(path.read_text('utf8'), str(path), 'exec')
    old_study = HERE.parent / 'flash-native-source-loop-20261116-linked11'
    reused = []
    for name in ['CPU-routing-current.json', 'CPU-source-current.json']:
        proof = json.loads((old_study / name).read_bytes())
        assert proof['passed']
        verify(proof['root'], proof['seal_sha256'])
        reused.append({'pointer': str(old_study / name), 'pointer_sha256': sha(old_study / name),
                       'proof': proof, 'new_control_executions': 0})
    root = HERE / ('cpu-unstarted26-metadata-qualification-' + str(time.time_ns())); root.mkdir()
    save(root / 'result.json', {'passed': True, 'manifest_sha256': prep['manifest_sha256'],
        'original_exact_unstarted_queue_only': True, 'expected_trajectories': 26, 'conditions': distribution,
        'attempted14_including_infrastructure_terminal_excluded': True,
        'parent_interruption_retained_not_relabelled_completed': True,
        'prior_actual_ledger_rows': 24, 'prior_cohorts': 2, 'prior_counts': counts,
        'resource_cost_cohorts_counted_once': True, 'duplicate_terminal_rejected': True,
        'hypothetical_26_failure_rows_change_no_success_counts': True,
        'raw_COMMON_PRIMARY_FLASH_and_strict_bind_identical': True,
        'complete_original_image_assessment_loop_identical': True,
        'same_native_full_input_history_precision_gate_capture_and_dispatch_sources': True,
        'reused_unchanged_routing_and_source_qualifications': reused,
        'algorithm_control_reexecutions': 0, 'new_model_GUI_calls': 0,
        'fresh_actual_eight_GPU_admission_still_required': True})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    save(HERE / 'CPU-routing-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
        'passed': True, 'manifest_sha256': prep['manifest_sha256'],
        'qualification_type': 'exact original unstarted26 metadata; source-identical qualification reuse'})
    managers = ['control.py', 'collect_progress.py', 'inspect_owned_runtime.py',
        'audit_finished_trajectory.py', 'audit_completed_group_bound_reuse.py', 'bound_request_audit_reuse.py',
        'protocol_audit_components.py', 'export_examples_sealed.py', 'watch_campaign_review_linked.py',
        'export_review_frames.py', 'export_sealed_capture_prefix.py', 'build_review_sheets.py',
        'bind_terminal_image_reviews.py', 'review_checkpoint.py', 'join_reviewed_results.py',
        'audit_resource_interval.py', 'audit_released_resources.py', 'audit_gui_site_lock.py',
        'reserve_cumulative_accounting.py', 'write_reserve_report.py', 'qualify_unstarted_continuation.py']
    audit = HERE / ('audit-preparation-' + str(time.time_ns())); audit.mkdir()
    for name in managers:
        (audit / name).write_bytes((HERE / name).read_bytes())
    save(audit / 'result.json', {'scope': 'unstarted26 read-only auditors; complete strict raw readers unchanged',
        'expected_trajectories': 26, 'normal_controls': 6, 'manifest_sha256': prep['manifest_sha256'],
        'files': {name: sha(HERE / name) for name in managers}, 'new_model_GUI_calls': 0})
    save(audit / 'seal.json', {p.name: sha(p) for p in audit.iterdir() if p.is_file()})
    save(HERE / 'audit-preparation-current.json', {'root': str(audit), 'seal_sha256': sha(audit / 'seal.json')})
    print(json.dumps({'root': str(root), 'passed': True, 'trajectories': 26, 'clean_controls': 6,
        'prior_counts': counts, 'new_model_GUI_calls': 0, 'fresh_actual_eight_GPU_admission_still_required': True}))


if __name__ == '__main__':
    main()
