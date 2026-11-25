"""Link only the frozen slots to their real wires, screenshots, decisions and scores."""

import argparse
import hashlib
import json
import time
from pathlib import Path

from collect import HERE, measurement_version, manifest_for, read, save, sha, stages
from extract_on_host import canonical, hx, unique


def verify(directory):
    seal = read(directory/'seal.json')
    for name, digest in seal.items():
        assert Path(name).name == name and sha(directory/name) == digest, (directory, name)


CHECKER = ('precheck_decision', 'capture_receipt_decision', 'gate_decision')


def link_stage(record):
    version = record['version']
    stage = record.get('stage_id', version)
    assert version == measurement_version(stage)
    ptr, _, _ = manifest_for(stage)
    assert (record['manifest_sha256'], record['plan_sha256']) == (ptr['manifest_sha256'], ptr['plan_sha256'])
    for receipt in record['transport'].values():
        operation = Path(receipt['operation'])
        assert sha(operation/'seal.json') == receipt['seal_sha256']
        verify(operation)
    base=record.get('base_audit')
    if base:
        prior=Path(base['previous_collection'])
        assert sha(prior/'seal.json')==base['seal_sha256']
        assert sha(prior/(stage+'.json'))==base['previous_version_file_sha256']
    gui, model = (record['hosts'][h] for h in ('4090','3090'))
    out = {}
    messages = model['public_legal_messages']
    assert all(hx(canonical(v)) == d for d,v in messages.items())
    for run, tape in gui['runs'].items():
        terminal = tape['terminal']
        end = model['run_end'].get(run)
        if end is None:
            assert terminal['infrastructure_failure'] and tape['end_notification_failed'], run
        else:
            assert end['terminal_sha256'] == tape['terminal_sha256'], run
            assert end['manual_stop'] == (terminal['outcome']=='manually_stopped'), run
            assert end['infrastructure_failure'] == terminal['infrastructure_failure'], run
        enabled = terminal['run']['gate_enabled']
        main_receipts = unique(tape['actor_receipts'],lambda r:r['request_id'])
        gate_receipts = unique(tape['flash_replies'],lambda r:r['request_id'])
        assert set(gate_receipts) == {r for r,x in model['flash'].items() if x['run']==run}, run
        assert enabled or not gate_receipts
        observed = sorted(tape['rows'],key=lambda r:r['step'])
        last_public=None
        previous_selected=None
        previous_action=None
        seen_requests, seen_gate, frame_ids, challenges = set(),set(),set(),set()
        for row in observed:
            n=row['step']; q=row['request']; s=row['submit']; rc=row['reply']; frames=row['frames']; gates=row['gates']
            by_capture=unique(frames,lambda f:f['capture_id'])
            initial=next((f for f in frames if f['capture_kind']=='initial'),None)
            for f in frames:
                assert f['capture_id'] not in frame_ids and f['challenge'] not in challenges, (run,n)
                frame_ids.add(f['capture_id']);challenges.add(f['challenge'])
            for g in gates:
                if g['event'] in CHECKER:
                    assert enabled and by_capture[g['capture_id']]['delivered_sha256']==g['image_sha256'], (run,n,g['event'])
                if g['event']=='gate_decision':
                    rid = g['request_id']
                    f = model['flash'][rid]; received=gate_receipts[rid]
                    assert rid not in seen_gate and f['run']==run
                    assert g['image_sha256']==f['image_sha256']==received['image_sha256']
                    assert g['decision']==f['decision']==received['decision']
                    seen_gate.add(rid)
                    g['Flash_seal_sha256']=f['seal_sha256']
                    g['Flash_probabilities']=f['probabilities']
            chosen = by_capture[s['capture_id']] if s else None
            if s:
                forwarded=[g for g in gates if g['event']=='main_image_forwarded']
                assert len(forwarded)==1 and forwarded[0]['capture_id']==s['capture_id']
                assert forwarded[0]['image_sha256']==s['image_sha256']==chosen['delivered_sha256']
                assert s['current_image_present']==(chosen['delivered_sha256'] is not None)
                assert not forwarded[0]['extra_auxiliary_text_in_main_prompt']
                if enabled:
                    assert any(g['event']=='gate_decision' and g['decision']=='YES' and g['capture_id']==s['capture_id']
                               and g['request_id']==forwarded[0]['gate_request_id'] for g in gates), (run,n)
                else:
                    assert forwarded[0]['gate_request_id'] is None
            m=None
            if q:
                rid=q['request_id']; assert s and rid not in seen_requests
                seen_requests.add(rid)
                m=model['requests'].get(rid)
                if m is None:
                    assert rc is None and terminal['infrastructure_failure'], (run,n)
                else:
                    ordered=m['messages_ordered']
                    assert m['run']==run and m['step']==n and q['body_sha256']==m['body_sha256']
                    assert q['history_messages']==len(ordered)==2*n
                    assert m['current_image_sha256']==s['image_sha256']
                    if last_public:
                        assert ordered[:-1]==last_public, (run,n,'full model history')
                    if rc:
                        assert rc['request_id']==rid and rc['receipt']==m['runtime_request_directory']
                        assert rc['text_sha256']==m['reply_sha256'] and m['natural_EOS']
                        assert hx(m['reply_text'].encode())==m['reply_sha256']
                        assert main_receipts[rid]['wire_sha256']==m['wire_sha256']
                        assistant={'role':'assistant','content':m['reply_text']}
                        last_public=ordered+[hx(canonical(assistant))]
                    else:
                        assert terminal['infrastructure_failure'], (run,n)
            if row['proposal']:
                prop=row['proposal']
                assert rc and prop['candidate_sha256']==rc['text_sha256'] and prop['capture_id']==s['capture_id']
                assert prop['image_sha256']==s['image_sha256']
                assert prop['environment_action']==bool(row['executed'])
            actual=bool(m and m['actual_forward'] and (m['forward_calls'] or 0)>=1)
            trigger = bool(initial and initial['injected'])
            changed = trigger and initial['captured_sha256']!=initial['delivered_sha256']
            if trigger and terminal['run']['condition'] in ('silent_drop','blank_replace','stale_replace'):
                assert previous_selected is not None and previous_action is not None, (run,n)
                assert previous_action['type'] in ('click','type','press','back','tab')
                assert previous_selected['delivered_sha256'] is not None
                assert initial['captured_sha256']!=previous_selected['delivered_sha256'], (run,n)
                if terminal['run']['condition']=='stale_replace':
                    assert initial['delivered_sha256']==previous_selected['delivered_sha256'], (run,n)
                if terminal['run']['condition']=='silent_drop':
                    assert initial['delivered_sha256'] is None
            bad_at_forward = bool(changed and actual and chosen['capture_id']==initial['capture_id'])
            initial_rejections = [g for g in gates if initial and g.get('capture_id')==initial['capture_id']
                                  and g['event'] in CHECKER and g['decision']=='NO']
            assert len(initial_rejections)<=1
            rejection=initial_rejections[0] if initial_rejections else None
            if changed and rejection:
                assert not bad_at_forward
                assert any(g['event']=='recapture_requested' and g['from_capture_id']==initial['capture_id']
                           for g in gates) or not actual, (run,n)
            same_live = []
            for f in frames:
                if f['capture_kind']!='recapture':
                    continue
                assert initial and all(f[k]==initial[k] for k in ('session_id','environment_id','action_sequence'))
                assert f['capture_index']>initial['capture_index'] and f['acquired_at_ns']>=initial['acquired_at_ns']
                assert not f['injected'] and f['delivered_sha256']==f['captured_sha256']
                same_live.append(f['capture_id'])
            restored = bool(changed and rejection and actual and chosen['capture_id'] in same_live)
            since=row['start']['initial_ready_monotonic_ns']
            wait=(s['submit_monotonic_ns']-since) if s else None
            terminal_wait=((row['finish']['ended_monotonic_ns']-since) if not s and row['finish'] else None)
            row.update({'main':m,'actual_first_forward':actual,'triggered':trigger,'altered_bytes':changed,
                        'known_injected_dose_at_first_forward':bad_at_forward,
                        'initial_rejection_event':rejection['event'] if rejection else None,
                        'same_decision_signed_recaptures':same_live,
                        'recapture_at_actual_forward_needs_visual_review':restored,
                        'first_frame_to_actor_ns':wait,'withheld_until_observation_end_ns':terminal_wait})
            if restored:
                assert chosen['delivered_sha256'] is not None
            previous_selected=chosen
            previous_action=row['executed']['payload'] if row['executed'] else None
        assert set(main_receipts) == {row['reply']['request_id'] for row in observed if row['reply']}
        assert set(model['requests']).issuperset(seen_requests) or terminal['infrastructure_failure']
        assert seen_gate == set(gate_receipts) or terminal['infrastructure_failure']
        assert {rid for rid,x in model['requests'].items() if x['run']==run} <= seen_requests
        assert sum(row['triggered'] for row in observed) <= 1
        if terminal['injection_fired'] is not None:
            assert terminal['injection_fired'] == any(row['triggered'] for row in observed)
        if terminal['actor_calls'] is not None:
            assert terminal['actor_calls']==len(seen_requests)
        out[run]={'version':version,'stage_id':stage,'terminal':terminal,'gui_attempt':tape['attempt'],
                  'terminal_sha256':tape['terminal_sha256'],'model_run_end_bound':end is not None,
                  'official_score_bound':tape['native_official_receipt_matches'],
                  'controller_head':tape['controller_head'],'source_head':tape['source_head'],'steps':observed}
    return out, messages, gui['live_unsealed']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('collections',nargs='+',type=Path,help='Supply later snapshots last; only the latest supplied snapshot for each version is used.')
    a=p.parse_args()
    _,_,queue=manifest_for('BF16-original')
    supplied={}
    for c in map(Path.resolve,a.collections):
        verify(c)
        snapshots=read(c/'index.json')
        assert not any('reader_error' in row for row in snapshots.values()), c
        for version in snapshots:
            previous=supplied.get(version)
            if previous:
                old=read(previous/(version+'.json'))['hosts']['4090']['runs']
                new=read(c/(version+'.json'))['hosts']['4090']['runs']
                assert old.keys()<=new.keys()
                assert all(x['terminal_sha256']==new[r]['terminal_sha256'] for r,x in old.items())
            supplied[version]=c
    out={}; public={}; active={}
    catalog=stages()
    assert supplied.keys() <= catalog.keys()
    for stage,(_,start,end) in catalog.items():
        if stage not in supplied:
            continue
        stage_rows, msg, live=link_stage(read(supplied[stage]/(stage+'.json')))
        allowed={r['run_id'] for r in queue[start:end]}
        assert set(stage_rows)|set(live) <= allowed and not out.keys() & stage_rows.keys()
        out.update(stage_rows);public.update(msg);active[stage]=live
    stage_order=[s for s,(_,i,j) in catalog.items() for _ in range(i,j)]
    assert len(stage_order)==len(queue)==100
    rows=[]
    for slot,stage in zip(queue,stage_order):
        version=measurement_version(stage)
        run=slot['run_id']; tape=out.get(run)
        if tape:
            assert tape['terminal']['run']==slot and tape['version']==version and tape['stage_id']==stage
        status=('verified_terminal' if tape else 'started_awaiting_seal' if run in active.get(stage,[])
                else 'not_started_at_collection' if stage in supplied else 'version_not_collected')
        rows.append({'slot':slot,'version':version,'stage_id':stage,'status':status,'evidence':tape})
    dst=HERE/'ledgers'/str(time.time_ns())
    dst.mkdir(parents=True,exist_ok=False)
    sources={v:{'path':str(c),'seal_sha256':sha(c/'seal.json')} for v,c in supplied.items()}
    save(dst/'private-linked.json',{'collections':sources,'rows':rows,
         'public_legal_messages':public,'independent_semantic_audit_joined':False})
    save(dst/'seal.json',{'private-linked.json':sha(dst/'private-linked.json')})
    scored=sum(t['official_score_bound'] for t in out.values())
    print(json.dumps({'ledger':str(dst),'slots':len(rows),'cross_host_terminals':sum(t['model_run_end_bound'] for t in out.values()),
                      'retained_technical_or_other_unscored':len(out)-scored,'officially_scored':scored}))


if __name__=='__main__':
    main()
