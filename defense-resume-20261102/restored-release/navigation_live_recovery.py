"""One back action in a fresh browser after replaying nine archived GUI actions.

This is a source-initialized local recovery diagnostic, never a natural whole task.
Only byte-identical public inputs/system/candidate may reuse a measured raw verdict.
"""
import argparse,base64,copy,json,os,sys,time,traceback
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--probe',type=Path,required=True);ap.add_argument('--release',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
sys.path.insert(0,str(a.release))
from defense.core import PublicView,VisibleImage,Controller,Journal,Limits,digest,canonical
from defense.http_backend import RemoteQwen

def main():
    a.root.mkdir(parents=True,exist_ok=False);journal=Journal(a.root/'recovery')
    def status(**x):(a.root/'status.json').write_text(json.dumps(x))
    status(phase='waiting_development_controls')
    deadline=time.time()+900
    while not(a.probe/'summary.json').exists():
        if time.time()>deadline:raise RuntimeError('Bounded development prerequisite timeout')
        time.sleep(2)
    summary=json.loads((a.probe/'summary.json').read_text());assert summary['passed']
    events=[json.loads(l)for l in(a.source/'events.jsonl').read_text().splitlines()]
    actions=[e for e in events if e['kind']=='action_executed'];assert len(actions)==9
    req=next(e['data']for e in reversed(events)if e['kind']=='verifier_request'and e['data']['phase']=='verify'and not e['data']['format_retry'])
    public=req['public'];candidate=req['candidate'];proposal=req['proposal'];assert proposal['name']=='back'
    recorded=[json.loads(l)for l in(a.probe/'exact_failed_back/events.jsonl').read_text().splitlines()]
    probe_request=next(e['data']for e in recorded if e['kind']=='verifier_request')
    probe_raw=next(e['data']['response']for e in recorded if e['kind']=='verifier_raw')
    assert sum(e['kind']=='verifier_request'for e in recorded)==1
    base=Path('/data/researcher/vwa100-2026-10-09');sys.path[:0]=[str(base),str(base/'upstream/visualwebarena-main')]
    from run_reddit_internvl_smoke import action,png
    from browser_env import ScriptBrowserEnv
    from browser_env.actions import create_page_focus_action
    env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file);reused=[]
    manifest={'source_attempt':str(a.source),'source_events_sha256':digest((a.source/'events.jsonl').read_bytes()),'probe_summary_sha256':digest((a.probe/'summary.json').read_bytes()),'prefix_actual_actions':9,'scope':'Fresh browser initialized by replayed archived actions; one proposed back verified/executed. Not natural full trajectory, formal outcome or efficacy estimate.'}
    (a.root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    status(phase='replaying_prefix',actions=0)
    try:
        obs,info=env.reset(seed=20261011,options={'config_file':str(a.source/'official_config.json')})
        for i,e in enumerate(actions,1):
            payload=e['data']['proposal']['payload'];native=create_page_focus_action(int(payload['index']))if payload['type']=='tab'else action(payload)
            if payload['type']=='wait':env.page.wait_for_timeout(1000)
            obs,ok,_,_,info=env.step(native);assert ok,info
            raw=png(obs);(a.root/(f'prefix-{i:03}.png')).write_bytes(raw)
            journal.append('prefix_action_replayed',{'source_seq':e['seq'],'payload':payload,'actual_image_sha256':digest(raw)})
        before=png(env._get_obs());(a.root/'before-back.png').write_bytes(before)
        original_current=next(im for im in public['images']if im['role']=='current');same=digest(before)==original_current['sha256']
        messages=copy.deepcopy(public['messages']);images=[]
        for im in public['images']:
            raw=before if im['role']=='current'else(a.source/(im['sha256']+'.image')).read_bytes()
            images.append(VisibleImage(raw,im['role']))
        if not same:
            for m in messages:
                if isinstance(m.get('content'),list):
                    for b in m['content']:
                        if b.get('type')=='image_url':
                            url=b['image_url']['url']
                            if url.startswith('data:image/')and digest(base64.b64decode(url.split(',',1)[1]))==original_current['sha256']:
                                b['image_url']={'url':'data:image/png;base64,'+base64.b64encode(before).decode()}
        view=PublicView(public['observation_id'],messages,tuple(images),public['recent_action'],public['execution_feedback'],public['observed_at'])
        def judge(system,v,c):
            if same and system==probe_request['system']and canonical(v.data())==canonical(probe_request['public'])and c==probe_request['candidate']:
                reused.append({'source_raw_event_sha256':next(e['sha256']for e in recorded if e['kind']=='verifier_raw'),'full_request_equal':True});return copy.deepcopy(probe_raw)
            return model.judge(system,v,c)
        controller=Controller(judge,journal,'post_only',Limits());journal.observation(view,audience='source_initialized_live')
        status(phase='verifying_live_back',prefix_actions=9,current_bytes_match=same)
        verdict=controller.inspect('verify',view,candidate,proposal)
        assert verdict['action']['status']=='supported',verdict
        assert not any(c['kind']in {'gui_fact','history_report'}and c['status']in {'contradicted','insufficient'}for c in verdict['claims']),verdict
        journal.append('verified_back',{'verdict':verdict,'source_candidate':candidate,'new_model_calls':len(model.calls),'reused':reused})
        obs,ok,_,_,info=env.step(action(proposal['payload']));assert ok,info
        after=png(env._get_obs());(a.root/'after-back.png').write_bytes(after)
        journal.append('diagnostic_back_executed',{'payload':proposal['payload'],'actual_after_sha256':digest(after),'execution_returned':bool(ok)})
        result={'phase':'completed','passed':digest(before)!=digest(after),'actual_prefix_actions':9,'actual_recovery_actions':1,'current_bytes_match_archived':same,'new_model_calls':len(model.calls),'exact_input_reused_verdicts':len(reused),'verdict':verdict,'before_sha256':digest(before),'after_sha256':digest(after),'after_url':env.page.url,'not_formal_completion':True,'official_score':None,'scope':manifest['scope']+' A changed frame alone is not independent destination verification; inspect after-back.png.'}
        (a.root/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));status(phase='completed',passed=result['passed'])
        print(json.dumps({k:v for k,v in result.items()if k!='verdict'}),flush=True)
    except Exception:
        (a.root/'failure.json').write_text(json.dumps({'traceback':traceback.format_exc(),'not_formal_completion':True},indent=2));status(phase='failed');raise
    finally:
        try:env.save_trace(a.root/'browser_trace.zip')
        finally:env.close()

if __name__=='__main__':main()
