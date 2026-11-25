"""Check the draft against sealed actual rows and accounting boundary cases."""
import copy
import json
import time
from pathlib import Path

from control import HERE, PACKAGE, save, sha
from join_reviewed_results import pointer, verify
from reserve_cumulative_accounting import combine_reviewed_rows


def main():
    old_binding = json.loads((PACKAGE / 'previous-completed-campaign.json').read_bytes())['report']
    old_root = verify(old_binding['root'], old_binding['seal_sha256'])
    prior = json.loads((old_root / 'report.json').read_bytes())
    review_root, review_binding = pointer('review-checkpoint-current.json')
    current = json.loads((review_root / 'result.json').read_bytes())['rows']
    result = combine_reviewed_rows(prior, current)
    assert len(result['cumulative_rows']) == len(prior['rows']) + len(current)
    assert result['all_attempted_rows_preserved']
    # A subsequent reserve consumes the full cumulative ledger, without adding
    # the original two-per-mode baseline a second time.
    cumulative = {**prior, **result}
    second = combine_reviewed_rows(cumulative, [])
    assert second['cumulative_counts'] == result['cumulative_counts']
    assert second['cumulative_rows'] == result['cumulative_rows']
    failures = []

    def rejected(name, earlier, later):
        try:
            combine_reviewed_rows(earlier, later)
        except AssertionError:
            failures.append(name)
        else:
            raise AssertionError('An invalid accounting case was accepted: ' + name)

    rejected('same_run_duplicate', prior, [prior['rows'][0]])
    repeated = copy.deepcopy(prior['rows'][0])
    repeated['run_id'] = 'reserve-' + repeated['run_id']
    rejected('same_task_condition_new_run_id', prior, [repeated])
    wrong = copy.deepcopy(prior)
    wrong['successful_complete_trajectories_per_condition']['silent_drop'] += 1
    rejected('prior_count_disagrees_with_rows', wrong, current)
    clean = copy.deepcopy(next(row for row in prior['rows'] if row['condition'] == 'clean_control'))
    clean['user_normal_frame_delivery_passed'] = True
    rejected('clean_control_cannot_count_as_recovery', {**prior, 'rows': [clean]}, [])
    invalid = copy.deepcopy(current)
    victim = next(row for row in invalid if row.get('user_normal_frame_delivery_passed'))
    victim['user_normal_frame_delivery_passed'] = 'true'
    rejected('truthy_string_is_not_verified_success', prior, invalid)
    root = HERE / ('reserve-accounting-qualification-' + str(time.time_ns()))
    root.mkdir()
    save(root / 'result.json', {
        'scope': 'local cumulative-accounting draft; not a reserve runtime package',
        'prior_report_binding': old_binding, 'reviewed_prefix_binding': review_binding,
        'actual_terminal_rows_checked': len(result['cumulative_rows']),
        'actual_prefix_counts': result['cumulative_counts'],
        'completed_failures_and_clean_controls_preserved': True,
        'second_chain_without_double_baseline_count_passed': True,
        'rejected_boundary_cases': failures,
        'initial_campaign_may_still_be_running': True,
        'unchanged_current_runtime': True, 'new_visual_labels': 0,
        'new_model_GUI_calls': 0, 'reserve_package_ready': False,
        'reserve_preparation_requires_completed_initial_report_and_actual_release': True,
    })
    for name in ['reserve_cumulative_accounting.py', 'qualify_reserve_accounting.py']:
        (root / name).write_bytes((HERE / name).read_bytes())
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    verify(root)
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                      'actual_prefix_counts': result['cumulative_counts'],
                      'boundary_cases_rejected': len(failures), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
