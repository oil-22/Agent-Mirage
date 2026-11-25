"""Replay a NEW supplementary consistency check on immutable judge replies; no inference."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
from pagination_derivation_guard import inspect_supported_claim
BASE=Path(__file__).resolve().parent;PREP=BASE/'history-carryover-development';sha=lambda b:hashlib.sha256(b).hexdigest()
ptr=json.loads((PREP/'carryover-current.json').read_bytes());root=Path(ptr['local_root']);raw=(root/'summary.json').read_bytes();summary=json.loads(raw)
observations=[json.loads(x)['data']['public']for x in(root/'journal/events.jsonl').read_text(encoding='utf-8').splitlines()if json.loads(x)['kind']=='observation'];rows=[]
for case,obs in zip(summary['results'],observations):
 rows.append({'case':case['id'],'source_observation_id':obs['observation_id'],'actual_source_image_sha256':[x['sha256']for x in obs['images']],'claims':[inspect_supported_claim(c,obs['observation_id'])for c in case['audit']['claims']]})
withheld=[(r['case'],c['claim_id'])for r in rows for c in r['claims']if c['withhold_supported_feedback']];assert withheld==[('h01','c1')]
test=subprocess.run([sys.executable,'-m','unittest','test_pagination_derivation_guard'],cwd=BASE,capture_output=True,text=True);assert test.returncode==0
out=BASE/'pagination-guard-development'/str(time.time_ns());out.mkdir(parents=True)
(out/'tests.txt').write_text(test.stdout+test.stderr,encoding='utf-8')
for name in ['pagination_derivation_guard.py','test_pagination_derivation_guard.py','replay_pagination_derivation_guard.py']:(out/name).write_bytes((BASE/name).read_bytes())
result={'source_summary_sha256':sha(raw),'source_terminal_manifest_sha256':ptr['seal']['sha256'],'rows':rows,'supplementary_guard_would_withhold_inconsistent_supported_claims':withheld,'engineering_tests':22,'new_model_calls':0,'new_gui_actions':0,'existing_verdicts_or_json_edited':False,'original_strict_validators_changed':False,'controller_integrated':False,'actor_feedback_sent':False,'trajectory_efficacy_established':False,'release_ready':False,'limits':'Nonblind post-development diagnostic. Parses a narrow positive current-page statement and only checks explicitly declared uniform-capacity arithmetic. Does not validate OCR/box semantic truth, infer page size, output a corrected page, prove unflagged claims true, or fix direction/coverage/intent errors. Existing completed trials unchanged.'}
(out/'replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
report='''# 分页推理一致性检查：新增暂存机制与真实输出回放

历史迁移审计h01把25–36/50解释成“12条/页的第4页”并给supported。本补充检查仅检查核验器自己明确给出的数值关系：正向当前页断言、当前图引用中读出的起止/总数，以及明确声明的固定每页容量。关系不相容时建议停止把该条supported当作actor反馈；不输出正确页号，不补猜容量，不改历史、原候选JSON、原strict validator或已完成结果。

22项工程测试通过。涵盖正确第3/4页、错误第4页、末页49–50/50仍按明确容量12核对、缺少容量保留不可判定、范围越界/反序、类型边界、引用错观察、历史引用、计划/否定句不误判、不修改传入对象。用本轮6份真实核验输出离线回放，仅h01/c1被标为内部矛盾；其它未标结果不代表语义通过。

这是针对已知失败的非盲开发，不是新独立测试集。原图读数是否准确、每页容量是否有真实依据仍须独立检查；该机制不能解决穿着/整页覆盖、计划误分类或文字/JSON方向冲突。0新增模型调用、0GUI、未接入Controller、未发新actor反馈；没有声称降低整体Mirage触发率。正式接入前须冻结反馈路由和原预算内处理、保留负例WAIT，再进行独立配对验证。
'''
(out/'report.md').write_text(report,encoding='utf-8');(out/'sha256.json').write_text(json.dumps({p.name:sha(p.read_bytes())for p in out.iterdir()if p.is_file()},indent=2),encoding='utf-8')
receipt={'directory':str(out),'replay_sha256':sha((out/'replay.json').read_bytes()),'manifest_sha256':sha((out/'sha256.json').read_bytes()),'engineering_tests':22,'withheld_real_claims':withheld,'model_calls':0,'release_ready':False}
(BASE/'pagination-guard-development/current.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(receipt))
