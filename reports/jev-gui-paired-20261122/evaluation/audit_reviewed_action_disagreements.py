"""Join already adjudicated prose/action disagreements to native calls and captures."""

import argparse
from collections import Counter
import json
from pathlib import Path
import time

from collect import HERE, manifest_for, read, save, sha
from link import verify
from review_cycle import review_pairs
from summarize import load_reviews


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('report', type=Path)
    a = p.parse_args()
    for d in (a.ledger, a.report):
        verify(d)
    dataset = read(a.ledger / 'private-linked.json')
    report = read(a.report / 'condition-by-version.json')
    assert report['ledger_seal_sha256'] == sha(a.ledger / 'seal.json')
    quality, labels, sources = load_reviews(dataset, review_pairs(a.report))
    assert sources == report['review_sources']
    expected = {(run, decision) for (run, decision), item in labels.items()
                if item.get('native_direction_conflict') or item.get('native_target_conflict')}
    cases = []
    for row in dataset['rows']:
        t = row['evidence']
        if not t:
            continue
        run = row['slot']['run_id']
        steps = t['steps']
        for i, step in enumerate(steps):
            key = run, step['step']
            if key not in expected:
                continue
            label = labels[key]
            m = step['main']
            assert step['actual_first_forward'] and m['natural_EOS']
            native = step['executed']
            img = m['current_image_sha256']
            proposal = step['proposal']
            if native:
                # The executor logs current_capture_sha256 after env.step().
                # The proposal, not that post-action image, binds to the model input.
                assert native['step'] == key[1] and proposal['environment_action']
                assert proposal['image_sha256'] == img and proposal['candidate_sha256'] == m['reply_sha256']
                assert proposal['capture_id'] == step['submit']['capture_id']
            if label.get('native_direction_conflict') and native:
                assert native['payload']['type'] == 'scroll'
            later = steps[i+1] if i+1 < len(steps) else None
            nxt = next((f for f in later['frames'] if f['capture_kind'] == 'initial'), None) if later else None
            diff = 'not_observed'
            next_ref, native_result_matches_next = None, None
            if nxt:
                raw = nxt['captured_sha256']
                if raw is not None and img is not None:
                    diff = 'same_png' if raw == img else 'different_png'
                next_ref = {'decision': later['step'], 'capture_id': nxt['capture_id'],
                            'genuine_source_PNG_sha256': raw, 'delivery_PNG_sha256': nxt['delivered_sha256'],
                            'genuine_source_action_sequence': nxt['action_sequence']}
                if native and native['current_capture_sha256'] is not None and raw is not None:
                    native_result_matches_next = native['current_capture_sha256'] == raw
            cases.append({'run_id': run, 'decision': key[1], 'stage': row['stage_id'], 'slot': row['slot'],
                'separate_from_Mirage_label': label['semantic_label'],
                'direction_disagreement': bool(label.get('native_direction_conflict')),
                'target_disagreement': bool(label.get('native_target_conflict')),
                'verbatim_independent_review': label,
                'actual_forward': {'request': step['request']['request_id'], 'wire_sha256': m['wire_sha256'],
                    'request_seal_sha256': m['seal_sha256'], 'reply_sha256': m['reply_sha256'],
                    'current_PNG_sha256': img, 'image_review_label': quality.get(img,{}).get('label')},
                'unmodified_proposal': proposal, 'native_execution_receipt': native,
                'native_receipt_image_is_post_action_not_actor_input': bool(native),
                'post_action_native_image_equals_next_source_capture': native_result_matches_next,
                'next_initial_capture': next_ref, 'next_genuine_PNG_compared_to_current_forward_PNG': diff,
                'terminal_sha256': t['terminal_sha256'], 'controller_chain_head': t['controller_head'],
                'trusted_source_chain_head': t['source_head']})
    assert {(c['run_id'],c['decision']) for c in cases} == expected
    overall = report['overall_counts_only_no_pooled_effect_estimate']
    direction = [s for s in cases if s['direction_disagreement']]
    assert len(direction) == overall['separate_prose_native_direction_conflicts']
    outcome = Counter((c['native_execution_receipt'] or {}).get('ok') for c in direction)
    comparison = Counter(c['next_genuine_PNG_compared_to_current_forward_PNG'] for c in direction)
    code = {}
    for stage in set(c['stage'] for c in cases):
        ptr, manifest, _ = manifest_for(stage)
        gui_source = Path(ptr['runtime']) / 'gui_experiment.py'
        code[stage] = sha(gui_source)
        assert code[stage] == manifest['files']['gui_experiment.py']
    out = HERE / 'semantic-action-audits' / str(time.time_ns())
    out.mkdir(exist_ok=False)
    result = {'verified_terminal_slots':overall['sealed_terminals'], 'previously_labeled_direction_cases':len(direction),
          'previously_labeled_target_cases':sum(c['target_disagreement'] for c in cases),
          'direction_executed_return_OK':outcome[True], 'direction_native_error':outcome[False],
          'direction_no_native_action_receipt':outcome[None], 'direction_following_PNG_status':dict(comparison),
          'all_direction_on_reviewed_usable_frame':all(c['actual_forward']['image_review_label']=='coherent_usable'
                                                        for c in direction),
          'post_action_digest_source_by_exact_runtime_sha256':code,
          'screening_scope':'Positive flags from sealed manual reviews or exact complete-input-and-reply reuse only. '
                            'No claim that other steps have no action error. Native OK is not task progress; '
                            'different PNG bytes alone do not establish a scroll direction.',
          'ledger_seal_sha256':sha(a.ledger/'seal.json'), 'report_seal_sha256':sha(a.report/'seal.json'),
          'legacy_labels_modified':False, 'new_model_browser_scorer_calls':0, 'cases':cases}
    save(out/'action-disagreements.json',result)
    save(out/'seal.json',{'action-disagreements.json':sha(out/'action-disagreements.json')})
    print(json.dumps({'audit':str(out), 'seal':sha(out/'seal.json'),
        **{k:result[k] for k in ('previously_labeled_direction_cases','previously_labeled_target_cases',
            'direction_executed_return_OK','direction_following_PNG_status','all_direction_on_reviewed_usable_frame')}}))


if __name__ == '__main__':
    main()
