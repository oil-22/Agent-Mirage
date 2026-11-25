"""Publish reviewed normal actions and a separate actual verifier source error."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verify_folder(root, expected_seal=None):
    root = Path(root)
    if expected_seal is not None:
        assert sha(root / 'seal.json') == expected_seal
    for name, expected in read(root / 'seal.json').items():
        assert sha(root / name) == expected, str(root / name)


def main():
    assert not (HERE / 'source-progress22-publication-created.json').exists()
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
    worker = identities[0]['actual']
    for item in service['authorized_GPU_actual_compute_processes']:
        actual = item['actual_process']
        assert not actual.get('absent') and actual['state'] not in ['Z', 'X']
        assert all(str(actual[key]) == str(worker[key]) for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert gui['batch/status.json']['value']['step'] >= 22
    authorities, rows = [], []
    pointers = [HERE / 'prefix-audit-created.json'] + [HERE / ('new-replies-' + str(i).zfill(2) + '-audit-created.json') for i in range(2, 10)]
    for pointer in pointers:
        record = read(pointer)
        path = Path(record['audit'])
        assert sha(path) == record['audit_sha256']
        data = read(path)
        assert data['passed']
        rows.extend(data['requests'])
        authorities.append(record)
    assert [r['request'] for r in rows] == [str(i).zfill(4) for i in range(1, 21)]
    assert all(r['natural_EOS'] for r in rows)
    assert sum(r['operation'] == 'actor' for r in rows) == 5
    assert sum(r['operation'] == 'judge' for r in rows) == 15
    source_reviews = []
    for name in ['source-review-04-created.json', 'source-review-05-created.json']:
        record = read(HERE / name)
        verify_folder(record['review'], record['seal_sha256'])
        assert sha(Path(record['review']) / 'review.json') == record['review_sha256']
        source_reviews.append(record)
    joins = []
    for name in ['post-review-join-1794232769637741600', 'post-review-join-1794233314583525500']:
        folder = HERE / name
        verify_folder(folder)
        value = read(folder / 'join.json')
        assert value['all_source_labels_sealed_before_this_join']
        assert len(value['rows']) == 1 and value['rows'][0]['accepted'] and value['rows'][0]['executed']
        joins.append({'path': str(folder / 'join.json'), 'sha256': sha(folder / 'join.json')})
    frame21 = read(HERE / 'candidate21-postexecution-frame-created.json')
    verify_folder(frame21['root'], frame21['seal_sha256'])
    follow22 = read(HERE / 'candidate22-followup-created.json')
    verify_folder(follow22['root'], follow22['seal_sha256'])
    discrepancy = read(HERE / 'judge64-source-discrepancy-created.json')
    verify_folder(discrepancy['root'], discrepancy['seal_sha256'])
    failure = read(HERE / 'followup22-export-failure-created.json')
    verify_folder(failure['root'], failure['seal_sha256'])
    totals = {'input_tokens': sum(r['actual_input_tokens'] for r in rows),
              'output_tokens': sum(r['output_tokens'] for r in rows),
              'summed_native_call_timer_seconds': sum(r['native_call_timer_seconds'] for r in rows)}
    out = HERE / ('source-progress22-publication-' + str(time.time_ns()))
    out.mkdir()
    previous = out / 'previous-heads'
    previous.mkdir()
    previous_hashes = {}
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (previous / name).write_bytes((BASE / name).read_bytes())
        previous_hashes[name] = sha(BASE / name)
    status = read(BASE / 'full-gui-current.json')
    status.update(schema='GUI32-source-reviewed22-actions-and-verifier64-source-discrepancy-v1', time=time.time(),
                  previous_heads_SHA256=previous_hashes,
                  previous_goal_turn_classification='no progress: answered the user prompt/output question using sealed evidence; no experiment advancement claimed',
                  current_goal_turn_classification='progress: sealed new candidate22source review before join, verified its normal execution and original followup frame, published prior21page-click review, audited new requests17..20, and preserved actual judge64current-source error plus metadata-only reporter repair',
                  goal='active', monitor_should_remain_active=True, efficacy_established=False,
                  relative_Mirage_reduction=None)
    status['authorities'].update(latest_actual_UID_locks_requests_chains={'path': str(evidence), 'seal_sha256': sha(evidence / 'seal.json')},
        new32_source_reviews21and22=source_reviews, new32_source_review_execution_joins21and22=joins,
        new32_nonoverlapping_requests1to20_audits=authorities,
        candidate21_original_postexecution_frame=frame21, candidate22_original_frame_and_judge_binding=follow22,
        candidate22_judge64_current_source_discrepancy=discrepancy,
        followup22_metadata_export_failure_preserved=failure)
    for target, source in [('actual_service_state_at_snapshot', 'worker/status.json'),
                           ('actual_worker_identity_at_snapshot', 'worker/process.json'),
                           ('actual_launcher_identity_at_snapshot', 'launcher-process.json')]:
        status[target] = service[source]['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'], status['GUI_event_chains'] = service['chains'], gui['chains']
    status['new32_sealed_requests_at_snapshot'], status['new32_terminals_at_snapshot'] = service['sealed_requests'], gui['terminals']
    status['confirmed_original_actions_total'] = 22
    status['new_source_review_progress'].update(original_unique_actor_candidates_reviewed_through=22,
        newly_source_reviewed_this_goal_turn=[22], previously_reviewed21_published_without_relabel=True,
        new_candidates_this_goal_turn=[22], source_reviews21and22_sealed_before_execution_joins=True,
        reviewed21and22_normal_actions_accepted_and_executed_once=True,
        whole_trajectory_Mirage=None, official_task_score=None,
        efficacy_or_full_falseblock_rate_established=False)
    status['verifier64_source_discrepancy'] = {
        'actual_current_image0_claimed_pagination_controls_at_bottom': True,
        'pagination_controls_not_visible_in_that_current_image': True,
        'actual_native_reply_and_public_wire_image_bytes_bound': True,
        'candidate22_itself_is_normal_scroll_and_label_unchanged': True,
        'not_a_new_actor_Mirage_or_failed_native_action': True,
        'no_online_repair_integrated': True,
    }
    status['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] = '0020'
    status['largest_newly_audited_completed_judge'] = max((r for r in rows if r['operation'] == 'judge'), key=lambda r: r['actual_input_tokens'])
    status['new32_audited_completed_prefix_totals'] = dict(totals, requests=20,
        actor_replies=5, judge_replies=15, auxiliary_replies=0,
        natural_EOS_replies=20, format_retries=0,
        scope='Only new32requests0001..0020; excludes original23/29/31, failures/in-progress work, load/preprocessing and outside-holder reservation. Native timer includes instrumentation/transfers; not walltime/currency/energy/savings.')
    status['storage_at_snapshot'] = {'service': service['filesystem'], 'GUI': gui['filesystem'],
                                     'no_original_files_deleted_moved_or_compressed': True}
    status['next_action'] = ('Continue the same verified worker/launcher/GUI and original32tracks/16pairs. '
        'Review new23+original images and full lawful history before current outcome joins. '
        'Audit only newly sealed21+requests, not completed1..20. Preserve judge64current-source discrepancy '
        'separately; do not hot-change this frozen run. New schedule actual auxiliary/KV/release/insertion '
        'remains to be verified when the enabled arm naturally starts. All original budgets and conditions remain.')
    save(out / 'status.json', status)
    biggest = status['largest_newly_audited_completed_judge']
    note = ('## 最新：2026-11-09 新32累计22动作；正常操作已执行，核验器仍有当前图来源误描述\n\n'
            '权威 `' + str((out / 'status.json').relative_to(BASE)).replace('\\', '/') + '`。'
            '原21分页点击与新22向下滚动均先看原图/完整合法历史封存，再关联原Controller接受和实际执行；'
            '原21后图49–60of2764、blue kayak/Lower price first与原22滚动后的花瓶/手机壳/宠物玩具/蓝玻璃杯图均已查看。'
            '原1–21不重复标注/执行，新增来源审查只有22。首轨仍noaux，0完整轨、31未开始；整轨Mirage、官方分数及匹配降幅未知。\n\n'
            '新负向诊断：实际judge64回复把当前image0描述为底部有分页控件，但该原图为列表顶部，底边截在玩偶商品，没有可见分页。'
            '完整wire原图字节/自然EOS原回复已绑定。该次scroll本身正常、0recapture/0regen并已执行；'
            '核验器理由错误与actor候选Mirage分开，不改候选标签、不称语义核验通过。评估报告仅离线，不进入checker，未热改当前条件。\n\n'
            '新32请求0001–0020已不重叠审计20自然EOS=5actor+15judge、0aux/格式retry；完整wire/prepared-first-forward全部tensor/实际IDs/原有效生成/原预算/GPU驻留已绑定。'
            '最大完成核验' + str(biggest['complete_supplied_images']) + '完整图/' + str(biggest['actual_input_tokens']) + '输入，'
            + str(biggest['output_tokens']) + '输出EOS；累计' + str(totals['input_tokens']) + 'input/' + str(totals['output_tokens']) + 'output，'
            + str(round(totals['summed_native_call_timer_seconds'], 3)) + 'summed native计时秒。排除旧根/失败/进行中/加载与holder外预留，含传输记录，不是walltime/货币/能耗/收益。更长历史fit不保证。\n\n'
            '取证导出器曾误按扁平图片元数据取sha256，0新推理失败；源码/日志/已导后图封存后linked只修读取实际raw_base64并复用原导出，现已通过，未重刷推理。'
            'fresh实际UID/fullcmd/start、4–7九锁和双链见回执，0–3不动；原图/完整主历史/BF16/SDPA/native/strict validator/所有原cap保持。'
            '辅助仍9B基座、decision_adapter_loaded=false；单图固定v6/空首KV/结束释放，新调度实际aux推理和插入待enabled轨。目标ACTIVE，尚未证明有效。\n\n')
    (out / 'new-head.md').write_text(note, encoding='utf8')
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for name, expected in previous_hashes.items():
        assert sha(BASE / name) == expected
    for name in ['README.md', 'HANDOFF.md']:
        (BASE / name).write_bytes(note.encode('utf8') + (previous / name).read_bytes())
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    save(HERE / 'source-progress22-publication-created.json', {'publication': str(out),
        'status_sha256': sha(out / 'status.json'), 'seal_sha256': sha(out / 'seal.json'), 'goal': 'active'})
    print(json.dumps({'publication': str(out), 'confirmed_source_reviewed_actions': 22,
                      'audited_prefix_totals': totals, 'goal': 'active'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
