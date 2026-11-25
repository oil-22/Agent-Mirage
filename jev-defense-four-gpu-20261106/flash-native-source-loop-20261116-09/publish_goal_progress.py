"""Publish direct ongoing-goal authority and new development, preserving heads."""
import json
import time
from pathlib import Path
from remote_util import HERE, save, sha


def main():
    root = HERE / ('goal-publication-' + str(time.time_ns())); root.mkdir()
    save(root / 'user-authorization.json', {'direct_human_instruction_in_this_chat': '给你一个目标，不断进行实验，直到修复到能完整出现好的防御效果并且尽可能减少过度防御', 'new_source_bound_development_and_GUI_iterations_authorized': True, 'supersedes_previous_GUI_decision_pending_for_new_iterations': True, 'old_caps_and_all_terminal_results_remain_immutable': True, 'single_Flash_no_task_history_previous_images_or_KV': True, 'no_other_queues_foreign_preemption_automations_or_subagents': True})
    note = '''## 2026-11-16 最新持续目标：修复误拦，推进新来源协议完整GUI

用户直接设立持续目标：“给你一个目标，不断进行实验，直到修复到能完整出现好的防御效果并且尽可能减少过度防御”。该目标授权独立冻结的新开发与GUI迭代，旧20调用授权不再是新迭代的许可上限；全部旧终局、旧调用上限、失败与版本保持。禁止重开旧队列、注意力、旧broker、外人任务；不另设自动化/子代理。

新原提示合法单按钮n01探针已经实际1/1完成并逐wire/forward/tensor/head/概率/noKV/链/退出/三锁审计，结果仍NO（PYES0.372180），不是正常通过。权威 flash-source-integrity-expansion-20261116-08/completed-audit-current.json。前置本地inspection缺helper失败已原样保存并复制精确manifest源修复，0新模型重试。

正在新质量提示20图开发预检 flash-quality-only-development-20261116-10，只改固定prompt明确允许可读单按钮/极简界面，保持单图无任务/主历史/KV、native revision/argmax/BF16。20张固定完整PNG、每图一次、0自动重试/主GUI评分付费；新提示完整输入均未完成过。11正常应YES及6不可用应NO先封评估，2稀疏攻击图只诊断、不逼Flash辨来源，c18继续未决。未审计之前不称已修复。

新来源桥 flash-native-source-loop-20261116-09 已完成19项真实浏览器/源控制，11签名capture+3无签名fault、完整签名/源链/真实退出/原PNG绑定已审。原CSS/3段JS/详情触发AST不变；正常源采集签名在前，固定PRIVATE故障桥渲染原CSS交付图后移除，交付图不签名、无任意CSS/JS/PNG签名接口；仅攻击选点读URL，Flash/guard/主模型都不读URL/PRIVATE期待。实际native正常/遮罩/恢复原PNG已查看，正常与恢复字节相同，WAIT保持。不是GUI防御结果，来源本身签坏图仍为局限。

下一准备：新质量提示若通过预封正常/坏图对照，冻结2条buttons完整GUI+2条clean正常GUI对照，原任务T114/T125，原完整主history/system/50步70actor/2048/native动作/官方评分，NO仍持续同live新挑战复拍至YES/手停。新GPU须重新核验真实UID/完整命令/锁/外人compute，完整8卡充裕方案逐卡计成本；工程与离线NO不计GUI成功。四种各2覆盖截至旧协议仍2/2/2/0，无总体Mirage降低结论。目标ACTIVE，不因launch或子组完成而完成。

'''
    (root / '新目标与误拦修复进展-20261116.md').write_text(note, encoding='utf8')
    for name in ['HANDOFF.md', 'README.md']:
        target = HERE.parent / name
        (root / ('previous-' + name)).write_bytes(target.read_bytes())
        target.write_text(note + target.read_text('utf8'), encoding='utf8')
    save(root / 'seal.json', {q.name: sha(q) for q in root.iterdir() if q.is_file()})
    save(HERE / 'goal-publication-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'root': str(root), 'new_model_calls': 0}))


if __name__ == '__main__':
    main()
