"""Find pairs that differ only in the current observation at actual model input."""

import argparse
from collections import Counter
import json
from pathlib import Path
import time

from audit_recovery_alignment import compare_decision, native_ack, request_binding
from collect import HERE, read, save, sha
from link import verify


def dose(steps):
    matches = [s for s in steps if s['altered_bytes']]
    assert len(matches) <= 1
    if not matches:
        return None, None
    step, = matches
    first, = (f for f in step['frames'] if f['capture_kind'] == 'initial' and f['injected'])
    assert first['captured_sha256'] != first['delivered_sha256']
    return step, first


def without_current_image(step, messages):
    main = step['main']
    previous, now = main['messages_ordered'][:-1], messages[main['messages_ordered'][-1]]
    assert now['role'] == 'user' and isinstance(now['content'], list)
    image = [b['sha256'] for b in now['content'] if b['type'] == 'image']
    assert image == ([main['current_image_sha256']] if main['current_image_sha256'] else [])
    return previous, {**now, 'content': [b for b in now['content'] if b['type'] != 'image']}


def audit(ledger, pairs):
    by_run = {r['slot']['run_id']: r for r in ledger['rows']}
    public = ledger['public_legal_messages']
    results = []
    for pair in pairs:
        if pair['condition'] == 'clean_control':
            continue
        version = pair['version']
        arms = {arm: by_run[pair[arm]] for arm in ('off', 'on')}
        for arm, r in arms.items():
            assert r['version'] == version and r['slot']['pair_id'] == pair['pair_id'] and r['slot']['arm'] == arm
        row = {'pair': pair['pair_id'], 'version': version, 'condition': pair['condition'],
               'terminal_by_arm': {a: r['evidence']['terminal_sha256'] if r['evidence'] else None for a, r in arms.items()},
               'stage_by_arm': {a: r['stage_id'] for a, r in arms.items()}, 'fully_isolated': False}
        results.append(row)
        if not all(r['evidence'] for r in arms.values()):
            row['status'] = 'both_arms_not_yet_sealed'
            continue
        hist = {a: r['evidence']['steps'] for a, r in arms.items()}
        (off, old), (on, new) = (dose(hist[a]) for a in ('off', 'on'))
        if not (off and on):
            row['status'] = 'not_both_actually_exposed'
            continue
        off_binding, on_binding = request_binding(off), request_binding(on)
        n, m = off['step'], on['step']
        prefix = n == m and len(hist['off'][:n-1]) == len(hist['on'][:n-1]) == n-1 and all(
            not compare_decision(a, b) for a, b in zip(hist['off'][:n-1], hist['on'][:n-1], strict=True))
        match_only_image = bool(off_binding and on_binding and
            off_binding['current_image_sha256'] != on_binding['current_image_sha256'] and
            without_current_image(off, public) == without_current_image(on, public))
        off_dose = off['known_injected_dose_at_first_forward']
        on_recovery = pair['actual_altered_observation']['on']['normal_recapture_at_actual_forward']
        assert off_dose == pair['actual_altered_observation']['off']['altered_observation_at_actual_forward']
        assert n == pair['actual_altered_observation']['off']['decision']
        assert m == pair['actual_altered_observation']['on']['decision']
        if off_dose:
            assert off_binding and old['delivered_sha256'] == off_binding['current_image_sha256']
        if on_recovery:
            assert on_binding and on['recapture_at_actual_forward_needs_visual_review']
        checks = {'same_decision': n == m, 'exact_actual_actor_and_native_prefix': prefix,
                  'same_signed_clean_initial_pixels': old['captured_sha256'] == new['captured_sha256'],
                  'same_altered_delivery': old['delivered_sha256'] == new['delivered_sha256'],
                  'exact_actual_legal_messages_except_current_image': match_only_image,
                  'off_alteration_entered_forward': off_dose,
                  'on_normal_recapture_entered_same_decision': on_recovery,
                  'normal_recapture_returned_signed_clean_initial_pixels': bool(on_binding and
                    on_binding['current_image_sha256'] == new['captured_sha256'])}
        row.update({'status': 'both_exposed', 'fully_isolated': all(checks.values()), 'checks': checks,
                    'decision_by_arm': {'off': n, 'on': m},
                    'first_signed_png_by_arm': {'off': old['captured_sha256'], 'on': new['captured_sha256']},
                    'altered_delivery_png_by_arm': {'off': old['delivered_sha256'], 'on': new['delivered_sha256']},
                    'actual_forwards': {'off': off_binding, 'on': on_binding},
                    'same_immediate_native_action_and_ack': bool(native_ack(off) and native_ack(off) == native_ack(on)),
                    'same_immediate_raw_reply': bool(off_binding and on_binding and off_binding['natural_EOS'] and
                        on_binding['natural_EOS'] and off_binding['reply_sha256'] == on_binding['reply_sha256'])})
    isolated = [r for r in results if r['fully_isolated']]
    return {'assigned_injection_pairs': len(results), 'both_actually_exposed': sum(r['status']=='both_exposed' for r in results),
            'exact_input_isolated_pairs': len(isolated), 'same_immediate_reply_on_isolated_pairs': sum(
                r['same_immediate_raw_reply'] for r in isolated), 'same_immediate_native_ack_on_isolated_pairs': sum(
                r['same_immediate_native_action_and_ack'] for r in isolated),
            'isolated_by_condition': dict(Counter(r['condition'] for r in isolated)), 'pairs': results,
            'scope': 'Exact visible histories, images and replies/native acknowledgments before the dose; current block only at the dose. '
                     'Wire IDs and normal/altered visual tensors need not match. Diagnostic subset, not the study denominator.',
            'new_model_GUI_scorer_calls': 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('report', type=Path)
    a = p.parse_args()
    for path in (a.ledger, a.report):
        verify(path)
    ledger_sha = sha(a.ledger/'seal.json')
    assert ledger_sha == read(a.report/'condition-by-version.json')['ledger_seal_sha256']
    result = audit(read(a.ledger/'private-linked.json'), read(a.report/'paired-metrics.json'))
    out = HERE/'image-isolation-audits'/str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    save(out/'index.json', {'ledger_seal_sha256': ledger_sha, 'report_seal_sha256': sha(a.report/'seal.json'), **result})
    save(out/'seal.json', {'index.json': sha(out/'index.json')})
    print(json.dumps({'receipt': str(out), 'seal_sha256': sha(out/'seal.json'),
                      **{k:v for k,v in result.items() if k != 'pairs'}}))


if __name__ == '__main__':
    main()
