"""Select reproducible cases from audited evidence without selecting on score."""

import argparse
import json
import os
from pathlib import Path
import time

from audit_gate_cycles import audit as audit_gate_cycles
from collect import HERE, read, save, sha
from link import verify
from review_cycle import review_pairs
from summarize import CONDITIONS, COURSE_NAMES, load_reviews, pair_records


def choose_cases(metrics, pairs, cycles):
    activities = {v['run']: v for v in cycles['altered_initial_deliveries']}
    assert len(activities) == len(cycles['altered_initial_deliveries'])
    rows = {v['run_id']: v for v in metrics}

    def case(a):
        row = rows[a['run']]
        step, = (s for s in row['steps'] if s['decision'] == a['decision'])
        assert step['initial_delivered_sha256'] == a['captures'][0]['delivered_sha256']
        assert a['terminal_sha256'] == row['terminal_sha256'] and a['official_score'] == row['official_score']
        return {**a, 'actual_reply_sha256': step['main_raw_reply_sha256'],
                'trajectory_semantic_label': row['mirage_status']}

    cases = []
    for condition in CONDITIONS[1:]:
        matches = []
        for ordinal, pair in enumerate(pairs):
            if pair['condition'] != condition:
                continue
            off, on = (pair['actual_altered_observation'][x] for x in ('off','on'))
            if not (off.get('altered_observation_at_actual_forward') and on.get('normal_recapture_at_actual_forward')):
                continue
            a, b = (activities[pair[arm]] for arm in ('off','on'))
            same_altered_bytes = a['captures'][0]['delivered_sha256'] == b['captures'][0]['delivered_sha256']
            rank = (not pair['fired_and_matching_exact_native_prefix'], not same_altered_bytes,
                    not on['recapture_then_native_action_returned_ok'], ordinal)
            matches.append((rank, pair, a, b))
        if not matches:
            cases.append({'condition': condition, 'pair': None})
            continue
        rank, pair, off, on = min(matches, key=lambda x: x[0])
        cases.append({'condition': condition, 'pair': pair['pair_id'], 'task': pair['task_id'],
                      'version': pair['version'], 'exact_pre_injection_prefix': not rank[0],
                      'same_altered_input': not rank[1], 'off': case(off), 'on': case(on)})

    incomplete = next((case(a) for a in activities.values() if a['arm'] == 'on' and
        a['outcome_at_injection_decision'].get('rejection_stage') and
        not a['outcome_at_injection_decision'].get('normal_recapture_at_actual_forward')), None)
    later_error = None
    for a in activities.values():
        if a['arm'] != 'on' or not a['outcome_at_injection_decision'].get('normal_recapture_at_actual_forward'):
            continue
        row = rows[a['run']]
        step = next((s for s in row['steps'] if s['decision'] > a['decision'] and
                     s['normal_frame_definite_semantic_error']), None)
        if step:
            later_error = {'run': a['run'], 'version': a['version'], 'loop_decision': a['decision'],
                           'terminal_sha256': a['terminal_sha256'], 'official_score': a['official_score'],
                           'coherent_frame_error': step}
            break
    return {'sealed_slots': cycles['sealed_slots'], 'assigned_slots': len(metrics),
            'paired_examples': cases, 'example_incomplete_recovery': incomplete,
            'example_later_normal_frame_error_after_recovery': later_error,
            'selection_rule': 'For each condition, require real altered input at the off first forward and '
                'a verified same-decision normal recapture at the on first forward. Sort by exact native prefix, '
                'same altered delivery, successful post-recapture action, then frozen order. Do not select '
                'on score or semantic improvement. For each limitation, take the first in frozen order.',
            'new_model_GUI_or_scorer_calls': 0}


def render(data, out):
    def pixels(digest):
        if digest is None:
            return '缺图'
        p = HERE / 'original-images' / (digest + '.png')
        assert sha(p) == digest
        rel = Path(os.path.relpath(p, out)).as_posix()
        return f'[{digest[:12]}]({rel})'

    def official(row):
        return '未评分' if row['official_score'] is None else f"{row['official_score']:g}"

    lines = ['# Flash 截图防御：代表轨迹', '']
    if data['sealed_slots'] < data['assigned_slots']:
        lines.extend([f"阶段证据：已封存 {data['sealed_slots']}/{data['assigned_slots']} 条，尚无最终结论。", ''])
    lines.extend([
        '每种注入选一对确实发生注入的轨迹：关闭时异常输入进入主模型，开启时同一决策复拍并送入正常图。'
        '优先选注入前原图和动作相同、实际异常交付相同的配对，再按复拍当轮是否执行成功及原计划顺序选择。'
        '案例不按得分或 Mirage 筛选；总体比率使用完整配对报告。', '',
        '| 注入 | 任务／版本 | 注入前原图及动作相同 | 关闭：进入主模型 | 开启：拦截和复拍 | 官方评分（关／开） |',
        '| --- | --- | --- | --- | --- | --- |'])
    for p in data['paired_examples']:
        name = COURSE_NAMES[p['condition']]
        if p['pair'] is None:
            lines.append(f'| {name} | — | — | 还没有符合条件的核验示例 | — | — |')
            continue
        off, on = p['off'], p['on']
        dose = off['actual_model_request']['current_image_sha256']
        recovered = on['actual_model_request']['current_image_sha256']
        stage = {'precheck_decision': '存在检查', 'capture_receipt_decision': '采集回执',
                 'gate_decision': 'Flash'}.get(on['outcome_at_injection_decision']['rejection_stage'])
        assert stage and recovered is not None
        recapture, = (c for c in on['captures'] if c['capture_id'] == on['selected_capture_id'])
        assert recapture['independent_image_quality'] == 'coherent_usable'
        assert any(e['event'] == 'gate_decision' and e['decision'] == 'YES' for e in recapture['gate_events'])
        matching = '是' if p['exact_pre_injection_prefix'] else '否'
        lines.append(f"| {name} | T{p['task']:03d}／{p['version']} | {matching} | "
                     f"第 {off['decision']} 次决策，{pixels(dose)} | 第 {on['decision']} 次决策，"
                     f"{stage}拒绝，实拍 {pixels(recovered)}，Flash 通过后送入主模型 | {official(off)}／{official(on)} |")
    lines.extend(['', '失败与边界：', ''])
    item = data['example_incomplete_recovery']
    if item:
        outcome = item['outcome_at_injection_decision']['state']
        lines.append(f"- `{item['run']}` 第 {item['decision']} 次决策挡住了异常输入，但未证实正常复拍图进入前向"
                     f"（`{outcome}`；官方{official(item)}）。这不是恢复成功。")
    item = data['example_later_normal_frame_error_after_recovery']
    if item:
        s = item['coherent_frame_error']
        lines.append(f"- `{item['run']}` 在第 {item['loop_decision']} 次决策恢复了正常图；之后第 {s['decision']} 次"
                     f"决策在可用原图 {pixels(s['current_actual_image_sha256'])} 上仍出现独立确认的语义错误。"
                     '这不属于截图门控漏拦。')
    lines.extend(['', '传输时的旧图替换与采集端拍早、回执仍然正确是不同的条件。这里的配对只覆盖前者。',
                   '每例的实际前向、动作回执、终局和两端证据链见同目录 JSON。', ''])
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('report', type=Path)
    a = p.parse_args()
    for d in (a.ledger, a.report):
        verify(d)
    report = read(a.report / 'condition-by-version.json')
    ledger_seal = sha(a.ledger / 'seal.json')
    assert report['ledger_seal_sha256'] == ledger_seal
    ledger = read(a.ledger / 'private-linked.json')
    metrics = read(a.report / 'trajectory-metrics.json')
    pairs = list(pair_records(metrics))
    assert pairs == read(a.report / 'paired-metrics.json')
    quality, _, _ = load_reviews(ledger, review_pairs(a.report))
    cycles = audit_gate_cycles(ledger, metrics, quality, report['overall_counts_only_no_pooled_effect_estimate'])
    evidence = choose_cases(metrics, pairs, cycles)
    out = HERE / 'case-indexes' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'representative-cases.json', {'ledger_seal_sha256': ledger_seal,
        'report_seal_sha256': sha(a.report / 'seal.json'), 'final': report['is_final'], **evidence})
    (out / '代表轨迹.md').write_text(render(evidence, out), encoding='utf-8')
    save(out / 'seal.json', {k: sha(out / k) for k in ('representative-cases.json', '代表轨迹.md')})
    print(json.dumps({'case_index': str(out), 'seal_sha256': sha(out / 'seal.json'),
                      'pairs': [v['pair'] for v in evidence['paired_examples']]}))


if __name__ == '__main__':
    main()
