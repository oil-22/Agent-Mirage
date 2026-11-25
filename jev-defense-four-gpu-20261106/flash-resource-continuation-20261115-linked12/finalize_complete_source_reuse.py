"""Mark exact reused labels complete only when the whole terminal is covered.

No new label or reviewer is created. The source judgments were sealed before
this terminal join. Partial prefixes cannot become complete on their own.
"""
import argparse
import json
import time
from pathlib import Path
from control import HERE, save, sha


def load(path):
    return json.loads(Path(path).read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix-review', type=Path, required=True)
    parser.add_argument('--terminals', type=Path, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--supersedes', type=Path)
    args = parser.parse_args()
    source = args.prefix_review.resolve()
    assert source.parent == HERE
    assert all(sha(source / n) == h for n, h in load(source / 'seal.json').items())
    review = load(source / 'review.json')
    assert review['partial_prefix_only'] and not review['completed_trajectory_review']
    assert review['same_prior_source_review_reused_after_exact_full_input_and_reply_equality']
    original = Path(review['existing_source_review'])
    assert all(sha(original / n) == h for n, h in load(original / 'seal.json').items())
    prior = load(original / 'review.json')
    assert prior['completed_trajectory_review'] and not prior['partial_prefix_only']
    assert sha(original / 'review.json') == review['existing_source_review_sha256']
    terminal = next(v for v in load(args.terminals)['result']['terminals'] if v['run']['run_id'] == args.run)
    assert not terminal['infrastructure_failure'] and not terminal['cleanup_error']
    assert review['candidate_coverage'] == len(review['rows']) == prior['candidate_coverage'] == terminal['actor_calls']
    assert review['unreviewed_within_exported_prefix'] == 0
    labels = [v['candidate_semantic_Mirage'] for v in review['rows']]
    assert labels == [v['candidate_semantic_Mirage'] for v in prior['rows']]
    whole_label = True if any(v is True for v in labels) else (
        None if any(v is None for v in labels) else False)
    assert prior['trajectory_semantic_Mirage'] is whole_label
    superseded = None
    if args.supersedes:
        superseded = args.supersedes.resolve()
        assert superseded.parent == HERE
        assert all(sha(superseded / n) == h for n, h in load(superseded / 'seal.json').items())
        old = load(superseded / 'review.json')
        assert old['completed_trajectory_review'] and old['rows'] == review['rows']
        assert old['prior_prefix_review'] == str(source)
        assert old['trajectory_semantic_Mirage'] is None and whole_label is False
    mappings = load(Path(review['source_packets']) / 'PRIVATE-source-index.json')
    assert len(mappings) == review['candidate_coverage'] and {v['run_id'] for v in mappings} == {args.run}
    dest = HERE / ('complete-source-review-reuse-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {**review, 'time': time.time(), 'prior_prefix_review': str(source),
         'prior_prefix_review_sha256': sha(source / 'review.json'),
         'partial_prefix_only': False, 'completed_trajectory_review': True,
         'whole_final_trajectory_not_fully_reviewed': False,
         'trajectory_semantic_Mirage': whole_label,
         'complete_trajectory_label_copied_from_exact_complete_source_not_partial_default': True,
         'superseded_completed_metadata_review': str(superseded) if superseded else None,
         'superseded_review_seal_sha256': sha(superseded / 'seal.json') if superseded else None,
         'original_candidate_labels_unchanged': True,
         'at_least_one_boundary_occurrence_despite_unfinished_trajectory': False,
         'terminal_count_only_join_after_labels': str(args.terminals.resolve()),
         'terminal_count_audit_sha256': sha(args.terminals),
         'terminal_sha256': terminal['terminal_sha256'],
         'execution_or_official_outcome_not_used_to_replace_labels': True,
         'source_labels_previously_sealed_before_this_terminal_count_join': True,
         'new_independent_reviewer_count': 0, 'Mirage_reduction': None})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'run_id': args.run,
         'complete_candidate_coverage': review['candidate_coverage'], 'review_reused_not_independent': True,
         'definite_positive_candidates': review['definite_positive_candidates'],
         'unresolved_candidates': review['unresolved_candidates'], 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
