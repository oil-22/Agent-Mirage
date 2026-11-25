"""Publish original source reviews23/24, their execution and25native audits."""
from pathlib import Path
import time
from publish_source_progress22_once import BASE, HERE, read, save, sha, verify_folder


def main():
    assert not (HERE / 'source-progress24-publication-created.json').exists()
    evidence = sorted(HERE.glob('actual-evidence-*'))[-1]
    verify_folder(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert 0 <= time.time() - service['time'] < 180
    identities = [service['worker/process.json']['value'], service['launcher-process.json']['value'],
                  gui['control/runner-process.json']['value']]
    for record in identities:
        assert not record['actual'].get('absent') and record['actual']['state'] not in ['Z', 'X']
        assert all(str(record['actual'][key]) == str(record['record'][key])
                   for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert len(service['held_locks']) == 9 and service['authorized_GPUs'] == [4, 5, 6, 7]
    assert service['authorized_GPU_actual_compute_processes']
    for item in service['authorized_GPU_actual_compute_processes']:
        actual = item['actual_process']
        assert not actual.get('absent') and actual['state'] not in ['Z', 'X']
        assert all(str(actual[key]) == str(identities[0]['actual'][key])
                   for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert gui['batch/status.json']['value']['step'] >= 24
    rows, audits = [], []
    pointers = [HERE / 'prefix-audit-created.json'] + [HERE / ('new-replies-' + str(i).zfill(2) + '-audit-created.json') for i in range(2, 13)]
    for pointer in pointers:
        record = read(pointer)
        path = Path(record['audit'])
        assert sha(path) == record['audit_sha256']
        value = read(path)
        assert value['passed']
        rows.extend(value['requests'])
        audits.append(record)
    assert [r['request'] for r in rows] == [str(i).zfill(4) for i in range(1, 26)]
    assert all(r['natural_EOS'] for r in rows)
    assert sum(r['operation'] == 'actor' for r in rows) == 7
    assert sum(r['operation'] == 'judge' for r in rows) == 18
    reviews = []
    for name in ['source-review-06-created.json', 'source-review-07-created.json']:
        record = read(HERE / name)
        verify_folder(record['review'], record['seal_sha256'])
        assert sha(Path(record['review']) / 'review.json') == record['review_sha256']
        reviews.append(record)
    joins = []
    for name in ['post-review-join-1794234183692723100', 'post-review-join-1794234457166494700']:
        folder = HERE / name
        verify_folder(folder)
        value = read(folder / 'join.json')
        assert value['all_source_labels_sealed_before_this_join']
        assert len(value['rows']) == 1 and value['rows'][0]['accepted'] and value['rows'][0]['executed']
        accepted = value['rows'][0]['accepted_events'][0]['data']
        assert accepted['recaptures'] == 0 and accepted['regenerations'] == 0
        joins.append({'path': str(folder / 'join.json'), 'sha256': sha(folder / 'join.json')})
    frame = read(HERE / 'candidate24-postexecution-frame-created.json')
    verify_folder(frame['root'], frame['seal_sha256'])
    observation_timeout = read(HERE / 'inspection-timeout-preservation-created.json')
    verify_folder(observation_timeout['root'], observation_timeout['seal_sha256'])
    assert service['observation_timeout_linked_retry']['all_original_SHA_checks_retained']
    framepath = Path(frame['root']) / '025-originally-captured.png'
    assert sha(framepath) == read(Path(frame['root']) / 'receipt.json')['next_observation_current_image']['sha256']
    totals = {'input_tokens': sum(r['actual_input_tokens'] for r in rows),
              'output_tokens': sum(r['output_tokens'] for r in rows),
              'summed_native_call_timer_seconds': sum(r['native_call_timer_seconds'] for r in rows)}
    out = HERE / ('source-progress24-publication-' + str(time.time_ns()))
    out.mkdir()
    previous = out / 'previous-heads'
    previous.mkdir()
    before = {}
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (previous / name).write_bytes((BASE / name).read_bytes())
        before[name] = sha(BASE / name)
    status = read(BASE / 'full-gui-current.json')
    status.update(schema='GUI32-source-reviewed24-actions-and-twentyfive-native-replies-v1', time=time.time(),
        previous_heads_SHA256=before, goal='active', monitor_should_remain_active=True,
        previous_goal_turn_classification='progress: source review22and execution joined, actual judge64source discrepancy preserved, original requests17..20audited and three heads published',
        current_goal_turn_classification='progress: new source reviews23/24sealed before outcome joins, both normal scrolls executed with0recapture/regen, original post24frame viewed, and only new requests21..25audited',
        efficacy_established=False, relative_Mirage_reduction=None)
    status['authorities'].update(latest_actual_UID_locks_requests_chains={'path': str(evidence), 'seal_sha256': sha(evidence / 'seal.json')},
        new32_source_reviews23and24=reviews, new32_source_review_execution_joins23and24=joins,
        new32_nonoverlapping_requests1to25_audits=audits, candidate24_original_postexecution_frame=frame,
        publication22_readback=read(HERE / 'source-progress22-readback-created.json'),
        read_only_observation_timeout_preservation=observation_timeout)
    for target, source in [('actual_service_state_at_snapshot', 'worker/status.json'),
                           ('actual_worker_identity_at_snapshot', 'worker/process.json'),
                           ('actual_launcher_identity_at_snapshot', 'launcher-process.json')]:
        status[target] = service[source]['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'], status['GUI_event_chains'] = service['chains'], gui['chains']
    status['new32_sealed_requests_at_snapshot'], status['new32_terminals_at_snapshot'] = service['sealed_requests'], gui['terminals']
    status['confirmed_original_actions_total'] = 24
    status['new_source_review_progress'] = dict(original_unique_actor_candidates_reviewed_through=24,
        newly_source_reviewed_this_goal_turn=[23, 24], new_candidates_this_goal_turn=[23, 24],
        earlier1to22_not_relabelled_or_executed_again=True,
        source_reviews23and24_sealed_before_execution_joins=True,
        reviewed23and24_normal_actions_accepted_and_executed_once=True,
        all_two_new_candidates_without_semantic_assertions=True,
        aggregate_live_counts_and_lawful_prior_feedback_known_not_fully_blind=True,
        whole_trajectory_Mirage=None, official_task_score=None,
        efficacy_or_full_falseblock_rate_established=False)
    status['post24_original_frame_review'] = dict(path=str(framepath), sha256=sha(framepath),
        independently_viewed_by_root=True,
        visible_facts='Lower listings with Gillette razor dispenser and napkin holder, coherent footer/contact, active page5and visible3..7plus arrows. Visible shortcuts do not establish total pages.',
        new_GUI_captures_or_actions=0, task_success_or_global_minimum_proven=False)
    status['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] = '0025'
    status['largest_newly_audited_completed_judge'] = max((r for r in rows if r['operation'] == 'judge'), key=lambda r: r['actual_input_tokens'])
    status['new32_audited_completed_prefix_totals'] = dict(totals, requests=25, actor_replies=7,
        judge_replies=18, auxiliary_replies=0, natural_EOS_replies=25, format_retries=0,
        scope='Only new32requests0001..0025; excludes original23/29/31, failures/in-progress work, preprocessing/load and outside-holder reservation. Native timer includes instrumentation/transfers; not walltime/currency/energy/savings.')
    status['storage_at_snapshot'] = {'service': service['filesystem'], 'GUI': gui['filesystem'],
                                     'no_original_files_deleted_moved_or_compressed': True}
    status['next_action'] = ('Continue the same actually verified worker/launcher/GUI and original32tracks/16pairs. '
        'Original1..24candidates reviewed and executed once; review newly generated25+from original pixels and complete lawful history before outcome joins. '
        'Audit only new26+sealed replies. New schedule actual auxiliary forward/KV/release/insertion remains to be verified when enabled arm naturally starts. '
        'Preserve the old judge64source error separately; do not hot-change frozen conditions or rerun old terminals.')
    save(out / 'status.json', status)
    biggest = status['largest_newly_audited_completed_judge']
    note = ('## 最新：2026-11-09 新32累计24动作；新增两次正常滚动已先审后关联执行\n\n'
        '权威 `' + str((out / 'status.json').relative_to(BASE)).replace('\\', '/') + '`。'
        '新23/24候选均仅native DOWN，无事实/历史/完成断言；各自原图与完整合法历史先审封存，'
        '再关联原Controller接受和实际执行，均0recapture/0regen。原1–22不重复审查/执行。'
        'post24原已捕获后图已查看：正常底部列表、Gillette刀片盒/餐巾架、active5与可见3..7和页脚；不推总页数/任务完成。\n\n'
        '新32请求0001–0025已不重叠审计25自然EOS=7actor+18judge、0aux/格式retry。'
        '完整wire/prepared-first-forward全部tensor/实际IDs/原effective generation/原调用编号/GPU驻留已绑定。'
        '最大完成核验' + str(biggest['complete_supplied_images']) + '完整图/' + str(biggest['actual_input_tokens']) + '输入、'
        + str(biggest['output_tokens']) + '输出EOS；累计' + str(totals['input_tokens']) + 'input/' + str(totals['output_tokens']) + 'output，'
        + str(round(totals['summed_native_call_timer_seconds'], 3)) + 'summed native计时秒。排除旧根/失败/进行中/加载与holder外预留，含传输记录，不是walltime/货币/能耗/收益；更长历史fit不保证。\n\n'
        '首轨仍noaux，0完整轨、31未开始，整轨Mirage/官方评分/配对降幅未知，不能称防御有效。'
        '旧judge64来源误描述及所有技术终局/报告器故障原件继续保留；本轮未改条件或重复控制。'
        '只读全量SHA巡检55秒观察超时已封存；同一worker/launcher/holder重新实证存活，linked仅将观察时限改120秒，全部SHA检查保留，未重启模型或GUI。'
        'fresh实际UID/fullcmd/start、4–7九锁/独占compute与双链见回执，0–3不动。'
        '主完整历史/原图/BF16/SDPA/native/strict validator/全部原cap保持。辅助仍9B基座、decision_adapter_loaded=false；'
        '单图固定v6/空首KV/结束释放，新调度实际aux调用/插入待enabled轨。目标ACTIVE。\n\n')
    prefix = note.encode('utf8')
    (out / 'new-head.md').write_bytes(prefix)
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for name, expected in before.items():
        assert sha(BASE / name) == expected
    for name in ['README.md', 'HANDOFF.md']:
        (BASE / name).write_bytes(prefix + (previous / name).read_bytes())
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == prefix + (previous / name).read_bytes()
    assert (BASE / 'full-gui-current.json').read_bytes() == (out / 'status.json').read_bytes()
    save(HERE / 'source-progress24-publication-created.json', {'publication': str(out),
        'status_sha256': sha(out / 'status.json'), 'seal_sha256': sha(out / 'seal.json'),
        'three_heads_original_byte_readback_passed': True, 'goal': 'active'})
    print({'publication': str(out), 'confirmed_actions': 24, 'audited_requests': 25,
           'totals': totals, 'goal': 'active'})


if __name__ == '__main__':
    main()
