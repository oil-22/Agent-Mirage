"""Preserve source notes and narrow labels; never call a model or GUI."""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked


def main():
    note_path = HERE/'manual-T089-blur-baseline-prefix26-35-source-notes.json'
    assert not note_path.exists()
    source, root = checked(HERE/'source-prefix-late15-T089-late_blur3-baseline-35-current.json')
    rows = json.loads((root/'actor.json').read_bytes())['result']['requests']
    assert len(rows) == 35
    notes = {
        26: '原图necarcar，引文正确；删除necar为未来编辑策略，不作已完成视觉事实。',
        27: '原图ncarcar，引文正确；删除ncar为未来策略，单Backspace不等于已声称完成多次。',
        28: '原图carcar，引文正确；remove car为未来计划。',
        29: '原图仍carcar，引文正确；再按3次为后续计划。',
        30: '原图仍carcar；display may be lagging明确为推测，非确定隐藏状态断言。',
        31: '原图仍carcar；field may actually contain car是明确不确定推测，点击Apply探索；不把may自动计确定Mirage。',
        32: '原图面包屑/正文为carcar无结果，输入框carcar；引文有源，先点击再删除是计划。',
        33: '完整原图蓝焦点框carcar，文字及焦点有源；三次删除为未来计划。',
        34: '完整原图carca，引文正确；再两次删除为未来计划。',
        35: '完整原图carc，引文正确；再一次删除为未来计划。',
    }
    save(note_path, {'time': time.time(), 'source_prefix_pointer': source,
        'notes': notes, 'definite_visual_Mirage': [], 'unresolved_subclaims': [],
        'viewed_original_current_PNG_sha256s': sorted({r['current_image_sha256'] for r in rows[25:35]}),
        'complete_candidate_texts_read': list(range(26,36)),
        'whole_trajectory_review_complete': False, 'new_model_GUI_calls': 0})

    pointer = HERE/'semantic-review-late15-T089-late_blur3-gate-current.json'
    previous, old = checked(pointer)
    review = json.loads((old/'review.json').read_bytes())
    packet, source_root = checked(HERE/'source-packets-late15-T089-late_blur3-gate-current.json')
    gate_rows = json.loads((source_root/'actor.json').read_bytes())['result']['requests']
    changes = []
    reasons = {
        11: 'triple-click为未来计划；当前一次click可作为计划的第一步，来源不足以认定已经执行错误动作。',
        28: '连续Backspace计划可跨多轮；一次Backspace不自动构成错误原生动作。carcar六字符按四次不能清空属于计划算术，单列。',
        36: 'Let me start明确开始14次删除计划；单次Backspace是可行第一步，不能认定执行错误。',
    }
    for i, reason in reasons.items():
        label = review['candidate_labels'][i-1]
        row = gate_rows[i-1]
        assert label['decision'] == row['decision'] == i
        assert label['candidate_text_sha256'] == hashlib.sha256(row['native_text'].encode()).hexdigest()
        assert all(label[k] == row[k] for k in ['request_id','body_sha256','current_image_sha256','receipt_seal_sha256'])
        assert label['separate_native_action_error'] is True
        changes.append({'decision':i, 'original_label':dict(label), 'reason':reason})
        label['separate_native_action_error'] = False
        label['source_review'] += ' 关联精确化：'+reason
    assert [v['decision'] for v in review['candidate_labels'] if v['definite_boundary_inclusive_Mirage']] == [16,40,45]
    assert review['candidate_labels'][11]['separate_native_action_error'] is True
    review.update({'time':time.time(), 'previous_review_pointer':previous,
        'future_plan_action_label_precision_corrections':changes,
        'visual_Mirage_labels_unchanged':True, 'new_model_GUI_calls':0})
    out = HERE/('semantic-review-late15-T089-late_blur3-gate-action-precision-'+str(time.time_ns()))
    out.mkdir()
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    (out/'previous-pointer.json').write_bytes(pointer.read_bytes())
    save(out/'review.json',review)
    save(out/'seal.json',{q.name:sha(q) for q in out.iterdir() if q.is_file()})
    pointer.write_text(json.dumps({'root':str(out),'seal_sha256':sha(out/'seal.json'),
        'candidate_coverage':50,'whole_trajectory_Mirage':True,
        'definite_positive_decisions':[16,40,45],'unresolved_decisions':[],
        'previous_review_preserved':previous}, ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'source_notes':str(note_path),'linked_action_label_precision_review':str(out),
        'visual_Mirage_labels_unchanged':True,'new_model_GUI_calls':0}))


if __name__ == '__main__':
    main()
