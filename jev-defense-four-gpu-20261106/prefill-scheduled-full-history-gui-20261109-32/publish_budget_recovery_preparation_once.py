"""Publish already sealed budget diagnosis and isolated CPU preparation.

No model, browser, scorer, runtime mutation or completed-control rerun occurs.
"""
import argparse
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import time

from publish_source_progress22_once import BASE, HERE, read, save, sha, verify_folder


def main(evidence):
    pointer = HERE / 'budget-recovery-preparation-publication-created.json'
    assert not pointer.exists()
    verify_folder(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert 0 <= time.time() - service['time'] < 300
    identities = [service['worker/process.json']['value'],
                  service['launcher-process.json']['value'],
                  gui['control/runner-process.json']['value']]
    for record in identities:
        assert not record['actual'].get('absent')
        assert record['actual']['state'] not in ['Z', 'X']
        assert all(str(record['actual'][k]) == str(record['record'][k])
                   for k in ['pid', 'uid', 'command', 'start_ticks'])
    assert service['authorized_GPUs'] == [4, 5, 6, 7]
    assert len(service['held_locks']) == 9
    assert service['authorized_GPU_actual_compute_processes']
    for row in service['authorized_GPU_actual_compute_processes']:
        assert all(str(row['actual_process'][k]) == str(identities[0]['actual'][k])
                   for k in ['pid', 'uid', 'command', 'start_ticks'])

    prep = read(HERE / 'pending-price-recovery-preparation-created.json')
    controls = read(HERE / 'pending-price-controller-controls-created.json')
    for authority in [prep, controls]:
        root = Path(authority['root'])
        verify_folder(root, authority['seal_sha256'])
        assert sha(root / 'receipt.json') == authority['receipt_sha256']
    prep_root, controls_root = Path(prep['root']), Path(controls['root'])
    prep_receipt, controls_receipt = read(prep_root / 'receipt.json'), read(controls_root / 'receipt.json')
    plan = read(prep_root / 'source-bound-budget-lower-bound.json')
    assert prep_receipt['CPU_scheduling_checks_passed'] == 22
    assert prep_receipt['original_validators_Limits_and_feedback_helpers_AST_unchanged']
    assert not prep_receipt['current32_runtime_modified'] and not prep_receipt['formal_release_ready']
    assert controls_receipt['passed'] and controls_receipt['CPU_Controller_cases'] == 5
    assert not controls_receipt['runtime_modified'] and not controls_receipt['formal_release_ready']
    assert plan['distinct_original_frames'] == plan['missing_original_frame_reads'] == 37
    assert plan['verifier_calls_before_branch'] == 102
    assert plan['remaining_original_verifier_calls'] == 38
    assert plan['minimum_additional_calls_for_acceptance'] == 40
    assert plan['no_terminal_failure_predicted_as_already_observed']

    rows, audits = [], []
    pointers = [HERE / 'prefix-audit-created.json'] + sorted(
        p for p in HERE.glob('new-replies-*-audit-created.json')
        if re.fullmatch(r'new-replies-\d+-audit-created\.json', p.name))
    for p in pointers:
        authority = read(p)
        ap = Path(authority['audit'])
        verify_folder(ap.parent)
        assert sha(ap) == authority['audit_sha256']
        audit = read(ap)
        assert audit['passed']
        if int(audit['requests'][0]['request']) > 81:
            continue
        assert int(audit['requests'][-1]['request']) <= 81
        rows.extend(audit['requests'])
        audits.append(authority)
    rows.sort(key=lambda row: row['request'])
    assert [row['request'] for row in rows] == [str(i).zfill(4) for i in range(1, 82)]
    assert all(row['natural_EOS'] for row in rows)
    assert sum(row['operation'] == 'actor' for row in rows) == 21
    assert sum(row['operation'] == 'judge' for row in rows) == 60
    totals = dict(requests=len(rows), actor_replies=21, judge_replies=60, auxiliary_replies=0,
                  natural_EOS_replies=len(rows),
                  input_tokens=sum(row['actual_input_tokens'] for row in rows),
                  output_tokens=sum(row['output_tokens'] for row in rows),
                  summed_native_call_timer_seconds=sum(row['native_call_timer_seconds'] for row in rows),
                  scope='Only sealed new32 native requests1..81. Includes original instrumentation/transfers; excludes failed/ongoing work, other roots, load and outside-holder reservation. Not walltime, currency, energy or savings.')
    old = read(BASE / 'full-gui-current.json')
    assert old['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] == '0076'
    assert old['confirmed_original_actions_total'] == 36
    stamp = str(time.time_ns())
    out = HERE / ('budget-recovery-preparation-publication-' + stamp)
    out.mkdir()
    previous = out / 'previous-heads'
    previous.mkdir()
    before = {}
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        (previous / name).write_bytes((BASE / name).read_bytes())
        before[name] = sha(BASE / name)
    status = copy.deepcopy(old)
    status.update(schema='GUI32-budget-lower-bound-and-isolated-recovery-preparation-v1',
                  time=time.time(), goal='active', monitor_should_remain_active=True,
                  previous_heads_SHA256=before, efficacy_established=False,
                  relative_Mirage_reduction=None,
                  current_goal_turn_classification='Progress: audited only new77..81 and published already sealed source-bound budget diagnosis plus isolated scheduling/Controller CPU preparation. No new inference or GUI calls, no runtime condition change, no efficacy result.',
                  native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request='0081',
                  new32_audited_completed_prefix_totals=totals)
    status['pending_price_budget_preparation'] = dict(
        source_bound_branch_entry_plan=plan,
        original_cache_and_branch_evidence=str(prep_root / 'actual-original-cache-and-branch-evidence.json'),
        isolated_preparation=prep, CPU_Controller_controls=controls,
        current32_runtime_modified=False, original_budget_and_validators_unchanged=True,
        real_model_negative_WAIT_controls_completed=False, formal_release_ready=False,
        lower_bound_is_not_an_observed_terminal=True,
        branch_entry_cannot_accept_current_candidate_within_remaining_original_budget=True,
        future_condition_tradeoff=prep_receipt['declared_condition_tradeoff'],
        new_model_GUI_scorer_paid_calls=0)
    status['authorities'].update(
        latest_actual_UID_locks_requests_chains=dict(path=str(evidence), seal_sha256=sha(evidence / 'seal.json')),
        latest_nonoverlapping_native_request_audits=audits,
        pending_price_recovery_preparation=prep, pending_price_Controller_CPU_controls=controls)
    for key, filename in [('actual_service_state_at_snapshot', 'worker/status.json'),
                          ('actual_worker_identity_at_snapshot', 'worker/process.json'),
                          ('actual_launcher_identity_at_snapshot', 'launcher-process.json')]:
        status[key] = service[filename]['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'], status['GUI_event_chains'] = service['chains'], gui['chains']
    status['new32_sealed_requests_at_snapshot'] = service['sealed_requests']
    status['new32_terminals_at_snapshot'] = gui['terminals']
    status['inspection_verification_scope'] = service['incremental_inspection_policy']
    status['storage_at_snapshot'] = dict(service=service['filesystem'], GUI=gui['filesystem'],
                                       no_original_files_deleted_moved_or_compressed=True)
    status['next_action'] = ('Keep the same frozen32 running; never hot-apply the isolated scheduling copy or rerun terminal controls. '
        'Source-review new candidates before actual checker/execution joins, audit only82+ next, preserve exact remaining original budgets. '
        'Finish the mixed native/HTTP/aux cache/GPU-cycle/insertion audit before certifying enabled calls. '
        'Independent new source-bound real negative/WAIT controls and full GUI efficacy remain unverified; goal active.')
    save(out / 'status.json', status)
    date = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    head = ('## 最新：' + date + ' 新32历史价格分支预算下限已来源绑定；恢复调度仅隔离准备，当前32未改\n\n'
        '权威 `' + (out / 'status.json').relative_to(BASE).as_posix() + '`。决策37的候选38进入历史价格分支前，'
        '真实judge已用102/140，剩38；37张独特原图从空分支缓存开始，37逐图读取+1关系+2点击检查至少需40次。'
        '这是该候选无法在余预算完成接受的调用下限，不能提前当作已经终局失败。当前原冻结运行照常继续，不加预算、不热改。\n\n'
        '已封存隔离Controller副本及差异：预算不足则将该断言保持pending、拒绝执行该候选，使用原有recapture/regeneration重提；'
        '不提供正确价格/目标/动作，新候选仍过完整原检查。已拒候选不再耗point/appearance。'
        '22调度边界+5真实Controller代码的脚本CPU流程检查通过；actor/judge/recapture均是脚本callbacks，'
        '不是新模型negative/WAIT语义控制或防御成功。严格validator/Limits/完整原图历史不变；formal_release_ready=false。'
        '代价是本可用更多预算查明的断言保留未知，仍可能最终阻断；末尾探索提醒仅文本准备。\n\n'
        '新32已不重叠审计81自然EOS=21actor+60judge，0aux；累计' + str(totals['input_tokens']) + 'input/'
        + str(totals['output_tokens']) + 'output，' + str(round(totals['summed_native_call_timer_seconds'], 3))
        + 'summed native计时秒，不是walltime/货币/能耗或收益。独立tokenizer仅原已声明范围，未称81全部独立重解码。'
        '实际UID/fullcmd/start、4–7独占compute/九锁/双链核对；旧二进制保持既有全量SHA权威，终局仍须原件全核。'
        '已来源审查候选至38、确认执行36动作，完整轨' + str(gui['batch/status.json']['value']['completed']) + '/32。'
        '辅助仍9B基座/decision_adapter_loaded=false，整轨Mirage、误拦率、官方成功和配对效果仍未知。目标ACTIVE。\n\n')
    (out / 'new-head.md').write_text(head, encoding='utf8')
    report = ('# 新32分页误拒绝与核验预算恢复准备\n\n'
        '当前实验尚未产生完整匹配轨效果结论。原候选37的正常分页被误拒绝已单独封存；原候选38仍按冻结流程检查。'
        '本报告只发布来源绑定诊断和隔离CPU准备，未改正在运行的32轨。\n\n'
        + head[head.index('权威 '):]
        + '\n隔离准备回执：`' + str(prep_root / 'receipt.json') + '`。\n\n'
        + 'Controller CPU流程回执：`' + str(controls_root / 'receipt.json') + '`。\n\n'
        + '实际分支/缓存证据：`' + str(prep_root / 'actual-original-cache-and-branch-evidence.json') + '`。\n\n'
        + '当前辅助实际prompt和同版真实预检回复：`' + str(BASE / 'prompt-output-disclosure-1794236291744372700/README.md') + '`。\n\n'
        + '后续只审新封存调用和新候选；辅助开启后的完整来源审计与独立新模型语义控制仍须完成。'
        + '不把小样本开发、少执行、阻断或CPU通过折算成Mirage降幅。\n')
    report_name = '新32分页误拒绝与核验预算恢复准备-20261110.md'
    assert not (BASE / report_name).exists()
    (out / report_name).write_text(report, encoding='utf8')
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for name, expected in before.items():
        assert sha(BASE / name) == expected
    note = (out / 'new-head.md').read_bytes()
    for name in ['README.md', 'HANDOFF.md']:
        (BASE / name).write_bytes(note + (previous / name).read_bytes())
        assert (BASE / name).read_bytes() == note + (previous / name).read_bytes()
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    (BASE / report_name).write_bytes((out / report_name).read_bytes())
    assert sha(BASE / 'full-gui-current.json') == sha(out / 'status.json')
    assert sha(BASE / report_name) == sha(out / report_name)
    result = dict(publication=str(out), status_sha256=sha(out / 'status.json'),
                  seal_sha256=sha(out / 'seal.json'), report=str(BASE / report_name),
                  three_heads_original_byte_readback_passed=True, goal='active')
    save(pointer, result)
    print(__import__('json').dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    main(parser.parse_args().evidence.resolve())
