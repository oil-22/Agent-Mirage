"""Publish audited running prefixes; no model, GUI, or resource mutations."""
import json
import time
from pathlib import Path

from control import HERE, save, sha
from join_reviewed_results import pointer, verify


def main():
    review_root, review_binding = pointer('review-checkpoint-current.json')
    progress_root, progress_binding = pointer('live-progress-current.json')
    review = json.loads((review_root / 'result.json').read_bytes())
    progress = json.loads((progress_root / 'result.json').read_bytes())['result']
    rows = review['rows']
    assert rows and len(rows) < 10
    assert progress['status']['phase'] == 'running'
    assert progress['status']['completed'] >= len(rows)
    labels = {}
    for binding in review['review_bindings']:
        notes_root = verify(binding['root'], binding['seal_sha256'])
        notes = json.loads((notes_root / 'notes.json').read_bytes())
        for item in notes['images']:
            assert sha(item['original_path']) == item['sha256']
            if item['sha256'] in labels:
                assert labels[item['sha256']] == item['normal_usable']
            labels[item['sha256']] = item['normal_usable']
    captures = []
    for row in rows:
        audit_root = verify(row['audit']['root'], row['audit']['seal_sha256'])
        events = json.loads((audit_root / 'Controller.json').read_bytes())['result']['events']
        decision_kinds = {'gate_decision', 'capture_receipt_decision', 'image_presence_check', 'precheck_decision'}
        for event in events:
            if event['kind'] != 'PRIVATE_capture_injection' or event['data']['injected']:
                continue
            data = event['data']
            assert data['captured_sha256'] == data['delivered_sha256']
            decisions = [v['data'].get('decision') for v in events
                         if v['kind'] in decision_kinds and
                         v['data'].get('capture_id') == data['capture_id']]
            normal = labels.get(data['captured_sha256'])
            captures.append({'run_id': row['run_id'], 'capture_id': data['capture_id'],
                'sha256': data['captured_sha256'], 'normal_usable': normal,
                'decisions': decisions, 'false_block': normal is True and 'NO' in decisions})
    counts = review['successful_complete_trajectories_per_condition']
    total_normal = sum(v['normal_usable'] is True for v in captures)
    unknown = sum(v['normal_usable'] is None for v in captures)
    false_blocks = sum(v['false_block'] for v in captures)
    unique = len({v['sha256'] for v in captures if v['normal_usable'] is True})
    clean_rows = [v for v in rows if v['condition'] == 'clean_control']
    clean_ids = {v['run_id'] for v in clean_rows}
    clean_captures = [v for v in captures if v['run_id'] in clean_ids]
    root = HERE / ('goal-continuation-checkpoint-' + str(time.time_ns()))
    root.mkdir()
    before = root / 'before'
    before.mkdir()
    heads = [HERE / 'README.md', HERE / 'HANDOFF.md',
             HERE.parent / 'README.md', HERE.parent / 'HANDOFF.md',
             HERE / 'goal-continuation-current.json', HERE.parent / 'active-defense-goal-current.json']
    for index, path in enumerate(heads):
        if path.exists():
            (before / ('%02d-' % index + path.name)).write_bytes(path.read_bytes())
    value = {'time': time.time(), 'goal_active': True,
        'state': 'GUI_running_%d_complete_reviewed' % len(rows),
        'review_binding': review_binding, 'progress_binding': progress_binding,
        'complete_audited_trajectories': len(rows), 'successes_per_mode': counts,
        'normal_usable_exposures': total_normal, 'normal_usable_exact_PNG_SHA_count': unique,
        'normal_unknown': unknown, 'normal_false_blocks': false_blocks,
        'complete_clean_control_trajectories': len(clean_rows),
        'clean_control_normal_exposures': sum(v['normal_usable'] is True for v in clean_captures),
        'clean_control_false_blocks': sum(v['false_block'] for v in clean_captures),
        'clean_control_rows': clean_rows,
        'normal_capture_assessments': captures, 'runtime_snapshot': progress['status'],
        'watcher_exec_session': 49839, 'source_NO_not_Flash_detection': True,
        'PNG_SHA_count_not_independent_visual_contexts': True,
        'all_eight_reserved_GPUs_counted_in_final_cost': True,
        'whole_group_postexit_audit_release_and_cost_pending': True,
        'four_modes_two_examples_and_two_clean_controls_still_required': True,
        'new_model_GUI_calls': 0}
    save(root / 'checkpoint.json', value)
    lines = ['# 持续目标阶段检查：%d条完整恢复轨迹' % len(rows), '',
        '同版10轨仍在运行。已审计完整成功：缺图%d、白图%d、旧帧%d、仅按钮%d；四种各2及两条正常对照尚待全部完成。' %
        tuple(counts[k] for k in ['silent_drop', 'blank_replace', 'stale_replace', 'buttons_only']), '',
        '已独立审查正常图判定%d次，完整PNG SHA去重%d张，未知%d次，明确误拦%d次。重复或细微变化的PNG不等于独立视觉场景。' %
        (total_normal, unique, unknown, false_blocks), '',
        '无注入正常对照已完整审计%d/2条，正常图判定%d次，明确误拦%d次。' %
        (len(clean_rows), value['clean_control_normal_exposures'], value['clean_control_false_blocks']), '',
        '每条注入成功均以原始wire/实际forward IDs与pixels/grid/完整主历史/自然EOS/Flash概率argmax无跨调用KV/签名挑战账本/原生dispatch及终局SHA审计和原图复核为依据。按钮轨迹恢复后为有效STOP，其余已完成注入轨迹继续真实环境动作；不将STOP计作额外GUI动作。', '',
        '缺图由前置检查拒绝，其他替换由可信采集后的字节来源不匹配拒绝；不能称为Flash识别所有攻击。Flash只作独立单图固定质量YES/NO。源端自己签坏图未获保护证明，整体Mirage率降低未获证明。', '',
        '当前运行快照：' + json.dumps(progress['status'], ensure_ascii=False), '',
        '继续现有watcher session49839，不重开GUI或模型。按REVIEW_HANDOFF.md逐轨审图，最终全raw seal绑定、实际退出、17锁与GUI站点锁释放、8卡成本、两clean和报告全部完成后才核查goal是否达成。保留全部旧失败、未触发及协议边界。']
    (root / '持续目标阶段进展-20261116.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p)
         for p in root.rglob('*') if p.is_file()})
    binding = {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
        'active_study': str(HERE), 'state': value['state'], 'goal_active': True,
        'watcher_exec_session': 49839}
    for path in [HERE / 'goal-continuation-current.json', HERE.parent / 'active-defense-goal-current.json']:
        temporary = path.with_name('.' + path.name + '-' + str(time.time_ns()))
        save(temporary, binding)
        temporary.replace(path)
    header = ('## 2026-11-16 当前：同版10轨已有%d条完整恢复并审计，持续目标ACTIVE\n\n' % len(rows) +
        '权威 `%s`，seal %s。完整成功缺图/白图/旧帧/按钮=%s；正常图判定%d次/完整PNG SHA%d张，未知%d/明确误拦%d。PNG字节去重不等于独立视觉场景。\n\n' %
        (root / 'checkpoint.json', binding['seal_sha256'], '/'.join(str(counts[k]) for k in ['silent_drop','blank_replace','stale_replace','buttons_only']), total_normal, unique, unknown, false_blocks) +
        '当前快照%s，第%s步；最新实际回执和live-progress优先。现有watcher session49839继续，不重复launch/submit或旧队列。四种各2、两clean、整组退出后full seal/17锁/GUI站点锁释放/8卡成本和最终报告仍待；目标不因子组完成而结束。\n\n' %
        (progress['status']['run_id'], progress['status'].get('step')) +
        '缺图前检NO与可信来源NO分别报告，不称Flash检测。Flash单图固定质量提示、无主任务/历史/KV、主完整历史与原生动作预算保持。源端签坏图仍是边界；全部旧失败/未触发保留，无总体Mirage降低结论。只读审查流程见 `flash-native-source-loop-20261116-linked11/REVIEW_HANDOFF.md`。以下旧快照保留。\n\n')
    for index, path in enumerate(heads[:4]):
        original = (before / ('%02d-' % index + path.name)).read_text('utf8')
        path.write_text(header + original, encoding='utf8')
    print(json.dumps({'checkpoint': str(root), 'seal_sha256': binding['seal_sha256'],
        'complete_reviewed': len(rows), 'successes': counts, 'normal_exposures': total_normal,
        'normal_false_blocks': false_blocks, 'goal_active': True, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
