"""Publish already sealed completed/ongoing source evidence; no model commands."""
import argparse
import contextlib
import io
import json
import time
from pathlib import Path
from control import HERE, activity, save, sha
from offline_followup_control import PREP


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    assert root.parent == HERE
    assert all(sha(root / n) == h for n, h in load(root / 'seal.json').items())


def main():
    parser = argparse.ArgumentParser()
    for name in ['registry', 'completed-join', 'ongoing-review', 'ongoing-binding', 'native', 'cpu', 'notes']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    roots = {k: getattr(args, k).resolve() for k in ['registry', 'completed_join', 'ongoing_review', 'ongoing_binding', 'native', 'cpu']}
    for root in roots.values():
        verify(root)
    registry = load(roots['registry'] / 'registry.json')
    completed = load(roots['completed_join'] / 'review-joined.json')
    ongoing = load(roots['ongoing_review'] / 'review.json')
    bound = load(roots['ongoing_binding'] / 'binding.json')
    native = load(roots['native'] / 'summary.json')
    cpu = load(roots['cpu'] / 'cumulative-report.json')
    assert bound['source_review'] == str(roots['ongoing_review'])
    assert bound['candidate_coverage'] == ongoing['candidate_coverage']
    assert ongoing['partial_prefix_only'] and not ongoing['completed_trajectory_review']
    assert completed['candidate_coverage'] == next(v['candidate_total'] for v in registry['runs'] if v['run_id'] == completed['run_id'])
    notes = args.notes.resolve()
    assert notes.is_relative_to(HERE.resolve())
    assert not (PREP / 'submission.json').exists()
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        activity()
    snapshots = [json.loads(v) for v in stream.getvalue().splitlines()]
    for snapshot in snapshots:
        for key in ['main_actual', 'Flash_actual', 'launcher_actual', 'GUI_actual']:
            if key in snapshot['data']:
                assert snapshot['data'][key]['same_live']
    dest = HERE / ('source-progress-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'notes-original.md').write_bytes(notes.read_bytes())
    done = registry['completed_trajectories']
    status = {'time': time.time(), 'goal': 'active', 'previous_goal_turn_classification': 'progress',
        'completed_trajectories_with_source_coverage': done, 'expected_logical_GUI_configurations': 29,
        'completed_replies_accounted_for': registry['completed_native_replies'],
        'source_labels_indexed': registry['source_labels_indexed'],
        'native_format_failures_without_semantic_labels': registry['native_format_failures_without_semantic_labels'],
        'completed_replies_waiting_for_source_review': registry['completed_replies_waiting_for_source_review'],
        'evidence': {k: {'root': str(root), 'seal_sha256': sha(root / 'seal.json')} for k, root in roots.items()},
        'new_completed_source_run': completed['run_id'], 'new_completed_source_coverage': completed['candidate_coverage'],
        'new_completed_trajectory_Mirage': completed['trajectory_semantic_Mirage'],
        'new_completed_definite_positive_candidates': completed['definite_positive_candidates'],
        'new_completed_unresolved_candidates': completed['unresolved_candidates'],
        'ongoing_run': bound['run_id'], 'ongoing_review_coverage': ongoing['candidate_coverage'],
        'ongoing_definite_positive_candidates': ongoing['definite_positive_candidates'],
        'ongoing_unresolved_candidates': ongoing['unresolved_candidates'],
        'native_raw_main_cumulative': native['cumulative_verified_main_replies'],
        'native_raw_Flash_cumulative': native['cumulative_verified_Flash_replies'],
        'Flash_CPU_cumulative': len(cpu['result']['requests']),
        'older_raw_keeps_original_audit_times': True, 'current_group_final_fresh_postexit_audits_required': True,
        'actual_process_snapshots': snapshots, 'approved_offline10_local_submission_absent': True,
        'all29_terminal_seals_chains_and_actual_model_GUI_launcher_exits_required': True,
        'formal_changed_GUI_authorized': False, 'effectiveness_proven': False, 'new_model_GUI_calls_by_publication': 0}
    save(dest / 'status.json', status)
    report = dest / 'GUI终局与进行中源审进展-20261115.md'
    report.write_text(f'# 已核验{done}/29终局，整体降低尚未证明\n\n' + notes.read_text('utf8')
        + f'\n\n覆盖索引共{registry["completed_native_replies"]}条完整回复，其中{registry["source_labels_indexed"]}条已有源标签，'
        + f'{registry["native_format_failures_without_semantic_labels"]}条原生格式失败。数字表示覆盖，不是独立样本或Mirage率。'
        + '\n\n原队列保持原版。批准10离线仍未在本地提交；ALL29终局/30attempt seals与链及实际模型、GUI、launcher退出后，'
        + '先collect_aggregate_completion.py，再offline_followup_control.py submit一次。+292原生system输入token/例、10×2048输出、完整原图全史、原种子精度及0GUI/Flash/scorer/自动重试不变。正式改版GUI尚未授权。目标ACTIVE。\n', encoding='utf8')
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    previous = dest / 'previous-heads'
    previous.mkdir()
    header = (f'## 最新：已核验{done}/29终局；{bound["run_id"]}前{ongoing["candidate_coverage"]}源审已绑定\n\n'
        + f'权威 {HERE.name}/{dest.name}/status.json 与 {report.name}。新终局{completed["run_id"]}共{completed["candidate_coverage"]}条，'
        + f'确定阳性{completed["definite_positive_candidates"]}、未决{completed["unresolved_candidates"]}、整轨Mirage={completed["trajectory_semantic_Mirage"]}；未知不是阴性、official不作真值。'
        + f'覆盖{registry["completed_native_replies"]}={registry["source_labels_indexed"]}源标签+{registry["native_format_failures_without_semantic_labels"]}格式失败，非率。运行位置以status实际时点为准。\n\n'
        + f'后续native从{roots["native"].name}、CPU从{roots["cpu"].name}/cumulative-report.json、source从{roots["ongoing_review"].name}继续；旧raw保留原时，当前组退出fresh全量仍待。'
        + '批准10离线未本地提交，ALL29/seals/链/实际全部退出后严格聚合准入一次，不重问、不自动发布正式新提示GUI。旧终局、容量、父fresh审计不重跑。目标ACTIVE，降低未证。以下为历史。\n\n')
    for i, path in enumerate([HERE.parent / 'HANDOFF.md', HERE.parent / 'README.md', HERE / 'CONTINUATION.md', HERE / 'README.md']):
        data = path.read_bytes()
        (previous / ('%02d-%s' % (i, path.name))).write_bytes(data)
        path.write_bytes(header.encode('utf8') + data)
    pointer = {'publication': str(dest), 'report': str(report), 'seal_sha256': sha(dest / 'seal.json'), 'goal': 'active', 'effectiveness_proven': False}
    for name in ['continuation-current.json', 'experiment-current.json', 'semantic-review-current.json', 'active-source-prefix-current.json']:
        path = HERE / name
        if path.exists():
            (previous / name).write_bytes(path.read_bytes())
        path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'publication': str(dest), 'completed': done, 'ongoing_source_coverage': ongoing['candidate_coverage'], 'report': str(report), 'goal': 'active'}))


if __name__ == '__main__':
    main()
