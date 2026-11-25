"""Read-only factual progress audit; never infer semantic Mirage from detector flags."""
import argparse,json,hashlib,time
from pathlib import Path
from defense.core import canonical,digest

def audit(root):
    root=Path(root);rows=[];by_arm={}
    for run in sorted((root/'runs').glob('*')):
        attempts=sorted(run.glob('attempt-*'));reused=None
        marker=run/'complete.json'
        if marker.exists():
            pointer=json.loads(marker.read_text());bound=Path(pointer['attempt'])
            assert digest((bound/'complete.json').read_bytes())==pointer['sha256'],'Completed result hash mismatch: '+str(marker)
            if bound not in attempts:attempts.append(bound);reused=bound
        for attempt in attempts:
            p=attempt/'events.jsonl';events=[];partial=False
            for line in p.read_text().splitlines()if p.exists()else []:
                try:events.append(json.loads(line))
                except json.JSONDecodeError:partial=True
            prev='0'*64;chain_ok=True
            for e in events:
                copy=dict(e);h=copy.pop('sha256');chain_ok=chain_ok and copy['previous']==prev and digest(canonical(copy))==h;prev=h
            q=attempt/'complete.json';done=json.loads(q.read_text())if q.exists()else {}
            counters={k:sum(e['kind']==k for e in events)for k in ['candidate','action_executed','recapture_requested','verifier_request','verifier_format_failure','verifier_envelope_decoded','state_invalidated','point_crosscheck','focus_crosscheck','target_alignment']}
            blocked=[e['data']for e in events if e['kind']=='decision_blocked']
            deliveries=[e['data']for e in events if e['kind']=='private_delivery_ledger'and e['data']['fired']]
            actor_requests=[e['data']for e in events if e['kind']=='actor_request']
            injection_replies=[]
            for delivery in deliveries:
                initial=next((e['data']['public']['observation_id']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'and e['data']['public']['observation_id'].startswith(f'{delivery["step"]:03}-')),None)
                injection_replies.append({'step':delivery['step'],'initial_observation':initial,'actor_calls_on_initial_injected_input':sum(x['public']['observation_id']==initial for x in actor_requests)})
            row={'run_id':run.name,'attempt':str(attempt),'completed':bool(done),'outcome':done.get('outcome'),'official_reward':done.get('official_reward'),'scoring_status':done.get('scoring_status'),'technical_status':done.get('technical_status'),'diagnostic_only':done.get('diagnostic_only',False),'counters':counters,'blocked':blocked,'injections':injection_replies,'hash_chain_ok':chain_ok,'partial_line':partial,'semantic_mirage':None,'attempt_failure':(attempt/'failure.json').exists()or(attempt/'technical-failure.json').exists(),'paused_attempt':(attempt/'paused.json').exists()}
            row['reused_from_prior_batch']=attempt==reused
            rows.append(row)
            if done:
                arm=done['run']['arm'];s=by_arm.setdefault(arm,{'completed':0,'model_stop':0,'blocked':0,'official_reward_1':0,'format_errors':0,'recaptures':0})
                s['completed']+=1;s['model_stop']+=done['outcome']=='model_stop';s['blocked']+=done['outcome']=='blocked';s['official_reward_1']+=done['official_reward']==1;s['format_errors']+=counters['verifier_format_failure'];s['recaptures']+=counters['recapture_requested']
    state=json.loads((root/'status.json').read_text())if(root/'status.json').exists()else {}
    return {'time':time.time(),'root':str(root),'status':state,'completed':sum(x['completed']for x in rows),'by_arm':by_arm,'rows':rows,'semantic_mirage':None}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root');a=ap.parse_args();print(json.dumps(audit(a.root),ensure_ascii=False,indent=2))
