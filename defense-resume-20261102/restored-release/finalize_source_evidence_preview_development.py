"""Seal independent manual development review and handoff. No inference or terminal mutation."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'source-evidence-preview-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
stamp=str(time.time_ns());out=PREP/('review-'+stamp);out.mkdir()
launches={k:json.loads((PREP/n).read_bytes())for k,n in [('main','launch.json'),('controls','controls-launch.json'),('routing','routing-launch.json')]}
summaries={k:json.loads((Path(v['local_root'])/'collected/summary.json').read_bytes())for k,v in launches.items()}
assert all(s['phase']=='completed'for s in summaries.values())
assert sum(s['new_model_calls']for s in summaries.values())==31
auditptr=json.loads((PREP/'service-audit-current.json').read_bytes());auditfolder=Path(auditptr['directory']);audit=json.loads((auditfolder/'audit.json').read_bytes())
assert sha((auditfolder/'audit.json').read_bytes())==auditptr['audit_sha256']and audit['verified_distinct_requests']==31
rows=[]
notes={
 'c01':{'baseline':'definite_false_current_no_suit','caution':'definite_false_current_no_suit','evidence':'green_suit_card_recognized; $30 vs previously observed $5 comparison; no global uniqueness claim',
        'review':'Original image visibly contains green-suited man on Victor card. Preview identified suit but added unreliable detail (dark suit, counter/display/framed item); not a semantically perfect reader.'},
 'c02':{'baseline':'definite_false_page4_and_wrong_pagination_click','caution':'definite_false_page2; scrolling action is grounded','evidence':'page3 consistent with25-36; scrolling instead of absent pagination click',
        'review':'Current frame explicitly25-36 of50; native523,892 falls in listing description, not pagination.'},
 'c03':{'baseline':'definite_false_page4_and_wrong_pagination_click','caution':'false_page4_remains; grounded_down_scroll','evidence':'false_page4_remains; grounded_down_scroll',
        'evidence_routing':'false_page4_remains; additionally proseUP/nativeDOWN conflict',
        'review':'Actual current Duke title at native523,892; no visible pagination. Known original legal source sequence/current delivered-frame audit establishes page3; earlier actor page4 labels are not truth. New routing condition did not cure this and introduced a direction conflict.'},
 'c04':{'baseline':'proseUP/nativeDOWN_conflict','caution':'proseUP/nativeDOWN_conflict','evidence':'proseUP/nativeDOWN_conflict','evidence_routing':'proseUP/nativeUP_consistent',
        'review':'Current coherent category list/footer, not a blank/loading fault. Preview usable is a stage result, not complete Controller recovery or task success. Direction contradiction is counted separately from perceptual semantic Mirage.'},
 'c05':{'baseline':'visible_blue_focus; grounded_type','caution':'visible_blue_focus; grounded_type','evidence':'visible_blue_focus; grounded_type',
        'review':'Preview did not explicitly identify blue focus cue; type retained by actor, not proof preview recovered focus.'},
 'c06':{'baseline':'pure_nativeWAIT_excluded','evidence':'pure_nativeWAIT_excluded','review':'Blank readout limited/loading uncertain. Both nativeWAIT excluded even with likely-loading prose; not a no-Mirage trajectory.'},
 'c07':{'baseline':'pure_nativeWAIT_excluded','evidence':'pure_nativeWAIT_excluded','review':'Nearblank with PublishAd fragment; readout limited/loading uncertain. Actor loading diagnosis stronger than evidence; nativeWAIT remains excluded by user counting.'},
 'c08':{'baseline':'native631,679_inside_page4; whole_page_no_suit_claim_unresolved','evidence':'native631,679_inside_page4; whole_page_no_suit_claim_unresolved',
        'review':'Selected3 and real page4 button visible.631*1280/1000=807.68,679*720/1000=488.88 inside792..831,470..510. Earlier whole-page visual-criterion/coverage assertions stay unresolved; not labeled all-correct.'}}
for name,note in notes.items():
 arms={}
 for key,s in summaries.items():
  for r in s['results']:
   if r['id']==name:
    for a in r['arms']:arms[a['arm']]={'candidate':a['candidate'],'candidate_sha256':sha(a['candidate'].encode()),'receipts':[c['receipt']for c in a['calls']]}
 rows.append({'id':name,'manual_semantic_review':note,'arms':arms})
review={'created_ns':stamp,'roots':launches,'summary_sha256':{k:sha((Path(v['local_root'])/'collected/summary.json').read_bytes())for k,v in launches.items()},
 'reviewer':'Single reviewer independent of checker outputs as ground truth, independently viewed all8 original frames; selected nonblind development, not inter-rater study.',
 'predeclared_expectations_sha256':sha((Path(launches['main']['local_root'])/'PRIVATE-predeclared-review.json').read_bytes()),
 'source_frames':8,'actor_outputs':23,'candidate_blind_readouts':8,'new_model_calls':31,'natural_eos_replies':31,'format_retries':0,
 'original_formal_trajectories_restarted':0,'new_gui_actions':0,'official_evaluations':0,'paid_api_calls':0,'rows':rows,
 'finding':'v1 independent readout corrects two preselected definite visual falsehood states vs baseline and caution, retains the third; footer native-direction error remains. Routing variant corrects footer direction in one selected diagnostic but retains page error and introduces UP/DOWN conflict in the other. Do not combine variants into an all-pass method.',
 'release_ready':False,'formal_trial_started':False,
 'limits':['One fixed archived task,8 selected frames, shared contaminated legal histories; not independent tasks or blind validation.','No full online trajectories, accepted/executed-error reduction, official success change or significant Mirage-trigger reduction measured.','Some readout details are wrong/unresolved, and valid screen citations do not establish semantic accuracy.','No whole-trajectory negative labels; pure nativeWAIT excluded; existing correction never erases earlier occurrence.'],
 'service_audit':auditptr,'cost':{k:audit[k]for k in ['input_tokens','output_tokens','summed_model_seconds','cost_scope']}}
(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
report=BASE/'前置视觉读数防御开发结果与未解问题-20261028.md'
report.write_text('''# 前置视觉读数：已完成真实开发对照，尚未达到正式放行条件

现有核验防御有漏检和误拦。此次把候选生成前的独立当前原图读数交给actor，检验其是否能减少首次错误断言。所有新结果独立保存，未重跑原20或新版两个终局。

## 实际完成

8个已知历史状态，前5个对照原始actor、仅一般提醒、同一提醒＋候选盲视觉读数；另3个状态读取原图后做原始/读数actor对照。最后两个仍失败的状态另设来源与执行契约反馈诊断。合计23个actor输出＋8个独立读数＝31次真实本地模型调用，恰好原先冻结的31次开发总上限，0格式重试、31自然EOS。三组worker均正常退出，终局文件和事件链通过校验，不再启动任何这轮队列。

模型均原27B BF16/SDPA；原图未改，actor原始完整消息前缀、原生system、原生成参数、2048输出均保留。只追加明确标记的防御消息；核验4096输出与原严格screen引用validator不变。候选盲读数只看当前真实用户文本/尝试动作/执行反馈/原图，看不到待生成候选或PRIVATE评估标签。属于新反馈条件开发，没有正式在线组、GUI执行或官方评分。

## 逐项结果

| 原图状态 | 原始组 | 一般提醒组 | 独立读数组 |
|---|---|---|---|
| 30美元Victor卡，有绿色西装男子 | 错称没有西装男子 | 仍错称没有 | 识别西装男子，并保留30美元高于先前5美元的比较 |
| 明示25–36/50的第3页顶部 | 错称第4页并点商品描述当分页 | 错称第2页，改为滚动 | 正确认第3页，滚动寻找分页 |
| 第3页中部、Duke标题处 | 错称第4页并点Duke当分页 | 第4页错误仍在 | 第4页错误仍在，未治愈 |
| 正常页脚 | 文字up/JSON down | 同样失配 | 同样失配；独立读数本身判usable |
| 蓝色Keyword焦点框 | 正常type | 正常type | 正常type；读数没有明确读出焦点，不冒称焦点能力通过 |
| 纯白、近白两图 | 均native WAIT | 未设此组 | 均native WAIT，按用户口径排除 |
| 第3页底部合法第4页按钮 | 合法点击 | 未设此组 | 同一合法点击；整页无西装/覆盖断言仍未决 |

在预先选定的三处确定视觉错误中，独立读数纠正两处；另一个仍锚定错误历史。不能把此结果外推为总体触发率下降或“准确率提升66.7%”。一般提醒对这三处都未消除错误。

另外的“来源与执行契约”变体，只做两个非盲选定诊断：页脚自然生成up且文字一致；另一图仍错报第4页，且新增文字up/JSON down冲突。不得把不同变体各自成功的样例拼成统一方法全通过。

## 反证与边界

视觉读数也有错误细节：Victor卡被说成dark suit、柜台/背后框等，虽识别关键西装，不能称读数语义全通过。纯WAIT保留不代表加载原因已被证实。分页631,679对应原像素807.68,488.88，确在第4页按钮内；合法动作与未决整页断言分开。页脚usable只是阶段检查，尚未验证整条Controller恢复。

目前尚无完整在线配对轨迹、接受/执行错误下降或官方成功变化，也没有证明整条任务首次Mirage触发率降低。事后拦截或纠正不能抵消已出现的Mirage。原20为单一任务混版本，不能作本轮公平对照。

## 证据与成本

完整原始请求/实际input IDs/输出IDs/自然EOS/回复/来源图/事件链均保留，并核对实际发送内容与journal一致。31次调用总输入88895、输出4523 token，累计生成745.16秒；不含服务加载、开发与审查，不是墙钟、货币或能耗。没有付费API、27B回退或新GPU服务。

## 接下来的门槛

前置读数是有局部证据的候选机制，暂不正式放行。下一步要解决旧叙述压过当前证据以及原生动作与解释失配，先冻结新协议和未尝试匹配/负例/WAIT控制，保留本轮全部失败。任何新正式反馈条件应独立根目录、同版本/同task-seed-injection、完整原输入和原调用/步数预算，比较首次候选Mirage、接受/执行错误、误拦、恢复、官方成功与总开销；按既有要求说明具体实验条件变化并取得用户决定。不能追加本轮31次预算或重启已完成队列。
''',encoding='utf-8')
latest={'directory':str(out),'review_sha256':sha((out/'review.json').read_bytes()),'report':str(report),'report_sha256':sha(report.read_bytes()),'release_ready':False,'formal_trial_started':False,'model_calls':31,'parents':launches,'service_audit':auditptr}
(PREP/'completed-current.json').write_text(json.dumps(latest,ensure_ascii=False,indent=2),encoding='utf-8')
header='''# 最新2026-10-28：前置视觉读数31次真实开发调用完成，局部改善但未正式放行

用户要求优先拿出降低Mirage触发的方法。权威`source-evidence-preview-development/completed-current.json`、报告`前置视觉读数防御开发结果与未解问题-20261028.md`。8个单任务选定历史状态，23actor＋8候选盲当前原图读数＝31自然EOS调用（原冻结开发总上限）、0格式重试；main/controls/routing三worker均终局正常退出，不重启。先inspect_source_evidence_preview_dev.py（--controls/--routing选择其它组，只读），绝不再跑launch或补预算。

v1三组同源比较：原始和一般提醒均漏认Victor卡西装、错报当前页；独立读数纠正西装及25–36/50页顶身份两处，但Duke中部仍被叫第4页，footer文字up/JSON down仍在。蓝焦点type、两图nativeWAIT和真实分页点击保留；整页衣着/覆盖断言仍有未决，不标无Mirage。另来源/执行契约变体只做两处非盲诊断：footer自然UP一致；Duke仍错页且新增方向冲突。不能拼接变体各自成功成统一全通过。读数有dark suit/柜台等错误细节、没明确读出焦点，8引用有效不是8语义通过。

原图、actor完整消息前缀/原生system/参数/2048输出，模型BF16/SDPA、核验4096及strict validator保留，仅独立开发条件追加防御反馈。0GUI/0官方评分/0paidAPI；未正式证明trajectory触发下降、执行错误下降或任务恢复。独立查看8原图/逐候选说明，PRIVATE期待没送模型。31实际服务request/generation/inputIDs/EOS/response与journal核对、三事件链及封存通过；88895输入/4523输出token、745.16累计生成秒，不是墙钟/货币/能耗。旧542审查、两full终局、UI旧控制及attention不改不重跑。

下一防御优先：在新冻结协议/未尝试控制中解决历史叙述锚定与文字/JSON动作失配，不能只堆提示或把候选少说话当感知改善；正式新反馈条件先完成可审阅适配/源图负例WAIT/审查，再按既有要求解释条件变化取得用户决定。保持首次候选Mirage、接受/执行错误、误拦、恢复、官方成功/成本分开。v1未放行；本轮失败终局保留不可重试。

UI双GPU已获用户授权，无需重问。最新guard仍因GPU1有他人进程和23022MiB<23500而waiting，0模型调用；权威dual-gpu-resource-current.json。不得抢卡/改精度/缩图/截历史。monitor继续ACTIVE、旧机制暂停，其余60原生预检与27Battention仍待办，防御优先。

--- 以下为历史交接 ---

'''
for p in [BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']:
 old=p.read_bytes();snapshot=out/(p.parent.name+'-'+p.name+'.before');snapshot.write_bytes(old)
 p.write_text(header+old.decode('utf-8'),encoding='utf-8')
(out/'sha256.json').write_text(json.dumps({str(p.relative_to(out)):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(latest,ensure_ascii=False))
