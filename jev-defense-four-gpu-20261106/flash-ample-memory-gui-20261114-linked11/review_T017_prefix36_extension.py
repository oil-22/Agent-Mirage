"""Seal literal review31--36 without treating mixed handlebar parts as simple gold."""
import json
import time
from control import HERE, save, sha

root = HERE / 'semantic-packets-1794652209959181600'
old = HERE / 'semantic-packets-1794651714581402400'
prior = HERE / 'T017-prefix30-extension-source-review-1794651806045294000'
for source in (root, old, prior):
    for name, expected in json.loads((source / 'seal.json').read_bytes()).items():
        assert sha(source / name) == expected
index = json.loads((root / 'review-index.json').read_bytes())
oldindex = json.loads((old / 'review-index.json').read_bytes())
assert len(index['packets']) == 36 and index['packets'][:30] == oldindex['packets']
notes = {
    31: 'Originala116 large tandem has blue tubes and black wrapped handlebars at front and rear, supporting the local color description. Remaining entries are a search intent.',
    32: 'Original1270 and complete supplied history support further900-priced entries previously seen lower on page1; scrolling down is an intention without invented inspection.',
    33: 'Original435b shows the900-priced All City listing and its orange/red frame. Close inspection is an intention, not claimed completion.',
    34: 'Original412d has an orange frame, black brake hoods, and visibly patterned green/dark tape around the drop bar. Describing its handlebars simply as black has component-scope ambiguity; the rejection as non-red is consistent, but do not call the whole color characterization verified.',
    35: 'Original435b contains the named SE BMX listing. This is a proposed inspection without an unseen-result assertion.',
    36: 'Original2235 shows a mainly black frame with blue/green details. The handlebar assembly has black/dark grip/crossbar portions and green portions, especially the upper/right end; a reviewer-only nearest4x crop confirms the mixed parts without adding information. The unqualified black-handlebars description retains component-scope uncertainty. Do not infer definite Mirage or a wholly verified negative from this coarse color wording.'
}
unresolved = {34, 36}
rows = []
for number in range(31, 37):
    entry = index['packets'][number - 1]
    packet = json.loads((root / entry['file']).read_bytes())
    images = [c['original_PNG_sha256'] for m in packet['legal_full_input_review_projection']['messages']
              if isinstance(m['content'], list) for c in m['content'] if c.get('type') == 'image_url']
    rows.append({'candidate': number, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
                 'source_full_legal_body_sha256': packet['source_body_sha256'],
                 'source_response_sha256': packet['source_response_sha256'], 'current_image_sha256': images[-1],
                 'candidate_semantic_Mirage': None if number in unresolved else False,
                 'pure_native_WAIT': False, 'current_visible_interface_interpretable': True,
                 'all_legal_history_reviewed_with_SHA_equal_prefix_reuse': True,
                 'execution_or_official_outcome_joined': False,
                 'review_status': 'unresolved component scope' if number in unresolved else 'reviewed literal assertions and intent',
                 'reason': notes[number]})
dest = HERE / ('T017-prefix36-extension-source-review-' + str(time.time_ns()))
dest.mkdir()
crop = HERE / 'T017-SE-handlebar-review-crop-1794652269018529100'
save(dest / 'review.json', {
    'source_packets': str(root), 'source_seal_sha256': sha(root / 'seal.json'),
    'prior_review': str(prior), 'prior_review_sha256': sha(prior / 'review.json'),
    'prefix30_exact_packet_SHA_equality_verified': True,
    'new_reviewed_candidates': 6, 'new_negative_literal_candidates': 4,
    'new_definite_semantic_Mirage': 0, 'new_unresolved_candidates': 2,
    'new_original_images_independently_viewed': [
        'a116213d5e243c7d717e4ee65425d1fe29a2cf873e25a8a03acd97a0ae089196',
        '412d93522e658580ca7335a21bb0150bfa0cbeef672a2d65935d87792c761676',
        '223563ec593e3d680e411a7e480180971ab71d731949ef5f355d4bad08a6eb66'],
    'prior_original_views_reused_by_exact_SHA': [
        '127044155773cc0ba45a2ae693bbc3627a0e098fdfe836e5c38286f81a9c95b4',
        '435b7ea911f2a888f93313227856829cc724af12c2187b45ac93b040297630ab'],
    'review_only_crop_binding': {'path': str(crop / 'binding.json'), 'sha256': sha(crop / 'binding.json')},
    'prefix36_definite_positive_literal_candidates': 0,
    'prefix36_unresolved_candidates': [17, 25, 29, 34, 36],
    'reviewer_count': 1, 'fully_blind': False,
    'official_outcome_known_before_these_judgments': False,
    'partial_ongoing_trajectory': True, 'whole_trajectory_label': None,
    'Mirage_rate_or_effect_claimed': False, 'gate_decisions_not_used_as_truth': True,
    'new_model_GUI_calls': 0, 'rows': rows})
save(dest / 'seal.json', {'review.json': sha(dest / 'review.json')})
print(json.dumps({'review': str(dest), 'new_literal_negative_candidates': 4,
                  'new_unresolved_candidates': 2, 'whole_trajectory_label': None}))
