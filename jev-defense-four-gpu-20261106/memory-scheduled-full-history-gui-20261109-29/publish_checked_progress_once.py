"""Publish a fresh actual-process/evidence snapshot; never relaunch an experiment."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_bytes())


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def main():
    assert not (HERE / 'publication-created.json').exists()
    result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(HERE / 'inspect_actual_evidence.py')],
        capture_output=True, text=True, encoding='utf8', check=True)
    fresh = json.loads(result.stdout)
    evidence = Path(fresh['evidence'])
    for name, expected in read(evidence / 'seal.json').items():
        assert sha(evidence / name) == expected
    primary, gui = read(evidence / '3090.json'), read(evidence / '4090.json')
    service = primary['worker/status.json']['value']; state = gui['batch/status.json']['value']
    worker = primary['worker/process.json']['value']; runner = gui['control/runner-process.json']['value']
    assert len(primary['held_locks']) == 9
    manifest = HERE / 'runtime-package-linked02/manifest.json'
    assert primary['manifest_sha256'] == gui['manifest_sha256'] == sha(manifest)
    chain = gui['chains'][0]
    kinds = chain['counts']
    reviewed = []
    for number in [1, 2, 3]:
        pointer = read(HERE / ('source-review-%02d-created.json' % number))
        path = Path(pointer['review']) / 'review.json'
        assert sha(path) == pointer['review_sha256']
        reviewed.extend(read(path)['rows'])
    assert len({r['candidate_event_sha256'] for r in reviewed}) == 3
    counts = kinds.get('candidate', 0)
    assert counts >= len(reviewed)
    root = BASE / 'checked-progress-20261109-30' / ('publication-' + str(time.time_ns())); root.mkdir(parents=True)
    old = {}
    for name in ['HANDOFF.md', 'README.md', 'full-gui-current.json']:
        source = BASE / name
        old[name] = sha(source)
        (root / ('previous-' + name)).write_bytes(source.read_bytes())
    audit_pointer = read(HERE / 'first-nine-prefix-audit.json')
    assert sha(audit_pointer['audit']) == audit_pointer['audit_sha256']
    audit = read(audit_pointer['audit'])
    status = {'schema': 'actual-native-GUI29-complete-history-original-budget-continuation-progress-v1',
        'time': time.time(), 'goal': 'active', 'monitor_should_remain_active': True,
        'previous_goal_turn_classification': 'No experimental advancement while answering prompt/output question; next safe unfinished-GUI action taken in this turn.',
        'current_goal_turn_classification': 'progress: new29source/carryover boundaries, actual owned model and GUI launch, exact live state restore and first execution of pending11, new complete-input EOS calls, source-first sealed labels followed by execution joins',
        'efficacy_established': False, 'relative_Mirage_reduction': None,
        'authorities': {'manifest': {'path': str(manifest), 'sha256': sha(manifest)},
            'fresh_actual_UID_full_command_start_locks_GPU_request_seals_and_both_chains': {'path': str(evidence), 'seal_sha256': sha(evidence / 'seal.json')},
            'first9actual_native_tensor_ID_generation_EOS_audit': audit_pointer,
            'original_public_checkpoint_and_pending_pipeline_replay': str(BASE / 'gui-technical-continuation-20261109-27'),
            'original23and26terminals_remain_immutable': True},
        'previous_heads_SHA256': old,
        'actual_service_state_at_snapshot': service, 'actual_worker_identity_at_snapshot': worker,
        'actual_GUI_state_at_snapshot': state, 'actual_GUI_runner_identity_at_snapshot': runner,
        'service_event_chains': primary['chains'], 'GUI_event_chains': gui['chains'],
        'fresh_service_sealed_requests': len(primary['sealed_requests']),
        'fresh_service_EOS_sealed': sum(row.get('generation', {}).get('natural_EOS') is True for row in primary['sealed_requests']),
        'new29_GUI_actions_executed': kinds.get('action_executed', 0),
        'original_actions_carried_not_reexecuted': 10,
        'track_actions_total_at_snapshot': 10 + kinds.get('action_executed', 0),
        'source_review': {'new_candidates_at_snapshot': counts, 'new_reviewed_candidates': len(reviewed),
            'unreviewed_new_candidates_at_snapshot': counts - len(reviewed),
            'definite_Mirage_in_reviewed_candidates': sum(row['definite_semantic_Mirage'] is True for row in reviewed),
            'all3reviewed_candidates_action_only_no_factual_assertions': True,
            'original11candidate_reviews_retained_without_relabelling_or_double_counting': True,
            'full_trajectory_Mirage': None, 'scope': 'Source author single reviewer, not fully blind or human gold; labels sealed before current execution/detector joins.'},
        'restore': {'new_genuine_native_capture_exact_original_PNG_SHA256': '9b2ad22c58d1c64033d60d0197b81d9aa1b09313dfc20df3fe4ffc5c37808500',
            'restoration_receipt_SHA256': 'f6268762fcd0e71c1e271504cf612b59c74b8f14a496fd69d0efd6af55465aab',
            'actual_native_navigation_back_history_and_scroll_xy_matched': [0, 720],
            'original_ten_agent_actions_reexecuted': False, 'restoration_infrastructure_navigations': 3,
            'pending_decision11_recaptures_spent': 1, 'pending11_first_executed_after_original_unchanged_Controller_acceptance': True,
            'cached_readiness32_actor11_linked_judge34_not_regenerated': True,
            'transport_started_from_actor11_judge34_including_OOM': True},
        'capacity_and_conditions': {'primary_language_layers_physical4to7': [18, 18, 15, 13],
            'all_actual_forwards_GPU_only': True, 'idle_auxiliary_BF16_weights_RAM_storage_not_CPU_inference': True,
            'same_memory_schedule_in_both_future_arms': True, 'stateless_auxiliary_generation_under_this_schedule_proven': False,
            'input_history_BF16_SDPA_native_parser_strict_validator_original_caps_unchanged': True,
            'original32tracks16pairs8tasks_frozen_queue_unchanged': True,
            'first_track_infrastructure_interruption_and_changed_placement_requires_unknown_failure_sensitivity_bounds': True,
            'all_later_long_context_inputs_fit': None},
        'resource_scope': {'authorized_physical_GPUs': [4, 5, 6, 7], 'GPUs0to3_authorized': False,
            'actual_holder': primary['holder'], 'held_resource_locks_verified': len(primary['held_locks']),
            'authorized_GPU_actual_compute_processes': primary['authorized_GPU_actual_compute_processes']},
        'model': {'single_auxiliary': 'Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a',
            'decision_adapter_loaded': False, 'input': 'Only one full currently delivered image and fixed genericv6; no task/history/candidate/previous reply, fresh per-call KV and release'},
        'audited_first9_cost_only': audit['totals'],
        'cost_scope': audit['scope'] + ' Four reserved GPUs and transfers remain chargeable; current noaux cannot establish auxiliary savings.',
        'preparation_and_reporter_failures_preserved': [str(BASE.parent / 'j29fail/1794226700166151800'),
            *[str(p) for p in HERE.glob('stage-reporter-failure-preservation-*')],
            *[str(p) for p in HERE.glob('prefix-audit-syntax-failure-preservation-*')]],
        'next_action': 'Continue the existing29actual worker4091634/fullcmd/start and native runner4170432/fullcmd/start. Source-review new candidate14+ before joins; collect actual auxiliary residency/KV/input/actor insertion when enabled. Do not repeat29prepare/stage/service/gui or old23/26controls. Preserve any new technical terminal before linked original-budget diagnosis.',
        'outstanding': ['Finish the original32matched tracks with full original histories and per-track budgets',
            'Audit actual one-image auxiliary generation and actor insertion under the four-GPU weight schedule',
            'Complete source-first candidate reviews, any-Mirage trajectory labels and accepted/executed/recovery separation',
            'Estimate matched reduction with technical/unknown bounds plus normal-operation/false-block/official-success/cost safeguards'],
        'no_completed_track_or_30percent_reduction_claim': True}
    save(root / 'status.json', status)
    report = '''# 完整历史 GUI 接续与首批核验

新29已实际恢复原未完GUI。真实原生截图与中断前PNG逐字节一致，浏览器导航历史和滚动位置核对后，原第11个滚动首次执行。前10个Agent动作未重做；3次页面导航、指针移动和绝对滚动作为基础设施恢复单独记录，恢复截图消耗该决策原2次重截图预算中的1次。原readiness32、actor11和唯一linked26 judge34回复经过未修改Controller接续，未重新推理或重置预算。

新服务与GUI仅提交一次，实际UID/完整命令/启动时间、4–7卡UUID、原holder九锁、请求回复seal与两条事件链已经核验。新服务采用26已实测的18/18/15/13分层和闲置权重RAM调度；模型forward仍GPU/BF16/SDPA。两组保持同样部署方式；四张卡预留与换入换出时间均计成本。首条原轨混合了旧部署前缀和技术中断，不能作为完全同质的配对轨迹，分析须保留技术/未知敏感性边界。

首9份完成回复已核完整wire、原生输入输出IDs、CPU-prepared/actual-first-forward全部tensor绑定、原有效generation与EOS，含12图和13图完整actor输入；89560输入/1121输出tokens、273.1714秒native调用计时。计时含生成取证，不含加载、预处理、失败/进行中工作或holder外预留，不是walltime、货币、能耗或辅助收益。

新增前三候选为向下滚动、可见3按钮内的翻页点击、向下滚动。原图/完整合法历史审查标签先封存，再关联接受/执行，三者均已正常执行；没有叙述或GUI/历史/完成事实断言。不能把它们称为三条无Mirage成功轨迹，也不能据此推断触发率下降。原第11候选不重复计样本。尚未完整配对；辅助模型在本新调度中的真实生成及接入也尚待其enabled轨迹实际发生。

唯一辅助实际为Qwen3.5-9B共享基座，decision_adapter_loaded=false；每次仅单完整供应图和固定v6提示，无任务/主历史/候选/旧辅助输出，首KV为空且结束后释放。主模型完整历史、原图、2048/4096输出、50步、70actor/140judge、原恢复预算与严格validator保持。

本地打包重名、旧环境回执重新序列化造成的字节比较错误，以及新只读报告器空格语法错误均保留原源码、失败输出与SHA；修复使用新linked目录或只读回收既有上传，没有新增模型控制或修改实验输入。所有旧23/26终局和旧队列保持不可变。

当前完整状态、计数、实际进程和链头以同目录status.json所引用的fresh证据为准；不能依赖旧PID或running字段。继续现有运行、增量来源审查和完整配对分析。目标ACTIVE，尚无可复核Mirage降幅。
'''
    (root / 'report.md').write_text(report, encoding='utf8')
    save(root / 'receipt.json', {'schema': 'checked-native-GUI29-progress-publication-v1', 'time': time.time(),
        'status_sha256': sha(root / 'status.json'), 'report_sha256': sha(root / 'report.md'),
        'fresh_evidence_seal_sha256': sha(evidence / 'seal.json'), 'previous_heads_SHA256': old,
        'experimental_effect_established': False, 'goal': 'active'})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    head = ("## 最新：2026-11-09 新29完整历史GUI已真实接续；原第11动作首次执行，效果仍未证明\n\n"
        "权威 `" + str(root.relative_to(BASE)).replace('\\', '/') + "/status.json`，fresh实际证据`" + evidence.name + "`位于新29目录。manifest bced549e679b03e286e2663a34f17b2319b2b35f0ef09397a8f39404073ee8a0；新29service/gui都已仅提交一次，严禁重跑prepare/stage/service/gui或旧23/26终局。实际worker4091634 UID1033/start1184665082、launcher4091340/start1184661748与GUI runner4170432 UID1015/start121105551仅定位，后续须重核fullcmd/UID/start/锁/请求回复与链。\n\n"
        "新live PNG严格等于原9b2ad22c，原生导航历史和scroll[0,720]相符；3基础设施导航单列，前10Agent动作未重做。第11待执行scroll经原Controller缓存来源接续后首次实际执行，恢复截图消耗原2recapture中的1次。原11actor/34judge（含OOM＋linked26）预算携带；新调用从actor12/judge35起，无已完成推理重复。新9份完成回复的wire/native IDs/全部prepared-first-forward tensor/EOS已审计，89560input/1121output/273.1714native调用计时秒，非walltime/currency/energy/收益。\n\n"
        "新增前三候选先看原图/合法历史封存，再join，均正常接受执行：down、page3内点击、down；均action-only，不能称轨迹0Mirage或辅助收益。原11候选不重复计数，后续未审是unknown。仍未有完整配对/降幅。新调度为27B18/18/15/13分4–7，辅助闲置BF16权重存RAM，全部forward仍GPU；两组一致，四卡与传输计成本，首轨中断换层须敏感性边界。实际辅助仍9B共享基座，decision_adapter_loaded=false，新调度真实aux生成/KV/插入未实证，待enabled轨自然发生。主完整历史/原图/BF16/SDPA/native/严格validator/所有原cap保持。\n\n"
        "本地准备重名/回执序列化比较/只读报告语法失败均原件保全，linked修复0新增模型控制。目标ACTIVE；继续现有29真实进程、源优先增量审查和剩余31未启动轨，勿restart/热改/裁图历史/擅扩预算。0–3未授权，原4–7 holder九锁仍须实际核验。最新运行计数与链头见权威，不将快照当永久状态。\n\n")
    for name in ['HANDOFF.md', 'README.md']:
        assert sha(BASE / name) == old[name]
        (BASE / name).write_text(head + (root / ('previous-' + name)).read_text(encoding='utf8'), encoding='utf8')
    assert sha(BASE / 'full-gui-current.json') == old['full-gui-current.json']
    (BASE / 'full-gui-current.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    save(HERE / 'publication-created.json', {'publication': str(root), 'receipt_sha256': sha(root / 'receipt.json'),
        'status_sha256': sha(root / 'status.json'), 'goal': 'active'})
    print(json.dumps({'publication': str(root), 'receipt_sha256': sha(root / 'receipt.json'),
        'actual_service': service, 'GUI_step': state.get('step'), 'new29_executed_actions': kinds.get('action_executed', 0),
        'reviewed_new_candidates': 3, 'unreviewed_new_at_snapshot': counts - 3,
        'goal': 'active', 'Mirage_reduction_established': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
