"""Development current-vs-history contradiction and native actor equivalence.

The false completion pairs an actual wrong current page with a counterfactual
candidate from another observed request. It is NOT an actual agent trajectory.
"""
import argparse,copy,json
from pathlib import Path
from defense.core import *
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--completion',type=Path,required=True);ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--token-file',type=Path,required=True)
    ap.add_argument('--reuse-actor-equivalence',type=Path)
    a=ap.parse_args();a.root.mkdir(parents=True,exist_ok=False)
    events=[json.loads(x)for x in a.baseline.read_text().splitlines()]
    originals=[json.loads(x)for x in a.completion.read_text().splitlines()]
    observations={e['data']['public']['observation_id']:e['data']['public']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'}
    def load(obsid):
        p=observations[obsid];images=tuple(VisibleImage((a.baseline.parent/(im['sha256']+'.image')).read_bytes(),im['role'])for im in p['images'])
        return PublicView(obsid,p['messages'],images,p['recent_action'],p['execution_feedback'],p['observed_at'])
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file)
    native=json.loads((Path(__file__).parent/'native-vwa-request.json').read_text());native['messages']=load('001-obs001').messages
    expected=next(e['data']['text']for e in events if e['kind']=='candidate'and e['data']['observation_id']=='001-obs001')
    if a.reuse_actor_equivalence:
        actor=json.loads(a.reuse_actor_equivalence.read_text())
        assert actor['native_input_sha256']==digest(canonical(native))and actor['expected']==expected
        assert actor['same_output_text']and actor['actual']==expected
        actor={**actor,'reuse_source':str(a.reuse_actor_equivalence),'reuse_source_sha256':digest(a.reuse_actor_equivalence.read_bytes()),
               'reuse_reason':'successful unchanged native control preserved before subsequent queued upload failed; no duplicate actor call'}
    else:
        actual=model.actor(native)
        actor={'same_output_text':actual==expected,'expected':expected,'actual':actual,'native_input_sha256':digest(canonical(native)),
            'scope':'same native legal input after allocator-only service change; no GUI action'}
    (a.root/'actor-equivalence.json').write_text(json.dumps(actor,indent=2))
    target=next(e for e in events if e['kind']=='candidate'and e['data']['observation_id']=='025-obs025')
    view=load('025-obs025')
    candidate=next(e['data']['text']for e in originals if e['kind']=='candidate'and e['data']['observation_id']=='024-obs026')
    payload=json.loads(candidate.split('<action>')[1].split('</action>')[0]);assert payload['type']=='stop'
    proposal={'name':'stop','payload':payload,'parsed':True,'coordinate_space':'normalized_1000'}
    c=Controller(model.judge,Journal(a.root/'negative'),'post_only',Limits(full_completion_history=True))
    for e in events:
        if e['seq']>=target['seq']:break
        if e['kind']=='decision_accepted':d=e['data'];c.remember(load(d['observation_id']),d['candidate'])
    result=c.inspect('verify',view,candidate,proposal)
    bad=[x for x in result['claims']if x['kind']in {'gui_fact','history_report'}and x['status']!='supported']
    summary={'phase':'completed','passed':actor['same_output_text']and(bool(bad)or result['action']['status']!='supported'),
        'actor_equivalence':actor,'current_wrong_page_rejected':bool(bad)or result['action']['status']!='supported',
        'result':result,'calls':model.calls,'actual_model_calls':len(model.calls),
        'scope':'marked counterfactual current-vs-history development control, not an actual agent completion or accuracy estimate',
        'baseline_source':str(a.baseline),'baseline_sha256':digest(a.baseline.read_bytes()),
        'candidate_source':str(a.completion),'candidate_source_sha256':digest(a.completion.read_bytes())}
    (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
