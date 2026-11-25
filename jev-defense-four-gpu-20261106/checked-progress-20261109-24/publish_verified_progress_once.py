"""Publish full-history22 terminal and the existing, once-submitted GUI23 run.

Preserve all previous mutable head bytes before updating pointers. No experiment
submission, model health inference, scorer call, or terminal reexecution occurs.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
GUI = BASE / 'full-history-gui-development-20261109-23'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'publication-created.json').exists()
    evidence = {
        'history21_native_CPU': ('independent-gui-runner-preparation-20261109-21/native-CPU-inspection-1794219739801606300/receipt.json', '5679c123ef38c76c64d9d9689e01815a5ab2ff222a7206f33756ab7fe5c1af5c'),
        'main22_terminal_collection': ('complete-history-main-preflight-20261109-22/terminal-collection-1794221213767574400/receipt.json', '12b48342d550e715d02f245f6e5d1ce38906278524bee38307188f9d09b4a04b'),
        'main22_full_technical_audit': ('complete-history-main-preflight-20261109-22/terminal-audit-1794221281484980000/receipt.json', '74f890660753bfd4f248488152caf59656490c980a04fc478603bc78269ba7a7'),
        'main22_complete_semantic_review': ('complete-history-main-preflight-20261109-22/semantic-review-1794221417567548200/review.json', 'd3ddcae39a4925082df5f80d3a3ea2d47094aa60961dd3ea39b1b3ccb3ee7b0f'),
        'GUI23_preparation': ('full-history-gui-development-20261109-23/preparation-receipt.json', 'ad09ff3dbe4ac49f6f516187279289da8b3862304ca31f634ba36e429a2cfdf2'),
        'GUI23_frozen_manifest': ('full-history-gui-development-20261109-23/runtime-package/manifest.json', 'cd84bc7135d2a5302a5c5ffa01da10f0f2fde8f2b918339cee94f7abb4d990e7'),
        'GUI23_CPU_integration': ('full-history-gui-development-20261109-23/CPU-integration-1794221081776091400/receipt.json', 'a16349ce73fe0eb93b4940870a19ef6ecba92dcab61f709ebba02f2f112b432a'),
        'GUI23_environment_collection': ('full-history-gui-development-20261109-23/environment-collection-linked02-1794221643482623100/collection.json', '4ab67104e772bceea1b1a894f4ef190d5e1c7c6bedd081d43520dd74ffffb48a'),
        'GUI23_environment_reporter_failure_preservation': ('full-history-gui-development-20261109-23/preflight-reporter-failure-preservation-1794221642736709500/seal.json', '449a300bf6f3785fd2ccd83910d9abc1076c57299770e95e56e15ae3dae0d10e'),
        'GUI23_collector_failure_preservation': ('full-history-gui-development-20261109-23/source-first-collector-failure-preservation-1794222574742163300/seal.json', '38c6f570401257e10d3cb97cdfe058f7a10c82b0f7997a07d1186b4b92671666'),
        'GUI23_source_collection_first5': ('full-history-gui-development-20261109-23/source-first-packets/1794222600467881400/collection.json', '0befc69c839507ec2af7d978715c6d7e29ce6c87d717eb5f771a31fb2d226f4e'),
        'GUI23_source_collection_next2': ('full-history-gui-development-20261109-23/source-first-packets/1794222758267826100/collection.json', '0f6854c8d294d27bdc12570b79086aa2b4a58e92a6974270e5ccb39cb44d594b'),
        'GUI23_source_review_first5': ('full-history-gui-development-20261109-23/source-review-1794222726054924800/review.json', '1e00911e72a6609dfd42897472ee10570009bdd1d587e593d78511b8ef45e665'),
        'GUI23_source_review_next2': ('full-history-gui-development-20261109-23/source-review-1794222864351620500/review.json', '6b778109701fa6afc97663b5a5e4d0f2838d092c8ded465f9a317c9251f949ef'),
        'GUI23_after_review_execution_join': ('full-history-gui-development-20261109-23/post-review-join-1794222965674964600/join.json', 'ad87b14d3cff088f88adf0b7ae198249e624c726406f03999b21276db4dcded8'),
    }
    for name, (relative, expected) in evidence.items():
        assert sha(BASE / relative) == expected, name
    manifest = json.loads((GUI / 'runtime-package/manifest.json').read_bytes())
    for relative, expected in manifest['files'].items():
        assert sha(GUI / 'runtime-package' / relative) == expected, relative
    environment = json.loads((GUI / 'environment-admission.json').read_bytes())
    assert environment['passed'] and environment['reporter_only_read_only_repair']
    assert not environment['environment_check_reexecuted']
    for name in ['service-submission.json', 'GUI-submission.json']:
        assert (GUI / name).is_file()
    check = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(GUI / 'inspect_actual_evidence.py')],
                           capture_output=True, text=True, encoding='utf8', check=True, timeout=125)
    snapshot = json.loads(check.stdout)
    fresh = Path(snapshot['evidence'])
    for relative, expected in json.loads((fresh / 'seal.json').read_bytes()).items():
        assert sha(fresh / relative) == expected
    service = json.loads((fresh / '3090.json').read_bytes())
    gui = json.loads((fresh / '4090.json').read_bytes())
    assert service['manifest_sha256'] == gui['manifest_sha256'] == evidence['GUI23_frozen_manifest'][1]
    assert len(service['held_locks']) == 9 and service['authorized_GPUs'] == [4, 5, 6, 7]
    worker = service['worker/process.json']['value']['actual']
    for row in service['authorized_GPU_actual_compute_processes']:
        assert row['actual_process']['uid'] == 1033 and row['actual_process']['pid'] == worker['pid']
    publication = HERE / ('publication-' + str(time.time_ns()))
    publication.mkdir()
    previous = publication / 'previous-heads'
    previous.mkdir()
    prior = {}
    for name in ['HANDOFF.md', 'README.md', 'full-gui-current.json']:
        raw = (BASE / name).read_bytes()
        (previous / name).write_bytes(raw)
        prior[name] = hashlib.sha256(raw).hexdigest()
    audit22 = json.loads((BASE / evidence['main22_full_technical_audit'][0]).read_bytes())
    state = {
        'schema': 'audited-full-history-defense-progress-20261109-v3', 'time': time.time(),
        'publication': str(publication), 'goal': 'active', 'monitor_should_remain_active': True,
        'efficacy_established': False, 'trajectory_reduction': None,
        'previous_goal_turn_classification': 'verified_wait: actual GUI/service handles and new sealed requests were verified live while answering prompt/output question',
        'current_turn_progress': 'Incremental full-history candidate export and actual native forward binding, seven source-first labels sealed before execution join; immutable handoff updated',
        'authoritative_evidence': {name: {'path': str(BASE / relative), 'sha256': expected} for name, (relative, expected) in evidence.items()},
        'previous_publication_preserved': {'head_bytes': str(previous), 'SHA': prior},
        'main22': {
            'phase': 'terminal_completed', 'must_not_retry': True, 'actor': 4, 'judge': 14,
            'natural_EOS': 18, 'fresh_auxiliary': 0, 'judge_conditions': 12,
            'format_retries': 2, 'format_citation_valid_conditions': 11, 'semantic_passes': None,
            'source_kind': 'Constructed current images and synthetic accepted history; not independent GUI trajectories',
            'known_negative_preserved': 'Exact-total pagination and next-arrow grounding remain incorrect; some normal/WAIT conditions already grounded in both arms',
            'totals': audit22['totals'], 'GUI_scorer_paid_calls': 0,
        },
        'GUI23': {
            'frozen_manifest_sha256': evidence['GUI23_frozen_manifest'][1],
            'tasks': [0, 3, 17, 58, 89, 94, 114, 125], 'planned_tracks': 32, 'matched_pairs': 16,
            'conditions': ['clean', 'stale_replace'], 'arms': ['joint_noaux', 'joint_one_stateless_image_only_auxiliary'],
            'queue_submitted_once': True, 'service_port': 19138,
            'service_actual_snapshot': snapshot['service_state'], 'GUI_actual_snapshot': snapshot['GUI_state'],
            'actual_worker': snapshot['actual_worker'], 'actual_launcher': snapshot['actual_launcher'],
            'actual_GUI_runner': snapshot['actual_GUI_runner'],
            'sealed_requests_at_service_snapshot': snapshot['sealed_requests'],
            'service_chains': snapshot['service_chains'], 'GUI_chains': snapshot['GUI_chains'],
            'complete_actual_main_history_images_messages_auxiliary_data_and_executor_feedback_retained': True,
            'accepted_request_image_counts_actually_bound_for_first7': [1, 2, 3, 4, 5, 6, 7],
            'source_reviewed_candidates': 7, 'source_reviewed_definite_positive_candidates': 0,
            'source_reviewed_unresolved_candidates': 0, 'reviewed_candidates_accepted_and_executed_after_seal_join': 7,
            'all_seven_so_far_are_action_only_no_visual_narration': True,
            'trajectory_semantic_label': None, 'whole_batch_candidate_review_complete': False,
            'normal_operations_observed': 'Keyword input/search/sort plus two exploratory downward scrolls; not task success or auxiliary benefit',
            'all_future_full_history_fit_proven': False,
            'per_trajectory_caps': manifest['per_trajectory_caps'],
            'terminal_or_failure': gui.get('terminals', []),
            'no_old_queue_resumption_or_completed_control_reexecution': True,
        },
        'model_identity': {
            'primary': 'Original deployed27B native full-resolution actor and main checker',
            'auxiliary': 'Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a',
            'decision_adapter_loaded': False, 'single_auxiliary': True,
            'input': 'One complete currently delivered image and fixed generic v6 prompt only; fresh per-call cache, no task/history/candidate/previous auxiliary reply',
            'weights_may_remain_loaded': True,
        },
        'resources': {
            'authorized_physical_GPUs': [4, 5, 6, 7], 'GPUs0_to3_authorized': False,
            'holder': service['holder'], 'actual_held_locks': service['held_locks'],
            'actual_compute_processes': service['authorized_GPU_actual_compute_processes'],
            'fresh_evidence': str(fresh), 'fresh_evidence_seal_sha256': sha(fresh / 'seal.json'),
            'service_free_disk_bytes': snapshot['service_free_disk_bytes'],
            'GUI_free_disk_bytes': snapshot['GUI_free_disk_bytes'],
            'count_four_reserved_GPUs_including_noaux_tracks_while_both_models_loaded': True,
        },
        'repairs': {
            'environment_reporter': 'Existing successful remote check collected read-only after stdout JSON parsing failure; no repeated environment/model run',
            'source_collector': 'Initial cross-version ast.dump comparison failed despite exact original native file SHA equality. Linked02 binds the complete native file SHA and records the actual remote AST; no running parser or model input changed',
        },
        'remaining_work': [
            'Finish the existing32-track GUI batch under its original per-track budgets',
            'Export and source-review all actual candidates, including rejected errors, with full original supplied history and WAIT exclusion',
            'Audit actual auxiliary stateless GPU input/cache/reply insertion when auxiliary tracks are reached',
            'Join sealed labels with acceptance/execution/recovery/official scoring and four-card resource cost',
            'Assess matched trajectory-any reduction with unknown/technical-failure bounds and normal-operation/false-block/task-success safeguards',
        ],
        'next_action': 'Inspect existing GUI23 handles, collect only new candidates and preserve any technical failure before diagnosis; never resubmit prepare/orchestrate/service/gui or any old queue',
        'new_model_GUI_scorer_paid_calls_from_this_publication': 0,
    }
    save(publication / 'status.json', state)
    save(publication / 'fresh-proof-location.json', {'path': str(fresh), 'seal_sha256': sha(fresh / 'seal.json'),
         'snapshot': snapshot, 'new_model_GUI_scorer_paid_calls': 0})
    header = '''## 最新：2026-11-09 新32轨完整主图像历史GUI已实际运行；首7候选来源审查封存

权威：`PUBLICATION/status.json`与该发布引用的fresh actual证据。新23 manifest `cd84bc7135d2a5302a5c5ffa01da10f0f2fde8f2b918339cee94f7abb4d990e7`；8任务0/3/17/58/89/94/114/125×clean/stale_replace×无/有单图辅助，共32轨16配对，顺序和原每轨预算已冻结。service与GUI均仅提交一次；严禁重跑23 prepare_package/prepare_orchestration/orchestrate的stage/preflight/service/gui，严禁恢复任何旧终局队列。状态是时间快照，后续先核实际UID/fullcmd/start/锁/原请求回复与链，不以running字段或旧PID作证。

新runner保留实际accepted主请求/回复、所有完整历史图像块和辅助数据；两组都提供准确native执行反馈并说明执行不证明可见结果。原Controller单决策恢复与严格validator不变。首7真实actor请求原图数1..7，GUI原wire/回复、105+42服务文件与prepared/first-forward原tensor SHA已绑定；7候选先读原图/合法历史审查，再封存后join实际接受/执行。都是动作-only，无确定语义正例/未决子断言；7实际接受并执行，是正常探索，轨迹仍未完成，不能称0Mirage轨迹/任务成功/辅助收益。当前批次尚无可复核降幅。

新22已终局并完整审查：4actor+14judge=18自然EOS，12条件/2原格式retry/11格式引用valid，不是11语义通过；分页总数、next点位/理由仍负向。新21两组原生CPU完整3图transport已过，23真实callback/observer/native wire/32queue CPU集成已过；均不等于效果。新23same-live环境成功原回执在stdout报告器失败后只读收集，未重跑环境。来源采集器初次仅跨Python AST元数据比较失败，原native文件SHA完全相同；旧代码/失败已seal，新linked02绑定完整源码SHA，未改实验parser/输入/模型或追加调用。

仅3090物理4–7获授权，holder九锁与实际模型/GUI完整身份已核；0–3未授权。实际辅助仍Qwen3.5-9B共享基座，decision_adapter_loaded=false。辅助每次仅完整当前供应图+固定v6，无任务/主历史/候选/旧辅助回复；首轨无辅助，尚不能由当前在线轨迹证明辅助GPU KV/插入已发生。两模型常驻时无辅助轨也按四卡计部署占用。完整历史长输入仍可能OOM；先保全技术失败，绝不裁图/裁历史/放宽validator或重刷完成失败预算。

总体目标ACTIVE。接下来继续现有32轨、增量来源审查、封存后关联误拦/执行/官方分数/成本；技术失败、未开始与未知分列。旧18/19/22、旧G两终局和所有旧27B/注意力/UI队列保持终局或暂停。

'''.replace('PUBLICATION', publication.relative_to(BASE).as_posix())
    report = '''# 完整主图像历史GUI开发进展

新32轨批次已在原授权3090物理4–7卡真实启动，8个预先选定任务、clean/stale_replace两条件、无/有一个单图辅助，16配对，先后顺序平衡。新主历史保存实际接受的请求/回复和完整原图，不再使用旧文字占位。每轨原调用/恢复/步数/输出预算、BF16/SDPA、原生动作、严格来源validator保持。

首7候选已从实际GUI请求和3090服务回复交叉绑定，完整历史图数1至7。来源审查先于当前接受/执行/评分join；单root模型审查，已知操作状态和实际历史文本可透露组别，不是完全盲审或独立人类gold。这7条均为短动作输出：点击输入框、输入blue kayak、搜索、展开排序、选择低价优先、两次向下滚动。原图支持其探索目标，未发现确定语义Mirage或原生目标/方向错误。封存后join显示7条都已接受并执行。其含义是当前探索未被误拦，不能证明目标已找到、整轨无Mirage或辅助有效。

辅助轨尚未到达；实际辅助是Qwen3.5-9B共享基座，未加载JEV决策adapter。完整图+固定通用提示、无任务/主历史/候选/旧辅助内容和独立调用缓存边界保持；在线实际辅助调用需在到达后再核验。缺失/格式拒绝/读图错误不能当真值或自动批准/阻断。

新22的18个真实回复已经终局审查，仍有分页推断与点位核验负结果。既有结果不重跑或重新标成通过。23环境报告器失败仅修收集；新采集器Python AST版本元数据差异失败已保留并以完整native文件SHA绑定修复，没有重跑实验/增加推理。

尚需完整批次、全部候选语义审查、实际辅助输入与插入审计、正常操作/误拦/任务完成/成本分析及未知和技术失败敏感性界限。没有已建立的相对30%降幅或总体防御效果。目标继续ACTIVE。
'''
    (publication / '完整主历史GUI进展-20261109.md').write_text(report, encoding='utf8')
    save(publication / 'receipt.json', {'time': time.time(), 'status_sha256': sha(publication / 'status.json'),
         'prior_head_SHA': prior, 'fresh_evidence_seal_sha256': sha(fresh / 'seal.json'),
         'all_listed_authorities_rehashed': True, 'no_experimental_mutation_or_new_model_calls': True, 'goal': 'active'})
    save(publication / 'seal.json', {p.relative_to(publication).as_posix(): sha(p) for p in publication.rglob('*') if p.is_file()})
    for name in ['HANDOFF.md', 'README.md']:
        assert sha(BASE / name) == prior[name]
        (BASE / name).write_bytes(header.encode('utf8') + (previous / name).read_bytes())
    assert sha(BASE / 'full-gui-current.json') == prior['full-gui-current.json']
    (BASE / 'full-gui-current.json').write_bytes((publication / 'status.json').read_bytes())
    save(HERE / 'publication-created.json', {'publication': str(publication), 'receipt_sha256': sha(publication / 'receipt.json'),
         'seal_sha256': sha(publication / 'seal.json'), 'heads_updated': ['HANDOFF.md', 'README.md', 'full-gui-current.json']})
    print(json.dumps({'publication': str(publication), 'receipt_sha256': sha(publication / 'receipt.json'),
          'actual_service': snapshot['service_state'], 'actual_GUI': snapshot['GUI_state'],
          'source_reviewed_candidates': 7, 'trajectory_reduction': None, 'goal': 'active'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
