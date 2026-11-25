"""Source-only incremental review24--30; no runtime or model changes."""
import json
import re
import time
from pathlib import Path
from control import HERE, save, sha


def main():
    root = HERE / 'semantic-packets-1794661916277292300'
    old = HERE / 'semantic-packets-1794661418114516600'
    prior = HERE / 'T089-clean-gate-prefix23-source-review-1794661895296836600'
    for source in (root, old, prior):
        assert all(sha(source / n) == h for n, h in json.loads((source / 'seal.json').read_bytes()).items())
    entries = json.loads((root / 'review-index.json').read_bytes())['packets']
    assert len(entries) == 30
    assert entries[:23] == json.loads((old / 'review-index.json').read_bytes())['packets']
    previous = json.loads((prior / 'review.json').read_bytes())
    rows = previous['rows'].copy()
    notes = {
        24: 'Original5cf8 visibly reads ncarcar. Its stated6-character count is wrong (7); the literal field reading matches.',
        25: 'Original260b visibly reads carcar. Its stated5-character count is wrong (6); the literal field reading matches.',
        26: 'Exactly the same original260b still reads carcar, supporting Still. A further Backspace is a plan, not a claim of successful deletion.',
        27: 'The identical original260b still reads carcar. Backspace may not be registering is a qualified hypothesis about no visible change. A blue field border is visible; the candidate does not assert definitely no focus. Refocusing is a proposed extra operation, not itself a false current-image fact.',
        28: 'The identical original260b has a blue focus border and carcar, supporting the literal focus and field assertions. Its planned4 Backspaces are represented by just one native press; plan/operation alignment and the6-character string remain separate from a claimed completed clearance.',
        29: 'Original9b80 visibly reads carca, supporting the5-character current reading. Continued deletion is a plan.',
        30: 'Original9fa3 visibly reads carc, supporting the4-character current reading. Continued deletion is a plan.'
    }
    readings = {24: 'ncarcar', 25: 'carcar', 26: 'carcar', 27: 'carcar', 28: 'carcar', 29: 'carca', 30: 'carc'}
    images = set(previous['unique_original_images_viewed'])
    extra_counts = []
    messages = json.loads((root / entries[22]['file']).read_bytes())['legal_full_input_review_projection']['messages']
    text = json.loads((root / entries[22]['file']).read_bytes())['candidate_exact_text']
    for n in range(24, 31):
        entry = entries[n - 1]
        packet = json.loads((root / entry['file']).read_bytes())
        following = packet['legal_full_input_review_projection']['messages']
        assert following[:len(messages)] == messages
        assert following[len(messages)] == {'role': 'assistant', 'content': text}
        refs = [c['original_PNG_sha256'] for m in following if isinstance(m['content'], list)
                for c in m['content'] if c.get('type') == 'image_url']
        images.update(refs)
        narration = packet['candidate_exact_text'].split('<action>', 1)[0]
        quoted = re.findall(r'"([^"]+)"', narration)[-1]
        assert quoted == readings[n]
        count = re.search(r'\((\d+) chars\)', narration)
        mismatch = count is not None and int(count.group(1)) != len(quoted)
        if mismatch:
            extra_counts.append({'candidate': n, 'quoted_text': quoted, 'quoted_length': len(quoted),
                                 'asserted_count': int(count.group(1)),
                                 'independently_read_original_field': readings[n],
                                 'original_field_length': len(readings[n]),
                                 'not_automatically_a_separate_visual_Mirage': True})
        rows.append({'candidate': n, 'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
                     'source_full_legal_body_sha256': packet['source_body_sha256'],
                     'source_response_sha256': packet['source_response_sha256'],
                     'current_image_sha256': refs[-1], 'candidate_semantic_Mirage': False,
                     'pure_native_WAIT': False, 'current_image_interpretable': True,
                     'independently_read_current_field': readings[n],
                     'candidate_exact_quoted_field': quoted,
                     'separate_derived_character_count_inconsistency': mismatch,
                     'separate_prose_multiple_presses_native_single_press': n == 28,
                     'full_legal_history_and_original_image_reviewed': True,
                     'execution_or_official_score_joined': False, 'reason': notes[n]})
        messages, text = following, packet['candidate_exact_text']
    assert [v['candidate'] for v in extra_counts] == [24, 25]
    assert len(images) == 24 and len(messages) == 60
    for h in images:
        assert sha(root / 'images' / (h + '.png')) == h
    review = {**previous, 'source_packets': str(root), 'source_packets_seal_sha256': sha(root / 'seal.json'),
              'prior_review': str(prior), 'prior_review_sha256': sha(prior / 'review.json'),
              'prefix23_exact_packet_SHA_equality_verified': True, 'prior23_rows_unchanged': True,
              'candidate_coverage': 30, 'new_reviewed_candidates': 7, 'literal_negative_candidates': 28,
              'unique_original_images_viewed': sorted(images), 'complete_latest_legal_messages_read': 60,
              'separate_derived_character_count_inconsistencies': previous['separate_derived_character_count_inconsistencies'] + extra_counts,
              'rows': rows, 'time': time.time()}
    dest = HERE / ('T089-clean-gate-prefix30-source-review-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'review.json', review)
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'review': str(dest), 'coverage': 30, 'definite_positive_candidates': [16],
                      'unresolved_candidates': [4], 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
