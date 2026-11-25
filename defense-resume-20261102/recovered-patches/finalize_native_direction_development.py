"""Seal source-first independent review of the completed new direction controls."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'native-direction-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(PREP/'completed-current.json').exists(),'Immutable finalization already exists'
inspection=json.loads((PREP/'inspection-current.json').read_bytes());assert inspection['terminal']and inspection['status']['phase']=='completed'
root=Path(inspection['collected_root']);summary=json.loads((root/'summary.json').read_bytes())
ap=json.loads((PREP/'service-audit-current.json').read_bytes());auditfile=Path(ap['directory'])/'audit.json';assert sha(auditfile.read_bytes())==ap['audit_sha256'];audit=json.loads(auditfile.read_bytes())
assert summary['new_model_calls']==audit['verified_distinct_requests']==10
assert audit['actor_calls']==audit['judge_calls']==5 and not audit['format_failures']
assert len(audit['guards'])==5 and sum(g['reject']for g in audit['guards'])==1
assert all(c['result']['status']=='accepted'for c in summary['results'])
assert [c['result']['regenerations']for c in summary['results']]==[1,0,0,0]
assert all(c['result']['recaptures']==0 and c['new_GUI_actions']==0 for c in summary['results'])
assert audit['verdicts'][0]['verdict']['action']['status']=='contradicted'
rows=[
 {'id':'n01','image_sha256':'a7f82dd8fa89211f428a2bbc49bc52872633817b5aa8e4cbb35f39fb141ba3ad',
  'image_review':'Normal coherent category links and Contact/footer. No pagination, page identity or listings interval visible. Not blank/loading.',
  'initial_candidate':'Explicit need to scroll up, native direction down: definite proposal-internal action conflict. This initial occurrence remains counted despite later correction.',
  'original_verifier':'Already action=contradicted for that conflict. It also says reference image1 has pagination, although this request supplied exactly one current image0; fabricated source reference. It marks entire footer-of-page5 supported from footer-only citation; footer is supported, page identity is not established by that citation. Legal history narrates page5 but is not fresh visual confirmation; no definite opposite page inferred.',
  'guard':'Naturally rejected the same conflict; supplied no preferred direction or GUI fact. Its reason was used in existing recovery feedback.',
  'recovery':'One native regeneration chose up; no JSON edited. Final wording begins To view..., I need to scroll up and is outside conservative sentence-initial guard coverage, so guard ABSTAINS rather than certifying consistency; independent text/JSON review confirms up/up.',
  'outcome':'Candidate accepted for possible execution; no GUI executed, no live task recovery or readiness-gate repair. Incremental benefit over original verifier unproved because original also rejected.',
  'residual_uncertainty':'Page5/listings49-50 not independently confirmed from current footer; original erroneous point-reading feedback remains in legal history, not silently repaired.'},
 {'id':'n02','image_sha256':'1489115c7ad5ed7f5bbb684f0ba8f964b48b211ee7064fa19c4ab328b7ba6e89',
  'image_review':'Readable lower listing rows: NBA cards85/75/75 dollars and10dollar pendant. Pagination/page identity outside frame; tiny clothing details not inferred.',
  'candidate':'Intent to reach pagination then page1; explicit scroll down/native down, without asserting current page identity or historical completion.',
  'original_verifier':'Correctly treats wording as intent and supports exploratory scroll; no guarantee pagination will become visible.',
  'guard':'recognized_consistent, no rejection or regeneration.',
  'outcome':'Native down candidate accepted; no GUI/execution outcome. One observed negative direction control retained, not general false-positive-rate estimate.'},
 {'id':'n03','image_sha256':'1029b7bcc1906f45e054eedc1c1c7efae2e0dee28fc02e7717cef8795dcaf23e',
  'image_review':'Readable basketball results1-12of50, Newly listed, Jason Kidd/Rocks/iTouch. Does not establish cheapest or all suit candidates.',
  'candidate':'50listings is visibly grounded. Finding suited-man item and cheapest is stated task intent; scroll through has no explicit up/down word, native down.',
  'original_verifier':'Supports50listings with the correct current header; labels remaining plans as intent.',
  'guard':'ambiguous_or_unrecognized_intent abstention; not semantic approval.',
  'outcome':'Candidate accepted without regeneration. No definite new semantic error identified in this short candidate; not a task-level no-Mirage label.'},
 {'id':'n04','image_sha256':'564e7a79f977e2d647625301b9539e73027467dad75a59a85eda7bb8f6f66848',
  'image_review':'Keyword input has clear blue outline, placeholder and no entered text. Current visible focus cue agrees with prior native click, not inferred solely from execution return.',
  'candidate':'Focused field; typebasketball, consistent with current visual focus cue and task.',
  'original_verifier':'Correctly sees blue outline and permits type this time. Different full input/prompt/development placement from earlier failed focus audit; cannot call that prior failure repaired.',
  'guard':'not_scroll; leaves native typing untouched.',
  'outcome':'Type candidate accepted without extra focus click or regeneration; GUI not executed and typed contents not observed afterward.'}
]
for row in rows:assert sha((root/'images'/(row['image_sha256']+'.png')).read_bytes())==row['image_sha256']
review={'scope':'Four distinct complete native prefixes from one known task; selected nonblind source-first development, not independent tasks/formal efficacy experiment',
        'rows':rows,'all_four_original_images_independently_viewed':True,'legal_history_reviewed':True,'private_expectations_transferred':False,
        'real_model_calls':10,'actor_calls':5,'judge_calls':5,'natural_eos_replies':10,'format_retries':0,
        'initial_definite_direction_conflicts':1,'conflicts_rejected_not_executed':1,'native_direction_recovery_after_one_regeneration':1,
        'incremental_benefit_over_original_verifier_demonstrated':False,'new_guard_only_rescues':0,
        'new_guard_checks':5,'guard_rejects':1,'guard_recognized_consistent':1,'guard_abstentions':2,'guard_other_action':1,
        'new_real_wait_control_passed':False,'wait_cpu_exclusion_only':True,'gui_actions':0,'official_scores':0,'paid_api_calls':0,
        'limits':'Original70actor/140verifier/2regen/2recapture/1format;24total development cap terminated at10, do not spend remaining14 on completed controls',
        'development_condition':'Post_only default Limits: readiness/current-target/alignment/history-report/completion probes OFF; source-bound archived frame, recapture=None. Not full live v3.9.9 trajectory.',
        'deployment_condition':'Original frozen27B/BF16/SDPA/full inputs/budgets;5GPU development placement instead of prior7GPU, no bitwise/cost equivalence claim',
        'feedback_metadata_limitation':'Legacy raw_verifier_reason_sha256 in action feedback hashes the chosen guard reason, not the separately preserved original judge reason. Before formal integration distinguish feedback origin and both hashes; no terminal edits.',
        'remaining':'Scoped footer-readiness false block, unsupported historical facts/intent confusion, real independent WAIT/negative controls and native live adapters remain outstanding; formal release false',
        'input_tokens':audit['input_tokens'],'output_tokens':audit['output_tokens'],'summed_generation_seconds':audit['summed_generation_seconds'],
        'terminal_manifest_sha256':inspection['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],'event_chains':audit['event_chains'],'formal_release':False}
out=PREP/('review-'+str(time.time_ns()));out.mkdir();(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
report=f'''# 原生方向一致性防御：新输入真实开发预检完成

防御已按最新指令恢复。本轮在隔离Controller中加入“明确滚动意图与原生direction参数矛盾”检查，接入原有预算内恢复路径，不改动作JSON，不指定方向/目标，不推断画面事实。四份此前未发送的完整原生前缀、原尺寸图片和调用前期待已冻结；推理端没有PRIVATE期待或未来候选。

共5actor＋5judge＝10次真实调用，全部自然EOS，0格式重试。4份输入均得到最终可执行候选，但没有执行GUI或官方评分。这是同一已知任务的非盲开发，不能称4个独立任务、4个语义通过或防御效力证明。

|新输入|实际结果|结论边界|
|---|---|---|
|n01正常页脚|首候选文字up/JSON down被拦，一次重新生成自然得到up/up，最终接受|原核验器本次也判contradicted，不能归因新增规则有增益；初始错误发生仍计数|
|n02列表底部|文字down/JSON down，一次通过|未因新增规则额外拦截；分页到达与任务结果未执行验证|
|n03第一页|50条结果有当前画面支持；scroll through无明确方向词，规则保守弃权，原核验器接受down|弃权不等于语义认证；找最便宜仍是计划|
|n04蓝焦点框|actor和judge均读出可见蓝框，直接typebasketball，一次通过|非scroll不干预；不同完整输入的一次正确不能抹去此前焦点误读|

n01最终句式“To view..., I need to scroll up”不在保守规则的句首模式内，因此实际日志是弃权，而不是自动认证up/up。up/up一致来自独立查看真实回复。原核验器还提到根本未提供的reference image1，并以只有页脚的当前引用支持整个“page5”断言：页脚部分成立，页码部分没有被该引用证明。合法历史有page5叙述，但这不自动是新视觉证据；不反向猜测另一页码。当前局部方向恢复没有解决核验器的来源/断言范围问题，更没有运行joint readiness门。

新增规则5次检查：1拒绝、1明确一致、2弃权、1非滚动动作。4个控制均已终局，不可用剩余14/24预算重复。未找到新的未用真实WAIT前缀，只有20项CPU测试中的WAIT排除/负例/预算流验证，不冒充新真实WAIT通过。

实际服务完整request/inputIDs/generation/outputIDs/EOS/response逐一与actor及verifier日志绑定；4条事件链共44事件验证，终局SHA {inspection['terminal_manifest_sha256']}。五张GPU的真实service.lock/资源锁、UID和完整命令以及认证health已核实。原服务精度/完整输入/2048actor/4096judge及预算不变，因其他用户占卡，新服务用0–4五卡而非原七卡，单列开发部署，不做逐位或正式成本等价假设。

累计输入{audit['input_tokens']:,}、输出{audit['output_tokens']:,}token，累计生成{audit['summed_generation_seconds']:.2f}秒；不是墙钟、货币、能耗或端到端成本。0付费API。启动路径兼容和原生import缺少DATASET的技术失败在0调用时保留原根/源码/日志及SHA，修复后用了新关联尝试，没有重跑终局。

下一步先分离反馈来源元数据（保留原verifier reason与guard reason两者），再准备正常页脚/屏外目标与真正不可解释画面的readiness边界、历史事实与计划的来源控制和独立WAIT。当前readiness、点定位、alignment、history-report、completion探针都未在此post_only开发组开启；离线图不能冒充实时回采。旧60正式配置、旧机制队列及已完成27B注意力都不重启。正式发布仍为false。
'''
rp=BASE/'原生方向一致性防御新输入预检-20261028.md';rp.write_text(report,encoding='utf-8')
seal={'review.json':sha((out/'review.json').read_bytes()),str(rp):sha(rp.read_bytes())};(out/'sha256.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2),encoding='utf-8')
pointer={'directory':str(out),'review_sha256':seal['review.json'],'report':str(rp),'report_sha256':sha(rp.read_bytes()),'remote_root':inspection['root'],'terminal_manifest_sha256':inspection['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],'calls':10,'natural_eos':10,'gui_actions':0,'formal_release':False,'incremental_benefit_demonstrated':False,'completed_controls_must_not_retry':True}
(PREP/'completed-current.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(pointer,ensure_ascii=False))
