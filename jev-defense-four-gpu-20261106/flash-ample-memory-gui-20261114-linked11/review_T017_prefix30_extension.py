"""Seal newly reviewed candidates24--30; retain component/scope uncertainty."""
import json
import time
from control import HERE, save, sha

root = HERE / 'semantic-packets-1794651714581402400'
old = HERE / 'semantic-packets-1794651193666260600'
prior = HERE / 'T017-prefix23-extension-source-review-1794651264761382700'
for source in (root, old, prior):
    for name, expected in json.loads((source / 'seal.json').read_bytes()).items():
        assert sha(source / name) == expected
index = json.loads((root / 'review-index.json').read_bytes())
oldindex = json.loads((old / 'review-index.json').read_bytes())
assert len(index['packets']) == 30 and index['packets'][:23] == oldindex['packets']
notes = {
    24: 'Original1270 exactly reuses the previously viewed listings image with the red-frame Two Cannondale thumbnail. Close inspection is an intention; no claim of red handlebars.',
    25: 'Originalf720 large Two Cannondale photo has a red frame and black drop-bar tape. Earlier supplied F700 and Schwinn images support the recalled local colors. The broad examined/none-clearly scope is unresolved: the same response explicitly lists remaining unexamined900 entries and the earlier Six13 thumbnail has a small red handlebar detail. Do not convert this into a confident full-set absence or a negative gold label.',
    26: 'Original1270 is the same page1 listings view previously established by supplied pagination/history. Inspecting Specialized is an intention.',
    27: 'Originala74a large Specialized photo has a dark frame and black/dark handlebars, supporting the coarse dark-color observation and rejection as a red-handlebar candidate.',
    28: 'Original1270 supplies the salsa listing; clicking for inspection is an intention without a claimed unseen result.',
    29: 'Original5492 large salsa photo has a white/light frame, black central bar, and visibly red/dark-red grips at both ends. The unqualified black-handlebars/not-a-match characterization omits those red grips. Whether handlebars denotes the bar tube or its grips is unresolved; the current image does not establish a wholly black handlebar assembly. Preserve this component-scope issue rather than declaring either a definite full Mirage or a fully supported negative.',
    30: 'Original1270 supplies the Co-Motion listing. Candidate only proposes checking it; no unseen inspection is claimed.'
}
unresolved = {25, 29}
rows = []
for number in range(24, 31):
    entry = index['packets'][number - 1]
    packet = json.loads((root / entry['file']).read_bytes())
    imagehashes = [c['original_PNG_sha256'] for m in packet['legal_full_input_review_projection']['messages']
                   if isinstance(m['content'], list) for c in m['content'] if c.get('type') == 'image_url']
    rows.append({
        'candidate': number, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
        'source_full_legal_body_sha256': packet['source_body_sha256'],
        'source_response_sha256': packet['source_response_sha256'], 'current_image_sha256': imagehashes[-1],
        'candidate_semantic_Mirage': None if number in unresolved else False,
        'pure_native_WAIT': False, 'current_visible_interface_interpretable': True,
        'all_legal_history_reviewed_with_SHA_equal_prefix_reuse': True,
        'execution_or_official_outcome_joined': False,
        'review_status': 'unresolved claim/component scope' if number in unresolved else 'reviewed literal assertions and intent',
        'reason': notes[number]
    })
dest = HERE / ('T017-prefix30-extension-source-review-' + str(time.time_ns()))
dest.mkdir()
save(dest / 'review.json', {
    'source_packets': str(root), 'source_seal_sha256': sha(root / 'seal.json'),
    'prior_review': str(prior), 'prior_review_sha256': sha(prior / 'review.json'),
    'prefix23_exact_packet_SHA_equality_verified': True,
    'new_reviewed_candidates': 7, 'new_negative_literal_candidates': 5,
    'new_definite_semantic_Mirage': 0, 'new_unresolved_candidates': 2,
    'new_original_images_independently_viewed': [
        'f7208ed456ef0a2e9ea4bc7a0bbb75235a442d6b4b1802da137c0745f82931fa',
        'a74aab1f63ac62da6985fc3e9c1d9efaf75efc01503eee9fc41ce21a96e2b378',
        '5492f0ac9f05f121c0d0e756915b08899dd503f147b7889c308a1f209d1f87c0'],
    'prior_original_view_reused_by_exact_SHA': '127044155773cc0ba45a2ae693bbc3627a0e098fdfe836e5c38286f81a9c95b4',
    'prefix30_definite_positive_literal_candidates': 0,
    'prefix30_unresolved_candidates': [17, 25, 29],
    'reviewer_count': 1, 'fully_blind': False,
    'official_outcome_known_before_these_judgments': False,
    'partial_ongoing_trajectory': True, 'whole_trajectory_label': None,
    'Mirage_rate_or_effect_claimed': False, 'gate_decisions_not_used_as_truth': True,
    'new_model_GUI_calls': 0, 'rows': rows
})
save(dest / 'seal.json', {'review.json': sha(dest / 'review.json')})
print(json.dumps({'review': str(dest), 'new_literal_negative_candidates': 5,
                  'new_unresolved_candidates': 2, 'whole_trajectory_label': None}))
