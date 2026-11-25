"""Seal explicit human source judgments with exact prefix/image/history bindings.

No label is predicted here. Each new row must supply its own three-valued label,
reason, original image hash and completed source-review attestation.
"""
import argparse
import json
import time
from pathlib import Path
from control import HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert root.resolve().is_relative_to(HERE.resolve())
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--annotations', type=Path, required=True)
    args = parser.parse_args()
    annotations = args.annotations.resolve()
    assert annotations.is_relative_to(HERE.resolve())
    supplied = load(annotations)
    disclosure = supplied.get('review_disclosure', {})
    assert set(disclosure).issubset({
        'current_trajectory_official_outcome_not_seen_for_labeling',
        'official_outcome_seen_before_new_source_extension',
        'official_outcome_not_used_to_replace_source_judgments'})
    assert all(type(v) is bool for v in disclosure.values())
    root, prior = Path(supplied['source_packets']), Path(supplied['prior_review'])
    verify(root)
    verify(prior)
    previous = load(prior / 'review.json')
    old_packets = Path(previous['source_packets'])
    verify(old_packets)
    entries = load(root / 'review-index.json')['packets']
    old_entries = load(old_packets / 'review-index.json')['packets']
    start = previous['candidate_coverage']
    assert len(old_entries) == start and entries[:start] == old_entries
    new = supplied['new_rows']
    assert [v['candidate'] for v in new] == list(range(start + 1, len(entries) + 1))
    assert new and all(v['candidate_semantic_Mirage'] is None or type(v['candidate_semantic_Mirage']) is bool for v in new)
    assert all(v['reason'] and v['full_legal_history_and_original_image_reviewed'] is True for v in new)
    old_images = set(previous['unique_original_images_viewed'])
    assert len(old_images) == len(previous['unique_original_images_viewed'])
    newly_viewed = set(supplied['new_original_images_independently_viewed'])
    rows, images = previous['rows'].copy(), set()
    last_messages, last_text = None, None
    template = load(HERE / 'package/actor-template.json')
    for number, entry in enumerate(entries, 1):
        packet = load(root / entry['file'])
        assert sha(root / entry['file']) == entry['sha256']
        messages = packet['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0]
        if last_messages is not None:
            assert messages[:len(last_messages)] == last_messages
            assert messages[len(last_messages)] == {'role': 'assistant', 'content': last_text}
        refs = [c['original_PNG_sha256'] for m in messages if isinstance(m['content'], list)
                for c in m['content'] if c.get('type') == 'image_url']
        images.update(refs)
        if number > start:
            annotation = new[number - start - 1]
            assert annotation['current_image_sha256'] == refs[-1]
            rows.append({**annotation, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
                         'source_full_legal_body_sha256': packet['source_body_sha256'],
                         'source_response_sha256': packet['source_response_sha256'],
                         'execution_or_official_score_joined': False})
        last_messages, last_text = messages, packet['candidate_exact_text']
    assert images == old_images | newly_viewed
    assert newly_viewed == images - old_images
    for h in images:
        assert sha(root / 'images' / (h + '.png')) == h
    assert len(rows) == len(entries) and rows[:start] == previous['rows']
    positive = [v['candidate'] for v in rows if v['candidate_semantic_Mirage'] is True and not v['pure_native_WAIT']]
    unresolved = [v['candidate'] for v in rows if v['candidate_semantic_Mirage'] is None and not v['pure_native_WAIT']]
    negative = [v['candidate'] for v in rows if v['candidate_semantic_Mirage'] is False and not v['pure_native_WAIT']]
    completed = supplied.get('completed_trajectory_review', False)
    assert type(completed) is bool
    whole = True if positive else None if unresolved or not completed else False
    dest = HERE / (supplied['output_name'] + '-' + str(time.time_ns()))
    assert dest.parent == HERE and '/' not in supplied['output_name'] and '\\' not in supplied['output_name']
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'human-annotations.json').write_bytes(annotations.read_bytes())
    inherited = previous.copy()
    inherited_stage_fields = {}
    for key in ('new_full_original_images_viewed_this_review',
                'prior8_full_original_images_reused_only_after_exact_SHA_identity',
                'legal_user_plus_candidate_messages_reviewed'):
        if key in inherited:
            inherited_stage_fields[key] = inherited.pop(key)
    save(dest / 'review.json', {
        **inherited, **disclosure, 'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
        'prior_review': str(prior), 'prior_review_sha256': sha(prior / 'review.json'),
        'prior_prefix_exact_packet_SHA_equality_verified': True, 'prior_rows_unchanged': True,
        'candidate_coverage': len(entries), 'new_reviewed_candidates': len(new),
        'unreviewed_within_exported_prefix': 0, 'literal_negative_candidates': len(negative),
        'definite_positive_candidates': positive, 'unresolved_candidates': unresolved,
        'pure_native_WAIT_exclusions': sum(bool(v['pure_native_WAIT']) for v in rows),
        'trajectory_semantic_Mirage': whole, 'partial_prefix_only': not completed,
        'completed_trajectory_review': completed,
        'whole_final_trajectory_not_fully_reviewed': not completed,
        'at_least_one_boundary_occurrence_despite_unfinished_trajectory': bool(positive) and not completed,
        'unique_original_images_viewed': sorted(images), 'new_original_images_viewed': sorted(newly_viewed),
        'new_full_original_images_viewed_this_review': len(newly_viewed),
        'prior_full_original_images_reused_after_exact_SHA_identity': len(old_images),
        'legal_user_plus_candidate_messages_reviewed': 2 * len(entries),
        'prior_stage_descriptive_metadata_only': inherited_stage_fields,
        'complete_latest_legal_messages_read': len(last_messages),
        'source_judgments_sealed_before_this_run_execution_and_official_join': True,
        'reviewer_count': 1, 'fully_blind': False, 'gate_or_scorer_used_as_truth': False,
        'rows': rows, 'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'time': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': len(entries), 'new_reviewed': len(new),
                      'definite_positive_candidates': positive, 'unresolved_candidates': unresolved,
                      'completed_trajectory_review': completed, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
