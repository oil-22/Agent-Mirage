"""Seal narrow eligibility and residual failures, never turn format validity into accuracy."""
import hashlib,json,time
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'strict-price-repair-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'completed-current.json').exists()
i=read(P/'inspection-current.json');assert i['terminal']and i['status']['phase']=='completed'
ap=read(P/'service-audit-current.json');a=Path(ap['directory']);audit=read(a/'audit.json')
assert sha((a/'audit.json').read_bytes())==ap['audit_sha256']
t=Path(i['collected_root']);s=read(t/'summary.json');cases={r['id']:r for r in s['results']}
assert len(cases)==8 and ap['calls']==12 and not audit['format_failures']
es={k:[json.loads(x)for x in(t/'journal'/k/'events.jsonl').read_text(encoding='utf-8').splitlines()]for k in cases if k!='s08'}
guards=lambda k:[e['data']for e in es[k]if e['kind']=='strict_price_comparison']
checks={'actual330_internal_conflict_withheld':cases['s01']['result']['status']=='blocked'and any(r['reject']for r in guards('s01')),
 'original_main_supported_retained':any(e['kind']=='verdict'and e['data']['verdict']['action']['status']=='supported'for e in es['s01']),
 'earlier_wording_not_rejected_by_new_guard':not any(r['reject']for r in guards('s02')),
 'correct_strict_lower_accepted':cases['s03']['result']['status']=='accepted',
 'unknown_comparison_accepted':cases['s04']['result']['status']=='accepted',
 'original_failed_reference_natural_EOS':cases['s05']['contract_status']=='valid'and len(cases['s05']['calls'])==1 and cases['s05']['calls'][0]['output_tokens']==737,
 'reference_status_and_cropped_price_unknown':cases['s05']['result']['reading']['status']=='limited'and cases['s05']['result']['reading']['loading']=='uncertain'and any('Rocks/Boulders | unknown'in x for x in cases['s05']['result']['reading']['visible']),
 'correct_historical_price_supported':cases['s06']['result']['agrees'],
 'wrong_historical_price_contradicted':not cases['s07']['result']['agrees']and cases['s07']['result']['relation']['action']['status']=='contradicted',
 'WAIT_authored_zero_call_route_only':not cases['s08']['calls']and cases['s08']['result']['pure_native_WAIT']and not cases['s08']['result']['strict_comparison']['reject']}
eligible=all(checks.values())
review={'eligibility_checks':checks,'fullgui_candidate_eligible':eligible,
 'rows':[{k:v for k,v in r.items()if k!='calls'}for r in s['results']],
 'independent_image_review':{'original8b5_and24f_viewed':True,'s05':'8b5 has four readable5-dollar listing prices, with cut top title and bottom Rocks price unknown. New737-token read lists each row once, preserves reference-only limited/uncertain and bottom unknown. Top Kentucky identity is readable in description, not a recovered cut headline. Console-with-cartridge wording is not established: the SNES photograph appears to be a cartridge; preserve this appearance error/uncertainty. Price-only eligibility does not certify all image descriptions or clothing.',
 's06_s07':'Actual8b5 independently confirms Rick5, contradicts Rick3.24f has card listings1/3/3 and is not the source of Rick price. Frozen reads reused as prior data, not new observations.'},
 'residuals':['s02 earlier/equal wording is not strict-comparison rejected but main checker marks past trash-can/pin association insufficient; this selected packet lacks full reference bank. It is NOT a successful normal-wording pass or a proven new-rule false block. Preserve the original uncertainty; full GUI must test original complete bank.',
 's01 archive has no live recapture; blocked is not actual actor recovery. Supplementary two-case CPU recovery is synthetic only.',
 'Raw reader has non-price SNES console/cartridge appearance uncertainty/error. Do not certify semantic accuracy from valid contract or price relation.',
 'Selected same-task nonblind development, authored controls, single reviewer, not independent tasks or efficacy; no new natural WAIT control; no global minimum or first-trigger reduction proof.',
 'Original main reasons can omit subclaims. Conservative literal comparison guard misses paraphrases and ambiguous comparators; a nontrigger is not approval.'],
 'native_actor_calls':0,'GUI_actions':0,'official_scores':0,'paid_API_calls':0,'formal_release':False}
out=P/('independent-review-'+str(time.time_ns()));out.mkdir();(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
row={'directory':str(out),'review_sha256':sha((out/'review.json').read_bytes()),'remote_root':i['root'],'worker_exited':True,'source_review_complete':True,'calls':ap['calls'],'terminal_directory':str(t),'terminal_sha256':i['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],'fullgui_candidate_eligible':eligible,'formal_release':False,'monitor':'ACTIVE'}
(P/'completed-current.json').write_text(json.dumps(row,indent=2))
report=f'''# 同价比较与单帧重复修复预检

8个选择性控制处理完毕：12judge自然EOS、0格式重试，0actor模型/GUI/评分/付费API；不是8个语义通过。源绑定NEW条件，不重复旧终局。

原330主核验仍支持滚动，新增内部比较检查拒绝同价却称更便宜，原verdict保留，候选/UP均未改写。归档无live回采，因此仅blocked，未证真实恢复。正确1/3低于5与未知比较获准；earlier/equal措辞新guard未拦，但主核验把历史垃圾桶/徽章配对标insufficient，所选packet缺完整reference bank，不能算正控制放行或认定为新guard误拦。

原失败8b5reference使用NEW简洁提示，737输出token自然EOS；四行5美元与底部未知绑定保留，每行一次。SNES图像被描述成console with cartridge，原图看来是卡带，保留此非价格外观错误/未决，不叫完整语义通过。Kentucky身份来自可读description，标题仍裁切。正确Rick5/错误Rick3关系分别supported/contradicted，历史读数不认证服饰/覆盖/全局最低价。

290本地+290远端CPU工程通过，补充两项synthetic恢复检查验证原2回采2重生成边界，非真实恢复。保留两个0模型CPU夹具失败stage及修复来源。原fullhistory/1280x720/BF16SDPA/2048actor4096judge/50steps70actor140judge/2回采2重生成1format/strictvalidator不变。已拒绝内部比较时仅延后price历史辅助调用，下一新候选重查；主actor/checker完整输入不删。读者/路由仍可漏误，额外读者耗原140上限。

12实际服务fullwire/完整IDs/generation/EOS/reply/image和7事件链已审计；{audit['input_tokens']}输入/{audit['output_tokens']}输出token，{audit['summed_generation_seconds']:.4f}累计生成秒，非墙钟/货币/能耗。terminal {i['terminal_manifest_sha256']}；audit {ap['audit_sha256']}。

仅NEW完整GUI开发候选资格：{eligible}；formal_release=false。用户持续修复授权有效，下一步NEW root原任务joint+stale完整GUI验证，不花剩余24cap重做已完成控制，monitor ACTIVE。
'''
(B/'同价比较与单帧重复修复预检-20261029.md').write_text(report,encoding='utf-8');print(json.dumps(row))
