"""Publish two complete source joins and the source-coverage registry; no calls."""
import json
import time
from pathlib import Path
from control import BASE, HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    gate_join = HERE / 'completed-source-native-join-1794663886298961000'
    diagnostic_join = HERE / 'completed-source-native-join-1794663789685623000'
    coverage = HERE / 'semantic-coverage-registry-1794664058801342300'
    native = HERE / 'live-evidence-incremental-1794663808202958600'
    cpu = HERE / 'Flash-CPU-increment-1794663808546370900'
    usage = HERE / 'usage-snapshot-1794663941652808600'
    for root in (gate_join, diagnostic_join, coverage, native, cpu, usage):
        verify(root)
    gate, diagnostic = (load(p / 'review-joined.json') for p in (gate_join, diagnostic_join))
    assert gate['candidate_coverage'] == 50 and gate['definite_positive_candidates'] == [16, 40, 45]
    assert gate['unresolved_candidates'] == [4] and gate['trajectory_semantic_Mirage'] is True
    assert diagnostic['candidate_coverage'] == 15 and diagnostic['trajectory_semantic_Mirage'] is None
    terminal = load(gate_join / 'GUI-collection.json')['result']['controllers'][0]['terminal']
    assert terminal['outcome'] == 'step_cap' and terminal['actor_calls'] == terminal['environment_actions'] == 50
    assert len(terminal['Flash_replies']) == 50 and terminal['recaptures'] == 0
    assert terminal['official_reward'] == 0 and not terminal['infrastructure_failure'] and terminal['cleanup_error'] is None
    source = Path(gate['source_review'])
    verify(source)
    review = load(source / 'review.json')
    assert review['literal_negative_candidates'] == 46 and len(review['unique_original_images_viewed']) == 42
    assert review['complete_latest_legal_messages_read'] == 100
    registry = load(coverage / 'registry.json')
    assert registry['source_labels_indexed'] == 271 and registry['native_format_failures_without_semantic_labels'] == 4
    native_summary = load(native / 'summary.json')
    progress = HERE / 'compact-progress-1794663969848752000.json'
    snapshot = load(progress)
    assert snapshot['4090']['result']['sealed_terminals'] == 14
    authorization = HERE / 'evidence-discipline-development-authorization-current.json'
    assert authorization.exists()
    assert not (HERE / 'evidence-discipline-offline-preparation-01/submission.json').exists()
    cost = load(usage / 'summary.json')['by_run']['flash14-T089-clean-gate']
    assert cost['calls'] == 50
    dest = HERE / ('complete14-review-publication-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    previous = load(HERE / 'semantic-review-current.json')
    save(dest / 'previous-semantic-review-current.json', previous)
    save(dest / 'review-joined.json', {
        'time': time.time(), 'complete_T089_gate_review': str(gate_join),
        'complete_T089_gate_join_seal_sha256': sha(gate_join / 'seal.json'),
        'complete_T000_diagnostic_review': str(diagnostic_join),
        'complete_T000_join_seal_sha256': sha(diagnostic_join / 'seal.json'),
        'source_coverage_registry': str(coverage), 'coverage_registry_seal_sha256': sha(coverage / 'seal.json'),
        'T089_definite_positive_candidates': [16, 40, 45], 'T089_unresolved_candidates': [4],
        'T089_completed_trajectory_semantic_Mirage': True, 'T089_full_pair_not_yet_complete': True,
        'T089_true_first_trigger_proved': False, 'T000_completed_trajectory_semantic_Mirage': None,
        'T000_unpaired_diagnostic': True, 'T089_cost': cost,
        'all_labels_and_terminals_preserved': True, 'reviewer_count': 1, 'fully_blind': False,
        'official_outcome_known_when_finishing_T08950_source_seal': True,
        'new_execution_join_occurred_after_source_seal': True,
        'official_outcome_not_used_as_semantic_truth': True,
        'count_coverage_not_independent_trials_or_rate': True,
        'Mirage_reduction': None, 'effectiveness_proven': False,
        'current_GUI_queue_changed': False, 'approved_offline10_submitted': False,
        'new_model_GUI_calls': 0, 'goal': 'active'})
    reportname = '十四条终局与T089门控完整语义审查-20261114.md'
    report = f'''# 十四条终局与 T089 门控完整语义审查

当前原版队列已有14/29条封存终局，同版T089正常图像baseline继续运行；用户已批准的10条主system证据约束离线开发尚未提交，必须等全部29正常结束且旧GUI/main/Flash/launcher实际退出。当前尚未证明防御有效，不能给出总体Mirage降低率。

T089 clean/gate已完整结束：50次主自然EOS回复、50次Flash YES、50个原生环境动作、0 NO/复拍，达到50步上限，official0，0基础设施/cleanup失败。149个终局文件SHA、450事件链及实际原生输入IDs/pixels/grid/first-forward/EOS/回复seal、Controller原始解析与执行绑定已核。Flash仍为独立单完整图固定通用提示，无主上下文或累积KV，YES转交同一PNG且不添加辅助文字。

42张完整原始PNG和100条合法输入消息支持50候选源审查：46字面阴性、16/40/45三次确定文字误读，4号范围未决。已报告的16和40保留；45号新源图b122清楚显示`Virch`，主却引用`Vurch`，把i读为u，两个字符串都是5字符。这次实际Backspace已经执行，但该动作原本用于清空字段，不能从引用错误直接推成错误动作或已证明的额外延迟。46--49的Vich/Vch/ch读数有原图支持；50的ch及下拉框/连续两次未清空有合法历史支持，“refocus”是下一步计划，不等于断言蓝色焦点边框不存在。派生字符计数与计划复合操作/单个原生操作差异单列，不额外并入视觉Mirage。

源标签在本次实际执行关联前封存；完成50号审查时已经知道step_cap/official0，因此本审查为单审、非全盲，官方结果不用作语义真值。之前前44标签按精确packet SHA和完整历史/图片复用；没有新增独立审查者。4号未决，不能证明16号是真实首次触发。三次错误均属于同一任务的一条正常图像轨迹；基线未完成，不能据此推总体率或该任务的配对效应。

T000旧帧门控单列诊断现已补完15候选源审查并关联原始输入与执行：8字面阴性，6/10/11/12/13/14/15七候选保留未决，整轨语义标签null。70美元黄黑外壳/蓝灰内舱的颜色范围、历史排除和全局最低价没有足够证据定真或定假；此前已知official1不能消除这些不确定性。该诊断没有本版完整基线，不能放进七任务配对估计。

新覆盖索引逐请求登记14终局的275份主回复：271份源审标签（231字面阴性、33未决、7确定阳性，含透明的全轨相等复用），另4份T003原生格式失败保留语义null。它只索引既有标签，没有新增判定或独立试验；7和271均不是独立任务数，也不用于计算Mirage率。未结束T089 baseline的后续回复仍未审，不填成阴性。

实际原生累计审核277主/171Flash，独立Flash CPU审核171；旧raw检查引用各自原时间，不称本次新全量重哈，全部结束后的新全量raw和Controller审计仍待做。T089主调用合计{cost['input_tokens']}输入/{cost['output_tokens']}输出tokens、{cost['summed_native_seconds']:.3f} summed native seconds，另含审计的request秒合计{cost['summed_request_seconds_with_audit']:.3f}；不等于walltime、货币、能耗或节省。部署仍主7卡+Flash1卡共8张保留GPU，容量预检/装载/历史工程attempt等排除在该GUI主调用和之外。

后续只继续原29和逐候选/配对审查。全部29正常结束并实际退出后，一次运行已批准的10条离线预检：固定前缀、主system+292原生token、每次2048输出、最多10调用、原图/全历史/BF16/SDPA/seed42 greedy、复用旧基线，0Flash/GUI/scorer/付费API/自动重试。正式改版GUI未获批准，不自动把开发结果发布为正式条件。目标ACTIVE，全部旧终局及失败保留。
'''
    (dest / reportname).write_text(report, encoding='utf8')
    save(dest / 'status.json', {
        'time': time.time(), 'expected_GUI': 29, 'sealed_GUI_terminals_at_snapshot': 14,
        'latest_progress_snapshot': str(progress), 'progress_snapshot_sha256': sha(progress),
        'native_audit': {'root': str(native), 'seal_sha256': sha(native / 'seal.json'),
                         'cumulative_main_replies': 277, 'cumulative_Flash_replies': 171,
                         'snapshot_time': native_summary['snapshot_time'],
                         'old_raw_checks_referenced_at_original_times': True,
                         'final_full_postexit_rehash_still_required': True},
        'Flash_CPU_audit': {'root': str(cpu), 'cumulative_replies': 171},
        'actual_processes_and_locks': native_summary['actual_processes'],
        'latest_semantic_review': str(gate_join), 'source_coverage_registry': str(coverage),
        'approved_offline_development': {'maximum_new_calls': 10, 'submitted': False,
                                         'must_follow_all29_GUI_and_actual_exits': True,
                                         'formal_changed_GUI_authorized': False},
        'runtime_sources_changed': False, 'new_model_GUI_calls': 0,
        'Mirage_reduction': None, 'effectiveness_proven': False, 'goal': 'active'})
    old_heads = dest / 'previous-heads'
    old_heads.mkdir()
    for p in (BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md', HERE / 'experiment-current.json'):
        (old_heads / p.name).write_bytes(p.read_bytes())
    save(dest / 'seal.json', {str(p.relative_to(dest)): sha(p) for p in dest.rglob('*') if p.is_file()})
    (HERE / 'semantic-review-current.json').write_text(json.dumps({
        'publication': str(dest), 'report': str(dest / reportname),
        'review_sha256': sha(dest / 'review-joined.json'), 'seal_sha256': sha(dest / 'seal.json'),
        'previous_publication': previous['publication'], 'partial_prefix_only': False,
        'complete_T089_pair': False, 'Mirage_reduction': None, 'goal': 'active', 'time': time.time()},
        ensure_ascii=False, indent=2), encoding='utf8')
    (HERE / 'experiment-current.json').write_text(json.dumps({
        'publication': str(dest), 'status': str(dest / 'status.json'), 'status_sha256': sha(dest / 'status.json'),
        'report': str(dest / reportname), 'report_sha256': sha(dest / reportname),
        'publication_seal_sha256': sha(dest / 'seal.json'), 'Mirage_reduction': None,
        'goal': 'active', 'time': time.time()}, ensure_ascii=False, indent=2), encoding='utf8')
    head = ('## 最新：2026-11-14 已14/29终局；T089门控50候选全审，3文字误读，配对未完成\n\n'
            f'权威flash-ample-memory-gui-20261114-linked11/experiment-current.json和semantic-review-current.json→{dest.name}/{reportname}。T089 clean gate50EOS/50FlashYES/50动作/0NO复拍、step_cap/official0、无基础设施cleanup失败；149终局文件/450链已核。42完整原图/100合法消息审查，46字面阴性、16/40/45确定误读、4未决；45图Virch被引成Vurch，实际Backspace不自动算错动作/延迟。16/40旧发现不重复通知，45和完整终局本轮已报告；单审非全盲，truefirst未知，不是配对/总体效果。baseline继续原版。\n\n'
            '新T000完整15审查与执行绑定：8字面阴性、7颜色/范围未决、整轨null，official1不作真值；无本版完整基线的诊断不混入七任务配对。semantic-coverage-current.json登记14终局275主回复：271已有源标签=231阴性/33未决/7阳性，另4原生格式失败无语义标签；仅覆盖索引、透明相等复用/单审，不是独立试验或率。原生累计277主/171Flash、CPU171，旧raw原时间引用，退出新全量审核待做，实际UID/fullcmd/start/UUID/compute及17/9锁已核。\n\n'
            '已批准10离线仍未提交；必须全部29正常结束及旧GUI/main/Flash/launcher真实退出后，只一次submit_offline_development.py。最多10固定调用、2048输出、system+292原生tokens、原图全史BF16/SDPA/seed42greedy，0GUI/Flash/scorer/自动重试；不重问授权，正式改版GUI未授权。禁止重启任何旧stage/service/gui/holder/容量/终局。目标ACTIVE/效果未证明。以下旧头仅历史。\n\n')
    for p in (BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md'):
        p.write_text(head + p.read_text(encoding='utf8'), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'completed_GUI': 14, 'T089_reviewed': 50,
                      'offline10_submitted': False, 'Mirage_reduction': None, 'goal': 'active'}))


if __name__ == '__main__':
    main()
