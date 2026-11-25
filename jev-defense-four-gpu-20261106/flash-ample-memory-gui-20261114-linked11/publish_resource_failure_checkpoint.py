"""Publish the preserved resource failure without changing runtime or labels."""
import json
import time
from pathlib import Path
from control import BASE, HERE, save, sha


def load(p):
    return json.loads(p.read_bytes())


def main():
    preserved = HERE / 'GPU-conflict-failure-preservation-1794671002471667500'
    assert all(sha(preserved / n) == h for n, h in load(preserved / 'seal.json').items())
    native = load(preserved / '3090.json')['result']
    gui = load(preserved / '4090.json')['result']
    report = native['report']
    assert report['failed_request_has_no_public_response']
    assert report['failed_request_actual_generation']['natural_EOS']
    assert report['failed_request_actual_generation']['output_tokens'] == 32
    assert gui['report']['terminal']['infrastructure_failure']
    assert gui['report']['terminal']['official_reward'] is None
    assert len(gui['report']['terminal']['actor_receipts']) == 27
    inspection = HERE / 'post-conflict-exit-inspection-1794671068329511400.json'
    actual = load(inspection)['result']
    assert not actual['postexit_seal_exists']
    assert actual['launcher_actual']['pid'] == 2039759
    assert all(actual['launcher_actual'][k] == actual['launcher_saved'][k]
               for k in ['uid', 'command', 'start_ticks'])
    root = HERE / ('resource-failure-checkpoint-' + str(time.time_ns()))
    root.mkdir()
    (root / 'publisher-source.py').write_bytes(Path(__file__).read_bytes())
    heads = [BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md',
             HERE / 'experiment-current.json', HERE / 'continuation-current.json']
    old = root / 'previous-heads'
    old.mkdir()
    for f in heads:
        (old / f.name).write_bytes(f.read_bytes())
    status = {
        'time': time.time(), 'phase': 'preserved_technical_failure',
        'completed_normal_GUI_terminals': 16, 'technical_GUI_attempts': 1,
        'unstarted_original_configurations': 12, 'current_total_logical_configurations': 29,
        'primary_attempts': 397, 'public_complete_primary_replies': 396,
        'failed_generation': {'request': '00397', 'decision': 28, 'natural_EOS': True,
                              'input_tokens': 28120, 'output_tokens': 32,
                              'public_response_delivered': False, 'action_executed': False},
        'failed_GUI_run': 'flash14-T089-stale_replace-gate',
        'successful_replies_in_failed_GUI_attempt': 27,
        'actual_environment_actions_in_failed_GUI_attempt': 27,
        'Flash_replies_in_failed_GUI_attempt': 28, 'Flash_NO_recaptures': 0,
        'actual_resource_failure': 'Post-generation guard observed main PID 2040397 plus unverified PID 2190562 on GPU 3.',
        'conflict_UID_and_command_not_captured_before_process_exit': True,
        'conflict_PID_not_killed_or_assumed_foreign_UID': True,
        'GPU_empty_at_later_read_does_not_remove_original_conflict': True,
        'preservation': str(preserved), 'preservation_seal_sha256': sha(preserved / 'seal.json'),
        'remote_preserved_native_files': native['files'],
        'remote_preserved_GUI_terminal_files': gui['report']['sealed_terminal_files_verified'],
        'remote_native_preservation_seal_sha256': native['seal_sha256'],
        'remote_GUI_preservation_seal_sha256': gui['seal_sha256'],
        'GUI_terminal_sha256': gui['report']['original_terminal_sha256'],
        'GUI_event_chain': gui['report']['event_chain'],
        'actual_primary_and_Flash_exited': True,
        'latest_actual_exit_inspection': str(inspection), 'exit_inspection_sha256': sha(inspection),
        'launcher_live_finalizing_full_postexit_seal_at_recorded_time': True,
        'all_launcher_and_GUI_postexit_audits_complete': False,
        'source_review_prefix25': str(HERE / 'T089-stale-gate-prefix25-source-review-1794670590558443900'),
        'prior_gate_candidate15_occurrence_stays_separate_from_infrastructure_failure': True,
        'full_failed_attempt_semantic_coverage_completed': False,
        'offline10_authorized': True, 'offline10_submitted': False,
        'old_queue_will_not_be_restarted': True, 'new_technical_retry_needs_new_linked_attempt': True,
        'completed_controls_and_capacity_not_repeated': True,
        'new_model_GUI_calls_by_publisher': 0, 'Mirage_reduction': None, 'goal': 'active',
    }
    save(root / 'status.json', status)
    name = 'GPU资源冲突与GUI技术失败保全-20261114.md'
    text = '''# GPU资源冲突与GUI技术失败保全

原队列已因技术失败停止，不能继续引用较早的 running 快照。16 条正常终局保持；T089 旧帧门控在第 28 次主请求的生成后资源检查失败，另 12 条原配置尚未开始。主模型共尝试 397 次、交付 396 条完整回复。失败请求实际生成了 32 个 token 并自然 EOS，但未形成公开成功回复，也未执行第 28 个动作；不能追认成功或作为语义零。该 GUI 尝试有 27 条实际回复、27 个动作、28 次 Flash YES、0 次 NO 复拍，官方评分未运行。

原资源检查在 GPU 3 看到主 PID 2040397 和未核验 PID 2190562。复查时冲突 PID 已退出，UID 和完整命令未能保存，故不能声称确定是其他用户或 whz。后续 8 卡无 compute 不会抹去原冲突。未终止该进程，也未抢占资源。

已逐字节保存并验证失败请求、实际 prepared/first-forward/sequence 原始张量、完整 wire/body、生成和失败记录、日志及 74 个冻结运行源，共 111 个原生侧文件。GUI 原 86 个终局文件（全部原图、浏览器轨迹、协议、请求回复和日志）已另行快照封存，251 事件链通过。旧终局、截图、动作、源审标签均未修改。

主服务与 Flash 已退出。最近核验 launcher 2039759（UID 1033、完整命令和 start_ticks 一致）仍在封存全部 postexit 文件；不能把 exit.json 等同 launcher 已退出。等待其真正退出后再核完整封存。只允许另建关联技术 attempt 处理未完成项，原 16 条终局和已完成容量预检不重跑；任何新入口都必须重新核验独占 GPU、UUID、显存和继承锁。当前不启动已批准的 10 条离线开发调用。

技术失败与已报告的门控候选 15 文字误读分开。该部分轨迹已有一次确定边界错误，但尚非完整配对效果；范围未决仍保留。整体 Mirage 降低尚未证明，目标保持 ACTIVE。
'''
    (root / name).write_text(text, encoding='utf8')
    save(root / 'receipt.json', {'status_sha256': sha(root / 'status.json'),
        'report_sha256': sha(root / name), 'new_model_GUI_calls': 0, 'goal': 'active'})
    save(root / 'seal.json', {str(f.relative_to(root)): sha(f) for f in root.rglob('*') if f.is_file()})
    head = (
        f'## 最新：原GUI因GPU资源冲突停止；16正常、1技术失败、12未开始\n\n'
        f'权威 flash-ample-memory-gui-20261114-linked11/{root.name}/status.json 与 {name}。'
        '397主尝试/396完整交付；T089-stale-gate第28生成32token自然EOS后资源检查拒绝，'
        '未交付成功回复、未执行动作，27原生动作/28FlashYES/0NO复拍、评分未运行。'
        'GPU3当时额外PID2190562，复查已消失，UID/fullcmd未捕获，不推测归属、不杀进程。\n\n'
        f'{preserved.name}保全111原生侧文件与86GUI终局文件，251事件链通过；'
        '原图、全史、failed wire/raw/prepared/firstforward/sequence/EOS、日志、74源与原终局不改。'
        '主/Flash实际退出；launcher2039759 UID1033/fullcmd/start匹配仍在完整postexit哈希（最近核验时间见status），'
        '必须继续核实际退出/全量seal，不能凭exit.json判结束。旧队列绝不重启；未完成技术重试要新关联attempt，'
        '16正常终局/已完成容量不重跑，新占卡前核UUID/compute/显存/继承锁。\n\n'
        '已批准10离线尚未提交；原29正常完成准入条件尚未满足。'
        '不把技术失败算NO/模型零/official0，不将已报告gate15再次通知。目标ACTIVE/降低尚未证明。'
        '下面所有running/16of29继续等旧头均是历史快照。\n\n'
    )
    for f in heads[:3]:
        f.write_text(head + f.read_text('utf8'), encoding='utf8')
    (HERE / 'experiment-current.json').write_text(json.dumps({
        'publication': str(root), 'status': str(root / 'status.json'),
        'status_sha256': sha(root / 'status.json'), 'report': str(root / name),
        'report_sha256': sha(root / name), 'publication_seal_sha256': sha(root / 'seal.json'),
        'phase': 'preserved_technical_failure', 'Mirage_reduction': None, 'goal': 'active',
        'time': time.time()}, ensure_ascii=False, indent=2), encoding='utf8')
    (HERE / 'continuation-current.json').write_text(json.dumps({
        'checkpoint': str(root), 'receipt_sha256': sha(root / 'receipt.json'),
        'seal_sha256': sha(root / 'seal.json')}, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(root), 'report': str(root / name),
                      'normal_GUI': 16, 'technical_GUI': 1, 'unstarted': 12, 'goal': 'active'}))


if __name__ == '__main__':
    main()
