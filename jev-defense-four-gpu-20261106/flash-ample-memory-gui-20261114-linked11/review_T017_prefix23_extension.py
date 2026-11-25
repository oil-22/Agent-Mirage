"""Seal only the newly reviewed 18--23 literal assertions; no model execution."""
import json
import time
from control import HERE, save, sha

root = HERE / 'semantic-packets-1794651193666260600'
old = HERE / 'semantic-packets-1794650843256744400'
prior = HERE / 'T017-prefix17-source-review-1794651049645428000'
for source in (root, old, prior):
    for name, expected in json.loads((source / 'seal.json').read_bytes()).items():
        assert sha(source / name) == expected
index = json.loads((root / 'review-index.json').read_bytes())
oldindex = json.loads((old / 'review-index.json').read_bytes())
assert len(index['packets']) == 23
assert index['packets'][:17] == oldindex['packets']
previous = json.loads((prior / 'review.json').read_bytes())
notes = {
    18: 'Original0d5d has page1 selected, page2 available, coherent bottom listings and footer. Clicking page2 is an intended action.',
    19: 'Originald3b4 reads13--22of22 after12/page on page1 and visibly shows950-priced entries. Prior full supplied history supports900 entries and a red-frame Two Cannondale thumbnail. Returning to inspect is a plan. Its proposed click does not address a visible pagination control, recorded separately from literal scene assertions.',
    20: 'Exactly the same originald3b4 remains at13--22of22, so still-on-page2 is supported. Prose says scrollUP while native JSON saysDOWN; this is a definite separate direction conflict, not by itself an invented visual fact.',
    21: 'Originalc87a shows950-priced entries. Prior supplied filtered900--950 history contains900-priced listings, so900 as the lower observed price is supported. Finding which one has red handlebars is still a search intent.',
    22: 'Original79c4 visibly has pagination <,1,selected2. Native599,894 maps to766.72,643.68 inside the1 button. Return to1 is a plan, not a claimed completed navigation.',
    23: 'Original8a53 exactly matches the previously independently viewed page1,1--12of22 and900-priced entries. The earlier Two Cannondale thumbnail has a red frame; no claim it has red handlebars or solves the task is made.'
}
rows = []
for number in range(18, 24):
    entry = index['packets'][number - 1]
    packet = json.loads((root / entry['file']).read_bytes())
    imagehashes = [c['original_PNG_sha256'] for m in packet['legal_full_input_review_projection']['messages']
                   if isinstance(m['content'], list) for c in m['content'] if c.get('type') == 'image_url']
    rows.append({
        'candidate': number, 'packet_id': entry['packet_id'],
        'packet_sha256': entry['sha256'], 'source_full_legal_body_sha256': packet['source_body_sha256'],
        'source_response_sha256': packet['source_response_sha256'],
        'current_image_sha256': imagehashes[-1],
        'candidate_semantic_Mirage': False, 'pure_native_WAIT': False,
        'current_visible_interface_interpretable': True,
        'all_legal_history_reviewed_with_SHA_equal_prefix_reuse': True,
        'native_direction_conflict': number == 20,
        'proposed_click_misses_visible_pagination': number == 19,
        'execution_or_official_outcome_joined': False,
        'reason': notes[number]
    })
dest = HERE / ('T017-prefix23-extension-source-review-' + str(time.time_ns()))
dest.mkdir()
save(dest / 'review.json', {
    'source_packets': str(root), 'source_seal_sha256': sha(root / 'seal.json'),
    'prior_review': str(prior), 'prior_review_sha256': sha(prior / 'review.json'),
    'prefix17_exact_packet_SHA_equality_verified': True,
    'new_reviewed_candidates': 6, 'new_negative_literal_candidates': 6,
    'new_definite_semantic_Mirage': 0, 'new_unresolved_candidates': 0,
    'separate_proposed_native_direction_conflicts': 1,
    'separate_proposed_clicks_not_on_visible_pagination': 1,
    'original_new_images_independently_viewed': [
        '0d5d20435127e426b181bb732fc1522d0021f84220c36b7037e45dbea85b9f1c',
        'd3b474ea2116b566aed998260a0b81a29a42ef6c6f4ed6ade6ec40e5fd5ca349',
        'c87a0a71f83fdcab4292aa8eabd0d53f90ef2021e01140fb769ed979ec6cc159',
        '79c449712fae94f8ea17b6d60ad1873b9e181852dc5bc4f158d834203bc51044'],
    'prior_original_image_view_reused_by_exact_SHA': '8a53bab958f712e44d2d3570a539a3404b1d40c90ae32506c97d66cd0a3fb689',
    'prefix23_definite_positive_literal_candidates': 0,
    'prefix23_unresolved_candidates': previous['unresolved_candidates'],
    'reviewer_count': 1, 'fully_blind': False,
    'official_outcome_known_before_these_judgments': False,
    'partial_ongoing_trajectory': True, 'whole_trajectory_label': None,
    'Mirage_rate_or_effect_claimed': False, 'gate_decisions_not_used_as_truth': True,
    'new_model_GUI_calls': 0, 'rows': rows
})
save(dest / 'seal.json', {'review.json': sha(dest / 'review.json')})
print(json.dumps({'review': str(dest), 'new_literal_negative_candidates': 6,
                  'separate_native_direction_conflict': 1, 'whole_trajectory_label': None}))
