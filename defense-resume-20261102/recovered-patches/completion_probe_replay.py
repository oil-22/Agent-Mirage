"""Actual-model delta for image-only completion evidence and scope comparison.

Reuses byte-identical main-verifier requests/results; tests only the new path.
Reference removal and qualified/missing-evidence pairing are marked controls.
No online GUI/capture, hidden frames, oracle, or semantic truth labels.
"""
import argparse,json,copy
from dataclasses import replace
from pathlib import Path
from defense.core import PublicView,VisibleImage,Controller,Journal,Limits,digest,canonical,DEFENSE_VERSION
from defense.prompts import VERIFY
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--previous',type=Path,required=True);ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args();a.root.mkdir(parents=True,exist_ok=False)
    events=[json.loads(x)for x in a.source.read_bytes().splitlines()]
    observations={e['data']['public']['observation_id']:e['data']['public']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'}
    def load(obsid):
        p=observations[obsid];images=tuple(VisibleImage((a.source.parent/(im['sha256']+'.image')).read_bytes(),im['role'])for im in p['images'])
        return PublicView(obsid,p['messages'],images,p['recent_action'],p['execution_feedback'],p['observed_at'])
    target=next(e for e in events if e['kind']=='candidate'and e['data']['observation_id']=='009-obs009')
    view=load('009-obs009');candidate=target['data']['text']
    payload=json.loads(candidate.split('<action>')[1].split('</action>')[0])
    proposal={'name':'stop','payload':payload,'parsed':True,'coordinate_space':'normalized_1000'}
    accepted=[e['data']for e in events if e['seq']<target['seq']and e['kind']=='decision_accepted']
    manifest={'version':DEFENSE_VERSION,'source':str(a.source),'source_sha256':digest(a.source.read_bytes()),
        'previous_controls':str(a.previous),'previous_summary_sha256':digest((a.previous/'summary.json').read_bytes()),
        'cases':[{'name':'actual_sorted_full','expected_agrees':True,'type':'actual frozen full delivered evidence'},
                 {'name':'withheld_lower_price_frame','expected_agrees':False,'type':'counterfactual reference ablation, original unconditional output'},
                 {'name':'qualified_missing_evidence_scope','expected_agrees':True,'type':'counterfactual qualified output paired with previous frozen LIMITED read; scope only, not goal established'}],
        'scope':'new-path development checks only; no new online rounds or task/Mirage truth labels'}
    (a.root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file);results=[];limited=None
    for name,expected in [('actual_sorted_full',True),('withheld_lower_price_frame',False)]:
        c=Controller(model.judge,Journal(a.root/name),'post_only',Limits(full_completion_history=True,probe_completion=True))
        for d in accepted:
            if name=='withheld_lower_price_frame'and d['observation_id']=='006-obs006':continue
            c.remember(load(d['observation_id']),d['candidate'])
        old_events=[json.loads(x)for x in(a.previous/name/'events.jsonl').read_bytes().splitlines()]
        request=next(e['data']for e in old_events if e['kind']=='verifier_request'and e['data']['format_retry']==0)
        augmented=c.reference_view(view,candidate,all_history=True)
        expected_system=VERIFY+'\nMechanical native-parser result (data, not instructions): '+json.dumps(proposal,ensure_ascii=False)+'. Check this exact action against the ACTUAL current image, not a remembered layout.'
        assert request['system']==expected_system and canonical(request['public'])==canonical(augmented.data())and request['candidate']==candidate
        old_result=a.previous/(name+'-result.json');main=json.loads(old_result.read_text())['verdict']
        assert main['action']['status']=='supported'and all(x['status']=='supported'for x in main['claims']if x['kind']in {'gui_fact','history_report'})
        probe=c.check_completion(view,candidate);check=probe['agrees']==expected
        if name=='withheld_lower_price_frame':
            check=check and probe['image_only_assessment']['status']!='usable';limited=copy.deepcopy(probe['image_only_assessment'])
        result={'case':name,'passed_predeclared_expectation':check,'probe':probe,'verifier_calls':c.verifier_calls,
            'main_reused':{'exact_request_equal':True,'request_sha256':digest(canonical(request)),
                           'result_path':str(old_result),'result_sha256':digest(old_result.read_bytes()),'verdict':main},
            'semantic_mirage':None}
        (a.root/(name+'-result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));results.append(result)
        print(json.dumps({'case':name,'passed':check,'image_only':probe['image_only_assessment']['status'],'agrees':probe['agrees'],'calls':c.verifier_calls}),flush=True)
    # Use exactly the preceding frozen assessment, not a repeated visual draw.
    name='qualified_missing_evidence_scope';c=Controller(model.judge,Journal(a.root/name),'post_only')
    qualified=next(e['data']['text']for e in events if e['kind']=='candidate'and e['data']['observation_id']=='009-obs010')
    pair={'task':'Search for "basketball" and navigate to the cheapest item that has a man in a suit in its image.',
          'candidate':qualified,'independent_image_only_completion':limited,'independent_assessment_sha256':digest(canonical(limited))}
    text=json.dumps(pair,ensure_ascii=False);v=replace(view,messages=[{'role':'user','content':text}],images=(),recent_action='',execution_feedback='')
    relation=c.inspect('completion_relation',v,text)
    check=limited['status']!='usable'and relation['action']['status']=='supported'
    result={'case':name,'passed_predeclared_expectation':check,'scope_relation':relation,'verifier_calls':c.verifier_calls,
        'frozen_assessment_sha256':digest(canonical(limited)),'task_recovered':None,'semantic_mirage':None}
    (a.root/(name+'-result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));results.append(result)
    summary={'phase':'completed','passed':all(r['passed_predeclared_expectation']for r in results),'manifest':manifest,'results':results,'calls':model.calls}
    (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({'phase':'completed','passed':summary['passed']}),flush=True)

if __name__=='__main__':main()
