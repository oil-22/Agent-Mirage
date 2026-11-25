"""Summarize unique main trajectories; keep probes, failures and branches separate."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
from deploy_scale100 import remote

P=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,time,collections
p=Path(ROOT);out=p/('model-output' if HOST=='3090' else 'gui-output');d=dict(host=HOST,time=time.time())
for n in ['status.json','failure.json','startup-failure.json','exit.json']:
    if (out/n).exists():d[n]=json.loads((out/n).read_text())
kind='model' if HOST=='3090' else 'gui';rec=p/(kind+'-launch-receipt.json')
if rec.exists():
    d['pid']=json.loads(rec.read_text())['pid'];proc=Path('/proc')/str(d['pid'])/'stat'
    d['process_state']=proc.read_text().split()[2] if proc.exists() else None
if HOST=='3090':
    if (out/'loaded.json').exists():
        v=json.loads((out/'loaded.json').read_text());d['loaded']={k:v[k] for k in ['model','quantized_linear_modules','physical_gpus','compute_dtype','history_truncation','memory_patch']}
else:
    ledger=p/'reuse-ledger.json';reused=json.loads(ledger.read_text())['completed_natural_trajectories'] if ledger.exists() else []
    d['reused_tasks']=[x['task_id'] for x in reused]
    d['completed']=[];folders=[Path(r['clean_path']) for r in reused]
    for f in sorted(out.glob('T*/clean/terminal.json')):
        v=json.loads(f.read_text());tid=int(f.parent.parent.name[1:]);d['completed'].append(dict(task_id=tid,**v));folders.append(f.parent)
    d['unique_completed']=len(set(d['reused_tasks']+[t['task_id'] for t in d['completed']]))
    d['partial_tasks']=[int(f.parent.name[1:]) for f in sorted(out.glob('T*/clean')) if not (f/'terminal.json').exists()]
    cps=[]
    for folder in folders:
        for f in sorted(folder.glob('checkpoint-*/checkpoint.json')):
            v=json.loads(f.read_text());cp=f.parent
            cps.append(dict(task_id=v['task'],bin=v['bin'],step=v['step'],input_tokens=v['normal_input']['input_tokens'],decisions=len(list(cp.glob('*-decision.json'))),state_drift=(cp/'original-state-drift.json').exists(),skips=[x.name for x in cp.glob('*-skip.json')]))
    # Add checkpoints from active unfinished tasks without counting those tasks as complete.
    for tid in d['partial_tasks']:
        for f in sorted((out/f'T{tid:03}'/'clean').glob('checkpoint-*/checkpoint.json')):
            v=json.loads(f.read_text());cp=f.parent
            cps.append(dict(task_id=tid,bin=v['bin'],step=v['step'],input_tokens=v['normal_input']['input_tokens'],decisions=len(list(cp.glob('*-decision.json'))),state_drift=(cp/'original-state-drift.json').exists(),partial_task=True,skips=[x.name for x in cp.glob('*-skip.json')]))
    d['checkpoints']=cps;d['bins']=dict(collections.Counter(str(x['bin']) for x in cps))
    d['initial_decisions']=sum(x['decisions'] for x in cps);d['state_drift_checkpoints']=sum(x['state_drift'] for x in cps)
    d['new_normal_generations']=len(list(out.glob('T*/clean/*-response.json')))
print(json.dumps(d))
'''

if __name__=='__main__':
    all_status={}
    for host in ['3090','4090']:
        d=remote(host,'HOST='+repr(host)+'\n'+code)
        (P/(host+'-status-latest.json')).write_text(json.dumps(d,indent=2),encoding='utf8');all_status[host]=d
        print(json.dumps({k:v for k,v in d.items() if k not in ['checkpoints','completed']}),flush=True)
    g=all_status['4090'];m=all_status['3090'];s=g.get('status.json',{})
    stamp=datetime.fromtimestamp(g['time'],timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    lines=['# 100 条自然主轨迹实验进度','',stamp,'',f"完整独立主轨迹：**{g['unique_completed']}/100**，其中复用 {len(g['reused_tasks'])} 条。",'',f"当前任务：{s.get('task')}；步骤：{s.get('step')}；当前正常输入 token：{s.get('input_tokens')}；阶段：{s.get('phase','尚未启动')}。",'',f"模型阶段：{m.get('status.json',{}).get('phase','尚未启动')}；PID：{m.get('pid')}。",'',f"已记录初始注入输出：{g['initial_decisions']}；可见状态漂移检查点：{g['state_drift_checkpoints']}（严格配对分析排除）。",'', '| Token 档位 | 已到达的自然检查点数（含当前进行中任务） |','|---|---:|']
    for b in [2000,5000,10000,20000,40000]:lines.append(f"| {b:,} ±10% | {g['bins'].get(str(b),0)} |")
    lines+=['','计数仅含固定任务面板中的不同任务主轨迹；注入分支、部分轨迹和补充诊断不凑入 100 条。新分支实际续跑暂缓。','', '任务未自然达到某档位时记为未覆盖，不补历史、不强制继续。各档位事件率需在视觉依赖与 Agent-Mirage 标签审核后计算，不能用继续行动次数代替。','', '参考图在初始消息中交付一次并保留；注入仅改变当前截图。','',f"复用任务：{g['reused_tasks']}。",f"新完成任务：{[r['task_id'] for r in g['completed']]}。"]
    for host,d in all_status.items():
        for k in ['failure.json','startup-failure.json']:
            if k in d:lines += ['',f'运行异常（{host}，{k}）：', '```', d[k].get('error',str(d[k])), '```']
    (P/'PROGRESS.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
