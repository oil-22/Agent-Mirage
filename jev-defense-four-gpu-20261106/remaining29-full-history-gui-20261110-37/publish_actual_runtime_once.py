"""Publish verified human resumption and actual runtime evidence; no launch."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
EVIDENCE = HERE / 'actual-evidence-1794293552923597800'
AUDIT = HERE / 'mixed-receipt-audit-1794293610690608700'
REVIEW = HERE / 'source-review-1794293705263977800'
POINTER = HERE / 'actual-runtime-publication-created.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verify(folder):
    for name, expected in json.loads((folder / 'seal.json').read_bytes()).items():
        target = folder / name
        assert target.resolve().is_relative_to(folder.resolve())
        assert sha(target) == expected, (folder.name, name)
    return sha(folder / 'seal.json')


def main():
    assert not POINTER.exists(), 'Publication is once-only; preserve it'
    seals = {str(folder): verify(folder) for folder in [EVIDENCE, AUDIT, REVIEW]}
    service = json.loads((EVIDENCE / '3090.json').read_bytes())
    gui = json.loads((EVIDENCE / '4090.json').read_bytes())
    audit = json.loads((AUDIT / 'receipt.json').read_bytes())
    review = json.loads((REVIEW / 'review.json').read_bytes())
    decision = json.loads((HERE / 'human-source-condition-decision.json').read_bytes())
    manifest = HERE / 'runtime-package/manifest.json'
    assert sha(manifest) == '368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
    assert decision['condition_blocker_resolved_by_this_human_reply'] is True
    assert decision['verbatim_human_reply'] == '采用修复，继续剩余 29 条（推荐）'
    worker = service['worker/process.json']['actual']
    launcher = service['launcher-process.json']['actual']
    runner = gui['control/runner-process.json']['actual']
    assert (worker['pid'], worker['uid'], worker['start_ticks']) == (252807, 1033, '1191243649')
    assert (launcher['pid'], launcher['uid'], launcher['start_ticks']) == (252451, 1033, '1191239591')
    assert (runner['pid'], runner['uid'], runner['start_ticks']) == (3333015, 1015, '127695701')
    assert HERE.name in worker['command'] and HERE.name in runner['command']
    assert len(service['held_locks']) == 9
    state = service['worker/status.json']['value']
    gui_state = gui['batch/status.json']['value']
    assert state['actual_model_attempts'] >= 2 and gui_state['expected'] == 29
    assert gui_state['phase'] == 'running'
    assert audit['passed'] and audit['requested'] == ['0001', '0002']
    assert audit['semantic_correctness_or_defense_efficacy_established'] is False
    assert len(review['rows']) == 1 and review['rows'][0]['candidate_semantic_mirage'] is False

    prior_publication = PARENT / 'remaining-full-history-gui-20261110-33/closed-terminal-publication-linked02-1794280835290980000/status.json'
    assert sha(prior_publication) == '71c250b00b2ba5d959412905c88a013d1b80c59fddc76a9afcb75a08214d3154'
    old_paths = [PARENT / name for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']]
    before = {path: path.read_bytes() for path in old_paths}
    previous_status = json.loads(before[PARENT / 'full-gui-current.json'])
    scope = previous_status['original_scope']
    assert (scope['tracks'], scope['matched_pairs'], scope['source_selected_tasks']) == (32, 16, 8)
    assert scope['original_full_plan_sha256'] == '51e35415fc7df2d0309e67f117310de8ecffd59b51ece6bcfdda176e5ae4f98c'
    out = HERE / ('actual-runtime-publication-' + str(time.time_ns()))
    out.mkdir()
    for path, raw in before.items():
        (out / ('before-' + path.name)).write_bytes(raw)
    (out / 'publication-source.py').write_bytes(Path(__file__).read_bytes())
    (out / 'human-source-condition-decision.json').write_bytes((HERE / 'human-source-condition-decision.json').read_bytes())
    status = dict(
        schema='original32-human-authorized-runtime-progress-v1', time=time.time(),
        experimental_state='running_under_explicit_human_authorization',
        source_condition_blocker_resolved=True,
        goal_tool_last_observed_status='blocked',
        goal_tool_status_note='Read-only get_goal still returned blocked after the actual human approval; no tool status was fabricated. Directly authorized runtime work is running.',
        monitor_should_remain_active=True, original_scope=scope,
        efficacy_established=False, relative_Mirage_reduction=None,
        original_three_terminal_authority=dict(path=str(prior_publication), sha256=sha(prior_publication),
            completed_endpoints=3, successes_not_inferred_from_endpoint_count=True,
            unchanged_terminals_never_reexecuted=True,
            clean_noaux_semantic_mirage=None, clean_aux_semantic_mirage=True,
            stale_replace_aux_semantic_mirage=True),
        remaining29=dict(runtime_root=str(HERE), manifest_sha256=sha(manifest),
            actual_service_state=state, actual_GUI_state=gui_state,
            actual_worker=worker, actual_launcher=launcher, actual_GUI_runner=runner,
            actual_held_locks=9, sealed_requests=len(service['sealed_requests']),
            service_event_chain=service['journal'], GUI_event_chains=gui['GUI_event_chains'],
            native_audit=dict(root=str(AUDIT), receipt_sha256=sha(AUDIT / 'receipt.json'),
                selected_original_requests=audit['requested'], passed=True,
                auxiliary_enabled_branch_observed=False),
            source_review=dict(root=str(REVIEW), review_sha256=sha(REVIEW / 'review.json'),
                candidate_count=1, source_negative_count=1,
                full_trajectory_mirage=None, current_execution_or_score_not_joined=True)),
        source_representation_change='Only the human-approved exact decoded native STOP answer source mapping; two Controller release files differ. Version boundary retained.',
        auxiliary=dict(model='Qwen/Qwen3.5-9B', decision_adapter_loaded=False,
            single_complete_supplied_image_and_fixed_v6_prompt=True,
            no_task_history_candidate_or_accumulated_KV=True,
            no_auxiliary_allow_block_or_Mirage_decision=True,
            structural_and_Unicode_length_decoding_mask=True,
            recognition_is_diagnostic_not_primary_outcome=True),
        full_images_main_history_native_actions_precision_and_budgets_unchanged=True,
        resource_scope='Only verified owned physical3090 GPUs4-7; no GPUs0-3 or foreign processes modified',
        actual_evidence=str(EVIDENCE), verified_source_seals=seals,
        human_authorization_sha256=sha(HERE / 'human-source-condition-decision.json'),
        immutable_publication=str(out), publication_adds_no_model_GUI_or_scorer_calls=True)
    save(out / 'status.json', status)
    head = f'''## 最新：2026-11-10 用户已采用来源修复；剩余29轨已实际启动并产生原生回复

用户已明确回复“采用修复，继续剩余 29 条（推荐）”，此前来源条件等待已解除，不再询问。新链接运行包 `{HERE.name}` 已部署；原32轨/16对/8选任务范围、3个不可变终局和362个旧请求排除保留。仅采用获批的精确原生STOP答案来源映射，版本 `evidence-v4.0.12-STAGED-native-answer-source-20261110`；原完整图像/主历史/BF16/SDPA/原生动作及全部预算不变。

权威 `{HERE.name}/{out.name}/status.json`，实际证据 `{HERE.name}/{EVIDENCE.name}`。实际worker252807 UID1033/start1191243649、launcher252451与GUI3333015 UID1015/start127695701完整命令已核；九把锁及4–7卡独占范围已核。两模型加载完成，GUI当前首条旧帧无辅助轨已进入真实推理，已发3次模型调用、封存2份完整回复（1judge+1actor），29条尚无新终局。不能依据旧ready文件里的0calls覆盖真实请求；不重启任何stage/service/gui。

0001/0002完整原生IDs/tensors/generation/HTTP来源审计通过；当前无新辅助推理，尚未观察此新批次的辅助分支。首个主候选先审完整原图/合法输入，只有落在Keyword框内的click，未发现该候选语义或动作错误；标签已先于当前执行/评分关联封存。这不是整轨阴性、任务成功或效力证据。

辅助实际为单个Qwen3.5-9B基座、decision_adapter_loaded=false，单完整供应图+固定v6，每次清空上下文；不称已经部署JEV适配器。主要终点仍为匹配完整轨迹的主模型Mirage，未证明30%或减半降幅。goal工具最后仍返回blocked，工具接口不能把它改为active；此为工具状态记录，不是仍待人类选择，实际实验按真实授权继续。监控保持；下方旧BLOCKED/未开始文字仅为历史，以上最新证据覆盖它。

'''
    (out / 'new-head.md').write_text(head, encoding='utf8', newline='\n')
    save(out / 'seal.json', {path.name: sha(path) for path in out.iterdir() if path.is_file()})
    for path, raw in before.items():
        assert path.read_bytes() == raw, 'Concurrent head update; leave the publication intact'
    for path in old_paths[:2]:
        value = head.encode('utf8') + before[path]
        path.write_bytes(value)
        assert path.read_bytes() == value
    current = PARENT / 'full-gui-current.json'
    current.write_bytes((out / 'status.json').read_bytes())
    assert sha(current) == sha(out / 'status.json')
    pointer = dict(root=str(out), status_sha256=sha(out / 'status.json'), seal_sha256=sha(out / 'seal.json'),
        human_choice_pending=False, runtime_running_from_actual_evidence=True,
        new_model_GUI_scorer_calls_by_publication=0)
    save(POINTER, pointer)
    print(json.dumps(pointer, ensure_ascii=True))


if __name__ == '__main__':
    main()
