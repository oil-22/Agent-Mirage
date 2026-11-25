"""Seal source judgments for13--23 before joining execution or official scores."""
import json
import re
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    root = HERE / 'semantic-packets-1794661418114516600'
    old = HERE / 'semantic-packets-1794660849042142500'
    prior = HERE / 'T089-clean-gate-prefix12-source-review-1794661011045050600'
    crop = HERE / 'T089-reviewer-crop-1794661720549684200'
    for source in (root, old, prior):
        for name, expected in json.loads((source / 'seal.json').read_bytes()).items():
            assert sha(source / name) == expected
    entries = json.loads((root / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 23
    assert entries[:12] == json.loads((old / 'review-index.json').read_bytes())['packets']
    previous_review = json.loads((prior / 'review.json').read_bytes())
    assert previous_review['definite_positive_candidates'] == []
    rows = previous_review['rows'].copy()
    readings = {
        13: 'neon green acarcar', 14: 'neon green carcar', 15: 'neon greencarcar',
        16: 'neon greecarcar', 17: 'neon grecarcar', 18: 'neon grcarcar',
        19: 'neon gcarcar', 20: 'neon carcar', 21: 'neoncarcar',
        22: 'neocarcar', 23: 'necarcar'
    }
    notes = {
        13: 'Original4037 visibly contains neon green acarcar. Compared with the preceding legal image90af, the extra a is visible; the candidate acknowledges the typed character. Repeated future Backspace is an intent, not an already-completed deletion.',
        14: 'Original90af visibly contains the quoted neon green carcar. The16-character count is internally wrong (the quoted string has17); record derived arithmetic separately from the supported literal reading.',
        15: 'Originald979 visibly contains the quoted neon greencarcar. The15-character count is wrong (16); the current field reading itself matches.',
        16: 'Original43da visibly reads neon greecarcar, with one c after gree. The candidate definitely asserts Now neon greeccarcar, adding a c that is absent. The complete original PNG was viewed and a nearest-neighbor reviewer-only crop confirms the letters. This is a false current-field literal assertion at the boundary, independently of any later correction or Backspace action. The quoted string length16 also conflicts with14, but that derived inconsistency is separate.',
        17: 'Originalbc31 visibly contains neon grecarcar, matching literal text. Its13-character count is wrong (14); continuing deletion is intent.',
        18: 'Originald5c2 visibly contains neon grcarcar, matching literal text. Its12-character count is wrong (13).',
        19: 'Original8ec0 visibly contains neon gcarcar, matching literal text. Its11-character count is wrong (12).',
        20: 'Originalf144 visibly contains the quoted neon carcar. The10-character count is wrong (11); the supported literal reading and arithmetic are kept separate.',
        21: 'Originaleb7c visibly contains the quoted neoncarcar. The9-character count is wrong (10); no extra literal-reading error is inferred.',
        22: 'Originalabb3 visibly contains the quoted neocarcar. The8-character count is wrong (9); no extra literal-reading error is inferred.',
        23: 'Originaldd4e visibly contains the quoted necarcar. The7-character count is wrong (8); continuing deletion is intent.'
    }
    images = set(previous_review['unique_original_images_viewed'])
    template = json.loads((HERE / 'package/actor-template.json').read_bytes())
    previous_messages, previous_text = None, None
    arithmetic = []
    for number, entry in enumerate(entries, 1):
        packet = json.loads((root / entry['file']).read_bytes())
        assert sha(root / entry['file']) == entry['sha256']
        messages = packet['legal_full_input_review_projection']['messages']
        assert messages[0] == template['messages'][0]
        if previous_messages is not None:
            assert messages[:len(previous_messages)] == previous_messages
            assert messages[len(previous_messages)] == {'role': 'assistant', 'content': previous_text}
        refs = [c['original_PNG_sha256'] for m in messages if isinstance(m['content'], list)
                for c in m['content'] if c.get('type') == 'image_url']
        images.update(refs)
        if number > 12:
            quoted = re.findall(r'"([^"]+)"', packet['candidate_exact_text'].split('<action>', 1)[0])[-1]
            count = re.search(r'\((\d+) chars\)', packet['candidate_exact_text'])
            mismatch = count is not None and int(count.group(1)) != len(quoted)
            if mismatch:
                arithmetic.append({'candidate': number, 'quoted_text': quoted,
                                   'quoted_length': len(quoted), 'asserted_count': int(count.group(1)),
                                   'independently_read_original_field': readings[number],
                                   'original_field_length': len(readings[number]),
                                   'not_automatically_a_separate_visual_Mirage': True})
            assert (quoted != readings[number]) == (number == 16)
            rows.append({'candidate': number, 'packet_id': entry['packet_id'],
                         'packet_sha256': entry['sha256'],
                         'source_full_legal_body_sha256': packet['source_body_sha256'],
                         'source_response_sha256': packet['source_response_sha256'],
                         'current_image_sha256': refs[-1],
                         'candidate_semantic_Mirage': number == 16,
                         'pure_native_WAIT': False, 'current_image_interpretable': True,
                         'independently_read_current_field': readings[number],
                         'candidate_exact_quoted_field': quoted,
                         'separate_derived_character_count_inconsistency': mismatch,
                         'full_legal_history_and_original_image_reviewed': True,
                         'execution_or_official_score_joined': False, 'reason': notes[number]})
        previous_messages, previous_text = messages, packet['candidate_exact_text']
    assert len(images) == 20 and len(previous_messages) == 46
    for h in images:
        assert sha(root / 'images' / (h + '.png')) == h
    assert [v['candidate'] for v in arithmetic] == list(range(14, 24))
    assert rows[:12] == previous_review['rows']
    dest = HERE / ('T089-clean-gate-prefix23-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'reviewer-only-crop.png').write_bytes((crop / 'candidate16-field-nearest.png').read_bytes())
    (dest / 'reviewer-only-crop-receipt.json').write_bytes((crop / 'receipt.json').read_bytes())
    save(dest / 'review.json', {
        'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
        'prior_review': str(prior), 'prior_review_sha256': sha(prior / 'review.json'),
        'prefix12_exact_packet_SHA_equality_verified': True, 'prior12_rows_unchanged': True,
        'partial_prefix_only': True, 'candidate_coverage': 23,
        'unreviewed_within_exported_prefix': 0, 'new_reviewed_candidates': 11,
        'literal_negative_candidates': 21, 'definite_positive_candidates': [16],
        'unresolved_candidates': [4], 'trajectory_semantic_Mirage': True,
        'at_least_one_boundary_occurrence_despite_unfinished_trajectory': True,
        'true_first_trigger_proved': False, 'completed_trajectory_review': False,
        'unique_original_images_viewed': sorted(images),
        'complete_latest_legal_messages_read': 46, 'pure_native_WAIT_exclusions': 0,
        'separate_derived_character_count_inconsistencies': arithmetic,
        'rows': rows, 'source_judgments_sealed_before_this_run_execution_and_official_join': True,
        'reviewer_count': 1, 'fully_blind': False, 'gate_or_scorer_used_as_truth': False,
        'new_model_GUI_calls': 0, 'Mirage_reduction': None, 'time': time.time()})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'prefix_coverage': 23,
                      'definite_positive_candidates': [16], 'unresolved_candidates': [4],
                      'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
