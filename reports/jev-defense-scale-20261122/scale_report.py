"""Render the preregistered measures from independently audited receipts."""

import argparse
from collections import Counter
from pathlib import Path
from statistics import median

from audit_panel import FAULT, READY, metrics
from live_common import load, put, sha


ARMS = {'defense': '真实早拍（有效回执）', 'missing': '缺图', 'white': '白屏', 'buttons': '仅剩按钮的过渡画面',
        'replaced': '交付环节替换为旧图', 'original': '原流程（无双帧 Flash）', 'fast': '快速更新',
        'sparse': '合法单按钮更新', 'boundary': '滚动边界'}
FLOWS = {'search': '搜索', 'type': '输入', 'pagination': '翻页', 'open': '打开弹窗', 'toggle': '切换设置', 'escape': 'Escape 关闭弹窗'}
REASONS = {'image_presence_NO': '存在性检查', 'receipt_NO': '可信回执检查',
           'temporal_pending_or_unsupported': '双帧 Flash', 'single_image_quality_NO': '单图 Flash'}


def ratio(k, n):
    return f"{k}/{n}（" + f'{100*k/n:.2f}'.rstrip('0').rstrip('.') + '%）' if n else '无可判定样本'


def link(text, path):
    return f'[{text}](<{Path(path).resolve().as_posix()}>)'


def pct_time(t):
    return f"{t['median_s']:.2f} 秒 / {t['p90_s']:.2f} 秒（{t['n']} 条）" if t else '无'


def fraction(k, n):
    return f'{k}/{n}' if n else '—'


def flow_table(a):
    lines = ['| 动作 | 原流程早拍进入 27B | 双帧组早拍进入 27B | 双帧组拦截并恢复 | 快速正常图首拍误拦 |',
             '|---|---:|---:|---:|---:|']
    for flow, name in FLOWS.items():
        arm = a['old_frame_by_flow'][flow]
        original, defense, fast = (arm[k] for k in ('original', 'defense', 'fast'))
        lines.append(f"| {name} | {fraction(original['fault_delivered'], original['first_fault_seen'])} | "
                     f"{fraction(defense['fault_delivered'], defense['first_fault_seen'])} | "
                     f"{fraction(defense['effective_recovery'], defense['first_fault_seen'])} | "
                     f"{fraction(fast['first_ready_false_hold'], fast['first_ready_seen'])} |")
    return lines


def make(audit_file, a):
    A = a['by_arm']
    panel = a['episodes']
    root = Path(a['attempt'])
    fault_arms = ('defense', 'missing', 'white', 'buttons', 'replaced')
    original, defense = A['original'], A['defense']
    ready_panel = [r for r in panel if r['case']['arm'] in ('fast', 'sparse', 'boundary')]
    normal = metrics(ready_panel)
    initial_counts = a['top_metrics']['initial_first_false_hold']
    paired = a['pairs']
    confirmed = [p for p in paired if p['both_first_early_confirmed']]
    pre, post = (sum(p[which] for p in confirmed) for which in ('original_fault_delivery', 'defense_fault_delivery'))
    recovered_count = sum(p['defense_loop_recovered'] for p in confirmed)
    fault_prevented = [p for p in confirmed if p['original_fault_delivery'] and not p['defense_fault_delivery']]
    fault_prevented_and_recovered = [p for p in fault_prevented if p['defense_loop_recovered']]
    exact = [p for p in paired if p['exact_same_confirmed_early_png']]
    both_replied = [p for p in confirmed if p['gate_seconds_original'] is not None and p['gate_seconds_defense'] is not None]
    delta = [p['gate_seconds_defense']-p['gate_seconds_original'] for p in both_replied]
    repaired_delta = [p['gate_seconds_defense']-p['gate_seconds_original'] for p in fault_prevented_and_recovered]
    leaked = [r for r in panel if r['case']['arm'] != 'original' and r.get('delivery_truth') in FAULT]
    normal_post_holds = [r for r in panel if r.get('any_post_ready_false_hold')]
    unfinished = [r for r in panel if r['status'] != 'main_inference_completed']
    native_escape = [r for r in panel if r.get('first_post_capture') and r['first_post_capture']['visual_label_override_reason']]
    run_title = '完成' if a['status'] == 'completed_panel' else '部分完成'
    lines = [
        '# Jev 截图防御：96 条浏览器实验',
        '',
        f"3090 · **{run_title} {a['audited_terminals']}/96 条可审计终局** · 4 种受控页面布局 × 6 类实际动作。",
        '',
        f"24 个延时配对里有 {len(confirmed)} 对经原图确认在两臂都制造出了真实早拍。在这些配对中，原流程有 **{ratio(pre, len(confirmed))}**"
        f" 的早拍进入 27B，现框架为 **{ratio(post, len(confirmed))}**。首张早拍被扣下并经复拍把正常图交付 27B 为 "
        f"**{ratio(recovered_count, len(confirmed))}**。按全部 24 条预定双帧轨迹计，证实闭环 {defense['effective_recovery']}/24。",
        '',
        f"三类正常对照合计：首张已确认正常的图被扣 **{ratio(normal['first_ready_false_hold'], normal['first_ready_seen'])}**；"
        f"不复拍就交付主模型 **{ratio(normal['ready_uninterrupted'], normal['planned'])}**。观察窗结束仍没有正常图进入 27B 的样本仍计入分母。",
        '',
        '## 各类异常',
        '',
        '| 场景 | 确认首张异常 / 计划 | 确认异常中首张被扣 | 拦截并复拍恢复 / 计划 | 异常最终进入 27B | 动作后 18 秒未放行 | 首次扣图环节 |',
        '|---|---:|---:|---:|---:|---:|---|',
    ]
    for arm in fault_arms:
        m = A[arm]
        stages = Counter(r['first_fault_hold_stage'] for r in panel if r['case']['arm'] == arm and r.get('first_fault_held'))
        stage = '；'.join(f'{REASONS[s]} {n}' for s, n in stages.items()) or '—'
        lines.append(f"| {ARMS[arm]} | {m['first_fault_seen']}/{m['planned']} | {ratio(m['first_fault_held'], m['first_fault_seen'])} | "
                     f"{ratio(m['effective_recovery'], m['planned'])} | {m['fault_delivered']}/{m['planned']} | "
                     f"{m['post_window_censored']}/{m['planned']} | {stage} |")
    uncertain = [r for r in panel if r.get('delivery_truth') == 'ambiguous']
    if uncertain:
        lines += ['', f"{len(uncertain)} 条交付时的画面处在更新边界或无法独立确认，单列为不确定，不记为正常或旧图。"]
    lines += [
        '',
        '早拍是动作已发出、页面尚未更新时真实采集的原图，回执仍有效。白屏和按钮过渡画面也是浏览器真实渲染；'
        '缺图和替换只在交付环节注入。替换是来源完整性故障，与正确签名的早拍分开。' 
        '原单图判据一直允许可读单按钮，因此这里的异常单按钮按动作结果尚未出现来评价；正常单按钮是独立正对照。',
        *(['', f"**Escape 造例例外：** {len(native_escape)} 条延时轨迹在测试回调前就拍到了弹窗已关闭的页面；"
                 '原图与同一布局的快速更新对照逐字节相同。它们保留在 96 条计划里，按正常图审计，不能当成拦截成功或漏拦。'] if native_escape else []),
        '',
        *flow_table(a),
        '',
        f"24 对中有 {len(exact)} 对首张确认早拍的 PNG 字节完全相同；{len(fault_prevented)} 对在原流程送了早拍、双帧组未送早拍，"
        f"其中 {len(fault_prevented_and_recovered)} 对证实复拍后交付了正常图。"
        '基线只移除双帧 Flash；其余检查一致。缺图、白屏、按钮过渡和旧图替换在本轮没有独立的无防御配对。',
        '',
        '## 正常图与等待时间',
        '',
        '| 正常对照 | 首个正常图误拦 / 已确认正常首拍 | 首拍直接交付 / 计划 | 最终正常图进入 27B / 计划 | 动作到放行：中位数 / P90 |',
        '|---|---:|---:|---:|---:|',
    ]
    for arm in ('fast', 'sparse', 'boundary'):
        m = A[arm]
        lines.append(f"| {ARMS[arm]} | {ratio(m['first_ready_false_hold'], m['first_ready_seen'])} | "
                     f"{m['ready_uninterrupted']}/{m['planned']} | {m['ready_delivered']}/{m['planned']} | {pct_time(m['post_gate_time'])} |")
    lines += [
        '',
        f"动作前正常初始图首拍被扣 {initial_counts} 条，初始观测窗结束未执行预定动作 {a['top_metrics']['initial_no_action']} 条。"
        f"所有组共 {len(normal_post_holds)} 条轨迹在页面结果明确更新后仍有拒绝。"
        '滚动边界组的无变化来自可信浏览器证据；这些放行不能归功于 Flash 识别了相同画面。',
        '',
        f"延时原流程动作至放行中位数 / P90：{pct_time(original['post_gate_time'])}；"
        f"延时双帧组全部已放行：{pct_time(defense['post_gate_time'])}；"
        f"延时双帧组真正放行正常图：{pct_time(defense['ready_gate_time'])}。"
        + (f"在确认恢复的 {len(repaired_delta)} 对中，双帧组耗时中位差 {median(repaired_delta):+.2f} 秒。" if repaired_delta else '')
        + (f"两边均有放行记录的 {len(delta)} 对中，差值中位数 {median(delta):+.2f} 秒。"
           if delta and len(delta) != len(repaired_delta) else ''),
        '',
        '放行延迟不含 27B 生成。18 秒是本次研究的观测窗口，窗内未通过就结束记录，不交付失败图；持续复拍的部署规则未改。',
        '',
        '## 可复查的失败与成功',
        '',
    ]
    if leaked:
        lines.append('防御组确认漏放：' + '、'.join(r['id'] for r in leaked) + '。')
    if unfinished:
        lines.append('没有获得 27B 完整结果的轨迹：' + '、'.join(f"{r['id']}（{r['status']}）" for r in unfinished) + '。')
    after_ready = Counter((r['case']['arm'], r['case']['flow']) for r in normal_post_holds)
    if after_ready:
        lines.append('已更新仍被扣的分布：' + '、'.join(f'{ARMS[arm]} / {FLOWS.get(flow, flow)} {n} 条' for (arm, flow), n in after_ready.items()) + '。')
    recovered = next((r for r in panel if r['case']['arm'] == 'defense' and r.get('effective_recovery')), None)
    if recovered:
        first, final = recovered['first_post_capture'], recovered['delivered']
        lines.append(f"闭环例子 **{recovered['id']}**：动作后 {first['s_after_action']:.2f} 秒获取早拍，"
                     f"扣下后在 {final['s_after_action']:.2f} 秒采到更新画面，{recovered['post_gate_seconds']:.2f} 秒时放行并获得 27B 的实际回复。"
                     f" {link('原始早拍', first['acquisition_png'])} · {link('恢复原图', final['acquisition_png'])} · "
                     f"{link('终局与调用索引', root / 'run/episodes' / recovered['id'] / 'terminal.json')}")
    if leaked:
        r = leaked[0]
        lines.append(f"漏放例子 **{r['id']}**：{link('原始漏放图', r['delivered']['acquisition_png'])} · "
                     f"{link('实际 27B 回复', root / 'run/primary' / r['main']['request_id'] / 'result.json')}")
    blocked_normal = next((r for r in normal_post_holds if r['case']['arm'] == 'fast' and not r.get('main')), None)
    if blocked_normal:
        first = blocked_normal['first_post_capture']
        n = sum(h['truth'] == 'ready' for h in blocked_normal['holds'])
        lines.append(f"正常图误拦例子 **{blocked_normal['id']}**：可以看到通知已经切到 On，"
                     f"但有 {n} 次确认正常的截图被拒且无主模型请求。 {link('被误拦的原图', first['acquisition_png'])} · "
                     f"{link('可复查事件链', root / 'run/episodes' / blocked_normal['id'] / 'events.jsonl')}")
    figure = audit_file.with_name('双帧拦截与误拦.png')
    if figure.is_file():
        lines.append(link('闭环恢复和误拦的四幅原图对照', figure))
    lines += [
        '',
        '## 证据与结论范围',
        '',
        f"独立验证了 {a['audited_terminals']} 条终局事件链与 {a['bound_signed_captures']} 次真实采集签名。"
        f"模型调用为 {a['model_calls']['quality']} 次单图 Flash、{a['model_calls']['temporal']} 次双帧 Flash、"
        f"{a['model_calls']['primary']} 次 27B（自然结束 {a['top_metrics']['main_natural_EOS']} 次）。"
        '逐次对照完整请求、实际首次前向的输入 ID、图像张量和图像网格、Flash 原生分数、27B 回包和 GPU 所有权。'
        + ('两个模型和浏览器均正常退出，本实验的 12 把资源锁已释放。' if a['resource_release'] else ''),
        '',
        '该结果衡量当前防御对坏截图的拦截和复拍恢复。六种动作由真实浏览器执行，但页面和故障由实验控制；'
        '主模型的后续提案未执行，模型误读不计入截图防御成败。没有正式任务评分或付费调用；不能由此估计完整代理任务的总体 Mirage 触发率。Flash、主模型和核验条件均未微调或中途更改。',
        '',
        f"{link('逐条独立审计 JSON', audit_file)} · {link('冻结统计口径', root / 'analysis-plan.json')} · "
        f"{link('冻结的 96 条配置', root / 'live_plan.json')} · {link('封存的完整实验校验索引', root / 'local-seal.json')}",
        '',
    ]
    return '\n'.join(lines)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('audit', type=Path)
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    a = load(args.audit)
    assert sha(Path(a['attempt']) / 'local-seal.json') == a['input_seal_sha256']
    put(args.out, make(args.audit, a).encode('utf-8'))
