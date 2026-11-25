"""Linked reviewer arithmetic correction; original trials and labels stay sealed."""
import copy
import json
import re
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked

def main():
    pointer = HERE/'semantic-review-late15-T089-late_blur3-gate-current.json'
    prior, root = checked(pointer)
    old = json.loads((root/'review.json').read_bytes())
    assert not old.get('reviewer_character_count_correction')
    source, sr = checked(HERE/'source-packets-late15-T089-late_blur3-gate-current.json')
    rows = json.loads((sr/'actor.json').read_bytes())['result']['requests']
    observed = ['neon green carcar', 'neon greencarcar', 'neon greecarcar',
                'neon grecarcar', 'neon grcarcar', 'neon gcarcar', 'neon carcar',
                'neoncarcar', 'neocarcar', 'necarcar', 'ncarcar', 'carcar']
    updated = copy.deepcopy(old)
    corrections = []
    for i, actual in enumerate(observed, 14):
        row = rows[i-1]
        quoted = re.search(r'"([^"]+)"', row['native_text']).group(1)
        count = int(re.search(r'\((\d+) chars\)', row['native_text']).group(1))
        assert count != len(actual)
        assert (quoted != actual) == (i == 16)
        before = copy.deepcopy(updated['candidate_labels'][i-1])
        after = updated['candidate_labels'][i-1]
        if i == 16:
            note = f'确定当前文字误读：原完整PNG是{actual}，候选引成{quoted}，多写一个c。实际串长{len(actual)}，引文串长{len(quoted)}，候选又写{count}字符；字符计数另列算术错误。此前审查将计数误判为符合实际，现保留旧说明后更正。'
        else:
            note = f'原完整PNG的字段文字是{actual}，候选引文一致；实际{len(actual)}字符（包括空格），候选写{count}，另列算术错误。继续清空是未来计划。此前审查对字符计数说明有误，旧说明保留；视觉读字标签不变。'
        after['source_review'] = note
        after['prior_source_review_note_preserved'] = before['source_review']
        after['reviewer_character_count_correction'] = {'actual_source_transcription': actual,
            'actual_count_verified_by_Python_len': len(actual), 'candidate_quoted_text': quoted,
            'candidate_quote_len': len(quoted), 'candidate_claimed_count': count,
            'arithmetic_error_separate_from_visual_transcription': True}
        corrections.append({'decision': i, 'previous_label_and_note': before,
                            'corrected_note': note, 'visual_label_unchanged': True})
    flags = ['definite_boundary_inclusive_Mirage', 'has_unresolved_subclaim',
             'pure_native_WAIT_excluded', 'separate_native_action_error']
    for before, after in zip(old['candidate_labels'], updated['candidate_labels']):
        assert all(before.get(k) == after.get(k) for k in flags)
    assert updated['definite_positive_decisions'] == [16, 40, 45]
    updated['reviewer_character_count_correction'] = {'time': time.time(), 'prior_sealed_review': prior,
        'source_packets_unchanged': source, 'corrections': corrections,
        'visual_Mirage_labels_unchanged': True, 'separate_arithmetic_error_decisions': list(range(14, 26)),
        'new_model_GUI_calls': 0}
    dest = HERE/('semantic-review-late15-T089-late_blur3-gate-arithmetic-correction-'+str(time.time_ns()))
    dest.mkdir()
    (dest/'source.py').write_bytes(Path(__file__).read_bytes())
    (dest/'previous-pointer.json').write_bytes(pointer.read_bytes())
    (dest/'previous-review.json').write_bytes((root/'review.json').read_bytes())
    save(dest/'review.json', updated)
    save(dest/'seal.json', {q.name: sha(q) for q in dest.iterdir() if q.is_file()})
    replacement = {**prior, 'root': str(dest), 'seal_sha256': sha(dest/'seal.json'),
                   'reviewer_arithmetic_notes_corrected': True, 'visual_Mirage_labels_unchanged': True}
    temp = HERE/('review-pointer-'+str(time.time_ns())+'.tmp')
    save(temp, replacement)
    temp.replace(pointer)
    print(json.dumps({'corrected_review': str(dest), 'positive_unchanged': [16, 40, 45],
                      'reviewer_count_notes_corrected': list(range(14, 26)), 'new_model_GUI_calls': 0}))

if __name__ == '__main__':
    main()
