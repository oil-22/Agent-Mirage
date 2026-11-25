"""Compare each sealed recovery with the same-task, same-version normal controls."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median
import time

from collect import HERE, read, save, sha
from link import verify


MAIN_KEYS = ('body_sha256', 'messages_ordered', 'current_image_sha256',
             'images_all_history', 'reply_sha256')


def native_ack(step):
    action = step['executed']
    return (action['payload'], action['ok']) if action else None


def compare_decision(left, right):
    different = []
    if not all(s and s['actual_first_forward'] and s['main']['natural_EOS'] for s in (left, right)):
        return ['paired_actual_forward_and_EOS_unavailable']
    if left['step'] != right['step']:
        different.append('decision_index')
    different.extend(key for key in MAIN_KEYS if left['main'][key] != right['main'][key])
    if native_ack(left) != native_ack(right):
        different.append('native_action_and_status')
    return different


def request_binding(step):
    if not (step and step['actual_first_forward']):
        return None
    main = step['main']
    return {'request_id': step['request']['request_id'], 'seal_sha256': main['seal_sha256'],
            'body_sha256': main['body_sha256'], 'current_image_sha256': main['current_image_sha256'],
            'reply_sha256': main['reply_sha256'], 'natural_EOS': main['natural_EOS'],
            'forward_calls': main['forward_calls'], 'native_action_and_status': native_ack(step)}


def audit(ledger, metrics):
    rows = list(zip(ledger['rows'], metrics, strict=True))
    assert all(r['slot']['run_id'] == m['run_id'] and r['version'] == m['version'] for r, m in rows)
    references = {(m['task_id'], m['arm']): (r, m) for r, m in rows if m['condition'] == 'clean_control'}
    comparisons = []
    matched_wait_by_group = defaultdict(list)
    for row, arm in rows:
        closures = [s for s in arm['steps'] or [] if s['independent_normal_loop_closure']]
        if not closures:
            continue
        recovery, = closures  # Each frozen slot has at most one injected initial observation.
        tape = row['evidence']['steps']
        restored, = (s for s in tape if s['step'] == recovery['decision'])
        assert arm['arm'] == 'on' and restored['recapture_at_actual_forward_needs_visual_review']
        item = {k: arm[k] for k in ('run_id', 'task_id', 'condition', 'version', 'stage_id',
                                    'terminal_sha256', 'outcome', 'official_score', 'mirage_status')}
        item.update({'recovery_decision': restored['step'], 'recovery_request': request_binding(restored),
                     'recovery_first_frame_ready_to_main_submit_ns': restored['first_frame_to_actor_ns'],
                     'comparisons': {}})
        for gate in ('on', 'off'):
            base, control = references[arm['task_id'], gate]
            target = {k: control[k] for k in ('run_id', 'version', 'stage_id', 'terminal_sha256',
                                               'outcome', 'official_score', 'mirage_status')}
            item['comparisons'][gate] = target
            if base['version'] != row['version'] or not base['evidence']:
                target['status'] = ('different_measurement_version' if base['version'] != row['version']
                                    else 'normal_reference_not_sealed')
                continue
            normal = base['evidence']['steps']
            indexed = {s['step']: s for s in normal}
            assert len(indexed) == len(normal)
            matched = 0
            first_difference = None
            matched_native = 0
            for x in tape:
                changed = compare_decision(x, indexed.get(x['step']))
                if changed:
                    first_difference = {'decision': x['step'], 'fields': changed}
                    break
                matched += 1
                matched_native += x['executed'] is not None
            if first_difference is None and len(tape) < len(normal):
                first_difference = {'decision': normal[matched]['step'], 'fields': ['recovered_trajectory_ended']}
            control_step = indexed.get(restored['step'])
            differences_at_recovery = compare_decision(restored, control_step)
            target.update({'status': 'compared', 'matched_actual_decision_prefix': matched,
                           'matched_native_actions_in_prefix': matched_native,
                           'first_recovery_path_difference': first_difference,
                           'full_observed_path_matches': bool(matched and matched == len(tape) == len(normal)),
                           'recovery_slot_differences': differences_at_recovery,
                           'control_request_at_recovery_decision': request_binding(control_step),
                           'recovered_decisions': len(tape), 'normal_decisions': len(normal)})
            offset = None
            if matched >= restored['step'] and restored['first_frame_to_actor_ns'] is not None:
                normal_wait = control_step['first_frame_to_actor_ns']
                if normal_wait is not None:
                    offset = restored['first_frame_to_actor_ns'] - normal_wait
                    if gate == 'on':
                        matched_wait_by_group[arm['version'], arm['condition']].append((arm['task_id'], offset))
            target['first_frame_ready_to_main_submit_difference_ns_exact_prefix'] = offset
        comparisons.append(item)
    wait = []
    for (version, condition), items in sorted(matched_wait_by_group.items()):
        seconds = [ns / 1e9 for _, ns in items]
        wait.append({'version': version, 'condition': condition, 'paths': len(items),
                     'distinct_tasks': len({task for task, _ in items}), 'median_seconds': median(seconds),
                     'observed_range_seconds': [min(seconds), max(seconds)]})
    return {'recovery_paths': comparisons, 'new_model_GUI_or_scorer_calls': 0,
            'additional_wait_vs_clean_on_with_exact_prefix_by_version_condition': wait,
            'scope': 'Observed actual forwards, legal messages, EOS replies and native acknowledgments. '
                     'Wait is initial frame ready to actor submit, only for paths with exact same-version '
                     'inputs, replies, actions and acknowledgments through the recovery decision. '
                     'The matched subset does not estimate a pooled effect.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('report', type=Path)
    args = p.parse_args()
    for source in (args.ledger, args.report):
        verify(source)
    ledger_sha = sha(args.ledger / 'seal.json')
    summary = read(args.report / 'condition-by-version.json')
    assert summary['ledger_seal_sha256'] == ledger_sha
    result = audit(read(args.ledger / 'private-linked.json'), read(args.report / 'trajectory-metrics.json'))
    out = HERE / 'recovery-alignment-audits' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'recovery-alignment.json', {'ledger_seal_sha256': ledger_sha,
                                          'report_seal_sha256': sha(args.report / 'seal.json'),
                                          'alignment_auditor_sha256': sha(Path(__file__)), **result})
    save(out / 'seal.json', {'recovery-alignment.json': sha(out / 'recovery-alignment.json')})
    print(json.dumps({'alignment': str(out), 'seal_sha256': sha(out / 'seal.json'),
                      'recovery_paths': len(result['recovery_paths'])}))


if __name__ == '__main__':
    main()
