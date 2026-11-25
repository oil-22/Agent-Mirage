"""Publish immutable actual runtime evidence, preserving superseded head bytes."""
import argparse
import json
from pathlib import Path
import time
from orchestrate import HERE, PACKAGE, admitted, sha, save


def verify(folder):
    for name,digest in json.loads((folder/'seal.json').read_bytes()).items():
        path=folder/name
        assert path.resolve().is_relative_to(folder.resolve()) and sha(path)==digest
    return sha(folder/'seal.json')


def main(evidence):
    manifest=admitted();assert evidence.parent==HERE
    seal=verify(evidence)
    service=json.loads((evidence/'3090.json').read_bytes());gui=json.loads((evidence/'4090.json').read_bytes())
    state=service['worker/status.json']['value'];gui_state=gui['batch/status.json']['value']
    worker=service['worker/process.json']['actual'];runner=gui['control/runner-process.json']['actual']
    assert worker['uid']==1033 and runner['uid']==1015
    assert HERE.name in worker['command'] and HERE.name in runner['command']
    assert worker['state']not in['Z','X'] and runner['state']not in['Z','X']
    assert len(service['held_locks'])==9 and gui_state['expected']==28
    assert state['actual_model_attempts']>0 and gui_state['phase']=='running'
    before={HERE.parent/name:(HERE.parent/name).read_bytes()for name in['README.md','HANDOFF.md','full-gui-current.json']}
    prior=json.loads(before[HERE.parent/'full-gui-current.json'])
    scope=prior['original_scope'];assert(scope['tracks'],scope['matched_pairs'],scope['source_selected_tasks'])==(32,16,8)
    decision=HERE/'human-source-reference-condition-decision.json'
    out=HERE/('approved-runtime-publication-'+str(time.time_ns()));out.mkdir()
    for path,raw in before.items():(out/('before-'+path.name)).write_bytes(raw)
    (out/'publication-source.py').write_bytes(Path(__file__).read_bytes())
    (out/decision.name).write_bytes(decision.read_bytes())
    reviews=[]
    for pointer in sorted(HERE.glob('source-review-*-created.json')):
        authority=json.loads(pointer.read_bytes());root=Path(authority['review'])
        assert verify(root)==authority['seal_sha256'] and sha(root/'review.json')==authority['review_sha256']
        reviews.append(authority)
    native_audits=[]
    for root in sorted(HERE.glob('mixed-receipt-audit-*')):
        if not root.is_dir()or not(root/'receipt.json').is_file():continue
        audit=json.loads((root/'receipt.json').read_bytes())
        if not audit.get('passed'):continue
        native_audits.append(dict(root=str(root),receipt_sha256=sha(root/'receipt.json'),
            seal_sha256=verify(root),requests=audit['actual_original_requests_read_not_generated'],
            enabled_auxiliary_branch=audit['actual_enabled_mixed_branch_observed']))
    quote_audits=[]
    for root in sorted(HERE.glob('quote-reference-runtime-audit-*')):
        if not root.is_dir()or not(root/'receipt.json').is_file():continue
        audit=json.loads((root/'receipt.json').read_bytes())
        if not audit.get('passed'):continue
        quote_audits.append(dict(root=str(root),receipt_sha256=sha(root/'receipt.json'),
            seal_sha256=verify(root),request=audit['request'],actual_wire_claims=audit['actual_wire_claims'],
            nonempty_source_ID_mapping_naturally_exercised=audit['nonempty_source_ID_mapping_naturally_exercised']))
    kind_issue=None
    if(HERE/'first-kind-recovery-created.json').is_file():
        kind_issue=json.loads((HERE/'first-kind-recovery-created.json').read_bytes())
        kind_root=Path(kind_issue['root'])
        assert verify(kind_root)==kind_issue['seal_sha256']
        assert sha(kind_root/'review.json')==kind_issue['review_sha256']
    nonempty_quote_replies=sum(r['nonempty_source_ID_mapping_naturally_exercised']for r in quote_audits)
    status=dict(schema='original32-approved28-source-reference-runtime-v1',time=time.time(),
        experimental_state='running_under_explicit_human_source_reference_authorization',
        source_condition_blocker_resolved=True,human_choice_pending=False,
        human_authorization_sha256=sha(decision),source_condition_choice=manifest['source_condition_choice'],
        goal_tool_last_observed_status='blocked',
        goal_tool_status_note='Read-only get_goal still reports prior blocked status after explicit human approval; actual authorized experiment is running. No active status was fabricated.',
        objective_complete=False,monitor_should_remain_active=True,original_scope=scope,
        efficacy_established=False,relative_Mirage_reduction=None,
        immutable_original4_terminal_authority=prior.get('original32_postexit_ledger',dict(
            path=str(HERE.parent/'remaining29-full-history-gui-20261110-37/original32-postexit-ledger-1794306065792235500/ledger.json'),
            sha256='b079d93b3dd131905dbbe914f48b0d235e161fc378978df680ef6a4856f6a1bb')),
        four_immutable_terminals_never_reexecuted=True,completed_request_ids_excluded=437,
        remaining28=dict(runtime_root=str(HERE),manifest_sha256=sha(PACKAGE/'manifest.json'),
            remaining_tracks=28,new_version_matched_pairs=14,both_arms_same_version=True,
            actual_service_state=state,actual_GUI_state=gui_state,
            actual_worker=worker,actual_launcher=service['launcher-process.json']['actual'],actual_GUI_runner=runner,
            sealed_request_count=len(service['sealed_requests']),actual_held_locks=9,
            actual_evidence=str(evidence),actual_evidence_seal_sha256=seal,
            service_event_chain=service['journal'],GUI_event_chains=gui['GUI_event_chains'],
            source_review_authorities=reviews,native_request_audits=native_audits,
            actual_quote_reference_audits=quote_audits,scoped_normal_operation_kind_issue=kind_issue),
        source_reference_condition=dict(verify_prompt_and_wire_and_decoding_choices_changed=True,
            exact_source_table_to_original_validator=True,whole_source_units_only=True,
            no_semantic_intervention_bundled=True,semantic_grounding_repair_or_efficacy_established=False,
            example_added_system_tokens=836,future_full_history_capacity_not_proven=True),
        auxiliary=dict(model='Qwen/Qwen3.5-9B',revision='c202236235762e1c871ad0ccb60c8ee5ba337b9a',
            decision_adapter_loaded=False,single_model=True,
            complete_current_supplied_image_plus_fixed_v6_only=True,empty_context_per_call=True,
            fixed_prompt_sha256='2a6a2d210bac4cd552e477df15dab86aacd4ff479cd85a3e070f01dcc97e558c'),
        full_images_main_history_BF16_SDPA_native_actions_validators_and_budgets_retained=True,
        per_trajectory_caps=manifest['per_trajectory_caps'],original_recovery_budgets=manifest['original_recovery_budgets'],
        resource_scope='Verified owned3090 physical4-7 via original nine-lock holder only',
        prelaunch_collector_path_failure_preserved_not_model_failure=True,
        publication_adds_model_GUI_scorer_paid_calls=0,immutable_publication=str(out))
    save(out/'status.json',status)
    head=f'''## 最新：2026-11-10 用户已采用来源编号修复；剩余28条完整GUI已实际启动

用户明确回复“采用修复，继续剩余28条（推荐）”，此前quote_id条件等待已解除，不再询问。新运行包`{HERE.name}`已双机逐文件核验并通过原持锁进程只提交一次，manifest `{sha(PACKAGE/'manifest.json')}`。原32轨/16对/8任务、4不可重跑终局和437旧请求排除保持；28条/14对是新版本分层，非替换原分母。

权威`{HERE.name}/{out.name}/status.json`，实际证据`{HERE.name}/{evidence.name}`。27B主模型和单个9B辅助已实际加载，worker{worker['pid']} UID1033/start{worker['start_ticks']}，GUI{runner['pid']} UID1015/start{runner['start_ticks']}完整命令/UUID/九锁已核；仅用3090物理4–7。当前运行`{gui_state.get('run')}`，已发{state['actual_model_attempts']}次/封存{len(service['sealed_requests'])}份新模型回复，完成{gui_state['completed']}/28；具体生成中/恢复状态以最新回执为准，不重启stage/service/gui。ready中的初始0calls不能覆盖真实请求。

仅采用已封存获批的来源ID→整句精确原文表示，Controller恢复后保留原校验。verify提示/字段/解码选择已变，整句不可任意截句/拼句；已封例子system增加836tokens，未证明未来容量或语义改善。原完整图/合法主历史/BF16/SDPA/原生动作评分和每轨50步、70actor/140judge/60辅助、2regen/2recapture/1formatretry保持，双臂同版；不捆绑新的语义放行规则。

已封{len(native_audits)}份原生/HTTP来源审计及{len(quote_audits)}份真实来源协议审计，其中{nonempty_quote_replies}份自然产生非空claims并实走ID→原句映射；空claims分支不充当非空来源映射或长STOP证明。{('新首个正常Category下拉框点击被主menu_option/点读input类型不一致触发原有复拍/再生成；点读明确同一个真实控件，原target_alignment未进入。记录已封，未热改校验或预算；该次局部拒绝不等于整轨终局。' if kind_issue else '当前尚无已封正常操作局部问题审查。')}

辅助实际为单个Qwen3.5-9B基座、decision_adapter_loaded=false，完整实际供应单图+固定v6，每次空上下文；不称已装JEV适配器。新首轨为无辅助对照，后续辅助分支须据真实调用核验。来源协议修复、格式合规、官方成功均不等于降低Mirage；相对降幅仍null，未证明30%或减半，正常操作/误拦/完成率待匹配整轨审查。首次只读预检错误假定旧R32服务目录在/data，已封失败源/日志，在linked02依原manifest查/home；0模型/GUI，未改实验条件或终局。

goal工具只读仍返回此前blocked状态，接口不能主动改成active；这不是仍待用户选择，实际实验按最新批准继续，完整目标未完成。以下旧“等待选择/未启动”仅为历史，由本头和新回执覆盖。

'''
    (out/'new-head.md').write_text(head,encoding='utf8',newline='\n')
    save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    for p,raw in before.items():assert p.read_bytes()==raw,'Concurrent update; preserve publication and inspect'
    for p in[HERE.parent/'README.md',HERE.parent/'HANDOFF.md']:p.write_bytes(head.encode('utf8')+before[p])
    (HERE.parent/'full-gui-current.json').write_bytes((out/'status.json').read_bytes())
    result=dict(root=str(out),status_sha256=sha(out/'status.json'),seal_sha256=sha(out/'seal.json'),
        human_choice_pending=False,actual_GUI_running=True,new_model_GUI_scorer_paid_calls_by_publication=0)
    save(HERE/('approved-runtime-publication-created-'+str(time.time_ns())+'.json'),result)
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True,type=Path)
    main(p.parse_args().evidence.resolve())
