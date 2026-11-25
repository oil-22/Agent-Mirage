"""Index the executed gate paths using only sealed ledgers and visual reviews."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import time

from collect import HERE, read, save, sha
from link import verify
from review_cycle import review_pairs
from summarize import altered_observation, load_reviews, quantiles_ns


def one(events, name):
    selected = [g for g in events if g['event'] == name]
    assert len(selected) <= 1, name
    return selected[0] if selected else None


def examine(step, enabled, quality, counts):
    frames, events = step['frames'], step['gates']
    by_capture = {f['capture_id']: f for f in frames}
    assert len(by_capture) == len(frames)
    capture_checks = []
    for index, f in enumerate(frames):
        capture_id, delivered = f['capture_id'], f['delivered_sha256']
        by_frame = [g for g in events if g.get('capture_id') == capture_id]
        presence = one(by_frame, 'precheck_decision')
        receipt = one(by_frame, 'capture_receipt_decision')
        flash = one(by_frame, 'gate_decision')
        fault = one(by_frame, 'checker_failure')
        same_signed_pixels = delivered == f['captured_sha256']
        role = ('altered_initial' if f['injected'] and not same_signed_pixels else
                'signed_recapture' if f['capture_kind'] == 'recapture' else 'signed_initial')
        image_quality = quality.get(delivered, {}).get('label', 'missing' if delivered is None else 'unreviewed')
        if not enabled:
            assert not any((presence, receipt, flash, fault))
        if presence:
            assert not any((receipt, flash, fault)) and presence['decision'] == 'NO'
            assert presence['not_a_model_NO'] and not presence['Flash_called']
            if delivered is None:
                assert presence['reason'] == 'missing_image'
        if receipt and receipt['decision'] == 'NO':
            assert not any((flash, fault)) and receipt['not_a_model_NO']
            if role == 'altered_initial':
                assert receipt['reason'] == 'capture_bytes_replaced'
        if flash or fault:
            assert delivered and receipt and receipt['decision'] == 'YES' and not presence
            assert not (flash and fault) and events.index(receipt) < events.index(flash or fault)
        if flash:
            assert flash['image_sha256'] == delivered and flash['Flash_seal_sha256']
            counts[(step['arm'], role, image_quality, flash['decision'])] += 1
        if index and f['capture_kind'] == 'recapture':
            predecessor = frames[index-1]['capture_id']
            wanted = [g for g in events if g['event'] == 'recapture_requested' and
                      g['from_capture_id'] == predecessor]
            assert len(wanted) == 1, (step['step'], predecessor)
        capture_checks.append({'capture_id': capture_id, 'capture_role': role,
            'acquired_at_ns': f['acquired_at_ns'], 'action_sequence': f['action_sequence'],
            'session_id': f['session_id'], 'original_sha256': f['captured_sha256'],
            'delivered_sha256': delivered, 'independent_image_quality': image_quality,
            'gate_events': [{k: g[k] for k in ('event', 'event_sha256', 'decision', 'reason',
                            'request_id', 'Flash_seal_sha256') if k in g}
                            for g in by_frame if g in (presence, receipt, flash, fault)]})
    if step['submit'] and enabled:
        selected = step['submit']['capture_id']
        end = one(events, 'gate_terminal')
        release = one(events, 'main_image_forwarded')
        assert end and end['status'] == 'accepted' and end['last_capture_id'] == selected
        assert release and release['capture_id'] == selected
        flash = one([g for g in events if g.get('capture_id') == selected], 'gate_decision')
        assert flash and flash['decision'] == 'YES' and flash['request_id'] == release['gate_request_id']
        assert events.index(flash) < events.index(end) < events.index(release)
    return capture_checks


def next_genuine_forward(steps, start_index, quality):
    """A later normal observation is distinct from repair before any bad forward."""
    exposed = steps[start_index]
    since = exposed['start']['initial_ready_monotonic_ns']
    skipped = []
    for step in steps[start_index:]:
        if not step['actual_first_forward']:
            continue
        main, submit = step['main'], step['submit']
        chosen, = (f for f in step['frames'] if f['capture_id'] == submit['capture_id'])
        image = chosen['delivered_sha256']
        label = quality.get(image, {}).get('label')
        assert image == main['current_image_sha256']
        if (label != 'coherent_usable' or chosen['injected'] or
                image != chosen['captured_sha256']):
            skipped.append(step['step'])
            continue
        delta = submit['submit_monotonic_ns'] - since
        assert delta >= 0
        return {'decision': step['step'], 'same_decision_as_injection': step['step'] == exposed['step'],
            'capture_id': chosen['capture_id'], 'image_sha256': image,
            'request_id': step['request']['request_id'], 'request_seal_sha256': main['seal_sha256'],
            'actual_actor_reply_EOS': main['natural_EOS'],
            'initial_frame_ready_to_genuine_actor_submit_ns': delta,
            'earlier_non_normal_actual_forwards_since_injection': skipped}
    return None


def usable_capture_fate(arm, step, frame, check):
    """Follow an independently reviewed, unchanged capture through the actual forward and reply."""
    image = frame['delivered_sha256']
    if (image != frame['captured_sha256'] or frame['injected'] or
            check['independent_image_quality'] != 'coherent_usable'):
        return None
    assert image and check['capture_role'] in ('signed_initial', 'signed_recapture')
    events = check['gate_events']
    flash = one(events, 'gate_decision')
    rejection = [g['event'] for g in events if g.get('decision') == 'NO']
    assert len(rejection) <= 1
    submitted = bool(step['submit'] and step['submit']['capture_id'] == frame['capture_id'])
    forwarded = bool(submitted and step['actual_first_forward'])
    delivered = bool(submitted and step['reply'])
    main = step['main'] if submitted else None
    if submitted:
        assert flash and flash['decision'] == 'YES' and not rejection
    if forwarded:
        assert main['current_image_sha256'] == image
    if delivered:
        assert forwarded and main['natural_EOS'] and step['reply']['text_sha256'] == main['reply_sha256']
    return {'run_id': arm['run_id'], 'version': arm['version'], 'condition': arm['condition'],
        'decision': step['step'], 'terminal_sha256': arm['terminal_sha256'],
        'capture_id': frame['capture_id'], 'capture_role': check['capture_role'], 'image_sha256': image,
        'flash_verdict': flash['decision'] if flash else None,
        'flash_request_id': flash['request_id'] if flash else None,
        'flash_reply_seal_sha256': flash['Flash_seal_sha256'] if flash else None,
        'rejected_by': rejection[0] if rejection else None,
        'checker_failure': bool(one(events, 'checker_failure')),
        'submitted_to_actor': submitted, 'reached_actual_first_forward': forwarded,
        'delivered_actor_natural_EOS': delivered,
        'actor_request_id': step['request']['request_id'] if submitted and step['request'] else None,
        'actor_request_seal_sha256': main['seal_sha256'] if main else None}


def usable_capture_coverage(rows):
    def rollup(samples):
        return {'captures': len(samples), 'distinct_original_PNGs': len({r['image_sha256'] for r in samples}),
            'flash_yes': sum(r['flash_verdict'] == 'YES' for r in samples),
            'flash_no': sum(r['flash_verdict'] == 'NO' for r in samples),
            'no_bound_Flash_verdict': sum(r['flash_verdict'] is None for r in samples),
            'rejected_by_any_guard': sum(r['rejected_by'] is not None for r in samples),
            'checker_failures': sum(r['checker_failure'] for r in samples),
            'submitted_to_actor': sum(r['submitted_to_actor'] for r in samples),
            'reached_actual_first_forward': sum(r['reached_actual_first_forward'] for r in samples),
            'delivered_actor_natural_EOS': sum(r['delivered_actor_natural_EOS'] for r in samples)}

    by_scope, by_version = defaultdict(list), defaultdict(list)
    for row in rows:
        scope = ('recapture' if row['capture_role'] == 'signed_recapture' else
                 'clean_initial' if row['condition'] == 'clean_control' else 'injection_arm_initial')
        by_scope[scope].append(row)
        by_version[(row['version'], scope)].append(row)
    initials = [r for r in rows if r['capture_role'] == 'signed_initial']
    return {'eligible_initials': rollup(initials),
            'by_scope': {k: rollup(v) for k, v in sorted(by_scope.items())},
            'by_version_and_scope': [{'version': v, 'scope': s, **rollup(items)}
                                     for (v, s), items in sorted(by_version.items())],
            'capture_evidence': rows}


def audit(led, metrics, quality, overall):
    """Rebuild the gate walk for either an interim snapshot or final verification."""
    activities, flash_counts, loop_clocks, usable = [], Counter(), {}, []
    examined = 0
    for slot, arm in zip(led['rows'], metrics, strict=True):
        assert slot['slot']['run_id'] == arm['run_id']
        tape = slot['evidence']
        if not tape:
            continue
        assert tape['terminal_sha256'] == arm['terminal_sha256']
        assert tape['terminal']['run']['gate_enabled'] == (arm['arm'] == 'on')
        exposed = altered_observation(arm)
        for i, (step, stat) in enumerate(zip(tape['steps'], arm['steps'], strict=True)):
            assert step['step'] == stat['decision']
            examined += 1
            captures = examine({**step, 'arm': arm['arm']}, arm['arm'] == 'on', quality, flash_counts)
            if arm['arm'] == 'on':
                usable_this_step = [r for frame, check in zip(step['frames'], captures, strict=True)
                                    if (r := usable_capture_fate(arm, step, frame, check)) is not None]
                initials = [r for r in usable_this_step if r['capture_role'] == 'signed_initial']
                assert len(initials) == int(stat['initial_signed_normal_independently_reviewed'])
                if initials:
                    initial, = initials
                    assert initial['rejected_by'] == stat['rejection_event']
                    assert initial['flash_verdict'] == stat['initial_actual_Flash_decision']
                usable.extend(usable_this_step)
            if step['altered_bytes']:
                assert exposed['decision'] == step['step']
                main = step['main']
                if stat['independent_normal_loop_closure']:
                    group = (arm['version'], arm['condition'])
                    loop_clocks.setdefault(group, []).append(step['first_frame_to_actor_ns'])
                onward = next_genuine_forward(tape['steps'], i, quality)
                assert not stat['independent_normal_loop_closure'] or (
                    onward and onward['same_decision_as_injection'])
                activities.append({'run': arm['run_id'], 'version': arm['version'], 'stage': arm['stage_id'],
                    'condition': arm['condition'], 'arm': arm['arm'], 'decision': step['step'],
                    'terminal_sha256': arm['terminal_sha256'], 'official_score': arm['official_score'],
                    'trajectory_outcome': arm['outcome'], 'controller_chain_head': tape['controller_head'],
                    'trusted_source_chain_head': tape['source_head'], 'captures': captures,
                    'recapture_requests': [g for g in step['gates'] if g['event'] == 'recapture_requested'],
                    'selected_capture_id': stat['selected_capture_id'],
                    'actual_model_request': ({'request_id': stat['request_id'],
                        **{k: main[k] for k in ('wire_sha256', 'seal_sha256', 'body_sha256',
                                                'natural_EOS', 'current_image_sha256', 'forward_calls')}}
                        if main and step['actual_first_forward'] else None),
                    'native_action_receipt': step['executed'], 'frame_ready_to_submit_ns': step['first_frame_to_actor_ns'],
                    'first_independently_normal_genuine_forward_at_or_after_injection': onward,
                    'outcome_at_injection_decision': exposed})
    assert len(activities) == overall['attempts_with_real_injected_change']
    closures = sum(r['outcome_at_injection_decision']['normal_recapture_at_actual_forward'] for r in activities)
    assert closures == overall['independently_normal_image_reached_actor_after_loop']
    exposures = sum(r['outcome_at_injection_decision']['altered_observation_at_actual_forward'] for r in activities)
    assert exposures == overall['injected_change_reached_actor_actual_forward']
    passed = [r for r in activities if r['arm'] == 'off' and
              r['outcome_at_injection_decision']['altered_observation_at_actual_forward']]
    off_followup = Counter('later_genuine_normal_forward' if
                          r['first_independently_normal_genuine_forward_at_or_after_injection'] else
                          'no_later_genuine_normal_forward_before_terminal' for r in passed)
    off_immediate_action = Counter(r['native_action_receipt']['payload']['type'] if r['native_action_receipt']
                                   else 'no_environment_action_receipt' for r in passed)
    return {'decisions_checked': examined,
        'sealed_slots': sum(r['evidence'] is not None for r in led['rows']),
        'actual_Flash_verdicts': [dict(zip(('arm', 'capture_role', 'independent_image_quality', 'decision'), key), n=n)
                                 for key, n in sorted(flash_counts.items())],
        'independently_usable_unchanged_captures_on_arm': usable_capture_coverage(usable),
        'closed_loop_frame_ready_to_submit_seconds': [{'version': k[0], 'condition': k[1], **quantiles_ns(v)}
                                                       for k, v in sorted(loop_clocks.items())],
        'off_arm_after_real_bad_forward': {'n': len(passed), 'immediate_actual_native_action': dict(off_immediate_action),
                                            'followup': dict(off_followup)},
        'altered_initial_deliveries': activities, 'new_model_GUI_or_scorer_calls': 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('report', type=Path)
    a = p.parse_args()
    for item in (a.ledger, a.report):
        verify(item)
    report = read(a.report / 'condition-by-version.json')
    ledger_seal = sha(a.ledger / 'seal.json')
    assert ledger_seal == report['ledger_seal_sha256']
    led = read(a.ledger / 'private-linked.json')
    quality, _, _ = load_reviews(led, review_pairs(a.report))
    metrics = read(a.report / 'trajectory-metrics.json')
    evidence = audit(led, metrics, quality, report['overall_counts_only_no_pooled_effect_estimate'])
    out = HERE / 'gate-cycle-audits' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'gate-cycles.json', {'ledger_seal_sha256': ledger_seal,
                                  'metrics_seal_sha256': sha(a.report / 'seal.json'), **evidence})
    save(out / 'seal.json', {'gate-cycles.json': sha(out / 'gate-cycles.json')})
    print(out)


if __name__ == '__main__':
    main()
