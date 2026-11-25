import collections,json,pathlib
root=pathlib.Path(__file__).parent;data=root/'analysis'
terminal=json.loads((data/'terminal-audit.json').read_text(encoding='utf-8'))['batches']
assert len(terminal)==5 and all(r['status'].get('phase')=='finished' and r['logical_completed']==r['expected'] for r in terminal),'Batches are not all complete'
summary=json.loads((data/'paired-summary.json').read_text(encoding='utf-8'));agg=summary['aggregates'];effects=summary['effects'];names={'qwen27':'原部署 27B','qwen9':'Qwen3.5-9B','glm':'GLM-4.6V-Flash'}
models=list(names);conditions=['current_control','blank_replace','silent_drop','stale_replace'];cn={'current_control':'正常图','blank_replace':'白屏','silent_drop':'缺图','stale_replace':'上一帧'}
def match(rows,**filters):return next(r for r in rows if all(r.get(k)==v for k,v in filters.items()))
def fmt(e,ci=True):
    if e is None:return 'N/A'
    return f"{e['mean']*100:+.2f} [{e['ci95'][0]*100:+.2f}, {e['ci95'][1]*100:+.2f}]；n={e['n_tasks']}" if ci else f"{e['mean']*100:.2f}"
def table(header,rows):return '\n'.join(['| '+' | '.join(header)+' |','|'+'|'.join(['---']*len(header))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])
runtime_table=table(['批次','完成逻辑配置','不同完整请求','完整单回复／截断','相同请求复用'],[[names[r['model'].replace('source-','')]+('：跨轮来源' if r['model'].startswith('source-') else '：时机×窗口'),r['logical_completed'],r['unique_requests'],f"{r['single_reply_eos']} / {len(r['single_reply_truncated_ids'])}",r['reused']] for r in terminal])
timing=[]
for model in models:
    for history in ['full','last2','none']:
        means=[fmt(match(agg,model=model,stage=s,history=history,condition='current_control',metric='first_image')['estimate'],False) for s in ['early','middle','late']]
        e=match(effects,model=model,factor='stage',comparison='late-early',history=history,condition='current_control',metric='first_image')['estimate']
        timing.append([names[model],{'full':'完整','last2':'最近两轮','none':'无'}[history],*means,fmt(e)])
timing_table=table(['模型','历史窗口','早期 %','中期 %','后期 %','后期−早期（百分点、95%区间）'],timing)
history=[]
for model in models:
    history.append([names[model]]+[fmt(match(effects,model=model,factor='history_window',comparison='full-last2',stage='late',condition=c,metric='first_image')['estimate']) for c in ['current_control','blank_replace','stale_replace']])
history_table=table(['模型','正常图','白屏','上一帧'],history)
interactions=[]
for model in models:
    interactions.append([names[model]]+[fmt(match(effects,model=model,factor='stage_by_injection',comparison='late-early',history='last2',condition=c,metric='first_image')['estimate']) for c in ['blank_replace','stale_replace']])
interaction_table=table(['模型','白屏额外时机差值','上一帧额外时机差值'],interactions)
reviews=json.loads((data/'semantic-reviewed.json').read_text(encoding='utf-8'));review_rows=[]
for model in models:
    rr=[r for r in reviews if r['model']==model];reviewed=[r for r in rr if r['semantic_review'] is not None]
    counts=collections.Counter()
    for r in reviewed:
        label=r['semantic_review'];counts['claim']+=label['unsupported_current_state_assertion'] is True;counts['uncertain']+=label['unsupported_current_state_assertion'] is None
        counts['recognizes']+=label['recognizes_invalid_observation'] is True
        counts['recognizes_nonterminal']+=label['recognizes_invalid_observation'] is True and r['action_kind'] not in ['wait','done','fail','unknown']
        counts['unparsed']+=r['action_intent'] is None
    review_rows.append([names[model],f'{len(reviewed)}/{len(rr)}',counts['claim'],counts['uncertain'],counts['recognizes'],counts['recognizes_nonterminal'],counts['unparsed']])
review_table=table(['模型','已复核／白屏缺图配置','无依据当前断言','断言含糊','明确识别异常','识别后仍提出非终止动作','无单一可比动作'],review_rows)
def claim_count(model,condition,**filters):
    rr=[r for r in reviews if r['model']==model and r['condition']==condition and all(r.get(k)==v for k,v in filters.items())]
    positive=sum(r['semantic_review'] is not None and r['semantic_review']['unsupported_current_state_assertion'] is True for r in rr)
    uncertain=sum(r['semantic_review'] is not None and r['semantic_review']['unsupported_current_state_assertion'] is None for r in rr)
    return f'{positive}/{len(rr)}'+(f'（另{uncertain}含糊）' if uncertain else '')
window_claim_table=table(['模型','条件','无历史','最近两轮','完整历史'],[[names[m],cn[c]]+[claim_count(m,c,history=h) for h in ['none','last2','full']] for m in models for c in ['blank_replace','silent_drop']])
stage_claim_table=table(['模型','条件：完整历史','早期','中期','后期'],[[names[m],cn[c]]+[claim_count(m,c,history='full',stage=s) for s in ['early','middle','late']] for m in models for c in ['blank_replace','silent_drop']])
source=json.loads((data/'source-comparisons.json').read_text(encoding='utf-8'));sa=json.loads((data/'source-input-audit.json').read_text(encoding='utf-8'))
source_table=table(['模型','归档案例','快照数','状态纠正：动作改变／可比','等价改写：动作改变／可比','仅纠正改变、改写未变'],[[names[r['model']],r['app'],r['snapshots'],f"{r['correction_changed']}/{r['correction_comparable']}",f"{r['sham_changed']}/{r['sham_comparable']}",r['correction_only_changed']] for r in source['summary']])
diag=json.loads((data/'analysis-diagnostics.json').read_text(encoding='utf-8'))
calibration=json.loads((root/'glm-async-validation.json').read_text(encoding='utf-8')) if (root/'glm-async-validation.json').exists() else {}
maxdiff=max(calibration.get('async_max_absolute_differences',{'none':0}).values())
text=f'''# 注意力实验结果与论文建议（2026-10-31）

**原来的三模型配对实验确实没有系统区分注入早／中／晚：主要固定在第 2 步。本次已补上“轨迹时机×可见历史窗口”的三模型离线实验，并复用已有四注入实验。** GLM 按用户确认使用 GLM-4.6V-Flash。

## 1. 完成范围与复用

{runtime_table}

本次时机×窗口共 972 个逻辑配置，另为 9B、GLM 补 66 个跨轮来源配置。相同完整请求的复用不是独立实验。技术失败、单回复截断及预检明细见 `analysis/terminal-audit.json`。原始逐 query×层×头张量保留在 `3090:/home/researcher/attention-20261031/`；本地有计划、原始结果汇总、复核标签、数值与 PNG/PDF/SVG 图。

四注入旧实验不重复：三模型均有 **39 任务×5 条件的 195 条严格配对配置**（OSWorld 19、AndroidWorld 20）。另有不平衡归档观察；总有效配置分别为 389、387、390。恢复依据见 [原27B及跨模型报告](D:/MultiModel/attention-audit-20261031/current-reports/8.md) 和 `evidence-bundle.json`。原完整归档位于 `4090:/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz`，本次未改动。

| 原四注入：相对正常图的历史注意力变化（百分点） | 原部署 27B | 9B | GLM |
|---|---:|---:|---:|
| 缺图 | +9.33 | +5.11 | +3.59 |
| 白屏 | −0.58 | +0.77 | +1.19 |
| 旧帧 | +4.99 | +7.42 | +1.11 |
| 仅按钮 | +0.96 | −2.56 | +0.55 |

这些旧结果按完整自然回复平均；与本次首 query 数值不是同一个指标。它们不支持“四种注入都通过相同的历史依赖机制触发 Mirage”。

## 2. 前中后怎样区分

在未注入的原 27B control 轨迹中，按应用、任务 UUID 选择 9 个任务、5 类应用；每条至少 15 个决策。执行前冻结决策索引 10%／50%／90% 分位为早／中／晚。多数 50 步轨迹对应第 6／25／45 次请求，一条 23 步轨迹为第 3／12／21 次。这里是**轨迹时间位置**，不代表任务语义上完成了 10%／50%／90%。部分原轨迹存在重复与循环；“干净前缀”仅指未注入，不保证历史中的每项状态判断都正确。

每个位置交叉比较无历史、最近两轮、完整历史，以及正常图、白屏、缺图、上一实际帧。历史窗口是文本窗口，旧历史截图未保留；主批正常／白屏／旧帧各只有一张当前交付图，缺图没有图像。三模型共享归档未注入前缀，使用各自原生模板与图像处理。没有同状态的原生按钮遮罩，故新时机实验不包含“仅按钮”；不能声称它已覆盖四种注入的全部时机交互。

27 个同源快照中，{diag['stale_snapshots_pixel_identical']} 个快照的上一帧与当前帧像素完全相同，已单列为同输入对照，不能称为有效过时状态。完整时机比较仍按相同 9 任务配对；全部逐配置像素差异见 `analysis/measurements.csv`。

## 3. 时机与图像注意力

主展示**预测本轮第一个输出 token 的 query**，它尚未读取本轮生成前缀，较少受回复长度影响。以下为正常图条件：

{timing_table}

**核心结果：完整历史下，两个 Qwen 的后期−早期差值分别为 −6.34、−3.09 个百分点，区间均低于零；GLM 的区间跨零。固定最近两轮后，三模型的早晚差值区间全部跨零。** 当前 9 个任务因此尚不支持独立于历史窗口的统一“越晚越忽略图片”效应；这也不等于证明没有时机效应，更不是 Mirage 触发率结论。

![时机与图像注意力](D:/MultiModel/attention-audit-20261031/figures/01_timing_image_attention.png)

注意“完整历史”的阶段差值同时包含历史增长、历史内容和画面变化。最近两轮与无历史用于诊断这一混淆，依然不能完全隔离任务状态与图像内容。不能只挑完整历史曲线下降来证明“越晚注入越容易触发 Mirage”。

最近两轮历史下，注入影响在后期相对早期的额外变化，定义为 **[注入−正常图]后期 − [注入−正常图]早期**，图像注意力单位为百分点：

{interaction_table}

这些是探索性按任务配对结果，每项 10,000 次任务 bootstrap；多重比较未校正。任务数小，区间不是总体或确认性机制结论。缺图条件图像注意力份额为结构性零，不能解释为主动忽略图片。

## 4. 历史窗口影响

同一个后期快照，完整历史相对最近两轮的首 query 图像注意力差值：

{history_table}

![历史来源注意力](D:/MultiModel/attention-audit-20261031/figures/02_timing_history_attention.png)

图中 H 是历史叙述与动作的注意力份额，I 是交付图像的注意力份额；H/(1−I) 每个案例先计算再按任务平均，不能拿总体均值事后相除。每 token 密度、动作 query 均值和逐层／头数据分别保存在 `measurements.json` 与 `query-measurements.json`。动作 query 指预测动作文本的 token 位置；不能误称它们是外部动作执行后的注意力。

**此实验测量可见历史窗口影响，不能命名为纯历史长度因果效应。** 截断历史同时改变相关事实、先前动作与文字数量；不同模型的 tokenizer 和图像 token 数也不同，不用注意力绝对大小给模型排 Mirage 严重程度。

## 5. 输出语义复核

对白屏、缺图输出按“条件+完整单回复文本”去重复核，再映射回配置。以下是助手的语义审查，**不是独立人工盲标，也不是最终 Mirage 触发率**。

{review_table}

为直接对应“历史窗口”和“注入时机”，下面单列显式无依据当前断言的配置数，含糊项不放进分子。每个历史窗口的分母 27 是 9 任务×3 位置；各位置完整历史的分母 9 是同一组任务。

{window_claim_table}

{stage_claim_table}

“无依据当前断言”指在当前视觉证据不可用时仍明确声称具体界面状态或任务已完成；它不自动证明实际环境中的该事实为假。明确回顾历史、表达假设、说明不确定性与盲点坐标动作分别记录。仅输出 DONE/FAIL 也与显式状态断言分开；WAIT 不因注意力低而判 Mirage。上述维度允许重叠，每模型 162 配置来自 9 任务的重复快照，不能当作 162 个独立任务。

一个重要区别是“已经识别白屏，但仍提出点击／快捷键”，与“没有承认证据失效，仍声称看见具体控件”不同。完整输出、动作结构、执行格式是否匹配、复核理由及含糊标签见 `analysis/semantic-reviewed.json`；与逐配置注意力联接的表为 `semantic-attention.csv`。JSON、裸函数、GLM box、伪 WAIT 调用和多语句输出保留原格式，不把它们都当作已执行的有效动作。

## 6. 后续动作读取最初来源

27B 原有两个来源追踪案例已复用：WebMall Find Task8 的 step 9 将白图写成 CamelCases“无结果”；VWA classifieds_177 的 step 10 在菜单已关闭时仍称打开。VWA 更早的 step 2 白图仅 WAIT，未证明它造成 step 10 以后的循环。

9B、GLM 本次补测 WebMall 后续 7 个、VWA 后续 4 个快照。每个快照原样、只纠正初始来源状态、同来源位置语义等价改写三条件，固定所有历史动作与后续截图。WebMall 只把源 step 9 的 no results 改为 unknown results，两份重复状态记录均编辑；sham 将 blank 改为 white。VWA 只改源 step 10 的 open→closed；sham 将 The→This，未把之前有依据的 open 全改为错误。

原生输入审计：共 {len(sa)} 对；等 token 长度 {sum(a['equal_native_token_length'] for a in sa)} 对，全部 token 差异位于目标断言 {sum(a['all_token_changes_inside_source_claim'] for a in sa)} 对，图像顺序与字节不变 {sum(a['image_order_and_bytes_unchanged'] for a in sa)} 对，历史动作文本不变 {sum(a['historical_action_blocks_unchanged'] for a in sa)} 对。详细差异见 `analysis/source-input-audit.json`。VWA 归档提示从保存的真实输入 IDs 精确 decode/reencode 后恢复，证明见 `source-campaign/reconstruction-audit.json`。

{source_table}

动作比较按可解析的动作意图与字面参数规范化，保留格式异常；没有单一可比动作的项不按“未变化”填零。变化也可能只是另一个无效动作，不能自动当作纠正成功。

逐回复核对提供了三个具体边界。9B 在 WebMall step 30 的原样与等价改写回复仍记住 CamelCases“无结果”，并导航到 8085；来源状态干预后改称“结果未知”，转而访问先前的 8081 商品链接。这里将 no results 改为 unknown results 是撤回无依据结论，并未补入真实搜索结果；改变后的动作也不是回访 CamelCases。GLM 同快照从搜索框 fill 改为 click('141')，尚无环境执行结果证明更有效。GLM step 45 的来源状态干预和等价改写都移除了商品 URL 尾部的 /###，因此该项不是来源状态纠正特有的变化。

相反，VWA step 11 两个模型在三条件下均逐字输出“The dropdown is open”，并提出相同坐标点击；源句注意力虽改变，状态描述与动作都未随之改变。它说明“读取源句的注意力变化”与“动作变化”需要分别呈现，不能将前者直接当成行为因果效应。

![后续动作读取源断言](D:/MultiModel/attention-audit-20261031/figures/03_source_claim_action_attention.png)

采集分别追踪最初源轮叙述、源轮动作和精确源断言；精确断言是源轮叙述的子集，不能把三个通道相加。图展示动作 query 对精确断言的注意力份额，各子图独立对数纵轴。原 27B 旧案例中，step 44 预测 no results 对源错误句约 5.75%，随后 fill/click 仅约 0.09%／0.07%，不能描述为每个后续动作始终高度读取同一句话。旧数据的选词口径不同，未与新 action-query 均值混成模型排名。

这两个案例是先前挑选的阳性案例，多个后续快照相关，不估总体效应或显著性。新模型读取的是原 27B 历史，尚不是自身自然产生的完整 Mirage 轨迹。只纠正最初源句时，后面已经派生的错误描述仍保留；因此干预无变化也不能排除原始来源曾影响轨迹。固定未来截图的回放没有检验真实环境恢复或最终任务成功率。

## 7. 对论文最有帮助的补强

1. **纯长度对照**：保留同一关键相关历史和最后两轮，仅增加不相关历史，匹配 token 长度及图片到查询的距离；同时控制请求步数文字，筛查注入前已有的错误状态。当前窗口实验尚不能排除内容差异和基线循环。
2. **正负案例与独立语义复核**：同应用、同注入和相近阶段同时纳入 Mirage 与未触发案例；先按截图、状态断言、动作判定，再关联注意力。尤其分开异常被识别、错误状态被相信、错误动作被提出，避免仅以注意力定义 Mirage。
3. **更强的因果与实际恢复证据**：在更多独立轨迹做来源状态／历史动作的分离干预，加入匹配的无关编辑；选择少量机制候选再做 activation patching 或匹配随机头对照。若要声称改善后续任务结果，需从纠正点真实续跑环境并验证最终结果，离线固定截图不能替代。

现有四类实验在问题设置上合理；最需要避免的是把“注意力变化”“无依据断言”“Mirage 触发”“下游失败”直接写成同一事件。当前补测优先补齐了原先缺少的时机因素，并提供来源文本干预；纯长度隔离、独立语义标签和真实恢复仍是论文下一步最有价值的证据。

## 8. 技术可复核性

- 三模型只采集语言模块的真实 full-attention softmax：27B 16 层×24 头，9B 8 层×16 头，GLM 40 层×32 头。Qwen 线性模块、视觉编码器、门控与残差的完整因果路径不在此范围；不做伪 attention rollout。27B 目录沿用 Qwen3.8-27B 名称，加载类为 Qwen3_5ForConditionalGeneration，未宣称获得上游官方版本身份。
- BF16／SDPA、原图字节和原生模板，greedy 自然生成，上限 2048；保存原始输入／输出 IDs 与逐 query 张量。先做文本、带图技术预检及真实快照预检，输出 IDs 与逐步完整 logits 完全不变。这个结论只覆盖实际预检，不能冒称每个正式配置都做过双重生成。
- 9B 原权重目录缺少 generation_config，默认仅用 endoftext 停止，曾在 im_end 后继续生成虚构轮次。保留原始记录，统一在首个原生回复终止符处建立单回复视图，注意力也同步截到对应 query。真实异常快照用修正停止设置重放后，90 token 与原记录前缀逐 ID 完全一致，预检 logits 差为 0；见 `qwen9-stop-validation.json`。剩余 9B 使用显式原生停止符。
- GLM 后半批将同样的 FP32 来源归约留在 GPU，回复结束后再搬到 CPU，以减少同步。新旧输出 IDs、采集开关 logits 完全一致；注意力浮点归约最大绝对差 {maxdiff:.3g}，并另做原同步版本重复生成校准，详见 `glm-async-validation.json`。未把浮点归约的末位差异说成逐字节相等。
- 两个复制模型的全部 26 个文件大小及 SHA-256 在 4090 与 3090 一致，见 `model-transfer-verification.json`。主计划 SHA-256 为 `1a5dd6bb78494618430f9578b7c170ec505ad0738715a94c9d606a14fc93163f`；计划、来源审计与实际 runner 均保留。终局逐张量 SHA 与输入长度核验见 `terminal-audit.json`。

数据表：`analysis/measurements.csv`、`paired-summary.json`、`semantic-reviewed.json`、`source-comparisons.json`。科学图同时提供 PNG、PDF、SVG。所有新增模型推理与注意力采集均在 3090 服务器完成；统计与制图在本机完成。未执行 GUI 或调用付费 API。
'''
(root/'实验结果与论文建议.md').write_text(text,encoding='utf-8');print('Wrote report',len(text),'characters')
