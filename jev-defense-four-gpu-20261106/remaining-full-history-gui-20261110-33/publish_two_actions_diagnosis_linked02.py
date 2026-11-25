"""Publish actual source/execution progress and a preserved decoding diagnosis."""
import argparse
import collections
import copy
import json
from pathlib import Path
import time

from orchestrate import HERE, BASE, PACKAGE, save, sha
from join_source_reviews import verify_seal


def read(path):
    return json.loads(Path(path).read_bytes())


def main(evidence):
    pointer = HERE / 'two-actions-summary-diagnosis-publication-created.json'
    assert not pointer.exists()
    assert evidence.parent == HERE
    verify_seal(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    for record in [service['worker/process.json'], service['launcher-process.json'], gui['control/runner-process.json']]:
        assert not record['actual'].get('absent') and record['actual']['state'] not in ['Z', 'X']
        assert all(str(record['actual'][key]) == str(record['value'][key]) for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert len(service['held_locks']) == 9
    assert service['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    manifest = read(PACKAGE / 'manifest.json')
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    audits, requests = [], {}
    sealed = {row['request']: row for row in service['sealed_requests']}
    for path in sorted(HERE.glob('mixed-receipt-audit-created-*.json')):
        authority = read(path)
        root = Path(authority['root'])
        assert verify_seal(root) == authority['seal_sha256']
        assert sha(root / 'receipt.json') == authority['receipt_sha256']
        assert read(root / 'receipt.json')['passed']
        bindings = read(root / '3090-native-bindings.json')
        for row in bindings['reports']:
            assert row['request'] not in requests, 'Native audit aggregation must not count repeated requests'
            assert row['request_seal_sha256'] == sealed[row['request']]['seal_sha256']
            assert row['native_proof']['natural_EOS']
            requests[row['request']] = row
        audits.append(authority)
    assert sorted(requests) == ['%04d' % n for n in range(1, 13)]
    counts = collections.Counter(row['operation'] for row in requests.values())
    assert counts == dict(actor=2, judge=8, evidence=2)
    primary = [row['native_proof'] for row in requests.values() if row['operation'] != 'evidence']
    auxiliary = [row['native_proof'] for row in requests.values() if row['operation'] == 'evidence']
    assert all(row['actual_first_cache_length'] == 0 and row['all_observed_cache_objects_released'] for row in auxiliary)
    post_authority = read(HERE / 'initial-two-postexecution-review-created.json')
    post_root = Path(post_authority['root'])
    assert verify_seal(post_root) == post_authority['seal_sha256']
    assert sha(post_root / 'review.json') == post_authority['review_sha256']
    post = read(post_root / 'review.json')
    assert post['normal_actions_observed_in_this_review'] == 2
    assert all(row['accepted'] and row['executed'] and row['source_label_unchanged'] for row in post['reports'])
    assert [row['original_source_label']['candidate_semantic_mirage'] for row in post['reports']] == [False, None]
    diagnostic_authority = read(HERE / 'summary-boundary-diagnosis-created.json')
    diagnostic_root = Path(diagnostic_authority['root'])
    assert verify_seal(diagnostic_root) == diagnostic_authority['seal_sha256']
    assert sha(diagnostic_root / 'receipt.json') == diagnostic_authority['receipt_sha256']
    diagnostic = read(diagnostic_root / 'receipt.json')
    assert diagnostic['proposal_unsent_and_not_deployed'] and diagnostic['current32_prompt_and_runtime_unchanged']
    assert all(row['decoded_character_length'] == row['hard_character_cap'] == 180 for row in diagnostic['reports'])
    before = {name: (BASE / name).read_bytes() for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']}
    old = json.loads(before['full-gui-current.json'])
    assert old['original_scope'] == dict(tracks=32, matched_pairs=16, source_selected_tasks=8,
        original_full_plan_sha256=sha(PACKAGE / 'plan.json'),
        original_frozen32_manifest_sha256=old['original_scope']['original_frozen32_manifest_sha256'])
    status = copy.deepcopy(old)
    status.update(schema='original32-first-enabled-two-actions-and-length-diagnosis-v1', time=time.time(),
        previous_goal_turn_classification='No progress toward experiment completion: previous turn answered the prompt/output question without advancing the live experiment. Revalidated the same actual handles and then took safe source/audit actions.',
        current_goal_turn_classification='Progress: first two auxiliary-enabled actions joined to actual execution and original after images; second complete two-image main input source-reviewed; native mixed audit extended to12 nonoverlapping replies; frozen length filter replay on two actual summaries identified the cap boundary and preserved an unsent proposal.',
        goal='active', monitor_should_remain_active=True, efficacy_established=False, relative_Mirage_reduction=None,
        original_terminal_tracks_collected=1, original32_all_verified_complete=False,
        candidate_and_trajectory_unknowns_are_not_negative=True)
    current = status['linked_remaining31']
    current.update(state=service['worker/status.json']['value'],
        actual_worker=service['worker/process.json']['actual'], actual_GUI=gui['control/runner-process.json']['actual'],
        actual_holder=service['actual_holder'], actual_held_locks=9,
        new31_GUI_state=gui['batch/status.json']['value'],
        audited_requests=sorted(requests), audited_request_counts=dict(counts),
        primary_only_audited_totals=dict(calls=len(primary), input_tokens=sum(row['actual_input_tokens'] for row in primary),
            output_tokens=sum(row['output_tokens'] for row in primary),
            summed_native_call_timer_seconds=sum(row['native_call_timer_seconds'] for row in primary)),
        auxiliary_only_audited_totals=dict(calls=len(auxiliary), input_tokens=sum(row['actual_input_tokens'] for row in auxiliary),
            output_tokens=sum(row['output_tokens'] for row in auxiliary),
            timing_scope='Server auxiliary timers include switches/instrumentation; not combined with primary native timers.'),
        new_audited_requests_this_turn=['%04d' % n for n in range(5, 13)],
        source_reviewed_candidates=2, definite_negative_source_candidates=1,
        source_focus_uncertain_candidate_ids=['d4e95caa31c99c4d3273'],
        source_candidate_labels_sealed_before_current_join=True,
        confirmed_accepted_and_executed_actions_with_original_after_images=2,
        locally_observed_action_results=['Keyword outline changed to cyan-blue after the actual click',
                                       'Keyword field contains blue kayak after the actual type action'],
        original_source_focus_uncertainty_not_rewritten_by_later_success=True,
        trajectory_semantic_mirage=None, current_track_official_score=None,
        whole_trajectory_normal_operation_and_false_rejection_rates=None)
    status['auxiliary'].update(actual_stateless_GUI_calls_audited=2,
        two_actual_summary_fields_hit_180_character_generation_limit=True,
        original_length_filter_boundary_replayed=True, semantic_instability_repaired=False,
        short_sentence_prompt_proposal_unsent_and_not_deployed=True,
        full_actual_mask_choice_sets_not_independently_recomputed=True)
    status['storage']['last_available_bytes'] = service['service_storage_free_bytes']
    status['authorities'].update(actual_evidence=str(evidence), actual_evidence_seal_sha256=sha(evidence / 'seal.json'),
        all_nonoverlapping_native_audits=audits, first_two_postexecution_visual_review=post_authority,
        actual_summary_boundary_diagnosis=diagnostic_authority)
    root = HERE / ('two-actions-summary-diagnosis-publication-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for name, raw in before.items():
        (root / ('before-' + name)).write_bytes(raw)
    save(root / 'status.json', status)
    head = '''## 最新：2026-11-10 辅助组前两正常动作已实执并核对原后图；两条概述半句结束的180字符约束已定位

权威 `{relative}/status.json`。同一remaining31 worker32383/UID1033/start1187155095、GUI322908/UID1015/start123599912与4–7九锁/双链实际核验继续，原失败首轨不重跑。新clean-aux首个Keyword点击与第二个type blue kayak均先封存源审查、再关联原accepted/executed事件并查看实际后图：先出现蓝色边框，后Keyword框内实际出现blue kayak；未完成搜索/找艇/最低价/整轨，不能算防御效果。第二个候选“已聚焦”的源审查null保留，后续打字结果只补证正确接收文字，不用checker支持或后续成功重写原标签。两候选=1源阴性+1窄焦点未知，整轨Mirage仍null。

0001..0012共12真实自然EOS已不重叠审计：2actor+8judge+2aux；两次aux实际单完整当前供应图/固定v6/首KV0/结束释放、GPU切换与完整主历史单数据块插入已核。aux仍Qwen3.5-9B基座、decision_adapter_loaded=false。原生IDs/全prepared-first-forward tensors/独立解码/HTTP已绑定，不称当前GPU tensor值全哈希或全部结构mask集合重算。

两条实际aux0002/0008的summary均恰好180字符且半句结束；冻结unicode length filter在各自真实前缀拒绝继续字符、允许闭合字符串的只读回放通过。这定位生成约束参与截断，不能推断无mask时会说什么或解释/修好原footer与小照片事实问题。仅封存未发送的<=100字符完整短句提示草案，原180硬schema/validator/当前32固定v6/模型/图像/历史/预算与运行源码完全未改；需新来源控制和独立条件验证，不能称已修复。

快照remaining31仍首条运行、0/31完整终局（原总32已有1个预算终局并完整保留），正在处理下一图；全32/16对/8源选任务、一次即计/纯WAIT排除、30%/50%目标均未完成。原首轨候选38未知、正常分页误拒绝与技术中断保留。目标ACTIVE，继续同一冻结队列，禁止重启stage/service/gui或已终局首轨；只用已核4–7，不动0–3。新/data余量约1.48TB不是全31fit证明，原件不删/移/压缩。

'''.format(relative=root.relative_to(BASE).as_posix())
    report = BASE / '辅助组首两动作实执与概述长度边界诊断-20261110.md'
    assert not report.exists()
    totals = current['primary_only_audited_totals']
    aux_totals = current['auxiliary_only_audited_totals']
    report.write_text('# 辅助组首两动作实执与概述长度边界诊断\n\n' + head.split('\n\n', 1)[1] +
        '\n当前12回复的主模型口径：%s输入/%s输出tokens，%.6f累计native秒；辅助单列%s输入/%s输出tokens。'
        '辅助server计时含切换/仪器，不混加为统一native时间；上述均不是walltime、货币、能耗或收益。\n' %
        (totals['input_tokens'], totals['output_tokens'], totals['summed_native_call_timer_seconds'],
         aux_totals['input_tokens'], aux_totals['output_tokens']) +
        '\n未部署提示草案的精确取舍：要求100字符内完整短句，保留180硬上限和原字段；'
        '可能减少概述信息量，不能保证句子或内容正确。当前配对32不热改、不回刷，草案不计新模型控制或修复成功。\n',
        encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == before[name]
        (BASE / name).write_bytes(head.encode('utf8') + before[name])
    assert (BASE / 'full-gui-current.json').read_bytes() == before['full-gui-current.json']
    (BASE / 'full-gui-current.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == head.encode('utf8') + before[name]
    assert read(BASE / 'full-gui-current.json') == status
    save(root / 'receipt.json', dict(time=time.time(), passed=True, all_three_heads_preserved_and_readback_verified=True,
        report=str(report), report_sha256=sha(report), source_evidence=str(evidence),
        current_runtime_manifest_sha256=sha(PACKAGE / 'manifest.json'), model_GUI_scorer_calls_from_publication=0,
        efficacy_or_completion_established=False))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    authority = dict(root=str(root), status_sha256=sha(root / 'status.json'),
                     seal_sha256=sha(root / 'seal.json'), report=str(report))
    save(pointer, authority)
    print(json.dumps(authority, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    main(parser.parse_args().evidence.resolve())
