"""Preserve handoff heads and record actual post-model audit continuation."""
import json
import time
from pathlib import Path
from remote_util import HERE, save, sha

root = HERE / ('IO-continuation-publication-' + str(time.time_ns()))
root.mkdir()
(root / 'before').mkdir()
head = f'''## 2026-11-16 当前：2/2 GUI终局，69主回复；仅CPU封存/审计仍在进行

本轮T058 model_stop/19主/18动作，T089 step_cap/50主/50动作，均1来源NO+1真复拍，official均0，0基础设施/cleanup错误。第一条完整逐轨审计与正常图交付已通过；第二条及整组完成前不先报2成功。模型/Flash/GUI原身份均已实际退出；launcher3007179 UID1033/start1242449681仍在顺序SHA封存原始张量，实际D状态/输出文件FD/IO字节持续推进，不是模型服务。released.json已记录17锁关闭；最终内核锁检查与整组退出审计尚待。不要kill正在封存的launcher，不要再次启动任何模型/GUI/旧队列。

原watcher exec session47249已因55秒只读审计SSH超时退出，勿轮询/重开。失败partial root trajectory-audit-receipt16-T089-stale_replace-gate-1794809123623714200保持；已完整保存在audit-IO-repair-1794809502101204700，seal与来源见linked-audit-preparation-current.json。原2 GUI绝不重跑。

新的audit_finished_trajectory_linked.py已实际运行，前台exec session78833，继续write_stdin等待该会话。它仅将8请求/批改为1请求/批、读取时限55→180秒；原strict SHA/实际张量/IDs/概率/EOS/历史检查不变，8个已完成原始请求核验按原operation seal/原输出/失败快照精确复用。其余42主/50Flash读取仍在进行；不分配GPU，不生成新回复。失败时保留新的partial root再关联只读续行，不重启实验。audit_completed_group_linked.py已准备但未启动；应在实际launcher完全退出并postexit-seal.json形成后运行，随后resource interval/kernel release/最终报告。现仍有较多大张量I/O，等待不是模型零分或新推理失败。

后续最终脚本已准备未运行：audit_resource_interval.py、audit_released_resources.py、write_protocol_report.py、publish_completed_protocol.py。第二条恢复图564e、第一条c2fae与旧交付c600均有精确SHA原图标签，independent-image-notes-1794805956420022200补齐564e；验收需在2逐轨封存后join_acceptance_checkpoint.py。四种各2目标仍有按钮缺口，旧10终局不改写。按钮20图新固定提示提案在{HERE.parent / 'flash-buttons-policy-proposal-20261116-07'}，request_user_input_async已询问，真实用户尚未回复；勿重问/默认批准/启动20调用。当前只继续已批两条的审计收尾。

'''
transitions = []
for label, path in [('new-HANDOFF.md', HERE / 'HANDOFF.md'), ('new-README.md', HERE / 'README.md'),
                    ('main-HANDOFF.md', HERE.parent / 'HANDOFF.md'), ('main-README.md', HERE.parent / 'README.md')]:
    old = path.read_bytes()
    (root / 'before' / label).write_bytes(old)
    path.write_bytes(head.encode('utf8') + old)
    transitions.append({'path': str(path), 'before_sha256': sha(root / 'before' / label), 'after_sha256': sha(path)})
save(root / 'state.json', {'created': time.time(), 'transitions': transitions,
                          'complete_GUI_trajectories': 2, 'complete_primary_replies': 69,
                          'model_GUI_not_relaunched': True, 'active_audit_exec_session': 78833,
                          'original_watcher_failed_not_running': 47249, 'new_model_GUI_calls': 0})
save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
save(HERE / 'IO-continuation-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
print(json.dumps({'root': str(root), 'new_model_GUI_calls': 0}))
