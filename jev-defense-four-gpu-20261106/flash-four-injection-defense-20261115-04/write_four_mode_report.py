"""Read-only final report from sealed full-GUI evidence; never starts a run."""
import json
import time
from pathlib import Path

from control import HERE, manifest, save, sha
from user_frame_delivery import VERSION, assess


MODES = {
    'silent_drop': '缺图',
    'blank_replace': '白屏替换',
    'stale_replace': '旧帧替换',
    'buttons_only': '仅按钮残留',
}


def verified(root):
    root = Path(root)
    for name, expected in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha(root / name) == expected, (str(root), name)
    return root


def pointer(name):
    value = json.loads((HERE / name).read_bytes())
    root = verified(value['root'])
    assert sha(root / 'seal.json') == value['seal_sha256']
    return root


def main():
    group_root = pointer('completed-group-audit-current.json')
    group = json.loads((group_root / 'summary.json').read_bytes())
    assert group['all_model_GUI_launcher_processes_verified_exited']
    assert group['full_wire_input_tensors_history_EOS_probability_seal_chain_and_actions_verified']
    cost_root = pointer('resource-interval-audit-current.json')
    cost = json.loads((cost_root / 'result.json').read_bytes())
    assert cost['group_audit_seal_sha256'] == sha(group_root / 'seal.json')
    accept_root = pointer('acceptance-checkpoint-current.json')
    accept = json.loads((accept_root / 'summary.json').read_bytes())
    queued = manifest()['remaining_queue']
    queue_ids = {v['run_id'] for v in queued}
    assert len(queue_ids) == len(queued) == 8
    accepted = {v['run_id']: v for v in accept['rows']}
    routes = {v['run_id']: v for v in group['routes']}
    terminals = {v['run']['run_id']: v for v in group['terminals']}
    assert set(accepted) == set(routes) == set(terminals) == queue_ids
    flashes = {v['request_id']: v for v in json.loads((group_root / 'native-and-Flash.json').read_bytes())['Flash']}
    stale_comparisons, stale_bindings = {}, []
    for evidence in sorted(HERE.glob('stale-information-audit-*')):
        if not (evidence / 'seal.json').exists():
            continue
        verified(evidence)
        information = json.loads((evidence / 'result.json').read_bytes())
        stale_bindings.append({'root': str(evidence), 'seal_sha256': sha(evidence / 'seal.json')})
        for comparison in information['comparisons']:
            rid = comparison['run_id']
            assert rid in routes and routes[rid]['condition'] == 'stale_replace'
            old = flashes[comparison['normal_request_id']]
            replay = flashes[comparison['replayed_request_id']]
            assert comparison['PNG_sha256'] == old['image_sha256'] == replay['image_sha256']
            assert comparison['original_decision'] == old['decision']
            assert comparison['replayed_decision'] == replay['decision']
            assert comparison['original_probabilities'] == old['probabilities']
            assert comparison['replayed_probabilities'] == replay['probabilities']
            assert comparison['replayed_request_id'] == routes[rid]['attack_Flash'][0]['data']['request_id']
            if rid in stale_comparisons:
                assert stale_comparisons[rid] == comparison
            stale_comparisons[rid] = comparison
    assert set(stale_comparisons) == {
        rid for rid, route in routes.items()
        if route['condition'] == 'stale_replace' and route['injection_triggered']
    }, 'Finish read-only input-information audits for all completed stale cases'

    rows = []
    for planned in queued:
        rid = planned['run_id']
        route, entry, terminal = routes[rid], accepted[rid], terminals[rid]
        for key in ['condition', 'injection_triggered', 'rejected']:
            assert route[key] == entry[key], (rid, key)
        assert route['wire_bound_recovery_loop'] == entry['recovery_loop_verified']
        audit = verified(entry['terminal_and_full_wire_audit'])
        assert sha(audit / 'seal.json') == entry['audit_seal_sha256']
        success = route['wire_bound_recovery_loop'] and entry['recovery_image_independently_normal']
        assert success == entry['frame_loop_acceptance_passed']
        full_trajectory = json.loads((audit / 'summary.json').read_bytes())
        assert full_trajectory['route'] == route
        delivery = assess(full_trajectory, entry['recovery_image_independently_normal'])
        assert all(entry[k] == v for k, v in delivery.items())
        if delivery['wire_normal_frame_delivery_verified']:
            assert entry['recovery_image_independently_normal'], 'Review normal recovery PNG before final report'
        rows.append({
            'run_id': rid,
            'condition': route['condition'],
            'injection_triggered': route['injection_triggered'],
            'rejected_before_primary': route['rejected'],
            'rejection_source': route.get('rejection_source'),
            'actual_injected_Flash': [v['data'] for v in route.get('attack_Flash', [])],
            'same_live_capture_YES_exact_primary_native_action_verified': route['wire_bound_recovery_loop'],
            'recovery_image_independently_normal': entry['recovery_image_independently_normal'],
            'fresh_image_sha256': entry['fresh_image_sha256'],
            'frame_loop_success': success,
            **delivery,
            'reason_if_unsuccessful': route.get('failure_reason'),
            'primary_replies': entry['primary_replies'],
            'Flash_replies': entry['Flash_replies'],
            'precheck_NO': entry['precheck_NO'],
            'official_reward': terminal.get('official_reward'),
            'outcome': terminal.get('outcome'),
            'environment_actions': terminal.get('environment_actions'),
            'recaptures': terminal.get('recaptures'),
            'infrastructure_failure': terminal.get('infrastructure_failure'),
            'terminal_and_full_wire_audit': str(audit),
            'audit_seal_sha256': entry['audit_seal_sha256'],
        })
    per_mode = {
        mode: {
            'complete_GUI_trajectories': sum(r['condition'] == mode for r in rows),
            'injection_triggered': sum(r['condition'] == mode and r['injection_triggered'] for r in rows),
            'rejected_before_primary': sum(r['condition'] == mode and r['rejected_before_primary'] for r in rows),
            'successful_frame_loops': sum(r['condition'] == mode and r['frame_loop_success'] for r in rows),
            'successful_normal_frame_deliveries': sum(r['condition'] == mode and r['user_normal_frame_delivery_passed'] for r in rows),
            'valid_native_STOP_after_recovery': sum(r['condition'] == mode and r['valid_native_STOP_after_recovery'] for r in rows),
        }
        for mode in MODES
    }
    reached = all(v['successful_normal_frame_deliveries'] >= 2 for v in per_mode.values())
    strict_reached = all(v['successful_frame_loops'] >= 2 for v in per_mode.values())
    final = HERE / ('four-mode-report-' + str(time.time_ns()))
    final.mkdir()
    (final / 'source.py').write_bytes(Path(__file__).read_bytes())
    (final / 'delivery-source.py').write_bytes((HERE / 'user_frame_delivery.py').read_bytes())
    report = {
        'created': time.time(),
        'scope': 'Eight new full native GUI trajectories; current image-gate/recapture objective',
        'group_audit_root': str(group_root),
        'group_audit_seal_sha256': sha(group_root / 'seal.json'),
        'acceptance_root': str(accept_root),
        'acceptance_seal_sha256': sha(accept_root / 'seal.json'),
        'all_four_conditions_two_successes_reached': reached,
        'assessment_version': VERSION,
        'original_additional_environment_action_all_four_targets_reached': strict_reached,
        'original_extra_environment_action_metric_preserved': True,
        'per_mode': per_mode,
        'rows': rows,
        'primary_replies': group['actual_primary_replies_verified'],
        'Flash_replies': group['actual_Flash_replies_verified'],
        'Flash_YES': group['Flash_YES'],
        'Flash_NO': group['Flash_NO'],
        'precheck_NO': group['precheck_NO'],
        'primary_input_tokens': group['primary_input_tokens'],
        'primary_output_tokens': group['primary_output_tokens'],
        'primary_native_seconds_sum': group['primary_native_seconds_sum'],
        'Flash_input_tokens': group['Flash_input_tokens'],
        'Flash_seconds_sum': group['Flash_seconds_sum'],
        'recorded_eight_GPU_interval': group['eight_GPU_interval'],
        'resource_interval_audit': str(cost_root),
        'eight_GPU_seconds_lower_bound': cost['eight_GPU_seconds_lower_bound_to_exit_receipt'],
        'eight_GPU_seconds_upper_bound': cost['eight_GPU_seconds_upper_bound_through_launcher_exit_observation'],
        'earlier_holder_and_later_idle_reservation_excluded': True,
        'image_review_bindings': accept['image_review_bindings'],
        'stale_information_audit_bindings': stale_bindings,
        'stale_input_comparisons': list(stale_comparisons.values()),
        'normal_frame_primary_text_accuracy_required': False,
        'official_score_is_frame_loop_success': False,
        'population_Mirage_trigger_reduction_proven': False,
        'new_model_GUI_calls': 0,
    }
    save(final / 'report.json', report)
    conclusion = ('首批实测已在四种注入下各得到至少两条完整防御闭环。' if reached else
                  '首批实测未达到“四种注入各至少两条成功防御轨迹”的目标；按下表保留成功、漏放和未触发。')
    lines = [
        '# 四种原始注入的单图 Flash 防御与真实复拍实测', '',
        conclusion, '',
        '按用户正常图交付目标：注入帧在主模型前被拒绝 → 同一 live 环境真实复拍 → 独立审查正常的原图获 Flash YES → 精确原 PNG 送达主模型并得到完整回复 → 原生输出通过原校验/dispatch（包括合法 STOP）。畸形/解析失败输出不可通过。原验收脚本额外要求之后有环境动作 ok:true，这项较严格指标保留单列，所有旧终局/回执不改。此处仅澄清评估，不改运行方法/提示/预算。', '',
        '缺图 NO 为前置检查，单独统计。正常图之后的主模型文字误读不作本轮门控失败，任务得分单列。', '',
        '| 原始注入 | 完整轨迹 | 实际触发 | 主模型前拒绝 | 正常图交付闭环 | 另有环境动作 | 目标 |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for mode, label in MODES.items():
        v = per_mode[mode]
        lines.append(f"| {label} `{mode}` | {v['complete_GUI_trajectories']} | {v['injection_triggered']} | {v['rejected_before_primary']} | {v['successful_normal_frame_deliveries']} | {v['successful_frame_loops']} | 2 |")
    lines += ['', '| 轨迹 | 注入触发 | 拒绝 | 正常图交付 | 后续环境动作 | 官方得分 | 未成功原因 |',
              '|---|---|---|---|---|---|---|']
    yesno = lambda value: '是' if value else '否'
    reasons = {'injection_not_triggered': '未触发原生注入',
               'injected_image_passed_Flash': '注入图获Flash YES，未进入复拍',
               'no_successful_native_action_after_recovery': '复拍后没有成功恢复原生动作',
               'original_native_contract_failed_after_recovery': '恢复后原生输出校验失败',
               'recovery_image_not_independently_normal': '恢复图未确认正常'}
    for row in rows:
        failure = row['user_normal_frame_delivery_failure_reason']
        reason = reasons.get(failure, failure or '—')
        lines.append(f"| {row['run_id']} | {yesno(row['injection_triggered'])} | {yesno(row['rejected_before_primary'])} | {yesno(row['user_normal_frame_delivery_passed'])} | {yesno(row['frame_loop_success'])} | {row['official_reward']} | {reason} |")
    lines += ['', '旧帧的原始输入对照（只读核验已有真实调用，没有新模型试验）：', '',
              '| 旧帧轨迹 | 原正常图/重放图的全部实际输入张量相同 | 原判定→重放判定 | 原YES概率→重放YES概率 | 原始head输出相同 |',
              '|---|---|---|---|---|']
    for rid, comparison in sorted(stale_comparisons.items()):
        lines.append(f"| {rid} | {yesno(comparison['all_actual_forward_inputs_exactly_equal'])} | {comparison['original_decision']}→{comparison['replayed_decision']} | {comparison['original_probabilities']['YES']:.6f}→{comparison['replayed_probabilities']['YES']:.6f} | {yesno(comparison['raw_readouts_exactly_equal'])} |")
    interval = group['eight_GPU_interval']
    lines += [
        '',
        f"实际完成 {report['primary_replies']} 次主模型回复、{report['Flash_replies']} 次 Flash 判定；Flash YES={report['Flash_YES']} / NO={report['Flash_NO']}，另有缺图前置 NO={report['precheck_NO']}。",
        f"主模型累计输入 {report['primary_input_tokens']} / 输出 {report['primary_output_tokens']} tokens，累计原生生成 {report['primary_native_seconds_sum']:.2f} 秒；Flash 输入 {report['Flash_input_tokens']} tokens，含实际输入取证的累计推理 {report['Flash_seconds_sum']:.2f} 秒。上述加总时间不是 wall time。",
        f"原exit回执记录八卡区间 {interval['seconds']:.2f} 秒，合计 {interval['GPU_seconds']:.2f} GPU·秒；exit写在最终封存和锁关闭之前。另用实际holder的child-exit回执与加锁前快照，将本组八卡保留成本限定在 {report['eight_GPU_seconds_lower_bound']:.2f}–{report['eight_GPU_seconds_upper_bound']:.2f} GPU·秒（{report['eight_GPU_seconds_lower_bound']/3600:.2f}–{report['eight_GPU_seconds_upper_bound']/3600:.2f} GPU·小时），包含最终封存阶段的上界，7张主卡+1张Flash卡全部计入。更早四卡holder和后续空闲保留未计入，不能当全部历次部署总成本，无货币或能耗估计。", '',
        'Flash 固定 revision、固定 YES/NO 提示；每次只有完整单图，无任务、主历史、候选动作、上一帧、上一轮判定或跨调用 KV。主模型完整历史、原 system、seed42、BF16、SDPA、2048 输出和原步骤预算保留。', '',
        '旧帧在当前协议中是之前被 Flash 接受的同一 PNG。固定单图模型没有时间来源证据；它的可用性 YES 不能证明图片来自本次截图。按钮残留也可能被当作可用的稀疏界面。漏放必须保留，不能以 PRIVATE 注入标签强制 NO 或反复重跑同一终局来挑选成功。', '',
        '本组无新 baseline；8 条为两个任务在四种条件下的开发验证，并非总体 Mirage 触发率或显著下降的统计证明。恢复图相同 SHA 的标签仅精确复用，不增加独立图像多样性。审图者已看到 gate 结果，非盲。官方任务成功不等于本轮门控闭环成功。', '',
        '全部实际 wire/输入 IDs、pixels/grid、原始概率、完整主历史、EOS、Controller 请求回复和原生动作、日志与终局 SHA 链通过整组 postexit 审计，已核对本组主/Flash/GUI/launcher 原实际身份退出。报告、审图和审计均没有新增模型或 GUI 调用。', '',
        f'原始整组审计：`{group_root}`；seal `{report["group_audit_seal_sha256"]}`。',
        f'逐轨验收与独立图像审查关联：`{accept_root}`；seal `{report["acceptance_seal_sha256"]}`。',
        '逐条详细回执和原图 SHA 见同目录 report.json。可信采集回执仅为隔离提案，尚未接入或计为真实防御效果。',
    ]
    (final / '四种注入防御真实GUI验证-20261116.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    save(final / 'seal.json', {p.name: sha(p) for p in final.iterdir() if p.is_file()})
    temporary = HERE / ('.four-mode-report-' + str(time.time_ns()))
    temporary.write_text(json.dumps({'root': str(final), 'seal_sha256': sha(final / 'seal.json')}), encoding='utf8')
    temporary.replace(HERE / 'four-mode-report-current.json')
    print(json.dumps({'root': str(final), 'all_four_conditions_two_successes_reached': reached,
                      'per_mode': per_mode, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
