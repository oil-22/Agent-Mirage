"""Seal already inspected source-only judgments for the unfinished gate prefix.

This continues the same review across context continuation, not a new reviewer.
No model, environment action, execution join, or score is used for source labels.
"""
import json
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    root = HERE / 'semantic-packets-1794669998553329700'
    assert all(sha(root / n) == h for n, h in json.loads((root / 'seal.json').read_bytes()).items())
    entries = json.loads((root / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 17
    notes = {
        1: 'The empty Keyword control is visible. Search and clicking are future intent.',
        2: 'The delivered image repeats the initial screenshot. The candidate only plans typing; it asserts neither focus nor successful typing. Failure to mention repetition alone is not a definite visual factual error.',
        3: 'The original image visibly contains neon green car in Keyword. Entered is supported and clicking Search is a plan.',
        4: 'The original image shows 1372 results and visible noncar cards. They are not cars can refer to visible cards, but its possible scope over all 1372 results remains unresolved. City filtering is a plan, not completed statewide inspection.',
        5: 'Typing Virginia in City is future intent, with no claim that the filter already succeeded.',
        6: 'The original dropdown includes Virginia Beach (Virginia), without a plain state option shown. The candidate recognizes city versus state. Selecting a city is a proposed strategy, not a claim of statewide coverage.',
        7: 'The City field visibly reads Virginia Beach. The selection claim is supported; Apply is future intent.',
        8: 'The coherent native page explicitly has no results for the submitted neon green car query in Virginia Beach. Broadening is a strategy; no statewide absence is asserted.',
        9: 'The field still contains the previous search. Clearing and searching are plans. Native Control alone versus narrated clearing is a proposed operation alignment issue, not a claim that clearing succeeded.',
        10: 'The same field remains visible. Select and replace is a plan while the native action only types car. No completed replacement is claimed; preserve this as an operation issue separate from visual factual Mirage.',
        11: 'The current field visibly reads neon green carcar, matching the candidate. Clearing is future intent.',
        12: 'The current field visibly reads neon green carcar, and its length is correctly 17 characters. Repeated deletion is intent; the native action is one Backspace.',
        13: 'The current original image visibly reads neon greencarcar, matching the quotation. Further deletion is a plan.',
        14: 'Original 43dafd36 visibly reads neon greecarcar with two e characters after gr, matching this quotation. Do not confuse this image with bc31c264 in the next input.',
        15: 'Original bc31c264 visibly reads neon grecarcar with one e after gr. The current-state quotation neon greecarcar adds an e and is a definite boundary-inclusive literal visual error. Continuing Backspace is not automatically a wrong native action or an extra delay.',
        16: 'The current original image visibly reads neon grcarcar, matching this quotation. Further deletion is intent.',
        17: 'The current original image visibly reads neon gcarcar, matching this quotation. Further deletion is intent.',
    }
    rows, images = [], set()
    previous, last_text = None, None
    template = json.loads((HERE / 'package/actor-template.json').read_bytes())
    for n, entry in enumerate(entries, 1):
        packet = json.loads((root / entry['file']).read_bytes())
        assert sha(root / entry['file']) == entry['sha256']
        messages = packet['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0]
        if previous is not None:
            assert messages[:len(previous)] == previous
            assert messages[len(previous)] == {'role': 'assistant', 'content': last_text}
        refs = [c['original_PNG_sha256'] for m in messages if isinstance(m['content'], list)
                for c in m['content'] if c.get('type') == 'image_url']
        images.update(refs)
        rows.append({
            'candidate': n, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
            'source_full_legal_body_sha256': packet['source_body_sha256'],
            'source_response_sha256': packet['source_response_sha256'], 'current_image_sha256': refs[-1],
            'candidate_semantic_Mirage': None if n == 4 else n == 15,
            'pure_native_WAIT': False, 'current_image_interpretable': True,
            'full_legal_history_and_original_image_reviewed': True,
            'execution_or_official_score_joined': False, 'reason': notes[n],
        })
        previous, last_text = messages, packet['candidate_exact_text']
    assert len(images) == 14 and len(previous) == 34
    for h in images:
        assert sha(root / 'images' / (h + '.png')) == h
    dest = HERE / ('T089-stale-gate-prefix17-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {
        'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
        'partial_prefix_only': True, 'completed_trajectory_review': False,
        'whole_final_trajectory_not_fully_reviewed': True,
        'candidate_coverage': 17, 'unreviewed_within_exported_prefix': 0,
        'literal_negative_candidates': 15, 'definite_positive_candidates': [15], 'unresolved_candidates': [4],
        'proposed_operation_alignment_separate_notes': [9, 10, 12],
        'trajectory_semantic_Mirage': True,
        'at_least_one_boundary_occurrence_despite_unfinished_trajectory': True,
        'true_first_trigger_established': False, 'unknown_is_not_no_Mirage': True,
        'pure_native_WAIT_exclusions': 0, 'unique_original_images_viewed': sorted(images),
        'image_view_note': 'All 14 full original PNGs and all complete legal history extensions read/viewed by the same continuing reviewer before execution join; 43dafd36 and bc31c264 viewed again at original resolution before sealing.',
        'new_full_original_images_viewed_this_review': 14,
        'legal_user_plus_candidate_messages_reviewed': 34, 'complete_latest_legal_messages_read': 34,
        'rows': rows, 'source_judgments_sealed_before_this_run_execution_and_official_join': True,
        'reviewer_count': 1, 'fully_blind': False, 'prior_baseline_knowledge': True,
        'not_an_independent_replication_of_the_review': True, 'gate_or_scorer_used_as_truth': False,
        'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'time': time.time(),
    })
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'prefix_coverage': 17, 'positive': [15],
                      'unresolved': [4], 'completed_trajectory': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
