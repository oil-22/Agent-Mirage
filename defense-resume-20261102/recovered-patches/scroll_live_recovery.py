"""Fresh browser prefix initialization, corrected native action, real screenshot.

This is a development recovery diagnostic, not a whole natural trajectory. It
does not change native action JSON or relabel the original terminal outcomes.
"""
import argparse,base64,copy,json,sys,time,traceback
from pathlib import Path

from defense.core import (PublicView,VisibleImage,Controller,Journal,Limits,
                          digest,correction_message)
from defense.http_backend import RemoteQwen
from scroll_source import with_native_action_feedback


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--development',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
    a.root.mkdir(parents=True,exist_ok=False);journal=Journal(a.root/'events')
    def status(**x):(a.root/'status.json').write_text(json.dumps({'time':time.time(),**x}))
    status(phase='waiting_five_development_controls')
    deadline=time.time()+1500
    while not(a.development/'summary.json').exists():
        if time.time()>deadline:raise RuntimeError('Bounded development prerequisite timeout; no browser started')
        time.sleep(2)
    dev=json.loads((a.development/'summary.json').read_bytes());assert dev['passed'],'Development controls failed, no browser started'
    base=Path('/data/researcher/vwa100-2026-10-09');sys.path[:0]=[str(base),str(base/'upstream/visualwebarena-main')]
    from run_reddit_internvl_smoke import parse,action,png
    from browser_env import ScriptBrowserEnv
    from browser_env.actions import create_page_focus_action
    events=[json.loads(line)for line in(a.source/'events.jsonl').read_text().splitlines()]
    actions=[e for e in events if e['kind']=='action_executed'];assert len(actions)==8
    def parse_proposal(text):
        payload=parse(text);action(payload)
        return {'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'payload':payload,'coordinate_space':'normalized_1000'}
    req,corrections,rejected_seq=with_native_action_feedback(events,parse_proposal)
    events=[e for e in events if e['seq']<req['seq']]
    public=req['data']['public'];current=next(im for im in public['images']if im['role']=='current')
    template=json.loads((Path(__file__).parent/'native-vwa-request.json').read_bytes())
    env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file)
    status(phase='replaying_eight_source_actions')
    try:
        obs,info=env.reset(seed=20261011,options={'config_file':str(a.source/'official_config.json')})
        for index,e in enumerate(actions,1):
            payload=e['data']['proposal']['payload'];native=create_page_focus_action(int(payload['index']))if payload['type']=='tab'else action(payload)
            if payload['type']=='wait':env.page.wait_for_timeout(1000)
            obs,ok,_,_,info=env.step(native);assert ok,info
            raw=png(obs);(a.root/('prefix-%03d.png'%index)).write_bytes(raw)
            journal.append('prefix_action_replayed',{'source_seq':e['seq'],'payload':payload,'actual_after_sha256':digest(raw)})
        before=png(env._get_obs());(a.root/'before-repair.png').write_bytes(before)
        messages=copy.deepcopy(public['messages']);messages[-1]=correction_message(corrections)
        replaced=0
        for message in messages:
            if not isinstance(message.get('content'),list):continue
            for block in message['content']:
                if block.get('type')!='image_url':continue
                url=block['image_url'];url=url['url']if isinstance(url,dict)else url
                if url.startswith('data:image/')and digest(base64.b64decode(url.split(',',1)[1]))==current['sha256']:
                    block['image_url']={'url':'data:image/png;base64,'+base64.b64encode(before).decode()};replaced+=1
        assert replaced==1
        view=PublicView('live-scroll-recovery',messages,(VisibleImage(before),),public['recent_action'],public['execution_feedback'])
        c=Controller(model.judge,journal,'post_only',Limits(max_format_retries=0))
        original_views={e['data']['public']['observation_id']:e['data']['public']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'}
        for e in events:
            if e['kind']!='decision_accepted':continue
            old=original_views[e['data']['observation_id']]
            prior=PublicView(old['observation_id'],old['messages'],tuple(VisibleImage((a.source/(im['sha256']+'.image')).read_bytes(),im['role'])for im in old['images']),old['recent_action'],old['execution_feedback'],old['observed_at'])
            c.remember(prior,e['data']['candidate'])
        journal.observation(view,audience='fresh_live_source_initialized')
        body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'};body['messages']=view.messages
        status(phase='generating_live_reconsideration',current_matches_source=digest(before)==current['sha256'])
        journal.append('live_actor_request',{'public':view.data(),'native_parameters':{k:v for k,v in body.items()if k!='messages'}})
        candidate=model.actor(body);payload=parse(candidate);native=action(payload)
        proposal={'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'payload':payload,'coordinate_space':'normalized_1000'}
        journal.append('live_actor_raw',{'text':candidate,'proposal':proposal})
        verdict=c.inspect('verify',view,candidate,proposal)
        bad=[x for x in verdict['claims']if x['kind']in {'gui_fact','history_report'}and x['status']!='supported']
        assert payload['type']=='scroll'and payload['direction']=='up'and verdict['action']['status']=='supported'and not bad,verdict
        journal.append('live_proposal_verified',{'candidate':candidate,'proposal':proposal,'verdict':verdict,'native_json_not_modified':True})
        status(phase='executing_original_actor_up')
        obs,ok,_,_,info=env.step(native);assert ok,info
        after=png(env._get_obs());(a.root/'after-repair.png').write_bytes(after)
        journal.append('live_recovery_action_executed',{'payload':payload,'actual_after_sha256':digest(after),'execution_returned':bool(ok)})
        result={'phase':'completed','passed':digest(before)!=digest(after),'source_attempt':str(a.source),'source_events_sha256':digest((a.source/'events.jsonl').read_bytes()),'source_prefix_actions':8,'actual_recovery_actions':1,'candidate':candidate,'proposal':proposal,'verdict':verdict,'before_sha256':digest(before),'after_sha256':digest(after),'current_matches_source':digest(before)==current['sha256'],'model_calls':model.calls,'official_evaluations':0,'full_task_recovered':None,'requires_independent_after_image_review':True,'scope':'Source-initialized live diagnostic; changing screenshot is not itself recovery proof or an efficacy estimate. Original terminal results unchanged.'}
        (a.root/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));status(phase='completed',passed=result['passed'])
        print(json.dumps({'phase':'completed','passed':result['passed'],'candidate':candidate}),flush=True)
    except Exception:
        (a.root/'failure.json').write_text(json.dumps({'traceback':traceback.format_exc(),'model_calls':model.calls},indent=2));status(phase='failed');raise
    finally:
        try:env.save_trace(a.root/'browser-trace.zip')
        finally:env.close()


if __name__=='__main__':main()
