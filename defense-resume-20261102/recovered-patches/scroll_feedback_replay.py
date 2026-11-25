"""Real-model, source-bound direction recovery controls; no GUI or formal score."""
import argparse,copy,json,time,traceback
from pathlib import Path
from dataclasses import replace

from defense.core import PublicView,VisibleImage,Controller,Journal,Limits,canonical,digest,correction_message
from defense.http_backend import RemoteQwen
from scroll_source import with_native_action_feedback


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--token-file',type=Path,required=True);a=ap.parse_args()
    a.root.mkdir(parents=True,exist_ok=False)
    base=Path('/data/researcher/vwa100-2026-10-09')
    import sys
    sys.path[:0]=[str(base),str(base/'upstream/visualwebarena-main')]
    from run_reddit_internvl_smoke import parse,action
    template=json.loads((Path(__file__).parent/'native-vwa-request.json').read_bytes())
    model=RemoteQwen('http://192.0.2.11:18127',a.token_file)
    results=[];sources=[]
    def status(**x):(a.root/'status.json').write_text(json.dumps({'time':time.time(),**x}))
    def load_public(pub,source):
        images=tuple(VisibleImage((source/(im['sha256']+'.image')).read_bytes(),im['role'])for im in pub['images'])
        view=PublicView(pub['observation_id'],copy.deepcopy(pub['messages']),images,pub['recent_action'],pub['execution_feedback'],pub['observed_at'])
        assert canonical(view.data())==canonical(pub)
        return view
    def controller(source,events,view,name):
        journal=Journal(a.root/name)
        c=Controller(model.judge,journal,'post_only',Limits(max_format_retries=0))
        # Only real previously accepted/delivered frames enter the reference bank.
        observations={e['data']['public']['observation_id']:e['data']['public']for e in events if e['kind']=='observation'and e['data'].get('audience','actor')=='actor'}
        for e in events:
            if e['kind']=='decision_accepted'and e['data']['observation_id']in observations:
                pub=observations[e['data']['observation_id']]
                c.remember(load_public(pub,source),e['data']['candidate'])
        journal.observation(view,audience='source_bound_development')
        return c
    def proposal(text):
        payload=parse(text);action(payload)
        return {'name':payload['type'],'parsed':True,'executor_fallback_wait':False,'payload':payload,'coordinate_space':'normalized_1000'}
    for arm in ['joint','post_only']:
        marker=a.source_root/'runs'/('vwa--classifieds_112--stale_replace--'+arm)/'complete.json'
        ptr=json.loads(marker.read_bytes());source=Path(ptr['attempt']);assert digest((source/'complete.json').read_bytes())==ptr['sha256']
        events=[json.loads(line)for line in(source/'events.jsonl').read_text().splitlines()]
        req,corrections,rejected_seq=with_native_action_feedback(events,proposal)
        events=[e for e in events if e['seq']<req['seq']]
        old=load_public(req['data']['public'],source)
        messages=copy.deepcopy(old.messages);assert messages[-1]['content'].startswith('TASK-STATE CORRECTION.')
        messages[-1]=correction_message(corrections)
        public=replace(old,messages=messages)
        assert public.messages[:-1]==old.messages[:-1] and public.images==old.images
        name=arm+'_scroll_reconsideration';status(phase='running',case=name)
        c=controller(source,events,public,name);before=len(model.calls)
        body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'};body['messages']=public.messages
        c.log.append('development_actor_request',{'public':public.data(),'native_parameters':{k:v for k,v in body.items()if k!='messages'},'only_changed_message':'final defense correction','source_request_seq':req['seq']})
        try:
            candidate=model.actor(body);p=proposal(candidate);c.log.append('development_actor_raw',{'text':candidate,'proposal':p})
            verdict=c.inspect('verify',public,candidate,p)
            bad=[x for x in verdict['claims']if x['kind']in {'gui_fact','history_report'}and x['status']!='supported']
            passed=p['name']=='scroll'and p['payload']['direction']=='up'and verdict['action']['status']=='supported'and not bad
            row={'case':name,'passed':passed,'candidate':candidate,'proposal':p,'verdict':verdict,'calls':model.calls[before:],'source':str(source),'source_events_sha256':digest((source/'events.jsonl').read_bytes()),'source_actor_request_seq':req['seq'],'full_history_images_and_native_parameters_preserved':True}
        except Exception:row={'case':name,'passed':False,'traceback':traceback.format_exc(),'calls':model.calls[before:]}
        results.append(row);(a.root/(name+'-result.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2))
        sources.append((source,events,public))
    # Fixed source-grounded controls; expected labels stay outside model inputs.
    source,events,public=sources[0]
    controls=[('up_text_down_json_rejected','I will scroll back up to inspect earlier items.\n<action>{"type":"scroll","direction":"down"}</action>','rejected'),
              ('valid_down_not_globally_forced_up','I cannot confirm a global minimum. I will scroll down to inspect additional listings.\n<action>{"type":"scroll","direction":"down"}</action>','supported'),
              ('pure_native_wait','I will wait for another observation.\n<action>{"type":"wait"}</action>','wait')]
    (a.root/'control-expectations.json').write_text(json.dumps([{'name':n,'expected':e,'candidate_sha256':digest(t.encode())}for n,t,e in controls],indent=2))
    for name,candidate,expected in controls:
        status(phase='running',case=name);c=controller(source,events,public,name);before=len(model.calls)
        try:
            p=proposal(candidate);v=c.inspect('verify',public,candidate,p)
            passed=(v['action']['status']!='supported'if expected=='rejected'else v['pure_wait']and v['action']['status']=='supported'if expected=='wait'else v['action']['status']=='supported')
            row={'case':name,'passed':passed,'candidate':candidate,'proposal':p,'verdict':v,'calls':model.calls[before:]}
        except Exception:row={'case':name,'passed':False,'traceback':traceback.format_exc(),'calls':model.calls[before:]}
        results.append(row);(a.root/(name+'-result.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2))
    summary={'phase':'completed','passed':len(results)==5 and all(x['passed']for x in results),'results':results,'new_model_calls':len(model.calls),'source_initialized':True,'new_gui_actions':0,'official_evaluations':0,'scope':'Nonblind development on two archived blocked traces, not full trajectories, independent Mirage labels or efficacy'}
    (a.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));status(phase='completed',passed=summary['passed'])
    print(json.dumps({'phase':'completed','passed':summary['passed'],'results':[{'case':x['case'],'passed':x['passed']}for x in results]}),flush=True)


if __name__=='__main__':main()
