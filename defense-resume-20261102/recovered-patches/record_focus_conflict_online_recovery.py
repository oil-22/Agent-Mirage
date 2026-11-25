"""Freeze the observed online interception/recovery without claiming trial completion."""
import hashlib,json,time
from pathlib import Path
from remote import remote
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-fullgui-development';sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(PREP/'focus-recovery-online-current.json').exists()
launch=json.loads((PREP/'fullgui-launch-current.json').read_bytes())
code=r'''
import hashlib,json
from pathlib import Path
a=next(Path(ROOT).glob('runs/*/attempt-*'));head='0'*64;events=[]
for line in(a/'events.jsonl').read_text().splitlines():
 try:e=json.loads(line)
 except json.JSONDecodeError:break
 d={k:v for k,v in e.items()if k!='sha256'};assert e['previous']==head and hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==e['sha256'];head=e['sha256'];events.append(e)
lookup={e['seq']:e for e in events}
assert lookup[73]['kind']=='candidate'and lookup[86]['kind']=='focus_absence_consistency'and lookup[86]['data']['reject']
assert lookup[96]['kind']=='state_invalidated'and any(x.get('execution_status')=='rejected_not_executed'and x.get('rejected_candidate_sha256')==hashlib.sha256(lookup[73]['data']['text'].encode()).hexdigest()for x in lookup[96]['data']['corrections'])
assert lookup[111]['kind']=='candidate'and lookup[127]['data']['recaptures']==lookup[127]['data']['regenerations']==2
assert lookup[128]['kind']=='action_executed'and lookup[128]['data']['proposal']['name']=='type'
print(json.dumps({'root':ROOT,'events':[lookup[n]for n in [44,56,58,73,79,86,95,96,111,127,128]],'verified_chain_prefix_events':len(events),'verified_chain_prefix_head':head,'not_terminal':True,'semantic_labels_joined':False}))
'''
row=json.loads(remote('ROOT='+repr(launch['root'])+'\n'+code,host='4090',timeout=40))
out=PREP/('focus-recovery-online-'+str(time.time_ns()));out.mkdir();(out/'evidence.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
pointer={'directory':str(out),'evidence_sha256':sha((out/'evidence.json').read_bytes()),'root':launch['root'],'explicit_negative_focus_candidate_rejected':73,'rule_hit':86,'correct_typing_executed':128,'original_local_budget_used':{'recaptures':2,'regenerations':2},'not_terminal':True,'already_reported_to_user':True,'general_focus_or_defense_success':False,'monitor':'ACTIVE'}
(PREP/'focus-recovery-online-current.json').write_text(json.dumps(pointer,indent=2))
head='''# 最新在线进展2026-10-29：新focus一致性已真实拦截并在原预算内恢复；整轮仍运行

先读focus-conflict-fullgui-development/focus-recovery-online-current.json与最新inspection-current.json。新v4.0.3b完整GUI仍运行，NEVER再次launch。事件44在实际提供的旧c600普通边框上断言已focus，主judge虽错误支持，独立focus56不确认，原流程58拦未执行。真实回采564e蓝框后candidate73明确错误否定focusoutline，主judge95仍支持且误当hypothesis；新一致性86真实reject，96明确rejected_not_executed，额外点击没有执行。随后candidate111正确读蓝框，127/128在原2recapture2regeneration内accepted/type实际执行，下一帧25c9确见basketball。不是0候选错误/首次触发降低，不抹去73已发生错误；44源证据不足不等于实际GUI一定未focus。三候选人工独立图/法律source标签已在执行join前封存，后续完整标签仍待完成。此新局部结果已向用户报告，不重复通知。整轮搜索/历史/比较/STOP/评分未终局，不能宣称防御整体成功，monitorACTIVE。

--- 以下为前序最新交接 ---

'''
backup=out/'handoffs';backup.mkdir();rows=[]
for j,p in enumerate([BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
    raw=p.read_bytes();bp=backup/(str(j)+'-'+p.name);bp.write_bytes(raw);p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8');rows.append({'path':str(p),'backup':str(bp),'before_sha256':sha(raw),'after_sha256':sha(p.read_bytes())})
(backup/'receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(pointer))
