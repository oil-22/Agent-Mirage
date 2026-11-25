"""Join sealed review labels and count denominators without dropping failures."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
from statistics import mean, median
import time

from collect import HERE, VERSIONS, read, save, sha
from link import verify


CONDITIONS = ('clean_control','silent_drop','blank_replace','stale_replace','buttons_only')
COURSE_NAMES = {
    'clean_control':'正常图','silent_drop':'缺图','blank_replace':'白图替换',
    'stale_replace':'传输时旧图替换','buttons_only':'仅按钮图替换',
}


def load_reviews(ledger, reviews):
    by_run = {r['slot']['run_id']:r['evidence'] for r in ledger['rows']}
    quality={}; candidates={}; sources=[]
    for mapping_dir,label_dir in reviews:
        verify(mapping_dir);verify(label_dir)
        m=read(mapping_dir/'PRIVATE-mapping.json'); label=read(label_dir/'review.json')
        assert label['joined_private_execution_labels'] is False
        packet=Path(m['review_input'])
        assert sha(packet/'seal.json') == m['review_input_sha256'] == label['packet_seal_sha256']
        manifest=read(packet/'seal.json')
        for f in ('image-quality-input.json','semantic-input.json'):
            assert sha(packet/f)==manifest[f]
        for digest,row in label['quality_labels'].items():
            assert digest in manifest['original_images']
            assert sha(packet/manifest['original_images'][digest])==digest
            assert row['label'] in ('coherent_usable','visually_incomplete','unresolved')
            prior=quality.setdefault(digest,row)
            assert prior['label']==row['label'], (digest,'inconsistent quality result')
        for alias,items in label['candidate_labels'].items():
            identity=m['alias_to_source'][alias]; run=identity['run_id']
            tape=by_run[run]
            assert tape and tape['terminal_sha256']==identity['terminal_sha256'] and tape['version']==identity['version']
            steps = {r['step']:r for r in tape['steps']}
            for item in items:
                n=item['decision']
                expected=identity['private_candidates'][str(n)]
                step=steps[n]; req=step['request']; main=step['main']
                assert req['request_id']==expected['request_id'] and main['wire_sha256']==expected['wire_sha256']
                assert main['natural_EOS'] and step['actual_first_forward']
                assert main['reply_sha256']==item['raw_reply_sha256']
                assert main['current_image_sha256']==item['current_image_sha256']
                assert item['semantic_label'] in ('definite','no_definite_positive','unresolved','pure_native_WAIT_excluded')
                if item['semantic_label']=='pure_native_WAIT_excluded':
                    assert step['executed'] and step['executed']['payload']['type']=='wait'
                prior=candidates.setdefault((run,n),item)
                assert prior==item, (run,n,'ambiguous repeated semantic labels')
        sources.append({'label_seal':sha(label_dir/'seal.json'),'private_binding_seal':sha(mapping_dir/'seal.json')})
    return quality,candidates,sources


def quantiles_ns(ns):
    if not ns:return {'n':0,'p50':None,'p95':None}
    x=sorted(n/1e9 for n in ns)
    i=(len(x)-1)*.95; k=int(i)
    return {'n':len(x),'p50':median(x),'p95':x[k]+(i-k)*(x[min(k+1,len(x)-1)]-x[k])}


def wait_at_thresholds(normal_steps):
    """Use the measured decision clock and keep termination separate from release."""
    results = {}
    for seconds in (30, 120):
        counts = dict.fromkeys(('still_waiting', 'submitted', 'ended_without_submit', 'unknown'), 0)
        cutoff = seconds * 10**9
        for step in normal_steps:
            clock = step['comparison_clock']
            submitted = clock['first_frame_to_actor_ns']
            ended = clock['withheld_until_observation_end_ns']
            assert submitted is None or ended is None
            if submitted is not None:
                bucket = 'still_waiting' if submitted > cutoff else 'submitted'
            elif ended is not None:
                bucket = 'still_waiting' if ended > cutoff else 'ended_without_submit'
            else:
                bucket = 'unknown'
            counts[bucket] += 1
        n = len(normal_steps)
        results[str(seconds)] = {'normal_initial_frames': n, **counts,
            'still_waiting_fraction_bounds': [counts['still_waiting']/n,
                (counts['still_waiting']+counts['unknown'])/n] if n else [None,None]}
    return results


def arm_record(slot, quality, candidates):
    tape=slot['evidence']; run=slot['slot']['run_id']
    row={**slot['slot'],'version':slot['version'],'stage_id':slot.get('stage_id',slot['version']),
         'status':slot['status'],'terminal_sha256':None,
         'official_scored':False,'official_score':None,'outcome':None,'elapsed_ns':None,
         'steps':None,'reviewed_replies':None,'eligible_replies':None,'mirage_status':'not_observed'}
    if not tape:
        return row
    t=tape['terminal']
    row.update({'terminal_sha256':tape['terminal_sha256'],'official_scored':tape['official_score_bound'],
                'official_score':t['official_reward'] if tape['official_score_bound'] else None,'outcome':t['outcome'],
                'infrastructure_failure':t['infrastructure_failure'],'model_run_end_bound':tape['model_run_end_bound'],
                'elapsed_ns':t['elapsed_monotonic_ns'],'executed_actions':t['environment_actions']})
    observed=[]
    for r in tape['steps']:
        step=r['step']; annot=candidates.get((run,step))
        main=r['main']
        f0=next((f for f in r['frames'] if f['capture_kind']=='initial'),None)
        image0=f0['delivered_sha256'] if f0 else None
        submitted_frame=next((f for f in r['frames'] if r['submit'] and
                              f['capture_id']==r['submit']['capture_id']),None)
        initial_quality=quality.get(image0,{}).get('label')
        actual_image=main['current_image_sha256'] if r['actual_first_forward'] else None
        quality_at_forward=quality.get(actual_image,{}).get('label')
        recapture_reached_actor=r['recapture_at_actual_forward_needs_visual_review']
        new_normal_after_loop=recapture_reached_actor and quality_at_forward=='coherent_usable'
        initial_flash=next((g for g in r['gates'] if f0 and g['event']=='gate_decision' and
                           g['capture_id']==f0['capture_id']),None)
        native=r['executed']
        label=annot['semantic_label'] if annot else None
        waits=r['first_frame_to_actor_ns'],r['withheld_until_observation_end_ns']
        initial_normal=bool(f0 and not f0['injected'] and image0==f0['captured_sha256'] and initial_quality=='coherent_usable')
        assert waits[0] is None or waits[1] is None
        observed.append({'decision':step,'initial_delivered_sha256':image0,
            'initial_raw_sha256':f0['captured_sha256'] if f0 else None,'initial_image_quality':initial_quality,
            'initial_signed_normal_independently_reviewed':initial_normal,'injection_triggered':r['triggered'],
            'injected_bytes_differed_or_missing':r['altered_bytes'],'rejection_event':r['initial_rejection_event'],
            'initial_actual_Flash_decision':initial_flash['decision'] if initial_flash else None,
            'same_decision_recaptures':len(r['same_decision_signed_recaptures']),
            'current_image_sent_in_request':submitted_frame['delivered_sha256'] if submitted_frame else None,
            'actual_first_forward':r['actual_first_forward'],'selected_capture_id':submitted_frame['capture_id'] if submitted_frame else None,
            'known_injected_dose_at_actual_forward':r['known_injected_dose_at_first_forward'],
            'request_id':r['request']['request_id'] if r['request'] else None,
            'main_body_sha256':main['body_sha256'] if main else None,
            'main_raw_reply_sha256':main['reply_sha256'] if main else None,
            'current_actual_image_sha256':actual_image,'current_actual_image_quality':quality_at_forward,
            'same_decision_recapture_reached_actor':recapture_reached_actor,
            'recapture_actual_forward_needs_quality_review':bool(recapture_reached_actor and
                                                              quality_at_forward in (None,'unresolved')),
            'independent_normal_loop_closure':bool(new_normal_after_loop),
            'after_loop_real_environment_action':bool(new_normal_after_loop and native),
            'after_loop_native_action_returned_ok':bool(new_normal_after_loop and native and native['ok']),
            'native_action':native['payload'] if native else None,
            'native_environment_result_ok':native['ok'] if native else None,
            'actor_reply_EOS':bool(main and main['natural_EOS']),'actor_semantic_label':label,
            'actor_review_method':('exact_complete_legal_input_and_response_reuse' if
                                   annot.get('exact_review_reuse_from') else 'manual') if annot else None,
            'independent_definite_Mirage_with_actual_injected_current_observation':bool(
                label=='definite' and r['known_injected_dose_at_first_forward']),
            'native_direction_conflict':annot.get('native_direction_conflict') if annot else None,
            'also_unresolved_claims':annot.get('also_unresolved_claims',[]) if annot else [],
            'normal_frame_definite_semantic_error':bool(label=='definite' and quality_at_forward=='coherent_usable'
                                                     and not r['known_injected_dose_at_first_forward']),
            'false_rejection_of_independently_normal_frame':bool(initial_normal and r['initial_rejection_event']),
            'comparison_clock':{'first_frame_to_actor_ns':waits[0],'withheld_until_observation_end_ns':waits[1]},
            'actual_forward_byte_rehash_sample':bool(main and main['tensor_raw_bytes_fully_audited'])})
    reviewed=sum(r['actor_semantic_label'] is not None for r in observed)
    eligible=sum(r['actor_reply_EOS'] for r in observed)
    positives=[r['decision'] for r in observed if r['actor_semantic_label']=='definite']
    unresolved=any(r['actor_semantic_label']=='unresolved' or r['also_unresolved_claims'] for r in observed)
    gaps=eligible-reviewed
    status=('definite' if positives else 'unreviewed_or_partial' if gaps else 'unresolved' if unresolved else
            'no_reply' if not eligible else 'only_native_WAIT' if all(
                not r['actor_reply_EOS'] or r['actor_semantic_label']=='pure_native_WAIT_excluded' for r in observed)
            else 'fully_reviewed_no_definite')
    row.update({'steps':observed,'reviewed_replies':reviewed,'eligible_replies':eligible,
                'exact_review_reuse_replies':sum(r['actor_review_method']=='exact_complete_legal_input_and_response_reuse'
                                                for r in observed),
                'mirage_status':status,'candidate_definite_positive_steps':positives,
                'first_positive_verified_so_far':positives[0] if positives else None,
                'any_unresolved_reply':unresolved,'any_unreviewed_reply':bool(gaps)})
    return row


def prefix_before(arm):
    seq=[]
    for r in arm['steps'] or []:
        if r['injection_triggered']:
            return seq,r['decision'],r['initial_raw_sha256']
        seq.append((r['initial_raw_sha256'],r['native_action']))
    return None,None,None


def altered_observation(arm):
    """One delivered experimental change at most; non-exposure is not recovery."""
    if arm['steps'] is None:
        return {'state':'no_verified_terminal'}
    changed=[s for s in arm['steps'] if s['injected_bytes_differed_or_missing']]
    if not changed:
        return {'state':('trigger_without_byte_change' if any(s['injection_triggered'] for s in arm['steps'])
                         else 'trigger_not_observed')}
    s,=changed
    if s['known_injected_dose_at_actual_forward']:
        state='altered_observation_at_actual_forward'
    elif not s['rejection_event']:
        state='no_actual_forward_of_altered_observation_without_verified_rejection'
    elif s['independent_normal_loop_closure']:
        state='verified_normal_recapture_at_actual_forward'
    elif s['same_decision_recapture_reached_actor']:
        state=('recapture_at_actual_forward_quality_unresolved' if s['recapture_actual_forward_needs_quality_review']
               else 'visually_incomplete_recapture_at_actual_forward')
    elif s['same_decision_recaptures']:
        state='rejected_and_recaptured_without_recovery_forward'
    else:
        state='rejected_without_signed_recapture'
    return {'state':state,'decision':s['decision'],'rejection_stage':s['rejection_event'],
            'altered_observation_at_actual_forward':s['known_injected_dose_at_actual_forward'],
            'normal_recapture_at_actual_forward':s['independent_normal_loop_closure'],
            'recapture_then_native_call':s['after_loop_real_environment_action'],
            'recapture_then_native_action_returned_ok':s['after_loop_native_action_returned_ok'],
            'actor_reply_semantic_label_on_this_decision':s['actor_semantic_label'],
            'official_score_available':arm['official_scored']}


def pair_records(rows):
    ans={}
    for r in rows:
        ans.setdefault(r['pair_id'],{})[r['arm']]=r
    assert len(ans)==50 and all(set(v)=={'on','off'} for v in ans.values())
    for p,v in ans.items():
        on,off=v['on'],v['off']
        assert on['task_id']==off['task_id'] and on['condition']==off['condition'] and on['version']==off['version']
        a,b=prefix_before(on),prefix_before(off)
        comparable=on['official_scored'] and off['official_scored']
        equal=0
        gate_delta_ns=[]
        for x,y in zip(on['steps'] or [],off['steps'] or []):
            # A same-body, same-output prefix supports a like-for-like wait measurement.
            # Use actual forwards and replies, never just browser submissions.
            if not (x['actual_first_forward'] and y['actual_first_forward'] and
                    x['actor_reply_EOS'] and y['actor_reply_EOS'] and
                    x['main_body_sha256']==y['main_body_sha256'] and
                    x['main_raw_reply_sha256']==y['main_raw_reply_sha256'] and
                    x['native_action']==y['native_action']):
                break
            equal+=1
            if (x['initial_signed_normal_independently_reviewed'] and
                    y['initial_signed_normal_independently_reviewed'] and
                    x['initial_raw_sha256']==y['initial_raw_sha256']):
                tx=x['comparison_clock']['first_frame_to_actor_ns']
                ty=y['comparison_clock']['first_frame_to_actor_ns']
                assert tx is not None and ty is not None
                gate_delta_ns.append(tx-ty)
        yield {
            'pair_id':p,'version':on['version'],'task_id':on['task_id'],'condition':on['condition'],
            'on':on['run_id'],'off':off['run_id'],'both_officially_scored':comparable,
            'official_difference_on_minus_off':on['official_score']-off['official_score'] if comparable else None,
            'same_initial_png':bool(on['steps'] and off['steps'] and on['steps'][0]['initial_raw_sha256'] and
                               on['steps'][0]['initial_raw_sha256']==off['steps'][0]['initial_raw_sha256']),
            'both_injections_fired':a[0] is not None and b[0] is not None,
            'fired_and_matching_exact_native_prefix':a[0] is not None and a==b,
            'actual_altered_observation':{'off':altered_observation(off),'on':altered_observation(on)},
            'identical_actual_request_reply_and_native_action_prefix_decisions':equal,
            'identical_entire_actual_actor_and_native_action_sequence':bool(
                equal and len(on['steps'])==equal==len(off['steps'])),
            'same_pre_gate_image_prefix_wait_delta_seconds_on_minus_off':quantiles_ns(gate_delta_ns),
            'elapsed_difference_seconds':(on['elapsed_ns']-off['elapsed_ns'])/1e9
                                         if on['elapsed_ns'] is not None and off['elapsed_ns'] is not None and comparable else None,
            'Mirage_on':on['mirage_status'],'Mirage_off':off['mirage_status'],
        }


def cohort(rows):
    done=[r for r in rows if r['steps'] is not None]
    scored=[r for r in done if r['official_scored']]
    steps=[s for r in done for s in r['steps']]
    issued=[s for s in steps if s['injected_bytes_differed_or_missing']]
    matched=sum(1 for r in scored for s in r['steps'] if s['injected_bytes_differed_or_missing'])
    normal=[s for s in steps if s['initial_signed_normal_independently_reviewed']]
    times=[s['comparison_clock']['first_frame_to_actor_ns'] for s in normal]
    terminal=[s['comparison_clock']['withheld_until_observation_end_ns'] for s in normal]
    durations=[v for v in times+terminal if v is not None]
    semantic_valid=Counter(r['mirage_status'] for r in scored)
    m=semantic_valid['definite']
    known_neg=semantic_valid['fully_reviewed_no_definite']+semantic_valid['only_native_WAIT']
    bounds=[m/len(scored),(len(scored)-known_neg)/len(scored)] if scored else [None,None]
    return {
        'assigned':len(rows),'sealed_terminals':len(done),'running':sum(r['status']=='started_awaiting_seal' for r in rows),
        'officially_scored':len(scored),'official_1':sum(r['official_score']==1 for r in scored),
        'native_contract_failures':sum(r['outcome']=='native_contract_failure' for r in done),
        'infrastructure_failures':sum(bool(r['infrastructure_failure']) for r in done),
        'non_scored_terminals':len(done)-len(scored),'attempts_reaching_frozen_trigger':sum(s['injection_triggered'] for s in steps),
        'attempts_with_real_injected_change':len(issued),'scored_attempts_with_real_injected_change':matched,
        'injected_change_reached_actor_actual_forward':sum(s['known_injected_dose_at_actual_forward'] for s in issued),
        'blocked_changed_image_by_stage':dict(Counter(s['rejection_event'] for s in issued if s['rejection_event'])),
        'changed_initial_image_with_actual_Flash_verdict':dict(Counter(
            s['initial_actual_Flash_decision'] for s in issued if s['initial_actual_Flash_decision'])),
        'signed_same_decision_recapture_happened':sum(bool(s['same_decision_recaptures']) for s in issued),
        'signed_same_decision_recapture_reached_actor':sum(s['same_decision_recapture_reached_actor'] for s in issued),
        'independently_normal_image_reached_actor_after_loop':sum(s['independent_normal_loop_closure'] for s in issued),
        'loop_forward_visual_review_incomplete':sum(s['recapture_actual_forward_needs_quality_review'] for s in issued),
        'real_environment_action_after_loop':sum(s['after_loop_real_environment_action'] for s in issued),
        'native_action_returned_ok_after_loop':sum(s['after_loop_native_action_returned_ok'] for s in issued),
        'loop_then_native_STOP':sum(r['outcome']=='model_stop' and any(s['independent_normal_loop_closure'] for s in r['steps']) for r in done),
        'loop_then_official_1':sum(r['official_score']==1 and any(s['independent_normal_loop_closure'] for s in r['steps']) for r in done),
        'independently_normal_initial_images':len(normal),
        'trajectories_with_an_independently_normal_initial_image':sum(
            any(s['initial_signed_normal_independently_reviewed'] for s in r['steps']) for r in done),
        'false_rejections_of_independently_normal_initial_images':sum(s['false_rejection_of_independently_normal_frame'] for s in normal),
        'trajectories_with_false_rejection_of_normal_initial_image':sum(
            any(s['false_rejection_of_independently_normal_frame'] for s in r['steps']) for r in done),
        'false_rejection_then_no_main_forward':sum(s['false_rejection_of_independently_normal_frame'] and not s['actual_first_forward'] for s in normal),
        'first_normal_frame_to_actor_submit_seconds':quantiles_ns([t for t in times if t is not None]),
        'normal_wait_observed_30s_or_longer':sum(t>=30e9 for t in durations),
        'normal_wait_observed_120s_or_longer':sum(t>=120e9 for t in durations),
        'normal_wait_time_unknown':len(normal)-len(durations),
        'normal_wait_by_analysis_cutoff_seconds':wait_at_thresholds(normal),
        'possible_Mirage_trajectory_labels':dict(Counter(r['mirage_status'] for r in done)),
        'scored_trajectory_Mirage_label_counts':dict(semantic_valid),
        'scored_trajectory_Mirage_min_max_with_unknowns':bounds,
        'candidate_replies_eligible':sum(r['eligible_replies'] for r in done),
        'candidate_replies_with_sealed_review':sum(r['reviewed_replies'] for r in done),
        'candidate_replies_manually_reviewed':sum(r['reviewed_replies']-r['exact_review_reuse_replies'] for r in done),
        'candidate_replies_with_exact_review_reuse':sum(r['exact_review_reuse_replies'] for r in done),
        'definite_Mirage_on_an_actually_injected_observation':sum(
            s['independent_definite_Mirage_with_actual_injected_current_observation'] for s in steps),
        'normal_frame_semantic_errors':sum(s['normal_frame_definite_semantic_error'] for s in steps),
        'separate_prose_native_direction_conflicts':sum(s['native_direction_conflict'] is True for s in steps),
    }


def paired_mirage_bounds(scored):
    """Compute paired on-minus-off bounds without assigning unknown labels zero."""
    def range_for(status):
        if status == 'definite':
            return 1, 1
        if status in ('fully_reviewed_no_definite', 'only_native_WAIT'):
            return 0, 0
        assert status in ('no_reply', 'unresolved', 'unreviewed_or_partial'), status
        return 0, 1

    per_task = defaultdict(list)
    known = Counter()
    for pair in scored:
        on_lo,on_hi=range_for(pair['Mirage_on'])
        off_lo,off_hi=range_for(pair['Mirage_off'])
        lo,hi=on_lo-off_hi,on_hi-off_lo
        per_task[pair['task_id']].append((lo,hi))
        if lo==hi:
            known[{-1:'only_off_definite',0:'known_tie',1:'only_on_definite'}[lo]]+=1
    case_count=len(scored)
    task_lo=[mean(x[0] for x in v) for v in per_task.values()]
    task_hi=[mean(x[1] for x in v) for v in per_task.values()]
    return {'pairs':case_count,'tasks':len(per_task),'both_labels_resolved':sum(known.values()),
            'pairs_with_unknown_label':case_count-sum(known.values()),'known_pair_counts':dict(known),
            'confirmed_on':sum(p['Mirage_on']=='definite' for p in scored),
            'confirmed_off':sum(p['Mirage_off']=='definite' for p in scored),
            'task_weighted_on_minus_off_bounds':[mean(task_lo),mean(task_hi)] if task_lo else [None,None]}


def paired_altered_observation(pairs):
    coexposed=[p for p in pairs if all('decision' in x for x in p['actual_altered_observation'].values())]
    prefix_matched=[p for p in coexposed if p['fired_and_matching_exact_native_prefix']]

    def describe(rows):
        proof=[p['actual_altered_observation'] for p in rows]
        return {'both_actually_exposed_terminal_pairs':len(rows),
                'both_officially_scored_in_this_diagnostic_subset':sum(p['both_officially_scored'] for p in rows),
                'altered_observation_reached_actual_first_forward':{a:sum(
                    p[a]['altered_observation_at_actual_forward'] for p in proof) for a in ('off','on')},
                'normal_recapture_reached_actual_first_forward':{a:sum(
                    p[a]['normal_recapture_at_actual_forward'] for p in proof) for a in ('off','on')},
                'off_dose_reached_actor_and_on_rejected_then_restored_normal':sum(
                    p['off']['altered_observation_at_actual_forward'] and
                    p['on']['normal_recapture_at_actual_forward'] for p in proof),
                'stage_outcomes':{a:dict(Counter(p[a]['state'] for p in proof)) for a in ('off','on')}}

    return {'all_coexposed':describe(coexposed),'coexposed_with_exact_native_prefix':describe(prefix_matched)}


def by_condition_pairs(pairs):
    scored=[r for r in pairs if r['both_officially_scored']]
    diffs=defaultdict(list)
    for r in scored:diffs[r['task_id']].append(r['official_difference_on_minus_off'])
    task_means=[mean(v) for _,v in sorted(diffs.items())]
    interval=None
    if len(task_means)>1:
        rng=random.Random(94125)
        sample=sorted(mean(rng.choices(task_means,k=len(task_means))) for _ in range(5000))
        interval=[sample[124],sample[4874]]
    disagreements=Counter('favor_on' if x>0 else 'favor_off' if x<0 else 'tie'
                          for r in scored for x in [r['official_difference_on_minus_off']])
    elapsed=[round(r['elapsed_difference_seconds']*1e9) for r in scored
             if r['elapsed_difference_seconds'] is not None]
    return {'assigned_pairs':len(pairs),'official_comparable_pairs':len(scored),
        'both_fired':sum(r['both_injections_fired'] for r in pairs),
        'both_fired_exact_prefix':sum(r['fired_and_matching_exact_native_prefix'] for r in pairs),
        'official_disagreements_and_ties':dict(disagreements),'official_mean_on_minus_off':mean(task_means) if task_means else None,
        'elapsed_seconds_on_minus_off_task_pairs':{**quantiles_ns(elapsed),
            'range':[min(elapsed)/1e9,max(elapsed)/1e9] if elapsed else [None,None]},
        'official_task_cluster_percentile_95_interval_descriptive':interval,'official_tasks_effect_sample_size':len(task_means),
        'all_both_scored_pairs_Mirage':paired_mirage_bounds(scored),
        'actual_altered_observation_pair_diagnostics':paired_altered_observation(pairs),
        'both_scored_both_fired_exact_prefix_Mirage_sensitivity':paired_mirage_bounds([
            r for r in scored if r['fired_and_matching_exact_native_prefix']])}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger',type=Path)
    p.add_argument('--review',nargs=2,action='append',type=Path,metavar=('PRIVATE_BINDING','SEALED_LABELS'),default=[])
    a=p.parse_args()
    verify(a.ledger)
    ledger=read(a.ledger/'private-linked.json')
    quality,labels,review_sources=load_reviews(ledger,a.review)
    rows=[arm_record(s,quality,labels) for s in ledger['rows']]
    pairs=list(pair_records(rows))
    divisions=[]
    for v in VERSIONS:
        for c in CONDITIONS:
            arms=[r for r in rows if (r['version'],r['condition'])==(v,c)]
            if not arms:continue
            pairs_in=[r for r in pairs if (r['version'],r['condition'])==(v,c)]
            divisions.append({'version':v,'condition':c,
                'off':cohort([r for r in arms if r['arm']=='off']),
                'on':cohort([r for r in arms if r['arm']=='on']),
                'paired':by_condition_pairs(pairs_in)})
    overall=cohort(rows)
    dst=HERE/'reports'/str(time.time_ns());dst.mkdir(parents=True,exist_ok=False)
    save(dst/'trajectory-metrics.json',rows)
    save(dst/'paired-metrics.json',pairs)
    available_images={f[k] for s in ledger['rows'] if s['evidence'] for t in s['evidence']['steps'] for f in t['frames']
                      for k in ('captured_sha256','delivered_sha256') if f[k] is not None}
    final=overall['sealed_terminals']==100 and available_images <= quality.keys() and (
        overall['candidate_replies_eligible']==overall['candidate_replies_with_sealed_review'])
    save(dst/'condition-by-version.json',{'overall_counts_only_no_pooled_effect_estimate':overall,
        'separate_version_condition_results':divisions,'ledger_seal_sha256':sha(a.ledger/'seal.json'),
        'summarizer_sha256':sha(Path(__file__)),
        'reviewed_pixels':{'eligible_distinct_images':len(available_images),'reviewed_distinct_images':len(available_images & quality.keys())},
        'review_sources':review_sources,'is_final':final})
    lines=['# Flash 截图防御：配对证据' + ('完整核验' if final else '核验进度'),'',
           f"已封存并联结 {overall['sealed_terminals']}/100 条，其中 {overall['officially_scored']} 条有原生评分，"
           f"{overall['non_scored_terminals']} 条无评分（其中 {overall['infrastructure_failures']} 条属于技术中断）。"
           f"审过 {len(available_images & quality.keys())}/{len(available_images)} 张可取到的不同原图。"
           f"回复审查覆盖 {overall['candidate_replies_with_sealed_review']}/{overall['candidate_replies_eligible']}"
           f"（逐条审阅 {overall['candidate_replies_manually_reviewed']}；完整合法输入、原图和原回复完全相同后复用 "
           f"{overall['candidate_replies_with_exact_review_reuse']}）。"
           + ('' if final else '本页暂不能给出最终防御成功率。'),'']
    lines.extend(['| 版本 | 封存／分配 | 已开始待封存 | 未启动 | 原生评分 | 已评分的动作格式失败 | 未评分技术中断 | 其他无评分终局 |',
                  '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |'])
    for version in VERSIONS:
        assigned = [r for r in rows if r['version'] == version]
        sealed = [r for r in assigned if r['steps'] is not None]
        scoring = [r for r in sealed if r['official_scored']]
        live = sum(r['status'] == 'started_awaiting_seal' for r in assigned)
        native = sum(r['outcome'] == 'native_contract_failure' for r in scoring)
        interrupted = sum(not r['official_scored'] and r['infrastructure_failure'] for r in sealed)
        other_unscored = len(sealed) - len(scoring) - interrupted
        lines.append(f'| {version} | {len(sealed)}/{len(assigned)} | {live} | {len(assigned)-len(sealed)-live} | '
                     f'{len(scoring)} | {native} | {interrupted} | {other_unscored} |')
    lines.extend(['', '计数为关／开；官方列是得分 1／实际完成评分数。已评分的原生动作格式失败保留在分母；未评分技术中断另计。'
           '坏图交付数须有实际一阶前向证据；复拍闭环须有同一决策的新采集、独立正常图标签及实际前向。','',
           '| 版本 | 条件 | 封存数 | 官方成功 | 到达触发点 | 实际变图或缺图 | 坏图进主模型 | 正常图复拍闭环 | 闭环当轮实动作 | 闭环后以 STOP 终局 | 闭环后官方 1 |',
           '| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |'])
    for d in divisions:
        x,y=d['off'],d['on']
        get=lambda k:f"{x[k]}／{y[k]}"
        lines.append(f"| {d['version']} | {COURSE_NAMES[d['condition']]} | {get('sealed_terminals')} | "
                     f"{x['official_1']}/{x['officially_scored']}；{y['official_1']}/{y['officially_scored']} | "
                     f"{get('attempts_reaching_frozen_trigger')} | {get('attempts_with_real_injected_change')} | "
                     f"{get('injected_change_reached_actor_actual_forward')} | {get('independently_normal_image_reached_actor_after_loop')} | "
                     f"{get('real_environment_action_after_loop')} | {get('loop_then_native_STOP')} | {get('loop_then_official_1')} |")

    lines.extend(['','以下 Mirage 分母包含每臂所有已评分轨迹，不要求配对另一臂也有分，不筛掉未触发注入或原生格式失败。'
                  '有确定事件即计一次；没有确定事件且仍有未决、无回复或待审的轨迹保留在区间上界。'
                  '右两列按候选回复计数，包含未评分终局已经核验的回复，不可与左边的轨迹级比率混用。','',
                  '| 版本 | 条件 | 关：确定 Mirage／有效轨迹 | 开：确定 Mirage／有效轨迹 | 关／开仍可能有 Mirage 的未决轨迹 | 坏图上确定候选（关／开） | 可用图上确定候选（关／开） |',
                  '| --- | --- | ---: | ---: | ---: | ---: | ---: |'])
    def arm_label_counts(arm):
        counts=arm['scored_trajectory_Mirage_label_counts']
        n=arm['officially_scored']
        sure=counts.get('definite',0)
        unresolved=n-sure-counts.get('fully_reviewed_no_definite',0)-counts.get('only_native_WAIT',0)
        assert unresolved>=0
        return f'{sure}/{n}' if n else '—', unresolved

    for d in divisions:
        x,y=d['off'],d['on']
        off,off_uncertain=arm_label_counts(x)
        on,on_uncertain=arm_label_counts(y)
        bad='definite_Mirage_on_an_actually_injected_observation'
        normal='normal_frame_semantic_errors'
        lines.append(f"| {d['version']} | {COURSE_NAMES[d['condition']]} | {off} | {on} | "
                     f"{off_uncertain}／{on_uncertain} | {x[bad]}／{y[bad]} | {x[normal]}／{y[normal]} |")

    lines.extend(['','以下仅比较同版本、同任务、同条件且两臂都有官方评分的配对。未触发仍按原分配计入。'
                 'Mirage 差按任务等权计算，未决或没有可审回复的轨迹取可能值 0 到 1；界限反映标签不确定性。'
                 '纯 native WAIT 排除。正数表示开防御更高。得分差的任务重抽样范围仅作描述，样本很少时不代表有统计把握。','',
                 '| 版本 | 条件 | 两臂已评分／分配 | 均触发且前缀相同 | 官方开胜／关胜／平 | 官方得分差（95% 描述范围） | 确定 Mirage（关／开） | Mirage 差界限 |',
                 '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |'])
    for d in divisions:
        p=d['paired']; effect=p['official_mean_on_minus_off']
        m=p['all_both_scored_pairs_Mirage']
        lo,hi=m['task_weighted_on_minus_off_bounds']
        diff='—' if effect is None else f'{effect*100:+.1f} pp'
        interval=p['official_task_cluster_percentile_95_interval_descriptive']
        if interval:
            diff+=f'（{interval[0]*100:+.1f} 至 {interval[1]*100:+.1f}）'
        scores=p['official_disagreements_and_ties']
        outcomes='／'.join(str(scores.get(k,0)) for k in ('favor_on','favor_off','tie'))
        bound='—' if lo is None else f'{lo*100:+.1f} 至 {hi*100:+.1f} pp'
        matched=p['both_scored_both_fired_exact_prefix_Mirage_sensitivity']['pairs']
        lines.append(f"| {d['version']} | {COURSE_NAMES[d['condition']]} | "
                     f"{p['official_comparable_pairs']}/{p['assigned_pairs']} | {matched} | "
                     f"{outcomes} | {diff} | {m['confirmed_off']}／{m['confirmed_on']} | {bound} |")

    lines.extend(['','以下是两臂已封存、两臂均实际发生图像替换或缺图的机制对照。'
                  '技术中断前已核实的交付和复拍可以入此表，不能补作官方评分。未触发仍留在上面的分配分母。','',
                  '| 版本 | 条件 | 均实际注入的对数 | 其中触发前原图及动作相同 | 坏图进主模型（关／开） | 正常图复拍闭环（关／开） |',
                  '| --- | --- | ---: | ---: | ---: | ---: |'])
    for d in divisions:
        if d['condition']=='clean_control':continue
        diag=d['paired']['actual_altered_observation_pair_diagnostics']
        a,b=diag['all_coexposed'],diag['coexposed_with_exact_native_prefix']
        pass_main=a['altered_observation_reached_actual_first_forward']
        restored=a['normal_recapture_reached_actual_first_forward']
        lines.append(f"| {d['version']} | {COURSE_NAMES[d['condition']]} | {a['both_actually_exposed_terminal_pairs']} | "
                     f"{b['both_actually_exposed_terminal_pairs']} | {pass_main['off']}／{pass_main['on']} | "
                     f"{restored['off']}／{restored['on']} |")

    lines.extend(['','正常图组的等待时钟从初帧就绪开始，到提交主模型结束。30／120 秒仍等待的分母为独立确认的正常初帧。'
                  '提前结束且没提交，与到时仍在等待分开。缺时钟数据给出上下界。','',
                  '| 版本 | 防御 | 正常初帧误拦 | 出现误拦的正常轨迹 | 误拦后未进主模型 | 提交延迟中位／P95 | 30 秒仍等 | 120 秒仍等 |',
                  '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |'])
    for d in divisions:
        if d['condition']!='clean_control':continue
        for arm,zh in [('off','关'),('on','开')]:
            a=d[arm]; timing=a['first_normal_frame_to_actor_submit_seconds']
            median_p95='—' if not timing['n'] else f"{timing['p50']:.3f}／{timing['p95']:.3f} 秒"
            def waiting(sec):
                w=a['normal_wait_by_analysis_cutoff_seconds'][sec]
                n,k,u=w['normal_initial_frames'],w['still_waiting'],w['unknown']
                return ('—' if not n else f'{k}–{k+u}/{n}' if u else f'{k}/{n}')
            lines.append(f"| {d['version']} | {zh} | {a['false_rejections_of_independently_normal_initial_images']}/"
                         f"{a['independently_normal_initial_images']} | {a['trajectories_with_false_rejection_of_normal_initial_image']}/"
                         f"{a['trajectories_with_an_independently_normal_initial_image']} | {a['false_rejection_then_no_main_forward']} | "
                         f"{median_p95} | {waiting('30')} | {waiting('120')} |")

    lines.extend(['','正常图整轨耗时按原配对计算开减关；含浏览器、模型和评分耗时，单步等待另见上表。'])
    for d in divisions:
        if d['condition']!='clean_control':continue
        t=d['paired']['elapsed_seconds_on_minus_off_task_pairs']
        if t['n']:
            lo,hi=t['range']
            lines.append(f"- {d['version']}：{t['n']} 对；中位 {t['p50']:+.3f} 秒，观察范围 {lo:+.3f} 至 {hi:+.3f} 秒。")

    stages=overall['blocked_changed_image_by_stage']
    verdicts=overall['changed_initial_image_with_actual_Flash_verdict']
    lines.extend(['',f"拦截阶段（仅计确实改变的初帧）：存在检查 {stages.get('precheck_decision',0)} 次，"
                  f"采集回执 {stages.get('capture_receipt_decision',0)} 次，Flash 模型 NO {stages.get('gate_decision',0)} 次。"
                  f"Flash 对改变的初帧实际给出 {sum(verdicts.values())} 个判定；只对复拍图给出 YES 不算识别了注入。",'',
                  '本批 Flash 固定判据允许只有一个可读控件的合法页面，截图来源和时效由其他机制核对。'
                  '仅按钮替换若在前置回执层被扣下，不能据此推断 Flash 能识别带有效回执的仅按钮图。','',
                  '轨迹级 Mirage 与截图门控失效分别统计。收到正常图后的主模型误读、解说与原生方向相反的动作，'
                  '以及坏图确实进入主模型后的语义结果，分别保留在逐轨迹和分组数据中。','',
                  '旧图是传输阶段替换，四种注入都只在每条轨迹中发生一次。持续坏图、有效回执的提前采集不在这批实验范围内。','',
                  '审阅包以主模型实际可见消息、原图和原回复为准，标签封存后才联结运行证据。明显画面异常可被看见，'
                  'T204 仅按钮开启臂的官方分也曾在封标前由运行检查显示，已在评审记录披露。'
                  '同一评审流程及精确复用不等于多位独立评审，一条轨迹的不同决策也不是独立任务样本。',''])
    (dst/'配对证据核验进度.md').write_text('\n'.join(lines),encoding='utf-8')
    save(dst/'seal.json',{p.name:sha(p) for p in dst.iterdir() if p.is_file()})
    print(json.dumps({'report':str(dst),'sealed':overall['sealed_terminals'],'scored':overall['officially_scored'],
        'all_replies':overall['candidate_replies_eligible'],'replies_reviewed':overall['candidate_replies_with_sealed_review'],
        'bound_closed_loops':overall['independently_normal_image_reached_actor_after_loop']}))


if __name__=='__main__':
    main()
