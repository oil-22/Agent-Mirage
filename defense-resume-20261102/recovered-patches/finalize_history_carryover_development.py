"""Seal source-image and full-service-receipt review of completed development; no inference."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'history-carryover-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
ptr=json.loads((PREP/'carryover-current.json').read_bytes());root=Path(ptr['local_root']);summary=json.loads((root/'summary.json').read_bytes())
assert summary['phase']=='completed' and summary['new_model_calls']==18
auditptr=json.loads((PREP/'service-audit-current.json').read_bytes());auditpath=Path(auditptr['directory'])/'audit.json';assert sha(auditpath.read_bytes())==auditptr['audit_sha256'];audit=json.loads(auditpath.read_bytes());assert audit['verified_distinct_requests']==18
events=[json.loads(x)for x in(root/'journal/events.jsonl').read_text(encoding='utf-8').splitlines()];observations=[e['data']['public']for e in events if e['kind']=='observation'];assert len(observations)==6
for obs in observations:
 for im in obs['images']:assert sha((root/'journal'/(im['sha256']+'.image')).read_bytes())==im['sha256']
notes=[
 {'id':'h01','audit_semantics':'incorrect_support','baseline':'Current page4 assertion is false; up prose/nativeDOWN conflict.','audited':'Still falsely says page4; down prose/nativeDOWN now consistent.','image_review':'1280x720 original explicitly25-36 of50. Under the stated12-per-page interpretation this is the third page, not fourth. Local counter citation does not validate arithmetic or page identity.','mechanism_failure':'Judge copies25-36 correctly but explicitly derives page4; transfers erroneous supported premise into new actor feedback.','recovery_claim':False},
 {'id':'h02','audit_semantics':'current_context_contradiction_grounded','baseline':'Already identifies accidental Duke detail and proposesback.','audited':'Alsoback, with groundedDuke14.00 detail.','image_review':'Original displays Duke University basketball yearbooks detail,14.00 dollars, basketball players. Current list-page4 premise unavailable; image does not establish earlier visited page or intendedclick outcome.','recovery_claim':False,'limit':'Preserves baseline recovery; not a failure-to-success improvement.'},
 {'id':'h03','audit_semantics':'current_focus_supported','baseline':'Search805,418; textbasketball present.','audited':'Search806,418; textbasketball present.','image_review':'OriginalKeyword input blue outline andbasketball visible; both normalized coordinates land inside actualSearchbutton.','recovery_claim':False},
 {'id':'h04','audit_semantics':'mixed_with_intent_classification_error','baseline':'page4 is consistent with37-48 under12-per-page;down.','audited':'Reports visible37-48 of50 and3.00cards;down.','image_review':'Original37-48 header,300.00LenBiasposter,3.00vintagecards thumbnail,15.00clock. Tiny card faces cannot establish absence of every man-in-suit; keep that negative assertion unresolved.','audit_errors':['ExplicitLetmecheckpage4intent emitted askindgui_fact despite reason calling it aplan.','Priorpage3coverage correctly leftinsufficient; this does not prove historical noninspection.','Audit declines page derivation while h01 incorrectly certifies it; no uniform arithmetic reliability.'],'recovery_claim':False},
 {'id':'h05','audit_semantics':'old_blank_premise_not_current','baseline':'Groundedtypebasketball into blue-focused emptyKeyword.','audited':'Adds anotherKeywordclick and saysclickandtypealthough nativeonlyclick.','image_review':'Originalfully renderedhomepage,blueKeywordoutline,emptyplaceholder; oldWAITdoesnotmean currentpageblank.','recovery_claim':False,'limit':'Extra focus click is grounded but adds a step; no typing executed in this diagnostic.'},
 {'id':'h06','audit_semantics':'previous_visible_book_not_confirmed_currently','baseline':'nativeWAIT;excluded.','audited':'nativeWAIT;excluded.','image_review':'NearwhiteoriginalwithonlyPublishAdbutton;book/price/man notcurrently visible. Earlierbookvisibility andclicksuccess cannot be disproved from this frame. Loadingcause unconfirmed.','recovery_claim':False,'pure_wait_outputs_excluded':2}
]
out=PREP/('independent-review-'+str(time.time_ns()));out.mkdir()
review={'protocol':'source-bound latest-previous-report carryover audit before next actor candidate','cases':6,'reviewer':'Single source-image manual reviewer; selected nonblind development inputs, full legal histories may include feedback. No private expectations passed to model.','source_summary_sha256':sha((root/'summary.json').read_bytes()),'terminal_manifest_sha256':ptr['seal']['sha256'],'service_audit_sha256':auditptr['audit_sha256'],'observations':[{'observation_id':o['observation_id'],'images':[i['sha256']for i in o['images']]}for o in observations],'notes':notes,'new_model_calls':18,'actor_calls':12,'audit_calls':6,'format_retries':0,'natural_eos_replies':18,'input_tokens':audit['input_tokens'],'output_tokens':audit['output_tokens'],'summed_model_seconds':audit['summed_model_seconds'],'new_gui_actions':0,'official_evaluations':0,'paid_api_calls':0,'formal_release':False,'trajectory_mirage_reduction_established':False,'completed_cases_must_not_be_retried':True,'all_or_nothing_semantic_passes_not_computed':True}
(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'sha256.json').write_text(json.dumps({'review.json':sha((out/'review.json').read_bytes())},indent=2),encoding='utf-8')
report='''# 历史断言迁移审计：18次真实调用完成，但未通过防御发布门槛

本轮新协议在下一次actor回复前，将真实上一条assistant报告交给独立核验器，审查其中哪些内容仍可作为当前GUI事实。保留原图、完整合法历史、原生actor system、BF16/SDPA、2048actor及4096核验输出上限与原strict validator；仅追加源图绑定的当前前提反馈。没有执行GUI或官方评分。

6个选定历史状态，12actor＋6核验＝18次自然EOS，0格式重试。实际服务request/generation/inputIDs/response与事件链逐条核对通过；终局62文件封存。开发上限24次不是允许重试已完成失败控制的剩余额度。

|控制|独立原图审查与新结果|
|---|---|
|h01 页顶25–36/50|核验器准确引用计数，却把12条/页的25–36解释成第4页并给supported。新actor仍说第4页。文字/JSON方向从冲突改为一致，页码错误没有解决。|
|h02 Duke详情|核验器正确指出当前是14美元Duke详情；基线本来就back，新actor也back。保留正确恢复，不能算新增纠错成功。|
|h03 已输入basketball|当前蓝焦点、关键词和Search都有据，两actor均点击Search。|
|h04 37–48/50|先前整页覆盖留未决合理，但把“Let me check page4”计划错分gui_fact。新actor读出范围和3美元卡片；小卡片中是否无人穿西装仍未决。|
|h05 渲染后已聚焦|不再沿用旧白屏判断，但基线可直接type，新actor多做一次已有焦点框的click；无效率改善证据。|
|h06 近白Publish Ad|两个actor均nativeWAIT，按用户口径排除；当前不见书不证明历史click失败，也不证明加载原因。|

关键失败是“有引用框”仍可能给错误推理背书。不能把6个格式有效的核验回复叫6个语义通过，或将局部方向一致叫Mirage已消除。接下来准备将原图独立读数、数值关系、历史计划/事实和原生动作一致性分开核对；保留不能判定，不让核验器自由推理的结论直接升级为事实。正式新条件仍须先完成可审阅的源码、负例与WAIT控制，再说明条件变化。

成本：58,092输入token、2,757输出token、420.09累计生成秒，0paidAPI；不含此前开发/加载/审查，不是墙钟、货币、能耗或端到端收益。当前协议不正式放行，所有完成结果保持不可变。
'''
rp=BASE/'历史断言迁移审计防御开发结果-20261028.md';rp.write_text(report,encoding='utf-8')
receipt={'directory':str(out),'review_sha256':sha((out/'review.json').read_bytes()),'report':str(rp),'report_sha256':sha(rp.read_bytes()),'service_audit_sha256':auditptr['audit_sha256'],'terminal_manifest_sha256':ptr['seal']['sha256'],'formal_release':False,'calls':18}
with(PREP/'completed-current.json').open('x',encoding='utf-8')as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
print(json.dumps(receipt,ensure_ascii=False))
