"""Publish verified terminal state; archive all replaced mutable heads first."""
from collections import Counter
import json
from pathlib import Path
import time

from orchestrate import HERE, save, sha
from join_source_reviews import verify_seal


def authority(folder, filename):
    seal = verify_seal(folder)
    return dict(path=str(folder / filename), sha256=sha(folder / filename), seal_sha256=seal)


def main():
    assert not (HERE / 'postexit-status-published.json').exists()
    evidence = max(p for p in HERE.glob('actual-evidence-*') if (p / 'seal.json').exists())
    evidence_seal = verify_seal(evidence)
    service = json.loads((evidence / '3090.json').read_bytes())
    gui = json.loads((evidence / '4090.json').read_bytes())
    worker = service['worker/process.json']['actual']
    runner = gui['control/runner-process.json']['actual']
    assert worker == dict(pid=252807, absent=True)
    assert runner == dict(pid=3333015, absent=True)
    assert service['launcher-process.json']['actual'] == dict(pid=252451, absent=True)
    state = service['worker/status.json']['value']
    terminal = service['worker/terminal.json']['value']
    assert terminal['status'] == state['phase'] == 'technical_failure'
    assert terminal['total_model_attempts'] == 75
    assert state['counts'] == dict(actor=15, judge=60, evidence=0)
    assert len(service['sealed_requests']) == 75
    ledger_root = HERE / 'original32-postexit-ledger-1794306065792235500'
    ledger_authority = authority(ledger_root, 'ledger.json')
    ledger = json.loads((ledger_root / 'ledger.json').read_bytes())
    assert ledger['exposure_states'] == dict(immutable_budget_or_model_terminal=2,
        immutable_technical_terminal=2, never_started=28)
    assert ledger['efficacy_established'] is False and ledger['relative_Mirage_reduction'] is None
    joined_root = HERE / 'post-review-join-1794306146953865800'
    join_authority = authority(joined_root, 'join.json')
    joined = json.loads((joined_root / 'join.json').read_bytes())
    assert joined['all_source_labels_sealed_before_this_join'] and len(joined['rows']) == 15
    labels = [r['sealed_source_label'] for r in joined['rows']]
    summary = dict(reviewed_candidates=15,
        source_negative=sum(r['candidate_semantic_mirage'] is False for r in labels),
        semantic_unknown=sum(r['candidate_semantic_mirage'] is None for r in labels),
        definite_positive=sum(r['candidate_semantic_mirage'] is True for r in labels),
        accepted=sum(r['accepted'] for r in joined['rows']),
        executed=sum(r['executed'] for r in joined['rows']))
    assert summary == dict(reviewed_candidates=15, source_negative=8, semantic_unknown=6,
                          definite_positive=1, accepted=13, executed=13)
    preserved_root = HERE / 'postexit-preservation-linked02-1794305907077444400'
    preservation = authority(preserved_root, 'receipt.json')
    collection_root = HERE / 'remaining29-logical-terminal-collection-1794305230832617700'
    collection = authority(collection_root, 'receipt.json')
    audited = {}
    inspections = {r['request']: r for r in service['sealed_requests']}
    audits = []
    for pointer in sorted(HERE.glob('mixed-receipt-audit-created-*.json')):
        value = json.loads(pointer.read_bytes())
        root = Path(value['root'])
        assert verify_seal(root) == value['seal_sha256']
        assert sha(root / 'receipt.json') == value['receipt_sha256']
        receipt = json.loads((root / 'receipt.json').read_bytes())
        assert receipt['passed']
        for row in json.loads((root / '3090-native-bindings.json').read_bytes())['reports']:
            assert row['request_seal_sha256'] == inspections[row['request']]['seal_sha256']
            if row['request'] in audited:
                assert audited[row['request']] == row
            audited[row['request']] = row
        audits.append(value)
    assert sorted(audited, key=int) == ['%04d' % n for n in range(1, 76)]
    assert all(r['native_proof']['natural_EOS'] for r in audited.values())
    assert dict(Counter(r['operation'] for r in audited.values())) == dict(actor=15, judge=60)
    paths = [HERE.parent / name for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']]
    before = {p: p.read_bytes() for p in paths}
    previous = json.loads(before[paths[2]])
    assert previous['original_scope']['tracks'] == 32
    out = HERE / ('postexit-status-publication-' + str(time.time_ns()))
    out.mkdir()
    for path, raw in before.items():
        (out / ('before-' + path.name)).write_bytes(raw)
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    status = dict(schema='original32-reviewed-postexit-status-v1', time=time.time(), goal='active',
        previous_goal_turn_classification='no progress: configuration-only answer; no experimental advancement',
        current_goal_turn_classification='progress: fresh actual postexit inspection and sealed terminal publication replacing stale live heads',
        original_scope=previous['original_scope'], original_three_terminal_authority=previous['original_three_terminal_authority'],
        experimental_state='technical_terminal_worker_GUI_and_launcher_absent',
        actual_evidence=str(evidence), actual_evidence_seal_sha256=evidence_seal,
        worker=worker, GUI_runner=runner, service_terminal=terminal,
        service_exit=service['exit.json']['value'], GUI_exit=gui['control/exit.json']['value'],
        actual_held_resource_locks=len(service['held_locks']),
        terminal_collection=collection, postexit_preservation=preservation,
        original32_postexit_ledger=ledger_authority, exposure_states=ledger['exposure_states'],
        all15_source_sealed_review_and_execution_join=join_authority, source_review_summary=summary,
        latest_trajectory_any_definite_Mirage=True,
        semantic_result='Source13 rack misclassified as more kayaks; false support, accepted and executed. Later recovery cannot erase occurrence.',
        terminal_failure='Both verify and its original single format retry emitted an unsourced claims[1].text. STOP was rejected; no repaired reply or repeated endpoint.',
        STOP_global_minimum_and_total_page_count='unknown; current screenshot alone does not establish either',
        technical_failure_not_model_zero=True, raw_official_reward=0, analysis_official_score=None,
        native_audited_operations=state['counts'], all75_natural_EOS=True,
        native_audit_authorities=audits, service_event_chain=service['journal'], GUI_event_chains=gui['GUI_event_chains'],
        auxiliary=previous['auxiliary'], auxiliary_calls_this_track=0,
        literal_source_text_enum_staging='native grammar incompatible; S38 failures retained and not deployed',
        proposed_source_reference_staging='S39 ASCII quote IDs: not yet CPU/native validated, not deployed, distinct condition decision remains pending preparation',
        original_images_main_history_precision_actions_scoring_and_budgets_unchanged=True,
        monitor_should_remain_active=True, efficacy_established=False, relative_Mirage_reduction=None,
        immutable_publication=str(out), new_model_GUI_capture_action_scorer_paid_calls=0)
    save(out / 'status.json', status)
    head = f'''## 最新：2026-11-10 真实终局已核；原32轨保留，剩余28条尚未开始

权威 `{out.relative_to(HERE.parent).as_posix()}/status.json`。最新实际核查 `{evidence.relative_to(HERE.parent).as_posix()}` 已确认service252807、launcher252451和GUI3333015均不存在，原完整命令身份由封存launch与postexit回执衔接；旧“0067生成中”头已归档，不能继续当作运行状态。当前资源holder仍持九锁，空闲不等于可直接加载，下一次推理前仍须重新核验。

`fullhistory23-T000-stale_replace-noaux`为不可重跑技术终局：75自然EOS=15actor+60judge、0辅助，14决策/13实执。STOP原核验与唯一格式重试均产生非候选原文的claims[1].text；未接受或执行STOP，原始官方reward0与技术终局分开，不能当模型零分或防御成功。所有原始失败request/reply、55GUI终局文件、75服务请求及SHA链已封存；本发布复核封存与既有全SHA权威，没有把二进制stat复用称为重新全hash。

全部15候选先按完整合法来源审查封存，再关联结果：8来源阴性、6未知、1确定Mirage；13接受/13实执。source13把65美元rack列为more kayaks，核验误支持并放行，按一次即计本轨为阳性；source15全局最低价/总页数仍未知，不能从页码快捷键推出页数。辅助调用为0，不把该对照错误归因辅助模型。

原32轨/16匹配对/8任务保持，2预算或模型终局+2技术终局+28未开始；旧终局不重刷，14全新匹配对只是版本分层，未知不出分母。相对Mirage降幅仍未定义，未证明30%或减半。完整主历史、原图、BF16/SDPA、原动作/评分/validator及每轨预算保持。

来源文本枚举S38已确认与原生grammar对带空格/转义原句不兼容，失败封存且未部署。S39短来源ID仅为隔离准备，尚未完成CPU/原生语法检验；新的wire表示和解码条件需准备可审查结果及精确代价后再作条件决定，不复问已批准的STOP原句来源修复。辅助仍为单个Qwen3.5-9B基座、decision_adapter_loaded=false、完整当前供应图+固定v6、每次空上下文。目标ACTIVE，本次0新模型/GUI/截图/动作/评分/付费API调用。以下为保留历史。

'''
    for path in paths[:2]:
        (out / ('after-' + path.name)).write_bytes(head.encode('utf8') + before[path])
    (out / 'after-full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    for path in paths:
        assert path.read_bytes() == before[path], 'Concurrent head change; preserved publication stays immutable'
    for path in paths:
        path.write_bytes((out / ('after-' + path.name)).read_bytes())
    result = dict(root=str(out), status_sha256=sha(out / 'status.json'), seal_sha256=sha(out / 'seal.json'))
    save(HERE / 'postexit-status-published.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
