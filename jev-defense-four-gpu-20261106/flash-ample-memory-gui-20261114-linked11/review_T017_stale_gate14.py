"""Seal fresh source-only judgments; this file does not read scores or execution."""
import json
import time
from pathlib import Path

from control import HERE, save, sha


def main():
    root = HERE / 'semantic-packets-1794657911428332100'
    for name, expected in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha(root / name) == expected
    index = json.loads((root / 'review-index.json').read_bytes())['packets']
    assert len(index) == 14
    notes = {
        1: 'The original646a visibly has a Keyword input. Clicking and typing are future intentions, not assertions of completed search.',
        2: 'The delivered646a repeats the preceding image and has no blue Keyword outline. The candidate only proposes typing into the field; it does not assert visible focus, an outline, or successful search. The legal previous click alone is not treated as visual proof. No definite erroneous visual or historical assertion occurs in this wording.',
        3: 'Original6744 visibly has bike in the Keyword field with a blue outline; the text-entry assertion is supported. Clicking Search is a plan.',
        4: 'Original35110 has the bike search-results page and Min input. Setting the price range is a future action.',
        5: 'Original88d1 has the Min blue outline. Typing900 is a plan, not an assertion of already-applied filtering.',
        6: 'Originaleed7 visibly has900 in Min. Selecting Max and entering950 are future intentions.',
        7: 'Original9acf has the Max blue outline; typing950 is a future intention.',
        8: 'Original189e visibly has Min900 and Max950. Both price values being set is supported; Apply is still proposed.',
        9: 'Originalef426 visibly shows1--12 of22 listings, the900--950 fields and newly listed order. The filter/count assertion is supported. Sorting and checking handlebar colors are plans, not completed exhaustive inspection.',
        10: 'Original96fb visibly has the open menu with Lower price first. Selecting it is a plan.',
        11: 'Original8a53 visibly shows Lower price first,900-dollar entries and a red F700 frame. The candidate identifies the frame and explicitly plans opening the F700 to verify the different handlebar component. It does not infer red handlebars from the red frame.',
        12: 'Original422d clearly shows the F700 title, red frame and black handlebar/grip assembly in its large photograph. The candidate distinguishes these components and plans returning to the list; no categorical exclusion of the other bikes occurs.',
        13: 'Original8a53 again shows the Six13 as the first listing. Inspecting its handlebar color is an intention; the candidate makes no unsupported negative about it.',
        14: 'Original027a clearly shows Six13,900-dollar price, Fairfax Station/Virginia and red drop-bar tape. Prior original8a53 shows the900--950 range and lower-price sorting. A qualifying900-dollar bike is at the task lower bound and is a cheapest match within that range without exhaustive exclusion or uniqueness. The prose and native STOP answer are supported at this bounded scope. This assessment does not use official scoring or a private target.'
    }
    rows, images = [], set()
    previous_messages = previous_text = None
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
                     'candidate_semantic_Mirage': False, 'pure_native_WAIT': False,
                     'current_visible_interface_interpretable': True,
                     'complete_legal_history_reviewed': True,
                     'new_source_judgment_not_other_arm_label_reuse': True,
                     'execution_or_official_outcome_joined': False, 'reason': notes[number]})
        previous_messages, previous_text = messages, packet['candidate_exact_text']
    assert len(images) == 12 and len(previous_messages) == 28
    for digest in images:
        assert sha(root / 'images' / (digest + '.png')) == digest
    dest = HERE / ('T017-stale-gate14-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {
        'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
        'candidate_coverage': 14, 'unreviewed_candidates': 0,
        'definite_positive_candidates': [], 'unresolved_candidates': [],
        'literal_negative_candidates': 14, 'pure_native_WAIT_exclusions': 0,
        'trajectory_semantic_Mirage': False,
        'scope': 'One complete14-candidate trajectory as read by one reviewer; not a general model or defense guarantee.',
        'all12_original_full_PNGs_viewed_this_review': sorted(images),
        'complete_latest_legal_input_messages_read': 28,
        'source_judgments_before_this_run_official_or_execution_join': True,
        'reviewer_count': 1, 'fully_blind': False,
        'other_arm_labels_not_reused_when_history_differs': True,
        'model_or_Flash_decisions_not_used_as_truth': True,
        'new_model_GUI_calls': 0, 'Mirage_reduction': None,
        'rows': rows, 'created': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': 14, 'definite_positives': 0,
                      'unresolved': [], 'trajectory_label': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
