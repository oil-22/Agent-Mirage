"""Publish a contiguous reviewed/executed prefix; no runtime changes."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import time
from publish_source_progress22_once import BASE, HERE, read, save, sha, verify_folder


def main(spec_path, evidence):
    spec = read(spec_path)
    key = spec['publication_key']
    assert re.fullmatch(r'source-progress\d+(?:-[a-z0-9]+)*', key)
    pointer = HERE / (key + '-publication-created.json')
    assert not pointer.exists()
    verify_folder(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert 0 <= time.time() - service['time'] < 180
    records = [service['worker/process.json']['value'], service['launcher-process.json']['value'],
               gui['control/runner-process.json']['value']]
    for record in records:
        assert not record['actual'].get('absent') and record['actual']['state'] not in ['Z', 'X']
        assert all(str(record['actual'][k]) == str(record['record'][k]) for k in ['pid', 'uid', 'command', 'start_ticks'])
    assert service['authorized_GPUs'] == [4, 5, 6, 7] and len(service['held_locks']) == 9
    assert service['authorized_GPU_actual_compute_processes']
    for item in service['authorized_GPU_actual_compute_processes']:
        actual = item['actual_process']
        assert not actual.get('absent') and actual['state'] not in ['Z', 'X']
        assert all(str(actual[k]) == str(records[0]['actual'][k]) for k in ['pid', 'uid', 'command', 'start_ticks'])
    old_status = read(BASE / 'full-gui-current.json')
    target, through = spec['confirmed_action_ordinal'], spec['audited_through_request']
    assert [c['ordinal'] for c in spec['cases']] == list(range(old_status['confirmed_original_actions_total'] + 1, target + 1))
    assert gui['batch/status.json']['value']['step'] >= target
    rows, audits = [], []
    pointers = [HERE / 'prefix-audit-created.json'] + sorted(p for p in HERE.glob('new-replies-*-audit-created.json')
        if re.fullmatch(r'new-replies-\d+-audit-created\.json', p.name))
    for path in pointers:
        record = read(path)
        audit_path = Path(record['audit'])
        assert sha(audit_path) == record['audit_sha256']
        value = read(audit_path)
        assert value['passed']
        if int(value['requests'][0]['request']) > through:
            continue
        assert int(value['requests'][-1]['request']) <= through
        rows.extend(value['requests'])
        audits.append(record)
    rows.sort(key=lambda row: row['request'])
    assert [r['request'] for r in rows] == [str(i).zfill(4) for i in range(1, through + 1)]
    counts = {'actor': 17, 'judge': 50}
    for row in rows:
        assert row['natural_EOS'] and row['operation'] in counts
        counts[row['operation']] += 1
        assert row['original_track_attempt_index'] == counts[row['operation']]
        assert counts['actor'] <= 70 and counts['judge'] <= 140
    reviews, joins = [], []
    for case in spec['cases']:
        record = read(HERE / case['review_pointer'])
        folder = Path(record['review'])
        verify_folder(folder, record['seal_sha256'])
        assert sha(folder / 'review.json') == record['review_sha256']
        review = read(folder / 'review.json')
        collection = Path(review['collection'])
        assert sha(collection / 'collection.json') == review['collection_sha256']
        assert len(review['rows']) == 1
        label = review['rows'][0]
        private = next(r for r in read(collection / 'PRIVATE-source-index.json') if r['id'] == label['id'])
        request = Path(private['service_receipt']).name
        native = next(r for r in rows if r['request'] == request)
        assert native['operation'] == 'actor' and native['original_track_attempt_index'] == case['ordinal']
        joinpath = HERE / case['execution_join']
        verify_folder(joinpath.parent)
        joined = read(joinpath)
        assert joined['all_source_labels_sealed_before_this_join'] and len(joined['rows']) == 1
        row = joined['rows'][0]
        assert row['id'] == label['id'] and row['accepted'] and row['executed']
        assert len(row['accepted_events']) == len(row['executed_events']) == 1
        reviews.append(record)
        joins.append({'path': str(joinpath), 'sha256': sha(joinpath)})
    frame = read(HERE / spec['post_frame_pointer'])
    verify_folder(frame['root'], frame['seal_sha256'])
    frame_root = Path(frame['root'])
    pictures = list(frame_root.glob('*-originally-captured.png'))
    assert len(pictures) == 1 and spec['post_frame_actually_viewed'] is True
    assert sha(pictures[0]) == read(frame_root / 'receipt.json')['next_observation_current_image']['sha256']
    totals = {'input_tokens': sum(r['actual_input_tokens'] for r in rows), 'output_tokens': sum(r['output_tokens'] for r in rows),
              'summed_native_call_timer_seconds': sum(r['native_call_timer_seconds'] for r in rows)}
    actor_count = sum(r['operation'] == 'actor' for r in rows)
    judge_count = len(rows) - actor_count
    out = HERE / (key + '-publication-' + str(time.time_ns()))
    out.mkdir()
    previous = out / 'previous-heads'
    previous.mkdir()
    before = {}
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (previous / name).write_bytes((BASE / name).read_bytes())
        before[name] = sha(BASE / name)
    (out / 'publication-spec.json').write_bytes(spec_path.read_bytes())
    status = old_status
    status.update(schema='GUI32-source-reviewed-native-action-prefix-v1', time=time.time(), goal='active',
        monitor_should_remain_active=True, previous_heads_SHA256=before,
        previous_goal_turn_classification=spec['previous_goal_turn_classification'],
        current_goal_turn_classification=spec['current_goal_turn_classification'],
        efficacy_established=False, relative_Mirage_reduction=None)
    status['authorities'].update(latest_actual_UID_locks_requests_chains={'path': str(evidence), 'seal_sha256': sha(evidence / 'seal.json')})
    status['authorities'][key + '_source_reviews'] = reviews
    status['authorities'][key + '_source_execution_joins'] = joins
    status['authorities']['latest_nonoverlapping_native_request_audits'] = audits
    status['authorities'][key + '_original_postexecution_frame'] = frame
    for authority_name, proof in spec.get('supplemental_authorities', {}).items():
        assert re.fullmatch(r'[a-z][a-z0-9_]+', authority_name)
        folder = Path(proof['root']).resolve()
        assert folder.is_relative_to(HERE) and folder != HERE
        verify_folder(folder, proof['seal_sha256'])
        status['authorities'][authority_name] = proof
    for target_key, source_key in [('actual_service_state_at_snapshot', 'worker/status.json'), ('actual_worker_identity_at_snapshot', 'worker/process.json'), ('actual_launcher_identity_at_snapshot', 'launcher-process.json')]:
        status[target_key] = service[source_key]['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'], status['GUI_event_chains'] = service['chains'], gui['chains']
    status['new32_sealed_requests_at_snapshot'], status['new32_terminals_at_snapshot'] = service['sealed_requests'], gui['terminals']
    status['confirmed_original_actions_total'] = target
    status['new_source_review_progress'] = {'original_unique_actor_candidates_reviewed_through': target,
        'newly_source_reviewed_this_goal_turn': [c['ordinal'] for c in spec['cases']],
        'source_labels_sealed_before_execution_joins': True, 'earlier_candidates_not_relabelled': True,
        'whole_trajectory_Mirage': None, 'official_task_score': None, 'efficacy_or_full_falseblock_rate_established': False}
    status['latest_original_postexecution_frame_review'] = {'path': str(pictures[0]), 'sha256': sha(pictures[0]),
        'independently_viewed_by_root': True, 'visible_facts': spec['post_frame_visible_facts'],
        'new_GUI_captures_or_actions': 0, 'task_success_or_global_minimum_proven': False}
    status['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] = str(through).zfill(4)
    status['largest_newly_audited_completed_judge'] = max((r for r in rows if r['operation'] == 'judge'), key=lambda r: r['actual_input_tokens'])
    status['new32_audited_completed_prefix_totals'] = dict(totals, requests=len(rows), actor_replies=actor_count,
        judge_replies=judge_count, auxiliary_replies=0, natural_EOS_replies=len(rows),
        scope='Only new32completed prefix; excludes original23/29/31, failed/ongoing work, preprocessing/load and outside-holder reservation. Includes instrumentation/transfers; not walltime/currency/energy/savings. Format retries are not separately re-counted by this summary.')
    status['inspection_verification_scope'] = service.get('incremental_inspection_policy', {'full_current_binary_SHA_verification': True})
    status['storage_at_snapshot'] = {'service': service['filesystem'], 'GUI': gui['filesystem'], 'no_original_files_deleted_moved_or_compressed': True}
    status['next_action'] = spec['next_action']
    save(out / 'status.json', status)
    publication_date = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    note = ('## 最新：' + publication_date + ' 新32累计确认' + str(target) + '动作；' + spec['headline'] + '\n\n'
        '权威 `' + str((out / 'status.json').relative_to(BASE)).replace('\\', '/') + '`。' + spec['source_and_execution_note'] + '\n\n'
        '新32已不重叠审计' + str(len(rows)) + '自然EOS=' + str(actor_count) + 'actor+' + str(judge_count) + 'judge，0aux。'
        '完整wire/全部prepared-first-forward tensor/实际IDs/原effective generation/连续原预算编号/GPU驻留已绑定。'
        '累计' + str(totals['input_tokens']) + 'input/' + str(totals['output_tokens']) + 'output，'
        + str(round(totals['summed_native_call_timer_seconds'], 3)) + 'summed native计时秒；含传输记录，排除旧根/失败/进行中/加载与holder外预留，不是walltime/货币/能耗或收益。\n\n'
        '当前完整轨' + str(gui['batch/status.json']['value']['completed']) + '/32，整轨Mirage/官方分数/配对降幅仍未知。'
        'fresh实际UID/fullcmd/start、4–7九锁/独占compute与双链已核；0–3不动。巡检新封存回复全量SHA，旧回复重核seal并保留直接全量SHA来源回执；'
        '不称旧二进制本次又全量重哈，终局仍须全量原件复核。未热改模型/GUI/validator/图像/主完整历史/精度或任何预算。'
        '辅助仍9B基座、decision_adapter_loaded=false，单图固定v6/空首KV/结束释放；新调度真实aux推理/插入仍待enabled轨自然发生。目标ACTIVE。\n\n').encode('utf8')
    (out / 'new-head.md').write_bytes(note)
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for name, expected in before.items():
        assert sha(BASE / name) == expected
    for name in ['README.md', 'HANDOFF.md']:
        (BASE / name).write_bytes(note + (previous / name).read_bytes())
        assert (BASE / name).read_bytes() == note + (previous / name).read_bytes()
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    assert (BASE / 'full-gui-current.json').read_bytes() == (out / 'status.json').read_bytes()
    save(pointer, {'publication': str(out), 'status_sha256': sha(out / 'status.json'),
        'seal_sha256': sha(out / 'seal.json'), 'three_heads_original_byte_readback_passed': True, 'goal': 'active'})
    print(json.dumps({'publication': str(out), 'confirmed_actions': target, 'audited_replies': len(rows), 'totals': totals, 'goal': 'active'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    main(args.spec.resolve(), args.evidence.resolve())
