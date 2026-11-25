"""Seal source-only review; never issue model or browser requests."""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked

NOTES = {
    11: '原图Your search完整显示neon green carcar及蓝色焦点边框，appended有源。triple-click为计划而原生单click，不把计划当已完成；原生表达差异另列。',
    12: 'select-all/delete是未来计划；原生a单键无法实现该快捷键，属于操作策略/表达差异，未声称已完成。原图仍同11。',
    13: '当前原图neon green acarcar可读；历史a单键及前图carcar支持新增a的观察。后续Backspace是计划。',
    14: '原图neon green carcar可读，含空格16字符；继续清空是未来计划。',
    15: '原图neon greencarcar可读，含空格15字符。',
    16: '确定当前文字误读：原图框内是neon greecarcar，候选写neon greeccarcar，多写一个c。原尺寸完整PNG和仅用于审查的放大裁剪一致；候选14字符计数符合实际字符串但不符合其所引字符串，计数矛盾另列，不抹去当前文字误读。',
    17: '原图neon grecarcar可读，含空格13字符。',
    18: '原图neon grcarcar可读，含空格12字符。',
    19: '原图neon gcarcar可读，含空格11字符。',
    20: '原图neon carcar可读，含空格10字符。',
    21: '原图neoncarcar可读，9字符；继续清空是计划。',
}

def main():
    pointer = HERE/'T089-blur-gate-prefix21-source-review-current.json'
    assert not pointer.exists()
    source, root = checked(HERE/'source-prefix-late15-T089-late_blur3-gate-21-current.json')
    oldsource, oldroot = checked(HERE/'source-packets-late15-T089-late_white3-baseline-current.json')
    oldreview, oldrr = checked(HERE/'semantic-review-late15-T089-late_white3-baseline-current.json')
    rows = json.loads((root/'actor.json').read_bytes())['result']['requests']
    oldrows = json.loads((oldroot/'actor.json').read_bytes())['result']['requests']
    oldlabels = json.loads((oldrr/'review.json').read_bytes())['candidate_labels']
    assert len(rows) == 21
    labels = []
    for row, old, label in zip(rows[:10], oldrows[:10], oldlabels[:10]):
        assert all(row[k] == old[k] for k in ['decision', 'body_sha256', 'native_text', 'all_image_sha256s', 'current_image_sha256'])
        assert hashlib.sha256(row['native_text'].encode()).hexdigest() == label['candidate_text_sha256']
        labels.append({**label, 'request_id': row['request_id'], 'receipt_seal_sha256': row['receipt_seal_sha256'],
                       'exact_complete_input_reply_PNG_cross_run_review_reuse': oldreview,
                       'cross_run_request_receipt_rebound_not_same_runtime_request': True,
                       'new_independent_reviewers': 0})
    for row in rows[10:]:
        i = row['decision']
        labels.append({'decision': i, 'request_id': row['request_id'], 'body_sha256': row['body_sha256'],
                       'candidate_text_sha256': hashlib.sha256(row['native_text'].encode()).hexdigest(),
                       'receipt_seal_sha256': row['receipt_seal_sha256'],
                       'current_image_sha256': row['current_image_sha256'],
                       'all_lawful_delivered_image_sha256s': row['all_image_sha256s'],
                       'definite_boundary_inclusive_Mirage': i == 16,
                       'has_unresolved_subclaim': False, 'pure_native_WAIT_excluded': False,
                       'separate_native_action_error': i in [11, 12],
                       'source_review': NOTES[i], 'source_review_complete_for_this_candidate': True})
    out = HERE/('T089-blur-gate-prefix21-source-review-'+str(time.time_ns()))
    out.mkdir()
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    (out/'review-zoom-16.png').write_bytes((HERE/'review-zoom-T089-blur-gate16.png').read_bytes())
    save(out/'review.json', {'time': time.time(), 'run_id': 'late15-T089-late_blur3-gate',
        'source_packets': source, 'cross_run_first10_source': oldsource, 'cross_run_first10_review': oldreview,
        'candidate_count_in_prefix': 21, 'candidate_labels': labels,
        'viewed_original_new_current_PNG_sha256s': sorted({r['current_image_sha256'] for r in rows[10:]}),
        'definite_positive_decisions_in_prefix': [16], 'unresolved_decisions_in_prefix': [],
        'whole_trajectory_review_complete': False, 'whole_trajectory_Mirage': None,
        'normal_frame_text_error_after_recovery_not_proof_of_blur_causation': True,
        'group_postexit_raw_audit_pending': True, 'single_reviewer_not_fully_blind': True,
        'new_model_GUI_calls': 0, 'Mirage_reduction_proven': False})
    save(out/'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    save(pointer, {'root': str(out), 'seal_sha256': sha(out/'seal.json'), 'candidate_prefix_coverage': 21,
                   'definite_positive_decisions': [16], 'whole_trajectory_review_complete': False})
    print(json.dumps({'review': str(out), 'candidates': 21, 'positive': [16], 'whole_review_complete': False}))

if __name__ == '__main__':
    main()
