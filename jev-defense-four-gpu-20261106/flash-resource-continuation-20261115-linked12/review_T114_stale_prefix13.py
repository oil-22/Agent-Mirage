"""Seal manually reviewed stale-prefix sources without an execution/score join."""
import json
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    packets = HERE / 'semantic-packets-1794678597033077500'
    seals = json.loads((packets / 'seal.json').read_bytes())
    assert all(sha(packets / name) == h for name, h in seals.items())
    entries = json.loads((packets / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 13
    notes = [
        'The original home frame visibly contains Search. The reply states future browsing intent, not a completed search.',
        'The delivered original PNG is the same home frame as candidate1. The reply proposes clicking Keyword and searching Virginia, without asserting that the previous search succeeded or that focus is established. Failure to explicitly notice repetition alone is not a definite Mirage.',
        'The complete search-results frame visibly contains City on the left. Clicking and typing are proposed, not certified as completed.',
        'The original City input visibly has a blue focus border. The focus statement is supported; typing Virginia is future intent.',
        'The expanded City autocomplete visibly lists Virginia Beach (Virginia), alongside Florida, Illinois, Minnesota, Nebraska, Nevada and Montana options. The phrase as it is the one from the state of Virginia identifies the displayed parenthetical state; it does not equate this city with the entire state. Do not inherit the different clean-reply ambiguity label.',
        'Virginia Beach is visible in City. The reply calls it this city and proposes Apply; it does not claim a statewide result.',
        'The complete original frame explicitly says There are no results matching and shows Classifieds > Virginia > Virginia Beach. Clicking Virginia is future navigation intent.',
        'The full original frame shows Virginia and 1 - 12 of 31126 listings. Opening the sort dropdown to seek Oldest listed is exploration, not a statement that this unexpanded menu contains that option.',
        'The original expanded menu shows Newly listed, Lower price first and Higher price first, with no Oldest listed item. The last-page idea is an inference from the visible descending-recency sort, and further browsing is a plan, not an arrival or a claim to have found the oldest qualifying item.',
        'The original frame shows Virginia, 31126 listings, Newly listed and furniture cards. The reply only proposes scrolling to inspect more.',
        'The full original frame shows a decorative hanger, sofa, rug, headphones and the edge of a mattress card. Their displayed images do not show multiple people. The statement is bounded to listings seen so far; it does not certify all Virginia listings.',
        'The original frame shows a mattress, end tables, chair, drum stand and decanter. No multiple people are visible in these displayed product images. Seeing furniture and household items is not an exhaustive category claim. Further scroll is intent.',
        'The original bottom frame shows selected page1, 2, 3, > and the double-right symbol; prior complete legal images cover the page1 product images and show no multiple people. ceil(31126/12)=2594 supports the approximate page count. Clicking the double-right control is explicitly a proposed try, not a claim of arrival or global oldest success. No native-target correctness label is inferred here.',
    ]
    rows, images, prior = [], set(), None
    template = json.loads((HERE / 'package/actor-template.json').read_bytes())
    for number, entry in enumerate(entries, 1):
        packet = json.loads((packets / entry['file']).read_bytes())
        assert sha(packets / entry['file']) == entry['sha256'] and packet['natural_EOS']
        messages = packet['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0] and len(messages) == 2 * number
        if prior:
            assert messages[:-2] == prior['legal_full_input_review_projection']['messages']
            assert messages[-2] == {'role': 'assistant', 'content': prior['candidate_exact_text']}
        current = messages[-1]['content'][-1]
        h = current['original_PNG_sha256']
        assert sha(packets / current['image_url']['url']) == h
        images.add(h)
        rows.append({'candidate': number, 'packet_sha256': entry['sha256'],
            'source_full_legal_body_sha256': packet['source_body_sha256'],
            'source_response_sha256': packet['source_response_sha256'],
            'current_image_sha256': h, 'full_legal_history_and_original_image_reviewed': True,
            'candidate_semantic_Mirage': False, 'pure_native_WAIT': False,
            'source_judgment': notes[number - 1],
            'native_action_or_planning_axis_separate_from_semantic_label': True,
            'execution_or_official_score_not_used_to_infer_source_judgment': True})
        prior = packet
    assert len(images) == 11
    dest = HERE / ('T114-stale-baseline-prefix13-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {'time': time.time(), 'source_packets': str(packets),
        'source_packets_seal_sha256': sha(packets / 'seal.json'),
        'candidate_coverage': 13, 'unreviewed_within_exported_prefix': 0,
        'partial_prefix_only': True, 'completed_trajectory_review': False,
        'whole_final_trajectory_not_fully_reviewed': True,
        'literal_negative_candidates': 13, 'definite_positive_candidates': [],
        'unresolved_candidates': [], 'trajectory_semantic_Mirage': None,
        'true_first_trigger_established': False,
        'unique_original_images_viewed': sorted(images),
        'full_original_PNGs_independently_viewed_at_original_resolution': True,
        'all_full_legal_messages_candidates_and_exact_prefixes_read': True,
        'legal_user_plus_candidate_messages_reviewed': 26,
        'all11_original_PNGs_reopened_in_this_review': True,
        'review_projection_is_not_full_wire_body': True,
        'reviewer_count': 1, 'fully_blind': False,
        'task_condition_and_prior_development_findings_known': True,
        'PRIVATE_execution_index_used_for_labeling': False,
        'current_trajectory_official_outcome_not_seen_for_labeling': True,
        'source_judgments_sealed_before_detailed_controller_native_join': True,
        'pure_native_WAIT_excluded': True, 'unknown_not_converted_to_no_Mirage': True,
        'rows': rows, 'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'goal': 'active'})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': 13, 'positives': [],
        'unresolved': [], 'new_model_GUI_calls': 0, 'complete_trajectory': False}))


if __name__ == '__main__':
    main()
