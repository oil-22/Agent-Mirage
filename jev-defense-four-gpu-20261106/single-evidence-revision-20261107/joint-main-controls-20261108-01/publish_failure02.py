"""Publish the actual OOM terminal before any new linked technical attempt."""
from pathlib import Path
import hashlib
import json
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
c = HERE / 'terminal-collection/1794141466927603400'
audit = json.loads((c / 'collection-audit.json').read_bytes())
t = json.loads((c / 'original/worker/terminal.json').read_bytes())
exit_value = json.loads((c / 'original/exit.json').read_bytes())
assert t['status'] == 'technical_failure' and audit['terminal']['all_SHA_verified']
assert len(t['attempted']['auxiliary']) == 4 and len(t['attempted']['judge']) == 6
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
saved = HERE / 'pointer-history' / str(time.time_ns())
saved.mkdir(parents=True)
pointer = PROJECT / 'single-evidence-development-current.json'
(saved / pointer.name).write_bytes(pointer.read_bytes())
value = {'status': 'attempt02_terminal_prefill_OOM_C05_no_active_inference',
    'directory': str(HERE), 'remote_root': audit['root'],
    'terminal_collection': str(c), 'terminal_collection_audit_sha256': sha(c / 'collection-audit.json'),
    'remote_terminal_manifest_sha256': audit['terminal']['manifest_sha256'],
    'terminal_files_verified': audit['terminal']['files'],
    'auxiliary_calls_completed': 4, 'auxiliary_EOS': 4, 'auxiliary_contract_valid': 3,
    'judge_calls_attempted': 6, 'judge_EOS': 5, 'judge_prefill_OOM': 1,
    'logical_controls_completed': ['C01','C02','C03','C04'],
    'logical_control_technical_failure': 'C05', 'unattempted': ['C06','C07','C08'],
    'failed_input_tokens': 17113, 'failed_generated_tokens': 0,
    'failed_physical_GPU': 6, 'worker_exit': exit_value['worker_exit_code'],
    'launcher_exit': exit_value['launcher_exit_code'],
    'no_completed_controls_to_be_replayed': True, 'pending_technical_repair_not_yet_started': True,
    'maximum_remaining_judge_calls_in_this_16_cap': 10,
    'auxiliary_total_across_new_development': 12,
    'actor_GUI_scorer_paid_calls': 0, 'formal_GUI_launch_ready': False,
    'actor_feedback_effect_tested': False, 'Mirage_reduction_established': False,
    'four_GPU_reserved_seconds_only_launcher_window': exit_value['four_GPU_reserved_seconds_in_launcher'],
    'original_holder_reservation_still_held': True,
}
pointer.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
head = '''## 最新：2026-11-08 attempt02 在C05完整历史prefill OOM终局；禁止重启旧批

权威：`single-evidence-revision-20261107/joint-main-controls-20261108-01/terminal-collection/1794141466927603400/collection-audit.json`。远端02共259终局项SHA核验，manifest `{manifest}`；原9完成调用的CPU/实际first-forward/输出IDs/EOS全核验，失败C05完整17113token/4image及实际forward也核验，0生成token。10实际调用=4辅助EOS+5judgeEOS+1judge prefill OOM；不是10模型语义通过。4辅助有3契约valid，N13超限拒绝，N16黑色按钮被说蓝/6个text_refs错关联等问题保留。

已完成C01正常点击通过、C03限定不确定获准、C04纯WAIT正确排除；C02两自然回复均错称点在Search内，由原containment拒绝，不能称主模型读准。C05在物理6卡申请202MiB而仅154.69MiB free时OOM，C06–08未开始；均不是模型阴性或无Mirage。worker/launcher exit1/1，原日志/请求/实际tensors/90事件链保留；原始tensor bytes留远端seal，未伪称完整本地镜像。完整GUI/actor/scorer/付费均0。

下一步只为未完成C05–08准备新linked技术重试，调整原4–7卡内层分配，不裁剪完整输入、不改BF16/生成/原严格validator/提示或retry预算。累计judge6已花，原16cap余10；新技术批最多8judge，0新辅助，禁止重复已完成N13–16/C01–04。尚未启动时不得报运行。仅该launcher656.325秒/2625.301四卡GPU秒，holder预留仍另计；非总成本。Mirage降幅和完整GUI准入仍未建立。

'''.format(manifest=audit['terminal']['manifest_sha256'])
handoff = PROJECT / 'HANDOFF.md'
(saved / 'HANDOFF-before.md').write_bytes(handoff.read_bytes())
handoff.write_text(head + handoff.read_text(encoding='utf8'), encoding='utf8')
(saved / 'seal.json').write_text(json.dumps({p.name:sha(p) for p in saved.iterdir() if p.is_file()}, indent=2), encoding='utf8')
print(json.dumps({'current_status':value['status'],'terminal_manifest':value['remote_terminal_manifest_sha256']}, ensure_ascii=False))
