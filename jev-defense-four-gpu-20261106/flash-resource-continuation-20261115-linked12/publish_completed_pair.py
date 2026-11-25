"""Publish a complete source-reviewed pair without inferring labels from scores."""
import argparse
import json
import time
from pathlib import Path
from control import HERE, save, sha


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(root):
    assert root.parent == HERE
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', type=int, required=True)
    parser.add_argument('--condition', choices=['clean', 'stale_replace'], required=True)
    for name in ['baseline', 'gate', 'trace', 'registry']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    roots = {k: getattr(args, k).resolve() for k in ['baseline', 'gate', 'trace', 'registry']}
    for root in roots.values():
        verify(root)
    prefix = 'flash14-T%03d-%s-' % (args.task, args.condition)
    pointer = HERE / ('pair-T%03d-%s-current.json' % (args.task, args.condition))
    assert not pointer.exists(), 'Use the already published immutable pair'
    joined = {arm: load(roots[arm] / 'review-joined.json') for arm in ['baseline', 'gate']}
    registry = load(roots['registry'] / 'registry.json')
    pair = next(v for v in load(roots['trace'] / 'comparison.json')['pairs']
                if v['task_id'] == args.task and v['condition'] == args.condition)
    assert pair['both_noninfrastructure_sealed_terminals']
    summaries = {}
    for arm, j in joined.items():
        assert j['run_id'] == prefix + arm
        reviewroot = Path(j['source_review'])
        verify(reviewroot)
        assert sha(reviewroot / 'seal.json') == j['source_review_seal_sha256']
        source = load(reviewroot / 'review.json')
        assert source['completed_trajectory_review'] and not source['partial_prefix_only']
        assert source['unreviewed_within_exported_prefix'] == 0
        terminal = pair[arm + '_terminal']
        indexed = next(v for v in registry['runs'] if v['run_id'] == j['run_id'])
        assert indexed['source_review_complete'] and not indexed['native_contract_failure']
        assert indexed['terminal_sha256'] == j['completed_controller_binding']['terminal_sha256']
        assert j['candidate_coverage'] == source['candidate_coverage'] == terminal['actor_calls']
        assert source['definite_positive_candidates'] == j['definite_positive_candidates'] == indexed['definite_positive_candidates']
        assert source['unresolved_candidates'] == j['unresolved_candidates'] == indexed['unresolved_candidates']
        labels = [v['candidate_semantic_Mirage'] for v in source['rows'] if not v['pure_native_WAIT']]
        whole = True if any(v is True for v in labels) else None if any(v is None for v in labels) else False
        assert source['trajectory_semantic_Mirage'] is j['trajectory_semantic_Mirage'] is indexed['trajectory_semantic_Mirage'] is whole
        assert not terminal['infrastructure_failure']
        summaries[arm] = {'candidate_coverage': j['candidate_coverage'], 'trajectory_semantic_Mirage': whole,
            'definite_positive_candidates': j['definite_positive_candidates'],
            'unresolved_candidates': j['unresolved_candidates'], 'official_reward': terminal['official_reward'],
            'injection_fired': terminal['injection_fired'], 'outcome': terminal['outcome'],
            'environment_actions': terminal['environment_actions'],
            'source_execution_join': str(roots[arm]), 'join_seal_sha256': sha(roots[arm] / 'seal.json'),
            'source_review': str(reviewroot), 'source_review_seal_sha256': sha(reviewroot / 'seal.json')}
    if pair['complete_trace_equal']:
        assert pair['same_closed_length'] and pair['first_difference'] is None
        assert [v['source_label_unchanged']['candidate_semantic_Mirage'] for v in joined['baseline']['rows']] == [
            v['source_label_unchanged']['candidate_semantic_Mirage'] for v in joined['gate']['rows']]
    a, b = (summaries[v]['trajectory_semantic_Mirage'] for v in ['baseline', 'gate'])
    reduction = None if a is None or b is None else a is True and b is False
    dest = HERE / ('T%03d-%s-complete-pair-' % (args.task, args.condition) + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(dest / 'status.json', {'time': time.time(), 'task_id': args.task, 'condition': args.condition,
        'arms': summaries, 'complete_trace_equal': pair['complete_trace_equal'],
        'all_actual_complete_bodies_history_PNGs_replies_actions_postimages_equal': pair['complete_trace_equal'],
        'first_trace_difference': pair['first_difference'],
        'within_this_pair_reduced_trajectory_occurrence': reduction,
        'trace': str(roots['trace']), 'trace_seal_sha256': sha(roots['trace'] / 'seal.json'),
        'semantic_registry': str(roots['registry']), 'registry_seal_sha256': sha(roots['registry'] / 'seal.json'),
        'completed_logical_GUI_configurations_at_registry_snapshot': registry['completed_trajectories'],
        'old_partial_occurrences_and_costs_preserved': True,
        'unknown_not_semantic_zero': True, 'official_success_not_semantic_truth': True,
        'single_reviewer_nonblind_and_exact_source_reuse_disclosed': True,
        'whole_Mirage_occurrence_not_wrong_native_action_count': True,
        'true_first_trigger_established': False,
        'counts_not_independent_tasks_or_overall_rate': True,
        'current_group_final_fresh_postexit_audits_still_required': True,
        'formal_changed_GUI_authorized': False, 'approved_offline10_not_auto_GUI_authorization': True,
        'new_model_GUI_calls': 0, 'effectiveness_proven': False, 'Mirage_reduction': None, 'goal': 'active'})
    report = dest / ('T%03d-%s完整配对源审结果-20261115.md' % (args.task, args.condition))
    lines = ['# 完整配对源审结果', '', '| 条件 | 完整候选 | 确定发生候选 | 未决候选 | 整轨Mirage | 官方得分 |',
        '|---|---:|---|---|---|---:|']
    for arm, v in summaries.items():
        lines.append('| %s | %d | %s | %s | %s | %s |' % (arm, v['candidate_coverage'],
            str(v['definite_positive_candidates']), str(v['unresolved_candidates']),
            str(v['trajectory_semantic_Mirage']), str(v['official_reward'])))
    lines += ['', '完整实际body/合法历史、捕获和交付原PNG、回复、原生动作与后图全相同：%s。' % pair['complete_trace_equal'],
        '仅本配对整轨发生是否降低：%s。这不是总体触发率、显著性或独立任务结论。' % reduction,
        '', '每条标签先据合法源图与完整消息封存，再绑定实际输入/first-forward/EOS/同PNG的Flash CPU原始概率和Controller。完全相同的输入/回复允许透明复用同一审查，不增加独立审查者。未决不当作阴性；后来恢复、任务得分和STOP都不删除已经发生的错误。叙述错误不自动等于原生动作错误。',
        '', '父技术attempt、未交付生成和全部成本另行保留，不覆盖、不清零、不当作新增独立试验。旧父组退出全量审计已完成；当前组退出后的fresh全量raw与Controller仍待。',
        '', '原队列继续原条件。用户批准10条离线开发预检，只有全部29逻辑终局/seals/链及实际模型、GUI、launcher退出后才单次提交。正式新提示GUI尚未授权。整体降低未证明，目标ACTIVE。', '']
    report.write_text('\n'.join(lines), encoding='utf8')
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    state = {'publication': str(dest), 'report': str(report), 'seal_sha256': sha(dest / 'seal.json'),
        'time': time.time(), 'goal': 'active', 'effectiveness_proven': False}
    save(pointer, state)
    archive = dest / 'previous-heads'
    archive.mkdir()
    header = (f'## 最新：{registry["completed_trajectories"]}/29终局；T{args.task:03d} {args.condition}完整配对已审\n\n'
        f'权威 {HERE.name}/{dest.name}/status.json 与 {report.name}。baseline/gate各'
        f'{summaries["baseline"]["candidate_coverage"]}/{summaries["gate"]["candidate_coverage"]}完整回复，'
        f'原始完整body/历史/捕获与交付PNG/候选/原生动作/后图全相同={pair["complete_trace_equal"]}；'
        f'整轨Mirage={a}/{b}，仅本配对是否减少={reduction}。'
        f'两臂official={summaries["baseline"]["official_reward"]}/{summaries["gate"]["official_reward"]}，'
        '不作语义真值。旧错误不因恢复清零，未决保持；精确来源复用非新增独立审查者。配对结论报告后不重复旧错误为新发现，非总体率/显著性。\n\n'
        f'覆盖索引 {roots["registry"].name}：{registry["completed_native_replies"]}完整回复='
        f'{registry["source_labels_indexed"]}已有源标签+{registry["native_format_failures_without_semantic_labels"]}格式失败，'
        '不是语义通过数。父组fresh原始11946文件/396公开主/199Flash/1未交付生成和17GUI Controller均完成并seal；禁止再poll15124/重跑父完整审核。'
        '父技术部分及成本另保留。当前组退出fresh raw/Controller和剩余源审仍待。\n\n'
        '原GUI队列继续原条件；已批准10离线只在全部29逻辑终局/30attempt seals和链及全部实际模型/GUI/launcher退出后，'
        'collect_aggregate_completion.py再offline_followup_control.py submit一次。原+292tokens/10x2048/完整原图历史/种子精度/0GUI Flash scorer retry保留，'
        '不重问、不自动发布正式新提示GUI、不重启旧stage/service/gui/容量/终局。目标ACTIVE、整体降低未证。以下为历史快照。\n\n')
    for i, path in enumerate([HERE.parent / 'HANDOFF.md', HERE.parent / 'README.md', HERE / 'CONTINUATION.md', HERE / 'README.md']):
        data = path.read_bytes()
        (archive / ('%02d-%s' % (i, path.name))).write_bytes(data)
        path.write_bytes(header.encode('utf8') + data)
    for name in ['continuation-current.json', 'experiment-current.json', 'semantic-review-current.json']:
        path = HERE / name
        if path.exists():
            (archive / name).write_bytes(path.read_bytes())
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'report': str(report), 'task': args.task,
        'condition': args.condition, 'complete_trace_equal': pair['complete_trace_equal'],
        'trajectory_labels': [a, b], 'within_this_pair_reduction': reduction,
        'new_model_GUI_calls': 0, 'goal': 'active'}))


if __name__ == '__main__':
    main()
