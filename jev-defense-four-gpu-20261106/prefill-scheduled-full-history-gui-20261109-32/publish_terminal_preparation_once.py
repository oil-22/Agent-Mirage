"""Publish source-bound terminal preparation without changing the running32."""
import argparse
import copy
from pathlib import Path
import re
import time

from publish_source_progress22_once import BASE, HERE, read, save, sha, verify_folder


def main(evidence):
    pointer=HERE/'terminal-preparation-publication-created.json'
    assert not pointer.exists()
    verify_folder(evidence)
    service,gui=read(evidence/'3090.json'),read(evidence/'4090.json')
    assert 0<=time.time()-service['time']<240
    records=[service['worker/process.json']['value'],service['launcher-process.json']['value'],
             gui['control/runner-process.json']['value']]
    for row in records:
        assert not row['actual'].get('absent')and row['actual']['state']not in ['Z','X']
        assert all(str(row['actual'][k])==str(row['record'][k])for k in ['pid','uid','command','start_ticks'])
    assert service['authorized_GPUs']==[4,5,6,7]and len(service['held_locks'])==9
    assert service['authorized_GPU_actual_compute_processes']
    for row in service['authorized_GPU_actual_compute_processes']:
        assert all(str(row['actual_process'][k])==str(records[0]['actual'][k])for k in ['pid','uid','command','start_ticks'])
    preparation={}
    for name in ['terminal-classification-preparation-created.json','logical-terminal-collection-preparation-created.json']:
        authority=read(HERE/name);verify_folder(authority['root'],authority['seal_sha256'])
        receipt=Path(authority['root'])/'receipt.json'
        assert sha(receipt)==authority['receipt_sha256']and read(receipt)['passed']
        preparation[name]=authority
    pending=HERE/'logical-terminal-collection-1794249638948911900'
    verify_folder(pending)
    assert read(pending/'receipt.json')['ready']is False
    totals=dict(input_tokens=0,output_tokens=0,native_call_timer_seconds=0.0)
    authorities=[];rows=[]
    paths=[HERE/'prefix-audit-created.json']+sorted(p for p in HERE.glob('new-replies-*-audit-created.json')
        if re.fullmatch(r'new-replies-\d+-audit-created\.json',p.name))
    for path in paths:
        authority=read(path);assert sha(authority['audit'])==authority['audit_sha256']
        audit=read(authority['audit']);assert audit['passed'];rows.extend(audit['requests']);authorities.append(authority)
        for key in totals:totals[key]+=audit['totals'][key]
    rows.sort(key=lambda row:row['request'])
    assert [row['request']for row in rows]==[str(i).zfill(4)for i in range(1,len(rows)+1)]
    assert rows[-1]['request']=='0106'
    counts={op:sum(row['operation']==op for row in rows)for op in ['actor','judge']}
    out=HERE/('terminal-preparation-publication-'+str(time.time_ns()));out.mkdir()
    previous=out/'previous-heads';previous.mkdir();before={}
    for name in ['README.md','HANDOFF.md','full-gui-current.json']:
        (previous/name).write_bytes((BASE/name).read_bytes());before[name]=sha(BASE/name)
    status=copy.deepcopy(read(BASE/'full-gui-current.json'))
    status.update(time=time.time(),goal='active',monitor_should_remain_active=True,previous_heads_SHA256=before,
        previous_goal_turn_classification='progress',previous_goal_turn_authority='matched-analysis-preparation-publication-created.json')
    status['terminal_classification_preparation']=dict(authority=preparation['terminal-classification-preparation-created.json'],
        synthetic_CPU_checks=12,deployed=False,actual_budget_terminal_not_yet_replayed=True,
        exact_runner_AST_only_outcome_classification_change_verified=True,
        no_extra_model_GUI_retries_or_recovery_granted=True,
        report=str(BASE/'新32终局分类与原件封存准备-20261110.md'))
    status['logical_terminal_collection_preparation']=dict(authority=preparation['logical-terminal-collection-preparation-created.json'],
        synthetic_CPU_checks=12,actual_pending_observation=dict(path=str(pending),seal_sha256=sha(pending/'seal.json')),
        semantic_coverage_and_efficacy_not_established=True,remaining_queue_not_stopped_or_modified=True)
    status['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request']='0106'
    status['nonoverlapping_native_audit_authorities']=authorities
    status['new32_native_audit_summary']=dict(completed_calls=len(rows),operations=counts,totals=totals,
        timing_not_walltime_currency_or_energy=True,independent_tokenizer_decode_not_claimed_for_all_calls=True)
    status['new32_audited_completed_prefix_totals']=dict(requests=len(rows),actor_replies=counts['actor'],judge_replies=counts['judge'],
        auxiliary_replies=0,natural_EOS_replies=len(rows),input_tokens=totals['input_tokens'],output_tokens=totals['output_tokens'],
        summed_native_call_timer_seconds=totals['native_call_timer_seconds'],
        scope='Only sealed new32native1..106, including original instrumentation/transfers. Excludes failures/ongoing work, other roots, load and outside-holder reservation. Not walltime/currency/energy/savings.')
    for key,name in [('actual_service_state_at_snapshot','worker/status.json'),('actual_worker_identity_at_snapshot','worker/process.json'),
                     ('actual_launcher_identity_at_snapshot','launcher-process.json')]:status[key]=service[name]['value']
    status['actual_GUI_state_at_snapshot']=gui['batch/status.json']['value']
    status['actual_GUI_runner_identity_at_snapshot']=gui['control/runner-process.json']['value']
    status['service_event_chains'],status['GUI_event_chains']=service['chains'],gui['chains']
    status['new32_sealed_requests_at_snapshot'],status['new32_terminals_at_snapshot']=service['sealed_requests'],gui['terminals']
    status['authorities']['latest_actual_UID_locks_requests_chains']=dict(path=str(evidence),seal_sha256=sha(evidence/'seal.json'))
    status['next_action']=('Same actual worker/GUI continue unchanged. When first track ends, source-review any new candidates before outcome join; '
        'collect_logical_terminal_once.py binds all GUI/request original SHA, /end, original140cap and scorer. '
        'If original budget exhaustion is labelled verifier_failure, preserve original first, replay isolated classification on actual receipts and inspect actual exits. '
        'Never rerun that completed logical failure or directly restart frozen32. Remaining31 may need a newly source-linked orchestration attempt with zero fresh-track carryover counts; '
        'same original order/full inputs/strict validators/budgets, no new defense condition. Actual source review and decision about original terminal classification still required. '
        'Audit only new107+ next; actual enabled auxiliary mixed chain and all32/16pair outcomes remain outstanding; goal active.')
    save(out/'status.json',status)
    current=service['worker/status.json']['value'];completed=gui['batch/status.json']['value']['completed']
    note=('## 最新：2026-11-10 终局预算/技术分类风险已源码绑定；仅隔离准备，原32继续不改\n\n'
        '权威 `'+(out/'status.json').relative_to(BASE).as_posix()+'`。原core达到140cap会本地抛BudgetExhausted，'
        'runner却按verifier_error子串归为技术失败并停队列。已隔离准备精确受控原因+140/140分类，12项合成CPU检查及'
        '整runner仅该处替换的AST核对通过；保留原分类、真传输/契约/评分失败，候选仍不执行、0额外调用/恢复。'
        '未部署、未有实际预算终局回放，不是新negative/WAIT模型语义控制或防御成功。原冻结包未改。\n\n'
        '另单轨终局收集器12项CPU来源/链/预算边界通过，原实际首轨接入仅返回no_terminal。'
        '它先核候选来源标签SHA，再关联原/end和原官方结果；终局时全核该GUI和模型请求原件SHA、链、连续预算，'
        '大文件留原处，不打断后续队列；carryover prefix仍需原权威。若实际预算终局发生，先保全原技术标签再审，'
        '不得重跑该失败轨或直接重启旧32；剩余未执行轨需新来源链接调度，不能把17actor/50judge错误带入下一新轨。\n\n'
        '新100–106共7自然EOS已审计，累计106='+str(counts['actor'])+'actor+'+str(counts['judge'])+'judge/0aux；'
        +str(totals['input_tokens'])+'input/'+str(totals['output_tokens'])+'output/'
        +format(totals['native_call_timer_seconds'],'.3f')+'summed native秒，不是walltime/货币/能耗。'
        'fresh UID/fullcmd/start、4–7独占compute/九锁/双链已核，快照actor'+str(current['counts']['actor'])
        +'/judge'+str(current['counts']['judge'])+'、完整轨'+str(completed)+'/32，未把预算下限或静态准备当作真实终局。'
        '辅助仍9B基座/decision_adapter_loaded=false，实际enabled整链和完整配对效力未建立，目标ACTIVE。\n\n').encode('utf8')
    (out/'new-head.md').write_bytes(note);(out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (out/'report.md').write_bytes((BASE/'新32终局分类与原件封存准备-20261110.md').read_bytes())
    save(out/'seal.json',{p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()})
    for name,value in before.items():assert sha(BASE/name)==value
    for name in ['README.md','HANDOFF.md']:
        (BASE/name).write_bytes(note+(previous/name).read_bytes());assert(BASE/name).read_bytes()==note+(previous/name).read_bytes()
    (BASE/'full-gui-current.json').write_bytes((out/'status.json').read_bytes())
    assert sha(BASE/'full-gui-current.json')==sha(out/'status.json')
    record=dict(publication=str(out),status_sha256=sha(out/'status.json'),seal_sha256=sha(out/'seal.json'),
        original_heads_preserved_and_readback_verified=True,goal='active')
    save(pointer,record);print(__import__('json').dumps(record))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True)
    main(p.parse_args().evidence.resolve())
