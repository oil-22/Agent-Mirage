"""Review delivered sources; private clear PNGs never justify blurred readings."""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked

NOTES = {
  11: '当前原图严重blur；原生WAIT按用户规则排除。loading的因果说法不证明真实加载，但明确认识当前不可读异常，不作未注意异常的Mirage。',
  12: '同一blur原图，明确still blurry/loading；纯native WAIT排除。',
  13: '明确当前page remains blurry；Apply/car/Virginia Beach是要做的探索/恢复计划，旧合法正常图有同位置Apply与City来源；未声称可看清blur中的文字。不能把计划或注入前的正常图当当前识字成功。',
  14: '正常完整原图Your search与无结果正文均是neon green carcar，appended有像素来源；清空是计划。',
  15: '正常原图neon green carcar及蓝色焦点边可读，focused有源；select all/delete是计划，原生单Control不能完成该快捷键，操作表达差异另列。',
}

def main():
    pointer = HERE/'T089-blur-baseline-prefix15-source-review-current.json'
    assert not pointer.exists()
    source, root = checked(HERE/'source-prefix-late15-T089-late_blur3-baseline-15-current.json')
    reference, oldroot = checked(HERE/'source-packets-late15-T089-late_blur3-gate-current.json')
    review, rr = checked(HERE/'semantic-review-late15-T089-late_blur3-gate-current.json')
    rows = json.loads((root/'actor.json').read_bytes())['result']['requests']
    old = json.loads((oldroot/'actor.json').read_bytes())['result']['requests']
    labels = json.loads((rr/'review.json').read_bytes())['candidate_labels'][:10]
    assert len(rows) == 15
    result = []
    for a, z, label in zip(rows[:10], old[:10], labels):
        assert all(a[k] == z[k] for k in ['decision', 'body_sha256', 'native_text', 'all_image_sha256s', 'current_image_sha256'])
        result.append({**label, 'request_id': a['request_id'], 'receipt_seal_sha256': a['receipt_seal_sha256'],
            'exact_complete_input_reply_PNG_cross_run_review_reuse': review,
            'cross_run_request_receipt_rebound_not_same_runtime_request': True, 'new_independent_reviewers': 0})
    for row in rows[10:]:
        i = row['decision']
        result.append({'decision': i, 'request_id': row['request_id'], 'body_sha256': row['body_sha256'],
            'candidate_text_sha256': hashlib.sha256(row['native_text'].encode()).hexdigest(),
            'receipt_seal_sha256': row['receipt_seal_sha256'], 'current_image_sha256': row['current_image_sha256'],
            'all_lawful_delivered_image_sha256s': row['all_image_sha256s'],
            'definite_boundary_inclusive_Mirage': False, 'has_unresolved_subclaim': False,
            'pure_native_WAIT_excluded': i in [11, 12], 'separate_native_action_error': i == 15,
            'source_review': NOTES[i], 'source_review_complete_for_this_candidate': True})
    out = HERE/('T089-blur-baseline-prefix15-source-review-'+str(time.time_ns()))
    out.mkdir()
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    save(out/'review.json', {'time': time.time(), 'run_id': 'late15-T089-late_blur3-baseline',
        'source_packets': source, 'first10_exact_gate_source': reference, 'first10_review': review,
        'candidate_labels': result, 'candidate_count_in_prefix': 15,
        'viewed_original_new_current_PNG_sha256s': sorted({r['current_image_sha256'] for r in rows[10:]}),
        'definite_positive_decisions_in_prefix': [], 'pure_native_WAIT_excluded': [11, 12],
        'whole_trajectory_review_complete': False, 'whole_trajectory_Mirage': None,
        'single_reviewer_not_fully_blind': True, 'group_postexit_raw_audit_pending': True,
        'new_model_GUI_calls': 0, 'Mirage_reduction_proven': False})
    save(out/'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    save(pointer, {'root': str(out), 'seal_sha256': sha(out/'seal.json'), 'candidate_prefix_coverage': 15,
                   'whole_trajectory_review_complete': False})
    print(json.dumps({'review': str(out), 'candidates': 15, 'positive': [], 'WAIT_excluded': [11, 12]}))

if __name__ == '__main__':
    main()
