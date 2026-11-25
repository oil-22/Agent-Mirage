"""Downstream companion outcomes; no new model/GUI calls or primary labels."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import time

from collect_four_terminal_once import HERE, BASE, R37, save, sha


def seal(folder, expected=None):
    value = sha(folder / 'seal.json')
    if expected is not None:
        assert value == expected
    for name, digest in json.loads((folder / 'seal.json').read_bytes()).items():
        target = folder / name
        assert target.resolve().is_relative_to(folder.resolve())
        assert sha(target) == digest, str(target)
    return value


def canonical(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def main():
    assert not (HERE / 'companion-panel-created.json').exists()
    pointer = json.loads((HERE / 'four-terminal-collected.json').read_bytes())
    root = Path(pointer['root'])
    seal(root, pointer['seal_sha256'])
    inventory = Path(pointer['source_inventory'])
    assert sha(inventory) == pointer['source_inventory_sha256']
    evidence = root / 'actual-terminal-event-evidence.json'
    assert sha(evidence) == pointer['event_evidence_sha256']
    source = {row['candidate_event_sha256']: row for row in json.loads(inventory.read_bytes())['rows']}
    data = json.loads(evidence.read_bytes())
    observations = {row['candidate_event_sha256']: row for row in data['rows']}
    assert len(source) == len(observations) == 84 and set(source) == set(observations)
    chainmap = {chain['attempt']: chain for chain in data['chains']}
    assert len(chainmap) == 6
    originals = {event['sha256'] for chain in chainmap.values() for event in chain['retained_events'] if event['kind'] == 'candidate'}
    assert originals == set(source), 'Every original candidate must have a previously sealed source label'
    byhash = {event['sha256']: (chain['attempt'], event)
              for chain in chainmap.values() for event in chain['retained_events']}

    cross = {}
    p11 = json.loads((HERE / 'pending11-collected.json').read_bytes())
    f11 = Path(p11['root'])
    seal(f11, p11['seal_sha256'])
    assert sha(f11 / 'join.json') == p11['join_sha256']
    j11 = json.loads((f11 / 'join.json').read_bytes())
    e11 = json.loads((f11 / 'execution-evidence.json').read_bytes())
    assert sha(f11 / 'execution-evidence.json') == j11['execution_evidence_sha256']
    id11 = j11['candidate_event_sha256']
    assert j11['source_label'] == source[id11]['original_label']
    assert j11['exact_original_full_actor_body_sha256'] == source[id11]['actor_request_body_sha256']
    cross[id11] = dict(accepted=e11['accepted_event'], executed=e11['execution_event'],
        authority=str(f11 / 'join.json'), authority_sha256=sha(f11 / 'join.json'),
        original_body_sha256=j11['exact_original_full_actor_body_sha256'], original_ordinal=11)

    r32 = BASE / 'prefill-scheduled-full-history-gui-20261109-32'
    p17 = json.loads((r32 / 'pending17-execution-join-created.json').read_bytes())
    f17 = Path(p17['join']).parent
    seal(f17, p17['seal_sha256'])
    assert sha(f17 / 'join.json') == p17['join_sha256']
    j17 = json.loads((f17 / 'join.json').read_bytes())
    assert sha(f17 / 'execution-evidence.json') == j17['evidence_sha256']
    e17 = json.loads((f17 / 'execution-evidence.json').read_bytes())
    id17 = j17['source_label']['candidate_event_sha256']
    assert j17['source_label'] == source[id17]['original_label']
    checkpoint = r32 / 'runtime-package/carryover/checkpoint/0020/payload.json'
    body = json.loads(checkpoint.read_bytes())['body']
    bodysha = hashlib.sha256(canonical(body)).hexdigest()
    assert bodysha == source[id17]['actor_request_body_sha256']
    assert e17['cached_candidate_event']['data']['text'] == source[id17]['candidate_text']
    cross[id17] = dict(accepted=e17['accepted_event'], executed=e17['execution_event'],
        authority=str(f17 / 'join.json'), authority_sha256=sha(f17 / 'join.json'),
        original_body_sha256=bodysha, original_ordinal=17,
        extra_body_binding_checkpoint=str(checkpoint), extra_body_binding_checkpoint_file_sha256=sha(checkpoint))
    assert len(cross) == 2
    for item in cross.values():
        for key in ['accepted', 'executed']:
            actual_attempt, actual_event = byhash[item[key]['sha256']]
            assert actual_event == item[key]
            item['linked_attempt'] = actual_attempt

    rows = []
    accepted_hashes, executed_hashes = set(), set()
    for eventid, source_row in source.items():
        observed = observations[eventid]
        accepted = list(observed['accepted_events'])
        executed = list(observed['executed_events'])
        provenance = 'original_namespace'
        if eventid in cross:
            assert not accepted and not executed
            accepted = [cross[eventid]['accepted']]
            executed = [cross[eventid]['executed']]
            provenance = 'source_exact_first_execution_in_linked_namespace'
        assert len(accepted) <= 1 and len(executed) <= 1
        if accepted:
            assert accepted[0]['data']['candidate'] == source_row['candidate_text']
            assert accepted[0]['sha256'] not in accepted_hashes
            accepted_hashes.add(accepted[0]['sha256'])
        if executed:
            assert accepted
            assert executed[0]['data']['observation_id'] == accepted[0]['data']['observation_id']
            assert executed[0]['data']['proposal'] == accepted[0]['data']['proposal']
            assert executed[0]['sha256'] not in executed_hashes
            executed_hashes.add(executed[0]['sha256'])
        row = dict(source_row, accepted=bool(accepted), environment_executed=bool(executed),
            original_namespace_accepted=observed['original_namespace_accepted'],
            original_namespace_executed=observed['original_namespace_executed'],
            accepted_events=accepted, executed_events=executed, acceptance_execution_provenance=provenance,
            cross_namespace_binding=cross.get(eventid),
            candidate_window_block_events=observed['candidate_window_blocks'],
            detector_events_not_semantic_gold=observed['detector_verdicts_not_gold'],
            execution_implies_desired_GUI_result=False,
            original_semantic_label_unchanged=True,
            false_block_not_inferred_from_negative_source_label_and_nonacceptance=True)
        row['accepted_without_environment_action'] = bool(accepted and not executed)
        if row['accepted_without_environment_action']:
            assert accepted[0]['data']['proposal']['name'] == 'stop'
        rows.append(row)
    all_exec = {event['sha256'] for _, event in byhash.values() if event['kind'] == 'action_executed'}
    all_accept = {event['sha256'] for _, event in byhash.values()
                  if event['kind'] in ['decision_accepted', 'carryover_replay_decision_accepted']}
    assert executed_hashes == all_exec and len(all_exec) == 74
    assert accepted_hashes == all_accept and len(all_accept) == 75

    ledger_root = R37 / 'original32-postexit-ledger-1794306065792235500'
    seal(ledger_root, 'a285a08d019b10297cab7f7c9c45a4ed3aa5866ef6536bba0aa464adbba8c98e')
    assert sha(ledger_root / 'ledger.json') == 'b079d93b3dd131905dbbe914f48b0d235e161fc378978df680ef6a4856f6a1bb'
    ledger = json.loads((ledger_root / 'ledger.json').read_bytes())
    summaries = []
    for terminal in ledger['rows']:
        if terminal['run_id'] not in {row['run_id'] for row in rows}:
            continue
        group = [row for row in rows if row['run_id'] == terminal['run_id']]
        originals = [chain for chain in chainmap.values() if Path(chain['attempt']).parent.name == terminal['run_id']]
        actual = [t for chain in originals for t in chain['terminals'] if t['sha256'] == terminal['terminal_receipt']['sha256']]
        assert len(actual) == 1, 'The actual logical endpoint must match the original sealed terminal SHA'
        terminal_actions = actual[0]['value']['environment_actions']
        assert sum(row['environment_executed'] for row in group) == terminal_actions == terminal['environment_actions']
        assert len(group) == terminal['source_reviewed_candidates']
        positive = [row for row in group if row['primary_semantic_label'] is True and not row['pure_native_WAIT_excluded']]
        unknown = [row for row in group if row['primary_semantic_label'] is None and not row['pure_native_WAIT_excluded']]
        negative = [row for row in group if row['primary_semantic_label'] is False and not row['pure_native_WAIT_excluded']]
        any_mirage = True if positive else None if unknown else False
        assert any_mirage == terminal['trajectory_any_definite_Mirage']
        summaries.append(dict(run_id=terminal['run_id'], condition=terminal['condition'],
            observer_enabled=terminal['observer_enabled'], reviewed_distinct_candidates=len(group),
            source_negative=len(negative), source_unknown=len(unknown), source_positive=len(positive),
            pure_native_WAIT_excluded=sum(row['pure_native_WAIT_excluded'] for row in group),
            accepted=sum(row['accepted'] for row in group), environment_executed=terminal_actions,
            accepted_without_environment_action=sum(row['accepted_without_environment_action'] for row in group),
            positive_accepted=sum(row['accepted'] for row in positive),
            positive_environment_executed=sum(row['environment_executed'] for row in positive),
            positive_not_accepted=sum(not row['accepted'] for row in positive),
            unaccepted_source_negative=sum(not row['accepted'] for row in negative),
            unaccepted_source_unknown=sum(not row['accepted'] for row in unknown),
            trajectory_any_Mirage=any_mirage, analysis_official_score=terminal['analysis_official_score'],
            raw_recorded_official_reward=terminal['raw_recorded_official_reward'],
            exposure_state=terminal['exposure_state'], termination_axis=terminal.get('termination_axis'),
            original_outcome=terminal['original_outcome'],
            original_terminal_call_counters=terminal['actual_call_counts'],
            counters_are_not_a_new_full_physical_service_overhead_cost_audit=True,
            immutable_terminal=terminal['terminal_receipt'], complete_original_candidate_coverage_proven_now=True))
    assert len(summaries) == 4

    # This is an outcome-aware follow-up assessment, separate from primary labels.
    normal = next(row for row in rows if row['candidate_id'] == '9334046de6a30e7d0ad3')
    assert normal['primary_semantic_label'] is False and normal['native_action_error'] is False
    assert not normal['accepted'] and not normal['environment_executed']
    normal_packet = json.loads(Path(normal['source_packet']).read_bytes())
    image = Path(normal['source_packet']).parent / 'image-36.png'
    imagesha = sha(image)
    assert imagesha == normal_packet['actual_delivered_images'][-1]['sha256'] == 'dddb52624c266c805e6cac0a90c7d3101532c443b4fd2edbc0d4427ab25aa9eb'
    native = normal_packet['native_parser_result']
    assert native['error'] is None and native['payload'] == dict(type='click', x=635, y=678)
    x, y = 635 * 1280 / 1000, 678 * 720 / 1000
    assert 792 < x < 831 and 470 < y < 509
    judgment = normal['detector_events_not_semantic_gold']
    assert len(judgment) == 1
    verdict = judgment[0]['data']['verdict']
    assert verdict['claims'] == [] and verdict['action']['status'] == 'insufficient'
    assert "falls on the '9' button" in verdict['action']['reason']
    actual_input = r32 / 'pagination37-main-source-input-1794244337147112200'
    seal(actual_input)
    payload = json.loads((actual_input / 'payload.json').read_bytes())
    receipt = json.loads((actual_input / 'receipt.json').read_bytes())
    assert sha(actual_input / 'payload.json') == receipt['original_SHA_bindings']['payload.json']
    assert payload['candidate'] == normal['candidate_text']
    assert 'A visible available navigation control may support\nexploration even when the target is not found yet.' in payload['system']
    assert payload['view']['observation_id'] == normal['observation_id']
    scoped = dict(schema='outcome-aware-scoped-normal-pagination-assessment-v1',
        candidate_event_sha256=normal['candidate_event_sha256'], original_ordinal=37,
        source_label_reused_unchanged=True, assessment_is_not_new_blind_primary_Mirage_label=True,
        complete_current_original_image_directly_viewed=True, current_image=str(image), image_sha256=imagesha,
        independently_visible_current_page=8, visible_available_target='9', native_point_pixels=[x, y],
        approximate_evaluation_only_visible_target_box_pixels=[792, 470, 831, 509],
        actual_main_checker_input=str(actual_input / 'payload.json'), actual_main_checker_input_sha256=sha(actual_input / 'payload.json'),
        original_checker_already_instructed_to_allow_grounded_exploration_before_goal_found=True,
        detector_verdict_event=judgment[0],
        scoped_main_action_false_insufficiency=True,
        entire_pipeline_would_accept_or_succeed=None,
        later_native_point_and_alignment_branches_were_not_run_for_this_insufficient_candidate=True,
        final38_price_history_scope_remains_unknown=True,
        aggregate_terminal_budget_exhaustion_has_multiple_prior_calls_not_attributed_solely_to_this_event=True,
        missing_focus_cases_not_declared_false_blocks=True,
        runtime_validator_prompt_action_budget_and_source_labels_changed=False,
        proposed_prompt_duplication_or_forced_allow_not_deployed=True,
        evaluation_geometry_never_supplied_to_actor_checker_or_executor=True)

    total = dict(reviewed_candidates=84,
        source_negative=sum(row['primary_semantic_label'] is False for row in rows),
        source_unknown=sum(row['primary_semantic_label'] is None for row in rows),
        source_positive=sum(row['primary_semantic_label'] is True for row in rows),
        accepted=len(accepted_hashes), environment_executed=len(executed_hashes),
        accepted_without_environment_action=sum(row['accepted_without_environment_action'] for row in rows),
        positive_accepted=sum(row['primary_semantic_label'] is True and row['accepted'] for row in rows),
        positive_environment_executed=sum(row['primary_semantic_label'] is True and row['environment_executed'] for row in rows),
        positive_not_accepted=sum(row['primary_semantic_label'] is True and not row['accepted'] for row in rows),
        pure_native_WAIT_excluded=sum(row['pure_native_WAIT_excluded'] for row in rows),
        actual_terminal_event_chains=6, verified_committed_events=sum(c['snapshot']['count'] for c in chainmap.values()),
        original_log_bytes_rehashed=sum(c['snapshot']['bytes'] for c in chainmap.values()),
        previously_pending_candidates_first_execution_bound=2)
    assert (total['source_negative'], total['source_unknown'], total['source_positive']) == (61, 18, 5)
    assert (total['positive_accepted'], total['positive_environment_executed'], total['positive_not_accepted']) == (3, 2, 2)
    panel = dict(schema='four-original-terminal-companion-outcomes-v1', time=time.time(),
        source_inventory=str(inventory), source_inventory_sha256=sha(inventory),
        actual_event_evidence=str(evidence), actual_event_evidence_sha256=sha(evidence),
        original32_ledger=str(ledger_root / 'ledger.json'), original32_ledger_sha256=sha(ledger_root / 'ledger.json'),
        original_scope=dict(tracks=32, matched_pairs=16, selected_tasks=8, never_started=28,
            wholly_prospective_pairs=14, prospective_pairs_are_version_stratum_not_replacement_denominator=True),
        all_four_observed_tracks_are_one_selected_T000_task=True,
        original_primary_labels_reused_unchanged_not_new_independent_semantic_review=True,
        original_lawful_histories_include_prior_feedback_single_source_reviewer_not_fully_blind=True,
        totals=total, tracks=summaries, candidate_rows=rows,
        all_84_original_candidates_and_all_74_actual_environment_executions_bound_exactly_once=True,
        scoped_normal_operation_followup='scoped-normal-pagination-assessment.json',
        broad_false_block_accuracy_or_fair_cost_comparison_established=False,
        matched_Mirage_relative_reduction=None,
        reason_no_effect_conclusion='clean noaux remains unknown; both stale trajectories already positive; one task, unequal exposure, technical endpoints and version/resource strata remain',
        efficacy_established=False, completion_audit_passed=False, goal='active',
        auxiliary_actual_model='Qwen/Qwen3.5-9B', decision_adapter_loaded=False,
        auxiliary_current_full_image_fixed_v6_empty_per_call_context_preserved=True,
        no_runtime_protocol_or_conditions_changed=True,
        new_quote_ID_condition_human_decision_still_pending=True,
        new_model_GUI_capture_action_scorer_paid_calls=0)
    out = HERE / ('companion-panel-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'panel.json', panel)
    save(out / 'scoped-normal-pagination-assessment.json', scoped)
    save(out / 'pending11-after-frame-review.json', dict(time=time.time(),
        image=str(f11 / '012-original-after-execution.png'), image_sha256=sha(f11 / '012-original-after-execution.png'),
        directly_viewed=True, assessment_scope='postexecution frame only, not a new primary source label',
        visible='Coherent further listings with a Chevrolet van, DJ equipment rig, Big Blue Lodge interior and Ryobi tools; readable listing rows continue.',
        supports='A normal subsequent listing viewport is visible after the separately event-bound original down scroll.',
        does_not_establish='kayak absence, relevance of the full result set, global cheapest match or task completion',
        new_model_GUI_calls=0))
    lines = ['四条原GUI终局的候选、放行与执行审查（2026-11-10）', '',
        '目前仍未证明辅助模型降低Mirage。此报告补齐执行关联和正常操作审查，不是新增GUI结果或新的盲审标签。', '',
        '| 条件 | 辅助 | 已审候选 | 来源阴性/未知/阳性 | 放行 | 实际环境动作 | 阳性放行/实执 | 官方分析分 |',
        '|---|---|---:|---|---:|---:|---|---|']
    for track in summaries:
        score = '技术终局，保留原始0但分析为null' if track['analysis_official_score'] is None else str(track['analysis_official_score'])
        lines.append(f"| {track['condition']} | {'有' if track['observer_enabled'] else '无'} | {track['reviewed_distinct_candidates']} | {track['source_negative']}/{track['source_unknown']}/{track['source_positive']} | {track['accepted']} | {track['environment_executed']} | {track['positive_accepted']}/{track['positive_environment_executed']} | {score} |")
    lines += ['',
        '84个候选沿用原已封存来源审查：61阴性、18未知、5阳性。75个候选被接受，74个实际执行环境动作；其差额为一次被接受的STOP。3个阳性候选被接受，其中2个随后执行环境动作、1个为STOP；另2个阳性候选未被接受，但它们已出现的Mirage仍按轨迹一次即计。语义阳性不自动等于原生目标或方向错误。纯native WAIT计0，本规则保持。', '',
        '原第11和17候选各在技术续跑中首次执行。两者的原完整actor请求SHA、候选文本、旧原始事件、续跑接受及执行事件均绑定；第11条新增只读证据与第17条既有封存证据对齐，修正了仅看原命名空间会漏掉2次执行的问题。全84个原始candidate事件、全部74个action_executed事件及75个接受事件均唯一对应，无重算候选。原文件与旧快照未改。', '',
        '正常操作的新限定结论：无辅助clean轨的第37候选只点击当前可见9号页按钮。完整原图显示当前8号页和可见9号按钮，归一化635,678映射812.8,488.16像素，落在按钮内。实际核验器也明确认出点击落在9号按钮，却以任务尚未找到目标和之前结果不相关为由输出insufficient；无任何事实断言需反驳。实际system原已明确可见导航控件可支持尚未找到目标时的探索。因此这是主动作核验阶段的局部错误证据不足判定，不能靠再重复同一句规则宣称已修复。', '',
        '该候选因主核验insufficient没有进入之后的点读/对齐分支，因此不宣称整个流水线已被证明必然放行或任务必然成功。后续第38候选的价格历史范围仍未知，最终140核验预算终局也不能仅归因这一次拒绝。另两条先前打字候选的真实OS焦点仍无来源证明，不把它们自动算误拦。以上为已知结果后的机制审查，与原主语义标签分开。', '',
        'clean无辅助轨仍有一个未知候选，不能作为Mirage零基线；clean辅助轨已阳性。旧帧两臂均已出现确定Mirage，之后纠正不抹去。四条都来自同一T000选定任务，版本、资源技术中断和实际暴露不同。候选计数、动作更少、阻断或官方1均不足以证明相对降低。原32轨/16配对/8任务以及28未开始保留，14全新配对只是版本分层；相对降幅仍null，未证明30%或减半。', '',
        '实际辅助仍为单个Qwen3.5-9B基座，decision_adapter_loaded=false。当前完整供应单图+固定v6、每次空上下文、完整合法主历史/原图、BF16/SDPA、原动作/来源校验及每轨原预算未变。新的quote_id来源协议仍待独立条件决定，本次没有部署，也没有新模型、GUI、截图、动作、评分或付费API调用。', '',
        f"本次重新只读核对6段完整事件链、{total['verified_committed_events']}事件、{total['original_log_bytes_rehashed']}日志字节；没有重新全hash模型权重。首个合并只读审查超过55秒，源输入与超时回执已封存，确认旧读取进程不存在后改为6个独立有界读取，全部完成。此工程读取超时不是模型失败或额外实验。", '',
        '证据索引：panel.json含逐候选原标签、原始来源SHA、实际链摘要、接受/执行事件和终局SHA；scoped-normal-pagination-assessment.json保存局部正常操作判断及限制。没有把来源格式合规当成语义正确。']
    (out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    pointer = dict(root=str(out), panel_sha256=sha(out / 'panel.json'), report_sha256=sha(out / 'report.md'),
        scoped_assessment_sha256=sha(out / 'scoped-normal-pagination-assessment.json'),
        seal_sha256=sha(out / 'seal.json'), totals=total, goal='active', efficacy_established=False)
    save(HERE / 'companion-panel-created.json', pointer)
    print(json.dumps(dict(pointer, tracks=summaries), ensure_ascii=False))


if __name__ == '__main__':
    main()
