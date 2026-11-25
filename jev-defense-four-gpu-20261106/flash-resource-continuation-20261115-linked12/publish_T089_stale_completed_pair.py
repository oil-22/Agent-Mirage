"""Publish the completed cross-root pair only after exact full-source/action joins."""
import argparse
import contextlib
import io
import json
import time
from pathlib import Path
from control import HERE, activity, save, sha
from offline_followup_control import PREP


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(root):
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    parser = argparse.ArgumentParser()
    for name in ['join', 'trace', 'terminals', 'native', 'CPU', 'review']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    roots = {name: getattr(args, name).resolve() for name in ['join', 'trace', 'native', 'CPU', 'review']}
    for root in roots.values():
        assert root.parent == HERE
        verify(root)
    joined = load(roots['join'] / 'review-joined.json')
    review = load(roots['review'] / 'review.json')
    run = 'flash14-T089-stale_replace-gate'
    assert joined['run_id'] == run and joined['candidate_coverage'] == 44
    assert review['completed_trajectory_review'] and not review['partial_prefix_only']
    assert joined['source_review'] == str(roots['review'])
    assert joined['source_review_seal_sha256'] == sha(roots['review'] / 'seal.json')
    assert joined['native_audit'] == str(roots['native']) and joined['Flash_CPU_audit'] == str(roots['CPU'])
    trace = load(roots['trace'] / 'comparison.json')
    pair = next(v for v in trace['pairs'] if v['task_id'] == 89 and v['condition'] == 'stale_replace')
    assert pair['both_noninfrastructure_sealed_terminals'] and pair['complete_trace_equal']
    assert pair['baseline_closed'] == pair['gate_closed'] == pair['compared_decisions'] == 44
    assert pair['first_difference'] is None
    terminals = load(args.terminals)['result']['terminals']
    terminal = next(v for v in terminals if v['run']['run_id'] == run)
    assert terminal['terminal_sha256'] == joined['completed_controller_binding']['terminal_sha256']
    assert terminal['outcome'] == 'model_stop' and terminal['official_reward'] == 0
    assert terminal['actor_calls'] == terminal['Flash_request_attempts'] == 44 and terminal['environment_actions'] == 43
    assert not terminal['infrastructure_failure'] and not terminal['cleanup_error'] and terminal['recaptures'] == 0
    old = HERE.parent / 'flash-ample-memory-gui-20261114-linked11'
    baseline_root = old / 'complete-trajectory-publication-1794669922600928300'
    verify(baseline_root)
    baseline = load(baseline_root / 'review-joined.json')
    assert baseline['candidate_coverage'] == 44 and baseline['trajectory_semantic_Mirage'] is True
    assert joined['trajectory_semantic_Mirage'] is True
    assert joined['definite_positive_candidates'] == baseline['definite_positive_candidates'] == [15]
    assert joined['unresolved_candidates'] == baseline['unresolved_candidates'] == [4, 35]
    assert trace['preserved_technical_attempts_excluded_from_normal_pair_replacement']
    assert not (PREP / 'submission.json').exists()
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        activity()
    snapshots = [json.loads(s) for s in stream.getvalue().splitlines()]
    dest = HERE / ('T089-stale-completed-pair-publication-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    native = load(roots['native'] / 'summary.json')
    state = {'time': time.time(), 'goal': 'active', 'new_completed_pair': {'task_id': 89, 'condition': 'stale_replace'},
         'baseline_and_gate_complete_source_coverage': [44, 44],
         'all44_full_bodies_original_PNGs_replies_actions_and_postimages_equal': True,
         'baseline_and_gate_trajectory_Mirage': [True, True], 'within_this_pair_improvement': False,
         'definite_positive_candidates': [15], 'unresolved_candidates': [4, 35],
         'true_first_trigger_established': False, 'native_actions_not_all_labeled_wrong_from_literal_error': True,
         'single_reviewer_explicit_exact_source_reuse_not_new_blind_review': True,
         'baseline_and_gate_official_reward': [0, 0], 'official_reward_not_used_as_semantic_truth': True,
         'new_gate_terminal': terminal, 'cross_root_trace': str(roots['trace']),
         'cross_root_trace_seal_sha256': sha(roots['trace'] / 'seal.json'),
         'source_execution_join': str(roots['join']), 'join_seal_sha256': sha(roots['join'] / 'seal.json'),
         'source_review': str(roots['review']), 'source_review_seal_sha256': sha(roots['review'] / 'seal.json'),
         'native_audit': str(roots['native']), 'native_audit_seal_sha256': sha(roots['native'] / 'seal.json'),
         'cumulative_new_root_raw_verified_main': native['cumulative_verified_main_replies'],
         'cumulative_new_root_raw_verified_Flash': native['cumulative_verified_Flash_replies'],
         'Flash_CPU_audit': str(roots['CPU']), 'Flash_CPU_audit_seal_sha256': sha(roots['CPU'] / 'seal.json'),
         'old_raw_check_times_retained_final_postexit_audits_still_required': True,
         'parent16_noninfrastructure_and_failed_partial_preserved': True,
         'old_partial_source_occurrences_and_costs_not_erased_or_counted_independent_trials': True,
         'normal_logical_terminals_at_terminal_snapshot': 16 + sum(not v['infrastructure_failure'] for v in terminals),
         'expected_normal_logical_terminals': 29, 'actual_process_snapshots': snapshots,
         'offline10_approved_staged_unsubmitted_calls0': True, 'formal_changed_GUI_authorized': False,
         'all29_and_actual_exits_required_before_single_offline_submission': True,
         'source_selection_nonblind_not_independent_tasks': True, 'overall_effectiveness_proven': False,
         'Mirage_reduction': None, 'new_model_GUI_calls_by_publication': 0}
    save(dest / 'status.json', state)
    report = dest / 'T089旧帧完整配对结果-20261115.md'
    report.write_text('''# T089旧帧完整配对：本次未降低Mirage

新linked12的T089旧帧门控正常完成：44次主模型自然回复、44次Flash判定、43次环境动作，以model_stop结束、official0，无基础设施/cleanup失败、无NO复拍。终局完整seal、事件链、实际主输入/first-forward/EOS/原图/Flash原始概率及原生解析执行已绑定。最终全量postexit审计仍待模型组自然退出，当前增量旧raw引用原核验时点。

和父linked11已封存基线相比，全部44个完整body/合法历史、实际捕获与交付原PNG、回复、原生动作和后图均相同。已审基线来源标签因此透明复用，没有新增独立审查者。两臂整轨都有15号确定文字误读；4与35继续未决，真实首次仍未证明。两臂official均0，评分未被用作语义真值，文字误读不等于43个原生动作都错误。这个完整配对没有观察到降低，不能归纳总体效果、模型排名或显著性。

父根旧技术中断attempt的27个已交付回复、未交付第28次生成、已发生的旧错误和成本完整保留，未被新44回复覆盖、清零或计成独立样本。未交付生成不能计作执行、模型语义零或Flash的NO。

剩余原配置继续，不改变当前主提示、图像、完整历史、Flash单图无状态YES/NO、原生解析执行评分及预算。获批10条system证据约束离线预检已部署但仍0调用；必须全部29逻辑终局/seal/链及相关模型、GUI和launcher实际退出后，只消耗一次10调用授权。它不代表正式新提示GUI许可。整体目标ACTIVE，降低尚未证明。
''', encoding='utf8')
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    archive = dest / 'previous-heads'
    archive.mkdir()
    header = (f'## 最新：T089旧帧完整配对已审，本配对没有降低；原队列继续\n\n'
        f'权威 {HERE.name}/{dest.name}/status.json 与 {report.name}。基线/新门控各44回复、43动作、model_stop/official0，完整44 body/历史/捕获与交付PNG/回复/原生动作/后图相同，源审透明复用非新增审查者；两臂整轨Mirage=True/True，15文字误读既有，4/35未决、真实首次未证。无infra/cleanup/NO复拍。本次完整配对负结果已报告后不重复，不能当总体率或显著性。父失败部分和成本保留，不清零、不作独立样本。\n\n'
        '原29继续原版；批准10离线85包已stage、0调用/未提交，只有两根全部29逻辑终局/30attempt seals与链及全部实际模型/GUI/launcher退出，才collect_aggregate_completion.py并一次offline_followup_control.py submit。原10完整body/+292tokens/2048/seed42greedy/0GUI/Flash/scorer/retry不改，不重问；正式新提示GUI未批准。禁止旧stage/service/gui/容量/终局或原单根29submit重跑。最终fresh全量raw与Controller及剩余语义审查仍待。目标ACTIVE、整体降低未证。以下为旧时快照。\n\n')
    for index, path in enumerate([HERE.parent / 'HANDOFF.md', HERE.parent / 'README.md', HERE / 'CONTINUATION.md', HERE / 'README.md']):
        data = path.read_bytes()
        (archive / ('%02d-%s' % (index, path.name))).write_bytes(data)
        path.write_bytes(header.encode('utf8') + data)
    pointer = {'publication': str(dest), 'report': str(report), 'status_sha256': sha(dest / 'status.json'),
         'seal_sha256': sha(dest / 'seal.json'), 'goal': 'active', 'effectiveness_proven': False, 'time': time.time()}
    for name in ['experiment-current.json', 'continuation-current.json', 'semantic-review-current.json']:
        p = HERE / name
        if p.exists():
            (archive / name).write_bytes(p.read_bytes())
        p.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'report': str(report),
         'within_T089_stale_pair_improvement': False, 'overall_effectiveness_proven': False,
         'normal_logical_terminals': state['normal_logical_terminals_at_terminal_snapshot'], 'goal': 'active'}))


if __name__ == '__main__':
    main()
