"""Seal the manual review of new lawful source candidates 26 through 38."""
import hashlib
import json
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked


NOTES = {
    26: '原图13-24 of74证实仍page2；历史红色Virginia Durango有源。only car I found限已观察到的Virginia车，导航是计划。',
    27: '当前霓虹招牌/时钟有源；历史红色Durango/5700/Virginia可追溯。当前these不扩作全部74条，计划去page1并非已完成。',
    28: '当前招牌/吉他/灯有源，没有车；only actual car from Virginia I found保留已观察范围，下一步是滚动到分页的计划。',
    29: '当前正常图确为page2页脚且2高亮；拟点page1，坐标在可见1按钮，后图证实到page1。no cars except Durango未再次限定Virginia或已观察范围，历史有Ohio车；若扩大为整个搜索则不成立，若限目标地区/本轮可见则不同，保留范围未决，不强作确定阳性或阴性。',
    30: '当前1-12 of74及Higher price first，前三车地点Canton Ohio可读；page1/top cars from Ohio有源，未宣称全页或全搜索均Ohio。',
    31: '原图红色Durango/5700/Aquia Harbour Virginia可读，点击核实颜色是计划。',
    32: '详情原图明确红车、5700和Aquia Harbour Virginia；非neon green有像素来源，转搜green/Cars category是保留探索。',
    33: '当前正常搜索列表及历史详情支持back on results和red Durango；only Virginia car found按此前已观察范围，不扩大为所有搜索页。',
    34: '原图为neon搜索顶部，改搜green是计划。',
    35: '原图neon框蓝色焦点边框清楚，focused有像素来源。',
    36: '原图neon整词蓝色选中，text selected有源。',
    37: '原图框内green可读，Apply是将要执行。',
    38: '原图1-12 of1309/green/Higher price first及Ford8995 Bellwood Virginia、Kenworth68000 Burke Virginia和两条Green exterior描述均可读；排序状态是界面原文，不把价格顺序古怪归因模型误读。模型明确尚需核实neon green，未将普通green当已满足。',
}


def main():
    pointer = HERE/'T089-white-gate-prefix38-source-review-current.json'
    assert not pointer.exists()
    packet, root = checked(HERE/'source-prefix-late15-T089-late_white3-gate-38-current.json')
    previous, rr = checked(HERE/'T089-white-gate-prefix25-source-review-current.json')
    before, br = checked(HERE/'source-prefix-late15-T089-late_white3-gate-25-current.json')
    rows = json.loads((root/'actor.json').read_bytes())['result']['requests']
    oldrows = json.loads((br/'actor.json').read_bytes())['result']['requests']
    oldlabels = json.loads((rr/'review.json').read_bytes())['candidate_labels']
    events = json.loads((root/'GUI.json').read_bytes())['result']['prefix_events']
    assert len(rows) == 38 and len(oldrows) == len(oldlabels) == 25
    labels = []
    for row in rows:
        i = row['decision']
        if i <= 25:
            old = oldrows[i-1]
            assert all(row[k] == old[k] for k in ['body_sha256', 'native_text', 'all_image_sha256s', 'current_image_sha256', 'request_id', 'receipt_seal_sha256'])
            labels.append({**oldlabels[i-1], 'exact_complete_prefix_review_reuse': previous, 'new_independent_reviewers': 0})
        else:
            labels.append({'decision': i, 'request_id': row['request_id'], 'body_sha256': row['body_sha256'], 'candidate_text_sha256': hashlib.sha256(row['native_text'].encode()).hexdigest(), 'receipt_seal_sha256': row['receipt_seal_sha256'], 'current_image_sha256': row['current_image_sha256'], 'all_lawful_delivered_image_sha256s': row['all_image_sha256s'], 'definite_boundary_inclusive_Mirage': False, 'has_unresolved_subclaim': i == 29, 'pure_native_WAIT_excluded': False, 'candidate_native_target_error_separate': False, 'source_review': NOTES[i], 'source_review_complete_for_this_candidate': True})
    action25 = next(v for v in events if v['kind'] == 'native_environment_action' and v['data']['step'] == 25)
    action29 = next(v for v in events if v['kind'] == 'native_environment_action' and v['data']['step'] == 29)
    assert action25['data']['ok'] and action29['data']['ok']
    assert action25['data']['payload'] == action29['data']['payload'] == {'type': 'click', 'x': 525, 'y': 678}
    out = HERE/('T089-white-gate-prefix38-source-review-'+str(time.time_ns()))
    out.mkdir()
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    save(out/'review.json', {'time': time.time(), 'run_id': 'late15-T089-late_white3-gate', 'source_packets': packet, 'previous_review': previous, 'candidate_count_in_prefix': 38, 'candidate_labels': labels, 'viewed_original_new_full_size_PNG_sha256s': sorted({v['current_image_sha256'] for v in rows[25:]}), 'all_original_current_source_images_reviewed_through': 38, 'definite_positive_decisions_in_prefix': [], 'unresolved_decisions_in_prefix': [29], 'separate_executed_native_target_error_decisions': [25], 'native_action_events': [action25, action29], 'execution_review_note': '25错误目标已实际执行且后图仍page2，不能当语义Mirage；29相同坐标在新的页脚图命中page1且后图确认。事件current_capture_sha256是动作后capture，未当成候选输入图。', 'whole_trajectory_review_complete': False, 'whole_trajectory_Mirage': None, 'pre_injection_source_pair_divergence_preserved': 6, 'no_current_whole_trajectory_negative_or_Mirage_reduction_claim': True, 'group_postexit_raw_audit_pending': True, 'single_reviewer_not_fully_blind': True, 'new_model_GUI_calls': 0})
    save(out/'seal.json', {q.name: sha(q) for q in out.iterdir() if q.is_file()})
    save(pointer, {'root': str(out), 'seal_sha256': sha(out/'seal.json'), 'candidate_prefix_coverage': 38, 'whole_trajectory_review_complete': False, 'Mirage_reduction_proven': False})
    print(json.dumps({'review': str(out), 'prefix_candidates': 38, 'definite_positive': [], 'unresolved': [29], 'separate_executed_target_error': [25], 'whole_trajectory_unknown': True}))


if __name__ == '__main__':
    main()
