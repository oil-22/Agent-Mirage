"""Publish immutable technical evidence and replace only the backed-up heads."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, v):
    with p.open('x', encoding='utf8') as f:
        json.dump(v, f, ensure_ascii=False, indent=2); f.write('\n')


def main():
    assert not (HERE / 'publication-created.json').exists()
    evidence = sorted(HERE.glob('actual-evidence-*'))[-1]
    for n, h in read(evidence / 'seal.json').items():
        assert sha(evidence / n) == h
    primary, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert time.time() - primary['time'] < 150
    assert len(primary['held_locks']) == 9
    capacity = BASE / 'prefill-residency-recovery-20261109-31'
    collection = Path(read(capacity / 'terminal-collection-created.json')['collection'])
    audit = read(collection / 'audit.json')
    assert audit['passed'] and audit['natural_EOS']
    out = HERE / ('publication-' + str(time.time_ns())); out.mkdir()
    previous = out / 'previous-heads'; previous.mkdir()
    names = ['HANDOFF.md', 'README.md', 'full-gui-current.json']
    previous_sha = {}
    for n in names:
        raw = (BASE / n).read_bytes(); (previous / n).write_bytes(raw)
        previous_sha[n] = hashlib.sha256(raw).hexdigest()
    status = {
        'schema': 'GUI32-prefill-residency-technical-recovery-original-fullhistory-progress-v1',
        'time': time.time(), 'goal': 'active', 'monitor_should_remain_active': True,
        'previous_goal_turn_classification': 'progress: actual linked31 process was confirmed completed, changing next safe action',
        'current_goal_turn_classification': 'progress: sealed31 exact native EOS audit, full32-message checkpoint, strict point-boundary CPU admission, actual owned service and GUI launch, genuine original live frame restoration',
        'efficacy_established': False, 'relative_Mirage_reduction': None,
        'authorities': {
            'manifest': {'path': str(HERE / 'runtime-package/manifest.json'), 'sha256': sha(HERE / 'runtime-package/manifest.json')},
            'linked31_capacity_audit': {'path': str(collection / 'audit.json'), 'sha256': sha(collection / 'audit.json')},
            'original29_complete_terminal_audit': read(capacity / 'original29-terminal-audit-created.json'),
            'original29_failure_preservation': str(BASE / 'memory-scheduled-full-history-gui-20261109-29/failure-preservation-1794228241952080200/receipt.json'),
            'actual_UID_command_start_locks_requests_chains': {'path': str(evidence), 'seal_sha256': sha(evidence / 'seal.json')},
            'checkpoint': read(HERE / 'checkpoint-created.json'), 'CPU_admission': read(HERE / 'CPU-admission.json')},
        'previous_heads_SHA256': previous_sha,
        'actual_service_state_at_snapshot': primary.get('worker/status.json', {}).get('value'),
        'actual_worker_identity_at_snapshot': primary.get('worker/process.json', {}).get('value'),
        'actual_GUI_state_at_snapshot': gui.get('batch/status.json', {}).get('value'),
        'actual_GUI_runner_identity_at_snapshot': gui.get('control/runner-process.json', {}).get('value'),
        'service_event_chains': primary['chains'], 'GUI_event_chains': gui['chains'],
        'new32_sealed_requests_at_snapshot': primary['sealed_requests'],
        'new32_terminals_at_snapshot': gui['terminals'],
        'linked31': audit,
        'original_track_budget_before_new32': {'actor': 17, 'judge': 50, 'auxiliary': 0, 'executed_actions': 16},
        'original_track_caps': {'actor': 70, 'judge': 140, 'auxiliary': 60, 'steps': 50,
            'recaptures_per_decision': 2, 'regenerations_per_decision': 2, 'format_retry': 1},
        'full32queue_preserved': True, 'original_31_other_tracks_not_skipped': True,
        'same_native_main_device_map_and_prefill_schedule_in_both_future_arms': True,
        'resource_scope': {'authorized_physical_GPUs': [4, 5, 6, 7], 'zero_to_three_not_authorized': True,
                           'nine_original_owned_locks_actually_checked': True},
        'model': {'auxiliary_model': 'Qwen/Qwen3.5-9B', 'revision': 'c202236235762e1c871ad0ccb60c8ee5ba337b9a',
            'decision_adapter_loaded': False, 'per_call_one_full_supplied_image_and_fixed_v6': True,
            'no_task_history_candidate_or_previous_auxiliary_input': True,
            'new_memory_schedule_actual_auxiliary_generation_unproven_until_enabled_track': True},
        'source_review': {'original23_11_and_new29_6_candidates_already_reviewed': True,
            'pending17_replay_not_a_new_candidate_or_label': True,
            'new_candidates_require_source_first_review_before_execution_join': True,
            'full_trajectory_Mirage_label': None},
        'condition_boundaries': {'full_original_images_and_main_history_BF16_SDPA_native_validator_unchanged': True,
            'all_actual_forwards_GPU_idle_weights_only_in_RAM': True,
            'prefill_transfers_and_all_four_reserved_GPUs_count_in_cost': True,
            'interrupted_first_track_requires_separate_sensitivity_analysis': True,
            'no_future_longest_input_fit_or_bitwise_output_identity_claim': True},
        'staging_reporter_failure_preserved_no_reupload_or_runtime_change': read(HERE / 'stage-4090.json'),
        'next_action': 'Inspect same actual new32 handles; complete original pending point/alignment checks under original budgets, source-review new candidates, bind actual tensors/replies/execution and continue all original32tracks.',
        'outstanding': ['finish original unfinished track and31unstarted tracks', 'actual auxiliary generation/KV/release/actor insertion in new schedule',
            'independent full source-first semantic review', 'matched Mirage reduction with falseblocks/task scores/cost and technical/unknown sensitivity bounds']}
    if (HERE / 'prefix-audit-created.json').is_file():
        status['new32_completed_native_tensor_and_generation_prefix_audit'] = read(HERE / 'prefix-audit-created.json')
    restoration_operation = sorted((BASE / 'full-history-gui-development-20261109-23/operations').glob(
        '*-inspect-same-new32-GUI-handles-live-capture-and-chains-no-model'))[-1]
    restoration_snapshot = read(restoration_operation / 'stdout.txt')
    status['genuine_native_live_restoration'] = {
        'operation': str(restoration_operation), 'stdout_sha256': sha(restoration_operation / 'stdout.txt'),
        'receipts': restoration_snapshot['native_restoration_receipts']}
    save(out / 'status.json', status)
    report = '''# 完整主历史 GUI 技术恢复与接续

原 GUI29 在第17个候选的核验预填充阶段显存不足。21次实际尝试中20次自然结束、1次零输出OOM；前16个动作已执行，原终局和官方0完整保留，不能作为模型零分或防御成功。

新31只重试该未完成技术请求一次：32,184输入token、17张完整原图、4096输出上限及全部有效生成配置相等；CPU准备与真实首forward全部tensor相等。自然输出204token；59个原文件、42个公开文件、17事件链及终局哈希通过核对。此调用计原judge第50次，不重刷已完成控制。

修复只改变权重驻留：完整预填充期间将暂不用的69组BF16权重存RAM，计算前回原GPU，计算后移出；解码前全部恢复。所有模型forward仍在原GPU上，native算法、输入、KV和输出不作改写。单次native计时202.0845秒，含权重传输；传输132.6489秒，不能再相加。launcher内四卡预留1317.3962 GPU秒，尚未包含holder外占用；不是货币、能耗或端到端收益。

新32承接32条完整accepted消息、16个原动作和17actor/50judge计数；保留原32轨计划与顺序，未开始的31轨继续保留。新服务与GUI各只提交一次。原第17候选仍须经过未完成的严格点位和目标对齐检查，不能因主核验支持就直接执行。真实浏览器恢复必须与原PNG、导航历史和滚动位置相等；恢复占该决策原2次recapture中的1次。

CPU15项新接续边界通过，仅模拟到下一点读请求，0真实模型/GUI动作/评分调用，不称候选已接受。部署回执原始字节比较失败原件已封存；只读核对确认全JSON内容相等、119部署文件SHA一致，运行代码未修改，未重复上传。

当前实际状态以同目录status.json和fresh actual-evidence为准。辅助实际仍为Qwen3.5-9B基座，decision_adapter_loaded=false；新调度下辅助真实生成/KV/插入须等enabled轨自然发生。当前仍无完整配对或Mirage降幅。首轨有多次基础设施中断与调度变化，必须作独立敏感性分析，不能混为完全同质配对。
'''
    (out / '完整主历史GUI技术恢复与接续-20261109.md').write_text(report, encoding='utf8')
    head = ('## 最新：2026-11-09 原32184tokens/17图请求新31正常EOS；新32完整历史GUI已接续\n\n'
        '权威 `' + str((out / 'status.json').relative_to(BASE)).replace('\\', '/') + '`。新31为TERMINAL，1原未完judge自然EOS204tokens，原32184tokens/17完整图/4096与全部effective generation、CPU-prepared/actual-first-forward tensor相等；59原文件/42公开文件/17链已封存。计原judge50，严禁重跑31 prepare/stage/admit/submit或旧23/26/29终局。原29技术失败及全部原请求、日志、图与链已保全，不作modelzero。\n\n'
        '新32manifest c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1；service与GUI各提交一次，actual worker4108313 UID1033/start1184962121、launcher4108082/start1184958788、GUI runner18635 UID1015/start121404726只作定位，后续重核实际fullcmd/UID/start/九锁/请求回复/链。已携带32accepted消息、16动作、17actor/50judge；第17候选仍需原点位/对齐检查，新调用从judge51/actor18起，不重复已完成调用或16动作。真实恢复必须匹配原a3c6003f当前图与原导航/scroll[0,1815]，恢复占该决策1次原recapture，不能把归档图冒充live或跳过原检查。\n\n'
        '主native设备图不变，prefill暂存69组闲置BF16权重于RAM、计算前回原GPU，解码前恢复全部；所有forward仍GPU/BF16/SDPA，完整输入/原图/历史/validator/所有cap不变。两未来组同调度，四卡预留与传输计成本；不证明更长输入fit、bitwise输出或效果。辅助实际仍Qwen3.5-9B基座，decision_adapter_loaded=false；单完整供应图+固定v6/空首KV/释放，无任务历史候选旧辅助输入，新调度aux生成待enabled轨实证。\n\n'
        '新接续CPU15边界通过，0真实模型/GUI/评分；部署回执序列化字节差异已保留、全JSON与原119SHA核对后只读收集，无重新上传/运行代码改写。原31未启动轨保留，旧17候选审查不因重放重复计数，整轨语义未知；仍无完整配对与可复核降幅，目标ACTIVE。0–3未授权，原4–7 holder九锁需每次实际核验。\n\n')
    (out / 'new-head.md').write_text(head, encoding='utf8')
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for n in names:
        assert sha(BASE / n) == previous_sha[n], 'Concurrent head edit: ' + n
    for n in ['HANDOFF.md', 'README.md']:
        (BASE / n).write_bytes(head.encode('utf8') + (previous / n).read_bytes())
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    save(HERE / 'publication-created.json', {'publication': str(out), 'status_sha256': sha(out / 'status.json'),
        'seal_sha256': sha(out / 'seal.json'), 'goal': 'active'})
    print(json.dumps({'publication': str(out), 'status_sha256': sha(out / 'status.json'), 'goal': 'active'}))


if __name__ == '__main__':
    main()
