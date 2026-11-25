import hashlib,json,shutil,time
from pathlib import Path
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
v=json.loads((H/'comparison-summary.json').read_bytes());m=v['models']
assert v['actual_calls']==v['complete_replies']==54
assert json.loads((H/'audit-receipt.json').read_bytes())['value']['status']=='passed'
assert json.loads((H/'final-resource-inspection.json').read_bytes())['value']['compute'].strip()==''
report=H/'三模型核验实测与选型结论-20261112.md'
lines=['# 单图 YES/NO 核验实测与选型结论','',
'**Flash 4B 与 NeoHorse 4B 在本轮明确标签样本上打平；Style 2B 发生一次合成加载画面漏放。尚无完整GUI中的Mirage降低结论。**','',
'实际运行：3090物理GPU4，三个固定revision原生模型分别顺序运行，同一组18张完整PNG，每模型18次，共54次独立调用。每次只有当前单图＋固定通用state/question/options，没有任务、主模型历史、候选动作或前一张图；实际forward无跨次KV缓存。全部54份二元答复完成，0推理失败、0重试。','',
'| 模型 | 不可用图漏放 | 可用图误拦 | 峰值分配显存 | 调用中位时长* |','|---|---:|---:|---:|---:|']
for key in ['flash','neohorse','style']:
 r=m[key];lines.append(f"| {r['model']} | {r['false_allow_unusable']}/6 | {r['false_reject_usable']}/10 | {r['max_peak_allocated_bytes']/2**30:.2f} GiB | {r['median_audited_call_seconds']:.2f} 秒 |")
lines+=['',
'*时长包括原生编码、推理和forward输入抓取；不包括每次资源准入检查、大张量写盘、SHA封存等开销。各自既有原生环境保留，未统一优化内核。该数字不是整批墙钟耗时、端到端GUI时延或公平部署成本结论。峰值为PyTorch已分配显存，非完整驱动总占用。','',
'9张真实历史原图＋9张合成控制。明确标签为10张可用、6张不可用；其余2张边界图不强迫标对错。真实可用7张、合成可用3张；真实不可用仅1张原空白、合成不可用5张。样本集中于同一网站，选取非盲；同一审查者在新输出前看联系表并封存标签，已知一些旧的不同问题结果。因此只是开发初筛，不能把16张明确标签结果称为普遍准确率。','',
'## 实际差异','',
'Style的c17为人工制作的整幅Loading画面，P(YES)=0.501526，按预设原生argmax返回YES；Flash、Neo均返回NO。这个失败接近二元边界，不能据一张合成图推出Style普遍不识别加载，也不能事后改阈值当作通过。没有新的真实加载正例。', '',
'正常页脚、原生无结果页、可读对话框、稀疏设置和深色空状态等明确可用样本，三者这轮均放行。判断只针对当前图像是否可解释，不等于任务成功或未来动作正确。','',
'| 无强制标签的边界图 | Flash | NeoHorse | Style |','|---|---|---|---|',
'| 旧buttons-only图，只剩Publish Ad和Search | YES | YES | NO |',
'| 合成的大面积内容遮挡，但页头仍可读 | YES | YES | YES |','',
'c09及c17在输出后另以完整原尺寸查看，未改动已封标签。已知注入制作方法不能代替模型实际能看到的证据：单图可能无法区分合法稀疏界面与被删去内容的页面，故不能把Style对c09的NO直接计为成功防御，也不能把两个4B的YES强制计为语义错。','',
'## 选型判断','',
f"预先写下的机械tie-break是同错数时取较低峰值显存，因此JSON候选为NeoHorse。但它只比Flash少{(m['flash']['max_peak_allocated_bytes']-m['neohorse']['max_peak_allocated_bytes'])/2**20:.2f} MiB，调用中位时长仅差{abs(m['flash']['median_audited_call_seconds']-m['neohorse']['median_audited_call_seconds']):.3f}秒；这些差别不足以构成实际优劣证据。**Flash与NeoHorse都保留为同级候选；若需按预设规则指定下一轮的一个模型，可暂用NeoHorse，但不能称其更准确或更能降低Mirage。** Style显存约一半，但本轮出现了加载图漏放，暂不作为优先候选。",'',
'本轮验证的是图片可用性门禁。清晰旧帧、正常可读但不符合主模型推断的画面，不能由此被判为安全或错误；这一接口也没有检测主模型随后发生的Mirage。两模型一致、概率高、基础门禁通过均不是Mirage降低证据。完整GUI中的触发、误拦、正常操作与任务完成仍须独立验证，当前降幅为null。','',
'## 核查和范围','',
'54份原始概率/读出分数绑定、完整PNG来源、实际input IDs/pixels/grid和每请求seal通过；另一个CPU审计程序重载54份实际forward张量逐字节核对SHA。三个38事件journal链与567个模型postexit文件通过，539份非大张量文件交付本地，532份原终局文件SHA在本地再次核对。原始forward张量留在3090原目录，无需重复推理。这个程序审计不是第二个独立盲评审查者。','',
'三模型worker和launcher已实查退出，GPU无compute，原holder UID1033/完整命令/start/九锁仍一致。没有启动主27B、actor、GUI、scorer、付费API或旧队列；原GUI目标保持用户暂停。本轮原生processor内部得到相同[1,44,80]网格，完整输入token数Flash1150、Neo1087、Style1101，差异来自各自原生文本模板。','',
'离线审计第一次在Flash Python环境导入Neo schema时缺pydantic而中断；source/stdout/stderr/已完成结果已保留，改用已有Neo环境执行相同CPU审计算法后全部通过，0新模型调用。两处本地进度显示/只读命令错误也已保留。均不是推理失败，也未改变判定、原图、样本或模型条件。','',
'完整设置和固定prompt见同目录《单图YES-NO三模型实测结果-20261112.md》及protocol.json；逐图概率见case-results.csv；机器摘要comparison-summary.json、audit-receipt.json、final-resource-inspection.json为权威。partial-*.json仅为中途记录，其中Style的pending固定文字被完整审计回执覆盖。','',
f"输出前标签SHA256：`{v['pre_output_labels_sha256']}`",f"协议SHA256：`{v['protocol_sha256']}`",f"机器摘要SHA256：`{sha(H/'comparison-summary.json')}`"]
with report.open('x',encoding='utf8') as f:f.write('\n'.join(lines)+'\n')
readme=('# 独立单图YES/NO三模型比较（完成）\n\n'
 '用户请求“你先试试这几个的效果给我一个答复”。本目录只执行Flash4B、NeoHorse4B、Style2B的新固定二元问题比较，不恢复原GUI目标。\n\n'
 '首先读三模型核验实测与选型结论-20261112.md、comparison-summary.json、audit-receipt.json、final-resource-inspection.json。54次真实调用全部完成，不重跑run_comparison.py、stage、submit或旧控件队列。\n\n'
 'Flash/Neo明确样本0/6漏放、0/10误拦；Style1/6漏放（合成加载图）、0/10误拦。两边界未强制gold。机械tie-break为Neo，仅少6.12MiB，没有模型效果胜负结论。Mirage降低null。\n\n'
 '9真实原图＋9合成控制；每次完整单图/固定prompt/空KV。所有54份实际张量和原生分数经退出后CPU核对，0新增推理。原始大张量在远端同名目录，metadata与审计在collection-receipt.json指向的本地目录。\n\n'
 '原终局、失败及首轮缺pydantic审计均保留。三worker/launcher已退出，原四卡holder九锁保持，广义GUI目标仍为用户暂停。新实验与正式条件不得从本比较自动外推或恢复。\n')
with (H/'README.md').open('x',encoding='utf8') as f:f.write(readme)
publication=H/('publication-'+str(time.time_ns()));publication.mkdir()
handoff=H.parent/'HANDOFF.md';previous=handoff.read_bytes();(publication/'before-HANDOFF.md').write_bytes(previous)
head=('## 最新：2026-11-12 独立单图二元三Jev比较54次完成；原GUI目标保持用户暂停\n\n'
 '权威binary-gate-comparison-20261112/三模型核验实测与选型结论-20261112.md、comparison-summary.json、audit-receipt.json及final-resource-inspection.json。只执行用户新请求的候选比较，不恢复旧GUI或此前持续目标。三固定revision×18张同图新单问，54完整原生二元答复、0推理失败/重试，0主27B/GUI/actor/scorer/付费调用。9真实历史图+9合成，10可用/6不可用+2无强制gold边界，预输出标签已封，非盲同网站开发初筛。\n\n'
 'Flash和Neo均漏放0/6、误拦0/10；Style合成Loading图近0.5而YES，漏放1/6、误拦0/10。两4B峰值都约8.86GiB，只差6.12MiB，中位审计调用约0.50/0.47秒；Style4.30GiB/0.46秒。机械规则候选Neo不代表实际胜过Flash，二者保留同级。buttons-only边界Flash/Neo YES、Style NO，局部遮挡全YES，不当作已成功防御；清晰旧帧新鲜性不可由单图证明，Mirage降低仍null。\n\n'
 '实际input IDs/pixels/grid及54份原始张量CPU重载字节SHA、原始分数概率、三38事件链和567模型postexit文件核对通过；本地539文件/532原终局SHA再核。首轮审计因Flash环境缺pydantic中断已完整保留，仅切到已有Neo环境做同算法CPU审计，0重发。三worker1274315/1279716/1281045与launcher1274128已实查退出；原holder UID1033/fullcmd/start/九锁仍一致、GPU无compute。本目录所有54终局不可重跑；不自动启动任何旧stage/service/gui、attention或UI队列。以下旧头保留历史。\n\n')
assert handoff.read_bytes()==previous
handoff.write_bytes(head.encode('utf8')+previous)
files=[report,H/'README.md',H/'comparison-summary.json',H/'case-results.csv',H/'audit-receipt.json',H/'audit-environment-repair.json',H/'final-resource-inspection.json',H/'delivery-seal.json']
save(publication/'publication.json',{'time':time.time(),'report':str(report),'files':{str(p.relative_to(H)):sha(p) for p in files},'before_handoff_sha256':hashlib.sha256(previous).hexdigest(),'after_handoff_sha256':sha(handoff),'54_calls_complete':True,'original_gui_goal_stays_paused':True,'new_model_calls_by_publication':0})
save(H/'completed-current.json',{'report':str(report),'publication':str(publication),'summary_sha256':sha(H/'comparison-summary.json'),'report_sha256':sha(report),'model_calls':54,'complete_replies':54,'model_failures':0,'GUI_calls':0,'Mirage_reduction':None})
print(json.dumps({'report':str(report),'publication':str(publication),'report_sha256':sha(report),'status':'delivered'}))
