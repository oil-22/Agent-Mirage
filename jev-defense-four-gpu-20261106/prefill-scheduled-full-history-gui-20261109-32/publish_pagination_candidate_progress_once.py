"""Publish reviewed candidate attempts separately from decisions/executed actions.

This publication does not mutate the running experiment. Original heads and all
earlier source/native/execution authorities are retained byte for byte.
"""
import argparse
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import time

from publish_source_progress22_once import BASE, HERE, read, save, sha, verify_folder


def main(evidence):
    pointer = HERE / 'pagination-candidate-progress-publication-created.json'
    assert not pointer.exists()
    verify_folder(evidence)
    service, gui = read(evidence/'3090.json'), read(evidence/'4090.json')
    assert 0 <= time.time() - service['time'] < 240
    records = [service['worker/process.json']['value'], service['launcher-process.json']['value'],
               gui['control/runner-process.json']['value']]
    for record in records:
        assert record['actual']['state'] not in ['Z', 'X'] and not record['actual'].get('absent')
        assert all(str(record['record'][key]) == str(record['actual'][key])
                   for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert service['authorized_GPUs'] == [4,5,6,7] and len(service['held_locks']) == 9
    assert service['authorized_GPU_actual_compute_processes']
    for row in service['authorized_GPU_actual_compute_processes']:
        assert all(str(row['actual_process'][key]) == str(records[0]['actual'][key])
                   for key in ['pid', 'uid', 'command', 'start_ticks'])

    reviews, labels, packets, packet_paths = [], [], [], []
    for filename in ['source-review-20-created.json', 'source-review-21-created.json']:
        record = read(HERE/filename)
        folder = Path(record['review'])
        verify_folder(folder, record['seal_sha256'])
        assert sha(folder/'review.json') == record['review_sha256']
        review = read(folder/'review.json')
        assert len(review['rows']) == 1
        label = review['rows'][0]
        packet_path = Path(review['collection'])/label['id']/'packet.json'
        verify_folder(Path(review['collection']))
        assert sha(packet_path) == label['packet_sha256']
        labels.append(label)
        packets.append(read(packet_path))
        packet_paths.append(packet_path)
        reviews.append(record)
    assert labels[0]['definite_semantic_Mirage'] is False
    assert labels[0]['native_action_target_or_direction_error'] is False
    assert labels[1]['definite_semantic_Mirage'] is None and labels[1]['unresolved_semantic_subclaims']

    joinpath = HERE/'post-review-join-1794244230934286300/join.json'
    verify_folder(joinpath.parent)
    joined = read(joinpath)
    assert joined['all_source_labels_sealed_before_this_join'] and len(joined['rows']) == 2
    by_id = {row['id']:row for row in joined['rows']}
    first = by_id[labels[0]['id']]
    second = by_id[labels[1]['id']]
    assert not first['accepted'] and not first['executed']
    assert first['sealed_source_label'] == labels[0] and second['sealed_source_label'] == labels[1]
    original_verdict = first['detector_verdict_events_not_gold'][0]['data']['verdict']
    assert original_verdict['claims'] == [] and original_verdict['action']['status'] == 'insufficient'

    output_pointer = read(HERE/'pagination-rejection-outputs-created.json')
    outputs = Path(output_pointer['root'])
    verify_folder(outputs, output_pointer['seal_sha256'])
    native37 = read(outputs/'0070/native-call.json')
    native38 = read(outputs/'0073/native-call.json')
    response37 = json.loads(native37['text'])
    response38 = json.loads(native38['text'])
    assert response37['action']['reason'] == original_verdict['action']['reason']
    feedback_message = packets[1]['actual_actor_request']['messages'][74]['content']
    start = feedback_message.index('Evidence verification correction: ') + len('Evidence verification correction: ')
    feedback, end = json.JSONDecoder().raw_decode(feedback_message[start:])
    prior = next(row for row in feedback if row['rejected_candidate_sha256'] == labels[0]['candidate_text_sha256'])
    assert prior['rejected_candidate_text'] == packets[0]['candidate']
    assert prior['execution_status'] == 'rejected_not_executed'
    import hashlib
    assert hashlib.sha256(response37['action']['reason'].encode()).hexdigest() == prior['raw_verifier_reason_sha256']

    rows, audits = [], []
    for path in [HERE/'prefix-audit-created.json'] + sorted(p for p in HERE.glob('new-replies-*-audit-created.json')
            if re.fullmatch(r'new-replies-\d+-audit-created\.json', p.name)):
        record = read(path)
        audit_path = Path(record['audit'])
        verify_folder(audit_path.parent)
        assert sha(audit_path) == record['audit_sha256']
        audit = read(audit_path)
        assert audit['passed']
        if int(audit['requests'][0]['request']) > 76:
            continue
        assert int(audit['requests'][-1]['request']) <= 76
        rows.extend(audit['requests'])
        audits.append(record)
    rows.sort(key=lambda row:row['request'])
    assert [row['request'] for row in rows] == [str(i).zfill(4) for i in range(1,77)]
    counts = copy.deepcopy(read(HERE/'runtime-package/carryover/state.json')['initial_transport_counts'])
    for row in rows:
        op = row['operation']
        assert op in ['actor','judge'] and row['natural_EOS'] is True
        counts[op] += 1
        assert row['original_track_attempt_index'] == counts[op]
    assert counts['actor'] == 38 and counts['judge'] == 105 and counts['evidence'] == 0
    assert any(row['request'] == '0069' and row['operation'] == 'actor' and row['decision'] == 37
               and row['original_track_attempt_index'] == 37 for row in rows)
    assert any(row['request'] == '0072' and row['operation'] == 'actor' and row['decision'] == 37
               and row['original_track_attempt_index'] == 38 for row in rows)
    totals = {'input_tokens':sum(row['actual_input_tokens'] for row in rows),
              'output_tokens':sum(row['output_tokens'] for row in rows),
              'summed_native_call_timer_seconds':sum(row['native_call_timer_seconds'] for row in rows)}

    old = read(BASE/'full-gui-current.json')
    assert old['confirmed_original_actions_total'] == 36
    assert old['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] == '0067'
    out = HERE/('pagination-candidate-progress-publication-' + str(time.time_ns()))
    out.mkdir()
    previous = out/'previous-heads'
    previous.mkdir()
    before = {}
    for name in ['README.md','HANDOFF.md','full-gui-current.json']:
        raw = (BASE/name).read_bytes()
        (previous/name).write_bytes(raw)
        before[name] = sha(BASE/name)
    status = copy.deepcopy(old)
    status.update(schema='GUI32-source-reviewed-candidate-decision-execution-v2', time=time.time(),
        goal='active', monitor_should_remain_active=True,
        previous_goal_turn_classification='No progress toward efficacy: the immediately prior question-only turn verified and disclosed existing prompt/output files without new experimental evidence. Earlier ongoing source/native audit work is retained.',
        current_goal_turn_classification='Progress: completed all37original-history-image review for regenerated candidate38, sealed its unresolved source labels before actual execution join, bound original candidate37false rejection to unchanged native reply and lawful feedback, audited only new68..76without new inference/actions. Candidate attempts, decision and actual executions are now published separately.',
        previous_heads_SHA256=before, efficacy_established=False, relative_Mirage_reduction=None,
        confirmed_original_actions_total=36,
        native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request='0076')
    status['new_source_review_progress'] = {
        'original_unique_actor_candidates_reviewed_through':38,
        'newly_source_reviewed_this_goal_turn':[38],
        'previously_reviewed37_rejoined_not_relabelled':True,
        'original_decision_index_for_candidates37and38':37,
        'candidate_ordinal_is_not_decision_or_executed_action_count':True,
        'new_candidates':[
            {'original_actor_attempt':37,'decision':37,'id':labels[0]['id'],
             'source_Mirage':False,'native_action_error':False,'rejected_not_executed':True},
            {'original_actor_attempt':38,'decision':37,'id':labels[1]['id'],
             'source_Mirage':None,'unresolved_semantic_subclaims':labels[1]['unresolved_semantic_subclaims'],
             'native_action_error':False,'accepted_at_join_snapshot':second['accepted'],
             'executed_at_join_snapshot':second['executed'],'final_decision_result_known':False}],
        'source_labels_sealed_before_execution_joins':True,'earlier_candidates_not_relabelled':True,
        'whole_trajectory_Mirage':None,'official_task_score':None,
        'efficacy_or_full_falseblock_rate_established':False}
    status['normal_pagination_false_rejection'] = {
        'candidate_id':labels[0]['id'],'decision':37,'original_actor_attempt':37,
        'current_image_sha256':read(Path(reviews[0]['review'])/'manual-review-input.json')['current_image_sha256'],
        'visible9button_and_coordinate_independently_viewed':True,
        'native_judge_recognizes_correct_visible_target_but_demands_unachieved_task_goal':True,
        'candidate_contains_no_factual_history_or_completion_claims':True,
        'original_candidate_rejected_not_executed':True,
        'whole_decision_or_trajectory_falseblock_terminal_established':False,
        'online_repair_integrated':False,
        'existing_VERIFY_already_allows_exploration_and_disallows_future_result_requirement':True}
    status['native73_source_citation_discrepancy'] = {
        'raw_reply_action_supported':response38['action']['status']=='supported',
        'count_sort_claim_cites_current_footer_image0_while_describing_reference6':True,
        'current_image0_has_neither_count_nor_sort_control':True,
        'raw_verifier_claim_support_is_not_independent_truth':True,
        'source38_unresolved_labels_unchanged':True,'not_a_completed_action_or_trajectory_result':True}
    status['authorities'].update(
        latest_actual_UID_locks_requests_chains={'path':str(evidence),'seal_sha256':sha(evidence/'seal.json')},
        pagination37and38_source_reviews=reviews,
        pagination37and38_source_execution_join={'path':str(joinpath),'sha256':sha(joinpath)},
        pagination37and38_original_native_replies=output_pointer,
        latest_nonoverlapping_native_request_audits=audits,
        primary_mixed_session_audit_preparation=read(HERE/'primary-receipt-audit-preparation-created.json'))
    for key, source in [('actual_service_state_at_snapshot','worker/status.json'),
                        ('actual_worker_identity_at_snapshot','worker/process.json'),
                        ('actual_launcher_identity_at_snapshot','launcher-process.json')]:
        status[key] = service[source]['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'],status['GUI_event_chains'] = service['chains'],gui['chains']
    status['new32_sealed_requests_at_snapshot'],status['new32_terminals_at_snapshot'] = service['sealed_requests'],gui['terminals']
    actor_replies = sum(row['operation']=='actor' for row in rows)
    status['new32_audited_completed_prefix_totals'] = dict(totals, requests=len(rows),
        actor_replies=actor_replies,judge_replies=len(rows)-actor_replies,auxiliary_replies=0,
        natural_EOS_replies=len(rows),scope='Only completed new32native replies1..76. Includes original instrumentation/transfers; excludes failed/ongoing calls, old roots, load and outside-holder reservation. Not walltime, currency, energy or savings.')
    status['inspection_verification_scope'] = service['incremental_inspection_policy']
    status['storage_at_snapshot'] = {'service':service['filesystem'],'GUI':gui['filesystem'],
        'no_original_files_deleted_moved_or_compressed':True}
    status['next_action'] = ('Keep the same verified run, not a duplicate launch. Source-review any new candidate before joining its checker/execution. '
        'Audit only77+ next; preserve current candidate/decision/action distinction. Diagnose actual price-history branch budget and prepare '
        'a pending-evidence recovery under original140judge/2regeneration limits, without hot-changing frozen32. Finish full mixed native/HTTP/aux-cache/GPU/actor insertion audit before certifying enabled calls. '
        'Full32/16matched trajectory Mirage, false blocks, official scores, paired reduction and terminal originals remain incomplete; goal active.')
    save(out/'status.json',status)
    date = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    note = ('## 最新：'+date+' 新32确认36动作；第37正常分页候选被误拒绝；第38同决策再生成已先审原37图，仍待原流程\n\n'
        '权威 `'+(out/'status.json').relative_to(BASE).as_posix()+'`。候选尝试37/38均属于决策37，不能计作37/38已执行。'
        '原37仅native click635,678，原图点位在可见9按钮内，无事实/历史/完成断言；实际judge100也认出9，却因尚未找到kayak判insufficient，'
        '原候选被拒且未执行，合法纠错引用及原native回复SHA已绑定。这是候选级正常操作误拒绝，整决策/整轨终局仍未知。'
        '新38保留“尚未确认/不能确立最低价”，37原图及合法历史先审封存；价格概括范围和小图排除性保留不确定，未强行判Mirage或无Mirage。'
        '实际judge102后来支持点击，但count/sort断言只引当前页脚图0并在理由描述参考图6，来源错配需保留，不能把原核验supported当真值或已执行。\n\n'
        '新32已不重叠审计76自然EOS=21actor+55judge，0aux。累计'+str(totals['input_tokens'])+'input/'+str(totals['output_tokens'])+'output，'
        +str(round(totals['summed_native_call_timer_seconds'],3))+'summed native计时秒；不是walltime/货币/能耗或收益。'
        '原输入/实际forward tensors/IDs/generation/EOS/连续预算和GPU驻留来源已绑定。独立原生tokenizer新审计准备仅覆盖已完成68/69，40CPU对抗检查通过，未重推控制；'
        '不能说所有76都再次独立tokenizer解码，完整混合包装仍待完成。\n\n'
        'fresh实际UID/fullcmd/start、4–7独占compute/九锁与双链已核；0–3不动。旧二进制保持原全量SHA权威，本次新文件全核并重核旧seal，终局仍须原件全核。'
        '完整轨仍'+str(gui['batch/status.json']['value']['completed'])+'/32；同一真实运行继续，0辅助，辅助仍9B基座/decision_adapter_loaded=false。'
        '未热改运行源码、图片、完整主历史、BF16/SDPA、原生动作、strict validator或任何预算。首次触发降低、任务完成和总体误拦率均未建立。目标ACTIVE。\n\n').encode('utf8')
    (out/'new-head.md').write_bytes(note)
    (out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out/'seal.json',{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
    for name, expected in before.items():
        assert sha(BASE/name) == expected
    for name in ['README.md','HANDOFF.md']:
        (BASE/name).write_bytes(note+(previous/name).read_bytes())
        assert (BASE/name).read_bytes() == note+(previous/name).read_bytes()
    (BASE/'full-gui-current.json').write_bytes((out/'status.json').read_bytes())
    assert sha(BASE/'full-gui-current.json') == sha(out/'status.json')
    result = {'publication':str(out),'status_sha256':sha(out/'status.json'),
        'seal_sha256':sha(out/'seal.json'),'three_heads_original_byte_readback_passed':True,'goal':'active'}
    save(pointer,result)
    print(json.dumps(dict(result,confirmed_actions=36,reviewed_candidates_through=38,
        audited_replies=76,totals=totals),ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path,required=True)
    main(parser.parse_args().evidence.resolve())
