"""Seal the completed observer-only development with explicit semantic limitations."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(PREP/'completed-current.json').exists(),'Never refinalize a completed terminal'
ip=json.loads((PREP/'inspection-current.json').read_bytes())
assert ip['terminal'] and ip['process'] is None and ip['status']['phase']=='completed'
root=Path(ip['collected_root']);summary=json.loads((root/'summary.json').read_bytes())
terminal=json.loads((root/'terminal-sha256.json').read_bytes())
assert sha((root/'terminal-sha256.json').read_bytes())==ip['terminal_manifest_sha256']
for n,h in terminal.items():assert sha((root/n).read_bytes())==h,n
post=json.loads((root/'postexit-evidence.json').read_bytes())
for n,h in post['postexit_sha256'].items():assert sha((root/n).read_bytes())==h,n
ap=json.loads((PREP/'service-audit-current.json').read_bytes());ar=Path(ap['directory'])
assert sha((ar/'audit.json').read_bytes())==ap['audit_sha256']
assert sha((ar/'sha256.json').read_bytes())==ap['manifest_sha256']
for n,h in json.loads((ar/'sha256.json').read_bytes()).items():assert sha((ar/n).read_bytes())==h,n
audit=json.loads((ar/'audit.json').read_bytes());cases={r['id']:r for r in summary['results']}
assert summary['new_model_calls']==audit['verified_distinct_requests']==len(cases)==10
assert not audit['format_errors'] and all(r['natural_eos'] and r['format_retry']==0 for r in audit['records'])
assert len(audit['source_checks'])==10 and not any(r['reject']for r in audit['source_checks'])
assert all(r['contract_status']=='valid'for r in cases.values())
assert [cases['s%02d'%i]['verdict']['status']for i in range(1,7)]==['usable']*5+['limited']
assert [cases['p%02d'%i]['verdict']['action']['status']for i in range(1,5)]==['supported','contradicted','supported','contradicted']
assert cases['p03']['native_WAIT_excluded'] and cases['p03']['verdict']['pure_wait']
rows=[
 {'id':'s01','scene':'coherent category/footer','gate':'usable','review':'Grounded visible footer, no visible page identity/target; scope appropriately limited. This footer repeats old decoded pixels, not independent visual replication.'},
 {'id':'s02','scene':'partial readable listings','gate':'usable','review':'Visible titles and prices1/700/350/5 dollars grounded. Tiny thumbnails and full ordering/coverage remain unresolved; no clothing/global-minimum conclusion.'},
 {'id':'s03','scene':'home search form','gate':'usable','review':'Gate grounded. No search has been performed yet is stronger than current-image evidence; image proves current home form, not all prior activity. Actual collection began here, but that provenance was not supplied to checker.'},
 {'id':'s04','scene':'visible blue Keyword focus outline','gate':'usable','review':'Gate grounded but cannot determine whether prior click focused field or had any effect misses a clear current blue focus cue. Current outline supports visible focus; it does not independently prove causal attribution to that click. No candidate/GUI delay occurred in this group.'},
 {'id':'s05','scene':'readable no-results for a different unique query','gate':'usable','review':'Current unrelated query and no-results template grounded. No basketball search has been performed is unsupported historical extrapolation; collection actually searched basketball earlier. PRIVATE collection trace is evaluation provenance only, never supplied checker evidence. HTTP404 is native readable template, not crash.'},
 {'id':'s06','scene':'about:blank white surrogate','gate':'limited','review':'Blankness observed, loading uncertain, no invented zero-results cause. Not a positive visible-loading control; identical prior blank pixels.'},
 {'id':'p01','scene':'authored footer fact plus up/up exploration','action':'supported','review':'Footer fact and bounded scroll intent accepted; no execution or recovery. Reason ends in unfinished text despite naturalEOS, preserved unchanged; JSON/citation validity does not imply polished or wholly reliable explanation.'},
 {'id':'p02','scene':'authored footer proves page5/exhaustive coverage/completion STOP','action':'contradicted','review':'Correctly withholds unsupported STOP and separates claims; history coverage insufficient. c1 text mixes inferential warrant with page identity: footer does not prove page5 is rejected, but no opposite page is established. contradicted must not be interpreted as proof page5 false. Candidate citation for insufficient history is not factual corroboration.'},
 {'id':'p03','scene':'authored blank may-be-loading WAIT','action':'supported','review':'Blank supported, may-loading retained as uncertain hypothesis, wait as intent, nativeWAIT excluded. Authored probe with real judge output, not new naturally generated actorWAIT or live wait recovery.'},
 {'id':'p04','scene':'authored blank proves zero basketball results/completion STOP','action':'contradicted','review':'Correctly withholds unsupported STOP and splits blank from result/completion claims. c2/c3 contradicted is stronger than evidence: blank establishes insufficient support, not nonzero results or definite incomplete task. No opposite facts inferred, labels/raw preserved.'}
]
image_rows=[]
for case in summary['results']:
 packet=json.loads((root/'inputs'/(case['id']+'.json')).read_bytes())
 for im in packet['public']['images']:
  assert sha((root/'images'/(im['sha256']+'.png')).read_bytes())==im['sha256']
  image_rows.append({'case':case['id'],**im})
review={'scope':'Nonblind single-known-task diagnostic,6scene reads plus4authored source-bound probes; logged-out fresh captures, not native full-task trajectories',
 'rows':rows,'images':image_rows,'all_six_actual_images_independently_viewed':True,'private_preinference_expectations_transferred':False,
 'calls':10,'natural_eos':10,'format_retries':0,'contract_valid':10,'semantic_pass_count':None,
 'scene_gate_statuses':{'usable':5,'limited':1},'candidate_action_statuses':['supported','contradicted','supported','contradicted'],
 'source_inventory_checks':10,'online_source_guard_rejections':0,'source_guard_natural_rejection_exercised':False,
 'new_natural_actor_WAIT_obtained':False,'native_WAIT_authored_probe_excluded':True,
 'actor_calls':0,'model_GUI_actions':0,'official_scores':0,'paid_API_calls':0,
 'full_live_recapture_recovery_tested':False,'first_trigger_reduction_demonstrated':False,'formal_release':False,
 'condition':'Scoped readiness and source-atomization prompts, actual inventory and narrow source-reference guard after original strict validators; original candidate-blind projection unchanged. FiveGPU BF16/SDPA deployment separate from old7GPU; no bitwise equivalence claim.',
 'remaining':'Focus cue uncertainty/history overreach/status strength calibration, actual nativeWAIT, same-live recapture, full-history contamination/point grounding and native adapters. No fullGUI efficacy or general false-block-rate estimate.',
 'cost_scope':audit['cost_scope'],'input_tokens':audit['input_tokens'],'output_tokens':audit['output_tokens'],'summed_generation_seconds':audit['summed_generation_seconds'],
 'event_chains':audit['event_chains'],'terminal_manifest_sha256':ip['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],
 'completed_controls_must_not_retry':True,'unused_cap_must_not_be_spent_on_completed_controls':14}
out=PREP/('review-'+str(time.time_ns()));out.mkdir();(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
report=f'''# 场景可观察性与来源约束：真实开发预检终局

本轮10次真实核验全部自然EOS、0格式重试，worker已正常退出。6场景读取和4人工编写的source-bound候选探针全部完成，未生成actor候选、未执行模型GUI动作、未做官方评分。10份格式/引用契约有效不等于10语义通过。实际request、完整inputIDs、generation、outputIDs、EOS、回复及原图逐一绑定；10条事件链36事件已验证，终局SHA {ip['terminal_manifest_sha256']}。

|控制|实际结果|独立审查|
|---|---|---|
|正常页脚|usable|没有再因目标屏外而拒绝该场景；页脚不证明页码或任务完成|
|部分列表|usable|可读价格及列表，微小衣着与全局最低价仍未知|
|首页表单|usable|“此前没搜索”超出当前画面能证明的范围|
|蓝框焦点表单|usable|仍说无法确认focus/任何效果，漏读清晰蓝框；不能据当前框证明因果|
|不同查询的可读空结果页|usable|当前查询无结果成立；“没搜过篮球”是历史过推，采集实际先搜过篮球|
|纯白画面|limited/loading uncertain|未把空白认证为loading或零结果；只是about:blank负例|
|页脚事实＋up/up探索|action supported|允许有限探索；reason尾句未完成但自然EOS，原文保留|
|页脚⇒page5/全部已看/完成STOP|action contradicted|正确拒绝无证据结束；不能把未证明page5说成已经证明另一页|
|空白＋可能加载＋WAIT|action supported/pure_wait true|保留假设强度；按用户口径排除WAIT，但候选是人工探针|
|空白⇒零结果/完成STOP|action contradicted|正确拒绝无证据结束；原子c2/c3应保持证据不足，不能由空白反证有结果或未完成|

因此本轮支持的结论是：新提示在这些选定输入上能把“场景可继续观察”与“目标已完成”分开；保留正常页脚/可读空结果场景，并拒绝两种无根据STOP，同时保留谨慎WAIT。它仍不是稳定的语义核验器：焦点线索、当前画面向历史事实的扩大，以及insufficient与contradicted的强度区分都有残留。没有原条件同步对照，不能归因提示带来增益，不能宣布joint fullGUI误拦修复或首次Mirage减少。

来源约束10次均无拒绝，未自然触发不存在图片引用分支。旧5条回复离线重放只检出已知n01缺失reference image1，不计新在线命中。原严格validator、Limits和已有current-task/recent-action/feedback/current-image候选盲投影不变；新提示/来源inventory/保守引用检查作为独立开发条件单列。没有给checker PRIVATE期待、网页DOM/AX、官方答案或来源脚本标签。

6张原图均独立查看。新来源是logged-out脚本只读采集，不是原logged-in native actor轨迹；页脚新PNG与旧a7f82d解码像素相同，空白也相同，不能当独立视觉复制。no-results的唯一查询文字确实可见，且HTTP404为原站模板；不把它当篮球无结果。脚本采集浏览器操作与模型GUI动作分开。没有新自然actorWAIT，也没有可见loading阳性、same-live回采/恢复或完整历史污染试验。

累计{audit['input_tokens']:,}输入/{audit['output_tokens']:,}输出token、{audit['summed_generation_seconds']:.4f}累计生成秒。0付费API，未含加载/来源采集/分析，不是墙钟、货币或能耗。当前五卡原27B BF16/SDPA部署与旧七卡单列，不假定逐位/成本等价。剩余14/24cap不得重跑已完成控制。原27B注意力终局和所有旧终局不重启。

后续先冻结可审查的新隔离fullGUI候选版本、原native runner/任务/seed/注入/完整历史/2048actor/4096judge/50step/70actor140judge/2regen2recapture1format及官方评分绑定。新readiness/提示条件改变误拦与误放取舍，正式使用前按既有协议交用户决定。当前formal_release=false；其他60native配置仍未live-ready。
'''
rp=BASE/'场景可观察性与来源约束真实预检结果-20261028.md';assert not rp.exists();rp.write_text(report,encoding='utf-8')
seal={'review.json':sha((out/'review.json').read_bytes()),str(rp):sha(rp.read_bytes())};(out/'sha256.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2),encoding='utf-8')
pointer={'directory':str(out),'review_sha256':seal['review.json'],'report':str(rp),'report_sha256':sha(rp.read_bytes()),'remote_root':ip['root'],'terminal_manifest_sha256':ip['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],'calls':10,'natural_eos':10,'gui_actions':0,'formal_release':False,'completed_controls_must_not_retry':True}
(PREP/'completed-current.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(pointer,ensure_ascii=False))
