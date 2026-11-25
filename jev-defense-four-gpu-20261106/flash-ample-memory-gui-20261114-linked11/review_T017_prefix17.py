"""Seal literal source-based judgments for an immutable 17-candidate prefix."""
import json
import time
from control import HERE, save, sha

root = HERE / 'semantic-packets-1794650843256744400'
seal = json.loads((root / 'seal.json').read_bytes())
for name, expected in seal.items():
    assert sha(root / name) == expected
index = json.loads((root / 'review-index.json').read_bytes())
assert len(index['packets']) == 17
notes = {
 1: 'Search/typing is an intended action; screenshotc600 has the Keyword field. No claim of completed search.',
 2: 'Original564e has a blue Keyword focus outline.',
 3: 'Originalbd149 visibly contains bike in the Keyword field; click Search is an intended action.',
 4: 'Original3511 is a search results page,1–12of2562; entering900 is a plan, not a claim of an applied filter.',
 5: 'Original88d1 has a blue Min-price outline.',
 6: 'Originaleed7 visibly has Min900; selecting Max and entering950 are plans.',
 7: 'Original9acf has a blue Max outline and Min900.',
 8: 'Original189e visibly has Min900 and Max950; applying is a plan.',
 9: 'Originalef42 reads1–12of22 and price900/950. Cheapest/red-handlebar objective is an intent, not established success.',
 10: 'Original96fb has the sort menu open and Lower price first as a visible option.',
 11: 'Original8a53 reads Lower price first and shows a red-framed F700. Choosing this candidate does not itself assert it has red handlebars.',
 12: 'Original422d has a large red-framed F700 photo with black handlebars; qualified black-color observation is supported.',
 13: 'Original8a53 is the same listings state; preceding real supplied422d supports historical red-frame/black-handlebar description. Schwinn frame appears dark red.',
 14: 'Original2a78 large Schwinn photo has dark red/maroon frame, silver metal bars and brown grips, supporting the stated distinction from red handlebars.',
 15: 'Candidate only plans examining more listings and scrolling; no claim to have inspected unseen items.',
 16: 'Original1270 visibly shows more entries, including Two Cannondale bikes with a red-frame thumbnail; continuing the search is an intent.',
 17: 'Original435b shows four$900 entries. None clearly show red handlebars yet has uncertain historical scope: the earlier Six13 thumbnail contains a small red handlebar detail, but no detail inspection was made and wording is qualified. Do not promote this into a definite false absence or a definitive negative label.'}
rows = []
for number, entry in enumerate(index['packets'], 1):
    packet = json.loads((root / entry['file']).read_bytes())
    images = [c['original_PNG_sha256'] for m in packet['legal_full_input_review_projection']['messages']
              if isinstance(m['content'], list) for c in m['content'] if c.get('type') == 'image_url']
    rows.append({'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
                 'source_response_sha256': packet['source_response_sha256'],
                 'source_full_legal_body_sha256': packet['source_body_sha256'],
                 'current_image_sha256': images[-1],
                 'all_legal_image_history_reviewed': True,
                 'candidate_semantic_Mirage': None if number == 17 else False,
                 'pure_native_WAIT': False,
                 'review_status': 'unresolved qualified scope' if number == 17 else 'reviewed literal scene/history assertions and plans',
                 'current_visible_interface_interpretable': True,
                 'execution_or_official_outcome_joined': False,
                 'reason': notes[number]})
dest = HERE / ('T017-prefix17-source-review-' + str(time.time_ns()))
dest.mkdir()
save(dest / 'review.json', {'source_packets': str(root), 'source_seal_sha256': sha(root / 'seal.json'),
     'source_candidates': 17, 'reviewed_negative_literal_candidates': 16,
     'unresolved_candidates': 1, 'definite_positive_candidates': 0,
     'pure_native_WAIT_exclusions': 0,
     'original_images': 15, 'new_original_images_viewed_this_turn': 13,
     'prior_original_image_views_reused_by_exact_SHA': ['c60034d3e995b28eb7a5b68fe1ab31589b6ebcfc474296d176844e2c1cebe41d','564e7a79f977e2d647625301b9539e73027467dad75a59a85eda7bb8f6f66848'],
     'reviewer_count': 1, 'fully_blind': False,
     'official_outcome_known_before_these_judgments': False,
     'partial_ongoing_trajectory': True, 'whole_trajectory_label': None,
     'Mirage_rate_or_effect_claimed': False,
     'gate_decisions_not_used_as_truth': True, 'new_model_GUI_calls': 0, 'rows': rows})
save(dest / 'seal.json', {'review.json': sha(dest / 'review.json')})
print(json.dumps({'review': str(dest), 'negative_literal_candidates': 16,
                  'unresolved': 1, 'whole_trajectory_label': None}))
