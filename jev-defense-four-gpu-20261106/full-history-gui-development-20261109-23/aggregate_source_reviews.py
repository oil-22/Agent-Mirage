"""Aggregate completed source reviews without turning unreviewed tracks into zero.

Only explicit sealed labels are joined. No candidate is labeled by this utility.
"""
import hashlib
import json
from pathlib import Path
import time

from remote_control import HERE, save, sha


def verify(folder):
    for name, expected in json.loads((folder / 'seal.json').read_bytes()).items():
        assert sha(folder / name) == expected


def main():
    labels = {}
    authorities = []
    for path in sorted(HERE.glob('source-review-*/review.json')):
        verify(path.parent)
        data = json.loads(path.read_bytes())
        authorities.append({'path': str(path), 'sha256': sha(path)})
        for row in data['rows']:
            assert row['candidate_event_sha256'] not in labels
            labels[row['candidate_event_sha256']] = row
    collected = {}
    collection_authorities = []
    maximum_snapshot_candidates = 0
    for path in sorted((HERE / 'source-first-packets').glob('*/collection.json')):
        verify(path.parent)
        data = json.loads(path.read_bytes())
        collection_authorities.append({'path': str(path), 'sha256': sha(path)})
        maximum_snapshot_candidates = max(maximum_snapshot_candidates, data['all_candidates_at_snapshot'])
        for row in data['packets']:
            assert row['candidate_event_sha256'] not in collected
            collected[row['candidate_event_sha256']] = row
    assert set(labels) <= set(collected)
    joins = {}
    join_authorities = []
    for path in sorted(HERE.glob('post-review-join-*/join.json')):
        verify(path.parent)
        data = json.loads(path.read_bytes())
        assert data['all_source_labels_sealed_before_this_join']
        join_authorities.append({'path': str(path), 'sha256': sha(path)})
        for row in data['rows']:
            key = row['candidate_event_sha256']
            assert labels[key] == row['sealed_source_label']
            if key not in joins or data['time'] > joins[key]['join_time']:
                joins[key] = dict(row, join_time=data['time'])
    fingerprint = hashlib.sha256(json.dumps([authorities, collection_authorities, join_authorities], sort_keys=True).encode()).hexdigest()
    pointer = HERE / 'source-review-current.json'
    if pointer.exists() and json.loads(pointer.read_bytes())['authority_fingerprint'] == fingerprint:
        print(json.dumps({'unchanged': True, 'new_model_GUI_scorer_calls': 0}))
        return
    out = HERE / ('source-review-aggregate-' + str(time.time_ns()))
    out.mkdir()
    prior = None
    if pointer.exists():
        (out / 'previous-source-review-current.json').write_bytes(pointer.read_bytes())
        prior = sha(pointer)
    groups = {}
    for key, row in joins.items():
        group = groups.setdefault(row['run'], {'reviewed_candidates': 0, 'definite_positive_candidates': 0,
            'candidates_with_unresolved_subclaims': 0, 'pure_native_WAIT_excluded': 0,
            'native_action_errors': 0, 'accepted': 0, 'executed': 0,
            'accepted_semantic_errors': 0, 'executed_semantic_errors': 0,
            'trajectory_any_Mirage': None, 'full_trajectory_coverage_proven': False})
        label = labels[key]
        positive = label['definite_semantic_Mirage'] is True and not label['pure_native_WAIT_excluded']
        group['reviewed_candidates'] += 1
        group['definite_positive_candidates'] += positive
        group['candidates_with_unresolved_subclaims'] += bool(label['unresolved_semantic_subclaims'])
        group['pure_native_WAIT_excluded'] += label['pure_native_WAIT_excluded']
        group['native_action_errors'] += label['native_target_or_direction_error'] is True
        group['accepted'] += row['accepted']
        group['executed'] += row['executed']
        group['accepted_semantic_errors'] += positive and row['accepted']
        group['executed_semantic_errors'] += positive and row['executed']
        if positive:
            group['trajectory_any_Mirage'] = True
    result = {'schema': 'GUI23-incremental-source-review-aggregate-v1', 'time': time.time(),
        'authority_fingerprint': fingerprint, 'source_review_authorities': authorities,
        'source_collection_authorities': collection_authorities, 'post_seal_join_authorities': join_authorities,
        'collected_candidates': len(collected), 'source_reviewed_candidates': len(labels),
        'unreviewed_collected_candidates': len(set(collected) - set(labels)),
        'actual_candidates_at_latest_collection_snapshot': maximum_snapshot_candidates,
        'live_candidates_may_have_advanced_after_collection': True,
        'unjoined_reviewed_candidates': len(set(labels) - set(joins)), 'groups': groups,
        'planned_tracks': 32, 'planned_pairs': 16, 'actual_complete_paired_estimand_available': False,
        'relative_Mirage_reduction': None, 'absolute_risk_difference': None,
        'baseline_scope': 'Both arms retain the existing joint main-checker framework and shared boundary instructions; contrast estimates incremental single-auxiliary reading effect, not total defense versus an undefended agent',
        'short_reply_limitation': 'Current reviewed prefix is action-only; no visual prose. Implicit action grounding is checked, but a low count cannot be attributed to auxiliary defense or generalized semantic accuracy',
        'prior_pointer_sha256': prior, 'no_semantic_labels_generated_by_aggregation': True,
        'new_model_GUI_scorer_paid_calls': 0, 'goal': 'active'}
    save(out / 'aggregate.json', result)
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    current = {'authority': str(out / 'aggregate.json'), 'sha256': sha(out / 'aggregate.json'),
        'seal_sha256': sha(out / 'seal.json'), 'authority_fingerprint': fingerprint,
        'source_reviewed_candidates': len(labels), 'collected_candidates': len(collected),
        'trajectory_reduction': None, 'goal': 'active'}
    if pointer.exists():
        assert sha(pointer) == prior
        pointer.write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    else:
        save(pointer, current)
    print(json.dumps({'aggregate': str(out), 'aggregate_sha256': sha(out / 'aggregate.json'),
          'source_reviewed_candidates': len(labels), 'groups': groups, 'relative_reduction': None}, ensure_ascii=False))


if __name__ == '__main__':
    main()
