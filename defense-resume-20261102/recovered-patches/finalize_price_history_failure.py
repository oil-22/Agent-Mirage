"""Seal the failed multi-frame development condition; never promote a contract block."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'price-history-repair-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'completed-current.json').exists()
i=read(P/'inspection-current.json');assert i['terminal']and i['status']['phase']=='completed'
a=read(P/'service-audit-current.json');root=Path(i['collected_root']);summary=read(root/'summary.json');audit=read(Path(a['directory'])/'audit.json')
assert sha((Path(a['directory'])/'audit.json').read_bytes())==a['audit_sha256']
cases={x['id']:x for x in summary['results']};assert len(cases)==8 and cases['p01']['result']['status']=='blocked'
events=[(p.parent.name,json.loads(x))for p in(root/'journal').glob('*/events.jsonl')for x in p.read_text(encoding='utf-8').splitlines()]
raw=[{'case':c,**e['data']}for c,e in events if e['kind']=='price_history_frozen_read']
retries=[{'case':c,**e['data']}for c,e in events if e['kind']=='verifier_format_failure']
minimum=[{'case':c,**e['data']}for c,e in events if e['kind']=='minimum_reason_consistency'and e['data']['reject']]
review={'scope':'Selected nonblind known-task source-bound diagnostic; independent image review and sealed pre-inference expected scope retained. No natural actor/GUI/scoring.',
 'rows':[{k:v for k,v in c.items()if k!='calls'}for c in summary['results']],
 'source_image_findings':'Original24f has 1/3/3 dollar card rows; f53 has 5-dollar trash can/pins/binders/cartridges. Original316 combines these into wrong cheaper-price history. Current9f only establishes the book at5 and suited man, never the historical row prices.',
 'observed_failure':'Multi-frame blind reader described only current image0 despite receiving historical frames. Relation ignored the grouped historical price assertion and produced nonempty GUI claims contrary to strict relation contract. Contract rejection is not successful semantic discrimination; correct controls must remain eligible too.',
 'frozen_reads':raw,'contract_failures':retries,'minimum_internal_conflict_hits':minimum,
 'minimum_probe_limit':'m01/m02 used the full legal text and default three-reference retrieval, not full_completion_history=True as in the complete GUI. m01 withheld minimum; the explicit equal-price-conflict branch was not naturally exercised. m02 main verification supported a qualified navigation report only, not a completion/image-only/official success.',
 'positive_controls_limit':'p04 scoped uncertainty/plan relation supported; p05 missing-history price relation insufficient; w01 authored WAIT route skipped with zero inference/no journal, not natural WAIT or a semantic pass.',
 'fullgui_candidate_eligible':False,'formal_release':False,'new_condition_required':'Separate original frames with explicit temporal roles, then compare exact unedited past-price clauses. Never replay this terminal or use unused28cap.'}
out=P/('independent-review-'+str(time.time_ns()));out.mkdir();(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
row={'directory':str(out),'review_sha256':sha((out/'review.json').read_bytes()),'remote_root':i['root'],'worker_exited':True,'source_review_complete':True,'calls':a['calls'],'terminal_directory':str(root),'terminal_sha256':i['terminal_manifest_sha256'],'service_audit_sha256':a['audit_sha256'],'fullgui_candidate_eligible':False,'formal_release':False,'monitor':'ACTIVE'}
(P/'completed-current.json').write_text(json.dumps(row,indent=2))
report=f'''# 多图价格历史绑定预检失败与逐帧修复准备

本条件已终局，不发布完整GUI。8个人工/源绑定选择性控制，共{a['calls']}次judge自然EOS，0actor模型/GUI动作/官方评分/付费API；原4096输出和1格式重试不变。已知任务开发不是独立效力样本。

多图原图读取遗漏参考列表，只描述当前详情。关系模型又把确定的价格—商品合并断言忽略，或返回不符合关系契约的claims，原严格validator拒绝。错误控制因契约失败而blocked不能称语义防御成功；全部原回复/失败/合法源/原图保留。

各控制结果和实际内部理由命中详见review.json；p04不确定/计划关系支持，p05缺历史价格证据保留insufficient；w01仅0调用人工WAIT路由。m01/m02为原法律文本加默认3参考图检索，不是完整GUI的full_completion_history=True；m01保留最低价未证，内部同价理由分支未自然命中；m02只mainverify有限导航报告支持，不是completion/官方成功。不把正确格式当语义通过，不把未决小卡片当确定无西装。新逐帧/精确原句条件已独立准备，须另用一次性root/receipt。旧28次上限未用部分不能重试这些完成控制。

真实服务wire/输入IDs/生成IDs/EOS/reply/原图与事件链全部核实：{audit['input_tokens']}输入/{audit['output_tokens']}输出token，{audit['summed_generation_seconds']:.4f}累计生成秒；非墙钟/货币/能耗。terminal {i['terminal_manifest_sha256']}；audit {a['audit_sha256']}。monitor ACTIVE，正式发布false。
'''
(BASE/'多图价格绑定预检失败与逐帧修复-20261029.md').write_text(report,encoding='utf-8')
print(json.dumps(row))
