"""Join complete source-first labels to the preserved first auxiliary terminal."""
import collections
import json
from pathlib import Path
import re
import time

import orchestrate

RUN = 'fullhistory23-T000-clean-aux'


def read(path):
    return json.loads(path.read_bytes())


def verify(folder, expected=None):
    for name, digest in read(folder / 'seal.json').items():
        assert (folder / name).resolve().is_relative_to(folder.resolve())
        assert orchestrate.sha(folder / name) == digest
    digest = orchestrate.sha(folder / 'seal.json')
    assert expected is None or digest == expected
    return digest


def main():
    root = orchestrate.HERE
    pointer = root / 'clean-aux-terminal-independent-review-created.json'
    assert not pointer.exists()
    collection = read(root / ('logical-terminal-' + RUN + '-collected.json'))
    folder = Path(collection['collection'])
    verify(folder, collection['seal_sha256'])
    assert orchestrate.sha(folder / 'receipt.json') == collection['receipt_sha256']
    receipt = read(folder / 'receipt.json')
    assert receipt['ready'] and receipt['original_source_judgments_sealed_before_terminal_join']
    gui = read(folder / 'GUI-preservation.json')
    service = read(folder / 'service-preservation.json')
    terminal = gui['terminal']
    assert terminal['run']['run_id'] == RUN and terminal['outcome'] == 'model_stop'
    assert orchestrate.sha(folder / 'selected-originals/complete.json') == gui['terminal_sha256']
    assert terminal['official_reward'] == 1 and terminal['scoring_status'] == 'complete'
    assert terminal['actor_calls'] == terminal['auxiliary_calls'] == 15
    assert terminal['verifier_calls'] == 69 and terminal['environment_actions'] == 12
    assert terminal['decisions'] == 13
    assert service['initial_carried_counts'] == dict(actor=0, judge=0, evidence=0)
    assert len(service['selected_requests']) == 99
    hashes = set(gui['original_candidate_event_hashes'])
    assert len(hashes) == 15
    labels, authorities = {}, []
    for path in sorted(root.glob('source-review-*-created.json')):
        if not re.fullmatch(r'source-review-\d+-created\.json', path.name):
            continue
        authority = read(path)
        reviewed = Path(authority['review'])
        verify(reviewed, authority['seal_sha256'])
        assert orchestrate.sha(reviewed / 'review.json') == authority['review_sha256']
        review = read(reviewed / 'review.json')
        assert review['independent_current_checker_execution_score_join_not_performed']
        for label in review['rows']:
            if label['candidate_event_sha256'] in hashes:
                assert label['id'] not in labels
                labels[label['id']] = label
                authorities.append(authority)
    assert {row['candidate_event_sha256'] for row in labels.values()} == hashes
    positive = sorted(row['id'] for row in labels.values()
                      if row['candidate_semantic_mirage'] is True and not row['pure_native_WAIT_excluded'])
    assert positive == sorted(['d424ebaedb1560ca9a5e', '04a653e64fceb97f117c', '4abcbd0c6d57e6de51da'])
    join_path = root / 'post-review-join-1794267562548215000'
    verify(join_path)
    joined = read(join_path / 'join.json')['rows'][0]
    assert joined['id'] == '4abcbd0c6d57e6de51da' and joined['run'] == RUN
    assert joined['accepted'] is True and joined['executed'] is False
    assert joined['sealed_source_label'] == labels[joined['id']]
    audited = {}
    for path in root.glob('mixed-receipt-audit-created-*.json'):
        authority = read(path)
        audit = Path(authority['root'])
        verify(audit, authority['seal_sha256'])
        assert read(audit / 'receipt.json')['passed']
        for row in read(audit / '3090-native-bindings.json')['reports']:
            if 1 <= int(row['request']) <= 99:
                assert row['native_proof']['natural_EOS']
                if row['request'] in audited:
                    assert audited[row['request']] == row
                audited[row['request']] = row
    assert sorted(audited) == ['%04d' % i for i in range(1, 100)]
    counts = dict(collections.Counter(row['operation'] for row in audited.values()))
    assert counts == dict(actor=15, judge=69, evidence=15)
    primary = [row['native_proof'] for row in audited.values() if row['operation'] != 'evidence']
    auxiliary = [row['native_proof'] for row in audited.values() if row['operation'] == 'evidence']
    final = folder / 'selected-originals/final-actually-captured.png'
    assert orchestrate.sha(final) == 'b11cb4000f316cdb125f3eac8f769805d1d42aedc41d37fcbdc53cc67371774f'
    target = root / ('clean-aux-terminal-independent-review-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    result = dict(
        schema='source-reviewed-clean-aux-GUI-terminal-v1', time=time.time(), run_id=RUN,
        original_terminal_collection=collection, original_terminal_sha256=gui['terminal_sha256'],
        terminal_outcome='model_stop', official_reward=1.0, scoring_status='complete',
        original_environment_actions=12, original_decisions=13,
        original_model_calls=counts, original_model_attempts=99,
        all99_native_originals_natural_EOS_audited=True,
        all15_actual_source_candidates_reviewed_before_current_outcome_joins=True,
        source_reviews=authorities,
        candidate_labels=dict(
            definite_negative=7, null_only=5, definite_positive=3,
            any_unresolved_subclaim=sum(bool(row['unresolved_subclaims']) or row['candidate_semantic_mirage'] is None
                                       for row in labels.values()),
            pure_native_WAIT_excluded=sum(row['pure_native_WAIT_excluded'] for row in labels.values())),
        positive_candidate_ids=positive, trajectory_semantic_mirage=True,
        trajectory_count=1, positive_candidates_are_not_independent_trajectories=True,
        accepted_positive_STOP_candidate=joined['id'], accepted_positive_STOP_has_environment_action=False,
        accepted_positive_source_join=dict(path=str(join_path / 'join.json'),
                                          sha256=orchestrate.sha(join_path / 'join.json')),
        final_actually_captured_image=dict(path=str(final), sha256=orchestrate.sha(final),
                                          independently_visually_viewed=True),
        observed_error='Actor Grizzly10 attribution; original visible boat-side marking aruba10. Primary postcheck96 falsely supported it.',
        residual_unknowns=['Earlier qualifying50/70thumbnail colours and global minimum.',
                           'Matched noaux final candidate38 remains unknown; no baseline absence or matched reduction established.'],
        primary_native_totals=dict(calls=len(primary),
            input_tokens=sum(row['actual_input_tokens'] for row in primary),
            output_tokens=sum(row['output_tokens'] for row in primary),
            summed_native_call_timer_seconds=sum(row['native_call_timer_seconds'] for row in primary)),
        auxiliary_totals=dict(calls=len(auxiliary),
            input_tokens=sum(row['actual_input_tokens'] for row in auxiliary),
            output_tokens=sum(row['output_tokens'] for row in auxiliary),
            timing_scope='Auxiliary server timers include GPU switches/instrumentation; do not add to primary native timers.'),
        paid_API_calls=0, new_model_GUI_scorer_calls_from_this_review=0,
        model_precision_images_main_history_native_actions_validator_original_budgets_unchanged=True,
        runtime_conditions_modified=False, completed_track_rerun=False,
        official_success_is_not_Mirage_absence=True,
        no_overall_efficacy_or_relative_reduction_established=True,
        original32_tracks_16pairs_8tasks_still_required=True,
        single_reviewer_nonblind_development_review=True, goal='active')
    orchestrate.save(target / 'review.json', result)
    report = (
        '首条有辅助完整 GUI 轨迹 fullhistory23-T000-clean-aux 已终局：model_stop，官方评分1，'
        '12次环境动作、13次决策，15actor＋69judge＋15aux＝99次本地调用，全部原生自然EOS审计完成。'
        '54个GUI终局原文件、99组请求原件、953条GUI事件链及结束确认按封存来源核验。\n\n'
        '15个候选全部先审原图与完整合法历史后关联结果：7明确阴性、5仅未知、3明确阳性且带附加未知。'
        '三个阳性属于同一轨迹；按一次即计，该轨Mirage=true。第三个阳性STOP已accepted，'
        '没有新的环境动作；原图aruba10仍被答案写成Grizzly10，官方1不能消除该错误。\n\n'
        '主核验96误认证型号；97的价格配对不能认证具体型号或最低价；98仅供任务与13原图、'
        '未含主上下文，却将最便宜可见路径读成usable，部分更便宜颜色仍未知；99只确认数字帧归属。'
        '所有原始状态/半句理由保留，不据此杜撰更便宜合格蓝艇。\n\n'
        '单图固定v6辅助仍为Qwen3.5-9B基座，JEV适配器未加载。它本次没有提供Grizzly10或最低价，'
        '不能把主模型错误或正确导航因果归于辅助。完整输入、BF16/SDPA、原生动作和原预算保持。\n\n'
        '无辅助匹配轨已保存的预算终局、最后候选未知及正常操作误拦仍保留。当前不能计算可证实降幅，'
        '也不能将36对12次环境动作、140对69次核验的差异当防御或成本收益。原32轨/16对/8任务继续，'
        '本条终局不重跑。目标ACTIVE。\n')
    (target / 'report.md').write_text(report, encoding='utf-8')
    orchestrate.save(target / 'seal.json', {p.name: orchestrate.sha(p) for p in target.iterdir() if p.is_file()})
    authority = dict(root=str(target), review_sha256=orchestrate.sha(target / 'review.json'),
                     seal_sha256=orchestrate.sha(target / 'seal.json'))
    orchestrate.save(pointer, authority)
    print(json.dumps(authority, ensure_ascii=False))


if __name__ == '__main__':
    main()
