"""Source-initialized live step9 using the unchanged complete Controller.decide."""
import argparse,base64,copy,json,sys,time,traceback
from pathlib import Path
from defense.core import PublicView,VisibleImage,Controller,Journal,Limits,digest
from defense.http_backend import RemoteQwen

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
    a.root.mkdir(parents=True,exist_ok=False);journal=Journal(a.root/'events')
    def status(**v):(a.root/'status.json').write_text(json.dumps({'time':time.time(),**v}))
    base=Path('/data/researcher/vwa100-2026-10-09');sys.path[:0]=[str(base),str(base/'upstream/visualwebarena-main')]
    from run_reddit_internvl_smoke import parse,action,png
    from browser_env import ScriptBrowserEnv
    from browser_env.actions import create_page_focus_action
    all_events=[json.loads(x)for x in(a.source/'events.jsonl').read_text().splitlines()]
    actions=[e for e in all_events if e['kind']=='action_executed'];assert len(actions)==8
    req=next(e for e in all_events if e['kind']=='actor_request'and e['data']['public']['observation_id'].startswith('009-')and not e['data']['corrections'])
    events=[e for e in all_events if e['seq']<req['seq']]
    public=req['data']['public'];assert len(public['images'])==1 and public['images'][0]['role']=='current'
    current=public['images'][0]
    lim=next(e['data']for e in events if e['kind']=='defense_configuration')
    arm=next(e['data']['run']['arm']for e in events if e['kind']=='protocol')
    template=json.loads((Path(__file__).parent/'native-vwa-request.json').read_bytes())
    env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file)
    status(phase='replaying_original_eight_actions')
    try:
        obs,info=env.reset(seed=20261011,options={'config_file':str(a.source/'official_config.json')})
        for index,e in enumerate(actions,1):
            payload=e['data']['proposal']['payload'];native=create_page_focus_action(int(payload['index']))if payload['type']=='tab'else action(payload)
            if payload['type']=='wait':env.page.wait_for_timeout(1000)
            obs,ok,_,_,info=env.step(native);assert ok,info
            journal.append('prefix_action_replayed',{'source_seq':e['seq'],'payload':payload,'actual_after_sha256':digest(png(obs))})
        before=png(env._get_obs());(a.root/'before-repair.png').write_bytes(before)
        sequence=0
        def public_view(raw):
            nonlocal sequence
            sequence+=1;messages=copy.deepcopy(public['messages']);replaced=0
            for message in messages:
                if not isinstance(message.get('content'),list):continue
                for block in message['content']:
                    if block.get('type')!='image_url':continue
                    url=block['image_url'];url=url['url']if isinstance(url,dict)else url
                    if url.startswith('data:image/')and digest(base64.b64decode(url.split(',',1)[1]))==current['sha256']:
                        block['image_url']={'url':'data:image/png;base64,'+base64.b64encode(raw).decode()};replaced+=1
            assert replaced==1
            return PublicView('009-live%03d'%sequence,messages,(VisibleImage(raw),),public['recent_action'],public['execution_feedback'])
        c=Controller(model.judge,journal,arm,Limits(**lim))
        c.actor_calls=sum(e['kind']=='actor_request'for e in events)
        c.verifier_calls=sum(e['kind']=='verifier_request'for e in events)
        original_counts={'actor':c.actor_calls,'verifier':c.verifier_calls}
        originals={e['data']['public']['observation_id']:e['data']['public']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'}
        for e in events:
            if e['kind']!='decision_accepted':continue
            old=originals[e['data']['observation_id']]
            view=PublicView(old['observation_id'],old['messages'],tuple(VisibleImage((a.source/(im['sha256']+'.image')).read_bytes(),im['role'])for im in old['images']),old['recent_action'],old['execution_feedback'],old['observed_at'])
            c.remember(view,e['data']['candidate'])
        def actor(view,corrections):
            body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'};body['messages']=copy.deepcopy(view.messages)
            return model.actor(body)
        def parser(text):
            payload=parse(text);action(payload)
            return {'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'payload':payload,'coordinate_space':'normalized_1000'}
        def recapture():
            raw=png(env._get_obs());(a.root/('recapture-%03d.png'%sequence)).write_bytes(raw);return public_view(raw)
        journal.append('source_initialized_decision',{'source':str(a.source),'source_request_seq':req['seq'],'source_events_sha256':digest((a.source/'events.jsonl').read_bytes()),'prefix_actions':8,'original_prefix_call_counts':original_counts,'source_initial_current_sha256':current['sha256'],'fresh_current_sha256':digest(before),'original_limits':lim,'initial_corrections':[],'full_controller_decide_unchanged':True})
        status(phase='complete_controller_decision',current_matches_source=digest(before)==current['sha256'])
        result=c.decide(public_view(before),actor,parser,recapture)
        passed=result['status']=='accepted'and result['proposal']['payload']=={'type':'scroll','direction':'up'}
        after=None
        if passed:
            payload=result['proposal']['payload'];native=action(payload);native['raw_prediction']=result['candidate']
            obs,ok,_,_,info=env.step(native);assert ok,info;c.executed(result,json.dumps({'execution_returned':bool(ok),'result_state':'not confirmed by execution alone'}))
            after=png(env._get_obs());(a.root/'after-repair.png').write_bytes(after);passed=after!=before
        summary={'phase':'completed','passed':passed,'result':result,'candidate':result.get('candidate'),'proposal':result.get('proposal'),'before_sha256':digest(before),'after_sha256':digest(after)if after else None,'current_matches_source':digest(before)==current['sha256'],'source_attempt':str(a.source),'source_prefix_actions':8,'actual_recovery_actions':int(after is not None),'original_prefix_call_counts':original_counts,'final_actor_calls':c.actor_calls,'final_verifier_calls':c.verifier_calls,'model_calls':model.calls,'full_controller_decide_unchanged':True,'official_evaluations':0,'full_task_recovered':None,'requires_independent_after_image_review':True,'scope':'Nonblind source-initialized single-decision diagnostic under original remaining call and per-decision budgets, not a complete natural trajectory.'}
        (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));status(phase='completed',passed=passed)
        print(json.dumps({'passed':passed,'result':result}),flush=True)
    except Exception:
        (a.root/'failure.json').write_text(json.dumps({'traceback':traceback.format_exc(),'model_calls':model.calls},indent=2));status(phase='failed');raise
    finally:
        try:env.save_trace(a.root/'browser-trace.zip')
        finally:env.close()

if __name__=='__main__':main()
