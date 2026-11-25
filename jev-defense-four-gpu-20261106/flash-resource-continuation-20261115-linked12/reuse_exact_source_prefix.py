"""Reuse already reviewed source labels only after exact full-input/image/reply equality.

This is explicit reuse by the same reviewer. It does not create a new reviewer,
read a private execution index, label differing inputs, or infer efficacy.
"""
import argparse
import copy
import json
import time
from pathlib import Path
from control import HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert all(sha(root / name) == h for name, h in load(root / 'seal.json').items())


def images(value):
    if isinstance(value, list):
        for v in value:
            yield from images(v)
    elif isinstance(value, dict):
        if value.get('type') == 'image_url':
            yield value
        else:
            for v in value.values():
                yield from images(v)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-review', type=Path, required=True)
    parser.add_argument('--target-packets', type=Path, required=True)
    args = parser.parse_args()
    previous = args.source_review.resolve()
    target = args.target_packets.resolve()
    assert target.parent == HERE
    verify(previous)
    old = load(previous / 'review.json')
    source = Path(old['source_packets'])
    verify(source)
    verify(target)
    assert sha(source / 'seal.json') == old['source_packets_seal_sha256']
    a, b = load(source / 'review-index.json')['packets'], load(target / 'review-index.json')['packets']
    assert 0 < len(b) <= len(a) and len(old['rows']) == len(a)
    rows, comparisons, used_images = [], [], set()
    for number, (left, right, original) in enumerate(zip(a, b, old['rows']), 1):
        p, q = load(source / left['file']), load(target / right['file'])
        assert sha(source / left['file']) == left['sha256'] == original['packet_sha256']
        assert sha(target / right['file']) == right['sha256']
        assert original['candidate'] == number
        assert original['source_full_legal_body_sha256'] == p['source_body_sha256']
        assert p['source_body_sha256'] == q['source_body_sha256']
        assert p['legal_full_input_review_projection'] == q['legal_full_input_review_projection']
        assert p['candidate_exact_text'] == q['candidate_exact_text']
        assert p['natural_EOS'] and q['natural_EOS']
        for image in images(q['legal_full_input_review_projection']):
            name = image['image_url']['url']
            h = image['original_PNG_sha256']
            assert sha(source / name) == sha(target / name) == h
            used_images.add(h)
        comparisons.append({'candidate': number, 'source_packet_sha256': left['sha256'],
                            'target_packet_sha256': right['sha256'], 'source_full_body_sha256': p['source_body_sha256'],
                            'target_full_body_sha256': q['source_body_sha256'], 'exact_full_legal_input_and_PNGs_and_candidate_equal': True})
        row = copy.deepcopy(original)
        row.update({'packet_sha256': right['sha256'], 'source_response_sha256': q['source_response_sha256'],
                    'source_full_legal_body_sha256': q['source_body_sha256'],
                    'same_existing_source_review_reused': True, 'new_independent_source_review': False,
                    'reused_source_packet_sha256': left['sha256'], 'execution_or_official_score_joined': False})
        rows.append(row)
    positive = [v['candidate'] for v in rows if v['candidate_semantic_Mirage'] is True]
    unknown = [v['candidate'] for v in rows if v['candidate_semantic_Mirage'] is None]
    root = HERE / ('exact-source-prefix-reuse-' + str(time.time_ns()))
    root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'equality.json', {'source_review': str(previous), 'source_review_sha256': sha(previous / 'review.json'),
         'target_packets': str(target), 'source_packets': str(source), 'comparisons': comparisons,
         'all_complete_legal_inputs_original_PNGs_and_replies_exactly_equal': True})
    save(root / 'review.json', {'time': time.time(), 'source_packets': str(target),
         'source_packets_seal_sha256': sha(target / 'seal.json'), 'candidate_coverage': len(rows),
         'unreviewed_within_exported_prefix': 0, 'partial_prefix_only': True,
         'completed_trajectory_review': False, 'whole_final_trajectory_not_fully_reviewed': True,
         'literal_negative_candidates': sum(v['candidate_semantic_Mirage'] is False for v in rows),
         'definite_positive_candidates': positive, 'unresolved_candidates': unknown,
         'trajectory_semantic_Mirage': True if positive else None,
         'at_least_one_boundary_occurrence_despite_unfinished_trajectory': bool(positive),
         'true_first_trigger_established': False, 'unknown_is_not_no_Mirage': True,
         'pure_native_WAIT_exclusions': sum(v.get('pure_native_WAIT', False) for v in rows),
         'unique_original_images_reused_after_exact_SHA_identity': sorted(used_images),
         'same_prior_source_review_reused_after_exact_full_input_and_reply_equality': True,
         'existing_source_review': str(previous), 'existing_source_review_sha256': sha(previous / 'review.json'),
         'new_independent_reviewer_count': 0, 'reviewer_count': 1, 'fully_blind': False,
         'prior_task_condition_and_development_findings_known': True,
         'source_judgments_sealed_before_this_run_execution_and_official_join': True,
         'PRIVATE_source_index_or_scorer_used_for_labeling': False, 'rows': rows,
         'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'goal': 'active'})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    print(json.dumps({'review': str(root), 'coverage': len(rows), 'definite_positive_candidates': positive,
                      'unresolved_candidates': unknown, 'same_source_review_reused': True,
                      'completed_trial_or_efficacy': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
