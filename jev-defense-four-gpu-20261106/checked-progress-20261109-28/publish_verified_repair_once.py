"""Publish sealed capacity repair and honest, still-unready GUI continuation."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
read = lambda path: json.loads(Path(path).read_bytes())


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def main():
    assert not (HERE / 'publication-created.json').exists()
    cap = BASE / 'memory-scheduled-capacity-20261109-26'
    cont = BASE / 'gui-technical-continuation-20261109-27'
    terminal_pointer = read(cap / 'terminal-collection-created.json')
    terminal = Path(terminal_pointer['collection'])
    assert sha(terminal / 'audit.json') == terminal_pointer['audit_sha256']
    assert sha(terminal / 'receipt.json') == terminal_pointer['receipt_sha256']
    assert sha(terminal / 'seal.json') == terminal_pointer['seal_sha256']
    audit = read(terminal / 'audit.json'); assert audit['passed']
    replay_pointer = read(cont / 'pending-pipeline-replay-created.json')
    replay = Path(replay_pointer['replay'])
    assert sha(replay / 'receipt.json') == replay_pointer['receipt_sha256']
    assert sha(replay / 'seal.json') == replay_pointer['seal_sha256']
    replay_receipt = read(replay / 'receipt.json'); assert replay_receipt['passed']
    checkpoint_pointer = read(cont / 'checkpoint-created.json')
    checkpoint = Path(checkpoint_pointer['checkpoint'])
    assert sha(checkpoint / 'requirements.json') == checkpoint_pointer['requirements_sha256']
    old = BASE / 'checked-progress-20261109-25/publication-1794224556917561700'
    old_audit = read(old / 'technical-audit.json'); assert old_audit['passed']
    manifest = cap / 'runtime-package/manifest.json'
    assert sha(manifest) == '97cf2c2e68917528aea6c25a214d294ea6710aca247d99cb2b62a700c3c1b08c'
    out = HERE / ('publication-' + str(time.time_ns())); out.mkdir()
    previous = out / 'previous-heads'; previous.mkdir()
    prior = {}
    for name in ['HANDOFF.md', 'README.md', 'full-gui-current.json']:
        raw = (BASE / name).read_bytes(); (previous / name).write_bytes(raw)
        prior[name] = hashlib.sha256(raw).hexdigest()
    authorities = {
        'original_GUI23_terminal_audit': {'path': str(old / 'technical-audit.json'), 'sha256': sha(old / 'technical-audit.json')},
        'linked26_manifest': {'path': str(manifest), 'sha256': sha(manifest)},
        'linked26_complete_original_collection': {'path': str(terminal / 'receipt.json'), 'sha256': sha(terminal / 'receipt.json')},
        'linked26_technical_audit': {'path': str(terminal / 'audit.json'), 'sha256': sha(terminal / 'audit.json')},
        'GUI27_public_checkpoint': {'path': str(checkpoint / 'requirements.json'), 'sha256': sha(checkpoint / 'requirements.json')},
        'GUI27_source_exact_Controller_replay': {'path': str(replay / 'receipt.json'), 'sha256': sha(replay / 'receipt.json')},
        'GUI27_initial_replay_failure_preserved': {'path': str(cont / 'pipeline-replay-failure-preservation-1794225419441668500/seal.json'),
                                                 'sha256': sha(cont / 'pipeline-replay-failure-preservation-1794225419441668500/seal.json')},
    }
    minimum = min(row['free_bytes'] for row in audit['per_device_generation_peak_memory']) / 1024**2
    state = {'schema': 'verified-exact-full-input-memory-repair-and-GUI-carryover-progress-v1',
        'time': time.time(), 'goal': 'active', 'monitor_should_remain_active': True,
        'efficacy_established': False, 'relative_Mirage_reduction': None,
        'authorities': authorities, 'previous_head_SHA': prior,
        'previous_goal_turn_classification': 'no experimental advancement while answering prompt/output question from immutable sources',
        'current_turn_progress': 'All44original attempts audited, all11candidate reviews aggregated, stale running heads superseded. New original-budget exact failed-request capacity repair completed on authorized4-7. Full original Controller pending-decision replay now matches actual source requests and counters.',
        'original_GUI23': {'phase': 'immutable_technical_terminal', 'complete_tracks': 0,
            'technical_failure_tracks': 1, 'unstarted_tracks': 31, 'actual_attempts': 44,
            'natural_EOS': 43, 'prefill_OOM': 1, 'source_reviewed_candidates': 11,
            'candidate_definite_Mirage': 0, 'action_only_limitation': True, 'trajectory_Mirage': None,
            'official0_preserved_as_technical_failure_not_semantic_zero': True,
            'never_resubmit_original23_or_any_old_terminal_queue': True},
        'linked26': {'phase': 'completed_terminal', 'must_not_retry': True,
            'actual_judge_calls': 1, 'actual_auxiliary_actor_GUI_scorer_paid_calls': 0,
            'natural_EOS': True, 'input_tokens': 22596, 'original_complete_images': 11,
            'output_tokens': 201, 'all_native_input_tensor_and_generation_fields_equal_original0044': True,
            'primary_layers_on_physical4_to7': [18, 18, 15, 13],
            'CPU_only_stores_idle_BF16_weights_all_forwards_GPU': True,
            'auxiliary_GPU_full_weight_cycle_verified_without_forward': True,
            'weight_switch_seconds': audit['weight_residency_switch_seconds'],
            'successful_native_generation_seconds': audit['native_generation_seconds'],
            'four_GPU_reserved_seconds_inside_launcher': audit['four_GPU_reserved_seconds_inside_launcher'],
            'minimum_recorded_generation_end_free_MiB': minimum,
            'all_future_history_fit_or_GUI_recovery_proven': False,
            'numerical_output_identity_from_changed_placement_guaranteed': False,
            'worker_and_launcher_actual_absence_and_exit0_verified': True},
        'GUI27': {'phase': 'prepared_source_only', 'launch_ready': False,
            'pending_original_decision': 11, 'pending_action': 'scroll down',
            'pending_action_executed': False, 'accepted_original_history_messages': 20,
            'original_actor_spent': 11, 'original_judge_spent_including_OOM_and_linked26': 34,
            'next_real_judge_attempt': 35, 'next_real_actor_attempt': 12,
            'original_actor_judge_step_caps': [70, 140, 50],
            'source_exact_unchanged_Controller_CPU_replay_accepted': True,
            'normal_11th_action_not_counted_as_new_candidate_or_GUI_execution': True,
            'genuine_live_browser_restore_and_capture_binding_still_required': True,
            'source_replay_first_failure_preserved': 'Initial replay used the projected readiness PublicView as initial input, losing original references/history. Linked02 hydrates full original view; original Controller projects screen input itself. Exact request equality is maintained, not relaxed.'},
        'model_identity': {'primary': 'Original deployed27B', 'single_auxiliary': 'Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a',
            'decision_adapter_loaded': False,
            'auxiliary_input': 'One full currently delivered image plus fixed genericv6 only. No task/history/candidate/previous reply; fresh empty KV and release.'},
        'resources': {'authorized_physical_GPUs': [4, 5, 6, 7], 'GPUs0_to3_authorized': False,
            'actual_postexit_no_GPU_compute': True, 'original_holder_nine_locks_verified_retained': True,
            'weight_RAM_storage_is_not_CPU_inference': True,
            'four_reserved_GPUs_and_transfer_time_count_toward_deployment_cost': True},
        'next_action': 'Prepare and source-verify genuine native browser restoration without repeating10executed actions; bind new live capture to pending original current image. Admit new linked service with identical memory schedule in both arms, carried counters and original recovery budget. Never rerun original23or26, discard failed hard case, or silently reset budgets/history.',
        'outstanding': ['Complete genuine live GUI continuation and the31unstarted tracks using new once-only linked execution',
            'Audit actual stateless auxiliary inference and actor insertion under the new weight schedule',
            'Source-review every actual candidate before execution/score joins; keep WAIT/error/recovery axes separate',
            'Compute matched trajectory-any Mirage difference with infrastructure/unknown bounds, false-block, normal-operation, official-success and actual four-GPU cost safeguards'],
        'no_paired_efficacy_or_30percent_reduction_claim': True}
    save(out / 'status.json', state)
    header = f'''## 最新：2026-11-09 原22596tokens/11图OOM请求已在新26正常EOS；GUI仍待真实状态恢复

权威 `{out.relative_to(BASE).as_posix()}/status.json`、新26terminal-collection-1794225272780936500/audit.json（21cadb0e80c1c98440a7632fe51d45ca982c85379348a81c69146fd6a8f2ecba）、新27pending-pipeline-replay-1794225471974982000/receipt.json。26manifest97cf2c2e68917528aea6c25a214d294ea6710aca247d99cb2b62a700c3c1b08c。26为TERMINAL：1实际judge自然EOS201tokens，原22596tokens/11完整图/4096输出、全部CPU-prepared/actual-first-forward tensors与所有有效generation配置相等；0新aux/actor/GUI/scorer/付费。严禁重跑26 prepare/stage/admit/submit或已完成控制。

新工程调度：主27B语言层18/18/15/13分物理4–7；唯一9B空闲权重存RAM，辅助阶段主模型在7的组转RAM、9B上7，结束后交换回来。全部模型forward仍GPU/BF16/SDPA；不是CPU推理，不裁历史原图、不改native算法/validator。实际完整权重GPU双向切换通过，0辅助forward；两次切换共32.956秒，1judge native58.057秒，launcher内四卡839.710GPU秒。请求生成后最低记录余量{minimum:.2f}MiB，不是更长历史fit/辅助生成/端到端收益证明；移动device map可能改变数值输出。worker/launcher实际均已退出0，4–7无compute，原holder九锁仍持有。0–3未授权，旧队列不恢复。

原23技术终局与全部失败仍不可变：44尝试43EOS、1零token预填充OOM，11actor/33judge/0aux，10动作；32轨0完成1技术终局31未开始。原官方0不作modelzero。11动作-only候选来源覆盖全，无确定语义正例但整轨仍unknown，不能说防御有效。26计入原轨judge第34次，原140cap尚余106；actor已11/70，前10动作不重跑。

新27完整20条accepted消息与原图/第11待执行候选已源绑定。CPU重放原readiness0042、actor0043和唯一linked26回复，未经修改的Controller接受，计数11actor/34judge，0新推理/GUI/评分；不是第11动作已执行或新的独立语义样本。初次CPU回放错误用了screen投影视图，原失败/source/log/SHA保留；linked02从完整原PublicView恢复，让原Controller自行投影，全部实际request system/candidate/messages/images精确相等，未放宽来源检查。

GUI27 launch_ready=false：接下来恢复真实原生浏览器状态并用新live capture核对原当前图，承接完整历史/原计数/原恢复预算，再准备新的once-only服务/GUI继续原未完轨与31未开始轨。不得归档图冒充live、重做10动作、跳过硬失败、重刷已完成43＋1调用、静默reset预算或把中断/换层轨混为完全同质配对。实际辅助仍Qwen3.5-9B共享基座、decision_adapter_loaded=false；每次仅单完整当前供应图＋固定v6，空首KV/释放、无task/history/candidate/前次输出。目标ACTIVE，尚无可复核Mirage降幅。

'''
    (out / '完整输入显存修复与GUI续接边界-20261109.md').write_text(header, encoding='utf8')
    save(out / 'receipt.json', {'time': time.time(), 'status_sha256': sha(out / 'status.json'),
        'authorities': authorities, 'previous_head_SHA': prior, 'new_model_GUI_scorer_paid_calls_from_publication': 0,
        'goal': 'active', 'efficacy_established': False})
    save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    for name in ['HANDOFF.md', 'README.md']:
        assert sha(BASE / name) == prior[name]
        (BASE / name).write_bytes(header.encode('utf8') + (previous / name).read_bytes())
    assert sha(BASE / 'full-gui-current.json') == prior['full-gui-current.json']
    (BASE / 'full-gui-current.json').write_bytes((out / 'status.json').read_bytes())
    save(HERE / 'publication-created.json', {'publication': str(out), 'receipt_sha256': sha(out / 'receipt.json'),
                                           'seal_sha256': sha(out / 'seal.json')})
    print(json.dumps({'publication': str(out), 'receipt_sha256': sha(out / 'receipt.json'),
                      'exact_capacity_repair_completed': True, 'GUI_launch_ready': False,
                      'efficacy_established': False, 'goal': 'active'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
