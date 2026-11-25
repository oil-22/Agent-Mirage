"""Read public run status; never print the service credential or scorer answers."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,subprocess

P=Path(__file__).resolve().parent
ROOT='/data/researcher/context-length-natural-20261117/batch01'
REMOTE=r'''
from pathlib import Path
import json,time
p=Path(ROOT);d={'time':time.time(),'host':HOST}
kind='model' if HOST=='3090' else 'gui';out=p/(kind+'-output')
for n in ['status.json','exit.json','failure.json','startup-failure.json','initial-phase-completed.json']:
    f=out/n
    if f.exists():d[n]=json.loads(f.read_text())
receipt=p/(kind+'-launch-receipt.json')
if receipt.exists():
    d['launch']=json.loads(receipt.read_text());proc=Path('/proc')/str(d['launch']['pid'])/'stat'
    d['process_state']=proc.read_text().split()[2] if proc.exists() else None
if kind=='model' and (out/'loaded.json').exists():
    loaded=json.loads((out/'loaded.json').read_text())
    d['loaded']={k:loaded[k] for k in ['model','torch','transformers','physical_gpus','quantized_linear_modules','compute_dtype','vision_encoder_quantized','history_truncation','memory_patch']}
if kind=='gui':
    d['normal_generations']=len(list(out.glob('T*/clean/*-response.json')))
    d['checkpoints']=[]
    for f in sorted(out.glob('T*/clean/checkpoint-*/checkpoint.json')):
        r=json.loads(f.read_text());cp=f.parent
        decisions={f.name.replace('-decision.json',''):json.loads(f.read_text()).get('natural_EOS') for f in cp.glob('*-decision.json')}
        d['checkpoints'].append({'task':r['task'],'step':r['step'],'bin':r['bin'],'input_tokens':r['normal_input']['input_tokens'],
            'decisions_natural_eos':decisions,'normal_decision_saved':(cp.parent/(str(r['step']).zfill(3)+'-response.json')).exists(),
            'state_drift':(cp/'original-state-drift.json').exists(),'image_count':len(r['normal_input'].get('images',[]))})
    d['clean_terminals']=[{'task':f.parent.parent.name,**json.loads(f.read_text())} for f in sorted(out.glob('T*/clean/terminal.json'))]
    d['branch_terminals']=[{'path':str(f.relative_to(out)),**json.loads(f.read_text())} for f in sorted(out.glob('T*/branches/*/*/terminal.json'))]
    q=out/'continuation-queue.json';d['queued_branches']=len(json.loads(q.read_text())) if q.exists() else 0
print(json.dumps(d))
'''
all_status={}
for host in ['3090','4090']:
    r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-o','BatchMode=yes','-o','ConnectTimeout=10',host,'python3 -'],input='ROOT='+repr(ROOT)+'\nHOST='+repr(host)+'\n'+REMOTE,text=True,capture_output=True,timeout=40)
    if r.returncode:raise RuntimeError(host+': '+r.stderr[-2000:])
    d=json.loads(r.stdout);all_status[host]=d
    (P/(host+'-status-latest.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in d.items() if k not in ['clean_terminals','branch_terminals']},ensure_ascii=False))
d=all_status['4090'];m=all_status['3090'];s=d.get('status.json',{})
stamp=datetime.fromtimestamp(d['time'],timezone(timedelta(hours=8))).isoformat(timespec='seconds')
lines=['# 自然长度分层实验进度','',stamp,'',f"模型：`{m.get('status.json',{}).get('phase','not yet recorded')}`；GUI：`{s.get('phase','not yet recorded')}`。",'',
       f"当前任务：{s.get('task')}；步骤：{s.get('step')}；正常输入 token：{s.get('input_tokens')}；注入档位：{s.get('bin')}；条件：{s.get('condition')}。",'',
       f"已生成正常决策 {d.get('normal_generations',0)} 次，已结束正常任务 {len(d.get('clean_terminals',[]))}/5；已记录自然检查点 {len(d.get('checkpoints',[]))} 个。",'',
       '| 任务 | 自然步数 | 正常输入 token | 档位 | 已生成初始干预 | 正常决策已保存 |','|---|---:|---:|---:|---:|---|']
for c in sorted(d.get('checkpoints',[]),key=lambda r:(r['task'],r['step'])):
    lines.append(f"| T{c['task']:03} | {c['step']} | {c['input_tokens']} | {c['bin']} | {len(c['decisions_natural_eos'])}/4 | {c['normal_decision_saved']} |")
lines+=['',f"已排队续跑 {d.get('queued_branches',0)} 条，已有终止记录 {len(d.get('branch_terminals',[]))} 条。",'',
        '先完成五条正常轨迹及自然检查点注入，再执行独立续跑。未填充或删减历史构造长度，未运行旧防御队列。是否触发 Agent-Mirage 尚待证据审核，不能把注入次数或继续行动次数当作事件数。']
(P/'PROGRESS.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
