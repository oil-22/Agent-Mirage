"""Check the real signed capture preflight and safety boundaries without loading models."""

import argparse
from pathlib import Path

from audit_panel import chain, event, verify_frames
from audit_toggle import checked_controls, verify_origin, verify_seal
from audit_truth import classify
from gate_core import Frame
from live_common import load, save, sha
from scoped_evidence import anchor, assess

HERE=Path(__file__).resolve().parent


def check(root):
    m,seal=verify_seal(root); origin=verify_origin(root)
    plan=load(root/'live_plan.json'); end=load(root/'run'/'terminal.json')
    assert end['status']=='passed' and end['new_model_calls']==end['gpu_allocations']==seal['exit_status']==0
    assert m['stage']=='capture-preflight' and sha(HERE/'heldout-plan.json')==sha(root/'live_plan.json')
    assert plan['preflight_ids']==m['preflight_ids']==[r['case']['id'] for r in end['completed']] and len(end['completed'])==11
    rows=[];tested=[]
    for t in end['completed']:
        case=t['case']; name=case['id']; folder=root/'run'/'episodes'/name; src=root/'run'/'source'/name
        source_action=load(src/'action.json'); terminal=load(folder/'terminal.json')
        head,events=chain(folder/'events.jsonl')
        assert head==terminal['journal_head'] and terminal['journal_sha256']==sha(folder/'events.jsonl')
        assert events[-1]['kind']=='terminal' and events[-1]['data']==t
        f,a,old=verify_frames(folder,src,case,events,{**terminal,'native_action':source_action['native_action'],
                     'subsequent_action_executed':False},origin,plan['viewport'],classify=classify)
        bind, action, dispatch, records=checked_controls(src,f,a)
        caps=(old,*list(f)[-2:]); frames, packets=zip(*(records[c] for c in caps),strict=True)
        result=assess(bind,action,dispatch,frames,packets)
        assert result==t['image_checks']
        role=anchor(bind,action,dispatch,frames[0],packets[0]); assert role==('plain_click' if case['scenario']=='ordinary' else 'bound_toggle')
        if result['eligible']:
            assert not assess(bind,action,dispatch,(frames[0],frames[1],frames[1]),(packets[0],packets[1],packets[1]))['eligible']
            assert not assess(bind,action,dispatch,frames,(*packets[:2],packets[0]))['eligible']
            swapped=Frame(frames[0].png,frames[2].capture_id,0,frames[2].receipt)
            assert not assess(bind,action,dispatch,(*frames[:2],swapped),packets)['eligible']
            missing=Frame(None,frames[2].capture_id,0,frames[2].receipt)
            assert not assess(bind,action,dispatch,(*frames[:2],missing),packets)['eligible']
            tested.extend((name,x) for x in ('repeat_id','wrong_signed_frame','substituted_png','missing_png'))
        rows.append({'id':name,'scope':result['reason'],'anchor':role,'frame_count':len(f)})
    frozen=load(HERE/'source-baseline.json')['parent_manifest_files']
    unchanged=('live_models.py','wire_contract.py','gate_core.py','actor-template.json','primary-reference.json','temporal_request.py',
               'resource_guard.py','service-config.json','gate-contract.json','flash-identity.json','receipt_protocol.py','capture_gui.py')
    assert all(sha(HERE/n)==frozen[n] for n in unchanged)
    files=('live_run.py','scoped_evidence.py','toggle_protocol.py','toggle_prompt.py','fixture.html','live_capture.py','analysis-plan.json',
           'heldout-plan.json','live_lease.py',*unchanged)
    return {'preflight_seal_sha256':sha(root/'local-seal.json'),'preflight':root.name,'passed':True,
            'cases':rows,'negative_boundaries':tested,'preserved_native_source':list(unchanged),
            'reviewed_signed_frames':sum(r['frame_count'] for r in rows),'files':{f:sha(HERE/f) for f in files},'new_model_calls':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('preflight',type=Path)
    r=check(p.parse_args().preflight.resolve());save(HERE/'cpu-qualification.json',r)
    print(len(r['cases']),'actual capture cases;',len(r['negative_boundaries']),'invalid packet/PNG paths refused;',r['reviewed_signed_frames'],'signatures')
