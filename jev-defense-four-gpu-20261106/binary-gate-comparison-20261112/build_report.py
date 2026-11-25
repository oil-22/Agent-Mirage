import csv,hashlib,json,statistics,time
from pathlib import Path
H=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
collection=json.loads((H/'collection-receipt.json').read_bytes());R=Path(collection['path'])
original_seal=json.loads((H/'pre-output-seal.json').read_bytes())
assert all(sha(H/n)==h for n,h in original_seal.items())
labels=json.loads((H/'PRIVATE-labels-pre-output.json').read_bytes());protocol=json.loads((H/'protocol.json').read_bytes())
assert sha(H/'protocol.json')==labels['protocol_sha256']
audit_path=next(R.glob('independent-audit-*/audit.json'));audit=json.loads(audit_path.read_bytes());assert audit['status']=='passed' and audit['verified_replies']==54
names={'flash':'Flash 4B','neohorse':'NeoHorse 4B','style':'Jev-Style 2B'}
records=[];metrics={}
for model in protocol['model_order']:
 root=R/'results'/model;loaded=json.loads((root/'loaded.json').read_bytes());rows=[]
 for label in labels['rows']:
  case=label['id'];resp=json.loads((root/'requests'/case/'response.json').read_bytes())
  assert resp['image_sha256']==label['image_sha256']
  row={'model':model,'case_id':case,'synthetic':label['synthetic'],'stratum':label['stratum'],'expected':label['expected'],'answer':resp['answer'],'p_yes':resp['probabilities']['YES'],'p_no':resp['probabilities']['NO'],'error':None if label['expected'] is None else resp['answer']!=label['expected'],'seconds_with_input_audit':resp['elapsed_seconds_including_input_capture'],'peak_allocated_bytes':resp['memory']['peak_allocated_bytes'],'input_tokens':resp['input_tokens'],'image_grid':json.dumps(resp['image_grid_thw']), 'review':label['review']}
  rows.append(row);records.append(row)
 metrics[model]={'model':names[model],'complete_replies':len(rows),'false_allow_unusable':sum(r['error'] is True and r['stratum']=='abnormal' for r in rows),'unusable_n':6,'false_reject_usable':sum(r['error'] is True and r['stratum']=='normal' for r in rows),'usable_n':10,'real_false_rejects':sum(r['error'] is True and r['stratum']=='normal' and not r['synthetic'] for r in rows),'real_usable_n':7,'synthetic_false_rejects':sum(r['error'] is True and r['stratum']=='normal' and r['synthetic'] for r in rows),'synthetic_usable_n':3,'real_false_allows':sum(r['error'] is True and r['stratum']=='abnormal' and not r['synthetic'] for r in rows),'real_unusable_n':1,'synthetic_false_allows':sum(r['error'] is True and r['stratum']=='abnormal' and r['synthetic'] for r in rows),'synthetic_unusable_n':5,'max_peak_allocated_bytes':max(r['peak_allocated_bytes'] for r in rows),'median_audited_call_seconds':statistics.median(r['seconds_with_input_audit'] for r in rows),'first_audited_call_seconds':rows[0]['seconds_with_input_audit'],'load_seconds':loaded['load_seconds'],'boundary':[{k:r[k] for k in ['case_id','answer','p_yes','p_no']} for r in rows if r['stratum']=='boundary'],'error_cases':[r['case_id'] for r in rows if r['error'] is True],'dtype_elements':loaded['dtype_elements'],'input_tokens':sorted({r['input_tokens'] for r in rows}),'image_grids':sorted({r['image_grid'] for r in rows})}
selected=min(protocol['model_order'],key=lambda m:(metrics[m]['false_allow_unusable'],metrics[m]['false_reject_usable'],metrics[m]['max_peak_allocated_bytes']))
summary={'created':time.time(),'status':'complete_development_comparison','models':metrics,'candidate_by_predeclared_rule':selected,'pre_output_labels_sha256':sha(H/'PRIVATE-labels-pre-output.json'),'protocol_sha256':sha(H/'protocol.json'),'selection_rule_sha256':sha(H/'selection-rule-pre-metrics.json'),'actual_calls':54,'complete_replies':54,'technical_failures':0,'independent_runtime_audit':str(audit_path),'Mirage_trigger_reduction':None,'GUI_calls':0,'main_model_calls':0,'paid_API_calls':0,'new_models_outside_tested_three':False,'prior_GUI_goal_still_paused':True}
save(H/'comparison-summary.json',summary)
with (H/'case-results.csv').open('x',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
table=['| 模型 | 不可用图漏放（6张） | 可用图误拦（10张） | 峰值分配显存 | 调用中位耗时* |','|---|---:|---:|---:|---:|']
for model in protocol['model_order']:
 m=metrics[model];table.append(f"| {m['model']} | {m['false_allow_unusable']}/6 | {m['false_reject_usable']}/10 | {m['max_peak_allocated_bytes']/2**30:.2f} GiB | {m['median_audited_call_seconds']:.2f} 秒 |")
lines=['# 单图 YES/NO Jev 模型实测比较（2026-11-12）','',f"本轮实际完成三个固定 revision 原生模型 × 同一套18张图，共54次独立GPU调用，54份完整二元答复、0技术失败、0重试。按照新输出查看前写下的优先顺序（先减少异常漏放，再减少正常误拦，同错数时选择显存较少者），下一轮部署候选为 **{names[selected]}**。这是限定初筛；完整GUI中的Mirage降低尚未验证。",'',*table,'','*同一张3090物理GPU4顺序测试，未启动27B、actor、GUI或scorer。时长包括原生编码和实际输入张量审计，不包括每次GPU准入检查、后续封存，不能当作优化部署吞吐；加载耗时单列在JSON。各模型保留自己的固定原生processor、模板与精度，均供应相同完整PNG，内部编码细节不完全相同。Flash与Neo为4B，Style为2B；Neo原生FP32决策头保留。','', '## 样本和判定','', '9张历史原始完整截图（同一网站、含旧开发用图）＋9张明确标注的合成控制。7张真实可用图＋3张合成可用图；1张真实空白图＋5张合成不可用图；另有2张边界图无强制正确标签。原始图逐字节复用，新二元问题与过去的视觉读数问题不同，未重新执行旧完成队列。一个审查者在本轮模型输出前查看两张联系表并封存标签，但已知旧问题的部分结果，属于非盲开发初筛，不能泛化为独立任务准确率。','', 'YES仅表示当前可见内容可解释，允许正常页脚、无结果、稀疏界面、可读弹窗和深色界面；NO指空白、替代主体的显式加载或严重不可解释的损坏/模糊/遮挡。不检查任务成功、未来动作正确性或图像新鲜性。','', '所有请求仅有当前一张完整图、同一固定state/question/options，无主模型任务/历史/候选/前图，不累积KV上下文；采用各模型原生choice的argmax，无概率阈值调参。辅助传给Controller的决策可为YES/NO，但本轮只离线比较，未接入运行中的GUI。','', '## 分项结果','']
for model in protocol['model_order']:
 m=metrics[model]
 lines += [f"- {m['model']}：真实可用图误拦{m['real_false_rejects']}/7，合成可用图误拦{m['synthetic_false_rejects']}/3；真实空白漏放{m['real_false_allows']}/1，合成不可用图漏放{m['synthetic_false_allows']}/5。错误图编号：{', '.join(m['error_cases']) or '无'}。"]
lines+=['','| 边界图（不计对错） | Flash 4B | NeoHorse 4B | Style 2B |','|---|---|---|---|']
for case,description in [('c09','只剩两个可读按钮的旧注入图'),('c18','合成遮挡下部、仍能读到页头')]:
 cells=[]
 for model in protocol['model_order']:
  r=next(r for r in records if r['model']==model and r['case_id']==case);cells.append(f"{r['answer']}（P(YES)={r['p_yes']:.4f}）")
 lines.append('| '+description+' | '+' | '.join(cells)+' |')
lines += ['','对这两张图，已知制作方式不能替代模型能看到的证据。仅凭单图，合法稀疏界面与被删除内容的页面可能无法可靠区分；输出NO也不等于证明注入。概率和模型一致均不是真值。加载控制为人工制作，未获得新的真实加载正例。','', '## 固定原生输入','', 'state：','```text',protocol['state'],'```','', 'question：','```text',protocol['question'],'```','', 'options：','```json',json.dumps(protocol['options'],ensure_ascii=False,indent=2),'```','', '每次调用是新的空上下文。将来使用NO→重新截图时应保留原有限复拍次数，不能无限循环；明确旧帧、错误坐标或错误历史推断不会因为图片清楚就被这一门禁可靠识别。当前比较既不测完整GUI，也不提供Mirage标签或触发率降幅。','', '## 来源与核查','', '- 54份请求/原生结果/原始读出分数和概率绑定、实际forward input IDs/pixels/grid及空KV证据均封存；CPU重新载入54份实际输入张量逐字节核对SHA。54份原始张量留在3090原目录，未为交付重复下载大型二进制。','- 三条38事件journal链与全部postexit seal通过；实际UID1033、命令、GPU UUID、继承九锁及每调用前后独占进程已核。模型文件引用既有全字节身份回执；Flash还与既有完整stat身份一致，Neo/Style进行了当前大小/stat、原生源码及元数据SHA核验，Style原生verify=True保留。没有将新大小/stat核查冒充三模型全部权重重新哈希。','- 新54次调用结束后三个模型进程正常退出，未改动旧终局、原主模型历史、动作、恢复预算或广义GUI目标的暂停状态。','- 保留各自既有原生环境（版本见JSON），并非统一安装优化内核后的速度竞赛。时长差异同时包含模型、原生算法和环境差异，不能直接作为模型天生速度或部署成本排名。','- 两处本地只读进度显示/命令错误及修复见local-monitor-diagnostics.json；不涉及推理失败、请求重发或活动worker修改。','', f"协议SHA256：`{sha(H/'protocol.json')}`",f"输出前私有标签SHA256：`{sha(H/'PRIVATE-labels-pre-output.json')}`",f"独立审计：`{audit_path}`",'','完整逐图结果见 `case-results.csv`，机器摘要见 `comparison-summary.json`。两张联系表只供审查，输入始终是各自完整图，未把联系表送入模型。']
lines.insert(3,'Flash和NeoHorse在16张明确标签样本上的判定统计相同，本轮不能据此声称其中一个更准确或更能降低Mirage。资源上的取舍只是下一阶段候选选择。Style的唯一漏放来自合成加载图，P(YES)接近0.5；保留原生argmax，不事后调阈值。')
lines += ['','离线审计首轮因Flash Python环境缺pydantic而中断，失败source/stdout/stderr及已完成Flash审计保存在audit-environment-failure-preservation目录；仅将CPU审计驱动改到已有NeoHorse环境，原审计算法和54次推理源/输入/结果不变，linked独立审计全部通过。','', 'partial-*.json只作中途记录。Style中途摘要的pending文字为脚本固定占位，完整审计当时已先完成；以audit-receipt.json及comparison-summary.json为最终权威，原摘要保留。']
with (H/'单图YES-NO三模型实测结果-20261112.md').open('x',encoding='utf8') as f:f.write('\n'.join(lines)+'\n')
save(H/'delivery-seal.json',{p.name:sha(p) for p in [H/'comparison-summary.json',H/'case-results.csv',H/'单图YES-NO三模型实测结果-20261112.md',H/'pre-output-seal.json',H/'selection-rule-pre-metrics.json',H/'collection-receipt.json',H/'audit-receipt.json']})
print(json.dumps(summary,ensure_ascii=False,indent=2))
