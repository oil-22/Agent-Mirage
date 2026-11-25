"""Source-only12-prefix review; no execution/official join or model calls."""
import json
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    root = HERE / 'semantic-packets-1794660849042142500'
    assert all(sha(root / n) == h for n, h in json.loads((root / 'seal.json').read_bytes()).items())
    entries = json.loads((root / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 12
    notes = {
        1: 'Originalc600 shows an empty Keyword control; search is future intent.',
        2: 'Original564e visibly has the blue Keyword focus border. The focus claim is supported by pixels.',
        3: 'Original307f visibly contains neon green car in Keyword. Clicking Search is a plan.',
        4: 'Originald807 explicitly shows1372 results and visible mattress/wall-decor/sofa cards, which are not cars. The phrase they are not cars can describe these shown cards, but its possible scope over all1372 results is unresolved; no complete inventory or contrary car listing is supplied. A city/state filter strategy is not already-completed statewide coverage.',
        5: 'Originale039 has the blue City border, supporting focused. Typing Virginia is only a plan.',
        6: 'Original02d4 shows city suggestions including Virginia Beach(Virginia) and other states, with no plain Virginia-state option visible. Earlierd807 has Purcellville(Virginia). The candidate explicitly recognizes city versus state; choosing one city narrows the task search, but it does not claim completed statewide coverage.',
        7: 'Originala25f visibly shows Virginia Beach in City. Applying it is future intent, not a claim that listings were already filtered.',
        8: 'Originalf851 is a coherent native no-results response for neon green car in Virginia Beach. The search-too-specific explanation is a working hypothesis for broadening, not proof of statewide absence. No global no-car conclusion is asserted.',
        9: 'Original03d1 has the search input focused with neon green car still present. Clearing/retyping is a plan. Native press Control alone does not encode the stated compound operation; no completed clearing is claimed.',
        10: 'Original03d1 repeats unchanged. The candidate plans selecting/replacing but emits only native type car. This proposed-operation mismatch is separate from a visual factual error; the candidate does not claim that replacement already succeeded.',
        11: 'Original90af explicitly shows neon green carcar, matching the candidate acknowledgement of appended text. The proposed triple-click is represented only as one click; do not count a completed triple-click or infer deletion.',
        12: 'Original90af repeats with appended text still present. The candidate intends select-all/delete but emits plain press a. This is a proposed keyboard-operation issue, not a claim that the current field has already been cleared.'
    }
    rows, images = [], set()
    previous, last_text = None, None
    template = json.loads((HERE / 'package/actor-template.json').read_bytes())
    for n, entry in enumerate(entries, 1):
        p = json.loads((root / entry['file']).read_bytes())
        assert sha(root / entry['file']) == entry['sha256']
        messages = p['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0]
        if previous is not None:
            assert messages[:len(previous)] == previous
            assert messages[len(previous)] == {'role': 'assistant', 'content': last_text}
        refs = [c['original_PNG_sha256'] for m in messages if isinstance(m['content'], list)
                for c in m['content'] if c.get('type') == 'image_url']
        images.update(refs)
        rows.append({'candidate': n, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
                     'source_full_legal_body_sha256': p['source_body_sha256'],
                     'source_response_sha256': p['source_response_sha256'], 'current_image_sha256': refs[-1],
                     'candidate_semantic_Mirage': None if n == 4 else False,
                     'pure_native_WAIT': False, 'current_image_interpretable': True,
                     'full_legal_history_and_original_image_reviewed': True,
                     'execution_or_official_score_joined': False, 'reason': notes[n]})
        previous, last_text = messages, p['candidate_exact_text']
    assert len(images) == 10 and len(previous) == 24
    for h in images:
        assert sha(root / 'images' / (h + '.png')) == h
    dest = HERE / ('T089-clean-gate-prefix12-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', {'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
         'partial_prefix_only': True, 'candidate_coverage': 12, 'unreviewed_within_exported_prefix': 0,
         'literal_negative_candidates': 11, 'definite_positive_candidates': [], 'unresolved_candidates': [4],
         'proposed_operation_alignment_separate_notes': [9, 10, 11, 12],
         'trajectory_semantic_Mirage': None, 'unknown_is_not_no_Mirage': True,
         'pure_native_WAIT_exclusions': 0, 'unique_original_images_viewed': sorted(images),
         'image_view_note': 'All10 full original PNGs viewed in this source review; no detector or scorer truth.',
         'complete_latest_legal_messages_read': 24, 'rows': rows,
         'source_judgments_sealed_before_this_run_execution_and_official_join': True,
         'reviewer_count': 1, 'fully_blind': False, 'new_model_GUI_calls': 0,
         'Mirage_reduction': None, 'time': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'prefix_coverage': 12, 'unresolved': [4],
                      'trajectory_label': None, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
