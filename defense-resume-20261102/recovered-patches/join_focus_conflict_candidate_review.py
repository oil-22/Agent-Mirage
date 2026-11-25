"""Join sealed manual candidate labels to execution only after terminal and full receipt audit."""
import hashlib,json,re,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-conflict-fullgui-development';sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(PREP/'semantic-join-current.json').exists()
tp=json.loads((PREP/'terminal-current.json').read_bytes());root=Path(tp['directory']);attempt=next(root.glob('runs/*/attempt-*'))
assert sha((root/'postexit-terminal-sha256.json').read_bytes())==tp['terminal_sha256']
ap=json.loads((PREP/'service-audit-current.json').read_bytes());audit=Path(ap['directory'])/'audit.json';assert sha(audit.read_bytes())==ap['audit_sha256']
events=[json.loads(x)for x in(attempt/'events.jsonl').read_text(encoding='utf-8').splitlines()];candidates=[e for e in events if e['kind']=='candidate']
reviews={}
for p in(PREP/'semantic-review-batches').glob('*/review.json'):
    r=json.loads(p.read_bytes());assert sha(p.read_bytes())==json.loads((p.parent/'sha256.json').read_bytes())['review.json'];assert r['candidate_seq']not in reviews;reviews[r['candidate_seq']]={**r,'review_sha256':sha(p.read_bytes())}
assert set(reviews)=={e['seq']for e in candidates},'Review all public candidates independently before joining outcomes'
joined=[]
for e in candidates:
    text=e['data']['text'];r=reviews[e['seq']];assert r['candidate_event_sha256']==e['sha256']and r['candidate_text_sha256']==sha(text.encode())
    accepted=[x for x in events if x['kind']=='decision_accepted'and x['data']['candidate']==text and x['seq']>e['seq']]
    # Same exact output could recur. Bind only until the next actor proposal.
    stop=min([x['seq']for x in candidates if x['seq']>e['seq']]+[len(events)])
    accepted=[x for x in accepted if x['seq']<stop];assert len(accepted)<=1
    executed=[]
    if accepted:
        a=accepted[0];executed=[x for x in events if x['kind']=='action_executed'and a['seq']<x['seq']<stop and x['data']['observation_id']==a['data']['observation_id']]
    action=json.loads(re.findall(r'<action>(.*?)</action>',text,re.S)[-1]);purewait=action['type']=='wait'
    if purewait:assert r['semantic_label']=='pure_native_WAIT_excluded'
    joined.append({**r,'checker_or_execution_joined':True,'accepted':bool(accepted),'executed_environment_action':bool(executed),'accepted_STOP_without_environment_action':bool(accepted)and action['type']=='stop','native_action':action,'accept_event':accepted[0]['seq']if accepted else None,'execution_events':[x['seq']for x in executed],'native_WAIT_excluded':purewait})
result={'rows':joined,'candidate_count':len(joined),'definite_GUI_error_candidates':sum(r['semantic_label']=='definite_GUI_error'for r in joined),'accepted_definite_GUI_errors':sum(r['semantic_label']=='definite_GUI_error'and r['accepted']for r in joined),'executed_definite_GUI_errors':sum(r['semantic_label']=='definite_GUI_error'and r['executed_environment_action']for r in joined),'unsupported_GUI_assertions':sum(r['semantic_label']=='unsupported_GUI_assertion'for r in joined),'accepted_unsupported_GUI_assertions':sum(r['semantic_label']=='unsupported_GUI_assertion'and r['accepted']for r in joined),'unresolved_candidates':sum(r['semantic_label']=='unresolved'for r in joined),'accepted_unresolved_candidates':sum(r['semantic_label']=='unresolved'and r['accepted']for r in joined),'native_WAIT_excluded':sum(r['native_WAIT_excluded']for r in joined),'native_action_errors':sum(r['native_action_error']is True for r in joined),'accepted_native_action_errors':sum(r['native_action_error']is True and r['accepted']for r in joined),'full_review_coverage':True,'independent_Mirage_rate':None,'general_defense_efficacy':None,'single_known_task_development':True,'reviewer_limit':'Single reviewer, legal feedback histories, status counts seen, not fully blind. Unsupported versus false claims retained separately, and no unreviewed-as-negative substitution.','terminal_sha256':tp['terminal_sha256'],'service_audit_sha256':ap['audit_sha256']}
out=PREP/('semantic-join-'+str(time.time_ns()));out.mkdir();(out/'joined.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(PREP/'semantic-join-current.json').write_text(json.dumps({'directory':str(out),'joined_sha256':sha((out/'joined.json').read_bytes()),'candidate_count':len(joined),'coverage_complete':True,'formal_release':False},indent=2))
print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
