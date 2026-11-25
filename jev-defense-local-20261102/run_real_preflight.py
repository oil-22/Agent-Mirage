"""Finite new-model development controls; original 27B not invoked."""
import argparse, hashlib, json, pathlib, time
from defense.core import Controller,Journal,PublicView,VisibleImage,canonical,digest
from jev_auxiliary import JevAuxiliary,LocalDecisionClient,JevAssistedController,REVISIONS,STATE,QUESTIONS
def save(p,x):
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,ensure_ascii=False)
def main(a):
    a.root.mkdir(parents=True,exist_ok=False)
    plan=json.loads(a.plan.read_bytes());save(a.root/'plan.json',plan)
    clients=[LocalDecisionClient(m['model'],m['url'],a.token_file) for m in plan['services'] if not a.only_models or m['model'] in a.only_models]
    aux=JevAuxiliary(clients,max_calls=a.max_new_calls if a.max_new_calls is not None else plan['max_calls']);journal=Journal(a.root/'journal');rows=[]
    for prior in a.reuse_from:
        seal=json.loads((prior/'terminal-sha256.json').read_bytes())
        assert all(digest((prior/name).read_bytes())==h for name,h in seal.items())
        prior_result=json.loads((prior/'summary.json').read_bytes())
        for row in prior_result['rows']:
            if 'result' not in row:continue
            result=row['result'];receipt=pathlib.Path(result['receipt'])
            assert digest((receipt/'response.json').read_bytes())==json.loads((receipt/'seal.json').read_bytes())['response.json']
            req=json.loads((receipt/'request.json').read_bytes());key=row['query'];model=row['model']
            assert req['state']==STATE and req['question']==QUESTIONS[key][0] and req['options']==QUESTIONS[key][1] and result['revision']==REVISIONS[model]
            assert digest((receipt/'original.image').read_bytes())==result['image_sha256']
            cache_key=(model,REVISIONS[model],result['image_sha256'],key,digest(canonical([STATE,QUESTIONS[key]])))
            aux.cache[cache_key]=result
    for case in plan['cases']:
        p=a.images/(case['image_sha256']+'.png');raw=p.read_bytes();assert digest(raw)==case['image_sha256']
        v=PublicView(case['id'],[{'role':'user','content':'Independent single-frame evidence development control.'}],(VisibleImage(raw),))
        journal.observation(v,audience='jev_development')
        result=aux.observe('verify',v,{'name':'scroll'},journal);rows.extend(result)
        save(a.root/(case['id']+'.json'),result)
        print(json.dumps({'case':case['id'],'new_calls':aux.calls,'results':[{'model':r['model'],'query':r['query'],'status':r['status'],'answer':r.get('result',{}).get('answer')} for r in result]}),flush=True)
    # Exercise actual Controller subclass with a real local-model response/reuse.
    # The main verifier here is a fixed contract fixture, not a 27B semantic experiment.
    packet=json.loads(a.packet.read_bytes());pub=packet['public']
    images=tuple(VisibleImage((a.images/(im['sha256']+'.png')).read_bytes(),im['role']) for im in pub['images'])
    v=PublicView(pub['observation_id'],pub['messages'],images,pub['recent_action'],pub['execution_feedback'],pub['observed_at'])
    assert canonical(v.data())==canonical(pub)
    original=canonical(v.data());seen=[]
    def judge(system,obs,candidate):
        seen.append({'system_sha256':digest(system.encode()),'view_sha256':digest(canonical(obs.data())),'candidate':candidate})
        im=obs.images[0];w,h=im.info()['size']
        return {'status':'usable','visible':['contract fixture'],'limitations':[],'loading':'not_observed','evidence':[{'observation_id':obs.observation_id,'image_index':0,'coordinate_space':'pixels','box_xyxy':[0,0,w,h],'description':'contract fixture'}],'reason':'Transport integration only; no main model call'}
    base=Controller(judge,Journal(a.root/'base-contract'));expected=base.inspect('screen',v);expected_seen=seen[-1]
    integrated=JevAssistedController(judge,Journal(a.root/'integrated-contract'),jev_auxiliary=aux)
    got=integrated.inspect('screen',v)
    assert got==expected and seen[-1]==expected_seen and original==canonical(v.data()) and integrated.verifier_calls==base.verifier_calls
    before=aux.calls;aux.observe('verify',v,{'name':'wait'},journal);assert aux.calls==before
    integration={'same_main_view':True,'same_original_verdict':True,'same_original_verifier_count':True,'wait_additional_calls':0,'main_judge_is_contract_fixture':True,'main_27B_calls':0}
    save(a.root/'summary.json',{'rows':rows,'integration':integration,'new_model_calls':aux.calls,'max_new_calls':aux.max_calls,'overall_preflight_cap':plan['max_calls'],'reuse_from':[str(x) for x in a.reuse_from],'GUI_actions':0,'paid_API_calls':0,'formal_release':False,'selected_nonblind_development':True,'semantic_labels_not_sent_to_model':True,'time':time.time()})
    save(a.root/'terminal-sha256.json',{str(p.relative_to(a.root)):digest(p.read_bytes()) for p in a.root.rglob('*') if p.is_file()})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--images',type=pathlib.Path,required=True);p.add_argument('--packet',type=pathlib.Path,required=True);p.add_argument('--token-file',type=pathlib.Path,required=True);p.add_argument('--only-models',nargs='+');p.add_argument('--reuse-from',type=pathlib.Path,action='append',default=[]);p.add_argument('--max-new-calls',type=int);main(p.parse_args())
