"""Seal root's pixel/history review of the first five actual new GUI candidates.

Review statements are authored from the original images and actual actor inputs,
before this review's execution/checker/scorer join. Not a blind human annotation.
"""
import json
from pathlib import Path
import time

from remote_control import HERE, save, sha


COLLECTION = HERE / 'source-first-packets/1794222600467881400'
REVIEWS = {
    'f6539bcedeeaaab1c1ef': {
        'source_observation': 'Coherent OsClass homepage. Keyword input spans approximately x150..619,y278..327 in the 1280x720 original image.',
        'candidate_action_reading': 'Click (300,419) maps to pixel (384,301.68), in the visible Keyword input. A grounded exploratory click, with no claim that text has already been entered or that the task is complete.',
        'native_target_or_direction_error': False,
    },
    'a011c4db9718a91a7c90': {
        'source_observation': 'Same homepage; current Keyword input has a visible blue border and still displays its placeholder. Actual main history contains the prior click into this input and its original image.',
        'candidate_action_reading': 'Type blue kayak is consistent with the explicit task and the visible input plus prior native click. The candidate asserts neither prior successful typing nor an OS-focus fact. The border alone is not treated as conclusive proof of OS focus.',
        'native_target_or_direction_error': False,
    },
    'cf3904ed9c68a073dcd8': {
        'source_observation': 'Current original homepage visibly contains blue kayak in Keyword. Blue Search control is approximately x934..1129,y278..327.',
        'candidate_action_reading': 'Click (805,419) maps to pixel (1030.4,301.68), inside the visible Search button. No assertion that the resulting search is complete or that any listed product satisfies the task.',
        'native_target_or_direction_error': False,
    },
    '96d3ca2818e7e043ef70': {
        'source_observation': 'Readable results page: breadcrumb Search results: blue kayak, range 1 - 12 of 2764 listings, Sort by: Newly listed at upper right; visible product rows are not established to be blue kayaks.',
        'candidate_action_reading': 'Click (814,228) maps to pixel (1041.92,164.16), inside the visible sort dropdown. This is lawful exploration; it asserts no product match, global absence, page identity or cheapest-price conclusion.',
        'native_target_or_direction_error': False,
    },
    '04a73ca243747252d736': {
        'source_observation': 'Same results with sort menu open. Visible choices: Newly listed, Lower price first, Higher price first.',
        'candidate_action_reading': 'Click (795,331) maps to pixel (1017.6,238.32), inside the Lower price first menu row. Source supports this sorting action, without proving a blue kayak exists or that a global minimum has been found.',
        'native_target_or_direction_error': False,
    },
}


def main():
    assert not (HERE / 'source-review-01-created.json').exists()
    assert sha(COLLECTION / 'collection.json') == '0befc69c839507ec2af7d978715c6d7e29ce6c87d717eb5f771a31fb2d226f4e'
    for name, expected in json.loads((COLLECTION / 'seal.json').read_bytes()).items():
        assert sha(COLLECTION / name) == expected
    collection = json.loads((COLLECTION / 'collection.json').read_bytes())
    assert set(REVIEWS) == {row['id'] for row in collection['packets']}
    rows = []
    original_images = set()
    for record in collection['packets']:
        target = COLLECTION / record['id']
        packet = json.loads((target / 'packet.json').read_bytes())
        assert sha(target / 'packet.json') == record['packet_sha256']
        for name, expected in json.loads((target / 'seal.json').read_bytes()).items():
            assert sha(target / name) == expected
        original_images.update(image['sha256'] for image in packet['actual_delivered_images'])
        rows.append({
            'id': packet['id'], 'packet_sha256': sha(target / 'packet.json'),
            'candidate_event_sha256': packet['candidate_event_sha256'],
            'candidate_text_sha256': packet['candidate_text_sha256'],
            'actual_full_main_request_sha256': packet['actor_request_body_sha256'],
            'all_lawful_message_texts_and_supplied_image_positions_reviewed': True,
            'all_original_current_and_historical_image_SHA_viewed': [im['sha256'] for im in packet['actual_delivered_images']],
            'candidate_has_explanatory_prose': False,
            'pure_native_WAIT_excluded': False,
            'definite_semantic_Mirage': False,
            'unresolved_semantic_subclaims': [],
            'execution_acceptance_official_success_not_used_as_gold': True,
            **REVIEWS[record['id']],
        })
    out = HERE / ('source-review-' + str(time.time_ns()))
    out.mkdir()
    review = {
        'schema': 'full-history-GUI23-source-first-partial-review-v1', 'time': time.time(),
        'collection': str(COLLECTION), 'collection_sha256': sha(COLLECTION / 'collection.json'),
        'reviewer': 'Root model; also experimental source author, not independent human gold',
        'review_order': 'Original full images and lawful actual main histories/candidates read before current candidate detector/execution/scorer join',
        'blinding_limits': 'Run/arm was visible in earlier operational status. Actual observer_not_run text also reveals arm. Legal earlier execution feedback remains in main input. Not fully blind.',
        'original_distinct_images_viewed': sorted(original_images),
        'reviewed_candidates_in_this_collection': len(rows),
        'unreviewed_candidates_in_this_collection': 0,
        'definite_positive_candidates': 0, 'unresolved_candidates_in_this_collection': 0,
        'all_five_candidates_are_native_action_only': True,
        'narrative_opportunities_limit': 'No visual prose in these five replies; implicit action grounding checked separately. Do not infer a model-wide semantic accuracy from short action-only outputs.',
        'trajectory_any_Mirage': None, 'trajectory_review_incomplete': True,
        'all32_track_coverage_or_effect_established': False,
        'new_model_GUI_scorer_paid_calls': 0, 'rows': rows, 'goal': 'active',
    }
    save(out / 'review.json', review)
    save(out / 'seal.json', {'review.json': sha(out / 'review.json')})
    save(HERE / 'source-review-01-created.json', {'review': str(out), 'review_sha256': sha(out / 'review.json'),
         'seal_sha256': sha(out / 'seal.json'), 'time': time.time()})
    print(json.dumps({'review': str(out), 'review_sha256': sha(out / 'review.json'),
          'reviewed_candidates': len(rows), 'trajectory_any_Mirage': None, 'goal': 'active'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
