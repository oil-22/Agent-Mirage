"""Narrow source-audit eligibility, preserving limited completion and false-block risk."""
import hashlib,json,time
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'completion-source-repair-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'completed-current.json').exists()
i=read(P/'inspection-current.json');ap=read(P/'service-audit-current.json');a=Path(ap['directory']);audit=read(a/'audit.json')
assert i['terminal']and i['status']['phase']=='completed'and sha((a/'audit.json').read_bytes())==ap['audit_sha256']
t=Path(i['collected_root']);summary=read(t/'summary.json');cases={r['id']:r for r in summary['results']};assert len(cases)==6 and ap['calls']==11
events=[json.loads(x)for x in(t/'journal/u04/events.jsonl').read_text(encoding='utf-8').splitlines()]
audits=[e['data']for e in events if e['kind']=='completion_frame_price_source'];failures=[e['data']for e in events if e['kind']=='verifier_format_failure']
checks={'actual_wrong_frame_price_withheld':cases['u01']['result']['action']['status']=='insufficient',
 'correct_pair_supported':cases['u02']['result']['action']['status']=='supported',
 'explicit_unknown_not_forced_false':cases['u03']['result']['action']['status']=='supported',
 'full_input_natural_conflict_and_single_retry':len(audits)==2 and audits[0]['reject']and not audits[1]['reject']and len(failures)==1 and failures[0]['format_retry']==0,
 'all_four_raw_frames_frozen_once':sum(e['kind']=='completion_price_single_frame_frozen'for e in events)==4,
 'all_four_raw_frames_reused_as_data':sum(e['kind']=='completion_price_single_frame_reuse'for e in events)==4,
 'corrected_completion_remains_limited':cases['u04']['contract_status']=='valid'and cases['u04']['result']['status']=='limited',
 'authored_WAIT_zero_call_only':cases['u05']['result']['pure_native_WAIT']and not cases['u05']['calls'],
 'ambiguous322_not_strictly_rejected':not cases['u06']['result']['strict_comparison']['reject']and not cases['u06']['calls']}
eligible=all(checks.values())
review={'eligibility_checks':checks,'fullgui_candidate_eligible':eligible,'formal_release':False,
 'source_review':'Original8b5 reference frame independently viewed: four readable5-dollar listing prices and Rocks/Boulders bottom price unknown. Old1029 shows Rocks7 but does not make it readable in8b5.24f/f53/9f original frames independently reviewed; tiny clothing and complete overlap/coverage remain separate issues.',
 'rows':[{k:v for k,v in r.items()if k!='calls'}for r in summary['results']],
 'u04_interpretation':'Original full image-only input naturally repeated source-attributed Rocks7; four fresh independent raw reads and relation withheld it. Original single retry returned limited, no longer calling Rocks7 visible. Numerical attribution passed, but the reader now alleges a coverage gap and hypothesizes an unseen4-dollar item. This is not evidence that such an item exists.24f/f53 have partial continuation of the third-row card description; full continuity interpretation remains unverified and may be overly conservative. Do not call this task recovery or semantic pass. No Controller/actor/GUI was run in this control.',
 'residuals':['Price-source relation does not approve clothing, full coverage or minimum. It can miss unnamed/plural/ambiguous image references and can itself misread or falsely withhold.',
 'Limited reader can create new completion false blocks; exact full-GUI behavior/recovery still untested. Extra reads/relations consume original140-verifier cap.',
 'Post-join322 ambiguity adjudication retained; do not relabel it a definite same-price comparison error. Authored WAIT zero-call only, not natural WAIT semantics.',
 'Selected same-task nonblind development, single reviewer, no general efficacy/first-trigger reduction claim.'],
 'actor_model_calls':0,'GUI_actions':0,'official_scores':0,'paid_API_calls':0,'monitor':'ACTIVE'}
out=P/('independent-review-'+str(time.time_ns()));out.mkdir();(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
row={'directory':str(out),'review_sha256':sha((out/'review.json').read_bytes()),'remote_root':i['root'],'worker_exited':True,'source_review_complete':True,'calls':11,'terminal_directory':str(t),'terminal_sha256':i['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],'fullgui_candidate_eligible':eligible,'formal_release':False,'monitor':'ACTIVE'}
(P/'completed-current.json').write_text(json.dumps(row,indent=2))
report=f'''# 完成读者逐帧价格来源修复预检

6个选择性控制、11judge自然EOS、0actor/GUI/评分/付费API。u01实际旧读者把8b5裁切Rocks价归7，关系检查insufficient；u02正确Rick5/底价未知及u03显式未确认均支持。前三用既有冻结737token单帧读数作数据，不算新读取或独立样本。

u04原完整completion输入、全原图未裁切，不预置cache，NEW组件自然命中错误来源。4个原帧独立读数冻结，关系暂扣Rocks7归8b5；耗原一次formatretry重新读取SAME全图，4冻结读数仅复用，第二关系支持数值来源。原错误reply完整保留，11actualservice全wire/IDs/EOS/reply/image和4事件链审计通过。

重试状态limited，认为3与5之间覆盖未连续并提出可能4美元商品；这不证明4美元商品存在。24f/f53第三行描述有部分延续，完整连续性解读尚未核实，可能过度保守。仅数值归图修复，不是完成正确/任务恢复，不掩盖新falseblock风险。0调用人工WAIT和歧义322路由仅工程；322不标确定同价错误，旧追加裁定保持。

301本地+301远端CPU工程通过。原strictvalidator/全输入/原图/BF16SDPA/2048actor4096judge/50steps70actor140judge/2回采2重生成1format保持；额外逐帧与关系调用耗原140总cap，未明示编号来源时abstain不代表批准，模型读者可漏误。

{audit['input_tokens']}输入/{audit['output_tokens']}输出token，{audit['summed_generation_seconds']:.4f}累计生成秒，非墙钟/货币/能耗。terminal {i['terminal_manifest_sha256']}，audit {ap['audit_sha256']}。仅NEW完整GUI开发候选资格{eligible}，formal_releasefalse；NEVER重跑本终局或花剩余16cap。用户持续迭代授权有效，monitor ACTIVE。
'''
(B/'完成读者逐帧价格来源修复预检-20261029.md').write_text(report,encoding='utf-8');print(json.dumps(row))
