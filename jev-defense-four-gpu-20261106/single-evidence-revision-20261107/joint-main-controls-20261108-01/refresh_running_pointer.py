"""Publish verified attempt-02 progress; never mutate completed receipts."""
from pathlib import Path
import hashlib
import json
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

snapshots = sorted((HERE / 'progress-evidence').glob('*/stdout.json'), reverse=True)
snapshot = next(p for p in snapshots if json.loads(p.read_bytes()).get('root', '').endswith('-02'))
d = json.loads(snapshot.read_bytes())
for key in ['launcher-process.json', 'worker/process.json']:
    actual = d[key]['value']['actual']
    assert actual['uid'] == 1033 and 'joint-main-controls-20261108-02' in actual['command']
    assert len(actual['locks']) == 9 and all(x['matches'] for x in actual['locks'])
assert d['journal']['errors'] == [] and 'worker/loaded.json' in d

archive = HERE / 'pointer-history' / str(time.time_ns())
archive.mkdir(parents=True, exist_ok=False)
pointer = PROJECT / 'single-evidence-development-current.json'
(archive / pointer.name).write_bytes(pointer.read_bytes())
launch = HERE / 'technical-retry-02/launch.json'
failure = HERE / 'technical-retry-02/failure-preservation.json'
value = {
    'status': 'attempt02_both_models_actually_loaded_finite_controls_running',
    'directory': str(HERE), 'remote_root': d['root'],
    'launch_receipt': str(launch), 'launch_sha256': sha(launch),
    'manifest_sha256': json.loads(launch.read_bytes())['manifest_sha256'],
    'latest_verified_evidence': str(snapshot), 'latest_evidence_sha256': sha(snapshot),
    'actual_worker_pid_locator': d['worker/process.json']['value']['actual']['pid'],
    'actual_launcher_pid_locator': d['launcher-process.json']['value']['actual']['pid'],
    'PIDs_require_full_identity_recheck': True,
    'loaded_receipt_sha256': d['worker/loaded.json']['sha256'],
    'verified_journal_events': d['journal']['verified_events'],
    'journal_head': d['journal']['head'], 'actual_event_counts': d['journal']['kind_counts'],
    'maximum_new_auxiliary': 4, 'maximum_new_judge': 16,
    'maximum_new_actor_GUI_scorer_paid': 0,
    'previous_completed_auxiliary_calls': 8,
    'original_zero_call_failed_attempt_preservation': str(failure),
    'original_failure_preservation_sha256': sha(failure),
    'old_terminals_must_not_be_replayed': True,
    'formal_GUI_launch_ready': False,
    'combined_auxiliary_to_actor_effect_tested': False,
    'last_observed_unix': d['time_unix'],
}
pointer.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
head = '''## 最新：2026-11-08 attempt02 已联合加载并真实推理；覆盖旧01加载描述

当前实际运行的是 `single-evidence-revision-20261107/joint-main-controls-20261108-01/technical-retry-02/launch.json` 指向的远端 **joint-main-controls-20261108-02**，不是旧01。最新只读快照 `{snapshot}` 复核 launcher3630398/worker3630561 的 UID1033、完整命令、start_ticks 与九把继承锁，journal{events}条校验无误；PID只作定位须重核。两模型均已真实CUDA加载，27B占物理4/5/6（18/24/22 decoder），唯一9B图像辅助在7，0–3外人计算未动。实际辅助请求已经开始，不是仅静态准备。

旧01在任何加载/调用前被资源门错误拒绝：独立 inference.lock 被误当额外外来锁。原24终局项/完整日志/7事件链已保留于 `technical-retry-02/original-failure`，不得重跑。新02只修锁核验：原九锁不变，额外只接受精确路径/UID/inode/device/WRITE owner均匹配的一把任务推理锁；11新边界检查通过。输入、模型、生成及预算未改。

本批4新辅助图/8新构造Controller.inspect控制；最多4辅助+16judge，0actor/GUI/scorer/付费。辅助仅原图+固定通用提示，主控制保留原完整历史/图像。两模型驻留与分别推理，不等于辅助答复已改变actor，更非完整GUI或Mirage降幅。辅助不合契约或语义失败均原样保留，不重采样。blank/loading/no-results负例、paired actor和完整GUI仍未完成；旧队列继续禁启。

'''.format(snapshot=str(snapshot.relative_to(PROJECT)).replace('\\', '/'), events=d['journal']['verified_events'])
handoff = PROJECT / 'HANDOFF.md'
(archive / 'HANDOFF-before.md').write_bytes(handoff.read_bytes())
handoff.write_text(head + handoff.read_text(encoding='utf8'), encoding='utf8')
readme = HERE / 'README.md'
(archive / 'README-before.md').write_bytes(readme.read_bytes())
readme.write_text('> 当前实际为attempt02；旧01在0加载/0调用时资源门失败，原终局完整保留。'
                  '新02已真实联合CUDA加载且辅助请求运行，参见technical-retry-02/launch.json和当前progress-evidence。'
                  '下方原启动01输出路径只属历史，不得作为当前运行定位。\n\n' + readme.read_text(encoding='utf8'), encoding='utf8')
(archive / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in archive.iterdir() if p.is_file()}, indent=2), encoding='utf8')
print(json.dumps({'current_pointer': str(pointer), 'based_on_evidence': str(snapshot), 'old_pointer_preserved': str(archive)}, ensure_ascii=False))
