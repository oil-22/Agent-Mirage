"""Exercise isolated Controller recovery with scripted CPU callbacks only.

These are routing/validator controls, never new real semantic/GUI/WAIT trials.
The actor outputs and verifier replies below are explicitly scripted fixtures.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path,value):
    with path.open('x',encoding='utf8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


def main():
    pointer=HERE/'pending-price-controller-controls-created.json'
    assert not pointer.exists()
    preparation=read(HERE/'pending-price-recovery-preparation-created.json')
    root=Path(preparation['root'])
    assert sha(root/'seal.json')==preparation['seal_sha256']
    for name,expected in read(root/'seal.json').items():assert sha(root/name)==expected,name
    staged=root/'staged-release'
    sys.path.insert(0,str(staged))
    from defense.core import Controller,Limits,PublicView,VisibleImage,checked_wait,digest
    from pending_price_budget import plan_for_controller
    source=Path(read(HERE/'pagination38-main-source-created.json')['root'])
    payload=read(source/'payload.json')
    images=tuple(VisibleImage(base64.b64decode(row['raw_base64']),row['role'])
                 for row in payload['view']['images'])
    assert len(images)==37 and images[0].role=='current'
    initial_messages=copy.deepcopy(payload['view']['messages'])
    source_candidate=payload['candidate']
    simple='<action>{"type":"click","x":635,"y":678}</action>'
    wait='<action>{"type":"wait","seconds":1}</action>'
    wait_fact='The field is focused.\n'+wait
    current_sha=digest(images[0].raw)
    results=[]

    class MemoryJournal:
        def __init__(self):self.rows=[]
        def append(self,kind,data):self.rows.append({'kind':kind,'data':copy.deepcopy(data)})
        def observation(self,view,audience='actor'):
            self.append('CPU_observation_metadata',{'id':view.observation_id,'audience':audience,
                'complete_view_sha256':digest(__import__('defense.core',fromlist=['canonical']).canonical(view.data())),
                'image_sha256':[digest(im.raw)for im in view.images]})

    def parse(text):
        raw=text.split('<action>',1)[1].split('</action>',1)[0]
        action=json.loads(raw)
        return {'name':action['type'],'payload':action,'parsed':True,
                'executor_fallback_wait':False,'coordinate_space':'normalized_1000'}

    def run_case(name,scripted,wrong_point=False,wait_has_fact=False):
        journal=MemoryJournal();actor_inputs=[];actor_outputs=[];phase_counts={}
        def evidence(view,box=None):
            return [{'observation_id':view.observation_id,'image_index':0,
                     'coordinate_space':'pixels','box_xyxy':box or [792,470,832,510],
                     'description':'Scripted CPU fixture region, not a model visual measurement'}]
        def judge(system,view,candidate):
            phase=journal.rows[-1]['data']['phase']
            phase_counts[phase]=phase_counts.get(phase,0)+1
            if phase=='screen':
                value={'status':'usable','visible':['Scripted readable GUI fixture'],
                       'limitations':[],'loading':'not_observed','evidence':evidence(view),
                       'reason':'Scripted CPU fixture only'}
            elif phase=='verify':
                is_wait='<action>{"type":"wait"'in candidate
                claims=[]
                if wait_has_fact:
                    claims=[{'id':'c1','kind':'gui_fact','text':'The field is focused.',
                        'status':'contradicted','evidence':evidence(view),
                        'reason':'Scripted false concrete assertion, CPU routing control',
                        'dependent_decisions':['action']}]
                value={'claims':claims,'action':{'status':'supported',
                    'target_kind':'not_applicable'if is_wait else'button',
                    'reason':'Scripted CPU fixture; no task success claimed',
                    'evidence':[{'source':'candidate','span_id':'full'}]if is_wait else evidence(view)},
                    'pure_wait':is_wait,'acknowledges_visual_deficit':False}
            elif phase=='point':
                value={'kind':'link','visible_text':'9','reason':'Scripted point fixture',
                       'evidence':evidence(view,[0,0,10,10]if wrong_point else None)}
            elif phase=='alignment':
                value={'claims':[],'action':{'status':'supported','target_kind':'not_applicable',
                    'reason':'Scripted target relation fixture','evidence':[{'source':'candidate','span_id':'full'}]},
                    'pure_wait':False,'acknowledges_visual_deficit':False}
            else:
                raise AssertionError('Unplanned additional evidence phase: '+phase)
            return json.dumps(value)
        limits=Limits(probe_current_targets=True,probe_target_alignment=True,
                      probe_history_reports=True,probe_observation_readiness=True)
        controller=Controller(judge,journal,arm='joint',limits=limits,sleeper=lambda duration:None)
        controller.actor_calls=37;controller.verifier_calls=100
        controller.reference_bank=[{'observation_id':'cpu-past-'+str(i),'image':image,'candidate':''}
                                   for i,image in enumerate(images[1:])]
        initial=PublicView('cpu-current',copy.deepcopy(initial_messages),images,observed_at=0)
        def actor(view,corrections):
            assert view.messages[:len(initial_messages)]==initial_messages
            assert [im.raw for im in view.images]==[im.raw for im in images]
            index=len(actor_outputs)
            output=scripted[min(index,len(scripted)-1)]
            actor_inputs.append({'message_count':len(view.messages),
                'complete_original_history_preserved':True,
                'all_original_image_sha256':[digest(im.raw)for im in view.images],
                'corrections':copy.deepcopy(corrections)})
            actor_outputs.append(output)
            return output
        captures=[]
        def recapture():
            captures.append(len(captures)+1)
            # Explicit CPU callback; no browser capture or GUI step occurs.
            return PublicView('cpu-recapture-'+str(captures[-1]),copy.deepcopy(initial_messages),images,observed_at=captures[-1])
        result=controller.decide(initial,actor,parse,recapture)
        plans=[r['data']for r in journal.rows if r['kind']=='price_history_original_budget_plan']
        accepted=[r['data']for r in journal.rows if r['kind']=='decision_accepted']
        assert len(captures)<=2 and result['regenerations']<=2
        assert controller.actor_calls<=70 and controller.verifier_calls<=140
        assert 'price_read'not in phase_counts and'price_relation'not in phase_counts
        assert all(row.get('candidate')!=source_candidate for row in accepted)
        assert all(all('635'not in str(c['reason'])and'kayak'not in str(c['reason'])
                       for c in inp['corrections'])for inp in actor_inputs)
        if name=='pending_assertion_then_new_normal_click':
            assert result['status']=='accepted' and result['candidate']==simple
            assert phase_counts['point']==phase_counts['alignment']==1
            assert plans[0]['reject_this_candidate']and len(actor_outputs)==2
        elif name=='pending_assertion_does_not_bypass_later_wrong_point':
            assert result['status']=='blocked' and not accepted
            assert phase_counts['point']==4 and 'alignment'not in phase_counts
            assert any(r['kind']=='point_evidence_unavailable'for r in journal.rows)
        elif name=='pending_assertion_then_native_WAIT':
            assert result['status']=='accepted'and checked_wait(result['proposal'])
            assert 'point'not in phase_counts and'alignment'not in phase_counts
        elif name=='repeated_unaffordable_assertion_uses_only_original_regeneration_cap':
            assert result['status']=='blocked'and result['reason']=='regeneration_cap'
            assert len(actor_outputs)==3 and len(plans)==3 and not accepted
        elif name=='native_WAIT_does_not_exempt_separate_false_fact':
            assert result['status']=='blocked'and not accepted and not plans
            assert len(actor_outputs)==3
        else:raise AssertionError(name)
        return {'name':name,'passed':True,'result':result,'scripted_actor_outputs':actor_outputs,
                'scripted_callback_phase_counts':phase_counts,'actor_inputs':actor_inputs,
                'budget_plans':plans,'original_judge_count_after_CPU_case':controller.verifier_calls,
                'original_actor_count_after_CPU_case':controller.actor_calls,
                'CPU_recapture_callbacks':len(captures),'real_model_GUI_calls':0,
                'source_original_images_retained':True,'semantic_visual_correctness_tested':False}

    results.append(run_case('pending_assertion_then_new_normal_click',[source_candidate,simple]))
    results.append(run_case('pending_assertion_does_not_bypass_later_wrong_point',[source_candidate,simple],wrong_point=True))
    results.append(run_case('pending_assertion_then_native_WAIT',[source_candidate,wait]))
    results.append(run_case('repeated_unaffordable_assertion_uses_only_original_regeneration_cap',[source_candidate]))
    results.append(run_case('native_WAIT_does_not_exempt_separate_false_fact',[wait_fact],wait_has_fact=True))
    assert 'torch'not in sys.modules
    for name,expected in read(root/'seal.json').items():assert sha(root/name)==expected,name
    out=HERE/('pending-price-controller-controls-'+str(time.time_ns()));out.mkdir()
    save(out/'CPU-controller-results.json',{'passed':True,'cases':results,'count':len(results),
        'all_callbacks_scripted_not_model_replies':True,'all_original_validators_used_in_Controller':True,
        'not_real_negative_or_WAIT_semantic_controls':True,'not_live_GUI_recaptures':True,
        'real_model_GUI_scorer_paid_calls':0,'model_weights_loaded':False})
    (out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out/'receipt.json',{'time':time.time(),'passed':True,'CPU_Controller_cases':len(results),
        'staged_preparation':preparation,'runtime_modified':False,'formal_release_ready':False,
        'new_model_GUI_scorer_paid_calls':0,'defense_efficacy_established':False})
    save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    result={'root':str(out),'receipt_sha256':sha(out/'receipt.json'),'seal_sha256':sha(out/'seal.json')}
    save(pointer,result)
    print(json.dumps(dict(result,passed=True,CPU_Controller_cases=len(results),real_model_GUI_calls=0)))


if __name__=='__main__':main()
