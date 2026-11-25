"""Append an explicit post-join ambiguity correction; never overwrite sealed labels."""
import copy,hashlib,json,time
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'strict-price-fullgui-retry1-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'semantic-adjudication-current.json').exists()
old=read(P/'semantic-join-current.json');source=Path(old['directory'])/'joined.json';assert sha(source.read_bytes())==old['joined_sha256']
j=read(source);row=next(r for r in j['rows']if r['candidate_seq']==322)
assert row['semantic_label']=='definite_GUI_error'and row['accepted']
correction={'candidate_seq':322,'original_review_sha256':row['review_sha256'],
 'old_label':'definite_GUI_error','adjudicated_label':'unresolved',
 'reason':'The phrase cheaper items at1/3, and other5-dollar items admits a coordinate-noun-phrase interpretation: cheaper1/3 items AND separate other5 items. Other explicitly supports the separate category. It is not unambiguously a strict5-vs5 claim, unlike original330 nested cheaper-items-images parenthesis. Preserve ambiguity; do not tune a rejection rule to this sentence as a definite negative. Global minimum and tiny-image exclusions remain unresolved.',
 'post_join_outcome_exposure':True,'no_blind_adjudication_claim':True,'original_label_and_join_preserved':True,'reviewer':'Same single reviewer, careful textual reassessment after own outcome joined'}
out=P/('semantic-adjudication-'+str(time.time_ns()));out.mkdir();(out/'correction.json').write_text(json.dumps(correction,ensure_ascii=False,indent=2),encoding='utf-8')
new=copy.deepcopy(j);r=next(r for r in new['rows']if r['candidate_seq']==322);r.update(semantic_label='unresolved',original_semantic_label='definite_GUI_error',adjudication_sha256=sha((out/'correction.json').read_bytes()),adjudication_post_outcome_exposure=True)
new.update(definite_GUI_error_candidates=1,accepted_definite_GUI_errors=0,executed_definite_GUI_errors=0,unresolved_candidates=4,accepted_unresolved_candidates=4,post_join_adjudication_candidate_seqs=[322],general_defense_efficacy=None,independent_Mirage_rate=None)
(out/'adjudicated-joined.json').write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding='utf-8')
pointer={'directory':str(out),'correction_sha256':sha((out/'correction.json').read_bytes()),'adjudicated_join_sha256':sha((out/'adjudicated-joined.json').read_bytes()),'supersedes_for_semantic_interpretation':old,'original_immutable_records_retained':True,'defense_success_not_established':True,'formal_release':False,'monitor':'ACTIVE'}
(P/'semantic-adjudication-current.json').write_text(json.dumps(pointer,indent=2))
head='''# 最新2026-10-29：语义追加更正322比较歧义；正式防御成功仍未建立

优先读strict-price-fullgui-retry1-development/semantic-adjudication-current.json及其correction/adjudicated-joined.json。旧review/join/completed/report全部保持原SHA，不删除或改写。322中cheaper items at1/3, and other5-dollar items可合理解析为“更便宜的1/3商品”和“其他5商品”两个并列短语，并非确定把5说成比5便宜。将其确定错误追加更正为unresolved，不扩展guard去误拦此歧义。此复核发生在结果join之后，非盲审，必须保留该限制。

更正后11候选：1确定（79焦点，拒绝未执行），0接受确定；1来源不足未接受；4未决全部接受，其中322acceptedSTOP无环境动作；0确定native错误/WAIT。official1/8环境动作/11actor41judge52EOS保持，但未决不是无Mirage，不能叫完整防御成功/零发生。此前说322确定同价错误的判断已向用户更正。旧preflight330括号列表的明确5vs5矛盾和对应guard仍成立。

明确待修是completion读者来源越界：把8b5裁切Rocks价说成在该帧可见7，并合成未完整可读的12价序列；旧1029可见Rocks7不能作为8b5可见价格证据。下一NEW条件先准备逐帧独立冻结读数与completion逐帧价格断言关系审计，负/正确/未知/WAIT/原预算与源引用控制；不供应正确页/价格/动作，不认证最低价，不把模型不确定性标definite。不要重跑任何旧终局或未改条件的已完成控制。

root strict-price-joint-stale-fullgui-retry1-1793261436045020832已退出；原terminal4d3d72608c788f88d6ea6a87a69a41c431a605bbc7c91f155d059089c4edae88/audit72583a39c03e375b51476e27f12ae088dd505daca64a1e0b3ab45e60fed27786和所有原预算/图像/fullhistory/precision/strictvalidator保持。用户持续迭代授权有效，monitor ACTIVE/formal_releasefalse，服务3090UID1033原五卡锁不重启，旧注意力/机制/UI队列不重启，不碰外资源/GPU5/6/7。

--- 以下为前序交接（含已更正的旧解释，以上述追加裁定为准）---

'''
backup=out/'handoffs';backup.mkdir();receipts=[]
for n,p in enumerate([B/'README.md',B/'REPAIR_HANDOFF.md',B.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
    raw=p.read_bytes();f=backup/(str(n)+'-'+p.name);f.write_bytes(raw);p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8');receipts.append({'path':str(p),'backup':str(f),'before_sha256':sha(raw),'after_sha256':sha(p.read_bytes())})
(backup/'receipt.json').write_text(json.dumps(receipts,indent=2))
(B/'完成断言语义追加复核与来源修复-20261029.md').write_text(head+'\n追加裁定SHA '+pointer['correction_sha256']+'\n',encoding='utf-8');print(json.dumps(pointer))
