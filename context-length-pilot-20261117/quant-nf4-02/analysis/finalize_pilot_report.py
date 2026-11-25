"""Finalize prose only after every planned branch has a terminal record."""
from pathlib import Path
import json,subprocess,sys

P=Path(__file__).resolve().parent
d=json.loads((P/'continuation-latest.json').read_text(encoding='utf8'))
assert d['status']['phase']=='completed', 'The pilot is not complete.'
terminals=[b for b in d['branches'] if 'terminal' in b]
assert len(terminals)==36, 'Expected all 36 planned branch terminal records.'
finished=[b for b in terminals if b['terminal'].get('reward') is not None]
skips=[b for b in terminals if b['terminal'].get('reward') is None]
success=sum(b['terminal']['reward']==1 for b in finished)
max_input=max(r['input_tokens'] for b in d['branches'] for r in b['responses'])
subprocess.run([sys.executable,str(P/'summarize_continuations.py')],check=True)
old='本报告回答的是快速触发诊断。完整分支续跑尚未全部完成，最新状态见同目录 `4090-live-status.json` 和上级 `PROGRESS.md`；不得把本报告称为五档正式实验全部完成。'
new=(f'本批技术预实验的计划分支已经全部处理：**{len(finished)} 条实际续跑完成，{len(skips)} 条未执行续跑并单列原因**。'
     f'已完成续跑中 {success} 条官方得分为 1，其余 {len(finished)-success} 条为 0；正常对照均为 0。'
     f'实际续跑最大输入为 {max_input:,} token。详见 [CONTINUATIONS.md](CONTINUATIONS.md)。'
     '自然 40k 首次注入仍无样本，因此不能称为五档正式统计已经完成；续跑没有改变先前的首次触发结果。')
path=P/'RESULTS.md';s=path.read_text(encoding='utf8')
if old in s:s=s.replace(old,new)
elif new not in s:raise RuntimeError('Unexpected RESULTS.md completion paragraph; manual review required.')
path.write_text(s,encoding='utf8')
path=P.parent/'README.md';s=path.read_text(encoding='utf8')
old='诊断期间的临时暂停已解除，完整续跑继续运行；本轮未重启用户暂停的旧防御队列。具体完成数以 [PROGRESS.md](PROGRESS.md) 的检查时刻为准。'
new=(f'本批续跑已结束：{len(finished)} 条实际续跑完成，{len(skips)} 条单列为跳过或未执行。'
     '结果见 [analysis/CONTINUATIONS.md](analysis/CONTINUATIONS.md)。本轮未重启用户暂停的旧防御队列。'
     '资源退出状态另以服务器退出记录和进程检查确认。')
if old in s:s=s.replace(old,new)
elif new not in s:raise RuntimeError('Unexpected README completion paragraph; manual review required.')
path.write_text(s,encoding='utf8')
root_readme=P.parent.parent/'README.md'
root_text=root_readme.read_text(encoding='utf8')
status_line=(f'**本批 NF4 预实验已结束：{len(finished)} 条实际续跑完成，{len(skips)} 条单列跳过；自然 40k 首次注入仍未覆盖。** '
             '完整结果见 [quant-nf4-02/analysis/RESULTS.md](quant-nf4-02/analysis/RESULTS.md)。\n\n')
if status_line not in root_text:
    first,rest=root_text.split('\n',1)
    root_readme.write_text(first+'\n\n'+status_line+rest.lstrip('\n'),encoding='utf8')
print(json.dumps({'finished':len(finished),'skipped':len(skips),'reward1':success,'max_input_tokens':max_input}))
