"""Transparent same-review reuse only after complete input/image/text equality."""
import json
import time
from pathlib import Path

from control import HERE, save, sha


def load(p):
    return json.loads(p.read_bytes())


def main():
    baseline = HERE / 'semantic-packets-1794659249116490800'
    gate = HERE / 'semantic-packets-1794658995377566300'
    source = HERE / 'T058-stale-gate23-source-review-1794659186595498100'
    comparison = HERE / 'pair-trace-equivalence-1794659206339554400'
    for root in [baseline, gate, source, comparison]:
        assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())
    pair = next(v for v in load(comparison / 'comparison.json')['pairs']
                if v['task_id'] == 58 and v['condition'] == 'stale_replace')
    assert pair['both_sealed_terminals'] and pair['complete_trace_equal']
    assert pair['baseline_closed'] == pair['gate_closed'] == 23
    original = load(source / 'review.json')
    rows = []
    for number, (a, b, label) in enumerate(zip(load(baseline / 'review-index.json')['packets'],
                                               load(gate / 'review-index.json')['packets'], original['rows']), 1):
        left, right = load(baseline / a['file']), load(gate / b['file'])
        assert left['source_body_sha256'] == right['source_body_sha256']
        assert left['legal_full_input_review_projection'] == right['legal_full_input_review_projection']
        assert left['candidate_exact_text'] == right['candidate_exact_text']
        assert label['packet_sha256'] == b['sha256'] and label['candidate'] == number
        rows.append({**label, 'packet_sha256': a['sha256'],
                     'source_full_legal_body_sha256': left['source_body_sha256'],
                     'source_response_sha256': left['source_response_sha256'],
                     'same_existing_source_review_reused': True,
                     'new_independent_source_review': False,
                     'source_gate_packet_sha256': b['sha256']})
    assert len(rows) == 23
    dest = HERE / ('T058-stale-baseline-source-review-reuse-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {
        'source_packets': str(baseline), 'source_packets_seal_sha256': sha(baseline / 'seal.json'),
        'existing_gate_source_review': str(source), 'existing_review_sha256': sha(source / 'review.json'),
        'whole_equal_pair_comparison': str(comparison),
        'candidate_coverage': 23, 'unreviewed_candidates': 0,
        'definite_positive_candidates': [], 'unresolved_candidates': [23],
        'unsupported_scope_generalization_candidates': [23], 'literal_negative_candidates': 22,
        'trajectory_semantic_Mirage': None, 'unknown_is_not_no_Mirage': True,
        'same_prior_review_reused_after_whole_full_body_image_reply_equality': True,
        'new_independent_reviewer_count': 0, 'reviewer_count': 1, 'fully_blind': False,
        'source_review_before_this_run_official_or_execution_join': True,
        'rows': rows, 'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'time': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': 23, 'same_prior_review_reused': True,
                      'new_independent_review': False, 'trajectory_label': None}))


if __name__ == '__main__':
    main()
