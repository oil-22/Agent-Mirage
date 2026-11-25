"""Publish a newly completed pair from two complete, already joined source reviews.

No inference, GUI, labels, repair, or trial is run here. Unknown labels remain
unknown, and a native-format failure is not admitted as a semantic zero.
"""
import argparse
import json
import time
from pathlib import Path
from control import BASE, HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert root.resolve().parent == HERE
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', type=int, required=True)
    parser.add_argument('--condition', choices=['clean', 'stale_replace'], required=True)
    for name in ['baseline-join', 'gate-join', 'pair', 'native', 'Flash-CPU', 'usage']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--terminals', type=Path, required=True)
    parser.add_argument('--progress', type=Path, required=True)
    args = parser.parse_args()
    roots = {name: getattr(args, name.replace('-', '_')).resolve() for name in
             ['baseline-join', 'gate-join', 'pair', 'native', 'Flash-CPU', 'usage']}
    for root in roots.values():
        verify(root)
    assert args.terminals.resolve().parent == args.progress.resolve().parent == HERE
    prefix = 'flash14-T%03d-%s-' % (args.task, args.condition)
    pair = next(v for v in load(roots['pair'] / 'comparison.json')['pairs']
                if v['task_id'] == args.task and v['condition'] == args.condition)
    assert pair['both_sealed_terminals'], 'Do not publish a partial pair as complete'
    alltraces = load(roots['pair'] / 'source-traces.json')['runs']
    terminals = {v['run']['run_id']: v for v in load(args.terminals)['result']['terminals']}
    native = load(roots['native'] / '3090.json')
    native_summary = load(roots['native'] / 'summary.json')
    mains = {v['request_id']: v for v in native['sealed_main_requests']}
    flashes = {v['request_id']: v for v in native['sealed_Flash_requests']}
    cpu = {v['request_id']: v for v in load(roots['Flash-CPU'] / 'cumulative-report.json')['result']['requests']}
    costs = load(roots['usage'] / 'summary.json')['by_run']
    arms = {}
    for arm in ['baseline', 'gate']:
        root = roots[arm + '-join']
        joined = load(root / 'review-joined.json')
        run_id = prefix + arm
        assert joined['run_id'] == run_id
        source = Path(joined['source_review'])
        verify(source)
        review = load(source / 'review.json')
        assert review['completed_trajectory_review'] and not review['partial_prefix_only']
        assert review['unreviewed_within_exported_prefix'] == 0
        assert review['rows'] == [v['source_label_unchanged'] for v in joined['rows']]
        terminal = terminals[run_id]
        assert not terminal['infrastructure_failure'] and terminal['cleanup_error'] is None
        assert terminal['outcome'] != 'native_contract_failure'
        bound = joined['completed_controller_binding']
        assert terminal['terminal_sha256'] == bound['terminal_sha256']
        assert terminal['event_chain_head'] == bound['chain']['head']
        assert terminal['event_chain_count'] == bound['chain']['verified_prefix_events']
        assert terminal['actor_calls'] == joined['candidate_coverage'] == len(joined['rows'])
        trace = next(v for v in alltraces if v['run']['run_id'] == run_id)
        assert trace['sealed_terminal'] and trace['terminal_sha256'] == terminal['terminal_sha256']
        assert len(trace['closed_actor_prefix']) == terminal['actor_calls']
        for row, trace_row in zip(joined['rows'], trace['closed_actor_prefix']):
            binding = row['native_and_controller_binding']
            actual = mains[binding['request_id']]
            assert actual['run_id'] == run_id and actual['actual_tensor_files_verified'] and actual['natural_EOS']
            assert actual['seal_sha256'] == binding['request_seal_sha256']
            assert actual['request_id'] == trace_row['actor_request_id']
            assert actual['body_sha256'] == trace_row['body_sha256']
            assert actual['current_image_sha256'] == binding['image_sha256'] == trace_row['delivered_PNG_sha256']
            gate_id = binding['gate_request_id']
            if arm == 'gate':
                online, independent = flashes[gate_id], cpu[gate_id]
                assert online['seal_sha256'] == independent['seal_sha256']
                assert online['decision'] == independent['decision'] == 'YES'
                assert online['image_sha256'] == independent['image_sha256'] == actual['current_image_sha256']
            else:
                assert gate_id is None
        count = joined['candidate_coverage']
        assert count >= 1
        assert costs[run_id]['calls'] == count
        positive = [v['candidate'] for v in review['rows'] if v['candidate_semantic_Mirage'] is True and not v['pure_native_WAIT']]
        unresolved = [v['candidate'] for v in review['rows'] if v['candidate_semantic_Mirage'] is None and not v['pure_native_WAIT']]
        whole = True if positive else None if unresolved else False
        assert whole is joined['trajectory_semantic_Mirage']
        arms[arm] = {'run_id': run_id, 'complete_source_native_join': str(root),
                     'join_seal_sha256': sha(root / 'seal.json'), 'source_review': str(source),
                     'source_review_seal_sha256': sha(source / 'seal.json'),
                     'candidate_coverage': count, 'literal_negative_candidates': review['literal_negative_candidates'],
                     'definite_positive_candidates': positive, 'unresolved_candidates': unresolved,
                     'trajectory_semantic_Mirage': whole, 'terminal': terminal, 'primary_call_cost': costs[run_id],
                     'rows': joined['rows']}
    if pair['complete_trace_equal']:
        assert [v['source_label_unchanged']['candidate_semantic_Mirage'] for v in arms['baseline']['rows']] == [
            v['source_label_unchanged']['candidate_semantic_Mirage'] for v in arms['gate']['rows']]
    a, b = (arms[arm]['trajectory_semantic_Mirage'] for arm in ['baseline', 'gate'])
    change = None if a is None or b is None else (int(a) - int(b)) * 100
    snapshot = load(args.progress)
    done = snapshot['4090']['result']['sealed_terminals']
    assert done >= len(terminals) and len(terminals) >= 2
    dest = HERE / ('T%03d-%s-complete-pair-publication-' % (args.task, args.condition) + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    previous = load(HERE / 'semantic-review-current.json')
    save(dest / 'previous-semantic-review-current.json', previous)
    save(dest / 'review-joined.json', {
        'time': time.time(), 'task_id': args.task, 'condition': args.condition, 'arms': arms,
        'pair_comparison': str(roots['pair']), 'pair_comparison_seal_sha256': sha(roots['pair'] / 'seal.json'),
        'complete_trace_equal': pair['complete_trace_equal'],
        'native_audit': str(roots['native']), 'native_audit_seal_sha256': sha(roots['native'] / 'seal.json'),
        'independent_Flash_CPU_audit': str(roots['Flash-CPU']), 'Flash_CPU_seal_sha256': sha(roots['Flash-CPU'] / 'seal.json'),
        'terminal_audit': str(args.terminals), 'terminal_audit_sha256': sha(args.terminals),
        'native_old_raw_checks_referenced_at_original_times': True, 'final_full_postexit_rehash_still_required': True,
        'within_this_pair_absolute_Mirage_reduction_pp_if_resolved': change,
        'not_independent_task_replicates_or_overall_effect': True, 'unknown_not_converted_to_no_Mirage': True,
        'reviewer_count': 1, 'fully_blind': False, 'new_independent_reviewers_from_equal_trace_reuse': 0,
        'score_or_gate_not_used_as_semantic_truth': True,
        'Mirage_reduction': None, 'effectiveness_proven': False, 'goal': 'active', 'new_model_GUI_calls': 0})
    reportname = 'T%03d-%s完整配对语义审查-20261114.md' % (args.task, args.condition)
    lines = [f'# T{args.task:03d} {args.condition} 完整配对审查', '',
             f'两臂已真正结束并完成全部候选源审查。完整轨迹相等：{pair["complete_trace_equal"]}。', '',
             '| 指标 | baseline | Flash gate |', '|---|---:|---:|']
    for title, key in [('主自然EOS回复', 'actor_calls'), ('环境动作', 'environment_actions'),
                       ('Flash回复', 'Flash_replies'), ('复拍', 'recaptures'), ('官方任务分数', 'official_reward')]:
        lines.append('| %s | %s | %s |' % (title, arms['baseline']['terminal'][key], arms['gate']['terminal'][key]))
    lines += ['', '| 语义审查 | baseline | Flash gate |', '|---|---|---|']
    for title, key in [('确定阳性候选', 'definite_positive_candidates'), ('未决候选', 'unresolved_candidates'),
                       ('整轨语义Mirage', 'trajectory_semantic_Mirage')]:
        lines.append('| %s | %s | %s |' % (title, arms['baseline'][key], arms['gate'][key]))
    lines += ['', f'仅本配对的已解决整轨标签绝对差（baseline减gate）：{change}个百分点；null表示不能计算。'
              '这不是总体降低率、显著性或独立任务重复。即使完成后纠正，早先边界错误仍计发生；未决不填阴性，纯native WAIT排除。', '',
              '源标签及全部合法历史/原图审查先封存于各自来源根，再关联真实完整原生输入、自然EOS、Flash同PNG传递、'
              '原始解析和实际执行/终局SHA链。全轨相等时透明复用同一审查，不新增独立审查者。单审、非全盲，官方评分和YES不当语义真值。', '',
              '各臂主调用token及summed native秒详见review-joined.json。主7卡+Flash1卡共8张保留GPU；'
              '调用秒合计不等于walltime、货币、能耗或完整部署成本，不据此宣称成本节省。', '',
              f'原队列快照已有{done}/29终局，当前队列/提示不改。已批准10条system+292token离线开发只在全部29正常结束和旧进程真实退出后一次启动。'
              '本报告不批准改版正式GUI，整体效果未证明，目标ACTIVE。']
    (dest / reportname).write_text('\n'.join(lines) + '\n', encoding='utf8')
    save(dest / 'status.json', {'time': time.time(), 'goal': 'active', 'expected_GUI': 29,
        'sealed_GUI_terminals_at_snapshot': done, 'latest_progress_snapshot': str(args.progress),
        'native_audit': {'root': str(roots['native']), 'seal_sha256': sha(roots['native'] / 'seal.json'),
                         'cumulative_main_replies': native_summary['cumulative_verified_main_replies'],
                         'cumulative_Flash_replies': native_summary['cumulative_verified_Flash_replies'],
                         'old_raw_checks_referenced_at_original_times': True,
                         'final_full_postexit_rehash_still_required': True},
        'actual_processes_and_locks': native_summary['actual_processes'],
        'latest_semantic_review': str(dest), 'current_GUI_sources_changed': False,
        'approved_offline10_submitted': (HERE / 'evidence-discipline-offline-preparation-01/submission.json').exists(),
        'formal_changed_GUI_authorized': False, 'Mirage_reduction': None, 'effectiveness_proven': False,
        'new_model_GUI_calls': 0})
    old = dest / 'previous-heads'
    old.mkdir()
    for p in [BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md', HERE / 'experiment-current.json']:
        (old / p.name).write_bytes(p.read_bytes())
    save(dest / 'seal.json', {str(p.relative_to(dest)): sha(p) for p in dest.rglob('*') if p.is_file()})
    (HERE / 'semantic-review-current.json').write_text(json.dumps({'publication': str(dest),
        'report': str(dest / reportname), 'review_sha256': sha(dest / 'review-joined.json'),
        'seal_sha256': sha(dest / 'seal.json'), 'previous_publication': previous['publication'],
        'partial_prefix_only': False, 'Mirage_reduction': None, 'goal': 'active', 'time': time.time()},
        ensure_ascii=False, indent=2), encoding='utf8')
    (HERE / 'experiment-current.json').write_text(json.dumps({'publication': str(dest),
        'status': str(dest / 'status.json'), 'status_sha256': sha(dest / 'status.json'),
        'report': str(dest / reportname), 'report_sha256': sha(dest / reportname),
        'publication_seal_sha256': sha(dest / 'seal.json'), 'Mirage_reduction': None,
        'goal': 'active', 'time': time.time()}, ensure_ascii=False, indent=2), encoding='utf8')
    head = (f'## 最新：2026-11-14 T{args.task:03d} {args.condition}完整配对已源审并绑定\n\n'
            f'权威flash-ample-memory-gui-20261114-linked11/experiment-current.json和semantic-review-current.json→{dest.name}/{reportname}。'
            f'快照{done}/29终局，baseline/gate各{arms["baseline"]["candidate_coverage"]}/{arms["gate"]["candidate_coverage"]}候选全审，'
            f'完整trace_equal={pair["complete_trace_equal"]}，整轨Mirage={a}/{b}，仅本配对已解决绝对差={change}pp。'
            '单审非全盲，相等复用非新增独立审查；未决/格式失败不算语义零，不是总体率或有效性证明。'
            '实际输入/firstforward/EOS/同PNGFlashCPU/原解析执行/终局SHA链已绑定，旧raw引用原时，退出全量审核待做。\n\n'
            '原29继续不改；已批准10离线只在全部29正常结束及旧GUI/main/Flash/launcher实际退出后一次submit_offline_development.py。'
            '不重问批准10条、不自动发布改版正式GUI，不重跑旧stage/service/gui/holder/容量/终局。目标ACTIVE，效果未证明。以下旧头仅历史。\n\n')
    for p in [BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md']:
        p.write_text(head + p.read_text(encoding='utf8'), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'within_pair_change_pp': change,
                      'overall_effectiveness_proven': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
