"""Publish verified new source/audit progress without editing the frozen experiment."""
import argparse
import collections
import copy
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, BASE, PACKAGE, save, sha
from join_source_reviews import verify_seal


def read(path):
    return json.loads(Path(path).read_bytes())


def authority_record(path, folder_key, content_name, hash_key):
    authority = read(path)
    folder = Path(authority[folder_key])
    assert folder.parent == HERE
    assert verify_seal(folder) == authority['seal_sha256']
    assert sha(folder / content_name) == authority[hash_key]
    return authority, read(folder / content_name)


def main(evidence, through, note_file):
    assert evidence.parent == HERE and note_file.parent == HERE
    verify_seal(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    for record in [service['worker/process.json'], service['launcher-process.json'], gui['control/runner-process.json']]:
        actual = record['actual']
        assert not actual.get('absent') and actual['state'] not in ['Z', 'X']
        assert all(str(actual[key]) == str(record['value'][key]) for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert len(service['held_locks']) == 9 and service['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    manifest = read(PACKAGE / 'manifest.json')
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    GUI_state = gui['batch/status.json']['value']
    assert GUI_state['phase'] == 'running', 'A terminal requires collection, not a running-progress publication'
    sealed = {row['request']: row for row in service['sealed_requests']}
    requests, audits = {}, []
    for path in sorted(HERE.glob('mixed-receipt-audit-created-*.json')):
        authority, receipt = authority_record(path, 'root', 'receipt.json', 'receipt_sha256')
        assert receipt['passed']
        data = read(Path(authority['root']) / '3090-native-bindings.json')
        for row in data['reports']:
            ident = row['request']
            assert row['native_proof']['natural_EOS']
            assert row['request_seal_sha256'] == sealed[ident]['seal_sha256']
            if ident in requests:
                assert row == requests[ident], 'Repeated audits must agree and must not add another model call'
            else:
                requests[ident] = row
        audits.append(authority)
    assert sorted(requests) == ['%04d' % n for n in range(1, through + 1)]
    labels, source_authorities = {}, []
    for path in sorted(HERE.glob('source-review-*-created.json')):
        if not re.fullmatch(r'source-review-\d+-created\.json', path.name):
            continue
        authority, review = authority_record(path, 'review', 'review.json', 'review_sha256')
        assert review['independent_current_checker_execution_score_join_not_performed']
        for row in review['rows']:
            assert row['id'] not in labels
            assert sha(row['public_source_packet']) == row['packet_sha256']
            labels[row['id']] = row
        source_authorities.append(authority)
    posts, post_authorities = {}, []
    for path in [HERE / 'initial-two-postexecution-review-created.json', *sorted(HERE.glob('postexecution-review-*-created.json'))]:
        authority, review = authority_record(path, 'root', 'review.json', 'review_sha256')
        for row in review['reports']:
            assert row['id'] not in posts and row['original_source_label'] == labels[row['id']]
            assert row['accepted'] and row['executed'] and row['source_label_unchanged']
            assert sha(row['original_postexecution_image']) == row['original_postexecution_image_sha256']
            posts[row['id']] = row
        post_authorities.append(authority)
    latest_joins = {}
    for folder in sorted(HERE.glob('post-review-join-*')):
        if not folder.is_dir():
            continue
        verify_seal(folder)
        joined = read(folder / 'join.json')
        assert joined['all_source_labels_sealed_before_this_join']
        for row in joined['rows']:
            assert row['sealed_source_label'] == labels[row['id']]
            record = dict(join=str(folder / 'join.json'), join_sha256=sha(folder / 'join.json'),
                candidate_event_sha256=row['candidate_event_sha256'], snapshot=row['snapshot'],
                accepted_at_last_join=row['accepted'], executed_at_last_join=row['executed'],
                blocked_at_last_join=bool(row['candidate_decision_block_events']))
            old = latest_joins.get(row['id'])
            if old is None or row['snapshot']['count'] >= old['snapshot']['count']:
                latest_joins[row['id']] = record
    note = read(note_file)
    assert note['goal_turn_classification'] == 'progress' and isinstance(note['findings'], list)
    before = {name: (BASE / name).read_bytes() for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']}
    status = copy.deepcopy(json.loads(before['full-gui-current.json']))
    current = status['linked_remaining31']
    assert through > len(current['audited_requests']) or len(labels) > current['source_reviewed_candidates'] or len(posts) > current['confirmed_accepted_and_executed_actions_with_original_after_images']
    counts = collections.Counter(row['operation'] for row in requests.values())
    primary = [row['native_proof'] for row in requests.values() if row['operation'] != 'evidence']
    auxiliary = [row['native_proof'] for row in requests.values() if row['operation'] == 'evidence']
    assert all(row['actual_first_cache_length'] == 0 and row['all_observed_cache_objects_released'] for row in auxiliary)
    current.update(state=service['worker/status.json']['value'], new31_GUI_state=GUI_state,
        actual_worker=service['worker/process.json']['actual'], actual_GUI=gui['control/runner-process.json']['actual'],
        actual_holder=service['actual_holder'], actual_held_locks=9, audited_requests=sorted(requests),
        audited_request_counts=dict(counts), source_reviewed_candidates=len(labels),
        definite_negative_source_candidates=sum(row['candidate_semantic_mirage'] is False and not row['unresolved_subclaims'] for row in labels.values()),
        definite_positive_source_candidates=sum(row['candidate_semantic_mirage'] is True and not row['pure_native_WAIT_excluded'] for row in labels.values()),
        unresolved_source_candidate_ids=[row['id'] for row in labels.values() if row['candidate_semantic_mirage'] is None or row['unresolved_subclaims']],
        latest_source_sealed_outcome_joins=latest_joins,
        confirmed_accepted_and_executed_actions_with_original_after_images=len(posts),
        normal_action_target_outcomes_locally_corroborated=sum(row.get('normal_action_target_outcome_locally_corroborated', row.get('normal_target_outcome_locally_corroborated', False)) for row in posts.values()),
        primary_only_audited_totals=dict(calls=len(primary), input_tokens=sum(row['actual_input_tokens'] for row in primary),
            output_tokens=sum(row['output_tokens'] for row in primary),
            summed_native_call_timer_seconds=sum(row['native_call_timer_seconds'] for row in primary)),
        auxiliary_only_audited_totals=dict(calls=len(auxiliary), input_tokens=sum(row['actual_input_tokens'] for row in auxiliary),
            output_tokens=sum(row['output_tokens'] for row in auxiliary), timing_scope='Server timers include switches/instrumentation; not added to primary native timers.'))
    status.update(schema='original32-verified-source-execution-progress-v1', time=time.time(),
        previous_goal_turn_classification='progress', current_goal_turn_classification=note['progress_basis'],
        goal='active', monitor_should_remain_active=True, efficacy_established=False, relative_Mirage_reduction=None,
        latest_findings=note['findings'], original32_all_verified_complete=False)
    status['auxiliary']['actual_stateless_GUI_calls_audited'] = len(auxiliary)
    status['storage']['last_available_bytes'] = service['service_storage_free_bytes']
    status['authorities'].update(actual_evidence=str(evidence), actual_evidence_seal_sha256=sha(evidence / 'seal.json'),
        all_nonoverlapping_native_audits=audits, all_current_source_reviews=source_authorities,
        all_postexecution_visual_reviews=post_authorities)
    root = HERE / ('progress-publication-' + str(time.time_ns()))
    root.mkdir()
    for name, raw in before.items():
        (root / ('before-' + name)).write_bytes(raw)
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (root / 'supplied-progress-note.json').write_bytes(note_file.read_bytes())
    save(root / 'status.json', status)
    findings = '\n\n'.join(note['findings'])
    state = current['state']
    head = ('## 最新：2026-11-10 ' + note['title'] + '\n\n权威 `' + root.relative_to(BASE).as_posix() + '/status.json`。\n\n'
        + findings + '\n\n真实回复已连续审计至' + str(through) + '，操作构成为' + json.dumps(dict(counts), ensure_ascii=False)
        + '；主模型与辅助计时分开，不是walltime/货币/能耗或收益。源候选审查' + str(len(labels))
        + '，已关联实执并读原后图' + str(len(posts)) + '；未知不作阴性，纯native WAIT排除。'
        + '当前' + str(state.get('request')) + '/' + str(state.get('operation')) + '/' + str(state.get('phase'))
        + '，同一实际UID/fullcmd/start/4–7九锁/独占compute/双链已核，0–3不动。\n\n'
        + '原32/16对/8源选任务范围与原预算不变；原首个预算终局与候选38未知/误拒/中断保留，剩余31当前'
        + str(GUI_state['completed']) + '/31完整终局。辅助仍9B基座/decision_adapter_loaded=false，单完整当前供应图+固定v6/首KV0/结束释放；'
        + '原主完整历史/图像/BF16/SDPA/原生动作/strict validator不变，180字符诊断与未发送短句草案没有热改运行。'
        + '不能将正常局部操作、格式、阻断或官方成功当效力。目标ACTIVE，继续同一队列，禁止重启stage/service/gui或已完成失败轨。\n\n')
    (root / 'report.md').write_text(head, encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == before[name]
        (BASE / name).write_bytes(head.encode('utf8') + before[name])
    assert (BASE / 'full-gui-current.json').read_bytes() == before['full-gui-current.json']
    (BASE / 'full-gui-current.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == head.encode('utf8') + before[name]
    assert read(BASE / 'full-gui-current.json') == status
    save(root / 'receipt.json', dict(time=time.time(), passed=True, old_heads_preserved=True,
        all_three_new_heads_readback_verified=True, source_labels_and_experiment_conditions_unchanged=True,
        new_model_GUI_scorer_calls=0, goal_completion_or_efficacy_established=False))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    authority = dict(root=str(root), status_sha256=sha(root / 'status.json'), seal_sha256=sha(root / 'seal.json'))
    save(HERE / ('progress-publication-created-' + root.name.rsplit('-', 1)[1] + '.json'), authority)
    print(json.dumps(authority))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--audited-through', type=int, required=True)
    parser.add_argument('--note-file', type=Path, required=True)
    args = parser.parse_args()
    main(args.evidence.resolve(), args.audited_through, args.note_file.resolve())
