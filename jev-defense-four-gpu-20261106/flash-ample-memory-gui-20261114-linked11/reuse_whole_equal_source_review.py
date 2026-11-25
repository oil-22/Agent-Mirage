"""Reuse one source review only after whole completed pair and packet equality."""
import argparse
import json
import time
from pathlib import Path
from control import HERE, save, sha


def load(p):
    return json.loads(p.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    for option in ['source-packets', 'target-packets', 'source-review', 'comparison']:
        parser.add_argument('--' + option, type=Path, required=True)
    parser.add_argument('--task', type=int, required=True)
    parser.add_argument('--condition', choices=['clean', 'stale_replace'], required=True)
    parser.add_argument('--source-arm', choices=['baseline', 'gate'], required=True)
    args = parser.parse_args()
    source, target, reviewroot, comparison = [p.resolve() for p in
        [args.source_packets, args.target_packets, args.source_review, args.comparison]]
    for root in [source, target, reviewroot, comparison]:
        assert root.parent == HERE
        assert all(sha(root / name) == h for name, h in load(root / 'seal.json').items())
    pair = next(v for v in load(comparison / 'comparison.json')['pairs']
                if v['task_id'] == args.task and v['condition'] == args.condition)
    assert pair['both_sealed_terminals'] and pair['complete_trace_equal']
    original = load(reviewroot / 'review.json')
    assert Path(original['source_packets']).resolve() == source
    entries, targets = load(source / 'review-index.json')['packets'], load(target / 'review-index.json')['packets']
    count = len(entries)
    assert count == len(targets) == len(original['rows']) == original['candidate_coverage']
    assert count == pair['baseline_closed'] == pair['gate_closed']
    target_arm = 'gate' if args.source_arm == 'baseline' else 'baseline'
    run = 'flash14-T%03d-%s-' % (args.task, args.condition)
    for root, arm in [(source, args.source_arm), (target, target_arm)]:
        mappings = load(root / 'PRIVATE-source-index.json')
        assert {v['run_id'] for v in mappings} == {run + arm}
    rows = []
    for number, (entry, target_entry, label) in enumerate(zip(entries, targets, original['rows']), 1):
        a, b = load(source / entry['file']), load(target / target_entry['file'])
        assert a['source_body_sha256'] == b['source_body_sha256']
        assert a['legal_full_input_review_projection'] == b['legal_full_input_review_projection']
        assert a['candidate_exact_text'] == b['candidate_exact_text']
        assert label['candidate'] == number and label['packet_sha256'] == entry['sha256']
        rows.append({**label, 'packet_sha256': target_entry['sha256'],
                     'source_full_legal_body_sha256': b['source_body_sha256'],
                     'source_response_sha256': b['source_response_sha256'],
                     'same_existing_source_review_reused': True, 'new_independent_source_review': False,
                     'source_review_packet_sha256': entry['sha256']})
    dest = HERE / ('T%03d-%s-%s-source-review-reuse-' % (args.task, args.condition, target_arm) + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {**original,
         'source_packets': str(target), 'source_packets_seal_sha256': sha(target / 'seal.json'),
         'existing_source_review': str(reviewroot), 'existing_review_sha256': sha(reviewroot / 'review.json'),
         'whole_equal_pair_comparison': str(comparison), 'pair_comparison_seal_sha256': sha(comparison / 'seal.json'),
         'same_prior_review_reused_after_whole_full_body_image_reply_equality': True,
         'new_independent_reviewer_count': 0, 'reviewer_count': 1, 'fully_blind': False,
         'source_review_before_this_run_official_or_execution_join': True,
         'rows': rows, 'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'time': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': count, 'same_prior_review_reused': True,
                      'new_independent_review': False, 'trajectory_label': original['trajectory_semantic_Mirage']}))


if __name__ == '__main__':
    main()
