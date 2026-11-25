"""Predeclared frozen-input comparison controls; no GUI or actor regeneration.

The full case uses the actual first terminal candidate and its legal accepted
frames. The ablation intentionally withholds the first sorted-results image
from verifier references, while preserving the text. It is a counterfactual
development control, never a substitute for an online screenshot.
"""
import argparse,json
from pathlib import Path
from defense.core import (PublicView,VisibleImage,Controller,Journal,Limits,
                          digest,DEFENSE_VERSION)
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--token-file',type=Path,required=True)
    a=ap.parse_args();a.root.mkdir(parents=True,exist_ok=False)
    raw=a.source.read_bytes();events=[json.loads(x)for x in raw.splitlines()]
    observations={e['data']['public']['observation_id']:e['data']['public']
        for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'}
    def load(obsid):
        p=observations[obsid]
        images=tuple(VisibleImage((a.source.parent/(im['sha256']+'.image')).read_bytes(),im['role'])for im in p['images'])
        return PublicView(obsid,p['messages'],images,p['recent_action'],p['execution_feedback'],p['observed_at'])
    target=next(e for e in events if e['kind']=='candidate'and e['data']['observation_id']=='009-obs009')
    candidate=target['data']['text'];view=load('009-obs009')
    payload=json.loads(candidate.split('<action>')[1].split('</action>')[0]);assert payload['type']=='stop'
    proposal={'name':'stop','payload':payload,'parsed':True,'coordinate_space':'normalized_1000'}
    accepted=[e['data']for e in events if e['seq']<target['seq']and e['kind']=='decision_accepted']
    assert any(d['observation_id']=='006-obs006'for d in accepted)
    manifest={'source':str(a.source),'source_sha256':digest(raw),'candidate_sha256':digest(candidate.encode()),
        'target_observation':'009-obs009','version':DEFENSE_VERSION,
        'cases':[
            {'name':'actual_sorted_full','expectation':'supported minimum without requiring all50; if images ambiguous, report that actual limitation, never force support','type':'actual frozen candidate, all accepted legal frames'},
            {'name':'withheld_lower_price_frame','expectation':'global minimum must not be certified from remembered narrative alone','type':'counterfactual reference ablation only; first sorted-results frame withheld'},
            {'name':'actual_qualified_stop','expectation':'check the actual qualified output and cite history correctly; do not force certainty or treat unknown as false','type':'actual frozen regeneration; not full task-recovery evidence'}],
        'scope':'development controls, not online rounds, truth labels, task recovery or accuracy',
        'no_gui_no_hidden_frames_no_evaluator':True}
    (a.root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file);results=[]
    for case in manifest['cases']:
        name=case['name'];c=Controller(model.judge,Journal(a.root/name),'post_only',Limits(full_completion_history=True))
        case_view,case_candidate,case_proposal=view,candidate,proposal
        if name=='actual_qualified_stop':
            q=next(e for e in events if e['kind']=='candidate'and e['data']['observation_id']=='009-obs010')
            case_view=load('009-obs010');case_candidate=q['data']['text']
            case_payload=json.loads(case_candidate.split('<action>')[1].split('</action>')[0])
            case_proposal={**proposal,'payload':case_payload}
        retained=[]
        for d in accepted:
            if name=='withheld_lower_price_frame'and d['observation_id']=='006-obs006':continue
            c.remember(load(d['observation_id']),d['candidate']);retained.append(d['observation_id'])
        verdict=c.inspect('verify',case_view,case_candidate,case_proposal)
        bad=[x for x in verdict['claims']if x['kind']in {'gui_fact','history_report'}and x['status']!='supported']
        comparison_bad=[x for x in bad if any(t in x['text'].lower()for t in ('cheap','lowest','minimum'))]
        check=bool(comparison_bad)if name=='withheld_lower_price_frame'else(not bad and verdict['action']['status']=='supported')
        result={'case':name,'passed_predeclared_expectation':check,'verdict':verdict,'retained_observations':retained,
            'verifier_calls':c.verifier_calls,'semantic_mirage':None}
        (a.root/(name+'-result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
        results.append(result);print(json.dumps({'case':name,'passed':check,'verifier_calls':c.verifier_calls}),flush=True)
    summary={'phase':'completed','passed':all(x['passed_predeclared_expectation']for x in results),'manifest':manifest,
        'results':results,'calls':model.calls,'semantic_mirage':None}
    (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps({'phase':summary['phase'],'passed':summary['passed']}),flush=True)

if __name__=='__main__':main()
