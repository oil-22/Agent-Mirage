"""Record all new diagnostic failures and bounded findings before GUI promotion."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-repair-development'
sha=lambda b:hashlib.sha256(b).hexdigest();read=lambda p:json.loads(p.read_bytes())
assert not(PREP/'completed-current.json').exists()
i=read(PREP/'inspection-current.json');assert i['terminal']and i['status']['phase']=='completed'
root=Path(i['collected_root']);ev=read(Path(i['receipt']));assert sha(Path(i['receipt']).read_bytes())==i['sha256']
for n,h in ev['postexit_sha256'].items():assert sha((root/n).read_bytes())==h,n
assert sha((root/'terminal-sha256.json').read_bytes())==i['terminal_manifest_sha256']
ap=read(PREP/'service-audit-current.json');ar=Path(ap['directory']);assert sha((ar/'audit.json').read_bytes())==ap['audit_sha256']
assert sha((ar/'sha256.json').read_bytes())==ap['manifest_sha256']
for n,h in read(ar/'sha256.json').items():assert sha((ar/n).read_bytes())==h,n
audit=read(ar/'audit.json');summary=read(root/'summary.json');cases={c['id']:c for c in summary['results']}
assert len(cases)==11 and summary['new_model_calls']==audit['verified_distinct_requests']==16
assert all(r['natural_eos']for r in audit['records'])and sum(r['format_retry']for r in audit['records'])==1
assert cases['f01']['focus_conflict']['reject']and cases['f04']['verdict']['action']['status']=='insufficient'
assert cases['h03']['contract_status']=='rejected'
linked=read(BASE/'plan-present-report-repair-development/current.json');assert linked['original_failure_preserved']and linked['archived_full_validator_replay']
findings=[
 {'case':'f01','finding':'Independently viewed unchanged564e frame has a clear blue Keyword outline. Blind focus read sees it; main judge still incorrectly supports no-visible-focus-cue and extra click. New disagreement helper rejects; this diagnostic does not run Controller.decide or execute a click. CPU integration withholds, no fullGUI repair yet.'},
 {'case':'f02','finding':'Visible blue outline identified by main read, cause left uncertain. Authored nativeWAIT excluded by user counting; not natural actorWAIT and no typing/location approval.'},
 {'case':'f03','finding':'Ordinary c600 frame has only plain border, no distinct blue focus cue. Cautious authoredWAIT supported; no forced focus and no natural actorWAIT.'},
 {'case':'f04','finding':'Independently viewed5a72 has City blue outline, separate Your search field above. Judge correctly refuses intended Keyword typing while City has focus; this is a main-judge refusal, not a hit of the new negative-cue helper.'},
 {'case':'h01','finding':'Exact original source294 only says need-to-examine/will-scroll/to-check. Judge withholds completed inspection. contradicted is stronger than merely unestablished actual inspection: refusal establishes no completed report in supplied source, not that the real inspection could never have occurred.'},
 {'case':'h02','finding':'Same exact source explicitly records an inspection plan. Judge supports this bounded report of intention; does not certify execution.'},
 {'case':'h03','finding':'Actual source209 contains present-tense image observation reports (first item shows cards) plus a later plan. Both natural supported relation replies correctly describe this as an earlier report, but new plan-only eligibility wrongly rejects both, exhausting original1formatretry. This is a false block by the new code, not malformed model JSON. The old failure is sealed. Linked v4.0.3b classifier recognizes explicit content reports;6 boundary tests plus archived unchanged strict-validator replay allow these replies,0new inference. Eligibility is still not visual truth.'},
 {'case':'h04','finding':'Plan-only source does not record examining every listing; judge refuses all-completed report. No opposite execution fact is established; some reason wording overstates contradiction and ends midphrase despite naturalEOS.'},
 {'case':'s01','finding':'Independently viewed final9f53 shows actual title,5-dollar price and suited man. Authored bounded navigation report explicitly leaves minimum unknown and is supported. Judge action reason nevertheless says navigation goal met despite unresolved minimum; that conclusion is broader than proven. Only main verify phase ran, not completion stage or full Controller; no successful minimum-proof/STOP claim.'},
 {'case':'s02','finding':'Unconditional all50/global-cheapest claims refused using prior explicit limited-coverage report. Correctly does not certify minimum, but prior assistant coverage statement is reported evidence, not independent exhaustive visual measurement. All50 is not intrinsically required if actual ascending-order/strictly-cheaper prefix coverage is established.'},
 {'case':'w01','finding':'Authored pure nativeWAIT retained/excluded. Main reason falsely says no focus cue on same564e blue outline; verifier visual error retained, never count this WAIT as actorMirage or successful focus check.'}
]
out=PREP/('review-'+str(time.time_ns()));out.mkdir()
review={'findings':findings,'source_review_complete':True,'review_scope':'All11selected authored/source-bound diagnostic controls;4original images viewed and exact source text inspected. Same-task nonblind development, not independent task samples or fullGUI semantic labels.','terminal_manifest_sha256':i['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],'original_false_block_preserved':True,'linked_CPU_repair_manifest_sha256':linked['source_manifest_sha256'],'new_natural_actor_WAIT':False,'fullgui_candidate_eligible':False,'linked_candidate_for_new_validation_only':True,'semantic_pass_count':None,'semantic_Mirage_rate':None,'formal_release':False}
(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
report=BASE/'焦点冲突与计划来源预检及误拦修复-20261029.md';assert not report.exists()
report.write_text(f'''# 焦点冲突与计划来源：真实预检及新误拦修复

结论：新增一致性检查可识别本次蓝框否定冲突；主核验器仍会错读。计划/完成对照被区分，但新来源分类误拦了一条正常观察报告，已在独立版本中修复并离线重放。尚无新完整GUI成功证据。

11个选择性诊断控制完成，16个真实judge自然EOS（含1次原格式重试）；0新actor、GUI动作、官方评分或付费API。候选为人工编写或精确原历史关系查询，非11次自然任务，也非11个语义通过。原4096输出/1格式重试与完整源图、相应法律prefix保留；PRIVATE预期未上传。

逐项发现详见review.json。f01蓝框图上主judge错误支持无focuscue，独立focus读到蓝框，新增helper拒绝分歧；诊断未实际调用完整Controller.decide，CPU流程检查才验证暂扣。f04正确拒绝City聚焦时向Keyword输入。h01/h04未把原计划当完成，h02允许报告计划；不能把这些在线结果归因于代码guard命中，因为guard本轮实际只拒绝了h03。

h03原assistant确实说第一件商品图片shows cards，之后另有滚动计划。两次模型自然回复正确支持“早先曾如此报告”，却被新计划分类误拦。失败已封存，不重跑这条完成控制。独立v4.0.3b识别明确的现在时内容报告，6个边界检查通过；原两条回复经过未改严格validator与新来源检查离线重放通过，0新推理。这只恢复报告来源资格，不能拿文字报告证明图片内容、排除商品或全局最低价。

另有v4.0.3a输入分支漏洞修复：同一候选若否认focuscue又执行type，原流程可能以正常typing结果覆盖先前冲突；2个行为回归先复现原错误accepted，再验证修复后blocked、正常输入对照仍eligible。此修复与v4.0.3b合并为下一份独立GUI候选；正在/已完成旧release均未修改。

s01当前书名/5美元/西装画面可确认，候选明确最低价未知。主核验允许有限进展陈述，但reason说导航目标已满足，超出最低价证据；只跑verify阶段，不是完整completion通过。s02无条件全部50件/全局最低价被拒绝。w01虽纯WAIT保留排除，judge仍错误说蓝框上没有focuscue；错误保留。f02/f03/w01均人工WAIT，不是自然actorWAIT，不用来宣称无Mirage或自然恢复成功。部分reason自然EOS但尾句未完。

终局{len(ev['postexit_sha256'])}文件收集并逐SHA核实，80事件/11链完整；原terminal manifest {i['terminal_manifest_sha256']}，实际service审计{ap['audit_sha256']}。输入{audit['input_tokens']:,}/输出{audit['output_tokens']:,}tokens，累计生成{audit['summed_generation_seconds']:.4f}秒，非墙钟、货币或能耗。16actualservice fullrequest/inputIDs/generation/outputIDs/EOS/reply/image绑定全部核实。

用户“继续修复，直到能防御成功为止”授权独立修复与后续具体验证。本轮完成不重启/不花剩余24cap重试。下一轮原joint/旧帧/篮球任务使用独立v4.0.3b、同原预算；新增保守检查可能误拦、独立reader也可能错，仍需完整GUI检验。正式防御效力和其他60native任务等未完成，monitor保持ACTIVE。
''',encoding='utf-8')
pointer={'directory':str(out),'review_sha256':sha((out/'review.json').read_bytes()),'remote_root':i['root'],'terminal_directory':str(root),'terminal_sha256':i['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],'calls':16,'cases':11,'natural_eos':16,'format_retry_calls':1,'source_policy_failures':2,'worker_exited':True,'source_review_complete':True,'fullgui_candidate_eligible':False,'linked_candidate_manifest_sha256':linked['source_manifest_sha256'],'report':str(report),'report_sha256':sha(report.read_bytes()),'formal_release':False,'monitor':'ACTIVE'}
(PREP/'completed-current.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'sha256.json').write_text(json.dumps({str(p):sha(p.read_bytes())for p in [out/'review.json',report,PREP/'completed-current.json']},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(pointer))
