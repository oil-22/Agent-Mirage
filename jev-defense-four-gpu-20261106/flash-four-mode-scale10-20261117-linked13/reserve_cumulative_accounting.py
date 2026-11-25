"""Local-only cumulative accounting draft for later, separately frozen reserves.

This consumes existing delivery assessments; it does not assess images, call a
model, alter a terminal, or certify that a running campaign has finished.
"""
import re

MODES = ('silent_drop', 'blank_replace', 'stale_replace', 'buttons_only')


def counts_from_rows(rows):
    seen_ids, seen_pairs = set(), set()
    counts = dict.fromkeys(MODES, 0)
    for row in rows:
        run_id, condition = row['run_id'], row['condition']
        assert condition in (*MODES, 'clean_control'), condition
        assert run_id not in seen_ids, 'A terminal must not be counted twice'
        seen_ids.add(run_id)
        match = re.search(r'(?:^|-)T([0-9]+)(?:-|$)', run_id)
        assert match, 'The task must be bound to the original run identifier'
        pair = (int(match.group(1)), condition)
        assert pair not in seen_pairs, 'A completed task/condition must not be rerun'
        seen_pairs.add(pair)
        passed = row.get('user_normal_frame_delivery_passed', False)
        assert type(passed) is bool, 'Only an actual boolean assessment is accepted'
        if condition == 'clean_control':
            assert passed is False, 'A clean control is not an injection recovery'
        elif passed:
            assert row['wire_normal_frame_delivery_verified'] is True
            assert row['environment_action_after_recovery'] is True or row['valid_native_STOP_after_recovery'] is True
            assert row['recaptures'] >= 1
            assert sum(row[name] for name in ('precheck_NO', 'source_NO', 'Flash_NO')) >= 1
            counts[condition] += 1
    return counts


def combine_reviewed_rows(prior_report, current_rows):
    """Carry forward the entire prior ledger once, including every failed row."""
    previous = prior_report.get('cumulative_rows', prior_report['rows'])
    prior_counts = counts_from_rows(previous)
    declared = prior_report.get('cumulative_counts', prior_report['successful_complete_trajectories_per_condition'])
    assert prior_counts == declared, 'Declared prior counts must match actual rows'
    new_counts = counts_from_rows(current_rows)
    combined = [*previous, *current_rows]
    total = counts_from_rows(combined)
    assert total == {mode: prior_counts[mode] + new_counts[mode] for mode in MODES}
    return {
        'prior_counts': prior_counts,
        'new_counts': new_counts,
        'cumulative_counts': total,
        'cumulative_rows': combined,
        'all_four_modes_at_least_ten_successes': all(value >= 10 for value in total.values()),
        'injection_rows_without_complete_recovery': [
            row for row in combined if row['condition'] != 'clean_control'
            and row.get('user_normal_frame_delivery_passed', False) is False
        ],
        'clean_control_rows': [row for row in combined if row['condition'] == 'clean_control'],
        'all_attempted_rows_preserved': len(combined) == len(previous) + len(current_rows),
        'whole_group_audit_release_cost_report_certified_here': False,
        'new_model_GUI_calls': 0,
    }
