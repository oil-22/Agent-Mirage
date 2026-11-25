"""Publish immutable analysis preparation alongside current live evidence."""
import argparse
import copy
from pathlib import Path
import re
import time

from publish_source_progress22_once import BASE, HERE, read, save, sha, verify_folder


def main(evidence):
    pointer = HERE / 'matched-analysis-preparation-publication-created.json'
    assert not pointer.exists()
    verify_folder(evidence)
    service, gui = read(evidence/'3090.json'), read(evidence/'4090.json')
    assert 0 <= time.time() - service['time'] < 240
    identities = [service['worker/process.json']['value'], service['launcher-process.json']['value'],
                  gui['control/runner-process.json']['value']]
    for identity in identities:
        assert not identity['actual'].get('absent') and identity['actual']['state'] not in ['Z','X']
        assert all(str(identity['actual'][key]) == str(identity['record'][key])
                   for key in ['pid','uid','command','start_ticks'])
    assert service['authorized_GPUs'] == [4,5,6,7] and len(service['held_locks']) == 9
    assert service['authorized_GPU_actual_compute_processes']
    for row in service['authorized_GPU_actual_compute_processes']:
        assert all(str(row['actual_process'][key]) == str(identities[0]['actual'][key])
                   for key in ['pid','uid','command','start_ticks'])
    preparation = read(HERE/'matched-analysis-preparation-created.json')
    verify_folder(preparation['root'], preparation['seal_sha256'])
    receipt = Path(preparation['root'])/'receipt.json'
    assert sha(receipt) == preparation['receipt_sha256'] and read(receipt)['passed']
    logs = (Path(preparation['root'])/'checks.stderr.txt').read_text(encoding='utf8')
    assert re.search(r'Ran 35 tests in ', logs) and logs.rstrip().endswith('OK')
    audit_pointers = [HERE/'prefix-audit-created.json'] + sorted(p for p in HERE.glob('new-replies-*-audit-created.json')
        if re.fullmatch(r'new-replies-\d+-audit-created\.json',p.name))
    audits, rows = [], []
    totals = dict(input_tokens=0, output_tokens=0, native_call_timer_seconds=0.0)
    for path in audit_pointers:
        authority = read(path)
        assert sha(authority['audit']) == authority['audit_sha256']
        audit = read(authority['audit'])
        assert audit['passed']
        rows.extend(audit['requests'])
        audits.append(authority)
        for key in totals:
            totals[key] += audit['totals'][key]
    rows.sort(key=lambda row:row['request'])
    assert [row['request'] for row in rows] == [str(i).zfill(4) for i in range(1,len(rows)+1)]
    assert rows[-1]['request'] == '0099'
    counts = {op:sum(row['operation']==op for row in rows) for op in ['actor','judge']}
    out = HERE/('matched-analysis-preparation-publication-'+str(time.time_ns()))
    out.mkdir()
    previous = out/'previous-heads'
    previous.mkdir()
    before = {}
    for name in ['README.md','HANDOFF.md','full-gui-current.json']:
        (previous/name).write_bytes((BASE/name).read_bytes())
        before[name] = sha(BASE/name)
    status = copy.deepcopy(read(BASE/'full-gui-current.json'))
    status.update(time=time.time(),goal='active',monitor_should_remain_active=True,previous_heads_SHA256=before)
    status['matched_descriptive_analysis_preparation'] = dict(authority=preparation, synthetic_CPU_checks=35,
        report=str(BASE/'新32配对分析口径与边界检查-20261110.md'),
        actual32_result_records_fed_to_analysis=False,
        prepared_after_review38_and_known_normal_pagination_false_rejection=True,
        fully_blind_preregistration=False, frozen_runtime_modified=False,
        actual_sources_and_receipt_joins_not_verified_by_mathematical_flags=True,
        no_efficacy_or_goal_completion_established=True)
    status['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'] = '0099'
    status['nonoverlapping_native_audit_authorities'] = audits
    status['new32_native_audit_summary'] = dict(completed_calls=len(rows),operations=counts,totals=totals,
        timing_not_walltime_currency_or_energy=True,new_model_GUI_scorer_calls=0,
        independent_tokenizer_decode_not_claimed_for_all_calls=True)
    status['new32_audited_completed_prefix_totals'] = dict(requests=len(rows),actor_replies=counts['actor'],
        judge_replies=counts['judge'],auxiliary_replies=0,natural_EOS_replies=len(rows),
        input_tokens=totals['input_tokens'],output_tokens=totals['output_tokens'],
        summed_native_call_timer_seconds=totals['native_call_timer_seconds'],
        scope='Only sealed new32native1..99, including original instrumentation/transfers. Excludes failures/ongoing work, other roots, load and outside-holder reservation. Not walltime/currency/energy/savings.')
    for key,name in [('actual_service_state_at_snapshot','worker/status.json'),
                     ('actual_worker_identity_at_snapshot','worker/process.json'),
                     ('actual_launcher_identity_at_snapshot','launcher-process.json')]:
        status[key] = service[name]['value']
    status['actual_GUI_state_at_snapshot'] = gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot'] = gui['control/runner-process.json']['value']
    status['service_event_chains'],status['GUI_event_chains'] = service['chains'],gui['chains']
    status['new32_sealed_requests_at_snapshot'],status['new32_terminals_at_snapshot'] = service['sealed_requests'],gui['terminals']
    status['authorities']['latest_actual_UID_locks_requests_chains'] = dict(path=str(evidence),seal_sha256=sha(evidence/'seal.json'))
    status['next_action'] = ('Continue same verified worker/GUI with original budgets and no runtime hot edit. '
        'On first logical terminal preserve all sources, chains and official score; never rerun completed failures. '
        'Audit only new100+; perform source-first actor review and composed mixed audit when actual enabled actor appears. '
        'Use prepared math only after externally verified original source/execution/score joins; full32/16pairs still required. '
        'Goal active; no efficacy established.')
    save(out/'status.json',status)
    current=service['worker/status.json']['value']
    completed=gui['batch/status.json']['value'].get('completed')
    note=('## 最新：2026-11-10 新32配对分析35项合成CPU边界检查通过；真实请求审计至99，未输入实际轨迹结果\n\n'
        '权威 `'+(out/'status.json').relative_to(BASE).as_posix()+'`。分析保持32轨/16对/8任务、一次即计与纯WAIT排除；'
        'pending/技术失败/缺失不作零，零基线相对量未定义；评分、误拒绝和较少操作机会单列，clean/stale分别检查。'
        '8任务簇参考和bootstrap仅来源选定数据的描述性补充。准备发生在候选38审查和已知正常分页误拒绝之后，'
        '不是全盲预注册；35项为合成CPU检查，没有向工具输入实际32结果、没有新推理/GUI/评分或热改冻结包。\n\n'
        '新增92–99共8个真实自然EOS核验回复已严格来源审计；累计99='+str(counts['actor'])+'actor+'
        +str(counts['judge'])+'judge、0aux，'+str(totals['input_tokens'])+'input/'+str(totals['output_tokens'])
        +'output/'+format(totals['native_call_timer_seconds'],'.3f')+'summed native秒，不是walltime/货币/能耗。'
        '实际UID/fullcmd/start、4–7独占compute/九锁/双链已核；快照actor'+str(current['counts']['actor'])
        +'/judge'+str(current['counts']['judge'])+'，完整轨'+str(completed)+'/32，状态'+str(current['phase'])
        +'。未终局不重启，未执行候选不计动作。辅助仍9B基座/decision_adapter_loaded=false；'
        '完整32实证和配对效果尚未建立，目标ACTIVE。\n\n').encode('utf8')
    (out/'new-head.md').write_bytes(note)
    (out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (out/'report.md').write_bytes((BASE/'新32配对分析口径与边界检查-20261110.md').read_bytes())
    save(out/'seal.json',{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
    for name,value in before.items():
        assert sha(BASE/name)==value
    for name in ['README.md','HANDOFF.md']:
        (BASE/name).write_bytes(note+(previous/name).read_bytes())
        assert (BASE/name).read_bytes()==note+(previous/name).read_bytes()
    (BASE/'full-gui-current.json').write_bytes((out/'status.json').read_bytes())
    assert sha(BASE/'full-gui-current.json')==sha(out/'status.json')
    record=dict(publication=str(out),status_sha256=sha(out/'status.json'),seal_sha256=sha(out/'seal.json'),
                original_heads_preserved_and_new_heads_readback_verified=True,goal='active')
    save(pointer,record)
    print(__import__('json').dumps(record))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path,required=True)
    main(parser.parse_args().evidence.resolve())
