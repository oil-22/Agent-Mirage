"""Audit a repeated required human condition choice; never infer approval."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time


HERE = Path(__file__).resolve().parent
BASE = HERE.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def verify(pointer):
    root = Path(pointer['root'])
    assert sha(root / 'seal.json') == pointer['seal_sha256']
    for name, digest in read(root / 'seal.json').items():
        assert sha(root / name) == digest, name
    return root


def audit():
    assert not (HERE / 'blocked-audit-created.json').exists(), 'Already audited'
    observation = read(HERE / 'third-turn-decision-observation.json')
    assert observation['affected_consecutive_goal_turn_count'] == 3
    assert len({x['id'] for x in observation['turns']}) == 3
    assert [x['status'] for x in observation['turns']] == ['completed', 'completed', 'inProgress']
    assert observation['no_new_human_choice_in_active_context']
    assert '来源规则的表示形式发生变化' in observation['original_question']
    status = read(BASE / 'full-gui-current.json')
    assert status['execution_state'] == 'original_batch_exited_after_technical_terminal'
    assert status['remaining29_preparation']['source_rule_choice_received'] is False
    assert status['linked_remaining31']['remaining_original_unstarted_track_count'] == 29
    template = read(HERE / 'preparation-created.json')
    template_root = verify(template)
    package = template_root / 'runtime-template'
    manifest = read(package / 'manifest.json')
    admission = read(package / 'admission.json')
    assert manifest['template_only'] and not manifest['launch_ready']
    assert admission['admit_new_GUI_development'] is False
    assert not (package / 'human-source-condition-decision.json').exists()
    assert not (BASE / 'remaining29-full-history-gui-20261110-37').exists()
    checks = read(template_root / 'CPU-checks.stdout.txt')
    assert checks['passed'] and len(checks['groups']) == 19
    primary = read(BASE / 'remaining29-primary-outcome-staging-20261110-35/preparation-created.json')
    verify(primary)
    proposal = read(BASE / 'native-answer-origin-staging-20261110-34/preparation-created.json')
    proposal_root = verify(proposal)
    replay = read(proposal_root / 'replay.json')
    assert replay['earlier_21_source_boundary_unit_tests_observed_passed']
    assert replay['proposed_only_deployed'] is False
    root = HERE / ('blocked-audit-' + str(time.time_ns()))
    root.mkdir()
    shutil.copyfile(__file__, root / 'record_blocked_audit_once.py')
    shutil.copyfile(HERE / 'third-turn-decision-observation.json', root / 'third-turn-decision-observation.json')
    for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']:
        shutil.copyfile(BASE / name, root / ('before-' + name))
    incomplete = [
        {'requirement': 'Complete original32 paired GUI trajectories', 'state': 'incomplete',
         'evidence': 'Three original endpoints including failures retained;29 never started'},
        {'requirement': 'Observable main-agent trajectory Mirage reduction >=30%, aiming50%',
         'state': 'not_proven', 'evidence': 'matched_efficacy_analysis_ready=false; baseline scope still unknown; no relative estimate'},
        {'requirement': 'Avoid explaining reduction by false blocks, lower completion or exposure',
         'state': 'not_proven', 'evidence': 'Full remaining matched GUI outcomes absent; existing false rejections and technical terminal retained'},
        {'requirement': 'Fix source representation without unsupported evidence or altered action',
         'state': 'prepared_not_deployed', 'evidence': 'Sealed21 source checks, native evidence negatives and actual181/182 CPU replay; verdict/action remain insufficient'},
        {'requirement': 'Single complete image/fixed prompt/stateless auxiliary and full lawful main history',
         'state': 'original_conditions_preserved_in_template_not_new_runtime_proof',
         'evidence': 'Original forward/Controller/prompt/history/native-action source bytes unchanged'},
        {'requirement': 'Preserve all outcomes and original scope/budgets; no completed terminal retries',
         'state': 'preparation_verified', 'evidence': 'All32 plan/16 pairs/8 tasks retained; three raw terminal exclusions;362 IDs;19 continuation/isolation checks'},
        {'requirement': 'Fresh ownership/locks/no foreign compute before actual allocation',
         'state': 'must_recheck_at_future_launch', 'evidence': 'Prior read-only ownership evidence is not a future resource lease or GPU fit guarantee'},
    ]
    result = {
        'schema': 'three-consecutive-turn-human-source-choice-blocked-audit-v1',
        'time': time.time(), 'condition': 'Unanswered explicit source-condition choice for remaining29 GUI trajectories',
        'same_condition_in_three_consecutive_goal_turns_verified': True,
        'turn_ids': [x['id'] for x in observation['turns']],
        'previous_goal_turn_classification': 'progress',
        'current_goal_turn_classification': 'no_experimental_progress_due_to_required_human_choice; audit_only',
        'live_experiment_wait_claimed': False,
        'source_choice_question_already_sent_no_repeat': True,
        'independent_preparation_required_for_review_complete': True,
        'remaining29_template': template, 'full32_primary_outcome_preparation': primary,
        'native_answer_source_proposal': proposal,
        'completion_audit': incomplete, 'goal_achieved': False,
        'safe_next_experimental_action_without_answer_exists': False,
        'why_no_launch': 'Selecting either formal source contract while the required choice is pending would decide the condition for the human; no reply or elapsed time is approval.',
        'no_rehash_retest_or_recognition_campaign_needed_to_repeat_ready_preparation': True,
        'technical_model_and_semantic_results_unchanged': True,
        'new_model_GPU_GUI_scorer_paid_calls': 0,
        'blocked_transition_eligible': True, 'blocked_transition_performed_here': False,
    }
    save(root / 'audit.json', result)
    save(root / 'seal.json', {p.name: sha(p) for p in sorted(root.iterdir()) if p.is_file()})
    pointer = {'root': str(root), 'audit_sha256': sha(root / 'audit.json'),
               'seal_sha256': sha(root / 'seal.json'), 'blocked_transition_eligible': True}
    save(HERE / 'blocked-audit-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=True))


def publish():
    # Run only after update_goal has actually returned status=blocked.
    assert not (HERE / 'blocked-publication-created.json').exists(), 'Already published'
    transition = read(HERE / 'goal-blocked-transition.json')
    assert transition['returned_goal_status'] == 'blocked'
    audit_pointer = read(HERE / 'blocked-audit-created.json')
    audit_root = verify(audit_pointer)
    proof = read(audit_root / 'audit.json')
    assert proof['blocked_transition_eligible'] and not proof['goal_achieved']
    root = HERE / ('blocked-publication-' + str(time.time_ns()))
    root.mkdir()
    shutil.copyfile(__file__, root / 'record_blocked_audit_once.py')
    shutil.copyfile(HERE / 'goal-blocked-transition.json', root / 'goal-blocked-transition.json')
    before = {name: (BASE / name).read_bytes()
              for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']}
    for name, raw in before.items():
        assert raw == (audit_root / ('before-' + name)).read_bytes(), 'Head changed after audit'
        (root / ('before-' + name)).write_bytes(raw)
    status = json.loads(before['full-gui-current.json'])
    linked_before = json.loads(json.dumps(status['linked_remaining31']))
    status['time'] = time.time()
    status['goal'] = 'blocked'
    status['goal_execution_blocked_waiting_existing_human_choice'] = True
    status['automation_preferences_or_status_changed'] = False
    status['previous_goal_turn_classification'] = 'progress: locked template and19 CPU groups plus fresh read-only resource evidence'
    status['current_goal_turn_classification'] = proof['current_goal_turn_classification']
    status['authorities']['three_turn_source_choice_blocked_audit'] = audit_pointer
    status['pending_decision_blocked_audit'] = {
        'condition': proof['condition'], 'affected_consecutive_goal_turns_verified': 3,
        'turn_ids': proof['turn_ids'], 'answer_received': False,
        'goal_tool_returned_status': 'blocked', 'goal_completed_or_user_paused': False,
        'source_choice_already_requested_no_duplicate': True,
        'full32_scope_and_remaining29_not_redefined': True,
        'human_reply_required_to_resume_dependent_work': True,
        'source_native_images_actions_BF16_or_budgets_changed': False,
    }
    status['latest_findings'] = [
        'Required human source-condition choice remains unanswered for three verified consecutive goal turns; independent reviewable preparation is complete and further experimental action depends on this choice.',
        'Goal tool status=blocked, not complete or user-paused. No new inference, GUI, source-rule deployment or old queue/terminal retry.',
        'Original32/16pairs/8tasks and three completed endpoints including failures remain;29 tracks unstarted; Mirage reduction and goal completion unproven.',
    ]
    assert status['linked_remaining31'] == linked_before
    save(root / 'status.json', status)
    header = '''## 最新：2026-11-10 目标BLOCKED：等待已提出的来源规则选择；未开始剩余29轨

已核实同一来源规则选择连续3个目标回合未获回复，已调用goal工具并返回blocked。原32轨/16对/8选任务范围保留，3个既有终局封存，29轨仍未开始；目标未完成，Mirage降幅未证明。来源修复、原32分析账本及29轨锁定模板均已完成独立准备，没有必要重复旧测试/识别试验。下一步依赖用户对已发出选项的真实回复，不能以自动目标继续或经过时间代替选择。

权威 `remaining29-runtime-template-20261110-36/blocked-audit-created.json` 与 `blocked-publication-created.json`。没有新推理/GUI/规则部署/资源变更，不重启旧队列或终局；没有修改任何automation偏好/状态。回复后应使用新链接运行包、保持全部原预算并重新核验实际资源；不要重跑三个已结束轨迹。

'''
    after = {'README.md': header.encode('utf-8') + before['README.md'],
             'HANDOFF.md': header.encode('utf-8') + before['HANDOFF.md'],
             'full-gui-current.json': (root / 'status.json').read_bytes()}
    for name, raw in after.items():
        target = BASE / name
        assert target.read_bytes() == before[name]
        target.write_bytes(raw)
        assert target.read_bytes() == raw
    save(root / 'receipt.json', {'actual_goal_tool_status': 'blocked', 'audit': audit_pointer,
                               'all_heads_exact_readback': True, 'outcomes_labels_scope_and_budgets_unchanged': True,
                               'new_model_GPU_GUI_scorer_paid_calls': 0})
    save(root / 'seal.json', {p.name: sha(p) for p in sorted(root.iterdir()) if p.is_file()})
    pointer = {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
               'status_sha256': sha(root / 'status.json'), 'goal': 'blocked'}
    save(HERE / 'blocked-publication-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['audit', 'publish'])
    args = parser.parse_args()
    audit() if args.action == 'audit' else publish()
