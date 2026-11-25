"""Explain temporary holds and check a one-level RGB deadband on sealed requests."""

import argparse
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops

from audit_truth import POSITIVE
from live_common import load, save, sha


def verified_rgb(frame):
    path = Path(frame['acquisition_png'])
    assert sha(path) == frame['source_sha256'] == frame['candidate_sha']
    with Image.open(path) as image:
        assert image.format == 'PNG' and image.size == (1280, 720) and image.n_frames == 1
        return image.convert('RGB')


def box_delta(before, candidate, rectangle):
    x1, y1, x2, y2 = rectangle
    assert 0 <= x1 < x2 <= before.width and 0 <= y1 < y2 <= before.height
    diff = ImageChops.difference(before.crop(rectangle), candidate.crop(rectangle))
    histogram = Counter(map(max, diff.get_flattened_data()))
    return {'rectangle': rectangle, 'max_channel_delta': max(histogram),
            'changed_pixels': diff.width * diff.height - histogram[0],
            'pixels_with_channel_delta_above_one': sum(n for level, n in histogram.items() if level > 1)}


def review(audit_file, original_review_file):
    audit, original_review = load(audit_file), load(original_review_file)
    assert audit['status'] == 'completed_panel' and audit['audited_episodes'] == 36
    assert original_review['source_audit_sha256'] == sha(audit_file)
    assert not original_review['possible_review_mismatches']
    counts = {arm: Counter() for arm in ('stock', 'repair')}
    affected, specialist = [], []
    for row in audit['episodes']:
        is_normal = row['case']['scenario'] in POSITIVE
        totals = counts[row['case']['arm']]
        frames = {f['capture_id']: f for f in row['frames']}
        policies = {p['capture_id']: p for p in row['policies']}
        decisions = {q['request_id']: q for q in row['flash']}
        delivery_id = (row['delivery'] or {}).get('capture_id')
        if is_normal:
            if delivery_id:
                assert original_review['bound_deliveries'][row['id']]
            for label, captures in [('first_ready', [row['first_ready']]),
                                    ('all_ready', [f for f in frames.values() if f['truth'] == 'ready'])]:
                caps = {f['capture_id'] for f in captures if f}
                hold_reasons = Counter()
                for hold in row['holds']:
                    cap = hold['capture_id']
                    if cap not in caps:
                        continue
                    rejected = next((q for q in row['flash'] if q['capture_id'] == cap and q['decision'] == 'NO'), None)
                    reason = rejected['kind'] + '_NO' if rejected else policies.get(cap, {}).get('route', hold['reason'])
                    hold_reasons[reason] += 1
                if hold_reasons:
                    totals[f'{label}_episodes_held'] += 1
                    if delivery_id:
                        totals[f'{label}_episodes_held_then_delivered'] += 1
                    for reason, n in hold_reasons.items():
                        totals[f'{label}_holds_{reason}'] += n
                    affected.append({'id': row['id'], 'scope': label, 'holds': dict(hold_reasons),
                                     'delivery_capture_id': delivery_id})
        for p in (v for v in policies.values() if v['route'] == 'specialized_temporal'):
            cap, previous = p['capture_id'], p['previous_authentic_capture_id']
            decision = decisions[p['request_id']]
            frame = frames[cap]
            before, last, current = [verified_rgb(f) for f in (row['initial'], frames[previous], frame)]
            regions = [box_delta(before, current, r) for r in p['scope']['checked_regions']]
            assert p['scope']['eligible'] and max(r['max_channel_delta'] for r in regions) > 0
            assert all(box_delta(last, current, r['rectangle'])['changed_pixels'] == 0 for r in regions)
            real_delta = any(r['max_channel_delta'] > 1 for r in regions)
            specialist.append({'id': row['id'], 'capture_id': cap, 'truth': frame['truth'],
                               'original_delivery': delivery_id == cap, 'actual_decision': decision['decision'],
                               'p_yes': decision['p_yes'], 'wire_sha256': decision['wire_sha256'],
                               'previous_png_sha256': row['initial']['source_sha256'],
                               'current_png_sha256': frame['source_sha256'], 'regions': regions,
                               'would_still_qualify_to_ask': real_delta})
    assert len(specialist) == audit['model_calls']['toggle_check']
    return {'source_audit_sha256': sha(audit_file), 'original_review_sha256': sha(original_review_file),
            'scope': ('Counterfactual eligibility on actual recorded specialized requests only. Same post-capture '
                      'stability; require at least one channel difference above one between before and current. '
                      'No simulation of later captures, new decisions, thresholds or end-to-end outcomes.'),
            'normal_holds_by_arm': {arm: dict(values) for arm, values in counts.items()},
            'normal_hold_episodes': affected, 'actual_specialized_requests': specialist,
            'rejected_by_deadband': [{'id': q['id'], 'truth': q['truth'], 'actual_decision': q['actual_decision'],
                                     'previously_delivered': q['original_delivery']} for q in specialist
                                    if not q['would_still_qualify_to_ask']],
            'new_model_calls': 0, 'new_GUI_actions': 0, 'integrated_or_deployed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audit', type=Path)
    parser.add_argument('original_review', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    options = parser.parse_args()
    result = review(options.audit, options.original_review)
    save(options.out, result)
    print(result['normal_holds_by_arm'], result['rejected_by_deadband'])
