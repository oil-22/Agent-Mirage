"""Independent source, wire, temporal-route and actual delivery audit for the holdout."""

import argparse
from collections import Counter
from math import comb
from pathlib import Path

from audit_panel import chain, event, only, timing, verify_flash, verify_frames, verify_main
from audit_toggle import audit_ownership, checked_controls, verify_origin, verify_seal
from audit_truth import BAD, POSITIVE, classify
from live_common import load, save, sha
from scoped_evidence import anchor, assess

HERE=Path(__file__).resolve().parent
ARMS=('stock','repair')
KINDS=('quality','temporal','toggle_check','primary')


def verify_policy(case, plan, rows, frames, flash, action, old, terminal, controls):
    scope=None
    binding, click, dispatch, records=controls
    if action:
        raw, packet=records[old]
        scope=anchor(binding,click,dispatch,raw,packet)
        assert event(rows,'click_scope')==[{'anchor':scope,'capture_id':old}]
    else:
        assert not event(rows,'click_scope')
    assert not event(rows,'trusted_static_boundary')
    windows={w['stage']:w for w in event(rows,'study_window_started')}
    assert list(windows)==(['initial','post_action'] if action else ['initial'])
    policies, holds, acceptances, per_frame = {}, {}, {}, {}
    kinds={'temporal_policy':policies,'withhold_and_recapture':holds,'gate_accepted':acceptances}
    for k,dest in kinds.items():
        for r in event(rows,k):
            assert r['capture_id'] not in dest; dest[r['capture_id']]=r
    assert list(holds.values())==terminal['holds']
    assert len(acceptances)==int(bool(old))+int(bool(terminal['delivery']))
    for f in flash:
        per_frame.setdefault(f['capture_id'],[]).append(f)
    assert set(per_frame)|set(policies)|set(holds)|set(acceptances) <= frames.keys()
    assert all(w['end_ns']-w['start_ns']==int(plan['observation_seconds']*1e9) for w in windows.values())
    if action:
        assert windows['post_action']['start_ns']==action['send_end_ns']
    stops=event(rows,'study_window_closed')
    if terminal['status'].endswith('_observation_window_ended'):
        close=only(stops)
        assert close['status']==terminal['status'] and close['fail_open'] is False
        assert close['closed_ns']>=close['end_ns']==windows[close['stage']]['end_ns']
    else:
        assert not stops or terminal['status']=='operator_stopped'

    previous=None; seen=set(); last_hold=None
    for cap, f in frames.items():
        post=bool(f['action_sequence']);stage='post_action' if post else 'initial'
        w=windows[stage]; a=acceptances.get(cap); hold=holds.get(cap); policy=policies.get(cap)
        calls=per_frame.get(cap,[]); modes=[r['kind'] for r in calls]
        stamp=f['finished_ns']
        assert w['start_ns']<=f['started_ns']<=stamp
        if last_hold:
            assert last_hold[0]==stage and f['started_ns']-last_hold[1]>=int(plan['recapture_seconds']*1e9)
            last_hold=None
        if stamp>=w['end_ns']:
            assert not any((a,hold,policy,calls)) and only(stops)['capture_id']==cap
        for call in calls:
            assert stamp<=call['started_ns']<=call['finished_ns']
            stamp=call['finished_ns']
        authenticated=f['presence']==f['receipt']=='YES'
        permit=authenticated
        q=calls[-1] if modes and modes[-1]=='quality' else None
        if not authenticated:
            previous=None
            assert not calls and not policy
        elif not post:
            assert modes in ([],['quality']) and not policy
        elif not policy:
            assert not (calls or a or hold) and only(stops)['capture_id']==cap
        else:
            expected, detail, specific_call=None,None,None
            if case['arm']=='stock' or scope=='plain_click':
                expected='general_temporal'
                assert modes in (['temporal'],['temporal','quality'])
                specific_call=calls[0]
            elif scope!='bound_toggle':
                expected='unverifiable_click'
            elif previous is None:
                expected='await_second_signed_capture'
            else:
                frecord, signed=zip(*(records[x] for x in (old,previous,cap)),strict=True)
                detail=assess(binding,click,dispatch,frecord,signed)
                if not detail['eligible']:
                    expected=detail['reason']
                elif f['candidate_sha'] in seen:
                    expected='already_checked_same_png'
                elif len(seen)>=plan['max_distinct_target_questions']:
                    expected='distinct_check_limit'
                elif not calls:
                    expected='window_before_specialized_call'
                    assert not a and only(stops)['capture_id']==cap
                else:
                    expected='specialized_temporal'
                    assert modes in (['toggle_check'],['toggle_check','quality'])
                    specific_call=calls[0]; seen.add(f['candidate_sha'])
            if specific_call is None:
                assert not calls
            permit=bool(specific_call and specific_call['decision']=='YES')
            assert policy=={'capture_id':cap,'arm':case['arm'],'anchor':scope,'previous_authentic_capture_id':previous,
                            'route':expected,'scope':detail,'request_id':specific_call['request_id'] if specific_call else None,
                            'proceed_to_quality':permit}
            previous=cap
        if q:
            assert permit
        if hold:
            assert not a and hold['stage']==stage and hold['sha256']==f['candidate_sha']
            assert hold['action_repeated'] is False and hold['sleep_seconds']==plan['recapture_seconds']
            if f['presence']=='NO':
                why='image_presence_NO'
            elif not authenticated:
                why='receipt_NO'
            elif post and not permit:
                why='temporal_pending_or_unsupported'
            else:
                why='single_image_quality_NO';assert q and q['decision']=='NO'
            assert hold['reason']==why
            last_hold=(stage,stamp)
        if a:
            assert a['stage']==stage and permit and q and q['decision']=='YES'
            assert a['quality_request_id']==q['request_id'] and a['window_end_ns']==w['end_ns']
            assert stamp<=a['accepted_ns']<w['end_ns']
    delivery=terminal['delivery']
    if old:
        assert acceptances[old]['stage']=='initial' and acceptances[old]['accepted_ns']<=action['send_begin_ns']
    if delivery:
        a=acceptances[delivery['capture_id']]
        assert a['stage']=='post_action' and a['accepted_ns']==delivery['gate_accepted_ns']
        assert a['quality_request_id']==delivery['last_quality_request_id']
    assert terminal['calls']=={key: int(delivery is not None) if key=='primary' else sum(f['kind']==key for f in flash) for key in KINDS}
    return holds, policies, scope


def verify_case(root, case, plan, template, origin, models, lease, expected=None):
    folder=root/'run'/'episodes'/case['id']; src=root/'run'/'source'/case['id']
    term=load(folder/'terminal.json'); head, rows=chain(folder/'events.jsonl')
    assert head==term['journal_head'] and len(rows)==term['events'] and sha(folder/'events.jsonl')==term['journal_sha256']
    assert rows[-1]['kind']=='terminal' and rows[-1]['data']=={k:v for k,v in term.items() if k not in ('journal_head','journal_sha256','events')}
    if expected is not None:
        assert rows[-1]['data']==expected
    assert term['case']==case and term['session']==only(event(rows,'session'))['session_id']
    frames,action,old=verify_frames(folder,src,case,rows,term,origin,plan['viewport'],classify=classify)
    controls=checked_controls(src,frames,action)
    asked,replies=event(rows,'flash_requested'),event(rows,'flash_replied')
    assert term['flash']==replies
    flash=[verify_flash(root,q,a,frames,old,action,models['flash'],lease) for q,a in zip(replies,asked,strict=True)]
    main, current=verify_main(root,template,case,rows,term,frames,old,action,models['primary'],lease)
    held, policies, scope=verify_policy(case,plan,rows,frames,flash,action,old,term,controls)
    post=[f for f in frames.values() if f['action_sequence']==1]; first=post[0] if post else None
    ready=next((f for f in post if f['truth']=='ready'),None)
    delivery=term['delivery']
    return {'id':case['id'],'case':case,'session_id':term['session'],'status':term['status'],'journal_head':head,
            'frames':list(frames.values()),'flash':flash,'calls':term['calls'],'action':action,'anchor':scope,'initial':frames.get(old),
            'holds':[{**data,'truth':frames[c]['truth']} for c,data in held.items()],'policies':list(policies.values()),
            'first':first,'first_ready':ready,'first_ready_withheld':bool(ready and ready['capture_id'] in held),
            'delivery':current,'main':main,'post_gate_seconds':(delivery['gate_accepted_ns']-action['send_end_ns'])/1e9 if delivery else None}


def outcome(r):
    return (r.get('delivery') or {}).get('truth')


def recovered_early(r):
    first=r['first'];current=r['delivery']
    return bool(first and first['truth']=='early' and current and current['truth']=='ready' and
                current['capture_id']!=first['capture_id'] and any(h['capture_id']==first['capture_id'] for h in r['holds']))


def summaries(rows, plan):
    by={}
    for arm in ARMS:
        sub=[r for r in rows if r['case']['arm']==arm]
        normal=[r for r in sub if r['case']['scenario'] in POSITIVE]
        by_scenario={}
        for g in sorted({c['scenario'] for c in plan['cases']}):
            p=[r for r in sub if r['case']['scenario']==g]
            kinds=Counter(outcome(r) or 'no_delivery' for r in p)
            by_scenario[g]={'settled':len(p),'results':dict(kinds),
                            'early_first':sum(bool(r['first'] and r['first']['truth']=='early') for r in p),
                            'early_to_ready':sum(recovered_early(r) for r in p)}
        elapsed=[r['post_gate_seconds'] for r in normal if outcome(r)=='ready']
        by[arm]={'completed':len(sub),'positive_planned':12,'negative_planned':6,'positive_settled':len(normal),
                 'ready_delivered':sum(outcome(r)=='ready' for r in normal),
                 'first_ready_seen':sum(r['first_ready'] is not None for r in normal),
                 'first_ready_withheld':sum(r['first_ready_withheld'] for r in normal),
                 'normal_ready_but_never_delivered':sum(r['first_ready'] is not None and outcome(r)!='ready' for r in normal),
                 'bad_deliveries':sum(outcome(r) in BAD for r in sub),'unresolved_deliveries':sum(outcome(r)=='ambiguous' for r in sub),
                 'natural_early_seen_first':sum(bool(r['first'] and r['first']['truth']=='early') for r in normal),
                 'authentic_early_recovery':sum(recovered_early(r) for r in normal),
                 'early_delivery':sum(outcome(r)=='early' for r in sub),
                 'negative_delivery':sum(r['case']['scenario'] not in POSITIVE and r['delivery'] is not None for r in sub),
                 'output_eos':sum(bool(r['main'] and r['main']['natural_eos']) for r in sub),
                 'ready_latency':timing(elapsed),'by_scenario':by_scenario,
                 'specialized_calls':sum(r['calls']['toggle_check'] for r in sub),
                 'specialized_NO':sum(f['decision']=='NO' for r in sub for f in r['flash'] if f['kind']=='toggle_check'),
                 'technical_missing_or_unstarted':plan['cases_by_arm'][arm]-len(sub)}
    return by


def compare(rows, plan):
    pairs=[]
    idx={(r['case']['group'],r['case']['arm']):r for r in rows}
    for group in sorted({c['group'] for c in plan['cases']}):
        stock, repair=[idx.get((group,a)) for a in ARMS]
        condition=only(c for c in plan['cases'] if c['group']==group and c['arm']=='stock')
        matched=bool(stock and repair and all(x['initial'] and x['action'] for x in (stock,repair)) and
                     stock['initial']['candidate_sha']==repair['initial']['candidate_sha'] and
                     stock['action']['native_action']==repair['action']['native_action'])
        facts={x['case']['arm']:outcome(x) for x in (stock,repair) if x}
        clocks={x['case']['arm']:x['post_gate_seconds'] for x in (stock,repair) if x}
        old,new=facts.get('stock'),facts.get('repair')
        pairs.append({'group':group,'scenario':condition['scenario'],'normal':condition['scenario'] in POSITIVE,'matched':matched,
                      'outcomes':facts,'seconds_to_delivery':clocks,
                      'new_ready_delivery':matched and new=='ready' and old not in ('ready','ambiguous'),
                      'lost_ready_delivery':matched and old=='ready' and new!='ready',
                      'new_bad_delivery':matched and new in BAD and old not in BAD,
                      'real_early_recovery':{x['case']['arm']:recovered_early(x) for x in (stock,repair) if x}})
    return pairs


def audit(root):
    m, remote=verify_seal(root)
    assert m['mode']==m['stage']=='live' and m['max_primary_calls']==36 and m['retries_of_model_or_action']==0
    plan, template=load(root/'live_plan.json'),load(root/'actor-template.json')
    assert len(plan['cases'])==len({c['id'] for c in plan['cases']})==36 and plan['cases_by_arm']=={'stock':18,'repair':18}
    assert plan['max_distinct_target_questions']==2
    assert sha(root/'live_plan.json')==sha(HERE/'heldout-plan.json')
    assert m['probe_audit_sha256']==sha(HERE/'probe-audit.json') and load(HERE/'probe-audit.json')['preflight_qualified']
    for key in ('preflight','probe'):
        p=root.parent/m[key]
        assert sha(p/'local-seal.json')==m[key+'_seal_sha256']
        verify_seal(p)
    q=load(root/'cpu-qualification.json')
    assert q['passed'] and q['preflight_seal_sha256']==m['preflight_seal_sha256']
    assert all(sha(root/('live_plan.json' if n=='heldout-plan.json' else n))==h for n,h in q['files'].items())
    top=load(root/'run'/'terminal.json');planned=[c['id'] for c in plan['cases']]
    by_id={r['case']['id']:r for r in top['sessions']}
    assert list(by_id)==planned[:len(by_id)] and len(by_id)==len(top['sessions'])
    assert top['planned_episodes']==36 and top['official_score_calls']==top['paid_API_calls']==top['old_queues_launched']==0
    ended=top['status']=='completed_panel'
    if ended:
        assert remote['exit_status']==0 and not top['error'] and len(by_id)==top['attempted_episodes']==36
        assert set(planned)=={p.name for p in (root/'run'/'episodes').iterdir() if p.is_dir()}
    origin=verify_origin(root)
    lease,models,release=audit_ownership(root,m,plan,top)
    if ended:
        assert load(root/'run/source/exit.json')=={'browser_exit':0,'identity':origin['browser']}
    rows, captures, sessions=[],set(),set()
    counts=Counter(dict.fromkeys(KINDS,0)); seen={'primary':set(),'flash':set()}
    for c in plan['cases']:
        if c['id'] not in by_id:
            continue
        r=verify_case(root,c,plan,template,origin,models,lease,by_id[c['id']])
        f={x['capture_id'] for x in r['frames']}
        assert not captures & f and r['session_id'] not in sessions
        captures|=f;sessions.add(r['session_id']);counts.update(r['calls'])
        for role,records in (('primary',[r['main']] if r['main'] else []),('flash',r['flash'])):
            ids={x['request_id'] for x in records}
            assert len(ids)==len(records) and not ids & seen[role]
            seen[role]|=ids
        rows.append(r)
    assert dict(counts)==top['completed_sessions_call_counts']
    for role, expected in seen.items():
        for leaf in ('start','result'):
            observed={p.parent.name for p in (root/'run'/role).glob('*/'+leaf+'.json')}
            assert observed==expected if ended else expected<=observed
    by=summaries(rows,plan);pairs=compare(rows,plan)
    helped=sum(p['new_ready_delivery'] for p in pairs if p['normal']);lost=sum(p['lost_ready_delivery'] for p in pairs if p['normal'])
    bad=by['repair']['bad_deliveries']; ambiguous=by['repair']['unresolved_deliveries']
    qualified=bool(ended and all(p['matched'] for p in pairs) and by['repair']['ready_delivered']==12 and helped>=2 and not lost
                   and not bad and not ambiguous and by['repair']['authentic_early_recovery']>0)
    n=helped+lost
    p_value=min(1,2*sum(comb(n,j) for j in range(min(helped,lost)+1))/2**n) if n else None
    return {'attempt':root.as_posix(),'status':top['status'],'source_wire_prequalification_pending_original_review':qualified,
            'input_manifest_sha256':sha(root/'manifest.json'),'raw_postexit_seal_sha256':sha(root/'local-seal.json'),
            'audited_episodes':len(rows),'signed_captures':len(captures),'by_arm':by,'pairs':pairs,'paired_positives':{
                'repair_better':helped,'repair_worse':lost,'exact_two_sided_binomial_McNemar':p_value},
            'model_calls':dict(counts),'old_queues_launched':top['old_queues_launched'],'official_score_calls':top['official_score_calls'],
            'paid_API_calls':top['paid_API_calls'],'resource_release':release,'model_loads':models,'lease':lease,'episodes':rows}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('attempt',type=Path);ap.add_argument('--out',required=True,type=Path)
    cli=ap.parse_args();result=audit(cli.attempt.resolve());save(cli.out,result)
    print(result['status'],result['model_calls'],result['paired_positives'],result['source_wire_prequalification_pending_original_review'])
