"""Seal twelve manually reviewed complete legal inputs and original PNGs."""
import json
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    packets = HERE / 'semantic-packets-1794676756035642400'
    assert all(sha(packets / n) == h for n, h in json.loads((packets / 'seal.json').read_bytes()).items())
    entries = json.loads((packets / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 12
    notes = [
        'Search button is visible on the complete home frame. Future browsing intent; no completed search or Virginia result is asserted.',
        'The full current frame explicitly shows 1 - 12 of 84149 listings and the City input. Searching Virginia is an intended next step, not a claim that the state filter is already applied.',
        'The current City field has the visible blue focus border. Its focus statement is grounded in the image; typing is future intent.',
        'Virginia Beach (Virginia) is a visible autocomplete option. The phrase which is the state of Virginia is ambiguous between identifying the parenthetical state and equating the selected city with statewide coverage. The proposed city selection does not by itself establish a false visual fact. Scope stays unresolved; do not count this as a definite error or a negative.',
        'Virginia Beach is visible in the City field, with the Apply button below. The reply correctly calls this a city and only proposes applying the filter.',
        'The current coherent page explicitly says There are no results matching and shows Classifieds > Virginia > Virginia Beach. Clicking the visible Virginia breadcrumb is future intent; no unseen state result is asserted.',
        'Virginia heading and 1 - 12 of 31126 listings are visible. The requested Oldest listed sort is exploratory intent, not a claim that the unexpanded dropdown contains that option.',
        'The expanded dropdown visibly contains exactly Newly listed, Lower price first and Higher price first. The visible count 31126 with 12 per page implies ceil(31126/12)=2594, agreeing with about 2594. Latest visible date is 2023/11/16. Going to the last page is a future search strategy; no page arrival or target image is asserted.',
        'The exact same original frame as candidate8 still visibly contains the expanded dropdown. The reply explicitly recognizes that Escape has not closed it and proposes another action.',
        'The original frame now shows the closed dropdown. Future downward exploration is stated; it does not claim the pagination or oldest target has already been seen.',
        'The complete frame shows further listings and no visible pagination controls. Continuing to scroll down is future intent, with no claim of completed target inspection.',
        'The full original frame shows listings including End tables, J Robert Scott chair and a drum stand, with further content below. The proposed scroll is an intent and no oldest item or people count is asserted.',
    ]
    rows, images, prior = [], set(), None
    for number, entry in enumerate(entries, 1):
        p = json.loads((packets / entry['file']).read_bytes())
        assert sha(packets / entry['file']) == entry['sha256'] and p['natural_EOS']
        messages = p['legal_full_input_review_projection']['messages']
        assert len(messages) == 2 * number
        if prior:
            assert messages[:-2] == prior['legal_full_input_review_projection']['messages']
            assert messages[-2] == {'role': 'assistant', 'content': prior['candidate_exact_text']}
        current = messages[-1]['content'][-1]
        h = current['original_PNG_sha256']
        assert sha(packets / current['image_url']['url']) == h
        images.add(h)
        rows.append({'candidate': number, 'packet_sha256': entry['sha256'],
            'source_full_legal_body_sha256': p['source_body_sha256'],
            'source_response_sha256': p['source_response_sha256'],
            'current_image_sha256': h, 'full_legal_history_and_original_image_reviewed': True,
            'candidate_semantic_Mirage': None if number == 4 else False,
            'pure_native_WAIT': False, 'source_judgment': notes[number - 1],
            'native_action_or_planning_axis_separate_from_semantic_label': True,
            'execution_or_official_score_not_used_to_infer_source_judgment': True})
        prior = p
    assert len(images) == 10
    dest = HERE / ('T114-clean-gate-prefix12-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {'time': time.time(), 'source_packets': str(packets),
        'source_packets_seal_sha256': sha(packets / 'seal.json'),
        'candidate_coverage': 12, 'unreviewed_within_exported_prefix': 0,
        'partial_prefix_only': True, 'completed_trajectory_review': False,
        'whole_final_trajectory_not_fully_reviewed': True,
        'literal_negative_candidates': 11, 'definite_positive_candidates': [],
        'unresolved_candidates': [4], 'trajectory_semantic_Mirage': None,
        'true_first_trigger_established': False,
        'unique_original_images_viewed': sorted(images),
        'full_original_PNGs_independently_viewed_at_original_resolution': True,
        'all_full_legal_messages_candidates_and_exact_prefixes_read': True,
        'review_projection_is_not_full_wire_body': True,
        'reviewer_count': 1, 'fully_blind': False,
        'task_condition_and_prior_development_findings_known': True,
        'PRIVATE_execution_index_used_for_labeling': False,
        'current_trajectory_official_outcome_not_seen_for_labeling': True,
        'source_judgments_sealed_before_detailed_controller_native_join': True,
        'pure_native_WAIT_excluded': True, 'unknown_not_converted_to_no_Mirage': True,
        'rows': rows, 'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'goal': 'active'})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': 12, 'positives': [],
        'unresolved': [4], 'new_model_GUI_calls': 0, 'complete_trajectory': False}))


if __name__ == '__main__':
    main()
