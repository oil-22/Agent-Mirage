"""Publish verified postexit progress; archive stale running heads unchanged."""
import collections
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import time

import orchestrate as current


def verified(path):
    for name,digest in json.loads((path/'seal.json').read_bytes()).items():
        assert (path/name).resolve().is_relative_to(path.resolve())
        assert current.sha(path/name)==digest
    return current.sha(path/'seal.json')


def main():
    current.admitted()
    base=current.HERE.parent
    sroot=current.HERE/'bounded-progress-3090-1794492867979185800'
    groot=current.HERE/'bounded-progress-4090-1794492867978820000'
    proot=current.HERE/'postexit-preservation-1794492985381577800'
    evidence=[{'path':str(p),'seal_sha256':verified(p)}for p in[sroot,groot,proot]]
    s=json.loads((sroot/'inventory.json').read_bytes());g=json.loads((groot/'inventory.json').read_bytes())
    ps=json.loads((proot/'3090.json').read_bytes());pg=json.loads((proot/'4090.json').read_bytes())
    assert all(s[n]['actual'].get('absent')for n in['worker/process.json','launcher-process.json'])
    assert g['control/runner-process.json']['actual']['absent']
    assert s['worker/status.json']['value']['phase']=='technical_failure'
    assert g['batch/status.json']['value']['phase']=='failed'
    assert s['holder_identity_matches']and sum(p['held']for p in s['locks'])==9
    counts=ps['journal']['counts'];assert(counts['model_request'],counts['model_reply_sealed'],counts['technical_failure'])==(134,133,1)
    assert len(ps['request_metadata_inventory'])==134
    assert[p['request']for p in ps['request_metadata_inventory']if p['failure']]==['0134']
    before={base/name:(base/name).read_bytes()for name in['README.md','HANDOFF.md','full-gui-current.json']}
    prior=json.loads(before[base/'full-gui-current.json'])
    assert prior['original_scope']['tracks']==32 and prior['remaining28']['manifest_sha256']==s['manifest_sha256']
    assert prior['experimental_state']=='running_under_explicit_human_source_reference_authorization'
    out=current.HERE/('postexit-progress-publication-'+str(time.time_ns()));out.mkdir()
    for path,raw in before.items():(out/('before-'+path.name)).write_bytes(raw)
    (out/'publication-source.py').write_bytes(Path(__file__).read_bytes())
    terminals=[]
    for run in g['runs']:
        assert len(run['attempts'])==1
        attempt=run['attempts'][0]
        item=attempt.get('technical-failure.json',attempt.get('complete.json'));v=item['value']
        audit=next(p for p in pg['runs']if p['run_id']==run['run_id']and p['attempt']==attempt['attempt'])
        filename='technical-failure.json'if'technical-failure.json'in attempt else'complete.json'
        assert audit['files'][filename]['sha256']==item['sha256']
        terminals.append({'run_id':run['run_id'],'attempt':attempt['attempt'],'terminal_sha256':item['sha256'],
            'terminal_file':filename,'actor_calls':v['actor_calls'],'verifier_calls':v['verifier_calls'],
            'auxiliary_calls':v['auxiliary_calls'],'decisions':v['decisions'],'environment_actions':v['environment_actions'],
            'blocked_reason':v['blocked_reason'],'technical_status':v['technical_status'],
            'raw_official_reward':v['official_reward'],'scoring_status':v['scoring_status'],
            'Mirage_trajectory_label':None,'independently_reviewed_complete_trajectory':False,
            'chain':audit['chain'],'terminal_files_full_SHA_this_audit':len(audit['files'])})
    assert len(terminals)==2
    assert sum(p['environment_actions']for p in terminals)==25
    status={k:v for k,v in prior.items()if k not in['remaining28','time','schema','immutable_publication','goal_tool_status_note']}
    status.update(schema='original32-approved28-source-reference-postexit-status-v1',time=time.time(),
        experimental_state='stopped_after_native_parser_terminal_and_prefill_OOM',actual_experiment_running=False,
        objective_complete=False,efficacy_established=False,relative_Mirage_reduction=None,
        goal_tool_status_note='Prior tool observation retained as historical; no new goal status transition made.',
        source_condition_blocker_resolved=True,human_choice_pending=False,
        remaining28={'runtime_root':str(current.HERE),'manifest_sha256':s['manifest_sha256'],
            'original_new_version_tracks':28,'model_or_budget_terminals':1,'technical_terminals':1,'never_started':26,
            'remaining_model_terminals_are_not_successes':True,'new_version_matched_pairs':14,
            'actual_service_state':s['worker/status.json']['value'],'actual_GUI_state':g['batch/status.json']['value'],
            'actual_worker':s['worker/process.json']['actual'],'actual_launcher':s['launcher-process.json']['actual'],
            'actual_GUI_runner':g['control/runner-process.json']['actual'],
            'actual_model_attempts':134,'complete_reply_events':133,'failed_requests':['0134'],
            'operation_counts':dict(collections.Counter(p['operation']for p in ps['request_metadata_inventory'])),
            'sealed_request_directories_including_failed':134,'actual_holder':s['holder_actual'],'actual_held_locks':9,
            'current_compute_on_authorized_GPUs':s['compute_identities'],
            'terminals':terminals,'service_event_chain':ps['journal'],'actual_evidence':evidence,
            'critical_service_requests_full_binary_SHA_verified':['0015','0017','0133','0134'],
            'all134_service_binary_receipts_newly_full_SHA_verified':False,
            'all_GUI_terminal_files_and_event_chains_verified':True,
            'full_current_semantic_candidate_review_complete':False,
            'previous_two_candidate_reviews_remain_valid_but_not_whole_trajectory_negative':True,
            'native_input_and_stateless_contract_all_new_calls_fully_audited':False},
        automatic_restart_or_terminal_rerun_performed=False,
        next_required_work=['Review all new lawful candidate/image histories before outcome join',
            'Diagnose and prepare full-input prefill memory repair with original failures preserved',
            'Separate normal-operation type refusal from semantic Mirage and validate before any condition change',
            'Continue only never-started authorized tracks through a new linked once-only entry after readiness checks'],
        immutable_publication=str(out),publication_adds_model_GUI_scorer_paid_calls=0)
    current.save(out/'status.json',status)
    stopped=datetime.fromtimestamp(g['batch/status.json']['value']['updated'],timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    report=f'''2026-11-12服务器实查：防御队列已停止，尚未证明Mirage降低

实际停止时间为北京时间{stopped}。3090服务worker/launcher和4090 GUI runner均已退出，不能沿用11月10日“运行中”的交接。原holder的完整UID/命令/start ticks和九个FD写锁仍匹配；本次查询时授权4–7卡没有compute进程，未改动资源或启动模型。

新版本28条中：T003旧帧无辅助对照因native_parser_error终止，4 actor、11 verifier、1个GUI动作；同任务旧帧有辅助轨迹执行24个GUI动作，28 actor、63 verifier（含一次失败）、28辅助，随后主核验prefill CUDA OOM，且服务退出使/end确认失败。26条尚未开始。原4条终局保留，不把6个原32终局都称为成功完成。

本命名空间134次调用=32 actor+74 judge+28辅助；133完整回复事件和1次OOM，134个sealed目录包含失败目录。OOM不是模型语义零分或防御成功。原始评分记录与技术失败分类分别保留；当前两轨未完成完整独立Mirage审查，触发率及相对降幅均未知。

来源编号→精确整句修复已有此前真实非空接线证据，但不证明语义核验准确。已独立审查的正常Category点击被menu_option/input类型不一致触发恢复；不能把正常操作拒绝当成成功阻止Mirage。辅助确实参与本次GUI，但实际模型为单个Qwen3.5-9B基座，decision_adapter_loaded=false；配置仍为完整当前供应单图+固定v6，每次空上下文，未称已加载JEV适配器。

本次只读取证通过983个服务事件、两GUI链1460事件；99个GUI终局文件（含原图/来源/事件）稳定SHA保留。4份关键服务请求0015/0017/0133/0134已逐文件含二进制完整SHA核验，其余请求本次只查seal和metadata，未宣称已完成134份全二进制原生审计。首次全量检查55秒超时已保留原观察器source/failure，分片只读取证完成；这是观察器限制，不是额外实验失败。

下一步先做全来源语义审查、长历史显存峰值修复与正常控件误拒的隔离验证，满足原协议后推进26条未开始轨迹。所有原图/主完整历史/BF16/SDPA/动作/严格validator/每轨预算和来源编号批准范围保留；本次未重跑终局、未重启旧队列、未增加模型/GUI/评分/付费调用，也未作新的实验条件变更。
'''
    (out/'实验进展-20261112.md').write_text(report,encoding='utf8')
    head=f'''## 最新：2026-11-12 实查服务与GUI已退出；新28条为1原生解析终局+1OOM技术终局+26未开始

权威`{current.HERE.name}/{out.name}/status.json`及同目录`实验进展-20261112.md`。实际队列于北京时间{stopped}停止，旧“生成中/运行中”头已过期。worker359137、launcher358975和GUI1650750实际不存在；原holder UID1033完整命令/start与九锁仍核实，授权4–7本次无compute。只读取证，未启动/停止/分配任何模型或GUI。

T003 stale/noaux因native_parser_error终止：4actor/11judge、1实执；T003 stale/aux为OOM技术终局：28actor/63judge含失败/28辅助、24实执，主核验prefill OOM后服务退出、/end连接失败。其余26未开始。原32轨/16对/8任务和4旧终局保留；不重刷任何终局，不把技术失败或原始评分0当模型语义零分。

134调用=32actor+74judge+28辅助；133完整回复+1OOM，134seal目录含失败。983服务/1460 GUI事件链和99 GUI终局文件SHA通过；4份关键服务请求0015/0017/0133/0134全二进制SHA通过，其余本次metadata/seal，未宣称全部134原生审计完成。当前整轨语义审查未完成，相对Mirage降低null，防御未证明有效。此前来源编号采用许可仍有效、不复问；无新增实验条件改变。

辅助仍为单个Qwen3.5-9B基座、decision_adapter_loaded=false，单图固定v6逐次空上下文；未称JEV适配器。已审正常下拉框类型误拒保留，不能算成功防御。下一步全来源审查、原完整历史的prefill显存修复和正常操作控制；未就绪前不重复旧stage/service/gui入口。完整目标未完成，旧目标工具状态仅历史，不在此伪造恢复或完成。以下旧头仅保留历史。

'''
    (out/'new-head.md').write_text(head,encoding='utf8')
    current.save(out/'seal.json',{p.name:current.sha(p)for p in out.iterdir()if p.is_file()})
    for path,raw in before.items():assert path.read_bytes()==raw,'Concurrent publication; archived result remains reviewable'
    for name in['README.md','HANDOFF.md']:(base/name).write_bytes(head.encode('utf8')+before[base/name])
    (base/'full-gui-current.json').write_bytes((out/'status.json').read_bytes())
    pointer={'root':str(out),'status_sha256':current.sha(out/'status.json'),'seal_sha256':current.sha(out/'seal.json'),
        'actual_running':False,'new_model_GUI_scorer_paid_calls':0}
    current.save(current.HERE/('postexit-progress-publication-created-'+str(time.time_ns())+'.json'),pointer)
    print(json.dumps(pointer,ensure_ascii=True))


if __name__=='__main__':main()
