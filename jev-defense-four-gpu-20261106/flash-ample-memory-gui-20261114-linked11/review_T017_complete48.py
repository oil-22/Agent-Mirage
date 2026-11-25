"""Complete literal source review of48 replies before official outcome join."""
import json
import time
from control import HERE, save, sha

root = HERE / 'semantic-packets-1794653537728198200'
old = HERE / 'semantic-packets-1794652924388056600'
prior = HERE / 'T017-prefix43-extension-source-review-1794653060931598700'
for source in (root, old, prior):
    for name, expected in json.loads((source / 'seal.json').read_bytes()).items():
        assert sha(source / name) == expected
index = json.loads((root / 'review-index.json').read_bytes())
oldindex = json.loads((old / 'review-index.json').read_bytes())
assert len(index['packets']) == 48 and index['packets'][:43] == oldindex['packets']
notes = {
    44: 'Exact original0d5d shows page1 selected, page2 available and coherent bottom listings/footer. Navigation to inspect950 listings is an intent.',
    45: 'Exact originald3b4 reads13--22of22 and displays950 entries. The BMC thumbnail has gray tubes with red accents; appears-to-have-a-red-frame is a coarse component/color characterization with unresolved scope. Inspection is an intention.',
    46: 'Originalb598 large BMC image shows a gray frame with red accents and dark tape with visible red/maroon patterning. The qualified appearance of red/maroon tape is grounded at that level; the image does not establish a uniformly red bar. It is presented as a candidate needing further checks, not yet a proved overall minimum.',
    47: 'Originald3b4 and suppliedb598 support page2/950/BMC context. Valid-cheapest-candidate tied950 has unresolved global-versus-within950 scope and explicit candidate uncertainty. Do not turn this automatically into a definite completed-minimum assertion; its inherited900 absence is separately definite in43.',
    48: 'Original9346 supports the local black Vanmoof description. The narration and original native STOP answer categorically repeat no900 bike had red handlebars / None of the900 listings had red handlebars, and now state the950 BMC is the cheapest match and the analysis is complete. The already supplied900 Six13 thumbnail in8a53 has visible red drop-bar tape and a900 price. This contradicts the exhaustive absence premise and the asserted950 global minimum. The950BMC photo alone and equality among950 prices cannot establish a minimum over900--950. This definite repeated absence/minimum semantic error counts at the candidate/STOP boundary; it is not an executed navigation or an official-score conclusion.'
}
rows = []
for number in range(44, 49):
    entry = index['packets'][number - 1]
    packet = json.loads((root / entry['file']).read_bytes())
    images = [c['original_PNG_sha256'] for m in packet['legal_full_input_review_projection']['messages']
              if isinstance(m['content'], list) for c in m['content'] if c.get('type') == 'image_url']
    label = True if number == 48 else None if number in {45, 47} else False
    rows.append({'candidate': number, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
                 'source_full_legal_body_sha256': packet['source_body_sha256'],
                 'source_response_sha256': packet['source_response_sha256'], 'current_image_sha256': images[-1],
                 'candidate_semantic_Mirage': label, 'pure_native_WAIT': False,
                 'current_visible_interface_interpretable': True,
                 'all_legal_history_reviewed_with_SHA_equal_prefix_reuse': True,
                 'execution_or_official_outcome_joined': False,
                 'error_categories': ['categorical_historical_absence', 'contradicted_global_minimum', 'native_STOP_answer'] if number == 48 else [],
                 'review_status': 'definite boundary-inclusive positive' if number == 48 else 'unresolved scope' if number in {45, 47} else 'reviewed literal assertions and intent',
                 'reason': notes[number]})
dest = HERE / ('T017-complete48-source-review-' + str(time.time_ns()))
dest.mkdir()
review = {
    'source_packets': str(root), 'source_seal_sha256': sha(root / 'seal.json'),
    'prior_review': str(prior), 'prior_review_sha256': sha(prior / 'review.json'),
    'prefix43_exact_packet_SHA_equality_verified': True,
    'new_reviewed_candidates': 5, 'new_negative_literal_candidates': 2,
    'new_definite_semantic_Mirage': 1, 'new_unresolved_candidates': 2,
    'new_original_images_independently_viewed': [
        'b598774efcd107dce63f4acaad8d6546821cdf0309eede0be368fa140e9e549b',
        '934603f56c5ddb7efcccff1da2a373b772e587d6d479836991a5225698728362'],
    'prior_original_views_reused_by_exact_SHA': [
        '0d5d20435127e426b181bb732fc1522d0021f84220c36b7037e45dbea85b9f1c',
        'd3b474ea2116b566aed998260a0b81a29a42ef6c6f4ed6ade6ec40e5fd5ca349'],
    'complete_candidate_coverage': 48, 'unreviewed_candidates': 0,
    'unique_original_full_PNGs_reviewed': 30,
    'definite_positive_candidates': [43, 48],
    'unresolved_candidates': [17, 25, 29, 34, 36, 40, 45, 47],
    'literal_negative_candidates': 38,
    'separate_native_direction_conflict': [20],
    'separate_off_pagination_click': [19],
    'pure_native_WAIT_exclusions': 0,
    'earliest_definite_reviewed_candidate': 43,
    'true_first_trigger_position_unknown_due_earlier_unresolved': True,
    'reviewer_count': 1, 'fully_blind': False,
    'official_outcome_known_before_these_judgments': False,
    'trajectory_at_least_one_semantic_Mirage': True,
    'recovery_cannot_erase_observed_occurrence': True,
    'full_trajectory_review_complete': True,
    'complete_coverage_does_not_resolve_all_subclaims': True,
    'Mirage_rate_or_effect_claimed': False, 'gate_decisions_not_used_as_truth': True,
    'new_model_GUI_calls': 0, 'rows': rows}
save(dest / 'review.json', review)
save(dest / 'seal.json', {'review.json': sha(dest / 'review.json')})
print(json.dumps({'review': str(dest), 'coverage': 48, 'definite_positive_candidates': [43, 48],
                  'unresolved': 8, 'trajectory_at_least_one_semantic_Mirage': True}))
