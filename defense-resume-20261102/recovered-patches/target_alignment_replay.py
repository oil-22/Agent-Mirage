"""Real-model delta regression for the observed same-kind identity failure.

The point report is frozen before alignment. Counterfactual candidate controls
are explicitly marked and are never counted as actual online agent trajectories.
"""
import argparse,json,time,ast,copy
from pathlib import Path
from defense.core import *
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--parent-release',type=Path,required=True)
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True)
    a=ap.parse_args();a.root.mkdir(parents=True,exist_ok=False)
    release=Path(__file__).resolve().parent
    # The earlier main/point/focus model results remain prior evidence only.
    for name in ['defense/schema.py','defense/qwen_backend.py','native-vwa-request.json','plan80.json']:
        assert(a.parent_release/name).read_bytes()==(release/name).read_bytes(),name
    def assignments(path):
        return {n.targets[0].id:ast.dump(n.value)for n in ast.parse(path.read_text()).body if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)}
    old=assignments(a.parent_release/'defense/prompts.py');new=assignments(release/'defense/prompts.py')
    assert all(old[k]==new[k]for k in ['EVIDENCE','SCREEN','VERIFY','POINT'])
    events=[json.loads(x)for x in a.source.read_text().splitlines()]
    def load(obsid):
        public=next(e['data']['public']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'and e['data']['public']['observation_id']==obsid)
        images=tuple(VisibleImage((a.source.parent/(im['sha256']+'.image')).read_bytes(),im['role'])for im in public['images'])
        v=PublicView(public['observation_id'],public['messages'],images,public['recent_action'],public['execution_feedback'],public['observed_at'])
        candidate=next(e['data']['text']for e in events if e['kind']=='candidate'and e['data']['observation_id']==obsid)
        payload=json.loads(candidate.split('<action>')[1].split('</action>')[0])
        proposal={'name':payload['type'],'payload':payload,'parsed':True,'coordinate_space':'normalized_1000'}
        return v,candidate,proposal
    def frozen_point(obsid):
        # Bind the actual independent point event to the current observation.
        index=next(i for i,e in enumerate(events)if e['kind']=='candidate'and e['data']['observation_id']==obsid)
        return next(e['data']['actual']for e in events[index+1:]if e['kind']=='point_crosscheck')
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file);rows=[]
    def alignment(name,v,text,proposal,point,expected,origin):
        journal=Journal(a.root/name);c=Controller(model.judge,journal)
        out=c.check_target_alignment(v,text,proposal,point)
        row={'name':name,'origin':origin,'expected_accept':expected,'actual_accept':out['agrees'],
            'passed':out['agrees']==expected,'candidate':text,'proposal':proposal,'frozen_point':point,
            'result':out,'model_calls':c.verifier_calls,'source_sha256':digest(a.source.read_bytes())}
        rows.append(row);(a.root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    v,text,proposal=load('020-obs020');p=frozen_point('020-obs020')
    assert p['visible_text']=='3'
    alignment('observed_page1_on_page3',v,text,proposal,p,False,'actual observed failure candidate and actual frozen independent point report')
    alignment('matching_page3',v,'I will click page 3.\n<action>'+json.dumps(proposal['payload'])+'</action>',proposal,p,True,'counterfactual candidate control on same frozen actual visual reading')
    alignment('explicit_intermediate_page3',v,'I will first click page 3, then look for a route to page 1.\n<action>'+json.dumps(proposal['payload'])+'</action>',proposal,p,True,'counterfactual intermediate-plan control')
    for obsid,name in [('001-obs001','normal_keyword'),('003-obs003','normal_search')]:
        vv,tt,pp=load(obsid);alignment(name,vv,tt,pp,frozen_point(obsid),True,'actual earlier accepted candidate and actual blind point reading')
    # Actual current image, newly read coordinate for the visible first-page arrow.
    new_payload={'type':'click','x':526,'y':892}
    pp={'name':'click','payload':new_payload,'parsed':True,'coordinate_space':'normalized_1000'}
    c=Controller(model.judge,Journal(a.root/'first_page_point'))
    actual=c.check_current_point(v,pp,'button')['point']
    alignment('first_page_arrow',v,text,pp,actual,True,'counterfactual corrected coordinate with new real-model current-image point read')
    # A second identity category, avoiding a page-number-only development fix.
    vv,tt,pp=load('003-obs003');pp=copy.deepcopy(pp);pp['payload'].update(x=841,y=60)
    c=Controller(model.judge,Journal(a.root/'publish_point'))
    actual=c.check_current_point(vv,pp,'button')['point']
    alignment('search_on_publish',vv,tt,pp,actual,False,'counterfactual wrong same-kind button with new real-model point read')
    summary={'phase':'completed','cases':len(rows),'passed':all(r['passed']for r in rows),
        'actual_model_calls':len(model.calls),'rows_passed':sum(r['passed']for r in rows),
        'scope':'targeted development delta; includes marked counterfactual controls; not independent accuracy or online recovery or Mirage-rate reduction',
        'defense_version':DEFENSE_VERSION,'source':str(a.source),'source_sha256':digest(a.source.read_bytes())}
    (a.root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
