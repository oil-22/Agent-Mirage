"""Record the completed new audit and unexecuted audit/publication preparation."""
import json
import time
from pathlib import Path
from control import BASE, HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def main():
    native = HERE / 'live-evidence-incremental-1794664345115396200'
    prepared = HERE / 'offline10-audit-preparation-1794664950047892500'
    pair = HERE / 'pair-trace-equivalence-1794665269530982800'
    progress = HERE / 'compact-progress-1794665218014967300.json'
    for root in (native, prepared, pair):
        assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())
    summary = load(native / 'summary.json')
    assert summary['cumulative_verified_main_replies'] == 293
    assert summary['cumulative_verified_Flash_replies'] == 171
    assert summary['new_raw_main_replies_verified'] == 16
    assert not (HERE / 'evidence-discipline-offline-preparation-01/submission.json').exists()
    comparison = next(v for v in load(pair / 'comparison.json')['pairs']
                      if v['task_id'] == 89 and v['condition'] == 'clean')
    assert comparison['baseline_closed'] == 32 and comparison['all_compared_fields_equal']
    assert not comparison['both_sealed_terminals']
    sources = ['audit_offline_development_postexit.py', 'publish_completed_pair.py', 'extend_semantic_coverage_registry.py']
    for name in sources:
        compile((HERE / name).read_text('utf8'), name, 'exec')
    dest = HERE / ('ongoing-GUI-checkpoint-' + str(time.time_ns()))
    dest.mkdir()
    for name in sources:
        (dest / name).write_bytes((HERE / name).read_bytes())
    save(dest / 'receipt.json', {
        'time': time.time(), 'previous_goal_turn': 'progress: complete14 semantic publication and two completed source/native joins',
        'this_goal_turn': 'progress:16 new actual main requests fully audited; original GUI verified live; future audit readers compiled only',
        'native_audit': str(native), 'native_audit_seal_sha256': sha(native / 'seal.json'),
        'cumulative_main_raw_verifications_at_original_times': 293, 'cumulative_Flash_raw_verifications': 171,
        'new_main_raw_requests_audited': 16, 'old_raw_requests_not_freshly_rehashed': True,
        'latest_actual_identity_snapshot': str(progress), 'snapshot_sha256': sha(progress),
        'partial_pair_comparison': str(pair), 'partial_pair_seal_sha256': sha(pair / 'seal.json'),
        'T089_baseline_closed': 32, 'partial_inputs_text_images_actions_equal': True, 'pair_complete': False,
        'offline10_postexit_audit_preparation': str(prepared), 'preparation_seal_sha256': sha(prepared / 'seal.json'),
        'new_offline_audit_actually_executed': False, 'offline10_submitted': False,
        'new_generic_publisher_and_registry_only_compiled': True,
        'no_static_preparation_called_a_model_result': True,
        'all_frozen_runtime_and_current_queue_sources_unchanged': True,
        'new_model_GUI_calls_by_inspectors_or_preparation': 0, 'formal_changed_GUI_authorized': False,
        'actual_GUI_calls_continue_in_original_queue': True,
        'new_semantic_labels_in_this_turn': 0, 'Mirage_reduction': None, 'effectiveness_proven': False, 'goal': 'active'})
    old = dest / 'previous-heads'
    old.mkdir()
    for p in (BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md'):
        (old / p.name).write_bytes(p.read_bytes())
    save(dest / 'seal.json', {str(p.relative_to(dest)): sha(p) for p in dest.rglob('*') if p.is_file()})
    head = ('## 最新补充：2026-11-14 原GUI仍运行，新16主请求已核；未新增模型条件\n\n'
            f'仅跟进权威flash-ample-memory-gui-20261114-linked11/{dest.name}/receipt.json。语义发布仍complete14-review-publication-1794664174681886700，不重复旧T089三误读/终局或T000结果。新live-evidence-incremental-1794664345115396200已完成：16新raw主请求，累计293主/171Flash，实际UID/fullcmd/start/UUID/compute与17/9继承锁通过；旧raw引用原检查时间，最终退出全量仍待做。CPU仍171，无Flash新请求时不重复旧CPU审核。所有本轮审计会话22420已完成，无悬挂审计会话。\n\n'
            '最新实际compact-progress-1794665218014967300：14/29终局、T089 clean baseline第33决策生成、307主完整回复、171Flash；后续调用不混入293已核数字。新pair-trace-equivalence-1794665269530982800只32已闭baseline对50gate，全部已比body/文字/原图/动作/后图相等，但不是完整配对，baseline未分配完整语义标签。队列/74冻结源不改，不重跑任何旧入口或终局。目标ACTIVE。\n\n'
            '新增audit_offline_development_postexit.py仅准备并编译读者，offline10-audit-preparation-1794664950047892500为最新，旧1794664638735831300源码保留；没有实际离线调用或退出审计。真正10离线结束后才能核全部83源/原图全史+292实际token/CPU-prepared-firstforward完整raw/sequence/EOS/单次generate/原始参数/实际退出/全postexit文件SHA/日志链/8卡保留秒；技术失败分开保全。新增publish_completed_pair.py和extend_semantic_coverage_registry.py仅语法/入口检查，尚未用于新配对发布或标签扩展。必须完整源审和真实终局后使用，不能强行复用、填未决或把空/技术失败算语义零。\n\n'
            '已批准10仍未提交：全部29正常结束与旧GUI/main/Flash/launcher实际退出后只一次submit_offline_development.py；10固定新主调用/2048输出/system+292native tokens，0GUI/Flash/scorer/自动重试，不重问，不自动发布正式改版GUI。无新用户决定或真实效果结论；以下旧头为历史。\n\n')
    for p in (BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md'):
        p.write_text(head + p.read_text(encoding='utf8'), encoding='utf8')
    print(json.dumps({'checkpoint': str(dest), 'actual_new_main_requests_audited': 16,
                      'GUI_continues': True, 'offline10_submitted': False, 'goal': 'active'}))


if __name__ == '__main__':
    main()
