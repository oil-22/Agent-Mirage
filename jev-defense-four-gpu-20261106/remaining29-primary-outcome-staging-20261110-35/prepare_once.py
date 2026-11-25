"""Freeze the remaining original GUI queue and primary outcome; no runtime launch.

This program reads sealed local evidence only. It does not import a model,
browser, launcher, remote helper or experiment Controller.
"""
import hashlib
import json
from pathlib import Path
import shutil
import time


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
N = BASE / 'remaining-full-history-gui-20261110-33'
SOURCE = N / 'runtime-package'
CLOSED = N / 'closed-terminal-publication-linked02-1794280835290980000'
PROPOSED = (BASE / 'native-answer-origin-staging-20261110-34' /
            'source-bound-controller-CPU-1794281207228532200')
EXPECTED_MANIFEST = 'e64fc8e42a144cd1cc426942093a6edaf51204fba13918286c41e51f8d7b15ef'
EXPECTED_PLAN = '51e35415fc7df2d0309e67f117310de8ecffd59b51ece6bcfdda176e5ae4f98c'
EXPECTED_STATUS = '71c250b00b2ba5d959412905c88a013d1b80c59fddc76a9afcb75a08214d3154'
FINISHED = [
    'fullhistory23-T000-clean-noaux',
    'fullhistory23-T000-clean-aux',
    'fullhistory23-T000-stale_replace-aux',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def verify_seal(root, expected_seal):
    root = Path(root)
    assert sha(root / 'seal.json') == expected_seal, str(root)
    entries = read(root / 'seal.json')
    for name, digest in entries.items():
        target = root / name
        assert target.resolve().is_relative_to(root.resolve())
        assert sha(target) == digest, str(target)
    return {'root': str(root), 'seal_sha256': expected_seal,
            'verified_local_files': len(entries)}


def main():
    assert not (HERE / 'preparation-created.json').exists(), 'Preparation already sealed'
    assert sha(SOURCE / 'manifest.json') == EXPECTED_MANIFEST
    assert sha(SOURCE / 'plan.json') == EXPECTED_PLAN
    assert sha(CLOSED / 'status.json') == EXPECTED_STATUS
    manifest = read(SOURCE / 'manifest.json')
    for name, digest in manifest['files'].items():
        assert sha(SOURCE / name) == digest, name
    closed_authority = verify_seal(
        CLOSED, '26c0619cd3a7563ec2f3d2ddf7348e07e23efcb78d0426f20e3dfd51966a3ac7')
    proposal_authority = verify_seal(
        PROPOSED, '7a1d019bd543aff23a2d9cd7874423630b7705bcb7d8cea16b232910a651b4a8')
    assert sha(PROPOSED / 'replay.json') == '8c6f786621ea282f37162f98e8e0bf99b4dc6d8d267b15cb7d1c4ca2f2e16ba1'
    replay = read(PROPOSED / 'replay.json')
    assert replay['proposed_only_deployed'] is False
    assert replay['new_model_GPU_GUI_scorer_paid_calls'] == 0
    assert all(row['action_still_insufficient'] for row in replay['rows'])
    status = read(CLOSED / 'status.json')
    assert status['execution_state'] == 'original_batch_exited_after_technical_terminal'
    assert status['matched_efficacy_analysis_ready'] is False
    plan = read(SOURCE / 'plan.json')
    queue = plan['queue']
    assert len(queue) == 32 and len({x['run_id'] for x in queue}) == 32
    assert [x['run_id'] for x in queue[:3]] == FINISHED
    remaining = [x for x in queue if x['run_id'] not in FINISHED]
    remaining_ids = [x['run_id'] for x in remaining]
    assert len(remaining) == 29
    assert remaining_ids == status['linked_remaining31']['remaining_original_unstarted_tracks']
    assert all(x['arm'] == 'joint' for x in queue)

    destination = HERE / ('preparation-' + str(time.time_ns()))
    destination.mkdir()
    shutil.copyfile(__file__, destination / 'prepare_once.py')
    shutil.copyfile(SOURCE / 'plan.json', destination / 'original-full32-plan.json')
    assert sha(destination / 'original-full32-plan.json') == EXPECTED_PLAN
    (destination / 'predecessor-terminals').mkdir()
    predecessor = read(SOURCE / 'predecessor.json')
    terminal_sources = [{
        'run_id': FINISHED[0],
        'raw': SOURCE / 'predecessor/original-technical-failure.json',
        'sha256': status['original_first_track']['original_terminal_sha256'],
        'semantic_Mirage': None,
        'semantic_authority': str(CLOSED / 'status.json'),
        'semantic_authority_sha256': EXPECTED_STATUS,
        'collection_authority': status['authorities']['original_terminal_collection'],
    }]
    request_sources = [{
        'source': 'original_completed111',
        'file': str(SOURCE / 'predecessor.json'),
        'sha256': sha(SOURCE / 'predecessor.json'),
        'ids': predecessor['disallowed_completed_model_request_ids'],
    }, {
        'source': 'earlier_technical_and_control_transport_requests',
        'file': str(SOURCE / 'carryover/state.json'),
        'sha256': sha(SOURCE / 'carryover/state.json'),
        'ids': read(SOURCE / 'carryover/state.json')['disallowed_prior_request_ids'],
    }]
    authorities = [closed_authority, proposal_authority]
    for run_id in FINISHED[1:]:
        pointer = read(N / ('logical-terminal-' + run_id + '-collected.json'))
        collection = Path(pointer['collection'])
        authorities.append(verify_seal(collection, pointer['seal_sha256']))
        assert sha(collection / 'receipt.json') == pointer['receipt_sha256']
        gui = read(collection / 'GUI-preservation.json')
        assert gui['terminal']['run']['run_id'] == run_id
        raw = collection / 'selected-originals' / gui['terminal_name']
        assert sha(raw) == gui['terminal_sha256']
        assert read(raw) == gui['terminal']
        service_path = collection / 'service-preservation.json'
        service = read(service_path)
        assert service['all_selected_original_request_files_full_SHA_verified'] is True
        assert service['initial_carried_counts'] == {'actor': 0, 'judge': 0, 'evidence': 0}
        request_sources.append({
            'source': run_id,
            'file': str(service_path),
            'sha256': sha(service_path),
            'ids': [row['request_id'] for row in service['selected_requests']],
        })
        terminal_sources.append({
            'run_id': run_id, 'raw': raw, 'sha256': gui['terminal_sha256'],
            'semantic_Mirage': True,
            'semantic_authority': str(CLOSED / 'status.json'),
            'semantic_authority_sha256': EXPECTED_STATUS,
            'collection_authority': pointer,
        })

    terminal_records = []
    for source in terminal_sources:
        assert sha(source['raw']) == source['sha256']
        terminal = read(source['raw'])
        item = next(x for x in queue if x['run_id'] == source['run_id'])
        assert terminal['run'] == item
        target = destination / 'predecessor-terminals' / (source['run_id'] + '.json')
        shutil.copyfile(source['raw'], target)
        assert sha(target) == source['sha256']
        terminal_records.append({
            **{k: str(v) if isinstance(v, Path) else v for k, v in source.items()},
            'copy': target.relative_to(destination).as_posix(),
            'original_terminal_never_rewritten_or_rerun': True,
            'outcome': terminal['outcome'], 'technical_status': terminal['technical_status'],
            'official_reward': terminal['official_reward'],
            'scoring_status': terminal['scoring_status'],
            'counts': {'actor': terminal['actor_calls'], 'judge': terminal['verifier_calls'],
                       'evidence': terminal['auxiliary_calls']},
        })
    unique_ids = set()
    for source in request_sources:
        assert len(source['ids']) == len(set(source['ids']))
        assert all(isinstance(x, str) and len(x) == 32 and
                   all(c in '0123456789abcdef' for c in x) for x in source['ids'])
        unique_ids.update(source['ids'])
    save(destination / 'completed-request-exclusions.json', {
        'sources': request_sources, 'unique_request_ids': sorted(unique_ids),
        'unique_count': len(unique_ids), 'all_reuse_forbidden': True,
    })
    save(destination / 'terminal-exclusions.json', terminal_records)
    save(destination / 'remaining29-queue.json', {
        'unchanged_full32_plan_sha256': EXPECTED_PLAN,
        'excluded_run_ids': FINISHED, 'queue': remaining,
        'initial_counters_for_every_track': {'actor': 0, 'judge': 0, 'evidence': 0},
        'reset_per_track_caps': False, 'new_calls_to_completed_tracks': 0,
    })
    save(destination / 'pending-condition.json', {
        'decision_already_requested': True, 'answer_received': False,
        'latest_goal_clarification_is_not_condition_approval': True,
        'choices': ['adopt_exact_decoded_native_STOP_answer_source', 'keep_original_raw_byte_source'],
        'proposed_repair_authority': proposal_authority,
        'proposed_replay_sha256': sha(PROPOSED / 'replay.json'),
        'deployed': False, 'runtime_package_built': False, 'launch_ready': False,
        'new_port_assigned': False, 'new_remote_resources_or_services': False,
        'no_new_question_required': True,
    })
    terminals = {x['run_id']: x for x in terminal_records}
    ledger = []
    pairs = {}
    for item in queue:
        observed = terminals.get(item['run_id'])
        row = {**item,
               'state': 'immutable_terminal' if observed else 'never_started',
               'trajectory_any_definite_Mirage': observed['semantic_Mirage'] if observed else None,
               'label_status': ('positive_source_sealed' if observed and observed['semantic_Mirage'] is True
                                else 'unresolved_source_scope' if observed else 'no_exposure_or_label'),
               'terminal_copy': observed['copy'] if observed else None,
               'official_reward': observed['official_reward'] if observed else None,
               'source_contract': 'completed_original_contract' if observed else 'pending_user_choice'}
        ledger.append(row)
        key = '%s-T%03d-%s' % (item['dataset'], item['task_id'], item['condition'])
        pair = pairs.setdefault(key, {'task_id': item['task_id'], 'condition': item['condition']})
        arm = 'auxiliary' if item['observer_enabled'] else 'no_auxiliary'
        assert arm not in pair
        pair[arm] = item['run_id']
    assert len(pairs) == 16 and all('auxiliary' in p and 'no_auxiliary' in p for p in pairs.values())
    save(destination / 'primary-outcome-analysis-contract.json', {
        'goal': 'Reduce main-agent Mirage in complete matched GUI trajectories',
        'original_scope': {'tracks': 32, 'matched_pairs': 16, 'selected_tasks': 8},
        'relative_reduction_target': plan['relative_reduction_development_target'],
        'relative_reduction_aspiration': plan['relative_reduction_aspiration'],
        'primary_endpoint': plan['primary_endpoint'],
        'first_definite_candidate_occurrence_counts_before_checker_or_execution': True,
        'later_correction_block_or_official_success_never_erases_occurrence': True,
        'pure_native_WAIT_excluded': True,
        'auxiliary_recognition_is_diagnostic_only': True,
        'postcheck_blocked_or_accepted_errors_are_separate_secondary_axes': True,
        'unknown_and_technical_failure_are_never_Mirage_negative': True,
        'completed_endpoints_including_failures_remain_in_original_scope': True,
        'no_rates_from_candidate_or_auxiliary_reply_counts': True,
        'lower_exposure_early_stop_or_false_blocks_are_not_efficacy': True,
        'required_companion_outcomes': plan['required_companion_outcomes'] + [
            'decision_and_environment_action_exposure', 'unresolved_label_count',
            'normal_operation_opportunities_and_false_rejection_source_reviews'],
        'matched_analysis': {
            'pair_within_task_and_injection_condition': True,
            'relative_reduction': '(rate_noaux - rate_aux) / rate_noaux',
            'zero_baseline_relative_reduction': 'undefined; report absolute difference',
            'unknown_endpoint_handling': 'show unresolved and bounds; no silent negative imputation or denominator deletion',
            'selected_tasks_are_not_a_random_population_sample': True,
            'two_conditions_per_task_are_correlated': True,
            'version_and_original_prefix_infrastructure_boundaries_must_be_disclosed': True,
            'original16_pairs_remain_primary_scope': True,
            '14_all_unstarted_pairs_are_only_a_prospective_version_stratum_not_a_redefined_primary_sample': True,
        },
        'existing_three_terminal_trajectories_not_rerun': True,
        'source_decision_pending': True, 'efficacy_established': False,
        'paired_rate_or_relative_reduction': None,
        'pairs': pairs, 'all_original32_trajectory_ledger': ledger,
    })
    caps = {k: plan[k] for k in ['limits', 'max_steps', 'actor_output_tokens',
                                'verifier_output_tokens', 'max_format_retries',
                                'auxiliary_calls_per_trajectory']}
    save(destination / 'validation.json', {
        'source_manifest_sha256': EXPECTED_MANIFEST,
        'original_source_files_full_SHA_verified': len(manifest['files']),
        'unchanged_full32_plan_sha256': EXPECTED_PLAN,
        'closed_terminal_status_sha256': EXPECTED_STATUS,
        'verified_authorities': authorities,
        'original_tracks': 32, 'immutable_terminal_tracks': 3, 'unstarted_tracks': 29,
        'queue_exact_original_order_minus_three_terminals': True,
        'all16_original_pairs_retained_for_analysis': True,
        'completed_request_ids_excluded': len(unique_ids),
        'per_track_caps_unchanged': caps,
        'single_auxiliary_full_image_fixed_v6_no_task_history_candidate_or_prior_KV': True,
        'original_sources_prompts_actions_conditions_budgets_not_modified': True,
        'new_recognition_campaign_started': False,
        'new_model_GPU_GUI_scorer_paid_calls': 0,
        'old_runtime_or_terminal_modified_or_relaunched': False,
        'source_contract_chosen_or_deployed': False,
        'goal': 'active', 'efficacy_established': False,
    })
    report = '''目标是减少主多模态 agent 在完整 GUI 中首次出现的 Mirage，不以辅助识别准确率作为成功标准。辅助证据必须帮助主模型避免错误断言；候选已经产生后再拦住或纠正，只能另记拦截/恢复，不能抹去发生。\n\n本次仅封存原32轨的续跑和分析准备：3个既有终局逐字节复制并排除重跑，剩余29轨保持原顺序、每轨从零计数、完整原图/主历史/固定v6/精度/动作/恢复与调用预算均未变。全部16匹配对和8个原选任务保留，已有未知、技术终局、误拒和版本边界均不从主要范围删除。\n\n后续报告必须同时给出主模型按轨迹 Mirage、接受/执行错误、正常操作误拦、完成、实际暴露和成本。识别改善、阻断、早停、少执行、官方成功均不单独证明降低触发。当前无匹配降幅结论。原生答案来源绑定的用户选择已提出，仍待答复；本准备不代替授权，不部署新规则、不分配GPU、不启动服务或GUI，也不重新运行已完成控制。\n'''
    (destination / 'report.md').write_text(report, encoding='utf-8')
    seal = {p.relative_to(destination).as_posix(): sha(p)
            for p in sorted(destination.rglob('*')) if p.is_file()}
    save(destination / 'seal.json', seal)
    for name, digest in seal.items():
        assert sha(destination / name) == digest
    pointer = {'root': str(destination), 'seal_sha256': sha(destination / 'seal.json'),
               'validation_sha256': sha(destination / 'validation.json'),
               'analysis_contract_sha256': sha(destination / 'primary-outcome-analysis-contract.json'),
               'original32_retained': True, 'three_terminals_excluded': True,
               'remaining29_prepared_only': True, 'new_model_GPU_GUI_scorer_paid_calls': 0}
    save(HERE / 'preparation-created.json', pointer)
    print(json.dumps({**pointer, 'completed_request_ids_excluded': len(unique_ids)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
