"""Publish sealed third-source review and new nonoverlapping native replies."""
import collections
import copy
import json
from pathlib import Path
import time

from orchestrate import HERE, BASE, PACKAGE, save, sha
from join_source_reviews import verify_seal


def read(path):
    return json.loads(Path(path).read_bytes())


def main():
    pointer = HERE / 'source03-audit15-supplement-created.json'
    assert not pointer.exists()
    prior = read(HERE / 'two-actions-summary-diagnosis-publication-created.json')
    prior_root = Path(prior['root'])
    assert verify_seal(prior_root) == prior['seal_sha256']
    assert sha(BASE / 'full-gui-current.json') == prior['status_sha256']
    evidence = HERE / 'actual-evidence-1794253994926412200'
    verify_seal(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    for record in [service['worker/process.json'], service['launcher-process.json'], gui['control/runner-process.json']]:
        assert not record['actual'].get('absent') and record['actual']['state'] not in ['Z', 'X']
        assert all(str(record['actual'][key]) == str(record['value'][key]) for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert len(service['held_locks']) == 9 and service['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    reports, audit_authorities = {}, []
    sealed = {row['request']: row for row in service['sealed_requests']}
    for path in sorted(HERE.glob('mixed-receipt-audit-created-*.json')):
        authority = read(path)
        root = Path(authority['root'])
        assert verify_seal(root) == authority['seal_sha256']
        assert sha(root / 'receipt.json') == authority['receipt_sha256'] and read(root / 'receipt.json')['passed']
        for row in read(root / '3090-native-bindings.json')['reports']:
            assert row['request'] not in reports and row['native_proof']['natural_EOS']
            assert row['request_seal_sha256'] == sealed[row['request']]['seal_sha256']
            reports[row['request']] = row
        audit_authorities.append(authority)
    assert sorted(reports) == ['%04d' % n for n in range(1, 16)]
    counts = collections.Counter(row['operation'] for row in reports.values())
    assert counts == dict(actor=3, judge=9, evidence=3)
    primary = [row['native_proof'] for row in reports.values() if row['operation'] != 'evidence']
    auxiliary = [row['native_proof'] for row in reports.values() if row['operation'] == 'evidence']
    assert all(row['actual_first_cache_length'] == 0 and row['all_observed_cache_objects_released'] for row in auxiliary)
    label_authorities, labels = [], []
    for sequence in ['01', '02', '03']:
        authority = read(HERE / ('source-review-' + sequence + '-created.json'))
        root = Path(authority['review'])
        assert verify_seal(root) == authority['seal_sha256'] and sha(root / 'review.json') == authority['review_sha256']
        labels.extend(read(root / 'review.json')['rows'])
        label_authorities.append(authority)
    assert [row['candidate_semantic_mirage'] for row in labels] == [False, None, False]
    last_join = HERE / 'post-review-join-1794253966879654200'
    verify_seal(last_join)
    joined = read(last_join / 'join.json')
    assert joined['all_source_labels_sealed_before_this_join']
    row = joined['rows'][0]
    assert row['sealed_source_label'] == labels[2] and not row['accepted'] and not row['executed']
    assert not row['candidate_decision_block_events']
    repair = read(HERE / 'publication-reporting-linked02-created.json')
    assert verify_seal(Path(repair['failure_preservation'])) == repair['failure_seal_sha256']
    assert sha(repair['linked_source']) == repair['linked_source_sha256']
    before = {name: (BASE / name).read_bytes() for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']}
    status = copy.deepcopy(json.loads(before['full-gui-current.json']))
    current = status['linked_remaining31']
    current.update(state=service['worker/status.json']['value'], actual_worker=service['worker/process.json']['actual'],
        actual_GUI=gui['control/runner-process.json']['actual'], actual_holder=service['actual_holder'],
        new31_GUI_state=gui['batch/status.json']['value'], audited_requests=sorted(reports),
        audited_request_counts=dict(counts), source_reviewed_candidates=3, definite_negative_source_candidates=2,
        third_candidate=dict(id=labels[2]['id'], candidate_semantic_mirage=False, native_action_error=False,
            last_source_sealed_outcome_join=str(last_join / 'join.json'),
            last_join_sha256=sha(last_join / 'join.json'), accepted_at_last_join=False, executed_at_last_join=False,
            rejected_at_last_join=False, pending_at_last_join=True),
        primary_only_audited_totals=dict(calls=len(primary), input_tokens=sum(row['actual_input_tokens'] for row in primary),
            output_tokens=sum(row['output_tokens'] for row in primary),
            summed_native_call_timer_seconds=sum(row['native_call_timer_seconds'] for row in primary)),
        auxiliary_only_audited_totals=dict(calls=len(auxiliary), input_tokens=sum(row['actual_input_tokens'] for row in auxiliary),
            output_tokens=sum(row['output_tokens'] for row in auxiliary),
            timing_scope='Server timers include switches/instrumentation; not added to primary native timers.'))
    status.update(schema='original32-first-enabled-three-source-candidates-native15-v1', time=time.time(),
        goal='active', efficacy_established=False, relative_Mirage_reduction=None)
    status['auxiliary']['actual_stateless_GUI_calls_audited'] = 3
    status['storage']['last_available_bytes'] = service['service_storage_free_bytes']
    status['authorities'].update(actual_evidence=str(evidence), actual_evidence_seal_sha256=sha(evidence / 'seal.json'),
        all_nonoverlapping_native_audits=audit_authorities, first_three_source_reviews=label_authorities,
        third_candidate_post_source_seal_join=str(last_join / 'join.json'),
        local_reporting_failure_preservation_and_one_key_repair=repair)
    root = HERE / ('source03-audit15-supplement-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for name, raw in before.items():
        (root / ('before-' + name)).write_bytes(raw)
    save(root / 'status.json', status)
    head = '''## 最新补充：第三候选先审原三图/六消息，真实原生审计至15；同一辅助轨继续

权威 `{relative}/status.json`。新增第三候选只声称Keyword已显示blue kayak并计划Search点击，原图支持文字且native804,419落在Search内，源Mirage=false/native error=false；先封源标签再关联current结果，最近join仍pending/无accepted/无executed/无block，不推断已搜到艇。前三候选=2明确源阴性+1窄焦点未知，原两动作实际后图与审查保持，整轨Mirage/得分仍null。

0001..0015共15真实自然EOS已不重叠审计：3actor+9judge+3aux。第三aux0013→actor0014实际单图固定v6/首KV0/释放/原生IDs/tensors/HTTP/GPU切换及完整6消息3图插入通过；aux仍9B基座/decision_adapter_loaded=false，格式不是语义通过。首两条180字符边界诊断与未发送短句草案保持，当前运行源码/提示/图像/完整主历史/严格validator和预算无热改。

最新双机UID/fullcmd/start/4–7九锁/独占compute/双链证明同一worker32383与GUI322908在运行，0016 judge生成；remaining31完整终局0/31，原32首个预算终局不重跑。仅本地汇总字段batch/state.json误名导致0调用KeyError，原源码/输入/错误/未改heads已封存；新linked02只改为实际batch/status.json并已成功发布/readback，不影响运行、结果、标签或预算。目标ACTIVE，原32/16对/8任务与可观Mirage降幅仍未完成。继续同一队列，不重新stage/service/gui。

'''.format(relative=root.relative_to(BASE).as_posix())
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == before[name]
        (BASE / name).write_bytes(head.encode('utf8') + before[name])
    assert (BASE / 'full-gui-current.json').read_bytes() == before['full-gui-current.json']
    (BASE / 'full-gui-current.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == head.encode('utf8') + before[name]
    assert read(BASE / 'full-gui-current.json') == status
    save(root / 'receipt.json', dict(time=time.time(), passed=True, original_heads_preserved=True,
        all_three_new_heads_readback_verified=True, current_runtime_conditions_unchanged=True,
        source_labels_unchanged=True, new_model_GUI_scorer_calls=0, defense_efficacy_established=False))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    authority = dict(root=str(root), status_sha256=sha(root / 'status.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, authority)
    print(json.dumps(authority))


if __name__ == '__main__':
    main()
