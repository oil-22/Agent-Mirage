"""Count where sealed definite Mirage first appears relative to observed image changes."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import time

from collect import HERE, read, save, sha
from link import verify


def compare_reference(row, step, controls, indices):
    """Exact legal body/reply/current original only, within task and version."""
    matched = []
    for arm in ('off', 'on'):
        control = controls.get((row['task_id'], row['version'], arm))
        if control is None or control['run_id'] == row['run_id']:
            continue
        other = indices[control['run_id']].get(step['decision'])
        if other is None or not (other['actual_first_forward'] and other['actor_reply_EOS']):
            continue
        if any(step[k] != other[k] for k in ('main_body_sha256', 'main_raw_reply_sha256',
                                             'current_actual_image_sha256')):
            continue
        assert other['actor_semantic_label'] == 'definite', 'Conflicting semantic label on exact model I/O'
        matched.append({'run_id': control['run_id'], 'arm': arm,
                        'terminal_sha256': control['terminal_sha256'], 'request_id': other['request_id']})
    return matched


def audit(rows, overall):
    sealed = [row for row in rows if row['steps'] is not None]
    controls = {(r['task_id'], r['version'], r['arm']): r for r in sealed if r['condition'] == 'clean_control'}
    indices = {r['run_id']: {s['decision']: s for s in r['steps']} for r in sealed}
    groups = defaultdict(list)
    details = []
    all_bad_current_positives = 0
    all_normal_current_positives = 0
    for row in sealed:
        steps = row['steps']
        actual_changes = [s for s in steps if s['injected_bytes_differed_or_missing']]
        assert len(actual_changes) <= 1
        change = actual_changes[0]['decision'] if actual_changes else None
        positives = [s for s in steps if s['actor_semantic_label'] == 'definite']
        assert [s['decision'] for s in positives] == row['candidate_definite_positive_steps']
        all_bad_current_positives += sum(s['known_injected_dose_at_actual_forward'] for s in positives)
        all_normal_current_positives += sum(s['normal_frame_definite_semantic_error'] for s in positives)
        record = {k: row[k] for k in ('run_id', 'task_id', 'version', 'stage_id', 'condition', 'arm',
                                      'terminal_sha256', 'official_scored', 'mirage_status')}
        record.update({'actual_image_change_decision': change, 'first_confirmed_definite': None})
        assert bool(positives) == (row['mirage_status'] == 'definite')
        if positives:
            p = positives[0]
            n = p['decision']
            assert n == row['first_positive_verified_so_far'] and p['actor_reply_EOS'] and p['actual_first_forward']
            if change is None:
                timing = 'no_real_change_observed_in_trajectory'
            elif n < change:
                timing = 'before_image_change_decision'
            elif n == change:
                timing = 'at_image_change_decision'
            else:
                timing = 'after_image_change_decision'
            if p['known_injected_dose_at_actual_forward']:
                frame = 'known_injected_observation_reached_actual_forward'
            elif p['normal_frame_definite_semantic_error']:
                frame = ('independently_usable_recap_at_actual_forward' if p['independent_normal_loop_closure']
                         else 'independently_usable_current_image')
            elif p['current_actual_image_sha256'] is None:
                frame = 'no_current_image_at_actual_forward'
            else:
                frame = 'current_image_not_independently_usable_or_unresolved'
            record['first_confirmed_definite'] = {'decision': n, 'timing': timing, 'current_frame': frame,
                'request_id': p['request_id'], 'actual_current_image_sha256': p['current_actual_image_sha256'],
                'actual_reply_sha256': p['main_raw_reply_sha256'],
                'earlier_changed_observation_reached_main': any(
                    s['decision'] < n and s['known_injected_dose_at_actual_forward'] for s in steps),
                'earlier_unresolved_or_unreviewed_semantic_decisions': [s['decision'] for s in steps
                    if s['decision'] < n and (s['also_unresolved_claims'] or
                        (s['actor_reply_EOS'] and s['actor_semantic_label'] in (None, 'unresolved')))],
                'native_action_executed_after_reply': p['native_action'] is not None,
                'exact_same_task_normal_refs': compare_reference(row, p, controls, indices)}
        details.append(record)
        groups[row['version'], row['condition'], row['arm']].append(record)

    assert len(sealed) == overall['sealed_terminals']
    assert all_bad_current_positives == overall['definite_Mirage_on_an_actually_injected_observation']
    assert all_normal_current_positives == overall['normal_frame_semantic_errors']

    def summarize(recs):
        def counts(rows):
            onset = [r['first_confirmed_definite'] for r in rows if r['first_confirmed_definite']]
            return {'trajectories': len(rows), 'Mirage_status': dict(Counter(r['mirage_status'] for r in rows)),
                'timing_of_first_confirmed_definite': dict(Counter(x['timing'] for x in onset)),
                'frame_at_first_confirmed_definite': dict(Counter(x['current_frame'] for x in onset)),
                'earlier_abnormal_actual_forward': sum(x['earlier_changed_observation_reached_main'] for x in onset),
                'with_earlier_unresolved_or_unreviewed': sum(bool(x['earlier_unresolved_or_unreviewed_semantic_decisions'])
                                                            for x in onset),
                'first_confirmed_reply_matches_definite_same_task_normal_reference': sum(
                    bool(x['exact_same_task_normal_refs']) for x in onset)}
        return {'all_sealed_including_unscored': counts(recs),
                'original_officially_scored_only': counts([r for r in recs if r['official_scored']])}

    return {'all_versions_counts_only': summarize(details),
            'by_version_condition_and_arm': [dict(zip(('version','condition','arm'), k), **summarize(v))
                                            for k,v in groups.items()],
            'traj': details, 'all_definite_replies_on_actual_injected_current': all_bad_current_positives,
            'all_definite_replies_on_usable_current': all_normal_current_positives,
            'scope': 'First confirmed under original independent labels; earlier unresolved cases can change true onset. '
                     'Temporal order and current-frame usability do not establish cause.',
            'new_model_GUI_or_scorer_calls': 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('report', type=Path)
    args = p.parse_args()
    verify(args.report)
    report = read(args.report / 'condition-by-version.json')
    rows = read(args.report / 'trajectory-metrics.json')
    result = audit(rows, report['overall_counts_only_no_pooled_effect_estimate'])
    out = HERE / 'mirage-timing-audits' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'index.json', {'report_seal_sha256': sha(args.report / 'seal.json'),
                             'ledger_seal_sha256': report['ledger_seal_sha256'],
                             'auditor_sha256': sha(Path(__file__)), **result})
    save(out / 'seal.json', {'index.json': sha(out / 'index.json')})
    print(json.dumps({'mirage_timing': str(out), 'seal_sha256': sha(out / 'seal.json'),
                      **result['all_versions_counts_only']}))


if __name__ == '__main__':
    main()
