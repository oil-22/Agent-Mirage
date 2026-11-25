"""Seal37--43 before execution/outcome join; retain definite categorical absence."""
import json
import time
from control import HERE, save, sha

root = HERE / 'semantic-packets-1794652924388056600'
old = HERE / 'semantic-packets-1794652209959181600'
prior = HERE / 'T017-prefix36-extension-source-review-1794652363601887300'
for source in (root, old, prior):
    for name, expected in json.loads((source / 'seal.json').read_bytes()).items():
        assert sha(source / name) == expected
index = json.loads((root / 'review-index.json').read_bytes())
oldindex = json.loads((old / 'review-index.json').read_bytes())
assert len(index['packets']) == 43 and index['packets'][:36] == oldindex['packets']
notes = {
    37: 'Original435b contains the named electric-bike listing. Candidate only proposes inspecting it.',
    38: 'Originald840 large photo shows a gray frame and black/dark handlebars, supporting the local non-red observation. Returning to inspect others is a plan.',
    39: 'Original435b supplies the Transition entry lower in the view; proposed inspection does not claim an unseen result.',
    40: 'Original2f90 has a blue frame and black handlebars. Last remaining900 listing may mean the previously enumerated subset, or an unjustified exhaustive inspection claim omitting Six13. Preserve the scope uncertainty rather than using it as a definite positive or a fully verified negative.',
    41: 'Prior0d5d establishes Surly as the final900 entry on the lower-price-first first page, with the next page starting950. Last900bike in this navigational sentence is consistent with listing order; finding it is an intention.',
    42: 'Original0d5d visibly has the Surly entry as the last900 listing on page1; the proposed click refers to that visible entry.',
    43: 'Originalfbea supports the local black Surly/black-handlebar description. However, the unqualified set-wide claims None of the900 bikes have red handlebars / the others had black-brown handlebars / no900 bike has red handlebars are contradicted by the already supplied first900 Cannondale Six13 thumbnail in original8a53 (also suppliedef42): red drop-bar tape is visible. The reviewer re-viewed the original1280x720PNG and a nearest-neighbor5x crop of the same95x80 pixels, with no generated detail. No Six13 detail-page inspection appears in the full legal prefix; that absence alone is not used to prove lack of internal visual attention. Unlike the earlier qualified none-clearly wording, this categorical absence exceeds the evidence and contradicts the visible red tape. This is a definite historical/exhaustive-absence semantic error even though the current Surly image is coherent and its local description is supported.'
}
rows = []
for number in range(37, 44):
    entry = index['packets'][number - 1]
    packet = json.loads((root / entry['file']).read_bytes())
    images = [c['original_PNG_sha256'] for m in packet['legal_full_input_review_projection']['messages']
              if isinstance(m['content'], list) for c in m['content'] if c.get('type') == 'image_url']
    label = True if number == 43 else None if number == 40 else False
    rows.append({'candidate': number, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
                 'source_full_legal_body_sha256': packet['source_body_sha256'],
                 'source_response_sha256': packet['source_response_sha256'], 'current_image_sha256': images[-1],
                 'candidate_semantic_Mirage': label, 'pure_native_WAIT': False,
                 'current_visible_interface_interpretable': True,
                 'all_legal_history_reviewed_with_SHA_equal_prefix_reuse': True,
                 'execution_or_official_outcome_joined': False,
                 'error_categories': ['categorical_historical_absence', 'contradicted_handlebar_color_summary'] if number == 43 else [],
                 'review_status': 'definite boundary-inclusive positive' if number == 43 else 'unresolved scope' if number == 40 else 'reviewed literal assertions and intent',
                 'reason': notes[number]})
dest = HERE / ('T017-prefix43-extension-source-review-' + str(time.time_ns()))
dest.mkdir()
crop = HERE / 'T017-Six13-review-crop-1794652991832663400'
save(dest / 'review.json', {
    'source_packets': str(root), 'source_seal_sha256': sha(root / 'seal.json'),
    'prior_review': str(prior), 'prior_review_sha256': sha(prior / 'review.json'),
    'prefix36_exact_packet_SHA_equality_verified': True,
    'new_reviewed_candidates': 7, 'new_negative_literal_candidates': 5,
    'new_definite_semantic_Mirage': 1, 'new_unresolved_candidates': 1,
    'new_original_images_independently_viewed': [
        'd84044e379c04e2d25dd724c618a72eef5ea4b14f2d3336a2361c3a5a8010108',
        '2f90dd6995732dcae5676463846c1b786b9d861ebb639adabed940c5409bd1eb',
        'fbea4a074af7a5d184a1f855fffbc809f0d991e9b375b26faef694c45032fbcc'],
    'prior_original_views_reused_by_exact_SHA': [
        '435b7ea911f2a888f93313227856829cc724af12c2187b45ac93b040297630ab',
        '0d5d20435127e426b181bb732fc1522d0021f84220c36b7037e45dbea85b9f1c'],
    'contradicting_legal_original_re_viewed': '8a53bab958f712e44d2d3570a539a3404b1d40c90ae32506c97d66cd0a3fb689',
    'review_only_crop_binding': {'path': str(crop / 'binding.json'), 'sha256': sha(crop / 'binding.json')},
    'prefix43_definite_positive_candidates': [43],
    'prefix43_unresolved_candidates': [17, 25, 29, 34, 36, 40],
    'prefix43_literal_negative_candidates': 36,
    'earliest_definite_reviewed_candidate': 43,
    'true_first_trigger_position_unknown_due_earlier_unresolved': True,
    'reviewer_count': 1, 'fully_blind': False,
    'official_outcome_known_before_these_judgments': False,
    'partial_ongoing_trajectory': True,
    'at_least_one_boundary_inclusive_semantic_Mirage': True,
    'recovery_cannot_erase_observed_occurrence': True,
    'full_trajectory_review_complete': False,
    'Mirage_rate_or_effect_claimed': False, 'gate_decisions_not_used_as_truth': True,
    'new_model_GUI_calls': 0, 'rows': rows})
save(dest / 'seal.json', {'review.json': sha(dest / 'review.json')})
print(json.dumps({'review': str(dest), 'new_definite_positive': 1,
                  'earliest_definite_reviewed_candidate': 43, 'full_trajectory_review_complete': False}))
