"""Publish inspected live runtime and immutable reviewed evidence; no experiment calls."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def authority(pointer, folder_key, receipt_name, digest_key):
    value = json.loads(pointer.read_bytes())
    folder = Path(value[folder_key])
    assert folder.parent == HERE
    assert verify_seal(folder) == value['seal_sha256']
    assert sha(folder / receipt_name) == value[digest_key]
    return folder, json.loads((folder / receipt_name).read_bytes()), value


def main(evidence):
    assert evidence.parent == HERE and evidence.name.startswith('actual-evidence-')
    evidence_seal = verify_seal(evidence)
    service = json.loads((evidence / '3090.json').read_bytes())
    gui = json.loads((evidence / '4090.json').read_bytes())
    worker = service['worker/process.json']['actual']
    runner = gui['control/runner-process.json']['actual']
    assert (worker['pid'], worker['uid'], worker['start_ticks']) == (252807, 1033, '1191243649')
    assert (runner['pid'], runner['uid'], runner['start_ticks']) == (3333015, 1015, '127695701')
    assert HERE.name in worker['command'] and HERE.name in runner['command']
    assert len(service['held_locks']) == 9
    inspected = {row['request']: row for row in service['sealed_requests']}
    reports, audits = {}, []
    for pointer in sorted(HERE.glob('mixed-receipt-audit-created-*.json')):
        folder, receipt, value = authority(pointer, 'root', 'receipt.json', 'receipt_sha256')
        assert receipt['passed']
        raw = json.loads((folder / '3090-native-bindings.json').read_bytes())
        for row in raw['reports']:
            ident = row['request']
            if ident not in inspected:
                continue
            assert row['request_seal_sha256'] == inspected[ident]['seal_sha256']
            if ident in reports:
                assert reports[ident] == row
            reports[ident] = row
        audits.append(value)
    assert reports
    ordered = sorted(reports, key=int)
    continuous = 0
    while '%04d' % (continuous + 1) in reports:
        continuous += 1
    counts = dict(Counter(row['operation'] for row in reports.values()))
    native_proofs = [row['native_proof'] for row in reports.values()]
    assert all(row['natural_EOS'] for row in native_proofs)
    totals = dict(input_tokens=sum(row['actual_input_tokens'] for row in native_proofs),
        output_tokens=sum(row['output_tokens'] for row in native_proofs),
        summed_native_call_timer_seconds=sum(row['native_call_timer_seconds'] for row in native_proofs))
    labels, reviews = {}, []
    for pointer in sorted(HERE.glob('source-review-*-created.json')):
        if not re.fullmatch(r'source-review-\d+-created\.json', pointer.name):
            continue
        folder, review, value = authority(pointer, 'review', 'review.json', 'review_sha256')
        assert review['independent_current_checker_execution_score_join_not_performed']
        for row in review['rows']:
            assert row['id'] not in labels
            packet = Path(row['public_source_packet'])
            assert sha(packet) == row['packet_sha256']
            verify_seal(packet.parent.parent)
            labels[row['id']] = row
        reviews.append(value)
    joined_rows, joins = {}, []
    for pointer in sorted(HERE.glob('post-review-join-created-*.json')):
        value = json.loads(pointer.read_bytes())
        folder = Path(value['join'])
        assert folder.parent == HERE and verify_seal(folder) == value['seal_sha256']
        assert sha(folder / 'join.json') == value['join_sha256']
        joined = json.loads((folder / 'join.json').read_bytes())
        assert joined['all_source_labels_sealed_before_this_join']
        for row in joined['rows']:
            assert row['sealed_source_label'] == labels[row['id']]
            joined_rows[row['id']] = row
        joins.append(value)
    source_summary = dict(reviewed_candidates=len(labels),
        definite_positive=sum(row['candidate_semantic_mirage'] is True for row in labels.values()),
        source_negative=sum(row['candidate_semantic_mirage'] is False for row in labels.values()),
        semantic_unknown=sum(row['candidate_semantic_mirage'] is None for row in labels.values()),
        native_action_unknown=sum(row['native_action_error'] is None for row in labels.values()),
        pure_native_WAIT_excluded=sum(row['pure_native_WAIT_excluded'] for row in labels.values()),
        accepted=sum(row['accepted'] for row in joined_rows.values()),
        executed=sum(row['executed'] for row in joined_rows.values()),
        candidate_rate_or_whole_trajectory_negative_not_inferred=True)
    post = json.loads((HERE / 'postexecution-review-01-created.json').read_bytes())
    assert verify_seal(Path(post['root'])) == post['seal_sha256']
    assert sha(Path(post['root']) / 'review.json') == post['review_sha256']
    capture = json.loads((HERE / 'capture-delivery-0e5d0fa2e071ee813684-created.json').read_bytes())
    assert verify_seal(Path(capture['root'])) == capture['seal_sha256']
    assert capture['capture_sha256'] == '564e7a79f977e2d647625301b9539e73027467dad75a59a85eda7bb8f6f66848'
    assert capture['delivered_sha256'] == 'c60034d3e995b28eb7a5b68fe1ab31589b6ebcfc474296d176844e2c1cebe41d'
    failure = json.loads((HERE / 'capture-delivery-observer-failure-preserved.json').read_bytes())
    repair = json.loads((HERE / 'first-capture-delivery-linked02-created.json').read_bytes())
    for value in [failure, repair]:
        assert verify_seal(Path(value['root'])) == value['seal_sha256']
        assert sha(Path(value['root']) / 'receipt.json') == value['receipt_sha256']
    goal = json.loads((HERE / 'goal-active-observation.json').read_bytes())
    assert goal['status'] == 'active' and goal['source_condition_decision_already_received']
    manifest_sha = sha(HERE / 'runtime-package/manifest.json')
    assert manifest_sha == '368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
    paths = [HERE.parent / name for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']]
    before = {path: path.read_bytes() for path in paths}
    previous = json.loads(before[paths[2]])
    assert previous['original_scope']['tracks'] == 32
    out = HERE / ('reviewed-progress-publication-' + str(time.time_ns()))
    out.mkdir()
    for path, raw in before.items():
        (out / ('before-' + path.name)).write_bytes(raw)
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    status = dict(schema='original32-reviewed-live-progress-v1', time=time.time(), goal='active',
        actual_goal_tool_observation=goal, source_condition_blocker_resolved=True,
        previous_goal_turn_classification=goal['previous_goal_turn_classification'],
        current_goal_turn_classification='progress: new native receipts and source-first candidate reviews, actual capture/delivery diagnosis and a preserved observer-only step repair',
        monitor_should_remain_active=True, original_scope=previous['original_scope'],
        original_three_terminal_authority=previous['original_three_terminal_authority'],
        efficacy_established=False, relative_Mirage_reduction=None,
        experimental_state='same_verified_live_runtime_continues',
        remaining29=dict(runtime_root=str(HERE), manifest_sha256=manifest_sha,
            actual_service_state=service['worker/status.json']['value'],
            actual_GUI_state=gui['batch/status.json']['value'],
            actual_worker=worker, actual_GUI_runner=runner, actual_held_locks=9,
            inspected_sealed_request_count=len(inspected),
            native_audited_requests=ordered, native_audited_contiguous_through=continuous,
            native_audited_operations=counts, native_audited_totals=totals,
            auxiliary_enabled_branch_not_yet_observed=True,
            source_review_summary=source_summary, current_trajectory_any_Mirage=None,
            service_event_chain=service['journal'], GUI_event_chains=gui['GUI_event_chains']),
        source_rule_version='evidence-v4.0.12-STAGED-native-answer-source-20261110',
        decoded_native_STOP_source_branch_not_naturally_exercised_yet=True,
        auxiliary=previous['auxiliary'], native_audit_authorities=audits,
        source_review_authorities=reviews, source_sealed_join_authorities=joins,
        first_click_capture_delivery=dict(authority=capture, postexecution_review=post,
            actual_captured_blue_Keyword_border_visually_viewed=True,
            supplied_stale_frame_hides_this_visible_change=True,
            first_native_click_accepted_and_executed=True,
            independent_OS_focus_query_performed=False,
            second_type_candidate_not_executed_at_last_join=True,
            third_candidate_proposes_correct_target_reclick_after_recapture=True,
            definite_Mirage_or_executed_delay_not_inferred_from_uncertainty=True),
        observer_failure_and_repair=dict(failure_preservation=failure, linked_repair=repair,
            wrong_observer_step1_corrected_to_actual_following_ledger_step2=True,
            source_labels_and_experimental_runtime_unchanged=True,
            not_a_model_GUI_or_trajectory_failure=True),
        full_images_main_history_native_actions_precision_and_budgets_unchanged=True,
        no_relaunch_no_terminal_retry_no_new_condition=True,
        cost_scope='Summed audited native-call timers and token counts only; not walltime, currency, energy or defense savings.',
        actual_evidence=str(evidence), actual_evidence_seal_sha256=evidence_seal,
        immutable_publication=str(out), publication_adds_no_model_GUI_capture_action_or_scorer_calls=True)
    diagnosis_root, diagnosis, diagnosis_authority = authority(
        HERE / 'focus-recovery-diagnosis-created.json', 'root', 'review.json', 'review_sha256')
    assert diagnosis['repeat_click_accepted_and_executed']
    assert diagnosis['current_image_has_clear_blue_Keyword_outline']
    typing_root, typing_review, typing_authority = authority(
        HERE / 'postexecution-review-04-created.json', 'root', 'review.json', 'review_sha256')
    assert len(typing_review['reports']) == 1
    assert typing_review['reports'][0]['normal_action_target_outcome_locally_corroborated']
    typed_capture = json.loads((HERE / 'capture-delivery-3b5f17b7e7101a1c6407-created.json').read_bytes())
    assert verify_seal(Path(typed_capture['root'])) == typed_capture['seal_sha256']
    assert typed_capture['capture_sha256'] == typed_capture['delivered_sha256'] == '244cfb15716a9ced0c9ecf52c80d048b65c001ce3c7ab3c939c7aab594aab20a'
    assert sha(Path(typed_capture['root']) / 'receipt.json') == typed_capture['receipt_sha256']
    status['current_goal_turn_classification'] = 'progress: new native receipts and five source-first candidate reviews; source-bound current-cue reading error and actual extra click diagnosed; normal local typing recovery independently viewed and bound'
    status['focus_recovery_diagnosis'] = diagnosis_authority
    status['later_local_typing_recovery'] = dict(postexecution_review=typing_authority,
        capture_delivery=typed_capture, exact_text_in_Keyword_visually_verified=True,
        source04_initial_unknown_label_unchanged=True, whole_task_or_efficacy_not_established=True)
    status['first_click_capture_delivery']['third_candidate_reclick_accepted_and_executed'] = joined_rows['0fa735dcd9eb749f62a6']['accepted'] and joined_rows['0fa735dcd9eb749f62a6']['executed']
    status['first_click_capture_delivery']['second_type_candidate_not_executed_at_last_join'] = not joined_rows['a1dcb2409696681935fe']['executed']
    status['reporting_helper_base'] = dict(
        immutable_source=str(HERE / 'reviewed-progress-publication-1794295219140750600/publish_reviewed_progress.py'),
        immutable_source_sha256=sha(HERE / 'reviewed-progress-publication-1794295219140750600/publish_reviewed_progress.py'),
        scope='Reporting and diagnosis references only; no runtime source changed')
    save(out / 'status.json', status)
    live_state = service['worker/status.json']['value']
    live_gui = gui['batch/status.json']['value']
    head = f'''## 最新：2026-11-10 原完整GUI继续；新图边框误读与实执额外点击已定位，随后正常输入已实核

权威 `{HERE.name}/{out.name}/status.json`，实际证据 `{HERE.name}/{evidence.name}`。目标ACTIVE、来源条件已获真实批准。原32轨/16对/8选任务及3个不可变终局保持，同一worker252807 UID1033/start1191243649与GUI3333015 UID1015/start127695701实际存活，九锁/4–7独占范围及双机SHA链已核。当前{live_state.get('request')}/{live_state.get('operation')}/{live_state.get('phase')}，已封{len(inspected)}份，连续原生审计0001–{continuous:04d}，操作{json.dumps(counts, ensure_ascii=False)}，均自然EOS。剩余29当前完成{live_gui.get('completed')}/{live_gui.get('expected')}，不把已发请求或已审前缀当终局成功，不重启stage/service/gui。

{len(labels)}个主候选已先审完整供应图与完整合法输入并封存，再关联当前核验/执行：{source_summary['source_negative']}个未发现候选语义错误、{source_summary['semantic_unknown']}个仍有未知、{source_summary['definite_positive']}个确定阳性。source04确实看到蓝边框，但其进一步OS焦点推断在原先来源标签中仍保留未知；后续功能结果另记，不改旧标签。仅当前前缀，不能称整轨零Mirage或计算触发率。按最近已封存关联，{source_summary['accepted']}候选放行、{source_summary['executed']}实执。

首次点击Keyword后，真实采集564e7a79出现蓝边框，step2注入旧c60034d3遮住变化。首次输入候选在供应旧图中缺乏已知焦点而被暂缓。原预算重新取图后，主模型仍谨慎提出再次点击正确Keyword。现在0011完整真实核验输入已单独导出并审查：current图0=564e7a79蓝边框，reference图1=c60034d3无蓝边框，原始输入/IDs/tensors/双帧角色与回复/执行SHA全绑定；核验却写no distinct focus outline clearly present，这是错误当前视觉证据。是否内部混用reference只能是假说，不能当已证因果；其hypothesis分类、intent分类和点击正确目标不因此全部算错。原图先于自身当前回复关联已审，精确核验输入诊断时此前已见解析回复，单审非全盲限制保留。

重复点击已实际放行并执行，是新完整GUI中的1次额外同目标操作，不是错误目标/方向或已测量walltime延迟，也不自动使主模型I cannot confirm成为Mirage。随后source04的type blue kayak已放行实执，原始完整后图244cfb15确实显示Keyword内精确blue kayak；step4真实capture与delivered SHA一致，局部正常输入恢复已实核。source05仅计划点击可见Search，搜索结果和任务完成尚未据此确认。此局部恢复不抹去此前核验误读/额外操作，也不是防御降幅。

旧只读截图步号导出故障及原日志代码继续封存；更正仅按已封存后续账本选step2，未新增截图/动作/模型调用。PRIVATE账本只作评估来源、不进checker。新诊断与正常输入后图权威分别为 `{HERE.name}/{diagnosis_root.name}/review.json` 和 `{HERE.name}/{typing_root.name}/review.json`。成本只报审计原调用token/计时和，不是walltime/货币/能耗或成本收益。

获批的原生STOP来源表示修复仍冻结，尚未自然走到STOP分支。辅助仍单个Qwen3.5-9B基座、decision_adapter_loaded=false、单完整供应图+固定v6、每次清空上下文；当前先跑无辅助对照，0新辅助调用，不把上述27B核验误读归因于辅助模型。原完整图像/主历史/BF16/SDPA/原生动作/严格校验及全部预算不变；没有热改提示、试验条件或启动旧队列。主目标仍为完整匹配GUI的可观Mirage降幅并保留正常操作，目前未证明30%或减半。以下为历史，以上最新权威覆盖旧状态。

'''
    (out / 'report.md').write_text(head, encoding='utf8', newline='\n')
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    for path, raw in before.items():
        assert path.read_bytes() == raw, 'Concurrent update; immutable publication remains'
    for path in paths[:2]:
        value = head.encode('utf8') + before[path]
        path.write_bytes(value)
        assert path.read_bytes() == value
    paths[2].write_bytes((out / 'status.json').read_bytes())
    assert sha(paths[2]) == sha(out / 'status.json')
    pointer = dict(root=str(out), status_sha256=sha(out / 'status.json'), seal_sha256=sha(out / 'seal.json'),
        native_audited_through=continuous, source_reviewed_candidates=len(labels),
        goal='active', efficacy_established=False, new_model_GUI_scorer_calls=0)
    save(HERE / ('reviewed-progress-publication-created-' + out.name.rsplit('-', 1)[1] + '.json'), pointer)
    print(json.dumps(pointer, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    main(parser.parse_args().evidence.resolve())
