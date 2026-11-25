"""Publish the locked local template and fresh evidence, without launching it."""
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


def verify(pointer, key='seal_sha256'):
    root = Path(pointer['root'])
    assert sha(root / 'seal.json') == pointer[key]
    for name, digest in read(root / 'seal.json').items():
        assert sha(root / name) == digest, name
    return root


def main():
    assert not (HERE / 'publication-created.json').exists(), 'Already published'
    template = read(HERE / 'preparation-created.json')
    template_root = verify(template)
    checks = read(template_root / 'CPU-checks.stdout.txt')
    assert checks['passed'] and len(checks['groups']) == 19
    assert template['launch_ready'] is False
    resources = list(HERE.glob('resource-evidence-*-created.json'))
    assert len(resources) == 1
    resource_pointer = read(resources[0])
    resource_root = verify(resource_pointer)
    evidence = read(resource_root / 'evidence.json')
    assert evidence['read_only'] and evidence['new_model_GUI_scorer_paid_calls'] == 0
    assert evidence['holder_full_identity_matches'] and evidence['nine_original_locks_actually_held']
    assert evidence['target_GPUs_empty'] and evidence['headroom_at_least23000MiB']
    observation = read(HERE / 'pending-decision-turn-observation.json')
    assert observation['new_human_source_condition_reply_received_in_active_context'] is False
    assert observation['source_condition_question_visible_in_prior_turn']
    root = HERE / ('publication-' + str(time.time_ns()))
    root.mkdir()
    shutil.copyfile(__file__, root / 'publish_preparation_once.py')
    shutil.copyfile(HERE / 'pending-decision-turn-observation.json', root / 'pending-decision-turn-observation.json')
    before = {name: (BASE / name).read_bytes()
              for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']}
    for name, raw in before.items():
        (root / ('before-' + name)).write_bytes(raw)
    status = json.loads(before['full-gui-current.json'])
    assert status['execution_state'] == 'original_batch_exited_after_technical_terminal'
    linked_before = json.loads(json.dumps(status['linked_remaining31']))
    assert status['linked_remaining31']['remaining_original_unstarted_track_count'] == 29
    status['time'] = time.time()
    status['previous_goal_turn_classification'] = 'progress: sealed native-answer source repair and exact original32-minus3 remaining29 primary-outcome preparation'
    status['current_goal_turn_classification'] = 'progress: locked remaining29 runtime template,19 new CPU continuation/isolation checks, fresh read-only owned4-7 identity/lock/compute evidence'
    status['authorities']['remaining29_locked_runtime_template_NOT_deployed'] = template
    status['authorities']['remaining29_fresh_readonly_owned_resource_evidence'] = resource_pointer
    status['remaining29_preparation'].update(
        runtime_template_built=True, runtime_template_authority=template,
        new_runtime_package_built=False, finalized_runtime_package_built=False,
        runtime_template_admission=False, launch_ready=False,
        original_Controller_forward_prompts_history_actions_and_budgets_unchanged=True,
        source_rule_choice_received=False, CPU_continuation_isolation_check_groups=19)
    status['fresh_resource_observation'] = {
        'authority': resource_pointer, 'captured_unix': evidence['captured_unix'],
        'holder_full_identity_matches': evidence['holder_full_identity_matches'],
        'nine_original_locks_actually_held': evidence['nine_original_locks_actually_held'],
        'target_GPUs_empty_at_observation': evidence['target_GPUs_empty'],
        'headroom_at_least23000MiB_at_observation': evidence['headroom_at_least23000MiB'],
        'prospective19142_port_not_listening_at_observation': not evidence['prospective_port_listeners'],
        'new_resources_or_locks_claimed': False, 'future_launch_must_recheck': True,
        'all_future_full_history_fit_or_efficacy_not_established': True,
    }
    status['pending_decision_blocked_audit'] = {
        'condition': 'human selection for formal native STOP answer source representation',
        'already_requested_no_duplicate_question': True, 'answer_received': False,
        'affected_consecutive_goal_turns_verified': 2,
        'turn_ids': [observation['question_and_prior_preparation_turn_id'], observation['current_turn_id']],
        'current_turn_has_concrete_progress': True, 'three_turn_threshold_not_yet_satisfied': True,
        'goal_status_kept_active': True,
        'next_if_same_blocker_persists': 'audit actual reply/current state and further meaningful work; blocked only if third consecutive and genuinely no safe progress remains',
    }
    status['unresolved_work'] = [
        'Already-requested human choice: exact decoded native STOP answer source or retain original raw-byte rule',
        'Finalize a new linked remaining29 runtime using that actual choice; recheck ownership/locks/UUID/compute/clients immediately before launch',
        'Run remaining29 complete GUI trajectories without reexecuting the three original endpoints or completed requests',
        'Source-first trajectory Mirage/execution/completion/false-rejection/exposure/cost review across all original32, retaining unknowns and version boundaries',
    ]
    status['latest_findings'] = [
        'Local locked runtime template prepared: all original32 plan bytes retained; three terminal exclusions and362 completed request IDs bound;29 never-started tracks retain original order and zero initial counters.',
        '19 CPU continuation/isolation groups pass. All four entrypoints refuse pending choice before model/browser/resource/network imports. Original Controller, forwards, prompts, full histories and per-track budgets unchanged.',
        'Fresh read-only3090 observation verifies original holder full UID/command/start, nine held locks, matching GPU4-7 UUIDs, no target compute and>=23000MiB free at observation. No new allocation or inference.',
        'Formal source-rule choice is still unanswered; new template is not remotely staged, finalized or launch-ready. No new semantic/GUI/model result; main-agent Mirage reduction remains unproven.',
    ]
    assert status['linked_remaining31'] == linked_before
    assert status['matched_efficacy_analysis_ready'] is False
    save(root / 'status.json', status)
    report = '''剩余29轨的本地运行模板已准备，3个原终局和362个既有请求均在来源绑定的排除清单中。19组新CPU续跑/隔离检查通过：逐轨从零开始、禁止旧请求和终局重入、保持原顺序/预算、技术终局停止队列；4个启动入口在导入模型、浏览器、GPU资源或网络模块前拒绝未决条件。主Controller、原生forward、固定v6、完整历史、图像及动作代码未改变。\n\n这些是工程准备，不是真实语义控制或防御效果。只读3090证据在采集时核实4–7卡原持有进程UID/完整命令/start、9个实际持锁描述符、UUID、空计算和显存；不新分配或抢占资源，正式启动仍需重新核对。\n\n先前来源规则选择仍待真实用户回复，模板admission=false、launch_ready=false，没有远程部署、新推理或GUI。实际聊天回合显示该选择出现在上一完整目标回合，本回为第二个连续受影响回合且有工程进展；未满足三回合blocked阈值，目标保持ACTIVE。主要终点仍为原32完整有/无辅助GUI轨迹中的主模型Mirage；辅助识别只作诊断，当前没有可核实降幅。\n'''
    (root / 'report.md').write_text(report, encoding='utf-8')
    header = '''## 最新：2026-11-10 剩余29轨本地运行模板与19组CPU检查完成；来源规则仍待选择

权威 `remaining29-runtime-template-20261110-36/preparation-created.json` 和 `publication-created.json`。原32计划/16对/8选任务保持；排除3个终局与362个既有请求，29轨均从零计数。19组CPU续跑/隔离检查通过，4个入口在模型/浏览器/资源/网络导入前拒绝未决条件。原Controller、forward、固定v6、完整主历史、动作和预算未改变；CPU模拟不是模型语义控制或GUI结果。

新只读3090回执核实持卡进程完整UID/命令/start、9把实际锁、4–7卡UUID/无compute/显存门槛；没有新分配。资源只代表采集时状态，实际启动还需重新核验。来源规则选择已提出且仍待回复，模板未部署/未选规则/admission=false/launch_ready=false，0新模型/GPU/GUI/scorer调用。实际回合审计为第二个受同一待决事项影响的连续目标回合，本回有工程进展，goal保持ACTIVE。效力未证实；3个原终局和所有未知、误拦、版本边界保留，旧队列绝不重启。

'''
    after = {'README.md': header.encode('utf-8') + before['README.md'],
             'HANDOFF.md': header.encode('utf-8') + before['HANDOFF.md'],
             'full-gui-current.json': (root / 'status.json').read_bytes()}
    for name, raw in after.items():
        path = BASE / name
        assert path.read_bytes() == before[name], 'Concurrent head change'
        path.write_bytes(raw)
        assert path.read_bytes() == raw
    save(root / 'receipt.json', {
        'template': template, 'fresh_readonly_resource_evidence': resource_pointer,
        '19_new_CPU_check_groups_passed': True,
        'original_closed_experiment_outcomes_and_labels_unchanged': True,
        'all_heads_readback_verified': True, 'new_model_GPU_GUI_scorer_paid_calls': 0,
        'before_SHA256': {k: hashlib.sha256(v).hexdigest() for k, v in before.items()},
        'after_SHA256': {k: hashlib.sha256(v).hexdigest() for k, v in after.items()},
        'goal': 'active', 'efficacy_established': False,
    })
    save(root / 'seal.json', {p.name: sha(p) for p in sorted(root.iterdir()) if p.is_file()})
    pointer = {'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
               'status_sha256': sha(root / 'status.json'), 'receipt_sha256': sha(root / 'receipt.json')}
    save(HERE / 'publication-created.json', pointer)
    print(json.dumps(pointer, ensure_ascii=True))


if __name__ == '__main__':
    main()
