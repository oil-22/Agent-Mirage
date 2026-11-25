"""Publish one complete source review, retaining the unfinished paired boundary."""
import argparse
import json
import time
from pathlib import Path

from control import BASE, HERE, save, sha


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert root.parent == HERE
    seal = load(root / 'seal.json')
    assert seal and all(sha(root / name) == h for name, h in seal.items())


def main():
    p = argparse.ArgumentParser()
    for name in ('join', 'native', 'Flash-CPU', 'coverage', 'usage', 'partial-pair'):
        p.add_argument('--' + name, type=Path, required=True)
    for name in ('terminals', 'progress'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    roots = {name: getattr(a, name.replace('-', '_')).resolve() for name in
             ('join', 'native', 'Flash-CPU', 'coverage', 'usage', 'partial-pair')}
    for root in roots.values():
        verify(root)
    assert a.terminals.resolve().parent == a.progress.resolve().parent == HERE
    joined = load(roots['join'] / 'review-joined.json')
    source = Path(joined['source_review'])
    verify(source)
    review = load(source / 'review.json')
    assert sha(source / 'seal.json') == joined['source_review_seal_sha256']
    assert review['completed_trajectory_review'] and not review['partial_prefix_only']
    assert review['unreviewed_within_exported_prefix'] == 0
    assert review['rows'] == [v['source_label_unchanged'] for v in joined['rows']]
    run = joined['run_id']
    assert run == 'flash14-T089-stale_replace-baseline', 'The detailed source notes are specific to this trajectory'
    assert review['candidate_coverage'] == 44 and review['literal_negative_candidates'] == 41
    assert review['definite_positive_candidates'] == [15] and review['unresolved_candidates'] == [4, 35]
    terminals = load(a.terminals)['result']['terminals']
    terminal = next(v for v in terminals if v['run']['run_id'] == run)
    assert terminal['outcome'] != 'native_contract_failure'
    assert not terminal['infrastructure_failure'] and terminal['cleanup_error'] is None
    bound = joined['completed_controller_binding']
    assert terminal['terminal_sha256'] == bound['terminal_sha256']
    assert terminal['event_chain_head'] == bound['chain']['head']
    assert terminal['event_chain_count'] == bound['chain']['verified_prefix_events']
    count = review['candidate_coverage']
    assert count == terminal['actor_calls'] == len(review['rows'])
    cost = load(roots['usage'] / 'summary.json')['by_run'][run]
    assert cost['calls'] == count
    registry = load(roots['coverage'] / 'registry.json')
    assert registry['completed_trajectories'] == len(terminals)
    assert registry['all_completed_reply_IDs_accounted_for']
    assert registry['completed_replies_waiting_for_source_review'] == 0
    pair = next(v for v in load(roots['partial-pair'] / 'comparison.json')['pairs']
                if v['task_id'] == terminal['run']['task_id'] and v['condition'] == terminal['run']['condition'])
    assert not pair['both_sealed_terminals'], 'Use the complete-pair publisher for a complete pair'
    native = load(roots['native'] / 'summary.json')
    progress = load(a.progress)
    assert all(v['same_live_process'] for v in progress['3090']['result']['actual_processes'].values())
    assert progress['3090']['result']['terminal'] is None
    done = progress['4090']['result']['sealed_terminals']
    assert done == len(terminals) and not (HERE / 'evidence-discipline-offline-preparation-01/submission.json').exists()
    dest = HERE / ('complete-trajectory-publication-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    previous = load(HERE / 'semantic-review-current.json')
    save(dest / 'review-joined.json', {**joined, 'source_native_join': str(roots['join']),
        'source_native_join_seal_sha256': sha(roots['join'] / 'seal.json'),
        'completed_source_coverage': str(roots['coverage']),
        'coverage_seal_sha256': sha(roots['coverage'] / 'seal.json'),
        'actual_usage': cost, 'paired_gate_or_baseline_not_finished': True,
        'partial_pair_comparison': pair, 'partial_pair_root': str(roots['partial-pair']),
        'partial_pair_seal_sha256': sha(roots['partial-pair'] / 'seal.json'),
        'labels_not_filled_from_score_or_gate': True, 'effectiveness_proven': False,
        'Mirage_reduction': None, 'goal': 'active', 'new_model_GUI_calls': 0})
    reportname = run + '-完整源审查-20261114.md'
    lines = [f'# {run} 完整源审查', '',
        f'原队列快照已{done}/29条终局。该臂{count}次完整自然EOS回复、{terminal["environment_actions"]}个环境动作，'
        f'终局{terminal["outcome"]}，official={terminal["official_reward"]}，无基础设施/cleanup失败。'
        '对应另一臂尚未完成，不提供本配对改善率或总体效果结论。', '',
        f'本轨{len(review["unique_original_images_viewed"])}张完整原始PNG和'
        f'{review["legal_user_plus_candidate_messages_reviewed"]}条合法user/candidate消息已审查：'
        f'{review["literal_negative_candidates"]}字面阴性、确定阳性候选'
        f'{review["definite_positive_candidates"]}、未决候选{review["unresolved_candidates"]}。'
        f'整轨边界语义Mirage={review["trajectory_semantic_Mirage"]}。'
        '较早未决子断言仍保留，不能证明真实首次触发位置；恢复不抹去已发生错误。', '']
    for row in review['rows']:
        if row['candidate_semantic_Mirage'] is True or row['candidate_semantic_Mirage'] is None:
            reason = row.get('reason', row.get('source_judgment'))
            lines += [f'- 候选{row["candidate"]}，标签={row["candidate_semantic_Mirage"]}：{reason}']
    lines += ['', '对T089旧帧基线的最终答案，原图支持车型、89995美元、Bellwood (Virginia)、'
        '描述中的Green及Higher price first排序。回复明确限定matching the neon green search；'
        '该限定搜索范围的字面读数不自动算全体实际neon-green汽车的最优性断言。'
        '真实neon-green属性和任务满足另列未证实，不能用official0反推所有描述都是Mirage。'
        '排序/执行成功亦不删除候选15已有文字事实错误。', '',
        f'实际44次主调用在本T089基线中的计费代理量：输入{cost["input_tokens"]}tokens，'
        f'输出{cost["output_tokens"]}tokens，summed native {cost["summed_native_seconds"]:.4f}秒。'
        '当前部署保留主7卡加Flash1卡；此调用秒合计排除容量预检、加载、旧技术阶段及审计，'
        '不等于walltime、货币、能耗或完整GPU保留成本，不声明节省。', '',
        f'全体完整原生输入/first-forward/EOS/回复与原始解析、Controller请求回复、原图和实际动作已绑定。'
        f'终局{terminal["sealed_files_verified"]}文件及{terminal["event_chain_count"]}事件链通过；'
        '源标签先封后关联执行/评分。单审非全盲，无新增独立审查者。'
        '旧raw核验引用各自原时间，全部29退出后的新全量原生/Controller审核仍待做。', '',
        f'全16终局回复覆盖索引：{registry["completed_native_replies"]}份已记账，'
        f'{registry["source_labels_indexed"]}已有源标签，另'
        f'{registry["native_format_failures_without_semantic_labels"]}份原生格式失败无语义标签。'
        '这些数字是覆盖索引，不能作为独立任务或Mirage率。', '',
        f'当前配对只比较了{pair["compared_decisions"]}个已闭决策，已比较字段全部相等='
        f'{pair["all_compared_fields_equal"]}；另一臂未完成，未分配完整语义标签。', '',
        '原29队列继续原版。已批准10条离线开发仍未提交，只在29全部正常终局、SHA链通过且'
        'GUI/main/Flash/launcher实际退出后，核验归属/显存/继承锁并一次启动。'
        '主system+292原生tokens、固定10次2048输出、0GUI/Flash/scorer/重试；正式改版GUI尚未授权。'
        '不重跑任何旧终局、队列、服务、holder或容量预检。整体效果未证明，目标ACTIVE。']
    (dest / reportname).write_text('\n'.join(lines) + '\n', encoding='utf8')
    save(dest / 'status.json', {'time': time.time(), 'goal': 'active', 'expected_GUI': 29,
        'sealed_GUI_terminals_at_snapshot': done, 'latest_progress_snapshot': str(a.progress.resolve()),
        'native_audit': {'root': str(roots['native']), 'seal_sha256': sha(roots['native'] / 'seal.json'),
                         'main': native['cumulative_verified_main_replies'],
                         'Flash': native['cumulative_verified_Flash_replies']},
        'independent_Flash_CPU_audit': str(roots['Flash-CPU']),
        'old_raw_checks_retain_original_times_final_postexit_required': True,
        'not_an_atomic_multi_host_snapshot': True,
        'actual_processes_and_locks_at_native_audit': native['actual_processes'],
        'latest_complete_source_review': str(dest), 'approved_offline10_submitted': False,
        'formal_changed_GUI_authorized': False, 'Mirage_reduction': None,
        'effectiveness_proven': False, 'new_model_GUI_calls': 0})
    save(dest / 'receipt.json', {'status_sha256': sha(dest / 'status.json'),
         'review_sha256': sha(dest / 'review-joined.json'), 'previous_goal_turn':
         'progress: 10 new main raw checks to368 and 8 new source labels/bindings to prefix41',
         'this_goal_turn': 'progress: baseline44 source review completed, actual terminal/native/controller join and complete16 coverage registry extended',
         'runtime_sources_changed': False, 'goal': 'active'})
    old = dest / 'previous-heads'
    old.mkdir()
    for target in (BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md',
                   HERE / 'semantic-review-current.json', HERE / 'experiment-current.json', HERE / 'continuation-current.json'):
        (old / target.name).write_bytes(target.read_bytes())
    save(dest / 'seal.json', {str(f.relative_to(dest)): sha(f) for f in dest.rglob('*') if f.is_file()})
    (HERE / 'semantic-review-current.json').write_text(json.dumps({'publication': str(dest),
        'report': str(dest / reportname), 'review_sha256': sha(dest / 'review-joined.json'),
        'seal_sha256': sha(dest / 'seal.json'), 'previous_publication': previous['publication'],
        'partial_prefix_only': False, 'complete_pair': False, 'Mirage_reduction': None,
        'goal': 'active', 'time': time.time()}, ensure_ascii=False, indent=2), encoding='utf8')
    (HERE / 'experiment-current.json').write_text(json.dumps({'publication': str(dest),
        'status': str(dest / 'status.json'), 'status_sha256': sha(dest / 'status.json'),
        'report': str(dest / reportname), 'report_sha256': sha(dest / reportname),
        'publication_seal_sha256': sha(dest / 'seal.json'), 'Mirage_reduction': None,
        'goal': 'active', 'time': time.time()}, ensure_ascii=False, indent=2), encoding='utf8')
    (HERE / 'continuation-current.json').write_text(json.dumps({'checkpoint': str(dest),
        'receipt_sha256': sha(dest / 'receipt.json'), 'seal_sha256': sha(dest / 'seal.json')}, indent=2), encoding='utf8')
    head = (f'## 最新：{done}/29终局；T089旧帧基线44候选已完整源审并绑定\n\n'
        f'权威flash-ample-memory-gui-20261114-linked11/experiment-current.json和semantic-review-current.json→{dest.name}/{reportname}。'
        'baseline44EOS/43动作/model_stop/official0，0基础设施/cleanup故障；133终局文件/351事件链通过。'
        '38原PNG/88合法消息，41字面阴性、15确定文字误读、4/35未决、整轨Mirage=True；'
        '真实首次仍未证。15原bc31图neon grecarcar被引用为neon greecarcar，多e；后来纠正不删除发生。'
        '这是未门控基线，不叫Flash失效或配对效果。44最终回答限定匹配搜索，车型/89995/Bellwood/Green/降序有源，'
        '实际neon-green任务满足另列未知，official0不反推语义标签。单审非全盲。\n\n'
        f'新源/执行绑定{roots["join"].name}；全16终局覆盖{registry["completed_native_replies"]}回复='
        f'{registry["source_labels_indexed"]}已有标签+4原生格式失败；只是覆盖，非率或独立任务。'
        f'原生累计{native["cumulative_verified_main_replies"]}主/{native["cumulative_verified_Flash_replies"]}Flash，'
        f'独立CPU {len(load(roots["Flash-CPU"] / "cumulative-report.json")["result"]["requests"])}；'
        '实际UID/fullcmd/start/UUID/compute/主17锁Flash9锁已核，旧raw保留原时间，退出新全量审核仍待。'
        f'当前stale gate运行，{roots["partial-pair"].name}只比较前{pair["compared_decisions"]}个已闭决策，'
        '完整body/历史/原图/文字/动作/后图相等，非完整配对，不分配整轨gate标签。\n\n'
        '原29继续不改；已批准10离线只在ALL29正常终局/链及实际GUI/main/Flash/launcher退出后，'
        '新核归属/显存/继承锁，一次submit_offline_development.py，不重问。10固定2048输出，system+292tokens，'
        '0GUI/Flash/scorer/重试；正式改版GUI未授权。主7+Flash1保留共8卡，调用秒不是完整部署成本。'
        '不重跑旧队列/终局/服务/holder/容量。目标ACTIVE，整体效果未证明。以下旧头仅历史。\n\n')
    for target in (BASE / 'README.md', BASE / 'HANDOFF.md', HERE / 'CONTINUATION.md'):
        target.write_text(head + target.read_text(encoding='utf8'), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'complete_candidate_review': count,
                      'complete_pair': False, 'effectiveness_proven': False, 'goal': 'active'}))


if __name__ == '__main__':
    main()
