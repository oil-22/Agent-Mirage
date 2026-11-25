"""CPU recovery behavior only; fake recaptures/replies are never live evidence."""
import copy,hashlib,json,sys,tempfile,time
from dataclasses import replace
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'strict-price-repair-development'
stage=json.loads((P/'current.json').read_bytes());release=Path(stage['release'])
sys.path.insert(0,str(release))
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage
fixture=json.loads((release/'strict-price-source-fixture.json').read_bytes());p=fixture['public']
image=VisibleImage((Path(stage['directory'])/'images'/(p['images'][0]['sha256']+'.png')).read_bytes(),'current')
view=PublicView(p['observation_id'],copy.deepcopy(p['messages']),(image,),p['recent_action'],p['execution_feedback'],p['observed_at'])
bad=fixture['candidate'];good=bad.replace('cheaper items','earlier items')
proposal={'name':'scroll','payload':{'type':'scroll','direction':'up'},'parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000'}
rows=[]
for condition in ['one_correction','persistent_conflict']:
    with tempfile.TemporaryDirectory()as tmp:
        calls=[];captures=[];actors=[]
        def judge(system,v,candidate):
            calls.append({'candidate':candidate,'observation_id':v.observation_id})
            cite={'observation_id':v.observation_id,'image_index':0,'coordinate_space':'pixels','box_xyxy':[402,160,1129,310],'description':'Synthetic unit-test source only'}
            if candidate is None:return json.dumps({'status':'usable','visible':['Synthetic unit-test row'],'limitations':[],'loading':'not_observed','evidence':[cite],'reason':'Synthetic unit-test reply only'})
            return json.dumps({'claims':[],'action':{'status':'supported','target_kind':'not_applicable','evidence':[cite],'reason':'Synthetic unit-test acceptance-boundary reply only'},'pure_wait':False,'acknowledges_visual_deficit':False})
        def actor(v,corrections):
            actors.append(copy.deepcopy(corrections))
            return good if condition=='one_correction'and len(actors)>1 else bad
        def recapture():
            captures.append(True)
            return replace(view,observation_id='SYNTHETIC-unit-recapture-'+str(len(captures)))
        c=Controller(judge,Journal(Path(tmp)/'journal'),'joint',Limits(probe_history_reports=True),sleeper=lambda _:None)
        result=c.decide(view,actor,lambda _:copy.deepcopy(proposal),recapture)
        assert len(captures)<3 and c.actor_calls<=3 and c.verifier_calls<=6
        events=[json.loads(x)for x in(c.log.root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        assert actors[1][0]['feedback_reason_source']=='strict_price_comparison'
        assert actors[1][0]['original_verifier_assessment']=='supported'
        assert actors[1][0]['rejected_native_proposal']==proposal
        assert not any(e['kind']=='action_executed'for e in events)
        if condition=='one_correction':
            assert result['status']=='accepted'and result['candidate']==good and result['proposal']==proposal
            assert result['regenerations']==result['recaptures']==1 and c.actor_calls==2 and c.verifier_calls==4
        else:
            assert result['status']=='blocked'and result['reason']=='regeneration_cap'
            assert result['regenerations']==result['recaptures']==2 and c.actor_calls==3 and c.verifier_calls==6
        rows.append({'condition':condition,'status':result['status'],'actor_callback_invocations':c.actor_calls,'fake_judge_callbacks':c.verifier_calls,'fake_recaptures':len(captures),'regenerations':result['regenerations']})
out=P/('supplemental-recovery-CPU-'+str(time.time_ns())+'.json')
out.write_text(json.dumps({'checks':rows,'new_model_calls':0,'GUI_actions':0,'no_real_recovery_claim':True,'source_release_manifest_sha256':stage['source_manifest_sha256'],'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2));print(json.dumps({'receipt':str(out),'checks':rows}))
