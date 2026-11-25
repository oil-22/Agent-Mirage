"""Report matched continuation outcomes, separately from Mirage labels."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone,timedelta
import json,statistics

P=Path(__file__).resolve().parent
d=json.loads((P/'continuation-latest.json').read_text(encoding='utf8'))
clean={r['path'].split('/')[0]:r for r in d['clean']}
rows=[]
for b in d['branches']:
    task,_,checkpoint,condition=b['path'].split('/')
    terminal=b.get('terminal',{})
    matched=terminal.get('reward') is not None
    rows.append(dict(task=task,bin=int(checkpoint.split('-')[1]),condition=condition,
        outcome=terminal.get('outcome','running'),executed_continuation_complete=matched,
        reward=terminal.get('reward'),normal_reward=clean[task]['reward'],
        final_step=terminal.get('final_step'),injection_step=terminal.get('injection_step'),
        additional_steps_vs_normal=(terminal['final_step']-clean[task]['steps']) if matched else None,
        continuation_steps_including_injection=(terminal['final_step']-terminal['injection_step']+1) if matched else None,
        max_input_tokens=max((r['input_tokens'] for r in b['responses']),default=None),
        model_generation_seconds=sum(r['seconds'] for r in b['responses']),
        semantic_label='not inferred from reward, duration, or non-wait action',path=b['path']))
rows.sort(key=lambda r:(r['task'],r['bin'],r['condition']))
(P/'continuation-summary.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
complete=[r for r in rows if r['executed_continuation_complete']]
skips=[r for r in rows if r['outcome']!='running' and not r['executed_continuation_complete']]
stamp=datetime.fromtimestamp(d['time'],timezone(timedelta(hours=8))).isoformat(timespec='seconds')
lines=['# 自然轨迹干预分支：实际续跑结果','',f'检查时间：{stamp}。运行阶段：`{d["status"]["phase"]}`。','',
       f'计划 36 条分支，已完成 {len(complete)} 条实际续跑，{len(skips)} 条跳过或异常，尚有 {36-len(complete)-len(skips)} 条未结束。','',
       '**以下是任务得分与步数，不是 Agent-Mirage 发生率，也不是已确认的错误恢复成本。** 各分支共享三个正常前缀，不能按独立任务进行显著性检验。','',
       '| 档位 | 已完成实际续跑 | 得分为 1 | 对应正常对照得分为 1 | 跳过或异常 |','|---|---:|---:|---:|---:|']
for bin_ in [2000,5000,10000,20000,40000]:
    g=[r for r in complete if r['bin']==bin_];sk=[r for r in skips if r['bin']==bin_]
    lines.append(f"| {bin_} | {len(g)} | {sum(r['reward']==1 for r in g)} | {sum(r['normal_reward']==1 for r in g)} | {len(sk)} |")
lines+=['','正常对照 T017、T000、T089 分别执行 12、6、18 步后停止，官方得分均为 0。干预分支存在成功案例，因此本批数据不能支持任务成功率下降的结论。','',
        '## 各分支','', '| 任务 | 档位 | 条件 | 结局 | 得分 | 相对正常对照多出的总步数 | 最大实际输入 token |','|---|---:|---|---|---:|---:|---:|']
for r in rows:
    def val(k):return '—' if r[k] is None else str(r[k])
    lines.append(f"| {r['task']} | {r['bin']} | {r['condition']} | {r['outcome']} | {val('reward')} | {val('additional_steps_vs_normal')} | {val('max_input_tokens')} |")
lines+=['','相对步数为干预分支总步数减对应正常对照总步数。负数表示更早停止，不能直接解释为恢复更快；正数也可能来自额外有效探索，不能自动算作错误损害。','',
        '干预后续跑中的输入长度用于描述运行负载，不能作为正常前缀在对应长度上的首次干预样本。40k 档位仍须按未干预正常轨迹覆盖判断。','',
        '任务得分使用原生 URL 匹配评估器，不能证明每条中间描述、视觉属性判断或推理都正确。语义事件与传播应回到交付截图、原文、实际动作及后续观察逐条核对。','',
        '触发对照与方法限制见 [RESULTS.md](RESULTS.md)。原始动作见 `continuation-latest.json`；结束后收集的截图及输出位于 `continuation-evidence/`。']
(P/'CONTINUATIONS.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps(dict(phase=d['status']['phase'],finished=len(complete),skipped_or_error=len(skips),pending=36-len(complete)-len(skips),success=sum(r['reward']==1 for r in complete)),ensure_ascii=False))
