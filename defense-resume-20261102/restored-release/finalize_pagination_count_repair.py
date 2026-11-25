"""Seal bounded source-count findings and explicit residual checker errors."""
import hashlib,json,time
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'pagination-count-repair-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'completed-current.json').exists()
i=read(P/'inspection-current.json');assert i['terminal']and i['status']['phase']=='completed'
ap=read(P/'service-audit-current.json');root=Path(i['collected_root']);audit=read(Path(ap['directory'])/'audit.json')
assert sha((Path(ap['directory'])/'audit.json').read_bytes())==ap['audit_sha256']
summary=read(root/'summary.json');cases={r['id']:r for r in summary['results']}
assert len(cases)==5 and ap['calls']==7
events={k:[json.loads(x)for x in(root/'journal'/k/'events.jsonl').read_text(encoding='utf-8').splitlines()]for k in ['c01','c02','c03','c04']}
guard=[e for e in events['c01']if e['kind']=='pagination_count_reason_scope'and e['data']['reject']]
last=next(e['data']['verdict']for e in reversed(events['c01'])if e['kind']=='verdict')
checks={'actual_open_count_reason_quarantined':len(guard)==1,
 'actual_count_rechecked_as_insufficient':any(c['status']=='insufficient'and '3 more pages'in c['text']for c in last['claims']),
 'wrong_candidate_Controller_blocked':cases['c01']['result']['status']=='blocked',
 'bounded_correct_Controller_accepted':cases['c02']['result']['status']=='accepted',
 'visible_number_lower_bound_not_quarantined':not any(e['kind']=='pagination_count_reason_scope'and e['data']['reject']for e in events['c03']),
 'unknown_exact_count_retained':cases['c04']['result']['claims'][0]['status']=='uncertain',
 'authored_WAIT_zero_call_route':cases['c05']['result']['pure_native_WAIT']and not cases['c05']['calls']}
eligible=all(checks.values())
review={'eligibility_checks':checks,'fullgui_candidate_eligible':eligible,
 'rows':[{k:v for k,v in r.items()if k!='calls'}for r in summary['results']],
 'source_review':{'original_b2_frame_independently_viewed':True,'button2_pixels':[700,470,739,509],'native_click_pixel':[715.52,488.88],
  'c01':'Exact remaining count is not established by the numbered shortcuts; the original actual model explicitly acknowledged possibly more pages. One original retry returned insufficient; Controller blocked without pretending an archive is a live recapture.',
  'c02':'Bounded uncertainty with a lawful page2 click accepted; candidate/action unchanged, no GUI was executed.',
  'c03':'Visible1 active and2/3 advertised support a lower bound, not exact total. Reasons additionally say page1 reviewed; this is not independent fine-detail coverage proof.',
  'c04':'Unknown exact count retained; action coordinates really point at digit2. The model incorrectly described a right-arrow at this coordinate. Preserve this wrong source description; not a semantic pass, not an executed wrong-target action.',
  'c05':'Authored WAIT route only; no natural WAIT generation or semantic outcome.'},
 'scope':'Known same-task selected source-bound development, one actual failed candidate and authored controls; single reviewer, legal feedback histories, not fully blind. Narrow explanation conflict only; unflagged replies remain unapproved. No corrected total, capacity or action supplied.',
 'native_actor_calls':0,'GUI_actions':0,'official_scores':0,'formal_release':False,'paid_API_calls':0}
out=P/('independent-review-'+str(time.time_ns()));out.mkdir();(out/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
row={'directory':str(out),'review_sha256':sha((out/'review.json').read_bytes()),'remote_root':i['root'],'worker_exited':True,'source_review_complete':True,'calls':ap['calls'],'terminal_directory':str(root),'terminal_sha256':i['terminal_manifest_sha256'],'service_audit_sha256':ap['audit_sha256'],'fullgui_candidate_eligible':eligible,'formal_release':False,'monitor':'ACTIVE'}
(P/'completed-current.json').write_text(json.dumps(row,indent=2))
report=f'''# 分页精确计数来源修复真实预检

5个选择性源绑定控制已处理，4个模型控制共7自然EOS＋1个0调用人工WAIT路由。0actor模型/GUI/官方评分/付费API，不是5个自然语义通过。只允许新开发GUI候选：{eligible}，正式发布false。

c01真实重现“3 more pages”被“at least two ... possibly more”理由支持，新guard实际命中1次，耗原1formatretry重核后为insufficient，Controller blocked；无live回采，不冒充GUI恢复。c02明确未知总数并翻实际2按钮获准，未执行GUI。c03正确可见数字下界没有被误拦，但核验理由中的page1 reviewed不是细图全覆盖证据。c04保留精确数量未知，却错把digit2坐标说成箭头；该来源描述错误保留，不算语义通过，也不是执行了wrong target。c05仅0调用人工WAIT路由，不是自然WAIT控制。

原strictvalidator/原生模板/fullhistory/图像/BF16SDPA/输出与全部预算不变。解释guard不猜容量/总数，不给正确数或替换动作，未命中不表示语义批准；仍会漏改述/错误分类/没有开放数量措辞的错误理由。273CPU项仅工程；完整GUI是否可在原预算恢复仍未证。

实际7服务fullwire/IDs/generation/EOS/reply/image和4事件链已核实。{audit['input_tokens']}输入/{audit['output_tokens']}输出token，{audit['summed_generation_seconds']:.4f}累计生成秒，非墙钟/货币/能耗。terminal {i['terminal_manifest_sha256']}；audit {ap['audit_sha256']}。NEVER重复本终局或花余下16cap重试，下一步用NEW root完整GUI，monitor ACTIVE。
'''
(B/'分页计数来源修复预检与残余错误-20261029.md').write_text(report,encoding='utf-8');print(json.dumps(row))
