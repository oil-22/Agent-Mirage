import json,pathlib
R=pathlib.Path(__file__).parent;A=R/'analysis'
def read(n):return json.loads((A/n).read_text(encoding='utf-8'))
terminal=read('terminal-audit.json');diag=read('analysis-diagnostics.json');paired=read('paired-summary.json');sem=read('semantic-counts.json');sp=read('semantic-paired-effects.json');source=read('source-comparisons.json');sa=read('source-attention-summary.json')
models=['qwen27','qwen9','glm'];names={'qwen27':'Qwen27（原部署名 Qwen3.8-27B）','qwen9':'Qwen3.5-9B','glm':'GLM-4.6V-Flash'}
def fmt(e,scale=100):
 if e is None:return '不可估计'
 return f"{e['mean']*scale:+.2f} [{e['ci95'][0]*scale:+.2f}, {e['ci95'][1]*scale:+.2f}]"
def effect(ds,m,h,c,metric,factor='stage',comparison='late-early'):
 return next(x['estimate'] for x in paired['effects'] if (x['dataset'],x['model'],x['history'],x['condition'],x['metric'],x['factor'],x['comparison'])==(ds,m,h,c,metric,factor,comparison))
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(c) for c in row)+' |' for row in rows])
def safmt(x,scale):return '{:.3f} (n={})'.format(x['estimate']['mean']*scale,x['estimate']['n_tasks'])
status='全部计划配置已完成并通过终局审计' if terminal['all_expected_complete'] else '阶段性结果：仍有计划配置未完成，暂不作为最终交付'
s=[f'# 四类注意力实验：多轨迹扩展结果（2026-11-02）\n\n{status}。新增已采集 {terminal["logical_completed"]}/1,728 个逻辑配置；失败与审计错误 {sum(len(x["failed"]) for x in terminal["batches"])} / {len(terminal["errors"])}。\n',
'## 已扩展的范围\n',
table(['实验','扩展单位与设计','新增逻辑配置（三模型合计）'],[
['历史窗口','新增 10 个 OSWorld 任务 UUID；无历史／最近两轮／完整历史，原九任务复用后共十九任务','与时机共同构成 1,080'],
['四种注入','新十任务同前缀的白屏／缺图／上一帧／控件区域遮罩，正常图为第五个配对条件','另加 270 遮罩，与主批组成 1,350 个五条件配置'],
['注入早中晚','每轨迹决策索引 10%／50%／90%，三位置与三历史窗口完全交叉','包含在主批'],
['后续动作读取来源','14 条不同 VWA 任务；源句原样／撤回为不确定／等价改写；后续间隔 1／3／6 决策','378']]),
'\n新增推理全部在 3090 执行。原始十月三十一日实验保留并复用，没有整批重跑。十九任务的四基础条件共 2,052 个配置；加上新十任务的遮罩共 2,322。十四条来源轨迹按任务计数，不能将四十二个后续快照称为四十二条独立轨迹。旧两例来源分析保留为单独证据。\n\n模型命名依据实际部署：27B 路径虽为 Qwen3.8-27B，其 config.json 声明 model_type=qwen3_5、architectures=Qwen3_5ForConditionalGeneration。本报告标作 Qwen27 并保留原部署名，不将目录名视为已核实的官方版本。GLM 使用用户确认的 GLM-4.6V-Flash 本地权重。配置与运行环境摘要已存档。\n',
'## 1. 早、中、晚已明确区分\n\n这里的“晚期”是归档轨迹的时间位置，不能解读为任务语义上接近成功。部分干净对照轨迹也有重复动作或未完成任务。首 query 为最后一个输入位置对第一个输出 token 的注意力，避免回复长度和生成前缀质量变化干扰。\n\n正常图片条件下，下面列出晚期减早期的图片注意力变化，单位为百分点；方括号为 95% 任务 bootstrap 区间。\n',
table(['模型','新十任务：无历史','新十任务：最近两轮','新十任务：完整历史','合并十九任务：完整历史'],[[names[m]]+[fmt(effect('new10',m,h,'current_control','first_image')) for h in ['none','last2','full']]+[fmt(effect('merged19',m,'full','current_control','first_image'))] for m in models]),
'\n完整历史下，十九任务中晚期图片份额低于早期的任务数：'+ '；'.join(names[m]+' '+str(sum(v<0 for v in effect('merged19',m,'full','current_control','first_image')['task_values'].values()))+'/19' for m in models)+'。\n',
'\n完整历史下，新集与合并集均出现晚期图片份额下降；固定短历史窗口后的变化较弱。这与历史竞争／位置效应相容，但历史窗口同时改变内容与长度，图片和任务状态也随轨迹变化，不能归因为纯长度造成。首 query 与动作 query、图片总份额与每 token 密度都保留在分析表中。\n\n![早中晚复制](figures/01_timing_replication.png)\n',
'## 2. 四注入严格配对与遮罩版本\n\n新十任务每个位置／历史窗口均有正常、白屏、缺图、上一实际帧、控件区域遮罩五个条件。下表为完整历史下，各注入相对正常图的首 query 历史条件份额 H/(1−I) 差值；先在任务内平均三个时点，再按任务重采样。H 是历史助手文字与动作，I 是本次提供的截图。\n',
table(['模型','白屏−正常','缺图−正常','上一帧−正常','控件区域 v2−正常'],[[names[m]]+[fmt(effect('new10_five',m,'full',c,'first_history_nonimage','injection',c+'-current_control')) for c in ['blank_replace','silent_drop','stale_replace','buttons_only']] for m in models]),
'\n9B 在白屏条件下的图像首 query 份额反而高于正常图：'+fmt(effect('new10_five','qwen9','full','blank_replace','first_image','injection','blank_replace-current_control'))+' 个百分点。这说明高图像注意力本身不等于读取了有效视觉证据或正确理解图片。\n',
'\n缺图的图片注意力是结构性零，不能用这个零单独证明模型忽视视觉。H/(1−I) 与历史每 token 密度用于补充检查归一化分母变化。上一帧与当前帧的像素差异见 pixel-audit.json；像素完全相同的快照也保留并披露。\n\n新版 visible-control-regions-v2 是预先人工式矩形标注：保留工具栏、侧栏控件、dock 与对话框表单的原像素，其他位置纯白；不是精确按钮分割。控件框可含文字和值。30 张源图／遮罩均经助手视觉核查，修订的三张已再次核查。新集相对旧四注入 39 任务集净增 8 个任务 UUID，另 2 个为重叠任务的新快照。旧原生网页遮罩版本未与新版直接混合估计。\n\n![四注入注意力差](figures/02_four_injections.png)\n',
'## 3. 历史长度与触发：没有统一的单调关系\n\n新增主批白屏／缺图共 540 个逻辑输出、420 个不同的“条件＋文本”已逐项做助手语义复核。区分无依据的当前状态断言、明确条件假设、只输出动作、承认无法观察，以及含糊的历史回述。这里统计的是缺少当前图像依据的断言，未逐一证明环境真值相反，也不是独立人工盲标，不能直接称 Mirage 发生率。达到生成上限的回复不进入完整回复分母。\n',
table(['模型','注入','无历史','最近两轮','完整历史'],[[names[m],{'blank_replace':'白屏','silent_drop':'缺图'}[c]]+[next(f"{x['unsupported']}/{x['complete_reply_n']}" for x in sem if (x['dataset'],x['model'],x['condition'],x['history'],x['stage'])==('new10',m,c,h,'all')) for h in ['none','last2','full']] for m in models for c in ['blank_replace','silent_drop']]),
'\n缺图下“完整历史减无历史”的任务内配对断言率变化（百分点；三个时点均完整才纳入）：\n',
table(['模型','配对变化 [95% CI]','纳入任务数'],[[names[m],fmt(e),e['n_tasks'] if e else 0] for m in models for e in [next(x['estimate'] for x in sp if (x['dataset'],x['model'],x['condition'],x['comparison'])==('new10',m,'silent_drop','full-none'))]]),
'\n不能写成“历史越长就越容易触发 Mirage”。例如 9B 在缺图无历史时常承认无法观察，增加历史后出现更多具体断言；27B 与 GLM 的扩展集不呈同一方向。注意力变化与行为断言应分别呈现，相关性本身也不是因果机制。\n\n![行为语义描述](figures/03_semantic_descriptive.png)\n',
'## 4. 后续动作对来源的读取与文字干预\n\n十四条来源均为原 27B 缺图 step 2 的真实归档回复，后续三个请求使用固定历史与真实截图，跨三模型重放。源句截图核查：3 条与截图矛盾（classifieds_109、classifieds_231、classifieds_232），8 条得到截图支持，3 条无法可靠确认输入框焦点。支持组是对照；不能将十四条都称为 Mirage 阳性。\n\n撤回条件把源句改为“无法确认”，不是注入正确环境状态；sham 保持原断言意思。全部三模型原生完整请求 token 长度一致，只改指定源句；历史动作、截图与其顺序不变。源句的精确 token mask 与实际 GPU 输入逐项比对，避免把整个来源轮次注意力当作该断言的注意力。\n',
table(['模型','来源组','可比较三条件快照','撤回改变动作','等价改写改变动作','仅撤回改变动作'],[[names[x['model']],{'all':'全部14任务','contradicted_by_capture':'截图矛盾3任务','supported_by_capture':'截图支持8任务','visually_unresolved':'无法确认3任务'}[x['grounding']],x['jointly_comparable'],x['withdrawn_changed'],x['sham_changed'],x['withdrawn_only']] for x in source['summary']]),
'\n按任务聚合的“撤回改变动作比例−sham 改变动作比例”（百分点）如下；区间跨零表示当前数据不足以区分两种文字修改的平均效应，绝不表示证明没有影响。\n',
table(['模型','撤回−sham [95% CI]','可比较任务数'],[[names[x['model']],fmt(x['task_paired_withdrawn_minus_sham']),x['task_paired_withdrawn_minus_sham']['n_tasks'] if x['task_paired_withdrawn_minus_sham'] else 0] for x in source['summary'] if x['grounding']=='all']),
'\n在截图确认矛盾的三个来源任务中，三模型的“仅撤回改变动作”均为 0/9 个后续快照。现有样本没有提供撤回错误来源所独有的动作变化证据，更不能称为修复；这个结果也不能排除来源沿固定后续历史传播而被间接保留。扩展后的来源实验应作为限制机制结论的对照证据呈现。\n',
'\n动作差异只在三个条件都有可解析单一动作且回复完整时比较；不可比较项从分母排除，没有填零。主表对 JSON 的 x/y/coordinate(s)/position 数值字符串做透明格式归一化，原始动作及 schema 违规另存。坐标偏差 1 像素也属于动作改变，因此“仅撤回改变”仍不等于纠错或任务恢复。sham 本身造成的动作变化用于检验措辞敏感性。\n\n源句之后的归档回复和动作全部固定，其中可能已重复或传播原断言。因此这测量的是给定后续历史时编辑早先一句话的局部敏感性，不是重新生成历史后的传播总效应。后续重复内容可能稀释源句撤回的影响。\n\n原样条件下，十四任务的精确源句注意力均值（百分比）及相对“同一来源轮次其余解释文字”的每 token 密度比（倍数）：\n',
table(['模型','源句质量：间隔1／3／6','密度比：间隔1／3／6'],[[names[m]]+[' / '.join(next((safmt(x,scale) for x in sa if (x['model'],x['grounding'],x['condition'],x['gap'],x['metric'])==(m,'all','original',gap,metric) and x['estimate']),'不可估计') for gap in [1,3,6]) for metric,scale in [('action_claim_mass',100),('action_claim_enrichment',1)]] for m in models]),
'\nsoftmax 权重通常本来就非零，因此非零注意力不等于该句具有决定性因果作用。密度比提供组长度对照，但未消除位置和语义差异。原句的后续动作 query 注意力及每 token 密度如下。每条线以可用任务为单位求均值，来源矛盾组只有三任务；缺少动作解析的分母可能随时点不同，详见 source-enriched-results.json。\n\n![来源读取](figures/04_source_attention.png)\n',
'## 核验与可复现文件\n',
table(['批次','模型','计划／完成','精确请求复用','截断'],[[x['cohort'],names[x['model']],f"{x['expected']} / {x['logical_completed']}",x['reused'],len(x['truncated'])] for x in terminal['batches']]),
f'\n三模型×三批各以两个真实请求检验采集开关：完整输出 token IDs 相同，逐步完整 logits 最大差 0。实际注意力张量通过有限性、质量守恒、输入分组、请求与文件 SHA 核验。来源 CPU 输入实际一致 {terminal["source_cpu_matches_actual"]}/378；配对修改范围审计 {terminal["source_pairs_audited"]}/252。\n',
'\n预设 2,048 输出 token 上限没有根据结果延长。截断名单：\n',
table(['模型','批次','配置 ID','输出 tokens'],[[x['model'],x['cohort'],x['id'],x['output_tokens']] for x in diag['new_censored']]),
'\n所有置信区间为探索性的任务 bootstrap（10,000 次），未做多重检验校正；样本是有限归档中的可恢复任务，非总体随机样本。注意力仅覆盖语言模型标准 softmax full-attention 层与 query heads；Qwen 的线性混合层、视觉编码器未包含，不进行架构之间注意力大小的直接排名。\n\n本地 analysis/ 保存原始导出、配对效应、语义标签联表、来源分层比较与终局审计；figures/ 每图提供 PNG、PDF、SVG。大体积逐 query×层×头 NPZ 留存于 3090:/home/researcher/attention-20261102/，每项文件 SHA 可由 measurements.json 回溯。\n',
'## 论文中可采用的结论与下一步\n\n可以写：多轨迹复制支持完整历史下的晚期视觉份额下降；四种观测破坏造成的注意力重分配具有模型与条件差异；后续动作生成会读取早先的精确状态句，来源文字替换和等价改写提供了措辞敏感性对照。不要把可读取或动作变化直接写成错误来源导致失败。\n\n最值得补充的是：① 对白屏／缺图断言做独立双人、盲于模型和条件的真值标注；② 增加真正与截图矛盾的来源任务，当前只有三条；③ 固定同一截图与请求，在语义匹配的历史内容中独立改变 token 长度，进一步区分长度、内容与时间位置；④ 在离线文字干预之外执行成对环境回放，测下一动作正确性及最终任务恢复。前两项优先于继续堆叠更多同一轨迹快照；若要声称注意力机制因果，还需来源 token 的消融／激活干预及等强度 sham。\n']
report='\n'.join(s).replace('后续动作生成会读取早先的精确状态句','后续动作 query 对早先的精确状态句分配注意力').replace('不要把可读取或动作变化直接写成错误来源导致失败','不要把非零注意力或动作变化直接写成错误来源导致失败')
report=report.replace('softmax 权重通常本来就非零','动作注意力根据唯一候选动作文本块定位，块内代码可能有 schema 或语法问题；动作改变率另要求能解析出单一动作，所以两者分母可以不同。\n\nsoftmax 权重通常本来就非零')
(R/'多轨迹扩展实验报告.md').write_text(report,encoding='utf-8')
print(status)
