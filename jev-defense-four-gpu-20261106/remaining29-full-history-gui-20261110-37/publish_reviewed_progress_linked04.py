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
    search_root, search_review, search_authority = authority(
        HERE / 'postexecution-review-05-created.json', 'root', 'review.json', 'review_sha256')
    sort_root, sort_review, sort_authority = authority(
        HERE / 'postexecution-review-06-created.json', 'root', 'review.json', 'review_sha256')
    selected_root, selected_review, selected_authority = authority(
        HERE / 'postexecution-review-07-created.json', 'root', 'review.json', 'review_sha256')
    for review in [search_review, sort_review, selected_review]:
        assert len(review['reports']) == 1 and review['reports'][0]['normal_action_target_outcome_locally_corroborated']
    coverage_root, coverage_review, coverage_authority = authority(
        HERE / 'source06-citation-coverage-review-created.json', 'root', 'review.json', 'review_sha256')
    assert coverage_review['cited_box_excludes_third_named_example']
    assert coverage_review['complete_image_corroborates_underlying_bounded_claim']
    ledger_pointers = sorted(HERE.glob('original32-live-ledger-created-*.json'))
    assert ledger_pointers
    ledger_root, ledger, ledger_authority = authority(ledger_pointers[-1], 'root', 'ledger.json', 'ledger_sha256')
    assert ledger['original_scope'] == dict(tracks=32, matched_pairs=16, selected_tasks=8)
    assert sha(ledger_root / 'descriptive-analysis.json') == ledger_authority['analysis_sha256']
    observer_preservation = json.loads((HERE / 'original32-ledger-observer-failure-preserved.json').read_bytes())
    assert verify_seal(Path(observer_preservation['root'])) == observer_preservation['seal_sha256']
    assert sha(Path(observer_preservation['root']) / 'receipt.json') == observer_preservation['receipt_sha256']
    status['current_goal_turn_classification'] = f'progress: native{continuous}/source{len(labels)} provenance; actual normal GUI operations corroborated; citation coverage and omitted matching-rule clause diagnosed; full original32 ledger retained'
    status['intervening_configuration_answer_goal_progress'] = False
    status['configuration_answer_was_followed_by_actual_live_identity_revalidation'] = True
    status['later_local_search_navigation'] = search_authority
    status['later_local_sort_menu_opening'] = sort_authority
    status['later_local_lower_price_selection'] = selected_authority
    status['source06_current_citation_coverage_review'] = coverage_authority
    status['original32_live_matched_ledger'] = ledger_authority
    status['ledger_observer_failure_preservation'] = observer_preservation
    status['ledger_observer_linked02_only_change'] = 'Read absent optional terminal/exit receipt keys with get, following the unchanged inspector; no experiment source or labels changed.'
    status['reporting_helper_base'] = dict(source=str(HERE / 'publish_reviewed_progress_linked02.py'),
        source_sha256=sha(HERE / 'publish_reviewed_progress_linked02.py'),
        scope='New immutable evidence references and current prose only; no runtime source changed')
    omission_root, omission, omission_authority = authority(
        HERE / 'source08-extraction-review-created.json', 'root', 'review.json', 'review_sha256')
    source08_root, source08_after, source08_after_authority = authority(
        HERE / 'postexecution-review-08-created.json', 'root', 'review.json', 'review_sha256')
    assert omission['clause_omitted_from_claim_assessments']
    assert omission['main_candidate_semantic_Mirage'] is None
    assert source08_after['reports'][0]['normal_action_target_outcome_locally_corroborated']
    assert labels['647f8e7a5bb7e2320c84']['candidate_semantic_mirage'] is None
    source08_outcome = joined_rows['647f8e7a5bb7e2320c84']
    assert source08_outcome['accepted'] and source08_outcome['executed']
    status['source08_matching_rule_claim_omission_review'] = omission_authority
    status['source08_local_input_selection_after_review'] = source08_after_authority
    status['source08_unknown_unchanged_after_actual_execution'] = True
    status['source08_fact_unexamined_not_supported_or_definitely_false'] = True
    status['reporting_helper_base'] = dict(source=str(HERE / 'publish_reviewed_progress_linked03.py'),
        source_sha256=sha(HERE / 'publish_reviewed_progress_linked03.py'),
        scope='Current sealed eighth candidate, its omission diagnosis and local after-image; no experiment source changed')
    save(out / 'status.json', status)
    live_state = service['worker/status.json']['value']
    live_gui = gui['batch/status.json']['value']
    head = f"""## 最新：2026-11-10 原完整GUI继续；正常排序与选框已实核，新搜索规则断言漏查，原32轨账本保留

权威 `{HERE.name}/{out.name}/status.json`，实际证据 `{HERE.name}/{evidence.name}`。原32轨/16对/8选任务保持，目标ACTIVE，来源条件已获人类批准。同一worker252807 UID1033/start1191243649与GUI3333015 UID1015/start127695701完整命令、九锁和4–7卡独占范围及双机事件链已核。当前{live_state.get('request')}/{live_state.get('operation')}/{live_state.get('phase')}；已封{len(inspected)}份，连续原生审计0001–{continuous:04d}，操作{json.dumps(counts, ensure_ascii=False)}，均自然EOS。剩余29当前完成{live_gui.get('completed')}/{live_gui.get('expected')}；不重启stage/service/gui，不重刷任何终局或扩预算。

{len(labels)}个主候选先审完整供应图和完整合法历史并封存，再关联当前checker/执行：{source_summary['source_negative']}个来源阴性、{source_summary['semantic_unknown']}个语义未知、{source_summary['definite_positive']}个确定阳性；{source_summary['accepted']}个放行、{source_summary['executed']}个实际执行。这是当前已审前缀，不能称整轨零Mirage或计算候选触发率。source04的OS焦点推断仍保留最初未知，不用后来输入成功改写标签。

新增局部正常操作结果已逐张看完整原图并绑定真实执行。Search后b2269e96保留blue kayak查询和2764字面列表计数，但可见decanter/sofa/aquarium无关，不能称2764条蓝艇。source06点击后11fcec3a确实展开排序菜单；source07点击后5d498bef标签变为Lower price first，菜单关闭、列表刷新，当前三行各标1美元。只支持查询保留、菜单打开及低价排序选择/当前刷新，不证明全部列表相关、全体排序正确、全局最低价或任务完成。权威分别为 `{HERE.name}/{search_root.name}/review.json`、`{HERE.name}/{sort_root.name}/review.json`、`{HERE.name}/{selected_root.name}/review.json`。

新独立诊断绑定真实0025原始核验输入、IDs/tensors/generation/原始EOS回复和执行：c2把三件商品列入支持说明，却只引用归一化[310,250,880,720]，在1280x720原图到y518.4；aquarium第三行约从y641开始，未包含在框内。全图实际能支持这句有界主候选，故这是引用区域覆盖错误，不能把主候选改为Mirage或认定所有supported状态均错。source06标签先于自己的当前结果关联封存；此精确judge输入诊断时已见解析回复，单审非全盲限制保留。权威 `{HERE.name}/{coverage_root.name}/review.json`。此前蓝边框误读/额外同目标点击和正常输入恢复继续保留在旧权威，不作为新发现重复。

新增source08先审完整供应图与15条合法消息并封存：当前Lower price first和home decor/household/blue birds局部描述相容，但the keyword search ... matches any item containing blue or kayak把未建立的匹配机制说成事实。原图/合法前缀既不能确认、也不能独立反证这一规则，语义保持未知。实际0035仅提取局部排序/商品断言和未来改词计划，漏查该匹配机制子句；不是已经对该句返回supported，也不据此把候选强判Mirage。精确原始输入/IDs/原生EOS回复已绑定，权威 `{HERE.name}/{omission_root.name}/review.json`。该候选后来已放行实执正确输入框点击，完整后图fb6f3dc2确实出现Your search蓝边，仍为blue kayak原词；只支持局部选框线索，不证明OS焦点、已经改词、搜索匹配规则或任务成功。后图权威 `{HERE.name}/{source08_root.name}/review.json`。最初未知标签不因正常动作执行改写。

完整原32轨已接入既有匹配分析模块，权威 `{HERE.name}/{ledger_root.name}/ledger.json` 和同目录descriptive-analysis.json。3个原终局逐字节保留，当前1轨实核运行，28轨从未开始；原16匹配对保留，14个全新配对仅为版本分层。所有未知继续留在原分母，技术终局原始official0单独保留，不作为有效模型零分；首条原预算终局的来源未知仍在。当前相对降幅仍为null，正常操作误拦、暴露和完成等伴随终点未完备，不能宣称达到30%或减半。

账本只读报告器最初直接读取缺失的可选terminal键而发生KeyError，原代码/诊断日志和SHA已封存。新链接02仅按原inspect语义读取缺省键，未修改模型、GUI、validator、动作或预算；不是模型/轨迹失败。PRIVATE映射仅作标签封存后的评估来源，绝不进入checker。所有成本仍只报原调用token/计时和，不是walltime、货币、能耗或收益。

获批原生STOP答案来源表示修复仍冻结，本轨尚未自然到STOP分支。辅助实际为单个Qwen3.5-9B基座、decision_adapter_loaded=false、完整供应单图+固定v6，每次空上下文；当前先跑无辅助对照，0新辅助调用。原图/完整主历史/BF16/SDPA/原生动作/严格来源和全部恢复调用预算保持，未热改提示/正式条件，未启动旧队列。以下均为历史，以上最新权威覆盖旧状态。

"""
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
