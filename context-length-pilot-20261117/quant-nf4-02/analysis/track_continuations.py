"""Read-only monitoring and public-artifact collection for the owned pilot."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from collections import Counter
import argparse,json,subprocess,time,tarfile,hashlib

P=Path(__file__).resolve().parent
ROOT='/data/researcher/context-length-pilot-20261117/quant-nf4-02'
SSH=['D:/Git/usr/bin/ssh.exe','-o','BatchMode=yes','-o','ConnectTimeout=10']
REMOTE=r'''
from pathlib import Path
import json,time
p=Path(ROOT)/'gui-output'
d={'time':time.time(),'status':json.loads((p/'status.json').read_text()),'branches':[],'clean':[]}
proc=Path('/proc/3181517/stat')
d['gui_process_state']=proc.read_text().split()[2] if proc.exists() else None
for f in ['exit.json','failure.json']:
    if (p/f).exists():d[f]=json.loads((p/f).read_text())
for folder in sorted(p.glob('T*/branches/checkpoint-*/*')):
    row={'path':str(folder.relative_to(p))}
    f=folder/'terminal.json'
    if f.exists():row['terminal']=json.loads(f.read_text())
    row['actions']=[json.loads(f.read_text()) for f in sorted(folder.glob('*-action.json'))]
    row['responses']=[{k:v for k,v in json.loads(f.read_text()).items() if k in ['input_tokens','output_tokens','seconds','natural_EOS','receipt','meta','visual_tokens','non_image_token_count']} for f in sorted(folder.glob('*-response.json'))]
    d['branches'].append(row)
for f in sorted(p.glob('T*/clean/terminal.json')):
    d['clean'].append({'path':str(f.relative_to(p)),**json.loads(f.read_text())})
print(json.dumps(d))
'''

def remote(code):
    r=subprocess.run(SSH+['4090','python3 -'],input='ROOT='+repr(ROOT)+'\n'+code,text=True,capture_output=True,timeout=45)
    if r.returncode:raise RuntimeError(r.stderr[-2000:])
    return json.loads(r.stdout)

def update():
    d=remote(REMOTE)
    (P/'continuation-latest.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
    terminals=[r for r in d['branches'] if 'terminal' in r]
    finished=[r for r in terminals if r['terminal'].get('reward') is not None]
    skipped=len(terminals)-len(finished)
    n_success=sum(r['terminal']['reward']==1 for r in finished)
    stamp=datetime.fromtimestamp(d['time'],timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    s=d['status'];pending=36-len(terminals)
    summary=dict(time=stamp,phase=s['phase'],task=s.get('task'),bin=s.get('bin'),condition=s.get('condition'),step=s.get('step'),finished=len(finished),skipped=skipped,pending=pending,reward1=n_success,gui_state=d['gui_process_state'])
    with (P/'continuation-monitor.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(summary,ensure_ascii=False)+'\n')
    lines=['# NF4 预实验进度快照','',stamp,'',
        f"运行阶段：`{s['phase']}`；GUI 进程状态：`{d['gui_process_state']}`。",
        f"当前任务 T{s.get('task',0):03}，档位 {s.get('bin')}，条件 `{s.get('condition')}`，步骤 {s.get('step')}。" if s['phase']=='branch_continuation' else '',
        '',f'36 个计划分支中：**{len(finished)} 条实际续跑结束，{skipped} 条跳过，{pending} 条尚未结束**（包含当前分支）。',
        f'已结束续跑中 {n_success} 条得分为 1，{len(finished)-n_success} 条得分为 0；三个正常对照得分均为 0。因此不能据此报告成功率下降，各分支也不是独立任务。','',
        '36 个自然轨迹初始干预输出与额外 30 次历史保留诊断已完成。**暂未观察到随上下文长度增长而稳定上升的触发趋势**；非等待动作不等同于 Agent-Mirage。见 [analysis/RESULTS.md](analysis/RESULTS.md)。','',
        '| 档位 | 正常轨迹覆盖任务数 | 初始干预输出数 |','|---|---:|---:|','| 2k | 3 | 12 |','| 5k | 3 | 12 |','| 10k | 2 | 8 |','| 20k | 1 | 4 |','| 40k | 0 | 0 |','',
        '自然 40k 样本仍未覆盖。容量测试与干预后续跑中出现的长输入，均不能充当未干预正常前缀的 40k 注入样本。','',
        '历史保留诊断只生成候选动作；其输出与实际续跑分开统计。动作前缀重放仅保证被检查的可见状态匹配，不是完整环境快照恢复。','',
        '本文件随当前监测脚本更新。原始运行快照及动作保存在 `analysis/continuation-latest.json`。']
    (P.parent/'PROGRESS.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return d,summary

def collect():
    code=r'''
from pathlib import Path
import tarfile,json,time,hashlib
root=Path(ROOT);p=root/'gui-output';out=root/'continuation-public-final.tar.gz'
files=[]
for f in p.rglob('*'):
    if not f.is_file() or any(x.startswith('.') for x in f.relative_to(p).parts):continue
    n=f.name
    if n.startswith('PRIVATE') or n=='browser_trace.zip':continue
    if n.endswith(('-action.json','-response.json','-decision.json','-skip.json','-observed.png','-normal-observation.png')) or n in ['normal.png','stale.png','blank.png','controls.png','checkpoint.json','prefix-actions.json','body.json','pairing.json','replayed-state.json','initial-decision-reuse.json','terminal.json','status.json','exit.json','failure.json','post-probe-state.json','original-state-drift.json']:
        files.append(f)
with tarfile.open(out,'w:gz') as t:
    for f in files:t.add(f,arcname=str(f.relative_to(p)),recursive=False)
print(json.dumps({'archive':str(out),'files':len(files),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'time':time.time()}))
'''
    meta=remote(code);archive=P/'continuation-public-final.tar.gz'
    r=subprocess.run(['D:/Git/usr/bin/scp.exe','-q','-o','BatchMode=yes','4090:'+meta['archive'],str(archive)],capture_output=True,text=True,timeout=120)
    if r.returncode:raise RuntimeError(r.stderr[-2000:])
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==meta['sha256']
    dest=P/'continuation-evidence';dest.mkdir(exist_ok=True)
    with tarfile.open(archive) as t:t.extractall(dest,filter='data')
    (P/'continuation-snapshot.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
    print('Collected '+json.dumps(meta),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--watch',action='store_true');ap.add_argument('--collect',action='store_true');args=ap.parse_args()
    while True:
        try:d,s=update()
        except Exception as e:
            print('MONITOR_ERROR: '+repr(e),flush=True)
            raise
        ended=s['phase'] in ['completed','failed','stopped'] or s['gui_state'] is None
        if ended or not args.watch:break
        time.sleep(45)
    if args.collect:collect()
