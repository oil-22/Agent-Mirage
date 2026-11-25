"""Publish preserved original terminal and the first actually audited aux chain."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from orchestrate import HERE, BASE, PACKAGE, OLD, save, sha


def read(p):
    return json.loads(Path(p).read_bytes())


def verify(root, expected=None):
    if expected is not None:
        assert sha(root / 'seal.json') == expected
    for name, digest in read(root / 'seal.json').items():
        assert (root / name).resolve().is_relative_to(root.resolve())
        assert sha(root / name) == digest, name


def main(evidence):
    pointer = HERE / 'first-enabled-chain-publication-created.json'
    assert not pointer.exists()
    assert evidence.parent == HERE
    verify(evidence)
    service, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    assert service['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    for record in [service['worker/process.json'], service['launcher-process.json'], gui['control/runner-process.json']]:
        assert not record['actual'].get('absent') and record['actual']['state'] not in ['Z', 'X']
        assert all(str(record['actual'][key]) == str(record['value'][key]) for key in ['pid', 'uid', 'command', 'start_ticks'])
    assert len(service['held_locks']) == 9
    original_authority = read(OLD / 'actual-budget-terminal-replay-created.json')
    original_root = Path(original_authority['root'])
    verify(original_root, original_authority['seal_sha256'])
    assert sha(original_root / 'receipt.json') == original_authority['receipt_sha256']
    original = read(original_root / 'receipt.json')
    audits = []
    for path in HERE.glob('mixed-receipt-audit-created-*.json'):
        authority = read(path);root = Path(authority['root'])
        verify(root, authority['seal_sha256'])
        assert sha(root / 'receipt.json') == authority['receipt_sha256']
        if read(root / 'receipt.json')['actual_enabled_mixed_branch_observed']:
            audits.append((root, authority))
    assert len(audits) == 1
    audit_root, audit_authority = audits[0]
    native, HTTP = read(audit_root / '3090-native-bindings.json'), read(audit_root / '4090-GUI-bindings.json')
    auxiliary = next(row for row in native['reports'] if row['operation'] == 'evidence')['native_proof']
    insertion = HTTP['actor_insertions'][0]
    assert auxiliary['single_complete_image_and_fixed_prompt_bound'] and auxiliary['actual_first_cache_length'] == 0
    assert auxiliary['all_observed_cache_objects_released'] and insertion['auxiliary_actual_HTTP_linked']
    assert insertion['all_original_messages_images_trailing_corrections_and_body_parameters_retained']
    assert insertion['preceding_auxiliary_request'] == '0002' and insertion['request'] == '0003'
    review_authority = read(HERE / 'source-review-01-created.json')
    review_root = Path(review_authority['review'])
    verify(review_root, review_authority['seal_sha256'])
    assert sha(review_root / 'review.json') == review_authority['review_sha256']
    review = read(review_root / 'review.json')
    assert len(review['rows']) == 1 and review['rows'][0]['candidate_semantic_mirage'] is False
    assert review['rows'][0]['native_action_error'] is False
    # This publication does not perform an execution/scorer join. The latest
    # committed chain may contain more events, but a source-negative candidate
    # must not automatically be called an accepted/executed action.
    state = service['worker/status.json']['value']
    root = HERE / ('first-enabled-chain-publication-' + str(time.time_ns()));root.mkdir()
    before = {name: (BASE / name).read_bytes() for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']}
    for name, raw in before.items():
        (root / ('before-' + name)).write_bytes(raw)
    status = dict(schema='original32-first-budget-terminal-and-real-enabled-chain-v1', time=time.time(),
        goal='active', monitor_should_remain_active=True, previous_goal_turn_classification='progress',
        current_goal_turn_classification='Progress: all actual first-track terminal originals preserved; real budget-terminal classifier replay passed; linked original31 zero-counter queue staged and launched; first enabled native/HTTP/GPU/KV/actor chain actually audited.',
        efficacy_established=False, relative_Mirage_reduction=None,
        original_scope=dict(tracks=32, matched_pairs=16, source_selected_tasks=8,
            original_full_plan_sha256=sha(PACKAGE / 'plan.json'), original_frozen32_manifest_sha256=sha(OLD / 'runtime-package/manifest.json')),
        original_first_track=dict(run_id='fullhistory23-T000-clean-noaux', original_terminal_preserved=True,
            original_terminal_sha256=original['original_terminal_sha256'],
            original_technical_status='verifier_failure', replayed_category='local_verifier_budget_terminal',
            official_reward=0.0, scoring_status='complete', actor_calls=38, verifier_calls=140, auxiliary_calls=0,
            environment_actions=36, decisions=37, distinct_source_candidates=38,
            definite_negative_source_candidates=37, unresolved_candidate_ordinals=[38], trajectory_semantic_mirage=None,
            normal_operation_false_rejection_candidate_count_lower_bound=1,
            prior_infrastructure_interruptions_remain=True, completed_terminal_never_reexecuted=True,
            current_root_native_audited_requests=111, current_root_audited_totals=original['current_root_audited_totals']),
        linked_remaining31=dict(manifest_sha256=sha(PACKAGE / 'manifest.json'),
            first_run='fullhistory23-T000-clean-aux', planned_unstarted_original_tracks=31,
            initial_counters_for_each=dict(actor=0, judge=0, evidence=0), state=state,
            actual_worker=service['worker/process.json']['actual'], actual_GUI=gui['control/runner-process.json']['actual'],
            actual_holder=service['actual_holder'], actual_held_locks=9,
            newly_audited_native_requests=['0001', '0002', '0003', '0004'],
            first_real_auxiliary_complete_image_fixed_prompt_empty_KV_release_GPU_cycle_HTTP_and_actor_insertion_bound=True,
            first_actor_source_review=dict(candidate_semantic_mirage=False, native_action_error=False,
                acceptance_execution_and_task_score_not_established_by_this_publication=True),
            original_model_and_Controller_sources_unchanged=True, terminal_classification_only_no_new_recovery_calls=True,
            pending_price_budget_recovery_not_deployed=True, CPU_bookkeeping_checks=47),
        auxiliary=dict(model='Qwen/Qwen3.5-9B', decision_adapter_loaded=False, model_count=1,
            fixed_prompt_sha256='2a6a2d210bac4cd552e477df15dab86aacd4ff479cd85a3e070f01dcc97e558c',
            single_complete_current_supplied_image_only=True, no_task_main_history_candidate_or_previous_auxiliary_context=True,
            semantic_correctness_established=False, first_raw_summary_incomplete_clause_and_footer_like_scope_unresolved=True),
        storage=dict(service_output='/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
            new_owned_namespace_on_separate_data_volume=True, last_available_bytes=service['service_storage_free_bytes'],
            no_originals_deleted_moved_compressed=True, whole_remaining31_capacity_not_proven=True),
        resource_scope='Only actually verified owned3090 physical4-7;0-3 untouched; four reserved GPU cost retained in both arms',
        inference_scope='Original BF16/SDPA, full images/main history/native prompts/actions/strict validators and50/70/140/60 with2recapture2regeneration1format retry remain',
        unresolved_work=['Full remaining31 GUI terminals and source-first semantics/execution/score joins',
            'Paired trajectory-level Mirage/normal operation/false rejection/completion/exposure/cost assessment',
            'Original candidate38 unresolved scope; source-negative prefix is not a negative trajectory',
            'Known false rejections, historical inference and auxiliary semantic limitations remain'],
        authorities=dict(actual_evidence=str(evidence), actual_evidence_seal_sha256=sha(evidence / 'seal.json'),
            original_terminal_replay=original_authority, original_terminal_collection=read(OLD / 'logical-terminal-fullhistory23-T000-clean-noaux-collected.json'),
            original38_source_ledger=read(OLD / 'first38-consolidated-source-ledger-created.json'),
            linked31_preparation=str(HERE / 'preparation.json'), CPU_admission=str(HERE / 'CPU-admission.json'),
            real_enabled_mixed_audit=audit_authority, first_actor_source_review=review_authority),
        old_queues_not_resumed=True, goal_completion_not_claimed=True)
    save(root / 'status.json', status)
    header = '''## 最新：2026-11-10 原首轨140预算终局已封存；原剩余31已启动，首次真实辅助整链审计通过

权威 `{relative}/status.json`。原first noaux在决策37/36执行动作处用满38actor/140judge/0aux，原得分0，原technical-failure文件SHA f1adf50d1f5f7d06ee8184b4b82833a7b915cf139d4bd77b904e9a50e9287857 保持。实际原因point_verifier_error:verifier_call_cap；原worker error=null/已退出。隔离分类实际回放证实是本地预算终局被旧记账误归技术失败，不增加调用/恢复/执行，不抹除此前OOM/中断。93GUI原文件与111实际请求全文件SHA、原/end/双链/完整计数已核。37源候选阴性、第38仍未知，整轨Mirage仍null；至少一次正常分页误拒绝保留。

新 `{dirname}` 仅接原32中从未执行的尾31，完整原plan/task/order/model/prompt/图像/主历史/strict Controller/原预算不变。47项合成CPU记账检查通过，首条clean-aux实际从0/0/0开始，原失败首轨绝不重跑；未部署pending-price恢复副本。3090新worker32383 UID1033/start1187155095、GUI322908 UID1015/start123599912的实际完整命令与4–7九锁/双链已核，0–3不动。

首次真实enabled链0002aux→0003actor已审计：单完整供应图+固定v6，无task/history/candidate/旧aux；实际首KV0/结束释放、原生IDs/全部forward tensors/UTF8/EOS、GPU切换与完整原actor2消息1图/单数据块插入、双机HTTP全绑定。0001..0004=1aux+1actor+2judge全部自然EOS已原生独立解码审计；首候选先审原图/合法输入，正常Keyword点击，源Mirage=false/native error=false，尚不由本发布认定接受/执行或完成。aux仍9B基座、decision_adapter_loaded=false；raw summary中段结束且footer-like范围未确立，不能将格式valid当语义通过。

新回执在3090 `/data/researcher/jev-defense-four-gpu-20261106/{dirname}` 的新自有目录，原件不删/移/压缩；约1.48TB初始余量不是31轨未来fit证明。原111累计1910714input/32673output/20026.959summed native秒，排除旧根/加载/先前失败，不是walltime/货币/能耗。全32/16对/8源选任务和30%/50%目标仍待实证；目标ACTIVE，不能因启动/局部正常操作暂停或称防御有效。

'''.format(relative=root.relative_to(BASE).as_posix(), dirname=HERE.name)
    report = BASE / '原32首条预算终局与剩余31真实辅助启动-20261110.md'
    assert not report.exists()
    report.write_text('# 原32首条预算终局与剩余31真实辅助启动\n\n' + header.split('\n\n', 1)[1] +
        '\n本次边界：修复的是终局记账与未执行队列的初始计数，未改变模型证据判定规则。原首轨得分0与未知语义标签保留，不能把未报告错误当作防御成功。新第一辅助链证明输入隔离与接线真实发生，尚无轨迹级相对降幅或正式效力结论。\n', encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == before[name]
        (BASE / name).write_bytes(header.encode('utf8') + before[name])
    assert (BASE / 'full-gui-current.json').read_bytes() == before['full-gui-current.json']
    (BASE / 'full-gui-current.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == header.encode('utf8') + before[name]
    assert read(BASE / 'full-gui-current.json') == status
    save(root / 'receipt.json', dict(time=time.time(), passed=True, report=str(report), report_sha256=sha(report),
        source_snapshot=str(evidence), original_heads_preserved=True, all_three_new_heads_readback_verified=True,
        new_model_GUI_scorer_calls=0, efficacy_or_goal_completion_established=False))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    record = dict(root=str(root), status_sha256=sha(root / 'status.json'), seal_sha256=sha(root / 'seal.json'), report=str(report))
    save(pointer, record)
    print(json.dumps(record))


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--evidence', type=Path, required=True)
    main(parser.parse_args().evidence.resolve())
