"""Seal a source-only review before joining this run's score or execution."""
import json
import time
from control import HERE, save, sha


def main():
    root = HERE / 'semantic-packets-1794657027458544900'
    prior_images = HERE / 'semantic-packets-1794653537728198200'
    prior_review = HERE / 'T017-source-review-publication-1794653905322631600'
    for source in [root, prior_images, prior_review]:
        for name, expected in json.loads((source / 'seal.json').read_bytes()).items():
            assert sha(source / name) == expected
    index = json.loads((root / 'review-index.json').read_bytes())['packets']
    assert len(index) == 12
    notes = {
        1: 'The original c600 contains the Keyword input; clicking it and later typing is an intention, not a claim that search already completed.',
        2: 'The supplied original c600 has no blue focus outline, whereas the candidate asserts the Keyword field is focused. The legal history includes a click inside that field and execution_returned=true but explicitly no visually confirmed result. The candidate does not assert a blue outline. Missing outline alone does not establish actual physical nonfocus, and the prior click can support an action-state inference without visually confirming it. Retain an unresolved focus-provenance subclaim, not a definite false-focus claim, not a proved semantic negative, and not an executed wrong-target label.',
        3: 'Original bd149 visibly contains bike in the Keyword field; clicking Search is an intended action.',
        4: 'Original 35110 shows a coherent bike search-results page; setting a minimum price is an intention.',
        5: 'Original 88d1 has the Min input focus outline; typing900 is an intended next action.',
        6: 'Original eed7 visibly has900 in Min; clicking Max is an intended next action.',
        7: 'Original 9acf has the Max focus outline; typing950 is an intended next action.',
        8: 'Original 189e visibly contains Min900/Max950; clicking Apply is an intended next action, not proof of an applied filter yet.',
        9: 'Original ef426 shows22 listings and the requested900--950 range in the fields. Sorting low to high and checking colors are plans, not completed exhaustive inspection.',
        10: 'Original 96fb shows the open sort menu with Lower price first; selecting it is a plan.',
        11: 'Original 8a53 displays Lower price first, initial900-priced entries and a red F700 frame. The candidate distinguishes frame from handlebars and proposes opening the first Six13 listing to inspect; it does not categorically exclude the first bike.',
        12: 'New original027a clearly shows the Six13 title,900-dollar price, Fairfax Station/Virginia location and large image with red drop-bar tape. Prior original8a53 shows the filtered900--950 range, lower-price sorting and the first900 listing. A qualifying900-dollar match at the requested lower bound is a cheapest match in that range; ties do not invalidate that bounded conclusion and no uniqueness is asserted. Unlike the prior950 conclusion, this does not require claiming all900 alternatives absent. The candidate and native STOP answer are supported at that task-bounded scope. Its correctness does not resolve the earlier focus-provenance subclaim or erase an earlier occurrence if one is later established.'
    }
    rows = []
    images = set()
    previous_messages = None
    previous_text = None
    template = json.loads((HERE / 'package/actor-template.json').read_bytes())
    for number, entry in enumerate(index, 1):
        packet = json.loads((root / entry['file']).read_bytes())
        assert sha(root / entry['file']) == entry['sha256']
        messages = packet['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0]
        if previous_messages is not None:
            assert messages[:len(previous_messages)] == previous_messages
            assert messages[len(previous_messages)] == {'role': 'assistant', 'content': previous_text}
        image_list = [b['original_PNG_sha256'] for m in messages if isinstance(m['content'], list)
                      for b in m['content'] if b.get('type') == 'image_url']
        images.update(image_list)
        rows.append({'candidate': number, 'packet_id': entry['packet_id'],
                     'packet_sha256': entry['sha256'],
                     'source_full_legal_body_sha256': packet['source_body_sha256'],
                     'source_response_sha256': packet['source_response_sha256'],
                     'current_image_sha256': image_list[-1],
                     'candidate_semantic_Mirage': None if number == 2 else False,
                     'pure_native_WAIT': False,
                     'current_visible_interface_interpretable': True,
                     'complete_legal_history_reviewed': True,
                     'new_source_judgment_not_clean_history_label_reuse': True,
                     'execution_or_official_outcome_joined': False,
                     'reason': notes[number]})
        previous_messages, previous_text = messages, packet['candidate_exact_text']
    new_image = '027a8983a81d1f659660d87441e62d0190a652eaec238249f823921eb644dbe6'
    assert len(images) == 11 and new_image in images
    reused = sorted(images - {new_image})
    for digest in reused:
        assert sha(root / 'images' / (digest + '.png')) == digest
        assert sha(prior_images / 'images' / (digest + '.png')) == digest
    dest = HERE / ('T017-stale-baseline12-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(__import__('pathlib').Path(__file__).read_bytes())
    save(dest / 'review.json', {
        'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
        'candidate_coverage': 12, 'unreviewed_candidates': 0,
        'definite_positive_candidates': [], 'unresolved_candidates': [2],
        'literal_negative_candidates': 11, 'pure_native_WAIT_exclusions': 0,
        'trajectory_semantic_Mirage': None,
        'no_definite_positive_is_not_a_proved_negative_trajectory': True,
        'new_unique_original_image_viewed': new_image,
        'prior_original_image_views_reused_by_exact_PNG_SHA': reused,
        'prior_image_review': str(prior_review),
        'complete_latest_legal_input_messages_read': len(previous_messages),
        'original_system_unchanged': True,
        'old_clean_labels_not_reused_when_legal_history_differs': True,
        'source_judgments_before_this_run_official_or_execution_join': True,
        'reviewer_count': 1, 'fully_blind': False,
        'model_or_Flash_decisions_not_used_as_truth': True,
        'new_model_GUI_calls': 0, 'Mirage_reduction': None,
        'rows': rows, 'created': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': 12, 'definite_positives': 0,
                      'unresolved': [2], 'trajectory_label': None, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
